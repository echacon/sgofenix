# utils/disponibilidad_recursos.py (versión final)

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from modelos.Recursos import RecursoEquipo

class ServicioDisponibilidad:
    def __init__(self, session: Session):
        self.session = session
    
    def unidades_para_operacion(self, tipo_operacion_nombre: str):
        """
        Retorna las unidades funcionales que pueden realizar una operación
        """
        result = self.session.execute(text("""
            SELECT u.id, u.nombre, uc.eficiencia, uc.costo_por_hora
            FROM unidad_funcional u
            JOIN unidad_capacidad uc ON u.id = uc.unidad_id
            JOIN tipo_de_operacion t ON uc.tipo_operacion_id = t.id
            WHERE t.nombre = :op_nombre
        """), {"op_nombre": tipo_operacion_nombre})
        
        unidades = []
        for row in result:
            unidades.append({
                "id": row[0],
                "nombre": row[1],
                "eficiencia": row[2],
                "costo_por_hora": row[3]
            })
        
        return unidades
    
    def recursos_en_unidad(self, unidad_id: int):
        """
        Retorna los equipos disponibles en una unidad funcional
        """
        equipos = self.session.query(RecursoEquipo).filter(
            RecursoEquipo.unidad_id == unidad_id,
            RecursoEquipo.disponible == True
        ).all()
        
        return [{
            "id": e.id, 
            "nombre": e.nombre, 
            "capacidad_maxima": e.capacidad_maxima,
            "velocidad_procesamiento": e.velocidad_procesamiento
        } for e in equipos]
    
    def mejor_unidad_para_operacion(self, tipo_operacion_nombre: str, cantidad_requerida: float):
        """
        Selecciona la mejor unidad funcional según capacidad y eficiencia
        """
        unidades = self.unidades_para_operacion(tipo_operacion_nombre)
        
        resultados = []
        for u in unidades:
            recursos = self.recursos_en_unidad(u["id"])
            if recursos:
                # Verificar si algún recurso tiene capacidad suficiente
                recursos_validos = [r for r in recursos if r["capacidad_maxima"] >= cantidad_requerida]
                if recursos_validos:
                    u["mejor_recurso"] = max(recursos_validos, key=lambda x: x["capacidad_maxima"])
                    u["recursos_disponibles"] = recursos_validos
                    resultados.append(u)
        
        if not resultados:
            return None
        
        # Seleccionar la unidad con mejor eficiencia * capacidad
        return max(resultados, key=lambda x: x["eficiencia"] * x["mejor_recurso"]["capacidad_maxima"])