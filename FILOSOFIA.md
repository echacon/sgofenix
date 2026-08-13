

# Filosofía FÉNIX - Sistema de Seguimiento de Producción

## Visión General

FÉNIX es un sistema de seguimiento de producción basado en **Redes de Petri Coloreadas** y arquitectura **Holónica**. Su nombre evoca la capacidad de **reiniciar desde cualquier punto** sin pérdida de información, como el ave que renace de sus cenizas.

### Principio Fundamental

> **"Cada lote de producción es un token que viaja por el sistema acumulando trazabilidad (cantidad, costo, tiempo). Cada recurso es un holón que sabe qué hacer y con quién coordinarse."**

---

## Los Tres Pilares Ontológicos

Siguiendo la tradición de la ingeniería ontológica (OntoUML), FÉNIX distingue tres tipos de entidades:

### 1. Continuants (El Saber Hacer)

**Naturaleza:** Entidades que **existen en el tiempo** pero no cambian su identidad. Son el "conocimiento estático" del sistema.

**Ejemplos:**
- `FamiliaProducto` (Látex, Esmalte, Sellador)
- `PatronDeRuta` (DIS-DIL, DIS-MOL-DIL)
- `TipoDeOperacion` (DIS, MOL, DIL)
- `Recurso` (Dispersor_22, Diluidor_1, Operador_Juan)
- `RedPetri` (la definición del proceso)

**Persistencia:** Permanecen en el sistema hasta que alguien los modifica explícitamente. Se versionan.

### 2. Perdurants (El Hacer)

**Naturaleza:** Entidades que **ocurren en el tiempo** y tienen duración. Son los "eventos y procesos" que suceden.

**Ejemplos:**
- `OrdenProduccion` (una solicitud concreta)
- `InstanciaRed` (una ejecución específica de una red)
- `TokenColoreado` (el lote viajando por la red)
- `EventoRed` (cada transición disparada)
- `MensajePendiente` (comunicación entre redes)

**Persistencia:** Se crean, evolucionan y se archivan. Son la "memoria operativa".

### 3. Históricos (El Aprender)

**Naturaleza:** Registros de lo que **ya ocurrió**, usados para auditoría y mejora continua.

**Ejemplos:**
- `DocumentoEstado` (historial de estados de una orden)
- `RecursoHistorico` (cambios en parámetros de recursos)
- `VersionRuta` (versiones de rutas de producción)

**Persistencia:** Inmutables. Solo se agregan, nunca se modifican.

---

## La Arquitectura de Tres Capas

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE GESTIÓN (MES)                        │
│  Responsabilidad: Planificar, negociar, optimizar               │
├─────────────────────────────────────────────────────────────────┤
│  • Selección de ruta de costo mínimo (Branch-and-Bound)         │
│  • Asignación de recursos por "Llamada a Ofertas"               │
│  • Costeo ABC (energía, MO, depreciación, pérdidas)             │
│  • Gestión de gemelos digitales                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE EJECUCIÓN (SCADA)                      │
│  Responsabilidad: Coordinar, sincronizar, persistir             │
├─────────────────────────────────────────────────────────────────┤
│  • Motor de Redes de Petri (disparo de transiciones)            │
│  • Gestión de triggers (None, 200, 201, 202)                    │
│  • Handshakes entre redes (mensajes pendientes)                 │
│  • Persistencia tolerante a fallos                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA FÍSICA (PLANTA)                         │
│  Responsabilidad: Sensar, actuar, reportar                      │
├─────────────────────────────────────────────────────────────────┤
│  • PLC y sensores (temperatura, nivel, presión)                 │
│  • SCADA (eventos automáticos)                                  │
│  • Tablets (confirmación manual de operadores)                  │
│  • Interfaz híbrida (alta o baja tecnología)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## El Holón Recurso (Concepto Clave)

Un **Holón Recurso** no es solo una máquina. Es una **unidad autónoma** que integra cuatro dimensiones:

