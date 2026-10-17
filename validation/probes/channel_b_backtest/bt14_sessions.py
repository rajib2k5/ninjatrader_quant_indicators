"""BT14: D-frame aggregation (17:00 CT trading-date roll; first open / max / min / last close / sum)
and right-labelled 15m bars, exactly as PROTOCOL section 3 states.

Hand fixtures (expected values written by hand below, from PROTOCOL 3 only):
  F1 Sunday 17:01 bar, Friday 15:59/16:00 bars, Monday 17:01 (-> Tuesday)
  F2 16:59 vs 17:00 vs 17:01 (trading date) and the halt (16:00, 17:00] check
  F3 DST-change week, March 2024 (DST starts Sun 2024-03-10) - naive CT and UTC input via to_central
  F4 DST-change week, November 2024 (DST ends Sun 2024-11-03) - naive CT and UTC input via to_central
  F5 a 16:00 bar (same date, not in the halt, 15m label 16:00, shares the bar with 15:46..15:59)
  F6 midnight: Mon 23:59 and Tue 00:00 share the 00:00 bar; 00:01 starts the 00:15 bar
Usage: python -I -B bt14_sessions.py [--qibt-root DIR]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

_cb.use_qibt()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from qibt import data  # noqa: E402

T = pd.Timestamp
c = _cb.Checker("BT14 sessions and frames")


def m1(times, opens=None):
    n = len(times)
    o = np.arange(100.0, 100.0 + n) if opens is None else np.asarray(opens, float)
    return pd.DataFrame({"BarTime": pd.to_datetime(times), "Open": o, "High": o + 2.0 + np.arange(n) % 3,
                         "Low": o - 1.0 - np.arange(n) % 2, "Close": o + 0.5, "Volume": np.arange(1.0, n + 1)})


def tds(frame):
    return [str(pd.Timestamp(x).date()) for x in frame["TradingDate"]]


# ---- F1 --------------------------------------------------------------------------------------
t1 = ["2024-01-05 15:59", "2024-01-05 16:00", "2024-01-07 17:01", "2024-01-07 17:02",
      "2024-01-08 09:00", "2024-01-08 16:00", "2024-01-08 17:01"]
f = m1(t1)
fr = data.build_frames(f)
c.check("F1 trading dates", tds(fr["1m"]) == ["2024-01-05", "2024-01-05", "2024-01-08", "2024-01-08",
                                              "2024-01-08", "2024-01-08", "2024-01-09"], "got %r" % tds(fr["1m"]))
D = fr["D"]
c.check("F1 D dates == [01-05, 01-08, 01-09]", tds(D) == ["2024-01-05", "2024-01-08", "2024-01-09"], "got %r" % tds(D))
# D bar of 01-08 = 1m rows 2..5: Open = row2 open, High = max, Low = min, Close = row5 close, Vol = sum
r = f.iloc[2:6]
exp = [float(r["Open"].iloc[0]), float(r["High"].max()), float(r["Low"].min()), float(r["Close"].iloc[-1]),
       float(r["Volume"].sum())]
got = [float(D.iloc[1][k]) for k in ("Open", "High", "Low", "Close", "Volume")]
c.check("F1 D(01-08) = first open (Sun 17:01) / max / min / last close (Mon 16:00) / sum", got == exp,
        "got %r exp %r" % (got, exp))
r = f.iloc[0:2]
exp0 = [float(r["Open"].iloc[0]), float(r["High"].max()), float(r["Low"].min()), float(r["Close"].iloc[-1]),
        float(r["Volume"].sum())]
c.check("F1 D(01-05) aggregation", [float(D.iloc[0][k]) for k in ("Open", "High", "Low", "Close", "Volume")] == exp0)
Q = fr["15m"]
lab = [str(x) for x in Q["BarTime"]]
c.check("F1 15m labels (right-labelled, ceil 15 min)",
        lab == ["2024-01-05 16:00:00", "2024-01-07 17:15:00", "2024-01-08 09:00:00", "2024-01-08 16:00:00",
                "2024-01-08 17:15:00"], "got %r" % lab)
c.check("F1 15m trading dates", tds(Q) == ["2024-01-05", "2024-01-08", "2024-01-08", "2024-01-08", "2024-01-09"],
        "got %r" % tds(Q))
q0 = [float(Q.iloc[0][k]) for k in ("Open", "High", "Low", "Close", "Volume")]
c.check("F1 15m bar 16:00 (Fri) = rows 0..1 aggregated", q0 == exp0, "got %r" % q0)

# ---- F2 --------------------------------------------------------------------------------------
t2 = ["2024-01-10 16:59", "2024-01-10 17:00", "2024-01-10 17:01"]
got = [str(x.date()) for x in data.trading_date(pd.Series(pd.to_datetime(t2)))]
c.check("F2 trading_date 16:59 / 17:00 / 17:01 == 01-10 / 01-10 / 01-11", got == ["2024-01-10", "2024-01-10", "2024-01-11"],
        "got %r" % got)
hm = data.halt_mask(pd.Series(pd.to_datetime(["2024-01-10 16:00", "2024-01-10 16:01", "2024-01-10 16:59",
                                              "2024-01-10 17:00", "2024-01-10 17:01"]))).tolist()
c.check("F2 halt (16:00, 17:00]: 16:00 F, 16:01 T, 16:59 T, 17:00 T, 17:01 F", hm == [False, True, True, True, False],
        "got %r" % hm)
for t in ("2024-01-10 16:59", "2024-01-10 17:00"):
    try:
        data.build_frames(m1(["2024-01-10 15:00", t]))
        raised = False
    except data.SessionError:
        raised = True
    c.check("F2 a bar closing at %s is rejected by the session builder" % t[11:], raised)
ok = True
try:
    data.build_frames(m1(["2024-01-10 16:00", "2024-01-10 17:01"]))
except Exception:
    ok = False
c.check("F2 16:00 and 17:01 bars are accepted", ok)
fr2 = data.build_frames(m1(t2), halt=None)
c.check("F2 halt=None: 16:59 and 17:00 stay on 01-10, 17:01 on 01-11", tds(fr2["1m"]) == ["2024-01-10", "2024-01-10", "2024-01-11"])

# ---- F3 / F4 DST weeks -----------------------------------------------------------------------
t3 = ["2024-03-08 15:59", "2024-03-08 16:00", "2024-03-10 17:01", "2024-03-11 09:30", "2024-03-11 16:00",
      "2024-03-11 17:01", "2024-03-12 16:00"]
fr3 = data.build_frames(m1(t3))
c.check("F3 March DST week (naive CT): roll stays at 17:00 wall clock",
        tds(fr3["1m"]) == ["2024-03-08", "2024-03-08", "2024-03-11", "2024-03-11", "2024-03-11", "2024-03-12", "2024-03-12"],
        "got %r" % tds(fr3["1m"]))
t4 = ["2024-11-01 16:00", "2024-11-03 17:01", "2024-11-04 16:00", "2024-11-04 17:01", "2024-11-05 08:30"]
fr4 = data.build_frames(m1(t4))
c.check("F4 November DST week (naive CT)", tds(fr4["1m"]) == ["2024-11-01", "2024-11-04", "2024-11-04", "2024-11-05", "2024-11-05"],
        "got %r" % tds(fr4["1m"]))
# UTC input converted with to_central (robustness-dataset path)
utc3 = pd.Series(pd.to_datetime(["2024-03-08 22:00", "2024-03-10 22:01", "2024-03-11 21:00", "2024-03-11 22:01"]))
ct3 = [str(x) for x in data.to_central(utc3, "UTC")]
c.check("F3 UTC->CT: 22:00Z Fri = 16:00 CST; 22:01Z Sun = 17:01 CDT; 21:00Z Mon = 16:00 CDT; 22:01Z Mon = 17:01 CDT",
        ct3 == ["2024-03-08 16:00:00", "2024-03-10 17:01:00", "2024-03-11 16:00:00", "2024-03-11 17:01:00"], "got %r" % ct3)
utc4 = pd.Series(pd.to_datetime(["2024-11-01 21:00", "2024-11-03 23:01", "2024-11-04 22:00"]))
ct4 = [str(x) for x in data.to_central(utc4, "UTC")]
c.check("F4 UTC->CT: 21:00Z Fri = 16:00 CDT; 23:01Z Sun = 17:01 CST; 22:00Z Mon = 16:00 CST",
        ct4 == ["2024-11-01 16:00:00", "2024-11-03 17:01:00", "2024-11-04 16:00:00"], "got %r" % ct4)
got = [str(x.date()) for x in data.trading_date(data.to_central(utc3, "UTC"))]
c.check("F3 UTC input trading dates == [03-08, 03-11, 03-11, 03-12]", got == ["2024-03-08", "2024-03-11", "2024-03-11", "2024-03-12"],
        "got %r" % got)

# ---- F5 16:00 bar ----------------------------------------------------------------------------
t5 = ["2024-01-10 15:45", "2024-01-10 15:46", "2024-01-10 15:59", "2024-01-10 16:00"]
f5 = m1(t5)
fr5 = data.build_frames(f5)
Q5 = fr5["15m"]
c.check("F5 15m labels: 15:45 alone, 15:46..16:00 -> 16:00", [str(x)[11:16] for x in Q5["BarTime"]] == ["15:45", "16:00"],
        "got %r" % [str(x) for x in Q5["BarTime"]])
r = f5.iloc[1:4]
expq = [float(r["Open"].iloc[0]), float(r["High"].max()), float(r["Low"].min()), float(r["Close"].iloc[-1]), float(r["Volume"].sum())]
c.check("F5 16:00 15m bar aggregation (first open / max / min / last close / sum)",
        [float(Q5.iloc[1][k]) for k in ("Open", "High", "Low", "Close", "Volume")] == expq)
c.check("F5 16:00 bar keeps its calendar date", tds(fr5["1m"])[-1] == "2024-01-10")
c.check("F5 D bar close == close of the 16:00 bar", float(fr5["D"].iloc[0]["Close"]) == float(f5["Close"].iloc[-1]))

# ---- F6 midnight -----------------------------------------------------------------------------
t6 = ["2024-01-08 23:59", "2024-01-09 00:00", "2024-01-09 00:01"]
fr6 = data.build_frames(m1(t6))
c.check("F6 midnight: labels [00:00, 00:00 -> one bar, 00:15]", [str(x) for x in fr6["15m"]["BarTime"]] ==
        ["2024-01-09 00:00:00", "2024-01-09 00:15:00"], "got %r" % [str(x) for x in fr6["15m"]["BarTime"]])
c.check("F6 midnight: all three on trading date 01-09", tds(fr6["1m"]) == ["2024-01-09"] * 3)
c.check("F6 15m bar counts (Bars) == [2, 1]", fr6["15m"]["Bars"].tolist() == [2, 1], "got %r" % fr6["15m"]["Bars"].tolist())
sys.exit(c.close())
