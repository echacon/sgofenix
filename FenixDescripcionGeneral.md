# Principios de Diseño.

## Antecedentes.

El desarrollo de las actividades de producción en una empresa pequeña industria corresponde a la actividad medular de la organización. Estas actividades deben interactuar con los distintos procesos del negocio con el fin de garantizar la sostenibilidad de la operación en un ambiente competitivo. Clásicamente las PyMEs, incluyendo las PiMIs constan de un organigrama funcional bastante sencillo tal como se muestra a continuación

```
                                       -----------
                                      | Dirección |
                                      |  General  |
                                       -----------
                                            |
            ------------------------------------------------------------------
            |                |               |               |                | 
       ---------        ----------       ---------        ---------       ----------
      | Compras |      |Producción|     |Mercadeo |      |   I&D   |     |Administra|
      |         |      |          |     | Ventas  |      |         |     |   ción   |
      ----------        ----------       ---------        ---------       ----------
                             | 
               -------------------------------
              |              |                |
          ---------        ----------       --------- 
         | Almacén |      | Talleres |     |Manteni | 
         |         |      |          |     | miento |
          ---------        ----------       ---------   
               
```   
                       Figura 1. Organigrama de una PyMI

Las interacciones entre las distintas unidades funcionales: Compras, Producción, Mercadeo, etc. se dan a través de procesos del negocio que siglen reglas para lograr los objetivos de la empresa. Cada unidad tiene unos procedimientos internos que garantizan que la unidad tenga los resultados esperados dentro del proceso del negocio. Las comunicaciones se dan mediante intercambio de mensajes entre las distintas unidades utilizando documentos estandarizados.

La Unidad de Producción desarrolla las actividades medulares de la empresa para satisfacer los objetivos planteados por Mercadeo / Ventas, bajo especificaciones de productos desarrollada por I&D, con materiales y suministros adquiridos por Compras.

Los procesos de producción son disparados por los procesos de producción de acuerdo a uno de los proceso de negocio mostrados a continuación:

```
Empujada

  Mercadeo  genera --> pronóstico de ventas  --->  Producción  construye --->   plan --->  
                                            |                                    |           |  
                                             --> Compras adquiere --> Insumos ---> Almacén --|
          ------------------------------------------------------------------------------------
          |                                          
           --> Talleres ---> Productos a Almacén ---> ventas  ----> Cliente                          
 
 Halada
  
  Cliente solicita ---> producto  --->  Ventas  requiere --->  producción planifica ---  
                                                                                       |
         ------------------------------------------------------------------------------ 
         |
         | ---> Compras adquiere --->  insumos ---
         |                                       |
           -------------------------->   Talleres -----> producto  al cliente 
```
                Figura 2. Flujos entre unidades de acuerdo al Modelo de Negocio

El sistema de planificación de la producción, en ambos casos, es un elemento clave en los procesos del negocio, ya que es el eslabón entre Compras - Mercadeo - Finanzas - Talleres - I&D para obtener el producto al cliente de manera eficiente. Planificación debe conocer la estructura de los productos, sus métodos de producción, la capacidad de la planta, para responder a los modelos de negocio presentes.

## La Unidad de Producción

De acuerdo al organigrama, la Unidad de Producción cumple 4 tipo de funciones:
- La función de gestión. Encargada de asegurar las interacciones con las otras unidades del negocio y la gestión interna de las operciones.
- La función de almacenamiento responsable del manejo de insumos, productos intermedios y productos finales.
- La función de mantenimiento para asegurar la buen calidad de los recursos para tener procesos de producción eficientes.
- La función de producción que transforma los insumos en productos intermedios y productos finales. 

Estas funciones están fuertemente enlazadas y manejan los tres componentes de la producción:
1. El **Recurso** que es el responsable de la ejecución de las *actividades* necesarias para obtener un **Producto**. 
2. El **Proceso** que establece la secuencia de *actividades* necesarias para obtener un **Producto** o avanzar en la consecución del misos en un **Recurso**
3. El **Producto** que tiene el conocimiento del *Procedimiento* necesario para obtener un producto utilizando una serie de *etapas* que se van a desarrollar en un **Recurso**.

Además, el **Recurso** es considerado como un elemento inteligente, que tiene el *conocimiento* para desarrollar el **Proceso**, la *capacidad* para ejecutar la tarea de manera eficiente utilizando sus recursos internos, y la *autonomía* para negociar con otros **Recursos** o con la *Unidad de Gestión* la la posibilidad de participar en una **Orden de Producción**.

Un **Recurso Autónomo** está compuesto por *Operadores*, *Operarios*, *Equipos*, *Sistemas de Control*, *Sistemas Inteligentes* que en conjunto le confieren la *autonomía* al **Recurso Inteligente** u **Holón Recurso**.

