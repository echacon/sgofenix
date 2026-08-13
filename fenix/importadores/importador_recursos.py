# importadores/importador_recursos.py (versión corregida)
from sqlalchemy.orm import Session
from modelos.Recursos import Recurso, RecursoEquipo, RecursoPersonal, UnidadFuncional, UnidadNegocio, Rol, ServicioTecnico
from typing import Dict, List, Tuple
import pandas as pd

class ImportadorRecursosExcel:
    def __init__(self, session: Session):
        self.session = session
        self.stats = {
            'recursos_base': 0,
            'recursos_equipo': 0,
            'recursos_personal': 0,
            'unidades_funcionales': 0,
            'unidades_negocio': 0,
            'roles': 0,
            'servicios_tecnicos': 0,
            'errores': []
        }
        self.uf_map = {}
        self.un_map = {}

    def importar(self, datos_validados: Dict) -> Tuple[bool, Dict]:
        try:
            # 1. Unidades Funcionales
            if not datos_validados['unidades_funcionales'].empty:
                self._importar_unidades_funcionales(datos_validados['unidades_funcionales'])
            
            # 2. Unidades Negocio
            if not datos_validados['unidades_negocio'].empty:
                self._importar_unidades_negocio(datos_validados['unidades_negocio'])
            
            # 3. Recursos (base) y Equipo/Personal
            if not datos_validados['recursos_equipo'].empty:
                self._importar_recursos_equipo(datos_validados['recursos_equipo'])
            if not datos_validados['recurso_personal'].empty:
                self._importar_recurso_personal(datos_validados['recurso_personal'])
            
            # 4. Roles y Servicios (opcional)
            if not datos_validados['roles'].empty:
                self._importar_roles(datos_validados['roles'])
            if 'servicios_tecnicos' in datos_validados and not datos_validados['servicios_tecnicos'].empty:
                self._importar_servicios_tecnicos(datos_validados['servicios_tecnicos'])
            
            self.session.commit()
            return True, self.stats
        except Exception as e:
            self.session.rollback()
            self.stats['errores'].append(str(e))
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False, self.stats

    def _importar_unidades_funcionales(self, df: pd.DataFrame):
        df = df.fillna('')
        objetos = {}
        for _, row in df.iterrows():
            if not row['nombre']:
                continue
            uf = UnidadFuncional(
                nombre=row['nombre'],
                descripcion=row['descripcion'] if row['descripcion'] else None
            )
            self.session.add(uf)
            self.session.flush()
            objetos[row['nombre']] = uf
            self.uf_map[row['nombre']] = uf
            self.stats['unidades_funcionales'] += 1
        # Establecer jerarquía
        for _, row in df.iterrows():
            nombre = row['nombre']
            padre = row['unidadPadre_nombre']
            if nombre and padre and padre != '' and nombre in objetos and padre in objetos:
                objetos[nombre].unidadPadre = objetos[padre]
        self.session.flush()

    def _importar_unidades_negocio(self, df: pd.DataFrame):
        df = df.fillna('')
        objetos = {}
        for _, row in df.iterrows():
            if not row['nombre']:
                continue
            un = UnidadNegocio(
                nombre=row['nombre'],
                descripcion=row['descripcion'] if row['descripcion'] else None
            )
            self.session.add(un)
            self.session.flush()
            objetos[row['nombre']] = un
            self.un_map[row['nombre']] = un
            self.stats['unidades_negocio'] += 1
        for _, row in df.iterrows():
            nombre = row['nombre']
            padre = row['unidadPadre_nombre']
            if nombre and padre and padre != '' and nombre in objetos and padre in objetos:
                objetos[nombre].unidadPadre = objetos[padre]
        self.session.flush()

    def _importar_recursos_equipo(self, df: pd.DataFrame):
        df = df.fillna('')
        for _, row in df.iterrows():
            if not row.get('nombre') or not row.get('codigo'):
                self.stats['errores'].append(f"Falta nombre o código en equipo: {row.to_dict()}")
                continue
            
            # Crear el Recurso base
            recurso_base = Recurso(
                codigo=row['codigo'],
                nombre=row['nombre'],
                tipo='equipo',
                descripcion=row.get('descripcion', None)
            )
            self.session.add(recurso_base)
            self.session.flush()  # para obtener id
            
            # Crear RecursoEquipo
            equipo = RecursoEquipo(
                id=recurso_base.id,
                modelo=row.get('modelo', ''),
                # unidad_funcional se asigna después si existe
            )
            # Asignar unidad funcional
            uf_nombre = row.get('unidadFuncional_nombre')
            if uf_nombre and uf_nombre in self.uf_map:
                equipo.unidad = self.uf_map[uf_nombre]
            
            # Parámetros adicionales (si existen columnas)
            if 'capacidad_maxima' in row and pd.notna(row['capacidad_maxima']):
                equipo.capacidad_maxima = float(row['capacidad_maxima'])
            if 'velocidad_procesamiento' in row and pd.notna(row['velocidad_procesamiento']):
                equipo.velocidad_procesamiento = float(row['velocidad_procesamiento'])
            if 'consumo_energia_kw' in row and pd.notna(row['consumo_energia_kw']):
                equipo.consumo_energia_kw = float(row['consumo_energia_kw'])
            if 'costo_depreciacion_hora' in row and pd.notna(row['costo_depreciacion_hora']):
                equipo.costo_depreciacion_hora = float(row['costo_depreciacion_hora'])
            if 'disponible' in row:
                equipo.disponible = bool(row['disponible'])
            
            self.session.add(equipo)
            self.stats['recursos_base'] += 1
            self.stats['recursos_equipo'] += 1
        self.session.flush()

    def _importar_recurso_personal(self, df: pd.DataFrame):
        df = df.fillna('')
        for _, row in df.iterrows():
            if not row.get('nombre') or not row.get('codigo'):
                self.stats['errores'].append(f"Falta nombre o código en personal: {row.to_dict()}")
                continue
            
            recurso_base = Recurso(
                codigo=row['codigo'],
                nombre=row['nombre'],
                tipo='personal',
                descripcion=row.get('descripcion', None)
            )
            self.session.add(recurso_base)
            self.session.flush()
            
            personal = RecursoPersonal(
                id=recurso_base.id
            )
            un_nombre = row.get('unidadNegocio_nombre')
            if un_nombre and un_nombre in self.un_map:
                personal.unidad = self.un_map[un_nombre]
            if 'costo_por_hora' in row and pd.notna(row['costo_por_hora']):
                personal.costo_por_hora = float(row['costo_por_hora'])
            if 'especialidad' in row and pd.notna(row['especialidad']):
                personal.especialidad = row['especialidad']
            if 'disponible' in row:
                personal.disponible = bool(row['disponible'])
            
            self.session.add(personal)
            self.stats['recursos_base'] += 1
            self.stats['recursos_personal'] += 1
        self.session.flush()

    def _importar_roles(self, df: pd.DataFrame):
        df = df.fillna('')
        for _, row in df.iterrows():
            if not row['nombre']:
                continue
            rol = Rol(nombre=row['nombre'], descripcion=row.get('descripcion', None))
            self.session.add(rol)
            self.stats['roles'] += 1
        self.session.flush()

    def _importar_servicios_tecnicos(self, df: pd.DataFrame):
        df = df.fillna('')
        for _, row in df.iterrows():
            if not row['nombre']:
                continue
            servicio = ServicioTecnico(nombre=row['nombre'], descripcion=row.get('descripcion', None))
            self.session.add(servicio)
            self.stats['servicios_tecnicos'] += 1
        self.session.flush()