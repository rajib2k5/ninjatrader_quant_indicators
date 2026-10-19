"""Unit tests for QI_<NN>_CompositeVol - composite volatility score ("v5_zscore").

Spec (ledger M6 + M5/B4/B5, ORIG IBSFade.cs 347, 416-418, 1308-1330, 1573-1596):
  composite = 0.40 * z_RV + 0.35 * (-priceZ) + 0.25 * ((vov - 0.15) / 0.10)
  z_RV   = (ATR14 - mean_20(ATR14)) / popstd_20(ATR14)                     (0 until bar 25)
  priceZ = (Close - SMA20(Close)) / popstd_20(Close)
  vov    = popstd_10(dATR14) / ATR14,   dATR14[t] = ATR14[t] - ATR14[t-1]
  ATR[t] = (min(t, 13) * ATR[t-1] + TR[t]) / min(t + 1, 14),  TR = max(H-L, |H-C[1]|, |L-C[1]|)
Reference lines 1.5 / -1.5 (rules.yaml: long x > 1.5, short x < -1.5).

Hand fact used throughout: with a population std, one outlier in a window of n = 20 values has
z = sqrt(n - 1) = sqrt(19) = 4.3589 whatever its size, and its sign is the sign of the outlier.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (REPO, assert_close, assert_names, bars, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "CompositeVol"
SQRT19 = math.sqrt(19)        # 4.358898943540674


def spike_frame(n, up=True):
    """n - 1 quiet bars (H=12 L=10 C=11, TR = 2) then one spike bar.
    up:   H=14 L=10 C=13  -> TR = max(4, |14-11| = 3, |10-11| = 1) = 4, close 2 above the flat closes
    down: H=12 L=8  C=9   -> TR = max(4, |12-11| = 1, |8-11| = 3) = 4, close 2 below the flat closes"""
    high, low, close = np.full(n, 12.0), np.full(n, 10.0), np.full(n, 11.0)
    high[-1], low[-1], close[-1] = (14.0, 10.0, 13.0) if up else (12.0, 8.0, 9.0)
    return bars(close, high=high, low=low)


# ---- 1. formula --------------------------------------------------------------------------
def test_components_of_an_up_spike_hand_values():
    # n = 60. ATR = 2 on bars 0-58. Bar 59: TR = 4, ATR59 = (13*2 + 4)/14 = 15/7, dATR59 = 15/7 - 2 = 1/7.
    #  z_RV   : window ATR[40..59] = nineteen 2s and one 15/7           -> sqrt(19)
    #  priceZ : window Close[40..59] = nineteen 11s and one 13          -> sqrt(19)
    #  vov    : dATR[50..59] = nine 0s and one 1/7: mean 1/70, pop var = (1/10)(1/7)^2 - (1/70)^2 = 9/4900,
    #           pop std = 3/70, vov = (3/70)/(15/7) = 21/1050 = 0.02
    r = R.composite_vol(spike_frame(60, up=True))
    assert r["atr_change"].to_numpy()[59] == pytest.approx(1 / 7, abs=1e-12)
    assert r["z_rv"].to_numpy()[59] == pytest.approx(SQRT19, abs=1e-9)
    assert r["price_z"].to_numpy()[59] == pytest.approx(SQRT19, abs=1e-9)
    assert r["vov"].to_numpy()[59] == pytest.approx(0.02, abs=1e-12)


def test_composite_of_up_and_down_spikes_hand_values():
    # (vov - 0.15)/0.10 = (0.02 - 0.15)/0.10 = -1.3, so the vol-of-vol term is 0.25 * (-1.3) = -0.325.
    # up spike  : z_RV = +sqrt(19), priceZ = +sqrt(19): 0.40*sqrt(19) - 0.35*sqrt(19) - 0.325 = 0.05*sqrt(19) - 0.325 = -0.10706
    # down spike: z_RV = +sqrt(19), priceZ = -sqrt(19): 0.40*sqrt(19) + 0.35*sqrt(19) - 0.325 = 0.75*sqrt(19) - 0.325 =  2.94417
    up = R.composite_vol(spike_frame(60, up=True))["composite"].to_numpy()[59]
    down = R.composite_vol(spike_frame(60, up=False))["composite"].to_numpy()[59]
    assert up == pytest.approx(0.05 * SQRT19 - 0.325, abs=1e-9)
    assert down == pytest.approx(0.75 * SQRT19 - 0.325, abs=1e-9)
    # the price term is subtracted: a price spike DOWN raises the score by 2 * 0.35 * sqrt(19) = 3.0512
    assert down - up == pytest.approx(0.70 * SQRT19, abs=1e-9)


def test_weighting_arithmetic_hand_values():
    f = R.composite_vol_from_parts
    # (z_RV, priceZ, vov) -> 0.40*z + 0.35*(-pz) + 0.25*((vov - 0.15)/0.10)
    assert f(1.0, 0.0, 0.15) == pytest.approx(0.40, abs=1e-12)        # only z_RV
    assert f(0.0, 2.0, 0.15) == pytest.approx(-0.70, abs=1e-12)       # 0.35 * (-2)
    assert f(0.0, 0.0, 0.25) == pytest.approx(0.25, abs=1e-12)        # 0.25 * (0.10/0.10)
    assert f(2.0, -1.0, 0.05) == pytest.approx(0.90, abs=1e-12)       # 0.80 + 0.35 + 0.25*(-1)
    assert f(0.0, 0.0, 0.15) == pytest.approx(0.0, abs=1e-12)         # neutral inputs


def test_rv_zscore_component_is_zero_before_bar_25():
    # a spike at bar 24 has a full 20-bar window (raw z = sqrt(19)) but the component reads 0 until bar 25
    z24 = R.composite_vol(spike_frame(25))["z_rv"].to_numpy()
    assert (z24 == 0.0).all()
    z25 = R.composite_vol(spike_frame(26))["z_rv"].to_numpy()
    assert z25[25] == pytest.approx(SQRT19, abs=1e-9)


def test_scale_and_shift_invariance():
    up = spike_frame(60, up=True)
    base = R.composite_vol(up)["composite"].to_numpy()[59]
    scaled = bars(up["Close"] * 4.0, high=up["High"] * 4.0, low=up["Low"] * 4.0)         # z-scores and vov are ratios
    shifted = bars(up["Close"] + 500.0, high=up["High"] + 500.0, low=up["Low"] + 500.0)  # TR and deviations unchanged
    assert R.composite_vol(scaled)["composite"].to_numpy()[59] == pytest.approx(base, abs=1e-9)
    assert R.composite_vol(shifted)["composite"].to_numpy()[59] == pytest.approx(base, abs=1e-9)


def test_components_obey_their_bounds():
    # population z-score of a 20-value window is at most sqrt(19) in magnitude; a std ratio is non-negative
    rs = np.random.RandomState(12)
    n = 600
    mid = 1000.0 + np.cumsum(rs.normal(0, 3, n))
    rng = rs.pareto(1.3, n) + 0.01
    high, low = mid + rng / 2, mid - rng / 2
    r = R.composite_vol(bars(low + rs.uniform(0, 1, n) * rng, high=high, low=low))
    z, pz, vov = (r[k].to_numpy()[50:] for k in ("z_rv", "price_z", "vov"))
    assert np.isfinite(z).all() and np.isfinite(pz).all() and np.isfinite(vov).all()
    assert (np.abs(z) <= SQRT19 + 1e-9).all() and (np.abs(pz) <= SQRT19 + 1e-9).all() and (vov >= 0).all()
    assert np.isfinite(r["composite"].to_numpy()[50:]).all()


def test_falsifier_sample_std_and_unnegated_price_term_are_rejected():
    """Two plausible miscodings. (1) sample std (divide by 19) in priceZ: for the up-spike hand case
    z = 1.9/sqrt(0.2) = 4.2485 instead of sqrt(19) = 4.3589. (2) price term added instead of subtracted:
    0.75*sqrt(19) - 0.325 = 2.944 instead of the hand value 0.05*sqrt(19) - 0.325 = -0.107."""
    df = spike_frame(60, up=True)
    w = df["Close"].to_numpy()[-20:]
    sample_z = (w[-1] - w.mean()) / w.std(ddof=1)
    assert sample_z == pytest.approx(1.9 / math.sqrt(0.2), abs=1e-9)
    assert abs(sample_z - SQRT19) > 0.05
    r = R.composite_vol(df)
    z, pz, vov = (r[k].to_numpy()[59] for k in ("z_rv", "price_z", "vov"))
    unnegated = 0.40 * z + 0.35 * pz + 0.25 * ((vov - 0.15) / 0.10)
    assert abs(unnegated - (0.05 * SQRT19 - 0.325)) > 1.0
    assert abs(r["composite"].to_numpy()[59] - unnegated) > 1.0


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["CompositeVol"]
    # CompositeVol is the plot; RVZScore and AtrChange are the exposed intermediates the harness exports
    assert {"CompositeVol", "RVZScore", "AtrChange"} <= set(c["series"])
    assert c["lines"] == {"Lower Threshold": -1.5, "Upper Threshold": 1.5}
    assert c["defaults"]["LowerThreshold"] == "-1.5" and c["defaults"]["UpperThreshold"] == "1.5"
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


def test_csharp_weights_gates_and_windows():
    text = cs_contract(MODULE)["text"]
    assert "if (CurrentBar < 50)" in text                                    # ORIG module-wide gate (series stay 0 before it)
    assert re.search(r"CurrentBar\s*>=\s*30\s*&&\s*closeStdDev20\[0\]\s*>\s*0", text)
    assert re.search(r"0\.40\s*\*\s*cc1\s*\+\s*0\.35\s*\*\s*\(-cc2\)\s*\+\s*0\.25\s*\*\s*cc3z", text)
    assert re.search(r"cc3z\s*=\s*\(ccvov\s*-\s*0\.15\)\s*/\s*0\.10", text)
    assert "Math.Min(10, CurrentBar)" in text and "Math.Min(20, CurrentBar)" in text
    assert re.search(r"StdDev\(Close,\s*20\)", text) and re.search(r"SMA\(Close,\s*20\)", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "CompositeVol")
    # The C# returns before bar 50 and only then starts writing dATR14 (the vol-of-vol series stays 0
    # before bar 50), so its 10-bar dATR window holds those zeros until bar 50 + 9 = 59.
    # From bar 59 the reference (which has no such gate) and the C# use the same data.
    start = 59
    if len(df) <= start:
        pytest.skip(f"export has {len(df)} bars; CompositeVol is compared from bar {start}")
    ref = R.composite_vol(df)["composite"].to_numpy()
    assert_close(ref, got, start=start, tol=6e-5, label="CompositeVol.CompositeVol")


def test_components_match_ninjatrader_export():
    df = harness_frame()
    r = R.composite_vol(df)
    # RVZScore and AtrChange are written from bar 50 (after the module gate) and only their [0] values are used.
    assert_close(r["z_rv"].to_numpy(), harness_col(df, MODULE, "RVZScore"), start=50, tol=6e-5,
                 label="CompositeVol.RVZScore")
    assert_close(r["atr_change"].to_numpy(), harness_col(df, MODULE, "AtrChange"), start=50, tol=6e-5,
                 label="CompositeVol.AtrChange")
