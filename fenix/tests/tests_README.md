# Tests — FÉNIX

Los tests están organizados siguiendo la estructura del proyecto.

## Cómo correr los tests

```bash
# Desde la raíz del proyecto, con el entorno virtual activo:
pytest

# Con reporte de cobertura:
pytest --cov=. --cov-report=html
# El reporte queda en htmlcov/index.html

# Solo un módulo:
pytest tests/test_motor.py -v
```

## Estructura prevista

```
tests/
├── README.md               (este archivo)
├── conftest.py             (fixtures compartidos: sesión BD, motor, etc.)
│
├── test_motor.py           → utils/motor_abtppn.py
├── test_orquestador.py     → servicios/orquestador.py
├── test_parser_pnml.py     → utils/parser_pnml.py
├── test_importadores.py    → importadores/
├── test_validadores.py     → validadores/
└── test_api.py             → app.py (endpoints Flask)
```

## Scripts de prueba existentes

Los scripts en `scripts/pruebas/` no son tests formales pero sirven como
referencia para escribirlos. En particular:

- `scripts/pruebas/simular_secuencia_real.py` — simula una orden completa
- `scripts/pruebas/depurar_paso_a_paso.py` — inspecciona el estado paso a paso

## Contribuir tests

Si quieres contribuir, los módulos más críticos y con menos cobertura son:

1. `utils/motor_abtppn.py` — lógica central de disparo de transiciones
2. `servicios/orquestador.py` — coordinación de redes
3. `importadores/importador_encadenamiento.py` — parsing de reglas

Un test mínimo útil para el motor:

```python
# tests/test_motor.py
import pytest
from utils.motor_abtppn import MotorABTPPN, TokenColoreado
from datetime import datetime

@pytest.fixture
def motor():
    return MotorABTPPN()

def test_crear_instancia_red_no_cargada(motor):
    token = TokenColoreado("ORD-001", 100.0, 0.0, datetime.now())
    resultado = motor.crear_instancia("red_inexistente", 1, token)
    assert resultado is None
```
