# importadores/importador_taxonomia.py

"""
Importador de plantilla de taxonomía
Importa el archivo 02_taxonomia.xlsx a la base de datos
"""

import sys
import os
from pathlib import Path

# Agregar el directorio padre (sistema) al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy.orm import Session

from modelos.declarative_base import SessionLocal
from modelos.Taxonomia import (
    FamiliaProducto, TipoDeOperacion, PatronDeRuta, EtapaRuta,
    TipoRecurso, CapacidadTipoOperacion, TransicionPatron,
    TParcoEnt, TParcoSal
)
from validadores.validador_taxonomia import ValidadorTaxonomia


class ImportadorTaxonomia:
    """Importador para la plantilla de taxonomía"""
    
    def __init__(self, ruta_archivo: str):
        """
        Inicializa el importador
        
        Args:
            ruta_archivo: Ruta al archivo Excel de taxonomía
        """
        self.ruta_archivo = Path(ruta_archivo)
        self.errores = []
        self.advertencias = []
        self.contadores = {
            'familias_producto': 0,
            'tipos_operacion': 0,
            'patrones_ruta': 0,
            'etapas_ruta': 0,
            'tipos_recurso': 0,
            'capacidades': 0,
            'transiciones_patron': 0,
            'arcos_entrada': 0,
            'arcos_salida': 0
        }
    
    def importar(self) -> tuple:
        """
        Ejecuta la importación completa
        
        Returns:
            tuple: (exito, mensaje, contadores, errores)
        """
        # Primero validar
        validador = ValidadorTaxonomia(self.ruta_archivo)
        es_valido, errores, advertencias, datos = validador.validar()
        
        if not es_valido:
            return False, "La validación falló. Corrija los errores antes de importar.", {}, errores
        
        self.advertencias = advertencias
        
        # Proceder con la importación
        session = SessionLocal()
        
        try:
            # Importar en orden (respetando dependencias)
            self._importar_familias_producto(session, datos.get('FamiliasProducto'))
            self._importar_tipos_operacion(session, datos.get('TiposDeOperacion'))
            self._importar_patrones_ruta(session, datos.get('PatronesDeRuta'))
            self._importar_etapas_ruta(session, datos.get('EtapasRuta'))
            self._importar_tipos_recurso(session, datos.get('TiposRecurso'))
            self._importar_capacidades(session, datos.get('Capacidades'))
            self._importar_transiciones_patron(session, datos.get('TransicionesPatron'))
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
    
    def _importar_familias_producto(self, session: Session, df):
        """Importa Familias de Producto"""
        if df is None or df.empty:
            self.advertencias.append("No hay datos de FamiliasProducto")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(FamiliaProducto).filter_by(
                    id=int(row['id'])
                ).first()
                
                if existente:
                    existente.nombre = row['nombre']
                    existente.descripcion = row.get('descripcion', '')
                else:
                    familia = FamiliaProducto(
                        id=int(row['id']),
                        nombre=row['nombre'],
                        descripcion=row.get('descripcion', '')
                    )
                    session.add(familia)
                
                self.contadores['familias_producto'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_FAMILIA_PRODUCTO',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_tipos_operacion(self, session: Session, df):
        """Importa Tipos de Operación"""
        if df is None or df.empty:
            self.advertencias.append("No hay datos de TiposDeOperacion")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(TipoDeOperacion).filter_by(
                    id=int(row['id'])
                ).first()
                
                if existente:
                    existente.nombre = row['nombre']
                    existente.descripcion = row.get('descripcion', '')
                else:
                    tipo = TipoDeOperacion(
                        id=int(row['id']),
                        nombre=row['nombre'],
                        descripcion=row.get('descripcion', '')
                    )
                    session.add(tipo)
                
                self.contadores['tipos_operacion'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_TIPO_OPERACION',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_patrones_ruta(self, session: Session, df):
        """Importa Patrones de Ruta"""
        if df is None or df.empty:
            self.advertencias.append("No hay datos de PatronesDeRuta")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(PatronDeRuta).filter_by(
                    id=int(row['id'])
                ).first()
                
                if existente:
                    existente.nombre = row['nombre']
                    existente.descripcion = row.get('descripcion', '')
                    existente.familiaProducto_id = int(row['familiaProducto_id'])
                else:
                    patron = PatronDeRuta(
                        id=int(row['id']),
                        nombre=row['nombre'],
                        descripcion=row.get('descripcion', ''),
                        familiaProducto_id=int(row['familiaProducto_id'])
                    )
                    session.add(patron)
                
                self.contadores['patrones_ruta'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_PATRON_RUTA',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_etapas_ruta(self, session: Session, df):
        """Importa Etapas de Ruta"""
        if df is None or df.empty:
            self.advertencias.append("No hay datos de EtapasRuta")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(EtapaRuta).filter_by(
                    id=int(row['id'])
                ).first()
                
                if existente:
                    existente.nombre = row['nombre']
                    existente.patronRuta_id = int(row['patronRuta_id'])
                    existente.tipoDeOperacion_id = int(row['tipoDeOperacion_id'])
                else:
                    etapa = EtapaRuta(
                        id=int(row['id']),
                        nombre=row['nombre'],
                        patronRuta_id=int(row['patronRuta_id']),
                        tipoDeOperacion_id=int(row['tipoDeOperacion_id'])
                    )
                    session.add(etapa)
                
                self.contadores['etapas_ruta'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_ETAPA_RUTA',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_tipos_recurso(self, session: Session, df):
        """Importa Tipos de Recurso"""
        if df is None or df.empty:
            self.advertencias.append("No hay datos de TiposRecurso")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(TipoRecurso).filter_by(
                    id=int(row['id'])
                ).first()
                
                if existente:
                    existente.nombre = row['nombre']
                    existente.descripcion = row.get('descripcion', '')
                else:
                    tipo = TipoRecurso(
                        id=int(row['id']),
                        nombre=row['nombre'],
                        descripcion=row.get('descripcion', '')
                    )
                    session.add(tipo)
                
                self.contadores['tipos_recurso'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_TIPO_RECURSO',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_capacidades(self, session: Session, df):
        """Importa Capacidades (CapacidadTipoOperacion)"""
        if df is None or df.empty:
            self.advertencias.append("No hay datos de Capacidades")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(CapacidadTipoOperacion).filter_by(
                    id=int(row['id'])
                ).first()
                
                if existente:
                    existente.tipoRecurso_id = int(row['tipoRecurso_id'])
                    existente.tipoOperacion_id = int(row['tipoOperacion_id'])
                    existente.eficiencia_estimada = float(row.get('eficiencia_estimada', 1.0))
                    existente.costo_por_hora = float(row.get('costo_por_hora', 0))
                else:
                    capacidad = CapacidadTipoOperacion(
                        id=int(row['id']),
                        tipoRecurso_id=int(row['tipoRecurso_id']),
                        tipoOperacion_id=int(row['tipoOperacion_id']),
                        eficiencia_estimada=float(row.get('eficiencia_estimada', 1.0)),
                        costo_por_hora=float(row.get('costo_por_hora', 0))
                    )
                    session.add(capacidad)
                
                self.contadores['capacidades'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_CAPACIDAD',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_transiciones_patron(self, session: Session, df):
        """Importa Transiciones de Patrón"""
        if df is None or df.empty:
            self.advertencias.append("No hay datos de TransicionesPatron")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(TransicionPatron).filter_by(
                    id=int(row['id'])
                ).first()
                
                if existente:
                    existente.nombre = row['nombre']
                    existente.patron_id = int(row['patron_id'])
                else:
                    transicion = TransicionPatron(
                        id=int(row['id']),
                        nombre=row['nombre'],
                        patron_id=int(row['patron_id'])
                    )
                    session.add(transicion)
                
                self.contadores['transiciones_patron'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_TRANSICION_PATRON',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })
    
    def _importar_arcos_entrada(self, session: Session, df):
        """Importa Arcos de Entrada (TParcoEnt)"""
        if df is None or df.empty:
            self.advertencias.append("No hay datos de ArcosEntrada")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(TParcoEnt).filter_by(
                    id=int(row['id'])
                ).first()
                
                if existente:
                    existente.nombre = row.get('nombre', '')
                    existente.trans_id = int(row['trans_id'])
                    existente.etapa_id = int(row['etapa_id'])
                else:
                    arco = TParcoEnt(
                        id=int(row['id']),
                        nombre=row.get('nombre', ''),
                        trans_id=int(row['trans_id']),
                        etapa_id=int(row['etapa_id'])
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
        """Importa Arcos de Salida (TParcoSal)"""
        if df is None or df.empty:
            self.advertencias.append("No hay datos de ArcosSalida")
            return
        
        for _, row in df.iterrows():
            try:
                existente = session.query(TParcoSal).filter_by(
                    id=int(row['id'])
                ).first()
                
                if existente:
                    existente.nombre = row.get('nombre', '')
                    existente.trans_id = int(row['trans_id'])
                    existente.etapa_id = int(row['etapa_id'])
                else:
                    arco = TParcoSal(
                        id=int(row['id']),
                        nombre=row.get('nombre', ''),
                        trans_id=int(row['trans_id']),
                        etapa_id=int(row['etapa_id'])
                    )
                    session.add(arco)
                
                self.contadores['arcos_salida'] += 1
                
            except Exception as e:
                self.errores.append({
                    'tipo': 'ERROR_ARCO_SALIDA',
                    'fila': row.get('id', 'desconocido'),
                    'mensaje': str(e)
                })


def importar_taxonomia(ruta_archivo: str) -> tuple:
    """
    Función de conveniencia para importar taxonomía
    
    Args:
        ruta_archivo: Ruta al archivo Excel
    
    Returns:
        tuple: (exito, mensaje, contadores, errores)
    """
    importador = ImportadorTaxonomia(ruta_archivo)
    return importador.importar()


if __name__ == "__main__":
    # Prueba del importador
    ruta_default = Path(__file__).parent.parent / 'static' / 'plantillas' / '02_taxonomia.xlsx'
    
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        ruta = ruta_default
    
    print(f"Importando: {ruta}")
    print()
    
    importador = ImportadorTaxonomia(ruta)
    exito, mensaje, contadores, errores = importador.importar()
    
    print("=" * 80)
    print("IMPORTACIÓN DE TAXONOMÍA")
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