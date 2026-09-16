# procesar_secuencia.py
import sys
import json
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from servicios.orquestador import Orquestador
from utils.motor_abtppn import MotorABTPPN
from modelos.RedPetri import RedPetri
from modelos.ProcesoOcurrente import InstanciaRed


class ProcesadorSecuencia:
    def __init__(self, archivo_eventos: str):
        self.archivo_eventos = Path(archivo_eventos)
        self.eventos = None
        self.ultimo_procesado = 0
        
        # Conectar a BD
        self.engine = create_engine("sqlite:///fenix.db")
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        self.orden_id = None
        if self.eventos and len(self.eventos) > 0:
            self.orden_id = self.eventos[0].get('orden_id')
            if self.orden_id:
                orden = self.session.query(OrdenProduccion).get(self.orden_id)
                if orden and orden.estado in ('completada', 'fallida', 'cancelada'):
                    print(f"⚠️ La orden {self.orden_id} ya está {orden.estado}. No se procesarán eventos.")
                    self.orden_completada = True
                else:
                    self.orden_completada = False
        
        # Crear orquestador
        self.motor = MotorABTPPN()
        self.orquestador = Orquestador(self.motor, self.session)
        self.orquestador.cargar_configuracion_desde_bd()
        
        # Cargar redes
        redes = self.session.query(RedPetri).filter_by(activo=True).all()
        for red in redes:
            red_mem = self.orquestador.cargar_red_desde_bd(red.nombre)
            if red_mem:
                self.motor.redes_cargadas[red.nombre] = red_mem
        
        # Cargar eventos
        self.cargar_eventos()
        self.cargar_instancias_existentes()
    
    def cargar_instancias_existentes(self):
        """Carga todas las instancias activas desde BD al motor (memoria)"""
        from modelos.ProcesoOcurrente import InstanciaRed
        from utils.motor_abtppn import TokenColoreado

        instancias_bd = self.session.query(InstanciaRed).filter_by(activa=True).all()
        if not instancias_bd:
            print("   ℹ️ No hay instancias activas en BD")
            return

        print(f"   🔄 Cargando {len(instancias_bd)} instancia(s) activa(s) a memoria...")
        
        for inst_bd in instancias_bd:
            # 1. Asegurar que la red esté cargada en el motor
            if inst_bd.tipo not in self.motor.redes_cargadas:
                red_mem = self.orquestador.cargar_red_desde_bd(inst_bd.tipo)
                if red_mem:
                    self.motor.redes_cargadas[inst_bd.tipo] = red_mem
                else:
                    print(f"      ❌ No se pudo cargar red {inst_bd.tipo}")
                    continue
            
            # 2. Reconstruir token
            token = TokenColoreado(
                orden_id=inst_bd.token_o,
                material=inst_bd.token_m,
                coste=inst_bd.token_c,
                timestamp=inst_bd.token_t or datetime.now()
            )
            
            # 3. Crear instancia en memoria
            mem_id = self.motor.crear_instancia(
                red_nombre=inst_bd.tipo,
                orden_id=inst_bd.orden_id,
                token_inicial=token,
                marcado_inicial=inst_bd.marcado,
                pnml_path=None
            )
            if mem_id:
                self.motor.actualizar_instancia_bd_id(mem_id, inst_bd.id)
                # Si la instancia ya estaba completada en BD, reflejarlo en memoria
                if inst_bd.completada:
                    self.motor.instancias[mem_id].completada = True
                    self.motor.instancias[mem_id].bloqueada = True
                print(f"      ✅ Instancia cargada: {inst_bd.tipo} (id_mem={mem_id})")
    
    def cargar_eventos(self):
        """Carga eventos desde archivo JSON"""
        if not self.archivo_eventos.exists():
            print(f"❌ Archivo no encontrado: {self.archivo_eventos}")
            return False
        
        with open(self.archivo_eventos, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.eventos = data.get('eventos', [])
        self.ultimo_procesado = data.get('ultimo_evento_procesado', 0)
        self.nombre = data.get('nombre', 'Sin nombre')
        
        print(f"✅ Cargados {len(self.eventos)} eventos")
        print(f"   Último procesado: {self.ultimo_procesado}")
        return True
    
    def guardar_eventos(self):
        """Guarda eventos actualizando el campo procesado"""
        data = {
            "nombre": self.nombre,
            "descripcion": "Producción normal sin fallos",
            "ultimo_evento_procesado": self.ultimo_procesado,
            "eventos": self.eventos
        }
        
        with open(self.archivo_eventos, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"   💾 Progreso guardado (último: {self.ultimo_procesado})")
    
    def obtener_eventos_pendientes(self):
        """Retorna eventos no procesados en orden"""
        pendientes = [e for e in self.eventos if not e.get('procesado', False)]
        return sorted(pendientes, key=lambda x: x.get('id', 0))
    
    def procesar_evento(self, evento):
        """Procesa un evento individual"""
        evento_id = evento.get('id')
        print(f"\n📱 Evento {evento_id}: {evento.get('red')}.{evento.get('transicion')}")
        print(f"   Recurso: {evento.get('recurso')}")
        
        resultado = self.orquestador.procesar_evento_planta(
            orden_id=evento.get('orden_id'),
            red_nombre=evento.get('red'),
            evento_nombre=evento.get('transicion'),
            recurso_id=evento.get('recurso'),
            timestamp=datetime.fromisoformat(evento.get('timestamp'))
        )
        
        # Marcar como procesado
        evento['procesado'] = True
        evento['fecha_procesado'] = datetime.now().isoformat()
        evento['resultado'] = "exito" if resultado else "fallo"
        
        if resultado:
            print(f"   ✅ Procesado")
            self.ultimo_procesado = evento_id
            # Procesar handshakes
            self.orquestador.procesar_mensajes_pendientes(evento.get('orden_id'))
        else:
            print(f"   ❌ Falló")
        
        return resultado
    
    def ejecutar(self, hasta_completar=True):
        """Ejecuta todos los eventos pendientes"""
        print(f"\n{'='*60}")
        print(f"📋 PROCESANDO: {self.nombre}")
        print(f"{'='*60}")

        if hasattr(self, 'orden_completada') and self.orden_completada:
            print("Orden ya finalizada. No se procesan eventos.")
            return
        
        while True:
            pendientes = self.obtener_eventos_pendientes()
            
            if not pendientes:
                print("\n✅ Todos los eventos han sido procesados")
                break
            
            print(f"\n📨 {len(pendientes)} evento(s) pendiente(s)")
            
            for evento in pendientes:
                self.procesar_evento(evento)
                self.guardar_eventos()
                
                if not hasta_completar:
                    # Preguntar si continuar
                    resp = input("\n¿Continuar con siguiente evento? (s/N): ")
                    if resp.lower() != 's':
                        print("⏸️ Pausado por el usuario")
                        return
        if self.orden_id:
            terminada = self.orquestador._verificar_y_finalizar_orden(self.orden_id)
            if terminada:
                print("🎉 Orden marcada como completada en BD.")
        self.mostrar_estado_final()

        # Mostrar estado final
        self.mostrar_estado_final()
        self.session.close()
    
    def mostrar_estado_final(self):
        """Muestra el estado de las instancias"""
        print(f"\n{'='*60}")
        print("📊 ESTADO FINAL")
        print(f"{'='*60}")
        
        instancias = self.session.query(InstanciaRed).filter_by(orden_id=1).all()
        for inst in instancias:
            print(f"\n📊 {inst.tipo}:")
            print(f"   Marcado: {inst.marcado}")
            print(f"   Token: {inst.token_m:.2f} kg, ${inst.token_c:.2f}")
    
    def reset(self):
        """Resetea el estado de procesamiento de todos los eventos"""
        print("🔄 Reseteando estado de eventos...")
        for evento in self.eventos:
            evento['procesado'] = False
            evento['fecha_procesado'] = None
            evento['resultado'] = None
        self.ultimo_procesado = 0
        self.guardar_eventos()
        print("✅ Estado reseteado")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--eventos", type=str, required=True, help="Archivo JSON de eventos")
    parser.add_argument("--reset", action="store_true", help="Resetear estado de eventos")
    parser.add_argument("--step", action="store_true", help="Procesar paso a paso")
    
    args = parser.parse_args()
    
    procesador = ProcesadorSecuencia(args.eventos)
    
    if args.reset:
        procesador.reset()
    else:
        procesador.ejecutar(hasta_completar=not args.step)