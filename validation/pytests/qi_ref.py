"""qi_ref.py - reference implementations of the built-in blocks B1-B9 and the arithmetic
modules M1-M23 of validation/algo-claims-ledger.md (FROZEN 2026-10-16).

Spec source: ONLY the ledger's "Formula F as implemented" column and its B1-B9 block
definitions. No NinjaTrader documentation, no @*.cs sources and no indicators/*.cs were
consulted; where the ledger is silent an explicit ASSUMPTION is documented on the function.

Conventions
-----------
* Every function takes a DataFrame with columns Open, High, Low, Close, Volume (oldest row
  first) and, where a calendar is needed, a datetime column BarTime (bar close time, chart
  local time = US Central per the ledger).
* Bars are indexed by position: bar 0 is the oldest row. The ledger's "k bars ago" is
  therefore position t-k. "X until bar N" / "X before bar N" is implemented as
  value = X for positions t < N (the NinjaScript `CurrentBar < N` guard reading).
* Returned Series are aligned to df.index. NaN marks "not yet defined" (warm-up) where the
  ledger gives no fallback value.
* Wilder_n (ledger notation) = running average with weight 1/n on the new value,
  seeded with the first available value. EMA_n uses alpha = 2/(n+1), seeded with x[0].
* StdDev is the POPULATION standard deviation (divide by n) - ledger B5.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

__all__ = [
    "ema", "sma", "stddev", "wilder", "rsi", "true_range", "atr", "macd", "bollinger",
    "stoch_fast", "adx",
    "ibs_bar", "ibs_daily", "trading_day", "calendar_day", "connors_rsi", "streak",
    "percent_rank", "rv_zscore", "composite_vol", "composite_vol_from_parts", "turn_of_month",
    "consec_days", "gap_pct", "pct_b", "pct_b_from_bands", "day_of_week", "vrp_proxy",
    "wide_range", "hp_basis_term", "hp_slope_term", "hp_clamp_total", "vwap", "vwap_distance",
    "macd_hist", "ema_cross", "sma200_trend", "atr_regime", "volume_spike", "volume_delta",
    "chop", "chop_state", "vol_ratio",
]


# ============================================================================================
# helpers
# ============================================================================================
def _col(df, name):
    return np.asarray(df[name], dtype=float)


def _series(values, df):
    return pd.Series(np.asarray(values, dtype=float), index=df.index)


def _as_array(x):
    if isinstance(x, pd.DataFrame):
        raise TypeError("expected a Series/array, got a DataFrame")
    return np.asarray(x, dtype=float)


def _index_of(x, fallback_len):
    if isinstance(x, pd.Series):
        return x.index
    return pd.RangeIndex(fallback_len)


# ============================================================================================
# B2  EMA_n[0] = EMA_n[1] + 2/(n+1) * (x[0] - EMA_n[1])
# ============================================================================================
def ema(x, n):
    """Ledger B2. Seeded with the first value (ASSUMPTION: the ledger states no seed)."""
    a = _as_array(x)
    alpha = 2.0 / (n + 1.0)
    out = np.full(len(a), np.nan)
    prev = np.nan
    for t in range(len(a)):
        v = a[t]
        if np.isnan(v):
            out[t] = np.nan
            continue
        if np.isnan(prev):
            prev = v
        else:
            prev = prev + alpha * (v - prev)
        out[t] = prev
    return pd.Series(out, index=_index_of(x, len(a)))


# ============================================================================================
# B3  SMA_n = mean of the last n values (NaN until n values exist)
# ============================================================================================
def sma(x, n):
    """Ledger B3."""
    s = pd.Series(_as_array(x), index=_index_of(x, len(_as_array(x))))
    return s.rolling(n, min_periods=n).mean()


# ============================================================================================
# B5  StdDev_n = population standard deviation (divide by n) of the last n values
# ============================================================================================
def stddev(x, n):
    """Ledger B5 (population, ddof = 0)."""
    s = pd.Series(_as_array(x), index=_index_of(x, len(_as_array(x))))
    return s.rolling(n, min_periods=n).std(ddof=0)


# ============================================================================================
# Wilder_n running average (ledger notation section): weight 1/n on the new value
# ============================================================================================
def wilder(x, n):
    """y[t] = y[t-1] + (x[t] - y[t-1]) / n, seeded with the first non-NaN value."""
    a = _as_array(x)
    out = np.full(len(a), np.nan)
    prev = np.nan
    for t in range(len(a)):
        v = a[t]
        if np.isnan(v):
            continue
        prev = v if np.isnan(prev) else prev + (v - prev) / n
        out[t] = prev
    return pd.Series(out, index=_index_of(x, len(a)))


# ============================================================================================
# B1  RSI_n = 100 - 100/(1+RS), RS = Wilder_n(up moves)/Wilder_n(down moves);
#     NT RSI(input, n, smooth) applies an extra EMA_smooth to the result, smooth = 1 => none
# ============================================================================================
def rsi(x, n, smooth=1):
    """Ledger B1. Bar 0 (no previous value) is NaN.

    ASSUMPTIONS (ledger silent): Wilder averages are seeded with the first move; when the
    down-average is 0 the RSI is 100 if the up-average is > 0 and 50 if both are 0.
    """
    a = _as_array(x)
    out = np.full(len(a), np.nan)
    avg_up = avg_dn = np.nan
    for t in range(1, len(a)):
        d = a[t] - a[t - 1]
        if np.isnan(d):
            continue
        up = d if d > 0 else 0.0
        dn = -d if d < 0 else 0.0
        if np.isnan(avg_up):
            avg_up, avg_dn = up, dn
        else:
            avg_up = avg_up + (up - avg_up) / n
            avg_dn = avg_dn + (dn - avg_dn) / n
        if avg_dn == 0.0:
            out[t] = 100.0 if avg_up > 0.0 else 50.0
        else:
            rs = avg_up / avg_dn
            out[t] = 100.0 - 100.0 / (1.0 + rs)
    res = pd.Series(out, index=_index_of(x, len(a)))
    if smooth and smooth > 1:
        res = ema(res, smooth)
    return res


# ============================================================================================
# B4  TR = max(H-L, |H-C[1]|, |L-C[1]|);  NT ATR = (min(bar, n-1)*ATR[1] + TR)/min(bar+1, n)
# ============================================================================================
def true_range(df):
    """TR per ledger B4; bar 0 has no C[1] so TR[0] = H - L."""
    h, l, c = _col(df, "High"), _col(df, "Low"), _col(df, "Close")
    tr = h - l
    if len(tr) > 1:
        pc = c[:-1]
        tr[1:] = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - pc), np.abs(l[1:] - pc)))
    return _series(tr, df)


def atr(df, n):
    """Ledger B4 exactly: ATR[t] = (min(t, n-1)*ATR[t-1] + TR[t]) / min(t+1, n), ATR[0] = TR[0]."""
    tr = true_range(df).to_numpy()
    out = np.empty(len(tr))
    for t in range(len(tr)):
        if t == 0:
            out[t] = tr[0]
        else:
            out[t] = (min(t, n - 1) * out[t - 1] + tr[t]) / min(t + 1, n)
    return _series(out, df)


# ============================================================================================
# B6  MACD: line = EMA_fast - EMA_slow, signal = EMA_signal(line), histogram = line - signal
# ============================================================================================
def macd(x, fast=12, slow=26, signal=9):
    """Ledger B6. Returns (line, signal, histogram)."""
    line = ema(x, fast) - ema(x, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


# ============================================================================================
# B7  Bollinger(numStdDev, n): middle = SMA_n(close), upper/lower = middle +/- numStdDev*StdDev_n
# ============================================================================================
def bollinger(x, n=20, num_std=2.0):
    """Ledger B7. Returns (upper, middle, lower).

    ASSUMPTION: the ledger states no parameters for QI_21_BollingerPctB; (2, 20) is used.
    """
    mid = sma(x, n)
    sd = stddev(x, n)
    return mid + num_std * sd, mid, mid - num_std * sd


# ============================================================================================
# B8  StochasticsFast(periodD, periodK): %K = 100*(C-LL_K)/(HH_K-LL_K), %D = SMA_periodD(%K)
# ============================================================================================
def stoch_fast(df, period_d=3, period_k=14):
    """Ledger B8 (NT StochasticsFast(3, 14) => periodD = 3, periodK = 14). Returns (K, D).

    ASSUMPTION: %K = 50 when HH_K == LL_K (ledger silent). NaN until K bars exist.
    """
    hh = df["High"].rolling(period_k, min_periods=period_k).max()
    ll = df["Low"].rolling(period_k, min_periods=period_k).min()
    rng = hh - ll
    k = 100.0 * (df["Close"] - ll) / rng.where(rng != 0, np.nan)
    k = k.where(rng != 0, 50.0).where(rng.notna(), np.nan)
    d = sma(k, period_d)
    return k.astype(float), d


# ============================================================================================
# B9  ADX_n = Wilder_n(DX), DX = 100*|+DI - -DI|/(+DI + -DI), +DM/-DM/TR per Wilder
# ============================================================================================
def adx(df, n=14):
    """Ledger B9 (Wilder): +DM = H-H[1] if > L[1]-L and > 0 else 0; -DM = L[1]-L if > H-H[1]
    and > 0 else 0; +DI = 100*Wilder_n(+DM)/Wilder_n(TR), -DI likewise; DX as above (0 when
    +DI + -DI = 0); ADX = Wilder_n(DX). Bar 0 is NaN. Returns (adx, plus_di, minus_di)."""
    h, l = _col(df, "High"), _col(df, "Low")
    tr = true_range(df).to_numpy()
    m = len(h)
    out = np.full(m, np.nan)
    dip_out = np.full(m, np.nan)
    dim_out = np.full(m, np.nan)
    s_dmp = s_dmm = s_tr = s_adx = np.nan
    for t in range(1, m):
        up_move = h[t] - h[t - 1]
        dn_move = l[t - 1] - l[t]
        dmp = up_move if (up_move > dn_move and up_move > 0) else 0.0
        dmm = dn_move if (dn_move > up_move and dn_move > 0) else 0.0
        if np.isnan(s_tr):
            s_dmp, s_dmm, s_tr = dmp, dmm, tr[t]
        else:
            s_dmp += (dmp - s_dmp) / n
            s_dmm += (dmm - s_dmm) / n
            s_tr += (tr[t] - s_tr) / n
        dip = 100.0 * s_dmp / s_tr if s_tr > 0 else 0.0
        dim = 100.0 * s_dmm / s_tr if s_tr > 0 else 0.0
        tot = dip + dim
        dx = 100.0 * abs(dip - dim) / tot if tot > 0 else 0.0
        s_adx = dx if np.isnan(s_adx) else s_adx + (dx - s_adx) / n
        out[t], dip_out[t], dim_out[t] = s_adx, dip, dim
    return _series(out, df), _series(dip_out, df), _series(dim_out, df)


# ============================================================================================
# M1  IBS = (C - L)/(H - L) of the DAILY bar; 0.5 if H = L; intraday: the forming daily bar
# ============================================================================================
def ibs_bar(df):
    """Per-bar IBS: (C - L)/(H - L), 0.5 when H == L (ledger M1 applied to each row)."""
    h, l, c = _col(df, "High"), _col(df, "Low"), _col(df, "Close")
    rng = h - l
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(rng == 0, 0.5, (c - l) / rng)
    return _series(v, df)


def calendar_day(times):
    """Calendar date of the bar time (used by M16 'day-of-year change')."""
    return pd.to_datetime(times).dt.normalize()


def trading_day(times, rollover_hour=17):
    """CME-style trading day: a bar closing after 17:00 belongs to the next calendar day.
    ASSUMPTION for M1 on intraday charts: NinjaTrader's daily bar follows the session's
    trading day (the ledger says 'the forming daily bar' without naming the boundary)."""
    t = pd.to_datetime(times)
    return (t + pd.Timedelta(hours=24 - rollover_hour)).dt.normalize()


def ibs_daily(df, day_key="trading"):
    """Ledger M1 on an intraday chart: IBS of the forming daily bar, i.e. H = running max of
    High and L = running min of Low since the day started, C = current close.
    day_key: 'trading' (17:00 rollover, primary) or 'calendar'."""
    key = trading_day(df["BarTime"]) if day_key == "trading" else calendar_day(df["BarTime"])
    dh = df["High"].groupby(key.to_numpy()).cummax()
    dl = df["Low"].groupby(key.to_numpy()).cummin()
    rng = dh - dl
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(rng.to_numpy() == 0, 0.5, (df["Close"].to_numpy() - dl.to_numpy()) / rng.to_numpy())
    return _series(v, df)


# ============================================================================================
# M3  CRSI = (RSI_2(close) + RSI_2(streak) + PercentRank_100(ROC_1))/3
# ============================================================================================
def streak(close):
    """Signed run of up/down closes; an unchanged close keeps the previous count (ledger M3/M8).
    Bar 0 = 0."""
    c = _as_array(close)
    out = np.zeros(len(c))
    for t in range(1, len(c)):
        if c[t] > c[t - 1]:
            out[t] = out[t - 1] + 1 if out[t - 1] > 0 else 1
        elif c[t] < c[t - 1]:
            out[t] = out[t - 1] - 1 if out[t - 1] < 0 else -1
        else:
            out[t] = out[t - 1]
    return pd.Series(out, index=_index_of(close, len(c)))


def percent_rank(x, lookback=100):
    """PercentRank over the PREVIOUS `lookback` values (positions t-lookback .. t-1):
    count of those strictly less than x[t], /lookback * 100. NaN until lookback previous
    values exist."""
    a = _as_array(x)
    out = np.full(len(a), np.nan)
    for t in range(lookback, len(a)):
        window = a[t - lookback:t]
        out[t] = 100.0 * np.count_nonzero(window < a[t]) / lookback
    return pd.Series(out, index=_index_of(x, len(a)))


def connors_rsi(close, warmup=100):
    """Ledger M3: CRSI = (RSI_2(close) + RSI_2(streak) + PercentRank_100(ROC_1))/3; 50 until
    bar 100 (positions t < 100). ROC_1 = (C - C[1])/C[1]; ROC at bar 0 taken as 0 (ASSUMPTION)."""
    c = _as_array(close)
    roc = np.zeros(len(c))
    roc[1:] = (c[1:] - c[:-1]) / c[:-1]
    r_price = rsi(c, 2).to_numpy()
    r_streak = rsi(streak(c).to_numpy(), 2).to_numpy()
    pr = percent_rank(roc, 100).to_numpy()
    out = (r_price + r_streak + pr) / 3.0
    out[:warmup] = 50.0
    return pd.Series(out, index=_index_of(close, len(c)))


# ============================================================================================
# M5  z = (ATR14[0] - mean_20(ATR14)) / popstd_20(ATR14); 0 until bar 25
# ============================================================================================
def rv_zscore(df, atr_n=14, window=20, warmup=25):
    """Ledger M5. ASSUMPTION: z = 0 when popstd_20 = 0 (ATR constant)."""
    a = atr(df, atr_n)
    mu = sma(a, window)
    sd = stddev(a, window)
    z = (a - mu) / sd.where(sd != 0, np.nan)
    z = z.where(sd != 0, 0.0)
    z = z.to_numpy()
    z[:warmup] = 0.0
    return _series(z, df)


# ============================================================================================
# M6  0.40*z_RV + 0.35*(-priceZ) + 0.25*((vov - 0.15)/0.10)
#     priceZ = (C - SMA20)/popstd20;  vov = popstd_10(dATR14)/ATR14
# ============================================================================================
def composite_vol_from_parts(z_rv, price_z, vov):
    """The weighting arithmetic of ledger M6 on already-computed inputs."""
    z_rv, price_z, vov = (np.asarray(v, dtype=float) for v in (z_rv, price_z, vov))
    return 0.40 * z_rv + 0.35 * (-price_z) + 0.25 * ((vov - 0.15) / 0.10)


def composite_vol(df):
    """Ledger M6. Returns dict(composite, z_rv, price_z, vov, atr_change).
    ASSUMPTIONS: priceZ = 0 when popstd20(close) = 0; vov = 0 when ATR14 = 0."""
    close = df["Close"]
    a14 = atr(df, 14)
    z_rv = rv_zscore(df)
    mu = sma(close, 20)
    sd = stddev(close, 20)
    price_z = ((close - mu) / sd.where(sd != 0, np.nan)).where(sd != 0, 0.0)
    d_atr = a14.diff()
    sd10 = stddev(d_atr, 10)
    vov = (sd10 / a14.where(a14 != 0, np.nan)).where(a14 != 0, 0.0)
    comp = composite_vol_from_parts(z_rv, price_z, vov)
    return {
        "composite": _series(comp, df),
        "z_rv": z_rv,
        "price_z": price_z.astype(float),
        "vov": vov.astype(float),
        "atr_change": d_atr,
    }


# ============================================================================================
# M7  flag = 1 if calendar day >= DaysInMonth-3 or <= 3 (US Central date)
# ============================================================================================
def turn_of_month(times):
    """Ledger M7. `times` are chart-local (US Central) bar times; returns 0/1 floats."""
    t = pd.to_datetime(times)
    day = t.dt.day
    dim = t.dt.days_in_month
    flag = (day >= dim - 3) | (day <= 3)
    return pd.Series(flag.to_numpy().astype(float), index=_index_of(times, len(t)))


# ============================================================================================
# M8  signed count of consecutive higher/lower closes; unchanged close keeps counts
# ============================================================================================
def consec_days(close):
    """Ledger M8 (same run arithmetic as the M3 streak)."""
    return streak(close)


# ============================================================================================
# M9  gap% = (O[0] - C[1]) / C[1] * 100
# ============================================================================================
def gap_pct(df):
    """Ledger M9 on every bar; bar 0 is NaN."""
    o, c = _col(df, "Open"), _col(df, "Close")
    out = np.full(len(o), np.nan)
    out[1:] = (o[1:] - c[:-1]) / c[:-1] * 100.0
    return _series(out, df)


# ============================================================================================
# M10 %B_here = (C - middle) / (half bandwidth) * 100   (half bandwidth = numStdDev*StdDev_n)
# ============================================================================================
def pct_b_from_bands(close, upper, middle, lower):
    """%B_here from already-computed bands: (C - middle)/((upper - lower)/2) * 100."""
    close, upper, middle, lower = (np.asarray(v, dtype=float) for v in (close, upper, middle, lower))
    half = (upper - lower) / 2.0
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(half == 0, 0.0, (close - middle) / half * 100.0)
    return v


def pct_b(close, n=20, num_std=2.0):
    """Ledger M10 with bands per B7. ASSUMPTION: 0 when the half bandwidth is 0."""
    up, mid, lo = bollinger(close, n, num_std)
    v = pct_b_from_bands(close, up, mid, lo)
    v = np.where(np.isnan(mid.to_numpy()), np.nan, v)
    return pd.Series(v, index=_index_of(close, len(v)))


# ============================================================================================
# M11 day-of-week (US Central) 0..6
# ============================================================================================
def day_of_week(times, sunday_zero=True):
    """Ledger M11. ASSUMPTION: 0 = Sunday .. 6 = Saturday (the .NET DayOfWeek numbering;
    the ledger only says '0..6'). sunday_zero=False gives Monday = 0 (ISO/pandas)."""
    t = pd.to_datetime(times)
    dow = t.dt.dayofweek.to_numpy()  # Monday = 0
    if sunday_zero:
        dow = (dow + 1) % 7
    return pd.Series(dow.astype(float), index=_index_of(times, len(t)))


# ============================================================================================
# M13 ATR5/ATR14; 1.0 before bar 20
# ============================================================================================
def vrp_proxy(df, warmup=20):
    """Ledger M13. ASSUMPTION: 1.0 when ATR14 = 0."""
    a5, a14 = atr(df, 5).to_numpy(), atr(df, 14).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(a14 > 0, a5 / a14, 1.0)
    v[:warmup] = 1.0
    return _series(v, df)


# ============================================================================================
# M14 (H - L)/ATR14; 1.0 if ATR <= 0
# ============================================================================================
def wide_range(df):
    """Ledger M14."""
    a14 = atr(df, 14).to_numpy()
    rng = _col(df, "High") - _col(df, "Low")
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(a14 > 0, rng / a14, 1.0)
    return _series(v, df)


# ============================================================================================
# M15 HedgingPressure: only two of the four terms are specified in the ledger.
# ============================================================================================
def hp_basis_term(df):
    """Ledger M15 term 1: clamp((C - SMA20)/ATR14 * -25, +/-25). NaN until SMA20 exists."""
    v = (df["Close"] - sma(df["Close"], 20)) / atr(df, 14).replace(0, np.nan) * -25.0
    return v.clip(-25.0, 25.0)


def hp_slope_term(df):
    """Ledger M15 term 2: clamp((dSMA5 - dSMA20)/ATR14 * -50, +/-25) with dSMA = SMA[0]-SMA[1]."""
    d5 = sma(df["Close"], 5).diff()
    d20 = sma(df["Close"], 20).diff()
    v = (d5 - d20) / atr(df, 14).replace(0, np.nan) * -50.0
    return v.clip(-25.0, 25.0)


def hp_clamp_total(*terms):
    """Ledger M15: each term clamped to +/-25, the sum clamped to +/-100."""
    tot = sum(np.clip(np.asarray(t, dtype=float), -25.0, 25.0) for t in terms)
    return np.clip(tot, -100.0, 100.0)


# ============================================================================================
# M16 VWAP = sum(typical*vol)/sum(vol), typical = (H+L+C)/3, reset at each trading session
#     (ADD-6: the module resets on Bars.IsFirstBarOfSession and exports that flag as
#     QI_23_VWAPDistance.SessionStart; when the flag column is absent the calendar day of BarTime
#     is used as the session key, which is the original indicator's day-of-year behaviour);
#     dist = (C - VWAP)/ATR14
# ============================================================================================
SESSION_FLAG_COL = "QI_23_VWAPDistance.SessionStart"


def vwap(df):
    """Ledger M16 (ADD-6). Reset key = cumulative count of session-start flags when the
    SessionStart column is present, else the calendar day of BarTime.
    ASSUMPTION: VWAP = typical price while the session's cumulative volume is 0."""
    typ = (df["High"] + df["Low"] + df["Close"]) / 3.0
    if SESSION_FLAG_COL in df.columns:
        flag = pd.to_numeric(df[SESSION_FLAG_COL], errors="coerce").fillna(0).to_numpy()
        key = np.cumsum(flag > 0.5)
    else:
        key = calendar_day(df["BarTime"]).to_numpy()
    pv = (typ * df["Volume"]).groupby(key).cumsum()
    vv = df["Volume"].groupby(key).cumsum()
    v = (pv / vv.where(vv != 0, np.nan)).where(vv != 0, typ)
    return v.astype(float)


