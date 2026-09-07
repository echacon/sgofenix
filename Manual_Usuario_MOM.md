# Manual de Usuario: Gestión, Carga y Operación del Sistema MOM (FÉNIX)

---

## 0. Filosofía del Sistema (FÉNIX)

**FÉNIX** es un sistema de gestión y seguimiento de operaciones de manufactura (**MOM / MES**) diseñado específicamente para Pequeñas y Medianas Empresas (PyMES). Combina la potencia matemática de las **Redes de Petri Temporizadas con Lugares con Costo (AB-TPPN)** con una **arquitectura holónica orientada a actividades**.

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

## 2. Formatos de Configuración: Enfoque Dual (YAML vs. PNML)

FÉNIX le da total libertad para elegir cómo ingresar la lógica de sus procesos:

```
                  ┌────────────────────────────────────────────────┐
                  │          ENTRADAS DE MODELADO LIBRES           │
                  └───────────────────────┬────────────────────────┘
                                          │
            ┌─────────────────────────────┴─────────────────────────────┐
            ▼                                                           ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────────┐
│     VÍA 1: ENFOQUE DECLARATIVO YAML   │   │       VÍA 2: ENFOQUE FORMAL PNML      │
│      (Para ingeniería de planta)      │   │     (Para modeladores y académicos)   │
│ • Archivos de texto simples           │   │ • Diseñado en editores como WoPeD     │
│ • Duraciones nominales e invariantes  │   │ • Validación matemática de propiedades│
│ • No requiere dibujar redes de Petri  │   │ • Importación directa del XML formal  │
└───────────────────┬───────────────────┘   └───────────────────┬───────────────────┘
                    │                                           │
                    └─────────────────────┬─────────────────────┘
                                          ▼
                         ┌─────────────────────────────────┐
                         │   MODELO INTERNO ÚNICO AB-TPPN   │
                         │ (Tablas SQL + Objetos Holónicos)│
                         └─────────────────────────────────┘
```

* **Vía Ligera (YAML):** Ideal para el personal operativo y técnicos de planta. Solo definen pasos, límites de seguridad (temperatura, RPM) y duraciones en texto claro.
* **Vía Formal (PNML):** Para modeladores que usan herramientas gráficas como **WoPeD** y desean importar redes de Petri con validación de propiedades estructurales (vivas, acotadas y sin bloqueos).

---

## 3. Guía de Carga Paso a Paso (Checklist de Onboarding)

Para evitar inconsistencias y dependencias rotas, **la carga de datos en FÉNIX debe seguir un orden secuencial estricto**.

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ FASE 1: Base Temporal (Turnos y Calendarios)                            │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ FASE 2: Catálogo de Recursos (Máquinas, Tarifas, Mermas y Conectividad) │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ FASE 3: Taxonomía y Familias de Productos                               │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ FASE 4: Catálogo de Productos y Recetas (BOM y Etapas)                  │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ FASE 5: Guiones de Secuencia de Proceso (YAML o PNML)                   │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ FASE 6: VALIDACIÓN INTEGRAL PREVIA ("Semáforo Listo para Producir")    │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

### Fase 1: Base Temporal y Calendarios de Turno
Antes de configurar máquinas, defina los horarios laborales de su planta:
* **Identificador de Calendario:** ej. `CAL-TURNO-A`, `CAL-24H`.
* **Horarios Disponibles:** Días hábiles y franjas horarias por turno (ej. Lunes a Viernes 07:00 a 17:00).
* **Intervalos de Mantenimiento Programado:** Bloqueos fijos de planta.

---

### Fase 2: Catálogo de Recursos (Oferta de Planta)
Declare cada equipo físico o estación de trabajo:

