# debug_orden.py
from modelos.declarative_base import SessionLocal
from modelos.Producto import HolonRuta, AsignacionRecurso
from modelos.Recursos import Recurso

session = SessionLocal()
producto_id = 3
cantidad = 1000
prioridad = 1

# 1. Verificar HolonRuta
rutas = session.query(HolonRuta).filter(
    HolonRuta.producto_id == producto_id,
    HolonRuta.activa == True
).all()
print(f"Rutas encontradas para producto_id={producto_id}: {len(rutas)}")
for r in rutas:
    print(f"  id={r.id}, nombre={r.nombre}, activa={r.activa}, condiciones={r.condiciones}")

if not rutas:
    print("❌ No hay rutas asociadas al producto. Actualiza el producto_id del holon_ruta id=1:")
    # Forzar actualización
    holon = session.query(HolonRuta).get(1)
    if holon:
        holon.producto_id = 3
        holon.activa = True
        session.commit()
        print("   ✅ Forzada actualización. Vuelve a ejecutar el script.")
    session.close()
    exit()

# 2. Probar la primera ruta (id=1) manualmente
ruta = rutas[0]
condiciones = ruta.condiciones or {}
lote_min = condiciones.get('lote_minimo_kg', 0)
lote_max = condiciones.get('lote_maximo_kg', float('inf'))
prioridad_min = condiciones.get('prioridad_minima', 1)
print(f"Condiciones: lote_min={lote_min}, lote_max={lote_max}, prioridad_min={prioridad_min}")
print(f"Cantidad={cantidad} (¿dentro? {lote_min <= cantidad <= lote_max})")
print(f"Prioridad={prioridad} (¿>= prioridad_min? {prioridad >= prioridad_min})")

if cantidad < lote_min or cantidad > lote_max:
    print("❌ La cantidad no cumple rango de lote.")
elif prioridad < prioridad_min:
    print("❌ La prioridad no cumple.")
else:
    print("✅ Condiciones cumplidas. Verificando asignaciones de recursos...")
    asignaciones = session.query(AsignacionRecurso).filter_by(holon_ruta_id=ruta.id).all()
    print(f"   Asignaciones encontradas: {len(asignaciones)}")
    for a in asignaciones:
        rec = session.query(Recurso).get(a.recurso_id)
        if rec:
            print(f"     - Etapa {a.etapa_ruta_id}: recurso '{rec.nombre}' (id={rec.id})")
        else:
            print(f"     ❌ Recurso_id={a.recurso_id} NO EXISTE en tabla recurso")
    if len(asignaciones) == 0:
        print("❌ No hay asignaciones para esta ruta. La orden no puede crearse.")
    else:
        # Simular creación de orden
        from servicios.seguimiento_ordenes import ServicioSeguimiento
        servicio = ServicioSeguimiento(session)
        orden = servicio.crear_orden(producto_id, cantidad, prioridad, 'Prueba')
        print(f"✅ Orden creada: ID={orden.id}")
session.close()