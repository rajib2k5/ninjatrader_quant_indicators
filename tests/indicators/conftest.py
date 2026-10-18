"""Shared helpers for the per-indicator test files (tests/indicators/test_<Module>.py).

Each indicator has one test file, named by module (stable across rank relabels), containing:
  1. formula tests with hand-computed expected values (literals, arithmetic shown in comments);
  2. the C# interface contract (plots, exposed series, overlay/panel, default reference lines) -
     the names strategies and the validation harness depend on;
  3. a single-file compile against the installed NinjaTrader assemblies (marked slow);
  4. a check against values exported from NinjaTrader by the QIV_* harness (skipped until an
     export exists in validation/runs/ - see TESTING.md);
  5. at least one test_falsifier_* proving the formula tests reject a plausible wrong variant.
The reference implementations live in validation/pytests/qi_ref.py and backtest/qibt/patterns.py.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
IND_DIR = REPO / "indicators"
RUNS = REPO / "validation" / "runs"
for p in (REPO / "validation" / "pytests", REPO / "backtest"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: compiles NinjaScript or reads large files")


# ---- indicator source ----------------------------------------------------------------------
def indicator_file(module: str) -> Path:
    """indicators/QI_<NN>_<module>.cs (or QI_<module>.cs before a relabel); exactly one."""
    rx = re.compile(r"^QI_(?:\d\d_)?%s\.cs$" % re.escape(module))
    found = [p for p in IND_DIR.glob("QI_*.cs") if rx.match(p.name)]
    assert len(found) == 1, f"{module}: expected one indicator file, found {[p.name for p in found]}"
    return found[0]


def cs_contract(module: str) -> dict:
    """Parse the declarations other code depends on. Not a formula check."""
    text = indicator_file(module).read_text(encoding="utf-8")
    sd = re.search(r"State == State\.SetDefaults\)\s*\{(.*?)\n\t\t\t\}", text, re.S)
    sd = sd.group(1) if sd else ""
    overlay = re.search(r"\bIsOverlay\s*=\s*(true|false)\s*;", sd)
    plots = [m.group(1) for m in re.finditer(r'AddPlot\([^;]*?"([^"]+)"\s*\)\s*;', sd)]
    lines = {m.group(2): float(m.group(1)) for m in re.finditer(r'AddLine\([^,]+,\s*(-?[\d.]+)\s*,\s*"([^"]+)"\s*\)', sd)}
    defaults = {m.group(1): m.group(2).strip() for m in re.finditer(r"^\s*(\w+)\s*=\s*([^;]+);", sd, re.M)}
    series = re.findall(r"public\s+Series<double>\s+(\w+)\s*(?:\{|=>)", text)
    cls = re.search(r"public\s+class\s+(\w+)\s*:\s*Indicator", text).group(1)
    display = re.search(r'DisplayName\s*\{\s*get\s*\{\s*return\s*"([^"]+)"', text)
    return {"class": cls, "overlay": overlay and overlay.group(1) == "true", "plots": plots,
            "lines": lines, "defaults": defaults, "series": series,
            "display": display.group(1) if display else None, "text": text}


def expected_names(module: str) -> dict | None:
    """The rank-based names from backtest/names.json, or None before a relabel."""
    f = REPO / "backtest" / "names.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8")).get(module)


def assert_names(module: str, c: dict):
    n = expected_names(module)
    if n is None:
        assert c["class"] == f"QI_{module}"
    else:
        assert c["class"] == n["qi"], (c["class"], n["qi"])
        assert c["defaults"].get("Name") == f'"{n["qi"]}"'
        assert c["display"] == n["display"]


# ---- compile -------------------------------------------------------------------------------
def compile_alone(path: Path) -> subprocess.CompletedProcess:
    bash = shutil.which("bash")
    probe = REPO / "validation" / "probes" / "compile_probe.sh"
    if not bash or not probe.exists():
        pytest.skip("bash or compile_probe.sh not available")
    out = Path(pytest.importorskip("tempfile").gettempdir()) / f"qi_probe_{path.stem}.dll"
    return subprocess.run([bash, str(probe), str(path)], cwd=REPO, capture_output=True, text=True,
                          env={**__import__("os").environ, "OUT": str(out)}, timeout=600)


# ---- NinjaTrader export (QIV_* harness) ----------------------------------------------------
def harness_frame() -> pd.DataFrame:
    files = sorted(RUNS.glob("qi_dump_*.csv"), key=lambda p: p.stat().st_mtime)
    if not files:
        pytest.skip("no NinjaTrader export yet (validation/runs/qi_dump_*.csv) - see TESTING.md")
    df = pd.read_csv(files[-1])
    if df.empty:
        pytest.skip(f"{files[-1].name} has no rows")
    return df


def harness_col(df: pd.DataFrame, module: str, member: str) -> pd.Series:
    rx = re.compile(r"^QI_(?:\d\d_)?%s\.%s$" % (re.escape(module), re.escape(member)))
    cols = [c for c in df.columns if rx.match(c)]
    if not cols:
        pytest.skip(f"export has no column for {module}.{member}")
    return pd.to_numeric(df[cols[0]], errors="coerce")


def assert_close(ref, got, start: int, tol: float, label: str):
    r = np.asarray(ref, dtype=float)[start:]
    g = np.asarray(got, dtype=float)[start:]
    both = ~np.isnan(r) & ~np.isnan(g)
    assert both.sum() > 0, f"{label}: nothing to compare"
    bad = np.flatnonzero(np.abs(r[both] - g[both]) > tol)
    assert bad.size == 0, f"{label}: {bad.size} of {both.sum()} bars differ > {tol}; first at offset {np.flatnonzero(both)[bad[0]] + start}"


# ---- bar builders --------------------------------------------------------------------------
def bars(close, open_=None, high=None, low=None, volume=None, start="2026-01-05 09:00", freq="1D"):
    c = np.asarray(close, dtype=float)
    o = c if open_ is None else np.asarray(open_, dtype=float)
    h = np.maximum(o, c) if high is None else np.asarray(high, dtype=float)
    lo = np.minimum(o, c) if low is None else np.asarray(low, dtype=float)
    v = np.full(len(c), 1000.0) if volume is None else np.asarray(volume, dtype=float)
    return pd.DataFrame({"BarTime": pd.date_range(start, periods=len(c), freq=freq),
                         "Open": o, "High": h, "Low": lo, "Close": c, "Volume": v})
