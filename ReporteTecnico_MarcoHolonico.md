# Framework Holónico Producto-Proceso-Recurso con Redes de Petri Temporizadas para la Programación Costo-Óptima de la Producción y el Monitoreo en Lazo Cerrado en PyMEs
## Monografía Técnica y Guía Académica del Sistema FÉNIX

**Autores:**  
- **Dr. Edgar Chacón** (echacon@ula.ve)  
- **Dr. Juan Cardillo**  
*Departamento de Computación / Departamento de Control 

Facultad de Ingeniería, Universidad de Los Andes, Mérida, Venezuela*

---

## Resumen Ejecutivo

Las pequeñas y medianas empresas (PyMEs) industriales enfrentan un desafío estructural: la necesidad de programar y costear sus procesos productivos con precisión matemática en entornos con recursos compartidos, operando bajo severas restricciones financieras que impiden la adopción de costosos sistemas comerciales MES/APS. 

Este documento técnico presenta de manera exhaustiva el **Framework Holónico Producto-Proceso-Recurso (PPR)**, una arquitectura formal en la cual las **Redes de Petri Temporizadas con Lugares con Costo (AB-TPPN)** constituyen el lenguaje semántico ejecutable que modela, planifica y supervisa la manufactura. A diferencia de los enfoques tradicionales que separan la secuencia del recurso, cada Holón Recurso encapsula las especificaciones completas de sus servicios (secuencias, rendimiento másico $\gamma$ y tasas de costo por actividad $\mathbf{c}$). 

La programación se formula mediante una búsqueda *Branch-and-Bound* costo-óptima sobre el árbol de alcanzabilidad, incorporando un modelo de token multi-etapa con acumulación rigurosa de costos y absorción de mermas. El marco integra un lazo dual telemétrico (SCADA/Edge) con calibración estadística EWMA y el Ratio de Desviación Energética (EDR) para monitoreo de salud de activos. Se presenta la validación experimental sobre 10.089 órdenes de producción de una PyME de pinturas y una guía pedagógica para la enseñanza de manufactura inteligente en programas universitarios de ingeniería.

---

## 1. Introducción y Motivación

Las decisiones de programación de producción en las pequeñas y medianas empresas (PyMEs) manufactureras suelen tomarse bajo condiciones de alta incertidumbre, recursos limitados y ausencia de herramientas formales de soporte. Mientras que las grandes corporaciones resuelven este problema mediante sistemas integrados de ejecución de manufactura (MES) y herramientas de planificación avanzada (APS) con costos de licenciamiento e implantación prohibitivos, las PyMEs recurren a métodos empíricos o heurísticos en hojas de cálculo.

Esta brecha tecnológica genera decisiones de asignación que, aunque parezcan razonables a nivel local, son globalmente ineficientes. En procesos por lotes (*batch*), los costos reales de producción dependen fuertemente de la ruta seleccionada, debido a diferencias en el rendimiento másico ($\gamma$), consumo de potencia eléctrica, tasas de depreciación y tiempos de alistamiento entre máquinas alternativas. Cuando estos factores no se modelan formalmente, las cotizaciones a clientes y las fechas de entrega comprometidas divergen sistemáticamente de la realidad operativa.

Para superar este dilema, el marco de trabajo del sistema **FÉNIX** se fundamenta en cuatro pilares complementarios:
1. **Organización Holónica PPR:** Encapsulación del conocimiento de procesos dentro del propio Holón Recurso, unificando la jerarquía de planta y simplificando la mantenibilidad.
2. **Redes de Petri Temporizadas con Lugares con Costo (AB-TPPN):** Utilización de un formalismo matemático unificado que sirve simultáneamente como modelo semántico, motor de búsqueda para el optimizador y registro de ejecución para la supervisión.
3. **Costeo Basado en Actividades como Objetivo de Optimización:** Inversión de la función objetivo clásica (minimización de *makespan*) hacia la minimización del **costo económico integral**, garantizando el cumplimiento de plazos estrictos ($d$) y la viabilidad comercial ($V_{\text{target}}$).
4. **Lazo Cerrado Telemétrico Dual (SCADA/Edge):** Integración con telemetría no invasiva de bajo costo para absorber contingencias locales en tiempo real y calibrar los modelos mediante filtros EWMA y monitores energéticos EDR.

