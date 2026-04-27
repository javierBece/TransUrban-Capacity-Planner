from __future__ import annotations

from pathlib import Path
from collections import Counter
import json
import unicodedata
import re
import difflib
import pandas as pd
from typing import Dict

# Carpeta APP raíz (tres niveles arriba: APP/src/adapter -> APP)
APP_DIR = Path(__file__).resolve().parents[2]


def _read_csv_autodetect(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    for sep in [';', ',', '\t']:
        try:
            df = pd.read_csv(p, sep=sep, dtype=str, encoding='latin-1').fillna('')
            if df.shape[1] > 1 or (df.shape[0] > 0 and len(df.columns) > 1):
                return df
            if df.shape[0] > 0 and any(str(c).strip() for c in df.columns):
                return df
        except Exception:
            continue

    try:
        df = pd.read_csv(p, sep=None, engine='python', dtype=str, encoding='latin-1').fillna('')
        if df.shape[1] == 0:
            raise ValueError(f'No se pudieron detectar columnas en {p}')
        return df
    except Exception as exc:
        raise ValueError(f'No se pudo leer el CSV {p}: {exc}') from exc

_STOPWORDS = set(['los','las','el','la','de','del','y','en','estacion','estaci','terminal','metro','plaza','diagonal','av','av.','avenida'])


def _normalize_text(s: str) -> str:
    if s is None:
        return ""
    try:
        t = str(s)
    except Exception:
        return ""
    t = t.strip().lower()
    if not t:
        return ""
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def validate_routes_vs_paraderos(routes_csv: str | Path, paraderos_csv: str | Path | None = None) -> Dict:
    routes_p = Path(routes_csv)
    if not routes_p.exists():
        raise FileNotFoundError(routes_p)

    df = _read_csv_autodetect(routes_p)
    origin_col = None
    dest_col = None
    for col in df.columns:
        lc = str(col).lower()
        if origin_col is None and ('origen' in lc or 'terminal' in lc or 'start' in lc):
            origin_col = col
        if dest_col is None and ('dest' in lc or 'terminal' in lc or 'end' in lc):
            dest_col = col

    values = []
    for _, row in df.iterrows():
        if origin_col and row.get(origin_col, ""):
            values.append(str(row.get(origin_col)))
        if dest_col and row.get(dest_col, ""):
            values.append(str(row.get(dest_col)))

    values = [v for v in (v.strip() for v in values) if v]
    total_checked = len(values)

    if paraderos_csv:
        par_p = Path(paraderos_csv)
    else:
        par_p = APP_DIR / 'datos' / 'Paraderos TRANSURBAN.csv'

    if not par_p.exists():
        return {
            'ok': True,
            'missing_values': [],
            'total_checked': total_checked,
            'report': f'Archivo de paraderos no encontrado: {par_p} — validación omitida.'
        }

    par_df = _read_csv_autodetect(par_p)
    candidate_cols = [c for c in par_df.columns if any(k in str(c).lower() for k in ('parad', 'paradero', 'nombre', 'stop', 'id', 'codigo', 'origen', 'dest', 'recorr'))]
    if not candidate_cols:
        candidate_cols = list(par_df.columns)

    par_values = set()
    for c in candidate_cols:
        for v in par_df[c].astype(str):
            nv = _normalize_text(v)
            if nv:
                par_values.add(nv)
    for colname in par_df.columns:
        lc = str(colname).lower()
        if 'origen' in lc or 'dest' in lc:
            for v in par_df[colname].astype(str):
                nv = _normalize_text(v)
                if nv:
                    par_values.add(nv)

    map_path = APP_DIR / 'datos' / 'paraderos_map.json'
    manual_map = {}
    if map_path.exists():
        try:
            with open(map_path, 'r', encoding='utf-8') as f:
                raw_map = json.load(f)
            for k, v in raw_map.items():
                nk = _normalize_text(k)
                nv = _normalize_text(v)
                if nk and nv:
                    manual_map[nk] = nv
                    par_values.add(nv)
        except Exception:
            manual_map = {}

    missing = []
    for v in values:
        nv = _normalize_text(v)
        if not nv:
            continue
        if nv in manual_map:
            nv = manual_map[nv]
        if nv in par_values:
            continue
        if any(nv in pv or pv in nv for pv in par_values):
            continue
        nv_tokens = [t for t in nv.split() if t not in _STOPWORDS]
        matched_by_tokens = False
        if nv_tokens:
            for pv in par_values:
                pv_tokens = [t for t in pv.split() if t not in _STOPWORDS]
                if not pv_tokens:
                    continue
                overlap = len(set(nv_tokens) & set(pv_tokens)) / max(1, len(set(nv_tokens)))
                if overlap >= 0.6:
                    matched_by_tokens = True
                    break
        if matched_by_tokens:
            continue
        close = difflib.get_close_matches(nv, list(par_values), n=1, cutoff=0.85)
        if close:
            continue
        missing.append(nv)

    missing_counts = Counter(missing)
    missing_list = sorted(missing_counts.items(), key=lambda x: -x[1])
    ok = len(missing_list) == 0

    suggestions = {}
    par_list = list(par_values)
    for val, _ in missing_list:
        sgs = []
        fuzzy = difflib.get_close_matches(val, par_list, n=3, cutoff=0.75)
        for f in fuzzy:
            if f not in sgs:
                sgs.append(f)
        for pv in par_list:
            if val in pv or pv in val:
                if pv not in sgs:
                    sgs.append(pv)
        val_tokens = [t for t in val.split() if t not in _STOPWORDS]
        scores = []
        for pv in par_list:
            pv_tokens = [t for t in pv.split() if t not in _STOPWORDS]
            if not val_tokens or not pv_tokens:
                continue
            overlap = len(set(val_tokens) & set(pv_tokens)) / max(1, len(set(val_tokens)))
            if overlap > 0:
                scores.append((overlap, pv))
        scores.sort(reverse=True)
        for score, pv in scores[:3]:
            if pv not in sgs:
                sgs.append(pv)
        suggestions[val] = sgs

    report_lines = []
    report_lines.append(f'Validación Rutas vs Paraderos — archivo paraderos: {par_p.name}')
    report_lines.append(f'Totales comprobados: {total_checked}')
    report_lines.append(f'Valores únicos no encontrados: {len(missing_list)}')
    if missing_list:
        report_lines.append('Primeros 20 valores faltantes (valor: ocurrencias):')
        for val, c in missing_list[:20]:
            report_lines.append(f' - {val}: {c}')
            s = suggestions.get(val, [])
            if s:
                report_lines.append(f'   -> Sugerencias: {", ".join(s[:5])}')

    report = "\n".join(report_lines)

    return {
        'ok': ok,
        'missing_values': missing_list,
        'total_checked': total_checked,
        'report': report,
        'suggestions': suggestions,
    }
