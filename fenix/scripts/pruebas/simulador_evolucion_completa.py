# scripts/pruebas/simulador_evolucion_completa.py
import requests
import time
import sys

URL_BASE = "http://127.0.0.1:5000"

def simular_evolucion():
    print("🚀 Iniciando Simulador de Evolución Completa de Redes de Petri...")
    print("------------------------------------------------------------------")
    
    session = requests.Session()
    
    # 1. Login
    print("🔐 Iniciando sesión como admin@fenix.local...")
    res_login = session.post(f"{URL_BASE}/login", data={
        "email": "admin@fenix.local",
        "password": "admin123"
    }, allow_redirects=False)
    
    if res_login.status_code not in (200, 302):
        print("❌ Error al iniciar sesión. ¿Está el servidor corriendo?")
        sys.exit(1)
    print("✅ Sesión iniciada con éxito.")
    
    # 2. Crear una nueva orden
    print("\n⚡ Creando nueva orden de producción para 'Plantilla Ruta Látex' (1000 L)...")
    res_crear = session.post(f"{URL_BASE}/operador/api/crear_orden", json={
        "producto_id": 1,
        "cantidad": 1000.0,
        "plazo_entrega": "2026-09-30T12:00:00"
    })
    
    if res_crear.status_code != 200:
        print(f"❌ Error al crear la orden: {res_crear.text}")
        sys.exit(1)
        
    data_crear = res_crear.json()
    orden_id = data_crear.get("orden_id")
    n_orden = data_crear.get("numero_orden")
    print(f"✅ Orden {n_orden} (ID: {orden_id}) creada exitosamente.")
    
    # 3. Esperar a que el daemon la inicialice y la mueva a 'en_produccion'
    print("\n⏳ Esperando a que el daemon asíncrono inicialice la orden en producción...")
    for _ in range(10):
        time.sleep(2)
        res_ordenes = session.get(f"{URL_BASE}/operador/api/ordenes_activas")
        data_ordenes = res_ordenes.json()
        orden_info = next((o for o in data_ordenes.get("ordenes", []) if o["id"] == orden_id), None)
        
        if orden_info and orden_info["estado"] == "en_produccion":
            print(f"✅ ¡Orden inicializada! Estado: {orden_info['estado']}")
            break
    else:
        print("❌ La orden no fue inicializada por el daemon a tiempo. ¿Está corriendo main.py?")
        sys.exit(1)
        
    # 4. Bucle de evolución dinámica
    max_pasos = 30
    paso = 1
    
    print("\n🏁 Comenzando evolución paso a paso...")
    while paso <= max_pasos:
        # Consultar estado de la orden y sus instancias
        res_ordenes = session.get(f"{URL_BASE}/operador/api/ordenes_activas")
        orden_info = next((o for o in res_ordenes.json().get("ordenes", []) if o["id"] == orden_id), None)
        
        if not orden_info:
            print("🏁 La orden ya no se encuentra en las órdenes activas (completada con éxito).")
            break
            
        print(f"\n==================== PASO {paso} ====================")
        print(f"Estado de la Orden: {orden_info['estado'].upper()}")
        print("Marcados de Petri:")
        
        for inst in orden_info.get("instancias", []):
            tipo = inst["tipo"]
            marcado = inst["marcado"]
            activo = [k for k, v in marcado.items() if v > 0]
            print(f"   - Red '{tipo}': {marcado} (Lugar activo: {activo})")
            
        # Buscar transiciones habilitadas para las instancias de la orden
        operacion_realizada = False
        for inst in orden_info.get("instancias", []):
            inst_id = inst["id"]
            tipo_red = inst["tipo"]
            
            # Consultar transiciones habilitadas
            res_trans = session.get(f"{URL_BASE}/operador/api/instancia/{inst_id}/transiciones")
            if res_trans.status_code != 200:
                print(f"❌ Error al consultar transiciones para {tipo_red} (instancia {inst_id}) [{res_trans.status_code}]: {res_trans.text}")
                sys.exit(1)
                
            try:
                transiciones = res_trans.json().get("transiciones", [])
            except Exception as e:
                print(f"❌ Fallo al decodificar JSON para {tipo_red} (instancia {inst_id}) [{res_trans.status_code}]: {res_trans.text}")
                raise e
            
            if transiciones:
                # Comprobar si hay una acción explícita de aprobación del operador disponible en la lista
                # IMPORTANTE: No usar "conforme" (falsos positivos con "no conforme") ni "tinturar"/"intermedio" (bucle)
                approval_keywords = ["transportar", "aprobado", "ok", "envasar", "descargar", "liberar", "completado"]
                approval_trans = next((t for t in transiciones if any(k in t["nombre"].lower() for k in approval_keywords)), None)
                
                # Comprobar si "No conforme" está en la lista
                has_no_conforme = any(t["nombre"].lower() == "no conforme" for t in transiciones)
                
                # Si está no conforme habilitada pero NO hay ninguna de aprobación en la lista trigger=200,
                # es porque estamos ante una compuerta de calidad (QA gate) esperando reporte del lab (trigger=201)
                if has_no_conforme and not approval_trans:
                    print(f"   🧪 Detectada compuerta de calidad (QA) en '{tipo_red}' (sin acción de aprobación manual).")
                    print(f"      Enviando reporte de laboratorio con Viscosidad conforme (95.0 KU)...")
                    res_disparo = session.post(f"{URL_BASE}/operador/api/control_calidad", json={
                        "instancia_id": inst_id,
                        "mediciones_qc": {"Viscosidad": 95.0}
                    })
                else:
                    # Usar la de aprobación si está disponible, si no, la primera del listado
                    trans = approval_trans if approval_trans else transiciones[0]
                    trans_id = trans["id"]
                    trans_nombre = trans["nombre"]
                    
                    print(f"👉 Acción disponible seleccionada en '{tipo_red}': {trans_nombre} (ID: {trans_id})")
                    
                    body = {
                        "instancia_id": inst_id,
                        "transicion_id": trans_id
                    }
                    
                    if "chequeo" in trans_nombre.lower():
                        body["invariantes"] = {"Temperatura": 50.0, "Velocidad": 1000.0}
                        print(f"   ⚡ Enviando telemetría física: Temperatura=50.0, Velocidad=1000.0")
                        
                    res_disparo = session.post(f"{URL_BASE}/operador/api/disparar", json=body)
                
                print(f"   📥 Respuesta de la API: {res_disparo.json()}")
                operacion_realizada = True
                break
                
        if not operacion_realizada:
            print("⏳ No hay acciones de operador disponibles en este momento. Esperando estabilización o proceso del orquestador...")
            
        time.sleep(3)
        paso += 1
        
    print("\n🏁 Simulación finalizada.")
    print("------------------------------------------------------------------")

if __name__ == "__main__":
    simular_evolucion()
