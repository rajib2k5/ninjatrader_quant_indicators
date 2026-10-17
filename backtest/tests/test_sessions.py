"""Session builder, D/15m resampling and loaders (PROTOCOL sections 2-3, ledger BT4/BT14)."""
from __future__ import annotations

import csv

import numpy as np
import pandas as pd
import pytest

from conftest import random_bars, session_close_times, weekday_dates
from qibt import data

TS = pd.Timestamp


def td(s):
    return data.trading_date(pd.Series([TS(s)])).iloc[0]


# --------------------------------------------------------------------------------------------
# trading date
# --------------------------------------------------------------------------------------------
def check_roll(fn):
    """Boundary cases of the 17:00 CT roll for a trading-date function; returns mismatches."""
    cases = [
        ("2024-03-05 16:59", "2024-03-05"), ("2024-03-05 16:00", "2024-03-05"),
        ("2024-03-05 17:00", "2024-03-05"),   # not AFTER 17:00 -> same date (and a halt bar)
        ("2024-03-05 17:01", "2024-03-06"), ("2024-03-05 23:59", "2024-03-06"),
        ("2024-03-06 00:00", "2024-03-06"), ("2024-03-10 17:01", "2024-03-11"),  # Sunday -> Monday
        ("2024-03-08 16:00", "2024-03-08"),   # Friday close
    ]
    return [(t, str(fn(pd.Series([TS(t)])).iloc[0].date()), want) for t, want in cases
            if fn(pd.Series([TS(t)])).iloc[0] != TS(want)]


def test_trading_date_roll_boundaries():
    assert check_roll(data.trading_date) == []


def test_sunday_1701_bar_opens_monday():
    d = td("2024-03-10 17:01")
    assert d == TS("2024-03-11") and d.dayofweek == 0


# --------------------------------------------------------------------------------------------
# halt (16:00, 17:00]
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("t", ["2024-03-05 16:01", "2024-03-05 16:30", "2024-03-05 17:00"])
def test_bar_inside_halt_is_rejected(t):
    m1 = random_bars(pd.DatetimeIndex([TS("2024-03-05 15:59"), TS(t), TS("2024-03-05 17:01")]))
    with pytest.raises(data.SessionError):
        data.add_sessions(m1)


def test_halt_edges_are_accepted():
    m1 = random_bars(pd.DatetimeIndex([TS("2024-03-05 16:00"), TS("2024-03-05 17:01")]))
    s = data.add_sessions(m1)
    assert list(s["TradingDate"]) == [TS("2024-03-05"), TS("2024-03-06")]


def _check_sessions(m1s, n_per_date=1380):
    """No trading date contains a bar in (16:00, 17:00]; each date runs 17:01 (previous calendar
    day) .. 16:00 with n_per_date bars."""
    tod = m1s["BarTime"] - m1s["BarTime"].dt.normalize()
    assert not ((tod > pd.Timedelta("16:00:00")) & (tod <= pd.Timedelta("17:00:00"))).any()
    for d, g in m1s.groupby("TradingDate"):
        assert len(g) == n_per_date, (d, len(g))
        assert g["BarTime"].iloc[0] == d - pd.Timedelta(days=1) + pd.Timedelta("17:01:00"), d
        assert g["BarTime"].iloc[-1] == d + pd.Timedelta("16:00:00"), d


def test_no_trading_date_contains_halt_bars_two_weeks():
    dates = weekday_dates("2024-01-08", "2024-01-19")
    m1s = data.add_sessions(random_bars(session_close_times(dates), seed=4))
    _check_sessions(m1s)
    assert list(pd.DatetimeIndex(m1s["TradingDate"].unique())) == list(dates)


# --------------------------------------------------------------------------------------------
# DST weeks: CME hours are fixed in CT, so a UTC-stamped vendor must be converted with the zone
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("week", [("2024-03-04", "2024-03-15"), ("2024-10-28", "2024-11-08"),
                                  ("2025-03-03", "2025-03-14"), ("2025-10-27", "2025-11-07")])
def test_dst_change_week_from_utc_source(week):
    """Two weeks around each change: sessions on both sides of the switch (CST and CDT)."""
    dates = weekday_dates(*week)
    local = session_close_times(dates)                    # naive CT wall clock
    utc = local.tz_localize(data.CENTRAL_TZ).tz_convert("UTC")
    back = data.to_central(pd.Series(utc.tz_localize(None)), source_tz="UTC")
    assert (back.to_numpy() == local.to_numpy()).all()
    m1s = data.add_sessions(random_bars(pd.DatetimeIndex(back), seed=5))
    _check_sessions(m1s)
    assert pd.DatetimeIndex(m1s["TradingDate"]).dayofweek.min() == 0


def test_dst_change_week_naive_central_unchanged():
    dates = weekday_dates("2024-03-11", "2024-03-15")   # DST began Sunday 2024-03-10 02:00 CT
    m1s = data.add_sessions(random_bars(session_close_times(dates), seed=6))
    _check_sessions(m1s)
    first = m1s.loc[m1s["TradingDate"] == TS("2024-03-11"), "BarTime"].iloc[0]
    assert first == TS("2024-03-10 17:01")


