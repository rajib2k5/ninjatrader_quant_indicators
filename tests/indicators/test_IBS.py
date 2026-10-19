"""Unit tests for QI_<NN>_IBS - Internal Bar Strength of the daily bar.

Spec (ledger M1, ORIG IBSFade.cs, rules.yaml IBS):
  IBS = (Close - Low) / (High - Low) of the DAILY bar, 0.5 when High == Low.
  On an intraday chart the daily bar is the FORMING one: High = running max of the bar highs and
  Low = running min of the bar lows since the trading day began, Close = the current close.
  The C# writes nothing before bar 50 (daily chart), or before bar 50 and the second daily bar (intraday).
Reference lines 0.20 / 0.80 (rules.yaml: long x < 0.20, short x > 0.80).

The reference starts a trading day at 17:00 US Central (a bar closing at or after 17:00 belongs to the
next day). The ledger only says "forming daily bar"; the 17:00 rollover is the reference's documented
assumption, so it is exercised in its own test.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

import qi_ref as R
from qi_helpers import (REPO, assert_close, assert_names, bars, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "IBS"


def daily_bars():
    """H=12 L=8 C=9 | H=12 L=8 C=8 | H=12 L=8 C=12 | H=12 L=8 C=11 | H=L=C=10."""
    return bars([9, 8, 12, 11, 10], high=[12, 12, 12, 12, 10], low=[8, 8, 8, 8, 10])


def intraday_bars():
    """Bar close times in US Central. Trading day 2026-01-06 has bars at 09:30, 09:45, 15:00; the bars
    at 17:15 and 17:30 belong to the next trading day (rollover 17:00)."""
    df = bars([10, 8, 13, 50, 48.5], high=[12, 11, 13, 52, 51], low=[9, 7, 8, 49, 48])
    df["BarTime"] = pd.to_datetime(["2026-01-06 09:30", "2026-01-06 09:45", "2026-01-06 15:00",
                                    "2026-01-06 17:15", "2026-01-06 17:30"])
    return df


# ---- 1. formula --------------------------------------------------------------------------
def test_daily_bar_hand_values():
    # (C - L)/(H - L):  (9-8)/4 = 0.25   (8-8)/4 = 0   (12-8)/4 = 1   (11-8)/4 = 0.75   H = L -> 0.5
    np.testing.assert_allclose(R.ibs_bar(daily_bars()).to_numpy(), [0.25, 0.0, 1.0, 0.75, 0.5], atol=1e-12)


def test_flat_bar_is_one_half():
    # H = L: the ratio is 0/0 and the spec gives 0.5, wherever the price is
    for p in (10.0, 5000.25, 0.01):
        assert R.ibs_bar(bars([p], high=[p], low=[p])).to_numpy()[0] == 0.5


def test_intraday_ibs_reads_the_forming_daily_bar():
    # trading day 2026-01-06:
    #   09:30  H=12 L=9 C=10   day H=12 L=9      IBS = (10-9)/(12-9)  = 1/3
    #   09:45  H=11 L=7 C=8    day H=12 L=7      IBS = (8-7)/(12-7)   = 1/5
    #   15:00  H=13 L=8 C=13   day H=13 L=7      IBS = (13-7)/(13-7)  = 1
    v = R.ibs_daily(intraday_bars()).to_numpy()
    np.testing.assert_allclose(v[:3], [1 / 3, 0.2, 1.0], atol=1e-12)


def test_forming_daily_range_restarts_at_the_17_00_rollover():
    # (reference assumption: the daily bar starts at 17:00 US Central)
    #   17:15  new day, H=52 L=49 C=50     IBS = (50-49)/(52-49) = 1/3
    #   17:30  day H=52 L=48 C=48.5        IBS = (48.5-48)/(52-48) = 0.5/4 = 0.125
    v = R.ibs_daily(intraday_bars()).to_numpy()
    np.testing.assert_allclose(v[3:], [1 / 3, 0.125], atol=1e-12)


def test_flat_first_bar_of_the_day_is_one_half_then_the_range_opens():
    df = bars([10, 12], high=[10, 12], low=[10, 10])
    df["BarTime"] = pd.to_datetime(["2026-01-06 09:30", "2026-01-06 09:45"])
    # bar 0: day H = L = 10 -> 0.5;  bar 1: day H=12 L=10, C=12 -> (12-10)/(12-10) = 1
    np.testing.assert_allclose(R.ibs_daily(df).to_numpy(), [0.5, 1.0], atol=1e-12)


def test_values_stay_inside_0_1():
    rs = np.random.RandomState(21)
    n = 600
    mid = 1000.0 + np.cumsum(rs.normal(0, 2, n))
    rng = rs.pareto(1.5, n) + 0.01
    high, low = mid + rng / 2, mid - rng / 2
    df = bars(low + rs.uniform(0, 1, n) * rng, high=high, low=low, freq="15min", start="2026-01-05 09:00")
    for v in (R.ibs_bar(df).to_numpy(), R.ibs_daily(df).to_numpy()):
        assert np.isfinite(v).all() and (v >= 0).all() and (v <= 1).all()


def test_scale_shift_and_mirror_symmetry():
    s = daily_bars()
    hand = np.array([0.25, 0.0, 1.0, 0.75, 0.5])
    scaled = bars(s["Close"] * 4.0, high=s["High"] * 4.0, low=s["Low"] * 4.0)
    shifted = bars(s["Close"] + 100.0, high=s["High"] + 100.0, low=s["Low"] + 100.0)
    np.testing.assert_allclose(R.ibs_bar(scaled).to_numpy(), hand, atol=1e-12)
    np.testing.assert_allclose(R.ibs_bar(shifted).to_numpy(), hand, atol=1e-12)
    # reflecting the price axis (C' = 100 - C, H' = 100 - L, L' = 100 - H) turns IBS into 1 - IBS:
    # 1 - [0.25, 0, 1, 0.75, 0.5] = [0.75, 1, 0, 0.25, 0.5]
    mirrored = bars(100.0 - s["Close"], high=100.0 - s["Low"], low=100.0 - s["High"])
    np.testing.assert_allclose(R.ibs_bar(mirrored).to_numpy(), [0.75, 1.0, 0.0, 0.25, 0.5], atol=1e-12)


def test_falsifier_inverted_per_bar_and_calendar_day_variants_are_rejected():
    """Plausible wrong variants, each rejected by the hand values above:
    (H - C)/(H - L) inverts test 1 (0.75 where 0.25 is right); IBS of each 15-minute bar instead of the
    forming daily bar gives (8-7)/(11-7) = 0.25 where test 3 has 0.2; a calendar-day key (no 17:00 rollover)
    gives (50-7)/(52-7) = 43/45 = 0.956 at 17:15 where test 4 has 1/3."""
    d = daily_bars()
    inverted = ((d["High"] - d["Close"]) / (d["High"] - d["Low"])).to_numpy()
    assert abs(inverted[0] - 0.25) > 0.4
    df = intraday_bars()
    per_bar = R.ibs_bar(df).to_numpy()
    assert per_bar[1] == pytest.approx(0.25, abs=1e-12) and abs(per_bar[1] - 0.2) > 0.04
    calendar = R.ibs_daily(df, "calendar").to_numpy()
    assert calendar[3] == pytest.approx(43 / 45, abs=1e-12) and abs(calendar[3] - 1 / 3) > 0.5
    assert abs(R.ibs_daily(df).to_numpy()[3] - calendar[3]) > 0.5


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["IBS"]
    assert "IBS" in c["series"]                       # read by QS_*_IBS and the harness
    assert c["lines"] == {"Lower Threshold": 0.2, "Upper Threshold": 0.8}
    assert c["defaults"]["LowerThreshold"] == "0.20" and c["defaults"]["UpperThreshold"] == "0.80"
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


def test_csharp_gates_daily_series_and_flat_fallback():
    text = cs_contract(MODULE)["text"]
    assert "if (CurrentBar < 50)" in text                                    # daily chart gate
    assert "CurrentBars[0] < 50 || CurrentBars[1] < 1" in text               # intraday gate
    assert re.search(r"AddDataSeries\(Data\.BarsPeriodType\.Day,\s*1\)", text)   # forming daily bar source
    assert re.search(r"\(range\s*>\s*0\)\s*\?\s*\(Close\[0\]\s*-\s*Low\[0\]\)\s*/\s*range\s*:\s*0\.5", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "IBS")
    t = pd.to_datetime(df["BarTime"])
    if t.diff().median() >= pd.Timedelta(hours=20):
        # daily chart: per-bar IBS from the C# gate CurrentBar >= 50
        ref, start = R.ibs_bar(df).to_numpy(), 50
    else:
        # intraday chart: forming daily bar. The C# also waits for CurrentBars[1] >= 1, i.e. until the
        # second daily bar has closed, so compare from the start of the fourth trading day (and bar 50).
        day = R.trading_day(t).factorize()[0]
        if day.max() < 3:
            pytest.skip("export covers fewer than four trading days")
        ref, start = R.ibs_daily(df).to_numpy(), max(50, int(np.argmax(day >= 3)))
    assert_close(ref, got, start=start, tol=6e-5, label="IBS")
