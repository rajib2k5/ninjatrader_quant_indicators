"""Unit tests for QI_<NN>_EMACross - EMA(20) / EMA(50) overlay with the spread series.

Spec (ledger M18 + B2, ORIG IBSFade.cs 344-345, 1404-1408):
  EMA_n[t] = EMA_n[t-1] + 2/(n+1) * (Close[t] - EMA_n[t-1]),  seeded with the first close (NinjaTrader EMA)
  Spread   = EMA20 - EMA50
Rule (rules.yaml): long Spread > 0, short Spread < 0. The module is an overlay with no reference lines
and no warm-up gate: it plots from bar 0.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from conftest import (REPO, assert_close, assert_names, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "EMACross"


# ---- 1. formula --------------------------------------------------------------------------
def test_first_three_closes_hand_values():
    # closes 10, 11, 12;  alpha20 = 2/21, alpha50 = 2/51, both seeded with the first close
    #  EMA20: e0 = 10
    #         e1 = 10 + (2/21)(11 - 10)                = 212/21
    #         e2 = 212/21 + (2/21)(12 - 212/21)        = 212/21 + (2/21)(40/21) = 4532/441
    #  EMA50: e0 = 10
    #         e1 = 10 + (2/51)(11 - 10)                = 512/51
    #         e2 = 512/51 + (2/51)(12 - 512/51)        = 512/51 + (2/51)(100/51) = 26312/2601
    #  Spread: 0;  212/21 - 512/51 = 2/21 - 2/51 = 20/357;  4532/441 - 26312/2601
    e20, e50, spread = (s.to_numpy() for s in R.ema_cross([10.0, 11.0, 12.0]))
    np.testing.assert_allclose(e20, [10.0, 212 / 21, 4532 / 441], atol=1e-12)
    np.testing.assert_allclose(e50, [10.0, 512 / 51, 26312 / 2601], atol=1e-12)
    np.testing.assert_allclose(spread, [0.0, 20 / 357, 4532 / 441 - 26312 / 2601], atol=1e-12)


def test_step_response_hand_values():
    # 60 closes at 100 (both EMAs stay exactly 100), then two closes at 200: EMA after k steps = 200 - 100*(1 - alpha)^k
    #  k = 1: EMA20 = 100 + 200/21 = 2300/21          EMA50 = 100 + 200/51 = 5300/51
    #  k = 2: EMA20 = 200 - 100*(19/21)^2 = 52100/441  EMA50 = 200 - 100*(49/51)^2 = 280100/2601
    e20, e50, spread = (s.to_numpy() for s in R.ema_cross([100.0] * 60 + [200.0, 200.0]))
    assert e20[59] == 100.0 and e50[59] == 100.0 and spread[59] == 0.0
    np.testing.assert_allclose(e20[60:], [2300 / 21, 52100 / 441], atol=1e-9)
    np.testing.assert_allclose(e50[60:], [5300 / 51, 280100 / 2601], atol=1e-9)
    np.testing.assert_allclose(spread[60:], [2300 / 21 - 5300 / 51, 52100 / 441 - 280100 / 2601], atol=1e-9)


def test_ramp_spread_converges_to_the_difference_of_the_lags():
    # On a ramp of slope 1 an EMA(n) lags the price by (n - 1)/2 bars: 9.5 for n = 20, 24.5 for n = 50.
    # So after the seed has been forgotten: EMA20 = 599 - 9.5, EMA50 = 599 - 24.5, Spread = 24.5 - 9.5 = 15
    e20, e50, spread = (s.to_numpy() for s in R.ema_cross(np.arange(600.0)))
    assert e20[-1] == pytest.approx(589.5, abs=1e-6)
    assert e50[-1] == pytest.approx(574.5, abs=1e-6)
    assert spread[-1] == pytest.approx(15.0, abs=1e-6)


def test_constant_series_and_bar_zero():
    e20, e50, spread = (s.to_numpy() for s in R.ema_cross([5.0] * 80))
    assert (e20 == 5.0).all() and (e50 == 5.0).all() and (spread == 0.0).all()
    # no warm-up: both EMAs exist from bar 0 and start at the first close
    a20, a50, _ = (s.to_numpy() for s in R.ema_cross([7.0, 9.0, 8.0]))
    assert np.isfinite(a20).all() and np.isfinite(a50).all()
    assert a20[0] == 7.0 and a50[0] == 7.0


def test_ema_is_a_weighted_average_of_past_closes_so_it_stays_inside_their_range():
    rs = np.random.RandomState(2)
    close = 1000.0 + np.cumsum(rs.normal(0, 4, 400))
    e20, e50, spread = R.ema_cross(close)
    lo, hi = np.minimum.accumulate(close), np.maximum.accumulate(close)
    for e in (e20.to_numpy(), e50.to_numpy()):
        assert (e >= lo - 1e-9).all() and (e <= hi + 1e-9).all()
    assert np.abs(spread.to_numpy()).max() <= (close.max() - close.min()) + 1e-9


def test_scale_and_shift_behaviour():
    close = 100.0 + np.cumsum(np.random.RandomState(8).normal(0, 2, 150))
    a20, a50, asp = (s.to_numpy() for s in R.ema_cross(close))
    s20, s50, ssp = (s.to_numpy() for s in R.ema_cross(close + 1000.0))     # back-adjustment: lines move, spread does not
    np.testing.assert_allclose(s20, a20 + 1000.0, atol=1e-9)
    np.testing.assert_allclose(s50, a50 + 1000.0, atol=1e-9)
    np.testing.assert_allclose(ssp, asp, atol=1e-9)
    m20, m50, msp = (s.to_numpy() for s in R.ema_cross(close * 3.0))        # scaling: all three scale
    np.testing.assert_allclose(m20, a20 * 3.0, atol=1e-9)
    np.testing.assert_allclose(msp, asp * 3.0, atol=1e-9)


def test_falsifier_wilder_weight_and_off_by_one_alpha_are_rejected():
    """Two plausible miscodings of the EMA weight, both rejected by the hand values of test 1
    (EMA20 = 10.0952 at bar 1, 10.2766 at bar 2): Wilder's 1/20 gives 10.05 / 10.1475, and alpha = 2/n = 0.1
    (instead of 2/(n+1)) gives 10.1 at bar 1."""
    close = [10.0, 11.0, 12.0]
    wilder = R.wilder(close, 20).to_numpy()
    assert wilder[2] == pytest.approx(10.1475, abs=1e-9) and abs(wilder[2] - 4532 / 441) > 0.1
    off_by_one = R.ema(close, 19).to_numpy()            # alpha = 2/20
    assert off_by_one[1] == pytest.approx(10.1, abs=1e-9) and abs(off_by_one[1] - 212 / 21) > 1e-3
    assert abs(R.ema_cross(close)[0].to_numpy()[1] - off_by_one[1]) > 1e-3


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # drawn on the price panel
    assert c["plots"] == ["EMA 20", "EMA 50"]         # Values[0] = EMA20, Values[1] = EMA50
    assert {"Ema20", "Ema50", "Spread"} <= set(c["series"])    # read by QS_*_EMACross and the harness
    assert c["lines"] == {}                           # overlay: no reference lines
    assert "LowerThreshold" not in c["defaults"] and "UpperThreshold" not in c["defaults"]
    assert c["defaults"]["ShowDisclaimer"] == "false"


def test_overlay_and_rule_match_readme_and_rules_yaml():
    c = cs_contract(MODULE)
    rule = next(l for l in (REPO / "backtest" / "rules.yaml").read_text(encoding="utf-8").splitlines()
                if f"module: {MODULE}," in l)
    assert 'long: "x > 0"' in rule and 'short: "x < 0"' in rule and "value: ema_spread" in rule
    row = next(l for l in (REPO / "README.md").read_text(encoding="utf-8").splitlines()
               if l.startswith(f"| `{c['class']}` |")).split("|")
    assert row[4].strip() == "Overlay"


def test_csharp_periods_spread_and_no_gate():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"ema20\s*=\s*EMA\(Close,\s*20\)", text) and re.search(r"ema50\s*=\s*EMA\(Close,\s*50\)", text)
    body = text[text.index("protected override void OnBarUpdate"):].split("DrawDisclaimerOnce();")[0]
    assert "CurrentBar" not in body                    # plots from bar 0
    assert re.search(r"emaDiff\s*=\s*ema20\[0\]\s*-\s*ema50\[0\]", body)
    assert re.search(r"spreadSeries\[0\]\s*=\s*emaDiff", body)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    e20, e50, spread = R.ema_cross(df["Close"].to_numpy(float))
    # No CurrentBar gate in the C#; NinjaTrader's EMA is seeded with the first close like the reference,
    # so every bar is comparable.
    assert_close(e20.to_numpy(), harness_col(df, MODULE, "Ema20"), start=0, tol=6e-5, label="EMACross.Ema20")
    assert_close(e50.to_numpy(), harness_col(df, MODULE, "Ema50"), start=0, tol=6e-5, label="EMACross.Ema50")
    assert_close(spread.to_numpy(), harness_col(df, MODULE, "Spread"), start=0, tol=6e-5, label="EMACross.Spread")