def vwap_distance(df):
    """Ledger M16: (C - VWAP)/ATR14. ASSUMPTION: 0 when ATR14 = 0."""
    a14 = atr(df, 14)
    v = ((df["Close"] - vwap(df)) / a14.where(a14 != 0, np.nan)).where(a14 != 0, 0.0)
    return v.astype(float)


# ============================================================================================
# M17 MACD(12, 26, 9).Diff
# ============================================================================================
def macd_hist(close):
    """Ledger M17 = B6 histogram with (12, 26, 9)."""
    return macd(close, 12, 26, 9)[2]


# ============================================================================================
# M18 EMA20, EMA50; Spread = EMA20 - EMA50
# ============================================================================================
def ema_cross(close):
    """Ledger M18. Returns (ema20, ema50, spread)."""
    e20, e50 = ema(close, 20), ema(close, 50)
    return e20, e50, e20 - e50


# ============================================================================================
# M19 SMA200; Distance = C - SMA200 from bar 200
# ============================================================================================
def sma200_trend(close):
    """Ledger M19. Returns (sma200, distance). Distance is NaN for positions < 200."""
    s = sma(close, 200)
    d = (pd.Series(_as_array(close), index=s.index) - s)
    d = d.to_numpy()
    d[:200] = np.nan
    return s, pd.Series(d, index=s.index)


