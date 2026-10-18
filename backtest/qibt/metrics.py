"""metrics.py - PROTOCOL section 7 and ledger BT9-BT12 (no scipy).

Phi(z) = 0.5*erfc(-z/sqrt 2) (accurate down to ~1e-300; the 0.5*(1 + erf) form used by
statistics.NormalDist cancels to exactly 0.0 below z ~ -8.26). log Phi has an asymptotic tail below
z = -37, so DSRs that underflow still order correctly. Phi^-1 = statistics.NormalDist().inv_cdf.

SR      = mean(daily) / std(daily, ddof=1) * sqrt(252)                         (BT9)
PSR(S*) = Phi((SR - S*) * sqrt(n-1) / sqrt(1 - g3*SR + (g4-1)/4 * SR^2))        (BT10)
          SR per day (not annualised), g3 = sample skewness, g4 = non-excess kurtosis
DSR     = PSR(SR0), SR0 = sqrt(V) * ((1-gamma) Phi^-1(1-1/N) + gamma Phi^-1(1-1/(N e)))  (BT11)
MDD     = max_t (running max of cumulative P&L - cumulative P&L), equity starting at 0 (BT12)
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

EULER_GAMMA = 0.5772156649015329
ANNUALISATION = 252
_N = NormalDist()


def _arr(x):
    return np.asarray(x, dtype=float).reshape(-1)


def sharpe_daily(x):
    """Per-period SR = mean / std(ddof=1); NaN if fewer than 2 values or zero variance."""
    a = _arr(x)
    if len(a) < 2:
        return math.nan
    sd = float(np.std(a, ddof=1))
    if not sd > 0:
        return math.nan
    return float(np.mean(a)) / sd


def sharpe(x, periods=ANNUALISATION):
    return sharpe_daily(x) * math.sqrt(periods)


def moments(x):
    """(skewness, non-excess kurtosis) with the biased moment estimators m3/m2^1.5, m4/m2^2."""
    a = _arr(x)
    d = a - a.mean()
    m2 = float(np.mean(d ** 2))
    if not m2 > 0:
        return math.nan, math.nan
    return float(np.mean(d ** 3)) / m2 ** 1.5, float(np.mean(d ** 4)) / m2 ** 2


_SQRT2 = math.sqrt(2.0)
_LOG_SQRT_2PI = 0.5 * math.log(2.0 * math.pi)
LOG_TAIL_Z = -37.0


def norm_cdf(z):
    """Standard normal CDF via erfc (no cancellation in the lower tail)."""
    return 0.5 * math.erfc(-z / _SQRT2)


def log_norm_cdf(z):
    """log Phi(z); below z = -37 the asymptotic series
    log Phi(z) = -z^2/2 - log(-z) - log sqrt(2 pi) + log(1 - 1/z^2 + 3/z^4 - 15/z^6)."""
    if not math.isfinite(z):
        return 0.0 if z > 0 else (-math.inf if z < 0 else math.nan)
    if z >= LOG_TAIL_Z:
        return math.log(norm_cdf(z))
    z2 = z * z
    return -0.5 * z2 - math.log(-z) - _LOG_SQRT_2PI + math.log1p(-1.0 / z2 + 3.0 / z2 ** 2 - 15.0 / z2 ** 3)


def psr_z(sr, sr_star, n, skew, kurt):
    """The PSR argument (SR - S*) sqrt(n-1) / sqrt(1 - g3 SR + (g4-1)/4 SR^2); NaN when undefined."""
    vals = (sr, sr_star, skew, kurt)
    if n < 2 or any(v is None or not math.isfinite(v) for v in vals):
        return math.nan
    rad = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if not rad > 0:
        return math.nan
    return (sr - sr_star) * math.sqrt(n - 1) / math.sqrt(rad)


def psr(sr, sr_star, n, skew, kurt):
    """Probabilistic Sharpe Ratio on per-period SRs; NaN when undefined."""
    z = psr_z(sr, sr_star, n, skew, kurt)
    return norm_cdf(z) if math.isfinite(z) else math.nan


def log_psr(sr, sr_star, n, skew, kurt):
    """log PSR (keeps the order of PSR/DSR values that underflow to 0.0)."""
    z = psr_z(sr, sr_star, n, skew, kurt)
    return log_norm_cdf(z) if math.isfinite(z) else math.nan


def psr_of(x, sr_star=0.0):
    a = _arr(x)
    sk, ku = moments(a)
    return psr(sharpe_daily(a), sr_star, len(a), sk, ku)


def expected_max_sr(var_sr, n_trials):
    """SR0 of the Deflated Sharpe Ratio (per-period units, like var_sr)."""
    if n_trials < 2:
        raise ValueError("DSR needs N >= 2 trials")
    if var_sr is None or not math.isfinite(var_sr) or var_sr < 0:
        return math.nan
    g = EULER_GAMMA
    z = (1.0 - g) * _N.inv_cdf(1.0 - 1.0 / n_trials) + g * _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(var_sr) * z


def dsr_of(x, var_sr, n_trials):
    return psr_of(x, expected_max_sr(var_sr, n_trials))


def max_drawdown(x):
    """Largest fall of cumulative P&L from its running peak; the equity curve starts at 0."""
    a = _arr(x)
    if len(a) == 0:
        return 0.0
    cum = np.concatenate([[0.0], np.cumsum(a)])
    return float(np.max(np.maximum.accumulate(cum) - cum))


def correlation(x, y):
    a, b = _arr(x), _arr(y)
    if len(a) < 2 or not (np.std(a) > 0 and np.std(b) > 0):
        return math.nan
    return float(np.corrcoef(a, b)[0, 1])


def sample_variance(values):
    """Sample variance (ddof=1) of the finite values; NaN if fewer than 2."""
    v = _arr(values)
    v = v[np.isfinite(v)]
    return float(np.var(v, ddof=1)) if len(v) >= 2 else math.nan
