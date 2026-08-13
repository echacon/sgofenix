#!/usr/bin/env python3
"""
Crear orden de producción con validación de:
- Fórmula (insumos)
- Lotes mínimos/máximos
- Conexiones físicas entre equipos de etapas consecutivas
"""

import sys
import argparse
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.Producto import Producto, HolonRuta, AsignacionRecurso, Formula, InsumoFormula
from modelos.Recursos import Recurso, ConexionFisica
from modelos.Taxonomia import EtapaRuta

def validar_conexiones_fisicas(session, holon_ruta):
    """
    Valida que existan conexiones físicas entre los recursos asignados a etapas consecutivas.
    Retorna (bool, mensaje).
    """
    if not holon_ruta.patron:
        return False, "La ruta no tiene un patrón asociado."
    
    # Obtener las etapas del patrón en orden (según los arcos del patrón)
    # Primero, obtener todas las transiciones y arcos para determinar el orden
    patron = holon_ruta.patron
    # Asumiendo que las etapas están en el orden de los arcos de entrada/salida de transiciones
    # Método simple: obtener las etapas ordenadas por nombre o por algún campo 'orden' si existe.
    # Alternativa: recorrer las transiciones para construir secuencia.
    # Por simplicidad, usaremos las etapas ordenadas alfabéticamente (no es correcto).
    # Mejor: usar el orden definido en el patrón a partir de las transiciones.
    # Construir grafo de etapas: transiciones conectan etapas.
    grafo = {}
    for trans in patron.transiciones:
        # Arcos de entrada: desde una etapa hacia la transición
        for arc_ent in trans.arc_ent_l:
            etapa_origen = arc_ent.etapa
            # Arcos de salida: desde la transición hacia una etapa
            for arc_sal in trans.arc_sal_l:
                etapa_destino = arc_sal.etapa
                if etapa_origen.id not in grafo:
                    grafo[etapa_origen.id] = []
                grafo[etapa_origen.id].append(etapa_destino.id)
    
    # Orden topológico simple (si no hay ciclos)
    orden = []
    visitados = set()
    def dfs(nodo):
        if nodo in visitados:
            return
        visitados.add(nodo)
        for vecino in grafo.get(nodo, []):
            dfs(vecino)
        orden.append(nodo)
    for nodo in grafo:
        if nodo not in visitados:
            dfs(nodo)
    orden.reverse()  # orden topológico
    
    # Mapa de etapa_id a recurso asignado
    asignaciones = {}
    for asig in holon_ruta.asignaciones:
        if asig.recurso_id:
            asignaciones[asig.etapa_ruta_id] = asig.recurso_id
    
    errores = []
    for i in range(len(orden)-1):
        etapa_id_origen = orden[i]
        etapa_id_destino = orden[i+1]
        recurso_id_origen = asignaciones.get(etapa_id_origen)
        recurso_id_destino = asignaciones.get(etapa_id_destino)
        if not recurso_id_origen or not recurso_id_destino:
            errores.append(f"Falta asignación de recurso para alguna etapa (ids: {etapa_id_origen}, {etapa_id_destino})")
            continue
        # Verificar conexión física entre los recursos
        conexion = session.query(ConexionFisica).filter(
            ((ConexionFisica.recurso_origen_id == recurso_id_origen) & (ConexionFisica.recurso_destino_id == recurso_id_destino)) |
            ((ConexionFisica.recurso_origen_id == recurso_id_destino) & (ConexionFisica.recurso_destino_id == recurso_id_origen))
        ).first()
        if not conexion:
            # Obtener nombres para mensaje
            recurso_origen = session.query(Recurso).get(recurso_id_origen)
            recurso_destino = session.query(Recurso).get(recurso_id_destino)
            errores.append(f"No existe conexión física entre {recurso_origen.codigo if recurso_origen else '?'} y {recurso_destino.codigo if recurso_destino else '?'}")
    
    if errores:
        return False, "\n".join(errores)
    return True, "Todas las conexiones físicas son válidas."


