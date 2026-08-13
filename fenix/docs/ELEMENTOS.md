# Flujo de Datos en FÉNIX

## Flujo 1: Creación de una Orden de Producción

### Paso a Paso

```
1. Usuario (planificador) ingresa orden
   │
   ├── Producto: "LAT-1000"
   ├── Cantidad: 1000 kg
   └── Fecha requerida: 2025-05-20
   
2. Sistema selecciona ruta automáticamente
   │
   ├── Busca HolonRuta para producto
   ├── Filtra por cantidad, prioridad, vigencia
   └── Selecciona la de mayor prioridad
   
3. Se crea registro en orden_produccion
   │
   └── estado = "pendiente"

4. Se instancian todas las redes de la ruta
   │
   ├── Integradora (1 instancia)
   ├── Dispersión (1 instancia por recurso asignado)
   └── Dilución (1 instancia por recurso asignado)

5. Token coloreado inicial
   │
   ├── orden_id = "ORD-1234"
   ├── material = 1000 kg
   ├── coste = 0
   └── timestamp = ahora

6. Procesar transiciones automáticas (trigger=None)
   │
   └── Se estabiliza la red (marcado inicial)
```

### Registros en Base de Datos

```sql
-- Orden
INSERT INTO orden_produccion (id, numero_orden, producto_id, cantidad, estado)
VALUES (1, 'ORD-001', 1, 1000, 'pendiente');

-- Instancias
INSERT INTO instancia_red (orden_id, tipo, marcado, token_o, token_m, token_c, token_t)
VALUES 
  (1, 'integradora', '{"p1":1}', 'ORD-001', 1000, 0, NOW()),
  (1, 'dispersion', '{"p14":1}', 'ORD-001', 1000, 0, NOW()),
  (1, 'dilucion', '{"p1":1}', 'ORD-001', 1000, 0, NOW());
```

---

## Flujo 2: Evento desde Planta (SCADA/Tablet)

### Formato del Evento

```json
{
  "tipo": "evento_planta",
  "recurso": "Dispersor_22",
  "red": "dispersion",
  "transicion": "Asignar equipo",
  "datos": {
    "operador": "Juan Pérez",
    "timestamp": "2025-05-12T08:00:00"
  }
}
```

### Procesamiento Interno

```
1. Orquestador recibe evento
   │
   └── Busca instancia por (recurso, red)
   
2. Verifica que la transición esté habilitada
   │
   ├── Precondiciones (tokens en lugares de entrada)
   └── Trigger = 200 (evento externo) → OK con mensaje_externo=True

3. Dispara la transición
   │
   ├── Consume tokens de entrada
   ├── Produce tokens en salida
   └── Token coloreado se actualiza (material, coste, timestamp)

4. Persiste EventoRed
   │
   ├── transicion_nombre = "Asignar equipo"
   ├── invariantes = {"recurso": "Dispersor_22", "operador": "Juan Pérez"}
   └── token_m, token_c

5. Actualiza instancia_red (marcado, token)

6. Procesa automáticas habilitadas (trigger=None)

7. Genera mensajes pendientes (trigger=201)
```

### Registros Generados

```sql
-- Evento
INSERT INTO evento_red (orden_id, instancia_id, transicion_nombre, invariantes, token_m, token_c)
VALUES (1, 2, 'Asignar equipo', '{"recurso":"Dispersor_22"}', 1000, 0);

-- Mensaje pendiente (si la transición genera salida)
INSERT INTO mensaje_pendiente (orden_id, red_origen, transicion_origen, red_destino, evento)
VALUES (1, 'dispersion', 'Asignar equipo', 'integradora', 'Iniciar disp');
```

---

## Flujo 3: Handshake entre Redes (Dispersión → Dilución)

### Contexto Físico

En la planta real:

1. **Dispersor_22** produce 950 kg de pasta base
2. Operador abre válvula y bombea a **Diluidor_1**
3. El bombeo toma 2 minutos
4. Sensor de flujo detecta que el material llegó
5. Diluidor comienza su ciclo

### Flujo de Eventos en el Sistema

```
T=09:00:00 - Dispersión: Operador confirma "Fin solidos"
   │
   └── Se dispara t18 (Fin solidos) en dispersión
   
T=09:00:30 - Dispersión: Automático "Dispersar" (30 min)
   │
   └── Trigger=None, se dispara automáticamente
   
T=09:30:30 - Dispersión: Operador toma muestra → "Chequeo"
   │
   └── Se dispara t7 (Chequeo)
   
T=09:35:00 - Laboratorio: Analiza muestra → "Chequeando"
   │
   └── Se dispara t19 (Chequeando) en dispersión
   
T=09:36:00 - Producto OK: Operador confirma "Transportar"
   │
   └── Se dispara t41 (Transportar) en dispersión
   └── Genera evento "Fin dispersion" → integradora
   
T=09:36:01 - Integradora recibe "Fin dispersion"
   │
   └── Dispara transición t11 en integradora
   └── Genera evento "Diluidor listo" → dispersión
   
T=09:36:02 - Dispersión recibe "Diluidor listo"
   │
   └── Se dispara t8 (Diluidor listo) en dispersión
   └── Dispersión queda en p12 (Transportar a DIL)
   
T=09:36:05 - SCADA: Bomba de transferencia arranca
   │
   └── Evento "Transportando" → t2 en dispersión
   
T=09:38:05 - SCADA: Flujo acumulado llega a 950 kg
   │
   └── Evento "Descargar" → t11 en dispersión
   
T=09:38:10 - Dilución: Confirma recepción "Recibir dispersion"
   │
   └── Se dispara t14 en dilución
   
T=09:38:15 - Dilución: Comienza "Carga auto" → t20 en dilución
```

