#!/usr/bin/env python3
#importadores/importador_productos.py
"""
Importador de plantilla de productos
Importa el archivo 03_productos.xlsx a la base de datos
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy.orm import Session

from modelos.declarative_base import SessionLocal
from modelos.Producto import (
    Producto, HolonRuta, Formula, Insumo,
    OperacionProduccion, TransicionProd, ArcoEntrProd, ArcoSalidaProd
)
from validadores.validador_productos import ValidadorProductos


class ImportadorProductos:
    """Importador para la plantilla de productos"""
    
    def __init__(self, ruta_archivo: str):
        self.ruta_archivo = Path(ruta_archivo)
        self.errores = []
        self.advertencias = []
        self.contadores = {
            'productos': 0,
            'holon_ruta': 0,
            'formulas': 0,
            'insumos': 0,
            'operaciones': 0,
            'transiciones': 0,
            'arcos_entrada': 0,
            'arcos_salida': 0
        }
    
    def importar(self) -> tuple:
        """Ejecuta la importación completa"""
        
        # Primero validar
        validador = ValidadorProductos(self.ruta_archivo)
        es_valido, errores, advertencias, datos = validador.validar()
        
        if not es_valido:
            return False, "La validación falló. Corrija los errores antes de importar.", {}, errores
        
        self.advertencias = advertencias
        
        session = SessionLocal()
        
        try:
            self._importar_productos(session, datos.get('Productos'))
            self._importar_holon_ruta(session, datos.get('HolonRuta'))
            self._importar_formulas(session, datos.get('Formula'))
            self._importar_insumos(session, datos.get('Insumos'))
            self._importar_operaciones(session, datos.get('Operaciones'))
            self._importar_transiciones(session, datos.get('Transiciones'))
            self._importar_arcos_entrada(session, datos.get('ArcosEntrada'))
            self._importar_arcos_salida(session, datos.get('ArcosSalida'))
            
            session.commit()
            
            mensaje = f"✅ Importación exitosa: {self.contadores}"
            return True, mensaje, self.contadores, self.errores
            
        except Exception as e:
            session.rollback()
            self.errores.append({
                'tipo': 'ERROR_IMPORTACION',
                'mensaje': str(e)
            })
            return False, f"Error en la importación: {str(e)}", {}, self.errores
        finally:
            session.close()
    
    def _importar_productos(self, session: Session, df):
        if df is None or df.empty:
            self.advertencias.append("No hay datos de Productos")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(Producto).filter_by(id=int(row['id'])).first()
                
                if existente:
                    existente.nombre = row['nombre']
                    existente.codigo_interno = row['codigo_interno']
                    existente.es_fabricado = bool(row['es_fabricado'])
                    existente.es_adquirido = bool(row['es_adquirido'])
                    existente.es_final = bool(row['es_final'])
                    existente.es_insumo = bool(row['es_insumo'])
                    existente.es_intermedio = bool(row['es_intermedio'])
                    existente.id_tipoDeProducto = int(row['id_tipoDeProducto'])
                else:
                    producto = Producto(
                        id=int(row['id']),
                        nombre=row['nombre'],
                        codigo_interno=row['codigo_interno'],
                        es_fabricado=bool(row['es_fabricado']),
                        es_adquirido=bool(row['es_adquirido']),
                        es_final=bool(row['es_final']),
                        es_insumo=bool(row['es_insumo']),
                        es_intermedio=bool(row['es_intermedio']),
                        id_tipoDeProducto=int(row['id_tipoDeProducto'])
                    )
                    session.add(producto)
                
                self.contadores['productos'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_PRODUCTO',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_holon_ruta(self, session: Session, df):
        if df is None or df.empty:
            self.advertencias.append("No hay datos de HolonRuta")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(HolonRuta).filter_by(id=int(row['id'])).first()
                
                if existente:
                    existente.producto_id = int(row['producto_id'])
                    existente.fechaModelo = row['fechaModelo']
                    existente.nombreRuta = row['nombreRuta']
                    existente.id_tipoRuta = int(row['id_tipoRuta'])
                else:
                    holon = HolonRuta(
                        id=int(row['id']),
                        producto_id=int(row['producto_id']),
                        fechaModelo=row['fechaModelo'],
                        nombreRuta=row['nombreRuta'],
                        id_tipoRuta=int(row['id_tipoRuta'])
                    )
                    session.add(holon)
                
                self.contadores['holon_ruta'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_HOLON_RUTA',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_formulas(self, session: Session, df):
        if df is None or df.empty:
            self.advertencias.append("No hay datos de Formula")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(Formula).filter_by(id=int(row['id'])).first()
                
                if existente:
                    existente.holonRuta_id = int(row['holonRuta_id'])
                    existente.cantidad = float(row['cantidad'])
                else:
                    formula = Formula(
                        id=int(row['id']),
                        holonRuta_id=int(row['holonRuta_id']),
                        cantidad=float(row['cantidad'])
                    )
                    session.add(formula)
                
                self.contadores['formulas'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_FORMULA',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_insumos(self, session: Session, df):
        if df is None or df.empty:
            self.advertencias.append("No hay datos de Insumos")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(Insumo).filter_by(id=int(row['id'])).first()
                
                if existente:
                    existente.producto_id = int(row['producto_id'])
                    existente.cantidad = float(row['cantidad'])
                    existente.formula_id = int(row['formula_id'])
                else:
                    insumo = Insumo(
                        id=int(row['id']),
                        producto_id=int(row['producto_id']),
                        cantidad=float(row['cantidad']),
                        formula_id=int(row['formula_id'])
                    )
                    session.add(insumo)
                
                self.contadores['insumos'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_INSUMO',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_operaciones(self, session: Session, df):
        if df is None or df.empty:
            self.advertencias.append("No hay datos de Operaciones")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(OperacionProduccion).filter_by(id=int(row['id'])).first()
                
                if existente:
                    existente.nombre = row['nombre']
                    existente.servicio = row.get('servicio', '')
                    existente.duracion = int(row['duracion'])
                    existente.marcacion = int(row.get('marcacion', 0))
                    existente.modeloDinamica_id = int(row['modeloDinamica_id'])
                else:
                    operacion = OperacionProduccion(
                        id=int(row['id']),
                        nombre=row['nombre'],
                        servicio=row.get('servicio', ''),
                        duracion=int(row['duracion']),
                        marcacion=int(row.get('marcacion', 0)),
                        modeloDinamica_id=int(row['modeloDinamica_id'])
                    )
                    session.add(operacion)
                
                self.contadores['operaciones'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_OPERACION',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_transiciones(self, session: Session, df):
        if df is None or df.empty:
            self.advertencias.append("No hay datos de Transiciones")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(TransicionProd).filter_by(id=int(row['id'])).first()
                
                if existente:
                    existente.nombre = row['nombre']
                    existente.disparador = int(row.get('disparador', 0))
                    existente.mensajeSalida = row.get('mensajeSalida', '')
                    existente.modeloDinamica_id = int(row['modeloDinamica_id'])
                else:
                    transicion = TransicionProd(
                        id=int(row['id']),
                        nombre=row['nombre'],
                        disparador=int(row.get('disparador', 0)),
                        mensajeSalida=row.get('mensajeSalida', ''),
                        modeloDinamica_id=int(row['modeloDinamica_id'])
                    )
                    session.add(transicion)
                
                self.contadores['transiciones'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_TRANSICION',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_arcos_entrada(self, session: Session, df):
        if df is None or df.empty:
            self.advertencias.append("No hay datos de ArcosEntrada")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(ArcoEntrProd).filter_by(id=int(row['id'])).first()
                
                if existente:
                    existente.es_inhibidor = bool(row.get('es_inhibidor', False))
                    existente.lugar = int(row['lugar'])
                    existente.trans = int(row['trans'])
                    existente.modeloDinamica_id = int(row['modeloDinamica_id'])
                else:
                    arco = ArcoEntrProd(
                        id=int(row['id']),
                        es_inhibidor=bool(row.get('es_inhibidor', False)),
                        lugar=int(row['lugar']),
                        trans=int(row['trans']),
                        modeloDinamica_id=int(row['modeloDinamica_id'])
                    )
                    session.add(arco)
                
                self.contadores['arcos_entrada'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_ARCO_ENTRADA',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_arcos_salida(self, session: Session, df):
        if df is None or df.empty:
            self.advertencias.append("No hay datos de ArcosSalida")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(ArcoSalidaProd).filter_by(id=int(row['id'])).first()
                
                if existente:
                    existente.lugar = int(row['lugar'])
                    existente.trans = int(row['trans'])
                    existente.modeloDinamica_id = int(row['modeloDinamica_id'])
                else:
                    arco = ArcoSalidaProd(
                        id=int(row['id']),
                        lugar=int(row['lugar']),
                        trans=int(row['trans']),
                        modeloDinamica_id=int(row['modeloDinamica_id'])
                    )
                    session.add(arco)
                
                self.contadores['arcos_salida'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_ARCO_SALIDA',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })


def importar_productos(ruta_archivo: str) -> tuple:
    """Función de conveniencia para importar productos"""
    importador = ImportadorProductos(ruta_archivo)
    return importador.importar()


if __name__ == "__main__":
    ruta_default = Path(__file__).parent.parent / 'static' / 'plantillas' / '03_productos.xlsx'
    
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        ruta = ruta_default
    
    print(f"Importando: {ruta}")
    print()
    
    importador = ImportadorProductos(ruta)
    exito, mensaje, contadores, errores = importador.importar()
    
    print("=" * 80)
    print("IMPORTACIÓN DE PRODUCTOS")
    print("=" * 80)
    print(mensaje)
    
    if contadores:
        print("\n📊 Registros importados:")
        for key, value in contadores.items():
            print(f"  • {key}: {value}")
    
    if errores:
        print(f"\n❌ Errores ({len(errores)}):")
        for error in errores:
            print(f"  - {error.get('tipo')}: {error.get('mensaje')}")
    
    print()