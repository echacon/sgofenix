# validadores/validador_encadenamiento.py

import pandas as pd
from typing import List, Dict, Tuple

class ValidadorEncadenamientoExcel:
    """Valida el archivo Excel de encadenamiento"""
    
    REQUIRED_COLUMNS = ['red_origen', 'transicion_origen', 'red_destino', 'evento_destino']
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.errores = []
        self.reglas = {}
    
    def validar(self) -> Tuple[bool, Dict, List[str]]:
        """Valida el archivo y retorna (es_valido, reglas, errores)"""
        
        try:
            df = pd.read_excel(self.filepath, sheet_name='Reglas')
        except Exception as e:
            self.errores.append(f"Error al leer el archivo: {e}")
            return False, {}, self.errores
        
        # Validar columnas requeridas
        missing_cols = set(self.REQUIRED_COLUMNS) - set(df.columns)
        if missing_cols:
            self.errores.append(f"Faltan columnas: {missing_cols}")
            return False, {}, self.errores
        
        # Procesar cada fila
        for idx, row in df.iterrows():
            linea = idx + 2  # +2 por cabecera y 0-index
            
            red_origen = row.get('red_origen')
            transicion_origen = str(row.get('transicion_origen')) if pd.notna(row.get('transicion_origen')) else None
            red_destino = row.get('red_destino')
            evento_destino = row.get('evento_destino')
            
            # Validar campos obligatorios
            if not red_origen:
                self.errores.append(f"Línea {linea}: 'red_origen' es obligatorio")
                continue
            if not transicion_origen:
                self.errores.append(f"Línea {linea}: 'transicion_origen' es obligatorio")
                continue
            if not red_destino:
                self.errores.append(f"Línea {linea}: 'red_destino' es obligatorio")
                continue
            if not evento_destino:
                self.errores.append(f"Línea {linea}: 'evento_destino' es obligatorio")
                continue
            
            # Agregar a reglas
            if red_origen not in self.reglas:
                self.reglas[red_origen] = {}
            
            self.reglas[red_origen][transicion_origen] = {
                "red_destino": red_destino,
                "evento": evento_destino
            }
        
        if self.errores:
            return False, {}, self.errores
        
        return True, self.reglas, []