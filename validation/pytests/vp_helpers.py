"""conftest.py - shared paths, CSV loaders and markers for the Channel B test suite.

Self-contained: nothing here imports from elsewhere in the repository.
Run from the repository root with:  python -I -m pytest validation/pytests -q
"""
from __future__ import annotations

import csv
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
INDICATORS_DIR = REPO / "indicators"
RUNS_DIR = REPO / "validation" / "runs"
PROBES_DIR = REPO / "validation" / "probes"
COMPILE_PROBE = PROBES_DIR / "compile_probe.sh"
LEDGER = REPO / "validation" / "algo-claims-ledger.md"

# Original (pre-split) indicator EveryBar export. HEADER layout (see validation/probes/diff_values.py):
#   0 Timestamp, 1 BarTime, 2 Symbol, 3 Timeframe, 4 SignalType, ..., 14 Open, 15 High, 16 Low,
#   17 Close, 18 Volume, 19 ATR14, ...  Bar rows carry one surplus field (Open..Volume at 15..19),
#   so load_old_export aligns each row by len(row) - len(header). Signal rows (column 4 non-empty)
#   are skipped.
OLD_EXPORT = Path(r"C:\Users\rajib\OneDrive\Docs\futures_data\ninja_trader_signal_data"
                  r"\MES_150tick_20250202_20260224.csv")
OLD_EXPORT_ROWS = 20_000

# The harness writes every value with ToString("F4"), i.e. rounded to 4 decimals. A ledger
# tolerance tighter than that rounding (1e-6) can only be tested as tolerance + half an ULP of
# the 4th decimal. This allowance is applied uniformly in the differential and is recorded in
# validation/channel-b-algo.md.
CSV_QUANT = 0.5e-4 + 1e-9

OHLCV = ["Open", "High", "Low", "Close", "Volume"]


# --------------------------------------------------------------------------------------------
# Harness CSV (validation/runs/qi_dump_*.csv written by QI_EgvDump)
# --------------------------------------------------------------------------------------------
def harness_files() -> list:
    return sorted(glob.glob(str(RUNS_DIR / "qi_dump_*.csv")))


def newest_harness_file():
    # QI_HARNESS_FILE overrides the newest-file rule (used for self-consistency smokes of the
    # differential; any such run must be reported as a smoke, never as a verdict).
    override = os.environ.get("QI_HARNESS_FILE")
    if override:
        return override
    files = harness_files()
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def load_harness(path) -> pd.DataFrame:
    """Load a QI_EgvDump CSV. Blank cells (NaN/Infinity in NinjaTrader) become NaN."""
    df = pd.read_csv(path, na_values=[""], keep_default_na=True)
    df["BarTime"] = pd.to_datetime(df["BarTime"], format="%Y-%m-%d %H:%M:%S")
    for c in OHLCV:
        df[c] = df[c].astype(float)
    return df.reset_index(drop=True)


@pytest.fixture(scope="session")
def harness():
    """Newest harness CSV as a DataFrame, or skip (UNVERIFIABLE) when none has data rows."""
    path = newest_harness_file()
    if path is None:
        pytest.skip("UNVERIFIABLE: no validation/runs/qi_dump_*.csv harness file exists")
    df = load_harness(path)
    if len(df) == 0:
        pytest.skip("UNVERIFIABLE: harness file %s has a header but no data rows" % os.path.basename(path))
    df.attrs["path"] = path
    return df


# --------------------------------------------------------------------------------------------
# Original-indicator export (first N rows only; the file is 168 MB)
# --------------------------------------------------------------------------------------------
def load_old_export(path=OLD_EXPORT, nrows=OLD_EXPORT_ROWS) -> pd.DataFrame:
    """First `nrows` rows of the original export, bar rows only (column 4 SignalType empty).

    Data finding (2026-10-16): the header has 53 fields but every bar row has 54, i.e. the bar
    rows carry one extra empty field before Open, so Open..Volume are at 15..19 rather than the
    header's 14..18. The loader aligns by the per-row field-count surplus and records it in
    df.attrs["column_shift"] so test_data_integrity can report it.
    """
    recs = []
    shifts = set()
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        base = header.index("Open")
        for i, row in enumerate(reader):
            if i >= nrows:
                break
            if len(row) < 19 or row[4] != "":
                continue  # signal rows carry no bar data
            shift = len(row) - len(header)
            shifts.add(shift)
            o = base + shift
            recs.append((row[1],) + tuple(row[o:o + 5]))
    df = pd.DataFrame(recs, columns=["BarTime"] + OHLCV)
    df["BarTime"] = pd.to_datetime(df["BarTime"], format="%Y-%m-%d %H:%M:%S")
    for c in OHLCV:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df.attrs["column_shift"] = sorted(shifts)
    df.attrs["header_len"] = len(header)
    return df.reset_index(drop=True)


@pytest.fixture(scope="session")
def old_export():
    if not OLD_EXPORT.exists():
        pytest.skip("original-indicator export not present: %s" % OLD_EXPORT)
    return load_old_export()


# --------------------------------------------------------------------------------------------
# Synthetic bar helpers shared by unit/property tests
# --------------------------------------------------------------------------------------------
def make_df(open_, high, low, close, volume=None, start="2026-01-05 09:30:00", freq="15min"):
    n = len(close)
    if volume is None:
        volume = np.full(n, 100.0)
    df = pd.DataFrame({
        "BarTime": pd.date_range(start, periods=n, freq=freq),
        "Open": np.asarray(open_, dtype=float),
        "High": np.asarray(high, dtype=float),
        "Low": np.asarray(low, dtype=float),
        "Close": np.asarray(close, dtype=float),
        "Volume": np.asarray(volume, dtype=float),
    })
    return df


def df_from_close(close, wick=0.0, volume=None, **kw):
    """Bars whose open is the previous close (first open = first close) with optional wick."""
    close = np.asarray(close, dtype=float)
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) + wick
    low = np.minimum(open_, close) - wick
    return make_df(open_, high, low, close, volume, **kw)