def obtener_etapas_ordenadas(patron):
    """
    Devuelve una lista de etapas en el orden de flujo del patrón.
    Asume un patrón lineal (sin bifurcaciones).
    """
    if not patron.transiciones:
        return list(patron.etapasRuta)  # sin transiciones, todas las etapas (sin orden definido)
    
    # Construir mapeo: etapa -> transiciones_salida, transicion -> etapas_entrada, etapas_salida
    # Para simplificar, encontramos la transición inicial: aquella que no tiene arcos de entrada desde otras transiciones
    # (o que tiene arcos de entrada solo de etapas sin transiciones previas).
    # Método práctico: buscar una transición que no aparezca como destino de un arco de salida de otra transición.
    
    # Mapear transiciones a sus etapas de entrada
    trans_entradas = {t: [arc.etapa for arc in t.arc_ent_l] for t in patron.transiciones}
    trans_salidas = {t: [arc.etapa for arc in t.arc_sal_l] for t in patron.transiciones}
    
    # Encontrar transición sin predecesoras (ninguna otra transición tiene arco de salida hacia esta)
    todas_trans = set(patron.transiciones)
    trans_con_predecesor = set()
    for t in patron.transiciones:
        for etapa_salida in trans_salidas[t]:
            # Ver si alguna otra transición tiene esta etapa como entrada
            for otra_t in patron.transiciones:
                if otra_t != t and etapa_salida in trans_entradas.get(otra_t, []):
                    trans_con_predecesor.add(otra_t)
    trans_inicial = todas_trans - trans_con_predecesor
    if not trans_inicial:
        # Si no se encuentra, tomar la primera transición por id
        trans_inicial = [patron.transiciones[0]]
    else:
        trans_inicial = list(trans_inicial)
    
    # Recorrido lineal
    etapas_orden = []
    visitadas = set()
    actual_trans = trans_inicial[0]
    
    while actual_trans:
        # Agregar etapas de entrada que no estén ya visitadas
        for etapa in trans_entradas.get(actual_trans, []):
            if etapa not in visitadas:
                etapas_orden.append(etapa)
                visitadas.add(etapa)
        # Luego agregar etapas de salida
        for etapa in trans_salidas.get(actual_trans, []):
            if etapa not in visitadas:
                etapas_orden.append(etapa)
                visitadas.add(etapa)
        # Determinar siguiente transición: buscar una que tenga como entrada alguna etapa de salida de la actual
        siguiente = None
        for etapa_sal in trans_salidas.get(actual_trans, []):
            for otra_t in patron.transiciones:
                if otra_t != actual_trans and etapa_sal in trans_entradas.get(otra_t, []):
                    siguiente = otra_t
                    break
            if siguiente:
                break
        actual_trans = siguiente
    
    return etapas_orden

