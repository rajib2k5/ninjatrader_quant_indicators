"""BT1 + BT2 (runtime part): engine contract arithmetic.

BT1 probe (ledger): a 1-point move on 1 contract = USD 5.00 exactly.
BT2 probe (ledger): 1-tick slippage = USD 1.25 (tick = 0.25 index points).
Expected values come from the ledger claim text only. Usage: python -I -B bt01_02_contract_arith.py
[--qibt-root DIR] [--only BT1|BT2]. Exit 0 = claim survived.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

only = None
if "--only" in sys.argv:
    i = sys.argv.index("--only")
    only = sys.argv[i + 1]
    del sys.argv[i:i + 2]
_cb.use_qibt()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from qibt import engine  # noqa: E402

rc = 0
if only in (None, "BT1"):
    c = _cb.Checker("BT1 1 point x 1 contract = USD 5.00")
    # 4 bars; p_0 = +1 is executed at Open_1 = 4000.00 and held to Open_2 = 4001.00 (+1 point)
    o = np.array([4000.00, 4000.00, 4001.00, 4001.00])
    held, gross, sides = engine.bar_ledger(o, np.array([1, 0, 0, 0]))
    c.check("long +1 point: gross of bar 1 == 5.00 exactly", gross[1] == 5.0, "gross=%r" % (gross.tolist(),))
    c.check("long: no other bar carries P&L", gross[0] == 0 and gross[2] == 0 and gross[3] == 0)
    held, gross, sides = engine.bar_ledger(o, np.array([-1, 0, 0, 0]))
    c.check("short +1 point: gross of bar 1 == -5.00 exactly", gross[1] == -5.0, "gross=%r" % (gross.tolist(),))
    # end to end through the daily aggregation with the default point value
    f = pd.DataFrame({"TradingDate": pd.to_datetime(["2022-03-01", "2022-03-02", "2022-03-03", "2022-03-04"]),
                      "Open": o})
    cal = pd.DatetimeIndex(f["TradingDate"])
    dr = engine.run_positions(f, np.array([1, 0, 0, 0]), cal)
    c.check("run_positions: daily gross == [0, 5, 0, 0]", dr.gross.tolist() == [0.0, 5.0, 0.0, 0.0],
            "daily gross=%r" % (dr.gross.tolist(),))
    # 10-point move = 50.00
    held, gross, sides = engine.bar_ledger(np.array([4000.0, 4000.0, 4010.0, 4010.0]), np.array([1, 0, 0, 0]))
    c.check("10 points = 50.00", gross[1] == 50.0, "gross=%r" % (gross[1],))
    rc |= c.close()

if only in (None, "BT2"):
    c = _cb.Checker("BT2 1 tick (0.25 pt) = USD 1.25; 1-tick slippage = USD 1.25")
    o = np.array([4000.00, 4000.00, 4000.25, 4000.25])
    held, gross, sides = engine.bar_ledger(o, np.array([1, 0, 0, 0]))
    c.check("1-tick move on 1 contract == 1.25 exactly", gross[1] == 1.25, "gross=%r" % (gross[1],))
    c.check("cost model: slippage per side == 1.25", engine.SLIPPAGE_PER_SIDE == 1.25,
            "SLIPPAGE_PER_SIDE=%r" % (engine.SLIPPAGE_PER_SIDE,))
    one_side = float(engine.bar_costs(np.array([1.0]), 1.0)[0])
    c.check("one executed side costs 1.00 + 1.25 = 2.25", one_side == 2.25, "cost(1 side)=%r" % (one_side,))
    c.check("one side minus the USD 1.00 commission == 1.25 slippage",
            one_side - engine.COMMISSION_PER_SIDE == 1.25,
            "commission=%r" % (engine.COMMISSION_PER_SIDE,))
    rc |= c.close()

sys.exit(rc)
