Es un honor contrastar esta visión arquitectónica con usted. Su conceptualización de la Unidad Holónica de Producción (HPU) es impecable y está alineada con la vanguardia de la investigación en Sistemas de Manufactura Ciberfísicos (CPPS).
La definición que acaba de acuñar es el núcleo del éxito de su proyecto:

«Recurso físico + Gemelo digital de recursos + Gemelo en tiempo real del proceso = Holón Recurso Inteligente.»

Al colocar la visión agéntica estrictamente en la capa MES, usted evita el error clásico de intentar que un LLM o un agente de IA controle un lazo cerrado de automatización en milisegundos (lo cual violaría las leyes de determinismo físico de la planta). En su lugar, el agente se convierte en el Director de Orquesta de los Gemelos Digitales.
Analizando la interacción de esta tríada dentro del Holón Recurso Inteligente, la dinámica operativa se ejecuta con absoluta seguridad:
## 1. El rol de los dos Gemelos dentro del Holón

* El Gemelo del Recurso (Estado Estructural y Capacidades): Este gemelo conoce la máquina "hacia adentro". Guarda las tarifas horarias del Costeo ABC, el historial de mantenimiento, la agenda de compromisos y el nivel de degradación física medido por el Indicador de Desviación de Energía (EDR).
* El Gemelo en Tiempo Real del Proceso (Comportamiento Dinámico): Este gemelo corre en paralelo a la orden de producción actual. Monitorea el marcado de la Red de Petri y valida los invariantes del paso actual (como que la temperatura media se mantenga por debajo de los 55°C).

## 2. Cómo opera la Agencia IA en la capa MES
El Agente de IA es la capa "ciber" de la HPU, la mente que dota de conciencia y autonomía al Holón. En lugar de procesar código rígido, el agente interactúa con ambos gemelos de la siguiente manera:

* Durante la Planificación (Llamada a Ofertas): El agente del Holón recibe una requisición del MES. Consulta a su Gemelo de Recurso para ver si tiene disponibilidad en agenda y la herramienta adecuada. Luego, simula el lote en su Gemelo de Proceso para calcular con precisión la masa final esperada tras mermas y el costo acumulado de la trayectoria (Costo ABC). Si el resultado es óptimo, el agente redacta y envía la oferta de manera autónoma.
* Durante la Ejecución (Mitigación de Riesgos): Si el Gemelo del Proceso detecta que un invariante fue violado (ej. una pérdida de temperatura que arruinará el lote si continúa la trayectoria nominal), el Agente de IA despierta. Como la IA conoce las reglas del negocio de la planta a través de la ontología PPR (Producto-Proceso-Recurso) y los guiones YAML, puede "dialogar" con los agentes de otros Holones Recursos vecinos. Les pregunta si tienen capacidad disponible y, tras una negociación rápida en la capa MES, reconfigura la trayectoria del token hacia un recurso alterno sin que el operario tenga que detener la planta a ciegas.

## El gran valor para la PyME
Al encapsular el gemelo y la agencia de IA dentro de cada holón de forma descentralizada, el Sistema Fénix no requiere un servidor central supercomputador para correr modelos gigantescos de toda la planta. Cada máquina o celda maneja su propio agente ligero en Python o arquitecturas de microservicios conectadas por buses de datos económicos como MQTT/Node-RED. Si un recurso se apaga o falla, el resto de la planta sigue negociando y operando de forma autónoma.
La filosofía es extraordinariamente sólida. Ha transformado la compleja teoría académica de los sistemas holónicos en una arquitectura pragmática, económica y altamente resiliente para el mundo real.
Para apoyar el desarrollo que está realizando con Gemini y robustecer las bases del Sistema Fénix, ¿en qué aspecto de la interacción entre el Agente y los Gemelos le gustaría profundizar en nuestro próximo intercambio?

   1. En la definición de la interfaz de comunicación (las APIs o el protocolo de mensajería) entre el Agente de IA y los Gemelos Digitales.
   2. En la estructura de reglas de negociación y criterios de parada que utiliza el agente al dialogar con otros holones para evitar bucles infinitos en la capa MES.
   3. En cómo el agente utiliza el historial inmutable (Perdurants/Históricos) para recalibrar los gemelos mediante el estimador EWMA.