```yaml
# Ejemplo: Declaración de un Recurso Holónico
resource:
  id: RH-DISP-2000
  name: "Dispersor de Alta Velocidad 2000L"
  type: "DISPERSOR"
  calendar: "CAL-TURNO-A"
  
  services:
    - id: SVC-DISPERSION
      nominal_duration_min: 145       # Duración nominal base
      yield: 0.97                     # Rendimiento (3% de merma residual)
      cost_rates:
        energy_rate: 0.38             # Costo eléctrico por unidad de tiempo ($/h)
        labor_rate: 0.22              # Asignación de operario ($/h)
        depreciation_rate: 0.08       # Tasa de desgaste de equipo ($/h)
      process_net: "Dis_ChildNet.pnml" # (Opcional si usa red PNML de detalle)
      
  # Matriz de Conectividad Física (hacia qué tanques puede descargar):
  connectivity: [RH-DIL-4000, RH-DIL-6000]
```

> [!IMPORTANT]
> **El factor de rendimiento ($\gamma = \text{yield}$)** debe ser un valor entre `0.01` y `1.00`. Por ejemplo, un rendimiento del $97\%$ se ingresa como `0.97` ($3\%$ de merma). Esto permite que el sistema calcule exactamente la materia prima adicional requerida según el camino elegido.

---

### Fase 3: Taxonomía y Familias de Productos
Agrupe sus productos en familias maestras:
1. **Familia:** ej. `FAM-ARQ-AGUA` (*Pinturas Arquitectónicas Base Agua*), `FAM-IND-SOLV` (*Pinturas Industriales Base Solvente*).
2. **Propiedades Maestras:** Tiempos de limpieza entre lotes, factores de merma típicos y restricciones de incompatibilidad de color.

---

### Fase 4: Catálogo de Productos y Recetas (Demanda)
Defina cada producto vendible y su estructura:

1. **Lista de Materiales (BOM):**
   * Código de materia prima (ej. `MP-PIGM-TITANIO`, `MP-RESINA-ACRIL`).
   * Cantidad requerida por unidad de producto terminado (ej. kg/L).
   * Costo unitario base del material ($u_{\text{mat}}$).
2. **Ruta de Proceso (BOP - Etapas Requeridas):**
   * Secuencia ordenada de etapas maestras (ej. $E_1$: `SVC-DISPERSION` $\to$ $E_2$: `SVC-DILUCION` $\to$ $E_3$: `SVC-ENVASADO`).

---

### Fase 5: Guiones de Secuencia de Proceso e Invariantes
Defina la coreografía interna de cada etapa mediante **YAML** o cargando el archivo **PNML**:

```yaml
# Ejemplo: Guion YAML de Proceso con Invariantes de Calidad
proceso:
  id: PROC-DISPERSION-LATEX
  etapa_asociada: SVC-DISPERSION
  
  pasos:
    - id: paso_1
      nombre: "Carga de Agua y Aditivos"
      duracion_min: 20
      
    - id: paso_2
      nombre: "Adición de Pigmentos y Dispersión Fuerte"
      duracion_min: 75
      # Invariantes de seguridad y calidad física:
      invariantes:
        - parametro: "Temperatura"
          limite_maximo: 55.0
          unidad: "C"
          accion_violacion: "ALARMA_Y_DETENER_MOTOR"
        - parametro: "Velocidad"
          limite_minimo: 600.0
          limite_maximo: 1200.0
          unidad: "RPM"

    - id: paso_3
      nombre: "Control de Calidad (Molienda/Hegman)"
      duracion_min: 15
      tipo: "COMPUERTA_CALIDAD" # QA Gate
```

---

## 4. Fase de Validación Integral: "El Semáforo de Listo para Producir"

Una vez completada la carga de archivos, **nunca lance producción sin ejecutar el módulo de validación**. FÉNIX analiza toda la base de conocimiento y genera un diagnóstico en cuatro niveles:

```
                    ┌──────────────────────────────────────────────┐
                    │      MOTOR DE VALIDACIÓN PRE-PRODUCCIÓN      │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌───────────────────┬─────────────┴───────┬───────────────────┐
         ▼                   ▼                     ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 1. Integridad   │ │ 2. Conectividad │ │ 3. Invariantes  │ │ 4. Prueba en    │
│    Referencial  │ │    Física       │ │    y Redes      │ │    Seco (Dry Run)│
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                     │                   │
         └───────────────────┼─────────────────────┴───────────────────┘
                             ▼
              ┌─────────────────────────────┐
              │   SEMÁFORO DE DIAGNÓSTICO   │
              │  [VERDE / AMARILLO / ROJO]  │
              └─────────────────────────────┘
```

