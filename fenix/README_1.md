# 🦅 FÉNIX — Sistema de Seguimiento de Producción

> *"Cada lote de producción es un token que viaja por el sistema acumulando trazabilidad. Cada recurso es un holón que sabe qué hacer y con quién coordinarse."*

FÉNIX es un sistema **MES (Manufacturing Execution System)** de código abierto basado en **Redes de Petri Coloreadas** y arquitectura **Holónica**. Su nombre evoca la capacidad de reiniciar desde cualquier punto sin pérdida de información.

---

## ¿Qué hace?

- Modela procesos de producción como **Redes de Petri coloreadas** (archivos `.pnml`)
- Sigue en tiempo real el estado de cada lote (orden de producción) como un **token coloreado** que acumula cantidad, costo y timestamp
- Coordina **múltiples redes** que se comunican mediante handshakes (mensajes entre redes)
- Recibe eventos desde **SCADA, tablets o simulación** JSON
- Es **fault-tolerant**: persiste cada cambio en SQLite/PostgreSQL; si se apaga, retoma exactamente donde quedó
- Expone una **API REST Flask** para operadores y sistemas externos

## Arquitectura

```
┌─────────────────────────────┐
│   API Flask  (app.py)        │  ← Operadores, SCADA, sistemas externos
└──────────────┬──────────────┘
               │ eventos (cola_evento en BD)
┌──────────────▼──────────────┐
│  Orquestador  (main.py)      │  ← Proceso continuo independiente
│  servicios/orquestador.py    │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│  Motor ABTPPN                │  ← Ejecución de redes de Petri en memoria
│  utils/motor_abtppn.py       │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│  SQLite / PostgreSQL         │  ← Persistencia de estado e historial
└─────────────────────────────┘
```

## Tipos de triggers de transición

| Trigger | Tipo | Origen |
|---------|------|--------|
| `None` | Automática | Interna — se dispara sola cuando las precondiciones se cumplen |
| `200` | Externa | SCADA o tablet — espera confirmación del mundo físico |
| `201` | Mensaje | Otra red — handshake de coordinación |
| `202` | Temporizador | Sistema — timeout de supervisión |

---

## Estructura del proyecto

```
fenix/
├── app.py                  # Entrypoint Flask (API REST)
├── main.py                 # Entrypoint orquestador continuo
├── pyproject.toml
│
├── config/                 # Configuración YAML del sistema
│   ├── 01_familias.yaml
│   ├── 02_tipos_operacion.yaml
│   └── ...
│
├── modelos/                # Modelos SQLAlchemy (ontología)
├── servicios/              # Lógica de negocio y orquestación
├── utils/                  # Motor Petri, parser PNML, utilidades
├── routes/                 # Blueprints Flask
├── validadores/            # Validación de datos entrantes
├── importadores/           # Importación de YAML, Excel, PNML
│
├── rutas_producto/         # Configuración por producto
│   └── PintucoBaseAgua_V1/
│       ├── redes/          # Archivos .pnml
│       └── recursos/       # Asignaciones de recursos
│
├── scripts/                # Scripts de operación y mantenimiento
│   ├── migraciones/
│   └── mantenimiento/
│
├── tests/                  # Tests (en construcción)
└── docs/                   # Documentación técnica
```

---

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/fenix.git
cd fenix

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -e ".[dev]"

# Inicializar base de datos
python scripts/migraciones/inicializar_sistema.py

# Cargar configuración inicial
python scripts/carga_inicial.py
```

## Ejecución

Se necesitan **dos procesos** corriendo en paralelo:

```bash
# Terminal 1 — Servidor web (API REST + interfaz operador)
python app.py

# Terminal 2 — Orquestador continuo (motor de redes de Petri)
python main.py
```

El orquestador lee eventos de la tabla `cola_evento` en BD y los procesa en orden FIFO cada 5 segundos.

---

## Tests

```bash
pytest
pytest --cov=. --cov-report=html   # con cobertura
```

> Los tests están en construcción. Contribuciones bienvenidas — ver `tests/README.md`.

---

## Documentación técnica

| Archivo | Contenido |
|---------|-----------|
| `docs/FILOSOFIA.md` | Principios ontológicos y arquitectura conceptual |
| `docs/FLUJO_DATOS.md` | Flujos de datos paso a paso con ejemplos SQL |
| `docs/ELEMENTOS.md` | Referencia de elementos del sistema |

---

## Contribuir

1. Fork del repositorio
2. Crea tu rama: `git checkout -b feature/mi-mejora`
3. Commit con mensaje descriptivo: `git commit -m "feat: descripción"`
4. Push y abre un Pull Request

Por favor incluye tests para cambios en `servicios/` o `utils/`.

---

## Licencia

AGPL-3.0 — ver `LICENSE` en la raíz del repositorio. Esto significa que si ejecutas una versión modificada de Fénix como servicio (incluso solo accesible por red, sin distribuir el software), debes poner a disposición de tus usuarios el código fuente de esas modificaciones.

---

## Estado del proyecto

🚧 **Alpha** — En uso en entorno de desarrollo. No recomendado para producción sin revisión de seguridad (la `secret_key` de Flask debe cambiarse obligatoriamente).
