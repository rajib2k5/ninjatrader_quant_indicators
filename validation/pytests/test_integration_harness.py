"""test_integration_harness.py - the P2 differential of validation/algo-claims-ledger.md.

Loads the newest validation/runs/qi_dump_*.csv (written by QI_EgvDump on a NinjaTrader chart),
recomputes every B/M claim from its Open/High/Low/Close/Volume columns with qi_ref, and asserts
|ref - harness| <= the ledger tolerance from the ledger's warm-up bar (bar >= 300 for recursive
indicators). One test per claim ID. Everything skips (UNVERIFIABLE) when no harness data exist.

Tolerance note: the harness prints doubles with ToString("F4"), so every comparison carries an
extra CSV_QUANT = 0.5e-4 rounding allowance on top of the ledger tolerance (conftest.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import qi_ref as R
from conftest import CSV_QUANT

RECURSIVE_WARMUP = 300


def _col(h, *names):
    """First existing column among `names`, else skip (insufficient harness columns)."""
    for n in names:
        if n in h.columns:
            return h[n].astype(float)
    pytest.skip("UNVERIFIABLE: harness has none of the columns %s" % (names,))


def check(h, ref, col, tol, start, claim, exact=False):
    """Assert |ref - harness| <= tol + CSV_QUANT for bars >= start, with the first offending bar
    quoted in the failure message. Also asserts the harness has a value on every such bar."""
    ref = np.asarray(ref, dtype=float)
    got = np.asarray(col, dtype=float)
    assert len(ref) == len(got)
    idx = np.arange(len(ref))
    m = idx >= start
    assert m.any(), "harness shorter than warm-up (%d bars)" % start
    missing = np.flatnonzero(m & np.isnan(got))
    assert len(missing) == 0, "%s: harness value blank at bars %s" % (claim, missing[:10].tolist())
    ref_nan = np.flatnonzero(m & np.isnan(ref))
    assert len(ref_nan) == 0, "%s: reference undefined at bars %s (warm-up assumption too short)" % (claim, ref_nan[:10].tolist())
    diff = np.abs(ref - got)
    allowed = (0.0 if exact else tol) + CSV_QUANT
    bad = np.flatnonzero(m & (diff > allowed))
    if len(bad):
        b = bad[0]
        raise AssertionError(
            "%s: %d of %d bars exceed tol %.2e (+quant %.1e); first at bar %d (%s): ref=%.6f harness=%.6f diff=%.3e; max diff=%.3e at bar %d"
            % (claim, len(bad), int(m.sum()), tol, CSV_QUANT, b, h["BarTime"].iloc[b], ref[b], got[b], diff[b],
               np.nanmax(diff[m]), int(idx[m][np.nanargmax(diff[m])])))
    return float(np.nanmax(diff[m]))


# ============================================================================================
# built-ins B1-B9
# ============================================================================================
def test_B1_rsi_wilder(harness):
    h = harness
    check(h, R.rsi(h["Close"], 2), _col(h, "QI_RSI2.RSI2", "QI_RSI2.Values[0]"), 1e-3, RECURSIVE_WARMUP, "B1/RSI2")
    check(h, R.rsi(h["Close"], 14), _col(h, "QI_RSI14.RSI14", "QI_RSI14.Values[0]"), 1e-3, RECURSIVE_WARMUP, "B1/RSI14")


def test_B2_ema(harness):
    h = harness
    e20, e50, _ = R.ema_cross(h["Close"])
    check(h, e20, _col(h, "QI_EMACross.Ema20", "QI_EMACross.Values[0]"), 1e-3, RECURSIVE_WARMUP, "B2/EMA20")
    check(h, e50, _col(h, "QI_EMACross.Ema50", "QI_EMACross.Values[1]"), 1e-3, RECURSIVE_WARMUP, "B2/EMA50")


def test_B3_sma200_exact_from_bar_199(harness):
    h = harness
    s, _ = R.sma200_trend(h["Close"])
    check(h, s, _col(h, "QI_SMA200Trend.Sma200", "QI_SMA200Trend.Values[0]"), 1e-6, 199, "B3/SMA200")


def test_B4_atr_via_wide_range_and_vrp(harness):
    h = harness
    check(h, R.wide_range(h), _col(h, "QI_WideRangeBar.WideRange", "QI_WideRangeBar.Values[0]"), 1e-3, RECURSIVE_WARMUP, "B4/(H-L)/ATR14")
    check(h, R.vrp_proxy(h), _col(h, "QI_VRPProxy.VRPProxy", "QI_VRPProxy.Values[0]"), 1e-3, RECURSIVE_WARMUP, "B4/ATR5/ATR14")


def test_B5_population_std_via_bollinger_or_pct_b(harness):
    h = harness
    up, mid, lo = R.bollinger(h["Close"], 20, 2.0)
    if "QI_BollingerPctB.Upper" in h.columns:
        check(h, up, h["QI_BollingerPctB.Upper"], 1e-6, 19, "B5/BollingerUpper(popstd)")
    else:
        check(h, R.pct_b(h["Close"]), _col(h, "QI_BollingerPctB.PctB"), 1e-3, 19, "B5/PctB(popstd)")


def test_B6_macd(harness):
    h = harness
    check(h, R.macd_hist(h["Close"]), _col(h, "QI_MACDHistogram.Histogram", "QI_MACDHistogram.Values[0]"), 1e-3, RECURSIVE_WARMUP, "B6/MACD.Diff")


def test_B7_bollinger_bands(harness):
    h = harness
    up, mid, lo = R.bollinger(h["Close"], 20, 2.0)
    check(h, up, _col(h, "QI_BollingerPctB.Upper"), 1e-6, 19, "B7/Upper")
    check(h, mid, _col(h, "QI_BollingerPctB.Middle"), 1e-6, 19, "B7/Middle")
    check(h, lo, _col(h, "QI_BollingerPctB.Lower"), 1e-6, 19, "B7/Lower")


def test_B8_stochastics_fast(harness):
    h = harness
    k, d = R.stoch_fast(h, 3, 14)
    check(h, k, _col(h, "QI_StochFade.K", "QI_StochFade.Values[0]"), 1e-6, 20, "B8/%K")
    check(h, d, _col(h, "QI_StochFade.D", "QI_StochFade.Values[1]"), 1e-6, 20, "B8/%D")


def test_B9_adx(harness):
    h = harness
    check(h, R.adx(h, 14)[0], _col(h, "QI_ChopIndex.Adx"), 1e-2, RECURSIVE_WARMUP, "B9/ADX14")


# ============================================================================================
# modules M1-M23
# ============================================================================================
def test_M1_ibs_daily(harness):
    h = harness
    col = _col(h, "QI_IBS.IBS", "QI_IBS.Values[0]")
    try:
        check(h, R.ibs_daily(h, "trading"), col, 1e-6, 0, "M1/IBS(trading-day)")
    except AssertionError as e:
        alt = np.nanmax(np.abs(R.ibs_daily(h, "calendar").to_numpy() - col.to_numpy()))
        raise AssertionError("%s | calendar-day keyed variant max diff = %.3e" % (e, alt))


def test_M2_rsi2(harness):
    h = harness
    check(h, R.rsi(h["Close"], 2), _col(h, "QI_RSI2.RSI2", "QI_RSI2.Values[0]"), 1e-3, RECURSIVE_WARMUP, "M2/RSI2")


def test_M3_connors_rsi(harness):
    h = harness
    check(h, R.streak(h["Close"]), _col(h, "QI_ConnorsRSI.Streak"), 0, 1, "M3/streak", exact=True)
    check(h, R.connors_rsi(h["Close"]), _col(h, "QI_ConnorsRSI.CRSI", "QI_ConnorsRSI.Values[0]"), 1e-3, RECURSIVE_WARMUP, "M3/CRSI")


def test_M4_stoch_fade(harness):
    h = harness
    k, d = R.stoch_fast(h, 3, 14)
    check(h, k, _col(h, "QI_StochFade.K", "QI_StochFade.Values[0]"), 1e-6, 20, "M4/%K")
    check(h, d, _col(h, "QI_StochFade.D", "QI_StochFade.Values[1]"), 1e-6, 20, "M4/%D")


def test_M5_rv_zscore(harness):
    h = harness
    check(h, R.rv_zscore(h), _col(h, "QI_RVZScore.RVZScore", "QI_RVZScore.Values[0]"), 1e-3, RECURSIVE_WARMUP, "M5/RVZ")


def test_M6_composite_vol(harness):
    h = harness
    parts = R.composite_vol(h)
    check(h, parts["z_rv"], _col(h, "QI_CompositeVol.RVZScore"), 1e-3, RECURSIVE_WARMUP, "M6/z_RV")
    check(h, parts["atr_change"], _col(h, "QI_CompositeVol.AtrChange"), 1e-3, RECURSIVE_WARMUP, "M6/dATR14")
    check(h, parts["composite"], _col(h, "QI_CompositeVol.CompositeVol", "QI_CompositeVol.Values[0]"), 1e-3, RECURSIVE_WARMUP, "M6/CompositeVol")


def test_M7_turn_of_month(harness):
    h = harness
    check(h, R.turn_of_month(h["BarTime"]), _col(h, "QI_TurnOfMonth.TurnOfMonth", "QI_TurnOfMonth.Values[0]"), 0, 0, "M7/flag", exact=True)


def test_M8_consec_days(harness):
    h = harness
    check(h, R.consec_days(h["Close"]), _col(h, "QI_ConsecDays.Streak", "QI_ConsecDays.Values[0]"), 0, 1, "M8/streak", exact=True)


def test_M9_overnight_gap(harness):
    h = harness
    check(h, R.gap_pct(h), _col(h, "QI_OvernightGap.GapPct", "QI_OvernightGap.Values[0]"), 1e-6, 1, "M9/gap%")


def test_M10_pct_b(harness):
    h = harness
    check(h, R.pct_b(h["Close"]), _col(h, "QI_BollingerPctB.PctB"), 1e-6, 19, "M10/%B")


def test_M11_day_of_week(harness):
    h = harness
    col = _col(h, "QI_TurnaroundTuesday.DayOfWeekValue", "QI_TurnaroundTuesday.Values[0]")
    try:
        check(h, R.day_of_week(h["BarTime"], sunday_zero=True), col, 0, 0, "M11/dow(Sunday=0)", exact=True)
    except AssertionError as e:
        alt = np.nanmax(np.abs(R.day_of_week(h["BarTime"], sunday_zero=False).to_numpy() - col.to_numpy()))
        raise AssertionError("%s | Monday=0 variant max diff = %.3e" % (e, alt))


def test_M12_rsi14(harness):
    h = harness
    check(h, R.rsi(h["Close"], 14), _col(h, "QI_RSI14.RSI14", "QI_RSI14.Values[0]"), 1e-3, RECURSIVE_WARMUP, "M12/RSI14")


def test_M13_vrp_proxy(harness):
    h = harness
    check(h, R.vrp_proxy(h), _col(h, "QI_VRPProxy.VRPProxy", "QI_VRPProxy.Values[0]"), 1e-3, RECURSIVE_WARMUP, "M13/VRP")


def test_M14_wide_range(harness):
    h = harness
    check(h, R.wide_range(h), _col(h, "QI_WideRangeBar.WideRange", "QI_WideRangeBar.Values[0]"), 1e-3, RECURSIVE_WARMUP, "M14/WideRange")


def test_M15_hedging_pressure_clamp_only(harness):
    """The ledger specifies only 2 of the 4 HP terms, so only the +/-100 clamp is testable."""
    h = harness
    col = _col(h, "QI_HedgingPressure.HPScore", "QI_HedgingPressure.Values[0]")
    v = col.to_numpy()[RECURSIVE_WARMUP:]
    assert not np.isnan(v).any()
    assert np.all((v >= -100) & (v <= 100))


def test_M15_hedging_pressure_formula_unverifiable(harness):
    pytest.skip("UNVERIFIABLE on Channel B: ledger M15 names 'vol/price divergence' and 'range "
                "compression' terms without formulas; no reference can be built from the ledger")


def test_M16_vwap(harness):
    h = harness
    # The module's accumulators only start at its bar-50 gate, so the first session in the export
    # is partial by construction; compare from the first session start after bar 50 (ADD-6).
    w = 0
    if R.SESSION_FLAG_COL in h.columns:
        flags = pd.to_numeric(h[R.SESSION_FLAG_COL], errors="coerce").fillna(0).to_numpy()
        starts = np.flatnonzero((flags > 0.5) & (np.arange(len(flags)) > 50))
        w = int(starts[0]) if len(starts) else len(h)
    check(h, R.vwap(h), _col(h, "QI_VWAPDistance.Vwap"), 1e-4, w, "M16/VWAP")
    check(h, R.vwap_distance(h), _col(h, "QI_VWAPDistance.VwapDistance", "QI_VWAPDistance.Values[1]"), 1e-3, max(w, RECURSIVE_WARMUP), "M16/dist")


def test_M17_macd_histogram(harness):
    h = harness
    check(h, R.macd_hist(h["Close"]), _col(h, "QI_MACDHistogram.Histogram", "QI_MACDHistogram.Values[0]"), 1e-3, RECURSIVE_WARMUP, "M17/hist")


def test_M18_ema_cross(harness):
    h = harness
    e20, e50, spread = R.ema_cross(h["Close"])
    check(h, spread, _col(h, "QI_EMACross.Spread"), 1e-3, RECURSIVE_WARMUP, "M18/Spread")


def test_M19_sma200_trend(harness):
    h = harness
    s, d = R.sma200_trend(h["Close"])
    check(h, d, _col(h, "QI_SMA200Trend.Distance"), 1e-6, 200, "M19/Distance")


def test_M20_atr_regime(harness):
    h = harness
    check(h, R.atr_regime(h), _col(h, "QI_ATRRegime.ATRRegime", "QI_ATRRegime.Values[0]"), 1e-3, RECURSIVE_WARMUP, "M20/ATRRegime")


def test_M21_volume_spike(harness):
    h = harness
    check(h, R.volume_spike(h), _col(h, "QI_VolumeSpike.VolumeSpike", "QI_VolumeSpike.Values[0]"), 1e-4, 19, "M21/VolSpike")


def test_M22_volume_delta(harness):
    h = harness
    d, cum, s10 = R.volume_delta(h)
    check(h, d, _col(h, "QI_VolumeDelta.VolDelta", "QI_VolumeDelta.Values[0]"), 0, 1, "M22/delta", exact=True)
    check(h, cum, _col(h, "QI_VolumeDelta.CumDelta20", "QI_VolumeDelta.Values[1]"), 0, 21, "M22/Cum20", exact=True)
    check(h, s10, _col(h, "QI_VolumeDelta.DeltaSMA10", "QI_VolumeDelta.Values[2]"), 1e-4, 10, "M22/SMA10")


def test_M23_chop_index(harness):
    h = harness
    check(h, R.chop(h), _col(h, "QI_ChopIndex.Chop", "QI_ChopIndex.Values[0]"), 1e-4, 14, "M23/CHOP")
    check(h, R.vol_ratio(h), _col(h, "QI_ChopIndex.VolRatio"), 1e-4, 19, "M23/VolRatio")
    check(h, R.chop_state(h), _col(h, "QI_ChopIndex.ChoppyFlag"), 0, RECURSIVE_WARMUP, "M23/state", exact=True)


def test_M27_key_levels_unverifiable(harness):
    h = harness
    if any(c.startswith("QI_KeyLevels.") for c in h.columns):
        pytest.skip("UNVERIFIABLE: ledger M27 gives session windows but no replayable level formula")
    pytest.skip("UNVERIFIABLE: harness exports no QI_KeyLevels columns")


# ============================================================================================
# P3 falsifier: one perturbed reference constant must break the differential
# ============================================================================================
def test_falsifier_differential(harness):
    """RSI period 14 -> 13 in the reference must exceed the B1 tolerance against the harness."""
    h = harness
    col = _col(h, "QI_RSI14.RSI14", "QI_RSI14.Values[0]")
    wrong = R.rsi(h["Close"], 13).to_numpy()
    got = col.to_numpy()
    m = np.arange(len(got)) >= RECURSIVE_WARMUP
    diff = np.abs(wrong - got)[m]
    assert np.nanmax(diff) > 1e-3 + CSV_QUANT, "perturbed reference (RSI 13) was NOT detected: max diff %.3e" % np.nanmax(diff)
    with pytest.raises(AssertionError):
        check(h, wrong, col, 1e-3, RECURSIVE_WARMUP, "falsifier/RSI13")
