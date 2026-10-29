"""Unit tests for QI_28_IcebergDetector - probable iceberg orders at the best bid/ask (unranked; live/Market Replay only).

Spec: validation/iceberg/spec.md (FROZEN 2026-10-28), claims I1-I8. The rules are tested in depth against the Python
reference in backtest/tests/test_iceberg.py (I3, I4, I5); this file covers the C# side:
  - the interface contract and the live-only guard (I6, I7);
  - the table box (table-spec.md): no price labels or TopLeft notice remain (P5), every SharpDX resource is disposed
    (P6), and the C# table/layout tests (P1, P2) pass and catch a planted mutant;
  - the C# IcebergEngine run as a console exe against hand-built streams, the C#-vs-Python differential with its
    falsifier (I2) and a no-look-ahead prefix check on the C# side (I4);
  - a single-file compile (I1);
  - a NinjaTrader export check: on historical bars the indicator must leave its plots unset (spec section 0).
Reference: backtest/qibt/iceberg.py (written independently of the C# file).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from qi_helpers import REPO, compile_alone, cs_contract, harness_frame, indicator_file

MODULE = "IcebergDetector"
ICE = REPO / "validation" / "iceberg"
STREAMS = ICE / "harness" / "streams"
PLOTS = ["IcebergBidVolume", "IcebergAskVolume", "IcebergCount", "MaxConfidence"]
NOTICE = "Iceberg detection runs on live or Market Replay data (historical Tick Replay has no bid/ask sizes)."

_COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def _code(text: str) -> str:
    return _COMMENT_RE.sub("", text)


def _method_body(code: str, name: str) -> str:
    m = re.search(r"override\s+void\s+%s\s*\([^)]*\)\s*\{" % name, code)
    assert m, f"no {name} override"
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(code[i], 0)
        i += 1
    return code[m.end():i - 1]


def _engine_block(text: str) -> str:
    m = re.search(r"namespace\s+[\w.]*Engines\s*\{", text)
    assert m, "IcebergEngine namespace not found"
    return text[m.start():]


def _overrides_depth(code: str) -> bool:
    return bool(re.search(r"override\s+void\s+OnMarketDepth\s*\(", code))


# ---- 1. contract and live-only guard (I6, I7) ----------------------------------------------
def test_contract_overlay_four_databox_plots_and_series():
    c = cs_contract(MODULE)
    assert c["class"] == "QI_28_IcebergDetector"
    assert c["defaults"].get("Name") == '"QI_28_IcebergDetector"'
    assert c["overlay"] is True
    assert c["plots"] == PLOTS
    assert sorted(c["series"]) == sorted(PLOTS)
    assert all("Brushes.Transparent" in p for p in re.findall(r"AddPlot\(([^;]*)\);", c["text"]))
    assert not c["lines"]


def test_detection_only_in_realtime_and_never_on_depth():
    code = _code(indicator_file(MODULE).read_text(encoding="utf-8"))
    assert not _overrides_depth(code)
    body = _method_body(code, "OnMarketData")
    guard = re.search(r"if\s*\(\s*State\s*!=\s*State\.Realtime\s*\)\s*return\s*;", body)
    assert guard, "OnMarketData must return unless State.Realtime"
    first_engine_call = min(body.find(k) for k in ("OnBid(", "OnAsk(", "OnTrade(") if k in body)
    assert guard.start() < first_engine_call, "the guard must come before any engine call"


def test_historical_notice_text_matches_the_spec():
    assert f'"{NOTICE}"' in indicator_file(MODULE).read_text(encoding="utf-8")


def test_table_box_replaces_price_labels_and_topleft_notice():
    """P5: the info lives in the OnRender box; no TopLeft notice (it sat on NinjaTrader's labels, T17)."""
    text = indicator_file(MODULE).read_text(encoding="utf-8")
    code = _code(text)
    assert "TextPosition.TopLeft" not in code
    assert " hidden (" not in code, "the old per-level price label text is still drawn"
    render = _method_body(code, "OnRender")
    assert "IcebergTable.Title" in render and "HistoricalNotice" in render
    assert "BoxLayout.Place(" in render and "Occupied(" in render
    c = cs_contract(MODULE)
    for prop, default in {"ShowTable": "true", "MaxTableRows": "8", "TableFontSize": "11",
                          "TableOpacity": "85", "ShowLevelLines": "true"}.items():
        assert c["defaults"].get(prop) == default, (prop, c["defaults"].get(prop))
    assert "ShowLabels" not in code


def _dispose_issues(code: str) -> list:
    """P6 checker: brushes from ToDxBrush must be in DisposeDx; layouts/formats must be disposed."""
    issues = []
    dx_fields = set(re.findall(r"\b(\w+)\s*=\s*[^;=]*?\.ToDxBrush\(", code))
    m = re.search(r"void\s+DisposeDx\s*\(\s*\)\s*\{(.*?)\n\t\t\}", code, re.S)
    body = m.group(1) if m else ""
    # only the brushes in the array the foreach disposes count (the "= null" line names them all)
    arr = re.search(r"DxBrush\[\]\s+all\s*=\s*\{([^}]*)\}", body)
    disposed = set(re.findall(r"\b(dx\w+)\b", arr.group(1))) if arr and ".Dispose()" in body else set()
    issues += [f"brush {f} never disposed" for f in sorted(dx_fields - disposed)]
    for hook in ("OnRenderTargetChanged",):
        if "DisposeDx()" not in _method_body(code, hook):
            issues.append(f"{hook} does not dispose")
    term = re.search(r"State\s*==\s*State\.Terminated\)\s*\{(.*?)\}", code, re.S)
    if not term or "DisposeDx()" not in term.group(1):
        issues.append("State.Terminated does not dispose")
    for mt in re.finditer(r"new\s+TextLayout\(", code):
        line_start = code.rfind("\n", 0, mt.start())
        line = code[line_start:code.find("\n", mt.end())]
        after = code[mt.end():mt.end() + 200]
        if "using (" not in line and "made.Add(" not in after:
            issues.append("TextLayout not disposed: " + line.strip()[:80])
    for mt in re.finditer(r"\.ToDirectWriteTextFormat\(\)", code):
        line = code[code.rfind("\n", 0, mt.start()):mt.end()]
        if "using (" not in line:
            issues.append("TextFormat not in using: " + line.strip()[:80])
    return issues


def test_sharpdx_resources_are_disposed():
    assert _dispose_issues(_code(indicator_file(MODULE).read_text(encoding="utf-8"))) == []


def test_falsifier_dispose_check_flags_leaks():
    code = _code(indicator_file(MODULE).read_text(encoding="utf-8"))
    leaked_brush = re.sub(r"(DxBrush\[\]\s+all\s*=\s*\{[^}]*?),\s*dxAsk", r"\1", code)
    assert leaked_brush != code
    assert any("dxAsk" in i for i in _dispose_issues(leaked_brush))
    leaked_layout = code.replace("made.Add(l);", "", 1)
    assert any("TextLayout" in i for i in _dispose_issues(leaked_layout))


def test_engine_uses_no_ninjatrader_types():
    """IcebergEngine must load in a plain console exe (the I2 harness): System namespaces only."""
    text = indicator_file(MODULE).read_text(encoding="utf-8")
    block = _code(_engine_block(text))
    body = block[block.index("{"):]
    nt_types = re.findall(r"\b(MarketDataEventArgs|MarketDataType|Instrument|Bars|Draw|Brush\w*|State\.|NinjaTrader\.)", body)
    assert not nt_types, nt_types
    sig = re.search(r"public\s+IcebergEngine\s*\(\s*double\s+\w+\s*,\s*int\s+\w+\s*,\s*long\s+\w+\s*,\s*long\s+\w+\s*\)", body)
    assert sig, "constructor signature per spec section 7"


def test_falsifier_depth_and_guard_checks_reject_planted_variants():
    planted = "protected override void OnMarketDepth(MarketDepthEventArgs e) { }"
    assert _overrides_depth(planted)
    assert not _overrides_depth("protected virtual void OnMarketDepth(MarketDepthEventArgs e) { }")
    no_guard = "protected override void OnMarketData(MarketDataEventArgs e) { engine.OnBid(1, 1.0, 1); }"
    assert not re.search(r"if\s*\(\s*State\s*!=\s*State\.Realtime\s*\)\s*return\s*;", _method_body(no_guard, "OnMarketData"))


# ---- 2. C# engine as a console exe (I2, I4) -------------------------------------------------
@pytest.fixture(scope="module")
def harness_exe():
    bash = shutil.which("bash")
    script = ICE / "harness" / "build_harness.sh"
    if not bash:
        pytest.skip("bash not available")
    out = Path(tempfile.gettempdir()) / "qi28_harness" / "IcebergHarness.exe"
    r = subprocess.run([bash, str(script)], cwd=REPO, capture_output=True, text=True, timeout=600,
                       env={**__import__("os").environ, "OUT": str(out)})
    if r.returncode != 0:
        pytest.skip("harness build failed (NinjaTrader / .NET SDK not installed?):\n" + r.stdout[-1500:])
    return out


def _run(exe, path, *args):
    return [ln for ln in subprocess.run([str(exe), str(path), *args], capture_output=True, text=True,
                                        check=True, timeout=60).stdout.splitlines() if ln.strip()]


@pytest.mark.slow
def test_cs_engine_hand_stream_bid_iceberg(harness_exe):
    # s1: bid 7012.25 shows 10; three absorbed trades each followed by a refill; then the bid drops.
    # Flag at seq 9: traded 25 >= 2.0 x shown_max 10, refills 2, traded >= 20 -> conf 0.4 + 0 + 0.1 x (2.5 - 2) = 0.45
    # Final at seq 14: traded 35, shown_max 12, refills 3 -> conf 0.4 + 0.15 + 0.1 x (35/12 - 2) = 0.6417 ; broken
    assert _run(harness_exe, STREAMS / "s1_bid_iceberg.csv") == [
        "FLAG,bid,7012.2500,9,25,10,2,0.4500",
        "FINAL,bid,7012.2500,1,14,35,12,23,3,10.0000,broken,0.6417"]
    assert _run(harness_exe, STREAMS / "s1_bid_iceberg.csv", "--hidden-ratio", "3.0") == []


@pytest.mark.slow
def test_cs_engine_hand_streams_join_and_ask_mirror(harness_exe):
    assert _run(harness_exe, STREAMS / "s2_no_trade_join.csv") == []
    assert _run(harness_exe, STREAMS / "s3_ask_mirror.csv") == [
        "FLAG,ask,7013.0000,13,21,6,3,0.7000",
        "FINAL,ask,7013.0000,2,15,21,6,15,3,6.0000,held,0.7000",
        "FLAG,ask,7012.7500,22,24,8,2,0.5000",
        "FINAL,ask,7012.7500,15,23,24,8,16,2,8.0000,open,0.5000"]


@pytest.mark.slow
def test_cs_engine_matches_python_reference_differential(harness_exe):
    r = subprocess.run([sys.executable, "-I", str(ICE / "diff_engines.py"), "--exe", str(harness_exe), "--fuzz", "60"],
                       cwd=REPO, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert '"mismatched_runs": 0' in r.stdout


@pytest.mark.slow
def test_falsifier_differential_sees_a_shifted_hidden_ratio(harness_exe):
    r = subprocess.run([sys.executable, "-I", str(ICE / "diff_engines.py"), "--exe", str(harness_exe), "--fuzz", "20",
                        "--falsify"], cwd=REPO, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, "the differential failed to see HiddenRatio 1.9 vs 2.0:\n" + r.stdout[-2000:]


@pytest.mark.slow
def test_cs_engine_no_look_ahead_on_prefixes(harness_exe, tmp_path):
    sys.path.insert(0, str(REPO / "backtest"))
    from qibt import booksim, iceberg
    import random
    rng = random.Random(11)
    for i, (rows, _t) in enumerate(booksim.simulate(6, 20261028)):
        full = tmp_path / f"full_{i}.csv"
        iceberg.write_stream_csv(full, rows)
        all_recs = _run(harness_exe, full)
        for k in sorted(rng.sample(range(1, len(rows)), 3)):
            pre = tmp_path / f"pre_{i}_{k}.csv"
            iceberg.write_stream_csv(pre, rows[:k])
            got = _run(harness_exe, pre)
            assert got == all_recs[:len(got)], (i, k)
            # nothing the full run emitted for the first k events may be missing from the prefix run
            assert len(got) == len(iceberg.run_stream(rows[:k])), (i, k)


# ---- 2b. table model and placement tests in C# (P1, P2) -----------------------------------
def _build_table_tests(out: Path, ind: Path | None = None):
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    env = {**__import__("os").environ, "OUT": str(out)}
    if ind is not None:
        env["IND"] = str(ind)
    r = subprocess.run([bash, str(ICE / "harness" / "build_tests.sh")], cwd=REPO, capture_output=True, text=True,
                       timeout=600, env=env)
    if r.returncode != 0:
        pytest.skip("TableTests build failed (NinjaTrader / .NET SDK not installed?):\n" + r.stdout[-1500:])


@pytest.mark.slow
def test_cs_table_and_layout_tests_pass(tmp_path):
    exe = tmp_path / "TableTests.exe"
    _build_table_tests(exe)
    r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-3000:]
    assert re.search(r"passed=\d{5,} failed=0", r.stdout), r.stdout[-500:]


@pytest.mark.slow
def test_falsifier_cs_table_tests_catch_ascending_sort(tmp_path):
    src = indicator_file(MODULE).read_text(encoding="utf-8")
    mutant = src.replace("int c = b.Detected.CompareTo(a.Detected);", "int c = a.Detected.CompareTo(b.Detected);")
    assert mutant != src
    ind = tmp_path / "QI_28_mutant.cs"
    ind.write_text(mutant, encoding="utf-8")
    exe = tmp_path / "TableTestsMutant.exe"
    _build_table_tests(exe, ind)
    r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=300)
    assert r.returncode != 0, "the table tests did not catch an ascending sort"


# ---- 3. compile (I1) ------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-3000:]


# ---- 4. NinjaTrader export: nothing on historical bars --------------------------------------
def test_export_has_no_historical_detections():
    df = harness_frame()
    cols = [c for c in df.columns if re.match(r"^QI_(?:\d\d_)?IcebergDetector\.", c)]
    if not cols:
        pytest.skip("export has no QI_28_IcebergDetector columns")
    # The indicator leaves its plots unset on historical bars. Depending on how NinjaTrader reads an unset plot the
    # export holds blank, 0 or the bar's input value (Close); a detection would be any other value.
    close = df["Close"] if "Close" in df.columns else None
    for c in cols:
        v = df[c]
        ok = v.isna() | (v == 0)
        if close is not None:
            ok |= (v - close).abs() < 1e-9
        assert ok.all(), f"{c}: {int((~ok).sum())} historical bars carry a value other than unset/0"