# --------------------------------------------------------------------------------------------
# D and 15m frames vs brute force
# --------------------------------------------------------------------------------------------
def _brute(m1s, key):
    out = {}
    for r in m1s.itertuples(index=False):
        k = key(r)
        if k not in out:
            out[k] = [r.Open, r.High, r.Low, r.Close, r.Volume, r.TradingDate]
        else:
            o = out[k]
            o[1] = max(o[1], r.High); o[2] = min(o[2], r.Low); o[3] = r.Close; o[4] += r.Volume
            assert o[5] == r.TradingDate, "bar spans trading dates"
    return out


def _sample_m1(seed=7):
    dates = weekday_dates("2024-03-07", "2024-03-13")
    t = session_close_times(dates)
    keep = np.random.default_rng(seed).random(len(t)) > 0.3          # holes inside sessions
    return data.add_sessions(random_bars(t[keep], seed=seed))


def check_daily(m1s, d):
    want = _brute(m1s, lambda r: r.TradingDate)
    got = {row.TradingDate: [row.Open, row.High, row.Low, row.Close, row.Volume] for row in d.itertuples()}
    return [k for k in want if want[k][:5] != got.get(k)] + [k for k in got if k not in want]


def check_15m(m1s, f):
    want = _brute(m1s, lambda r: r.BarTime.ceil("15min"))
    got = {row.BarTime: [row.Open, row.High, row.Low, row.Close, row.Volume, row.TradingDate] for row in f.itertuples()}
    return [k for k in want if want[k] != got.get(k)] + [k for k in got if k not in want]


def test_daily_frame_matches_brute_force():
    m1s = _sample_m1()
    d = data.daily_frame(m1s, close_mode="last")          # v1 close = last 1-minute close
    assert check_daily(m1s, d) == []
    assert d["TradingDate"].is_monotonic_increasing and d["TradingDate"].is_unique
    assert (d["Bars"].sum() == len(m1s))


def test_15m_frame_matches_brute_force_and_is_right_labelled():
    m1s = _sample_m1()
    f = data.resample_frame(m1s, 15)
    assert check_15m(m1s, f) == []
    lab = data.resample_frame(data.add_sessions(random_bars(pd.DatetimeIndex(
        [TS("2024-03-07 15:46"), TS("2024-03-07 16:00"), TS("2024-03-07 17:01"), TS("2024-03-07 17:15"),
         TS("2024-03-07 17:16")]))), 15)
    assert list(lab["BarTime"]) == [TS("2024-03-07 16:00"), TS("2024-03-07 17:15"), TS("2024-03-07 17:30")]
    assert list(lab["TradingDate"]) == [TS("2024-03-07"), TS("2024-03-08"), TS("2024-03-08")]
    assert list(lab["Bars"]) == [2, 2, 1]


def test_15m_bars_never_span_a_trading_date_with_odd_times():
    rng = np.random.default_rng(8)
    base = TS("2024-03-04")
    t = pd.DatetimeIndex(sorted(set(base + pd.to_timedelta(rng.integers(0, 3 * 86400, 3000), unit="s"))))
    m1s = data.add_sessions(random_bars(t, seed=8), halt=None)
    f = data.resample_frame(m1s, 15)
    lab = m1s["BarTime"].dt.ceil("15min")
    for (d, l), g in m1s.groupby([m1s["TradingDate"], lab]):
        assert g["TradingDate"].nunique() == 1
    assert f.groupby("BarTime")["TradingDate"].nunique().max() == 1


# --------------------------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------------------------
HEADER = ("Timestamp,BarTime,Symbol,Timeframe,SignalType,Direction,Description,Price,IBS,AlphaCount,"
          "HpScore,Confidence,SweptLevel,Patterns,Open,High,Low,Close,Volume,ATR14").split(",") + [
    "databox_" + n for n in [
        "HPScore", "IBS", "RSI2", "ConnorsRSI", "StochK", "RVZScore", "CompositeVol", "TurnOfMonth",
        "ConsecDays", "OvernightGap", "Bollinger", "TurnaroundTue", "RSI14", "VRPProxy", "WideRange",
        "VWAPDist", "MACDHist", "EMA2050", "SMA200", "ATRRegime", "VolSpike", "VolDelta", "VolDeltaSMA",
        "AlphaCount", "LiqSweep", "ChopIndex", "ChoppyFlag", "OFSignal", "OFDetail", "SMCSignal",
        "SMCDetail", "TotalBuys", "TotalSells"]]


def _bar_row(bt, o, h, l, c, v, shift=1, price=None):
    row = ["2026-02-22 13:31:43", bt, "MES", "1min", "", "", "", price or c] + [""] * 6 + [""] * shift
    row += [o, h, l, c, v, "0.47"] + ["%.4f" % (i / 10) for i in range(33)]
    return row


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(rows)


