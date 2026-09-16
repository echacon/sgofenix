# Estructura de Archivos del Proyecto FÉNIX

```text
sgofenix/
│   .gitignore
│   FILOSOFIA.md
│   FLUJO_DATOS.md
│   FenixDescripcionGeneral.md
│   Filosofia_Integracion_Holonica.md
│   Glosario_de_Terminos.md
│   LICENSE
│   Manual_Tecnico_Final_MOM.md
│   Manual_Tecnico_MOM.md
│   Manual_Usuario_MOM.md
│   README.md
│   ReporteTecnico_MarcoHolonico.md
│
├───fenix                           <── CORE / LIBRERÍA DEL SISTEMA
│   │   __init__.py
│   │   fenix.db
│   │   fenix.log
│   │   main.py                     (Orquestador continuo en segundo plano)
│   │   pyproject.toml
│   │
│   ├───docs
│   │       DescripcionModeloProducto.md
│   │       ELEMENTOS.md
│   │       estructuraArchivos.md
│   │       plan_refactorizacion.md
│   │
│   ├───importadores
│   │       cargador_yaml.py
│   │       compilador_recetas.py
│   │       importador_encadenamiento.py
│   │       importador_patrones.py
│   │       importador_productos.py
│   │       importador_recursos.py
│   │       importador_taxonomia.py
│   │       importar_config_yaml.py
│   │       importar_encadenamiento.py
│   │       importar_patron_completo.py
│   │       __init__.py
│   │
│   ├───modelos
│   │       Colaevento.py
│   │       declarative_base.py
│   │       DocumentosNegocio.py
│   │       Encadenamiento.py
│   │       MensajePendiente.py
│   │       ProcesoDescripcion.py
│   │       ProcesoNegocio.py
│   │       ProcesoOcurrente.py
│   │       Producto.py
│   │       Recursos.py
│   │       RedPetri.py
│   │       RutaProducto.py
│   │       Taxonomia.py
│   │       Usuario.py
│   │       Versionamiento.py
│   │       __init__.py
│   │
│   ├───ontologia
│   │   ├───empresa
│   │   │       00_empresa.yaml
│   │   │       01_familias.yaml
│   │   │       02_tipos_operacion.yaml
│   │   │       03_patrones.yaml
│   │   │       04_recursos.yaml
│   │   │       05_capacidades.yaml
│   │   │       06_productos.yaml
│   │   │       07_conectividad.yaml
│   │   │
│   │   ├───modelos_proceso
│   │   │       IND_DIS_MOL_DIL_modelo_dilucion.yaml
│   │   │       IND_DIS_MOL_DIL_modelo_dispersion.yaml
│   │   │       IND_DIS_MOL_DIL_modelo_molinos.yaml
│   │   │
│   │   └───rutas
│   │       └───BASEAGUA_DIS_DIL
│   │           │   asignaciones_recursos.yaml
│   │           │   config_original.json
│   │           │   encadenamiento.yaml
│   │           │   metadatos.yaml
│   │           └───redes
│   │                   DIS_DIL_dilucion.pnml
│   │                   DIS_DIL_dispersion.pnml
│   │                   DIS_DIL_integradora.pnml
│   │
│   ├───servicios
│   │       cola_eventos.py
│   │       grafo_conectividad.py
│   │       orquestador.py
│   │       planificador.py
│   │       seguimiento_ordenes.py
│   │       selector_ruta.py
│   │       validador_modelos.py
│   │       verificador_terminacion.py
│   │       __init__.py
│   │
│   ├───utils
│   │       disponibilidad_recursos.py
│   │       global_reachability.py
│   │       motor_abtppn.py
│   │       parser_pnml.py
│   │       reachability.py
│   │       validador_modelos.py
│   │       __init__.py
│   │
│   └───validadores
│           validador_encadenamiento.py
│           validador_productos.py
│           validador_recursos.py
│           validador_taxonomia.py
│           __init__.py
│
├───web                             <── INTERFAZ WEB Y DASHBOARD
│   │   app.py                      (Servidor Flask y endpoints REST)
│   │
│   ├───routes
│   │       auth.py
│   │       carga_productos.py
│   │       carga_recursos.py
│   │       carga_taxonomia.py
│   │       operador.py
│   │       __init__.py
│   │
│   ├───templates
│   │   │   base.html
│   │   │   carga_errores.html
│   │   │   carga_productos.html
│   │   │   carga_recursos.html
│   │   │   carga_taxonomia.html
│   │   │   login.html
│   │   │
│   │   └───operador
│   │           dashboard.html
│   │
│   └───static
│       └───css
│
├───tools                           <── HERRAMIENTAS DE ADMINISTRACIÓN Y CLI
│   ├───carga
│   │       asociar_ruta_producto.py
│   │       carga_inicial.py
│   │       cargar_asignaciones.py
│   │       cargar_estructura_empresa.py
│   │       cargar_ontologia.py
│   │       cargar_ontologia_completo.py
│   │       cargar_productos.py
│   │       cargar_recursos.py
│   │       cargar_rutas_y_encadenamiento.py
│   │       cargar_todo.py
│   │       generador_yaml_desde_pnml.py
│   │       init_db.py
│   │       recrear_holon_ruta.py
│   │
│   ├───mantenimiento
│   │       convert_yaml_to_utf8.py
│   │       diagnosticar_asignacion.py
│   │       diagnosticar_instancias.py
│   │       diagnosticar_mensajes.py
│   │       diagnosticar_pnml.py
│   │       diagnosticar_redes_cargadas.py
│   │       listar_modelos.py
│   │       resetear_orden.py
│   │       validar_protocolo.py
│   │       validar_yaml.py
│   │       validar_yaml_empresa.py
│   │       verificar_archivos_redes.py
│   │       verificar_config.py
│   │       verificar_estado_completo.py
│   │       verificar_modelo_ruta.py
│   │       verificar_redes.py
│   │       verificar_ruta_y_marcados.py
│   │
│   └───migraciones
│           agregar_version_ruta_id.py
│           crear_tablas_ocurrentes.py
│           crear_todo_desde_cero.py
│           fix_config_directo.py
│           fix_crear_instancia_calls.py
│           fix_db_schema.py
│           fix_tipo_recurso_descripcion.py
│           inicializar_completo.py
│           inicializar_datos.py
│           inicializar_entorno_prueba.py
│           inicializar_ruta_producto.py
│           inicializar_sistema.py
│           inicializar_tablas_redes.py
│           renombrar_pnml_a_nombres_originales.py
│           renombrar_pnml_en_ruta.py
│           update_ruta_config.py
│
└───tests                           <── PRUEBAS Y SIMULACIÓN
    │   tests_README.md
    │
    ├───fixtures
    │       eventos_exito.json
    │       eventos_exito_orden1.json
    │       eventos_orden1.json
    │       eventos_orden_errada_disp.json
    │       eventos_scada.json
    │       orden_error_dilucion.json
    │
    ├───simulador
    │       crear_orden.py
    │       debug_orden.py
    │       ejemplo_proceso_negocio.py
    │       inicializar_orden.py
    │       init_prueba.py
    │       procesar_secuencia.py
    │       prueba_orden.py
    │       simulador_evolucion_completa.py
    │       simulador_tiempo_real.py
    │       simular_con_estado_completo.py
    │       simular_desde_json.py
    │       simular_secuencia_real.py
    │       test_import_metadatos.py
    │       test_ruta_producto.py
    │       verificar_compilador_sesion2.py
    │       verificar_dashboard_api.py
    │       verificar_db_sesion1.py
    │       verificar_ejecucion_sesion4.py
    │
    ├───unit
    └───integracion
```
