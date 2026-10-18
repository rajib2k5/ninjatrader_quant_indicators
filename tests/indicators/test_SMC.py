"""Unit tests for QI_<NN>_SMC - Smart Money Concepts (ICT) patterns with Confidence, Structure and TrendDir.

Spec (ledger M26; header of the .cs; ORIG 2548-2739; README "Indicators"):
  swing points: High[lb] >= every High in the 2*lb+1 window (lb = SwingLookback = 20), confirmed lb bars late, updated only from
                CurrentBar >= lb*2+5; prevSwing* is the swing before lastSwing*.
  TrendDir: +1 when lastSwingHigh > prevSwingHigh AND lastSwingLow > prevSwingLow (HH+HL), -1 for LH+LL, else unchanged (0 at start).
  Patterns / confidence (a bar's Confidence is the BEST one that fired, direction is first-come):
    OB Retest 0.72, FVG 0.68, BOS 0.60 (Close beyond the PREVIOUS swing high / low, 5-bar cooldown), CHoCH 0.75 (Close beyond the LAST
    swing against the trend: trend +1 and Close < lastSwingLow -> -1; trend -1 and Close > lastSwingHigh -> +1), Displacement 0.58.
  Plots: Confidence in {0.58, 0.60, 0.68, 0.72, 0.75} or 0, Structure in {-1, 0, +1} with Confidence > 0 <=> Structure != 0.
  Nothing before bar 50 (NaN in the port). A signal in the same direction as the previous one within DuplicateBarWindow = 5 bars
  (barsSince < 5) is suppressed.
Pattern rules themselves are covered bar by bar in backtest/tests/test_patterns_unit.py (test_patterns_smc_*, bullish CHoCH
not among them); this file adds indicator-level checks (bullish CHoCH, BOS on the previous swing, strict boundaries, window, ranges,
TrendDir, defaults, C# contract).
Reference: qibt.patterns.smc / smc_events (a port, verified against the original on 2.1M bars).

Base frame `_tri(n)`: High falls 0.01 per bar, Low rises 0.01 per bar (no swing point, no gap, ranges ~17 so ATR14 ~17), Close alternates
100.5 / 99.5, Volume 1000; times on a Saturday.  `_downtrend_frame()` adds four spikes: swing low 87 (pivot bar 90), swing high 115
(pivot 100), lower low 85 (pivot 140), lower high 113 (pivot 150); they are confirmed at bars 110 / 120 / 160 / 170, so from bar 170
TrendDir = -1 (LH + LL), lastSwingHigh = 113, prevSwingHigh = 115, lastSwingLow = 85, prevSwingLow = 87.
"""
from __future__ import annotations

import inspect
import re

import numpy as np
import pytest

from qibt import patterns as P
from conftest import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "SMC"
CONFIDENCES = {0.58, 0.60, 0.68, 0.72, 0.75}


def _tri(n):
    t = np.arange(n)
    even = t % 2 == 0
    return bars(np.where(even, 100.5, 99.5), open_=np.where(even, 99.5, 100.5), high=110.0 - 0.01 * t,
                low=90.0 + 0.01 * t, volume=np.full(n, 1000.0), start="2024-01-06 00:00", freq="1min")


def _put(df, t, o, h, l, c, v=1000.0):
    for col, val in (("Open", o), ("High", h), ("Low", l), ("Close", c), ("Volume", v)):
        df.loc[t, col] = float(val)


def _downtrend_frame(n=260):
    df = _tri(n)
    df.loc[90, "Low"] = 87.0
    df.loc[100, "High"] = 115.0
    df.loc[140, "Low"] = 85.0
    df.loc[150, "High"] = 113.0
    return df


def _events_at(ev, bar):
    sel = ev[ev["bar"] == bar]
    return [(int(d), round(float(c), 10), [(n, round(float(x), 10)) for n, x in p])
            for d, c, p in zip(sel["direction"], sel["confidence"], sel["patterns"])]


