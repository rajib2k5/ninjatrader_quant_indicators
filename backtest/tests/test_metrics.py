"""Sharpe, PSR, DSR, max drawdown (PROTOCOL section 7, ledger BT9-BT12)."""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pytest

from qibt import metrics as M

PHI = NormalDist().cdf
PHI_INV = NormalDist().inv_cdf


def test_sharpe_matches_numpy():
    x = np.random.default_rng(10).normal(3.0, 40.0, 1300)
    want = np.mean(x) / np.std(x, ddof=1) * np.sqrt(252)
    assert M.sharpe(x) == pytest.approx(want, rel=1e-12)
    assert M.sharpe_daily(x) == pytest.approx(np.mean(x) / np.std(x, ddof=1), rel=1e-12)


def check_sharpe(fn):
    """[1,2,3,4]: mean 2.5, std(ddof=1) = sqrt(5/3) = 1.2909944..., SR = 2.5/1.2909944*sqrt(252)."""
    want = 2.5 / math.sqrt(5.0 / 3.0) * math.sqrt(252)          # 30.74085...
    return abs(fn([1.0, 2.0, 3.0, 4.0]) - want) < 1e-9


def test_sharpe_hand_value():
    assert check_sharpe(M.sharpe)


def test_sharpe_undefined_cases():
    assert math.isnan(M.sharpe([5.0, 5.0, 5.0])) and math.isnan(M.sharpe([1.0])) and math.isnan(M.sharpe([]))


def test_sharpe_scale_invariance_and_sign():
    x = np.random.default_rng(11).normal(1, 10, 500)
    assert M.sharpe(7.5 * x) == pytest.approx(M.sharpe(x), rel=1e-12)
    assert M.sharpe(-x) == pytest.approx(-M.sharpe(x), rel=1e-12)


def test_moments_hand_value():
    # x = [0, 0, 0, 4]: mean 1, d = [-1,-1,-1,3]; m2 = 3, m3 = 6, m4 = 21
    sk, ku = M.moments([0.0, 0.0, 0.0, 4.0])
    assert sk == pytest.approx(6 / 3 ** 1.5) and ku == pytest.approx(21 / 9)


def test_moments_normal_sample_is_non_excess():
    sk, ku = M.moments(np.random.default_rng(12).normal(0, 1, 200_000))
    assert abs(sk) < 0.02 and abs(ku - 3.0) < 0.05


def check_psr(fn):
    """SR=0.1, SR*=0, n=101, skew 0, kurt 3 (normal): z = 0.1*10/sqrt(1 + 2/4*0.01) = 0.997509."""
    want = PHI(1.0 / math.sqrt(1.005))
    return abs(fn(0.1, 0.0, 101, 0.0, 3.0) - want) < 1e-12


def test_psr_hand_value():
    assert check_psr(M.psr)


def test_psr_is_half_when_sr_equals_benchmark():
    assert M.psr(0.08, 0.08, 500, -0.7, 6.0) == 0.5
    x = np.random.default_rng(13).normal(0.5, 10, 800)
    assert M.psr_of(x, M.sharpe_daily(x)) == pytest.approx(0.5, abs=1e-15)


def test_psr_increases_with_n():
    vals = [M.psr(0.05, 0.0, n, -0.5, 5.0) for n in (50, 100, 250, 1000, 5000)]
    assert all(b > a for a, b in zip(vals, vals[1:]))


def test_expected_max_sr_hand_value():
    g = M.EULER_GAMMA
    want = 2.0 * ((1 - g) * PHI_INV(1 - 1 / 100) + g * PHI_INV(1 - 1 / (100 * math.e)))
    assert M.expected_max_sr(4.0, 100) == pytest.approx(want, rel=1e-12)
    assert M.EULER_GAMMA == 0.5772156649015329


def test_dsr_paper_numeric_example():
    """Bailey & Lopez de Prado (2014) example: annual SR 2.5, T = 1250 days, N = 100,
    V[SR] = 1/2 (annual), skew -3, kurt 10, 250 days a year -> SR0 = 0.1132/day, DSR = 0.9004."""
    sr, v = 2.5 / math.sqrt(250), 0.5 / 250
    sr0 = M.expected_max_sr(v, 100)
    assert sr0 == pytest.approx(0.1132, abs=5e-5)
    assert M.psr(sr, sr0, 1250, -3.0, 10.0) == pytest.approx(0.9004, abs=5e-4)


def test_dsr_le_psr0_and_decreasing_in_n():
    x = np.random.default_rng(14).normal(2.0, 30.0, 1300)
    p0 = M.psr_of(x, 0.0)
    ds = [M.dsr_of(x, 0.002, n) for n in (2, 5, 10, 25, 50, 100, 1000)]
    assert all(d <= p0 for d in ds)
    assert all(b < a for a, b in zip(ds, ds[1:]))
    with pytest.raises(ValueError):
        M.expected_max_sr(0.002, 1)


