# servicios/seguimiento_ordenes.py - versión actualizada con condiciones JSON

from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from modelos.Producto import Producto, HolonRuta
from modelos.Versionamiento import VersionRuta
from modelos.Encadenamiento import ConfiguracionEncadenamiento
from utils.motor_abtppn import MotorABTPPN, TokenColoreado
from servicios.orquestador import Orquestador
from servicios.verificador_terminacion import VerificadorTerminacion
from servicios.planificador import PlanificadorProduccion


class ServicioSeguimiento:
    """
    Servicio para el seguimiento de órdenes de producción.
    Maneja el ciclo: evento SCADA → evolución de red → persistencia.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.motor = MotorABTPPN()
        self.orquestador = Orquestador(self.motor, session)
        self.verificador = VerificadorTerminacion(session)
    
    # ============================================================
    # CREACIÓN DE ORDEN
    # ============================================================
    
    def crear_orden(self, producto_id: int, cantidad: float, prioridad: int = 1, cliente: str = None) -> OrdenProduccion:
        planificador = PlanificadorProduccion(self.session)
        plan = planificador.seleccionar_recursos_para_orden(producto_id, cantidad, prioridad)
        if not plan:
            raise ValueError("No se pudo asignar recursos para la orden")
        
        orden = OrdenProduccion(
            producto_id=producto_id,
            cantidad=cantidad,
            prioridad=prioridad,
            cliente=cliente,
            holon_ruta_id=plan["holon_ruta_id"],
            asignacion_recursos=plan["asignacion"],   # ← nuevo
            estado="pendiente"
        )
        self.session.add(orden)
        self.session.commit()
        return orden
    
    def _seleccionar_mejor_ruta(self, producto_id: int, cantidad: float, 
                                 prioridad: int) -> Optional[HolonRuta]:
        """Selecciona la mejor ruta según condiciones en JSON"""
        
        rutas = self.session.query(HolonRuta).filter(
            HolonRuta.producto_id == producto_id,
            HolonRuta.activa == True
        ).all()
        
        rutas_validas = []
        
        for ruta in rutas:
            # Obtener condiciones del JSON
            condiciones = ruta.condiciones or {}
            
            # Verificar rango de lote
            lote_min = condiciones.get('lote_minimo_kg', 0)
            lote_max = condiciones.get('lote_maximo_kg', float('inf'))
            
            if cantidad < lote_min or cantidad > lote_max:
                continue
            
            # Verificar prioridad mínima
            prioridad_min = condiciones.get('prioridad_minima', 1)
            if prioridad < prioridad_min:
                continue
            
            rutas_validas.append(ruta)
        
        if not rutas_validas:
            return None
        
        # Ordenar por orden_preferencia (menor número = mayor prioridad)
        rutas_validas.sort(key=lambda r: r.condiciones.get('orden_preferencia', 999))
        
        return rutas_validas[0]
    
    # ============================================================
    # INICIALIZACIÓN DE EJECUCIÓN
    # ============================================================
    
    def iniciar_ejecucion(self, orden_id: int) -> bool:
        """
        Inicia la ejecución de una orden.
        Crea todas las instancias de red y procesa automáticas iniciales.
        """
        
        orden = self.session.query(OrdenProduccion).get(orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no existe")
        
        holon_ruta = self.session.query(HolonRuta).get(orden.holon_ruta_id)
        if not holon_ruta:
            raise ValueError(f"HolonRuta {orden.holon_ruta_id} no existe")
        
        # Obtener la versión activa de ruta
        version_ruta = self.session.query(VersionRuta).filter_by(
            producto_id=orden.producto_id,
            estado="activa"
        ).first()
        
        if not version_ruta:
            # Crear versión por defecto
            version_ruta = self._crear_version_por_defecto(orden.producto_id, holon_ruta.id)
        
        orden.version_ruta_id = version_ruta.id
        
        # Token inicial
        token_inicial = TokenColoreado(
            orden_id=f"ORD-{orden.id}",
            material=orden.cantidad,
            coste=0.0,
            timestamp=datetime.now()
        )
        
        # Crear instancias para cada red en la versión
        instancias_creadas = []
        
        for red_nombre, red_snapshot in version_ruta.redes_snapshot.items():
            # Buscar el archivo PNML
            pnml_path = red_snapshot.get('archivo_pnml_origen')
            if not pnml_path:
                continue
            
            # Ajustar ruta si es necesario
            from pathlib import Path
            if not Path(pnml_path).exists():
                # Buscar en la carpeta rutas_producto
                posibles = [
                    Path(f"rutas_producto/PintucoBaseAgua_V1/redes/{Path(pnml_path).name}"),
                    Path(pnml_path)
                ]
                for p in posibles:
                    if p.exists():
                        pnml_path = str(p)
                        break
            
            # Crear instancia en motor
            inst_mem_id = self.motor.crear_instancia(
                red_nombre=red_nombre,
                orden_id=orden.id,
                token_inicial=token_inicial,
                pnml_path=pnml_path
            )
            
            if inst_mem_id:
                # Guardar en BD
                instancia_bd = InstanciaRed(
                    orden_id=orden.id,
                    tipo="hija" if "integracion" not in red_nombre.lower() else "principal",
                    patron_ruta_id=holon_ruta.patron_id,
                    holon_ruta_id=holon_ruta.id,
                    marcado=self.motor.obtener_marcado(inst_mem_id),
                    token_o=token_inicial.orden_id,
                    token_m=token_inicial.material,
                    token_c=token_inicial.coste,
                    token_t=token_inicial.timestamp,
                    activa=True
                )
                self.session.add(instancia_bd)
                self.session.flush()
                
                self.motor.actualizar_instancia_bd_id(inst_mem_id, instancia_bd.id)
                instancias_creadas.append(inst_mem_id)
        
        # Cargar reglas de encadenamiento en el orquestador
        if version_ruta.encadenamiento_id:
            encadenamiento = self.session.query(ConfiguracionEncadenamiento).get(
                version_ruta.encadenamiento_id
            )
            if encadenamiento and encadenamiento.reglas:
                self.orquestador.mapeo_mensajes = encadenamiento.reglas
        
        # Procesar transiciones automáticas iniciales
        for inst_mem_id in instancias_creadas:
            self.orquestador.procesar_automaticas_instancia(inst_mem_id)
        
        # Actualizar orden
        orden.estado = "en_produccion"
        orden.fecha_inicio = datetime.now()
        
        self.session.commit()
        
        print(f"   ✅ Orden {orden.id} iniciada con {len(instancias_creadas)} instancias")
        return True
    
    def _crear_version_por_defecto(self, producto_id: int, holon_ruta_id: int) -> VersionRuta:
        """Crea una versión por defecto si no existe"""
        
        from modelos.Producto import Producto
        
        producto = self.session.query(Producto).get(producto_id)
        
        version = VersionRuta(
            nombre=producto.codigo,
            version_semver="1.0.0",
            estado="activa",
            creado_por="sistema",
            descripcion="Versión creada automáticamente",
            producto_id=producto_id,
            holon_ruta_id=holon_ruta_id,
            encadenamiento_id=0,
            redes_snapshot={}
        )
        self.session.add(version)
        self.session.commit()
        
        return version
    
    # ============================================================
    # PROCESAMIENTO DE EVENTOS
    # ============================================================
    
    def procesar_evento(self, orden_id: int, recurso: str, 
                        red_nombre: str, evento_nombre: str,
                        datos: Dict = None) -> Dict:
        """
        Procesa un evento de planta (SCADA o Tablet).
        """
        
        orden = self.session.query(OrdenProduccion).get(orden_id)
        if not orden:
            return {"error": f"Orden {orden_id} no existe", "procesado": False}
        
        if orden.estado != "en_produccion":
            return {"error": f"Orden {orden_id} no está en producción", "procesado": False}
        
        # Usar el orquestador para procesar el evento
        resultado = self.orquestador.procesar_evento_planta(
            orden_id=orden_id,
            red_nombre=red_nombre,
            evento_nombre=evento_nombre,
            recurso_id=recurso,
            timestamp=datetime.now()
        )
        
        if resultado:
            # Verificar si la orden terminó
            if self._verificar_orden_terminada(orden_id):
                orden.estado = "completada"
                orden.fecha_fin = datetime.now()
                self.session.commit()
            
            return {
                "procesado": True,
                "mensaje": f"Evento {evento_nombre} procesado en {red_nombre}",
                "orden_terminada": orden.estado == "completada"
            }
        else:
            return {
                "procesado": False,
                "error": f"No se pudo procesar {evento_nombre} en {red_nombre}"
            }
    
    def _verificar_orden_terminada(self, orden_id: int) -> bool:
        """Verifica si la orden ha terminado"""
        resultado = self.verificador.orden_terminada(orden_id)
        return resultado["terminada"]
    
    def procesar_mensajes_pendientes(self, orden_id: int = None):
        """Procesa mensajes pendientes en cola (handshakes)"""
        self.orquestador.procesar_mensajes_pendientes(orden_id)
    
    def obtener_estado(self, orden_id: int) -> Dict:
        """Obtiene el estado actual de una orden"""
        
        orden = self.session.query(OrdenProduccion).get(orden_id)
        if not orden:
            return {"error": f"Orden {orden_id} no existe"}
        
        instancias = self.session.query(InstanciaRed).filter(
            InstanciaRed.orden_id == orden_id,
            InstanciaRed.activa == True
        ).all()
        
        estado_redes = []
        for inst in instancias:
            estado_redes.append({
                "red": inst.tipo,
                "marcado": inst.marcado,
                "token_material": inst.token_m,
                "token_coste": inst.token_c
            })
        
        return {
            "orden_id": orden.id,
            "estado": orden.estado,
            "producto": orden.producto.codigo if orden.producto else "N/A",
            "cantidad": orden.cantidad,
            "fecha_inicio": orden.fecha_inicio.isoformat() if orden.fecha_inicio else None,
            "redes": estado_redes
        }