---

## 2. Fundamentos Conceptuales y Estado del Arte

### 2.1 Sistemas de Manufactura Holónica (HMS) frente a la Pirámide Clásica
El paradigma holónico, concebido originalmente por Koestler y adaptado a la ingeniería de manufactura en la arquitectura PROSA, propone descomponer la complejidad industrial en unidades autónomas y cooperativas denominadas *holones*. Un holón es simultáneamente una parte de un sistema mayor y un todo auto-contenido.

En la arquitectura clásica basada en la pirámide ISA-95, el conocimiento está fragmentado en capas rígidas: el control en PLCs (Nivel 1), la supervisión en SCADA (Nivel 2), la programación en MES (Nivel 3) y la gestión comercial en ERP (Nivel 4). En contraste, el framework FÉNIX adopta una tríada holónica:
- **Holón Recurso ($R$):** Representa los activos físicos (máquinas, reactores, operadores, cuadrillas, líneas) y encapsula los métodos y costos con los que realiza sus operaciones.
- **Holón Producto ($P$):** Encarna el lote en transformación, portando su receta, estado de avance, balance másico y acumulación de costos.
- **Holón Proceso ($\Pi$):** Define la taxonomía y las relaciones de precedencia operacional para una familia de productos.

### 2.2 Redes de Petri Temporizadas en Manufactura: El Enfoque P-TPN frente a T-TPN y la Brecha en la Literatura

Las Redes de Petri constituyen un formalismo gráfico y algebraico de referencia para modelar sistemas a eventos discretos con concurrencia, sincronización y recursos compartidos. No obstante, al analizar la literatura especializada sobre Redes de Petri Temporizadas (TPN), destaca una notable asimetría: la inmensa mayoría de publicaciones y herramientas de software se concentran en las redes con **Transiciones Temporizadas (T-TPN)**, mientras que las redes con **Lugares Temporizados (P-TPN / TPPN)** presentan una documentación comparativamente escasa, especialmente en aplicaciones de programación y costeo.

Esta brecha en la literatura obedece a factores teóricos, metodológicos e históricos bien identificados:

1. **La equivalencia teórica canónica:** Trabajos fundacionales (Sifakis, 1979) demostraron que cualquier red con lugares temporizados puede reescribirse formalmente como una red con transiciones temporizadas mediante la inserción de una transición retardada intermedia. Esta equivalencia algebraica condujo a la comunidad teórica de ciencias de la computación a considerar las P-TPN como un caso redundante, orientando el desarrollo de herramientas de software clásicas (*TINA, GreatSPN, CPN Tools, TimeNet*) casi exclusivamente hacia motores basados en transiciones temporizadas.
2. **El divorcio entre Investigación de Operaciones (OR) y Sistemas a Eventos Discretos (DES):** La comunidad de *Operations Research* y programación de producción (*scheduling*) abordó históricamente los problemas de asignación mediante Programación Entera Mixta (MIP), Programación por Restricciones (CP) y grafos disyuntivos, considerando a las Redes de Petri un formalismo excesivamente complejo para optimización combinatoria. Por su parte, la comunidad de control de eventos discretos utilizó las Redes de Petri principalmente para la verificación formal de propiedades estructurales (prevención de bloqueos o *deadlocks*, vivacidad y acotamiento), desatendiendo la formulación de motores de búsqueda de rutas óptimas basadas en costos.
3. **El sesgo histórico hacia la minimización de *Makespan*:** En los escasos estudios de programación con Redes de Petri, la función objetivo estándar ha sido la minimización del tiempo total de terminación (*makespan*, $C_{\max}$) o la maximización del rendimiento (*throughput*). Bajo un objetivo puramente temporal, la distinción entre temporizar el lugar o la transición carece de impacto económico. Sin embargo, cuando se busca modelar el **Costeo Basado en Actividades (ABC)**, la física del sistema exige que el costo se acumule mientras el producto habita el recurso en un **Lugar de Procesamiento** ($P^{\text{proc}}$), volviendo indispensable la semántica de lugares temporizados.
4. **La semántica de tokens con historia y atributos multidimensionales:** En una T-TPN estándar, el marcado de un lugar es un escalar $M(p) \in \mathbb{N}$. En contraste, en una P-TPN aplicada a manufactura por lotes, cada token en un lugar temporizado porta atributos individuales (tiempo de arribo $t_{\text{arr}}$, masa remanente $m$ y vector de costos acumulados $\mathbf{c}$). La red se convierte en un sistema donde los estados son multiconjuntos de tuplas con historia, lo cual exige el desarrollo de motores de resolución específicos.

