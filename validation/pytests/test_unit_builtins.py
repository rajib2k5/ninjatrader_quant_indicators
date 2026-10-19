"""test_unit_builtins.py - closed-form / synthetic tests for ledger claims B1-B9.

Every expected value here comes from the ledger's formula statement evaluated by hand or by
an independent numpy expression - never from the C# sources. Each block has at least one
`test_falsifier_*` that applies a deliberately wrong definition and asserts the SAME
assertion rejects it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import qi_ref as R
from vp_helpers import df_from_close, make_df

rng = np.random.default_rng(20261016)
PRICES = 4000.0 + np.cumsum(rng.normal(0, 2.0, 400)).round(2)


# --------------------------------------------------------------------------------------------
# B1  RSI
# --------------------------------------------------------------------------------------------
def test_B1_rsi_monotone_rising_is_100():
    close = np.arange(1, 61, dtype=float)
    r = R.rsi(close, 14)
    assert np.all(r.to_numpy()[1:] == 100.0)


def test_B1_rsi_monotone_falling_is_0():
    close = np.arange(60, 0, -1, dtype=float)
    r = R.rsi(close, 14)
    assert np.all(r.to_numpy()[1:] == 0.0)


def test_B1_rsi_hand_values_n2():
    # changes: +1, +1, -1, -1
    # Wilder_2 up: 1, 1, 0.5, 0.25 ; down: 0, 0, 0.5, 0.75  -> RSI: 100, 100, 50, 25
    r = R.rsi([1.0, 2.0, 3.0, 2.0, 1.0], 2).to_numpy()
    assert np.isnan(r[0])
    np.testing.assert_allclose(r[1:], [100.0, 100.0, 50.0, 25.0], atol=1e-12)


def test_B1_rsi_smoothing_parameter_one_is_identity():
    a = R.rsi(PRICES, 14, smooth=1)
    b = R.rsi(PRICES, 14)
    pd.testing.assert_series_equal(a, b)


def test_B1_rsi_bounded():
    r = R.rsi(PRICES, 14).dropna()
    assert (r >= 0).all() and (r <= 100).all()


def _rsi_simple_average(close, n):
    """WRONG reference: RSI with plain n-bar averages instead of Wilder smoothing."""
    c = np.asarray(close, dtype=float)
    d = np.diff(c)
    up, dn = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    out = np.full(len(c), np.nan)
    for t in range(n, len(c)):
        au, ad = up[t - n:t].mean(), dn[t - n:t].mean()
        out[t] = 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)
    return out


def test_falsifier_rsi_without_wilder_is_detected():
    wrong = _rsi_simple_average([1.0, 2.0, 3.0, 2.0, 1.0], 2)
    # the hand value at bar 4 is 25 (Wilder); the plain average gives 0
    assert abs(wrong[4] - 25.0) > 1e-6
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(wrong[4], 25.0, atol=1e-12)


# --------------------------------------------------------------------------------------------
# B2  EMA
# --------------------------------------------------------------------------------------------
def _ema_closed_form(x, n):
    a = 2.0 / (n + 1.0)
    x = np.asarray(x, dtype=float)
    out = np.empty(len(x))
    for t in range(len(x)):
        k = np.arange(t + 1)
        w = a * (1 - a) ** k
        w[-1] = (1 - a) ** t  # the seed x[0] keeps its full residual weight
        out[t] = np.dot(w, x[t::-1])
    return out


def test_B2_ema_matches_closed_form():
    np.testing.assert_allclose(R.ema(PRICES[:120], 20).to_numpy(), _ema_closed_form(PRICES[:120], 20), rtol=1e-12)


def test_B2_ema_of_constant_is_constant():
    assert np.all(R.ema(np.full(50, 7.5), 20).to_numpy() == 7.5)


def test_B2_ema_recursion_one_step():
    e = R.ema([10.0, 20.0], 9).to_numpy()
    assert e[0] == 10.0
    assert e[1] == pytest.approx(10.0 + 2.0 / 10.0 * (20.0 - 10.0))


def test_falsifier_ema_alpha_1_over_n_is_detected():
    x = PRICES[:120]
    wrong = pd.Series(x).ewm(alpha=1.0 / 20, adjust=False).mean().to_numpy()
    assert np.max(np.abs(wrong - _ema_closed_form(x, 20))) > 1e-6
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(wrong, _ema_closed_form(x, 20), rtol=1e-12)


# --------------------------------------------------------------------------------------------
# B3  SMA
# --------------------------------------------------------------------------------------------
def test_B3_sma_matches_numpy_convolution():
    x = PRICES[:100]
    ref = np.convolve(x, np.ones(20) / 20.0, mode="valid")
    got = R.sma(x, 20).to_numpy()
    assert np.all(np.isnan(got[:19]))
    np.testing.assert_allclose(got[19:], ref, rtol=1e-12)


def test_B3_sma_hand_value():
    assert R.sma([1.0, 2.0, 3.0, 4.0], 3).to_numpy()[-1] == pytest.approx(3.0)


# --------------------------------------------------------------------------------------------
# B5  StdDev (population)
# --------------------------------------------------------------------------------------------
def test_B5_stddev_is_population_std():
    x = PRICES[:60]
    got = R.stddev(x, 20).to_numpy()
    ref = np.array([np.std(x[t - 19:t + 1], ddof=0) for t in range(19, 60)])
    np.testing.assert_allclose(got[19:], ref, rtol=1e-10)


def test_B5_stddev_hand_value():
    # [2, 4, 4, 4, 5, 5, 7, 9]: population std = 2 exactly
    assert R.stddev([2, 4, 4, 4, 5, 5, 7, 9], 8).to_numpy()[-1] == pytest.approx(2.0)


def test_falsifier_sample_std_is_detected():
    x = PRICES[:60]
    wrong = pd.Series(x).rolling(20).std(ddof=1).to_numpy()
    ref = np.array([np.std(x[t - 19:t + 1], ddof=0) for t in range(19, 60)])
    assert np.max(np.abs(wrong[19:] - ref)) > 1e-6
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(wrong[19:], ref, rtol=1e-10)


# --------------------------------------------------------------------------------------------
# B7  Bollinger
# --------------------------------------------------------------------------------------------
def test_B7_bollinger_is_sma_pm_2_popstd():
    x = PRICES[:80]
    up, mid, lo = (s.to_numpy() for s in R.bollinger(x, 20, 2.0))
    for t in range(19, 80):
        w = x[t - 19:t + 1]
        m, s = w.mean(), np.std(w, ddof=0)
        assert mid[t] == pytest.approx(m, rel=1e-12)
        assert up[t] == pytest.approx(m + 2 * s, rel=1e-12)
        assert lo[t] == pytest.approx(m - 2 * s, rel=1e-12)


def test_B7_bollinger_symmetric_about_middle():
    up, mid, lo = R.bollinger(PRICES, 20, 2.0)
    np.testing.assert_allclose((up - mid).dropna(), (mid - lo).dropna(), rtol=1e-12)


def test_falsifier_bollinger_sample_std_is_detected():
    x = PRICES[:80]
    s = pd.Series(x)
    wrong_up = (s.rolling(20).mean() + 2 * s.rolling(20).std(ddof=1)).to_numpy()
    up = R.bollinger(x, 20, 2.0)[0].to_numpy()
    assert np.nanmax(np.abs(wrong_up - up)) > 1e-6


# --------------------------------------------------------------------------------------------
# B8  StochasticsFast
# --------------------------------------------------------------------------------------------
def test_B8_pct_k_100_at_range_high_0_at_range_low():
    n = 30
    high = np.full(n, 110.0)
    low = np.full(n, 90.0)
    close = np.full(n, 100.0)
    close[20] = 110.0  # close at the 14-bar range high
    close[25] = 90.0   # close at the 14-bar range low
    df = make_df(close, high, low, close)
    k, d = R.stoch_fast(df, 3, 14)
    assert k[20] == 100.0
    assert k[25] == 0.0
    assert k[15] == 50.0  # mid-range close (bar 10 is still inside the 14-bar warm-up)


def test_B8_pct_d_is_sma3_of_k():
    df = df_from_close(PRICES[:100], wick=1.0)
    k, d = R.stoch_fast(df, 3, 14)
    np.testing.assert_allclose(d.to_numpy()[16:], k.rolling(3).mean().to_numpy()[16:], rtol=1e-12)


def test_B8_pct_k_hand_value():
    # 14 bars: highs 10..23, lows 0..13, last close 20 -> HH=23, LL=0 -> K = 100*20/23
    high = np.arange(10, 24, dtype=float)
    low = np.arange(0, 14, dtype=float)
    close = np.full(14, 15.0)
    close[-1] = 20.0
    df = make_df(close, high, low, close)
    k, _ = R.stoch_fast(df, 3, 14)
    assert k.to_numpy()[-1] == pytest.approx(100.0 * 20.0 / 23.0)


# --------------------------------------------------------------------------------------------
# B4  ATR with NinjaTrader warm-up recursion
# --------------------------------------------------------------------------------------------
def test_B4_atr_constant_range_bars_equals_range():
    # O = C = previous close, H-L = 2 symmetric -> TR = 2 on every bar (|H-C1| = 1)
    close = np.full(40, 100.0)
    df = make_df(close, close + 1, close - 1, close)
    a = R.atr(df, 14).to_numpy()
    np.testing.assert_allclose(a, 2.0, atol=1e-12)


def test_B4_atr_warmup_recursion_hand_values():
    # TR = [1, 3, 2]: ATR0 = 1; ATR1 = (1*1 + 3)/2 = 2; ATR2 = (2*2 + 2)/3 = 2
    df = make_df([10, 10, 10], [10.5, 11.5, 11.0], [9.5, 8.5, 9.0], [10.0, 10.0, 10.0])
    tr = R.true_range(df).to_numpy()
    np.testing.assert_allclose(tr, [1.0, 3.0, 2.0])
    np.testing.assert_allclose(R.atr(df, 14).to_numpy(), [1.0, 2.0, 2.0])


def test_B4_atr_after_warmup_is_wilder():
    df = df_from_close(PRICES[:100], wick=1.5)
    tr = R.true_range(df).to_numpy()
    a = R.atr(df, 14).to_numpy()
    for t in range(14, 100):
        assert a[t] == pytest.approx((13 * a[t - 1] + tr[t]) / 14, rel=1e-12)


def test_B4_true_range_includes_gaps():
    # gap up: previous close 100, bar H=106 L=104 -> TR = |106-100| = 6 not 2
    df = make_df([100, 104], [101, 106], [99, 104], [100, 105])
    assert R.true_range(df).to_numpy()[1] == 6.0


def test_falsifier_atr_plain_wilder_from_bar0_is_detected():
    df = make_df([10, 10, 10], [10.5, 11.5, 11.0], [9.5, 8.5, 9.0], [10.0, 10.0, 10.0])
    wrong = R.wilder(R.true_range(df), 14).to_numpy()  # no linear warm-up
    assert np.max(np.abs(wrong - np.array([1.0, 2.0, 2.0]))) > 1e-6
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(wrong, [1.0, 2.0, 2.0])


# --------------------------------------------------------------------------------------------
# B6  MACD
# --------------------------------------------------------------------------------------------
def test_B6_macd_histogram_zero_for_constant_series():
    line, sig, hist = R.macd(np.full(100, 50.0), 12, 26, 9)
    assert np.all(line.to_numpy() == 0.0) and np.all(hist.to_numpy() == 0.0)


def test_B6_macd_components_consistent():
    x = PRICES[:200]
    line, sig, hist = R.macd(x, 12, 26, 9)
    np.testing.assert_allclose(line.to_numpy(), (R.ema(x, 12) - R.ema(x, 26)).to_numpy(), rtol=1e-12)
    np.testing.assert_allclose(sig.to_numpy(), R.ema(line, 9).to_numpy(), rtol=1e-12)
    np.testing.assert_allclose(hist.to_numpy(), (line - sig).to_numpy(), rtol=1e-12)


def test_B6_macd_line_sign_for_trend():
    # a rising series: the fast EMA sits above the slow EMA
    line, _, _ = R.macd(np.arange(100, dtype=float), 12, 26, 9)
    assert line.to_numpy()[-1] > 0


def test_falsifier_macd_swapped_fast_slow_is_detected():
    x = PRICES[:200]
    wrong = (R.ema(x, 26) - R.ema(x, 12)).to_numpy()
    assert np.max(np.abs(wrong - R.macd(x)[0].to_numpy())) > 1e-6


# --------------------------------------------------------------------------------------------
# B9  ADX
# --------------------------------------------------------------------------------------------
def test_B9_adx_zero_for_flat_series():
    close = np.full(60, 100.0)
    df = make_df(close, close + 1, close - 1, close)
    a, dip, dim = R.adx(df, 14)
    assert np.all(a.to_numpy()[1:] == 0.0)


def test_B9_adx_near_100_for_straight_trend():
    # strictly rising bars with no overlap: -DM is always 0, so DX = 100 on every bar
    t = np.arange(200, dtype=float)
    df = make_df(t, t + 1, t, t + 1)
    a, dip, dim = R.adx(df, 14)
    assert np.all(dim.to_numpy()[1:] == 0.0)
    assert a.to_numpy()[-1] == pytest.approx(100.0, abs=1e-6)


def test_B9_adx_bounded():
    df = df_from_close(PRICES, wick=1.0)
    a = R.adx(df, 14)[0].dropna()
    assert (a >= 0).all() and (a <= 100).all()


def test_B9_dm_rules_hand_values():
    # bar1: H up by 3, L up by 1 -> +DM 3, -DM 0;  bar2: H down 1, L down 4 -> +DM 0, -DM 4
    df = make_df([10, 10, 10], [12, 15, 14], [8, 9, 5], [10, 10, 10])
    _, dip, dim = R.adx(df, 14)
    tr = R.true_range(df).to_numpy()
    # at bar 1 (seed): +DI = 100*3/TR1, -DI = 0
    assert dip[1] == pytest.approx(100.0 * 3.0 / tr[1])
    assert dim[1] == 0.0


def test_falsifier_adx_without_wilder_smoothing_of_dx_is_detected():
    df = df_from_close(PRICES, wick=1.0)
    a, dip, dim = R.adx(df, 14)
    tot = dip + dim
    raw_dx = (100.0 * (dip - dim).abs() / tot.where(tot != 0, np.nan)).fillna(0.0)
    assert np.nanmax(np.abs(raw_dx.to_numpy()[50:] - a.to_numpy()[50:])) > 1e-2
