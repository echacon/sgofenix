# tools/edge_y_scada/conector_scada_cliente.py
"""
Conector de Referencia para Captura de Datos en Modo B (Tecnología Media — SCADA / PLC Existente).

Filosofía Fénix ("Primero el saber hacer, después la tecnología"):
------------------------------------------------------------------
En muchas PyMEs manufactureras ya existe un sistema SCADA parcial, un PLC con servidor
OPC-UA / Modbus TCP o un historiador local en ciertas estaciones críticas (por ejemplo,
reactores térmicos, homogeneizadores o líneas de envasado), mientras que otras estaciones
siguen operando manualmente (Modo A) o con nodos de borde de bajo coste (Modo C).

Este módulo actúa como adaptador ligero entre los tags del SCADA/PLC existente y la
Pasarela Unificada de Ingesta de Fénix (`/api/ingesta/evento_planta`), traduciendo:
1. Flancos de estado de etapa en eventos de la serie `200` de la Red de Petri AB-TPPN.
2. Tags analógicos acumulados (energía activa `kWh`, temperatura de proceso `°C`, caudal/masa)
   al diccionario `mediciones`, alimentando automáticamente el lazo de aprendizaje
   EWMA/EDR (Ec. 12 - Ec. 15) y la verificación de invariantes físicos.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import json
import urllib.request
import urllib.error


@dataclass
class MapeoTagSCADA:
    """
    Define la correspondencia entre un tag de disparo de un SCADA/PLC y una transición
    de planta (serie 200) de un Holón Recurso en Fénix.
    """
    tag_disparo: str
    recurso_fenix: str
    evento_fenix: str
    red_fenix: str = "red_ejecucion_orden"
    tag_energia_kwh: Optional[str] = None
    tag_temperatura_c: Optional[str] = None
    tag_merma_kg: Optional[str] = None
    tags_extra: Dict[str, str] = field(default_factory=dict)


class ConectorSCADAFenix:
    """
    Adaptador cliente para integración Modo B (`B_SCADA`).
    Puede enviar los eventos mediante HTTP POST al servidor Fénix o a través de un
    cliente inyectado (como `FlaskClient` durante pruebas integrales sin red).
    """

    def __init__(
        self,
        url_base_fenix: str = "http://10.10.20.1:5001",
        cliente_local_post: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None
    ):
        """
        Por defecto apunta al puerto OT aislado del servidor Fénix (:5001 en la subred segura
        de planta 10.10.20.0/24), separado del puerto de la red empresarial IT (:5000).
        """
        self.url_endpoint = f"{url_base_fenix.rstrip('/')}/api/ingesta/evento_planta"
        self.cliente_local_post = cliente_local_post
        self.mapeos: Dict[str, MapeoTagSCADA] = {}

    def registrar_mapeo(self, mapeo: MapeoTagSCADA) -> None:
        """Registra la regla de traducción para un tag de flanco del SCADA."""
        self.mapeos[mapeo.tag_disparo] = mapeo

    def construir_payload(
        self,
        orden_id: int,
        tag_disparo: str,
        lecturas_tags: Dict[str, Any],
        forzar: bool = False
    ) -> Dict[str, Any]:
        """
        Construye el payload canónico para `/api/ingesta/evento_planta` bajo modalidad `B_SCADA`.
        """
        if tag_disparo not in self.mapeos:
            raise KeyError(f"El tag SCADA '{tag_disparo}' no tiene un mapeo registrado en Fénix.")

        mapeo = self.mapeos[tag_disparo]
        mediciones: Dict[str, Any] = {
            "origen_scada_tag": tag_disparo,
            "timestamp_scada": datetime.now().isoformat()
        }

        if mapeo.tag_energia_kwh and mapeo.tag_energia_kwh in lecturas_tags:
            mediciones["kwh_consumidos"] = float(lecturas_tags[mapeo.tag_energia_kwh])

        if mapeo.tag_temperatura_c and mapeo.tag_temperatura_c in lecturas_tags:
            mediciones["temperatura_c"] = float(lecturas_tags[mapeo.tag_temperatura_c])

        if mapeo.tag_merma_kg and mapeo.tag_merma_kg in lecturas_tags:
            mediciones["merma_kg"] = float(lecturas_tags[mapeo.tag_merma_kg])

        for nombre_param, tag_scada in mapeo.tags_extra.items():
            if tag_scada in lecturas_tags:
                mediciones[nombre_param] = lecturas_tags[tag_scada]

        return {
            "orden_id": int(orden_id),
            "recurso": mapeo.recurso_fenix,
            "red": mapeo.red_fenix,
            "evento": mapeo.evento_fenix,
            "modo_captura": "B_SCADA",
            "mediciones": mediciones,
            "forzar": bool(forzar)
        }

    def procesar_flanco_tag(
        self,
        orden_id: int,
        tag_disparo: str,
        lecturas_tags: Dict[str, Any],
        forzar: bool = False
    ) -> Dict[str, Any]:
        """
        Dispara el evento hacia Fénix cuando un tag booleano de fin de operación pasa a TRUE en el SCADA.
        """
        payload = self.construir_payload(orden_id, tag_disparo, lecturas_tags, forzar=forzar)

        if self.cliente_local_post is not None:
            return self.cliente_local_post("/api/ingesta/evento_planta", payload)

        req = urllib.request.Request(
            self.url_endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Fenix-Zone": "OT"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            cuerpo = err.read().decode("utf-8", errors="replace")
            try:
                return json.loads(cuerpo)
            except Exception:
                return {"success": False, "status_code": err.code, "error": cuerpo}
