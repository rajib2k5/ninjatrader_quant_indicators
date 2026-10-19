"""Unit tests for QI_<NN>_BollingerPctB - Bollinger(20, 2) bands on price plus %B scaled to -100..+100.

Spec (ledger M10 + built-in B7; ORIG IBSFade.cs 349, 1353-1360; README "Deliberate changes"):
  middle = SMA20(Close), upper / lower = middle +/- 2 * StdDev20(Close)     (StdDev = POPULATION, divide by n)
  %B_here = (Close - middle) / (half bandwidth) * 100, half bandwidth = (upper - lower) / 2 = 2 * StdDev ;
            0 when the bandwidth is 0.       => +100 at the upper band, -100 at the lower band, 0 at the middle.
  Deliberate change: the original read the UPPER band as "mid" (value = ours - 100: 0 at the upper band, -200 at the
  lower); this module uses the MIDDLE band. The C# writes nothing before bar 50; the bands need 20 bars.
  Because StdDev is the population one, |%B| <= 100 * sqrt(n - 1) / 2 = 217.94 for n = 20 (a lone outlier).
Reference: qi_ref.bollinger -> (upper, middle, lower) and qi_ref.pct_b.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (assert_close, assert_names, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "BollingerPctB"


# ---- 1. formula --------------------------------------------------------------------------
def test_half_and_half_window_hand_values():
    close = [99.0] * 10 + [101.0] * 10
    # bar 19: mean = (10 * 99 + 10 * 101) / 20 = 100 ; variance = (10 * 1 + 10 * 1) / 20 = 1 -> sd 1
    # upper = 100 + 2 = 102 ; lower = 100 - 2 = 98 ; %B = (101 - 100) / (2 * 1) * 100 = +50
    up, mid, lo = R.bollinger(close)
    pb = R.pct_b(close).to_numpy()
    assert (up.iloc[19], mid.iloc[19], lo.iloc[19]) == pytest.approx((102.0, 100.0, 98.0), abs=1e-12)
    assert pb[19] == pytest.approx(50.0, abs=1e-12)
    assert np.isnan(pb[:19]).all()                   # the bands need 20 bars


def test_close_on_the_upper_band_is_plus_100_and_on_the_lower_band_minus_100():
    hi = [100.0] * 16 + [110.0] * 4
    # mean = (16 * 100 + 4 * 110) / 20 = 102 ; variance = (16 * 2^2 + 4 * 8^2) / 20 = 320 / 20 = 16 -> sd 4
    # upper = 102 + 8 = 110 = the close  =>  %B = (110 - 102) / 8 * 100 = +100
    up, mid, lo = R.bollinger(hi)
    assert (up.iloc[19], mid.iloc[19], lo.iloc[19]) == pytest.approx((110.0, 102.0, 94.0), abs=1e-12)
    assert R.pct_b(hi).to_numpy()[19] == pytest.approx(100.0, abs=1e-12)
    lo_case = [110.0] * 16 + [100.0] * 4
    # mean = (16 * 110 + 4 * 100) / 20 = 108 ; variance = 16 -> sd 4 ; lower = 108 - 8 = 100 = the close => -100
    assert R.pct_b(lo_case).to_numpy()[19] == pytest.approx(-100.0, abs=1e-12)


def test_next_window_hand_value():
    close = [99.0] * 10 + [101.0] * 11
    # bar 20 window = bars 1..20 = nine 99s and eleven 101s: mean = (891 + 1111) / 20 = 100.1
    # variance = (9 * 1.1^2 + 11 * 0.9^2) / 20 = (10.89 + 8.91) / 20 = 0.99 ; sd = 0.99498743710662
    # %B = (101 - 100.1) / (2 * 0.99498743710662) * 100 = 45 / sqrt(0.99) = 45.22670168666454
    assert R.pct_b(close).to_numpy()[20] == pytest.approx(45.22670168666454, abs=1e-9)


def test_zero_bandwidth_fallback_and_the_extreme_outlier_bound():
    assert (R.pct_b([100.0] * 25).to_numpy()[19:] == 0.0).all()               # bands collapse -> %B = 0, not a division
    # nineteen 100s and a 110: mean 100.5, variance = (19 * 0.5^2 + 9.5^2) / 20 = 4.75, half bandwidth = 2 sqrt(4.75)
    # %B = 9.5 / (2 * sqrt(4.75)) * 100 = 950 / sqrt(19) = 217.94494717703367 = 50 * sqrt(19), the maximum for n = 20
    top = R.pct_b([100.0] * 19 + [110.0]).to_numpy()[19]
    assert top == pytest.approx(217.94494717703367, abs=1e-9)
    assert top == pytest.approx(50.0 * math.sqrt(19.0), abs=1e-9)
    assert R.pct_b([100.0] * 19 + [90.0]).to_numpy()[19] == pytest.approx(-217.94494717703367, abs=1e-9)
    rng = np.random.default_rng(2)
    walk = 4000 + np.cumsum(rng.choice([-2.0, -0.5, 0.25, 1.0, 3.0], 400))
    pb = R.pct_b(walk).to_numpy()
    assert np.nanmax(np.abs(pb)) <= 50.0 * math.sqrt(19.0) + 1e-9


def test_affine_invariance_and_reflection():
    rng = np.random.default_rng(9)
    close = 4000 + np.cumsum(rng.choice([-2.0, -0.5, 0.25, 1.0, 3.0], 120))
    base = R.pct_b(close).to_numpy()
    # %B is a ratio of price differences: a shift (back-adjustment) or a scale (unit change) leaves it alone,
    # reflecting the prices flips its sign
    assert R.pct_b(close + 321.5).to_numpy()[19:] == pytest.approx(base[19:], abs=1e-6)
    assert R.pct_b(close * 0.01).to_numpy()[19:] == pytest.approx(base[19:], abs=1e-6)
    assert R.pct_b(-close).to_numpy()[19:] == pytest.approx(-base[19:], abs=1e-6)


def test_falsifier_original_mid_equals_upper_band_bug_is_rejected():
    """The original's "mid" variable was the UPPER band, giving %B_orig = %B - 100: 0 at the upper band and -200 at
    the lower. On the hand cases that is 0 (instead of +100), -200 (instead of -100) and -50 (instead of +50), so the
    hand-value tests reject it. Likewise the sample (n-1) standard deviation gives 48.73 instead of 50."""
    assert R.pct_b([100.0] * 16 + [110.0] * 4).to_numpy()[19] != pytest.approx(0.0, abs=1e-6)
    assert R.pct_b([110.0] * 16 + [100.0] * 4).to_numpy()[19] != pytest.approx(-200.0, abs=1e-6)
    assert R.pct_b([99.0] * 10 + [101.0] * 10).to_numpy()[19] != pytest.approx(-50.0, abs=1e-6)
    sample_sd_variant = 1.0 / (2.0 * math.sqrt(20.0 / 19.0)) * 100.0            # = 48.73397172404483
    assert R.pct_b([99.0] * 10 + [101.0] * 10).to_numpy()[19] != pytest.approx(sample_sd_variant, abs=1e-6)


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # bands on the price chart, no sub-panel
    assert c["plots"] == ["Upper", "Middle", "Lower", "%B"]       # %B is transparent, DataBox only
    assert sorted(c["series"]) == ["Lower", "Middle", "PctB", "Upper"]   # read by QS_*_BollingerPctB and the harness
    assert c["lines"] == {}
    assert c["defaults"]["ShowDisclaimer"] == "false"
    assert c["defaults"]["ShowTransparentPlotsInDataBox"] == "true"


def test_csharp_uses_the_middle_band_and_the_original_bar_50_gate():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"boll\s*=\s*Bollinger\(Close,\s*2,\s*20\)", text)
    assert "double bollMid = boll.Middle[0];" in text                       # the deliberate change (ORIG read boll[0])
    assert re.search(r"bollBandWidth\s*>\s*0\s*\?\s*\(Close\[0\]\s*-\s*bollMid\)\s*/\s*\(bollBandWidth\s*\*\s*0\.5\)\s*\*\s*100\.0\s*:\s*0", text)
    assert "if (CurrentBar < 50)" in text


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    close = df["Close"].to_numpy(float)
    up, mid, lo = R.bollinger(close)
    # C# gate: nothing before bar 50 (the 20-bar bands are defined long before that). 4-decimal export -> 6e-5.
    assert_close(up, harness_col(df, MODULE, "Upper"), start=50, tol=6e-5, label="BollingerPctB.Upper")
    assert_close(mid, harness_col(df, MODULE, "Middle"), start=50, tol=6e-5, label="BollingerPctB.Middle")
    assert_close(lo, harness_col(df, MODULE, "Lower"), start=50, tol=6e-5, label="BollingerPctB.Lower")
    assert_close(R.pct_b(close), harness_col(df, MODULE, "PctB"), start=50, tol=6e-5, label="BollingerPctB.PctB")
