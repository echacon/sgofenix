# servicios/cola_eventos.py

from datetime import datetime
from typing import Optional
from modelos.declarative_base import SessionLocal
from modelos.Colaevento import ColaEvento


class ServicioColaEventos:
    """Servicio para gestionar cola de eventos asíncronos"""
    
    def __init__(self, session=None):
        """
        Inicializa el servicio.
        Si no se provee sesión, crea una propia.
        """
        self.session = session
        self._own_session = session is None
        if self._own_session:
            self.session = SessionLocal()
    
    def _get_session(self):
        """Retorna la sesión actual, creando una nueva si es necesario"""
        if self._own_session and self.session is None:
            self.session = SessionLocal()
        return self.session
    
    def encolar(self, orden_id: int, transicion_nombre: str,
                recurso_nombre: str = None, red_nombre: str = None,
                datos: dict = None) -> ColaEvento:
        """Agrega un evento a la cola.
        
        Args:
            orden_id: ID de la orden
            transicion_nombre: Nombre del evento (ej: "Cargar solidos")
            recurso_nombre: Nombre del recurso físico (opcional)
            red_nombre: Nombre de la red (opcional, se puede inferir)
            datos: Datos adicionales (timestamp, operador, etc.)
        """
        session = self._get_session()
        
        evento = ColaEvento(
            orden_id=orden_id,
            recurso_nombre=recurso_nombre,
            red_nombre=red_nombre,
            transicion_nombre=transicion_nombre,
            datos=datos or {},
            estado="pendiente"
        )
        session.add(evento)
        session.commit()
        
        # Si la sesión es propia, la cerramos
        if self._own_session:
            session.close()
            self.session = None
        
        return evento
    
    def obtener_siguiente(self) -> Optional[ColaEvento]:
        """Obtiene el siguiente evento pendiente (FIFO)"""
        session = self._get_session()
        
        evento = session.query(ColaEvento).filter_by(
            estado="pendiente"
        ).order_by(ColaEvento.fecha_creacion).first()
        
        if evento:
            evento.estado = "procesando"
            session.commit()
        
        if self._own_session:
            session.close()
            self.session = None
        
        return evento
    
    def marcar_completado(self, evento_id: int):
        """Marca un evento como completado"""
        session = self._get_session()
        
        evento = session.query(ColaEvento).get(evento_id)
        if evento:
            evento.estado = "completado"
            evento.fecha_procesamiento = datetime.now()
            session.commit()
        
        if self._own_session:
            session.close()
            self.session = None
    
    def marcar_error(self, evento_id: int, error: str):
        """Marca un evento con error"""
        session = self._get_session()
        
        evento = session.query(ColaEvento).get(evento_id)
        if evento:
            evento.estado = "error"
            evento.intentos += 1
            evento.error = error
            evento.fecha_procesamiento = datetime.now()
            session.commit()
        
        if self._own_session:
            session.close()
            self.session = None
    
    def close(self):
        """Cierra la sesión si es propia"""
        if self._own_session and self.session:
            self.session.close()
            self.session = None