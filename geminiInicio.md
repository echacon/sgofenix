 1. Arquitectura del Sistema (Unidad Holónica de Producción - HPU)
  El sistema debe implementarse siguiendo una arquitectura de tres capas para cada recurso (Holón Recurso):
   * Capa de Gestión (Nivel MES): Responsable de la negociación de compromisos, gestión de servicios y mantenimiento de
     los Gemelos Digitales. Utiliza un mecanismo de "Llamada a Ofertas" para asignar órdenes de producción basadas en
     costo, tiempo y disponibilidad.
   * Capa de Ejecución (Nivel SCADA): Supervisa el proceso en tiempo real y coordina las interacciones entre holones
     (ej. trasvases de material) mediante "Acuerdos de Coordinación" distribuidos.
   * Capa Física: Interfaz con los equipos, sensores y operarios. El sistema debe ser agnóstico al nivel de
     automatización (desde operarios como sensores hasta integración con PLC).

  2. Modelo de Datos y Entidades Principales
   * Holón Producto: Define la taxonomía del negocio y las Rutas de Producto (secuencia de etapas de transformación).
   * Holón Recurso: Define las capacidades (servicios), costos unitarios y procedimientos internos (Máquinas de
     Estado/Redes de Petri).
   * Token Coloreado (Entidad de Trazabilidad): Cada lote de producción se representa por un token que viaja por el
     sistema acumulando:
       * o: Identificador de la orden/lote.
       * m: Cantidad de material (dinámica según el rendimiento).
       * c: Costo acumulado (ABC).
       * t_arr: Timestamp de llegada/duración.

  3. Lógica de Planificación y Optimización
   * Modelo de Costeo ABC (Activity-Based Costing): El sistema debe calcular el costo de cada etapa considerando:
       * Energía, Mano de Obra y Depreciación (proporcionales al tiempo $\Delta t$).
       * Pérdida de Material: Basada en el rendimiento ($\gamma$) del recurso.
   * Dependencia de Ruta: El algoritmo debe reconocer que las pérdidas en etapas finales exigen mayor producción en
     etapas iniciales, afectando el costo global.
   * Algoritmo de Planificación:
       * Filtros de Factibilidad: Estructural (conectividad de holones) y Temporal (disponibilidad de equipos).
       * Búsqueda Global: Uso de Branch-and-Bound sobre el árbol de alcanzabilidad de las Redes de Petri para encontrar
         la ruta de costo mínimo dentro de un plazo (deadline) fijo.

  4. Metodología de Implementación y Madurez
  El sistema debe permitir una transición gradual en tres niveles:
   1. Nivel 1 (Manual): Generación de planillas (Excel/Papel) para captura de datos manual por operarios.
   2. Nivel 2 (Integrado): Intercambio de documentos con el ERP (Órdenes de Producción, Partes de Producción).
   3. Nivel 3 (FÉNIX): Operación automatizada sobre gemelos digitales, con captura de eventos en tiempo real y
      supervisión distribuida.

  5. Requerimientos Funcionales de Configuración (Elicitación)
  El sistema debe proveer interfaces para cargar el conocimiento extraído en campo:
   * Definición de familias de productos y sus rutas.
   * Modelado de procedimientos internos de recursos (estados: Cargando, Procesando, Lavando, etc.).
   * Configuración de patrones de interacción (trasvases sincronizados, tanques pulmón, co-actividad).

## Implementación
### Modelo de datos

