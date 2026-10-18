"""BT10: PSR(SR*) = Phi((SR - SR*) sqrt(n-1) / sqrt(1 - g3 SR + (g4 - 1)/4 SR^2)),
SR per period (not annualised), g3 sample skewness, g4 NON-excess kurtosis.

Pre-registered: PSR = 0.5 when SR = SR*; PSR increases with n (paper example not available).
Added: numeric fixtures against the ledger formula (reference in _cb.psr_ref, Phi via erfc), and
the moment conventions (non-excess kurtosis). Usage: python -I -B bt10_psr.py [--qibt-root DIR]
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

c = _cb.Checker("BT10 PSR")
# property 1: PSR = 0.5 when SR = SR*
vals = [metrics.psr(s, s, n, g3, g4) for s in (-0.2, 0.0, 0.05, 0.3) for n in (10, 252, 5000)
        for g3, g4 in ((0.0, 3.0), (-1.0, 8.0), (0.7, 4.5))]
c.check("PSR(SR*=SR) == 0.5 (36 combos)", all(abs(v - 0.5) < 1e-15 for v in vals),
        "range [%r, %r]" % (min(vals), max(vals)))
# property 2: increases with n when SR > SR*, decreases when SR < SR*
ns = list(range(3, 3000, 17))
up = [metrics.psr(0.06, 0.0, n, -0.3, 6.0) for n in ns]
dn = [metrics.psr(-0.06, 0.0, n, -0.3, 6.0) for n in ns]
c.check("SR > SR*: PSR strictly increasing in n (until it saturates at 1.0)",
        all(b > a or (a == 1.0 and b == 1.0) for a, b in zip(up, up[1:])), "first/last %r / %r" % (up[0], up[-1]))
c.check("SR < SR*: PSR strictly decreasing in n (until 0.0)",
        all(b < a or (a == 0.0 and b == 0.0) for a, b in zip(dn, dn[1:])), "first/last %r / %r" % (dn[0], dn[-1]))
# numeric fixtures against the ledger formula
fx = [(0.1, 0.0, 253, -0.5, 5.0), (0.05, 0.02, 1320, 1.36, 39.0), (-0.03, 0.0, 1320, -1.8, 109.8),
      (0.2, 0.1, 60, 0.0, 3.0), (0.0532, 0.0, 1320, 0.3, 12.0)]
for sr, ss, n, g3, g4 in fx:
    ref = _cb.psr_ref(sr, ss, n, g3, g4)
    got = metrics.psr(sr, ss, n, g3, g4)
    c.check("psr(%g, %g, n=%d, g3=%g, g4=%g) == ledger formula %.12f" % (sr, ss, n, g3, g4, ref),
            abs(got - ref) < 1e-12, "got %.15f" % got)
# moment conventions: two-point +-1 distribution -> skew 0, non-excess kurtosis exactly 1
sk, ku = metrics.moments([-1.0, 1.0] * 50)
c.check("moments([-1,1]*50) == (0, 1) (non-excess kurtosis)", abs(sk) < 1e-15 and abs(ku - 1.0) < 1e-15,
        "got (%r, %r)" % (sk, ku))
rng = np.random.default_rng(11)
z = rng.normal(0, 1, 400000)
sk, ku = metrics.moments(z)
c.check("normal sample: kurtosis ~ 3 (non-excess), |skew| < 0.02", abs(ku - 3.0) < 0.05 and abs(sk) < 0.02,
        "got skew %.4f kurt %.4f" % (sk, ku))
a = rng.standard_t(5, 300) * 40 + 3
r_sk, r_ku = _cb.skew_kurt(list(a))
sk, ku = metrics.moments(a)
c.check("moments == m3/m2^1.5, m4/m2^2 on a t5 sample", abs(sk - r_sk) < 1e-12 and abs(ku - r_ku) < 1e-10,
        "got (%.12f, %.12f) ref (%.12f, %.12f)" % (sk, ku, r_sk, r_ku))
# psr_of uses the PER-PERIOD SR, not the annualised one
ref = _cb.psr_ref(_cb.sr_daily(list(a)), 0.0, len(a), r_sk, r_ku)
c.check("psr_of(x) == formula on per-day SR", abs(metrics.psr_of(a) - ref) < 1e-12,
        "got %.15f ref %.15f" % (metrics.psr_of(a), ref))
sys.exit(c.close())
