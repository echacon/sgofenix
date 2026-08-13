# Filosofía de Integración Holónica: El Sistema Fénix

> *"Cada lote de producción es un token que viaja por el sistema acumulando trazabilidad (cantidad, costo, tiempo). Cada recurso es un holón autónomo que sabe qué hacer y con quién coordinarse."*

Este documento describe la base conceptual y la filosofía de diseño del **Sistema Fénix**, un sistema de Gestión de Operaciones de Manufactura (**MOM - Manufacturing Operations Management**) diseñado específicamente para Pequeñas y Medianas Empresas (PyMEs). El objetivo es guiar tanto a investigadores como a empresas que deseen instalar y desplegar Fénix en planta, ayudándoles a comprender la lógica subyacente que lo hace flexible, resiliente y de bajo costo.

---

## 1. De la Jerarquía a la Autonomía: Un Cambio de Paradigma

El desarrollo de Fénix representa una evolución histórica y conceptual de los sistemas de automatización industrial. Durante décadas, las grandes corporaciones automatizaron sus plantas utilizando el **enfoque jerárquico clásico**, estructurado según la norma **ISA-95**. 

Este modelo divide la fábrica en niveles rígidos:
*   **Nivel 1:** Instrumentación y PLCs (Control Físico).
*   **Nivel 2:** SCADA (Supervisión).
*   **Nivel 3:** MES (Ejecución).
*   **Nivel 4:** ERP (Planificación/Finanzas).

```
          ENFOQUE CLÁSICO (ISA-95)              ENFOQUE HOLÓNICO (FÉNIX)
                 
               [ Nivel 4: ERP ]
                      │                                    ┌──────────────┐
               [ Nivel 3: MES ]                  ┌────────>│ Holón Orden  │<────────┐
                      │                          │         └──────────────┘         │
              [ Nivel 2: SCADA ]                 ▼                                  ▼
                      │                  ┌──────────────┐                  ┌──────────────┐
              [ Nivel 1: PLCs ]          │ Holón Recurso│<────────────────>│ Holón Producto│
                                         └──────────────┘                  └──────────────┘
                                          (Autonomía Edge)                 (Conocimiento)
```

### El Antecedente Histórico
El primer autor de esta arquitectura participó en el diseño y definición de las estructuras de automatización de grandes empresas estatales del sector petroquímico y petrolero a finales del siglo XX. Aquellas arquitecturas, aunque robustas, eran **jerárquicas y descentralizadas**: el control de la información fluía verticalmente. Si un PLC en el Nivel 1 fallaba o cambiaba de comportamiento, la actualización de los modelos de planificación en el Nivel 4 requería complejas intervenciones manuales y middleware costoso.

Este enfoque jerárquico tradicional es inviable para las PyMEs debido a:
1.  **Altos costos de integración:** Licenciamiento y mantenimiento de software propietario (MES/APS).
2.  **Rigidez:** Cualquier cambio en la planta (una máquina fuera de servicio, un operario reasignado) rompe el plan de producción centralizado.
3.  **Brecha IT/OT:** Los objetivos financieros de negocio y la realidad física de la planta están desconectados.

### La Solución: Integración Holónica (Fénix)
Fénix rompe la estructura vertical y la sustituye por una **red de agentes autónomos y cooperativos llamados Holones**. Un holón es una entidad que es, al mismo tiempo, un todo y una parte (ej. una máquina es un holón completo en sí misma, pero es parte del holón del taller de producción).

| Dimensión | Enfoque Jerárquico Clásico (ISA-95) | Enfoque Holónico (Fénix) |
| :--- | :--- | :--- |
| **Flujo de Información** | Vertical, a través de capas rígidas. | Red distribuida de colaboración. |
| **Toma de Decisiones** | Centralizada en el software ERP/MES. | Descentralizada y negociada por los recursos. |
| **Resiliencia** | Sensible a fallos en la red central. | Tolerante a fallos; auto-organizado. |
| **Mantenimiento** | Requiere personal especializado de IT. | Modificable por personal de planta en YAML/Excel. |
| **Calibración** | Periódica, manual y offline. | Continua, automática y online (vía SCADA). |

---

## 2. Los Pilares de la Arquitectura Fénix

Fénix se sostiene sobre tres pilares conceptuales y un bucle de retroalimentación en tiempo real:

### Pilar A: La Ontología PPR (Producto-Proceso-Recurso)
La información de la planta no se modela en tablas aisladas, sino en una estructura de conocimiento integrada:
*   **Holón Recurso (Con qué se fabrica):** Encapsula el "saber hacer" físico de las máquinas y operarios. Lleva consigo su capacidad, su agenda de disponibilidad, su tasa de consumo de energía y su historial de rendimiento.
*   **Holón Producto (Qué se fabrica):** Define las especificaciones técnicas del artículo y la receta de materiales (BOM).
*   **Holón Proceso (Cómo se fabrica):** Especifica las secuencias lógicas, paralelismos y alternativas de producción (BOP).

En Fénix, **el conocimiento del proceso se encapsula en el recurso que lo ejecuta**. Si se instala un nuevo mezclador, este declara autónomamente qué servicios ofrece, su rendimiento y costos. El resto del sistema no necesita reprogramarse.