Para poder obtener un **Producto**, se deben combinar varios **Recursos** por donde el **Producto** viaja para ir transformándose de un grupo de *Insumos* en un *Producto intermedio* hasta lograr tener el **Producto**. Esta combinación de recursos especificados en el *Procedimiento*, también llamado el *Modelo del Producto*, implica la conformación de un grupo de **Recursos** en un **Recurso Holárquico** que define la **Ruta del Producto**. Esta *ruta* no es única, ya que el *Modelo del Producto* puede ser ejecutado en distintas conformaciones de recursos, que dependen de la disponibilidad de los recursos, del tamaño del *lote* de **Producto** esperado. La planificación de la producción resulta en la definición de una *Ruta de Producto* para una **Orden de Producción**. El grupo de recursos se maneja como un **Holón Recurso** compuesto.


En la Figura siguiente (2)  se muestra la organización de un grupo de Holones para satisfacer una orden de producción.


```
                            -----------------
                           |     Holón       |
                           |   Compuesto     |
                            -----------------
                                   |
                ------------------------------------------
               |                                          |
      ---------------                            ---------------
     |    Holón      |                          |    Holón      |
     |   Recurso     |    <-- Negociación -->   |   Recurso     |
     | ------------- |                          | ------------- |
     |  Supervisor   |   <-- Coordinación -->   |  Supervisor   |
     | ------------- |                          | ------------- |
     |    Proceso    |  <--Flujo Productos-->   |    Proceso    |
     |    Físico     |                          |    Físico     |
      ---------------                            ---------------
```
                   Figura 3. El Recurso Holónico

El procedimiento es el siguiente:
1. La Unidad de Producción recibe un requerimiento de producción.
2. La Unidad de Producción verifica que tiene el conocimiento para hacerlo, si no lo tiene rechaza el requerimiento.
3. Selecciona dentro de los recursos aquellos que tienen las competencias para desarrollar el producto de acuerdo al modelo del producto.
4. Solicita a las diferentes recursos su disponibilidad para realizar las operaciones necesarias (prestar el servicio de manufactura).
5. Crea modelos compuestos para las diferentes combinaciones y simula la producción en cada compbinación.
6. Seleciona las alternativas viables de acuerdo al requerimiento de producción y las entrega al que hizo la solicitud.
7. Se recibe la aceptación de una o más de las alternativas.
8. Se genera la orden de producción con su esquema de seguimiento. Holón Compuesto y la trayectoria esperada.
9. Los recursos comienzan su producción de acuerdo a su conocimiento internos y aseguran que se efectúe la coordinación entre ellos.
10. Periódicamente los recursos envían el avance de la orden y el holón compuesto la monitorea.
11. Al finalizar la orden se evalúa el rendimiento de lo obtenido respecto a lo pllanificado.
12. Se ajustan los modelos de acuerdo al histórico de las órdenes ejecutadas.

### Partes del Holón Recurso
De la Figura 3, el Holón Recurso tiene 3 niveles, el nivel de conciencia que maneja el conocimiento de los modelos del producto, tiene la capacidad de negociación para establecer objetivos y la cooperación con otros holones para cumplir con un objetivo de producción. El nivel supervisor, donde se dan los mecanismos para ejecutar la coordinación de las tareas físicas necesarias para lograr el servicio de manufactura comprometido. El supervisor puede ser humano, un sistema o una mezcla humanos sistemas que aseguren el cumoplimiento de las tareas, y el nivel del proceso físico donde se realizan la transformación de los insumos en un producto, su traslado y almacenamiento.

#### Proceso físico (Nivel 0)

  El procesos físico puede ser manual o automático y va a ser realizado en un conjunto de pasos que pueden ser paralelos, tal como se muestra en la Figura 4.

```

                                  ---------       
                            | ---> paso 2    ---> |
     |       ----------     |     ---------       |       ---------     |
 --->| --->   paso 1   ---->|                     | --->  paso  i   --->|--->
     |       ----------     |     ---------       |       ---------     |
                            | ---> paso 3    ---> |
                                  ---------
  evento, puede ser nulo                                         evento final

```
                        Figura 4. Evolución de un procesos

En un paso existe un conjunto de valores que se manienen dentro de ciertos límites, tales como velocidad, temperatura, etc. o que siguen unas leyes físicas asociadas a las condiciones de operación. La salida de esos valores de los límites puede generar un evento que haga evolucionar el proceso hacia otro paso.

La medición de estos valores permite  controlar el proceso en sistemas automáticos o semi-automáticos, evaluar el comportamiento del mismo, elaborar indicadores.


#### El Sistema Supervisor (Nivel 1)

El nivel supervisor determina si la evolución del nivel físico es la esperada, se determinan los ajustes necesarios y se decide cuando un paso ha sido completado para pasar al siguiente. En la ejecución conjunta de un proceso complejo entre varios recursos, asegura la coordinación entre los procesos, el intercambio de productos entre dos **Recursos**. El *Sistema Supervisor* puede ser automático, realizado por el operador con el apoyo de la tecnolgía de operaciones, o totalmente manual.