### Mensajes Pendientes (Handshake)

| Tiempo | Origen | Evento | Destino |
|--------|--------|--------|---------|
| 09:36:00 | dispersión.t41 | Fin dispersion | integradora |
| 09:36:01 | integradora.t11 | Diluidor listo | dispersión |

**El mensaje "Diluidor listo" es el handshake que sincroniza ambas redes.**

---

## Flujo 4: Lectura Periódica de Eventos

### Bucle Principal (Orquestador)

```python
while sistema_activo:
    # 1. Leer eventos nuevos de archivos/SCADA
    eventos = leer_eventos_desde_ultima_fecha()
    
    # 2. Procesar en orden cronológico
    for evento in sorted(eventos, key=lambda e: e['timestamp']):
        procesar_evento_planta(evento)
        
        # 3. Procesar mensajes pendientes (handshakes)
        procesar_mensajes_pendientes()
        
        # 4. Verificar temporizadores (trigger=202)
        verificar_temporizadores()
    
    # 5. Esperar 1 minuto
    time.sleep(60)
```

### Archivos de Eventos (Simulación)

Para pruebas sin SCADA real, se usan archivos JSON:

```json
// eventos_orden1.json
{
  "eventos": [
    {"orden_id": 3, "recurso": "Dispersor_22", "red": "dispersion", 
     "transicion": "Asignar equipo", "fecha": "2025-05-12T08:00:00"},
    {"orden_id": 3, "recurso": "Dispersor_22", "red": "dispersion", 
     "transicion": "Cargar auto", "fecha": "2025-05-12T08:05:00"}
  ]
}
```

---

## Flujo 5: Recuperación después de Reinicio

### Escenario

El sistema se apaga abruptamente mientras una orden está en proceso.

### Recuperación

```python
def recuperar_sistema():
    # 1. Cargar todas las instancias activas desde BD
    instancias = session.query(InstanciaRed).filter_by(activa=True)
    
    # 2. Reconstruir en memoria
    for inst_bd in instancias:
        inst_mem = InstanciaRedMem(
            id=inst_bd.id,
            red_nombre=inst_bd.tipo,
            marcado=inst_bd.marcado,
            token=TokenColoreado(...)
        )
        motor.instancias[inst_bd.id] = inst_mem
    
    # 3. Cargar mensajes pendientes no consumidos
    mensajes = session.query(MensajePendiente).filter_by(consumido=False)
    
    # 4. Reprocesar (ordenados por fecha)
    for msg in sorted(mensajes, key=lambda m: m.fecha_creacion):
        # El orquestador decidirá si es válido re-procesar
        orquestador.procesar_mensaje(msg)
```

**El sistema sigue exactamente donde quedó, sin pérdida de información.**

---

## Diagrama de Secuencia: Orden Completa

```
Planificador    Orquestador    MotorPetri    Integradora    Dispersión    Dilución    SCADA
     │               │              │             │             │           │          │
     │──Crear orden──→│              │             │             │           │          │
     │               │──Instanciar──→│             │             │           │          │
     │               │              │──Crear─────→│             │           │          │
     │               │              │──Crear──────────────────→│           │          │
     │               │              │──Crear────────────────────────────────→│          │
     │               │              │             │             │           │          │
     │               │              │──Auto───→   │             │           │          │
     │               │              │             │──Auto───→   │           │          │
     │               │              │             │             │──Auto───→ │          │
     │               │              │             │             │           │          │
     │               │←─────────────────────────Respuesta──────────────────→│          │
     │               │              │             │             │           │          │
     │               │              │             │   SCADA: Asignar equipo  │          │
     │               │←────────────────────────────────────────Evento────────│          │
     │               │──Disparar───→│             │             │           │          │
     │               │              │             │             │           │          │
     │               │              │   ... (ciclo completo de producción)   │          │
     │               │              │             │             │           │          │
     │               │              │             │   SCADA: Descargar        │          │
     │               │←────────────────────────────────────────Evento────────│          │
     │               │──Disparar───→│             │             │           │          │
     │               │              │             │             │           │          │
     │               │              │             │             │   Confirmar recepción
     │               │←────────────────────────────────────────────────Evento→│          │
     │               │──Disparar─────────────────────────────────────────────→│          │
     │               │              │             │             │           │          │
     │               │←──────────────────────────Orden completada──────────────────────│
     │←───Notificación──│              │             │             │           │          │
```

---

## Resumen de Tablas y sus Roles

| Tabla | Rol en el Flujo |
|-------|-----------------|
| `orden_produccion` | Cabecera de la orden |
| `instancia_red` | Estado actual de cada red |
| `evento_red` | Trazabilidad de cada paso |
| `mensaje_pendiente` | Comunicación entre redes |
| `producto` | Qué se fabrica |
| `holon_ruta` | Cómo se fabrica (qué recursos) |
| `recurso` | Quién/Qué lo fabrica |
| `configuracion_encadenamiento` | Cómo se comunican las redes |
```