def main():
    parser = argparse.ArgumentParser(description="Crear orden de producción con validaciones")
    parser.add_argument("--producto", required=True, help="Código del producto (ej. LAT-1000)")
    parser.add_argument("--cantidad", type=float, required=True, help="Cantidad a producir (kg)")
    parser.add_argument("--fecha_requerida", help="Fecha requerida (YYYY-MM-DD). Por defecto hoy+7 días")
    parser.add_argument("--ruta", help="Nombre de la ruta (holón). Si no se especifica, se listan disponibles")
    parser.add_argument("--prioridad", type=int, default=1, help="Prioridad 1=normal, 2=urgente, 3=express")
    parser.add_argument("--observaciones", default="", help="Observaciones")
    args = parser.parse_args()

    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    # Buscar producto
    producto = session.query(Producto).filter_by(codigo=args.producto).first()
    if not producto:
        print(f"❌ Producto '{args.producto}' no encontrado.")
        sys.exit(1)

    # Holones activos
    holones = session.query(HolonRuta).filter_by(producto_id=producto.id, activa=True).all()
    if not holones:
        print(f"❌ No hay rutas activas para el producto {producto.codigo}.")
        sys.exit(1)

    # Seleccionar ruta
    if args.ruta:
        holon = next((h for h in holones if h.nombre == args.ruta), None)
        if not holon:
            print(f"❌ Ruta '{args.ruta}' no encontrada. Rutas disponibles:")
            for h in holones:
                print(f"   - {h.nombre}")
            sys.exit(1)
    else:
        if len(holones) == 1:
            holon = holones[0]
        else:
            print(f"Rutas disponibles para {producto.codigo}:")
            for i, h in enumerate(holones, 1):
                print(f"   {i}. {h.nombre}")
            opcion = input("Seleccione una ruta (número): ")
            try:
                idx = int(opcion) - 1
                holon = holones[idx]
            except:
                print("❌ Opción inválida")
                sys.exit(1)

    print(f"\n✅ Ruta seleccionada: {holon.nombre}")

    # 1. Validar condiciones de lote
    if not holon.cumple_condiciones(args.cantidad, args.prioridad):
        lote_min = holon.get_condicion("lote_minimo_kg", 0)
        lote_max = holon.get_condicion("lote_maximo_kg", float('inf'))
        print(f"❌ Cantidad {args.cantidad} kg no cumple condiciones de la ruta.")
        print(f"   Rango permitido: {lote_min} - {lote_max} kg")
        sys.exit(1)

    # 2. Mostrar fórmula y calcular necesidades
    formula = holon.formula
    if not formula:
        print("⚠️ ATENCIÓN: Esta ruta no tiene fórmula definida. No se podrá gestionar materiales.")
        respuesta = input("   ¿Continuar de todos modos? (s/N): ")
        if respuesta.lower() != 's':
            sys.exit(0)
    else:
        print("\n📋 FÓRMULA (insumos por lote):")
        print(f"   Lote estándar: {formula.cantidad_producir_lote} {formula.unidad_medida}")
        print("   Insumos requeridos para esta orden:")
        total_insumos = []
        for insumo in formula.insumos:
            cantidad_total = (args.cantidad / formula.cantidad_producir_lote) * insumo.cantidad
            print(f"     - {insumo.nombre_insumo}: {cantidad_total:.2f} {insumo.unidad}  "
                  f"(costo unitario estimado: {insumo.costo_unitario_estimado})")
            total_insumos.append(f"{insumo.nombre_insumo}:{cantidad_total:.2f}{insumo.unidad}")
        # Opcional: guardar en observaciones
        args.observaciones += f" | Insumos: {', '.join(total_insumos)}"

    # 3. Validar conexiones físicas entre equipos
    print("\n🔌 Verificando conexiones físicas entre recursos...")
    conexiones_ok, msg_conexiones = validar_conexiones_fisicas(session, holon)
    if not conexiones_ok:
        print(f"❌ {msg_conexiones}")
        sys.exit(1)
    else:
        print(f"   ✅ {msg_conexiones}")

    # 4. Mostrar asignaciones de recursos por etapa (útil)
    print("\n📌 Asignaciones de recursos por etapa:")
    asignaciones = session.query(AsignacionRecurso).filter_by(holon_ruta_id=holon.id).all()
    recursos_por_etapa = {}
    for asig in asignaciones:
        recurso = session.query(Recurso).get(asig.recurso_id)
        print(f"   Etapa '{asig.etapa.nombre}' -> {recurso.codigo} ({recurso.nombre})")
        recursos_por_etapa[asig.etapa.nombre] = recurso.codigo

    # 5. Generar número de orden
    ultima_orden = session.query(OrdenProduccion).order_by(OrdenProduccion.id.desc()).first()
    if ultima_orden and ultima_orden.numero_orden:
        try:
            last_num = int(ultima_orden.numero_orden.split('-')[-1])
            next_num = last_num + 1
        except:
            next_num = 1
    else:
        next_num = 1
    numero_orden = f"ORD-{datetime.now().strftime('%Y%m%d')}-{next_num:04d}"

    # Fecha requerida
    if args.fecha_requerida:
        fecha_req = datetime.strptime(args.fecha_requerida, "%Y-%m-%d").date()
    else:
        fecha_req = date.today() + timedelta(days=7)

    # Crear orden
    orden = OrdenProduccion(
        numero_orden=numero_orden,
        producto_id=producto.id,
        holon_ruta_id=holon.id,
        cantidad=args.cantidad,
        estado="pendiente",
        prioridad=args.prioridad,
        fecha_requerida=fecha_req,
        observaciones=args.observaciones
    )
    session.add(orden)
    session.commit()

    print(f"\n✅ Orden creada exitosamente:")
    print(f"   ID: {orden.id}")
    print(f"   Número: {orden.numero_orden}")
    print(f"   Producto: {producto.codigo} - {producto.nombre}")
    print(f"   Ruta: {holon.nombre}")
    print(f"   Cantidad: {orden.cantidad} kg")
    print(f"   Fecha requerida: {orden.fecha_requerida}")
    print(f"\n⚠️ Para ejecutar eventos, usa orden_id={orden.id} y los recursos mostrados.")
    session.close()

if __name__ == "__main__":
    main()