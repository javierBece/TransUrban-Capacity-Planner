# 🛠️ Guía de Desarrollo

Esta guía está dirigida a desarrolladores que deseen entender la arquitectura interna, contribuir código, o extender la funcionalidad del proyecto.

## 📂 Estructura de Carpetas Detallada

```
.
├── app_transurban.py              # Punto de entrada - Ventana principal Tkinter
├── adaptar_recorridos_a_demanda.py    # Procesamiento CSV → Demanda
├── generador_rostering.py         # Generación de plantilla FT/PT
├── main_rostering_admm.py         # Motor ADMM - Asignación de turnos
├── Loader.py                      # Carga y precarga de datos
├── src/
│   ├── adapter/
│   │   ├── adapter.py             # Interfaz principal
│   │   ├── parsers.py             # Lectura y parseo de CSV
│   │   └── validators.py          # Validación fuzzy
│   └── rostering/
│       └── rostering.py           # Clases del dominio (RuteadorLegal, etc.)
└── ...
```

## 🏗️ Arquitectura General

### 1. **Capa de Entrada (UI)**
- **Archivo:** `app_transurban.py`
- **Componentes:** Tkinter widgets, GradientButton, pestañas
- **Responsabilidades:** 
  - Manejo de eventos del usuario
  - Threading para ejecuciones no bloqueantes
  - Actualización de UI desde threads secundarios

### 2. **Capa de Datos (Adapter)**
- **Archivo:** `src/adapter/`
- **Componentes:** Parsers, Validators
- **Responsabilidades:**
  - Lectura de archivos CSV
  - Validación fuzzy de paraderos
  - Transformación de datos en estructuras internas

### 3. **Capa de Lógica de Negocio (Rostering)**
- **Archivo:** `src/rostering/rostering.py`, `generador_rostering.py`
- **Componentes:** RuteadorLegal, MotorADMMTransUrban
- **Responsabilidades:**
  - Generación de demanda
  - Creación de plantilla de conductores
  - Implementación del algoritmo ADMM

## 🔄 Flujo de Datos

```
CSV Import
    ↓
Parser (src/adapter/parsers.py)
    ↓
Validator (src/adapter/validators.py)
    ↓
Loader (Loader.py) → demanda_mensual.csv
    ↓
RuteadorLegal (generador_rostering.py) → plantilla_mensual.csv
    ↓
MotorADMMTransUrban (main_rostering_admm.py)
    ↓
ROSTER_FINAL_TRANSURBAN.csv
```

## 🔧 Clases Principales

### `MotorADMMTransUrban`
**Ubicación:** `main_rostering_admm.py`

Implementa el algoritmo ADMM:
- `__init__(ids_conductores, ids_viajes, costos_base, df_viajes_completo)`
- `ejecutar_iteracion()` - Actualización rodante de conductores
- `actualizar_multiplicadores()` - Actualización de lambdas
- `calcular_costo_ajustado(viaje_id)` - Fórmula M4

**Parámetros clave (CONFIG):**
```python
CONFIG = {
    "rho_inicial": 0.5,        # Penalización inicial
    "rho_max": 10.0,           # Límite de penalización
    "rho_incremento": 1.05,    # Factor de crecimiento
    "max_iteraciones": 100,    # Máximo de iteraciones
    "alpha_equidad": 0.1       # Peso de equidad (opcional)
}
```

### `RuteadorLegal`
**Ubicación:** `generador_rostering.py`

Resuelve el Restricted Master Problem:
- `construir_mejor_ruta(costos_percibidos, conductor_id)` - Encuentra mejor ruta viable

Implementa restricciones:
- ✅ Descansos obligatorios (11h)
- ✅ Máximas horas de trabajo
- ✅ Fines de semana libres
- ✅ Balance punta/valle

### `Parsers`
**Ubicación:** `src/adapter/parsers.py`

Métodos principales:
- `aggregate_from_routes_csv(df_rutas)` - Agregar demanda por bloque
- `generate_demanda_csv(df_rutas, ruta_salida)` - Generar CSV de demanda

