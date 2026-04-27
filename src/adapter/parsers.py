from __future__ import annotations

from pathlib import Path
from typing import Dict

import math
import pandas as pd
import unicodedata
import re
import types

try:
    import exportar_recorridos_frecuencias as exporter
except Exception:
    exporter = None


def _read_csv_autodetect(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    # Try semicolon first, then comma, then automatic inference.
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


def block_from_time(t: str) -> int | None:
    if not t or pd.isna(t):
        return None
    try:
        hh = int(t.split(":")[0])
    except Exception:
        return None
    if 0 <= hh < 4:
        return 1
    if 4 <= hh < 8:
        return 2
    if 8 <= hh < 12:
        return 3
    if 12 <= hh < 16:
        return 4
    if 16 <= hh < 20:
        return 5
    if 20 <= hh < 24:
        return 6
    return None


def aggregate_by_block(outputs_csv: str | Path) -> Dict[int, int]:
    p = Path(outputs_csv)
    if not p.exists():
        raise FileNotFoundError(p)

    df = _read_csv_autodetect(p)
    block_totals: Dict[int, int] = {i: 0 for i in range(1, 7)}

    if 'times' not in df.columns:
        raise ValueError("El CSV no contiene la columna 'times'.")

    for _, row in df.iterrows():
        times_field = str(row.get('times', '')).strip('"')
        if not times_field:
            continue
        times = [t.strip() for t in times_field.split(';') if t.strip()]
        for t in times:
            b = block_from_time(t)
            if b:
                block_totals[b] += 1

    return block_totals


def aggregate_from_routes_csv(routes_csv: str | Path, include_reverse: bool = False, match_alternate: bool = True, turnaround_min: int = 0) -> Dict[int, int]:
    """Lee el CSV oficial de rutas y calcula la demanda por bloque.

    Si el CSV tiene una columna `Terminal_logico`, esta se usa para decidir
    si una ruta puede generar un reverso sintético, porque los cambios de
    chofer sólo pueden ocurrir en terminales lógicos.
    """
    p = Path(routes_csv)
    if not p.exists():
        raise FileNotFoundError(p)

    df = _read_csv_autodetect(p)
    if df.empty:
        return {i: 0 for i in range(1, 7)}

    rec_col = None
    range_col = None
    freq_col = None
    dur_col = None
    origin_col = None
    dest_col = None
    terminal_col = None

    for col in df.columns:
        lc = str(col).strip().lower()
        if terminal_col is None and ('terminal_logico' in lc or 'terminal logico' in lc or lc == 'terminal'):
            terminal_col = col
        if rec_col is None and ('recorr' in lc or 'ruta' in lc):
            rec_col = col
        if range_col is None and ('rango' in lc or 'horario' in lc):
            range_col = col
        if freq_col is None and ('frecuenc' in lc or 'headway' in lc):
            freq_col = col
        if dur_col is None and ('tiempo' in lc or 'durac' in lc):
            dur_col = col
        if origin_col is None and 'origen' in lc:
            origin_col = col
        if dest_col is None and 'dest' in lc:
            dest_col = col

    processed = []
    for idx, row in df.iterrows():
        try:
            start_dt, end_dt = exporter.parse_range(row.get(range_col, '') if range_col else '')
        except Exception:
            start_dt, end_dt = None, None
        try:
            headway = exporter.parse_headway(row.get(freq_col, None) if freq_col else None)
        except Exception:
            headway = None

        dur = None
        if dur_col:
            try:
                v = row.get(dur_col)
                if v == "" or pd.isna(v):
                    dur = None
                else:
                    dur = float(str(v).replace(',', '.'))
            except Exception:
                dur = None

        if headway and headway > 0 and dur:
            buses_needed = max(1, int(math.ceil(dur / headway)))
        else:
            if headway and headway > 0:
                buses_needed = max(1, int(math.ceil(60.0 / headway)))
            else:
                buses_needed = 1

        origin = row.get(origin_col) if origin_col in df.columns else None
        dest = row.get(dest_col) if dest_col in df.columns else None
        terminal = row.get(terminal_col) if terminal_col in df.columns else None

        processed.append({
            'origin': origin,
            'dest': dest,
            'terminal': terminal,
            'start_dt': start_dt,
            'end_dt': end_dt,
            'headway': headway,
            'dur': dur,
            'buses': buses_needed,
            'idx': idx,
        })

    block_totals: Dict[int, int] = {i: 0 for i in range(1, 7)}
    block_ranges = [
        (0, 4),
        (4, 8),
        (8, 12),
        (12, 16),
        (16, 20),
        (20, 24),
    ]

    def add_to_blocks(start_dt, end_dt, buses):
        if start_dt is None:
            return
        if end_dt < start_dt:
            end_dt = end_dt + pd.Timedelta(days=1)
        s_hour = start_dt.hour + start_dt.minute / 60.0
        e_hour = end_dt.hour + end_dt.minute / 60.0
        for i, (bstart, bend) in enumerate(block_ranges, start=1):
            if s_hour < bend and e_hour > bstart:
                block_totals[i] += buses

    for r in processed:
        add_to_blocks(r['start_dt'], r['end_dt'], r['buses'])

    if include_reverse:
        origin_map = {}
        pair_set = set()
        for r in processed:
            origin_map.setdefault(r['origin'], []).append(r)
            pair_set.add((r['origin'], r['dest']))

        for r in processed:
            if (r['dest'], r['origin']) in pair_set:
                continue
            alternates = origin_map.get(r['dest'], [])
            if alternates and match_alternate:
                continue
            # Sólo generar reversos sintéticos si la ruta termina en un terminal lógico,
            # porque el cambio de chofer sólo debería ocurrir en un terminal.
            terminal = r.get('terminal')
            if terminal is None or str(terminal).strip() == "":
                continue
            start_dt = r['start_dt']
            end_dt = r['end_dt']
            if start_dt is None:
                continue
            if turnaround_min and isinstance(turnaround_min, int) and turnaround_min > 0:
                start_dt = start_dt + pd.Timedelta(minutes=turnaround_min)
                end_dt = end_dt + pd.Timedelta(minutes=turnaround_min)
            add_to_blocks(start_dt, end_dt, r['buses'])

    return block_totals


def generate_demanda_csv(block_totals: Dict[int, int], dias: int = 28, output_dir: str | Path = 'datos_rostering', weekend_factor: float | None = None) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for d in range(1, dias + 1):
        es_fin = (d % 7 == 6) or (d % 7 == 0)
        factor = weekend_factor if (es_fin and weekend_factor is not None) else 1.0
        b1 = int(round(block_totals.get(1, 0) * factor))
        b2 = int(round(block_totals.get(2, 0) * factor))
        b3 = int(round(block_totals.get(3, 0) * factor))
        b4 = int(round(block_totals.get(4, 0) * factor))
        b5 = int(round(block_totals.get(5, 0) * factor))
        b6 = int(round(block_totals.get(6, 0) * factor))

        rows.append({
            'Dia': d,
            'Es_Finde': es_fin,
            'B1_00_04': b1,
            'B2_04_08': b2,
            'B3_08_12': b3,
            'B4_12_16': b4,
            'B5_16_20': b5,
            'B6_20_24': b6,
        })

    out_df = pd.DataFrame(rows)
    out_file = out_dir / 'demanda_mensual.csv'
    out_df.to_csv(out_file, index=False, sep=';')
    return out_file


# Fallback exporter si no existe el módulo original
import re as _re
if exporter is None:
    def _fallback_parse_range(s: str):
        if not s or pd.isna(s):
            return None, None
        s = str(s)
        matches = _re.findall(r'([0-2]?\d[:.][0-5]\d)', s)
        if len(matches) >= 2:
            try:
                today = pd.Timestamp.today().normalize()
                h1 = pd.to_datetime(matches[0], format='%H:%M', errors='coerce')
                h2 = pd.to_datetime(matches[1], format='%H:%M', errors='coerce')
                if pd.isna(h1) or pd.isna(h2):
                    h1 = pd.to_datetime(matches[0], errors='coerce')
                    h2 = pd.to_datetime(matches[1], errors='coerce')
                if pd.isna(h1) or pd.isna(h2):
                    return None, None
                start = pd.Timestamp(year=today.year, month=today.month, day=today.day, hour=h1.hour, minute=h1.minute)
                end = pd.Timestamp(year=today.year, month=today.month, day=today.day, hour=h2.hour, minute=h2.minute)
                return start, end
            except Exception:
                return None, None
        if len(matches) == 1:
            try:
                today = pd.Timestamp.today().normalize()
                h1 = pd.to_datetime(matches[0], format='%H:%M', errors='coerce')
                if pd.isna(h1):
                    h1 = pd.to_datetime(matches[0], errors='coerce')
                if pd.isna(h1):
                    return None, None
                start = pd.Timestamp(year=today.year, month=today.month, day=today.day, hour=h1.hour, minute=h1.minute)
                end = start + pd.Timedelta(hours=1)
                return start, end
            except Exception:
                return None, None
        matches2 = _re.findall(r'(\d{1,2})\s*-\s*(\d{1,2})', s)
        if matches2:
            try:
                today = pd.Timestamp.today().normalize()
                sh, eh = matches2[0]
                start = pd.Timestamp(year=today.year, month=today.month, day=today.day, hour=int(sh), minute=0)
                end = pd.Timestamp(year=today.year, month=today.month, day=today.day, hour=int(eh), minute=0)
                return start, end
            except Exception:
                return None, None
        return None, None

    def _fallback_parse_headway(s):
        if s is None:
            return None
        s = str(s).strip()
        if not s:
            return None
        s2 = s.lower().replace('min', '').replace('mins', '').strip()
        if ':' in s2 or '.' in s2:
            parts = _re.split('[:.]', s2)
            try:
                h = int(parts[0]) if parts[0] else 0
                m = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                return h*60 + m
            except Exception:
                pass
        try:
            return float(s2)
        except Exception:
            m = _re.search(r'\d+', s2)
            if m:
                return float(m.group())
            return None

    exporter = types.SimpleNamespace(parse_range=_fallback_parse_range, parse_headway=_fallback_parse_headway)
