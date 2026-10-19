"""Unit tests for QI_<NN>_LiquiditySweep - liquidity-sweep / stop-hunt patterns with Confidence and Structure plots.

Spec (ledger M24; header of the .cs; ORIG 2340-2404; README "Indicators"):
  Seven checks per bar, in order: basic sweep (swing 0.70 "Liq Sweep"; key levels 0.85 "Sweep PDH/PDL/ORB-H/ORB-L/MoHigh/MoLow"),
  SFP 0.50 (2-bar 0.60), equal-level trap 0.60, consolidation trap 0.65, Wyckoff Spring / Upthrust 0.60 (0.75 inside a
  consolidation), Turtle Soup 0.55, volume-divergence 0.35 (a "Start" label that never writes the plots; its confirmation is an
  "End" 0.55). The bar's Confidence is min(sum of the patterns that fired, 1.0), so a single pattern keeps its own value and any
  two patterns give 1.0 (every pattern is >= 0.50).  Key-level sweep (0.85): the bar breaches the level, closes back on the
  other side, its wick is >= SweepWickMultiple (2.0) times its body and Volume > SweepVolMultiple (1.5) * SMA(Volume, 20).
  Previous-day levels = RTH (08:30-16:00 US Central) high / low of the previous weekday; ORB = 08:30-09:00.
  Plots: Confidence in {0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.85, 1.0} or 0, Structure in {-1, 0, +1} with Confidence > 0 <=>
  Structure != 0. Nothing before bar 50 (NaN in the port); detection from CurrentBar >= SwingLookback*2+5 (= 45, below the global
  gate); a sweep in the same direction as the previous one within DuplicateBarWindow = 5 bars (barsSince < 5) is suppressed.
Pattern rules themselves are covered bar by bar in backtest/tests/test_patterns_unit.py (test_patterns_sweep_*, bearish PDH
and ORB-H among them); this file adds indicator-level checks (bullish PDL sweep, wick / volume thresholds, window, switches,
ranges, defaults, C# contract).
Reference: qibt.patterns.liquidity_sweep / liquidity_sweep_events (a port, verified against the original on 2.1M bars).

Base frame `_tri(n)`: High falls 0.01 per bar, Low rises 0.01 per bar (no swing point, no gap, ATR14 ~17), Close alternates 100.5 / 99.5,
Volume 1000. `_session_frame()` puts bars 0-119 on Monday 2024-01-08 from 08:30 and bars 120-199 on Tuesday from 08:30 (one-minute
bars). Monday's RTH bars 50..119 (bars < 50 are never processed) give PDH = High[50] = 109.5 and PDL = Low[50] = 90.5; Tuesday's
opening range (bars 120..149) gives ORB-H = 108.8 and ORB-L = 91.2, complete from 09:00 (bar 150).
"""
from __future__ import annotations

import inspect
import re

import numpy as np
import pandas as pd
import pytest

from qibt import patterns as P
from qi_helpers import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "LiquiditySweep"
CONFIDENCES = {0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.85, 1.0}


def _tri(n):
    t = np.arange(n)
    even = t % 2 == 0
    return bars(np.where(even, 100.5, 99.5), open_=np.where(even, 99.5, 100.5), high=110.0 - 0.01 * t,
                low=90.0 + 0.01 * t, volume=np.full(n, 1000.0), start="2024-01-06 00:00", freq="1min")


def _put(df, t, o, h, l, c, v=1000.0):
    for col, val in (("Open", o), ("High", h), ("Low", l), ("Close", c), ("Volume", v)):
        df.loc[t, col] = float(val)


def _session_frame():
    df = _tri(200)
    mon = pd.date_range("2024-01-08 08:30:00", periods=120, freq="1min")
    tue = pd.date_range("2024-01-09 08:30:00", periods=80, freq="1min")
    df["BarTime"] = mon.append(tue)
    return df


def _pdl_sweep(df, t, o=90.9, l=84.0, c=91.0, v=3000.0):
    """A bar that dips below PDL = 90.5 and closes back above it: wick (o - l) over body (c - o)."""
    _put(df, t, o, max(o, c), l, c, v)


def _events_at(ev, bar):
    sel = ev[ev["bar"] == bar]
    return [(int(d), round(float(c), 10), [(n, round(float(x), 10)) for n, x in p])
            for d, c, p in zip(sel["direction"], sel["confidence"], sel["patterns"])]


