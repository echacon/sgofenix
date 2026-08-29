fenix
│   .gitignore
│   app.py
│   convert_yaml_to_utf8.py
│   crear_orden.py
│   eventos_exito_orden1.json
│   eventos_orden1.json
│   eventos_orden_errada_disp.json
│   eventos_scada.json
│   fenix.db
│   fenix.log
│   fenix.sqbpro
│   inicializar_orden.py
│   main.py
│   orden_error_dilucion.json
│   pyproject.toml
│
├───docs
│       DescripcionModeloProducto.md
│       ELEMENTOS.md
│       estructuraArchivos.md
│       plan_refactorizacion.md
│
├───importadores
│   │   cargador_yaml.py
│   │   importador_encadenamiento.py
│   │   importador_patrones.py
│   │   importador_productos.py
│   │   importador_recursos.py
│   │   importador_taxonomia.py
│   │   importar_config_yaml.py
│   │   importar_encadenamiento.py
│   │   importar_patron_completo.py
│   │   __init__.py
│   │
│   └───__pycache__
│           cargador_yaml.cpython-312.pyc
│           importador_encadenamiento.cpython-312.pyc
│           importador_patrones.cpython-312.pyc
│           importador_recursos.cpython-312.pyc
│           __init__.cpython-312.pyc
│
├───logs
├───modelos
│   │   Colaevento.py
│   │   declarative_base.py
│   │   DocumentosNegocio.py
│   │   Encadenamiento.py
│   │   MensajePendiente.py
│   │   ProcesoNegocio.py
│   │   ProcesoOcurrente.py
│   │   Producto.py
│   │   Recursos.py
│   │   RedPetri.py
│   │   RutaProducto.py
│   │   Taxonomia.py
│   │   Usuario.py
│   │   Versionamiento.py
│   │   __init__.py
│   │
│   └───__pycache__
│           Colaevento.cpython-312.pyc
│           declarative_base.cpython-312.pyc
│           DocumentosNegocio.cpython-312.pyc
│           Encadenamiento.cpython-312.pyc
│           MensajePendiente.cpython-312.pyc
│           ProcesoNegocio.cpython-312.pyc
│           ProcesoOcurrente.cpython-312.pyc
│           Producto.cpython-312.pyc
│           Recursos.cpython-312.pyc
│           Recursos_backup.cpython-312.pyc
│           RedPetri.cpython-312.pyc
│           RutaProducto.cpython-312.pyc
│           Taxonomia.cpython-312.pyc
│           Usuario.cpython-312.pyc
│           Versionamiento.cpython-312.pyc
│           __init__.cpython-312.pyc
│
├───ontologia
│   ├───empresa
│   │       00_empresa.yaml
│   │       01_familias.yaml
│   │       02_tipos_operacion.yaml
│   │       03_patrones.yaml
│   │       04_recursos.yaml
│   │       05_capacidades.yaml
│   │       06_productos.yaml
│   │       07_conectividad.yaml
│   │
│   ├───rutas
│   │   ├───BASEAGUA_DIS_DIL
│   │   │   │   asignaciones_recursos.yaml
│   │   │   │   config_original.json
│   │   │   │   encadenamiento.yaml
│   │   │   │   metadatos.yaml
│   │   │   │
│   │   │   └───redes
│   │   │           DIS_DIL_dilucion.pnml
│   │   │           DIS_DIL_dispersion.pnml
│   │   │           DIS_DIL_integradora.pnml
│   │   │
│   │   ├───BASEAGUA_DIS_MOL
│   │   └───PROCESADOS_v1
│   │       └───redes
│   └───versionado
├───routes
│       auth.py
│       carga_productos.py
│       carga_recursos.py
│       carga_taxonomia.py
│       operador.py
│       __init__.py
│
├───scripts
│   │   asociar_ruta_producto.py
│   │   cargar_asignaciones.py
│   │   cargar_estructura_empresa.py
│   │   cargar_ontologia.py
│   │   cargar_ontologia_completo.py
│   │   cargar_productos.py
│   │   cargar_recursos.py
│   │   cargar_rutas_y_encadenamiento.py
│   │   cargar_todo.py
│   │   carga_inicial.py
│   │   recrear_holon_ruta.py
│   │   validar_protocolo.py
│   │   validar_yaml_empresa.py
│   │   verificar_estado_completo.py
│   │   __init__.py
│   │
│   ├───core
│   │       init_db.py
│   │
│   ├───mantenimiento
│   │       diagnosticar_asignacion.py
│   │       diagnosticar_instancias.py
│   │       diagnosticar_mensajes.py
│   │       diagnosticar_pnml.py
│   │       diagnosticar_redes_cargadas.py
│   │       listar_modelos.py
│   │       resetear_orden.py
│   │       validar_yaml.py
│   │       verificar_archivos_redes.py
│   │       verificar_config.py
│   │       verificar_estado_completo.py
│   │       verificar_modelo_ruta.py
│   │       verificar_redes.py
│   │       verificar_ruta_y_marcados.py
│   │
│   ├───migraciones
│   │       agregar_version_ruta_id.py
│   │       crear_tablas_ocurrentes.py
│   │       crear_todo_desde_cero.py
│   │       fix_config_directo.py
│   │       fix_crear_instancia_calls.py
│   │       fix_db_schema.py
│   │       fix_tipo_recurso_descripcion.py
│   │       inicializar_completo.py
│   │       inicializar_datos.py
│   │       inicializar_entorno_prueba.py
│   │       inicializar_ruta_producto.py
│   │       inicializar_sistema.py
│   │       inicializar_tablas_redes.py
│   │       renombrar_pnml_a_nombres_originales.py
│   │       renombrar_pnml_en_ruta.py
│   │       update_ruta_config.py
│   │
│   ├───pruebas
│   │       ejemplo_proceso_negocio.py
│   │       eventos_exito copy.json
│   │       eventos_exito.json
│   │       init_prueba.py
│   │       procesar_secuencia.py
│   │       prueba_orden.py
│   │       simular_con_estado_completo.py
│   │       simular_desde_json.py
│   │       simular_secuencia_real.py
│   │       test_import_metadatos.py
│   │       test_ruta_producto.py
│   │
│   └───__pycache__
│           cargar_asignaciones.cpython-312.pyc
│           cargar_ontologia_completo.cpython-312.pyc
│           cargar_productos.cpython-312.pyc
│           cargar_recursos.cpython-312.pyc
│           cargar_rutas_y_encadenamiento.cpython-312.pyc
│           carga_inicial.cpython-312.pyc
│           __init__.cpython-312.pyc
│
├───servicios
│   │   cola_eventos.py
│   │   grafo_conectividad.py
│   │   orquestador.py
│   │   seguimiento_ordenes.py
│   │   selector_ruta.py
│   │   validador_modelos.py
│   │   verificador_terminacion.py
│   │
│   └───__pycache__
│           cola_eventos.cpython-312.pyc
│           orquestador.cpython-312.pyc
│           seguimiento_ordenes.cpython-312.pyc
│           validador_modelos.cpython-312.pyc
│           verificador_terminacion.cpython-312.pyc
│
├───static
│   └───css
├───templates
│   │   base.html
│   │   carga_errores.html
│   │   carga_productos.html
│   │   carga_recursos.html
│   │   carga_taxonomia.html
│   │   login.html
│   │
│   └───operador
│           dashboard.html
│
├───tests
│       tests_README.md
│       __init__.py
│
├───uploads
├───utils
│   │   disponibilidad_recursos.py
│   │   global_reachability.py
│   │   motor_abtppn.py
│   │   parser_pnml.py
│   │   reachability.py
│   │   validador_modelos.py
│   │
│   └───__pycache__
│           motor_abtppn.cpython-312.pyc
│           motor_abtppn_backup.cpython-312.pyc
│           parser_pnml.cpython-312.pyc
│
└───validadores
    │   validador_encadenamiento.py
    │   validador_productos.py
    │   validador_recursos.py
    │   validador_taxonomia.py
    │   __init__.py
    │
    └───__pycache__
            validador_recursos.cpython-312.pyc
            validador_taxonomia.cpython-312.pyc
            __init__.cpython-312.pyc
