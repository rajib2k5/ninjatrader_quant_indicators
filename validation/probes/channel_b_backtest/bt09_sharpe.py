"""BT9 (estimator part): SR = mean / std(ddof=1) of daily P&L x sqrt(252).

Pre-registered: numeric fixture vs numpy; scale invariance under P&L x k.
The "assumes iid" half of BT9 is a literature claim (Lo 2002) - not decidable at runtime.
Usage: python -I -B bt09_sharpe.py [--qibt-root DIR]
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

_cb.use_qibt()
import numpy as np  # noqa: E402
from qibt import metrics  # noqa: E402

c = _cb.Checker("BT9 annualised Sharpe")
# hand fixture: x = [1, 2, 3, 4, 10]; mean 4; sum sq dev = 9+4+1+0+36 = 50; var(ddof=1) = 12.5
x = [1.0, 2.0, 3.0, 4.0, 10.0]
hand = 4.0 / math.sqrt(12.5) * math.sqrt(252.0)          # = 17.959955...
c.check("hand fixture SR == 4/sqrt(12.5)*sqrt(252) = %.12f" % hand, abs(metrics.sharpe(x) - hand) < 1e-12,
        "got %.15f" % metrics.sharpe(x))
c.check("per-day SR == 4/sqrt(12.5)", abs(metrics.sharpe_daily(x) - 4.0 / math.sqrt(12.5)) < 1e-15,
        "got %.15f" % metrics.sharpe_daily(x))
rng = np.random.default_rng(7)
worst = 0.0
for _ in range(200):
    a = rng.normal(rng.normal(0, 20), abs(rng.normal(100, 50)) + 1, int(rng.integers(5, 1500)))
    ref = float(np.mean(a) / np.std(a, ddof=1) * np.sqrt(252))
    worst = max(worst, abs(metrics.sharpe(a) - ref) / max(1.0, abs(ref)))
c.check("200 random series vs numpy mean/std(ddof=1)*sqrt(252): rel err < 1e-12", worst < 1e-12, "worst %.3g" % worst)
a = rng.normal(3, 50, 1000)
s = metrics.sharpe(a)
inv = [abs(metrics.sharpe(a * k) - s) for k in (0.01, 0.5, 2.0, 5.0, 1000.0)]
c.check("scale invariance SR(k x) == SR(x) for k > 0", max(inv) < 1e-12, "max diff %.3g" % max(inv))
c.check("SR(-x) == -SR(x)", abs(metrics.sharpe(-a) + s) < 1e-12)
c.check("constant series -> NaN (zero variance), not inf", math.isnan(metrics.sharpe([5.0] * 10)))
sys.exit(c.close())