def _random_bars(n=4000, seed=3):
    rng = np.random.default_rng(seed)
    c = 4000 + np.cumsum(rng.choice([-1.5, -0.5, -0.25, 0.0, 0.25, 0.5, 1.5], n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.choice([0.0, 0.25, 0.5, 1.5, 5.0], n)
    l = np.minimum(o, c) - rng.choice([0.0, 0.25, 0.5, 1.5, 5.0], n)
    v = rng.choice([50, 200, 800, 1500, 6000], n).astype(float)
    return bars(c, open_=o, high=h, low=l, volume=v, start="2024-01-02 07:00", freq="1min")


# ---- 1. formula --------------------------------------------------------------------------
def test_bullish_choch_fires_with_confidence_075_and_structure_plus_1():
    # From bar 170: trend -1, lastSwingHigh = 113.  Bar 200 closes at 114 > 113 (and < prevSwingHigh 115, so no BOS):
    # CHoCH 0.75, direction +1.  Its range 14.5 < 1.5 * ATR14 (~26), so no Displacement / Order Block, and its low 100 is not
    # above High[2] (~108): no FVG.
    df = _downtrend_frame()
    _put(df, 200, 100.5, 114.5, 100.0, 114.0)
    out = P.smc(df)
    assert (out["trend_dir"].iloc[50:170] == 0).all() and (out["trend_dir"].iloc[170:] == -1).all()
    assert (out["confidence"].iloc[200], out["structure"].iloc[200]) == (0.75, 1.0)
    assert _events_at(P.smc_events(df), 200) == [(1, 0.75, [("CHoCH", 0.75)])]
    others = out.drop(index=200).iloc[50:]
    assert (others[["confidence", "structure"]] == 0).all().all()


def test_bos_is_keyed_to_the_previous_swing_low_with_strict_boundaries():
    # prevSwingLow = 87, lastSwingLow = 85 (trend -1, so no bearish CHoCH is possible).  A bar closing BELOW 87 is a bearish BOS
    # (0.60, -1) even though it is above the last swing low 85; closing exactly ON 87 or above it is not (strict <).
    for close, expect in ((86.5, (0.60, -1.0)), (87.0, (0.0, 0.0)), (87.5, (0.0, 0.0))):
        df = _downtrend_frame()
        _put(df, 200, 99.0, 99.5, 86.0, close)           # range 13.5 < 1.5 * ATR14: no Displacement
        out = P.smc(df)
        assert (out["confidence"].iloc[200], out["structure"].iloc[200]) == expect, close
    df = _downtrend_frame()
    _put(df, 200, 99.0, 99.5, 86.0, 86.5)
    assert _events_at(P.smc_events(df), 200) == [(-1, 0.6, [("BOS", 0.6)])]


def test_same_direction_signal_inside_the_5_bar_window_is_suppressed():
    df = _downtrend_frame()
    for t in (200, 202, 205):
        _put(df, t, 100.5, 114.5, 100.0, 114.0)
    out = P.smc(df)
    # bar 200 fires (barsSince reset); bar 202 is 2 bars later and +1 again: 2 < 5 -> suppressed;
    # bar 205 is 5 bars after bar 200: barsSince = 5 is NOT < 5 -> fires
    assert (out["confidence"].iloc[200], out["structure"].iloc[200]) == (0.75, 1.0)
    assert (out["confidence"].iloc[202], out["structure"].iloc[202]) == (0.0, 0.0)
    assert (out["confidence"].iloc[205], out["structure"].iloc[205]) == (0.75, 1.0)


def test_warmup_is_nan_before_bar_50_and_quiet_bars_are_zero_after():
    out = P.smc(_tri(120))
    assert out.iloc[:50].isna().all().all()
    assert (out.iloc[50:] == 0.0).all().all()          # no swing, no zone, no break: nothing fires, TrendDir stays 0


def test_plot_values_stay_in_the_documented_sets():
    out = P.smc(_random_bars())
    conf, st = out["confidence"].to_numpy()[50:], out["structure"].to_numpy()[50:]
    assert (conf > 0).sum() > 20                                         # the check is not vacuous
    assert set(np.round(conf[conf > 0], 10)) <= CONFIDENCES
    assert set(st.tolist()) <= {-1.0, 0.0, 1.0}
    assert ((conf > 0) == (st != 0)).all()                               # Confidence > 0 <=> Structure != 0
    assert set(out["trend_dir"].to_numpy()[50:].tolist()) <= {-1.0, 0.0, 1.0}


def test_falsifier_duplicate_window_of_6_instead_of_5_is_detected():
    """With DuplicateBarWindow = 6 the signal 5 bars after the previous one (bar 205, barsSince = 5 < 6) would be suppressed.
    The window test above pins bar 205 as firing, so a port or a C# default of 6 is rejected."""
    df = _downtrend_frame()
    for t in (200, 205):
        _put(df, t, 100.5, 114.5, 100.0, 114.0)
    assert P.smc(df, duplicate_bar_window=6)["confidence"].iloc[205] == 0.0
    assert P.smc(df)["confidence"].iloc[205] == 0.75


def test_python_port_defaults_equal_the_csharp_defaults():
    d = cs_contract(MODULE)["defaults"]
    sig = inspect.signature(P._run_smc).parameters
    assert sig["swing_lookback"].default == int(d["SwingLookback"]) == 20
    assert sig["duplicate_bar_window"].default == int(d["DuplicateBarWindow"]) == 5


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # labels on the price chart, no sub-panel
    assert c["plots"] == ["Confidence", "Structure"]  # transparent, DataBox only
    assert sorted(c["series"]) == ["Confidence", "Structure", "TrendDir"]     # read by QS_*_SMC and the harness
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
    assert re.search(r"smcDir == lastSmcDir && barsSinceLastSmc < DuplicateBarWindow", text)
    assert re.search(r"Close\[0\] > prevSwingHigh && CurrentBar - lastBosBar > 5", text)
    assert re.search(r"smcTrendDir == -1 && lastSwingHigh > double\.MinValue && Close\[0\] > lastSwingHigh", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    ref = P.smc(df[["BarTime", "Open", "High", "Low", "Close", "Volume"]])
    conf, st = harness_col(df, MODULE, "Confidence"), harness_col(df, MODULE, "Structure")
    # C# gate: nothing before bar 50 (the port is NaN there too). Compare Confidence (4-decimal export), Structure and TrendDir
    # (integer flags) on every bar, then the bars that fire event for event.
    assert_close(ref["confidence"], conf, start=50, tol=6e-5, label="SMC.Confidence")
    assert_close(ref["structure"], st, start=50, tol=1e-9, label="SMC.Structure")
    assert_close(ref["trend_dir"], harness_col(df, MODULE, "TrendDir"), start=50, tol=1e-9, label="SMC.TrendDir")
    fired_ref = np.flatnonzero(ref["confidence"].to_numpy()[50:] > 0)
    fired_got = np.flatnonzero(np.nan_to_num(conf.to_numpy(float)[50:]) > 0)
    assert fired_ref.tolist() == fired_got.tolist()
