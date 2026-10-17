"""D-frame close modes of PROTOCOL amendment A1: settle (snap + fallbacks), 1500, last."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from conftest import random_bars, session_close_times, weekday_dates
from qibt import data
from test_sessions import HEADER, _bar_row, _write

TS = pd.Timestamp
IBS = data.IBS_ORIG_COL
DATES = weekday_dates("2024-03-04", "2024-03-11")      # 6 trading dates, hourly bars incl. 15:00


def _frames():
    """Six dates, one per branch (hand-set databox_IBS on each date's bars):
       0 on-grid          IBS rounded to 4 dp of an on-grid close   -> settle (snapped)
       1 off-grid         unsnapped value 0.10 off the grid          -> 15:00 close
       2 H == L           all bars at one price                      -> 15:00 close
       3 IBS missing      last bar empty, the bar before has a value -> 15:00 close (no stale value)
       4 off-grid, no 15:00 bar                                      -> last close
       5 on-grid,  no 15:00 bar                                      -> settle"""
    m1 = random_bars(session_close_times(DATES, step_minutes=60), seed=31, max_ticks=10)
    m1[IBS] = 0.5
    td = data.trading_date(m1["BarTime"])
    d2 = m1.index[td == DATES[2]]
    m1.loc[d2, ["Open", "High", "Low", "Close"]] = 4100.0
    no15 = m1.index[(td.isin([DATES[4], DATES[5]])) & ((m1["BarTime"] - m1["BarTime"].dt.normalize()) == pd.Timedelta("15:00:00"))]
    m1 = m1.drop(index=no15).reset_index(drop=True)
    td = data.trading_date(m1["BarTime"])
    g = m1.groupby(td)
    H, L = g["High"].max(), g["Low"].min()
    last_ix = m1.groupby(td).tail(1).index
    for i, d in enumerate(DATES):
        h, l = H[d], L[d]
        target = l + 0.25 * round((h - l) * 0.37 / 0.25)            # an on-grid price inside [L, H]
        on = round((target - l) / (h - l), 4) if h > l else 0.5
        off = (target + 0.10 - l) / (h - l) if h > l else 0.5
        val = {0: on, 1: off, 2: 0.5, 3: math.nan, 4: off, 5: on}[i]
        m1.loc[last_ix[i], IBS] = val
        if i == 3:
            m1.loc[last_ix[i] - 1, IBS] = on                         # a stale, on-grid earlier value
    targets = {d: L[d] + 0.25 * round((H[d] - L[d]) * 0.37 / 0.25) for d in DATES}
    return m1, targets


@pytest.fixture(scope="module")
def case():
    m1, targets = _frames()
    m1s = data.add_sessions(m1)
    c15 = {d: m1s.loc[(m1s["TradingDate"] == d) & (m1s["BarTime"] == d + pd.Timedelta("15:00:00")), "Close"]
           for d in DATES}
    c15 = {d: (float(v.iloc[0]) if len(v) else math.nan) for d, v in c15.items()}
    last = m1s.groupby("TradingDate")["Close"].last().to_dict()
    return m1s, targets, c15, last


def expected(case, mode):
    m1s, targets, c15, last = case
    if mode == "last":
        return [last[d] for d in DATES]
    if mode == "1500":
        return [c15[d] if not math.isnan(c15[d]) else last[d] for d in DATES]
    return [targets[DATES[0]], c15[DATES[1]], c15[DATES[2]], c15[DATES[3]], last[DATES[4]], targets[DATES[5]]]


def test_settle_branches(case):
    m1s = case[0]
    d = data.daily_frame(m1s, "settle")
    assert d["Close"].tolist() == expected(case, "settle")
    assert d["CloseSource"].tolist() == ["settle", "1500", "1500", "1500", "last", "settle"]
    assert d["CloseReason"].tolist() == ["", "off_grid", "h_eq_l", "ibs_missing", "off_grid", ""]
    rep = data.close_report(d)
    assert rep == {"dates": 6, "source": {"settle": 2, "1500": 3, "last": 1},
                   "fallback_reason": {"off_grid": 2, "h_eq_l": 1, "ibs_missing": 1}}


def test_1500_and_last_modes(case):
    m1s = case[0]
    d15 = data.daily_frame(m1s, "1500")
    assert d15["Close"].tolist() == expected(case, "1500")
    assert d15["CloseSource"].tolist() == ["1500", "1500", "1500", "1500", "last", "last"]
    dl = data.daily_frame(m1s, "last")
    assert dl["Close"].tolist() == expected(case, "last") and set(dl["CloseSource"]) == {"last"}


def test_only_the_close_changes(case):
    m1s = case[0]
    fr = {m: data.build_frames(m1s[["BarTime", "Open", "High", "Low", "Close", "Volume", IBS]], close_mode=m)
          for m in data.CLOSE_MODES}
    for m in ("settle", "1500"):
        for c in ("TradingDate", "BarTime", "Open", "High", "Low", "Volume", "Bars"):
            assert fr[m]["D"][c].equals(fr["last"]["D"][c]), (m, c)
        pd.testing.assert_frame_equal(fr[m]["15m"], fr["last"]["15m"])
    assert data.DEFAULT_CLOSE_MODE == "settle"
    with pytest.raises(ValueError):
        data.daily_frame(m1s, "settlement")


def test_settle_without_ibs_column_falls_back(case):
    m1s = case[0].drop(columns=[IBS])
    d = data.daily_frame(m1s, "settle")
    assert set(d["CloseReason"]) == {"ibs_missing"}
    assert d["Close"].tolist() == expected(case, "1500")


# A1.1: on-grid when |raw - snapped| <= 0.00005 * (H - L) + 1e-9 (4-decimal IBS rounding bound).
# Range 10 points -> bound 0.0005 points.
@pytest.mark.parametrize("ibs,want,why", [
    (0.325, 103.25, ""),          # exactly on the grid
    (0.32504, 103.25, ""),        # 0.0004 off <= 0.0005: rounding can explain it -> snapped
    (0.32506, None, "off_grid"),  # 0.0006 off > 0.0005
    (0.3255, None, "off_grid"),   # 0.005 off (the old fixed 0.01 rule would have snapped this)
    (0.337, None, "off_grid"),
    (0.0, 100.0, ""), (1.0, 110.0, ""),
    (math.nan, None, "ibs_missing"),
])
def test_snap_settle_hand_values(ibs, want, why):
    snapped, reason = data.snap_settle([100.0], [110.0], [ibs])
    assert reason[0] == why
    if want is not None:
        assert snapped[0] == want


def test_snap_settle_bound_scales_with_range():
    # Real P1 cases (validation/addenda.md ADD-9): 2020-03-12 range 332.5, dist 0.01625 <= 0.016625
    # -> on grid; 2025-03-31 range 138.75, dist 0.0080 > 0.0069375 -> off grid.
    lo = 6000.0
    wide_raw = 6100.25 + 0.01625
    _, r_wide = data.snap_settle([lo], [lo + 332.5], [(wide_raw - lo) / 332.5])
    narrow_raw = 6050.0 + 0.0080
    _, r_narrow = data.snap_settle([lo], [lo + 138.75], [(narrow_raw - lo) / 138.75])
    assert r_wide[0] == "" and r_narrow[0] == "off_grid"


def test_falsifier_fixed_tolerance_is_detected():
    """The superseded fixed 0.01-point rule disagrees with A1.1 on both real-world cases above."""
    def fixed(lo, hi, ibs):
        raw = lo + ibs * (hi - lo)
        return "off_grid" if abs(raw - round(raw / 0.25) * 0.25) > 0.01 else ""
    lo = 6000.0
    wide = fixed(lo, lo + 332.5, (6100.25 + 0.01625 - lo) / 332.5)
    narrow = fixed(lo, lo + 138.75, (6050.0 + 0.0080 - lo) / 138.75)
    _, r_wide = data.snap_settle([lo], [lo + 332.5], [(6100.25 + 0.01625 - lo) / 332.5])
    _, r_narrow = data.snap_settle([lo], [lo + 138.75], [(6050.0 + 0.0080 - lo) / 138.75])
    assert (wide, narrow) == ("off_grid", "") and (r_wide[0], r_narrow[0]) == ("", "off_grid")


def test_snap_settle_h_equal_l():
    _, reason = data.snap_settle([100.0], [100.0], [0.5])
    assert reason[0] == "h_eq_l"


def test_everybar_reader_extracts_databox_ibs(tmp_path):
    p = tmp_path / "MES_1min_x.csv"
    _write(p, [_bar_row("2020-01-03 16:00:00", "3864.75", "3865.00", "3864.50", "3864.75", "55")])
    df, _ = data.read_everybar(p, extra_cols=data.P1_EXTRA_COLS)
    assert data.P1_EXTRA_COLS == ("databox_IBS",) and HEADER[21] == "databox_IBS"
    assert df["databox_IBS"].tolist() == [0.1] and df["Close"].tolist() == [3864.75]


# --------------------------------------------------------------------------------------------
# falsifiers
# --------------------------------------------------------------------------------------------
def test_falsifier_nan_skipping_last_is_detected(case):
    """groupby().last() skips an empty last value and uses the stale earlier IBS (date 3)."""
    m1s = case[0]
    g = m1s.groupby("TradingDate")
    stale = g[IBS].last().to_numpy()
    snapped, reason = data.snap_settle(g["Low"].min(), g["High"].max(), stale)
    assert reason[3] == "" and data.daily_frame(m1s, "settle")["CloseReason"].iloc[3] == "ibs_missing"


def test_falsifier_no_grid_check_is_detected(case):
    m1s = case[0]
    g = m1s.groupby("TradingDate")
    raw = g["Low"].min() + m1s.groupby("TradingDate").tail(1).set_index("TradingDate")[IBS] * (g["High"].max() - g["Low"].min())
    always = (np.round(raw / 0.25) * 0.25).tolist()
    assert always[1] != expected(case, "settle")[1]


def test_falsifier_last_bar_at_or_before_1500_is_detected(case):
    """'Last bar with close time <= 15:00' differs from 'the bar ending 15:00, else last close'
    on a date without a 15:00 bar (date 4: it would take the 14:00 close)."""
    m1s = case[0]
    tod = m1s["BarTime"] - m1s["BarTime"].dt.normalize()
    sel = (tod <= pd.Timedelta("15:00:00")) & (m1s["BarTime"].dt.normalize() == m1s["TradingDate"])
    wrong = m1s.loc[sel].groupby("TradingDate")["Close"].last().reindex(DATES).tolist()
    assert wrong[4] != expected(case, "1500")[4]