```
┌─────────────────────────────────────────────┐
│              HOLÓN RECURSO                   │
├─────────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐    │
│  │  EQUIPO FÍSICO                       │    │
│  │  • Tanque, motor, bomba             │    │
│  │  • Capacidad, potencia              │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │  ROL DEL OPERADOR                    │    │
│  │  • Competencias requeridas          │    │
│  │  • Autorizaciones                   │    │
│  │  • Tablet asignada                  │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │  SISTEMA DE CONTROL                  │    │
│  │  • PLC, sensores, actuadores        │    │
│  │  • Lógica de automatización         │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │  INTERFAZ HUMANO-MÁQUINA             │    │
│  │  • SCADA (automático)               │    │
│  │  • Tablet (manual)                  │    │
│  │  • Botones físicos                  │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

**Ejemplo concreto:** `Diluidor_1` es:

- **Equipo:** Tanque 5000L, agitador 15HP, bomba de transferencia
- **Operador:** Juan Pérez (turno 1) con competencia en mezcla
- **Control:** PLC Siemens, sensor de nivel, válvula automática
- **Interfaz:** Pantalla SCADA + Tablet Samsung

**Cuando el sistema habla de `Diluidor_1`, habla de TODO esto como una unidad.**

---

## Tipos de Transiciones (Triggers)

| Trigger | Nombre | Origen | Comportamiento | Ejemplo |
|---------|--------|--------|----------------|---------|
| `None` | Automática | Interno | Se dispara inmediatamente cuando las precondiciones se cumplen | "Dispersar" (proceso automático de 30 min) |
| `200` | Externa | SCADA/Tablet | Espera evento externo del mundo físico | "Fin solidos" (operador confirma carga) |
| `201` | Mensaje | Otra red | Espera mensaje de coordinación entre redes | "Diluidor listo" (desde integradora) |
| `202` | Temporizador | Sistema | Espera timeout (supervisión de bloqueos) | "Alarma por inactividad" |

---

## El Token Coloreado (Corazón de la Trazabilidad)

Cada lote de producción es un **token** que viaja por las redes acumulando información:

```python
class TokenColoreado:
    orden_id: str      # "ORD-1234" (identificador único)
    material: float    # 950.0 kg (cantidad actual, se reduce por pérdidas)
    coste: float       # 125000.0 COP (costo acumulado)
    timestamp: datetime # 2025-05-12T09:25:00 (momento del último cambio)
```

### Comportamiento en Split (División)

Cuando un proceso se divide en ramas paralelas (ej: 90% sigue, 10% va a laboratorio):

- `orden_id` se **hereda** idéntico en todos los tokens hijos
- `material` se **reparte** según distribución (0.9, 0.1)
- `coste` se **hereda** (todos parten del mismo costo base)
- `timestamp` se **hereda** (mismo momento de salida)

### Comportamiento en Join (Unión)

Cuando múltiples ramas paralelas se reúnen:

- `timestamp` = `max(tiempos_llegada)` (el cuello de botella)
- `material` = `sum(materiales)` (se reúne toda la masa)
- `coste` = `coste_base + sum(coste_i - coste_base)` (se suman los incrementos)

---

## Handshake entre Redes (Coordinación Física)

En una planta real, cuando el **Dispersor** termina su ciclo, debe transferir producto al **Diluidor**. Esto no es instantáneo:

```
1. Dispersor termina producción
   ↓
2. Operador abre válvula
   ↓
3. Bomba transfiere material (2 minutos)
   ↓
4. Sensor de flujo detecta fin de transferencia
   ↓
5. Diluidor recibe el material
```

**El sistema modela esto como:**

- Dispersor dispara `t41` (Transportar) → genera evento "Fin dispersion"
- Integradora recibe y envía "Diluidor listo" a dispersión
- Dispersión espera en `p9` hasta recibir confirmación
- Dilución confirma lista a través de `t14` (Diluidor ok)

**Este es un handshake de 3 vías:** Dispersión → Integradora → Dilución → Dispersión

---

## Principios de Persistencia (Tolerancia a Fallos)

**Cada cambio de estado se persiste inmediatamente en SQLite/PostgreSQL.**

Esto permite:

- **Apagar el computador** en cualquier momento
- **Reiniciar el sistema** y recuperar todas las órdenes en curso
- **Replay de eventos** para auditoría

No hay pérdida de información. El sistema es **fault-tolerant by design**.

---

## El Ciclo de Aprendizaje

```
Tiempo nominal (planificado)
        ↓
   [EJECUCIÓN]
        ↓
Tiempo real (medido) → Diferencia Δt
        ↓
   [REGISTRO]
        ↓
Actualización de modelo (rendimiento_real, tiempo_real)
        ↓
Próxima planificación más precisa
```

**FÉNIX no solo sigue, APRENDE.**
```