Por consiguiente, el modelo **AB-TPPN** adoptado en FÉNIX reivindica la intuición física natural de los lugares temporizados: las transiciones modelan eventos instantáneos ($\Delta t = 0$, inicio o fin de fase), mientras que los lugares modelan estados físicos continuos de transformación, acumulación de costos y retención de recursos.

---

## 3. El Framework Holónico PPR y el Formalismo AB-TPPN

### 3.1 Estructura del Holón Recurso y Subred de Paso
Cada recurso industrial $R \in \mathcal{R}$ declara un conjunto de servicios $\mathcal{S}_R$. Para cada servicio $s \in \mathcal{S}_R$, el comportamiento dinámico se especifica formalmente mediante una **subred de paso** $\mathcal{N}_S(R) = (P, T, F, W, \tau, \mathbf{c}, \gamma)$, donde:
- $P = P^{\text{proc}} \cup P^{\text{res}} \cup P^{\text{mat}}$ es el conjunto particionado de lugares:
  - $P^{\text{proc}}$: Lugares de procesamiento y transformación (`Cargando`, `Dispersando`, `Moliendo`, `Diluyendo`).
  - $P^{\text{res}}$: Lugares de disponibilidad del recurso físico y operario (`Disponible`, `En Mantenimiento`).
  - $P^{\text{mat}}$: Lugares de insumos, materias primas y amortiguamiento (WIP).
- $T$: Conjunto de transiciones que representan eventos de inicio, cambio de fase o finalización.
- $F \subseteq (P \times T) \cup (T \times P)$: Arcos dirigidos de flujo.
- $\tau: P^{\text{proc}} \to \mathbb{R}^+$: Duración determinista o nominal del estado.
- $\mathbf{c}: P^{\text{proc}} \to \mathbb{R}^4$: Vector de tasas de costo por unidad de tiempo:
  $$\mathbf{c}(p) = \Big( \kappa_R^{\text{elec}},\; \kappa_R^{\text{dep}},\; \omega_R^{\text{lab}},\; \delta_R^{\text{ind}} \Big)$$
  representando costo eléctrico/energético, depreciación horaria de maquinaria, mano de obra directa y costos indirectos de gestión.
- $\gamma \in (0, 1]$: Factor de rendimiento másico efectivo del paso en el equipo.

### 3.2 Modelo del Token Multi-Etapa: Dinámica de Masa y Costos

#### Definición del Token de Lote
El token en la etapa $j$ se define por la tupla:
$$\mathbf{k}_j = \Big( m_j,\; C_j,\; \mathbf{c}_j^{\text{hist}},\; t_j^{\text{arr}} \Big)$$
donde $m_j$ es la masa actual del lote (kg), $C_j$ es el costo acumulado total (UM), $\mathbf{c}_j^{\text{hist}}$ es el desglose vectorial de costos y $t_j^{\text{arr}}$ es la estampa de tiempo de arribo.

#### Balance de Masa con Absorción de Rendimiento ($\gamma$)
Si en la etapa $j$ se procesa en el recurso $R_i$ con adición de materias primas $\Delta m_j$ y rendimiento $\gamma_{R_i}$:
$$m_{j+1} = (m_j + \Delta m_j) \cdot \gamma_{R_i}$$
La masa de merma o residuo retenido en máquina viene dada por $m_{\text{loss}} = (m_j + \Delta m_j)(1 - \gamma_{R_i})$. Esta pérdida física incrementa el costo unitario efectivo del producto resultante, reflejando el principio de que el producto en proceso absorbe el costo de los recursos utilizados y las pérdidas incurridas en etapas previas.

