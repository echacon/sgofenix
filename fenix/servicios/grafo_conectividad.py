# servicios/grafo_conectividad.py

from typing import List, Dict, Optional, Set
from sqlalchemy.orm import Session
from modelos.Recursos_backup import Recurso, ConexionFisica

class GrafoConectividad:
    """
    Grafo de conectividad física entre recursos.
    Permite validar si una transferencia es físicamente posible.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self._grafo = None
        self._inicializar_grafo()
    
    def _inicializar_grafo(self):
        """Construye el grafo desde la base de datos"""
        
        self._grafo = {}
        conexiones = self.session.query(ConexionFisica).filter_by(activa=True, disponible=True).all()
        
        for conn in conexiones:
            origen = conn.recurso_origen.nombre
            destino = conn.recurso_destino.nombre
            
            if origen not in self._grafo:
                self._grafo[origen] = []
            
            self._grafo[origen].append({
                "destino": destino,
                "tipo": conn.tipo,
                "flujo_maximo_lps": conn.flujo_maximo_lps,
                "perdida_material_pct": conn.perdida_material_pct,
                "requiere_bombeo": conn.requiere_bombeo,
                "requiere_operador": conn.requiere_operador
            })
    
    def puede_transferir(self, origen: str, destino: str) -> bool:
        """Verifica si existe conexión directa"""
        
        if origen not in self._grafo:
            return False
        
        for conn in self._grafo[origen]:
            if conn["destino"] == destino:
                return True
        
        return False
    
    def obtener_conexion(self, origen: str, destino: str) -> Optional[Dict]:
        """Obtiene los detalles de la conexión directa"""
        
        if origen not in self._grafo:
            return None
        
        for conn in self._grafo[origen]:
            if conn["destino"] == destino:
                return conn
        
        return None
    
    def encontrar_ruta(self, origen: str, destino: str, 
                       max_hop: int = 3) -> Optional[List[str]]:
        """
        Encuentra una ruta física entre recursos (BFS).
        Útil para transferencias indirectas (ej: con tanque pulmón).
        """
        
        if origen == destino:
            return [origen]
        
        if max_hop < 1:
            return None
        
        visitados = set()
        cola = [(origen, [origen])]
        
        while cola:
            actual, ruta = cola.pop(0)
            
            if actual in visitados:
                continue
            
            visitados.add(actual)
            
            if actual not in self._grafo:
                continue
            
            for conn in self._grafo[actual]:
                vecino = conn["destino"]
                
                if vecino == destino:
                    return ruta + [vecino]
                
                if len(ruta) < max_hop:
                    cola.append((vecino, ruta + [vecino]))
        
        return None
    
    def validar_holon_ruta(self, holon_ruta_id: int) -> List[Dict]:
        """
        Valida que todas las transferencias en una HolonRuta
        sean físicamente posibles.
        """
        
        from modelos.Producto import HolonRuta, ConexionReal
        
        holon_ruta = self.session.query(HolonRuta).get(holon_ruta_id)
        if not holon_ruta:
            return [{"error": "HolonRuta no existe"}]
        
        invalidaciones = []
        
        for conexion in holon_ruta.conexiones:
            etapa_origen = conexion.etapa_origen
            etapa_destino = conexion.etapa_destino
            
            # Obtener recursos asignados a cada etapa
            recurso_origen = None
            recurso_destino = None
            
            for asignacion in holon_ruta.asignaciones:
                if asignacion.etapa_id == etapa_origen.id:
                    recurso_origen = asignacion.recurso
                if asignacion.etapa_id == etapa_destino.id:
                    recurso_destino = asignacion.recurso
            
            if recurso_origen and recurso_destino:
                if not self.puede_transferir(recurso_origen.nombre, recurso_destino.nombre):
                    invalidaciones.append({
                        "etapa_origen": etapa_origen.nombre,
                        "etapa_destino": etapa_destino.nombre,
                        "recurso_origen": recurso_origen.nombre,
                        "recurso_destino": recurso_destino.nombre,
                        "razon": "No existe conexión física directa"
                    })
        
        return invalidaciones