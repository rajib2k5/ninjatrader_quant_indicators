"""_cb.py - shared helpers for the Channel B backtest probes (validation/probes/channel_b_backtest).

Every probe is run as   python -I -B <probe>.py [--qibt-root DIR]
-I drops the script directory from sys.path, so each probe inserts its own directory first and
then calls use_qibt(), which (optionally) puts a MUTANT copy of the qibt package first on sys.path.

Nothing here imports or reads qibt for expected values: the reference maths below (Phi, Phi^-1,
Sharpe, moments, PSR, SR0) is written from backtest/PROTOCOL.md and the frozen ledger only.
"""
from __future__ import annotations

import math
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
QI_REF_DIR = os.path.join(REPO, "validation", "pytests")
EULER_GAMMA = 0.57721566490153286060651209  # Euler-Mascheroni constant (ledger BT11)


def use_qibt(need_qi_ref=False):
    """Honour --qibt-root DIR (mutant package root); return the imported qibt package."""
    if "--qibt-root" in sys.argv:
        i = sys.argv.index("--qibt-root")
        root = sys.argv[i + 1]
        del sys.argv[i:i + 2]
        sys.path.insert(0, os.path.abspath(root))
    if need_qi_ref and QI_REF_DIR not in sys.path:
        sys.path.append(QI_REF_DIR)
    import qibt
    print("qibt loaded from: %s" % qibt.__file__)
    return qibt


class Checker:
    """Collects named checks; exit code 0 only if every check passed."""

    def __init__(self, title):
        self.title = title
        self.n = 0
        self.fail = []
        print("=== %s ===" % title)

    def check(self, name, ok, detail=""):
        self.n += 1
        tag = "PASS" if ok else "FAIL"
        print("[%s] %s%s" % (tag, name, (" | " + detail) if detail else ""))
        if not ok:
            self.fail.append(name)
        return ok

    def close(self):
        print("--- %s: %d checks, %d failed%s" % (
            self.title, self.n, len(self.fail), (": " + "; ".join(self.fail)) if self.fail else ""))
        return 0 if not self.fail else 1


# ---------------------------------------------------------------------------------------------
# reference maths (from PROTOCOL section 7 / ledger BT9-BT12), float64, stdlib only
# ---------------------------------------------------------------------------------------------
def phi(x):
    """Standard normal CDF via erfc (no cancellation in the lower tail)."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def phi_inv(p, lo=-40.0, hi=40.0):
    """Inverse standard normal CDF by bisection on phi (independent of statistics.NormalDist)."""
    if not 0.0 < p < 1.0:
        raise ValueError(p)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if phi(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def mean(a):
    return math.fsum(a) / len(a)


def std_ddof1(a):
    m = mean(a)
    return math.sqrt(math.fsum((x - m) ** 2 for x in a) / (len(a) - 1))


def sr_daily(a):
    if len(a) < 2:
        return math.nan
    s = std_ddof1(a)
    return mean(a) / s if s > 0 else math.nan


def sr_annual(a, periods=252):
    return sr_daily(a) * math.sqrt(periods)


def skew_kurt(a):
    """Sample skewness m3/m2^1.5 and NON-excess kurtosis m4/m2^2 (moment estimators)."""
    m = mean(a)
    d = [x - m for x in a]
    m2 = math.fsum(x * x for x in d) / len(a)
    m3 = math.fsum(x ** 3 for x in d) / len(a)
    m4 = math.fsum(x ** 4 for x in d) / len(a)
    if not m2 > 0:
        return math.nan, math.nan
    return m3 / m2 ** 1.5, m4 / m2 ** 2


def psr_ref(sr, sr_star, n, g3, g4):
    """Ledger BT10: Phi((SR - SR*) sqrt(n-1) / sqrt(1 - g3 SR + (g4 - 1)/4 SR^2))."""
    rad = 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr * sr
    return phi((sr - sr_star) * math.sqrt(n - 1) / math.sqrt(rad))


def sr0_ref(var_sr, n_trials):
    """Ledger BT11: sqrt(V) ((1-g) Phi^-1(1 - 1/N) + g Phi^-1(1 - 1/(N e)))."""
    g = EULER_GAMMA
    return math.sqrt(var_sr) * ((1.0 - g) * phi_inv(1.0 - 1.0 / n_trials)
                                + g * phi_inv(1.0 - 1.0 / (n_trials * math.e)))


def load_p1_frame(argv):
    """The P1 1-minute frame: --pkl PATH (e.g. Channel B's own raw re-parse) or qibt.data.load_p1()
    (the cached loaded P1). Returns (df, source)."""
    import pandas as pd
    if "--pkl" in argv:
        i = argv.index("--pkl")
        p = argv[i + 1]
        del argv[i:i + 2]
        return pd.read_pickle(p), "pickle %s" % p
    from qibt import data
    df = data.load_p1()
    return df, "qibt.data.load_p1() cache=%s" % df.attrs.get("info", {}).get("cache")


def trading_dates_ns(bar_ns):
    """PROTOCOL 3: calendar date of the close time, +1 day if the close time is after 17:00.
    bar_ns: int64 nanoseconds of naive Central wall-clock times. Returns int64 ns of midnight."""
    import numpy as np
    day = np.int64(86_400_000_000_000)
    b = np.asarray(bar_ns, dtype=np.int64)
    mid = (b // day) * day
    tod = b - mid
    return mid + np.where(tod > np.int64(17 * 3_600_000_000_000), day, np.int64(0))


def mdd_ref(a):
    """Ledger BT12 with the equity curve starting at 0 before the first day."""
    cum, peak, worst = 0.0, 0.0, 0.0
    for x in a:
        cum += x
        peak = max(peak, cum)
        worst = max(worst, peak - cum)
    return worst
