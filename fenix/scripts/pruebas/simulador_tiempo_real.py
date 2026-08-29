# scripts/pruebas/simulador_tiempo_real.py
import requests
import time
import sys

URL_BASE = "http://127.0.0.1:5000"

def simular():
    print("🚀 Iniciando Simulador en Tiempo Real...")
    print("--------------------------------------------------")
    
    # 1. Crear sesión de peticiones (mantiene las cookies de login)
    session = requests.Session()
    
    # 2. Iniciar Sesión como Administrador/Supervisor
    print("🔐 Iniciando sesión como admin@fenix.local...")
    res_login = session.post(f"{URL_BASE}/login", data={
        "email": "admin@fenix.local",
        "password": "admin123"
    }, allow_redirects=False)
    
    if res_login.status_code not in (200, 302):
        print("❌ Error al iniciar sesión. ¿Está el servidor Flask corriendo en el puerto 5000?")
        sys.exit(1)
    print("✅ Sesión iniciada con éxito.")
    
    # 3. Obtener órdenes activas
    print("\n🔍 Consultando órdenes activas...")
    res_ordenes = session.get(f"{URL_BASE}/operador/api/ordenes_activas")
    data_ordenes = res_ordenes.json()
    
    ordenes = [o for o in data_ordenes.get("ordenes", []) if o["estado"] == "en_proceso"]
    if not ordenes:
        print("⚠️ No hay órdenes en estado 'en_proceso' en el dashboard.")
        print("Por favor, crea una orden para 'Plantilla Ruta Látex' en la interfaz web primero.")
        sys.exit(1)
        
    orden_activa = ordenes[-1] # Tomar la última creada
    orden_id = orden_activa["id"]
    n_orden = orden_activa["numero_orden"]
    print(f"🎯 Seleccionada Orden ID: {orden_id} ({n_orden})")
    
    # Encontrar la instancia activa de dispersión
    instancia_disp = [i for i in orden_activa["instancias"] if i["tipo"] == "DIS_DIL_dispersion"]
    if not instancia_disp:
        print("❌ No se encontró instancia activa de tipo 'DIS_DIL_dispersion' para la orden.")
        sys.exit(1)
        
    inst_id = instancia_disp[0]["id"]
    print(f"🔗 ID de Instancia de Petri a disparar: {inst_id}")
    
    time.sleep(3)
    
    # --- PASO 1: Disparar el inicio ---
    print("\n⚙️ Paso 1: Iniciando carga de dispersor...")
    # Ver transiciones habilitadas
    res_trans = session.get(f"{URL_BASE}/operador/api/instancia/{inst_id}/transiciones")
    print(f"   Transiciones habilitadas: {res_trans.json().get('transiciones')}")
    
    # El primer disparo es el inicio de la dispersión
    print("   👉 Disparando transición 'Chequeo' con temperatura alta (60°C) para probar bloqueo de seguridad...")
    res_disparo = session.post(f"{URL_BASE}/operador/api/disparar", json={
        "instancia_id": inst_id,
        "transicion_id": "t7",
        "invariantes": {"Temperatura": 60.0} # Límite es 55°C
    })
    print(f"   Respuesta del servidor: {res_disparo.json()}")
    print("   📢 ¡Revisa tu navegador ahora! Deberías ver la orden bloqueada por Alerta Física en color rojo.")
    
    print("\n⏳ Esperando 7 segundos para que observes el bloqueo en la pantalla...")
    time.sleep(7)
    
    # --- PASO 2: Resolver bloqueo de temperatura ---
    print("\n⚙️ Paso 2: Temperando dispersor (reduciendo a 51.5°C) y re-intentando...")
    res_disparo = session.post(f"{URL_BASE}/operador/api/disparar", json={
        "instancia_id": inst_id,
        "transicion_id": "t7",
        "invariantes": {"Temperatura": 51.5}
    })
    print(f"   Respuesta del servidor: {res_disparo.json()}")
    print("   📢 ¡Revisa tu navegador! El token debió avanzar al lugar de Control de Calidad (p10).")
    
    print("\n⏳ Esperando 7 segundos para el siguiente paso...")
    time.sleep(7)
    
    # --- PASO 3: Control de Calidad - Rechazo ---
    print("\n⚙️ Paso 3: Enviando mediciones de viscosidad no conformes (75 KU) desde el laboratorio...")
    res_qa = session.post(f"{URL_BASE}/operador/api/control_calidad", json={
        "instancia_id": inst_id,
        "mediciones": {"Viscosidad": 75.0} # Requerido: 90 a 100 KU
    })
    print(f"   Respuesta del servidor: {res_qa.json()}")
    print("   📢 ¡Revisa tu navegador! Al fallar calidad, el lote fue desviado a Reproceso (retornado al dispersor).")
    
    print("\n⏳ Esperando 7 segundos...")
    time.sleep(7)
    
    # --- PASO 4: Re-chequeo del reproceso ---
    print("\n⚙️ Paso 4: Ajustando mezcla y completando la dispersión del reproceso...")
    res_disparo = session.post(f"{URL_BASE}/operador/api/disparar", json={
        "instancia_id": inst_id,
        "transicion_id": "t7",
        "invariantes": {"Temperatura": 50.0}
    })
    print(f"   Respuesta del servidor: {res_disparo.json()}")
    
    print("\n⏳ Esperando 7 segundos...")
    time.sleep(7)
    
    # --- PASO 5: Aprobación de Calidad ---
    print("\n⚙️ Paso 5: Enviando viscosidad conforme (95 KU) para aprobación final...")
    res_qa = session.post(f"{URL_BASE}/operador/api/control_calidad", json={
        "instancia_id": inst_id,
        "mediciones": {"Viscosidad": 95.0}
    })
    print(f"   Respuesta del servidor: {res_qa.json()}")
    print("   📢 ¡Revisa tu navegador! El lote fue aprobado y el orquestador lo avanzó a la etapa de Dilución.")
    
    print("\n🏁 Simulación completada. Revisa los logs de consola de tu servidor web y el daemon.")

if __name__ == "__main__":
    simular()
