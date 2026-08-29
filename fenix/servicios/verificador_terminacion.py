# servicios/verificador_terminacion.py
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from modelos.ProcesoOcurrente import InstanciaRed
from modelos.RedPetri import RedPetri

class VerificadorTerminacion:
    def __init__(self, session: Session):
        self.session = session

    def obtener_estados_terminales_de_red(self, red_nombre: str) -> Dict:
        """Retorna {'exito': [lugares], 'fallo': [], 'descarte': []} desde metadatos o detección"""
        red = self.session.query(RedPetri).filter_by(nombre=red_nombre).first()
        if not red:
            return {'exito': [], 'fallo': [], 'descarte': []}
        
        metadatos = red.metadatos or {}
        estados = metadatos.get('estados_finales', {})
        if estados:
            # Ya está categorizado (ej: {'exito': ['p8'], 'fallo': ['p_error']})
            return {
                'exito': estados.get('exito', []),
                'fallo': estados.get('fallo', []),
                'descarte': estados.get('descarte', [])
            }
        
        # Detección automática: lugares sin arcos de salida
        arcos = red.arcos or {}
        lugares_con_salida = set()
        for arco in arcos.values():
            if arco.get('source'):
                lugares_con_salida.add(arco['source'])
        
        # Asumir que todos los lugares del marcado que no tienen salida son de éxito
        # (esto es heurístico, mejor definir en metadatos)
        return {'exito': [], 'fallo': [], 'descarte': []}
    
    def instancia_terminada(self, instancia: InstanciaRed) -> Dict:
        marcado = instancia.marcado or {}
        terminales = self.obtener_estados_terminales_de_red(instancia.tipo)
        
        # Verificar éxito
        for lugar in terminales['exito']:
            if marcado.get(lugar, 0) > 0:
                return {"terminada": True, "tipo": "exito", "lugar": lugar}
        # Verificar fallo
        for lugar in terminales['fallo']:
            if marcado.get(lugar, 0) > 0:
                return {"terminada": True, "tipo": "fallo", "lugar": lugar}
        # Verificar descarte
        for lugar in terminales['descarte']:
            if marcado.get(lugar, 0) > 0:
                return {"terminada": True, "tipo": "descarte", "lugar": lugar}
        
        # Si no hay configuración, usar detección por lugares sin salida (solo éxito)
        if not terminales['exito'] and not terminales['fallo']:
            red = self.session.query(RedPetri).filter_by(nombre=instancia.tipo).first()
            if red and red.arcos:
                arcos = red.arcos
                lugares_con_salida = {a['source'] for a in arcos.values() if 'source' in a}
                for lugar in marcado:
                    if marcado[lugar] > 0 and lugar not in lugares_con_salida:
                        return {"terminada": True, "tipo": "detectada", "lugar": lugar}
        
        return {"terminada": False, "tipo": None, "lugar": None}
    
    def orden_terminada(self, orden_id: int) -> Dict:
        from modelos.DocumentosNegocio import OrdenProduccion
        orden = self.session.query(OrdenProduccion).get(orden_id)
        if not orden:
            return {"terminada": False, "error": "Orden no existe"}
        
        instancias = self.session.query(InstanciaRed).filter(
            InstanciaRed.orden_id == orden_id,
            InstanciaRed.activa == True
        ).all()
        
        if not instancias:
            return {"terminada": False, "razon": "No hay instancias activas"}
        
        # Priorizar fallo/descarte
        for inst in instancias:
            res = self.instancia_terminada(inst)
            if res["terminada"] and res["tipo"] in ("fallo", "descarte"):
                return {
                    "terminada": True,
                    "tipo": res["tipo"],
                    "razon": f"Instancia {inst.tipo} terminó en {res['tipo']}",
                    "lugar": res["lugar"],
                    "instancia_id": inst.id
                }
        
        # Verificar si todas están terminadas (éxito o detectadas)
        todas_terminadas = all(self.instancia_terminada(inst)["terminada"] for inst in instancias)
        if todas_terminadas:
            return {
                "terminada": True,
                "tipo": "completada",
                "razon": "Todas las instancias terminaron exitosamente"
            }
        
        return {"terminada": False, "razon": "Hay instancias en curso"}
    
    def instancia_terminada(self, instancia: InstanciaRed) -> Dict:
        import json
        marcado = instancia.marcado or {}
        if isinstance(marcado, str):
            marcado = json.loads(marcado)
        
        # 1. Intentar obtener metadatos explícitos
        terminales = self.obtener_estados_terminales_de_red(instancia.tipo)
        if terminales.get('exito') or terminales.get('fallo') or terminales.get('descarte'):
            for lugar in terminales.get('exito', []):
                if marcado.get(lugar, 0) > 0:
                    return {"terminada": True, "tipo": "exito", "lugar": lugar}
            for lugar in terminales.get('fallo', []):
                if marcado.get(lugar, 0) > 0:
                    return {"terminada": True, "tipo": "fallo", "lugar": lugar}
            for lugar in terminales.get('descarte', []):
                if marcado.get(lugar, 0) > 0:
                    return {"terminada": True, "tipo": "descarte", "lugar": lugar}
        
        # 2. Si no hay metadatos o ningún lugar coincidió, usar detección por sumideros
        #    (lugares que no son source de ningún arco)
        red = self.session.query(RedPetri).filter_by(nombre=instancia.tipo).first()
        if red and red.arcos:
            arcos = red.arcos
            lugares_con_salida = {a['source'] for a in arcos.values() if 'source' in a}
            for lugar, tokens in marcado.items():
                if tokens > 0 and lugar not in lugares_con_salida:
                    return {"terminada": True, "tipo": "detectada", "lugar": lugar}
        
        return {"terminada": False, "tipo": None, "lugar": None}
    
    def obtener_estados_terminales_de_red(self, red_nombre: str) -> Dict:
        red = self.session.query(RedPetri).filter_by(nombre=red_nombre).first()
        if not red or not red.metadatos:
            return {'exito': [], 'fallo': [], 'descarte': []}
        metadatos = red.metadatos
        estados = metadatos.get('estados_finales', {})
        return {
            'exito': estados.get('exito', []),
            'fallo': estados.get('fallo', []),
            'descarte': estados.get('descarte', [])
        }