# ============================================================================================
# M20 ATR14/SMA50(ATR14); 1.0 before bar 50
# ============================================================================================
def atr_regime(df, warmup=50):
    """Ledger M20. ASSUMPTION: 1.0 when SMA50(ATR14) = 0."""
    a14 = atr(df, 14)
    s50 = sma(a14, 50)
    v = (a14 / s50.where(s50 != 0, np.nan)).where(s50 != 0, 1.0).to_numpy()
    v[:warmup] = 1.0
    return _series(v, df)


# ============================================================================================
# M21 Vol/SMA20(Vol); 1.0 if SMA <= 0
# ============================================================================================
def volume_spike(df):
    """Ledger M21. NaN while SMA20(Vol) is undefined (first 19 bars)."""
    s20 = sma(df["Volume"], 20)
    v = (df["Volume"] / s20.where(s20 > 0, np.nan)).where(s20 > 0, 1.0)
    v = v.where(s20.notna(), np.nan)
    return v.astype(float)


# ============================================================================================
# M22 delta = +Vol if C > C[1], -Vol if C < C[1], else 0; Cum20 = sum_{k=0..19} delta[k]
#     (bar > 20); SMA10(delta) (bar >= 10)
# ============================================================================================
def volume_delta(df):
    """Ledger M22. Returns (delta, cum20, sma10). delta[0] = 0 (no C[1]);
    cum20 = 0 for positions <= 20 (strict 'bar > 20' guard); sma10 = 0 for positions < 10."""
    c, vol = _col(df, "Close"), _col(df, "Volume")
    delta = np.zeros(len(c))
    delta[1:] = np.where(c[1:] > c[:-1], vol[1:], np.where(c[1:] < c[:-1], -vol[1:], 0.0))
    d = _series(delta, df)
    cum = d.rolling(20, min_periods=20).sum().to_numpy()
    cum[:21] = 0.0
    s10 = d.rolling(10, min_periods=10).mean().to_numpy()
    s10[:10] = 0.0
    return d, _series(cum, df), _series(s10, df)