def test_everybar_reader_aligns_surplus_field(tmp_path):
    assert len(HEADER) == 53
    sig = ["2026-02-22 13:31:43", "2020-01-03 16:00:00", "MES", "1min", "OrderFlow+", "Sell", "x",
           "3864.75", "", "", "", "0.65", "", "Absorption", "3864.75", "3864.75", "3864.50", "3864.75", "55", "0.47"]
    rows = [sig, _bar_row("2020-01-03 16:00:00", "3864.75", "3865.00", "3864.50", "3864.75", "55"),
            _bar_row("2020-01-05 17:01:00", "3852.00", "3852.00", "3847.50", "3848.75", "1233")]
    assert len(rows[1]) == 54
    p = tmp_path / "MES_1min_test.csv"
    _write(p, rows)
    df, info = data.read_everybar(p, extra_cols=["databox_HPScore", "databox_TotalSells"])
    assert info["shift"] == 1 and info["signal_rows"] == 1 and info["bar_rows"] == 2
    assert df[["Open", "High", "Low", "Close", "Volume"]].iloc[0].tolist() == [3864.75, 3865.0, 3864.5, 3864.75, 55.0]
    assert df["BarTime"].iloc[1] == TS("2020-01-05 17:01")
    assert df["databox_HPScore"].tolist() == [0.0, 0.0] and df["databox_TotalSells"].tolist() == [3.2, 3.2]


def test_everybar_reader_aborts_on_misalignment(tmp_path):
    p = tmp_path / "bad.csv"
    _write(p, [_bar_row("2020-01-03 16:00:00", "1", "2", "0.5", "1.5", "5", price="9.99")])
    with pytest.raises(data.LayoutError):
        data.read_everybar(p)
    _write(p, [_bar_row("2020-01-03 16:00:00", "1", "2", "0.5", "1.5", "5", shift=1),
               _bar_row("2020-01-03 16:01:00", "1", "2", "0.5", "1.5", "5", shift=2)])
    with pytest.raises(data.LayoutError):
        data.read_everybar(p)


def test_combine_dedups_first_wins_and_sorts():
    a = random_bars(pd.DatetimeIndex([TS("2024-01-02 10:00"), TS("2024-01-02 10:01")]), seed=1)
    b = random_bars(pd.DatetimeIndex([TS("2024-01-02 09:59"), TS("2024-01-02 10:01")]), seed=2)
    df, ndup = data.combine_bars([a, b])
    assert ndup == 1 and df["BarTime"].is_monotonic_increasing
    assert df.loc[df["BarTime"] == TS("2024-01-02 10:01"), "Close"].item() == a["Close"].iloc[1]


def test_generic_ohlcv_loader(tmp_path):
    p = tmp_path / "es.csv"
    p.write_text("Date,Time,Open,High,Low,Close,Volume\n"
                 "2024-03-11,15:00:00,1,2,0.5,1.5,10\n"
                 "2024-03-11,14:00:00,1,2,0.5,1.25,10\n"
                 "2024-03-11,15:00:00,9,9,9,9,9\n", encoding="utf-8")
    df = data.load_ohlcv_csv(p)
    assert list(df["BarTime"]) == [TS("2024-03-11 14:00"), TS("2024-03-11 15:00")]
    assert df["Close"].tolist() == [1.25, 1.5] and df.attrs["info"]["duplicates_dropped"] == 1
    utc = data.load_ohlcv_csv(p, source_tz="UTC")          # 15:00 UTC = 10:00 CDT on 2024-03-11
    assert utc["BarTime"].iloc[1] == TS("2024-03-11 10:00")
    op = data.load_ohlcv_csv(p, label="open", bar_minutes=60)
    assert op["BarTime"].iloc[0] == TS("2024-03-11 15:00")


# --------------------------------------------------------------------------------------------
# falsifiers
# --------------------------------------------------------------------------------------------
def test_falsifier_shift_and_normalize_roll_is_detected():
    """(t + 7 h).normalize() (qi_ref.trading_day style) moves a 17:00:00 close to the next date."""
    def plus7(times):
        return (pd.Series(pd.to_datetime(times)) + pd.Timedelta(hours=7)).dt.normalize()
    assert check_roll(plus7) != []


def test_falsifier_fixed_utc_offset_is_detected():
    """Converting UTC with a fixed -6 h offset puts the CDT part of a DST week into the halt."""
    dates = weekday_dates("2024-03-11", "2024-03-15")
    utc = session_close_times(dates).tz_localize(data.CENTRAL_TZ).tz_convert("UTC").tz_localize(None)
    wrong = pd.DatetimeIndex(utc - pd.Timedelta(hours=6))
    with pytest.raises(data.SessionError):
        data.add_sessions(random_bars(wrong, seed=9))


def test_falsifier_left_labelled_resample_is_detected():
    m1s = _sample_m1()
    left = (m1s.set_index("BarTime")[["Open", "High", "Low", "Close", "Volume"]]
            .resample("15min").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last",
                                    "Volume": "sum"}).dropna().reset_index())
    left["TradingDate"] = data.trading_date(left["BarTime"]).to_numpy()
    assert check_15m(m1s, left) != []
