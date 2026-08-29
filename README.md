# Fénix: sistema MOM holónico para PyMEs, basado en Redes de Petri

Fénix es un sistema ligero de **Gestión de Operaciones de Manufactura (MOM)** pensado para pequeñas y medianas empresas industriales. Modela la planta como una red de agentes autónomos (holones) que representan recursos, productos y órdenes, y usa **Redes de Petri** como motor de seguimiento y programación de la producción al menor costo posible.

> ¿Primera vez aquí? Sigue el orden de este README: instalación → conceptos clave → cómo configurar tu planta → dónde profundizar según tu rol.

---

## 🚀 Instalación

```bash
# Clonar el repositorio
git clone https://github.com/echacon/sgofenix.git
cd sgofenix/fenix

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

## ▶️ Ejecución

Se necesitan **dos procesos corriendo en paralelo**:

```bash
# Terminal 1 — Servidor web (API REST + interfaz de operador)
python app.py

# Terminal 2 — Orquestador continuo (motor de Redes de Petri)
python main.py
```

El orquestador lee eventos de la tabla `cola_evento` en la base de datos y los procesa en orden FIFO cada 5 segundos.

> 🚧 **Estado del proyecto: Alpha.** En uso en entorno de desarrollo. No recomendado para producción sin revisión de seguridad (la `secret_key` de Flask debe cambiarse obligatoriamente).

---

## 🚀 Características Clave

- **Autonomía Distribuida (Diseño Holónico):** reemplaza el control jerárquico vertical rígido (ISA-95 clásico) por agentes autónomos y cooperativos que representan Recursos, Productos y Órdenes.
- **Programación al Costo Óptimo:** minimiza el costo real de producción (energía, mano de obra, depreciación y merma de material) bajo una fecha de entrega fija.
- **Calibración Automática vía SCADA:** ajusta automáticamente los tiempos de proceso y tarifas energéticas a partir de los registros de ejecución de planta, usando un estimador EWMA de doble escala temporal.
- **Monitoreo de Condición No Intrusivo:** detecta el desgaste de los recursos mediante un Ratio de Desviación de Energía (EDR) y ajusta la competitividad del recurso automáticamente.
- **Alta Resiliencia (Tolerancia a Fallos):** el estado se reconstruye automáticamente a partir de los marcados de las Redes de Petri persistidos en base de datos.

---

## 🛠️ Configurar tu planta (para ingenieros de planta, sin programación)

Fénix está diseñado para que un ingeniero de planta lo configure sin necesidad de programar ni de conocer Redes de Petri. La configuración se hace con dos archivos simples:

1. **Datos estáticos (plantillas Excel):**
   Recursos (máquinas, operarios, tarifas de costo por hora), taxonomías de producto y listas de materiales (BOM), en una hoja de cálculo estándar.
2. **Lógica del flujo de proceso (scripts YAML):**
   Un archivo YAML simple que declara los pasos operativos y las sincronizaciones entre estaciones:
   ```yaml
   proceso:
     estaciones:
       - dispersor_espera
       - dispersor_mezclando
       - diluidor_espera
     acciones:
       iniciar_mezcla:
         cuando: [dispersor_espera]
         mueve_a: [dispersor_mezclando]
         tipo: "Manual"
       unir_con_diluidor:
         cuando: [dispersor_mezclando, diluidor_espera]
         mueve_a: [diluidor_recibiendo]
         tipo: "Sincronizado"
   ```

Para el detalle paso a paso, ve al [Manual de Usuario](Manual_Usuario_MOM.md).

---

## 📂 Estructura del repositorio — ¿por dónde empiezo según mi rol?

| Si eres...                                | Empieza por |
|--------------------------------------------|-------------|
| Ingeniero de planta / usuario operativo     | [`Manual_Usuario_MOM.md`](Manual_Usuario_MOM.md) |
| Desarrollador / integrador técnico          | [`Manual_Tecnico_Final_MOM.md`](Manual_Tecnico_Final_MOM.md) y [`Manual_Tecnico_MOM.md`](Manual_Tecnico_MOM.md) *(ver nota abajo)* |
| Interesado en los fundamentos y la filosofía del diseño | [`Filosofia_Integracion_Holonica.md`](Filosofia_Integracion_Holonica.md), [`FILOSOFIA.md`](FILOSOFIA.md) |
| Interesado en las bases científicas         | sección [Publicaciones Científicas](#-publicaciones-científicas) más abajo |

> **Nota:** actualmente hay dos manuales técnicos (`Manual_Tecnico_MOM.md` y `Manual_Tecnico_Final_MOM.md`) con contenido complementario, no uno "borrador" y otro "definitivo". Están pendientes de consolidación — ver ambos por ahora.

Referencia completa de archivos:

- [`fenix/`](fenix/): código fuente del motor de ejecución en Python, esquemas de base de datos e interfaces web.
  - [`fenix/servicios/`](fenix/servicios/): orquestador, planificador y validador de condición de recursos.
  - [`fenix/utils/motor_abtppn.py`](fenix/utils/motor_abtppn.py): motor matemático de simulación de Redes de Petri.
- [`Manual_Usuario_MOM.md`](Manual_Usuario_MOM.md): guía de usuario para configuración y operación de planta.
- [`Manual_Tecnico_Final_MOM.md`](Manual_Tecnico_Final_MOM.md) / [`Manual_Tecnico_MOM.md`](Manual_Tecnico_MOM.md): manuales de arquitectura técnica (diseño de BD, disparadores de eventos, APIs, metodología de modelado).
- [`Filosofia_Integracion_Holonica.md`](Filosofia_Integracion_Holonica.md): filosofía introductoria de los sistemas holónicos y la transición histórica desde el control jerárquico (contexto del proyecto PDVSA).
- [`FenixDescripcionGeneral.md`](FenixDescripcionGeneral.md), [`FILOSOFIA.md`](FILOSOFIA.md), [`FLUJO_DATOS.md`](FLUJO_DATOS.md), [`geminiInicio.md`](geminiInicio.md), [`Glosario_de_Terminos.md`](Glosario_de_Terminos.md): filosofía de diseño adicional, especificación de flujo de datos y glosario de términos.

---

## 📖 Publicaciones Científicas

Fénix se desarrolla como parte de un proyecto de investigación académica en la **Universidad de los Andes (ULA), Mérida, Venezuela**. Sus bases teóricas y resultados empíricos están detallados en dos artículos complementarios:

1. **Parte I: Bases Conceptuales y Optimización**
   *Título:* "A Holonic PPR Framework and Petri Net Formalism for Cost-Optimal Production Scheduling in SMEs"
   *Enfoque:* definición formal del modelo matemático AB-TPPN, dependencia de trayectoria de los costos de producción bajo límites de rendimiento de recursos, y el motor de programación Branch-and-Bound.
2. **Parte II: Integración SCADA y Validación Empírica**
   *Título:* "SCADA-Driven Model Calibration, Condition Monitoring, and Empirical Cost Verification in Holonic Manufacturing"
   *Enfoque:* calibración de parámetros en tiempo real usando timestamps SCADA en vivo vía un estimador EWMA, seguimiento no intrusivo de degradación usando el Ratio de Desviación de Energía (EDR), y validación sobre un dataset de 14 meses con 10,089 órdenes de producción.

---

## 🎓 Citación

Si usas Fénix en tu investigación académica, por favor cita los artículos complementarios:

```bibtex
@article{ChaconCardillo2026_PartI,
  author  = {Chac{\'o}n, Edgar and Cardillo, Juan},
  title   = {A Holonic PPR Framework and Petri Net Formalism for Cost-Optimal Production Scheduling in SMEs},
  journal = {Computers in Industry},
  year    = {2026},
  note    = {Under review}
}

@article{ChaconCardillo2026_PartII,
  author  = {Chac{\'o}n, Edgar and Cardillo, Juan},
  title   = {SCADA-Driven Model Calibration, Condition Monitoring, and Empirical Cost Verification in Holonic Manufacturing},
  journal = {Computers in Industry},
  year    = {2026},
  note    = {Under review}
}
```

---

## 📄 Licencia

Este proyecto está licenciado bajo **GNU Affero General Public License v3.0 (AGPL-3.0)** — ver el archivo [`LICENSE`](LICENSE).

En términos simples: puedes usar, modificar y redistribuir Fénix libremente, incluso con fines comerciales (por ejemplo, ofreciendo servicios de soporte o consultoría a una empresa que ya lo usa). La única condición fuerte es que si tomas una versión modificada de Fénix y la ofreces a terceros — incluso solo como servicio accesible por red, sin distribuir el software — debes poner a disposición de esos terceros el código fuente de tus modificaciones. Esto busca que las mejoras hechas sobre el núcleo público del sistema beneficien también a otras PyMEs, y no queden encerradas dentro de un producto comercial cerrado.

> **Nota:** el módulo de planificación (Branch-and-Bound / selección de ruta óptima) y el módulo de aprendizaje no forman parte de este repositorio por el momento y se gestionan por separado.