### Pilar B: Redes de Petri Coloreadas y P-Timed (AB-TPPN)
Fénix no utiliza diagramas de flujo pasivos. El proceso de manufactura se representa formalmente mediante una **Red de Petri Coloreada Temporal (P-timed)**:
*   **Lugares (Places):** Representan estados ocupacionales (ej. "Mezclando en Dispersor 1"). El tiempo de residencia en el lugar representa el tiempo que el lote ocupa la máquina.
*   **Transiciones:** Representan eventos de cambio (ej. "Iniciar trasvase").
*   **Tokens Coloreados:** Representan los lotes físicos de producción. El token viaja por la red acumulando dinámicamente tres atributos: identificador de orden, masa/cantidad de material (ajustado por mermas) y costo económico.

### Pilar C: Costeo Basado en Actividades (ABC) como Objetivo
A diferencia de la mayoría de los programadores de fábrica que optimizan únicamente el tiempo total de fabricación (makespan), **Fénix tiene como objetivo principal la minimización del costo total real de producción**, sujeto a cumplir con la fecha límite de entrega.

El costo acumulado por el token en cada etapa se calcula considerando cuatro componentes clave en tiempo real:
$$\Delta c = (\text{Costo Energía} \times \Delta t) + (\text{Mano de Obra} \times \Delta t) + (\text{Depreciación} \times \Delta t) + \text{Pérdida de Material}$$

Debido a que el rendimiento de materiales de una etapa previa influye en la cantidad de material requerida en la etapa posterior, **el costo de producción es dependiente de la trayectoria (path-dependent)**. Fénix calcula el árbol de alcanzabilidad del proceso y evalúa mediante *Branch-and-Bound* la secuencia óptima global.

---

## 3. Resiliencia ante Fallos (La Capacidad Fénix)

El nombre del sistema evoca al ave mitológica que renace de sus cenizas. En entornos de PyMEs, las caídas de tensión eléctrica, fallos de red o reinicios de computadores son comunes. 

Fénix logra una **tolerancia a fallos absoluta** mediante la persistencia transaccional del marcado de Petri:
1.  Cada vez que ocurre un evento físico (detectado por el SCADA o reportado por el operario), el motor de Petri valida las precondiciones.
2.  Si la transición es válida, el Token se mueve de lugar y sus atributos (cantidad, costo, tiempo) se recalculan.
3.  Este nuevo estado se guarda en la base de datos local en una transacción atómica instantánea.
4.  Si el servidor se apaga repentinamente, al reiniciarse Fénix lee el último estado guardado y reconstruye la red exactamente donde quedó, permitiendo continuar la producción de inmediato sin pérdida de trazabilidad.

---

## 4. Guía de Despliegue Práctico para la Empresa

Fénix está estructurado para que una empresa real pueda desplegarlo sin conocimientos avanzados de programación o teoría de grafos, utilizando herramientas familiares:

```
    DATOS ESTÁTICOS (Excel)
  ┌────────────────────────┐
  │ Familias, Insumos,     ├──────┐
  │ Costos de Máquinas     │      │
  └────────────────────────┘      ▼
                             ┌──────────┐      ┌─────────────┐      ┌───────────────┐
                             │  FÉNIX   │─────>│ Programación│─────>│Ejecución en   │
    LÓGICA DE FLUJO (YAML)   │  Parser  │      │   Óptima    │      │ Planta (SCADA)│
                             └──────────┘      └─────────────┘      └───────┬───────┘
                                  ▲                                         |
  ┌────────────────────────┐      │                                         └─────      
  │ Secuencia de pasos     |      |                                         Realimentación   
  | y Reglas de Handshake  │──────┘         
  └────────────────────────┘                                          
```

1.  **Carga de Datos (Excel):** La empresa define su estructura de costos básicos en una plantilla Excel inteligente. Aquí se listan las familias de productos, los recursos físicos con sus tarifas horarias de operarios, costos de energía y depreciación, y las recetas de ingredientes (BOM).
2.  **Definición del Flujo (YAML):** En lugar de programar código, el ingeniero de planta escribe un "guion" YAML muy simple donde declara los pasos del proceso. Fénix traduce este YAML automáticamente a la Red de Petri formal. También pued eser utilizado un archivo .pnml
3.  **Orquestador de Ejecución:** El sistema genera una interfaz web responsiva para los operarios. Cuando un operario presiona "Iniciar" en su tablet, el SCADA envía un trigger a Fénix, el token avanza en la Red de Petri y se registra el costo acumulado.
4.  **Bucle de Retroalimentación (SCADA y EWMA):** Los sensores de energía y los registros de tiempo reales del SCADA se comparan con los parámetros nominales guardados en el Excel. Semanalmente, el estimador EWMA de Fénix calibrá los parámetros nominales históricos, y el cálculo del **Indicador de Desviación de Energía (EDR)** alerta al equipo de mantenimiento si una máquina está consumiendo más de lo normal debido a desgaste físico.

---

## 5. Enlaces y Recursos

*   **Manual Técnico Detallado:** [`Manual_Tecnico_Final_MOM.md`](file:///C:/Users/echac/Documents/gemini/Manual_Tecnico_Final_MOM.md)
*   **Manual del Usuario de Planta:** [`Manual_Usuario_MOM.md`](file:///C:/Users/echac/Documents/gemini/Manual_Usuario_MOM.md)
*   **Código de la Ontología y Motores:** Ubicado en la subcarpeta [`sgo/fenix/`](file:///C:/Users/echac/Documents/gemini/sgo/fenix)