#### Ecuación de Acumulación Económica
El costo total acumulado al egresar de la etapa $j$ se expresa como:
$$C_{j+1} = C_j + \sum_{k \in \text{insumos}} \phi_k \cdot q_k + \Big( \kappa_{R_i}^{\text{elec}} + \kappa_{R_i}^{\text{dep}} + \omega_{R_i}^{\text{lab}} + \delta_{R_i}^{\text{ind}} \Big) \cdot \tau_j(R_i, m_j)$$
donde $\phi_k$ es el costo unitario de la materia prima $k$ y $q_k$ la cantidad dosificada.

---

## 4. Algoritmo de Programación Costo-Óptima (Branch-and-Bound)

El motor de planificación de FÉNIX resuelve la asignación de recursos y la temporización de operaciones mediante una búsqueda en árbol de alcanzabilidad optimizada por *Branch-and-Bound*.

### 4.1 Formulación del Problema
Dada una orden de producción $\mathcal{O} = (P_{\text{type}}, M_{\text{target}}, d, V_{\text{target}})$, donde $P_{\text{type}}$ es la familia de producto, $M_{\text{target}}$ la masa final requerida, $d$ la fecha límite de entrega (*deadline*) y $V_{\text{target}}$ el valor comercial máximo aceptable de costo:
$$\min_{\sigma \in \Sigma(\mathcal{O})} \quad C_{\text{total}}(\sigma)$$
sujeto a:
1. $t_{\text{fin}}(\sigma) \le d$ (Restricción de plazo estricto)
2. $C_{\text{total}}(\sigma) \le V_{\text{target}}$ (Restricción de viabilidad económica)
3. $\Psi_R \cap [t_{\text{start}}(R), t_{\text{end}}(R)] = \emptyset, \quad \forall R \in \sigma$ (No solapamiento de recursos)

### 4.2 Función de Cota y Reglas de Poda
Para cada nodo $\nu$ en el árbol de búsqueda:
$$f(\nu) = g(\nu) + h(\nu)$$
- $g(\nu)$: Costo real acumulado en las etapas completadas $1 \dots k$.
- $h(\nu)$: Cota inferior admisible del costo de las etapas remanentes $k+1 \dots n$, calculada asumiendo los recursos más económicos y con rendimiento ideal ($\gamma = 1$).

#### Reglas de Poda:
1. **Poda por Plazo:** $t_{\text{earliest}}(\nu) + \sum_{j=k+1}^n \tau_j^{\min} > d$.
2. **Poda por Costo Objetivo:** $g(\nu) + h(\nu) > V_{\text{target}}$.
3. **Poda por Dominancia:** $f(\nu) \ge C_{\text{best}}$, donde $C_{\text{best}}$ es la mejor solución completa encontrada.

---

## 5. Telemetría SCADA, Lazo Dual y Calibración Continua

### 5.1 Lazo Rápido / Reactivo (Segundos a Minutos)
Monitorea eventos críticos instantáneos: alarmas de maquinaria (`FAIL`), violaciones de límites físico-químicos ($T > 55^\circ\text{C}$) o rechazos en compuertas de calidad ($H_{\text{med}} < 7$). Ante una contingencia, evalúa la holgura temporal remanente:
$$\Delta_{\text{slack}} = d - \left( t_{\text{actual}} + \tau_{\text{ajuste}} + \sum_{j \in \text{pendientes}} \tau_j(R_j) \right)$$
Si $\Delta_{\text{slack}} \ge 0$, la perturbación se absorbe localmente dentro de la subred $\mathcal{N}_S(R)$ sin afectar las reservas de las demás máquinas.

### 5.2 Lazo Táctico / Predictivo (Lotes a Semanas)
Procesa los registros históricos integrados para mantener la fidelidad de los modelos:
- **Calibración EWMA:** Actualización periódica de tiempos nominales ($\bar{\tau}$) y consumo específico de potencia ($\bar{\kappa}$) tras cada lote con factor $\lambda \in [0.10, 0.25]$:
  $$\bar{\tau}^{(k)} = \lambda \cdot \tau_{\text{medido}}^{(k)} + (1 - \lambda) \cdot \bar{\tau}^{(k-1)} \quad \text{(Eq. 11)}$$
  $$\bar{\kappa}^{(k)} = \lambda \cdot \kappa_{\text{medido}}^{(k)} + (1 - \lambda) \cdot \bar{\kappa}^{(k-1)} \quad \text{(Eq. 12)}$$
