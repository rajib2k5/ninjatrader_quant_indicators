"""Unit tests for QI_<NN>_MACDHistogram - the MACD(12, 26, 9) histogram (MACD line minus signal line).

Spec (ledger M17 = built-in B6; ORIG IBSFade.cs 348, 1399-1402; README "Indicators"):
  EMA_n[0] = EMA_n[1] + 2/(n+1) * (x[0] - EMA_n[1]), seeded with the first value (NinjaTrader Value[0] = Input[0])
  line      = EMA12(Close) - EMA26(Close)
  signal    = EMA9(line)
  histogram = line - signal                      (NinjaTrader MACD(Close, 12, 26, 9).Diff)
  The C# writes nothing before bar 50 (module-wide warm-up gate); reference line "Zero" at Threshold = 0.
  rules.yaml: long when x > 0, short when x < 0 - the zero line is a neutral boundary, not a signal.
Reference: qi_ref.macd_hist (and qi_ref.macd for the line).
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (assert_close, assert_names, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "MACDHistogram"


# ---- 1. formula --------------------------------------------------------------------------
def test_constant_prices_give_a_zero_histogram():
    # Both EMAs equal the constant, so line = 0 and signal = 0 on every bar.
    hist = R.macd_hist(np.full(40, 4321.25))
    assert (hist.to_numpy() == 0.0).all()


def test_step_up_hand_values():
    close = [100, 110, 110, 110]
    # alpha12 = 2/13, alpha26 = 2/27, alpha9 = 2/10; all three EMAs are seeded with 100, so bar 0: line 0, signal 0.
    # bar 1: EMA12 = 100 + 2/13*10 = 1320/13, EMA26 = 100 + 2/27*10 = 2720/27
    #        line = 1320/13 - 2720/27 = 280/351, signal = 0.2*280/351 = 56/351
    #        hist = 280/351 - 56/351 = 224/351 = 0.6381766381766382
    # bar 2: EMA12 = 1320/13*11/13 + 110*2/13 = 17380/169, EMA26 = 2720/27*25/27 + 110*2/27 = 73940/729
    #        line = 17380/169 - 73940/729 = 174160/123201, signal = 0.8*56/351 + 0.2*line = 252784/616005
    #        hist = 618016/616005 = 1.0032645838913645
    # bar 3: line = 81300520/43243551, signal = 761411336/1081088775, hist = 1271101664/1081088775
    expected = [0.0, 224 / 351, 618016 / 616005, 1271101664 / 1081088775]
    assert expected[1:] == pytest.approx([0.6381766381766382, 1.0032645838913645, 1.1757606714582713], abs=1e-12)
    assert R.macd_hist(close).to_numpy() == pytest.approx(expected, abs=1e-12)


def test_pulse_hand_values_and_mirror_down_step():
    # [100, 110, 100]: bars 0-1 as above; bar 2: EMA12 = 1320/13*11/13 + 100*2/13 = 17120/169,
    # EMA26 = 2720/27*25/27 + 100*2/27 = 73400/729, line = 17120/169 - 73400/729 = 75880/123201,
    # signal = 0.8*56/351 + 0.2*75880/123201 = 154504/616005, hist = 224896/616005 = 0.36508794571472636
    assert R.macd_hist([100, 110, 100]).to_numpy() == pytest.approx([0.0, 224 / 351, 224896 / 616005], abs=1e-12)
    # [100, 90, 90] is the mirror of [100, 110, 110]: the histogram is minus the step-up values
    assert R.macd_hist([100, 90, 90]).to_numpy() == pytest.approx([0.0, -224 / 351, -618016 / 616005], abs=1e-12)


def test_sign_follows_the_trend():
    up = 100.0 + np.arange(60)
    # A rising ramp: the MACD line climbs towards 7 (= slope * (12.5 - 5.5), the lag difference of the two
    # EMAs) and the signal trails it, so line - signal > 0; a falling ramp is the mirror.
    assert (R.macd_hist(up).to_numpy()[1:] > 0).all()
    assert (R.macd_hist(300.0 - np.arange(60)).to_numpy()[1:] < 0).all()


def test_shift_scale_and_reflection_invariances():
    rng = np.random.default_rng(11)
    close = 4000 + np.cumsum(rng.choice([-2.0, -1.0, -0.25, 0.25, 1.0, 2.0], 120))
    base = R.macd_hist(close).to_numpy()
    assert R.macd_hist(close + 1000.0).to_numpy() == pytest.approx(base, abs=1e-9)   # EMA12 - EMA26 cancels a shift
    assert R.macd_hist(close * 3.0).to_numpy() == pytest.approx(3.0 * base, abs=1e-9)  # linear in the price level
    assert R.macd_hist(-close).to_numpy() == pytest.approx(-base, abs=1e-9)           # reflection flips the sign


def test_falsifier_macd_line_instead_of_histogram_is_detected():
    """The classic mix-up returns the MACD line. At bar 1 of the step case the line is 280/351 = 0.79772 but the
    histogram is 224/351 = 0.63818 (line minus signal 56/351), so the hand-value test tells them apart."""
    wrong_line_at_bar1 = 280 / 351
    hist = R.macd_hist([100, 110, 110, 110]).to_numpy()
    assert hist[1] != pytest.approx(wrong_line_at_bar1, abs=1e-6)
    assert hist[1] == pytest.approx(224 / 351, abs=1e-12)


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["MACD Hist"]
    assert c["series"] == ["Histogram"]               # read by QS_*_MACDHistogram and the harness
    assert c["lines"] == {"Zero": 0.0}
    assert c["defaults"]["Threshold"] == "0"
    assert c["defaults"]["ShowDisclaimer"] == "false"


def test_csharp_is_macd_12_26_9_diff_with_the_original_bar_50_gate():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"macd\s*=\s*MACD\(Close,\s*12,\s*26,\s*9\)\s*;", text)
    assert "Values[0][0] = macd.Diff[0];" in text
    assert "if (CurrentBar < 50)" in text


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "Histogram")
    # The C# writes from bar 50 (first bar after its gate); the EMAs themselves run from bar 0 in NinjaTrader and
    # in the reference, so there is no further warm-up to skip. 4-decimal export -> 6e-5.
    ref = R.macd_hist(df["Close"].to_numpy(float))
    assert_close(ref, got, start=50, tol=6e-5, label="MACDHistogram.Histogram")
