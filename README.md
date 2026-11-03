# Fénix: Sistema MOM / MES Holónico para PyMEs basado en Redes de Petri AB-TPPN

Fénix es un sistema ligero de **Gestión de Operaciones de Manufactura (MOM / MES)** de código abierto pensado para Pequeñas y Medianas Empresas (PyMEs) industriales bajo el principio **"Primero el saber hacer, después la tecnología"**. Modela la planta como una red de agentes cooperativos (**Holones de Producto** y **Holones de Recurso**) y utiliza **Redes de Petri Temporizadas Basadas en Actividades (AB-TPPN)** como motor formal de programación al costo óptimo, seguimiento en tiempo real y auto-calibración estadística.

> ¿Primera vez aquí? Sigue el orden de este README: instalación rápida → modalidades tecnológicas de planta (A/B/C) → ruta de carga en 6 pasos → dónde profundizar según tu rol.

---

## 🚀 Instalación Rápida

```bash
# 1. Clonar el repositorio
git clone https://github.com/echacon/sgofenix.git
cd sgofenix

# 2. Crear y activar entorno virtual (Python 3.10+)
python -m venv env
source env/bin/activate      # En Windows PowerShell: .\env\Scripts\Activate.ps1

# 3. Instalar el núcleo Fénix y sus dependencias
pip install --upgrade pip
pip install -e "./fenix[dev]"

# 4. (Opcional) Ejecutar las suites de verificación matemática y ejemplo integral (en memoria)
python tests/simulador/verificar_paper_ieee_tii.py
python tests/simulador/ejemplo_integral_modos_abc.py

# 5. Inicializar base de datos SQLite y usuarios por defecto (admin@fenix.local / admin123)
python tools/carga/init_db.py
```

## ▶️ Ejecución

```bash
# Iniciar el Servidor Web, Centro de Control MES y Pasarela Unificada de Ingesta (:5000)
python web/app.py
```

Una vez iniciado, abre `http://localhost:5000` en tu navegador:
- **Centro de Control Ejecutivo MES**: `http://localhost:5000/mes`
- **Semáforo Pre-Producción & Validador YAML**: `http://localhost:5000/cargas/validar`
- **Planificador y Cotizador Dinámico ABC (Algoritmo 1)**: `http://localhost:5000/planificador`
- **Panel de Operación en Planta (Tablet Operador)**: `http://localhost:5000/operador`
- **Lazo de Aprendizaje EWMA / EDR**: `http://localhost:5000/aprendizaje`

📘 **Para instrucciones detalladas de despliegue en red local, conexión de tablets, integración SCADA o cableado de nodos Arduino + Raspberry Pi, consulta el [`Manual_Instalacion_MOM.md`](Manual_Instalacion_MOM.md).**

---

## 🔌 Tres Modalidades Tecnológicas de Piso de Planta (Coexistentes)

Fénix desacopla la semántica formal de sus Redes de Petri respecto al nivel de automatización física de cada máquina a través de la pasarela unificada `POST /api/ingesta/evento_planta`. Esto permite que en una misma PyME —y dentro de una misma Orden de Producción— coexistan tres niveles tecnológicos:

1. **Versión A — Sin tecnología avanzada de piso (*Human-in-the-Loop*)**:
   El operador confirma el inicio/fin de cada etapa e introduce mediciones de calidad o mermas desde una tablet web (`/operador`).
2. **Versión B — Tecnología media (*SCADA / PLC existente*)**:
   El adaptador [`tools/edge_y_scada/conector_scada_cliente.py`](tools/edge_y_scada/conector_scada_cliente.py) captura flancos de tags, lecturas de energía ($\text{kWh}$) y temperatura desde un SCADA o PLC existente.
3. **Versión C — Tecnología de borde de bajo coste (*Low-Cost Edge IIoT: Arduino + Raspberry Pi*)**:
   Maquinaria legada instrumentada de forma no invasiva (< 80 USD/estación) mediante un microcontrolador **Arduino/ESP32** ([`firmware_arduino_holon.ino`](tools/edge_y_scada/firmware_arduino_holon.ino)) con pinza amperimétrica **SCT-013**, sonda térmica **DS18B20** y pulsador industrial, concentrado por una **Raspberry Pi** ([`nodo_edge_raspberry_arduino.py`](tools/edge_y_scada/nodo_edge_raspberry_arduino.py)) que integra los $\text{kWh}$ del lote y dispara los eventos hacia Fénix.

---

## 🚀 Características Clave