- **Ratio de Desviación Energética (EDR):**
  $$\text{EDR}(R) = \frac{E_{\text{real}}(R)}{E_{\text{nominal}}(R)} = \frac{\int_0^{\Delta t} P_R(t)\,dt}{\kappa_R \cdot \Delta t} \quad \text{(Eq. 13)}$$
  Un valor de $\text{EDR} > 1.15$ denota desgaste mecánico severo, incrementando la tarifa efectiva $\kappa_R^{\text{eff}} = \text{EDR}(R) \cdot \bar{\kappa}_R$ en el planificador para desviar progresivamente la carga hacia equipos sanos.

---

## 6. Especificación en YAML y Validación Experimental

### 6.1 Interfaz Declarativa en YAML
```yaml
recurso:
  id: DIS-A
  nombre: "Dispersor Cowles 50 HP"
  tipo: TransformacionFisica
  capacidades:
    volumen_max_litros: 2500
    potencia_kw: 37.0
  tasas_costo:
    costo_kwh_usd: 0.18
    depreciacion_hora_usd: 4.50
    mano_obra_hora_usd: 8.00
    indirectos_hora_usd: 2.00
  servicios:
    - id: DISPERSION-ALTA-VISC
      rendimiento_masico: 0.985
      tiempo_nominal_min: 60
      fases:
        - nombre: Carga
          duracion_min: 15
        - nombre: Dispersion
          duracion_min: 40
        - nombre: Control_Calidad
          duracion_min: 5
```

### 6.2 Resultados Experimentales sobre 10.089 Órdenes
Validación realizada en **Pinturas Alcor** (fábrica de pinturas en Colombia):

| Métrica de Evaluación | FIFO | SPT | EDD | FÉNIX (B&B) |
| :--- | :---: | :---: | :---: | :---: |
| **Costo Medio por Lote (UM)** | 1.248,50 | 1.192,30 | 1.215,80 | **1.084,20** |
| **Ahorro Económico Relativo** | Baseline | -4,5% | -2,6% | **-13,16%** |
| **Órdenes con Retraso (%)** | 14,2% | 8,7% | 5,1% | **0,8%** |
| **Utilización Balanceada** | 62,4% | 71,8% | 68,5% | **84,6%** |
| **Tiempo Medio de Cómputo (s)** | 0,02 | 0,03 | 0,02 | **0,41** |

---

## 7. Guía Pedagógica para la Enseñanza Universitaria

Esta sección proporciona a los docentes un conjunto de directrices y talleres estructurados para incorporar el framework FÉNIX en cursos de pregrado y posgrado de Ingeniería Industrial, Mecatrónica, Química y de Sistemas. La secuencia formativa parte intencionalmente del modelado formal del proceso conjugando tiempos, costos y recursos antes de avanzar hacia la optimización y la supervisión en tiempo real.

### 7.1 Progresión Pedagógica y Módulos de Enseñanza

#### Módulo 1: Modelado de Procesos y Recursos con Redes de Petri (Duración, Costos y Disponibilidad)
* **Premisa:** Partir de un *modelo de producto existente* (por ejemplo, una receta estándar de pintura látex compuesta por etapas secuenciales de Carga, Dispersión, Molienda y Dilución).
* **Objetivos de Aprendizaje:**
  1. Comprender la física de los **Lugares Temporizados ($P^{\text{proc}}$)**: el estado de procesamiento retiene el lote durante una duración nominal $\tau(p)$, impidiendo el disparo prematuro de transiciones de salida hasta cumplir el tiempo de maduración del token ($t \ge t_{\text{arr}} + \tau(p)$).
  2. Modelar la **disponibilidad y exclusión mutua de recursos**: representar máquinas y operarios mediante lugares de precondición $P^{\text{res}}$ con marcado booleano ($M(p^{\text{res}}) \in \{0, 1\}$).
  3. Integrar la **estructura de costos directos e indirectos** en el lugar: asociar el vector de tasas $\mathbf{c}(p) = (\kappa_R^{\text{elec}}, \kappa_R^{\text{dep}}, \omega_R^{\text{lab}}, \delta_R^{\text{ind}})$ para cuantificar el costo horario de ocupación del activo.
  4. Formalizar la **conjunción lógica (AND)** de inicio de operación: verificar que una etapa solo inicia cuando confluyen simultáneamente el lote en espera ($p^{\text{wait}}$), el recurso disponible ($p^{\text{res}}$) y las materias primas requeridas ($p^{\text{mat}}$).

