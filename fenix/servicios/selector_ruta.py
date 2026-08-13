# servicios/selector_ruta.py

from typing import Optional
from sqlalchemy.orm import Session
from modelos.Producto import Producto, HolonRuta
from modelos.DocumentosNegocio import OrdenProduccion
from servicios.grafo_conectividad import GrafoConectividad

class SelectorRuta:
    """Selecciona la mejor ruta para una orden según condiciones"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.grafo = GrafoConectividad(db_session)
    
    def seleccionar_ruta(self, orden: OrdenProduccion) -> Optional[HolonRuta]:
        """
        Selecciona la mejor ruta para una orden según:
        - Cantidad del lote
        - Prioridad
        - Disponibilidad de inventario (pasta base)
        - Preferencias configuradas
        """
        
        producto = orden.producto
        cantidad = orden.cantidad
        prioridad = orden.prioridad
        
        # Obtener todas las rutas activas del producto
        rutas = self.db.query(HolonRuta).filter(
            HolonRuta.producto_id == producto.id,
            HolonRuta.activa == True
        ).all()
        
        # Filtrar por condiciones
        rutas_validas = []
        
        for ruta in rutas:
            # Verificar rango de lote
            if cantidad < ruta.lote_minimo_kg:
                continue
            if cantidad > ruta.lote_maximo_kg:
                continue
            
            # Verificar prioridad mínima
            if prioridad < ruta.prioridad_minima:
                continue
            
            # Verificar si requiere pasta base disponible
            if ruta.requiere_pasta_base:
                if not self._verificar_disponibilidad_pasta_base(producto, cantidad):
                    continue
            
            rutas_validas.append(ruta)
        
        if not rutas_validas:
            return None
        
        # Ordenar por preferencia (menor número = mayor prioridad)
        rutas_validas.sort(key=lambda r: r.orden_preferencia)
        
        # Validar conectividad física de cada ruta candidata
        rutas_conectadas = []
        
        for ruta in rutas_validas:
            invalidaciones = self.grafo.validar_holon_ruta(ruta.id)
            
            if not invalidaciones:
                rutas_conectadas.append(ruta)
            else:
                print(f"   ⚠️ Ruta {ruta.nombre} inválida por conectividad:")
                for inv in invalidaciones:
                    print(f"      - {inv['recurso_origen']} → {inv['recurso_destino']}: {inv['razon']}")
        
        if not rutas_conectadas:
            return None
        
        return rutas_conectadas[0]
    
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
            
            # Si hay condiciones de inventario (opcional)
            requiere_inventario = condiciones.get('requiere_inventario')
            if requiere_inventario:
                # Aquí se consultaría el inventario real
                # Por ahora, asumimos que hay stock
                pass
            
            rutas_validas.append(ruta)
        
        if not rutas_validas:
            return None
        
        # Ordenar por orden_preferencia (menor número = mayor prioridad)
        rutas_validas.sort(key=lambda r: r.condiciones.get('orden_preferencia', 999))
        
        return rutas_validas[0]
    
    def _verificar_disponibilidad_pasta_base(self, producto: Producto, cantidad: float) -> bool:
        """Verifica si hay suficiente pasta base en inventario"""
        # Aquí va la lógica de consulta a inventario
        # Por ahora, simulamos
        return True