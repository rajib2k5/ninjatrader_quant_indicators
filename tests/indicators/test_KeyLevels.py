"""Unit tests for QI_<NN>_KeyLevels - previous-day RTH, monthly, 30-min ORB and Asian session levels.

Spec (QI_27_KeyLevels.cs; ORIG IBSFade UpdateKeyLevels and helpers), on the bar CLOSE time t in
US Central (cstTime == BarTime on this PC), all updates skipped while CurrentBar < 50:
  PrevDay  Sat/Sun skipped. A new calendar date rolls the finished RTH [08:30, 16:00) high/low into
           PrevDayHigh/Low (if that date had an RTH bar). Friday's RTH therefore becomes PrevDay* on
           Monday; Saturday/Sunday bars keep the levels unchanged.
  Monthly  Every bar (weekends too) extends the current calendar month's high/low; reset on a new month.
  ORB      Sat/Sun skipped. Reset at each new date; bars in [08:30, 09:00) set the range (live);
           frozen from the first bar with t >= 09:00.
  Asian    Sat/Sun skipped. Bars with t >= 17:00 belong to the NEXT date (reset there); bars with
           t >= 17:00 or t < 02:00 set the range; frozen from the first bar with 02:00 <= t < 17:00.
The eight read-only Series<double> expose the level after each bar's update, NaN while unknown
(the C# double.MinValue / MaxValue sentinels). Reference: backtest/qibt/patterns.py key_levels().
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from conftest import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)
from qibt import patterns as P

MODULE = "KeyLevels"
SERIES = ["PrevDayHigh", "PrevDayLow", "MonthlyHigh", "MonthlyLow",
          "OrbHigh", "OrbLow", "AsianHigh", "AsianLow"]
TOGGLES = ["ShowPrevDayLevels", "ShowMonthlyLevels", "ShowOrbLevels", "ShowAsianSessionLevels"]
PAD = 50            # `if (CurrentBar < 50) return;` - rows 0..49 never touch a level
NA = np.nan


# ---- hand-built bars -----------------------------------------------------------------------
def _pad():
    """50 one-minute bars Mon 2026-01-05 08:30..09:19 (inside RTH and the ORB window) with
    absurd prices High 9999 / Low 1: any of them leaking past the bar-50 gate shows up."""
    return bars(np.full(PAD, 5000.0), high=np.full(PAD, 9999.0), low=np.full(PAD, 1.0),
                start="2026-01-05 08:30", freq="1min")


def _at(rows):
    """rows = [(bar close time, High, Low), ...]; Open = Close = midpoint (unused by the module)."""
    times, hi, lo = zip(*rows)
    df = bars((np.asarray(hi, float) + np.asarray(lo, float)) / 2.0, high=hi, low=lo)
    df["BarTime"] = pd.to_datetime(list(times))
    return df


def levels(day):
    """key_levels of PAD gate bars followed by `day` (rows list or frame); the `day` part only."""
    day = day if isinstance(day, pd.DataFrame) else _at(day)
    df = pd.concat([_pad(), day], ignore_index=True)
    return P.key_levels(df).iloc[PAD:].reset_index(drop=True)


def _eq(got, want):
    np.testing.assert_array_equal(np.asarray(got, float), np.asarray(want, float))   # NaN == NaN


def _same(a, b):
    return np.array_equal(np.asarray(a, float), np.asarray(b, float), equal_nan=True)


# Tuesday RTH read on Wednesday (5-minute bars, sparse)
TUESDAY = [
    ("2026-01-06 06:00", 120, 80),   # 0 Tue overnight Globex: not RTH
    ("2026-01-06 08:25", 115, 95),   # 1 closes before 08:30: not RTH
    ("2026-01-06 08:30", 105, 100),  # 2 first RTH bar (08:30 inclusive)
    ("2026-01-06 12:00", 110, 99),   # 3 RTH
    ("2026-01-06 15:55", 108, 98),   # 4 last RTH bar
    ("2026-01-06 16:00", 130, 70),   # 5 closes at 16:00: not RTH (16:00 exclusive)
    ("2026-01-06 18:00", 125, 75),   # 6 evening session, still Tuesday's date: not RTH
    ("2026-01-07 00:05", 104, 101),  # 7 Wed: the new date rolls Tue RTH into PrevDay*
    ("2026-01-07 09:00", 104, 101),  # 8 Wed
]

# Thursday -> Monday across a weekend
WEEKEND = [
    ("2026-01-08 10:00", 200, 190),  # 0 Thu RTH
    ("2026-01-09 00:05", 199, 191),  # 1 Fri: Thu RTH -> PrevDay; Asian window (< 02:00)
    ("2026-01-09 08:45", 207, 206),  # 2 Fri RTH, ORB window
    ("2026-01-09 10:00", 210, 205),  # 3 Fri RTH
    ("2026-01-09 15:55", 212, 204),  # 4 Fri RTH  -> Fri RTH = 212 / 204
    ("2026-01-10 10:00", 300, 100),  # 5 SATURDAY inside 08:30-16:00: skipped by PrevDay/ORB/Asian
    ("2026-01-11 17:05", 220, 215),  # 6 SUNDAY evening Globex open: Sunday -> skipped as well
    ("2026-01-12 00:05", 218, 216),  # 7 Mon: new date rolls Fri RTH into PrevDay*
    ("2026-01-12 10:00", 219, 217),  # 8 Mon RTH
]

# one opening range (5-minute bars)
ORB_DAY = [
    ("2026-01-06 08:25", 101, 99),   # 0 closes before 08:30: outside the window
    ("2026-01-06 08:30", 102, 100),  # 1 08:30 inclusive
    ("2026-01-06 08:45", 104, 101),  # 2
    ("2026-01-06 08:55", 103, 98),   # 3 last window bar
    ("2026-01-06 09:00", 110, 90),   # 4 09:00 exclusive; completes the ORB
    ("2026-01-06 09:30", 111, 89),   # 5
    ("2026-01-06 15:00", 120, 80),   # 6
    ("2026-01-07 00:05", 100, 99),   # 7 Wed: new date resets
    ("2026-01-07 08:30", 97, 96),    # 8 Wed's first window bar
]

# Asian session Tue 17:00 -> Wed 02:00 (keyed to Wednesday)
ASIAN = [
    ("2026-01-06 10:00", 150, 140),  # 0 Tue day session: trading date Tue, outside the window
    ("2026-01-06 16:55", 151, 141),  # 1 before 17:00: still Tue, outside
    ("2026-01-06 17:05", 160, 150),  # 2 t >= 17:00: trading date Wed -> reset, in window
    ("2026-01-06 23:55", 165, 155),  # 3
    ("2026-01-07 00:05", 162, 145),  # 4 after midnight: still trading date Wed
    ("2026-01-07 01:55", 170, 148),  # 5 last window bar (t < 02:00)
    ("2026-01-07 02:00", 180, 140),  # 6 02:00 exclusive; completes the session
    ("2026-01-07 10:00", 190, 130),  # 7
    ("2026-01-07 17:05", 175, 172),  # 8 trading date Thu -> reset
]

# month end Thu Jan 29 -> Mon Feb 2
MONTH_END = [
    ("2026-01-29 10:00", 50, 40),    # 0 Thu
    ("2026-01-30 10:00", 55, 45),    # 1 Fri
    ("2026-01-31 10:00", 60, 35),    # 2 Sat (weekend bars count for the month)
    ("2026-02-01 17:05", 52, 48),    # 3 Sun, February: reset
    ("2026-02-02 10:00", 54, 49),    # 4 Mon
]


# ---- 1. formula --------------------------------------------------------------------------
def test_prev_day_is_tuesday_rth_read_on_wednesday():
    lv = levels(TUESDAY)
    # Tue rows 0..6: no earlier RTH session was processed (Monday is the gated pad) -> NaN.
    # RTH bars are rows 2, 3, 4 (08:30, 12:00, 15:55): high max(105, 110, 108) = 110,
    # low min(100, 99, 98) = 98. Rows 1 (08:25: 115/95), 5 (16:00: 130/70), 0 and 6 are outside.
    # The roll happens at Wednesday's first bar (row 7), not at 16:00 or 17:00 on Tuesday.
    _eq(lv["PrevDayHigh"], [NA, NA, NA, NA, NA, NA, NA, 110, 110])
    _eq(lv["PrevDayLow"], [NA, NA, NA, NA, NA, NA, NA, 98, 98])


def test_a_weekday_without_rth_bars_keeps_the_previous_levels():
    # Tue RTH as above, then a Wednesday with overnight bars only (e.g. a holiday or a data gap):
    # Thu 00:05 finds no started Wednesday RTH session, so PrevDay* stays Tuesday's 110/98.
    rows = TUESDAY[:8] + [("2026-01-07 06:00", 103, 102),   # 8 Wed, before 08:30
                          ("2026-01-08 00:05", 104, 101)]   # 9 Thu
    lv = levels(rows)
    _eq(lv["PrevDayHigh"], [NA] * 7 + [110, 110, 110])
    _eq(lv["PrevDayLow"], [NA] * 7 + [98, 98, 98])


def test_weekend_keeps_the_levels_and_monday_reads_friday():
    lv = levels(WEEKEND)
    # row 0 Thu: NaN.  rows 1..4 Fri: Thu RTH 200/190.  row 5 Sat and row 6 Sun are skipped, so
    # the levels stay at Thursday's (Fri's RTH is still "today" until a weekday date change).
    # row 7 Mon 00:05: Fri RTH = max(207, 210, 212) / min(206, 205, 204) = 212 / 204.
    _eq(lv["PrevDayHigh"], [NA, 200, 200, 200, 200, 200, 200, 212, 212])
    _eq(lv["PrevDayLow"], [NA, 190, 190, 190, 190, 190, 190, 204, 204])
    # ORB: Fri 08:45 bar = 207/206, frozen from Fri 10:00, persists through Sat/Sun, reset by
    # Monday's first bar (00:05) and NaN on Monday (no Monday bar in 08:30-09:00).
    _eq(lv["OrbHigh"], [NA, NA, 207, 207, 207, 207, 207, NA, NA])
    _eq(lv["OrbLow"], [NA, NA, 206, 206, 206, 206, 206, NA, NA])
    # Asian: Fri session = the Fri 00:05 bar (199/191), frozen from Fri 08:45. The Sunday 17:05
    # bar would be Monday's Asian session but Sunday is skipped, so Monday's session is the
    # Mon 00:05 bar alone (218/216).
    _eq(lv["AsianHigh"], [NA, 199, 199, 199, 199, 199, 199, 218, 218])
    _eq(lv["AsianLow"], [NA, 191, 191, 191, 191, 191, 191, 216, 216])
    # Monthly: no weekend skip - the Saturday bar (300/100) becomes January's high/low.
    _eq(lv["MonthlyHigh"], [200, 200, 207, 210, 212, 300, 300, 300, 300])
    _eq(lv["MonthlyLow"], [190, 190, 190, 190, 190, 100, 100, 100, 100])


def test_orb_is_the_0830_0900_range_and_frozen_after_0900():
    lv = levels(ORB_DAY)
    # row 0 (08:25) is outside -> NaN. rows 1..3: 102/100 -> 104/100 -> 104/98.
    # row 4 (09:00, 110/90) is outside the window and completes the ORB; 09:30 and 15:00 bars
    # (111/89, 120/80) do not move it. Wed 00:05 resets (NaN); Wed 08:30 starts 97/96.
    _eq(lv["OrbHigh"], [NA, 102, 104, 104, 104, 104, 104, NA, 97])
    _eq(lv["OrbLow"], [NA, 100, 100, 98, 98, 98, 98, NA, 96])


def test_orb_on_contiguous_one_minute_bars():
    k = np.arange(41)                                  # closes 08:25, 08:26, ..., 09:05
    hi, lo = 100.0 + k, 90.0 - k                       # each bar widens both ends
    day = bars((hi + lo) / 2.0, high=hi, low=lo, start="2026-01-06 08:25", freq="1min")
    lv = levels(day)
    # window [08:30, 09:00) on the close time = rows 5 (08:30) .. 34 (08:59): high 100+k,
    # low 90-k; rows 0..4 (08:25..08:29) NaN; rows 35..40 (09:00..09:05) frozen at row 34 = 134/56.
    _eq(lv["OrbHigh"], [NA] * 5 + list(range(105, 135)) + [134] * 6)
    _eq(lv["OrbLow"], [NA] * 5 + list(range(85, 55, -1)) + [56] * 6)


def test_asian_session_spans_midnight_and_belongs_to_the_next_date():
    lv = levels(ASIAN)
    # rows 0, 1 (Tue 10:00, 16:55): trading date Tue, outside the window -> NaN.
    # Tue 17:05 starts Wednesday's session: 160/150 -> 23:55 165/150 -> Wed 00:05 165/145 (no reset
    # at midnight: same trading date) -> 01:55 170/145. Wed 02:00 (180/140) is outside and
    # completes it; Wed 10:00 does not move it; Wed 17:05 starts Thursday's session: 175/172.
    _eq(lv["AsianHigh"], [NA, NA, 160, 165, 165, 170, 170, 170, 175])
    _eq(lv["AsianLow"], [NA, NA, 150, 150, 145, 145, 145, 145, 172])


def test_month_rollover_resets_the_monthly_levels():
    lv = levels(MONTH_END)
    # Jan: 50/40 -> 55/40 -> Sat 60/35.  Sun Feb 1 17:05: new month -> 52/48 -> Mon 54/48.
    # (The January pad bars at 9999/1 are before bar 50 and never counted.)
    _eq(lv["MonthlyHigh"], [50, 55, 60, 52, 54])
    _eq(lv["MonthlyLow"], [40, 40, 35, 48, 48])


def test_bar_50_gate():
    df = pd.concat([_pad(), _at([("2026-01-05 09:30", 101, 99),       # bar 50, Monday
                                 ("2026-01-06 00:05", 100, 100)])],   # bar 51, Tuesday
                   ignore_index=True)
    lv = P.key_levels(df)
    assert lv.iloc[:PAD].isna().all().all()            # nothing is known before bar 50
    # bar 50 is the first bar seen: month 101/99 (the pad's 9999/1 never counted), ORB NaN (09:30
    # is outside the window and the pad's 08:30-09:19 bars are gated), Monday RTH = 101/99.
    # bar 51 (Tue 00:05) rolls Monday RTH -> PrevDay 101/99; Asian window bar -> 100/100.
    _eq(lv["MonthlyHigh"].iloc[PAD:], [101, 101])
    _eq(lv["MonthlyLow"].iloc[PAD:], [99, 99])
    _eq(lv["OrbHigh"].iloc[PAD:], [NA, NA])
    _eq(lv["PrevDayHigh"].iloc[PAD:], [NA, 101])
    _eq(lv["PrevDayLow"].iloc[PAD:], [NA, 99])
    _eq(lv["AsianHigh"].iloc[PAD:], [NA, 100])
    assert P.key_levels(_pad()).isna().all().all()     # exactly 50 bars: all NaN


def test_toggle_off_leaves_that_level_unknown():
    df = pd.concat([_pad(), _at(WEEKEND)], ignore_index=True)
    on = P.key_levels(df)
    off = P.key_levels(df, show_orb_levels=False, show_asian_session_levels=False)
    assert off[["OrbHigh", "OrbLow", "AsianHigh", "AsianLow"]].isna().all().all()
    pd.testing.assert_frame_equal(off[SERIES[:4]], on[SERIES[:4]])   # the others are unaffected


def test_falsifier_orb_window_ending_0930_is_detected():
    """A 08:30-09:30 ORB would also take ORB_DAY's 09:00 bar (110/90) from row 4 on."""
    variant_high = [NA, 102, 104, 104, 110, 110, 110, NA, 97]
    variant_low = [NA, 100, 100, 98, 90, 90, 90, NA, 96]
    lv = levels(ORB_DAY)
    assert not _same(lv["OrbHigh"], variant_high) and not _same(lv["OrbLow"], variant_low)
    assert lv["OrbHigh"][4] == 104 and lv["OrbLow"][4] == 98