def _random_session_bars(n=6000, seed=17):
    rng = np.random.default_rng(seed)
    c = 4000 + np.cumsum(rng.choice([-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0], n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.choice([0.0, 0.25, 0.5, 1.5, 4.0], n)
    l = np.minimum(o, c) - rng.choice([0.0, 0.25, 0.5, 1.5, 4.0], n)
    v = rng.choice([50, 200, 800, 1500, 6000], n).astype(float)
    return bars(c, open_=o, high=h, low=l, volume=v, start="2024-01-02 07:00", freq="1min")


# ---- 1. formula --------------------------------------------------------------------------
def test_previous_day_low_sweep_fires_085_bullish():
    # Bar 180 (Tuesday 09:30): Open 90.9, High 91.0, Low 84.0, Close 91.0, Volume 3000.
    #   PDL = 90.5: Low 84 < 90.5 and Close 91 > 90.5.  body = 0.1, lower wick = 90.9 - 84 = 6.9 -> ratio 69 >= 2.
    #   Volume 3000 > 1.5 * SMA20 = 1.5 * (19 * 1000 + 3000) / 20 = 1650.
    #   No swing points exist (no SFP / Liq Sweep); Close 91.0 is below the 40-bar low 91.4 and the 20-bar low 91.6 (no Spring /
    #   Turtle Soup); ORB-L = 91.2 > Close (no ORB sweep).  => the single pattern "Sweep PDL" 0.85, direction +1.
    df = _session_frame()
    _pdl_sweep(df, 180)
    out = P.liquidity_sweep(df)
    assert (out["confidence"].iloc[180], out["structure"].iloc[180]) == (0.85, 1.0)
    assert _events_at(P.liquidity_sweep_events(df), 180) == [(1, 0.85, [("Sweep PDL", 0.85)])]
    assert (out.drop(index=180).iloc[50:] == 0).all().all()          # the rest of the quiet frame stays at 0


@pytest.mark.parametrize("volume,fires", [(1500.0, False), (1600.0, True)])
def test_volume_spike_threshold_is_strict(volume, fires):
    # SMA20 = (19 * 1000 + V) / 20 : V = 1500 -> 1025, 1.5x = 1537.5 > 1500 (no spike); V = 1600 -> 1030, 1.5x = 1545 < 1600 (spike)
    df = _session_frame()
    _pdl_sweep(df, 180, v=volume)
    out = P.liquidity_sweep(df)
    assert (out["confidence"].iloc[180], out["structure"].iloc[180]) == ((0.85, 1.0) if fires else (0.0, 0.0))


@pytest.mark.parametrize("open_,fires", [(89.0, True), (88.9, False)])
def test_wick_to_body_threshold_is_inclusive(open_, fires):
    # Low 85, Close 91: Open 89 -> lower wick 89 - 85 = 4, body 91 - 89 = 2, ratio exactly 2.0 >= 2 (fires);
    # Open 88.9 -> 3.9 / 2.1 = 1.857 < 2 (no sweep)
    df = _session_frame()
    _pdl_sweep(df, 180, o=open_, l=85.0)
    out = P.liquidity_sweep(df)
    assert (out["confidence"].iloc[180], out["structure"].iloc[180]) == ((0.85, 1.0) if fires else (0.0, 0.0))


def test_same_direction_sweep_inside_the_5_bar_window_is_suppressed():
    df = _session_frame()
    for t in (180, 182, 185):
        _pdl_sweep(df, t)
    out = P.liquidity_sweep(df)
    # bar 180 fires (barsSince reset to 0); bar 182 is 2 bars later, same direction: 2 < 5 -> suppressed;
    # bar 185 is 5 bars later: barsSince = 5 is NOT < 5 -> fires
    assert (out["confidence"].iloc[180], out["structure"].iloc[180]) == (0.85, 1.0)
    assert (out["confidence"].iloc[182], out["structure"].iloc[182]) == (0.0, 0.0)
    assert (out["confidence"].iloc[185], out["structure"].iloc[185]) == (0.85, 1.0)


def test_previous_day_switch_removes_the_sweep():
    df = _session_frame()
    _pdl_sweep(df, 180)
    off = P.liquidity_sweep(df, use_prev_day_levels=False)
    assert (off["confidence"].iloc[180], off["structure"].iloc[180]) == (0.0, 0.0)      # no other level is breached by this bar
    assert P.liquidity_sweep(df)["confidence"].iloc[180] == 0.85


def test_warmup_is_nan_before_bar_50_and_quiet_bars_are_zero_after():
    out = P.liquidity_sweep(_tri(120))
    assert out.iloc[:50].isna().all().all()
    assert (out.iloc[50:] == 0.0).all().all()


def test_plot_values_stay_in_the_documented_sets():
    out = P.liquidity_sweep(_random_session_bars())
    conf, st = out["confidence"].to_numpy()[50:], out["structure"].to_numpy()[50:]
    assert (conf > 0).sum() > 20                                         # the check is not vacuous
    assert set(np.round(conf[conf > 0], 10)) <= CONFIDENCES              # one pattern keeps its value, two or more cap at 1.0
    assert set(st.tolist()) <= {-1.0, 0.0, 1.0}
    assert ((conf > 0) == (st != 0)).all()                               # Confidence > 0 <=> Structure != 0


def test_falsifier_duplicate_window_of_6_instead_of_5_is_detected():
    """With DuplicateBarWindow = 6 the sweep 5 bars after the previous one (bar 185, barsSince = 5 < 6) would be suppressed.
    The window test above pins bar 185 as firing, so a port or a C# default of 6 is rejected."""
    df = _session_frame()
    for t in (180, 185):
        _pdl_sweep(df, t)
    assert P.liquidity_sweep(df, duplicate_bar_window=6)["confidence"].iloc[185] == 0.0
    assert P.liquidity_sweep(df)["confidence"].iloc[185] == 0.85


def test_python_port_defaults_equal_the_csharp_defaults():
    d = cs_contract(MODULE)["defaults"]
    sig = inspect.signature(P._run_liquidity_sweep).parameters
    assert sig["swing_lookback"].default == int(d["SwingLookback"]) == 20
    assert sig["sweep_wick_multiple"].default == float(d["SweepWickMultiple"]) == 2.0
    assert sig["sweep_vol_multiple"].default == float(d["SweepVolMultiple"]) == 1.5
    assert sig["equal_level_tolerance"].default == float(d["EqualLevelTolerance"]) == 0.05
    assert sig["consolidation_atr_ratio"].default == float(d["ConsolidationAtrRatio"]) == 0.6
    assert sig["duplicate_bar_window"].default == int(d["DuplicateBarWindow"]) == 5
    for py, cs in (("use_prev_day_levels", "UsePrevDayLevels"), ("use_monthly_levels", "UseMonthlyLevels"),
                   ("use_orb_levels", "UseOrbLevels")):
        assert sig[py].default is True and d[cs] == "true"


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # labels on the price chart, no sub-panel
    assert c["plots"] == ["Confidence", "Structure"]  # transparent, DataBox only
    assert sorted(c["series"]) == ["Confidence", "Structure"]       # read by QS_*_LiquiditySweep and the harness
    assert c["lines"] == {}
    d = c["defaults"]
    assert (d["SwingLookback"], d["SweepWickMultiple"], d["SweepVolMultiple"]) == ("20", "2.0", "1.5")
    assert (d["EqualLevelTolerance"], d["ConsolidationAtrRatio"], d["DuplicateBarWindow"]) == ("0.05", "0.6", "5")
    assert (d["UsePrevDayLevels"], d["UseMonthlyLevels"], d["UseOrbLevels"]) == ("true", "true", "true")
    assert d["ShowDisclaimer"] == "false"
    assert d["ShowTransparentPlotsInDataBox"] == "true"


def test_csharp_confidences_gates_and_window():
    text = cs_contract(MODULE)["text"]
    found = {float(x) for x in re.findall(r"conf=([\d.]+);", text)}
    assert found == {0.50, 0.55, 0.60, 0.65, 0.70, 0.85}
    assert re.search(r"isInConsolidation \? 0\.75 : 0\.60", text)                   # Spring / Upthrust
    assert re.search(r"DrawSweepLabel\(pendingSweepDir, 0\.55,", text)              # confirmed volume-divergence "End"
    assert re.search(r"DrawSweepLabel\(-?1, 0\.35,", text)                          # "Start" label, never writes the plots
    assert "if (CurrentBar < 50)" in text and re.search(r"if \(CurrentBar < SwingLookback \* 2 \+ 5\) return;", text)
    assert re.search(r"sweepDir == lastSweepDir && barsSinceLastSweep < DuplicateBarWindow", text)
    assert re.search(r"Math\.Min\(totalConf, 1\.0\)", text)
    assert re.search(r"wr >= wickThresh", text) and re.search(r"Volume\[0\] > SweepVolMultiple \* volSma20\[0\]", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    ref = P.liquidity_sweep(df[["BarTime", "Open", "High", "Low", "Close", "Volume"]])
    conf, st = harness_col(df, MODULE, "Confidence"), harness_col(df, MODULE, "Structure")
    # C# gate: nothing before bar 50 (the port is NaN there too). Compare Confidence (4-decimal export) and Structure
    # (integer flag) on every bar, then the bars that fire event for event.
    assert_close(ref["confidence"], conf, start=50, tol=6e-5, label="LiquiditySweep.Confidence")
    assert_close(ref["structure"], st, start=50, tol=1e-9, label="LiquiditySweep.Structure")
    fired_ref = np.flatnonzero(ref["confidence"].to_numpy()[50:] > 0)
    fired_got = np.flatnonzero(np.nan_to_num(conf.to_numpy(float)[50:]) > 0)
    assert fired_ref.tolist() == fired_got.tolist()
