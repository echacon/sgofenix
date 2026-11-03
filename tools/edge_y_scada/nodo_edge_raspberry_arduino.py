# tools/edge_y_scada/nodo_edge_raspberry_arduino.py
r"""
Pasarela de Borde de Bajo Coste para Modo C (Arduino/ESP32 + Sensores + Raspberry Pi).

Arquitectura de Hardware Abierto para PyMEs (Modo C — `C_EDGE`):
----------------------------------------------------------------
Cuando una PyME cuenta con maquinaria legada puramente electromecánica (reactores, mezcladores,
molinos o envasadoras sin PLC moderno ni SCADA), Fénix propone instrumentar el **Holón Recurso**
de forma no intrusiva con una arquitectura de borde de muy bajo coste (< 80 USD por estación):

1. Nivel de Captura Física (Microcontrolador Arduino Nano / ESP32):
   - Pinza amperimétrica no invasiva **SCT-013** o módulo medidor **PZEM-004T** abrazando la
     acometida eléctrica del equipo: mide corriente RMS $I_{\text{rms}}$ (A) y potencia activa $P$ (kW).
   - Sonda digital impermeable **DS18B20** (bus 1-Wire): mide temperatura de proceso $T$ (°C).
   - Pulsador industrial luminoso o final de carrera óptico en pin digital con interrupción:
     señaliza inicio/fin de lote cuando el flujo no puede inferirse solo por umbral de corriente.
   - Emite tramas JSON por puerto serie USB (`/dev/ttyUSB0` a 115200 baudios) o WiFi/MQTT cada $\Delta t$ segundos.

2. Nivel de Agregación Holónica (Gateway Raspberry Pi — este módulo):
   - Recibe las tramas periódicas del Arduino/ESP32:
     `{"nodo_id": "ARD-MEZ-01", "corriente_a": 19.4, "voltaje_v": 220.0, "potencia_kw": 3.85, "temp_c": 65.2, "boton_fin": 0, "dt_seg": 1.0}`
   - Integra numéricamente la energía consumida por el Holón durante la etapa activa:
     $$E_{\text{lote}} = \sum P(t) \cdot \frac{\Delta t}{3600} \quad [\text{kWh}]$$
   - Detecta el fin de la operación (por pulsador físico `boton_fin == 1` o por caída de corriente
     bajo el umbral de reposo $I_{\text{idle}}$ tras haber superado el tiempo mínimo de ciclo) y
     envía el evento `200` con las mediciones acumuladas a `/api/ingesta/evento_planta` bajo
     modalidad `C_EDGE`.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
import json
import urllib.request
import urllib.error


@dataclass
class EstadoAcumuladoHolonEdge:
    """Estado de integración energética y térmica de una estación de trabajo durante un lote."""
    nodo_id: str
    recurso_fenix: str
    evento_fin_fenix: str
    red_fenix: str = "red_ejecucion_orden"
    kwh_acumulados: float = 0.0
    tiempo_activo_seg: float = 0.0
    temp_max_c: Optional[float] = None
    temp_ultima_c: Optional[float] = None
    muestras_procesadas: int = 0
    en_operacion: bool = False


class NodoEdgeRaspberryArduino:
    """
    Gateway de borde (Raspberry Pi) que procesa tramas JSON provenientes de nodos
    Arduino/ESP32 y publica eventos enriquecidos hacia Fénix en Modo C (`C_EDGE`).
    """

    def __init__(
        self,
        url_base_fenix: str = "http://localhost:5000",
        umbral_corriente_operacion_a: float = 2.5,
        cliente_local_post: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None
    ):
        self.url_endpoint = f"{url_base_fenix.rstrip('/')}/api/ingesta/evento_planta"
        self.umbral_corriente_a = umbral_corriente_operacion_a
        self.cliente_local_post = cliente_local_post
        self.estaciones: Dict[str, EstadoAcumuladoHolonEdge] = {}

    def registrar_estacion_arduino(
        self,
        nodo_id: str,
        recurso_fenix: str,
        evento_fin_fenix: str,
        red_fenix: str = "red_ejecucion_orden"
    ) -> None:
        """Vincula un identificador de microcontrolador (`nodo_id`) con un Holón Recurso de Fénix."""
        self.estaciones[nodo_id] = EstadoAcumuladoHolonEdge(
            nodo_id=nodo_id,
            recurso_fenix=recurso_fenix,
            evento_fin_fenix=evento_fin_fenix,
            red_fenix=red_fenix
        )

    def reiniciar_acumulador(self, nodo_id: str) -> None:
        """Limpia los contadores energéticos de la estación al iniciar un nuevo lote."""
        est = self.estaciones[nodo_id]
        est.kwh_acumulados = 0.0
        est.tiempo_activo_seg = 0.0
        est.temp_max_c = None
        est.temp_ultima_c = None
        est.muestras_procesadas = 0
        est.en_operacion = False

    def procesar_trama_arduino(
        self,
        orden_id: int,
        trama_json: str | Dict[str, Any],
        forzar: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Procesa una trama de telemetría recibida por Puerto Serie / MQTT desde el Arduino/ESP32.
        Si la trama indica fin de operación (`boton_fin == 1` o flanco descendente de carga),
        dispara automáticamente el evento hacia Fénix y retorna la respuesta del servidor.
        """
        datos = json.loads(trama_json) if isinstance(trama_json, str) else dict(trama_json)
        nodo_id = datos.get("nodo_id")
        if not nodo_id or nodo_id not in self.estaciones:
            raise KeyError(f"Nodo Arduino/ESP32 '{nodo_id}' no registrado en el Gateway Raspberry Pi.")

        est = self.estaciones[nodo_id]
        dt_seg = float(datos.get("dt_seg", 1.0))
        corriente_a = float(datos.get("corriente_a", 0.0))
        voltaje_v = float(datos.get("voltaje_v", 220.0))
        factor_potencia = float(datos.get("cos_phi", 0.88))

        # Si el Arduino envía potencia activa directa (ej. PZEM-004T), usarla; si solo envía corriente (SCT-013), estimar P
        if "potencia_kw" in datos and datos["potencia_kw"] is not None:
            potencia_kw = float(datos["potencia_kw"])
        else:
            potencia_kw = (voltaje_v * corriente_a * factor_potencia) / 1000.0

        # Integrar energía si el motor/equipo está bajo carga
        if corriente_a >= self.umbral_corriente_a or potencia_kw > 0.2:
            est.en_operacion = True
            est.kwh_acumulados += potencia_kw * (dt_seg / 3600.0)
            est.tiempo_activo_seg += dt_seg

        # Actualizar lecturas térmicas (DS18B20 / PT100)
        if "temp_c" in datos and datos["temp_c"] is not None:
            temp_actual = float(datos["temp_c"])
            est.temp_ultima_c = temp_actual
            if est.temp_max_c is None or temp_actual > est.temp_max_c:
                est.temp_max_c = temp_actual

        est.muestras_procesadas += 1

        # Verificar condición de disparo de fin de etapa:
        # 1) Botón físico presionado en la estación Arduino (`boton_fin == 1`), o
        # 2) Parada del motor (`corriente_a < umbral`) tras haber estado operando (`fin_ciclo_auto == True`)
        boton_fin = int(datos.get("boton_fin", 0)) == 1
        caida_carga_fin = bool(datos.get("fin_por_caida_corriente", False)) and est.en_operacion and corriente_a < self.umbral_corriente_a

        if boton_fin or caida_carga_fin:
            return self.emitir_evento_fin_etapa(
                orden_id=orden_id,
                nodo_id=nodo_id,
                mediciones_adicionales=datos.get("mediciones_extra"),
                forzar=forzar
            )

        return None

    def emitir_evento_fin_etapa(
        self,
        orden_id: int,
        nodo_id: str,
        mediciones_adicionales: Optional[Dict[str, Any]] = None,
        forzar: bool = False
    ) -> Dict[str, Any]:
        """
        Empaqueta la energía integrada (kWh) y la temperatura del lote y las envía
        a la Pasarela Unificada de Fénix bajo modalidad `C_EDGE`.
        """
        est = self.estaciones[nodo_id]
        mediciones: Dict[str, Any] = {
            "nodo_edge_id": est.nodo_id,
            "arquitectura_borde": "Arduino_SCT013_DS18B20 + RaspberryPi_Gateway",
            "kwh_consumidos": round(est.kwh_acumulados, 4),
            "tiempo_efectivo_motor_seg": round(est.tiempo_activo_seg, 1),
            "muestras_integradas": est.muestras_procesadas
        }

        if est.temp_ultima_c is not None:
            mediciones["temperatura_c"] = round(est.temp_ultima_c, 2)
        if est.temp_max_c is not None:
            mediciones["temperatura_max_c"] = round(est.temp_max_c, 2)

        if mediciones_adicionales:
            mediciones.update(mediciones_adicionales)

        payload = {
            "orden_id": int(orden_id),
            "recurso": est.recurso_fenix,
            "red": est.red_fenix,
            "evento": est.evento_fin_fenix,
            "modo_captura": "C_EDGE",
            "mediciones": mediciones,
            "forzar": bool(forzar)
        }

        # Reiniciar acumulador para el próximo lote tras construir el payload
        self.reiniciar_acumulador(nodo_id)

        if self.cliente_local_post is not None:
            return self.cliente_local_post("/api/ingesta/evento_planta", payload)

        req = urllib.request.Request(
            self.url_endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
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
