# Manual de Usuario: Gestión y Operación del Sistema MOM

## 0. Filosofía del Sistema (FÉNIX)

FÉNIX es un sistema de seguimiento y gestión de producción (MOM) basado en **Redes de Petri Coloreadas** y una **arquitectura holónica**. Su diseño marca una evolución desde los viejos esquemas de control rígido y centralizado (como los utilizados en la automatización tradicional de grandes refinerías e industrias como PDVSA) hacia una red ágil de unidades autónomas y colaborativas. Su nombre evoca la capacidad de **reiniciar desde cualquier punto** sin pérdida de información, como el ave fénix que renace de sus cenizas. Para conocer los fundamentos filosóficos e históricos que sustentan el sistema, te sugerimos leer la [Filosofía de Integración Holónica](file:///C:/Users/echac/Documents/gemini/Filosofia_Integracion_Holonica.md).

### Principio Fundamental
> **"Cada lote de producción es un token que viaja por el sistema acumulando trazabilidad (cantidad, costo, tiempo). Cada recurso es un holón que sabe qué hacer y con quién coordinarse."**

### Los Tres Pilares del Conocimiento
1.  **Saber Hacer (Estático):** Sus familias de productos, rutas y máquinas.
2.  **El Hacer (Dinámico):** Sus órdenes de producción actuales y los eventos en tiempo real.
3.  **El Aprender (Histórico):** El registro de todo lo que pasó para mejorar el futuro.

## 1. Bienvenido al Sistema MOM para su Fábrica
Este manual le guiará en el proceso de digitalizar su producción. El objetivo principal es que usted tenga el control total de qué se fabrica, cómo se fabrica y, lo más importante, **cuánto le cuesta realmente producir**.

## 2. Los tres pilares de su fábrica: El Enfoque de "Moldes y Piezas"
Para que el sistema sea fácil de usar y crezca con usted, primero definimos los "moldes" (Taxonomía) y luego las "piezas" reales (sus Productos y Recursos).

*   **Pilar 1: Familias y Plantillas (La Taxonomía):** Definimos categorías generales. Por ejemplo, la familia "Sillas", el tipo de recurso "Torno Manual" o el proceso "Lijado Estándar". Esto sirve como un molde que ahorra tiempo al crear nuevos elementos.
*   **Pilar 2: Sus Productos (Qué fabrica):** Utilizando los moldes de las familias, detallamos cada producto real (ej: Silla de Roble Modelo A). Aquí definimos su "receta" técnica (Materiales y Pasos).
*   **Pilar 3: Sus Recursos (Con qué fabrica):** Mapeamos sus máquinas y operarios reales (ej: Torno #1, Juan Pérez) a los moldes de recursos. Aquí configuramos qué tan rápido trabajan y cómo se conectan entre sí en la planta.

## 3. ¿Cómo y por qué organizamos la información? (Excel vs. YAML)

Para que FÉNIX actúe como el GPS de su fábrica y calcule las mejores rutas de producción, necesita entender su planta de forma ordenada. Para ello, utilizamos un **enfoque híbrido** que hace la configuración simple y sin complicaciones:

1. **Excel es para sus Datos Tabulares (Listas):** Escribir listas de ingredientes (BOM), nombres de productos, costos de energía y tarifas por hora de operarios es muy fácil en Excel. FÉNIX utiliza estas planillas para almacenar toda su información estática.
2. **YAML es para su Lógica de Secuencia (El Guion):** Explicar en un Excel qué máquina debe esperar a cuál (handshakes) o qué botones debe presionar el operario (triggers) es sumamente enredado. En su lugar, usamos un archivo de texto simple (**YAML**), que actúa como el "guion de una sinfonía" donde se define la coreografía de la planta.

### ¿Qué gano con esta organización?
* **Planificación Automática:** El sistema busca en su YAML qué pasos se necesitan y en su Excel qué máquinas están libres para armar el plan ideal.
* **Seguimiento sin pérdidas:** Cada lote se representa como un "token digital" que viaja por el flujo que usted definió en el YAML, permitiéndole ver el estado exacto en su tablet o pantalla.
* **Costeo Real ABC:** Al asociar las máquinas y tiempos del YAML con los costos por hora del Excel, FÉNIX le da el costo real de cada lote (incluyendo mermas) al terminar la producción.

## 4. Configuración Inicial: El Camino al Éxito
La configuración se realiza paso a paso utilizando nuestras plantillas de Excel inteligentes. Siga este orden para asegurar que todo encaje perfectamente:

### 4.1. Paso 1: Definiendo los "Moldes" (Taxonomía)
Antes de cargar 100 productos, defina sus 5 familias principales. Complete la plantilla de **Taxonomía**:
*   **Familias de Producto:** Clasifique por tipo (Maderas, Metales, Plásticos).
*   **Tipos de Recurso:** Agrupe sus máquinas (Manuales, CNC, Ensamblado).
*   **Operaciones Maestras:** Defina cómo se hace un "Corte" o un "Pintado" de forma general.

### 4.2. Paso 2: Creando sus Productos
Ahora, asigne cada producto a su familia y complete los detalles específicos:
*   **Receta de Materiales (BOM):** ¿Qué ingredientes usa este producto específico?
*   **Ruta de Proceso (BOP):** ¿Qué pasos sigue? El sistema le sugerirá los pasos basados en la familia que eligió en el Paso 1.

### 4.3. Paso 3: Configurando su Planta (Recursos y Conectividad)
Finalmente, detalle sus máquinas y operarios reales:
*   **Capacidades:** ¿Cuántas horas al día están disponibles? ¿Qué tan rápido son comparados con el estándar?
*   **Mapa de Movimiento (Conectividad):** Dígale al sistema qué máquina está al lado de cuál. Esto ayuda al sistema a calcular cuánto tiempo se pierde moviendo material de un lado a otro.

## 5. El Ciclo de Operación Diaria: De la Orden a la Entrega
Una vez configurado el sistema, el trabajo diario es fluido y automático. El sistema se encarga de que nada se detenga.

### Paso 1: El "Guion de la Sinfonía" (Su proceso en YAML)
En FÉNIX, no dibujamos flujos complicados. Escribimos un **Guion** (en formato YAML) que le dice al sistema cómo deben coordinarse sus máquinas. 

Imagine el proceso del Látex Blanco como una sinfonía:

```yaml
# Guion simplificado para Látex
proceso:
  estaciones:
    - dispersor_espera
    - dispersor_mezclando
    - diluidor_espera

  acciones:
    iniciar_mezcla:
      cuando: [dispersor_espera]
      mueve_a: [dispersor_mezclando]
      tipo: "Manual" # El operario presiona un botón

    unir_con_diluidor:
      cuando: [dispersor_mezclando, diluidor_espera]
      mueve_a: [diluidor_recibiendo]
      tipo: "Sincronizado" # Ambos deben estar listos
```

Este guion es lo que el sistema usa para encender las luces en su panel de control. Si el guion dice que se necesitan dos estaciones listas, el sistema esperará automáticamente por ambas.

### Paso 2: El Reporte en Planta (Interfaz Web)
Sus operarios no ven el código YAML. Ellos ven una interfaz limpia con botones que corresponden a las **acciones** definidas en el guion.
*   **Botón de Acción:** Al presionar "Iniciar Mezcla", el sistema mueve el lote digitalmente.
*   **Alertas de Sincronización:** Si un operario intenta mover material pero la siguiente estación no está lista (según el guion), el sistema le avisará: *"Esperando al Diluidor"*.

### Paso 3: Monitoreo en Tiempo Real y Cuellos de Botella
En su panel de control, usted verá el mapa de su fábrica con luces:
*   **Verde:** La tarea está fluyendo según lo planeado.
*   **Amarillo:** La tarea está esperando en una estación (posible cuello de botella).
*   **Rojo:** La tarea se ha detenido por un problema de máquina o calidad.

## 6. Mejora Continua: El sistema que aprende de usted
Al final de cada semana, el sistema le propondrá **Ajustes de Modelo**. Si una tarea siempre toma más tiempo del que usted escribió en el Excel, el sistema le pedirá permiso para actualizar su "receta" original. Así, sus planes futuros serán cada vez más exactos.

---

---

## 7. Caso de Estudio: El Ciclo Completo en "Pinturas El Fénix"

Para visualizar cómo funciona el sistema, veamos el ciclo de una orden de **1.000 kg de Pintura Látex Blanco**.

1.  **Configuración:** Usted cargó en su Excel que para hacer esta pintura se necesita pasar por el **Dispersor_22** y luego por el **Diluidor_01**.
2.  **La Orden:** Usted recibe el pedido y presiona "Aprobar". El sistema crea la orden `ORD-2025-001`.
3.  **El Inicio:** El operario en el Dispersor ve la tarea en su tablet, carga los pigmentos y presiona **"Iniciar"**. Usted ve una luz verde en su panel.
4.  **La Coordinación:** Cuando el Dispersor termina, el sistema le pregunta automáticamente al Diluidor si está libre. Si lo está, el operario recibe la señal de **"Trasvasar"**.
5.  **El Cierre:** Al terminar el envasado, el sistema detecta que se obtuvieron **970 kg** (hubo 3% de pérdida) y que el proceso tomó **15 minutos más** de lo previsto.
6.  **El Aprendizaje:** El sistema le enviará una notificación: *"He notado que en el Dispersor_22 siempre perdemos 30 kg. ¿Desea que ajuste sus recetas automáticamente para el futuro?"*.

Al aceptar, su fábrica se vuelve más inteligente y sus costos más reales.

---

### Consejos para el Éxito:
1.  **Sea preciso con los desperdicios:** Reportar el material que sobra ayuda al sistema a calcular mejor sus próximas compras.
2.  **Revise sus costos:** Si el precio de la energía o los materiales sube, actualice su plantilla Excel para que el sistema recalcule su rentabilidad.
