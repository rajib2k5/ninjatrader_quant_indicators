"""Unit tests for QI_<NN>_StochFade - Fast Stochastic %K / %D.

Spec (ledger B8 / M4, ORIG IBSFade.cs 350, 1298-1301):
  NinjaTrader StochasticsFast(periodD = 3, periodK = 14):
    %K = 100 * (Close - LowestLow_14) / (HighestHigh_14 - LowestLow_14),   %D = SMA_3(%K)
  The C# writes %K and %D from bar 50 (ORIG's module-wide gate).
Reference lines 30 / 70 (rules.yaml: long %K < 30, short %K > 70).
The ledger does not state %K when the 14-bar range is zero, so only "finite and inside 0..100" is
asserted for that case.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from conftest import (REPO, assert_close, assert_names, bars, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "StochFade"


def hand_frame():
    """High 20 / Low 10 on all 17 bars; closes: 14 bars at 15 (positions 0-13), then 17.5, 12, 20."""
    return bars([15.0] * 14 + [17.5, 12.0, 20.0], high=[20.0] * 17, low=[10.0] * 17)


# ---- 1. formula --------------------------------------------------------------------------
def test_k_and_d_hand_values():
    # HH = 20 and LL = 10 in every 14-bar window, so %K = 100*(C - 10)/10 = 10*(C - 10):
    #   position 13: C=15   -> 50      position 14: C=17.5 -> 75
    #   position 15: C=12   -> 20      position 16: C=20   -> 100 (close at the highest high)
    # %K needs 14 bars (first value at position 13); %D = mean of three %K values (first at position 15):
    #   D15 = (50 + 75 + 20)/3 = 145/3 = 48.333      D16 = (75 + 20 + 100)/3 = 195/3 = 65
    k, d = R.stoch_fast(hand_frame())
    kv, dv = k.to_numpy(), d.to_numpy()
    assert np.isnan(kv[:13]).all() and np.isnan(dv[:15]).all()
    np.testing.assert_allclose(kv[13:], [50.0, 75.0, 20.0, 100.0], atol=1e-9)
    np.testing.assert_allclose(dv[15:], [145 / 3, 65.0], atol=1e-9)


def test_old_extreme_leaves_the_14_bar_window_exactly_at_position_14():
    # Bar 0 has High 30, every other bar High 20, Low 10, Close 15.
    #   position 13: window = bars 0..13 contains the 30 -> %K = 100*(15 - 10)/(30 - 10) = 25
    #   position 14: window = bars 1..14                  -> %K = 100*(15 - 10)/(20 - 10) = 50
    hi = bars([15.0] * 16, high=[30.0] + [20.0] * 15, low=[10.0] * 16)
    k = R.stoch_fast(hi)[0].to_numpy()
    np.testing.assert_allclose(k[13:], [25.0, 50.0, 50.0], atol=1e-9)
    # the same for a low: bar 0 has Low 0 (others 10, High 20, Close 15)
    #   position 13: %K = 100*(15 - 0)/(20 - 0) = 75;  position 14: 100*(15 - 10)/(20 - 10) = 50
    lo = bars([15.0] * 16, high=[20.0] * 16, low=[0.0] + [10.0] * 15)
    np.testing.assert_allclose(R.stoch_fast(lo)[0].to_numpy()[13:], [75.0, 50.0, 50.0], atol=1e-9)


def test_close_at_the_extremes_gives_100_and_0():
    up = np.arange(100.0, 130.0)                         # every close is the highest high of its window
    k_up, d_up = R.stoch_fast(bars(up, high=up, low=up - 1))
    assert (k_up.to_numpy()[13:] == 100.0).all() and (d_up.to_numpy()[15:] == 100.0).all()
    down = np.arange(200.0, 170.0, -1.0)                 # every close is the lowest low of its window
    k_dn, d_dn = R.stoch_fast(bars(down, high=down + 1, low=down))
    assert (k_dn.to_numpy()[13:] == 0.0).all() and (d_dn.to_numpy()[15:] == 0.0).all()


def test_values_stay_inside_0_100_including_a_zero_range_window():
    rs = np.random.RandomState(14)
    n = 500
    mid = 1000.0 + np.cumsum(rs.normal(0, 3, n))
    rng = rs.pareto(1.5, n) + 0.01
    high, low = mid + rng / 2, mid - rng / 2
    close = low + rs.uniform(0, 1, n) * rng
    # a stretch of 20 identical bars: HH = LL, the %K ratio is 0/0 (spec silent) and must still be a number in range
    high[300:320], low[300:320], close[300:320] = 1000.0, 1000.0, 1000.0
    k, d = R.stoch_fast(bars(close, high=high, low=low))
    for v in (k.to_numpy()[13:], d.to_numpy()[15:]):
        assert np.isfinite(v).all() and (v >= -1e-9).all() and (v <= 100 + 1e-9).all()   # 100*x/x can land 1 ulp above 100


def test_scale_shift_and_mirror_symmetry():
    base_k, base_d = R.stoch_fast(hand_frame())
    s = hand_frame()
    scaled = bars(s["Close"] * 3.0, high=s["High"] * 3.0, low=s["Low"] * 3.0)
    shifted = bars(s["Close"] + 1000.0, high=s["High"] + 1000.0, low=s["Low"] + 1000.0)
    for frame in (scaled, shifted):
        k, d = R.stoch_fast(frame)
        np.testing.assert_allclose(k.to_numpy()[13:], base_k.to_numpy()[13:], atol=1e-9)
        np.testing.assert_allclose(d.to_numpy()[15:], base_d.to_numpy()[15:], atol=1e-9)
    # reflecting the price axis about 15 (C' = 30 - C, H' = 30 - L = 20, L' = 30 - H = 10) turns %K into 100 - %K:
    # 100 - [50, 75, 20, 100] = [50, 25, 80, 0];  %D: 100 - 145/3 = 155/3, 100 - 65 = 35
    mirrored = bars(30.0 - s["Close"], high=30.0 - s["Low"], low=30.0 - s["High"])
    k, d = R.stoch_fast(mirrored)
    np.testing.assert_allclose(k.to_numpy()[13:], [50.0, 25.0, 80.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(d.to_numpy()[15:], [155 / 3, 35.0], atol=1e-9)


def test_falsifier_window_13_swapped_arguments_and_d_for_k_are_rejected():
    """Plausible slips: a 13-bar window, StochasticsFast(14, 3) (periodD and periodK swapped), and plotting %D where
    %K is meant. At position 13 of the window test the right %K is 25; a 13-bar window or a 3-bar window has
    already dropped the 30 and gives 50. In the hand frame %D15 = 48.33 where %K15 = 20."""
    hi = bars([15.0] * 16, high=[30.0] + [20.0] * 15, low=[10.0] * 16)
    k13 = R.stoch_fast(hi, 3, 13)[0].to_numpy()
    assert k13[13] == pytest.approx(50.0, abs=1e-9) and abs(k13[13] - 25.0) > 10
    swapped = R.stoch_fast(hi, 14, 3)[0].to_numpy()
    assert swapped[13] == pytest.approx(50.0, abs=1e-9) and abs(swapped[13] - 25.0) > 10
    k, d = R.stoch_fast(hand_frame())
    assert abs(d.to_numpy()[15] - 20.0) > 10 and abs(k.to_numpy()[15] - 145 / 3) > 10


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["%K", "%D"]                 # Values[0] = %K, Values[1] = %D
    assert {"K", "D"} <= set(c["series"])             # read by QS_*_StochFade and the harness
    assert c["lines"] == {"Lower Threshold": 30.0, "Upper Threshold": 70.0}
    assert c["defaults"]["LowerThreshold"] == "30" and c["defaults"]["UpperThreshold"] == "70"
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


def test_csharp_uses_stochastics_fast_3_14_and_the_bar_50_gate():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"stoch\s*=\s*StochasticsFast\(3,\s*14\)", text)         # periodD = 3, periodK = 14
    assert "if (CurrentBar < 50)" in text
    assert re.search(r"Values\[0\]\[0\]\s*=\s*stoch\.K\[0\]", text) and re.search(r"Values\[1\]\[0\]\s*=\s*stoch\.D\[0\]", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_k_matches_ninjatrader_export():
    df = harness_frame()
    k, _ = R.stoch_fast(df)
    # The C# gate is CurrentBar >= 50; both windows (14 bars for %K, 3 for %D) are full by then.
    assert_close(k.to_numpy(), harness_col(df, MODULE, "K"), start=50, tol=6e-5, label="StochFade.K")


def test_d_matches_ninjatrader_export():
    df = harness_frame()
    _, d = R.stoch_fast(df)
    assert_close(d.to_numpy(), harness_col(df, MODULE, "D"), start=50, tol=6e-5, label="StochFade.D")
