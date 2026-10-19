"""Unit tests for QI_<NN>_RSI2 - 2-period Relative Strength Index (Connors / Alvarez).

Spec (ledger B1 / M2, ORIG IBSFade.cs 342, 1272-1275):
  RS  = Wilder_2(up moves) / Wilder_2(down moves),  Wilder_2 = running average, weight 1/2 on the new value
  RSI = 100 - 100 / (1 + RS);  NinjaTrader RSI(Close, 2, 1) adds no extra smoothing.
  The C# writes nothing before bar 50 (ORIG's module-wide gate).
Reference lines 25 / 75 (rules.yaml: long x < 25, short x > 75).

The ledger does not say how the Wilder averages are seeded, so the hand values use the steady state
of an alternating +1/-1 series (the seed is forgotten like (1/2)^t) and single steps taken from it.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (REPO, assert_close, assert_names, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "RSI2"


def alternating(n_bars):
    """10, 11, 10, 11, ...: odd positions are +1 moves, even positions (> 0) are -1 moves."""
    return 10.0 + (np.arange(n_bars) % 2)


# ---- 1. formula --------------------------------------------------------------------------
def test_alternating_closes_settle_at_the_wilder_steady_state():
    # Weight 1/2. After an up bar the averages satisfy U_up = U_dn + (1 - U_dn)/2 and U_dn = U_up/2
    # -> U_up = 2/3, U_dn = 1/3; mirrored D_dn = 2/3, D_up = 1/3.
    # After an up bar:   RS = (2/3)/(1/3) = 2     RSI = 100 - 100/3     = 200/3
    # After a down bar:  RS = (1/3)/(2/3) = 1/2   RSI = 100 - 100/1.5   = 100/3
    rsi = R.rsi(alternating(101), 2).to_numpy()          # position 100 is a down bar, 99 an up bar
    assert rsi[99] == pytest.approx(200 / 3, abs=1e-9)    # 66.666...
    assert rsi[100] == pytest.approx(100 / 3, abs=1e-9)   # 33.333...


def test_consecutive_down_closes_halve_the_rsi_each_time():
    # From the steady state after a down bar: avgUp = 1/3, avgDn = 2/3.
    # 2nd down (-1): avgUp = 1/3 * 1/2 = 1/6;  avgDn = 2/3 + (1 - 2/3)/2 = 5/6    RSI = 100*(1/6)/(1/6 + 5/6)   = 100/6
    # 3rd down (-1): avgUp = 1/6 * 1/2 = 1/12; avgDn = 5/6 + (1 - 5/6)/2 = 11/12  RSI = 100*(1/12)/(1/12 + 11/12) = 100/12
    close = list(alternating(101)) + [9.0, 8.0]           # 10 -> 9 -> 8
    rsi = R.rsi(close, 2).to_numpy()
    assert rsi[101] == pytest.approx(100 / 6, abs=1e-9)   # 16.666...
    assert rsi[102] == pytest.approx(100 / 12, abs=1e-9)  # 8.333...


def test_two_consecutive_closes_cross_the_25_and_75_reference_lines():
    # After a down bar RSI is 100/3 (> 25: no long); the second down close gives 100/6 (< 25).
    # After an up bar RSI is 200/3 (< 75: no short); a second up close gives avgUp = 2/3 + (1 - 2/3)/2 = 5/6,
    # avgDn = 1/3 * 1/2 = 1/6, RSI = 100 * (5/6)/(5/6 + 1/6) = 500/6 = 83.33 (> 75).
    down = R.rsi(list(alternating(101)) + [9.0], 2).to_numpy()
    assert down[100] > 25.0 > down[101]
    up = R.rsi(list(alternating(100)) + [12.0], 2).to_numpy()   # ends ... 10, 11, 12
    assert up[99] < 75.0 < up[100]
    assert up[100] == pytest.approx(500 / 6, abs=1e-9)


def test_monotone_series_reach_the_bounds():
    assert (R.rsi(np.arange(1.0, 41.0), 2).to_numpy()[1:] == 100.0).all()     # only up moves
    assert (R.rsi(np.arange(40.0, 0.0, -1.0), 2).to_numpy()[1:] == 0.0).all()  # only down moves


def test_values_stay_inside_0_100():
    rs = np.random.RandomState(3)
    close = 1000.0 + np.cumsum(rs.normal(0, 5, 500))
    close[100] *= 2.0                      # an outlier jump
    close[250:260] = close[250]            # a flat stretch
    v = R.rsi(close, 2).to_numpy()[1:]
    assert np.isfinite(v).all() and (v >= 0).all() and (v <= 100).all()


def test_scale_and_shift_invariance():
    close = np.concatenate([alternating(40), [12.0, 13.0, 12.5, 12.0, 9.0]])
    base = R.rsi(close, 2).to_numpy()
    np.testing.assert_allclose(R.rsi(close * 5.0, 2).to_numpy(), base, atol=1e-9)
    np.testing.assert_allclose(R.rsi(close + 250.0, 2).to_numpy(), base, atol=1e-9)


def test_falsifier_published_rsi3_and_off_by_one_period_are_rejected():
    """Connors' own long-term RSI uses period 3 and an off-by-one slip gives 1 or 3; the steady-state
    hand values 200/3 and 100/3 of test 1 reject them (RSI(3): 100*3/5 = 60 up, 100*2/5 = 40 down)."""
    close = alternating(101)
    p3 = R.rsi(close, 3).to_numpy()
    assert abs(p3[99] - 200 / 3) > 1.0 and abs(p3[100] - 100 / 3) > 1.0
    p1 = R.rsi(close, 1).to_numpy()          # weight 1: the RSI only sees the last move (100 or 0)
    assert abs(p1[99] - 200 / 3) > 1.0 and abs(p1[100] - 100 / 3) > 1.0


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["RSI(2)"]
    assert "RSI2" in c["series"]                      # read by QS_*_RSI2 and the harness
    assert c["lines"] == {"Lower Threshold": 25.0, "Upper Threshold": 75.0}
    assert c["defaults"]["LowerThreshold"] == "25" and c["defaults"]["UpperThreshold"] == "75"
    assert c["defaults"]["ShowDisclaimer"] == "false"


def test_reference_lines_and_panel_match_rules_yaml_and_readme():
    c = cs_contract(MODULE)
    num = r"-?\d+(?:\.\d+)?"
    rule = next(l for l in (REPO / "backtest" / "rules.yaml").read_text(encoding="utf-8").splitlines()
                if f"module: {MODULE}," in l)
    from_rules = sorted(float(v) for s in re.findall(r'(?:long|short): "([^"]*)"', rule) for v in re.findall(num, s))
    row = next(l for l in (REPO / "README.md").read_text(encoding="utf-8").splitlines()
               if l.startswith(f"| `{c['class']}` |")).split("|")
    from_readme = sorted(float(v) for v in re.findall(num, row[3]))
    assert from_rules == from_readme == sorted(c["lines"].values())
    assert row[4].strip() == "Panel"


def test_csharp_keeps_the_original_bar_50_gate_and_period_2():
    text = cs_contract(MODULE)["text"]
    assert "if (CurrentBar < 50)" in text
    assert re.search(r"rsi2\s*=\s*RSI\(Close,\s*2,\s*1\)", text)         # period 2, no extra smoothing


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "RSI2")
    # The C# writes from bar 50. NinjaTrader's Wilder seed differs from the reference's first-move
    # seed, but with weight 1/2 the difference is below (1/2)^50 = 1e-15 by bar 50.
    ref = R.rsi(df["Close"].to_numpy(float), 2).to_numpy()
    assert_close(ref, got, start=50, tol=6e-5, label="RSI2")
