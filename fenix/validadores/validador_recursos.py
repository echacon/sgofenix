# validadores/validador_recursos.py

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict


class ValidadorRecursosExcel:
    """Valida el archivo 01_recursos.xlsx antes de importar"""
    
    def __init__(self):
        self.errores: List[str] = []
        self.advertencias: List[str] = []
        self.datos_validados: Dict = {}
    
    def validar(self, ruta_archivo: str) -> Tuple[bool, List[str], List[str]]:
        self.errores = []
        self.advertencias = []
        
        try:
            # Leer todas las hojas
            df_uf = pd.read_excel(ruta_archivo, sheet_name='UnidadesFuncionales')
            df_eq = pd.read_excel(ruta_archivo, sheet_name='RecursosEquipo')
            df_un = pd.read_excel(ruta_archivo, sheet_name='UnidadesNegocio')
            df_rp = pd.read_excel(ruta_archivo, sheet_name='RecursoPersonal')
            df_roles = pd.read_excel(ruta_archivo, sheet_name='Roles')
            
            try:
                df_servicios = pd.read_excel(ruta_archivo, sheet_name='ServiciosTecnicos')
            except ValueError:
                df_servicios = pd.DataFrame()
                self.advertencias.append("Hoja 'ServiciosTecnicos' no encontrada, se omite")
            
            # Reemplazar NaN y None por cadena vacía
            df_uf = df_uf.replace([np.nan, None], '')
            df_eq = df_eq.replace([np.nan, None], '')
            df_un = df_un.replace([np.nan, None], '')
            df_rp = df_rp.replace([np.nan, None], '')
            df_roles = df_roles.replace([np.nan, None], '')
            
            # Validar cada hoja
            self._validar_unidades_funcionales(df_uf)
            self._validar_recursos_equipo(df_eq, df_uf)
            self._validar_unidades_negocio(df_un)
            self._validar_recurso_personal(df_rp, df_un)
            self._validar_roles(df_roles)
            
            # Guardar datos validados
            self.datos_validados = {
                'unidades_funcionales': df_uf,
                'recursos_equipo': df_eq,
                'unidades_negocio': df_un,
                'recurso_personal': df_rp,
                'roles': df_roles,
                'servicios_tecnicos': df_servicios
            }
            
            return len(self.errores) == 0, self.errores, self.advertencias
            
        except Exception as e:
            self.errores.append(f"Error leyendo archivo: {str(e)}")
            return False, self.errores, self.advertencias
    
    def _validar_unidades_funcionales(self, df: pd.DataFrame):
        if df.empty:
            self.errores.append("Hoja 'UnidadesFuncionales' está vacía")
            return
        
        # Verificar columnas
        if 'nombre' not in df.columns:
            self.errores.append("Hoja 'UnidadesFuncionales' falta columna 'nombre'")
            return
        
        # Validar nombres no vacíos
        for idx, row in df.iterrows():
            nombre = row.get('nombre', '')
            if not nombre or nombre == '':
                self.errores.append(f"UF fila {idx+2}: 'nombre' es obligatorio")
        
        # Validar que los padres existen (solo si no están vacíos)
        nombres = set(df['nombre'].tolist())
        for idx, row in df.iterrows():
            nombre = row.get('nombre', '')
            padre = row.get('unidadPadre_nombre', '')
            
            if padre and padre != '' and padre not in nombres:
                self.errores.append(f"UF '{nombre}': padre '{padre}' no existe")
    
    def _validar_recursos_equipo(self, df: pd.DataFrame, df_uf: pd.DataFrame):
        if df.empty:
            self.advertencias.append("Hoja 'RecursosEquipo' está vacía")
            return
        
        uf_nombres = set(df_uf['nombre'].tolist()) if not df_uf.empty else set()
        
        for idx, row in df.iterrows():
            nombre = row.get('nombre', '')
            if not nombre or nombre == '':
                self.errores.append(f"Equipo fila {idx+2}: 'nombre' es obligatorio")
            
            uf = row.get('unidadFuncional_nombre', '')
            if uf and uf != '':
                if uf not in uf_nombres:
                    self.errores.append(f"Equipo '{nombre}': unidad funcional '{uf}' no existe")
    
    def _validar_unidades_negocio(self, df: pd.DataFrame):
        if df.empty:
            self.advertencias.append("Hoja 'UnidadesNegocio' está vacía")
            return
        
        if 'nombre' not in df.columns:
            self.errores.append("Hoja 'UnidadesNegocio' falta columna 'nombre'")
            return
        
        # Validar nombres no vacíos
        for idx, row in df.iterrows():
            nombre = row.get('nombre', '')
            if not nombre or nombre == '':
                self.errores.append(f"UN fila {idx+2}: 'nombre' es obligatorio")
        
        # Validar padres (solo si no están vacíos)
        nombres = set(df['nombre'].tolist())
        for idx, row in df.iterrows():
            nombre = row.get('nombre', '')
            padre = row.get('unidadPadre_nombre', '')
            
            if padre and padre != '' and padre not in nombres:
                self.errores.append(f"UN '{nombre}': padre '{padre}' no existe")
    
    def _validar_recurso_personal(self, df: pd.DataFrame, df_un: pd.DataFrame):
        if df.empty:
            self.advertencias.append("Hoja 'RecursoPersonal' está vacía")
            return
        
        un_nombres = set(df_un['nombre'].tolist()) if not df_un.empty else set()
        
        for idx, row in df.iterrows():
            nombre = row.get('nombre', '')
            if not nombre or nombre == '':
                self.errores.append(f"Personal fila {idx+2}: 'nombre' es obligatorio")
            
            un = row.get('unidadNegocio_nombre', '')
            if un and un != '':
                if un not in un_nombres:
                    self.errores.append(f"Personal '{nombre}': unidad negocio '{un}' no existe")
    
    def _validar_roles(self, df: pd.DataFrame):
        if df.empty:
            self.advertencias.append("Hoja 'Roles' está vacía")
            return
        
        for idx, row in df.iterrows():
            nombre = row.get('nombre', '')
            if not nombre or nombre == '':
                self.errores.append(f"Roles fila {idx+2}: 'nombre' es obligatorio")