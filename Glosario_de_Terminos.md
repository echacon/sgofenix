# Glosario de Términos para Ontología MOM de PyMEs

Este documento consolida la terminología de los manuales del sistema y los documentos de arquitectura para establecer una base conceptual unificada para el sistema de Gestión de Operaciones de Manufactura (MOM) para PyMEs.

---

### A

**Agente**
- **Definición:** Un recurso con autonomía para prestar un servicio. Es una entidad (física, digital o híbrida) que puede tomar decisiones y actuar de forma independiente para cumplir sus objetivos.
- **Relaciones:**
    - *Es un tipo de:* `Recurso`.
    - *Posee:* `Autonomía`.
    - *Realiza:* `Servicios`.

**Autonomía**
- **Definición:** La capacidad de un recurso para cumplir un objetivo o prestar un servicio sin intervención externa, tomando sus propias decisiones.
- **Relaciones:**
    - *Es una característica de:* `Agente`, `Recurso Autónomo`.

---

### C

**Calidad**
- **Definición:** Conjunto de características y atributos de un producto, proceso o recurso que determinan su aptitud para satisfacer las necesidades especificadas. Se mide a través de métricas como rendimiento, durabilidad, conformidad, etc.
- **Relaciones:**
    - *Es un atributo de:* `Producto`.
    - *Se verifica mediante:* `Proceso` de monitoreo.

---

### M

**Manufactura Orientada por Servicios (MOS)**
- **Definición:** Un modelo de producción industrial que integra los principios de la orientación a servicios (SOA). En este enfoque, los recursos de manufactura (máquinas, sistemas, procesos) son tratados como proveedores de servicios modulares, interoperables y bajo demanda.
- **Relaciones:**
    - *Utiliza:* `Servicio`, `RPSM`.
    - *Orquesta:* `Servicios de Núcleo` y `Servicios de Soporte`.

**Modelo del Proceso**
- **Definición:** La descripción formal de cómo realizar un proceso en un recurso. Especifica los pasos, las reglas, los recursos necesarios y la dinámica (discreta, continua o híbrida) para lograr un objetivo.
- **Relaciones:**
    - *Describe a:* `Proceso`.
    - *Es la base para:* `Plan de Ejecución`.

---

### O

**Orden de Producción**
- **Definición:** Una entidad ocurrente que forma parte del `Plan de Ejecución`. Autoriza la fabricación de una cantidad específica de un producto. Contiene al menos una `Orden de Trabajo` y especifica los recursos, insumos y fechas para la producción.
- **Relaciones:**
    - *Es parte de:* `Plan de Ejecución`.
    - *Contiene una o más:* `Orden de Trabajo`.
    - *Inicia la:* `Ejecución` de un `Proceso`.

**Orden de Trabajo**
- **Definición:** Especifica las actividades detalladas de transformación a realizar en cada paso de un `Proceso`. Es la unidad mínima de trabajo asignada a un recurso para su ejecución.
- **Relaciones:**
    - *Es parte de:* `Orden de Producción`.
    - *Detalla un:* `Paso` de un `Proceso`.

**Orquestador**
- **Definición:** Entidad (generalmente un sistema software como un MOM/MES) que organiza, sincroniza y asigna los `Servicios` (tanto de núcleo como de soporte) necesarios para obtener un producto, basándose en la disponibilidad, coste y capacidad.
- **Relaciones:**
    - *Equivalente a:* Planificador o Scheduler.
    - *Gestiona:* `RPSM` y `Servicios`.

---

### P

**Etapa de Proceso (Segmento de Producto)**
- **Definición:** Una actividad o etapa individual dentro de un proceso de fabricación. Corresponde a la unidad mínima de trabajo que se realiza en un recurso específico. Bajo la norma ISA-95, se denomina "Segmento de Producto"^1.
- **Relaciones:**
    - *Es un componente de:* `Holón de Ruta` o `Ruta de Proceso`.
    - *Es detallado por:* `Orden de Trabajo`.
    - *Se ejecuta en un:* `Holón de Recurso`.