### 4.1. Verificación 1: Integridad Referencial
* **Chequeo de Insumos:** Que todo ingrediente en el BOM exista en la tabla maestra de materiales con costo unitario $> 0$.
* **Chequeo de Servicios:** Que cada servicio solicitado por los productos ($s_i$) sea ofrecido por al menos un recurso activo en planta.
* **Chequeo de Calendarios:** Que ninguna máquina tenga un calendario inexistente o vacío.

### 4.2. Verificación 2: Conectividad Física del Grafo de Planta ($\mathcal{K}$)
* FÉNIX construye el grafo dirigido de la planta.
* Verifica que para cada producto exista **al menos una ruta física continua sin cortes**.
* *Ejemplo de detección de error:* Si un producto requiere `Dispersión` $\to$ `Dilución` $\to$ `Envasado`, pero `DIS-A` solo se conecta a `DIL-1` y `DIL-1` no tiene tubería hacia `ENV-AUTO`, el sistema emite un error de ruta rota.

### 4.3. Verificación 3: Validación de Invariantes y Redes de Petri
* **En YAML:** Comprueba que no existan tiempos negativos, que los rangos mínimo/máximo de invariantes sean coherentes ($\text{mínimo} < \text{máximo}$) y que los identificadores de pasos sean únicos.
* **En PNML (WoPeD):** Verifica que la red sea conexa, tenga un único lugar inicial ($p_{\text{in}}$) y final ($p_{\text{out}}$), y que no existan bloqueos estructurales (*deadlocks*).

### 4.4. Verificación 4: La "Prueba en Seco" (Dry-Run de Orden Cero)
* El sistema crea una orden de prueba virtual de 1 lote sin afectar los registros reales.
* Simula el viaje del token por la red, evalúa la acumulación de costos por actividad ($c_{\text{acc}}$) y verifica que el cálculo de merma acumulada retropropague correctamente.
* Si el token llega al lugar de salida con éxito, la prueba pasa.

### 4.5. Interpretación del Semáforo

| Color | Estado | Significado para el Usuario | Acción Requerida |
| :---: | :---: | :--- | :--- |
| 🟢 | **LISTO PARA PRODUCIR** | 100% de integridad, conectividad y lógica verificada. | Puede recibir y programar órdenes reales de clientes. |
| 🟡 | **ADVERTENCIA** | Hay datos no críticos faltantes (ej. un recurso secundario no tiene tarifa de depreciación asignada). | Se puede operar, pero se recomienda completar los datos para máxima exactitud de costos. |
| 🔴 | **BLOQUEO CRÍTICO** | Errores de ruta rota, servicio huérfano o red de Petri no conexa. | El sistema bloquea el lanzamiento de órdenes hasta corregir la inconsistencia. |

---

## 5. Guía de Solución de Problemas Frecuentes (Troubleshooting)

| Mensaje de Error / Alerta en Fénix | Causa Raíz Probable | Solución Paso a Paso |
| :--- | :--- | :--- |
| **`"Error: Servicio SVC-XXX huérfano"`** | Un producto requiere un servicio que ninguna máquina tiene registrado en su lista de servicios. | Abra el archivo de Recursos (`yaml` o Excel), ubique la máquina correspondiente y agregue `SVC-XXX` en su bloque `services`. |
| **`"Error: Ruta física rota para Producto P"`** | Las máquinas que hacen las etapas consecutivas $E_i$ y $E_{i+1}$ no están conectadas en la matriz $\mathcal{K}$. | Verifique la línea `connectivity:` del recurso de la etapa $E_i$ y asegúrese de que incluya el ID del recurso de la etapa siguiente. |
| **`"Alerta: Yield fuera de rango [0.01, 1.00]"`** | Se ingresó un porcentaje entero (ej. `97`) en lugar de la fracción decimal (`0.97`). | Modifique el valor de `yield` para que sea decimal entre 0 y 1 (ej. 0.95 para 5% de merma). |
| **`"Error: PNML Deadlock detectado en Net N"`** | La red de Petri diseñada en WoPeD tiene una bifurcación sin unión o una transición que consume tokens de un recurso que nunca se liberan. | Abra la red en WoPeD, use el análisis de *Soundness* (propiedades de Workflow-Net), corrija los lazos y re-exporte el archivo `.pnml`. |
| **`"Alerta: EDR > 1.15 en Recurso R"`** | El sensor SCADA detecta sobreconsumo eléctrico continuado en la máquina (posible fricción o desgaste de rodamiento). | Programe una inspección mecánica preventiva. El sistema automáticamente penalizará el costo de ese equipo en la optimización hasta que se normalice. |

