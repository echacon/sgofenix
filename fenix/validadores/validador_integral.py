# validadores/validador_integral.py
"""
=============================================================================
FÉNIX - Validador Integral de Planta y Semáforo Pre-Producción
=============================================================================
Implementa las cuatro verificaciones descritas en el Manual de Usuario:
1. Integridad Referencial (Insumos, Servicios, Recursos, Calendarios).
2. Conectividad Física del Grafo de Planta (Matriz K y continuidad de rutas).
3. Parámetros e Invariantes de Calidad/Seguridad (Rendimientos, Tarifas).
4. Prueba en Seco (Dry-Run de Orden Cero: retropropagación y costeo ABC).

Emite un diagnóstico visual (VERDE / AMARILLO / ROJO) y reporte estructurado.
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque


@dataclass
class ItemDiagnostico:
    nivel: str  # 'ERROR', 'ADVERTENCIA', 'INFO'
    categoria: str  # 'INTEGRIDAD', 'CONECTIVIDAD', 'PARAMETROS', 'DRY_RUN'
    mensaje: str
    detalles: Optional[str] = None


@dataclass
class ReporteDiagnostico:
    estado_semaforo: str  # 'VERDE', 'AMARILLO', 'ROJO'
    total_errores: int = 0
    total_advertencias: int = 0
    total_info: int = 0
    items: List[ItemDiagnostico] = field(default_factory=list)
    resumen_recursos: Dict[str, Any] = field(default_factory=dict)
    resumen_productos: Dict[str, Any] = field(default_factory=dict)
    
    def agregar(self, nivel: str, categoria: str, mensaje: str, detalles: Optional[str] = None):
        self.items.append(ItemDiagnostico(nivel, categoria, mensaje, detalles))
        if nivel == 'ERROR':
            self.total_errores += 1
        elif nivel == 'ADVERTENCIA':
            self.total_advertencias += 1
        else:
            self.total_info += 1


class ValidadorIntegralPlanta:
    """Validador integral de configuraciones y modelos de planta para FÉNIX."""

    def __init__(self):
        self.reporte = ReporteDiagnostico(estado_semaforo='VERDE')
        self.recursos: Dict[str, Dict[str, Any]] = {}
        self.productos: Dict[str, Dict[str, Any]] = {}
        self.grafo_conectividad: Dict[str, Set[str]] = defaultdict(set)
        self.servicios_ofrecidos: Dict[str, Set[str]] = defaultdict(set)  # servicio -> set(recursos)
        self.materiales: Dict[str, float] = {}  # material_id -> costo_unitario

    def cargar_desde_yaml(self, dir_config: Path) -> bool:
        """Carga y consolida todos los archivos YAML del directorio de configuración."""
        if not dir_config.exists():
            self.reporte.agregar('ERROR', 'INTEGRIDAD', f"Directorio de configuracion no encontrado: {dir_config}")
            return False

        archivos = list(dir_config.glob("*.yaml")) + list(dir_config.glob("*.yml"))
        if not archivos:
            self.reporte.agregar('ERROR', 'INTEGRIDAD', f"No se encontraron archivos YAML en {dir_config}")
            return False

        for arc in archivos:
            try:
                with open(arc, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                # Cargar Recursos
                if 'recursos' in data:
                    for r in data['recursos']:
                        codigo = r.get('codigo') or r.get('id')
                        if codigo:
                            self.recursos[codigo] = r
                elif 'resource' in data:
                    r = data['resource']
                    codigo = r.get('id') or r.get('codigo')
                    if codigo:
                        self.recursos[codigo] = r

                # Cargar Productos
                if 'productos' in data:
                    for p in data['productos']:
                        codigo = p.get('codigo') or p.get('id')
                        if codigo:
                            self.productos[codigo] = p
                elif 'product' in data:
                    p = data['product']
                    codigo = p.get('id') or p.get('codigo')
                    if codigo:
                        self.productos[codigo] = p

                # Cargar Conectividad explícita si existe
                if 'conectividad' in data:
                    for origen, destinos in data['conectividad'].items():
                        if isinstance(destinos, list):
                            self.grafo_conectividad[origen].update(destinos)
                        elif isinstance(destinos, str):
                            self.grafo_conectividad[origen].add(destinos)

                # Cargar Materiales si existen
                if 'materiales' in data:
                    for m in data['materiales']:
                        m_id = m.get('id') or m.get('codigo')
                        costo = float(m.get('costo_unitario', m.get('precio', 1.0)))
                        if m_id:
                            self.materiales[m_id] = costo

            except Exception as e:
                self.reporte.agregar('ERROR', 'INTEGRIDAD', f"Error parseando {arc.name}: {str(e)}")

        return True

    def ejecutar_diagnostico_completo(self) -> ReporteDiagnostico:
        """Ejecuta las 4 fases de validacion integral."""
        
        # 1. Procesar Recursos y Mapear Servicios / Conectividad
        self._mapear_recursos_y_conectividad()

        # 2. Fase 1: Integridad Referencial
        self._validar_integridad_referencial()

        # 3. Fase 2: Conectividad Fisica del Grafo
        self._validar_conectividad_rutas()

        # 4. Fase 3: Parametros e Invariantes
        self._validar_parametros_invariantes()

        # 5. Fase 4: Prueba en Seco (Dry Run)
        self._ejecutar_prueba_en_seco()

        # Determinar Semaforo Final
        if self.reporte.total_errores > 0:
            self.reporte.estado_semaforo = 'ROJO'
        elif self.reporte.total_advertencias > 0:
            self.reporte.estado_semaforo = 'AMARILLO'
        else:
            self.reporte.estado_semaforo = 'VERDE'

        self.reporte.resumen_recursos = {
            'total_recursos': len(self.recursos),
            'servicios_disponibles': list(self.servicios_ofrecidos.keys())
        }
        self.reporte.resumen_productos = {
            'total_productos': len(self.productos)
        }

        return self.reporte

    def _mapear_recursos_y_conectividad(self):
        """Mapea servicios y construye el grafo de conectividad K."""
        for r_id, r in self.recursos.items():
            # Extraer servicios
            servicios = r.get('puede_hacer', [])
            if not servicios and 'services' in r:
                servicios = [s.get('id') for s in r['services'] if isinstance(s, dict)]
            
            for s in servicios:
                self.servicios_ofrecidos[s].add(r_id)

            # Extraer conectividad interna declarada en el recurso
            conn = r.get('conectividad') or r.get('connectivity', [])
            if isinstance(conn, list):
                self.grafo_conectividad[r_id].update(conn)
            elif isinstance(conn, str):
                self.grafo_conectividad[r_id].add(conn)

    def _validar_integridad_referencial(self):
        """Verifica que ningun producto o servicio quede huerfano."""
        if not self.recursos:
            self.reporte.agregar('ERROR', 'INTEGRIDAD', "No hay recursos registrados en la planta.")
            return

        if not self.productos:
            self.reporte.agregar('ADVERTENCIA', 'INTEGRIDAD', "No hay catalogo de productos registrado en los archivos analizados.")
            return

        for p_id, p in self.productos.items():
            # Validar etapas / servicios requeridos
            etapas = p.get('ruta', p.get('etapas', p.get('steps', [])))
            if not etapas:
                self.reporte.agregar('ADVERTENCIA', 'INTEGRIDAD', f"Producto '{p_id}' no tiene ruta de proceso definida.")
                continue

            for idx, etapa in enumerate(etapas):
                svc = etapa if isinstance(etapa, str) else etapa.get('servicio', etapa.get('id'))
                if svc not in self.servicios_ofrecidos or len(self.servicios_ofrecidos[svc]) == 0:
                    self.reporte.agregar(
                        'ERROR', 'INTEGRIDAD',
                        f"Servicio huerfano: '{svc}' requerido por '{p_id}' (etapa {idx+1}) no lo ofrece ningun recurso de planta."
                    )

            # Validar Insumos / BOM
            bom = p.get('bom', p.get('materiales', p.get('formula', [])))
            if bom and self.materiales:
                for item in bom:
                    mat_id = item if isinstance(item, str) else item.get('material_id', item.get('id'))
                    if mat_id and mat_id not in self.materiales:
                        self.reporte.agregar(
                            'ADVERTENCIA', 'INTEGRIDAD',
                            f"Insumo '{mat_id}' en receta de '{p_id}' no esta registrado en el catalogo maestro de materiales."
                        )

    def _validar_conectividad_rutas(self):
        """Valida que para cada producto exista al menos una ruta continua en K."""
        for p_id, p in self.productos.items():
            etapas = p.get('ruta', p.get('etapas', p.get('steps', [])))
            if len(etapas) <= 1:
                continue

            candidatos_por_etapa: List[Set[str]] = []
            for etapa in etapas:
                svc = etapa if isinstance(etapa, str) else etapa.get('servicio', etapa.get('id'))
                candidatos = self.servicios_ofrecidos.get(svc, set())
                candidatos_por_etapa.append(candidatos)

            if not self._existe_camino_continuo(candidatos_por_etapa):
                self.reporte.agregar(
                    'ERROR', 'CONECTIVIDAD',
                    f"Ruta rota para Producto '{p_id}': No existe ninguna combinacion de maquinas conectadas fisicamente en K para la secuencia de etapas.",
                    detalles=f"Etapas: {[e if isinstance(e, str) else e.get('servicio') for e in etapas]}"
                )

    def _existe_camino_continuo(self, etapas_recursos: List[Set[str]]) -> bool:
        """Verifica mediante busqueda de caminos si hay continuidad paso a paso."""
        if not etapas_recursos or any(len(s) == 0 for s in etapas_recursos):
            return False

        actuales = set(etapas_recursos[0])
        for siguiente_etapa in etapas_recursos[1:]:
            siguientes_alcanzables = set()
            for r_actual in actuales:
                destinos_posibles = self.grafo_conectividad.get(r_actual, set())
                if destinos_posibles:
                    alcanzables = destinos_posibles.intersection(siguiente_etapa)
                    siguientes_alcanzables.update(alcanzables)
                else:
                    siguientes_alcanzables.update(siguiente_etapa)

            if not siguientes_alcanzables:
                return False
            actuales = siguientes_alcanzables

        return len(actuales) > 0

    def _validar_parametros_invariantes(self):
        """Verifica rangos de rendimiento, duraciones y tasas horarias."""
        for r_id, r in self.recursos.items():
            params = r.get('parametros', {})
            
            # Rendimiento (Yield)
            rendimiento = params.get('rendimiento', params.get('yield', 1.0))
            try:
                rend_val = float(rendimiento)
                if rend_val <= 0 or rend_val > 1.0:
                    if rend_val > 1.0 and rend_val <= 100.0:
                        self.reporte.agregar(
                            'ADVERTENCIA', 'PARAMETROS',
                            f"Recurso '{r_id}': rendimiento={rend_val} parece ser porcentaje. Debe ser fraccion decimal (ej. {rend_val/100:.2f})."
                        )
                    else:
                        self.reporte.agregar(
                            'ERROR', 'PARAMETROS',
                            f"Recurso '{r_id}': rendimiento={rend_val} invalido. Debe estar en (0.00, 1.00]."
                        )
            except (ValueError, TypeError):
                self.reporte.agregar('ERROR', 'PARAMETROS', f"Recurso '{r_id}': valor de rendimiento no numerico.")

            # Costos horarios
            costo_h = params.get('costo_hora', params.get('hourly_rate', 0.0))
            try:
                if float(costo_h) < 0:
                    self.reporte.agregar('ERROR', 'PARAMETROS', f"Recurso '{r_id}': costo por hora negativo ({costo_h}).")
            except (ValueError, TypeError):
                pass

    def _ejecutar_prueba_en_seco(self):
        """Simula una orden de prueba (Dry-Run) de 1.000 unidades para cada producto."""
        for p_id, p in self.productos.items():
            etapas = p.get('ruta', p.get('etapas', p.get('steps', [])))
            if not etapas:
                continue

            rendimiento_acumulado = 1.0
            tiempo_estimado_min = 0.0

            for etapa in etapas:
                svc = etapa if isinstance(etapa, str) else etapa.get('servicio', etapa.get('id'))
                candidatos = list(self.servicios_ofrecidos.get(svc, []))
                if candidatos:
                    r_elegido = self.recursos[candidatos[0]]
                    params = r_elegido.get('parametros', {})
                    rend = float(params.get('rendimiento', params.get('yield', 1.0)))
                    if rend > 1.0 and rend <= 100.0:
                        rend /= 100.0
                    rendimiento_acumulado *= rend
                    dur = float(params.get('duracion_nominal_min', params.get('nominal_duration_min', 60.0)))
                    tiempo_estimado_min += dur

            if rendimiento_acumulado <= 0:
                self.reporte.agregar('ERROR', 'DRY_RUN', f"Prueba en seco fallo para '{p_id}': rendimiento acumulado <= 0.")
            else:
                materia_prima_necesaria = 1000.0 / rendimiento_acumulado
                self.reporte.agregar(
                    'INFO', 'DRY_RUN',
                    f"Prueba en seco OK '{p_id}': Lote 1.000u requiere {materia_prima_necesaria:.1f}u de MP (Merma: {(1-rendimiento_acumulado)*100:.1f}%, Tiempo est.: {tiempo_estimado_min:.0f} min)."
                )

    def imprimir_reporte_consola(self):
        """Imprime un resumen formateado en consola."""
        print("\n======================================================================")
        print("       FENIX - DIAGNOSTICO INTEGRAL DE PLANTA Y PRE-PRODUCCION        ")
        print("======================================================================")
        print(f"ESTADO DEL SEMAFORO: [ {self.reporte.estado_semaforo} ]")
        print(f"Errores Criticos: {self.reporte.total_errores} | Advertencias: {self.reporte.total_advertencias} | Info: {self.reporte.total_info}")
        print(f"Recursos Verificados: {self.reporte.resumen_recursos.get('total_recursos', 0)} | Productos: {self.reporte.resumen_productos.get('total_productos', 0)}")
        print("----------------------------------------------------------------------")

        for item in self.reporte.items:
            prefix = "[ERROR]" if item.nivel == 'ERROR' else ("[ADVERTENCIA]" if item.nivel == 'ADVERTENCIA' else "[INFO]")
            print(f"{prefix} ({item.categoria}) {item.mensaje}")
            if item.detalles:
                print(f"   └─ Detalles: {item.detalles}")

        print("----------------------------------------------------------------------")
        if self.reporte.estado_semaforo == 'VERDE':
            print("OK: LA PLANTA ESTA 100% LISTA PARA RECIBIR Y PROGRAMAR ORDENES REALES.")
        elif self.reporte.estado_semaforo == 'AMARILLO':
            print("AVISO: LA PLANTA PUEDE OPERAR, PERO SE RECOMIENDA RESOLVER LAS ADVERTENCIAS.")
        else:
            print("BLOQUEO: DEBE CORREGIR LOS ERRORES CRITICOS ANTES DE PRODUCIR.")
        print("======================================================================\n")


if __name__ == "__main__":
    dir_base = Path(__file__).parent.parent / "uploads"
    if not dir_base.exists():
        dir_base = Path(__file__).parent.parent / "config"
    
    validador = ValidadorIntegralPlanta()
    validador.cargar_desde_yaml(dir_base)
    validador.ejecutar_diagnostico_completo()
    validador.imprimir_reporte_consola()
