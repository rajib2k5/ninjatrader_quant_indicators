"""Unit tests for QI_<NN>_TurnaroundTuesday - day of week of the bar in US Central time, 0 = Sunday .. 6 = Saturday.

Spec (ledger M11; ORIG IBSFade.cs 370, 1333-1334, 1362-1366; README "Indicators"):
  value = (int) cstTime.DayOfWeek, where cstTime = the bar time (chart-local = US Central) -> the .NET numbering
          Sunday 0, Monday 1, Tuesday 2, Wednesday 3, Thursday 4, Friday 5, Saturday 6.
  It is the CALENDAR date of the bar time that counts (no 17:00 trading-day roll). No warm-up: plots from bar 0.
  Monday bars are shaded (ShadeMonday); rules.yaml: long when x == 1 (Monday), never short.
Reference: qi_ref.day_of_week(times, sunday_zero=True) (ISO numbering Monday = 0 with sunday_zero=False).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import qi_ref as R
from qi_helpers import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "TurnaroundTuesday"


def _dow(stamps):
    return R.day_of_week(pd.Series(pd.to_datetime(stamps))).tolist()


# ---- 1. formula --------------------------------------------------------------------------
def test_weekday_numbering_hand_values():
    # 2026-01-01 was a Thursday, so 2026-01-04 is a Sunday and 2026-01-05 a Monday.
    df = bars(np.arange(9.0) + 100.0, start="2026-01-04 15:00", freq="1D")
    # Sun Mon Tue Wed Thu Fri Sat Sun Mon
    #  0   1   2   3   4   5   6   0   1
    assert R.day_of_week(df["BarTime"]).tolist() == [0, 1, 2, 3, 4, 5, 6, 0, 1]


def test_known_calendar_dates_across_month_and_year_boundaries():
    stamps = ["2000-01-01 12:00",   # Saturday
              "2024-02-29 12:00",   # Thursday (leap day)
              "2024-03-01 12:00",   # Friday
              "2025-12-31 12:00",   # Wednesday
              "2026-01-01 12:00"]   # Thursday
    assert _dow(stamps) == [6, 4, 5, 3, 4]


def test_only_the_calendar_date_of_the_bar_time_counts():
    stamps = ["2026-01-04 17:30",   # Sunday evening: the Globex session for Monday, but the calendar day is Sunday -> 0
              "2026-01-05 00:00",   # midnight starts Monday -> 1
              "2026-01-05 23:59",   # still Monday -> 1
              "2026-01-06 00:00",   # Tuesday -> 2
              "2026-01-06 17:05"]   # Tuesday evening -> 2 (no 17:00 trading-day roll)
    assert _dow(stamps) == [0, 1, 1, 2, 2]


def test_range_is_0_to_6_and_the_sequence_repeats_every_seven_days():
    df = bars(np.ones(70), start="2026-01-05 15:00", freq="1D")
    v = R.day_of_week(df["BarTime"]).to_numpy()
    assert set(v.tolist()) == {0, 1, 2, 3, 4, 5, 6}
    assert (v[7:] == v[:-7]).all()                       # period 7
    for k in range(0, 70, 7):                            # every aligned week holds each weekday exactly once
        assert sorted(v[k:k + 7].tolist()) == [0, 1, 2, 3, 4, 5, 6]


def test_monday_is_exactly_one_day_in_seven():
    # The rule and the shading both key on x == 1.
    df = bars(np.ones(28), start="2026-01-05 15:00", freq="1D")     # starts on a Monday
    monday = (R.day_of_week(df["BarTime"]) == 1).to_numpy()
    assert monday.sum() == 4
    assert np.flatnonzero(monday).tolist() == [0, 7, 14, 21]


def test_falsifier_iso_weekday_numbering_is_detected():
    """pandas / ISO numbering (Monday = 0) is the plausible slip. For the Sunday..Monday week of the first hand case it
    gives [6, 0, 1, 2, 3, 4, 5, 6, 0] - different on every bar, so the hand-value test cannot pass with it."""
    df = bars(np.arange(9.0) + 100.0, start="2026-01-04 15:00", freq="1D")
    iso_variant = [6, 0, 1, 2, 3, 4, 5, 6, 0]
    assert R.day_of_week(df["BarTime"]).tolist() != iso_variant
    assert all(a != b for a, b in zip(R.day_of_week(df["BarTime"]).tolist(), iso_variant))


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # shades Monday on the price chart, no sub-panel
    assert c["plots"] == ["Day of Week"]              # transparent, DataBox only
    assert c["series"] == ["DayOfWeekValue"]          # read by QS_*_TurnaroundTuesday and the harness
    assert c["lines"] == {}
    assert c["defaults"]["ShadeMonday"] == "true"
    assert c["defaults"]["ShowDisclaimer"] == "false"
    assert c["defaults"]["ShowTransparentPlotsInDataBox"] == "true"


def test_csharp_value_is_the_dotnet_day_of_week_of_the_central_time_with_no_warmup():
    text = cs_contract(MODULE)["text"]
    assert "int dow = (int)cstT.DayOfWeek;" in text
    assert "Values[0][0] = dow;" in text
    assert "TimeZoneInfo.FindSystemTimeZoneById(\"Central Standard Time\")" in text
    assert "cstT.DayOfWeek == DayOfWeek.Monday" in text
    assert "if (CurrentBar <" not in text             # plots from bar 0


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "DayOfWeekValue")
    # No C# warm-up gate: compare from bar 0. Integer flag -> 1e-9.
    ref = R.day_of_week(pd.to_datetime(df["BarTime"]))
    assert_close(ref, got, start=0, tol=1e-9, label="TurnaroundTuesday.DayOfWeekValue")
