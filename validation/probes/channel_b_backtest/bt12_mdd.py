"""BT12: MDD = max over t of (running max of cumulative P&L - cumulative P&L).

Pre-registered: hand fixtures incl. monotone up (MDD 0). Observation (not a verdict input): whether
the equity curve starts at 0 (the ledger text does not say). Usage: python -I -B bt12_mdd.py [--qibt-root DIR]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

_cb.use_qibt()
import numpy as np  # noqa: E402
from qibt import metrics  # noqa: E402

c = _cb.Checker("BT12 max drawdown")
# [5,-3,-4,6,-1]: cum 5,2,-2,4,3; running max 5,5,5,5,5; dd 0,3,7,1,2 -> 7
# [10,-2,5,-20,3,30,-4]: cum 10,8,13,-7,-4,26,22; peaks 10,10,13,13,13,26,26; dd 0,2,0,20,17,0,4 -> 20
# [3,-1,-1,4,-6,1]: cum 3,2,1,5,-1,0; peaks 3,3,3,5,5,5; dd 0,1,2,0,6,5 -> 6
fx = [([5, -3, -4, 6, -1], 7.0), ([1, 2, 3, 4], 0.0), ([0, 0, 0], 0.0), ([1, -1, 1, -1], 1.0),
      ([10, -2, 5, -20, 3, 30, -4], 20.0), ([3, -1, -1, 4, -6, 1], 6.0)]
for x, exp in fx:
    got = metrics.max_drawdown(np.array(x, dtype=float))
    c.check("MDD(%r) == %g" % (x, exp), got == exp, "got %r" % got)
rng = np.random.default_rng(3)
bad = 0
for _ in range(300):
    a = np.round(rng.normal(0, 100, int(rng.integers(1, 500))), 2)
    if abs(metrics.max_drawdown(a) - _cb.mdd_ref(list(a))) > 1e-9:
        bad += 1
c.check("300 random series vs own loop (equity from 0)", bad == 0, "mismatches=%d" % bad)
c.check("monotone up (strictly) -> 0", metrics.max_drawdown(np.arange(1.0, 100.0)) == 0.0)
# observation: first-day loss (equity-from-0 convention)
print("OBSERVATION: MDD([-5, 3]) = %r  (5 if the curve starts at 0; 0 if the running max starts at day 1)"
      % metrics.max_drawdown(np.array([-5.0, 3.0])))
sys.exit(c.close())
