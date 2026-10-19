"""Unit tests for QI_<NN>_TurnOfMonth - turn-of-month calendar window flag.

Spec (ledger M7, ORIG IBSFade.cs 370, 1332-1340, rules.yaml TurnOfMonth):
  with dom = day of month and dim = days in the month (US Central date of the bar):
      flag = 1 if dom >= dim - 3 or dom <= 3, else 0
  i.e. the last 4 and the first 3 CALENDAR days of every month (not the trading-day window of
  Lakonishok & Smidt / Hensel & Ziemba - a deviation documented in the C# header).
  There is no warm-up: the C# writes from bar 0. Rule: long x == 1, short never. Overlay, no reference lines.
The reference takes bar times that are already US Central (the C# converts from the platform zone).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

import qi_ref as R
from qi_helpers import (REPO, assert_close, assert_names, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "TurnOfMonth"

# (date, flag) - derived by hand from dom >= dim - 3 or dom <= 3
CASES = [
    ("2026-01-01", 1), ("2026-01-03", 1), ("2026-01-04", 0), ("2026-01-15", 0),     # 31-day month: window days 28..31
    ("2026-01-27", 0), ("2026-01-28", 1), ("2026-01-31", 1),
    ("2026-04-03", 1), ("2026-04-04", 0), ("2026-04-26", 0), ("2026-04-27", 1),     # 30-day month: window days 27..30
    ("2026-04-30", 1),
    ("2026-02-24", 0), ("2026-02-25", 1), ("2026-02-28", 1),                         # Feb 2026, 28 days: window 25..28
    ("2024-02-25", 0), ("2024-02-26", 1), ("2024-02-29", 1),                         # leap Feb, 29 days: window 26..29
    ("2000-02-25", 0), ("2000-02-26", 1),                                            # 2000 is a leap year (divisible by 400)
    ("2100-02-24", 0), ("2100-02-25", 1),                                            # 2100 is not (28 days: window 25..28)
]


def flags(dates):
    return R.turn_of_month(pd.Series(pd.to_datetime(list(dates)))).to_numpy()


# ---- 1. formula --------------------------------------------------------------------------
@pytest.mark.parametrize("date, expected", CASES)
def test_calendar_window_hand_values(date, expected):
    assert flags([date])[0] == expected


def test_exactly_seven_days_are_flagged_in_every_month():
    # last 4 + first 3 = 7 days per month, 12 * 7 = 84 per year (leap or not)
    for year in (2026, 2024):
        days = pd.Series(pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D"))
        f = R.turn_of_month(days)
        per_month = f.groupby(days.dt.month.to_numpy()).sum()
        assert (per_month == 7).all()
        assert f.sum() == 84


def test_clock_time_does_not_matter_only_the_date():
    t = pd.Series(pd.date_range("2026-01-27 00:00", "2026-01-28 23:55", freq="5min"))
    f = R.turn_of_month(t).to_numpy()
    on_27 = (t.dt.day == 27).to_numpy()
    assert (f[on_27] == 0.0).all() and (f[~on_27] == 1.0).all()      # 27th: never; 28th: all day (midnight to 23:55)


def test_output_is_a_zero_one_float_flag():
    f = R.turn_of_month(pd.Series(pd.date_range("2026-01-01", "2026-12-31", freq="D")))
    assert f.dtype == float
    assert set(np.unique(f.to_numpy())) == {0.0, 1.0}


def test_window_is_the_same_every_year_for_the_same_month_length():
    # Feb 2026 and Feb 2027 both have 28 days: same flags day by day
    a = flags(pd.date_range("2026-02-01", "2026-02-28"))
    b = flags(pd.date_range("2027-02-01", "2027-02-28"))
    np.testing.assert_array_equal(a, b)
    # hand pattern: days 1-3 -> 1, days 4-24 -> 0, days 25-28 -> 1
    np.testing.assert_array_equal(a, [1] * 3 + [0] * 21 + [1] * 4)


def test_falsifier_other_windows_are_rejected_by_the_hand_table():
    """Plausible wrong windows, each disagreeing with CASES somewhere:
    last 3 days instead of 4 (Jan 28 -> 0), first 4 days instead of 3 (Jan 4 -> 1), a fixed 30-day month
    (Jan 27 -> 1, Feb 25 -> 0), and the literature's trading-day window for Jan/Feb 2026
    (last trading day Fri Jan 30 + first three trading days Feb 2, 3, 4 -> Jan 28 -> 0, Jan 31 -> 0)."""
    dates = pd.Series(pd.to_datetime([d for d, _ in CASES]))
    expected = np.array([e for _, e in CASES], dtype=float)
    day, dim = dates.dt.day, dates.dt.days_in_month
    variants = {
        "last 3": ((day >= dim - 2) | (day <= 3)),
        "first 4": ((day >= dim - 3) | (day <= 4)),
        "30-day month": ((day >= 27) | (day <= 3)),
    }
    for name, v in variants.items():
        assert (v.to_numpy().astype(float) != expected).any(), name
    trading = {"2026-01-30", "2026-02-02", "2026-02-03", "2026-02-04"}
    jan28, jan31 = "2026-01-28", "2026-01-31"
    assert jan28 not in trading and jan31 not in trading                       # trading-day window says 0 ...
    assert flags([jan28])[0] == 1.0 and flags([jan31])[0] == 1.0               # ... the calendar window (the spec here) says 1


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # shades window bars on the price chart; no sub-panel
    assert c["plots"] == ["Turn-of-Month"]            # transparent, DataBox only (1 = in window)
    assert "TurnOfMonth" in c["series"]               # read by QS_*_TurnOfMonth and the harness
    assert c["lines"] == {}                           # overlay: no reference lines
    assert "LowerThreshold" not in c["defaults"] and "UpperThreshold" not in c["defaults"]
    assert c["defaults"]["ShadeWindow"] == "true" and c["defaults"]["ShowDisclaimer"] == "false"


def test_overlay_and_rule_match_readme_and_rules_yaml():
    c = cs_contract(MODULE)
    rule = next(l for l in (REPO / "backtest" / "rules.yaml").read_text(encoding="utf-8").splitlines()
                if f"module: {MODULE}," in l)
    assert 'long: "x == 1"' in rule and 'short: "never"' in rule and "value: turn_of_month" in rule
    row = next(l for l in (REPO / "README.md").read_text(encoding="utf-8").splitlines()
               if l.startswith(f"| `{c['class']}` |")).split("|")
    assert row[4].strip() == "Overlay"


def test_csharp_window_zone_and_no_gate():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"bool\s+tom\s*=\s*dom\s*>=\s*\(dim\s*-\s*3\)\s*\|\|\s*dom\s*<=\s*3\s*;", text)
    assert re.search(r"int\s+dim\s*=\s*DateTime\.DaysInMonth\(cstT\.Year,\s*cstT\.Month\)", text)
    assert '"Central Standard Time"' in text and "TimeZoneInfo.ConvertTime(Time[0]," in text
    body = text[text.index("protected override void OnBarUpdate"):].split("DrawDisclaimerOnce();")[0]
    assert "CurrentBar" not in body                    # plots from bar 0


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "TurnOfMonth")
    # No CurrentBar gate. The export's BarTime is platform time; the C# converts it to US Central and the
    # reference expects Central times (ledger: chart-local = US Central), so this assumes a Central platform zone.
    ref = R.turn_of_month(pd.to_datetime(df["BarTime"])).to_numpy()
    assert_close(ref, got, start=0, tol=1e-9, label="TurnOfMonth.TurnOfMonth")