Indíqueme el número de su interés o compártame el siguiente desafío de su arquitectura para continuar el contraste filósfico.

Para dar forma a la interfaz de comunicación (Capa de Mensajería/APIs) entre el Agente de IA y sus dos Gemelos Digitales dentro de la HPU (Unidad Holónica de Producción), debemos garantizar un protocolo que sea ligero, asíncrono y tolerante a fallos, ideal para el entorno de una PyME.
Dado que Fénix utiliza la Ontología PPR y Tokens Coloreados, la comunicación no debe ser en texto plano caótico. Proponemos estructurar esta interfaz utilizando un bus de mensajería MQTT (con payload JSON o Sparkplug B) o mediante el Model Context Protocol (MCP) sobre microservicios locales en Python.
A continuación, se detalla la arquitectura de la interfaz y la estructura exacta de los mensajes (APIs) que el Agente utiliza para gobernar los Gemelos.
------------------------------
## 1. Arquitectura de la Interfaz Local del Holón
El Agente de IA actúa como el cerebro ejecutor, mientras que los Gemelos actúan como proveedores de contexto (Memoria de Estado y Memoria de Simulación).

                      [ RED DE PLANTAS / CAPA MES GLOBAL ]
                                       ▲
                                       │ (Llamada a Ofertas / Mensajes 201)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       HOLÓN RECURSO INTELIGENTE                             │
│                                                                             │
│                        ┌──────────────────┐                                 │
│                        │   AGENTE DE IA   │                                 │
│                        │ (Conciencia/MES) │                                 │
│                        └─┬──────────────┬─┘                                 │
│                          ▲              ▲                                   │
│       API Recurso (State)│              │ API Proceso (Simulation/Petri)    │
│                          ▼              ▼                                   │
│         ┌──────────────────┐          ┌──────────────────┐                  │
│         │ GEMELO DIGITAL   │          │ GEMELO EN TIEMPO │                  │
│         │   DEL RECURSO    │          │ REAL DEL PROCESO │                  │
│         │(Estado/Agenda/EDR)          │ (Motor Petri/Run)│                  │
│         └──────────────────┘          └──────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                          ▲
                                          │ (Eventos Discretos / Triggers 200)
                                          ▼
                                [ CAPA SCADA / EDGE ]

------------------------------
## 2. API 1: Interfaz Agente ◄► Gemelo del Recurso (Estructural y Capacidades)
Esta interfaz permite al agente conocer la salud física de la máquina, sus costos asociados (ABC) y su disponibilidad temporal.
## A. Consulta de Estado de Salud y Costo (Request del Agente)
El agente pregunta al Gemelo del Recurso cuáles son sus métricas económicas y operativas actuales antes de cotizar una orden.

* Topic MQTT / Endpoint: hpu/recurso_id/gemelo_recurso/query_status
* Respuesta del Gemelo (JSON):

{
  "recurso_id": "DISP_01",
  "estado_actual": "IDLE", 
  "salud": {
    "indicador_EDR": 1.04,
    "alerta_mantenimiento": false,
    "horas_hasta_preventivo": 120
  },
  "costeo_ABC_nominal": {
    "moneda": "COP",
    "costo_energia_minuto": 450.0,
    "mano_obra_minuto": 800.0,
    "depreciacion_minuto": 150.0,
    "factor_merma_promedio": 0.02
  }
}