def test_falsifier_rth_ending_1515_is_detected():
    """An RTH ending at 15:15 (the old equity-index close) would drop TUESDAY's 15:55 bar (low 98),
    giving PrevDayLow 99 on Wednesday."""
    variant_low = [NA, NA, NA, NA, NA, NA, NA, 99, 99]
    lv = levels(TUESDAY)
    assert not _same(lv["PrevDayLow"], variant_low)
    assert lv["PrevDayLow"][7] == 98


def test_falsifier_asian_keyed_to_same_calendar_date_is_detected():
    """Keyed to the bar's own date, the session would reset at midnight (Wed 00:05 -> 162/145) and
    Wed 17:05 would still belong to the completed Wednesday session (170/145)."""
    variant_high = [NA, NA, 160, 165, 162, 170, 170, 170, 170]
    variant_low = [NA, NA, 150, 150, 145, 145, 145, 145, 145]
    lv = levels(ASIAN)
    assert not _same(lv["AsianHigh"], variant_high) and not _same(lv["AsianLow"], variant_low)
    assert (lv["AsianHigh"][4], lv["AsianHigh"][8]) == (165, 175)


def test_falsifier_no_weekend_skip_is_detected():
    """Without the Sat/Sun skip the Saturday bar becomes a trading day: Sunday and Monday would read
    PrevDay 300/100 (Saturday's 'RTH') instead of Thursday's / Friday's levels."""
    variant_high = [NA, 200, 200, 200, 200, 212, 300, 300, 300]
    lv = levels(WEEKEND)
    assert not _same(lv["PrevDayHigh"], variant_high)
    assert lv["PrevDayHigh"][7] == 212