---

## 6. El Ciclo de Operación Diaria: De la Orden a la Entrega

```
  1. RECEPCIÓN DE PEDIDO
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ El planificador ingresa la orden: Producto, Cantidad (kg/L) y Deadline d │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       │
  2. PROGRAMACIÓN ÓPTIMA (Horizonte Deslizante)
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ El motor B&B busca la terna de máquinas con menor costo total ABC y     │
  │ reserva los intervalos en las agendas Ψ de los recursos.                │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       │
  3. EJECUCIÓN EN PLANTA Y CONTROL EN TIEMPO REAL
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ Operarios ejecutan pasos en tablet. SCADA valida invariantes (T°, RPM). │
  │ Transiciones de compuerta verifican calidad antes del trasvase.         │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       │
  4. CIERRE Y COSTEO REAL
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ El sistema registra los kWh reales y tiempo exacto. Calcula costo final │
  │ y alimenta el lazo de aprendizaje EWMA para futuras órdenes.           │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Caso Práctico Guiado: Orden de 1.000 kg de Látex Blanco

1. **Configuración Validada:** En planta disponemos de los dispersores `DIS-A` ($\gamma=0.97$), `DIS-B` ($\gamma=0.94$), los diluidores `DIL-1`, `DIL-2` y la envasadora `ENV-AUTO`.
2. **Recepción de la Orden:** Se recibe pedido `ORD-2026-101` de $1.000\text{ kg}$ con fecha límite $d = 8\text{ horas}$ ($480\text{ min}$).
3. **Cálculo de Demanda Real:**
   * Al elegir `DIS-A` ($\gamma=0.97$) y `DIL-1` ($\gamma=0.99$), el sistema calcula que se deben cargar exactamente:
     $$\text{Materia Prima Requerida} = \frac{1000}{0.97 \times 0.99} = 1.041,3\text{ kg}$$
4. **Optimización Económica:** Aunque `DIS-B` tiene un motor eléctrico más pequeño, su menor rendimiento ($\gamma=0.94$) obligaría a cargar $1.074,5\text{ kg}$ ($33,2\text{ kg}$ extra de materias primas caras). El optimizador selecciona automáticamente la ruta `DIS-A` $\to$ `DIL-1` $\to$ `ENV-AUTO` como la de **menor costo global**.
5. **Seguimiento en Pantalla:** Durante la dispersión, la temperatura se mantiene en $48^\circ\text{C}$ ($< 55^\circ\text{C}$). Al completarse, el laboratorio registra viscosidad OK y el lote avanza al diluidor.
6. **Cierre de Orden:** Al finalizar el envasado, el sistema emite el reporte de costo real desglosado:
   * Materias Primas: $\$1.250$
   * Energía Eléctrica: $\$45,60$
   * Mano de Obra Directa: $\$38,20$
   * Depreciación de Máquinas: $\$12,40$
   * **Costo Real Total:** $\mathbf{\$1.346,20}$ ($\$1,346/\text{kg}$).

---

## 8. Recomendaciones para el Éxito en Planta

1. **Mantenga al día la conectividad física:** Si traslada una manguera o habilita una tubería nueva entre dos tanques, actualice la lista `connectivity` del recurso.
2. **Reporte paradas reales:** Cuando una máquina entre en mantenimiento, bloquéela en su calendario $\Omega$ para que el programador no asigne lotes a ese equipo.
3. **Valide siempre antes de arrancar:** Si agrega un nuevo producto al catálogo, pulse **"Validar Configuración"** para asegurarse de que el semáforo esté en **Verde**.
