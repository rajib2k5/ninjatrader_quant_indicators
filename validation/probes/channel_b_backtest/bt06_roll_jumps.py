"""BT6 (runtime part, a property of P1): no quarterly roll jump > 3 x median daily range at roll dates.

Roll date R (pre-registered window rule given to Channel B): 8 calendar days before the third Friday
of Mar/Jun/Sep/Dec. For every trading date d with R-3 <= d <= R+3 (calendar days) the probe takes
  session-open gap |Open_d - Close_prev|  (D bars built by Channel B's own PROTOCOL-3 aggregation)
  largest 1-minute step |Open_t - Close_{t-1}| inside d (first bar of d against the previous bar)
and compares the largest value with 3 x median(High - Low) of all D bars.

Supplementary (printed + own check): (a) where the roll-window session-open gaps rank among ALL
session-open gaps (an unadjusted roll of a few tens of points would be a top outlier); (b) tick-grid
test: every OHLC price is a multiple of 0.25 (additive adjustment by a tick multiple keeps the grid,
a ratio adjustment would not).
Falsifiers: --inject jump  (add 4 x median range to every price before the 2023-06-08 roll)
            --inject ratio (multiply every price before the 2023-06-08 roll by 1.003)
Usage: python -I -B bt06_roll_jumps.py [--pkl PATH] [--inject jump|ratio]
"""
from __future__ import annotations

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

argv = sys.argv
inject = None
if "--inject" in argv:
    i = argv.index("--inject"); inject = argv[i + 1]; del argv[i:i + 2]
_cb.use_qibt()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

df, src = _cb.load_p1_frame(argv)
df = df.reset_index(drop=True)
print("source: %s, %d bars" % (src, len(df)))
PX = ["Open", "High", "Low", "Close"]


def third_friday(y, m):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(4 - d.weekday()) % 7)
    return d + dt.timedelta(days=14)


rolls = [pd.Timestamp(third_friday(y, m) - dt.timedelta(days=8)) for y in range(2020, 2027) for m in (3, 6, 9, 12)]
ns = df["BarTime"].to_numpy().astype("datetime64[ns]").astype(np.int64)
td = _cb.trading_dates_ns(ns)
if inject in ("jump", "ratio"):
    R = pd.Timestamp("2023-06-08")
    before = td < R.value
    if inject == "jump":
        pass  # size set after the median range is known
    else:
        for k in PX:
            df.loc[before, k] = df.loc[before, k] * 1.003
        print("INJECTED: prices before %s x 1.003 (%d bars)" % (R.date(), int(before.sum())))

# own D frame (first open, max, min, last close per trading date)
u, start = np.unique(td, return_index=True)
end = np.r_[start[1:], len(td)]
O = df["Open"].to_numpy(); H = df["High"].to_numpy(); L = df["Low"].to_numpy(); C = df["Close"].to_numpy()
rng_d = np.maximum.reduceat(H, start) - np.minimum.reduceat(L, start)
med = float(np.median(rng_d))
thr = 3.0 * med
if inject == "jump":
    R = pd.Timestamp("2023-06-08")
    before = td < R.value
    k = np.round(4.0 * med * 4) / 4
    for col in PX:
        df.loc[before, col] = df.loc[before, col] + k
    O = df["Open"].to_numpy(); H = df["High"].to_numpy(); L = df["Low"].to_numpy(); C = df["Close"].to_numpy()
    print("INJECTED: +%.2f points on every price before %s (%d bars)" % (k, R.date(), int(before.sum())))
dO = O[start]
dC = C[end - 1]
gap = np.r_[np.nan, np.abs(dO[1:] - dC[:-1])]                       # session-open gap per D bar
step = np.r_[np.nan, np.abs(O[1:] - C[:-1])]                          # every 1-minute step
max_step_in_day = np.array([np.nanmax(step[s:e]) if e > s and not (s == 0 and e == 1) else np.nan
                            for s, e in zip(start, end)])
dates = pd.to_datetime(u)
print("D bars %d; median daily range %.2f pts; threshold 3x = %.2f pts" % (len(u), med, thr))
c = _cb.Checker("BT6 roll-date jumps")
worst = (0.0, None, None)
rank_pct = []
gap_sorted = np.sort(gap[1:])
for R in rolls:
    if not (dates[0] < R <= dates[-1]):
        continue
    sel = np.where((dates >= R - pd.Timedelta(days=3)) & (dates <= R + pd.Timedelta(days=3)))[0]
    g = [(gap[i], max_step_in_day[i], dates[i]) for i in sel if i > 0]
    if not g:
        print("  roll %s: no trading dates in window" % R.date())
        continue
    gmax = max(x[0] for x in g)
    smax = max(x[1] for x in g)
    dmax = max(g, key=lambda x: x[0])[2]
    pct = 100.0 * np.searchsorted(gap_sorted, gmax, side="right") / len(gap_sorted)
    rank_pct.append(pct)
    print("  roll %s: window dates %s; max session-open gap %.2f (on %s, percentile %.1f of all gaps); "
          "max 1-min step %.2f" % (R.date(), [str(x[2].date()) for x in g], gmax, dmax.date(), pct, smax))
    for val, label in ((gmax, "gap"), (smax, "1-min step")):
        if val > worst[0]:
            worst = (val, R, label)
c.check("no roll-window jump > 3 x median daily range (%.2f)" % thr, worst[0] <= thr,
        "largest %.2f (%s, roll %s)" % (worst[0], worst[2], worst[1].date() if worst[1] is not None else "-"))
allgap = gap[1:]
top = np.argsort(-np.nan_to_num(gap, nan=-1))[:8]
print("OBSERVATION top-8 session-open gaps in all of P1: %s" % (
    [("%s" % dates[i].date(), round(float(gap[i]), 2)) for i in top],))
print("OBSERVATION session-open gaps: median %.2f, p95 %.2f, p99 %.2f, max %.2f; roll-window maxima percentiles: "
      "median %.1f, max %.1f" % (np.median(allgap), np.percentile(allgap, 95), np.percentile(allgap, 99),
                                 np.max(allgap), np.median(rank_pct), np.max(rank_pct)))
tf = (dates.dayofweek >= 1) & (dates.dayofweek <= 4)
tf_gaps = np.sort(gap[1:][np.asarray(tf[1:])])
exact = []
for R in rolls:
    for off in (0, 1):
        d = R + pd.Timedelta(days=off)
        j = dates.get_indexer([d])[0]
        if j > 0:
            exact.append((str(d.date()), round(float(gap[j]), 2),
                          round(float(100.0 * np.searchsorted(tf_gaps, gap[j], side="right") / len(tf_gaps)), 1)))
print("OBSERVATION session-open gap on the roll date R (Thu) and R+1 (Fri) [date, points, percentile among all "
      "Tue-Fri gaps]: %s" % (exact,))
print("OBSERVATION Tue-Fri session-open gaps: median %.2f, p90 %.2f, p99 %.2f; share of Tue-Fri gaps >= 10 points: %.2f%%"
      % (np.median(tf_gaps), np.percentile(tf_gaps, 90), np.percentile(tf_gaps, 99), 100.0 * np.mean(tf_gaps >= 10)))
allpx = np.concatenate([df[k].to_numpy() for k in PX])
off = int(np.sum(np.abs(allpx * 4 - np.round(allpx * 4)) > 1e-9))
c.check("supplementary: every OHLC price on the 0.25 tick grid", off == 0,
        "off-grid prices=%d of %d" % (off, len(allpx)))
sys.exit(c.close())
