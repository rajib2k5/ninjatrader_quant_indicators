"""Unit tests for QI_<NN>_VRPProxy - ATR(5) / ATR(14) volatility ratio.

Spec (ledger M13 + B4, ORIG IBSFade.cs 347, 414, 1373-1377):
  VRP = ATR5[0] / ATR14[0]   when CurrentBar >= 20 and ATR14 > 0, else 1.0
  ATR_n[t] = (min(t, n-1) * ATR_n[t-1] + TR[t]) / min(t + 1, n),  TR = max(H-L, |H-C[1]|, |L-C[1]|)
Reference lines 1.5 / 0.7 (rules.yaml: long x > 1.5, short x < 0.7).
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (REPO, assert_close, assert_names, bars, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "VRPProxy"


def quiet_with_wide_bar(n, at):
    """n bars with H=12 L=10 C=11 (TR = 2) except bar `at`: H=18 L=10 C=11 (TR = max(8, 7, 1) = 8).
    at=None gives no wide bar at all."""
    high, low, close = np.full(n, 12.0), np.full(n, 10.0), np.full(n, 11.0)
    if at is not None:
        high[at] = 18.0
    return bars(close, high=high, low=low)


# ---- 1. formula --------------------------------------------------------------------------
def test_wide_bar_then_quiet_bar_hand_values():
    # Wide bar at 25 (TR = 8), quiet bars before and after (TR = 2); ATR5 = ATR14 = 2 before it.
    # bar 25: ATR5  = (4*2 + 8)/5 = 16/5        ATR14 = (13*2 + 8)/14 = 17/7        VRP = (16/5)/(17/7) = 112/85
    # bar 26: ATR5  = (4*(16/5) + 2)/5 = 74/25  ATR14 = (13*(17/7) + 2)/14 = 235/98  VRP = (74/25)/(235/98) = 7252/5875
    v = R.vrp_proxy(quiet_with_wide_bar(40, 25)).to_numpy()
    assert v[24] == pytest.approx(1.0, abs=1e-12)               # 2/2
    assert v[25] == pytest.approx(112 / 85, abs=1e-12)          # 1.31765
    assert v[26] == pytest.approx(7252 / 5875, abs=1e-12)       # 1.23438


def test_value_is_one_for_every_bar_before_bar_20():
    # Wide bar at 19: ATR5 = 16/5, ATR14 = 17/7, so the raw ratio 112/85 is not 1 - the guard hides it.
    # bar 20 (first bar after the guard): same arithmetic as bar 26 above -> 7252/5875.
    v = R.vrp_proxy(quiet_with_wide_bar(40, 19)).to_numpy()
    assert (v[:20] == 1.0).all()
    assert v[20] == pytest.approx(7252 / 5875, abs=1e-12)
    # a wide bar at 10: raw ATR5 = (4*2 + 8)/5 = 16/5, ATR14 = (10*2 + 8)/11 = 28/11, ratio 1.257 - still 1.0 at bar 10
    v10 = R.vrp_proxy(quiet_with_wide_bar(30, 10)).to_numpy()
    assert (v10[:20] == 1.0).all()
    assert (16 / 5) / (28 / 11) == pytest.approx(1.2571428571, abs=1e-9)    # what an unguarded module would show


def test_zero_atr14_falls_back_to_one():
    flat = bars([10.0] * 40, high=[10.0] * 40, low=[10.0] * 40)       # ATR5 = ATR14 = 0
    assert (R.vrp_proxy(flat).to_numpy() == 1.0).all()


def test_constant_ranges_give_exactly_one():
    # TR = 2 on every bar -> ATR5 = ATR14 = 2
    assert R.vrp_proxy(quiet_with_wide_bar(60, None)).to_numpy()[20:] == pytest.approx(1.0)


def test_scale_and_shift_invariance():
    s = quiet_with_wide_bar(40, 25)
    base = R.vrp_proxy(s).to_numpy()
    scaled = bars(s["Close"] * 3.0, high=s["High"] * 3.0, low=s["Low"] * 3.0)
    shifted = bars(s["Close"] + 500.0, high=s["High"] + 500.0, low=s["Low"] + 500.0)
    np.testing.assert_allclose(R.vrp_proxy(scaled).to_numpy(), base, atol=1e-12)
    np.testing.assert_allclose(R.vrp_proxy(shifted).to_numpy(), base, atol=1e-12)


def test_ratio_is_positive_and_at_most_fourteen_fifths():
    # Both ATRs are exponentially weighted averages of TR; the newest TR has weight 1/5 in ATR5 and
    # 1/14 in ATR14 and older weights shrink faster in ATR5, so ATR5/ATR14 <= (1/5)/(1/14) = 14/5.
    rs = np.random.RandomState(9)
    n = 500
    mid = 1000.0 + np.cumsum(rs.normal(0, 2, n))
    rng = rs.pareto(1.5, n) + 0.01
    high, low = mid + rng / 2, mid - rng / 2
    v = R.vrp_proxy(bars(low + rs.uniform(0, 1, n) * rng, high=high, low=low)).to_numpy()
    assert np.isfinite(v).all() and (v > 0).all() and (v <= 14 / 5 + 1e-9).all()


def test_falsifier_inverted_ratio_and_wrong_short_period_are_rejected():
    """ATR14/ATR5 (inverted, so '> 1.5' would mean calm) and ATR(7)/ATR(14) both miss the hand value 112/85
    at bar 25 of test 1: inverted = 85/112 = 0.759; ATR7 = (6*2 + 8)/7 = 20/7, ratio (20/7)/(17/7) = 20/17 = 1.176."""
    df = quiet_with_wide_bar(40, 25)
    inverted = (R.atr(df, 14) / R.atr(df, 5)).to_numpy()
    assert inverted[25] == pytest.approx(85 / 112, abs=1e-12)
    assert abs(inverted[25] - 112 / 85) > 0.1
    atr7 = (R.atr(df, 7) / R.atr(df, 14)).to_numpy()
    assert atr7[25] == pytest.approx(20 / 17, abs=1e-12)
    assert abs(atr7[25] - 112 / 85) > 0.1


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["ATR5/ATR14"]
    assert "VRPProxy" in c["series"]                  # read by QS_*_VRPProxy and the harness
    assert c["lines"] == {"Lower Threshold": 0.7, "Upper Threshold": 1.5}
    assert c["defaults"]["LowerThreshold"] == "0.7" and c["defaults"]["UpperThreshold"] == "1.5"
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


def test_csharp_guard_is_bar_20_and_positive_atr14_with_fallback_one():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"CurrentBar\s*>=\s*20\s*&&\s*atr14\[0\]\s*>\s*0\s*\?\s*atr5\[0\]\s*/\s*atr14\[0\]\s*:\s*1\.0", text)
    assert re.search(r"atr5\s*=\s*ATR\(5\)", text) and re.search(r"atr14\s*=\s*ATR\(14\)", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "VRPProxy")
    # The C# guard (CurrentBar >= 20) opens at bar 20; NinjaTrader's ATR warm-up is the ledger recursion.
    ref = R.vrp_proxy(df).to_numpy()
    assert_close(ref, got, start=20, tol=6e-5, label="VRPProxy")
