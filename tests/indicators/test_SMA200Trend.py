"""Unit tests for QI_<NN>_SMA200Trend - SMA(200) overlay and the close-to-SMA distance series.

Spec (ledger M19 + B3, rules.yaml note, ORIG IBSFade.cs 346, 1410-1414):
  Sma200   = mean of the last 200 closes (NinjaTrader averages the available bars before bar 199)
  Distance = Close[0] - Sma200[0] when CurrentBar >= 200, else 0
Rule (rules.yaml): long x > 0, short x < 0, with the note "0 before bar 200 -> flat".
The module is an overlay: it draws the SMA on price and has no reference lines.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (REPO, assert_close, assert_names, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "SMA200Trend"


def step_series():
    """Positions 0-199 close at 100, positions 200-249 at 300."""
    return np.concatenate([np.full(200, 100.0), np.full(50, 300.0)])


# ---- 1. formula --------------------------------------------------------------------------
def test_ramp_hand_values():
    close = np.arange(1.0, 251.0)               # position t closes at t + 1
    sma, dist = R.sma200_trend(close)
    # SMA at t >= 199 = mean of (t-198 .. t+1) = ((t - 198) + (t + 1))/2 = (2t - 197)/2
    #   t = 199: 100.5      t = 200: 101.5      t = 249: (498 - 197)/2 = 150.5
    # Distance = (t + 1) - (2t - 197)/2 = 199/2 = 99.5 for every t >= 200
    assert sma.to_numpy()[199] == pytest.approx(100.5, abs=1e-9)
    assert sma.to_numpy()[200] == pytest.approx(101.5, abs=1e-9)
    assert sma.to_numpy()[249] == pytest.approx(150.5, abs=1e-9)
    assert (dist.to_numpy()[200:] == pytest.approx(99.5, abs=1e-9))


def test_step_moves_the_average_one_hundredth_of_the_jump_per_bar():
    # Step from 100 to 300 at position 200: each new bar replaces a 100 by a 300, adding 200/200 = 1.
    #   position 199: SMA = 100                          (full window of 100s)
    #   position 200: SMA = (199*100 + 300)/200 = 20200/200 = 101    Distance = 300 - 101 = 199
    #   position 201: SMA = (198*100 + 2*300)/200 = 20400/200 = 102  Distance = 300 - 102 = 198
    #   position 202: SMA = (197*100 + 3*300)/200 = 20600/200 = 103  Distance = 300 - 103 = 197
    sma, dist = R.sma200_trend(step_series())
    assert sma.to_numpy()[199] == pytest.approx(100.0, abs=1e-9)
    np.testing.assert_allclose(sma.to_numpy()[200:203], [101.0, 102.0, 103.0], atol=1e-9)
    np.testing.assert_allclose(dist.to_numpy()[200:203], [199.0, 198.0, 197.0], atol=1e-9)


def test_constant_series_has_zero_distance():
    sma, dist = R.sma200_trend(np.full(260, 50.0))
    assert (sma.to_numpy()[199:] == 50.0).all()
    assert (dist.to_numpy()[200:] == 0.0).all()


def test_average_needs_200_closes():
    sma, _ = R.sma200_trend(np.arange(1.0, 251.0))
    assert np.isnan(sma.to_numpy()[:199]).all()       # fewer than 200 closes: no 200-bar average
    assert np.isfinite(sma.to_numpy()[199:]).all()    # position 199 is the 200th close


@pytest.mark.xfail(strict=True, reason="spec/reference disagreement: the C# and rules.yaml ('0 before bar 200 -> flat') "
                   "give 0, but qi_ref.sma200_trend returns NaN for positions < 200")
def test_distance_is_zero_before_bar_200():
    _, dist = R.sma200_trend(np.arange(1.0, 251.0))
    assert (dist.to_numpy()[:200] == 0.0).all()


def test_scale_and_shift_behaviour():
    close = step_series()
    sma, dist = R.sma200_trend(close)
    sma_s, dist_s = R.sma200_trend(close + 1000.0)       # back-adjustment: SMA moves, distance does not
    np.testing.assert_allclose(sma_s.to_numpy()[199:], sma.to_numpy()[199:] + 1000.0, atol=1e-9)
    np.testing.assert_allclose(dist_s.to_numpy()[200:], dist.to_numpy()[200:], atol=1e-9)
    sma_m, dist_m = R.sma200_trend(close * 3.0)          # scaling: both scale
    np.testing.assert_allclose(sma_m.to_numpy()[199:], sma.to_numpy()[199:] * 3.0, atol=1e-9)
    np.testing.assert_allclose(dist_m.to_numpy()[200:], dist.to_numpy()[200:] * 3.0, atol=1e-9)


def test_average_stays_between_the_window_extremes():
    rs = np.random.RandomState(4)
    close = 1000.0 + np.cumsum(rs.normal(0, 4, 600))
    sma, _ = R.sma200_trend(close)
    for t in range(199, 600, 17):
        w = close[t - 199:t + 1]
        assert w.min() - 1e-9 <= sma.to_numpy()[t] <= w.max() + 1e-9


def test_falsifier_sma199_and_ema200_are_rejected():
    """SMA(199) and EMA(200) are the plausible wrong averages; the step hand case rejects both:
    SMA199 at position 200 = (198*100 + 300)/199 = 20100/199 = 101.005 -> distance 198.995 (not 199);
    EMA200 after a long run at 100 = 100 + (2/201)*200 = 101.99 -> distance 198.01 (not 199)."""
    close = step_series()
    sma199 = R.sma(close, 199).to_numpy()
    assert sma199[200] == pytest.approx(20100 / 199, abs=1e-9)
    assert abs((close[200] - sma199[200]) - 199.0) > 1e-3
    ema200 = R.ema(close, 200).to_numpy()
    assert abs((close[200] - ema200[200]) - 199.0) > 0.5
    assert abs(R.sma200_trend(close)[1].to_numpy()[200] - (close[200] - sma199[200])) > 1e-3


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # drawn on the price panel
    assert c["plots"] == ["SMA 200"]
    assert {"Sma200", "Distance"} <= set(c["series"])  # read by QS_*_SMA200Trend and the harness
    assert c["lines"] == {}                           # overlay: no reference lines
    assert "LowerThreshold" not in c["defaults"] and "UpperThreshold" not in c["defaults"]
    assert c["defaults"]["ShowDisclaimer"] == "false"


def test_overlay_and_rule_match_readme_and_rules_yaml():
    c = cs_contract(MODULE)
    rule = next(l for l in (REPO / "backtest" / "rules.yaml").read_text(encoding="utf-8").splitlines()
                if f"module: {MODULE}," in l)
    assert 'long: "x > 0"' in rule and 'short: "x < 0"' in rule and "0 before bar 200" in rule
    row = next(l for l in (REPO / "README.md").read_text(encoding="utf-8").splitlines()
               if l.startswith(f"| `{c['class']}` |")).split("|")
    assert row[4].strip() == "Overlay"


def test_csharp_distance_is_zero_before_bar_200():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"CurrentBar\s*>=\s*200\s*\?\s*Close\[0\]\s*-\s*sma200\[0\]\s*:\s*0\s*;", text)
    assert re.search(r"sma200\s*=\s*SMA\(Close,\s*200\)", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    if len(df) <= 200:
        pytest.skip(f"export has {len(df)} bars; SMA200Trend needs more than 200")
    close = df["Close"].to_numpy(float)
    sma, dist = R.sma200_trend(close)
    # The plot is a true 200-bar mean from position 199 (before that NinjaTrader averages what it has).
    assert_close(sma.to_numpy(), harness_col(df, MODULE, "Sma200"), start=199, tol=6e-5, label="SMA200Trend.Sma200")
    # Distance: the C# gate is CurrentBar >= 200 (it is 0 before; the reference leaves those bars NaN).
    assert_close(dist.to_numpy(), harness_col(df, MODULE, "Distance"), start=200, tol=6e-5, label="SMA200Trend.Distance")
