# Manual de Usuario y Operación del Sistema MOM (FÉNIX)

---

## 0. Filosofía del Sistema: El Lote como Token Inteligente

**FÉNIX** es un sistema de Gestión y Ejecución de Operaciones de Manufactura (**MOM / MES**) diseñado específicamente para Pequeñas y Medianas Empresas (PyMEs).

A diferencia de los sistemas tradicionales rígidos y centralizados, FÉNIX organiza la fábrica como una red de unidades autónomas y colaborativas (**Holones**), capaces de adaptarse rápidamente y **reiniciar o recuperarse desde cualquier punto sin pérdida de información**.

### Principio Fundamental de Operación
> **"Cada lote de producción es un *token digital* que viaja por la red acumulando trazabilidad física y económica (tiempos reales, cantidades, mermas y costos por actividad ABC). Cada recurso es un *holón inteligente con conocimiento* que encapsula cómo procesar, cuánto rinde y con quién conectarse en la planta."**

```
   ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
   │  SABER HACER    │       │    EL HACER     │       │   EL APRENDER   │
   │   (Estático)    │ ────► │   (Dinámico)    │ ────► │   (Histórico)   │
   │ Familias, Rutas,│       │ Órdenes activas,│       │ Calibración     │
   │ Tarifas y YAML  │       │ Tokens y SCADA  │       │ EWMA y EDR      │
   └─────────────────┘       └─────────────────┘       └─────────────────┘
```

---

## 1. Estructura de la Fábrica: El Enfoque de "Moldes y Piezas"

Para que la configuración sea intuitiva y escale con su empresa, la información se organiza en tres pilares:

* **Pilar 1: La Taxonomía (Los Moldes Maestros):** Define categorías genéricas (ej. Familia *"Pinturas Arquitectónicas"*, Tipo de Recurso *"Dispersor de Alta Velocidad"*, Operación Maestra *"Dispersión Estándar"*).
* **Pilar 2: Sus Productos (La Demanda - Qué se fabrica):** Especifica cada producto concreto (ej. *"Látex Blanco Premium 1000L"*), incluyendo su **Lista de Materiales (BOM)** y su **Ruta de Proceso requerida (BOP)**.
* **Pilar 3: Sus Recursos (La Oferta - Con qué se fabrica):** Define sus máquinas y puestos de trabajo reales (ej. `DIS-A`, `DIL-1`, `ENV-AUTO`). Aquí se configuran sus capacidades, rendimientos ($\gamma$), tarifas horarias ($\kappa, \omega, \delta$) y la **matriz de conectividad física ($\mathcal{K}$)**.

---

## 2. Los 4 Módulos Web de la Interfaz FÉNIX

La interfaz web unificada de FÉNIX proporciona cuatro paneles especializados accesibles desde la barra superior de navegación:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FÉNIX MOM  |  [🚦 Semáforo Pre-Producción]  [📐 Planificador & Cotizador]  │
│            |  [🏭 Dashboard Operador]        [📈 Calibración & Aprendizaje] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Módulo 1: Semáforo y Diagnóstico Pre-Producción (`/cargas/validar`)

Antes de iniciar cualquier orden en planta, el ingeniero de procesos debe consultar el **Semáforo Pre-Producción**. FÉNIX analiza toda la base de datos para garantizar que no existan inconsistencias (*Anti-Basura*).

```
                    ┌──────────────────────────────────────────────┐
                    │      MOTOR DE VALIDACIÓN PRE-PRODUCCIÓN      │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌───────────────────┬─────────────┴───────┬───────────────────┐
         ▼                   ▼                     ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 1. Integridad   │ │ 2. Conectividad │ │ 3. Invariantes  │ │ 4. Prueba en    │
│    Referencial  │ │    Física (K)   │ │    y Redes      │ │    Seco (Dry Run)│
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                     │                   │
         └───────────────────┼─────────────────────┴───────────────────┘
                             ▼
              ┌─────────────────────────────┐
              │   SEMÁFORO DE DIAGNÓSTICO   │
              │  [VERDE / AMARILLO / ROJO]  │
              └─────────────────────────────┘
```

### 3.1. Interpretación de los Estados del Semáforo

| Color | Estado en Pantalla | Significado Operativo | Acción Recomendada |
| :---: | :---: | :--- | :--- |
| 🟢 | **VERDE (Listo para Producir)** | 100% de integridad, conectividad física y lógica verificada. | Se pueden recibir, cotizar y ejecutar órdenes reales. |
| 🟡 | **AMARILLO (Advertencias Menores)** | Datos no críticos faltantes (ej. tarifas secundarias en cero). | Se puede operar, pero se recomienda completar los costos. |
| 🔴 | **ROJO (Bloqueo Crítico)** | Errores de ruta rota, servicio huérfano o red de Petri no conexa. | Se bloquea el lanzamiento de órdenes hasta corregir los datos. |

---

## 4. Módulo 2: Planificador Holónico y Cotizador (`/planificador`)

Permite cotizar y optimizar la ruta de producción antes de comprometer materiales en planta.

### 4.1. Cómo Usar el Cotizador:
1. Seleccione el **Producto** deseado del menú desplegable (ej. `Látex Blanco Premium 1000L`).
2. Ingrese la **Cantidad Requerida ($V_{\text{target}}$)** en litros o kilogramos (ej. `1000`).
3. Presione el botón **"Calcular Ruta Óptima y Cotización"**.

