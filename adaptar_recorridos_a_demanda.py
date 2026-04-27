"""Shim de compatibilidad: reexporta el adaptador refactorizado desde src/adapter.

Si el paquete no se puede importar, intenta cargar el adaptador archivado en
legacy/legacy_adaptador.py.
"""

from __future__ import annotations

import os
import sys

try:
    # Intentar importar el adaptador refactorizado desde el paquete dentro de APP
    from APP.src.adapter import *  # reexporta aggregate_by_block, aggregate_from_routes_csv, generate_demanda_csv, validate_routes_vs_paraderos, etc.
except Exception:
    try:
        # Si ejecutamos desde la raíz del proyecto, el paquete puede estar disponible como `src.adapter`
        from src.adapter import *
    except Exception:
        pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'legacy'))
        if pkg_dir not in sys.path:
            sys.path.insert(0, pkg_dir)
        try:
            import legacy_adaptador as _legacy
            globals().update({k: v for k, v in _legacy.__dict__.items() if not k.startswith('_')})
        except Exception as e:
            raise
