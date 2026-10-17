"""BT4 (runtime part, a property of P1): no trading date contains a bar timestamped in
(16:00, 17:00] CT; bars only Sunday 17:00 -> Friday 16:00.

Pre-registered probe: session builder on P1 - qibt.data.build_frames must succeed and its sessioned
1-minute frame must hold no bar whose close time-of-day is in (16:00, 17:00]. The time-of-day test
itself is Channel B's own (integer nanoseconds), not qibt's halt_mask.
Observation (printed, not a verdict input): bar counts per minute 15:14-15:31 CT by year.
Falsifier: --inject halt adds one bar closing at 16:30 on a weekday.
Usage: python -I -B bt04_session_halt.py [--pkl PATH] [--inject halt|saturday]
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
_cb.use_qibt()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from qibt import data  # noqa: E402

HOUR = 3_600_000_000_000
MIN = 60_000_000_000
DAY = 24 * HOUR

df, src = _cb.load_p1_frame(argv)
print("source: %s, %d bars" % (src, len(df)))
if inject == "halt":
    row = df.iloc[[500000]].copy()
    row["BarTime"] = row["BarTime"].dt.normalize() + pd.Timedelta(hours=16, minutes=30)
    df = pd.concat([df, row], ignore_index=True).sort_values("BarTime", kind="mergesort").reset_index(drop=True)
    print("INJECTED: bar at %s" % row["BarTime"].iloc[0])
elif inject == "saturday":
    row = df.iloc[[500000]].copy()
    d = row["BarTime"].dt.normalize().iloc[0]
    row["BarTime"] = d + pd.Timedelta(days=(5 - d.dayofweek) % 7, hours=10)
    df = pd.concat([df, row], ignore_index=True).sort_values("BarTime", kind="mergesort").reset_index(drop=True)
    print("INJECTED: bar at %s" % row["BarTime"].iloc[0])

c = _cb.Checker("BT4 P1 session / halt property")
try:
    frames = data.build_frames(df)
    built = True
    m1s = frames["1m"]
    msg = "1m %d bars, D %d dates, 15m %d bars" % (len(m1s), len(frames["D"]), len(frames["15m"]))
except Exception as e:  # SessionError expected on a halt violation
    built = False
    m1s = None
    msg = "%s: %s" % (type(e).__name__, e)
c.check("session builder (qibt.data.build_frames) runs on P1", built, msg)
ns = (m1s if built else df)["BarTime"].to_numpy().astype("datetime64[ns]").astype(np.int64)
tod = ns % DAY
in_halt = (tod > 16 * HOUR) & (tod <= 17 * HOUR)
c.check("no bar closes in (16:00, 17:00] CT", int(in_halt.sum()) == 0, "bars in halt=%d" % int(in_halt.sum()))
dow = ((ns // DAY) + 3) % 7          # 1970-01-01 was a Thursday -> Monday = 0
sat = int(np.sum(dow == 5))
sun_early = int(np.sum((dow == 6) & (tod <= 17 * HOUR)))
fri_late = int(np.sum((dow == 4) & (tod > 16 * HOUR)))
c.check("no bar on Saturday", sat == 0, "Saturday bars=%d" % sat)
c.check("no Sunday bar closing at or before 17:00", sun_early == 0, "count=%d" % sun_early)
c.check("no Friday bar closing after 16:00", fri_late == 0, "count=%d" % fri_late)
if built:
    td = pd.to_datetime(m1s["TradingDate"]).to_numpy().astype("datetime64[ns]").astype(np.int64)
    mine = _cb.trading_dates_ns(ns)
    c.check("builder TradingDate == own PROTOCOL-3 rule on every bar", bool(np.array_equal(td, mine)),
            "mismatches=%d" % int(np.sum(td != mine)))
earliest = int(tod.min()) // MIN
hist = pd.Series(tod // MIN).value_counts()
print("OBSERVATION: distinct close minutes-of-day present: %d of 1440; minutes 16:01..17:00 present: %d"
      % (len(hist), int(sum(hist.get(m, 0) > 0 for m in range(961, 1021)))))
yr = pd.to_datetime(ns).year
rows = []
for m in range(15 * 60 + 14, 15 * 60 + 32):
    sel = (tod // MIN) == m
    rows.append(("%02d:%02d" % divmod(m, 60), [int(np.sum(sel & (yr == y))) for y in range(2020, 2027)]))
print("OBSERVATION bars per close minute, years 2020..2026:")
for lab, cnt in rows:
    print("  %s %s" % (lab, cnt))
# monthly share of weekdays (with > 100 bars before 15:00) that have >= 15 bars closing 15:16..15:30
day = pd.to_datetime((ns // DAY) * DAY)
mins = tod // MIN
s = pd.DataFrame({"d": day, "mid": (mins >= 15 * 60 + 16) & (mins <= 15 * 60 + 30), "early": mins < 15 * 60})
g = s.groupby("d").agg(mid=("mid", "sum"), early=("early", "sum"))
g = g[(g["early"] > 100) & (g.index.dayofweek < 5)]
share = (g["mid"] >= 15).groupby(g.index.to_period("M")).mean()
print("OBSERVATION monthly share of weekdays with >= 15 bars closing 15:16..15:30 CT:")
print("  " + " ".join("%s:%.2f" % (str(k), v) for k, v in share.items()))
sys.exit(c.close())
