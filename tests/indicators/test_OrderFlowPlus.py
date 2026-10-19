"""Unit tests for QI_<NN>_OrderFlowPlus - volume-delta order-flow patterns with Confidence and Structure plots.

Spec (ledger M25; header of the .cs; ORIG 2420-2541; README "Indicators"):
  volDelta = +Volume on an up close, -Volume on a down close, 0 if unchanged (M22);  cumDelta10 = sum of the last 10.
  Patterns, confidence (a bar's Confidence is the BEST one that fired, direction is first-come):
    DeltaDiv 0.78  High > lastSwingHigh with cumDelta10 < the value snapshotted when that swing was confirmed (-1);
                   Low < lastSwingLow with cumDelta10 > its snapshot (+1)            (strict inequalities)
    Absorption 0.65, DeltaRev 0.70 (cannot fire as written), Exhaustion 0.60, StackedDelta 0.55
  Plots: Confidence in {0.55, 0.60, 0.65, 0.70, 0.78} or 0, Structure in {-1, 0, +1} with Confidence > 0 <=> Structure != 0.
  Nothing before bar 50 (NaN in the port); swing points update only from CurrentBar >= SwingLookback*2+5; a signal in the
  same direction as the previous one within DuplicateBarWindow = 5 bars (barsSince < 5) is suppressed.
Pattern rules themselves are covered bar by bar in backtest/tests/test_patterns_unit.py (test_patterns_ofp_*);
this file adds indicator-level checks (bullish divergence, strict boundary, window, ranges, defaults, C# contract).
Reference: qibt.patterns.order_flow_plus / order_flow_plus_events (a port, verified against the original on 2.1M bars).

Base frame `_tri(n)`: High falls 0.01 per bar, Low rises 0.01 per bar (no swing point, no gap), Close alternates 100.5 / 99.5
(Open = previous Close) so volDelta alternates +1000 / -1000 and cumDelta10 = 0; Volume 1000; times on a Saturday.
"""
from __future__ import annotations

import inspect
import re

import numpy as np
import pytest

from qibt import patterns as P
from qi_helpers import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "OrderFlowPlus"
CONFIDENCES = {0.55, 0.60, 0.65, 0.70, 0.78}


def _tri(n):
    t = np.arange(n)
    even = t % 2 == 0
    return bars(np.where(even, 100.5, 99.5), open_=np.where(even, 99.5, 100.5), high=110.0 - 0.01 * t,
                low=90.0 + 0.01 * t, volume=np.full(n, 1000.0), start="2024-01-06 00:00", freq="1min")


def _put(df, t, o, h, l, c, v=1000.0):
    for col, val in (("Open", o), ("High", h), ("Low", l), ("Close", c), ("Volume", v)):
        df.loc[t, col] = float(val)


def _bull_divergence_frame():
    """Swing low 85 at bar 100 (confirmed at bar 120, cumDelta10 snapshot 0). Bar 149 closes unchanged (volDelta 0), so
    bar 150's up close (+1000) gives cumDelta10 = +1000 > 0 while its low 84 breaks the swing low."""
    df = _tri(220)
    df.loc[100, "Low"] = 85.0
    _put(df, 149, 100.5, 108.51, 91.49, 100.5)
    _put(df, 150, 100.5, 101.5, 84.0, 101.0)
    return df


def _events_at(ev, bar):
    sel = ev[ev["bar"] == bar]
    return [(int(d), round(float(c), 10), [(n, round(float(x), 10)) for n, x in p])
            for d, c, p in zip(sel["direction"], sel["confidence"], sel["patterns"])]


