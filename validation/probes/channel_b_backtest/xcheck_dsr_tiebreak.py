"""PROTOCOL 8 tie-break check on the committed results (no qibt import).

For every adjacent pair in results/ranking.csv with |dSR| < 0.005, recompute DSR from the committed
metrics_P1.csv columns (sr_daily, n_days, skew, kurt; N = 25; V = sample variance of the 25 sr_daily)
with scipy.stats.norm (cdf / logcdf, accurate in the far lower tail) and report whether the committed
order follows "higher DSR, then module name A->Z". Also reports where statistics.NormalDist().cdf
(the stdlib normal CDF) first returns exactly 0.0.
Usage: python -I -B xcheck_dsr_tiebreak.py [--results DIR]   exit 1 if a tie pair is ordered against the true DSR
"""
from __future__ import annotations

import math
import os
import sys
from statistics import NormalDist

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402

rdir = os.path.join(_cb.REPO, "results")
if "--results" in sys.argv:
    i = sys.argv.index("--results"); rdir = sys.argv[i + 1]
m = pd.read_csv(os.path.join(rdir, "metrics_P1.csv")).set_index("module")
rk = pd.read_csv(os.path.join(rdir, "ranking.csv"))
rules = m.drop(index="BuyHold")
V = float(np.var(rules["sr_daily"].to_numpy(), ddof=1))
N = len(rules)
g = _cb.EULER_GAMMA
sr0 = math.sqrt(V) * ((1 - g) * norm.ppf(1 - 1 / N) + g * norm.ppf(1 - 1 / (N * math.e)))
print("N = %d, V[SR per day] = %.9f, SR0 per day = %.9f" % (N, V, sr0))


def z_of(mod):
    r = m.loc[mod]
    s = r["sr_daily"]
    rad = 1 - r["skew"] * s + (r["kurt"] - 1) / 4 * s * s
    return (s - sr0) * math.sqrt(r["n_days"] - 1) / math.sqrt(rad)


ok = rk[rk["status"] == "ok"].sort_values("rank")
bad = 0
for (_, a), (_, b) in zip(ok.iterrows(), list(ok.iterrows())[1:]):
    if abs(a["sr"] - b["sr"]) < 0.005:
        za, zb = z_of(a["module"]), z_of(b["module"])
        print("tie pair rank %d %s (SR %.6f) / rank %d %s (SR %.6f): |dSR| = %.6f" % (
            a["rank"], a["module"], a["sr"], b["rank"], b["module"], b["sr"], abs(a["sr"] - b["sr"])))
        for mod, z in ((a["module"], za), (b["module"], zb)):
            print("   %-12s z = %.6f  DSR(scipy cdf) = %.6e  log DSR = %.4f  NormalDist.cdf = %r  committed dsr = %r"
                  % (mod, z, norm.cdf(z), norm.logcdf(z), NormalDist().cdf(z), m.loc[mod, "dsr"]))
        first = a["module"] if za > zb or (za == zb and a["module"] < b["module"]) else b["module"]
        follows = first == a["module"]
        print("   PROTOCOL 8 (higher DSR, then A->Z) puts %s first; committed order %s" % (
            first, "follows it" if follows else "does NOT follow it"))
        bad += 0 if follows else 1
zero = max(x / 100 for x in range(-1000, 0) if NormalDist().cdf(x / 100) == 0.0)
print("statistics.NormalDist().cdf(x) == 0.0 for x <= %.2f (scipy norm.cdf(%.2f) = %.3e)" % (zero, zero, norm.cdf(zero)))
print("committed dsr values: %s" % sorted(set(m["dsr"].dropna())))
sys.exit(1 if bad else 0)