### 4.2. Resultados Mostrados en Pantalla:
* **Ruta de Recursos Seleccionada:** Las máquinas asignadas para cada etapa (ej. `DIS-A` $\to$ `DIL-1` $\to$ `ENV-AUTO`).
* **Materia Prima Total Requerida:** La masa inicial corregida para absorber las mermas intermedias:
  $$M_{\text{inicial}} = \frac{V_{\text{target}}}{\gamma_1 \cdot \gamma_2 \cdots \gamma_K}$$
* **Desglose de Costos ABC:**
  * Costo de Materia Prima ($\$$).
  * Costo de Energía Eléctrica ($\$$).
  * Costo de Mano de Obra Directa ($\$$).
  * Costo de Depreciación de Maquinaria ($\$$).
  * **Costo Total Estimado ($\$) y Costo Unitario ($\$/\text{kg}$).**

---

## 5. Módulo 3: Terminal de Ejecución del Operador (`/operador`)

Diseñado para uso en pantallas táctiles (tablets o terminales de puesto de trabajo en planta).

### 5.1. Flujo de Trabajo del Operario:
1. **Selección de Orden:** El operario visualiza las órdenes activas en el tablero.
2. **Visualización de Etapa y Máquina:** La pantalla muestra el marcado actual de la Red de Petri (ej. *"Cargando Material"*, *"Dispersión Fuerte"*, *"Control de Calidad"*).
3. **Botón de Disparo Manual (Trigger 200):** Al completar físicamente una actividad, el operario pulsa **"Avanzar Paso"**.
4. **Compuertas de Calidad (QA Gate):**
   * Si la viscosidad o pH están dentro de especificación, se presiona **"Aprobar Calidad"** (Trigger 201 $\to$ avanza a envasado).
   * Si no cumple especificación, se presiona **"Rechazar / Reproceso"** (Trigger 200 $\to$ retorna al mezclador para ajuste).
5. **Transferencia Automática (Handshake Inter-Redes):** Al terminar la última etapa de una máquina, el sistema envía el mensaje inter-redes y habilita automáticamente la máquina siguiente en la ruta.

---

## 6. Módulo 4: Panel de Calibración y Aprendizaje (`/aprendizaje`)

Permite a la gerencia de planta auditar cómo el sistema aprende y calibra sus estándares basándose en la ejecución real de las órdenes cerradas.

### 6.1. Funcionalidades del Panel:
* **Auditoría de Calibración EWMA:** Muestra la evolución del tiempo nominal vs. tiempo real para cada etapa, y cómo la media móvil exponencial actualiza el estándar de la planta:
  $$\hat{\tau}_{\text{nuevo}} = \alpha \cdot \tau_{\text{real}} + (1 - \alpha) \cdot \hat{\tau}_{\text{anterior}}$$
* **Monitoreo de Degradación Energética ($EDR$):**
  * $EDR \le 1.10$: Equipo en condición óptima (tarjeta verde).
  * $EDR > 1.15$: Alerta preventiva de sobreconsumo / fricción mecánica (tarjeta ámbar/roja).
* **Auditoría de Resiliencia ante Tracking Error:** Muestra la lista de órdenes que sufrieron pérdida de telemetría y fueron cerradas por resiliencia, confirmando su **exclusión estadística** del lazo de aprendizaje.

---

## 7. Guía de Solución de Problemas Frecuentes (Troubleshooting)

| Síntoma / Mensaje de Error | Causa Raíz Probable | Solución Paso a Paso |
| :--- | :--- | :--- |
| **`"Error: Servicio SVC-XXX huérfano"`** | Un producto requiere un servicio que ninguna máquina tiene registrado en su lista de servicios. | Abra el archivo de Recursos (`yaml` o Excel), ubique la máquina correspondiente y agregue `SVC-XXX` en su bloque `services`. |
| **`"Error: Ruta física rota para Producto P"`** | Las máquinas que hacen las etapas consecutivas $E_i$ y $E_{i+1}$ no están conectadas en la matriz $\mathcal{K}$. | Verifique la línea `connectivity:` del recurso de la etapa $E_i$ y asegúrese de que incluya el ID del recurso de la etapa siguiente. |
| **`"Alerta: Yield fuera de rango [0.01, 1.00]"`** | Se ingresó un porcentaje entero (ej. `97`) en lugar de la fracción decimal (`0.97`). | Modifique el valor de `yield` para que sea decimal entre 0 y 1 (ej. 0.95 para 5% de merma). |
| **`"Red bloqueada en espera de mensaje"`** | La máquina anterior no ha registrado su evento final o el mensaje no coincidía con el ID/nombre. | En el panel de Operador, complete el paso final en la máquina emisora para disparar el mensaje de transferencia. |
| **`"Alerta: EDR > 1.15 en Recurso R"`** | El sensor SCADA detecta sobreconsumo eléctrico continuado en la máquina (posible fricción o desgaste de rodamiento). | Programe una inspección mecánica preventiva. El sistema automáticamente penalizará el costo de ese equipo en la optimización hasta que se normalice. |

---

## 8. Checklist de Buenas Prácticas para Planta

1. **Ejecute el Semáforo Pre-Producción diariamente o tras cada carga de catálogo.**
2. **Revise las alertas de EDR semanalmente para anticipar fallas de mantenimiento.**
3. **Asegure que los operarios registren las aprobaciones de calidad en tiempo real para mantener la trazabilidad del lote.**
4. **Si traslada mangueras o conexiones físicas entre tanques, actualice la conectividad del recurso en el sistema.**
