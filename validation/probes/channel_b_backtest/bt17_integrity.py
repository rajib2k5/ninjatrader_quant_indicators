"""BT17: P1 covers 2020-01-03 -> 2026-02-24 with no gap > 3 trading dates and no duplicated bar
after de-duplication. Data-integrity probe on the LOADED P1 (qibt.data.load_p1 cache, or --pkl PATH).

Gap definition (from the claim; no holiday calendar is assumed): for consecutive trading dates
d_i < d_{i+1} of P1 (PROTOCOL 3 rule), gap = number of Mon-Fri dates strictly between them.
A gap > 3 refutes the claim. Every gap >= 1 is listed, with the bars on both sides.
Also listed (observation, not a claim condition): sessions with < 300 one-minute bars.

Options: --raw PATH  compare the loaded frame with Channel B's own raw re-parse (exact equality)
         --inject dup|gap  falsifier data mutations (duplicate a bar / drop 5 weekdays in 2022-06)
         --control  run the gap logic on a synthetic clean weekday calendar (must pass)
Usage: python -I -B bt17_integrity.py [--pkl PATH] [--raw PATH] [--inject dup|gap] [--control]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

argv = sys.argv
inject = None
if "--inject" in argv:
    i = argv.index("--inject"); inject = argv[i + 1]; del argv[i:i + 2]
raw = None
if "--raw" in argv:
    i = argv.index("--raw"); raw = argv[i + 1]; del argv[i:i + 2]
control = "--control" in argv
if control:
    argv.remove("--control")
_cb.use_qibt()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

DAY = np.int64(86_400_000_000_000)


def weekday_gaps(td_dates):
    """[(d_prev, d_next, missing_weekdays)] for consecutive trading dates with >= 1 missing weekday."""
    out = []
    for a, b in zip(td_dates[:-1], td_dates[1:]):
        between = pd.date_range(a + pd.Timedelta(days=1), b - pd.Timedelta(days=1), freq="D")
        miss = int(np.sum(between.dayofweek < 5))
        if miss >= 1:
            out.append((a, b, miss))
    return out


if control:
    c = _cb.Checker("BT17 control: synthetic weekday calendar with only 1-day holidays")
    cal = pd.bdate_range("2021-01-04", "2021-12-31")
    cal = cal.drop([pd.Timestamp("2021-04-02"), pd.Timestamp("2021-12-24")])
    g = weekday_gaps(list(cal))
    c.check("control: max gap == 1 (so the probe can PASS)", max(x[2] for x in g) == 1, "gaps=%r" % (g,))
    cal2 = cal.drop(pd.bdate_range("2021-06-07", "2021-06-10"))
    g2 = weekday_gaps(list(cal2))
    c.check("control: a 4-weekday hole is reported as gap 4", max(x[2] for x in g2) == 4,
            "gaps=%r" % ([x for x in g2 if x[2] > 1],))
    sys.exit(c.close())

df, src = _cb.load_p1_frame(argv)
print("source: %s, %d bars" % (src, len(df)))
if inject == "dup":
    df = pd.concat([df, df.iloc[[1000]]], ignore_index=True).sort_values("BarTime", kind="mergesort")
    print("INJECTED: duplicated bar %s" % df["BarTime"].iloc[1000])
elif inject == "gap":
    td_tmp = pd.to_datetime(_cb.trading_dates_ns(df["BarTime"].to_numpy().astype("datetime64[ns]").astype(np.int64)))
    drop = (td_tmp >= pd.Timestamp("2022-06-06")) & (td_tmp <= pd.Timestamp("2022-06-10"))
    df = df.loc[~np.asarray(drop)]
    print("INJECTED: dropped trading dates 2022-06-06..2022-06-10 (%d bars)" % int(drop.sum()))

c = _cb.Checker("BT17 P1 data integrity")
bt = df["BarTime"].to_numpy().astype("datetime64[ns]")
ns = bt.astype(np.int64)
td = pd.to_datetime(_cb.trading_dates_ns(ns))
dates = pd.DatetimeIndex(np.unique(td.values))
print("bars %d, first bar %s, last bar %s, trading dates %d (%s -> %s)" % (
    len(df), bt[0], bt[-1], len(dates), dates[0].date(), dates[-1].date()))
c.check("first trading date == 2020-01-03", dates[0] == pd.Timestamp("2020-01-03"), str(dates[0].date()))
c.check("last trading date == 2026-02-24", dates[-1] == pd.Timestamp("2026-02-24"), str(dates[-1].date()))
ndup = int(pd.Series(bt).duplicated().sum())
c.check("no duplicated BarTime", ndup == 0, "duplicates=%d" % ndup)
steps = np.diff(ns)
c.check("BarTime strictly increasing", bool(np.all(steps > 0)), "non-increasing steps=%d" % int(np.sum(steps <= 0)))
wk = dates[dates.dayofweek >= 5]
print("trading dates on Sat/Sun: %d %s" % (len(wk), [str(d.date()) for d in wk[:10]]))

gaps = weekday_gaps(list(dates))
first_idx = {}
last_bar_of = pd.Series(bt).groupby(td.values).max()
first_bar_of = pd.Series(bt).groupby(td.values).min()
print("gaps with >= 1 missing weekday (%d):" % len(gaps))
for a, b, m in gaps:
    flag = "  <-- > 3" if m > 3 else ""
    print("  %s (last bar %s) -> %s (first bar %s): %d missing weekday(s)%s" % (
        a.date(), last_bar_of[a], b.date(), first_bar_of[b], m, flag))
big = [(a, b, m) for a, b, m in gaps if m > 3]
c.check("no gap > 3 trading dates", len(big) == 0,
        "gaps > 3: %s" % ([("%s -> %s" % (a.date(), b.date()), m) for a, b, m in big],))

nbars = pd.Series(1, index=td.values).groupby(level=0).sum()
short = nbars[nbars < 300]
print("OBSERVATION sessions with < 300 one-minute bars (%d):" % len(short))
for d, n in short.items():
    print("  %s: %d bars (%s -> %s)" % (pd.Timestamp(d).date(), n, first_bar_of[d], last_bar_of[d]))

if raw is not None:
    r = pd.read_pickle(raw)
    same = (len(r) == len(df) and np.array_equal(r["BarTime"].to_numpy(), df["BarTime"].to_numpy())
            and all(np.array_equal(r[k].to_numpy(), df[k].to_numpy()) for k in ("Open", "High", "Low", "Close", "Volume")))
    c.check("loaded P1 == Channel B raw re-parse (BarTime + OHLCV exact)", same,
            "raw %d bars vs loaded %d" % (len(r), len(df)))
sys.exit(c.close())