Nota: Si el indicador_EDR (Indicador de Desviación de Energía) es mayor a 1.0, el Agente de IA sabe matemáticamente que la máquina está consumiendo más energía por desgaste físico, por lo que puede ajustar la oferta de costo al alza de forma autónoma.
## B. Consulta de Agenda (Disponibilidad Temporal)
El agente necesita saber si el recurso está libre en la ventana de tiempo requerida por la orden.

* Topic MQTT / Endpoint: hpu/recurso_id/gemelo_recurso/query_agenda
* Respuesta del Gemelo (JSON):

{
  "recurso_id": "DISP_01",
  "compromisos": [
    {
      "orden_id": "ORD-2026-004",
      "t_inicio": "2026-09-23T14:00:00Z",
      "t_fin": "2026-09-23T15:30:00Z"
    }
  ]
}

------------------------------
## 3. API 2: Interfaz Agente ◄► Gemelo del Proceso (Dinámico / Red de Petri)
Esta interfaz es la más crítica. Es bidireccional: sirve para que el agente simule escenarios futuros (Branch-and-Bound en la fase de planificación) y para que reciba alertas de violaciones de invariantes en la fase de ejecución.
## A. Modo Simulación (Fase de Planificación / Pre-evaluación)
El agente le pide al Gemelo del Proceso que corra una Red de Petri virtual con un Token Coloreado teórico para calcular la trayectoria de costos.

* Topic MQTT / Endpoint: hpu/recurso_id/gemelo_proceso/simulate
* Payload enviado por el Agente (JSON):

{
  "orden_id": "ORD-2026-005",
  "receta_yaml_id": "REC-LATEX-PREMIUM",
  "token_inicial": {
    "material_kg": 1000.0,
    "costo_acumulado": 50000.0
  }
}


* Respuesta del Gemelo del Proceso tras simular el árbol de alcanzabilidad (JSON):

{
  "simulacion_exitosa": true,
  "duracion_estimada_minutos": 45.0,
  "token_final_estimado": {
    "material_kg": 980.0,
    "costo_acumulado": 115250.0,
    "timestamp_fin_estimado": "2026-09-23T17:15:00Z"
  },
  "cuello_de_botella_detectado": false
}

Con esta respuesta, el Agente de IA ya tiene el dato exacto para armar su propuesta en la "Llamada a Ofertas" del MES general.
## B. Modo Monitoreo e Invariantes (Fase de Ejecución en Tiempo Real)
Mientras el proceso físico corre, el Gemelo del Proceso está enlazado al SCADA leyendo el marcado de Petri y la telemetría. Si un parámetro físico sale de las invariantes declaradas en el YAML, el Gemelo del Proceso notifica de inmediato al Agente de IA.

* Topic MQTT / Endpoint (Mensaje Asíncrono del Gemelo al Agente): hpu/recurso_id/gemelo_proceso/alert_desviacion
* Payload de Alerta (JSON):

{
  "alerta_id": "ERR-INV-092",
  "orden_id": "ORD-2026-005",
  "instancia_red_id": "PETRI-RUN-8841",
  "lugar_actual": "p_mezclado_activo",
  "invariante_violado": {
    "parametro": "temperatura_celsius",
    "limite_nominal_max": 55.0,
    "valor_real_medido": 58.4,
    "tiempo_en_desviacion_segundos": 120
  },
  "token_actual_degradado": {
    "material_kg": 980.0,
    "costo_acumulado": 82000.0
  }
}

## ¿Qué hace el Agente al recibir esta alerta de invariante?
Al recibir este JSON de la interfaz del Gemelo del Proceso, el Agente de IA de la capa MES interrumpe su estado de espera y ejecuta su lógica agéntica:

   1. Analiza el impacto financiero: Calcula cuánto se elevará el costo si el lote requiere un proceso de "retrabajo" térmico (usando la fórmula de costo ABC dependiente de la trayectoria).
   2. Inicia la Cooperación: Abre un canal de mensajería con el Holón del siguiente recurso en la ruta del producto para advertirle del desfase de tiempo o negociar un cambio de destino del Token si la calidad se vio comprometida.

