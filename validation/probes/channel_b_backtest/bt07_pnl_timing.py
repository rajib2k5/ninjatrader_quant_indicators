"""BT7: P&L of bar t+1 = p_t x (Open_{t+2} - Open_{t+1}) x 5, p_t decided at bar t's close.

Pre-registered probe: hand fixtures + no-look-ahead metamorphic test (mutating bars > t+2 never
changes P&L <= t+1). Expected values are hand-computed from PROTOCOL section 4 (shown inline).
Usage: python -I -B bt07_pnl_timing.py [--qibt-root DIR]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

_cb.use_qibt()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from qibt import engine  # noqa: E402

c = _cb.Checker("BT7 P&L timing")

# --- fixture A (hand count) -----------------------------------------------------------------
# bar     0    1    2    3    4    5
# Open  100  101  103  102  110  107
# p_t    +1   -1    0   +1   +1   -1
# bar1 = p0*(O2-O1)*5 = +1*(103-101)*5 = +10
# bar2 = p1*(O3-O2)*5 = -1*(102-103)*5 = +5
# bar3 = p2*(O4-O3)*5 =  0
# bar4 = p3*(O5-O4)*5 = +1*(107-110)*5 = -15
# bar0 = 0 (nothing held), bar5 = 0 (last bar: no Open_{t+2})
O = np.array([100.0, 101.0, 103.0, 102.0, 110.0, 107.0])
P = np.array([1, -1, 0, 1, 1, -1])
held, gross, sides = engine.bar_ledger(O, P)
c.check("fixture A gross == [0, 10, 5, 0, -15, 0]", gross.tolist() == [0.0, 10.0, 5.0, 0.0, -15.0, 0.0],
        "got %r" % (gross.tolist(),))
c.check("fixture A held (position during bar j = p_{j-1}) == [0, 1, -1, 0, 1, 0]",
        held.tolist() == [0.0, 1.0, -1.0, 0.0, 1.0, 0.0], "got %r" % (held.tolist(),))

# --- fixture B: a gap-up executed bar; the open of the DECISION bar must not matter ------------
# p0 = +1 decided at close of bar 0. Changing Open_0 must not change anything.
O1 = np.array([100.0, 200.0, 205.0, 205.0])
O2 = O1.copy(); O2[0] = 50.0
g1 = engine.bar_ledger(O1, np.array([1, 0, 0, 0]))[1]
g2 = engine.bar_ledger(O2, np.array([1, 0, 0, 0]))[1]
c.check("fixture B gross == [0, 25, 0, 0] (5 points from Open_1 to Open_2)", g1.tolist() == [0.0, 25.0, 0.0, 0.0],
        "got %r" % (g1.tolist(),))
c.check("fixture B: Open_0 (decision bar) does not enter P&L", np.array_equal(g1, g2))

# --- fixture C: daily booking on the trading date of the holding bar --------------------------
# frame bars (e.g. 15m): TD d1 d1 d1 d2 d2 ; Open 10 11 13 12 15 ; p 1 1 -1 0 0
# bar1 (d1) = 1*(13-11)*5 = 10 ; bar2 (d1) = 1*(12-13)*5 = -5 ; bar3 (d2) = -1*(15-12)*5 = -15
# bar4 last -> 0. Calendar d0..d3 -> [0, 5, -15, 0]
d = pd.to_datetime(["2022-01-03", "2022-01-04", "2022-01-05", "2022-01-06"])
f = pd.DataFrame({"TradingDate": [d[1], d[1], d[1], d[2], d[2]], "Open": [10.0, 11.0, 13.0, 12.0, 15.0]})
dr = engine.run_positions(f, np.array([1, 1, -1, 0, 0]), pd.DatetimeIndex(d))
c.check("fixture C daily gross on calendar == [0, 5, -15, 0]", dr.gross.tolist() == [0.0, 5.0, -15.0, 0.0],
        "got %r" % (dr.gross.tolist(),))
# window restriction: a calendar of only d2 keeps only d2's bars
dr2 = engine.run_positions(f, np.array([1, 1, -1, 0, 0]), pd.DatetimeIndex([d[2]]))
c.check("fixture C, calendar [d2] only -> [-15]", dr2.gross.tolist() == [-15.0], "got %r" % (dr2.gross.tolist(),))

# --- reference identity on random data --------------------------------------------------------
rng = np.random.default_rng(20261017)
n = 400
Orand = np.round(4000 + np.cumsum(rng.normal(0, 3, n)) * 4) / 4      # on the 0.25 grid
Prand = rng.integers(-1, 2, n)
g = engine.bar_ledger(Orand, Prand)[1]
ref = np.zeros(n)
for j in range(1, n - 1):
    ref[j] = Prand[j - 1] * (Orand[j + 1] - Orand[j]) * 5.0
c.check("random n=400: gross[j] == p_{j-1}*(O_{j+1}-O_j)*5 for every j (exact)", np.array_equal(g, ref),
        "max |diff| = %g" % float(np.max(np.abs(g - ref))))

# --- metamorphic no-look-ahead ------------------------------------------------------------------
bad_bars = bad_pos = 0
for t in range(0, n - 3, 7):
    O_m = Orand.copy(); O_m[t + 3:] = O_m[t + 3:] + rng.normal(0, 50, n - t - 3)   # bars > t+2
    P_m = Prand.copy(); P_m[t + 1:] = rng.integers(-1, 2, n - t - 1)                 # decisions after t
    g_o = engine.bar_ledger(O_m, Prand)[1]
    g_p = engine.bar_ledger(Orand, P_m)[1]
    if not np.array_equal(g_o[: t + 2], g[: t + 2]):
        bad_bars += 1
    if not np.array_equal(g_p[: t + 2], g[: t + 2]):
        bad_pos += 1
c.check("mutating Open of bars > t+2 never changes P&L of bars <= t+1 (%d t values)" % len(range(0, n - 3, 7)),
        bad_bars == 0, "violations=%d" % bad_bars)
c.check("mutating decisions p_s, s > t never changes P&L of bars <= t+1", bad_pos == 0, "violations=%d" % bad_pos)
# High/Low/Close must not enter (P&L is open-to-open)
f2 = pd.DataFrame({"TradingDate": pd.to_datetime(["2022-01-03"] * n), "Open": Orand,
                   "High": Orand + 5, "Low": Orand - 5, "Close": Orand + 1})
f3 = f2.copy(); f3["Close"] = f3["Close"] + 100; f3["High"] = f3["High"] * 2; f3["Low"] = 0
cal = pd.DatetimeIndex(pd.to_datetime(["2022-01-03"]))
c.check("High/Low/Close do not enter P&L", engine.run_positions(f2, Prand, cal).gross.tolist()
        == engine.run_positions(f3, Prand, cal).gross.tolist())

sys.exit(c.close())
