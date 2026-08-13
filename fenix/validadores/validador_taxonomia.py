"""
Validador de plantilla de taxonomía
Valida el archivo 02_taxonomia.xlsx contra la estructura del modelo Taxonomia.py
ACTUALIZADO para incluir Servicios de Manufactura
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any

class ValidadorTaxonomia:
    """Validador para la plantilla de taxonomía"""
    
    # Estructura esperada de cada hoja (según modelo Taxonomia.py)
    ESTRUCTURA_HOJAS = {
        'FamiliasProducto': {
            'columnas': ['id', 'nombre', 'descripcion'],
            'requeridas': ['id', 'nombre'],
            'tipos': {
                'id': int,
                'nombre': str,
                'descripcion': str
            }
        },
        'TiposDeOperacion': {
            'columnas': ['id', 'nombre', 'descripcion'],
            'requeridas': ['id', 'nombre'],
            'tipos': {
                'id': int,
                'nombre': str,
                'descripcion': str
            }
        },
        'PatronesDeRuta': {
            'columnas': ['id', 'nombre', 'descripcion', 'familiaProducto_id'],
            'requeridas': ['id', 'nombre', 'familiaProducto_id'],
            'tipos': {
                'id': int,
                'nombre': str,
                'descripcion': str,
                'familiaProducto_id': int
            }
        },
        'EtapasRuta': {
            'columnas': ['id', 'nombre', 'patronRuta_id', 'tipoDeOperacion_id', 'servicio_manufactura_id'],
            'requeridas': ['id', 'nombre', 'patronRuta_id'],  # tipoDeOperacion_id o servicio_manufactura_id pueden ser opcionales
            'tipos': {
                'id': int,
                'nombre': str,
                'patronRuta_id': int,
                'tipoDeOperacion_id': int,  # puede ser nulo si se usa servicio
                'servicio_manufactura_id': int  # NUEVO: puede ser nulo si se usa tipoDeOperacion
            }
        },
        'TiposRecurso': {
            'columnas': ['id', 'nombre', 'descripcion'],
            'requeridas': ['id', 'nombre'],
            'tipos': {
                'id': int,
                'nombre': str,
                'descripcion': str
            }
        },
        'Capacidades': {
            'columnas': ['id', 'tipoRecurso_id', 'tipoOperacion_id', 'eficiencia_estimada', 'costo_por_hora'],
            'requeridas': ['id', 'tipoRecurso_id', 'tipoOperacion_id'],
            'tipos': {
                'id': int,
                'tipoRecurso_id': int,
                'tipoOperacion_id': int,
                'eficiencia_estimada': float,
                'costo_por_hora': float
            }
        },
        # NUEVA HOJA: Servicios de Manufactura
        'ServiciosManufactura': {
            'columnas': ['id', 'nombre', 'descripcion', 'tipo_operacion_id', 'capacidad_nominal', 
                        'unidad_capacidad', 'tiempo_preparacion_min', 'temp_min', 'temp_max', 
                        'presion_max_bar', 'activo'],
            'requeridas': ['id', 'nombre', 'tipo_operacion_id'],
            'tipos': {
                'id': int,
                'nombre': str,
                'descripcion': str,
                'tipo_operacion_id': int,
                'capacidad_nominal': float,
                'unidad_capacidad': str,
                'tiempo_preparacion_min': float,
                'temp_min': float,
                'temp_max': float,
                'presion_max_bar': float,
                'activo': bool
            }
        },
        # NUEVA HOJA: Tipo Recurso → Servicio
        'TipoRecursoServicio': {
            'columnas': ['tipo_recurso_nombre', 'servicio_nombre', 'tiempo_unitario', 'costo_por_hora',
                        'eficiencia', 'prioridad', 'capacidad_maxima_lote', 'tiempo_preparacion_extra_min'],
            'requeridas': ['tipo_recurso_nombre', 'servicio_nombre'],  # referencia por nombre, no por ID
            'tipos': {
                'tipo_recurso_nombre': str,
                'servicio_nombre': str,
                'tiempo_unitario': float,
                'costo_por_hora': float,
                'eficiencia': float,
                'prioridad': int,
                'capacidad_maxima_lote': float,
                'tiempo_preparacion_extra_min': float
            }
        },
        'TransicionesPatron': {
            'columnas': ['id', 'nombre', 'patron_id'],
            'requeridas': ['id', 'nombre', 'patron_id'],
            'tipos': {
                'id': int,
                'nombre': str,
                'patron_id': int
            }
        },
        'ArcosEntrada': {
            'columnas': ['id', 'nombre', 'trans_id', 'etapa_id', 'peso'],
            'requeridas': ['id', 'trans_id', 'etapa_id'],
            'tipos': {
                'id': int,
                'nombre': str,
                'trans_id': int,
                'etapa_id': int,
                'peso': int
            }
        },
        'ArcosSalida': {
            'columnas': ['id', 'nombre', 'trans_id', 'etapa_id', 'peso'],
            'requeridas': ['id', 'trans_id', 'etapa_id'],
            'tipos': {
                'id': int,
                'nombre': str,
                'trans_id': int,
                'etapa_id': int,
                'peso': int
            }
        }
    }
    
    def __init__(self, ruta_archivo: str):
        """
        Inicializa el validador
        
        Args:
            ruta_archivo: Ruta al archivo Excel de taxonomía
        """
        self.ruta_archivo = Path(ruta_archivo)
        self.errores: List[Dict] = []
        self.advertencias: List[Dict] = []
        self.datos_validados: Dict[str, pd.DataFrame] = {}
        
    def validar(self) -> Tuple[bool, List[Dict], List[Dict], Dict]:
        """
        Ejecuta la validación completa
        
        Returns:
            Tuple[bool, List, List, Dict]: (es_valido, errores, advertencias, datos_validados)
        """
        self.errores = []
        self.advertencias = []
        self.datos_validados = {}
        
        # Verificar que el archivo existe
        if not self.ruta_archivo.exists():
            self.errores.append({
                'tipo': 'ARCHIVO_NO_ENCONTRADO',
                'mensaje': f"No se encontró el archivo: {self.ruta_archivo}"
            })
            return False, self.errores, self.advertencias, self.datos_validados
        
        # Verificar que es un archivo Excel
        if self.ruta_archivo.suffix.lower() not in ['.xlsx', '.xls']:
            self.errores.append({
                'tipo': 'FORMATO_INVALIDO',
                'mensaje': f"Formato de archivo inválido. Debe ser .xlsx o .xls"
            })
            return False, self.errores, self.advertencias, self.datos_validados
        
        try:
            # Cargar todas las hojas
            excel_file = pd.ExcelFile(self.ruta_archivo)
            hojas_encontradas = excel_file.sheet_names
            
            # Verificar que existen todas las hojas requeridas
            hojas_requeridas = set(self.ESTRUCTURA_HOJAS.keys())
            hojas_faltantes = hojas_requeridas - set(hojas_encontradas)
            
            if hojas_faltantes:
                self.errores.append({
                    'tipo': 'HOJAS_FALTANTES',
                    'mensaje': f"Hojas faltantes: {', '.join(hojas_faltantes)}"
                })
                return False, self.errores, self.advertencias, self.datos_validados
            
            # Validar cada hoja
            for nombre_hoja, estructura in self.ESTRUCTURA_HOJAS.items():
                self._validar_hoja(excel_file, nombre_hoja, estructura)
            
            # Validar integridad referencial
            self._validar_integridad_referencial()
            
            # Validación específica para EtapasRuta: al menos una referencia válida
            self._validar_etapas_ruta()
            
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
            
            # Verificar que no esté vacía
            if df.empty:
                self.errores.append({
                    'hoja': nombre_hoja,
                    'tipo': 'HOJA_VACIA',
                    'mensaje': f"La hoja '{nombre_hoja}' está vacía"
                })
                return
            
            # Verificar columnas requeridas
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
            
            # Validar tipos de datos
            for columna, tipo_esperado in estructura['tipos'].items():
                if columna in df.columns:
                    self._validar_tipos(df, nombre_hoja, columna, tipo_esperado)
            
            # Validar IDs únicos
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
            
            # Validar eficiencia (rango 0-1)
            if nombre_hoja == 'Capacidades' and 'eficiencia_estimada' in df.columns:
                eficiencias_invalidas = df[(df['eficiencia_estimada'] < 0) | (df['eficiencia_estimada'] > 1)]['eficiencia_estimada'].tolist()
                if eficiencias_invalidas:
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'EFICIENCIA_INVALIDA',
                        'mensaje': f"Eficiencias fuera de rango [0,1]: {eficiencias_invalidas}"
                    })
            
            # Validar eficiencia para servicios (rango 0-1)
            if nombre_hoja == 'TipoRecursoServicio' and 'eficiencia' in df.columns:
                eficiencias_invalidas = df[(df['eficiencia'] < 0) | (df['eficiencia'] > 1)]['eficiencia'].tolist()
                if eficiencias_invalidas:
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'EFICIENCIA_INVALIDA',
                        'mensaje': f"Eficiencias fuera de rango [0,1]: {eficiencias_invalidas}"
                    })
            
            # Validar prioridad positiva
            if nombre_hoja == 'TipoRecursoServicio' and 'prioridad' in df.columns:
                prioridades_invalidas = df[df['prioridad'] <= 0]['prioridad'].tolist()
                if prioridades_invalidas:
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'PRIORIDAD_INVALIDA',
                        'mensaje': f"Prioridades deben ser mayores a 0: {prioridades_invalidas}"
                    })
            
            # Validar capacidad nominal positiva
            if nombre_hoja == 'ServiciosManufactura' and 'capacidad_nominal' in df.columns:
                capacidades_invalidas = df[df['capacidad_nominal'] <= 0]['capacidad_nominal'].tolist()
                if capacidades_invalidas:
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'CAPACIDAD_INVALIDA',
                        'mensaje': f"Capacidad nominal debe ser mayor a 0: {capacidades_invalidas}"
                    })
            
            # Validar pesos positivos
            if 'peso' in df.columns:
                pesos_invalidos = df[df['peso'] <= 0]['peso'].tolist()
                if pesos_invalidos:
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'PESO_INVALIDO',
                        'mensaje': f"Pesos deben ser mayores a 0: {pesos_invalidos}"
                    })
            
            # Validar costo_por_hora positivo
            if 'costo_por_hora' in df.columns:
                costos_invalidos = df[df['costo_por_hora'] < 0]['costo_por_hora'].tolist()
                if costos_invalidos:
                    self.advertencias.append({
                        'hoja': nombre_hoja,
                        'tipo': 'COSTO_NEGATIVO',
                        'mensaje': f"Costos negativos encontrados: {costos_invalidos}"
                    })
            
            # Validar tiempo_unitario positivo
            if nombre_hoja == 'TipoRecursoServicio' and 'tiempo_unitario' in df.columns:
                tiempos_invalidos = df[df['tiempo_unitario'] <= 0]['tiempo_unitario'].tolist()
                if tiempos_invalidos:
                    self.errores.append({
                        'hoja': nombre_hoja,
                        'tipo': 'TIEMPO_UNITARIO_INVALIDO',
                        'mensaje': f"Tiempo unitario debe ser mayor a 0: {tiempos_invalidos}"
                    })
            
            # Guardar datos validados
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
            
            if tipo_esperado == int:
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
            elif tipo_esperado == bool:
                if not isinstance(valor, (bool, np.bool_)):
                    # Convertir strings a bool
                    if isinstance(valor, str):
                        if valor.lower() not in ['true', 'false', '1', '0', 'si', 'no']:
                            self.errores.append({
                                'hoja': hoja,
                                'tipo': 'TIPO_INVALIDO',
                                'mensaje': f"Columna '{columna}' fila {idx+2}: valor '{valor}' no es booleano"
                            })
    
    def _validar_etapas_ruta(self):
        """Validación específica para EtapasRuta: debe tener tipoDeOperacion_id o servicio_manufactura_id"""
        
        if 'EtapasRuta' not in self.datos_validados:
            return
        
        df = self.datos_validados['EtapasRuta']
        
        for idx, row in df.iterrows():
            tiene_tipo = pd.notna(row.get('tipoDeOperacion_id', None))
            tiene_servicio = pd.notna(row.get('servicio_manufactura_id', None))
            
            if not tiene_tipo and not tiene_servicio:
                self.errores.append({
                    'hoja': 'EtapasRuta',
                    'tipo': 'SIN_REFERENCIA',
                    'mensaje': f"Fila {idx+2}: La etapa debe tener tipoDeOperacion_id o servicio_manufactura_id"
                })
    
    def _validar_integridad_referencial(self):
        """Valida que las relaciones entre hojas sean consistentes"""
        
        # PatronesDeRuta -> FamiliasProducto
        if 'PatronesDeRuta' in self.datos_validados and 'FamiliasProducto' in self.datos_validados:
            patrones = self.datos_validados['PatronesDeRuta']
            familias = self.datos_validados['FamiliasProducto']
            
            ids_familia_validos = set(familias['id'])
            ids_familia_referenciados = set(patrones['familiaProducto_id'].dropna())
            
            ids_invalidos = ids_familia_referenciados - ids_familia_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"PatronesDeRuta referencia familias inexistentes: {ids_invalidos}"
                })
        
        # EtapasRuta -> PatronesDeRuta
        if 'EtapasRuta' in self.datos_validados and 'PatronesDeRuta' in self.datos_validados:
            etapas = self.datos_validados['EtapasRuta']
            patrones = self.datos_validados['PatronesDeRuta']
            
            ids_patron_validos = set(patrones['id'])
            ids_patron_referenciados = set(etapas['patronRuta_id'].dropna())
            
            ids_invalidos = ids_patron_referenciados - ids_patron_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"EtapasRuta referencia patrones inexistentes: {ids_invalidos}"
                })
        
        # EtapasRuta -> TiposDeOperacion (si tiene valor)
        if 'EtapasRuta' in self.datos_validados and 'TiposDeOperacion' in self.datos_validados:
            etapas = self.datos_validados['EtapasRuta']
            operaciones = self.datos_validados['TiposDeOperacion']
            
            ids_operacion_validos = set(operaciones['id'])
            ids_operacion_referenciados = set(etapas[etapas['tipoDeOperacion_id'].notna()]['tipoDeOperacion_id'])
            
            ids_invalidos = ids_operacion_referenciados - ids_operacion_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"EtapasRuta referencia tipos de operación inexistentes: {ids_invalidos}"
                })
        
        # NUEVA: EtapasRuta -> ServiciosManufactura
        if 'EtapasRuta' in self.datos_validados and 'ServiciosManufactura' in self.datos_validados:
            etapas = self.datos_validados['EtapasRuta']
            servicios = self.datos_validados['ServiciosManufactura']
            
            ids_servicio_validos = set(servicios['id'])
            ids_servicio_referenciados = set(etapas[etapas['servicio_manufactura_id'].notna()]['servicio_manufactura_id'])
            
            ids_invalidos = ids_servicio_referenciados - ids_servicio_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"EtapasRuta referencia servicios de manufactura inexistentes: {ids_invalidos}"
                })
        
        # NUEVA: ServiciosManufactura -> TiposDeOperacion
        if 'ServiciosManufactura' in self.datos_validados and 'TiposDeOperacion' in self.datos_validados:
            servicios = self.datos_validados['ServiciosManufactura']
            operaciones = self.datos_validados['TiposDeOperacion']
            
            ids_operacion_validos = set(operaciones['id'])
            ids_operacion_referenciados = set(servicios['tipo_operacion_id'].dropna())
            
            ids_invalidos = ids_operacion_referenciados - ids_operacion_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"ServiciosManufactura referencia tipos de operación inexistentes: {ids_invalidos}"
                })
        
        # Capacidades -> TiposRecurso
        if 'Capacidades' in self.datos_validados and 'TiposRecurso' in self.datos_validados:
            capacidades = self.datos_validados['Capacidades']
            recursos = self.datos_validados['TiposRecurso']
            
            ids_recurso_validos = set(recursos['id'])
            ids_recurso_referenciados = set(capacidades['tipoRecurso_id'].dropna())
            
            ids_invalidos = ids_recurso_referenciados - ids_recurso_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"Capacidades referencia tipos de recurso inexistentes: {ids_invalidos}"
                })
        
        # Capacidades -> TiposDeOperacion
        if 'Capacidades' in self.datos_validados and 'TiposDeOperacion' in self.datos_validados:
            capacidades = self.datos_validados['Capacidades']
            operaciones = self.datos_validados['TiposDeOperacion']
            
            ids_operacion_validos = set(operaciones['id'])
            ids_operacion_referenciados = set(capacidades['tipoOperacion_id'].dropna())
            
            ids_invalidos = ids_operacion_referenciados - ids_operacion_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"Capacidades referencia tipos de operación inexistentes: {ids_invalidos}"
                })
        
        # TransicionesPatron -> PatronesDeRuta
        if 'TransicionesPatron' in self.datos_validados and 'PatronesDeRuta' in self.datos_validados:
            transiciones = self.datos_validados['TransicionesPatron']
            patrones = self.datos_validados['PatronesDeRuta']
            
            ids_patron_validos = set(patrones['id'])
            ids_patron_referenciados = set(transiciones['patron_id'].dropna())
            
            ids_invalidos = ids_patron_referenciados - ids_patron_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"TransicionesPatron referencia patrones inexistentes: {ids_invalidos}"
                })
        
        # ArcosEntrada -> TransicionesPatron
        if 'ArcosEntrada' in self.datos_validados and 'TransicionesPatron' in self.datos_validados:
            arcos = self.datos_validados['ArcosEntrada']
            transiciones = self.datos_validados['TransicionesPatron']
            
            ids_trans_validos = set(transiciones['id'])
            ids_trans_referenciados = set(arcos['trans_id'].dropna())
            
            ids_invalidos = ids_trans_referenciados - ids_trans_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"ArcosEntrada referencia transiciones inexistentes: {ids_invalidos}"
                })
        
        # ArcosEntrada -> EtapasRuta
        if 'ArcosEntrada' in self.datos_validados and 'EtapasRuta' in self.datos_validados:
            arcos = self.datos_validados['ArcosEntrada']
            etapas = self.datos_validados['EtapasRuta']
            
            ids_etapa_validos = set(etapas['id'])
            ids_etapa_referenciados = set(arcos['etapa_id'].dropna())
            
            ids_invalidos = ids_etapa_referenciados - ids_etapa_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"ArcosEntrada referencia etapas inexistentes: {ids_invalidos}"
                })
        
        # ArcosSalida -> TransicionesPatron
        if 'ArcosSalida' in self.datos_validados and 'TransicionesPatron' in self.datos_validados:
            arcos = self.datos_validados['ArcosSalida']
            transiciones = self.datos_validados['TransicionesPatron']
            
            ids_trans_validos = set(transiciones['id'])
            ids_trans_referenciados = set(arcos['trans_id'].dropna())
            
            ids_invalidos = ids_trans_referenciados - ids_trans_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"ArcosSalida referencia transiciones inexistentes: {ids_invalidos}"
                })
        
        # ArcosSalida -> EtapasRuta
        if 'ArcosSalida' in self.datos_validados and 'EtapasRuta' in self.datos_validados:
            arcos = self.datos_validados['ArcosSalida']
            etapas = self.datos_validados['EtapasRuta']
            
            ids_etapa_validos = set(etapas['id'])
            ids_etapa_referenciados = set(arcos['etapa_id'].dropna())
            
            ids_invalidos = ids_etapa_referenciados - ids_etapa_validos
            if ids_invalidos:
                self.errores.append({
                    'tipo': 'REFERENCIA_INVALIDA',
                    'mensaje': f"ArcosSalida referencia etapas inexistentes: {ids_invalidos}"
                })
    
    def generar_reporte(self) -> str:
        """Genera un reporte legible de la validación"""
        
        reporte = []
        reporte.append("=" * 80)
        reporte.append("VALIDACIÓN DE TAXONOMÍA")
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


def validar_taxonomia(ruta_archivo: str) -> Tuple[bool, List[Dict], List[Dict], Dict]:
    """
    Función de conveniencia para validar taxonomía
    
    Args:
        ruta_archivo: Ruta al archivo Excel
    
    Returns:
        Tuple[bool, List, List, Dict]: (es_valido, errores, advertencias, datos)
    """
    validador = ValidadorTaxonomia(ruta_archivo)
    return validador.validar()


if __name__ == "__main__":
    import sys
    
    # Prueba del validador
    ruta_default = Path(__file__).parent.parent / 'static' / 'plantillas' / '02_taxonomia.xlsx'
    
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        ruta = ruta_default
    
    print(f"Validando: {ruta}")
    print()
    
    validador = ValidadorTaxonomia(ruta)
    es_valido, errores, advertencias, datos = validador.validar()
    
    print(validador.generar_reporte())
    
    sys.exit(0 if es_valido else 1)