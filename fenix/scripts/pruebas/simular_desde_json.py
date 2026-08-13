#!/usr/bin/env python3
# simular_desde_json.py - Envía eventos desde JSON a la cola

import json
import time
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

RAIZ = Path(__file__).parent.parent.parent
sys.path.insert(0, str(RAIZ))

from modelos.Colaevento import ColaEvento

engine = create_engine('sqlite:///fenix.db')
Session = sessionmaker(bind=engine)

COMPRESION = 4.0  # Factor de aceleración

def cargar_eventos(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['eventos']

def enviar_eventos(eventos):
    session = Session()
    try:
        # Ordenar por timestamp (convertir a datetime para ordenar)
        eventos_con_dt = []
        for ev in eventos:
            # El timestamp puede venir como string ISO
            ts = ev.get('timestamp')
            if ts:
                dt = datetime.fromisoformat(ts)
            else:
                dt = datetime.now()
            eventos_con_dt.append((dt, ev))
        eventos_con_dt.sort(key=lambda x: x[0])
        
        timestamps = [dt for dt, _ in eventos_con_dt]
        
        for i, (dt, ev) in enumerate(eventos_con_dt):
            if i == 0:
                delay = 0
            else:
                delta = timestamps[i] - timestamps[i-1]
                delay = delta.total_seconds() / COMPRESION
            
            if delay > 0:
                print(f"⏳ Esperando {delay:.1f}s antes del evento {ev.get('id', i)}...")
                time.sleep(delay)
            
            # Preparar campos según nuevo modelo
            orden_id = ev['orden_id']
            transicion_nombre = ev['transicion']  # nombre legible
            recurso_nombre = ev.get('recurso')   # puede ser None
            red_nombre = ev.get('red')           # puede ser None (opcional)
            
            datos_extra = {k: v for k, v in ev.items() if k not in ['orden_id', 'transicion', 'recurso', 'red', 'timestamp', 'id']}
            # Si se desea preservar el recurso en datos por compatibilidad, se puede, pero ya tenemos recurso_nombre
            if recurso_nombre and 'recurso' not in datos_extra:
                datos_extra['recurso'] = recurso_nombre
            
            evento_cola = ColaEvento(
                orden_id=orden_id,
                red_nombre=red_nombre,
                recurso_nombre=recurso_nombre,
                transicion_nombre=transicion_nombre,
                datos=datos_extra,
                estado='pendiente',
                fecha_creacion=datetime.now(),
                intentos=0
            )
            session.add(evento_cola)
            session.commit()
            print(f"📨 Evento {ev.get('id', i)} encolado: recurso='{recurso_nombre}', red='{red_nombre}', trans='{transicion_nombre}'")
        
        print("✅ Todos los eventos han sido encolados.")
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', type=str, default='eventos_exito.json',
                        help='Ruta al archivo JSON de eventos')
    args = parser.parse_args()
    
    json_path = Path(__file__).parent / args.json
    if not json_path.exists():
        print(f"No se encuentra {json_path}")
        sys.exit(1)
    
    eventos = cargar_eventos(json_path)
    print(f"📋 Cargados {len(eventos)} eventos desde {json_path}")
    enviar_eventos(eventos)