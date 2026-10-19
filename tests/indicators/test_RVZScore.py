"""Unit tests for QI_<NN>_RVZScore - z-score of ATR(14) against its trailing 20-bar mean / population std.

Spec (ledger M5 + B4/B5, ORIG IBSFade.cs 347, 1304-1306, 1573-1593):
  z = (ATR14[0] - mean_20(ATR14)) / popstd_20(ATR14),  window = ATR14[0..19]
  z = 0 until bar 25 (CurrentBar < 25) and z = 0 when the std is 0
  ATR[t] = (min(t, 13) * ATR[t-1] + TR[t]) / min(t + 1, 14),  TR = max(H-L, |H-C[1]|, |L-C[1]|)
Reference lines 2.0 / -1.5 (rules.yaml: long x > 2.0, short x < -1.5).

A key hand fact: with a population std, one outlier in a window of n = 20 values has z = sqrt(n - 1) =
sqrt(19) whatever its size (mean = a + d/20, deviations -d/20 (x19) and 19d/20: var = 19d^2/400,
z = (19d/20)/(d*sqrt(19)/20) = sqrt(19)).
"""
from __future__ import annotations

import math
import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (REPO, assert_close, assert_names, bars, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "RVZScore"
SQRT19 = math.sqrt(19)        # 4.358898943540674


def quiet_bars(n, last=None):
    """n bars with H=12 L=10 C=11 (TR = 2, ATR = 2). `last` replaces the final bar with (H, L, C)."""
    high, low, close = np.full(n, 12.0), np.full(n, 10.0), np.full(n, 11.0)
    if last is not None:
        high[-1], low[-1], close[-1] = last
    return bars(close, high=high, low=low)


# ---- 1. formula --------------------------------------------------------------------------
def test_single_atr_spike_has_z_of_sqrt_19():
    # 59 quiet bars (ATR = 2) then a wide bar H=18 L=10 C=11: TR = max(8, 7, 1) = 8, ATR59 = (13*2 + 8)/14 = 17/7.
    # Window ATR[40..59] = nineteen 2s and one 17/7: z = sqrt(19) (see module docstring).
    z = R.rv_zscore(quiet_bars(60, last=(18.0, 10.0, 11.0))).to_numpy()
    assert z[59] == pytest.approx(SQRT19, abs=1e-9)             # 4.3589
    assert (z[:59] == 0.0).all()                                # flat ATR -> std 0 -> 0


def test_single_atr_drop_has_z_of_minus_sqrt_19():
    # last bar H=L=C=11: TR = 0, ATR59 = (13*2 + 0)/14 = 13/7 < 2 -> one low outlier in the window -> z = -sqrt(19)
    z = R.rv_zscore(quiet_bars(60, last=(11.0, 11.0, 11.0))).to_numpy()
    assert z[59] == pytest.approx(-SQRT19, abs=1e-9)


def test_spike_one_bar_ago_hand_value():
    # Wide bar (TR = 8) at bar 58, quiet bar 59 (TR = 2):
    #   ATR58 = (13*2 + 8)/14 = 17/7 = 4760/1960,  ATR59 = (13*(17/7) + 2)/14 = 235/98 = 4700/1960,  quiet ATR = 2 = 3920/1960
    # window ATR[40..59] = eighteen 2s, ATR58, ATR59 (units of 1/1960):
    #   mean      = (18*3920 + 4760 + 4700)/20 = 80020/20 = 4001
    #   deviations: -81 (x18), +759, +699
    #   sum sq    = 18*81^2 + 759^2 + 699^2 = 118098 + 576081 + 488601 = 1182780
    #   pop var   = 1182780/20 = 59139,   z = 699/sqrt(59139) = 2.8744
    df = quiet_bars(60)
    high, low = df["High"].to_numpy().copy(), df["Low"].to_numpy().copy()
    high[58] = 18.0
    z = R.rv_zscore(bars(df["Close"], high=high, low=low)).to_numpy()
    assert z[59] == pytest.approx(699 / math.sqrt(59139), abs=1e-9)


def test_constant_atr_gives_zero_not_a_division_error():
    assert (R.rv_zscore(quiet_bars(80)).to_numpy() == 0.0).all()                       # ATR = 2, std = 0
    flat = bars([10.0] * 80, high=[10.0] * 80, low=[10.0] * 80)                        # ATR = 0, std = 0
    assert (R.rv_zscore(flat).to_numpy() == 0.0).all()


def test_value_is_zero_before_bar_25():
    # a spike at bar 24 has raw z = sqrt(19) (its 20-bar window is full) but the module reads 0 until bar 25
    z24 = R.rv_zscore(quiet_bars(25, last=(18.0, 10.0, 11.0))).to_numpy()
    assert (z24 == 0.0).all()
    z25 = R.rv_zscore(quiet_bars(26, last=(18.0, 10.0, 11.0))).to_numpy()
    assert (z25[:25] == 0.0).all()
    assert z25[25] == pytest.approx(SQRT19, abs=1e-9)           # first bar after the gate


def test_scale_and_shift_invariance():
    s = quiet_bars(60, last=(18.0, 10.0, 11.0))
    base = R.rv_zscore(s).to_numpy()
    scaled = bars(s["Close"] * 5.0, high=s["High"] * 5.0, low=s["Low"] * 5.0)
    shifted = bars(s["Close"] + 300.0, high=s["High"] + 300.0, low=s["Low"] + 300.0)
    np.testing.assert_allclose(R.rv_zscore(scaled).to_numpy(), base, atol=1e-9)
    np.testing.assert_allclose(R.rv_zscore(shifted).to_numpy(), base, atol=1e-9)


def test_z_is_bounded_by_sqrt_19():
    # for a population std the largest possible |z| in a window of 20 values is sqrt(19)
    rs = np.random.RandomState(6)
    n = 600
    mid = 1000.0 + np.cumsum(rs.normal(0, 2, n))
    rng = rs.pareto(1.2, n) + 0.01                      # very heavy tails -> big ATR outliers
    high, low = mid + rng / 2, mid - rng / 2
    z = R.rv_zscore(bars(low + rs.uniform(0, 1, n) * rng, high=high, low=low)).to_numpy()
    assert np.isfinite(z).all() and (np.abs(z) <= SQRT19 + 1e-9).all()
    assert np.abs(z).max() > 1.0                         # the data really exercises the statistic


def test_falsifier_sample_std_and_window_14_are_rejected():
    """Sample std (divide by 19) and a 14-bar window are the plausible miscodings. For the single-spike hand case:
    sample std makes z = sqrt(19)*sqrt(19/20) = 19/sqrt(20) = 4.2485; a 14-bar window makes z = sqrt(13) = 3.6056;
    neither is the sqrt(19) = 4.3589 of test 1."""
    df = quiet_bars(60, last=(18.0, 10.0, 11.0))
    a = R.atr(df, 14).to_numpy()
    w20 = a[-20:]
    sample = (a[-1] - w20.mean()) / w20.std(ddof=1)
    assert sample == pytest.approx(19 / math.sqrt(20), abs=1e-9)
    assert abs(sample - SQRT19) > 0.05
    w14 = a[-14:]
    short = (a[-1] - w14.mean()) / w14.std(ddof=0)
    assert short == pytest.approx(math.sqrt(13), abs=1e-9)
    assert abs(short - SQRT19) > 0.5
    assert abs(R.rv_zscore(df).to_numpy()[59] - sample) > 0.05


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["RV Z-Score"]
    assert "RVZScore" in c["series"]                  # read by QS_*_RVZScore and the harness
    assert c["lines"] == {"Lower Threshold": -1.5, "Upper Threshold": 2.0}
    assert c["defaults"]["LowerThreshold"] == "-1.5" and c["defaults"]["UpperThreshold"] == "2.0"
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


def test_csharp_gate_window_and_population_std():
    text = cs_contract(MODULE)["text"]
    assert "if (CurrentBar >= 25)" in text
    assert "Math.Min(20, CurrentBar)" in text
    assert re.search(r"atrStd\s*=\s*Math\.Sqrt\(atrSumSq\s*/\s*lookback\)", text)      # divide by n: population
    assert re.search(r"atrStd\s*>\s*0\s*\?\s*\(atr14\[0\]\s*-\s*atrMean\)\s*/\s*atrStd\s*:\s*0", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "RVZScore")
    # The C# value is 0 before bar 25 (matching the reference) and a 20-bar statistic after it.
    ref = R.rv_zscore(df).to_numpy()
    assert_close(ref, got, start=25, tol=6e-5, label="RVZScore")
