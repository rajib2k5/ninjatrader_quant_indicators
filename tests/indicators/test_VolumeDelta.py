"""Unit tests for QI_<NN>_VolumeDelta - close-direction volume delta, its 20-bar sum and its 10-bar SMA.

Spec (ledger M22; ORIG IBSFade.cs 357-360, 1428-1443, 1623-1634; README "Indicators"):
  delta[0] = +Volume if Close > Close[1], -Volume if Close < Close[1], 0 if unchanged; 0 on bar 0
  CumDelta20 = sum of delta[0..19]  only when CurrentBar > 20 (strict), else 0
  DeltaSMA10 = SMA(delta, 10)[0]    only when CurrentBar >= 10, else 0
  The C# writes nothing before bar 50 and its delta series stays 0 there, so the 20-bar sum is only exact from bar 70
  and the 10-bar SMA from bar 59 (docstring of the .cs). Reference line "Zero" at 0 (rules.yaml: long x > 0, short x < 0
  on CumDelta20).
Reference: qi_ref.volume_delta -> (delta, cum20, sma10).
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from conftest import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "VolumeDelta"


def _alternating(n=40):
    """close = 100, 101, 100, 101 ... and volume[t] = t, so delta[t] = +t on odd bars, -t on even bars (bar 0: 0)."""
    t = np.arange(n)
    return bars(100.0 + (t % 2), volume=t.astype(float))


def _rising(n=30):
    return bars(100.0 + np.arange(n), volume=np.full(n, 10.0))


# ---- 1. formula --------------------------------------------------------------------------
def test_delta_hand_values_up_down_and_unchanged():
    df = bars([100, 101, 99, 99, 102, 98], volume=[10, 20, 30, 40, 50, 60])
    # bar 0: no previous close -> 0 ; bar 1: 101 > 100 -> +20 ; bar 2: 99 < 101 -> -30 ;
    # bar 3: 99 == 99 -> 0 ; bar 4: 102 > 99 -> +50 ; bar 5: 98 < 102 -> -60
    delta, _, _ = R.volume_delta(df)
    assert delta.tolist() == [0, 20, -30, 0, 50, -60]


def test_cumulative_delta_is_zero_until_bar_21_then_the_20_bar_sum():
    # _alternating: delta[t] = (-1)^(t+1) * t, i.e. +1, -2, +3, -4, ...
    # bar 21: sum delta[2..21] = (-2+3) + (-4+5) + ... + (-20+21) = 10 pairs of +1 = +10
    # bar 22: sum delta[3..22] = (+3-4) + (+5-6) + ... + (+21-22) = 10 pairs of -1 = -10
    # bar 20: the window delta[1..20] sums to -10 but the guard is "CurrentBar > 20" (strict) -> 0
    _, cum, _ = R.volume_delta(_alternating())
    c = cum.to_numpy()
    assert (c[:21] == 0.0).all()
    assert c[21:].tolist() == [10.0 if t % 2 == 1 else -10.0 for t in range(21, 40)]


def test_delta_sma10_is_zero_until_bar_10_then_the_10_bar_mean():
    # bar 10: mean delta[1..10] = (1 + (-2+3) + (-4+5) + (-6+7) + (-8+9) - 10) / 10 = -5/10 = -0.5
    # bar 11: mean delta[2..11] = 5 pairs of +1 / 10 = +0.5 ; bar 12: delta[3..12] = 5 pairs of -1 / 10 = -0.5
    # bar 9: the window delta[0..9] would average +0.5, but the guard is "CurrentBar >= 10" -> 0
    _, _, s = R.volume_delta(_alternating())
    v = s.to_numpy()
    assert (v[:10] == 0.0).all()
    assert v[10:].tolist() == [-0.5 if t % 2 == 0 else 0.5 for t in range(10, 40)]


def test_monotone_rise_hand_values():
    # delta = [0, 10, 10, ...]; bar 20: guard -> 0 ; bar 21: delta[2..21] = 20 * 10 = 200 ; from bar 10 the SMA10 window
    # delta[t-9..t] holds ten 10s -> 10 ; bar 9: guard -> 0 although the window delta[0..9] would average 9
    delta, cum, s = R.volume_delta(_rising())
    assert delta.iloc[0] == 0.0 and (delta.iloc[1:] == 10.0).all()
    assert cum.iloc[20] == 0.0 and (cum.iloc[21:] == 200.0).all()
    assert s.iloc[9] == 0.0 and (s.iloc[10:] == 10.0).all()


def test_scaling_and_reflection_invariances_and_bounds():
    rng = np.random.default_rng(5)
    close = 4000 + np.cumsum(rng.choice([-1.0, -0.25, 0.0, 0.25, 1.0], 80))
    vol = rng.integers(1, 500, 80).astype(float)
    d0, c0, s0 = R.volume_delta(bars(close, volume=vol))
    d1, c1, s1 = R.volume_delta(bars(close * 3.0 + 1000.0, volume=vol))      # only the sign of the close change counts
    assert d1.tolist() == d0.tolist() and c1.tolist() == c0.tolist()
    d2, c2, s2 = R.volume_delta(bars(close, volume=vol * 4.0))               # linear in volume
    assert d2.to_numpy() == pytest.approx(4.0 * d0.to_numpy()) and c2.to_numpy() == pytest.approx(4.0 * c0.to_numpy())
    assert s2.to_numpy() == pytest.approx(4.0 * s0.to_numpy())
    d3, c3, s3 = R.volume_delta(bars(-close, volume=vol))                    # reflecting the prices flips every sign
    assert d3.to_numpy() == pytest.approx(-d0.to_numpy()) and c3.to_numpy() == pytest.approx(-c0.to_numpy())
    assert (np.abs(d0.to_numpy()) <= vol).all()                              # |delta| <= volume
    assert (np.abs(c0.to_numpy()) <= vol.cumsum()[-1]).all()


def test_falsifier_non_strict_cumulative_guard_is_detected():
    """CurrentBar >= 20 instead of > 20 would show the full 20-bar window at bar 20: for the alternating case that
    window delta[1..20] sums to -10, while the specified (strict) guard gives 0. The hand-value test pins bar 20 at 0."""
    unguarded_bar20 = -10.0
    _, cum, _ = R.volume_delta(_alternating())
    assert cum.iloc[20] != unguarded_bar20
    assert cum.iloc[20] == 0.0


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["Vol Delta", "CumDelta 20", "Delta SMA 10"]
    assert sorted(c["series"]) == ["CumDelta20", "DeltaSMA10", "VolDelta"]     # read by QS_*_VolumeDelta and the harness
    assert c["lines"] == {"Zero": 0.0}
    assert c["defaults"]["ShowDisclaimer"] == "false"


def test_csharp_keeps_the_original_guards():
    text = cs_contract(MODULE)["text"]
    assert "if (CurrentBar < 50)" in text                                       # module-wide gate
    assert re.search(r"if\s*\(CurrentBar\s*>\s*20\)", text)                     # strict cumulative guard
    assert re.search(r"for\s*\(int i = 0; i < 20; i\+\+\)", text)
    assert re.search(r"CurrentBar\s*>=\s*10\s*\?\s*volDeltaSma\[0\]\s*:\s*0", text)
    assert re.search(r"volDeltaSma\s*=\s*SMA\(volDelta,\s*10\)", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    delta, cum, sma10 = R.volume_delta(df)
    # C# gate: nothing before bar 50, and its delta series is 0 there, so the 20-bar sum is exact only once its window
    # lies inside bars >= 50 (bar 70, per the .cs header "bars 50-69") and the 10-bar SMA from bar 59.
    assert_close(delta, harness_col(df, MODULE, "VolDelta"), start=50, tol=6e-5, label="VolumeDelta.VolDelta")
    assert_close(cum, harness_col(df, MODULE, "CumDelta20"), start=70, tol=6e-5, label="VolumeDelta.CumDelta20")
    assert_close(sma10, harness_col(df, MODULE, "DeltaSMA10"), start=59, tol=6e-5, label="VolumeDelta.DeltaSMA10")