```
     Orden de
     Trabajo                        Resultados
      |           --------------        |
      |          |              |       |
      ---------> |              |  ---->
                 |  Supervisor  |
        -------> |              | ----->
       |         |              |       |
       |         ---------------        |
       |                                |
       |                                |
       |         ---------------        |
       |        |              |        |
        <------ |    Proceso   | <------
                |    Físico    |
                 --------------

```

   Figura 5. Interacción en las capas inferiores del Holón

#### El nivel de conciencia del Holón Recurso

El nivel de conciencia comporta la parte ciber del **Holón Recurso**. El Holón Recurso guarda el conocimiento de como realizar la ejjecución física del proceso, su control y las interacciones con otros recursos para la realización de las tareas. Desde el punto de vista de gestión, titne conciencia de su estado, de los compromisos mediante una agenda donde está la lista de compromisos pendientes, es capaz de negociar con otros holones recurso la posibilidad de realizar una tarea.

El nivel de conciencia está formado por los siguientes elementos:
1. La Arquitectura Física: Conjunto de operarios, dispositivos que forman parte del Holón Recurso (Recursos propios), con sus funciones, la arquitectura de Tecnología de Operaciones.
2. Los modelos de comportamiento para las distintas operaciones de manufactura que puede realizar el recurso. Los modelos se usan para estimar el comportamiento futuro del sistema para una Orden de Trabajo (parte de la Orden de Producción), el sistema de seguimiento que permite tener la imagen de los que ocurre en los dos primeros niveles del **Holón Recurso**
3. El sistema de negociación, con la agenda, que permite al **Holón Recurso** establecer compromisos.
4. El sistema de interacción con las otras unidades para los procesos del negocio.



## Arquitectura de Implantación (Unidad Holónica de Producción - HPU)

  El sistema debe implementarse siguiendo una arquitectura de tres capas para cada recurso (Holón Recurso):
   * Capa de Gestión (Nivel MES): Responsable de la negociación de compromisos, gestión de servicios y mantenimiento de
     los Gemelos Digitales. Utiliza un mecanismo de "Llamada a Ofertas" para asignar órdenes de producción basadas en
     costo, tiempo y disponibilidad.
   * Capa de Ejecución (Nivel SCADA): Supervisa el proceso en tiempo real y coordina las interacciones entre holones
     (ej. trasvases de material) mediante "Acuerdos de Coordinación" distribuidos.
   * Capa Física: Interfaz con los equipos, sensores y operarios. El sistema debe ser agnóstico al nivel de
     automatización (desde operarios como sensores hasta integración con PLC).

###  Modelo de Datos y Entidades Principales
   * Holón Producto: Define la taxonomía del negocio y las Rutas de Producto (secuencia de etapas de transformación).
   * Holón Recurso: Define las capacidades (servicios), costos unitarios y procedimientos internos (Máquinas de
     Estado/Redes de Petri).
   * Token Coloreado (Entidad de Trazabilidad): Cada lote de producción se representa por un token que viaja por el
     sistema acumulando:
       * o: Identificador de la orden/lote.
       * m: Cantidad de material (dinámica según el rendimiento).
       * c: Costo acumulado (ABC).
       * t_arr: Timestamp de llegada/duración.

### Lógica de Planificación y Optimización
   * Modelo de Costeo ABC (Activity-Based Costing): El sistema debe calcular el costo de cada etapa considerando:
       * Energía, Mano de Obra y Depreciación (proporcionales al tiempo $\Delta t$).
       * Pérdida de Material: Basada en el rendimiento ($\gamma$) del recurso.
   * Dependencia de Ruta: El algoritmo debe reconocer que las pérdidas en etapas finales exigen mayor producción en
     etapas iniciales, afectando el costo global.
   * Algoritmo de Planificación:
       * Filtros de Factibilidad: Estructural (conectividad de holones) y Temporal (disponibilidad de equipos).
       * Búsqueda Global: Uso de Branch-and-Bound sobre el árbol de alcanzabilidad de las Redes de Petri para encontrar
         la ruta de costo mínimo dentro de un plazo (deadline) fijo.

### Metodología de Implementación y Madurez
  El sistema debe permitir una transición gradual en tres niveles:
   1. Nivel 1 (Manual): Generación de planillas (Excel/Papel) para captura de datos manual por operarios.
   2. Nivel 2 (Integrado): Intercambio de documentos con el ERP (Órdenes de Producción, Partes de Producción).
   3. Nivel 3 (FÉNIX): Operación automatizada sobre gemelos digitales, con captura de eventos en tiempo real y
      supervisión distribuida.

### Requerimientos Funcionales de Configuración (Elicitación)
  El sistema debe proveer interfaces para cargar el conocimiento extraído en campo:
   * Definición de familias de productos y sus rutas.
   * Modelado de procedimientos internos de recursos (estados: Cargando, Procesando, Lavando, etc.).
   * Configuración de patrones de interacción (trasvases sincronizados, tanques pulmón, co-actividad).






 

