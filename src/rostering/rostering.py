# Wrapper para el motor de rostering legacy
import os
import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
try:
    import App.main_rostering_admm as legacy
except Exception:
    legacy = None

def ejecutar_admm_mensual(*args, **kwargs):
    if legacy and hasattr(legacy, 'ejecutar_admm_mensual'):
        return legacy.ejecutar_admm_mensual(*args, **kwargs)
    raise ImportError('Motor de rostering no disponible')
