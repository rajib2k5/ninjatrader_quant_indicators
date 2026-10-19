"""PROTOCOL A3 robustness datasets (qibt/robustness.py) on SYNTHETIC Stooq-format fixtures only."""
from __future__ import annotations

import hashlib
import math

import numpy as np
import pandas as pd
import pytest

from qibt import cli, engine, robustness as rb, signals

TS = pd.Timestamp


def write_stooq(path, dates, o, h, l, c, v=None, extra=False, header=None):
    v = np.zeros(len(dates)) if v is None else v
    cols = header or ["Date", "Open", "High", "Low", "Close", "Volume"]
    rows = {"Date": [d.strftime("%Y-%m-%d") for d in dates], "Open": o, "High": h, "Low": l, "Close": c, "Volume": v}
    df = pd.DataFrame({k: rows[k] for k in cols})
    if extra:
        df["OpenInt"] = 7
    df.to_csv(path, index=False)
    return path


def walk(dates, seed=0, start=1500.0, step=8.0, gap=1.0, quiet_gaps=False):
    """Daily bars on the 0.25 grid with small overnight gaps (|O_t - C_{t-1}| ~ gap);
    quiet_gaps: deterministic gaps -0.25, 0, +0.25 (median |gap| 0.25, so only planted gaps count)."""
    rng = np.random.default_rng(seed)
    n = len(dates)
    c = np.round((start + np.cumsum(rng.normal(0, step, n))) * 4) / 4
    g = (np.arange(n) % 3 - 1) * 0.25 if quiet_gaps else np.round(rng.normal(0, gap, n) * 4) / 4
    o = np.concatenate([[start], c[:-1]]) + g
    h = np.maximum(o, c) + 1.0
    l = np.minimum(o, c) - 1.0
    return o, h, l, c


