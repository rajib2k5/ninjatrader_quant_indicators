"""test_unit_modules.py - hand-constructed bars with known answers for ledger claims M1-M23.

Expected values are evaluated from the ledger's formula text, never from the C# sources.
`test_falsifier_*` tests show that a plausible wrong formula is rejected by the same checks.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import qi_ref as R
from conftest import df_from_close, make_df

rng = np.random.default_rng(7)
PRICES = 4000.0 + np.cumsum(rng.normal(0, 2.0, 400)).round(2)
VOLS = rng.integers(50, 500, 400).astype(float)


# --------------------------------------------------------------------------------------------
# M1  IBS
# --------------------------------------------------------------------------------------------
def test_M1_ibs_known_bar_is_0_25():
    df = make_df([10], [12], [8], [9])
    assert R.ibs_bar(df)[0] == pytest.approx(0.25)


def test_M1_ibs_doji_h_equals_l_is_0_5():
    df = make_df([10], [10], [10], [10])
    assert R.ibs_bar(df)[0] == 0.5


def test_M1_ibs_daily_uses_forming_daily_range():
    # three 15-min bars of one trading day: daily H = 12 (bar 0), daily L = 7 (bar 1), C = 11 at bar 2
    df = make_df([10, 9, 8], [12, 9, 11], [9, 7, 8], [9, 8, 11], start="2026-01-06 09:30:00")
    ibs = R.ibs_daily(df, "trading").to_numpy()
    assert ibs[0] == pytest.approx((9 - 9) / (12 - 9))
    assert ibs[1] == pytest.approx((8 - 7) / (12 - 7))
    assert ibs[2] == pytest.approx((11 - 7) / (12 - 7))


def test_M1_ibs_daily_resets_at_17_00_rollover():
    # bar closing 16:00 (day D) then bar closing 17:15 (trading day D+1): the range restarts
    times = pd.to_datetime(["2026-01-06 15:45:00", "2026-01-06 16:00:00", "2026-01-06 17:15:00"])
    df = make_df([10, 10, 50], [20, 12, 52], [5, 9, 49], [10, 11, 50])
    df["BarTime"] = times
    ibs = R.ibs_daily(df, "trading").to_numpy()
    assert ibs[1] == pytest.approx((11 - 5) / (20 - 5))   # still day D's range
    assert ibs[2] == pytest.approx((50 - 49) / (52 - 49))  # fresh range after 17:00


def test_falsifier_ibs_close_minus_open_is_detected():
    df = make_df([10], [12], [8], [9])
    wrong = (df["Close"] - df["Open"]) / (df["High"] - df["Low"])
    assert abs(wrong[0] - 0.25) > 1e-9


# --------------------------------------------------------------------------------------------
# M8 / M3 streak  ConsecDays
# --------------------------------------------------------------------------------------------
def test_M8_consec_days_counts_runs_and_keeps_on_unchanged():
    close = [10, 11, 12, 12, 13, 12, 11, 11, 10, 14]
    #        0  +1  +2  +2  +3  -1  -2  -2  -3  +1
    np.testing.assert_array_equal(R.consec_days(close).to_numpy(), [0, 1, 2, 2, 3, -1, -2, -2, -3, 1])


def test_M8_unchanged_close_keeps_negative_count():
    np.testing.assert_array_equal(R.consec_days([5, 4, 4, 4, 3]).to_numpy(), [0, -1, -1, -1, -2])


def test_falsifier_streak_reset_on_unchanged_is_detected():
    close = [10, 11, 12, 12, 13]
    c = np.asarray(close, dtype=float)
    wrong = np.zeros(len(c))
    for t in range(1, len(c)):
        wrong[t] = (wrong[t - 1] + 1 if wrong[t - 1] > 0 else 1) if c[t] > c[t - 1] else (
            (wrong[t - 1] - 1 if wrong[t - 1] < 0 else -1) if c[t] < c[t - 1] else 0)
    assert not np.array_equal(wrong, [0, 1, 2, 2, 3])


# --------------------------------------------------------------------------------------------
# M3  ConnorsRSI
# --------------------------------------------------------------------------------------------
def test_M3_percent_rank_strictly_less_over_previous_100():
    x = np.concatenate([np.arange(100, dtype=float), [50.0]])  # previous 100 = 0..99; 50 of them < 50
    pr = R.percent_rank(x, 100).to_numpy()
    assert np.all(np.isnan(pr[:100]))
    assert pr[100] == 50.0
    x2 = np.concatenate([np.full(100, 7.0), [7.0]])  # ties are not 'strictly less'
    assert R.percent_rank(x2, 100).to_numpy()[100] == 0.0


def test_M3_crsi_is_50_until_bar_100_and_mean_of_three_after():
    close = PRICES[:160]
    crsi = R.connors_rsi(close).to_numpy()
    assert np.all(crsi[:100] == 50.0)
    roc = np.zeros(len(close))
    roc[1:] = (close[1:] - close[:-1]) / close[:-1]
    expected = (R.rsi(close, 2).to_numpy() + R.rsi(R.streak(close).to_numpy(), 2).to_numpy()
                + R.percent_rank(roc, 100).to_numpy()) / 3.0
    np.testing.assert_allclose(crsi[100:], expected[100:], rtol=1e-12)
    assert np.all((crsi >= 0) & (crsi <= 100))


def test_falsifier_crsi_with_rsi3_of_price_is_detected():
    close = PRICES[:160]
    roc = np.zeros(len(close))
    roc[1:] = (close[1:] - close[:-1]) / close[:-1]
    wrong = (R.rsi(close, 3).to_numpy() + R.rsi(R.streak(close).to_numpy(), 2).to_numpy()
             + R.percent_rank(roc, 100).to_numpy()) / 3.0
    assert np.nanmax(np.abs(wrong[100:] - R.connors_rsi(close).to_numpy()[100:])) > 1e-3


# --------------------------------------------------------------------------------------------
# M9  gap%
# --------------------------------------------------------------------------------------------
def test_M9_gap_pct_hand_values():
    df = make_df([100, 102, 99], [101, 103, 100], [99, 101, 98], [100, 102, 99])
    g = R.gap_pct(df).to_numpy()
    assert np.isnan(g[0])
    assert g[1] == pytest.approx(2.0)            # (102 - 100)/100*100
    assert g[2] == pytest.approx(-3.0 / 102 * 100)


def test_falsifier_gap_vs_previous_open_is_detected():
    df = make_df([100, 102, 99], [101, 103, 100], [99, 101, 98], [100, 101, 99])
    wrong = ((df["Open"] - df["Open"].shift(1)) / df["Open"].shift(1) * 100).to_numpy()
    assert abs(wrong[2] - R.gap_pct(df).to_numpy()[2]) > 1e-9


# --------------------------------------------------------------------------------------------
# M7  Turn-of-month
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("date, expected", [
    ("2026-02-24", 0), ("2026-02-25", 1), ("2026-02-28", 1),      # Feb 2026: 28 days -> >= 25
    ("2024-02-25", 0), ("2024-02-26", 1), ("2024-02-29", 1),      # leap Feb: 29 days -> >= 26
    ("2026-01-27", 0), ("2026-01-28", 1), ("2026-01-31", 1),      # 31-day month -> >= 28
    ("2026-04-26", 0), ("2026-04-27", 1), ("2026-04-30", 1),      # 30-day month -> >= 27
    ("2026-03-01", 1), ("2026-03-03", 1), ("2026-03-04", 0), ("2026-03-15", 0),
])
def test_M7_turn_of_month_flags(date, expected):
    assert R.turn_of_month(pd.Series(pd.to_datetime([date + " 10:00:00"]))).to_numpy()[0] == expected


def test_falsifier_turn_of_month_window_of_last_3_days_is_detected():
    t = pd.Series(pd.to_datetime(["2026-02-25 10:00:00"]))
    wrong = int(t.dt.day.iloc[0] >= t.dt.days_in_month.iloc[0] - 2)
    assert wrong != R.turn_of_month(t).to_numpy()[0]


# --------------------------------------------------------------------------------------------
# M11 day-of-week
# --------------------------------------------------------------------------------------------
def test_M11_day_of_week_sunday_zero():
    t = pd.Series(pd.to_datetime(["2026-10-11", "2026-10-12", "2026-10-13", "2026-10-17"]))  # Sun Mon Tue Sat
    np.testing.assert_array_equal(R.day_of_week(t).to_numpy(), [0, 1, 2, 6])
    np.testing.assert_array_equal(R.day_of_week(t, sunday_zero=False).to_numpy(), [6, 0, 1, 5])


# --------------------------------------------------------------------------------------------
# M23 CHOP
# --------------------------------------------------------------------------------------------
def _trend_df(n=60):
    t = np.arange(n, dtype=float)
    return make_df(t, t + 1, t, t + 1)  # O=L=t, H=C=t+1 : TR = 1, HH-LL = 14 over 14 bars


def _oscillation_df(n=60):
    close = np.where(np.arange(n) % 2 == 0, 0.0, 1.0)
    return make_df(close, np.ones(n), np.zeros(n), close)  # TR = 1, HH-LL = 1


def test_M23_chop_straight_trend_is_0_and_oscillation_is_100():
    assert R.chop(_trend_df()).to_numpy()[-1] == pytest.approx(0.0, abs=1e-12)
    assert R.chop(_oscillation_df()).to_numpy()[-1] == pytest.approx(100.0, abs=1e-12)


def test_M23_chop_trend_below_oscillation():
    assert R.chop(_trend_df()).to_numpy()[20:].max() < R.chop(_oscillation_df()).to_numpy()[20:].min()


def test_M23_chop_50_until_bar_14_and_bounded():
    df = df_from_close(PRICES[:100], wick=1.0)
    c = R.chop(df).to_numpy()
    assert np.all(c[:14] == 50.0)
    assert np.all((c >= 0) & (c <= 100))


def test_M23_chop_hand_value():
    # 14 bars, TR sum = 14*1, HH-LL = 2 -> 100*log10(7)/log10(14)
    close = np.where(np.arange(30) % 2 == 0, 0.0, 1.0) * 2.0  # alternating 0, 2 closes
    df = make_df(close, close + 0.5, close - 0.5, close)        # H-L = 1 ; |H-C1| up to 2.5
    tr = R.true_range(df).to_numpy()
    sum_tr = tr[16:30].sum()
    expected = 100 * np.log10(sum_tr / 3.0) / np.log10(14)  # HH = 2.5, LL = -0.5
    assert R.chop(df).to_numpy()[29] == pytest.approx(min(100.0, expected))


def test_M23_chop_state_counts_three_conditions():
    df = df_from_close(PRICES[:120], wick=1.0, volume=VOLS[:120])
    st = R.chop_state(df)
    c, a, s20 = R.chop(df), R.adx(df, 14)[0], R.sma(df["Volume"], 20)
    exp = (c > 61.8).astype(float) + (a < 20).astype(float) + (df["Volume"] < 0.7 * s20).astype(float)
    np.testing.assert_array_equal(st.to_numpy()[20:], exp.to_numpy()[20:])
    assert set(np.unique(st.dropna())) <= {0.0, 1.0, 2.0, 3.0}


def test_falsifier_chop_without_log_is_detected():
    # linear ratio instead of log10 ratio: on the straight trend the ledger formula gives 0,
    # the wrong one 100/14 (the oscillation case would NOT discriminate: both give 100)
    df = _trend_df()
    wrong = 100.0 * (R.true_range(df).rolling(14).sum() / (df["High"].rolling(14).max() - df["Low"].rolling(14).min())) / 14
    assert abs(wrong.to_numpy()[-1] - R.chop(df).to_numpy()[-1]) > 1.0


# --------------------------------------------------------------------------------------------
# M13 VRP = ATR5/ATR14 ; M14 WideRange ; M20 ATR regime
# --------------------------------------------------------------------------------------------
def test_M13_vrp_is_atr5_over_atr14_and_1_before_bar_20():
    df = df_from_close(PRICES[:100], wick=1.0)
    v = R.vrp_proxy(df).to_numpy()
    assert np.all(v[:20] == 1.0)
    np.testing.assert_allclose(v[20:], (R.atr(df, 5) / R.atr(df, 14)).to_numpy()[20:], rtol=1e-12)


def test_M13_vrp_is_1_for_constant_range_bars():
    close = np.full(60, 100.0)
    df = make_df(close, close + 1, close - 1, close)
    np.testing.assert_allclose(R.vrp_proxy(df).to_numpy(), 1.0)


def test_M14_wide_range_hand_value():
    close = np.full(40, 100.0)
    high, low = close + 1, close - 1
    high[-1], low[-1] = 103.0, 97.0  # range 6 on the last bar, ATR before it = 2
    df = make_df(close, high, low, close)
    a_prev = 2.0
    atr_last = (13 * a_prev + 6.0) / 14
    assert R.wide_range(df).to_numpy()[-1] == pytest.approx(6.0 / atr_last)


def test_M14_wide_range_fallback_1_when_atr_zero():
    close = np.full(30, 100.0)
    df = make_df(close, close, close, close)
    np.testing.assert_array_equal(R.wide_range(df).to_numpy(), 1.0)


def test_M20_atr_regime_1_before_bar_50_then_ratio():
    df = df_from_close(PRICES[:150], wick=1.0)
    v = R.atr_regime(df).to_numpy()
    assert np.all(v[:50] == 1.0)
    a = R.atr(df, 14)
    np.testing.assert_allclose(v[50:], (a / R.sma(a, 50)).to_numpy()[50:], rtol=1e-12)


def test_falsifier_vrp_inverted_ratio_is_detected():
    df = df_from_close(PRICES[:100], wick=1.0)
    wrong = (R.atr(df, 14) / R.atr(df, 5)).to_numpy()
    assert np.max(np.abs(wrong[20:] - R.vrp_proxy(df).to_numpy()[20:])) > 1e-6


# --------------------------------------------------------------------------------------------
# M21 volume spike
# --------------------------------------------------------------------------------------------
def test_M21_volume_spike_ratio_hand_value():
    vol = np.full(40, 100.0)
    vol[-1] = 400.0
    df = df_from_close(PRICES[:40], wick=1.0, volume=vol)
    # SMA20 at the last bar = (19*100 + 400)/20 = 115
    assert R.volume_spike(df).to_numpy()[-1] == pytest.approx(400.0 / 115.0)


def test_M21_volume_spike_fallback_when_sma_zero():
    df = df_from_close(PRICES[:40], wick=1.0, volume=np.zeros(40))
    assert np.all(R.volume_spike(df).to_numpy()[19:] == 1.0)


# --------------------------------------------------------------------------------------------
# M22 volume delta
# --------------------------------------------------------------------------------------------
def test_M22_delta_signs():
    df = make_df([1, 1, 1, 1], [2, 2, 2, 2], [0, 0, 0, 0], [10, 11, 11, 9], volume=[5, 6, 7, 8])
    d, _, _ = R.volume_delta(df)
    np.testing.assert_array_equal(d.to_numpy(), [0, 6, 0, -8])


def test_M22_cum20_strict_bar_gt_20_guard_and_window():
    n = 40
    close = np.arange(n, dtype=float)  # every close is an up close -> delta = volume
    vol = np.arange(1, n + 1, dtype=float)
    df = df_from_close(close, wick=0.5, volume=vol)
    d, cum, s10 = R.volume_delta(df)
    assert np.all(cum.to_numpy()[:21] == 0.0)        # bar 20 still 0 although 20 deltas exist
    assert cum.to_numpy()[21] == pytest.approx(d.to_numpy()[2:22].sum())
    assert cum.to_numpy()[39] == pytest.approx(d.to_numpy()[20:40].sum())
    assert np.all(s10.to_numpy()[:10] == 0.0)
    assert s10.to_numpy()[10] == pytest.approx(d.to_numpy()[1:11].mean())


def test_falsifier_cum20_at_bar_20_is_detected():
    close = np.arange(40, dtype=float)
    df = df_from_close(close, wick=0.5, volume=np.arange(1, 41, dtype=float))
    d, cum, _ = R.volume_delta(df)
    wrong = d.rolling(20).sum().fillna(0.0).to_numpy()  # bar >= 19 guard instead of > 20
    assert wrong[20] != cum.to_numpy()[20]


# --------------------------------------------------------------------------------------------
# M16 VWAP
# --------------------------------------------------------------------------------------------
def test_M16_vwap_hand_values_and_reset_at_day_change():
    times = pd.to_datetime(["2026-01-06 09:30", "2026-01-06 09:45", "2026-01-07 09:30"])
    df = make_df([10, 10, 20], [12, 14, 22], [8, 10, 18], [10, 12, 20], volume=[100, 300, 50])
    df["BarTime"] = times
    v = R.vwap(df).to_numpy()
    typ = np.array([10.0, 12.0, 20.0])
    assert v[0] == pytest.approx(typ[0])
    assert v[1] == pytest.approx((10 * 100 + 12 * 300) / 400)
    assert v[2] == pytest.approx(typ[2])  # new calendar day -> only this bar


def test_M16_vwap_distance_in_atr_units():
    df = df_from_close(PRICES[:60], wick=1.0, volume=VOLS[:60])
    dist = R.vwap_distance(df)
    np.testing.assert_allclose(dist.to_numpy(), ((df["Close"] - R.vwap(df)) / R.atr(df, 14)).to_numpy(), rtol=1e-12)


def test_falsifier_vwap_with_close_instead_of_typical_is_detected():
    df = make_df([10, 10], [12, 14], [8, 10], [10, 13], volume=[100, 300])
    wrong = (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum()
    assert abs(wrong.to_numpy()[1] - R.vwap(df).to_numpy()[1]) > 1e-9


# --------------------------------------------------------------------------------------------
# M10 %B
# --------------------------------------------------------------------------------------------
def test_M10_pct_b_plus_100_at_upper_minus_100_at_lower_0_at_middle():
    up, mid, lo = 110.0, 100.0, 90.0
    assert R.pct_b_from_bands(up, up, mid, lo) == 100.0
    assert R.pct_b_from_bands(lo, up, mid, lo) == -100.0
    assert R.pct_b_from_bands(mid, up, mid, lo) == 0.0
    assert R.pct_b_from_bands(105.0, up, mid, lo) == 50.0


def test_M10_pct_b_is_affine_in_bollinger_pct_b():
    # %B_here = 200*%b - 100 with %b = (C - lower)/(upper - lower)
    x = PRICES[:80]
    up, mid, lo = R.bollinger(x, 20, 2.0)
    pb = (x - lo) / (up - lo)
    np.testing.assert_allclose(R.pct_b(x).to_numpy()[19:], (200 * pb - 100).to_numpy()[19:], rtol=1e-9)


def test_falsifier_pct_b_unscaled_is_detected():
    x = PRICES[:80]
    up, mid, lo = R.bollinger(x, 20, 2.0)
    wrong = (100 * (x - lo) / (up - lo)).to_numpy()
    assert np.nanmax(np.abs(wrong[19:] - R.pct_b(x).to_numpy()[19:])) > 1.0


# --------------------------------------------------------------------------------------------
# M5 / M6  RV z-score and CompositeVol
# --------------------------------------------------------------------------------------------
def test_M5_rv_zscore_zero_when_atr_constant_and_until_bar_25():
    close = np.full(80, 100.0)
    df = make_df(close, close + 1, close - 1, close)
    z = R.rv_zscore(df).to_numpy()
    assert np.all(z == 0.0)
    df2 = df_from_close(PRICES[:80], wick=1.0)
    z2 = R.rv_zscore(df2).to_numpy()
    assert np.all(z2[:25] == 0.0)
    a = R.atr(df2, 14)
    exp = ((a - R.sma(a, 20)) / R.stddev(a, 20)).to_numpy()
    np.testing.assert_allclose(z2[25:], exp[25:], rtol=1e-10)


def test_M6_composite_vol_weights():
    # z = 1, priceZ = 1, vov = 0.25 -> 0.40 - 0.35 + 0.25*((0.25-0.15)/0.10) = 0.30
    assert R.composite_vol_from_parts(1.0, 1.0, 0.25) == pytest.approx(0.30)
    assert R.composite_vol_from_parts(0.0, 0.0, 0.15) == pytest.approx(0.0)
    assert R.composite_vol_from_parts(2.0, -1.0, 0.15) == pytest.approx(0.8 + 0.35)


def test_M6_composite_vol_parts_definitions():
    df = df_from_close(PRICES[:120], wick=1.0, volume=VOLS[:120])
    parts = R.composite_vol(df)
    a = R.atr(df, 14)
    close = df["Close"]
    pz = ((close - R.sma(close, 20)) / R.stddev(close, 20)).to_numpy()
    vov = (R.stddev(a.diff(), 10) / a).to_numpy()
    np.testing.assert_allclose(parts["price_z"].to_numpy()[30:], pz[30:], rtol=1e-10)
    np.testing.assert_allclose(parts["vov"].to_numpy()[30:], vov[30:], rtol=1e-10)
    np.testing.assert_allclose(parts["atr_change"].to_numpy()[30:], a.diff().to_numpy()[30:], rtol=1e-12)
    exp = 0.40 * parts["z_rv"].to_numpy() - 0.35 * pz + 0.25 * (vov - 0.15) / 0.10
    np.testing.assert_allclose(parts["composite"].to_numpy()[30:], exp[30:], rtol=1e-10)


def test_falsifier_composite_weights_swapped_is_detected():
    wrong = 0.35 * 1.0 + 0.40 * (-1.0) + 0.25 * ((0.25 - 0.15) / 0.10)
    assert abs(wrong - R.composite_vol_from_parts(1.0, 1.0, 0.25)) > 1e-9


# --------------------------------------------------------------------------------------------
# M15 HedgingPressure (only the two specified terms + clamps)
# --------------------------------------------------------------------------------------------
def test_M15_basis_term_sign_and_clamp():
    # close far above SMA20 -> (C - SMA20)/ATR*(-25) is very negative -> clamped at -25
    close = np.full(60, 100.0)
    close[-1] = 200.0
    df = make_df(close, close + 1, close - 1, close)
    assert R.hp_basis_term(df).to_numpy()[-1] == -25.0


def test_M15_slope_term_zero_for_flat_and_clamped():
    close = np.full(60, 100.0)
    df = make_df(close, close + 1, close - 1, close)
    assert R.hp_slope_term(df).to_numpy()[-1] == 0.0
    # 40 flat bars then a 10-bar ramp of +100/bar: dSMA5 = 100 > dSMA20 = 50 -> term very
    # negative (x -50 / ATR) -> clamped at -25
    close = np.concatenate([np.full(40, 100.0), 100.0 + 100.0 * np.arange(1, 11)])
    df = make_df(close, close + 1, close - 1, close)
    assert R.hp_slope_term(df).to_numpy()[-1] == -25.0


def test_M15_total_clamp():
    assert R.hp_clamp_total(40, 40, 40, 40) == 100.0        # each clamped to 25 -> 100
    assert R.hp_clamp_total(-40, -40, -40, -40) == -100.0
    assert R.hp_clamp_total(10, -5, 3, 0) == pytest.approx(8.0)


# --------------------------------------------------------------------------------------------
# M17 / M18 / M19 thin wrappers
# --------------------------------------------------------------------------------------------
def test_M17_macd_hist_matches_b6():
    np.testing.assert_allclose(R.macd_hist(PRICES).to_numpy(), R.macd(PRICES, 12, 26, 9)[2].to_numpy())


def test_M18_ema_cross_spread():
    e20, e50, spread = R.ema_cross(PRICES)
    np.testing.assert_allclose(spread.to_numpy(), (R.ema(PRICES, 20) - R.ema(PRICES, 50)).to_numpy())


def test_M19_sma200_distance_from_bar_200():
    s, d = R.sma200_trend(PRICES)
    assert np.all(np.isnan(d.to_numpy()[:200]))
    np.testing.assert_allclose(d.to_numpy()[200:], (PRICES - s.to_numpy())[200:], rtol=1e-12)
    assert s.to_numpy()[199] == pytest.approx(PRICES[:200].mean())
