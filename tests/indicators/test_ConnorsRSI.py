"""Unit tests for QI_<NN>_ConnorsRSI - mean of RSI(2) of price, RSI(2) of the streak and the 100-bar percent rank.

Spec (ledger M3 + B1, ORIG IBSFade.cs 342, 410-411, 1277-1296, 1552-1568):
  CRSI   = (RSI_2(Close) + RSI_2(streak) + PercentRank_100(ROC_1)) / 3,   50 until bar 100
  streak = signed run of up (+n) / down (-n) closes; an unchanged close keeps the counts
  PercentRank = (number of the previous 100 one-bar changes strictly below today's) / 100 * 100
  The C# also keeps ORIG's module-wide gate: nothing is computed before bar 50.
Reference lines 15 / 85 (rules.yaml: long x < 15, short x > 85).
Deviations from Connors' published CRSI (RSI(3) of price, streak reset on an unchanged close) are
documented in the C# header and are the falsifier targets below.

Hand values avoid the (unstated) Wilder seed: they use the steady state of an alternating series,
flat series ended by one move, and monotone series.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (REPO, assert_close, assert_names, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "ConnorsRSI"


def alternating(n_bars):
    """10, 11, 10, 11, ...: odd positions are up closes, even positions (> 0) are down closes."""
    return 10.0 + (np.arange(n_bars) % 2)


# ---- 1. formula --------------------------------------------------------------------------
def test_alternating_closes_hand_values():
    # close 10, 11, 10, 11, ...: position 199 is an up close, 198 a down close (windows have 50 ups + 50 downs).
    #  RSI_2(close): weight 1/2 steady state -> 200/3 after an up bar, 100/3 after a down bar
    #  streak alternates +1, -1 (moves of +2 / -2), so RSI_2(streak) is the same 200/3 / 100/3
    #  PercentRank: at an up close (ROC +10%) the 50 down changes are strictly below, the 50 equal up changes are not -> 50;
    #               at a down close (ROC -9.09%) nothing is strictly below -> 0
    #  up bar:   (200/3 + 200/3 + 50)/3 = (400/3 + 150/3)/3 = 550/9 = 61.11
    #  down bar: (100/3 + 100/3 + 0)/3  = 200/9 = 22.22
    crsi = R.connors_rsi(alternating(200)).to_numpy()
    assert crsi[199] == pytest.approx(550 / 9, abs=1e-6)
    assert crsi[198] == pytest.approx(200 / 9, abs=1e-6)


def test_value_is_50_until_bar_100_then_the_three_legs_apply():
    # 100 flat closes then one up close. Positions 0-99 -> the fixed 50 (they would otherwise be undefined).
    # Position 100: RSI_2(close) = 100 (no down move, an up move), RSI_2(streak) = 100 (streak 0 -> +1),
    # PercentRank: the 100 previous changes are all 0, all strictly below +10% -> 100.   CRSI = (100+100+100)/3 = 100
    up = R.connors_rsi([10.0] * 100 + [11.0]).to_numpy()
    assert (up[:100] == 50.0).all()
    assert up[100] == pytest.approx(100.0, abs=1e-9)
    # mirror: one down close -> RSI_2 legs 0 and 0, none of the previous changes is strictly below -10% -> rank 0 -> CRSI = 0
    down = R.connors_rsi([10.0] * 100 + [9.0]).to_numpy()
    assert (down[:100] == 50.0).all()
    assert down[100] == pytest.approx(0.0, abs=1e-9)


def test_percent_rank_counts_strictly_below_over_the_previous_100_values():
    x = np.concatenate([np.arange(100.0), [50.0]])      # previous 100 values are 0..99; 0..49 are strictly below 50
    pr = R.percent_rank(x, 100).to_numpy()
    assert np.isnan(pr[:100]).all()                     # needs 100 previous values
    assert pr[100] == 50.0                              # 50/100 * 100
    ties = R.percent_rank(np.full(101, 7.0), 100).to_numpy()
    assert ties[100] == 0.0                             # equal values are not strictly below


def test_monotone_series_hand_values():
    # Rising by 1 each bar: RSI_2(close) = 100, streak 1, 2, 3, ... rises by 1 each bar -> RSI_2(streak) = 100;
    # ROC = 1/(99 + t) keeps shrinking, so today's change is below every previous one: rank 0.  CRSI = 200/3 (t >= 101)
    up = R.connors_rsi(100.0 + np.arange(200)).to_numpy()
    assert up[101:] == pytest.approx(200 / 3, abs=1e-9)
    # Falling by 1 each bar: both RSI legs are 0 and ROC becomes more negative every bar: nothing is below it.  CRSI = 0
    down = R.connors_rsi(500.0 - np.arange(200)).to_numpy()
    assert down[101:] == pytest.approx(0.0, abs=1e-9)


def test_values_stay_inside_0_100():
    rs = np.random.RandomState(13)
    close = 1000.0 + np.cumsum(rs.normal(0, 4, 500))
    close[250] *= 1.2                                   # an outlier jump
    close[300:320] = close[300]                         # a flat stretch (unchanged closes)
    v = R.connors_rsi(close).to_numpy()
    assert np.isfinite(v).all() and (v >= 0).all() and (v <= 100).all()


def test_scale_invariance():
    close = np.concatenate([alternating(150), [12.0, 13.0, 12.5, 14.0]])
    base = R.connors_rsi(close).to_numpy()
    np.testing.assert_allclose(R.connors_rsi(close * 7.0).to_numpy(), base, atol=1e-9)
    # (a level shift is NOT an invariance: the percent rank uses percentage changes)


def test_falsifier_published_rsi3_and_non_strict_rank_are_rejected():
    """Two plausible miscodings, rejected by the alternating hand value 550/9 = 61.11:
    (1) Connors' published RSI(3) on price: steady state 60 after an up bar -> (60 + 200/3 + 50)/3 = 58.89;
    (2) a non-strict rank (<=): the 50 equal up changes also count -> rank 100 -> (200/3 + 200/3 + 100)/3 = 77.78."""
    c = alternating(200)
    roc = np.zeros(len(c))
    roc[1:] = (c[1:] - c[:-1]) / c[:-1]
    streak_rsi = R.rsi(R.streak(c).to_numpy(), 2).to_numpy()
    rank = R.percent_rank(roc, 100).to_numpy()
    rsi3 = (R.rsi(c, 3).to_numpy() + streak_rsi + rank) / 3.0
    assert abs(rsi3[199] - 550 / 9) > 1.0
    rank_le = 100.0 * np.count_nonzero(roc[99:199] <= roc[199]) / 100
    assert rank_le == 100.0
    non_strict = (R.rsi(c, 2)[199] + streak_rsi[199] + rank_le) / 3.0
    assert abs(non_strict - 550 / 9) > 1.0
    assert abs(R.connors_rsi(c).to_numpy()[199] - rsi3[199]) > 1.0


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["ConnorsRSI"]
    assert {"CRSI", "Streak"} <= set(c["series"])     # read by QS_*_ConnorsRSI and the harness
    assert c["lines"] == {"Lower Threshold": 15.0, "Upper Threshold": 85.0}
    assert c["defaults"]["LowerThreshold"] == "15" and c["defaults"]["UpperThreshold"] == "85"
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


def test_csharp_gates_legs_and_strict_rank():
    text = cs_contract(MODULE)["text"]
    assert "if (CurrentBar < 50)" in text                                     # ORIG module-wide gate
    assert re.search(r"double\s+crsiVal\s*=\s*50\s*;", text) and "if (CurrentBar >= 100)" in text
    assert re.search(r"rsi2\s*=\s*RSI\(Close,\s*2,\s*1\)", text)              # price leg is RSI(2), not Connors' RSI(3)
    assert re.search(r"rsiStreak\s*=\s*RSI\(streakSeries,\s*2,\s*1\)", text)
    assert "Math.Min(100, CurrentBar)" in text and "if (pRoc < tRoc) below++;" in text    # strictly below
    assert "consecUpDays > 0 ? consecUpDays : -consecDownDays" in text         # unchanged close keeps the counts
    assert re.search(r"\(rsiP\s*\+\s*rsiS\s*\+\s*pRank\)\s*/\s*3\.0", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "CRSI")
    # Gates in the C#: nothing before bar 50, 50 until bar 100, and the oldest percent-rank samples
    # degrade to 0 while i + 1 >= CurrentBar (bars 100 and 101, header quirk 2), so the full formula
    # applies from bar 102. The streak memory starts at bar 50 and agrees with the reference after the
    # first reversal, long before bar 102.
    start = 102
    if len(df) <= start:
        pytest.skip(f"export has {len(df)} bars; ConnorsRSI is compared from bar {start}")
    ref = R.connors_rsi(df["Close"].to_numpy(float)).to_numpy()
    assert_close(ref, got, start=start, tol=6e-5, label="ConnorsRSI.CRSI")


def test_streak_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "Streak")
    # The C# starts counting at bar 50 (comparing bar 50 with bar 49), so the reference is the streak of
    # the closes from bar 49 on, aligned to the export.
    close = df["Close"].to_numpy(float)
    ref = np.full(len(close), np.nan)
    ref[49:] = R.streak(close[49:]).to_numpy()
    ref[49] = np.nan
    assert_close(ref, got, start=50, tol=1e-9, label="ConnorsRSI.Streak")