# --------------------------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------------------------
def test_header_parsed_by_name_with_extra_column_and_reordered(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("Volume,Close,Date,High,Low,Open,OpenInt\n"
                 "10,101.5,2024-01-03,102,100,100.5,1\n"
                 "11,100.25,2024-01-02,101,99,100,1\n"
                 "12,999,2024-01-02,999,999,999,1\n"
                 "13,,2024-01-04,1,1,1,1\n", encoding="utf-8")
    bars, info = rb.read_stooq(p)
    assert list(bars["Date"]) == [TS("2024-01-02"), TS("2024-01-03")]
    assert bars.loc[0, ["Open", "High", "Low", "Close", "Volume"]].tolist() == [100.0, 101.0, 99.0, 100.25, 11.0]
    assert info["duplicates_dropped"] == 1 and info["rows_dropped_nan"] == 1 and info["data_rows"] == 4
    assert info["extra_columns"] == ["OpenInt"]


def test_standard_stooq_header(tmp_path):
    dates = pd.bdate_range("2024-01-02", periods=5)
    o, h, l, c = walk(dates)
    bars, info = rb.read_stooq(write_stooq(tmp_path / "s.csv", dates, o, h, l, c, v=np.arange(5.0)))
    assert list(bars.columns) == ["Date", "Open", "High", "Low", "Close", "Volume"]
    assert np.array_equal(bars["Close"].to_numpy(), c) and bars["Volume"].tolist() == [0, 1, 2, 3, 4]


@pytest.mark.parametrize("text", [
    "<!DOCTYPE html><html><head><title>stooq</title></head><body>checking your browser</body></html>",
    "﻿  \n<html><script>bot check</script></html>",
    "<HTML>",
])
def test_html_page_is_rejected(tmp_path, text):
    p = tmp_path / "spy_us_d.csv"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(rb.StooqFormatError, match="HTML"):
        rb.read_stooq(p)


@pytest.mark.parametrize("text,match", [("No data\n", "lacks"), ("", "empty"),
                                        ("Date,Open,High,Low,Close,Volume\n2024/01/02,1,1,1,1,0\n", "YYYY-MM-DD")])
def test_other_bad_files_are_rejected(tmp_path, text, match):
    p = tmp_path / "x.csv"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(rb.StooqFormatError, match=match):
        rb.read_stooq(p)


def test_r1_ohlc_times_10_volume_as_is(tmp_path):
    dates = pd.bdate_range("2024-01-02", periods=4)
    o, h, l, c = walk(dates, start=480.0, step=2.0)
    v = np.array([1e6, 2e6, 3e6, 4e6])
    d, info = rb.load_r1(write_stooq(tmp_path / "spy_us_d.csv", dates, o, h, l, c, v))
    for col, x in zip(("Open", "High", "Low", "Close"), (o, h, l, c)):
        assert np.array_equal(d[col].to_numpy(), x * 10.0), col
    assert np.array_equal(d["Volume"].to_numpy(), v) and info["rows_used"] == 4


def test_r3_drops_rows_before_es_launch(tmp_path):
    dates = pd.bdate_range("1997-09-03", "1997-09-12")      # 3,4,5,8 | 9,10,11,12
    o, h, l, c = walk(dates)
    d, info = rb.load_r3(write_stooq(tmp_path / "es_f_d.csv", dates, o, h, l, c))
    assert d["TradingDate"].iloc[0] == TS("1997-09-09") and len(d) == 4
    assert info["rows_before_launch_dropped"] == 4


def test_daily_bars_used_as_delivered(tmp_path):
    dates = pd.to_datetime(["2024-03-08", "2024-03-11"])    # Friday, Monday: no 17:00 roll applies
    d = rb.daily_frame_from(pd.DataFrame({"Date": dates, "Open": [1.0, 2], "High": [2.0, 3], "Low": [0.5, 1],
                                          "Close": [1.5, 2.5], "Volume": [0.0, 0]}))
    assert list(d["TradingDate"]) == list(dates) and set(d["CloseSource"]) == {"delivered"}
    assert d["Close"].tolist() == [1.5, 2.5]


def test_manifest(tmp_path):
    dates = pd.bdate_range("2024-01-02", periods=3)
    o, h, l, c = walk(dates)
    p = write_stooq(tmp_path / "es_f_d.csv", dates, o, h, l, c)
    m = rb.file_manifest(p)
    assert m["sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert (m["data_rows"], m["first"], m["last"]) == (3, "2024-01-02", "2024-01-04")


# --------------------------------------------------------------------------------------------
# roll-gap filter
# --------------------------------------------------------------------------------------------
def test_third_fridays():
    assert [rb.third_friday(2015, m) for m in (3, 6, 9, 12)] == [TS("2015-03-20"), TS("2015-06-19"),
                                                                 TS("2015-09-18"), TS("2015-12-18")]
    assert rb.third_friday(2008, 3) == TS("2008-03-21") and rb.third_friday(2021, 1) == TS("2021-01-15")


def test_roll_window_is_plus_minus_5_trading_days():
    dates = pd.bdate_range("2015-03-02", "2015-04-10")
    m = pd.Series(rb.roll_window_mask(dates), index=dates)
    i = list(dates).index(TS("2015-03-20"))
    assert m.iloc[i - 5: i + 6].all() and not m.iloc[i - 6] and not m.iloc[i + 6]
    hol = dates[dates != TS("2015-03-20")]                    # third Friday not a trading date
    mh = pd.Series(rb.roll_window_mask(hol), index=hol)
    a = list(hol).index(TS("2015-03-23"))                     # anchor = next trading date
    assert mh.iloc[a - 5: a + 6].all() and not mh.iloc[a - 6] and not mh.iloc[a + 6]


GAP_DATES = pd.bdate_range("2014-10-01", "2015-08-31")
ROLL_DAY, PLAIN_DAY = TS("2015-03-20"), TS("2015-05-06")      # third Friday of March / not near one


def gap_fixture(roll=True, plain=True):
    o, h, l, c = walk(GAP_DATES, seed=4, step=6.0, quiet_gaps=True)
    for day, on in ((ROLL_DAY, roll), (PLAIN_DAY, plain)):
        if on:
            i = list(GAP_DATES).index(day)
            o, h, l, c = o.copy(), h.copy(), l.copy(), c.copy()
            o[i:] += 40.0; h[i:] += 40.0; l[i:] += 40.0; c[i:] += 40.0   # a 40-point step at the open
    return rb.daily_frame_from(pd.DataFrame({"Date": GAP_DATES, "Open": o, "High": h, "Low": l, "Close": c,
                                             "Volume": 0.0}))


def test_planted_40pt_gap_filtered_only_on_the_roll_friday():
    d = gap_fixture()
    flags = pd.Series(rb.roll_dates(d), index=GAP_DATES)
    assert flags[flags].index.tolist() == [ROLL_DAY]
    g = rb.open_gaps(d)
    i, j = list(GAP_DATES).index(ROLL_DAY), list(GAP_DATES).index(PLAIN_DAY)
    assert g[i] > 39 and g[j] > 39                            # the same gap on both dates
    mask = rb.roll_gross_mask(flags.to_numpy())
    assert np.flatnonzero(mask).tolist() == [i - 1, i]


def test_filter_removes_the_jump_from_pnl_and_keeps_costs():
    d = gap_fixture(plain=False)
    i = list(GAP_DATES).index(ROLL_DAY)
    pos = np.ones(len(d))                                     # always long
    cal = pd.DatetimeIndex(d["TradingDate"])
    raw = engine.run_positions(d, pos, cal)
    filt = engine.run_positions(d, pos, cal, gross_mask=rb.roll_gross_mask(rb.roll_dates(d)))
    o = d["Open"].to_numpy()
    assert raw.gross[i - 1] == pytest.approx((o[i] - o[i - 1]) * 5) and raw.gross[i - 1] > 150
    assert filt.gross[i - 1] == 0 and filt.gross[i] == 0
    assert np.array_equal(np.delete(filt.gross, [i - 1, i]), np.delete(raw.gross, [i - 1, i]))
    assert np.array_equal(filt.sides, raw.sides)


def test_gap_must_exceed_3x_median_of_previous_60():
    d = gap_fixture(roll=False, plain=False)
    i = list(GAP_DATES).index(ROLL_DAY)
    g = rb.open_gaps(d)
    med = np.median(g[i - 60:i])
    o = d["Open"].to_numpy().copy()
    o[i] = d["Close"].iloc[i - 1] + 2.9 * med                 # below 3x: not a roll
    assert not rb.roll_dates(d.assign(Open=o))[i]
    o[i] = d["Close"].iloc[i - 1] + 3.2 * med                 # above 3x: a roll
    assert rb.roll_dates(d.assign(Open=o))[i]


# --------------------------------------------------------------------------------------------
# agreement measure, warm-up, end to end
# --------------------------------------------------------------------------------------------
def test_spearman_hand_values():
    idx = list("abcde")
    assert rb.spearman(pd.Series([1, 2, 3, 4, 5], idx), pd.Series([2, 1, 4, 3, 5], idx)) == pytest.approx(0.8)
    assert rb.spearman(pd.Series([1, 2, 3], list("abc")), pd.Series([30, 20, 10], list("abc"))) == pytest.approx(-1.0)
    # ties -> average ranks [1, 2.5, 2.5, 4] vs [1, 2, 3, 4]
    want = np.corrcoef([1, 2.5, 2.5, 4], [1, 2, 3, 4])[0, 1]
    assert rb.spearman(pd.Series([0.1, 0.5, 0.5, 0.9], list("abcd")), pd.Series([1, 2, 3, 4], list("abcd"))) == pytest.approx(want)
    # a rule without SR is left out; alignment is by name, not position
    a = pd.Series({"x": 1.0, "y": 2.0, "z": 3.0, "hp": math.nan})
    b = pd.Series({"z": 9.0, "y": 8.0, "x": 7.0, "hp": 1.0})
    assert rb.spearman(a, b) == pytest.approx(1.0)


def test_sr_ranks():
    r = rb.sr_ranks(pd.Series({"b": 0.5, "a": 0.5, "c": 0.9, "d": math.nan}))
    assert (r["c"], r["a"], r["b"]) == (1.0, 2.0, 3.0) and math.isnan(r["d"])


def test_warmup_start_is_bar_300():
    dates = pd.bdate_range("2019-01-01", periods=420)
    o, h, l, c = walk(dates, seed=6)
    d = rb.daily_frame_from(pd.DataFrame({"Date": dates, "Open": o, "High": h, "Low": l, "Close": c, "Volume": 0.0}))
    w = rb.windows_for(d)
    assert w["full"] == (dates[300], dates[-1])
    assert w["p1window"] == (max(engine.EVAL_WINDOW[0], dates[300]), dates[-1])
    cal = engine.window_calendar(d, w["full"])
    pos = np.zeros(len(d))
    pos[299:] = 1                                             # decided at bar 299 -> executed at bar 300
    dr = engine.run_positions(d, pos, cal)
    assert len(cal) == 120 and dr.sides[0] == 1 and dr.sides.sum() == 1
    with pytest.raises(ValueError):
        rb.windows_for(d.iloc[:300])


def _fixture_files(tmp_path):
    r1d = pd.bdate_range("2014-01-02", "2026-02-24")
    o, h, l, c = walk(r1d, seed=11, start=180.0, step=1.5, gap=0.3)
    write_stooq(tmp_path / "spy_us_d.csv", r1d, o, h, l, c, v=np.full(len(r1d), 5e7), extra=True)
    r3d = pd.bdate_range("1997-08-01", "2026-02-24")
    o, h, l, c = walk(r3d, seed=12, start=950.0, step=10.0, quiet_gaps=True)
    i = list(r3d).index(TS("2015-03-20"))
    o[i:] += 40.0; h[i:] += 40.0; l[i:] += 40.0; c[i:] += 40.0
    write_stooq(tmp_path / "es_f_d.csv", r3d, o, h, l, c)
    rules = rb.d_rules(signals.load_rules())
    p1 = pd.DataFrame({"module": [r.module for r in rules], "sr": np.linspace(0.8, -0.8, len(rules))})
    p1.to_csv(tmp_path / "metrics_P1.csv", index=False)


def test_robustness_cli_end_to_end_on_synthetic_files(tmp_path):
    _fixture_files(tmp_path)
    out = tmp_path / "robustness"
    assert cli.main(["robustness", "--data-dir", str(tmp_path), "--p1-metrics", str(tmp_path / "metrics_P1.csv"),
                     "--out", str(out)]) == 0
    for ds in ("R1", "R3", "R3_unfiltered"):
        for w in ("full", "p1window"):
            m = pd.read_csv(out / ("%s_%s_metrics.csv" % (ds, w))).set_index("module")
            assert len(m) == 19 and "BuyHold" in m.index, (ds, w)
            ranked = m["rank_sr"].dropna().astype(int)
            finite = int(((m["status"] == "ok") & m["sr"].notna()).sum())   # a rule that never trades has no SR
            assert sorted(ranked) == list(range(1, finite + 1)) and finite >= 15, (ds, w)
            assert int((m["status"] == "ok").sum()) == (18 if ds == "R1" else 17), (ds, w)
            if ds != "R1":
                assert m.loc["HedgingPressure", "status"] == "not_available" and m.loc["HedgingPressure", "reason"] == "n/a (no volume)"
    full_r3 = pd.read_csv(out / "R3_full_metrics.csv").set_index("module")
    full_un = pd.read_csv(out / "R3_unfiltered_full_metrics.csv").set_index("module")
    # only the planted 2015-03-20 gap is a roll: the filter removes exactly bars r-1 and r
    d3, _ = rb.load_r3(tmp_path / "es_f_d.csv")
    flags = rb.roll_dates(d3)
    assert d3.loc[flags, "TradingDate"].tolist() == [TS("2015-03-20")]
    _, g, _ = engine.bar_ledger(d3["Open"].to_numpy(), rb.engine.buy_and_hold_positions(d3, rb.windows_for(d3)["full"]))
    removed = g[rb.roll_gross_mask(flags)].sum()
    i = int(np.flatnonzero(flags)[0])
    o3, c3 = d3["Open"].to_numpy(), d3["Close"].to_numpy()
    assert o3[i] - c3[i - 1] == pytest.approx(40.0, abs=0.25)        # the jump sits in bar i-1 (O_{i-1} -> O_i)
    assert g[i - 1] == pytest.approx((o3[i] - o3[i - 1]) * 5)
    assert full_r3.loc["BuyHold", "gross_pnl"] == pytest.approx(full_un.loc["BuyHold", "gross_pnl"] - removed)
    pw = pd.read_csv(out / "R1_p1window_metrics.csv").set_index("module")
    assert pw.loc["BuyHold", "n_days"] == len(pd.bdate_range("2021-01-04", "2026-02-24"))
    txt = (out / "ROBUSTNESS.md").read_text(encoding="utf-8")
    sha = hashlib.sha256((tmp_path / "es_f_d.csv").read_bytes()).hexdigest()
    assert "## MANIFEST" in txt and sha in txt and "never change it" in txt
    assert txt.count("Spearman") >= 2 and "2015-03-20" in txt and "n/a (no volume)" in txt
    assert "1 roll dates, 2 bars with gross P&L set to 0" in txt


# --------------------------------------------------------------------------------------------
# falsifiers
# --------------------------------------------------------------------------------------------
def test_falsifier_gap_rule_without_roll_window_is_detected():
    """Dropping the third-Friday window flags the same 40-point gap on the non-roll date too."""
    d = gap_fixture()
    g = pd.Series(rb.open_gaps(d))
    med = g.rolling(60, min_periods=60).median().shift(1)
    no_window = (g > 3 * med).to_numpy()
    assert no_window[list(GAP_DATES).index(PLAIN_DAY)]
    assert not rb.roll_dates(d)[list(GAP_DATES).index(PLAIN_DAY)]


def test_falsifier_zeroing_only_the_roll_bar_leaves_the_jump():
    """A half-open reading (zero bar r only) keeps the Close_{r-1} -> Open_r jump in bar r-1."""
    d = gap_fixture(plain=False)
    i = list(GAP_DATES).index(ROLL_DAY)
    flags = rb.roll_dates(d)
    only_r = flags.copy()
    cal = pd.DatetimeIndex(d["TradingDate"])
    pos = np.ones(len(d))
    wrong = engine.run_positions(d, pos, cal, gross_mask=only_r)
    right = engine.run_positions(d, pos, cal, gross_mask=rb.roll_gross_mask(flags))
    assert wrong.gross[i - 1] > 150 and right.gross[i - 1] == 0


def test_runs_with_only_the_spy_file_and_reports_the_missing_one(tmp_path):
    """A missing ES.F file is reported as 'not downloaded', not a crash (2026-10-18)."""
    import pandas as pd
    from qibt import robustness as rb
    d = tmp_path / "stooq"; d.mkdir()
    dates = pd.bdate_range("2019-01-01", periods=420)
    close = 250 + (pd.Series(range(420)) % 7 - 3) * 0.5 + pd.Series(range(420)) * 0.05
    df = pd.DataFrame({"Date": dates.strftime("%Y-%m-%d"), "Open": close - 0.2, "High": close + 0.6,
                       "Low": close - 0.7, "Close": close, "Volume": 1_000_000})
    df.to_csv(d / rb.FILES["R1"], index=False)
    p1 = tmp_path / "metrics_P1.csv"
    mods = [r.module for r in rb.d_rules(rb.signals.load_rules(rb.signals.RULES_PATH))]
    pd.DataFrame({"module": mods, "sr": [0.1 * i for i in range(len(mods))]}).to_csv(p1, index=False)
    res, _, meta, _ = rb.run_all(d, p1, tmp_path / "out")
    assert set(res) == {"R1"} and meta["missing"] == [rb.FILES["R3"]]
    assert "Not run (input file not downloaded)" in (tmp_path / "out" / "ROBUSTNESS.md").read_text(encoding="utf-8")


def test_falsifier_no_input_files_is_an_error(tmp_path):
    import pytest as _pt
    from qibt import robustness as rb
    with _pt.raises(FileNotFoundError):
        rb.run_all(tmp_path, tmp_path / "none.csv", tmp_path / "out")
