"""BT11 (properties only; the paper's numeric example is not available to Channel B):
DSR = PSR(SR0), SR0 = sqrt(V) ((1-g) Phi^-1(1-1/N) + g Phi^-1(1-1/(N e))).

Checks: DSR <= PSR(0); DSR non-increasing (strictly decreasing until saturation) in N; DSR == PSR(0)
when the SR0 term is 0 (V = 0); plus SR0 vs the ledger formula (own Phi^-1 by bisection).
Usage: python -I -B bt11_dsr.py [--qibt-root DIR]
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

c = _cb.Checker("BT11 DSR properties")
rng = np.random.default_rng(2014)
series = [rng.normal(mu, 1.0, n) for mu, n in ((0.08, 1320), (0.02, 1320), (-0.03, 800), (0.15, 250), (0.0, 2000))]
viol = 0
for x in series:
    p0 = metrics.psr_of(x, 0.0)
    for V in (1e-6, 1e-4, 0.001, 0.0552):
        for N in (2, 5, 25, 100, 1000):
            if metrics.dsr_of(x, V, N) > p0 + 1e-15:
                viol += 1
c.check("DSR <= PSR(0) for 5 series x 4 V x 5 N", viol == 0, "violations=%d" % viol)

mono_bad = 0
strict_bad = 0
for x in series:
    for V in (1e-5, 1e-3):
        d = [metrics.dsr_of(x, V, N) for N in range(2, 400)]
        for a, b in zip(d, d[1:]):
            if b > a:
                mono_bad += 1
            if not (b < a) and not (a == b and (a == 0.0 or a == 1.0)):
                strict_bad += 1
c.check("DSR non-increasing in N (N = 2..399)", mono_bad == 0, "increases=%d" % mono_bad)
c.check("DSR strictly decreasing in N unless saturated at 0/1", strict_bad == 0, "non-strict steps=%d" % strict_bad)

eq_bad = 0
for x in series:
    for N in (2, 25, 1000):
        if metrics.dsr_of(x, 0.0, N) != metrics.psr_of(x, 0.0):
            eq_bad += 1
c.check("V = 0 (SR0 term 0): DSR == PSR(0) exactly", eq_bad == 0, "mismatches=%d" % eq_bad)

worst = 0.0
for V in (1e-6, 0.001, 0.055193):
    for N in (2, 3, 10, 25, 100, 10000):
        ref = _cb.sr0_ref(V, N)
        got = metrics.expected_max_sr(V, N)
        worst = max(worst, abs(got - ref) / max(abs(ref), 1e-300))
c.check("SR0 == ledger formula (own bisection Phi^-1), rel err < 1e-9", worst < 1e-9, "worst rel err %.3g" % worst)
c.check("SR0(V, N) > 0 for V > 0, N >= 2", all(metrics.expected_max_sr(1e-3, N) > 0 for N in range(2, 50)))
sys.exit(c.close())