1. Grupo de Clases Persistentes (Continuants - El "Saber Hacer")
  Estas clases definen la estructura estática y las capacidades del sistema antes de que entre la primera orden.

   * Modelo de Producto (ProductHolon):
       * Taxonomia: Familia a la que pertenece (Esmalte, Látex, etc.).
       * RutaMaestra: Grafo de etapas (Red de Petri de nivel superior).
       * BOM (Bill of Materials): Lista de materiales e insumos necesarios.
   * Modelo de Recurso (ResourceHolon):
       * Capacidades: Servicios que ofrece (Dispersión, Molienda, etc.).
       * ParametrosCoste: Tasas fijas ($\kappa$ energía, $\omega$ mano de obra, $\delta$ depreciación).
       * RendimientoNominal ($\gamma$): Porcentaje de eficiencia esperado.
       * ProcedimientoInterno: La Red de Petri de paso (estados como Cargando, Lavando, Procesando).
   * Organización y Recursos Humanos:
       * UnidadNegocio: Departamentos (Ventas, Compras, Producción).
       * RolUsuario: Permisos y capacidades del personal (Operador, Planificador, Jefe de Planta).

  2. Grupo de Clases Ocurrentes (Perdurants - El "Hacer")
  Representan la dinámica del sistema en tiempo real. Son las instancias que "viven" mientras se ejecuta la producción.

   * Orden de Producción (ProductionOrder):
       * Estado actual de la demanda (Solicitada, Cotizada, En Ejecución).
       * Deadline y cantidad final comprometida ($q_n$).
   * Token Coloreado (ProcessToken):
       * o: ID de la Orden.
       * m: Cantidad de material actual (se reduce en cada transición según $\gamma$).
       * c: Costo acumulado (suma de energía, MO, depreciación y material perdido).
       * t_arr: Timestamp de llegada al estado/lugar actual.
   * Plan/Agenda Activa (ActiveSchedule):
       * La ruta óptima seleccionada por el algoritmo Branch-and-Bound.
       * Asignación específica de Recursos a Tareas con ventanas de tiempo.

  3. Grupo de Clases Históricas (La Memoria - El "Aprendizaje")
  Registran lo ocurrido para auditoría, trazabilidad y, crucialmente, para refinar los modelos persistentes.

   * Traza de Ejecución (ExecutionTrace):
       * Registro de eventos (disparo de transiciones).
       * Diferencia entre el tiempo nominal ($\tau$) y el tiempo real ejecutado.
   * Trayectoria del Lote (BatchTrajectory):
       * Historial completo del token: por qué equipos pasó y quiénes fueron los operadores.
       * Costo final real vs. Costo estimado en la planificación.
   * Desempeño de Recurso (ResourcePerformanceLog):
       * Historial de fallos y micro-paradas (indisponibilidad detectada).
       * Datos para actualizar el "Tiempo Aprendido" y el "Rendimiento Real".

 ### Lógica para refinar el comportamiento del token