def test_falsifier_missing_bar_50_gate_is_detected():
    """Without the gate the pad's 9999/1 bars would be January's high/low and Monday's ORB."""
    lv = levels(MONTH_END)
    assert not _same(lv["MonthlyHigh"], [9999] * 5) and lv["MonthlyHigh"].max() == 60


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # price-panel overlay
    assert c["plots"] == [] and "AddPlot(" not in c["text"]   # levels are drawn, never plotted
    assert c["lines"] == {}
    assert c["series"] == SERIES                      # the harness columns, in this order
    for s in SERIES:                                  # read-only, hidden, not serialised
        assert re.search(r"\[Browsable\(false\)\]\s*\[XmlIgnore\]\s*public\s+Series<double>\s+%s\s*\{\s*get\s*\{"
                         % s, c["text"]), s
    for tg in TOGGLES:
        assert c["defaults"][tg] == "true", tg
    assert c["defaults"]["ShowDisclaimer"] == "false"
    assert list(P.KEY_LEVEL_COLUMNS) == SERIES


def test_csharp_windows_match_the_reference():
    """The boundaries key_levels() ports; a change in the C# makes the reference stale."""
    t = " ".join(cs_contract(MODULE)["text"].split())
    assert "if (CurrentBar < 50) { WriteLevelSeries();" in t          # NaN before bar 50
    assert "UpdateKeyLevels(); WriteLevelSeries();" in t              # written after the update
    assert "t >= new TimeSpan(8, 30, 0) && t < new TimeSpan(16, 0, 0)" in t     # RTH
    assert "t >= new TimeSpan(8, 30, 0) && t < new TimeSpan(9, 0, 0)" in t      # ORB window
    assert "t >= new TimeSpan(9, 0, 0) && orbHigh > double.MinValue" in t        # ORB complete
    assert "cstTime.TimeOfDay >= new TimeSpan(17, 0, 0) ? cstTime.Date.AddDays(1) : cstTime.Date" in t
    assert "t >= new TimeSpan(17, 0, 0) || t < new TimeSpan(2, 0, 0)" in t      # Asian window
    assert "t >= new TimeSpan(2, 0, 0) && t < new TimeSpan(17, 0, 0) && asianHigh > double.MinValue" in t
    assert t.count("cstTime.DayOfWeek == DayOfWeek.Saturday") == 3    # PrevDay, ORB, Asian - not Monthly


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    # Row r must be CurrentBar r: the reference replays the bar-50 gate and all state from bar 0.
    if "Bar" in df.columns:
        assert df["Bar"].tolist() == list(range(len(df))), "export rows are not bars 0..n-1"
    # BarTime is in the chart's time zone (this PC: US Central incl. DST), so the C#
    # ConvertTime(..., "Central Standard Time") is the identity and BarTime is used directly.
    ref = P.key_levels(df[["BarTime", "Open", "High", "Low", "Close", "Volume"]])
    for name in SERIES:
        got = harness_col(df, MODULE, name).to_numpy(float)
        r = ref[name].to_numpy(float)
        # unknown (NaN) on exactly the same bars ...
        diff = np.flatnonzero(np.isnan(r[PAD:]) != np.isnan(got[PAD:]))
        assert diff.size == 0, f"KeyLevels.{name}: NaN pattern differs on {diff.size} bars; first at {diff[0] + PAD}"
        # ... and equal to the export's 4 decimals where known. (On 60-minute bars no bar closes
        # inside [08:30, 09:00), so the ORB legitimately stays NaN on every bar.)
        if (~np.isnan(r[PAD:])).any():
            assert_close(r, got, start=PAD, tol=6e-5, label=f"KeyLevels.{name}")
