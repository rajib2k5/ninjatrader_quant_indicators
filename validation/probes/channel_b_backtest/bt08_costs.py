"""BT8: costs = |p_t - p_{t-1}| x USD 2.25, charged at execution (open of bar t+1).

Pre-registered: flip long->short charges 2 sides; hold charges 0; 0x/2x scale linearly.
Supplementary (--edge, separate exit code): a change executed at the open of the LAST bar of the
data - PROTOCOL section 4 executes p_{n-2} at Open_{n-1}, section 5 charges every change.
Usage: python -I -B bt08_costs.py [--qibt-root DIR] [--edge]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

edge = "--edge" in sys.argv
if edge:
    sys.argv.remove("--edge")
_cb.use_qibt()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from qibt import engine  # noqa: E402

if not edge:
    c = _cb.Checker("BT8 cost model (pre-registered)")
    # bar      0   1   2   3   4   5   6
    # p_t     +1  -1  -1   0  +1  +1   0
    # execution of p_t at bar t+1, sides |p_t - p_{t-1}| with a flat start (p_{-1} = 0):
    # bar1: |1-0|=1 (entry)   bar2: |-1-1|=2 (flip)   bar3: |-1-(-1)|=0 (hold)
    # bar4: |0-(-1)|=1 (exit) bar5: |1-0|=1 (entry)   bar6 (last): |1-1|=0
    O = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0])
    P = np.array([1, -1, -1, 0, 1, 1, 0])
    held, gross, sides = engine.bar_ledger(O, P)
    c.check("sides per execution bar == [0, 1, 2, 0, 1, 1, 0]", sides.tolist() == [0, 1, 2, 0, 1, 1, 0],
            "got %r" % (sides.tolist(),))
    cost1 = engine.bar_costs(sides, 1.0)
    c.check("cost at 1x == [0, 2.25, 4.50, 0, 2.25, 2.25, 0]",
            cost1.tolist() == [0.0, 2.25, 4.5, 0.0, 2.25, 2.25, 0.0], "got %r" % (cost1.tolist(),))
    c.check("flip long->short costs 2 sides = 4.50", cost1[2] == 4.5)
    c.check("hold costs 0", cost1[3] == 0.0)
    cost0 = engine.bar_costs(sides, 0.0)
    cost2 = engine.bar_costs(sides, 2.0)
    c.check("0x costs are all 0", cost0.tolist() == [0.0] * 7, "got %r" % (cost0.tolist(),))
    c.check("2x costs == 2 * 1x costs", np.array_equal(cost2, 2 * cost1), "got %r" % (cost2.tolist(),))
    # end to end through DailyResult: each bar on its own trading date
    td = pd.date_range("2022-01-03", periods=7, freq="B")
    f = pd.DataFrame({"TradingDate": td, "Open": O})
    dr = engine.run_positions(f, P, pd.DatetimeIndex(td))
    c.check("DailyResult.sides == [0,1,2,0,1,1,0]", dr.sides.tolist() == [0, 1, 2, 0, 1, 1, 0],
            "got %r" % (dr.sides.tolist(),))
    # gross by hand: bar1 = +1*(102-101)*5 = 5, bar2 = -1*1*5 = -5, bar3 = -5, bar4 = 0, bar5 = +5
    exp_gross = [0.0, 5.0, -5.0, -5.0, 0.0, 5.0, 0.0]
    c.check("DailyResult.gross == hand", dr.gross.tolist() == exp_gross, "got %r" % (dr.gross.tolist(),))
    for m in (0.0, 1.0, 2.0):
        exp = [g - s * 2.25 * m for g, s in zip(exp_gross, [0, 1, 2, 0, 1, 1, 0])]
        c.check("net at %gx == gross - sides*2.25*%g" % (m, m), dr.net(m).tolist() == exp,
                "got %r" % (dr.net(m).tolist(),))
    tot = [float(dr.cost(m).sum()) for m in (0.0, 1.0, 2.0)]
    c.check("total cost 0x/1x/2x == 0 / 11.25 / 22.50 (5 sides)", tot == [0.0, 11.25, 22.5], "got %r" % (tot,))
    sys.exit(c.close())
else:
    c = _cb.Checker("BT8 supplementary: change executed at the open of the last bar")
    # n = 4, p = [0, 0, 1, 1]: p_2 = +1 is executed at Open_3 (the last bar, which exists).
    # PROTOCOL 5 literal: charged |p_2 - p_1| = 1 side = 2.25 at bar 3. No P&L (no Open_4).
    held, gross, sides = engine.bar_ledger(np.array([1.0, 2.0, 3.0, 4.0]), np.array([0, 0, 1, 1]))
    c.check("last-bar execution charged 1 side", sides[3] == 1, "sides=%r gross=%r" % (sides.tolist(), gross.tolist()))
    sys.exit(c.close())