@pytest.mark.parametrize("x,want", [
    ([1, 2, 3], 0.0),                    # monotone up
    ([], 0.0),
    ([1, -2, 1, -3, 5], 4.0),            # cum 1,-1,0,-3,2 ; peak 1 -> -3
    ([-1, -1], 2.0),                     # equity starts at 0
    ([5, -5], 5.0),
    ([-5, 10], 5.0),
    ([3, -1, 4, -6, 2, -1], 6.0),        # cum 3,2,6,0,2,1 ; peak 6 -> 0
])
def test_max_drawdown_hand_cases(x, want):
    assert M.max_drawdown(x) == want


def test_max_drawdown_scales():
    x = np.random.default_rng(15).normal(0, 5, 300)
    assert M.max_drawdown(3 * x) == pytest.approx(3 * M.max_drawdown(x))


def test_correlation_and_sample_variance():
    x = np.arange(10.0)
    assert M.correlation(x, 2 * x + 1) == pytest.approx(1.0)
    assert math.isnan(M.correlation(x, np.ones(10)))
    assert M.sample_variance([1.0, 2.0, 3.0, math.nan]) == pytest.approx(1.0)


# --------------------------------------------------------------------------------------------
# falsifiers
# --------------------------------------------------------------------------------------------
def test_falsifier_population_std_sharpe_is_detected():
    assert not check_sharpe(lambda x: np.mean(x) / np.std(x, ddof=0) * np.sqrt(252))


def test_falsifier_unannualised_sharpe_is_detected():
    assert not check_sharpe(M.sharpe_daily)


def test_falsifier_range_drawdown_is_detected():
    def rng_dd(x):
        c = np.cumsum(x)
        return float(c.max() - c.min())
    assert rng_dd([-5, 10]) != M.max_drawdown([-5, 10])


def test_falsifier_excess_kurtosis_in_psr_is_detected():
    assert not check_psr(lambda sr, s, n, sk, ku: M.psr(sr, s, n, sk, ku - 3.0))


# --------------------------------------------------------------------------------------------
# lower tail of Phi (Channel B finding F2: the erf form cancels to 0.0 below z ~ -8.26)
# --------------------------------------------------------------------------------------------
def test_norm_cdf_lower_tail():
    assert M.norm_cdf(-10.0) == pytest.approx(7.619853024160527e-24, rel=1e-6)
    assert M.norm_cdf(0.0) == 0.5 and M.norm_cdf(1.959963984540054) == pytest.approx(0.975, rel=1e-12)
    assert M.norm_cdf(-37.0) > 0.0


def test_norm_cdf_monotone_on_minus35_to_5():
    z = np.linspace(-35.0, 5.0, 4001)
    v = np.array([M.norm_cdf(x) for x in z])
    assert (v > 0).all() and (np.diff(v) > 0).all()


def test_log_norm_cdf_tail_is_continuous_and_monotone():
    exact = math.log(M.norm_cdf(M.LOG_TAIL_Z))
    asym = -0.5 * 37.0 ** 2 - math.log(37.0) - 0.5 * math.log(2 * math.pi) + math.log1p(-1 / 37.0 ** 2 + 3 / 37.0 ** 4 - 15 / 37.0 ** 6)
    assert asym == pytest.approx(exact, rel=1e-12)
    z = np.linspace(-80.0, 5.0, 3000)
    lv = np.array([M.log_norm_cdf(x) for x in z])
    assert np.isfinite(lv).all() and (np.diff(lv) > 0).all()
    assert M.log_norm_cdf(-10.0) == pytest.approx(math.log(7.619853024160527e-24), rel=1e-9)


def test_dsr_values_that_underflowed_now_order():
    """V[SR] large (P1-like): DSRs are ~1e-58 and must differ, not collapse to 0."""
    x1 = np.random.default_rng(16).normal(4.0, 50.0, 1320)
    x2 = x1 * 0.98 + np.random.default_rng(17).normal(0.0, 5.0, 1320)
    d1, d2 = M.dsr_of(x1, 0.0552, 25), M.dsr_of(x2, 0.0552, 25)
    assert 0.0 < d1 < 1e-20 and 0.0 < d2 < 1e-20 and d1 != d2
    sk, ku = M.moments(x1)
    assert M.log_psr(M.sharpe_daily(x1), M.expected_max_sr(0.0552, 25), 1320, sk, ku) == pytest.approx(math.log(d1), rel=1e-9)


def test_falsifier_erf_form_cdf_underflows():
    erf_form = lambda z: 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    assert erf_form(-10.0) == 0.0 and NormalDist().cdf(-10.0) == 0.0
    assert M.norm_cdf(-10.0) > 0.0