### `Validators`
**Ubicación:** `src/adapter/validators.py`

Métodos principales:
- `validate_paraderos(df_rutas, df_paraderos)` - Validación fuzzy
- `suggest_corrections(paradero, lista_disponibles)` - Sugerencias

## 🧪 Testing

Actualmente el proyecto no tiene suite de tests automatizados. Para agregar tests:

1. Crea carpeta `tests/`
2. Usa `pytest` o `unittest`
3. Estructura: `tests/test_[modulo].py`

**Ejemplo (a implementar):**
```python
# tests/test_rostering.py
import unittest
from main_rostering_admm import MotorADMMTransUrban

class TestMotorADMM(unittest.TestCase):
    def test_inicializacion(self):
        motor = MotorADMMTransUrban([1,2,3], [10,20,30], {}, None)
        assert len(motor.conductores) == 3
```

Para ejecutar:
```bash
pytest tests/
```

## 🚀 Mejoras Sugeridas

### Alto Impacto
1. **Tests automatizados** - Cobertura mínima 70%
2. **Type hints** - Agregar al código Python
3. **API REST** - FastAPI para acceso externo
4. **Logs estructurados** - Usar `logging` módulo

### Medio Impacto
5. **Caching** - Cachear cálculos repetidos
6. **Profiling** - Identificar bottlenecks (cProfile)
7. **Configuración externa** - YAML/JSON para params
8. **CI/CD** - GitHub Actions para tests

### Bajo Impacto
9. **Documentación API** - Sphinx/MkDocs
10. **Dark mode** - Tkinter theme adicional

## 🐛 Debugging

### Logs
La consola de la UI muestra logs en tiempo real. Para logs persistentes:
```python
import logging
logging.basicConfig(filename='debug.log', level=logging.DEBUG)
```

### Profiling
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# ... código a perfilar ...
profiler.disable()
stats = pstats.Stats(profiler)
stats.print_stats()
```

### Debugging interactivo
```python
import pdb
pdb.set_trace()  # Detiene ejecución aquí
```

## 📊 Métricas del Proyecto

**Líneas de código:** ~2,500  
**Módulos:** 6 principales  
**Dependencias:** 1 (pandas)  
**Complejidad ciclomática:** Media (ADMM es complejo inherentemente)  

## 🔐 Consideraciones de Seguridad

- ✅ No hay credenciales hardcodeadas
- ✅ Validación de entrada en parsers
- ⚠️ Rutas de archivos: validar antes de acceso
- ⚠️ Inyección CSV: escapar caracteres especiales

## 📖 Referencias Técnicas

### ADMM
- [Boyd et al. "Distributed Optimization and Statistical Learning"](https://web.stanford.edu/~boyd/papers/admm_distr_stats.html)
- **Feng et al. (2023)** - "An ADMM-based dual decomposition mechanism for integrating crew scheduling and rostering in an urban rail transit line" 
  - Transportation Research Part C: Emerging Technologies, 149, 104081
  - [DOI: 10.1016/j.trc.2023.104081](https://doi.org/10.1016/j.trc.2023.104081)
  - **Este paper fue la inspiración principal para la arquitectura del motor ADMM**
- Implementación adaptada para rostering

### Algoritmo de Rostering
- Restricted Master Problem (RMP)
- Subproblema del precio (Dual)
- Frontera de Pareto mediante búsqueda enumerativa
- Dual decomposition basada en Lagrangian relaxation

## 🤝 Contribuir Código

1. Fork el repositorio
2. Crea rama: `git checkout -b feature/mi-cambio`
3. Haz cambios con buenas prácticas:
   - Nombres descriptivos
   - Funciones pequeñas (<50 líneas)
   - Docstrings en funciones públicas
4. Agregar tests si aplica
5. Commit: `git commit -m "Add: descripción clara"`
6. Push y abre PR

---

**¡Bienvenido al equipo de desarrollo!** 🚀
