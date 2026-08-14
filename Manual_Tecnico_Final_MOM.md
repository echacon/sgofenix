# Manual Técnico de Arquitectura e Integración MOM

## 0. Filosofía de Diseño: El Sistema FÉNIX

FÉNIX representa un cambio de paradigma en la automatización de operaciones de manufactura, evolucionando desde los modelos clásicos de control jerárquico vertical (como las estructuras rígidas ISA-95 implementadas históricamente en grandes sectores como PDVSA) hacia un **enfoque holónico y autónomo distribuido**. Para una comprensión profunda de este marco evolutivo y sus pilares de diseño, consulta el documento principal de la [Filosofía de Integración Holónica](file:///C:/Users/echac/Documents/gemini/Filosofia_Integracion_Holonica.md).

El sistema se basa en la convergencia de **Redes de Petri Coloreadas (CPN)** y la **Arquitectura Holónica**. Está diseñado para ser "fault-tolerant" (tolerante a fallos), permitiendo la reconstrucción completa del estado de planta a partir de los logs de eventos transaccionales persistidos en base de datos.

### 0.1. El Token Coloreado (Entidad de Trazabilidad)
Cada lote de producción se representa por un objeto `TokenColoreado` que viaja por las redes acumulando:
*   `o`: Identificador de la orden.
*   `m`: Masa/Material actual (ajustado por mermas $\gamma$).
*   `c`: Costo acumulado (ABC - Activity Based Costing).
*   `t`: Timestamp de los eventos.

### 0.2. Ontología de Objetos
*   **Continuants (Saber Hacer):** Entidades estáticas como `Recurso`, `HolonRuta`, `Producto`.
*   **Perdurants (El Hacer):** Entidades dinámicas con duración como `InstanciaRed`, `OrdenProduccion`, `EventoRed`.

---

## 1. Arquitectura de Implantación (HPU - Holonic Production Unit)
El sistema implementa una arquitectura de tres capas para cada **Holón Recurso**:

### 1.1. Capa de Gestión (Nivel MES)
Responsable de la negociación de compromisos y mantenimiento de los Gemelos Digitales. 
*   **Mecanismo:** "Llamada a Ofertas" para asignar órdenes basadas en costo y disponibilidad.
*   **Optimización:** Algoritmo Branch-and-Bound sobre el árbol de alcanzabilidad de las Redes de Petri.

### 1.2. Capa de Ejecución (Nivel SCADA)
Supervisa el proceso en tiempo real y gestiona los **Acuerdos de Coordinación** (Handshakes).

#### El Motor de Orquestación (Symphony Parser)
El sistema utiliza un DSL en YAML (basado en Symphony Workflow) para definir los procedimientos. El motor de ejecución traduce este YAML a una Red de Petri Coloreada (CPN) siguiendo estas reglas:
*   **Places:** Definidos en la sección `estaciones` del YAML. Cada estación representa un estado posible del token.
*   **Transitions:** Definidas en la sección `acciones`.
    *   `cuando: [A, B]`: Genera arcos de entrada desde los lugares A y B (Join/Sincronización).
    *   `mueve_a: [C, D]`: Genera arcos de salida hacia los lugares C y D (Split/Paralelismo).
*   **Triggers:** Mapeados a partir del campo `tipo`:
    *   `Manual`: Trigger 200 (Evento externo).
    *   `Sincronizado`: Trigger 201 (Mensaje entre redes).
    *   `Automatico`: Trigger `none`.

### 1.3. Capa Física
Interfaz agnóstica al nivel de automatización (PLCs, Sensores o Tablets para operarios).

---

## 2. Convergencia IT/OT
El sistema MOM actúa como el "Sistema Nervioso Central" de la producción, conectando los objetivos de negocio (IT) con la ejecución física (OT). Su diseño se basa en **Holones cooperativos** que permiten una orquestación distribuida y resiliente.

---

## 2. Los Tres Niveles de Madurez Digital
El sistema se adapta dinámicamente según la versión seleccionada por el usuario, manteniendo la misma base de datos pero activando diferentes motores de lógica.

### 2.1. V1: MOM Manual (Modo Taller/PyME)
*   **Enfoque:** Digitalización básica de procesos manuales.
*   **Captura:** Formularios Web simplificados.
*   **Lógica:** Secuenciación FIFO/Prioridad. El operario es el sensor principal.

### 2.2. V2: MOM Híbrido (Modo Crecimiento)
*   **Enfoque:** Seguimiento de flujo y eficiencia.
*   **Captura:** Mixta (Web + IoT básico/PLCs aislados).
*   **Lógica:** Capacidad Finita. Control de materiales por lotes y estados de máquina.

### 2.3. V3: MOM Avanzado (Smart Factory)
*   **Enfoque:** Orquestación autónoma y conectividad total.
*   **Captura:** Automática vía SCADA/OPC-UA/MQTT.
*   **Lógica:** Orquestación PPR (**Producto, Proceso, Recurso**) con grafo de conectividad, basada en **Holones**.

---

## 3. El Modelo de Conectividad y Orquestación (V3)
En la versión avanzada, el sistema utiliza un **Holón de Ruta** (o Grafo de Transferencia) para decidir la ruta óptima de fabricación.

### 3.1. Definición del Grafo de Recursos
Cada **Holón de Recurso** define sus "puertos" de salida y entrada hacia otros recursos. Esto permite al planificador calcular el **Tiempo de Tránsito** y gestionar el **Handshake de Transferencia** (protocolo de intercambio de información entre máquinas).


### 3.2. Sincronización SCADA
El sistema se suscribe a tags específicos para detectar eventos de:
*   `Order_Start` / `Order_Complete`.
*   `Machine_State` (Producción, Parada, Mantenimiento).
*   `Real_Consumption` (kWh, kg, unidades).

### 3.3. Validación de Invariantes Físicos y Compuertas de Calidad (QA Loops)
El sistema intercepta la telemetría recibida desde los PLCs o estaciones SCADA para realizar dos tipos de validación en tiempo real:

1.  **Validación de Invariantes (`InvariantePaso`):** 
    Antes del disparo de cualquier transición discreta (evento de fin de paso), el orquestador compara las lecturas físicas promediadas del paso actual (ej. `Temperatura`, `Velocidad`) contra los límites definidos en la base de datos para esa asignación de recurso. Si se detecta una violación:
    $$\text{Lectura} > \text{valor\_maximo} \quad \text{o} \quad \text{Lectura} < \text{valor\_minimo}$$
    El orquestador bloquea el disparo de la transición, registra la anomalía en el log de eventos (`EventoRed.invariantes`) y levanta un estado de alarma de trayectoria, evitando que un lote defectuoso progrese en la planta.
2.  **Compuertas de Calidad Automáticas (QA Loops):**
    En las etapas de control de calidad, cuando el laboratorio ingresa los valores de las pruebas físicas (viscosidad, pH), el orquestador los evalúa contra las especificaciones del producto (`CriterioAceptacionEtapa` y `EspecificacionCalidad`):
    *   **Pasa (Aprobado):** Se dispara automáticamente la transición conectada de aprobación (trigger `"201"`), avanzando el lote a la etapa de envasado.
    *   **No Pasa (Rechazado):** Se dispara automáticamente la transición de reproceso (trigger `"200"`), retornando el lote al dispersor/mezclador y forzando la acumulación de tiempos y costos de retrabajo.

---

## 4. Ingesta de Datos (Excel Parser Inteligente)
El Parser de plantillas Excel es la puerta de entrada al Modelo de Conocimiento.
*   **Para V1:** Procesa tiempos estándar y materiales.
*   **Para V3:** Construye automáticamente el **Grafo de Conectividad** basándose en la tabla de adyacencia de máquinas y los mapas de transferencia cargados por el ingeniero de planta.

---

## 5. Ciclo de Mejora Continua: Costos y Eficiencia
El sistema cierra el ciclo comparando el **Costo Teórico (Excel)** contra el **Costo Real (Captura)**.

1.  **Recolección:** Datos de consumo (energía/insumos) y tiempo hombre.
2.  **Modelo de Conocimiento:** Gemelo digital con valor económico actualizado.
3.  **Análisis de Desviaciones:** Alertas de variaciones de costos y desperdicios.
4.  **Ajuste:** Retroalimentación automática a la Fase 2 para calibrar el próximo plan de producción.

---

## 7. Arquitectura de Datos y Ciclos de Eventos (Persistencia)

Para asegurar la resiliencia del sistema (Capacidad FÉNIX), cada cambio de estado se registra en un ciclo de 4 pasos.

### 7.1. Flujo de Captura de Evento
```
1. Orquestador recibe evento (SCADA/Tablet)
2. Motor de Petri valida precondiciones de la transición.
3. Se dispara la transición y se actualiza el Token Coloreado.
4. Persistencia inmediata en base de datos (Atomic Transaction).
```

### 7.2. Handshake entre Redes (Trigger 201)
Cuando dos máquinas deben intercambiar material, el sistema utiliza un **Mensaje Pendiente** para sincronizarlas:
*   **Origen:** Red A dispara `t_fin` -> Genera `MensajePendiente`.
*   **Destino:** Red B recibe `MensajePendiente` -> Habilita `t_inicio`.

### 7.3. Recuperación tras Fallos
Al reiniciar, el sistema lee la tabla `instancia_red` y reconstruye el marcado de las Redes de Petri y el estado de los Tokens, permitiendo continuar la producción exactamente donde se detuvo.

---

## 8. Caso de Estudio Técnico: El Ciclo de Retroalimentación

Considerando el caso de **"Pinturas El Fénix"**:
1.  **Ejecución:** Se capturan eventos de `Dispersor_22` vía Trigger 200.
2.  **Detección de Desviación:** El orquestador compara el `token.t` (tiempo real) vs el `HolonRuta.tiempo_std`.
3.  **Cálculo de KPI:** Se genera un `EventoRed` con el delta de tiempo y costo adicional.
4.  **Ajuste de Modelo:** El sistema de gestión propone la actualización del `Continuant` (Recurso) basándose en la media móvil de los últimos 3 `Perdurants` (Órdenes ejecutadas).