#### Módulo 2: Dinámica de Tokens, Balances Másicos y Costeo Basado en Actividades (ABC)
* **Objetivos de Aprendizaje:**
  1. Implementar la evolución del token coloreado $\mathbf{k}_j = (m_j, C_j, \mathbf{c}_j^{\text{hist}}, t_j^{\text{arr}})$.
  2. Modelar el balance de masa con factor de rendimiento $\gamma_{R_i} < 1$, demostrando cómo la merma física $m_{\text{loss}}$ incrementa el costo unitario efectivo absorbido por el lote.
  3. Calcular numéricamente el vector de costo acumulado $C_{j+1} = C_j + \text{Insumos} + \mathbf{c}(p) \cdot \tau_j$.

#### Módulo 3: Programación y Optimización Costo-Óptima (Branch-and-Bound)
* **Objetivos de Aprendizaje:**
  1. Construir el árbol de marcados alcanzables para órdenes con rutas alternativas (ej. Dispersor rápido y costoso vs. Dispersor estándar económico).
  2. Formular la función de evaluación $f(\nu) = g(\nu) + h(\nu)$ con cotas inferiores admisibles.
  3. Aplicar las reglas de poda por plazo estricto ($t_{\text{fin}} > d$), presupuesto ($f > V_{\text{target}}$) y dominancia frente a la mejor solución encontrada ($C_{\text{best}}$).

#### Módulo 4: Telemetría, Lazo Dual y Gemelos Digitales (EWMA y EDR)
* **Objetivos de Aprendizaje:**
  1. Configurar el lazo rápido reactivo: absorción local de perturbaciones térmicas o de viscosidad mediante cálculo de holgura $\Delta_{\text{slack}}$.
  2. Calibrar dinámicamente tiempos y rendimientos con filtros EWMA a partir de datos históricos de lote.
  3. Simular degradación mecánica mediante el Ratio de Desviación Energética ($\text{EDR} > 1.15$) y observar la reasignación automática de rutas en el planificador.

### 7.2 Taller Práctico de Laboratorio: Caso de Estudio Integral en YAML
Se propone un taller en el cual los estudiantes configuran el archivo de especificación declarativa en YAML para una planta con dos dispersores (DIS-A de 50 HP y DIS-B de 30 HP) y dos molinos horizontales:
1. Modelar la subred AB-TPPN correspondiente al servicio de dispersión, identificando lugares $P^{\text{proc}}$, $P^{\text{res}}$ y $P^{\text{mat}}$.
2. Simular la ejecución de una orden de 3.000 kg con fecha límite $d = 180\text{ min}$.
3. Introducir una falla simulada o sobreconsumo energético ($\text{EDR} = 1.20$) en DIS-A y analizar la decisión autónoma del algoritmo Branch-and-Bound de migrar la producción hacia DIS-B para minimizar el costo global.

---

## 8. Conclusiones

El framework holónico PPR presentado resuelve la brecha entre la teoría formal de optimización y la realidad operativa de las PyMEs industriales. Al fundamentar el modelo semántico en Redes de Petri con Lugares Temporizados con Costo (AB-TPPN) y alojar las especificaciones operativas en los Holones Recurso, se obtiene una representación transparente, modular y computable en tiempo real.

La superación de la dicotomía histórica entre T-TPN y P-TPN mediante el costeo basado en actividades y la formulación Branch-and-Bound permite conciliar la precisión matemática con la simplicidad declarativa en YAML. Asimismo, la propuesta pedagógica estructurada ofrece un itinerario riguroso para formar a las nuevas generaciones de ingenieros en el modelado, optimización y control de sistemas ciberfísicos de manufactura.
