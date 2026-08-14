# Manual de Arquitectura e Integración: Sistema MOM para PyMEs

## 1. Introducción y Contexto
En el ecosistema de aplicaciones de una empresa industrial, el MOM (Manufacturing Operations Management) actúa como la **bisagra crítica entre el mundo de los negocios (IT) y el mundo de la producción (OT)**. Traduce las órdenes de producción provenientes del sistema ERP en tareas ejecutables en el piso de planta y, en sentido inverso, agrega y contextualiza los datos operativos en tiempo real (consumos, estados, calidad) para ofrecer una visión precisa del rendimiento a los sistemas de negocio.

### 1.1. El Desafío de la PyME Industrial
La PyME enfrenta una realidad marcada por un parque de máquinas heterogéneo, baja automatización y recursos limitados. Este sistema está diseñado para cerrar la brecha IT/OT permitiendo una transformación digital progresiva basada en la realidad actual de la planta.

## 2. Arquitectura de Aplicaciones
El sistema se basa en una arquitectura de **holones**, unidades autónomas y cooperativas que representan recursos, productos y procesos.

### 2.1. Componentes Clave
*   **MOM (Manufacturing Operations Management):** Recibe las órdenes del ERP y las descompone en tareas detalladas. Orquesta la ejecución y monitoriza los datos del piso de planta.
*   **Piso de Planta (Shop Floor):** Ejecuta las tareas físicas y genera un flujo masivo de datos en tiempo real (temperaturas, ciclos, unidades producidas) que es enviado hacia el MOM.
*   **Integración Vertical:** Conexión bidireccional entre los sistemas de nivel de negocio (ERP) y los de producción (SCADA/PLC).

## 3. El Ciclo Operativo de Mejora Continua
El sistema utiliza un ciclo de retroalimentación de 5 fases para garantizar que la planificación sea siempre realista y rentable.

### 3.1. Fase 1: Recolección Híbrida (Excel + Web)
*   **Excel/CSV:** Para la definición de maestros (materiales, rutas, costos, consumos teóricos).
*   **Interfaz Web:** Para el reporte dinámico de la operación (tiempos reales, paradas, desperdicios).

### 3.2. Fase 2: Modelo de Conocimiento
El sistema construye un **Gemelo Digital Económico** que entiende las capacidades reales y los costos proyectados.

### 3.3. Fase 3: Planificación y Optimización
Algoritmo de programación que busca el cumplimiento de fechas y la minimización de costos operativos (energía y horas hombre).

### 3.4. Fase 4: Ejecución y Monitoreo de Consumos
Seguimiento en tiempo real de la variación entre lo planificado y lo real, con alertas visuales ante desviaciones de costos o materiales.

### 3.5. Fase 5: Análisis y Ajuste
Cierre del ciclo mediante la recalibración de los parámetros del modelo (tiempos estándar y recetas) basados en la historia real recolectada.

## 4. Metodología de Levantamiento de Información
Para garantizar la integridad y escalabilidad del sistema MOM, el proceso de obtención y carga de datos sigue un enfoque top-down basado en una taxonomía jerárquica. Este método asegura que la estructura de datos sea consistente y que cada nuevo elemento herede las reglas de negocio pertinentes.

### 4.1. Fase 1: Definición de la Taxonomía Global
Antes de modelar productos individuales, se deben establecer las categorías maestras que regirán el sistema:
*   **Taxonomía de Productos:** Clasificación por familias, niveles de transformación (MP, SE, PT) y criticidad de trazabilidad.
*   **Taxonomía de Recursos:** Definición de tipos de estaciones (Manual, Semiautomática, Automática), centros de costo y capacidades genéricas (Setup, Run, Tear-down).
*   **Taxonomía de Procesos:** Catálogo de operaciones estándar (Corte, Ensamble, Prueba, Empaque) con sus variables de control asociadas.

