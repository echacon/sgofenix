# validadores/validador_productos.py

#!/usr/bin/env python3
"""
Validador de plantilla de productos
Valida el archivo 03_productos.xlsx contra la estructura del modelo Producto.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any

class ValidadorProductos_excel:
    """Validador para la plantilla de productos"""
    
    # Estructura esperada de cada hoja (según modelo Producto.py)
    ESTRUCTURA_HOJAS = {
        'Productos': {
            'columnas': ['id', 'nombre', 'codigo_interno', 'es_fabricado', 'es_adquirido', 
                        'es_final', 'es_insumo', 'es_intermedio', 'id_tipoDeProducto'],
            'requeridas': ['id', 'nombre', 'codigo_interno'],
            'tipos': {
                'id': int,
                'nombre': str,
                'codigo_interno': str,
                'es_fabricado': bool,
                'es_adquirido': bool,
                'es_final': bool,
                'es_insumo': bool,
                'es_intermedio': bool,
                'id_tipoDeProducto': int
            }
        },
        'HolonRuta': {
            'columnas': ['id', 'producto_id', 'fechaModelo', 'nombreRuta', 'id_tipoRuta'],
            'requeridas': ['id', 'producto_id', 'nombreRuta', 'id_tipoRuta'],
            'tipos': {
                'id': int,
                'producto_id': int,
                'fechaModelo': str,
                'nombreRuta': str,
                'id_tipoRuta': int
            }
        },
        'Formula': {
            'columnas': ['id', 'holonRuta_id', 'cantidad'],
            'requeridas': ['id', 'holonRuta_id', 'cantidad'],
            'tipos': {
                'id': int,
                'holonRuta_id': int,
                'cantidad': float
            }
        },
        'Insumos': {
            'columnas': ['id', 'producto_id', 'cantidad', 'formula_id'],
            'requeridas': ['id', 'producto_id', 'cantidad', 'formula_id'],
            'tipos': {
                'id': int,
                'producto_id': int,
                'cantidad': float,
                'formula_id': int
            }
        },
        'Operaciones': {
            'columnas': ['id', 'nombre', 'servicio', 'duracion', 'marcacion', 'modeloDinamica_id'],
            'requeridas': ['id', 'nombre', 'duracion', 'modeloDinamica_id'],
            'tipos': {
                'id': int,
                'nombre': str,
                'servicio': str,
                'duracion': int,
                'marcacion': int,
                'modeloDinamica_id': int
            }
        },
        'Transiciones': {
            'columnas': ['id', 'nombre', 'disparador', 'mensajeSalida', 'modeloDinamica_id'],
            'requeridas': ['id', 'nombre', 'modeloDinamica_id'],
            'tipos': {
                'id': int,
                'nombre': str,
                'disparador': int,
                'mensajeSalida': str,
                'modeloDinamica_id': int
            }
        },
        'ArcosEntrada': {
            'columnas': ['id', 'es_inhibidor', 'lugar', 'trans', 'modeloDinamica_id'],
            'requeridas': ['id', 'lugar', 'trans', 'modeloDinamica_id'],
            'tipos': {
                'id': int,
                'es_inhibidor': bool,
                'lugar': int,
                'trans': int,
                'modeloDinamica_id': int
            }
        },
        'ArcosSalida': {
            'columnas': ['id', 'lugar', 'trans', 'modeloDinamica_id'],
            'requeridas': ['id', 'lugar', 'trans', 'modeloDinamica_id'],
            'tipos': {
                'id': int,
                'lugar': int,
                'trans': int,
                'modeloDinamica_id': int
            }
        }
    }
    
    def __init__(self, ruta_archivo: str):
        self.ruta_archivo = Path(ruta_archivo)
        self.errores: List[Dict] = []
        self.advertencias: List[Dict] = []
        self.datos_validados: Dict[str, pd.DataFrame] = {}
        
    def validar(self) -> Tuple[bool, List[Dict], List[Dict], Dict]:
        """Ejecuta la validación completa"""
        
        self.errores = []
        self.advertencias = []
        self.datos_validados = {}
        
        if not self.ruta_archivo.exists():
            self.errores.append({
                'tipo': 'ARCHIVO_NO_ENCONTRADO',
                'mensaje': f"No se encontró el archivo: {self.ruta_archivo}"
            })
            return False, self.errores, self.advertencias, self.datos_validados
        
        if self.ruta_archivo.suffix.lower() not in ['.xlsx', '.xls']:
            self.errores.append({
                'tipo': 'FORMATO_INVALIDO',
                'mensaje': f"Formato de archivo inválido. Debe ser .xlsx o .xls"
            })
            return False, self.errores, self.advertencias, self.datos_validados
        
        try:
            excel_file = pd.ExcelFile(self.ruta_archivo)
            hojas_encontradas = excel_file.sheet_names
            
            hojas_requeridas = set(self.ESTRUCTURA_HOJAS.keys())
            hojas_faltantes = hojas_requeridas - set(hojas_encontradas)
            
            if hojas_faltantes:
                self.errores.append({
                    'tipo': 'HOJAS_FALTANTES',
                    'mensaje': f"Hojas faltantes: {', '.join(hojas_faltantes)}"
                })
                return False, self.errores, self.advertencias, self.datos_validados
            
            for nombre_hoja, estructura in self.ESTRUCTURA_HOJAS.items():
                self._validar_hoja(excel_file, nombre_hoja, estructura)
            
            self._validar_integridad_referencial()
            
            es_valido = len(self.errores) == 0
            
            return es_valido, self.errores, self.advertencias, self.datos_validados
            
        except Exception as e:
            self.errores.append({
                'tipo': 'ERROR_LECTURA',
                'mensaje': f"Error al leer el archivo: {str(e)}"
            })
            return False, self.errores, self.advertencias, self.datos_validados
    
    def _validar_hoja(self, excel_file: pd.ExcelFile, nombre_hoja: str, estructura: Dict):
        """Valida una hoja específica"""
        
        try:
            df = excel_file.parse(nombre_hoja)
            
            if df.empty:
                self.errores.append({
                    'hoja': nombre_hoja,
                    'tipo': 'HOJA_VACIA',
                    'mensaje': f"La hoja '{nombre_hoja}' está vacía"
                })
                return
            
            columnas_df = set(df.columns)
            columnas_requeridas = set(estructura['requeridas'])
            columnas_faltantes = columnas_requeridas - columnas_df
            
            if columnas_faltantes:
                self.errores.append({
                    'hoja': nombre_hoja,
                    'tipo': 'COLUMNAS_FALTANTES',
                    'mensaje': f"Columnas requeridas faltantes: {', '.join(columnas_faltantes)}"
                })
                return
            
            for columna, tipo_esperado in estructura['tipos'].items():
                if columna in df.columns:
                    self._validar_tipos(df, nombre_hoja, columna, tipo_esperado)
            
            if 'id' in df.columns:
                ids = df['id']
                if ids.isnull().any():
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'ID_NULO',
                        'mensaje': f"La columna 'id' contiene valores nulos"
                    })
                
                if ids.duplicated().any():
                    duplicados = ids[ids.duplicated()].tolist()
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'ID_DUPLICADO',
                        'mensaje': f"IDs duplicados encontrados: {duplicados}"
                    })
            
            # Validar duración positiva
            if 'duracion' in df.columns:
                duraciones_invalidas = df[df['duracion'] <= 0]['duracion'].tolist()
                if duraciones_invalidas:
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'DURACION_INVALIDA',
                        'mensaje': f"Duración debe ser mayor a 0: {duraciones_invalidas}"
                    })
            
            # Validar cantidad positiva
            if 'cantidad' in df.columns:
                cantidades_invalidas = df[df['cantidad'] <= 0]['cantidad'].tolist()
                if cantidades_invalidas:
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'CANTIDAD_INVALIDA',
                        'mensaje': f"Cantidad debe ser mayor a 0: {cantidades_invalidas}"
                    })
            
            # Validar marcación no negativa
            if 'marcacion' in df.columns:
                marcaciones_invalidas = df[df['marcacion'] < 0]['marcacion'].tolist()
                if marcaciones_invalidas:
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'MARCACION_INVALIDA',
                        'mensaje': f"Marcación no puede ser negativa: {marcaciones_invalidas}"
                    })
            
            self.datos_validados[nombre_hoja] = df
            
        except Exception as e:
            self.errores.append({
                'hoja': nombre_hoja,
                'tipo': 'ERROR_LECTURA_HOJA',
                'mensaje': f"Error al leer la hoja '{nombre_hoja}': {str(e)}"
            })
    
    def _validar_tipos(self, df: pd.DataFrame, hoja: str, columna: str, tipo_esperado: type):
        """Valida los tipos de datos de una columna"""
        
        for idx, valor in df[columna].items():
            if pd.isna(valor):
                if columna in self.ESTRUCTURA_HOJAS[hoja]['requeridas']:
                    self.errores.append({
                        'hoja': hoja,
                        'tipo': 'VALOR_NULO',
                        'mensaje': f"Columna requerida '{columna}' fila {idx+2}: valor nulo"
                    })
                continue
            
            if tipo_esperado == bool:
                if not isinstance(valor, (bool, np.bool_)):
                    if isinstance(valor, str) and valor.lower() in ['true', 'false', '1', '0', 'yes', 'no']:
                        continue
                    self.errores.append({
                        'hoja': hoja,
                        'tipo': 'TIPO_INVALIDO',
                        'mensaje': f"Columna '{columna}' fila {idx+2}: valor '{valor}' no es booleano"
                    })
            elif tipo_esperado == int:
                try:
                    int(valor)
                except (ValueError, TypeError):
                    self.errores.append({
                        'hoja': hoja,
                        'tipo': 'TIPO_INVALIDO',
                        'mensaje': f"Columna '{columna}' fila {idx+2}: valor '{valor}' no es entero"
                    })
            elif tipo_esperado == float:
                try:
                    float(valor)
                except (ValueError, TypeError):
                    self.errores.append({
                        'hoja': hoja,
                        'tipo': 'TIPO_INVALIDO',
                        'mensaje': f"Columna '{columna}' fila {idx+2}: valor '{valor}' no es número decimal"
                    })
            elif tipo_esperado == str:
                if not isinstance(valor, str):
                    self.errores.append({
                        'hoja': hoja,
                        'tipo': 'TIPO_INVALIDO',
                        'mensaje': f"Columna '{columna}' fila {idx+2}: valor '{valor}' no es texto"
                    })
    
    def _validar_integridad_referencial(self):
        """Valida las relaciones entre hojas"""
        
        # HolonRuta -> Productos
        if 'HolonRuta' in self.datos_validados and 'Productos' in self.datos_validados:
            holones = self.datos_validados['HolonRuta']
            productos = self.datos_validados['Productos']
            
            ids_producto_validos = set(productos['id'])
            ids_producto_referenciados = set(holones['producto_id'].dropna())
            
            ids_invalidos = ids_producto_referenciados - ids_producto_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"HolonRuta referencia productos inexistentes: {ids_invalidos}"
                })
        
        # Formula -> HolonRuta
        if 'Formula' in self.datos_validados and 'HolonRuta' in self.datos_validados:
            formulas = self.datos_validados['Formula']
            holones = self.datos_validados['HolonRuta']
            
            ids_holon_validos = set(holones['id'])
            ids_holon_referenciados = set(formulas['holonRuta_id'].dropna())
            
            ids_invalidos = ids_holon_referenciados - ids_holon_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"Formula referencia holones inexistentes: {ids_invalidos}"
                })
        
        # Insumos -> Formula
        if 'Insumos' in self.datos_validados and 'Formula' in self.datos_validados:
            insumos = self.datos_validados['Insumos']
            formulas = self.datos_validados['Formula']
            
            ids_formula_validos = set(formulas['id'])
            ids_formula_referenciados = set(insumos['formula_id'].dropna())
            
            ids_invalidos = ids_formula_referenciados - ids_formula_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"Insumos referencia formulas inexistentes: {ids_invalidos}"
                })
        
        # Operaciones, Transiciones, Arcos -> ModeloDinamica
        for hoja in ['Operaciones', 'Transiciones', 'ArcosEntrada', 'ArcosSalida']:
            if hoja in self.datos_validados:
                df = self.datos_validados[hoja]
                if 'modeloDinamica_id' in df.columns:
                    # Verificar que exista al menos un modelo dinámico
                    if df['modeloDinamica_id'].isnull().any():
                        self.errores.append({
                            'hoja': hoja,
                            'tipo': 'MODELO_DINAMICA_NULO',
                            'mensaje': f"modeloDinamica_id tiene valores nulos"
                        })
    
    def generar_reporte(self) -> str:
        """Genera un reporte legible de la validación"""
        
        reporte = []
        reporte.append("=" * 80)
        reporte.append("VALIDACIÓN DE PRODUCTOS")
        reporte.append("=" * 80)
        reporte.append(f"Archivo: {self.ruta_archivo}")
        reporte.append("")
        
        if self.errores:
            reporte.append(f"❌ ERRORES ENCONTRADOS: {len(self.errores)}")
            reporte.append("-" * 40)
            for i, error in enumerate(self.errores, 1):
                reporte.append(f"{i}. {error.get('tipo', 'ERROR')}")
                if 'hoja' in error:
                    reporte.append(f"   Hoja: {error['hoja']}")
                reporte.append(f"   {error['mensaje']}")
                reporte.append("")
        else:
            reporte.append("✅ No se encontraron errores")
            reporte.append("")
        
        if self.advertencias:
            reporte.append(f"⚠️ ADVERTENCIAS: {len(self.advertencias)}")
            reporte.append("-" * 40)
            for i, adv in enumerate(self.advertencias, 1):
                reporte.append(f"{i}. {adv.get('tipo', 'ADVERTENCIA')}")
                if 'hoja' in adv:
                    reporte.append(f"   Hoja: {adv['hoja']}")
                reporte.append(f"   {adv['mensaje']}")
                reporte.append("")
        
        if self.datos_validados:
            reporte.append("📊 RESUMEN DE DATOS:")
            reporte.append("-" * 40)
            for nombre_hoja, df in self.datos_validados.items():
                reporte.append(f"  • {nombre_hoja}: {len(df)} registros")
        
        reporte.append("=" * 80)
        
        return "\n".join(reporte)


def validar_productos(ruta_archivo: str) -> Tuple[bool, List[Dict], List[Dict], Dict]:
    """Función de conveniencia para validar productos"""
    validador = ValidadorProductos(ruta_archivo)
    return validador.validar()


if __name__ == "__main__":
    import sys
    
    ruta_default = Path(__file__).parent.parent / 'static' / 'plantillas' / '03_productos.xlsx'
    
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        ruta = ruta_default
    
    print(f"Validando: {ruta}")
    print()
    
    validador = ValidadorProductos(ruta)
    es_valido, errores, advertencias, datos = validador.validar()
    
    print(validador.generar_reporte())
    
    sys.exit(0 if es_valido else 1)