Lógica para refinar el comportamiento del token en estos dos escenarios críticos:

  1. En la Transición de División (Fork/Split)
  Ocurre cuando una transición genera tokens hacia varios lugares en paralelo (ej. una parte del lote va a control de
  calidad mientras el resto sigue a un pulmón, o el lote se divide en dos máquinas).

   * Atributo Identificador (o): Se hereda idéntico en todos los nuevos tokens.
   * Atributo Masa (m): Debe cumplir la ley de conservación. Si el proceso se divide físicamente, la masa se reparte
     ($m_1 + m_2 = m_{total}$). Si es un proceso de información (ej. sacar una muestra para laboratorio sin detener la
     línea), el token principal mantiene casi toda la masa y el token "hijo" lleva una masa simbólica.
   * Atributo Costo (c): Cada token "hijo" comienza con el costo acumulado hasta ese momento ($c_{inicial}$). Ojo: Este
     es el costo "base". Lo que ocurra en paralelo después se sumará al final.
   * Atributo Tiempo (t_arr): Todos los tokens hijos nacen con el mismo timestamp de salida de la transición.

  2. En la Transición de Unión (Join/Merge)
  Ocurre cuando una transición espera a que llegen tokens de varias ramas paralelas para dispararse (ej. esperar el
  resultado de laboratorio para autorizar el envasado, o reunir dos partes de un lote).

  Aquí es donde se consolida la "historia" de las ramas paralelas:

   * Sincronización Temporal: El t_arr del nuevo token resultante será el máximo de los tiempos de llegada de los tokens
     entrantes ($t_{out} = \max(t_1, t_2, \dots, t_n)$). Esto captura el concepto de "cuello de botella".
   * Agregación de Masa: La masa del token resultante es la suma de las masas de los tokens que llegan ($m_{out} = \sum
     m_i$), menos cualquier pérdida por rendimiento en la transición misma.
   * Consolidación de Costo: Este es el punto clave. El costo acumulado final de la rama paralela debe ser:
      $$c_{final} = c_{base} + \sum (c_i - c_{base})$$
      Es decir, tomamos el costo inicial común y le sumamos los "incrementos" que cada rama generó de forma
  independiente (energía de la máquina A + energía de la máquina B + mano de obra de ambas).

  3. Propuesta para las Clases "Ocurrentes"

  Para implementar esto, la clase ProcessToken (o su gestor de transiciones) podría tener métodos específicos:

    1 class ProcessToken:
    2     def split(self, num_branches, mass_distribution):
    3         # Genera n tokens hijos heredando el costo base c
    4         # Reparte la masa m según la distribución
    5         pass
    6
    7     @staticmethod
    8     def merge(tokens_incoming):
    9         # 1. Verifica que todos los tokens pertenezcan a la misma orden 'o'
   10         # 2. t_arr = max(t.t_arr for t in tokens_incoming)
   11         # 3. m = sum(t.m for t in tokens_incoming)
   12         # 4. c = c_comun + sum(t.c - c_comun for t in tokens_incoming)
   13         pass

  Consideración sobre la "Invariante de Lugar"
  Si el lugar tiene una invariante (ej. "la temperatura debe estar entre 60°C y 80°C"), el sistema histórico/ocurrente
  debe registrar no solo que el token "estuvo" ahí, sino si la invariante se cumplió.
   * Si la invariante se rompe, el costo podría incrementarse (ej. reprocesamiento) o la masa podría perderse (ej. lote
     descartado).
   * Esto conecta tus Clases Ocurrentes con los datos del sensor en tiempo real.

 2.X. Jerarquía de Taxonomía: Abstracción de Productos y Procesos

  La arquitectura de FÉNIX implementa un nivel de Taxonomía que actúa como el puente entre la ontología pura (PPR) y la
  operación real de la planta. El objetivo principal de esta jerarquía es permitir la reutilización de patrones de
  producción y simplificar la configuración masiva de productos mediante la definición de familias.

  2.X.1. El Concepto de Abstracción de Producción
  En lugar de definir una ruta de producción única para cada SKU (Stock Keeping Unit), el sistema utiliza Taxonomías
  para agrupar productos con comportamientos similares. Esto permite que cientos de productos compartan un mismo
  "esqueleto" de procesos, variando únicamente sus parámetros específicos (fórmulas, tiempos, recursos asignados).

  2.X.2. Estructura de Clases de Taxonomía
  Basado en el modelo Taxonomia.py, la jerarquía se organiza en dos ejes principales: el eje del Producto/Proceso y el
  eje del Recurso/Capacidad.

  A. Eje de Producto y Proceso (El "Qué" y el "Cómo")
   1. FamiliaProducto: Es el nivel superior de agrupación (ej. Pinturas Base Agua, Esmaltes Alquídicos). Define el
      contexto de negocio para un grupo de productos.
   2. PatronDeRuta: Es la representación abstracta del proceso de producción para una familia.
       * Implementa una Red de Petri Genérica mediante las clases TransicionPatron, TParcoEnt y TParcoSal.
       * No está amarrado a máquinas específicas, sino a Etapas de Ruta.
   3. EtapaRuta: Representa un nodo de procesamiento en el patrón (ej. Dispersión, Molienda). Cada etapa está vinculada
      a un TipoDeOperacion.

  B. Eje de Recurso y Capacidad (El "Con Qué")
   1. TipoDeOperacion: Define la naturaleza técnica de la actividad (ej. Dispersión de Alta Velocidad, Envasado
      Automático). Es la unidad mínima de "servicio" que el sistema puede planificar.
   2. TipoRecurso: Clasifica el equipamiento físico por categorías funcionales (ej. Dispersores de 500L, Molinos de
      Perlas).
   3. CapacidadTipoOperacion: Es la clase de enlace crítica. Define la relación de costo y rendimiento entre un Tipo de
      Recurso y un Tipo de Operación.
       * eficiencia_estimada: Coeficiente $\gamma$ nominal para la planificación.
       * costo_por_hora: Tasa base para el cálculo del costo ABC a nivel de presupuesto.

  2.X.3. Flujo de Instanciación de una Orden
  Cuando el sistema recibe una solicitud para un producto específico, el motor de planificación sigue este flujo de
  resolución taxonómica:
   1. Identifica la FamiliaProducto del producto.
   2. Carga el PatronDeRuta asociado (Red de Petri abstracta).
   3. Para cada EtapaRuta, busca los Recursos Reales que pertenecen al TipoRecurso capaz de realizar el TipoDeOperacion
      requerido.
   4. Calcula el costo y tiempo final utilizando los valores de CapacidadTipoOperacion si no hay datos históricos, o los
      valores reales si existen.

  2.X.4. Beneficios Arquitectónicos
   * Escalabilidad: La incorporación de nuevos productos solo requiere asociarlos a una familia existente.
   * Mantenibilidad: Un cambio en el proceso de una familia (ej. agregar una etapa de control de calidad) se propaga
     automáticamente a todos los productos de esa taxonomía.
   * Normalización de Datos: La carga mediante la planilla 02_taxonomia.xlsx asegura que la estructura de la planta y
     los tipos de procesos sean coherentes antes de iniciar la producción.