^1: En este manual se utilizará preferentemente el término "Etapa de Proceso" para facilitar la comprensión operativa, manteniendo "Segmento de Producto" para referencias técnicas normativas.

**Holón de Ruta (o Ruta de Proceso)**
- **Definición:** La secuencia organizada de `Etapas de Proceso` necesarias para fabricar un producto específico (ej. DIS -> MOL -> DIL). Define la precedencia y lógica del flujo de producción.
- **Relaciones:**
    - *Contiene:* Una secuencia de `Etapas de Proceso`.
    - *Es propiedad del:* `Holón Producto`.
    - *Es la base para:* `Plan de Ejecución`.

**Orden de Trabajo**
- **Definición:** Especifica las actividades detalladas de transformación a realizar en una `Etapa de Proceso`. Es la unidad mínima de trabajo asignada a un recurso para su ejecución.
- **Relaciones:**
    - *Es parte de:* `Orden de Producción`.
    - *Detalla una:* `Etapa de Proceso`.

**Orquestador**
- **Definición:** Entidad (generalmente un sistema software como un MOM/MES) que organiza, sincroniza y asigna las `Etapas de Proceso` a los `Holones de Recurso` necesarios para obtener un producto.

---

**Paso**
- **Eliminado:** Ver `Etapa de Proceso`.

**Plan de Ejecución**
- **Definición:** El resultado del proceso de `Planificación`. Es una entidad ocurrente y dinámica que describe el conjunto de tareas a ser realizadas de acuerdo a la `Ruta de Proceso`, asignando recursos y tiempos.

**Proceso**
- **Definición:** Ver `Holón de Ruta`. En términos generales, es el conjunto de actividades que transforman entradas en salidas.

**Producto (Holón Producto)**
- **Definición:** La entidad que contiene la "fórmula" y la "ruta" (secuencia de etapas) para obtener un bien. Es el dueño de la información técnica.


---

### R

**Recurso**
- **Definición:** Actores, agentes, equipos, localidades o cualquier entidad necesaria para ejecutar un `Proceso`. Poseen capacidades y conocimiento para cumplir un `Rol` específico.
- **Relaciones:**
    - *Es utilizado por:* `Proceso`.
    - *Provee:* `Servicio`.
    - *Desempeña un:* `Rol`.

**Recurso Proveedor de Servicios de Manufactura (RPSM)**
- **Definición:** En un ecosistema MOS, es una entidad (física, digital o híbrida) que, mediante un proceso específico, ofrece una o más capacidades de manufactura estandarizadas (`Servicios`) requeridas en las etapas de fabricación de un producto.
- **Relaciones:**
    - *Es un tipo de:* `Recurso`.
    - *Provee:* `Servicios de Núcleo`.

**Rol**
- **Definición:** La función específica que un `Recurso` cumple dentro de un `Proceso`. Define las responsabilidades y capacidades esperadas.
- **Relaciones:**
    - *Es desempeñado por:* `Recurso`.
    - *Es requerido por:* `Proceso`.

---

### S

**Servicio**
- **Definición:** Una función estandarizada y modular ofrecida por un `Recurso` que puede ser descubierta, compuesta y orquestada. Actúa como una interfaz que desacopla la capacidad del recurso que la ejecuta.
- **Relaciones:**
    - *Es provisto por:* `Recurso` (especialmente `RPSM`).
    - *Se clasifica en:* `Servicio de Núcleo` y `Servicio de Soporte`.

**Servicios de Núcleo (Core Services)**
- **Definición:** Capacidades que transforman directamente materiales o información en productos (ej. maquinado, soldadura, impresión 3D).
- **Relaciones:**
    - *Son un tipo de:* `Servicio`.
    - *Son ejecutados por:* `RPSM`.

**Servicios de Soporte (Support Services)**
- **Definición:** Servicios que habilitan, optimizan o gestionan los `Servicios de Núcleo` (ej. planificación, mantenimiento, logística, abastecimiento).
- **Relaciones:**
    - *Son un tipo de:* `Servicio`.
    - *Apoyan a:* `Servicios de Núcleo`.