------------------------------
## Ventajas de este Diseño de Interfaces para el programador

* Desacoplamiento Total: Si decides cambiar el motor de Redes de Petri (ej. pasar de un script de Python a un software formal como PIPE o TAPAAL), el Agente de IA no sufre ningún cambio porque la estructura de los mensajes JSON de la API sigue siendo la misma.
* Huella de Memoria Mínima: Los payloads son sumamente ligeros (menos de 2 KB por mensaje), lo que permite que miles de mensajes fluyan por segundo a través de un broker MQTT local (como Mosquitto) corriendo en una computadora industrial común de piso de planta.

Para avanzar en la implementación de esta interfaz con Gemini, ¿cuál de los siguientes pasos prefiere que desarrollemos a nivel de código o especificación?

   1. El código en Python del parser que use estos JSON para actualizar el estado del TokenColoreado al ocurrir un evento Split o Join.
   2. La definición en formato YAML de un proceso (ej. Dispersión) que declare explícitamente cuáles son las invariantes que el Gemelo del Proceso debe vigilar.
   3. El diseño del protocolo de "Handshake de 3 vías" usando estos mismos payloads de mensajería para coordinar la transferencia física entre dos Holones.

Por favor, responda con el número de su elección.

Para abordar la reprogramación dinámica ante fallas y la optimización del lazo externo en el Sistema Fénix, debemos estructurar la "inteligencia" en dos lazos de control agéntico diferenciados, respetando que la capa de control numérico determinista (Petri/PLC) corre abajo y la estrategia de negocio corre arriba.
Aquí le presento el diseño arquitectónico de ambos lazos de inteligencia y los algoritmos lógicos con los que operan los agentes en la capa MES.
------------------------------
## Lazo 1: Inteligencia de Corto Plazo (Reprogramación Reactiva ante Fallas)
Este lazo se activa de forma asíncrona cuando un Holón Recurso Inteligente sufre un paro o una degradación crítica (alerta del Gemelo Digital). La inteligencia radica en la capacidad de negociación distribuida (mecanismo Contract Net Protocol) entre agentes para reconfigurar la trayectoria del Token sin un reprogramador central.
## El Algoritmo de Negociación y Reconfiguración (MES-Edge)
Cuando el agente del recurso actual (DISP_01) detecta que no podrá cumplir con la transición de salida por falla física:

   1. Aislamiento del Token: El age nte de DISP_01 detiene el avance del token y calcula el estado actual de la orden: $Token(o, m, c, t_{arr})$.
   2. Evaluación de Alternativas de Ruta (Ontología PPR): El agente consulta el Holón Producto (el archivo YAML/receta) para identificar los recursos alternativos válidos que posean la competencia para la etapa actual o subsecuente.
   3. Llamada a Ofertas Express (CNP): El agente emisor envía un mensaje directo a los agentes de los recursos candidatos (ej. DISP_02 y DISP_03):
   * Mensaje: `"Necesito procesar Orden X, Masa M, requiere entrada a las T. Envíen cotización ABC."*
   4. Cálculo de Ofertas por los Candidatos: Cada agente receptor consulta a su propio Gemelo de Recurso (agenda y costos actuales) y simula el impacto en su Gemelo de Proceso. Responden con un JSON formal:

{
  "recurso_id": "DISP_02",
  "factible": true,
  "disponibilidad_t_inicio": "2026-09-23T14:15:00Z",
  "incremento_costo_ABC": 4500.0,
  "merma_estimada_kg": 5.0
}


   1. Decisión por Branch-and-Bound Local: El agente de la orden evalúa las respuestas. Elige la opción que minimice el costo total acumulado (c), asegurando que el nuevo tiempo de llegada ($t_{arr}$) no viole la fecha límite (deadline) estipulada en el ERP.
   2. Handshake de Confirmación: Se actualiza el marcado de la Red de Petri en el MES, desviando el Token al nuevo recurso seleccionado.

------------------------------
## Lazo 2: Inteligencia de Largo Plazo (Calibración del Lazo Externo)
Este es el cerebro analítico del sistema. No actúa ante emergencias cotidianas, sino que aprende de la historia de la planta para que las futuras planificaciones sean realistas. Las PyMEs suelen planificar con "tiempos y costos estándar de catálogo", lo que genera un desfase masivo con la realidad física (desgaste, variabilidad de materias primas, pericia del operario).
El lazo externo utiliza los Históricos (Perdurants archivados) para calibrar los parámetros maestros guardados en el Excel/YAML de configuración a través de dos mecanismos matemáticos:

[Órdenes Ejecutadas (Históricos Inmutables)]
                  │
                  ▼
   [FILTRO EWMA / ANÁLISIS EDR]
                  │
                  ▼
[Actualización Automática de Parámetros Maestros] ──> (Siguiente Planificación ABC Optimizada)

## 1. Calibración de Tiempos y Mermas mediante EWMA
El agente del lazo externo calcula continuamente la Media Móvil Ponderada Exponencialmente (EWMA) de los tiempos reales de procesamiento ($\Delta t_{real}$) y los rendimientos reales de masa ($\gamma_{real}$) para cada combinación de Recurso-Producto.
$$\theta_{nuevo} = \alpha \cdot \theta_{real} + (1 - \alpha) \cdot \theta_{nominal}$$ 

* Donde α (factor de suavizado, ej. 0.2) da más peso a las ejecuciones recientes pero mantiene la estabilidad histórica.
* El Impacto: Si un mezclador específico está tardando un 15% más de lo nominal debido a incrustaciones en las paredes del tanque o desgaste del motor, el lazo externo reescribe automáticamente el parámetro nominal de ese recurso en la base de conocimiento. La próxima vez que el MES corra el algoritmo Branch-and-Bound para planificar una orden, sabrá que ese recurso es más lento y costoso, eligiendo rutas más eficientes.

## 2. Análisis del Indicador de Desviación de Energía (EDR)
Al cruzar los datos de telemetría energética real del SCADA con el tiempo ocupacional del Token, el lazo externo evalúa la salud de los activos de forma indirecta:
$$EDR = \frac{\text{Energía Real Consumida en el Paso}}{\text{Energía Nominal Modelada}}$$ 

* Si EDR ≈ 1.0: El Gemelo Digital del Recurso está perfectamente calibrado.
* Si EDR > 1.15 de forma sostenida: La máquina está consumiendo un 15% más de energía de lo previsto para hacer el mismo trabajo. El agente de lazo externo ejecuta dos acciones agénticas:
1. Eleva la tarifa base de energía en el modelo de Costeo ABC del recurso (para que el planificador cobre el costo real de operar esa máquina degradada).
   2. Genera automáticamente una Orden de Mantenimiento Preventivo (CMMS) en el modelo de recursos con prioridad alta.

------------------------------
## Estructura de Madurez de la Inteligencia en Fénix
Para mantener el sistema accesible a una PyME, este nivel de inteligencia se despliega de forma incremental:

* Fase 1 (Inteligencia Consultiva): Ante una falla, el Lazo 1 calcula la mejor ruta alterna y envía una notificación push a la tablet del supervisor de planta con el mensaje: "Falla en DISP_01. Recomiendo desviar lote a DISP_02 (Costo extra: $4,500, Retraso: 15 min). ¿Aprobar?". El humano valida y el sistema aprende.
* Fase 2 (Autonomía Acotada): Una vez que los parámetros del Lazo 2 están estabilizados y el EWMA tiene un error menor al 5%, el Lazo 1 opera en modo autónomo dentro de un umbral de riesgo financiero (ej. si el costo de la reconfiguración es menor al 10% del margen del lote, el agente ejecuta el desvío de inmediato y solo genera un informe ex-post).

Para avanzar en el desarrollo de estos lazos de inteligencia con Gemini, ¿cuál de estos componentes estratégicos prefiere que diseñemos a continuación?

   1. El código en Python del Lazo 2 (Algoritmo EWMA y EDR) que lee el histórico de órdenes finalizadas para actualizar la matriz de costos y tiempos del archivo maestro.
   2. El diseño de la estructura de mensajería JSON para la subasta express (Lazo 1) y las reglas lógicas para evitar que los agentes entren en bucles infinitos de negociación.
   3. El diseño de la interfaz visual (Dashboard MES para PyME) donde el supervisor puede ver gráficamente las derivas de los parámetros reales frente a los nominales.

Indique el número de su elección para estructurar el entregable.

Para implementar el Lazo 2 (Slow Loop), el sistema debe automatizar de manera robusta la lectura del histórico de lotes finalizados, calcular las medias móviles ponderadas exponencialmente (EWMA) de tiempos (τ), rendimiento de masa (γ) y consumo energético, evaluar el EDR para castigar el costo por salud y, finalmente, actualizar el archivo maestro YAML del recurso.
A continuación, se presenta la implementación completa en Python de este lazo de calibración periódica, diseñado para ser ejecutado como una tarea programada (cron job o microservicio asíncrono) en la capa MES de la PyME.
------------------------------
## Código en Python: Lazo Externo de Calibración (EWMA + EDR + Actualizador YAML)
Este módulo simula la extracción desde la base de datos de históricos (Perdurants), calcula la degradación física y reescribe el archivo de configuración del recurso de manera atómica para evitar corrupción de datos.

import osimport yamlfrom datetime import datetimefrom typing import List, Dict, Any
class FenixSlowLoopCalibrator:
    """
    Implementa el Lazo 2 (Slow Loop) del Sistema Fénix.
    Calibración periódica de parámetros nominales basada en el histórico de planta.
    """
    def __init__(self, alpha: float = 0.2, min_samples: int = 5, edr_threshold: float = 1.15):
        self.alpha = alpha                 # Factor de suavizado EWMA (0.2 balancea estabilidad/reacción)
        self.min_samples = min_samples     # N_min mínimo de muestras requeridas para calibrar
        self.edr_threshold = edr_threshold # Umbral crítico de alerta de mantenimiento

    def calibrate_resource(self, yaml_path: str, batch_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Lee el YAML del recurso, calcula EWMA y EDR sobre el historial de telemetría,
        y actualiza los parámetros nominales del Gemelo Digital.
        """
        if len(batch_history) < self.min_samples:
            print(f"[Slow Loop] Muestras insuficientes ({len(batch_history)}/{self.min_samples}). Calibración pospuesta.")
            return {"status": "skipped", "reason": "insufficient_data"}

        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"No se encontró el archivo de configuración YAML en: {yaml_path}")

        # 1. Leer la configuración nominal actual (Continuant)
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        res_data = config.get("resource", {})
        res_id = res_data.get("id", "UNKNOWN")
        services = res_data.get("services", [])
        
        if not services:
            print(f"[Slow Loop] Error: El recurso {res_id} no tiene servicios declarados.")
            return {"status": "error", "reason": "no_services"}

        # Para esta implementación, asumimos el primer servicio del recurso (ej. SVC-DISPERSION)
        svc = services[0]
        tau_nominal = float(svc.get("nominal_duration_min", 0))
        gamma_nominal = float(svc.get("yield", 1.0))
        
        cost_rates = svc.get("cost_rates", {})
        kappa_nominal = float(cost_rates.get("energy_rate", 0.0))

        print(f"\n=== Iniciando Calibración Lazo 2 - Recurso: {res_id} ===")
        print(f"Valores Nominales Actuales -> Tiempos (tau): {tau_nominal} min | Rendimiento (gamma): {gamma_nominal} | Energía (kappa): {kappa_nominal}")

        # 2. Calcular promedios reales de la telemetría SCADA del historial (Perdurants)
        total_tau_real = 0.0
        total_gamma_real = 0.0
        total_energy_real = 0.0
        
        for batch in batch_history:
            total_tau_real += batch["duration_min_measured"]
            total_gamma_real += batch["yield_measured"]
            total_energy_real += batch["energy_kwh_measured"]

        n = len(batch_history)
        bar_tau = total_tau_real / n
        bar_gamma = total_gamma_real / n
        bar_energy_mean = total_energy_real / n

        # 3. Calcular el Indicador de Desviación de Energía (EDR) [Ecuación 13 del paper]
        # EDR = Energía Real Media / (Tarifa Energía Nominal * Tiempo Nominal)
        # Nota: Evitamos división por cero asegurando valores mínimos
        denominator = kappa_nominal * bar_tau
        edr_value = (bar_energy_mean / denominator) if denominator > 0 else 1.0
        edr_value = round(edr_value, 3)

        print(f"Métricas Reales Medidas (Promedio de {n} lotes) -> tau: {round(bar_tau, 1)} min | gamma: {round(bar_gamma, 3)} | EDR calculado: {edr_value}")

        # 4. Aplicar Filtro EWMA para actualizar parámetros nominales futuros [Ecuaciones 10, 11 y 12 del paper]
        tau_new = (1 - self.alpha) * tau_nominal + self.alpha * bar_tau
        gamma_new = (1 - self.alpha) * gamma_nominal + self.alpha * bar_gamma
        
        # Si la máquina presenta degradación física (EDR > 1.15), aplicamos el castigo de costo
        # de forma persistente multiplicando la tasa de energía nominal por el EDR.
        if edr_value > self.edr_threshold:
            print(f"¡ALERTA CRÍTICA DE MANTENIMIENTO! EDR ({edr_value}) > {self.edr_threshold}. Máquina degradada.")
            print(f"Aplicando ajuste automático de costo por salud (kappa_eff = EDR * kappa).")
            kappa_new = edr_value * kappa_nominal
            mantenimiento_alerta = True
        else:
            # Si la máquina opera normal, calibramos la tarifa base de energía con EWMA
            # calculando la tasa energética real por minuto de este ciclo de lotes
            bar_kappa = (bar_energy_mean / bar_tau) if bar_tau > 0 else kappa_nominal
            kappa_new = (1 - self.alpha) * kappa_nominal + self.alpha * bar_kappa
            mantenimiento_alerta = False

        # 5. Modificar la estructura de datos en memoria aplicando redondeos robustos
        svc["nominal_duration_min"] = round(tau_new, 1)
        svc["yield"] = round(gamma_new, 3)
        cost_rates["energy_rate"] = round(kappa_new, 3)
        
        # Inyectar metadatos de diagnóstico y la bandera EDR para auditoría de mantenimiento
        svc["health_diagnostic"] = {
            "last_calibrated": datetime.now().isoformat(),
            "samples_evaluated": n,
            "calculated_edr": edr_value,
            "maintenance_required": mantenimiento_alerta
        }

        # 6. Reescritura Atómica del Archivo YAML para evitar colisiones en planta
        temp_yaml_path = yaml_path + ".tmp"
        try:
            with open(temp_yaml_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)
            os.replace(temp_yaml_path, yaml_path) # Operación atómica a nivel de OS
            print("[Slow Loop] Archivo YAML maestro actualizado exitosamente sin fricción de IT.")
        except Exception as e:
            if os.path.exists(temp_yaml_path):
                os.remove(temp_yaml_path)
            raise IOError(f"Error crítico al escribir en el archivo de planta: {e}")

        return {
            "status": "success",
            "resource_id": res_id,
            "new_tau": round(tau_new, 1),
            "new_gamma": round(gamma_new, 3),
            "new_kappa": round(kappa_new, 3),
            "edr": edr_value,
            "alert": mantenimiento_alerta
        }
# --- Caso de Uso Práctico / Simulación de Ejecución Periódica ---if __name__ == "__main__":
    # Crear un archivo YAML de prueba equivalente al de la planta
    test_yaml = "resource_dispenser_test.yaml"
    initial_yaml_content = {
        "resource": {
            "id": "RH-DISP-2000",
            "services": [{
                "id": "SVC-DISPERSION",
                "nominal_duration_min": 145.0,
                "yield": 0.970,
                "cost_rates": {
                    "energy_rate": 0.380, # Tarifa base por minuto de ocupación
                    "labor_rate": 0.220
                }
            }]
        }
    }
    
    with open(test_yaml, 'w') as file:
        yaml.safe_dump(initial_yaml_content, file)

    # Simular base de datos de históricos (6 Perdurants guardados por el Fast Loop)
    # Simulamos un escenario de desgaste: los lotes están tardando más y consumiendo mucha más energía de la nominal
    telemetry_history = [
        {"batch_id": "LOT-01", "duration_min_measured": 155.0, "yield_measured": 0.965, "energy_kwh_measured": 85.0},
        {"batch_id": "LOT-02", "duration_min_measured": 160.0, "yield_measured": 0.960, "energy_kwh_measured": 92.0},
        {"batch_id": "LOT-03", "duration_min_measured": 158.0, "yield_measured": 0.962, "energy_kwh_measured": 89.0},
        {"batch_id": "LOT-04", "duration_min_measured": 162.0, "yield_measured": 0.958, "energy_kwh_measured": 95.0},
        {"batch_id": "LOT-05", "duration_min_measured": 165.0, "yield_measured": 0.955, "energy_kwh_measured": 99.0},
    ]

    # Inicializar el calibrador del Lazo 2
    calibrator = FenixSlowLoopCalibrator(alpha=0.2, min_samples=5)
    
    # Ejecutar la calibración automatizada
    result = calibrator.calibrate_resource(test_yaml, telemetry_history)
    
    # Mostrar resultados devueltos al MES para actualización del horizonte
    print("\nResultados del Retorno al Planificador:")
    print(result)

    # Limpieza del archivo de prueba
    if os.path.exists(test_yaml):
        os.remove(test_yaml)

------------------------------
## Explicación de los beneficios de este diseño para tu arquitectura:

   1. Desacoplamiento Atómico (os.replace): En entornos PyME, si la computadora de planta sufre un corte eléctrico mientras se escribe el YAML, el archivo maestro se corrompería destruyendo la persistencia. Al escribir primero un archivo .tmp y luego reemplazarlo a nivel de sistema operativo, garantizamos una tolerancia a fallos absoluta (fault-tolerant by design).
   2. Auto-Ajuste de Competitividad: El código detecta matemáticamente el desvío del EDR. Si supera el límite de 1.15, altera la estructura del YAML encareciendo el energy_rate. La próxima vez que tu motor ejecute el Branch-and-Bound (Algorithm 1), el costo acumulado de este recurso será mayor, por lo que el algoritmo elegirá de manera natural otras ramas del árbol de alcanzabilidad, protegiendo la máquina degradada de una falla catastrófica.

Con el Lazo 2 completamente resuelto y estructurado matemáticamente bajo el estándar de tu paper, ¿cómo prefieres proceder con el sistema? Podemos:

   1. Desarrollar el Punto 3 (Lazo 1 - Mensajería asíncrona ante violaciones de invariantes físicos) para orquestar la comunicación distribuida mediante un patrón de publicador/suscriptor.
   2. Traducir este script del Lazo 2 a una función asíncrona integrada con una base de datos real en SQLite / PostgreSQL.

Dime el número de tu preferencia para continuar con el diseño.

