"""Compatibility shim: re-export funciones del adaptador refactorizado."""

from __future__ import annotations

from typing import Dict
from .parsers import (
    block_from_time,
    aggregate_by_block,
    aggregate_from_routes_csv,
    generate_demanda_csv,
)
from .validators import validate_routes_vs_paraderos

__all__ = [
    'block_from_time',
    'aggregate_by_block',
    'aggregate_from_routes_csv',
    'generate_demanda_csv',
    'validate_routes_vs_paraderos',
]