- **Autonomía Distribuida (Marco PPR Holónico):** reemplaza la rigidez jerárquica tradicional por Holones de Producto ($\text{PH}$) y Holones de Recurso ($\text{RH}$) acoplados mediante Redes de Petri de Ejecución ($\mathcal{N}_E$) y Seguimiento ($\mathcal{N}_S$).
- **Programación al Costo Óptimo (Algoritmo 1):** poda en dos etapas (conectividad física $\mathcal{K}$ y agendas dinámicas $\Psi_R$ bajo plazo de entrega $d$) y búsqueda *Branch-and-Bound* con cota inferior admisible $LB(\nu)$ y retropropagación exacta de mermas ($m_0 = q_n / \prod \gamma_k$).
- **Calibración Automática de Doble Escala Temporal (EWMA):** ajusta las duraciones efectivas $\tau(p,R)$, los rendimientos másicos $\gamma(p,R)$ y la eficiencia energética al cierre de cada lote válido.
- **Monitoreo de Condición No Intrusivo ($\text{EDR}$):** detecta la degradación electromecánica de los equipos mediante la Relación de Desviación Energética $\text{EDR}(R) = \bar{e}_{\text{EWMA}} / e_{\text{nom}}$ y actualiza automáticamente su tasa horaria energética $\kappa_R^{\text{eff}}$.
- **Resiliencia ante Pérdida de Eventos (*Tracking Error*):** reconstruye el estado desde la base de datos y aísla cierres forzados por fallos de telemetría para no contaminar los estimadores estadísticos EWMA.

---

## 📂 Estructura del Repositorio — ¿Por dónde empiezo según mi rol?

| Si eres... | Empieza por |
| :--- | :--- |
| **Técnico / Integrador (Instalación y Hardware Edge/SCADA)** | [`Manual_Instalacion_MOM.md`](Manual_Instalacion_MOM.md) y [`tools/edge_y_scada/`](tools/edge_y_scada/) |
| **Ingeniero de planta / Usuario operativo** | [`Manual_Usuario_MOM.md`](Manual_Usuario_MOM.md) |
| **Desarrollador / Arquitecto de software** | [`Manual_Tecnico_Final_MOM.md`](Manual_Tecnico_Final_MOM.md) (sincronizado con [`Manual_Tecnico_MOM.md`](Manual_Tecnico_MOM.md)) |
| **Investigador / Reproducibilidad experimental** | [`tests/simulador/verificar_paper_ieee_tii.py`](tests/simulador/verificar_paper_ieee_tii.py), [`tests/simulador/ejemplo_integral_modos_abc.py`](tests/simulador/ejemplo_integral_modos_abc.py) y [`fenix/data/benchmark_pintura/`](fenix/data/benchmark_pintura/) |
| **Interesado en fundamentos y filosofía holónica** | [`ReporteTecnico_MarcoHolonico.md`](ReporteTecnico_MarcoHolonico.md), [`Filosofia_Integracion_Holonica.md`](Filosofia_Integracion_Holonica.md) y [`Glosario_de_Terminos.md`](Glosario_de_Terminos.md) |

### Referencia de directorios principales
- [`fenix/`](fenix/): núcleo matemático y modelos ORM SQLAlchemy (`modelos/`, `servicios/`, `utils/motor_abtppn.py`, `validadores/`, `importadores/`).
- [`web/`](web/): aplicación web Flask (`app.py`, `routes/mes.py`, `routes/planificador.py`, `routes/operador.py`, `routes/cargas_validadas.py`, `routes/aprendizaje.py` y plantillas HTML/Bootstrap 5).
- [`tools/edge_y_scada/`](tools/edge_y_scada/): conectores para Modo B (`conector_scada_cliente.py`) y Modo C (`nodo_edge_raspberry_arduino.py`, `firmware_arduino_holon.ino`).
- [`tests/simulador/`](tests/simulador/): suites de verificación formal del artículo *IEEE TII* (`verificar_paper_ieee_tii.py`), resiliencia (`test_resiliencia_tracking.py`) y ejemplo integral híbrido A/B/C (`ejemplo_integral_modos_abc.py`).
- [`fenix/data/benchmark_pintura/`](fenix/data/benchmark_pintura/): dataset público empírico (`dataset_ordenes_indicadores_IJPR.csv`) y scripts de análisis estadístico.

---

## 📖 Publicaciones Científicas y Citación

Fénix se desarrolla como parte de un proyecto de investigación en la **Universidad de los Andes (ULA), Mérida, Venezuela**. Si utilizas Fénix en tu investigación académica o desarrollo industrial, por favor cita:

```bibtex
@article{ChaconCardillo2026,
  author  = {Chac{\'o}n, Edgar and Cardillo, Juan},
  title   = {An Activity-Centric Holonic PPR Framework and Petri Net Formalism for Cost-Optimal Scheduling and SCADA-Driven Model Refinement in SMEs},
  journal = {IEEE Transactions on Industrial Informatics},
  year    = {2026},
  note    = {Under review}
}
```

---

## 📄 Licencia

Distribuido bajo licencia **GNU Affero General Public License v3.0 (AGPL-3.0-only)**. Consulta [`fenix/pyproject.toml`](fenix/pyproject.toml) para más detalles.
