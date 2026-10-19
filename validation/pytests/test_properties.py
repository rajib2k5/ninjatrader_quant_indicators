"""test_properties.py - trading-domain invariants of the ledger formulas (hypothesis).

Bars are generated on a 0.25 tick grid so that price shifts by whole ticks and scalings by
powers of two are exact in binary floating point; the remaining tolerances cover genuinely
inexact scalings (x3, x10, x0.1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

import qi_ref as R
from vp_helpers import df_from_close, make_df

SETTINGS = dict(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
# Bounds are mathematical; the references do not clamp (the ledger defines no clamp for RSI,
# %K or ADX), so allow floating-point rounding of 1e-9 (observed: ADX = 100 + 1.4e-14).
FP = 1e-9


def within(s, lo, hi):
    s = pd.Series(s).dropna()
    return ((s >= lo - FP) & (s <= hi + FP)).all()


# --------------------------------------------------------------------------------------------
# strategies
# --------------------------------------------------------------------------------------------
@st.composite
def bars(draw, min_bars=30, max_bars=70):
    n = draw(st.integers(min_bars, max_bars))
    ticks = draw(st.lists(st.integers(-40, 40), min_size=n, max_size=n))
    up_w = draw(st.lists(st.integers(0, 12), min_size=n, max_size=n))
    dn_w = draw(st.lists(st.integers(0, 12), min_size=n, max_size=n))
    vol = draw(st.lists(st.integers(0, 1000), min_size=n, max_size=n))
    close = 4000.0 + np.cumsum(ticks) * 0.25
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) + np.asarray(up_w) * 0.25
    low = np.minimum(open_, close) - np.asarray(dn_w) * 0.25
    return make_df(open_, high, low, close, np.asarray(vol, dtype=float))


SCALES = st.sampled_from([0.5, 2.0, 4.0, 0.25, 3.0, 10.0, 0.1])
SHIFTS = st.sampled_from([1.0, -1.0, 250.0, -250.0, 1000.0])


def scaled(df, k):
    out = df.copy()
    for c in ("Open", "High", "Low", "Close"):
        out[c] = out[c] * k
    return out


def shifted(df, c):
    out = df.copy()
    for col in ("Open", "High", "Low", "Close"):
        out[col] = out[col] + c
    return out


def same(a, b, rtol=1e-9, atol=1e-9):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    assert a.shape == b.shape
    nan_a, nan_b = np.isnan(a), np.isnan(b)
    assert np.array_equal(nan_a, nan_b), "NaN pattern differs"
    np.testing.assert_allclose(a[~nan_a], b[~nan_b], rtol=rtol, atol=atol)


# --------------------------------------------------------------------------------------------
# range invariants
# --------------------------------------------------------------------------------------------
@settings(**SETTINGS)
@given(bars())
def test_rsi_in_0_100(df):
    for n in (2, 14):
        assert within(R.rsi(df["Close"], n), 0, 100)


@settings(**SETTINGS)
@given(bars())
def test_pct_k_in_0_100(df):
    k, d = R.stoch_fast(df, 3, 14)
    assert within(k, 0, 100) and within(d, 0, 100)


@settings(**SETTINGS)
@given(bars())
def test_ibs_in_0_1(df):
    for s in (R.ibs_bar(df), R.ibs_daily(df, "trading"), R.ibs_daily(df, "calendar")):
        assert within(s, 0, 1)


@settings(**SETTINGS)
@given(bars())
def test_chop_in_0_100_and_adx_bounded(df):
    assert within(R.chop(df), 0, 100)          # CHOP is clamped by the ledger: exact bounds
    assert ((R.chop(df) >= 0) & (R.chop(df) <= 100)).all()
    assert within(R.adx(df, 14)[0], 0, 100)


@settings(**SETTINGS)
@given(bars(min_bars=110, max_bars=130))
def test_crsi_in_0_100(df):
    assert within(R.connors_rsi(df["Close"]), 0, 100)


@settings(**SETTINGS)
@given(bars())
def test_hp_clamps_respected(df):
    b, s = R.hp_basis_term(df).dropna(), R.hp_slope_term(df).dropna()
    assert ((b >= -25) & (b <= 25)).all() and ((s >= -25) & (s <= 25)).all()
    tot = R.hp_clamp_total(R.hp_basis_term(df).fillna(0), R.hp_slope_term(df).fillna(0), 30 * np.ones(len(df)), -60 * np.ones(len(df)))
    assert np.all((tot >= -100) & (tot <= 100))


@settings(**SETTINGS)
@given(bars())
def test_consec_streak_changes_by_at_most_one_and_sign_follows_close(df):
    s = R.consec_days(df["Close"]).to_numpy()
    c = df["Close"].to_numpy()
    for t in range(1, len(c)):
        if c[t] > c[t - 1]:
            assert s[t] >= 1 and (s[t] == s[t - 1] + 1 or s[t] == 1)
        elif c[t] < c[t - 1]:
            assert s[t] <= -1 and (s[t] == s[t - 1] - 1 or s[t] == -1)
        else:
            assert s[t] == s[t - 1]


# --------------------------------------------------------------------------------------------
# scale invariance  (multiply O/H/L/C by k > 0)
# --------------------------------------------------------------------------------------------
@settings(**SETTINGS)
@given(bars(), SCALES)
def test_scale_invariant_modules(df, k):
    dk = scaled(df, k)
    same(R.rsi(df["Close"], 14), R.rsi(dk["Close"], 14), atol=1e-7)
    same(R.rsi(df["Close"], 2), R.rsi(dk["Close"], 2), atol=1e-7)
    same(R.ibs_bar(df), R.ibs_bar(dk), atol=1e-9)
    same(R.ibs_daily(df), R.ibs_daily(dk), atol=1e-9)
    same(R.pct_b(df["Close"]), R.pct_b(dk["Close"]), rtol=1e-7, atol=1e-6)
    same(R.stoch_fast(df)[0], R.stoch_fast(dk)[0], atol=1e-7)
    same(R.chop(df), R.chop(dk), atol=1e-7)
    same(R.consec_days(df["Close"]), R.consec_days(dk["Close"]), atol=0)
    same(R.gap_pct(df), R.gap_pct(dk), rtol=1e-9, atol=1e-9)
    same(R.wide_range(df), R.wide_range(dk), rtol=1e-9)
    same(R.vrp_proxy(df), R.vrp_proxy(dk), rtol=1e-9)
    same(R.atr_regime(df), R.atr_regime(dk), rtol=1e-9)
    same(R.vwap_distance(df), R.vwap_distance(dk), rtol=1e-9, atol=1e-9)


@settings(**SETTINGS)
@given(bars(), SCALES)
def test_scale_equivariant_modules(df, k):
    dk = scaled(df, k)
    same(R.vwap(dk), k * R.vwap(df), rtol=1e-9)
    same(R.ema(dk["Close"], 20), k * R.ema(df["Close"], 20), rtol=1e-9)
    same(R.sma(dk["Close"], 20), k * R.sma(df["Close"], 20), rtol=1e-9)
    up, mid, lo = R.bollinger(df["Close"])
    upk, midk, lok = R.bollinger(dk["Close"])
    same(upk, k * up, rtol=1e-9)
    same(lok, k * lo, rtol=1e-9)
    same(R.atr(dk, 14), k * R.atr(df, 14), rtol=1e-9)
    same(R.macd_hist(dk["Close"]), k * R.macd_hist(df["Close"]), rtol=1e-9, atol=1e-9)


# --------------------------------------------------------------------------------------------
# shift invariance (constant price offset c)
# --------------------------------------------------------------------------------------------
@settings(**SETTINGS)
@given(bars(), SHIFTS)
def test_shift_invariant_modules(df, c):
    dc = shifted(df, c)
    same(R.rsi(df["Close"], 14), R.rsi(dc["Close"], 14), atol=1e-9)
    same(R.stoch_fast(df)[0], R.stoch_fast(dc)[0], atol=1e-9)
    same(R.chop(df), R.chop(dc), atol=1e-9)
    same(R.ibs_bar(df), R.ibs_bar(dc), atol=1e-9)
    same(R.atr(df, 14), R.atr(dc, 14), atol=1e-9)
    same(R.macd_hist(df["Close"]), R.macd_hist(dc["Close"]), atol=1e-7)
    same(R.pct_b(df["Close"]), R.pct_b(dc["Close"]), rtol=1e-7, atol=1e-6)
    same(R.consec_days(df["Close"]), R.consec_days(dc["Close"]), atol=0)
    same(R.wide_range(df), R.wide_range(dc), rtol=1e-9)


@settings(**SETTINGS)
@given(bars(), SHIFTS)
def test_shift_equivariant_modules(df, c):
    dc = shifted(df, c)
    same(R.sma(dc["Close"], 20), R.sma(df["Close"], 20) + c, atol=1e-9)
    same(R.ema(dc["Close"], 20), R.ema(df["Close"], 20) + c, atol=1e-7)
    same(R.vwap(dc), R.vwap(df) + c, atol=1e-7)


@settings(**SETTINGS)
@given(bars(), st.sampled_from([250.0, 1000.0, -250.0]))
def test_gap_pct_is_NOT_shift_invariant(df, c):
    """gap% divides by the previous close, so a price offset changes it whenever a gap exists.
    bars() opens every bar at the previous close, so inject a one-tick gap on every bar."""
    gapped = df.copy()
    gapped.loc[1:, "Open"] = df["Close"].to_numpy()[:-1] + 0.25
    gapped["High"] = np.maximum(gapped["High"], gapped["Open"])
    gapped["Low"] = np.minimum(gapped["Low"], gapped["Open"])
    g0 = R.gap_pct(gapped).to_numpy()
    assert np.nanmax(np.abs(g0)) > 0
    g1 = R.gap_pct(shifted(gapped, c)).to_numpy()
    assert np.nanmax(np.abs(g0 - g1)) > 1e-9


@settings(**SETTINGS)
@given(bars(min_bars=60, max_bars=70), st.sampled_from([250.0, 1000.0]))
def test_sma200_distance_is_shift_invariant_but_sma_is_not(df, c):
    big = pd.concat([df] * 4, ignore_index=True)
    big["BarTime"] = pd.date_range("2026-01-05", periods=len(big), freq="15min")
    s0, d0 = R.sma200_trend(big["Close"])
    s1, d1 = R.sma200_trend(shifted(big, c)["Close"])
    same(d0, d1, atol=1e-7)
    assert np.nanmax(np.abs(s1.to_numpy() - s0.to_numpy() - c)) < 1e-7


# --------------------------------------------------------------------------------------------
# causality: appending future bars never changes earlier values
# --------------------------------------------------------------------------------------------
REFERENCES = {
    "rsi2": lambda d: R.rsi(d["Close"], 2),
    "rsi14": lambda d: R.rsi(d["Close"], 14),
    "ema20": lambda d: R.ema(d["Close"], 20),
    "sma20": lambda d: R.sma(d["Close"], 20),
    "stddev20": lambda d: R.stddev(d["Close"], 20),
    "atr14": lambda d: R.atr(d, 14),
    "macd_hist": lambda d: R.macd_hist(d["Close"]),
    "boll_up": lambda d: R.bollinger(d["Close"])[0],
    "stochK": lambda d: R.stoch_fast(d)[0],
    "stochD": lambda d: R.stoch_fast(d)[1],
    "adx": lambda d: R.adx(d)[0],
    "ibs_bar": R.ibs_bar,
    "ibs_daily": lambda d: R.ibs_daily(d, "trading"),
    "crsi": lambda d: R.connors_rsi(d["Close"]),
    "rvz": R.rv_zscore,
    "composite": lambda d: R.composite_vol(d)["composite"],
    "tom": lambda d: R.turn_of_month(d["BarTime"]),
    "consec": lambda d: R.consec_days(d["Close"]),
    "gap": R.gap_pct,
    "pct_b": lambda d: R.pct_b(d["Close"]),
    "dow": lambda d: R.day_of_week(d["BarTime"]),
    "vrp": R.vrp_proxy,
    "wide": R.wide_range,
    "hp_basis": R.hp_basis_term,
    "hp_slope": R.hp_slope_term,
    "vwap": R.vwap,
    "vwap_dist": R.vwap_distance,
    "ema_spread": lambda d: R.ema_cross(d["Close"])[2],
    "atr_regime": R.atr_regime,
    "vol_spike": R.volume_spike,
    "vol_delta": lambda d: R.volume_delta(d)[0],
    "cum20": lambda d: R.volume_delta(d)[1],
    "delta_sma10": lambda d: R.volume_delta(d)[2],
    "chop": R.chop,
    "chop_state": R.chop_state,
}


@settings(**SETTINGS)
@given(bars(min_bars=120, max_bars=140), st.integers(30, 110))
def test_no_lookahead(df, n):
    head = df.iloc[:n].reset_index(drop=True)
    for name, fn in REFERENCES.items():
        full = fn(df).to_numpy()[:n]
        part = fn(head).to_numpy()
        try:
            same(part, full, rtol=1e-12, atol=1e-12)
        except AssertionError as e:
            raise AssertionError("look-ahead in reference %r: %s" % (name, e))


# --------------------------------------------------------------------------------------------
# determinism
# --------------------------------------------------------------------------------------------
@settings(**SETTINGS)
@given(bars(min_bars=120, max_bars=130))
def test_determinism(df):
    for name, fn in REFERENCES.items():
        a, b = fn(df.copy()).to_numpy(), fn(df.copy()).to_numpy()
        assert np.array_equal(a, b, equal_nan=True), name


# --------------------------------------------------------------------------------------------
# zero-range / zero-volume bars: finite where the ledger gives a fallback
# --------------------------------------------------------------------------------------------
@settings(**SETTINGS)
@given(st.integers(30, 60), st.sampled_from([0.0, 100.0]))
def test_zero_range_and_zero_volume_bars_have_fallbacks(n, vol):
    close = np.full(n, 4000.0)
    df = make_df(close, close, close, close, np.full(n, vol))
    assert (R.ibs_bar(df) == 0.5).all()                           # M1: 0.5 if H = L
    assert (R.ibs_daily(df) == 0.5).all()
    assert (R.wide_range(df) == 1.0).all()                         # M14: 1.0 if ATR <= 0
    assert (R.vrp_proxy(df) == 1.0).all()                          # M13: 1.0 before bar 20 / ATR 0
    assert (R.atr_regime(df) == 1.0).all()                         # M20
    assert (R.rv_zscore(df) == 0.0).all()                          # M5
    assert np.isfinite(R.chop(df)).all()                           # M23 clamp / fallback
    assert np.isfinite(R.volume_delta(df)[1]).all()
    vs = R.volume_spike(df).to_numpy()[19:]
    if vol == 0:
        assert (vs == 1.0).all()                                   # M21: 1.0 if SMA <= 0
    else:
        assert np.allclose(vs, 1.0)
    assert np.isfinite(R.vwap(df)).all()                           # finite even with zero volume
    assert (R.consec_days(df["Close"]) == 0).all()


# --------------------------------------------------------------------------------------------
# monotonicity: an up-close raises RSI relative to a down-close
# --------------------------------------------------------------------------------------------
@settings(**SETTINGS)
@given(bars(min_bars=20, max_bars=40), st.sampled_from([2, 14]))
def test_rsi_monotone_in_last_move(df, n):
    base = df["Close"].to_numpy()
    up = np.append(base, base[-1] + 0.25)
    dn = np.append(base, base[-1] - 0.25)
    r_up, r_dn = R.rsi(up, n).to_numpy()[-1], R.rsi(dn, n).to_numpy()[-1]
    assert r_up > r_dn
    flat = np.append(base, base[-1])
    r_flat = R.rsi(flat, n).to_numpy()[-1]
    assert r_dn <= r_flat <= r_up


# --------------------------------------------------------------------------------------------
# falsifiers: the invariants above do reject broken references
# --------------------------------------------------------------------------------------------
def _fixed_df():
    rng = np.random.default_rng(3)
    close = 4000 + np.cumsum(rng.integers(-10, 11, 80)) * 0.25
    return df_from_close(close, wick=0.5, volume=rng.integers(1, 500, 80).astype(float))


def test_falsifier_scale_invariance_detects_unnormalised_range():
    df = _fixed_df()
    wrong = lambda d: d["High"] - d["Low"]  # a 'wide range' that forgot to divide by ATR
    with pytest.raises(AssertionError):
        same(wrong(df), wrong(scaled(df, 2.0)), rtol=1e-9)


def test_falsifier_lookahead_detected_in_centered_average():
    df = _fixed_df()
    wrong = lambda d: d["Close"].rolling(5, center=True).mean()  # uses future bars
    n = 50
    with pytest.raises(AssertionError):
        same(wrong(df.iloc[:n].reset_index(drop=True)), wrong(df).to_numpy()[:n], rtol=1e-12)


def test_falsifier_rsi_sample_average_breaks_monotone_bound():
    # a 'RSI' that ignores the sign of the last move cannot satisfy r_up > r_dn
    df = _fixed_df()
    base = df["Close"].to_numpy()
    wrong = lambda x: 100.0 - 100.0 / (1.0 + np.abs(np.diff(x[-15:])).mean())
    assert not (wrong(np.append(base, base[-1] + 0.25)) > wrong(np.append(base, base[-1] - 0.25)))


def test_falsifier_shift_invariance_detects_price_level_dependence():
    df = _fixed_df()
    wrong = lambda d: R.atr(d, 14) / d["Close"]  # ATR in percent of price is not shift invariant
    with pytest.raises(AssertionError):
        same(wrong(df), wrong(shifted(df, 1000.0)), atol=1e-9)
