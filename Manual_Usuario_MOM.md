# Manual de Usuario y Operación del Sistema MOM (FÉNIX)

---

## 0. Filosofía de FÉNIX: Primero el «Saber Hacer», Después la Tecnología

**FÉNIX** es un sistema de Gestión y Ejecución de Operaciones de Manufactura (**MOM / MES**) diseñado específicamente para Pequeñas y Medianas Empresas (PyMEs).

A diferencia de los sistemas comerciales tradicionales que exigen comprar costosos PLCs y sensores en toda la fábrica antes de empezar, **FÉNIX** parte de una premisa práctica:

> **«La verdadera inteligencia de una planta está en conectar el proceso de negocio (pedidos, costos y fechas de entrega) con el proceso de piso de planta (recetas, equipos, tuberías y calidad). Primero estructuramos el saber hacer; luego incorporamos tecnología donde realmente genera valor.»**

```
   ┌────────────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
   │  1. EL SABER HACER     │       │     2. EL HACER        │       │    3. EL APRENDER      │
   │  (Modelo de Planta)    │ ────► │ (Cuenta Corriente Viva)│ ────► │ (Calibración Continua) │
   │ Productos, Recetas,    │       │ Lotes en curso, costos │       │ Ajuste automático EWMA │
   │ Equipos y Tuberías (K) │       │ reales ABC y mermas    │       │ de tiempos, merma y EDR│
   └────────────────────────┘       └────────────────────────┘       └────────────────────────┘
```

---

## 1. Ruta de Carga: Cómo Configurar una Planta en 6 Pasos

Para montar una aplicación en FÉNIX desde cero, el sistema sigue una **Ruta de Carga de 6 Pasos** que garantiza que no existan cabos sueltos:

1. **Paso 1 — Estructura de la Empresa (`00_empresa.yaml`):** Se definen las áreas administrativas (`UnidadNegocio`) y las secciones físicas de la planta (`UnidadFuncional`, por ejemplo: *Sección Dispersión*, *Sección Envasado*).
2. **Paso 2 — Taxonomía y Servicios (`01_familias.yaml`, `02_tipos_operacion.yaml`):** Se declaran las familias de productos y las operaciones técnicas que existen en la fábrica (*Dispersión*, *Molienda*, *Dilución*, *Control de Calidad*).
3. **Paso 3 — Patrones de Proceso y Redes (`03_patrones.yaml` y archivos `.pnml`):** Se cargan las redes de proceso que describen el flujo general de la orden (**Red Integradora**) y los pasos detallados dentro de cada máquina (**Redes de Servicio**), junto con sus reglas de pase de mensajes (`encadenamiento.yaml`).
4. **Paso 4 — Recursos, Tarifas ABC y Tuberías (`04_recursos.yaml`, `05_capacidades.yaml`, `07_conectividad.yaml`):**
   * Se registran los equipos y operarios con sus costos horarios reales: energía ($\kappa$), mano de obra ($\omega$), depreciación ($\delta$) y gastos generales/overhead ($\mu$).
   * Se indica el rendimiento físico esperado de cada máquina ($\gamma$, por ejemplo `0.98` si hay 2% de merma) y si cuenta con **medidor de energía eléctrica** (`medidor_energia: true/false`).
   * Se declaran las tuberías, mangueras o bombas que conectan una máquina con otra (**Grafo de Conectividad $\mathcal{K}$**).
5. **Paso 5 — Productos, Fórmulas e Invariantes (`06_productos.yaml`, `asignaciones_recursos.yaml`):** Se cargan los productos, su lista de materias primas (BOM), los equipos candidatos por etapa y los límites seguros de operación (por ejemplo: *Temperatura máxima $55^\circ\text{C}$*).
6. **Paso 6 — Validación en el Semáforo Pre-Producción (`/cargas/validar`):** Antes de lanzar la primera orden, el Semáforo verifica automáticamente la integridad de los datos y realiza una simulación en seco (*Dry-Run*).

---

## 2. Las 3 Modalidades de Captura en Piso de Planta (Versiones A, B y C)

Una de las mayores fortalezas de **FÉNIX** para una PyME es que permite operar con tres niveles tecnológicos distintos —e incluso **combinarlos dentro de la misma planta**— sin cambiar el sistema:

| Modalidad | ¿Cómo funciona en la planta? | ¿Cuándo usarla en la PyME? |
| :--- | :--- | :--- |
| **Versión A: Sin Tecnología de Piso (Operador con Tablet)** | El operario usa una tablet o teléfono en su puesto (`/operador`) y pulsa los botones de inicio/fin de cada etapa (ej. *«Cargar sólidos»*, *«Fin dispersión»*), anotando lecturas manuales si aplica. | **Día 1 de implementación (Inversión \$0 en hardware):** Ideal para capturar tiempos reales, costos por lote y mermas de inmediato. |
| **Versión B: Tecnología Media (SCADA / PLC Existente)** | Si la empresa ya tiene un SCADA o PLC en alguna línea, el conector de FÉNIX captura automáticamente las señales de inicio/fin de paso y las lecturas de proceso. | Cuando la PyME ya posee máquinas automatizadas o un SCADA previo y desea integrarlos al costeo y seguimiento de órdenes. |
| **Versión C: Tecnología de Borde de Bajo Coste (Arduino / ESP32 + Raspberry Pi)** | Se instalan sensores económicos (pinza amperimétrica no invasiva para medir los kWh del equipo, sensor de temperatura y botonera industrial) conectados a un **Arduino/ESP32** y una **Raspberry Pi** que envían los datos a FÉNIX por Wi-Fi. | **Crecimiento quirúrgico de bajo costo (< \$100 por máquina):** Cuando los datos del Nivel A muestran que un reactor o molino es crítico y se desea medir su desgaste energético (**EDR**) y temperatura en tiempo real. |

