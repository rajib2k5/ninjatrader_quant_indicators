"""Unit tests for QI_<NN>_ChopIndex - Choppiness Index (14) plus the 2-of-3 "choppy" state.

Spec (ledger M23 + B9; ORIG IBSFade.cs 358-359, 1453-1524; header of the .cs; README "Indicators"):
  CHOP = 100 * log10( sum(TrueRange, 14) / (HH14 - LL14) ) / log10(14), clamped to 0..100
         TrueRange = max(H - L, |H - C[1]|, |L - C[1]|)   (the C# extends H - L with the gap terms only when i < CurrentBar)
         50 while CurrentBar < 14 and 50 when HH14 == LL14
  VolRatio = Volume / SMA(Volume, 20)   (1.0 when the SMA is <= 0)
  state count = [CHOP > 61.8] + [ADX14 < 20] + [VolRatio < 0.7] ; ChoppyFlag = 1 if count >= 2 (CHOPPY),
                0.5 if count == 1 (CAUTION), 0 otherwise (TRENDING)
Reference lines 38.2 / 61.8. Not backtestable (rules.yaml: no Buy/Sell class in the original).
Reference: qi_ref.chop, qi_ref.chop_state (the COUNT), qi_ref.vol_ratio, qi_ref.adx.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "ChopIndex"


def _ohlc(high, low, close, volume=None):
    return bars(close, high=high, low=low, volume=volume)


def _ramp(n, step=1.0, rng=1.0, volume=None):
    """Bars that rise by `step` per bar, each with range `rng`, closing at the high."""
    t = np.arange(n, dtype=float)
    return _ohlc(100.0 + rng + step * t, 100.0 + step * t, 100.0 + rng + step * t, volume)


def _flat(n, volume=None):
    return _ohlc(np.full(n, 101.0), np.full(n, 99.0), np.full(n, 100.0), volume)


# ---- 1. formula --------------------------------------------------------------------------
def test_a_perfect_trend_gives_chop_zero_and_a_flat_range_gives_chop_hundred():
    # ramp: high = 101 + t, low = 100 + t, close = high -> every TR = 1 (gap terms 1 and 0), sum over 14 = 14 ;
    #       HH14 - LL14 = (101 + t) - (100 + t - 13) = 14  =>  CHOP = 100 * log10(14 / 14) / log10(14) = 0
    ramp = R.chop(_ramp(20)).to_numpy()
    assert ramp[14:].tolist() == pytest.approx([0.0] * 6, abs=1e-12)
    # flat: high = 101, low = 99, close = 100 -> every TR = 2, sum = 28 ; HH - LL = 2 => ratio 14 => CHOP = 100
    flat = R.chop(_flat(20)).to_numpy()
    assert flat[14:].tolist() == pytest.approx([100.0] * 6, abs=1e-9)


def test_intermediate_hand_value_ratio_28_over_15():
    # ramp with range 2: high = 102 + t, low = 100 + t, close = high -> TR = max(2, |102+t-(101+t)| = 1, |100+t-(101+t)| = 1) = 2
    # sum over 14 = 28 ; HH14 - LL14 = (102 + t) - (100 + t - 13) = 15 ; CHOP = 100 * log10(28 / 15) / log10(14)
    #                                                                          = 23.6506536659432
    chop = R.chop(_ramp(20, step=1.0, rng=2.0)).to_numpy()
    assert chop[14:].tolist() == pytest.approx([23.6506536659432] * 6, abs=1e-9)


def test_true_range_includes_the_gap_to_the_previous_close():
    # Each bar has range 1 but opens 3 higher than the last: high = 101 + 3t, low = 100 + 3t, close = high.
    # TR = max(1, |101 + 3t - (101 + 3(t-1))| = 3, |100 + 3t - (101 + 3(t-1))| = 2) = 3 -> sum over 14 = 42
    # HH14 - LL14 = (101 + 3t) - (100 + 3(t-13)) = 40  =>  CHOP = 100 * log10(42 / 40) / log10(14) = 1.8487724242256245
    chop = R.chop(_ramp(20, step=3.0, rng=1.0)).to_numpy()
    assert chop[14:].tolist() == pytest.approx([1.8487724242256245] * 6, abs=1e-9)


def test_fifty_during_warmup_and_when_high_equals_low():
    # The 14-bar ramp would read 0 on every bar; the C# (CurrentBar >= 14) holds 50 on bars 0..13 and computes from bar 14.
    chop = R.chop(_ramp(20)).to_numpy()
    assert chop[:14].tolist() == [50.0] * 14 and chop[14] == pytest.approx(0.0, abs=1e-12)
    # HH14 == LL14 (a dead market): the ratio is undefined -> 50 on every bar
    dead = R.chop(_ohlc(np.full(30, 100.0), np.full(30, 100.0), np.full(30, 100.0))).to_numpy()
    assert dead.tolist() == [50.0] * 30


def test_clamped_to_0_100():
    # bar 0 is a single price 100, bar 1 jumps to a quiet band 199..201 closing at 200: TR[1] = max(2, 101, 99) = 101, later TR = 2.
    # At bar 14 the window is bars 1..14: sum TR = 101 + 13 * 2 = 127, HH - LL = 2 -> ratio 63.5 -> raw CHOP = 157.29 -> clamp 100.
    high = np.r_[100.0, np.full(19, 201.0)]
    low = np.r_[100.0, np.full(19, 199.0)]
    close = np.r_[100.0, np.full(19, 200.0)]
    chop = R.chop(_ohlc(high, low, close)).to_numpy()
    assert chop[14] == 100.0
    assert chop[15] == pytest.approx(100.0, abs=1e-9)             # window bars 2..15: ratio 28 / 2 = 14 exactly
    rng = np.random.default_rng(8)
    c = 4000 + np.cumsum(rng.choice([-3.0, -1.0, 0.5, 2.0, 4.0], 500))
    rand = R.chop(_ohlc(c + 1.5, c - 1.5, c)).to_numpy()
    assert rand.min() >= 0.0 and rand.max() <= 100.0


def test_shift_scale_and_reflection_invariances():
    rng = np.random.default_rng(1)
    c = 4000 + np.cumsum(rng.choice([-3.0, -1.0, 0.5, 2.0, 4.0], 120))
    h, l = c + rng.choice([0.5, 1.0, 2.0], 120), c - rng.choice([0.5, 1.0, 2.0], 120)
    base = R.chop(_ohlc(h, l, c)).to_numpy()
    # CHOP is a ratio of price differences (sum of ranges over the net range)
    assert R.chop(_ohlc(h + 777.0, l + 777.0, c + 777.0)).to_numpy() == pytest.approx(base, abs=1e-9)
    assert R.chop(_ohlc(h * 0.01, l * 0.01, c * 0.01)).to_numpy() == pytest.approx(base, abs=1e-9)
    assert R.chop(_ohlc(-l, -h, -c)).to_numpy() == pytest.approx(base, abs=1e-9)        # mirrored market


def test_state_count_hand_cases():
    # flat market, constant volume 100: CHOP = 100 > 61.8 (1), ADX = 0 < 20 (1), VolRatio = 1 (0)            -> 2 (CHOPPY)
    assert R.chop_state(_flat(40, volume=np.full(40, 100.0))).iloc[39] == 2
    # same, last bar volume 10: SMA20 = (19 * 100 + 10) / 20 = 95.5, 0.7 * 95.5 = 66.85 > 10 (1)                -> 3
    v = np.full(40, 100.0)
    v[39] = 10.0
    assert R.chop_state(_flat(40, volume=v)).iloc[39] == 3
    # one-directional ramp (+DM only): CHOP = 0 (0), ADX = 100 (0), VolRatio = 1 (0)                              -> 0 (TRENDING)
    assert R.chop_state(_ramp(40, volume=np.full(40, 100.0))).iloc[39] == 0
    # same ramp with the low last bar volume                                                                      -> 1 (CAUTION)
    assert R.chop_state(_ramp(40, volume=v)).iloc[39] == 1


def test_vol_ratio_hand_value():
    v = np.r_[np.full(19, 100.0), 300.0]
    # SMA20 = (19 * 100 + 300) / 20 = 110 ; ratio = 300 / 110 = 30/11 ; undefined before 20 bars in the reference
    r = R.vol_ratio(_flat(20, volume=v)).to_numpy()
    assert r[19] == pytest.approx(30.0 / 11.0, abs=1e-12) and np.isnan(r[:19]).all()


def test_falsifier_missing_true_range_gap_terms_is_detected():
    """Dropping the |H - C[1]| / |L - C[1]| terms (TR = H - L) is the slip the i < CurrentBar guard exists to avoid.
    On the gapping ramp the specified sum is 42 (CHOP 1.8488) but H - L alone gives 14 -> ratio 0.35 -> negative log,
    clamped to 0. The hand value of test_true_range_includes_the_gap_to_the_previous_close pins the difference.
    A missing 0..100 clamp would read 157.29 instead of 100 on the jump case."""
    gap = R.chop(_ramp(20, step=3.0, rng=1.0)).to_numpy()[14]
    assert gap != pytest.approx(0.0, abs=1e-6)                    # the no-gap-terms variant
    assert gap == pytest.approx(1.8487724242256245, abs=1e-9)
    jump = R.chop(_ohlc(np.r_[100.0, np.full(19, 201.0)], np.r_[100.0, np.full(19, 199.0)],
                        np.r_[100.0, np.full(19, 200.0)])).to_numpy()[14]
    assert jump != pytest.approx(157.29252484650706, abs=1e-6)    # the unclamped variant
    assert jump == 100.0


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["CHOP"]
    assert sorted(c["series"]) == ["Adx", "Chop", "ChoppyFlag", "VolRatio"]    # read by the harness
    assert c["lines"] == {"Lower Threshold": 38.2, "Upper Threshold": 61.8}
    assert c["defaults"]["LowerThreshold"] == "38.2" and c["defaults"]["UpperThreshold"] == "61.8"
    assert c["defaults"]["ShowStateText"] == "true"
    assert c["defaults"]["ShowDisclaimer"] == "false"


def test_csharp_formula_gates_and_state_mapping():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"double chopVal = 50;", text) and re.search(r"int chopPeriod = 14;", text)
    assert re.search(r"if \(CurrentBar >= chopPeriod\)", text)                         # 50 before bar 14
    assert re.search(r"if \(i < CurrentBar\)", text)                                   # the TR guard
    assert re.search(r"chopVal = Math\.Max\(0, Math\.Min\(100, chopVal\)\)", text)    # clamp 0..100
    assert re.search(r"if \(range > 0\)", text)                                        # HH == LL keeps 50
    assert re.search(r"chopVal > 61\.8", text) and re.search(r"adxVal < 20", text) and re.search(r"volRatioChop < 0\.7", text)
    assert re.search(r"chopSignals >= 2\)[^}]*chopFlag = 1;", text, re.S)             # CHOPPY
    assert re.search(r"chopSignals == 1\)[^}]*chopFlag = 0\.5;", text, re.S)          # CAUTION
    assert re.search(r"else\s*\{[^}]*chopFlag = 0;", text, re.S)                       # TRENDING
    assert re.search(r"volSma20\[0\] > 0 \? Volume\[0\] / volSma20\[0\] : 1\.0", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    chop = harness_col(df, MODULE, "Chop")
    # C# gate: CurrentBar >= 14 (no module-wide bar-50 gate); the first 14 bars hold the fallback 50.
    assert_close(R.chop(df), chop, start=14, tol=6e-5, label="ChopIndex.Chop")
    assert (np.nan_to_num(chop.to_numpy(float)[:14], nan=50.0) == 50.0).all()
    # VolRatio: NinjaTrader's SMA averages fewer bars before 20, the reference needs 20.
    assert_close(R.vol_ratio(df), harness_col(df, MODULE, "VolRatio"), start=19, tol=6e-5, label="ChopIndex.VolRatio")


def test_adx_and_choppy_flag_match_the_export():
    df = harness_frame()
    adx_ref = R.adx(df, 14)[0].to_numpy(float)
    adx_got = harness_col(df, MODULE, "Adx")
    # Ledger B9: the NT ADX recursion agrees with the Wilder reference to 1e-2 after a 300-bar warm-up (plus the 4-decimal export).
    assert_close(adx_ref, adx_got, start=300, tol=1e-2 + 6e-5, label="ChopIndex.Adx")
    # ChoppyFlag = 1 / 0.5 / 0 from the reference COUNT (the C# mapping). A flag can flip when ADX is within the
    # tolerance of 20, so those bars (and bars on the CHOP / volume thresholds) are left out of the comparison.
    count = R.chop_state(df).to_numpy(float)
    flag = np.where(np.isnan(count), np.nan, np.where(count >= 2, 1.0, np.where(count == 1, 0.5, 0.0)))
    near = ((np.abs(adx_ref - 20.0) < 0.02) | (np.abs(R.chop(df).to_numpy() - 61.8) < 1e-3)
            | (np.abs(R.vol_ratio(df).to_numpy() - 0.7) < 1e-3))
    flag[near] = np.nan
    assert_close(flag, harness_col(df, MODULE, "ChoppyFlag"), start=300, tol=1e-9, label="ChopIndex.ChoppyFlag")