### 4.2. Fase 2: Modelado por Producto (Enfoque en el "Qué")
Una vez establecida la taxonomía, se procede a detallar cada producto siguiendo la estructura heredada:
1.  **Asignación Taxonómica:** Cada producto se vincula a una familia predefinida.
2.  **BOM (Bill of Materials):** Definición de la estructura de materiales, vinculando insumos con etapas del proceso.
3.  **BOP (Bill of Process):** Secuencia lógica de operaciones, utilizando las plantillas de la taxonomía de procesos para asegurar tiempos estándar coherentes.

### 4.3. Fase 3: Modelado por Recurso (Enfoque en el "Cómo")
Finalmente, se modela la capacidad física de la planta:
1.  **Instanciación de Recursos:** Mapeo de máquinas y puestos de trabajo reales hacia los tipos definidos en la taxonomía.
2.  **Parámetros de Capacidad:** Definición de calendarios, turnos y restricciones específicas por recurso.
3.  **Grafo de Conectividad (Arquitectura de Red):** 
    *   **Nodos y Arcos:** Los recursos se modelan como nodos en un grafo dirigido.
    *   **Costo de Transferencia:** Cada conexión (arco) entre recursos define un `tiempo_transito` y un método de transporte (Manual vs. Automático).
    *   **Cálculo de Ruta Óptima:** El motor de orquestación utiliza algoritmos de búsqueda en grafos para determinar la secuencia de máquinas que minimiza el tiempo total de ciclo (Throughput Time), considerando las restricciones de la taxonomía.

## 5. Motor de Orquestación y Ejecución (Petri-Net Engine)
La ejecución del sistema no es lineal, sino asíncrona y basada en eventos, utilizando el formalismo de **Redes de Petri** para gestionar el estado de cada Holón de Producto.

### 5.1. El Holón de Producto en Movimiento
Cuando se libera una Orden de Producción, el sistema genera un "Token" (Marca) que representa el producto físico. Este token viaja a través del modelo dinámico (`ModeloProductoDinamica`):
1.  **Lugares (Places):** Representan estados u operaciones (ej: "Esperando en Soldadura", "En Inspección").
2.  **Transiciones (Transitions):** Son las reglas de disparo. Una tarea solo comienza si:
    *   Existe un token en el lugar de entrada (el material llegó).
    *   El recurso asociado (máquina/operario) está `Disponible` en el Modelo de Recurso.
    *   Se recibe el `disparador` (mensaje de SCADA o confirmación del operario vía Web).

### 5.2. Sincronización IT/OT y Handshake
El motor de ejecución realiza un "apretón de manos" (Handshake) entre los niveles:
*   **Nivel de Negocio:** Reserva el material en el inventario.
*   **Nivel de Orquestación:** Envía el `mensajeSalida` (parámetros de receta) al recurso.
*   **Nivel de Ejecución:** Monitorea el tiempo de ciclo real vs. el teórico definido en la taxonomía.

### 5.3. Validación de Invariantes y Bucles de Calidad
El motor implementa dos mecanismos de supervisión sobre la trayectoria del token:
*   **Invariantes de Lazo Cerrado:** Antes de disparar una transición, el sistema compara las lecturas continuas recolectadas del sensor (temperatura, presión) contra los límites de `InvariantePaso` del recurso. Si hay desviación, bloquea el disparo y lanza una alarma.
*   **Compuertas de Calidad (QA Loops):** Al reportarse las mediciones físicas de laboratorio, el orquestador valida automáticamente contra `CriterioAceptacionEtapa` y `EspecificacionCalidad`. Si cumple, dispara la aprobación (trigger `"201"`); de lo contrario, dispara la transición competitiva de reproceso (trigger `"200"`), devolviendo el token a la etapa de mezcla.

## 6. Especificaciones de Interfaz

*   **Holón:** Una unidad organizativa autónoma y cooperativa que puede representar un recurso físico o un proceso lógico.
*   **Convergencia IT/OT:** La integración de las tecnologías de la información (negocios) con las tecnologías de la operación (producción).
*   **OEE (Overall Equipment Effectiveness):** KPI que mide la disponibilidad, el rendimiento y la calidad de los recursos de producción.
*   **Plan de Ejecución:** El conjunto de tareas orquestadas y asignadas a recursos específicos para cumplir una orden de producción.
