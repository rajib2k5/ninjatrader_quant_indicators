"""Unit tests for QI_<NN>_HedgingPressure - the four-term price/volume "hedging pressure" score (-100..+100).

Spec (ledger M15; header of the .cs; ORIG ComputeHedgingPressure; README "Indicators"):
  atr = ATR(14), s20 = SMA(Close, 20), s5 = SMA(Close, 5), vr = Volume / SMA(Volume, 20), rr = (H - L) / SMA(H - L, 20)
  basis = clamp((C - s20) / atr * -25, +-25)
  term  = clamp((dSMA5 - dSMA20) / atr * -50, +-25)          dSMA = SMA[0] - SMA[1] , each divided by atr
  vp    = clamp(dir * vr * 10, +-25)  only when vr > 1.2 and |C - O| / atr < 0.5     (dir = -1 if C < O else +1)
  rc    = clamp(dir * (1 - rr) * 50, +-25) only when rr < 0.6 and vr > 1.3           (dir = -1 if C < s20 else +1)
  HP    = clamp(basis + term + vp + rc, +-100) ; 0 when atr <= 0 or s20 <= 0 ; nothing is computed before bar 50.
  It is a price/volume proxy, NOT the COT-based hedging pressure of Basu & Miffre (2013). rules.yaml: long x <= -35,
  short x >= 35 (the original's "Strong" zones).  Ported in backtest/qibt/patterns.py as hp_score; its own hand tests
  (backtest/tests/test_patterns_unit.py, test_patterns_hp_*) cover the +-25 clamps of each term and a random-bar
  cross-check, so the cases below are different bars: one per term, unclamped, plus invariances.
Reference: qibt.patterns.hp_score (NaN before bar 50).

Base frame: 61 flat bars O = 100, H = 101, L = 99, C = 100, V = 100  =>  TR = 2 so ATR14 = 2 exactly, SMA20(C) = SMA5(C) = 100,
SMA20(H - L) = 2, SMA20(V) = 100. Only bar 60 differs between the cases.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

from qibt import patterns as P
from conftest import (REPO, assert_close, assert_names, bars, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "HedgingPressure"


def _flat(n=61):
    return bars(np.full(n, 100.0), open_=np.full(n, 100.0), high=np.full(n, 101.0), low=np.full(n, 99.0),
                volume=np.full(n, 100.0), start="2024-01-06 00:00", freq="1min")


def _with_last(o, h, l, c, v=100.0, n=61):
    df = _flat(n)
    for col, val in (("Open", o), ("High", h), ("Low", l), ("Close", c), ("Volume", v)):
        df.loc[n - 1, col] = float(val)
    return df


# ---- 1. formula --------------------------------------------------------------------------
def test_basis_and_slope_terms_only():
    # bar 60: O 100, H 101, L 99, C 100.8, V 100  (TR = max(2, 1, 1) = 2, ATR stays 2; vr = 1, rr = 1 -> vp = rc = 0)
    # SMA20 = (19 * 100 + 100.8) / 20 = 100.04 -> basis = (100.8 - 100.04) / 2 * -25 = -9.5
    # SMA5 = (4 * 100 + 100.8) / 5 = 100.16 (d = 0.16), SMA20 d = 0.04 -> (0.16 - 0.04) / 2 * -50 = -3.0
    hp = P.hp_score(_with_last(100.0, 101.0, 99.0, 100.8)).to_numpy()
    assert hp[60] == pytest.approx(-12.5, abs=1e-9)


def test_volume_price_divergence_term_only_unclamped():
    # bar 60: O 100, H 101, L 99, C 100.4, V 200.  SMA20(V) = (19 * 100 + 200) / 20 = 105 -> vr = 200 / 105 = 40/21
    # |C - O| / atr = 0.4 / 2 = 0.2 < 0.5 and vr > 1.2 -> vp = +1 * 40/21 * 10 = 19.047619047619047 (< 25, not clamped)
    # basis = (100.4 - 100.02) / 2 * -25 = -4.75 ; term = (0.08 - 0.02) / 2 * -50 = -1.5 ; rr = 1 -> rc = 0
    # HP = -4.75 - 1.5 + 400/21 = 12.797619047619047
    hp = P.hp_score(_with_last(100.0, 101.0, 99.0, 100.4, v=200.0)).to_numpy()
    assert hp[60] == pytest.approx(12.797619047619047, abs=1e-9)


def test_range_compression_term_unclamped_and_the_half_atr_boundary():
    # bar 60: O 101, H 102, L 101, C 102, V 160.  TR = max(1, |102 - 100| = 2, |101 - 100| = 1) = 2 -> ATR stays 2.
    # |C - O| / atr = 1 / 2 = 0.5, NOT < 0.5 -> vp = 0 even though vr = 160 / 103 = 1.55 > 1.2
    # basis = (102 - 100.1) / 2 * -25 = -23.75 ; term = (0.4 / 2 - 0.1 / 2) * -50 = -7.5
    # rr = 1 / ((19 * 2 + 1) / 20) = 1 / 1.95 = 0.5128 < 0.6 and vr > 1.3 -> rc = +1 * (1 - 1/1.95) * 50 = 47.5 / 1.95 = 24.358974358974358
    # HP = -23.75 - 7.5 + 24.358974358974358 = -6.891025641025642      (rc opposes basis: that is why |HP| <= 75)
    hp = P.hp_score(_with_last(101.0, 102.0, 101.0, 102.0, v=160.0)).to_numpy()
    assert hp[60] == pytest.approx(-6.891025641025642, abs=1e-9)


def test_atr_is_the_14_bar_nt_recursion():
    # The other cases keep TR = 2, where ATR(14) = ATR(20) = 2. Here bar 60 has TR = max(5.5, |105 - 100| = 5, |99.5 - 100| = 0.5) = 5.5,
    # so ATR14 = (13 * 2 + 5.5) / 14 = 2.25 (an ATR(20) would be (19 * 2 + 5.5) / 20 = 2.175).
    # O 100, H 105, L 99.5, C 100.5, V 100 (vr = 1, rr = 5.5 / 2.175 > 0.6, |C - O| / atr = 0.22 but vr <= 1.2: vp = rc = 0)
    # basis = (100.5 - 100.025) / 2.25 * -25 = -5.277777... ; term = (0.1 / 2.25 - 0.025 / 2.25) * -50 = -1.666666...
    # HP = -95/18 - 30/18 = -125/18 = -6.944444444444445
    hp = P.hp_score(_with_last(100.0, 105.0, 99.5, 100.5)).to_numpy()
    assert hp[60] == pytest.approx(-125.0 / 18.0, abs=1e-9)
    assert hp[60] != pytest.approx(-7.1839, abs=1e-3)          # the ATR(20) value: -11.875 / 2.175 - 3.75 / 2.175


def test_quiet_market_scores_zero_and_early_bars_are_nan():
    hp = P.hp_score(_flat(70)).to_numpy()
    assert np.isnan(hp[:50]).all()                            # nothing before bar 50
    assert (hp[50:] == 0.0).all()                             # C = SMA20, flat slopes, vr = rr = 1 -> every term 0
    # ATR14 = 0 (open = high = low = close on every bar) -> the score is the fallback 0, not a division by zero
    dead = bars(np.full(60, 100.0), volume=np.full(60, 100.0), start="2024-01-06 00:00", freq="1min")
    hp0 = P.hp_score(dead).to_numpy()
    assert np.isnan(hp0[:50]).all() and (hp0[50:] == 0.0).all()


def test_price_shift_price_scale_and_volume_scale_invariance():
    base = P.hp_score(_with_last(101.0, 102.0, 101.0, 102.0, v=160.0)).to_numpy()[60]
    assert base == pytest.approx(-6.891025641025642, abs=1e-9)
    for k, s, vk in ((1.0, 1000.0, 1.0), (2.0, 0.0, 1.0), (1.0, 0.0, 7.0)):
        df = _with_last(101.0, 102.0, 101.0, 102.0, v=160.0)
        for c in ("Open", "High", "Low", "Close"):
            df[c] = df[c] * k + s            # (C - SMA) / ATR, slopes / ATR and |C - O| / ATR are unit-free
        df["Volume"] = df["Volume"] * vk     # only volume RATIOS enter
        assert P.hp_score(df).to_numpy()[60] == pytest.approx(base, abs=1e-9)


def test_score_stays_within_75_and_every_value_is_finite_after_bar_50():
    rng = np.random.default_rng(21)
    n = 1500
    c = 4000 + np.cumsum(rng.choice([-1.0, -0.5, 0.0, 0.25, 0.75], n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.choice([0.0, 0.25, 1.0, 3.0], n)
    l = np.minimum(o, c) - rng.choice([0.0, 0.25, 1.0, 3.0], n)
    v = rng.integers(20, 3000, n).astype(float)
    df = bars(c, open_=o, high=h, low=l, volume=v, start="2024-01-06 00:00", freq="1min")
    hp = P.hp_score(df).to_numpy()
    assert np.isfinite(hp[50:]).all()
    # basis and rc always have opposite signs, so the sum never reaches the +-100 clamp
    assert np.abs(hp[50:]).max() <= 75.0 + 1e-9


def test_falsifier_sign_flipped_basis_and_term_is_detected():
    """Reading the score as "high when price is above its average" (positive weights) is the natural slip: on the first
    hand case it gives +9.5 + 3.0 = +12.5 instead of -9.5 - 3.0 = -12.5, so the hand-value test rejects it."""
    hp = P.hp_score(_with_last(100.0, 101.0, 99.0, 100.8)).to_numpy()[60]
    assert hp != pytest.approx(12.5, abs=1e-6)
    assert hp == pytest.approx(-12.5, abs=1e-9)


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # HP lines on the price chart, no sub-panel
    assert c["plots"] == ["HP Score"]                 # transparent, DataBox only
    assert c["series"] == ["HPScore"]                 # read by QS_*_HedgingPressure and the harness
    assert c["lines"] == {}
    assert c["defaults"]["ShowHpLines"] == "true"
    assert c["defaults"]["ShowDisclaimer"] == "false"
    assert c["defaults"]["ShowTransparentPlotsInDataBox"] == "true"


def test_csharp_constants_match_the_spec_and_the_rule_thresholds():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"if \(atr14\[0\] <= 0 \|\| sma20hp\[0\] <= 0\)\s*return 0;", text)
    assert re.search(r"Clamp\(basisDev \* -25\.0, -25, 25\)", text)
    assert re.search(r"Clamp\(slopeDiff \* -50\.0, -25, 25\)", text)
    assert re.search(r"volRatio > 1\.2 && priceChangePct < 0\.5", text) and re.search(r"direction \* volRatio \* 10\.0", text)
    assert re.search(r"rangeRatio < 0\.6 && volRatio > 1\.3", text) and re.search(r"\(1\.0 - rangeRatio\) \* 50\.0", text)
    assert re.search(r"Clamp\(composite, -100, 100\)", text)
    assert "if (CurrentBar < 50)" in text
    # the "Strong" zone cut-offs of the C# are the thresholds of the frozen backtest rule
    assert "hpScore <= -35" in text and re.search(r"else\s*\{\s*zoneName = \"Strong Long HP\"", text)
    rules = (REPO / "backtest" / "rules.yaml").read_text(encoding="utf-8")
    line = next(l for l in rules.splitlines() if "module: HedgingPressure" in l)
    assert 'long: "x <= -35"' in line and 'short: "x >= 35"' in line


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "HPScore")
    ref = P.hp_score(df[["BarTime", "Open", "High", "Low", "Close", "Volume"]])
    # C# gate: nothing before bar 50; every NT SMA / ATR it reads is fully formed by then. 4-decimal export -> 6e-5.
    assert_close(ref, got, start=50, tol=6e-5, label="HedgingPressure.HPScore")
