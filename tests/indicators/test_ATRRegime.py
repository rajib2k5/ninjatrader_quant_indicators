"""Unit tests for QI_<NN>_ATRRegime - ATR(14) relative to its 50-bar simple average.

Spec (ledger M20 + B3/B4, ORIG IBSFade.cs 347, 409, 1416-1420):
  regime = ATR14[0] / SMA(ATR14, 50)[0]   when CurrentBar >= 50 and the SMA > 0, else 1.0
  ATR[t] = (min(t, 13) * ATR[t-1] + TR[t]) / min(t + 1, 14),  TR = max(H-L, |H-C[1]|, |L-C[1]|)
Reference line 1.5 (rules.yaml: long x < 1.5, short never).
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from conftest import (REPO, assert_close, assert_names, bars, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "ATRRegime"


def quiet_with_wide_bar(n, at):
    """n bars with H=12 L=10 C=11 (TR = 2) except bar `at`: H=18 L=10 C=11 (TR = max(8, 7, 1) = 8).
    at=None gives no wide bar at all."""
    high, low, close = np.full(n, 12.0), np.full(n, 10.0), np.full(n, 11.0)
    if at is not None:
        high[at] = 18.0
    return bars(close, high=high, low=low)


# ---- 1. formula --------------------------------------------------------------------------
def test_first_bars_after_the_gate_hand_values():
    # Wide bar at 49. ATR = 2 up to bar 48.
    #   ATR49 = (13*2 + 8)/14 = 17/7;   ATR50 = (13*(17/7) + 2)/14 = 235/98;   ATR51 = (13*(235/98) + 2)/14 = 3251/1372
    # bar 49 is inside the warm-up -> 1.0 (even though ATR49/SMA would not be 1)
    # bar 50: SMA50 = mean(ATR[1..50]) = (48*2 + 17/7 + 235/98)/50 = (9408/98 + 473/98)/50 = 9881/4900
    #         regime = (235/98)/(9881/4900) = 235*50/9881 = 11750/9881
    # bar 51: SMA50 = mean(ATR[2..51]) = (47*2 + 17/7 + 235/98 + 3251/1372)/50 = (138841/1372)/50 = 138841/68600
    #         regime = (3251/1372)/(138841/68600) = 3251*50/138841 = 162550/138841
    v = R.atr_regime(quiet_with_wide_bar(70, 49)).to_numpy()
    assert v[49] == 1.0
    assert v[50] == pytest.approx(11750 / 9881, abs=1e-12)       # 1.18915...
    assert v[51] == pytest.approx(162550 / 138841, abs=1e-12)    # 1.17077...


def test_value_is_one_for_every_bar_before_bar_50():
    # a wide bar at 30 and at 10: an unguarded ratio would not be 1 there
    v = R.atr_regime(quiet_with_wide_bar(70, 30)).to_numpy()
    assert (v[:50] == 1.0).all()
    # bar 30 is a wide bar: ATR30 = 17/7, SMA of the available bars would be (30*2 + 17/7)/31 != 17/7
    assert abs((17 / 7) / ((30 * 2 + 17 / 7) / 31) - 1.0) > 0.1
    v10 = R.atr_regime(quiet_with_wide_bar(60, 10)).to_numpy()
    assert (v10[:50] == 1.0).all()


def test_constant_ranges_give_exactly_one():
    # ATR = 2 on every bar, so SMA50(ATR) = 2 and the ratio is 2/2 = 1
    assert (R.atr_regime(quiet_with_wide_bar(120, None)).to_numpy()[60:] == pytest.approx(1.0))


def test_zero_sma_falls_back_to_one():
    flat = bars([10.0] * 80, high=[10.0] * 80, low=[10.0] * 80)       # ATR = 0, SMA = 0
    assert (R.atr_regime(flat).to_numpy() == 1.0).all()


def test_scale_and_shift_invariance():
    s = quiet_with_wide_bar(70, 49)
    base = R.atr_regime(s).to_numpy()
    scaled = bars(s["Close"] * 5.0, high=s["High"] * 5.0, low=s["Low"] * 5.0)
    shifted = bars(s["Close"] + 100.0, high=s["High"] + 100.0, low=s["Low"] + 100.0)
    np.testing.assert_allclose(R.atr_regime(scaled).to_numpy(), base, atol=1e-12)
    np.testing.assert_allclose(R.atr_regime(shifted).to_numpy(), base, atol=1e-12)


def test_ratio_is_non_negative_and_at_most_50():
    # SMA50 = (1/50) * sum of 50 non-negative ATRs >= ATR[t]/50  =>  0 <= ratio <= 50
    rs = np.random.RandomState(8)
    n = 500
    mid = 1000.0 + np.cumsum(rs.normal(0, 2, n))
    rng = rs.pareto(1.5, n) + 0.01
    high, low = mid + rng / 2, mid - rng / 2
    v = R.atr_regime(bars(low + rs.uniform(0, 1, n) * rng, high=high, low=low)).to_numpy()
    assert np.isfinite(v).all() and (v >= 0).all() and (v <= 50 + 1e-9).all()


def test_falsifier_sma20_denominator_is_rejected():
    """ATR14/SMA20(ATR14) is the plausible wrong window. At bar 50 of the hand case:
    SMA20 = mean(ATR[31..50]) = (18*2 + 17/7 + 235/98)/20 = 4001/1960, ratio = 235*20/4001 = 4700/4001 = 1.1747,
    which is not the 11750/9881 = 1.18915 the 50-bar window gives."""
    df = quiet_with_wide_bar(70, 49)
    a14 = R.atr(df, 14)
    wrong = (a14 / R.sma(a14, 20)).to_numpy()
    assert wrong[50] == pytest.approx(4700 / 4001, abs=1e-12)
    assert abs(wrong[50] - 11750 / 9881) > 1e-3
    assert abs(R.atr_regime(df).to_numpy()[50] - wrong[50]) > 1e-3


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["ATR14 / SMA50(ATR14)"]
    assert "ATRRegime" in c["series"]                 # read by QS_*_ATRRegime and the harness
    assert c["lines"] == {"Upper Threshold": 1.5}
    assert c["defaults"]["Threshold"] == "1.5"        # single threshold, no Lower/Upper pair
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


def test_csharp_guard_is_bar_50_and_positive_sma_with_fallback_one():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"CurrentBar\s*>=\s*50\s*&&\s*atrSma50\[0\]\s*>\s*0\s*\?\s*atr14\[0\]\s*/\s*atrSma50\[0\]\s*:\s*1\.0", text)
    assert re.search(r"atrSma50\s*=\s*SMA\(atr14,\s*50\)", text)          # SMA built on the ATR instance


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "ATRRegime")
    # From bar 50 the C# guard is open and NinjaTrader's SMA(ATR14, 50) is a true 50-bar mean.
    ref = R.atr_regime(df).to_numpy()
    assert_close(ref, got, start=50, tol=6e-5, label="ATRRegime")