# ============================================================================================
# M23 CHOP_14 = 100*log10(sumTR_14/(HH_14 - LL_14))/log10(14), clamped 0..100, 50 until bar 14
#     state: count of {CHOP > 61.8, ADX14 < 20, Vol < 0.7*SMA20(Vol)}
# ============================================================================================
def chop(df, n=14, warmup=14):
    """Ledger M23. ASSUMPTION: 50 when HH_14 == LL_14 (undefined ratio)."""
    tr_sum = true_range(df).rolling(n, min_periods=n).sum()
    hh = df["High"].rolling(n, min_periods=n).max()
    ll = df["Low"].rolling(n, min_periods=n).min()
    rng = (hh - ll)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = tr_sum.to_numpy() / rng.to_numpy()
        v = 100.0 * np.log10(ratio) / math.log10(n)
    v = np.clip(v, 0.0, 100.0)
    v = np.where(rng.to_numpy() == 0, 50.0, v)
    v[:warmup] = 50.0
    return _series(v, df)


def vol_ratio(df):
    """Vol / SMA20(Vol) as used by the M23 state (no fallback stated; NaN during warm-up)."""
    s20 = sma(df["Volume"], 20)
    return (df["Volume"] / s20).astype(float)


def chop_state(df):
    """Ledger M23 state: number of true conditions among CHOP > 61.8, ADX14 < 20,
    Vol < 0.7*SMA20(Vol). NaN where ADX or SMA20 are undefined."""
    c = chop(df)
    a = adx(df, 14)[0]
    s20 = sma(df["Volume"], 20)
    cnt = (c > 61.8).astype(float) + (a < 20).astype(float) + (df["Volume"] < 0.7 * s20).astype(float)
    cnt = cnt.where(a.notna() & s20.notna(), np.nan)
    return cnt.astype(float)