---

## 3. Los 5 Módulos Web de la Interfaz FÉNIX

La barra superior de navegación da acceso directo a los cinco paneles del sistema:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ FÉNIX MOM  |  [🖥️ Centro de Control MES]  [🚦 Semáforo Pre-Producción]  [📐 Cotizador]   │
│            |  [🏭 Terminal Operador]      [📈 Calibración EWMA & EDR]                    │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1. Módulo 1: Centro de Control Ejecutivo MES (`/mes`)
Es la pantalla principal para el Jefe de Planta, Supervisor e Ingeniero de Integración. Consta de tres vistas integradas:
* **Mapa Vivo de Holones Recurso:** Muestra todas las máquinas de la planta, su estado actual (`LIBRE` / `EN PRODUCCIÓN`), su modalidad de captura (**Modo A**, **Modo B** o **Modo C**), su tarifa horaria efectiva, su rendimiento másico ($\gamma$) y su indicador de salud energética ($\mathrm{EDR}$).
* **Seguimiento de Órdenes y «Cuenta Corriente Viva» del Lote:** Muestra para cada orden activa el avance en la **Red Integradora** y en las **Redes de Servicio de los Equipos**, detallando en tiempo real:
  * **Masa actual en proceso ($m$)** en kg o litros.
  * **Costo total acumulado ($c_{\mathrm{acc}}$)** frente al presupuesto límite ($V_{\mathrm{target}}$).
  * **Costo unitario real ($u = c_{\mathrm{acc}} / m$)** que absorbe automáticamente las mermas ocurridas hasta el momento.
* **Asistente de Ruta de Carga y Simulador de Integración A / B / C:** Permite verificar el estado de los 6 pasos de carga de la planta y probar en vivo el envío de eventos hacia una orden desde las tres modalidades (**Botón Operador A**, **Trama SCADA B** o **Nodo Edge Arduino/Raspberry C**).

---

### 3.2. Módulo 2: Semáforo y Diagnóstico Pre-Producción (`/cargas/validar`)
Verifica en 4 fases que los archivos cargados no tengan errores antes de autorizar la producción:
* 🟢 **VERDE (Listo para Producir):** Recetas, servicios, tuberías ($\mathcal{K}$) y redes de Petri 100% válidas.
* 🟡 **AMARILLO (Advertencias Menores):** Se puede producir, pero existen tarifas secundarias en cero.
* 🔴 **ROJO (Bloqueo Crítico):** Ruta física rota o servicio inexistente; indica exactamente qué línea corregir.

---

### 3.3. Módulo 3: Planificador Holónico y Cotizador (`/planificador`)
Permite cotizar un lote y elegir la combinación óptima de equipos antes de fabricar:
1. Seleccione el **Producto**, la **Cantidad Neta a Entregar ($q_n$)**, la **Prioridad**, el **Presupuesto Máximo ($V_{\mathrm{target}}$)** opcional y el **Plazo Máximo / Deadline ($d$ en minutos)**.
2. FÉNIX ejecuta el **Algoritmo 1 (Branch-and-Bound)** y muestra:
   * **Masa Inicial Requerida ($m_0$)** vs. **Masa Final Entregada ($q_n$):** Calcula cuánto material adicional debe cargarse al inicio para compensar las mermas de los equipos seleccionados:
     $$m_0 = \frac{q_n}{\gamma_1 \cdot \gamma_2 \cdots \gamma_n}$$
   * **Cronograma por Etapa ($\mathrm{EAT} \to \mathrm{EST} \to \mathrm{EFT}$):** Respeta la agenda de reservas de cada máquina y garantiza que el lote termine antes de la fecha límite.
   * **Desglose de Costos ABC y Botón de Lanzamiento de Orden.**

---

### 3.4. Módulo 4: Terminal de Ejecución del Operador (`/operador`)
Diseñado para pantallas táctiles en piso de planta (**Versión A**):
* Muestra las órdenes activas y los botones grandes de las actividades habilitadas en cada estación (*«Asignar equipo»*, *«Cargar sólidos»*, *«Aprobar Calidad»* / *«Reproceso»*).
* Al finalizar el trabajo en una máquina, FÉNIX transfiere automáticamente el testigo (Mensaje `201`) al siguiente equipo de la ruta.

---

### 3.5. Módulo 5: Panel de Calibración EWMA y Salud Energética (`/aprendizaje`)
Permite auditar cómo el sistema aprende automáticamente al cerrarse cada orden:
* **Calibración de Tiempos ($\tau$) y Rendimientos ($\gamma$):** Muestra cómo se ajustan los estándares de cada máquina según el desempeño real de los últimos lotes.
* **Monitoreo de Condición Energética ($\mathrm{EDR}$):** En los equipos que cuentan con medidor de energía (Versión B o Versión C), compara el consumo eléctrico real frente al nominal:
  * $\mathrm{EDR} \le 1.10$: Equipo operando en condición saludable.
  * $\mathrm{EDR} > 1.15$: Alerta de sobreconsumo por desgaste mecánico o incrustación (recomienda mantenimiento preventivo y ajusta automáticamente el costo energético del equipo).
* **Aislamiento de Errores de Seguimiento (*Tracking Error*):** Si una orden se cerró forzosamente por caída de red u olvido de registro intermedio, aparece identificada y excluida del cálculo estadístico para no distorsionar los promedios de la planta.