def _random_bars(n=4000, seed=3):
    rng = np.random.default_rng(seed)
    c = 4000 + np.cumsum(rng.choice([-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0], n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.choice([0.0, 0.25, 0.5, 1.5, 4.0], n)
    l = np.minimum(o, c) - rng.choice([0.0, 0.25, 0.5, 1.5, 4.0], n)
    v = rng.choice([50, 200, 800, 1500, 6000], n).astype(float)
    return bars(c, open_=o, high=h, low=l, volume=v, start="2024-01-02 07:00", freq="1min")


# ---- 1. formula --------------------------------------------------------------------------
def test_bullish_delta_divergence_fires_with_confidence_078_and_structure_plus_1():
    # volDelta alternates -1000 (odd bars) / +1000 (even bars): the snapshot at bar 120 is the sum of bars 111..120 = 0.
    # Bar 149: close == previous close -> volDelta 0.  Bar 150: close 101 > 100.5 -> +1000.
    # cumDelta10(150) = (bars 141..148: -1000+1000-1000+1000-1000+1000-1000+1000 = 0) + 0 + 1000 = +1000 > snapshot 0
    # and Low 84 < lastSwingLow 85  =>  DeltaDiv 0.78, direction +1.  No other pattern: Volume 1000 is no spike
    # (no Absorption); |volDelta| 1000 is not < |volDelta[1]| = 0 (no Exhaustion); volDelta[1] = 0 (no StackedDelta).
    df = _bull_divergence_frame()
    out = P.order_flow_plus(df)
    assert (out["confidence"].iloc[150], out["structure"].iloc[150]) == (0.78, 1.0)
    assert _events_at(P.order_flow_plus_events(df), 150) == [(1, 0.78, [("DeltaDiv", 0.78)])]
    # nothing else fires on the surrounding bars of the quiet base
    others = out.drop(index=150).iloc[50:]
    assert (others == 0).all().all()


def test_divergence_needs_a_strictly_larger_cumulative_delta():
    # Same swing low, but bar 150 is the base's own up bar (+1000 after bar 149's -1000): cumDelta10 = 0 = the snapshot.
    # The test is "cumDelta10 > snapshot" (strict), so no DeltaDiv; Exhaustion needs |volDelta| shrinking (1000 vs 1000: no).
    df = _tri(220)
    df.loc[100, "Low"] = 85.0
    _put(df, 150, 99.5, 108.5, 84.0, 100.5)
    out = P.order_flow_plus(df)
    assert (out["confidence"].iloc[150], out["structure"].iloc[150]) == (0.0, 0.0)
    assert P.order_flow_plus_events(df).empty


def test_same_direction_signal_inside_the_5_bar_window_is_suppressed():
    df = _bull_divergence_frame()
    # Absorption (0.65, +1): Volume 3000 > 1.5 * SMA20 (1100), range 10 > 0.5 * ATR14 (~17), body 1 < 0.3 * range.
    for t in (152, 155):
        _put(df, t, 100.0, 105.0, 95.0, 101.0, 3000.0)
    out = P.order_flow_plus(df)
    # bar 150 fires (barsSince reset to 0); bar 152 is 2 bars later, same direction (+1): 2 < 5 -> suppressed;
    # bar 155 is 5 bars later: barsSince = 5 is NOT < 5 -> fires
    assert (out["confidence"].iloc[150], out["structure"].iloc[150]) == (0.78, 1.0)
    assert (out["confidence"].iloc[152], out["structure"].iloc[152]) == (0.0, 0.0)
    assert (out["confidence"].iloc[155], out["structure"].iloc[155]) == (0.65, 1.0)
    assert _events_at(P.order_flow_plus_events(df), 155) == [(1, 0.65, [("Absorption", 0.65)])]


def test_warmup_is_nan_before_bar_50_and_quiet_bars_are_zero_after():
    out = P.order_flow_plus(_tri(120))
    assert out.iloc[:50].isna().all().all()
    assert (out.iloc[50:] == 0.0).all().all()


def test_plot_values_stay_in_the_documented_sets():
    out = P.order_flow_plus(_random_bars())
    conf, st = out["confidence"].to_numpy()[50:], out["structure"].to_numpy()[50:]
    assert (conf > 0).sum() > 20                                       # the check is not vacuous
    assert set(np.round(conf[conf > 0], 10)) <= CONFIDENCES
    assert set(st.tolist()) <= {-1.0, 0.0, 1.0}
    assert ((conf > 0) == (st != 0)).all()                             # Confidence > 0 <=> Structure != 0


def test_falsifier_duplicate_window_of_6_instead_of_5_is_detected():
    """With DuplicateBarWindow = 6 the 5-bars-later signal at bar 155 (barsSince = 5 < 6) would be suppressed. The
    window test above pins bar 155 as firing, so a port or a C# default of 6 is rejected."""
    df = _bull_divergence_frame()
    for t in (152, 155):
        _put(df, t, 100.0, 105.0, 95.0, 101.0, 3000.0)
    six = P.order_flow_plus(df, duplicate_bar_window=6)
    assert six["confidence"].iloc[155] == 0.0
    assert P.order_flow_plus(df)["confidence"].iloc[155] == 0.65


def test_python_port_defaults_equal_the_csharp_defaults():
    d = cs_contract(MODULE)["defaults"]
    sig = inspect.signature(P._run_order_flow_plus).parameters
    assert sig["swing_lookback"].default == int(d["SwingLookback"]) == 20
    assert sig["duplicate_bar_window"].default == int(d["DuplicateBarWindow"]) == 5


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # labels on the price chart, no sub-panel
    assert c["plots"] == ["Confidence", "Structure"]  # transparent, DataBox only
    assert sorted(c["series"]) == ["Confidence", "Structure"]       # read by QS_*_OrderFlowPlus and the harness
    assert c["lines"] == {}
    d = c["defaults"]
    assert (d["SwingLookback"], d["DuplicateBarWindow"], d["TextOffsetTicks"], d["SignalFontSize"]) == ("20", "5", "15", "13")
    assert d["ShowDisclaimer"] == "false"
    assert d["ShowTransparentPlotsInDataBox"] == "true"


def test_csharp_confidences_gates_and_window():
    text = cs_contract(MODULE)["text"]
    found = {float(x) for x in re.findall(r"Math\.Max\(bestConf,\s*([\d.]+)\)", text)}
    assert found == CONFIDENCES
    assert "if (CurrentBar < 50)" in text and "if (CurrentBar < 20) return;" in text
    assert re.search(r"if \(CurrentBar >= SwingLookback \* 2 \+ 5\)", text)
    assert re.search(r"ofDir == lastOfDir && barsSinceLastOf < DuplicateBarWindow", text)
    assert re.search(r"cumD10 < cumDeltaAtLastSwingHigh", text) and re.search(r"cumD10 > cumDeltaAtLastSwingLow", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    ref = P.order_flow_plus(df[["BarTime", "Open", "High", "Low", "Close", "Volume"]])
    conf, st = harness_col(df, MODULE, "Confidence"), harness_col(df, MODULE, "Structure")
    # C# gate: nothing before bar 50 (the port is NaN there too). Compare Confidence (4-decimal export) and Structure
    # (integer flag) on every bar, then the bars that fire event for event.
    assert_close(ref["confidence"], conf, start=50, tol=6e-5, label="OrderFlowPlus.Confidence")
    assert_close(ref["structure"], st, start=50, tol=1e-9, label="OrderFlowPlus.Structure")
    fired_ref = np.flatnonzero(ref["confidence"].to_numpy()[50:] > 0)
    fired_got = np.flatnonzero(np.nan_to_num(conf.to_numpy(float)[50:]) > 0)
    assert fired_ref.tolist() == fired_got.tolist()
