"""patterns.py - faithful Python ports of four QI NinjaScript indicators.

Educational research only. Not financial advice. See DISCLAIMER.md.

Ported (shipping C#, read in full):
    indicators/QI_HedgingPressure.cs   -> hp_score(df)
    indicators/QI_LiquiditySweep.cs    -> liquidity_sweep(df)  (+ its own PDH/PDL, monthly, 30-min ORB tracking)
    indicators/QI_OrderFlowPlus.cs     -> order_flow_plus(df)
    indicators/QI_SMC.cs               -> smc(df)
Convenience aliases: sweep_structure(df), ofp_structure(df), smc_structure(df) (the Structure plots).
Event logs (every label the C# would draw, with its component patterns): liquidity_sweep_events(df),
order_flow_plus_events(df), smc_events(df).

Input: pandas DataFrame with columns BarTime (naive datetime, US Central, bar CLOSE time), Open, High,
Low, Close, Volume; oldest row first. Row position t is NinjaTrader's CurrentBar; "x[k]" in the C#
(k bars ago) is row t-k here.

NinjaTrader semantics reproduced
--------------------------------
* Calculate.OnBarClose, one OnBarUpdate per row, in row order, with every warm-up gate and early return
  of the QI files: global `CurrentBar < 50` return; LiquiditySweep detection and the OF+/SMC swing
  update only from `CurrentBar >= SwingLookback*2+5`; `CurrentBar < 20` guards; `CurrentBar >= 2/3/4`
  guards. Bars before 50 carry NaN (the C# never writes Values there).
* OnBarUpdate ordering of each QI file (e.g. LiquiditySweep: UpdateKeyLevels -> Values = 0 ->
  DetectLiquiditySweeps: barsSince++ -> swings -> consolidation -> Donchian -> pending confirmation
  -> 7 checks in order -> duplicate filter).
* NT8 ATR(14) recursion (validation/pytests/qi_ref.py `atr`, ledger B4 = @ATR.cs) and NT8 SMA as
  @SMA.cs computes it on Minute bars (IsRemoveLastBarSupported = false): running
  `sum = priorSum + x[0] - x[Period]`, value = sum / min(CurrentBar+1, Period). qi_ref.sma is a
  pandas rolling mean with NaN warm-up, i.e. not the NT recursion, so it is not used.
* C# double.MinValue / double.MaxValue sentinels, int.MaxValue initial bar counters with C#
  unchecked int32 wrap-around on `++`, List.Add / RemoveAt(0) / RemoveAt(i) bookkeeping with the same
  loop directions, zone caps (5 / 10) and expiries (50 / 100 / 200 bars), first-come direction rules.
* Defaults of the C# properties: SwingLookback 20, SweepWickMultiple 2.0, SweepVolMultiple 1.5,
  EqualLevelTolerance 0.05, ConsolidationAtrRatio 0.6, Use*Levels true, DuplicateBarWindow 5.
* Key levels: TimeZoneInfo.ConvertTime(Time[0], <chart zone>, "Central Standard Time") is the identity
  on this machine (PC zone = US Central incl. DST), so BarTime is used as CST time directly.
  DayOfWeek / Date / Month / TimeOfDay are taken from BarTime.
* volDelta (a Series<double>) is only written from bar 50 on; unwritten slots are read as 0.0
  (ASSUMPTION: NT Series<double> default). This can affect only ComputeCumDelta10 and the
  volDelta[1..3] reads on bars 50..59.

Not ported (no effect on any plotted/returned value): label text/fonts/brushes, Draw.* calls, the HP
price lines/panel, the Start->End connecting line, the disclaimer, the never-read swingHigh/LowSeries,
prevSwing*Bar, prevOrbHigh/Low and the LiquiditySweep volDelta series (no sweep check reads it).

Observations from the C# (kept, not "fixed"):
* "Sweep MoHigh/MoLow" can never fire: UpdateKeyLevels raises klMonthlyHigh/Low with the current bar
  before the check, so High[0] > klMonthlyHigh is always false.
* OF+ "DeltaRev" can never fire: volDelta[0] < 0 implies Close[0] < Close[1], contradicting the
  required Close[0] > Close[1] (and symmetrically).
* LiquiditySweep "Liq Sweep" (0.70) always co-fires with "SFP" (0.50) (identical price condition on
  the swing levels), so its End confidence is min(0.70 + 0.50 + ..., 1.0) = 1.0.
* HP: rc and basis always have opposite signs, so |HP| <= 75 and the +/-100 clamp never binds.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
_QIREF_DIR = str(_REPO / "validation" / "pytests")
if _QIREF_DIR not in sys.path:
    sys.path.append(_QIREF_DIR)          # appended, not prepended: never shadows another module
import qi_ref  # noqa: E402  (atr = NT8 ATR recursion, ledger B4)

__all__ = [
    "hp_score", "liquidity_sweep", "order_flow_plus", "smc",
    "sweep_structure", "ofp_structure", "smc_structure",
    "liquidity_sweep_events", "order_flow_plus_events", "smc_events",
    "nt_sma", "nt_atr",
]

DBL_MIN = -sys.float_info.max            # C# double.MinValue
DBL_MAX = sys.float_info.max             # C# double.MaxValue
INT_MAX = 2147483647                     # C# int.MaxValue
INT_MIN = -2147483648

_NS = 1_000_000_000
_T_0830 = (8 * 3600 + 30 * 60) * _NS
_T_0900 = 9 * 3600 * _NS
_T_1600 = 16 * 3600 * _NS

_REQUIRED = ("BarTime", "Open", "High", "Low", "Close", "Volume")


# ============================================================================================
# helpers
# ============================================================================================
def _inc32(x):
    """C# unchecked `x++` on an int: int.MaxValue + 1 wraps to int.MinValue."""
    return INT_MIN if x == INT_MAX else x + 1


def _check(df):
    missing = [c for c in _REQUIRED if c not in df.columns]
    if missing:
        raise KeyError("patterns: input DataFrame lacks column(s) %s" % missing)


def _ohlcv(df):
    return tuple(np.asarray(df[c], dtype=float) for c in ("Open", "High", "Low", "Close", "Volume"))


def nt_sma(x, period):
    """NT8 @SMA.cs, Minute-bars branch (IsRemoveLastBarSupported = false), computed from bar 0:
    sum = priorSum + x[0] - (CurrentBar >= Period ? x[Period] : 0); value = sum / min(CurrentBar+1, Period)."""
    xl = np.asarray(x, dtype=float).tolist()
    n = len(xl)
    out = [0.0] * n
    s = 0.0
    for t in range(n):
        s = s + xl[t] - (xl[t - period] if t >= period else 0)
        out[t] = s / (t + 1 if t < period else period)
    return np.asarray(out, dtype=float)


def nt_atr(df, period=14):
    """NT8 @ATR.cs recursion via validation/pytests/qi_ref.py atr() (ledger B4):
    ATR[0] = H-L; ATR[t] = ((min(t+1,P)-1)*ATR[t-1] + TR[t]) / min(t+1,P)."""
    return qi_ref.atr(df[["High", "Low", "Close"]].reset_index(drop=True), period).to_numpy(dtype=float)


def _time_parts(df):
    """(date ordinal [days], weekday Mon=0..Sun=6, month 1..12, time of day [ns]) of BarTime (= CST)."""
    dti = pd.DatetimeIndex(pd.to_datetime(df["BarTime"]))
    if dti.tz is not None:
        raise ValueError("patterns: BarTime must be naive US Central time")
    ns = dti.asi8
    day_ns = dti.normalize().asi8
    return ((day_ns // (86400 * _NS)).tolist(), dti.weekday.tolist(), dti.month.tolist(),
            (ns - day_ns).tolist())


def _swing_flags(H, L, lb):
    """isSwingHigh[t]: no i in 0..2lb, i != lb, with High[i] > High[lb]  <=>  High[t-lb] == max(High[t-2lb..t]).
    Only defined for t >= 2lb (C# `if (CurrentBar < lb*2) return;`)."""
    n = len(H)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    w = 2 * lb + 1
    if n >= w:
        from numpy.lib.stride_tricks import sliding_window_view
        mx = sliding_window_view(H, w).max(axis=1)
        mn = sliding_window_view(L, w).min(axis=1)
        sh[2 * lb:] = H[lb:n - lb] >= mx
        sl[2 * lb:] = L[lb:n - lb] <= mn
    return sh.tolist(), sl.tolist()


def _prior_extremes(H, L, k):
    """max(High[1..k]) and min(Low[1..k]) (the k bars BEFORE bar t), for t >= k; sentinels before."""
    n = len(H)
    hi = np.full(n, DBL_MIN)
    lo = np.full(n, DBL_MAX)
    if n > k:
        from numpy.lib.stride_tricks import sliding_window_view
        hi[k:] = sliding_window_view(H[:-1], k).max(axis=1)
        lo[k:] = sliding_window_view(L[:-1], k).min(axis=1)
    return hi.tolist(), lo.tolist()


def _clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _events_frame(events, df):
    cols = ["bar", "BarTime", "kind", "direction", "confidence", "patterns", "level"]
    if not events:
        return pd.DataFrame({c: pd.Series(dtype=object) for c in cols})
    ev = pd.DataFrame(events, columns=["bar", "kind", "direction", "confidence", "patterns", "level"])
    ev.insert(1, "BarTime", pd.to_datetime(df["BarTime"]).to_numpy()[ev["bar"].to_numpy()])
    return ev


# ============================================================================================
# QI_HedgingPressure (QI 135-196)
# ============================================================================================
def hp_score(df):
    """HP composite score per bar (Values[0]); NaN on bars < 50 (QI 137 `CurrentBar < 50` return)."""
    _check(df)
    O, H, L, C, V = _ohlcv(df)
    n = len(C)
    atr = nt_atr(df, 14).tolist()
    sma20 = nt_sma(C, 20).tolist()        # sma20hp == closeSma20 (same NT cached SMA(Close,20))
    sma5 = nt_sma(C, 5).tolist()
    rsma20 = nt_sma(H - L, 20).tolist()   # SMA(Range(), 20), Range = High - Low
    vsma20 = nt_sma(V, 20).tolist()
    Ol, Hl, Ll, Cl, Vl = O.tolist(), H.tolist(), L.tolist(), C.tolist(), V.tolist()
    out = [float("nan")] * n
    for t in range(50, n):
        a = atr[t]
        s20 = sma20[t]
        if a <= 0 or s20 <= 0:
            out[t] = 0.0
            continue
        c = Cl[t]
        o = Ol[t]
        basis_dev = (c - s20) / a
        basis_score = _clamp(basis_dev * -25.0, -25.0, 25.0)

        short_slope = (sma5[t] - sma5[t - 1]) / a if (sma5[t] > 0 and t > 5) else 0.0
        long_slope = (s20 - sma20[t - 1]) / a if (s20 > 0 and t > 20) else 0.0
        slope_diff = short_slope - long_slope
        term_score = _clamp(slope_diff * -50.0, -25.0, 25.0)

        price_change_pct = abs(c - o) / a if a > 0 else 1.0
        vs = vsma20[t]
        vol_ratio = Vl[t] / vs if vs > 0 else 1.0
        vp_div = 0.0
        if vol_ratio > 1.2 and price_change_pct < 0.5:
            direction = -1.0 if c < o else 1.0
            vp_div = direction * vol_ratio * 10.0
        vp_score = _clamp(vp_div, -25.0, 25.0)

        rs = rsma20[t]
        range_ratio = (Hl[t] - Ll[t]) / rs if rs > 0 else 1.0
        rc_score = 0.0
        if range_ratio < 0.6 and vol_ratio > 1.3:
            direction = -1.0 if c < s20 else 1.0
            rc_score = _clamp(direction * (1.0 - range_ratio) * 50.0, -25.0, 25.0)

        composite = basis_score + term_score + vp_score + rc_score
        out[t] = _clamp(composite, -100.0, 100.0)
    return pd.Series(out, index=df.index, name="hp_score", dtype=float)


# ============================================================================================
# QI_LiquiditySweep (QI 246-750)
# ============================================================================================
def _run_liquidity_sweep(df, swing_lookback=20, sweep_wick_multiple=2.0, sweep_vol_multiple=1.5,
                         equal_level_tolerance=0.05, consolidation_atr_ratio=0.6,
                         use_prev_day_levels=True, use_monthly_levels=True, use_orb_levels=True,
                         duplicate_bar_window=5, events=None):
    _check(df)
    O, H, L, C, V = _ohlcv(df)
    n = len(C)
    lb = int(swing_lookback)
    atr = nt_atr(df, 14).tolist()
    vsma = nt_sma(V, 20).tolist()
    asma = nt_sma(np.asarray(atr), 50).tolist()
    day, wday, month, tod = _time_parts(df)
    sh_flag, sl_flag = _swing_flags(H, L, lb)
    don_h, don_l = _prior_extremes(H, L, lb)            # UpdateDonchianChannel (limit = lb for t >= lb)
    rng_h, rng_l = _prior_extremes(H, L, 2 * lb)        # CheckWyckoffSpringUpthrust range
    Ol, Hl, Ll, Cl, Vl = O.tolist(), H.tolist(), L.tolist(), C.tolist(), V.tolist()

    wick_mult = float(sweep_wick_multiple)
    vol_mult = float(sweep_vol_multiple)
    eq_tol = float(equal_level_tolerance)
    cons_ratio = float(consolidation_atr_ratio)
    dup_win = int(duplicate_bar_window)
    log = events is not None

    nan = float("nan")
    conf = [nan] * n
    struct = [nan] * n

    # key levels (QI 193-210)
    prev_day_high, prev_day_low = DBL_MIN, DBL_MAX
    today_high, today_low = DBL_MIN, DBL_MAX
    today_date = None
    today_started = False
    mo_high, mo_low = DBL_MIN, DBL_MAX
    cur_month = 0
    orb_high, orb_low = DBL_MIN, DBL_MAX
    orb_complete = False
    orb_date = None
    # sweep state (QI 213-240)
    last_sh, last_sl = DBL_MIN, DBL_MAX
    pool_p, pool_b, pool_hi = [], [], []
    cons_high, cons_low = DBL_MIN, DBL_MAX
    cons_start = 0
    in_cons = False
    pend_bar, pend_dir, pend_lvl, pend_type, pend_win = 0, 0, 0.0, "", 3
    last_dir = 0
    bars_since = INT_MAX
    gate = lb * 2 + 5

    for t in range(50, n):
        h = Hl[t]
        l = Ll[t]
        c = Cl[t]
        o = Ol[t]
        v = Vl[t]
        # ---- UpdateKeyLevels (QI 282-404); cstTime == BarTime ----
        weekend = wday[t] >= 5
        if use_prev_day_levels and not weekend:
            if day[t] != today_date:
                if today_started and today_high > DBL_MIN and today_low < DBL_MAX:
                    prev_day_high = today_high
                    prev_day_low = today_low
                today_high, today_low = DBL_MIN, DBL_MAX
                today_date = day[t]
                today_started = False
            if _T_0830 <= tod[t] < _T_1600:
                today_started = True
                if h > today_high:
                    today_high = h
                if l < today_low:
                    today_low = l
        if use_monthly_levels:
            if month[t] != cur_month:
                mo_high, mo_low = DBL_MIN, DBL_MAX
                cur_month = month[t]
            if h > mo_high:
                mo_high = h
            if l < mo_low:
                mo_low = l
        if use_orb_levels and not weekend:
            if day[t] != orb_date:
                orb_high, orb_low = DBL_MIN, DBL_MAX
                orb_complete = False
                orb_date = day[t]
            if _T_0830 <= tod[t] < _T_0900 and not orb_complete:
                if h > orb_high:
                    orb_high = h
                if l < orb_low:
                    orb_low = l
            if not orb_complete and day[t] == orb_date:
                if tod[t] >= _T_0900 and orb_high > DBL_MIN:
                    orb_complete = True
        # (UpdateVolumeDelta: series maintained by the C# but never read by a sweep check)

        conf[t] = 0.0
        struct[t] = 0.0

        # ---- DetectLiquiditySweeps (QI 426-476) ----
        if t < gate:
            continue
        bars_since = _inc32(bars_since)

        # UpdateSwingPoints (QI 478-523)
        if sh_flag[t]:
            cand = Hl[t - lb]
            if last_sh > DBL_MIN and abs(cand - last_sh) < eq_tol * 0.01 * cand:
                avg = (cand + last_sh) / 2.0
                if len(pool_p) >= 10:
                    del pool_p[0], pool_b[0], pool_hi[0]
                pool_p.append(avg)
                pool_b.append(t)
                pool_hi.append(True)
            last_sh = cand
        if sl_flag[t]:
            cand = Ll[t - lb]
            if last_sl < DBL_MAX and abs(cand - last_sl) < eq_tol * 0.01 * cand:
                avg = (cand + last_sl) / 2.0
                if len(pool_p) >= 10:
                    del pool_p[0], pool_b[0], pool_hi[0]
                pool_p.append(avg)
                pool_b.append(t)
                pool_hi.append(False)
            last_sl = cand
        for i in range(len(pool_p) - 1, -1, -1):
            if t - pool_b[i] > 200:
                del pool_p[i], pool_b[i], pool_hi[i]

        # UpdateConsolidationZone (QI 525-538)
        if not (t < 50 or asma[t] <= 0):
            ratio = atr[t] / asma[t]
            if ratio < cons_ratio:
                if not in_cons:
                    in_cons = True
                    cons_start = t
                    cons_high = h
                    cons_low = l
                else:
                    if h > cons_high:
                        cons_high = h
                    if l < cons_low:
                        cons_low = l
            elif ratio >= cons_ratio * 1.5 and t - cons_start > 50:
                in_cons = False

        # UpdateDonchianChannel (QI 540-546)
        dh = don_h[t]
        dl = don_l[t]

        # CheckPendingSweepConfirmation (QI 548-560) - End label 0.55, not subject to the window
        if pend_dir != 0:
            if t - pend_bar > pend_win:
                pend_dir = 0
            elif (pend_dir == 1 and c > pend_lvl) or (pend_dir == -1 and c < pend_lvl):
                conf[t] = 0.55
                struct[t] = float(pend_dir)
                if log:
                    events.append((t, "End", pend_dir, 0.55, [(pend_type, 0.55)], pend_lvl))
                last_dir = pend_dir
                bars_since = 0
                pend_dir = 0

        results = []
        total_conf = 0.0
        sweep_dir = 0
        swept = 0.0

        body = abs(c - o)
        vs = vsma[t]

        # 1. CheckBasicLiquiditySweep (QI 562-606)
        d1 = 0
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        vol_spike = vs > 0 and v > vol_mult * vs
        wick_thresh = wick_mult if body > 0 else 1.0
        if body > 0:
            wr_up = upper_wick / body
            wr_lo = lower_wick / body
        else:
            wr_up = 99.0 if upper_wick > 0 else 0.0
            wr_lo = 99.0 if lower_wick > 0 else 0.0
        while True:
            if last_sh > DBL_MIN and h > last_sh and c < last_sh:
                if wr_up >= wick_thresh and vol_spike:
                    d1, c1, lv1, n1 = -1, 0.70, last_sh, "Liq Sweep"
                    break
            if last_sl < DBL_MAX and l < last_sl and c > last_sl:
                if wr_lo >= wick_thresh and vol_spike:
                    d1, c1, lv1, n1 = 1, 0.70, last_sl, "Liq Sweep"
                    break
            if use_prev_day_levels and prev_day_high > DBL_MIN:
                if h > prev_day_high and c < prev_day_high and vol_spike:
                    if wr_up >= wick_thresh:
                        d1, c1, lv1, n1 = -1, 0.85, prev_day_high, "Sweep PDH"
                        break
                if l < prev_day_low and c > prev_day_low and vol_spike:
                    if wr_lo >= wick_thresh:
                        d1, c1, lv1, n1 = 1, 0.85, prev_day_low, "Sweep PDL"
                        break
            if use_orb_levels and orb_complete and orb_high > DBL_MIN:
                if h > orb_high and c < orb_high and vol_spike:
                    if wr_up >= wick_thresh:
                        d1, c1, lv1, n1 = -1, 0.85, orb_high, "Sweep ORB-H"
                        break
                if l < orb_low and c > orb_low and vol_spike:
                    if wr_lo >= wick_thresh:
                        d1, c1, lv1, n1 = 1, 0.85, orb_low, "Sweep ORB-L"
                        break
            if use_monthly_levels and mo_high > DBL_MIN:
                if h > mo_high and c < mo_high and vol_spike:
                    if wr_up >= wick_thresh:
                        d1, c1, lv1, n1 = -1, 0.85, mo_high, "Sweep MoHigh"
                        break
                if l < mo_low and c > mo_low and vol_spike:
                    if wr_lo >= wick_thresh:
                        d1, c1, lv1, n1 = 1, 0.85, mo_low, "Sweep MoLow"
                        break
            break
        if d1 != 0:
            sweep_dir = d1
            total_conf += c1
            swept = lv1
            results.append((n1, c1))

        # 2. CheckSwingFailurePattern (QI 608-621)
        d2 = 0
        if last_sh > DBL_MIN and h > last_sh and c < last_sh:
            d2, c2, lv2, n2 = -1, 0.50, last_sh, "SFP"
        elif last_sl < DBL_MAX and l < last_sl and c > last_sl:
            d2, c2, lv2, n2 = 1, 0.50, last_sl, "SFP"
        elif t >= 2 and last_sh > DBL_MIN and Hl[t - 1] > last_sh and Cl[t - 1] > last_sh and c < last_sh:
            d2, c2, lv2, n2 = -1, 0.60, last_sh, "SFP(2bar)"
        elif t >= 2 and last_sl < DBL_MAX and Ll[t - 1] < last_sl and Cl[t - 1] < last_sl and c > last_sl:
            d2, c2, lv2, n2 = 1, 0.60, last_sl, "SFP(2bar)"
        if d2 != 0:
            if sweep_dir == 0:
                sweep_dir = d2
            total_conf += c2
            if swept == 0:
                swept = lv2
            results.append((n2, c2))

        # 3. CheckEqualLevelTrap (QI 623-636)
        d3 = 0
        for i in range(len(pool_p) - 1, -1, -1):
            lvl = pool_p[i]
            if pool_hi[i] and h > lvl and c < lvl:
                d3, c3, lv3, n3 = -1, 0.60, lvl, "EqHigh Trap"
                del pool_p[i], pool_b[i], pool_hi[i]
                break
            if (not pool_hi[i]) and l < lvl and c > lvl:
                d3, c3, lv3, n3 = 1, 0.60, lvl, "EqLow Trap"
                del pool_p[i], pool_b[i], pool_hi[i]
                break
        if d3 != 0:
            if sweep_dir == 0:
                sweep_dir = d3
            total_conf += c3
            if swept == 0:
                swept = lv3
            results.append((n3, c3))

        # 4. CheckConsolidationBreakoutTrap (QI 638-649)
        d4 = 0
        if not ((not in_cons) and t - cons_start > 10) and not (cons_high <= cons_low):
            big_vol = vs > 0 and v > 2.0 * vs
            if big_vol:
                if h > cons_high and c <= cons_high:
                    d4, c4, lv4, n4 = -1, 0.65, cons_high, "Consol Trap"
                elif l < cons_low and c >= cons_low:
                    d4, c4, lv4, n4 = 1, 0.65, cons_low, "Consol Trap"
        if d4 != 0:
            if sweep_dir == 0:
                sweep_dir = d4
            total_conf += c4
            if swept == 0:
                swept = lv4
            results.append((n4, c4))

        # 5. CheckWyckoffSpringUpthrust (QI 651-665)
        d5 = 0
        if t >= 2 * lb + 1:
            r_hi = rng_h[t]
            r_lo = rng_l[t]
            if not (r_hi <= r_lo):
                base_conf = 0.75 if in_cons else 0.60
                if l < r_lo and c > r_lo and c > o:
                    d5, c5, lv5, n5 = 1, base_conf, r_lo, "Spring"
                elif h > r_hi and c < r_hi and c < o:
                    d5, c5, lv5, n5 = -1, base_conf, r_hi, "Upthrust"
        if d5 != 0:
            if sweep_dir == 0:
                sweep_dir = d5
            total_conf += c5
            if swept == 0:
                swept = lv5
            results.append((n5, c5))

        # 6. CheckTurtleSoup (QI 667-675)
        d6 = 0
        if not (dh <= DBL_MIN or dl >= DBL_MAX):
            if h > dh and c < dh and o < dh:
                d6, c6, lv6, n6 = -1, 0.55, dh, "Turtle Soup"
            elif l < dl and c > dl and o > dl:
                d6, c6, lv6, n6 = 1, 0.55, dl, "Turtle Soup"
        if d6 != 0:
            if sweep_dir == 0:
                sweep_dir = d6
            total_conf += c6
            if swept == 0:
                swept = lv6
            results.append((n6, c6))

        # 7. CheckVolumeDivergenceFakeout (QI 677-705) - always returns false; may arm a pending sweep
        if pend_dir == 0:
            new_high = last_sh > DBL_MIN and h > last_sh
            new_low = last_sl < DBL_MAX and l < last_sl
            if new_high or new_low:
                rng = h - l
                weak_vol = vs > 0 and v < 0.8 * vs
                absorbed_vol = vs > 0 and v > vol_mult * vs and rng > 0 and body < 0.3 * rng
                if weak_vol or absorbed_vol:
                    p_type = "VolDiv (weak)" if weak_vol else "VolDiv (absorbed)"
                    if new_high:
                        pend_bar, pend_dir, pend_lvl, pend_type, pend_win = t, -1, last_sh, p_type, 3
                    else:
                        pend_bar, pend_dir, pend_lvl, pend_type, pend_win = t, 1, last_sl, p_type, 3
                    if log:   # Start label (no Values write, no duplicate filter)
                        events.append((t, "Start", pend_dir, 0.35, [(p_type, 0.35)], pend_lvl))

        if not results or sweep_dir == 0:
            continue
        if sweep_dir == last_dir and bars_since < dup_win:
            continue
        total_conf = min(total_conf, 1.0)
        conf[t] = total_conf
        struct[t] = float(sweep_dir)
        if log:
            events.append((t, "End", sweep_dir, total_conf, results, swept))
        last_dir = sweep_dir
        bars_since = 0

    return conf, struct


def liquidity_sweep(df, **params):
    """QI_LiquiditySweep plots: confidence (Values[0]) and structure (Values[1], +1/-1, 0 otherwise).
    Values are written on End events only (QI 729-733); 0 on other bars >= 50; NaN on bars < 50."""
    conf, struct = _run_liquidity_sweep(df, **params)
    return pd.DataFrame({"confidence": conf, "structure": struct}, index=df.index, dtype=float)


def liquidity_sweep_events(df, **params):
    """Every LiquiditySweep label: kind 'End' (writes the plots) or 'Start' (VolDiv, 0.35, no plot write);
    patterns = [(name, confidence)] in check order; End confidence = min(sum, 1.0)."""
    events = []
    _run_liquidity_sweep(df, events=events, **params)
    return _events_frame(events, df)


def sweep_structure(df, **params):
    s = liquidity_sweep(df, **params)["structure"]
    s.name = "sweep_structure"
    return s


# ============================================================================================
# QI_OrderFlowPlus (QI 156-347)
# ============================================================================================
def _run_order_flow_plus(df, swing_lookback=20, duplicate_bar_window=5, events=None):
    _check(df)
    O, H, L, C, V = _ohlcv(df)
    n = len(C)
    lb = int(swing_lookback)
    atr = nt_atr(df, 14).tolist()
    vsma = nt_sma(V, 20).tolist()
    sh_flag, sl_flag = _swing_flags(H, L, lb)
    Ol, Hl, Ll, Cl, Vl = O.tolist(), H.tolist(), L.tolist(), C.tolist(), V.tolist()
    dup_win = int(duplicate_bar_window)
    log = events is not None

    nan = float("nan")
    conf = [nan] * n
    struct = [nan] * n
    vd = [0.0] * n                      # volDelta; unwritten (bars < 50) read as 0.0
    last_sh, last_sl = DBL_MIN, DBL_MAX
    cd_at_sh = 0.0
    cd_at_sl = 0.0
    last_of_dir = 0
    bars_since = INT_MAX
    gate = lb * 2 + 5

    for t in range(50, n):
        h = Hl[t]
        l = Ll[t]
        c = Cl[t]
        o = Ol[t]
        v = Vl[t]
        # UpdateVolumeDelta (QI 179-190)
        if t < 1:
            vd[t] = 0.0
        else:
            pc = c - Cl[t - 1]
            vd[t] = v if pc > 0 else (-v if pc < 0 else 0.0)

        conf[t] = 0.0
        struct[t] = 0.0

        # swing points only from CurrentBar >= SwingLookback*2+5 (QI 168-169)
        if t >= gate and t >= lb * 2:
            if sh_flag[t]:
                last_sh = Hl[t - lb]
                cd = 0.0
                for i in range(min(10, t)):
                    cd += vd[t - i]
                cd_at_sh = cd
            if sl_flag[t]:
                last_sl = Ll[t - lb]
                cd = 0.0
                for i in range(min(10, t)):
                    cd += vd[t - i]
                cd_at_sl = cd

        # ProcessOrderFlowSignals (QI 243-347)
        if t < 20:
            continue
        bars_since = _inc32(bars_since)
        patterns = []
        best = 0.0
        of_dir = 0
        body = abs(c - o)
        rng = h - l
        cum_d10 = 0.0
        for i in range(min(10, t)):
            cum_d10 += vd[t - i]

        # 1. Delta Divergence 0.78 (low side may overwrite the high side's direction)
        if last_sh > DBL_MIN and h > last_sh and cum_d10 < cd_at_sh:
            of_dir = -1
            best = max(best, 0.78)
            patterns.append(("DeltaDiv", 0.78))
        if last_sl < DBL_MAX and l < last_sl and cum_d10 > cd_at_sl:
            of_dir = 1
            best = max(best, 0.78)
            patterns.append(("DeltaDiv", 0.78))
        # 2. Absorption 0.65
        vs = vsma[t]
        if vs > 0 and v > 1.5 * vs and rng > 0.5 * atr[t] and rng > 0 and body < 0.30 * rng:
            abs_dir = 1 if c > o else -1
            if of_dir == 0:
                of_dir = abs_dir
            best = max(best, 0.65)
            patterns.append(("Absorption", 0.65))
        # 3. Exhaustion 0.60
        if t >= 3:
            new_high = last_sh > DBL_MIN and h >= last_sh
            new_low = last_sl < DBL_MAX and l <= last_sl
            declining = abs(vd[t]) < abs(vd[t - 1]) and abs(vd[t - 1]) < abs(vd[t - 2])
            if (new_high or new_low) and declining:
                exh_dir = -1 if new_high else 1
                if of_dir == 0:
                    of_dir = exh_dir
                best = max(best, 0.60)
                patterns.append(("Exhaustion", 0.60))
        # 4. Stacked Delta 0.55
        if t >= 3:
            all_pos = vd[t] > 0 and vd[t - 1] > 0 and vd[t - 2] > 0
            all_neg = vd[t] < 0 and vd[t - 1] < 0 and vd[t - 2] < 0
            if all_pos:
                if of_dir == 0:
                    of_dir = 1
                best = max(best, 0.55)
                patterns.append(("StackedDelta", 0.55))
            elif all_neg:
                if of_dir == 0:
                    of_dir = -1
                best = max(best, 0.55)
                patterns.append(("StackedDelta", 0.55))
        # 5. Delta Reversal 0.70 (unreachable as written in the C#; kept verbatim)
        if t >= 4:
            prev3_pos = vd[t - 1] > 0 and vd[t - 2] > 0 and vd[t - 3] > 0
            prev3_neg = vd[t - 1] < 0 and vd[t - 2] < 0 and vd[t - 3] < 0
            if prev3_pos and vd[t] < 0 and c > Cl[t - 1]:
                if of_dir == 0:
                    of_dir = -1
                best = max(best, 0.70)
                patterns.append(("DeltaRev", 0.70))
            elif prev3_neg and vd[t] > 0 and c < Cl[t - 1]:
                if of_dir == 0:
                    of_dir = 1
                best = max(best, 0.70)
                patterns.append(("DeltaRev", 0.70))

        if not patterns or of_dir == 0:
            continue
        if of_dir == last_of_dir and bars_since < dup_win:
            continue
        best = min(best, 1.0)
        conf[t] = best
        struct[t] = float(of_dir)
        if log:
            events.append((t, "Signal", of_dir, best, patterns, float("nan")))
        last_of_dir = of_dir
        bars_since = 0

    return conf, struct


def order_flow_plus(df, **params):
    """QI_OrderFlowPlus plots: confidence (best of the bar) and structure (+1/-1/0); NaN on bars < 50."""
    conf, struct = _run_order_flow_plus(df, **params)
    return pd.DataFrame({"confidence": conf, "structure": struct}, index=df.index, dtype=float)


def order_flow_plus_events(df, **params):
    events = []
    _run_order_flow_plus(df, events=events, **params)
    return _events_frame(events, df)


def ofp_structure(df, **params):
    s = order_flow_plus(df, **params)["structure"]
    s.name = "ofp_structure"
    return s


# ============================================================================================
# QI_SMC (QI 176-428)
# ============================================================================================
def _run_smc(df, swing_lookback=20, duplicate_bar_window=5, events=None):
    _check(df)
    O, H, L, C, V = _ohlcv(df)
    n = len(C)
    lb = int(swing_lookback)
    atr = nt_atr(df, 14).tolist()
    sh_flag, sl_flag = _swing_flags(H, L, lb)
    Ol, Hl, Ll, Cl = O.tolist(), H.tolist(), L.tolist(), C.tolist()
    dup_win = int(duplicate_bar_window)
    log = events is not None

    nan = float("nan")
    conf = [nan] * n
    struct = [nan] * n
    trend = [nan] * n
    last_sh, last_sl = DBL_MIN, DBL_MAX
    prev_sh, prev_sl = DBL_MIN, DBL_MAX
    ob_bull_h, ob_bull_l, ob_bull_b = [], [], []
    ob_bear_h, ob_bear_l, ob_bear_b = [], [], []
    fvg_bull_t, fvg_bull_bt, fvg_bull_b = [], [], []
    fvg_bear_t, fvg_bear_bt, fvg_bear_b = [], [], []
    trend_dir = 0
    last_smc_dir = 0
    bars_since = INT_MAX
    last_bos_bar = 0
    gate = lb * 2 + 5

    for t in range(50, n):
        h = Hl[t]
        l = Ll[t]
        c = Cl[t]
        o = Ol[t]
        # (UpdateVolumeDelta: maintained by the C# for parity, never read by SMC)
        conf[t] = 0.0
        struct[t] = 0.0

        if t >= gate and t >= lb * 2:            # UpdateSwingPoints (QI 219-247)
            if sh_flag[t]:
                prev_sh = last_sh
                last_sh = Hl[t - lb]
            if sl_flag[t]:
                prev_sl = last_sl
                last_sl = Ll[t - lb]

        # ProcessSmcSignals (QI 254-428)
        if t >= 20:
            bars_since = _inc32(bars_since)
            if last_sh > DBL_MIN and prev_sh > DBL_MIN:
                if last_sh > prev_sh and last_sl > prev_sl:
                    trend_dir = 1
                elif last_sh < prev_sh and last_sl < prev_sl:
                    trend_dir = -1

            body = abs(c - o)
            rng = h - l
            atr_val = atr[t]

            # Order Block zones
            if t >= 2 and rng > 0 and body > 0.75 * rng and rng > 1.5 * atr_val:
                if c > o:
                    if Cl[t - 1] < Ol[t - 1]:
                        if len(ob_bull_h) >= 5:
                            del ob_bull_h[0], ob_bull_l[0], ob_bull_b[0]
                        ob_bull_h.append(Hl[t - 1])
                        ob_bull_l.append(Ll[t - 1])
                        ob_bull_b.append(t - 1)
                else:
                    if Cl[t - 1] > Ol[t - 1]:
                        if len(ob_bear_h) >= 5:
                            del ob_bear_h[0], ob_bear_l[0], ob_bear_b[0]
                        ob_bear_h.append(Hl[t - 1])
                        ob_bear_l.append(Ll[t - 1])
                        ob_bear_b.append(t - 1)
            # FVG zones
            if t >= 3:
                if l > Hl[t - 2]:
                    if len(fvg_bull_t) >= 5:
                        del fvg_bull_t[0], fvg_bull_bt[0], fvg_bull_b[0]
                    fvg_bull_t.append(l)
                    fvg_bull_bt.append(Hl[t - 2])
                    fvg_bull_b.append(t)
                if h < Ll[t - 2]:
                    if len(fvg_bear_t) >= 5:
                        del fvg_bear_t[0], fvg_bear_bt[0], fvg_bear_b[0]
                    fvg_bear_t.append(Ll[t - 2])
                    fvg_bear_bt.append(h)
                    fvg_bear_b.append(t)
            # expiry
            for i in range(len(ob_bull_b) - 1, -1, -1):
                if t - ob_bull_b[i] > 100:
                    del ob_bull_h[i], ob_bull_l[i], ob_bull_b[i]
            for i in range(len(ob_bear_b) - 1, -1, -1):
                if t - ob_bear_b[i] > 100:
                    del ob_bear_h[i], ob_bear_l[i], ob_bear_b[i]
            for i in range(len(fvg_bull_b) - 1, -1, -1):
                if t - fvg_bull_b[i] > 50:
                    del fvg_bull_t[i], fvg_bull_bt[i], fvg_bull_b[i]
            for i in range(len(fvg_bear_b) - 1, -1, -1):
                if t - fvg_bear_b[i] > 50:
                    del fvg_bear_t[i], fvg_bear_bt[i], fvg_bear_b[i]

            patterns = []
            best = 0.0
            smc_dir = 0
            # 1. OB Retest 0.72
            for i in range(len(ob_bull_b) - 1, -1, -1):
                if l <= ob_bull_h[i] and l >= ob_bull_l[i]:
                    smc_dir = 1
                    best = max(best, 0.72)
                    patterns.append(("OB Retest", 0.72))
                    del ob_bull_h[i], ob_bull_l[i], ob_bull_b[i]
                    break
            for i in range(len(ob_bear_b) - 1, -1, -1):
                if h >= ob_bear_l[i] and h <= ob_bear_h[i]:
                    if smc_dir == 0:
                        smc_dir = -1
                    best = max(best, 0.72)
                    patterns.append(("OB Retest", 0.72))
                    del ob_bear_h[i], ob_bear_l[i], ob_bear_b[i]
                    break
            # 2. FVG Entry 0.68
            for i in range(len(fvg_bull_b) - 1, -1, -1):
                if l <= fvg_bull_t[i] and c >= fvg_bull_bt[i]:
                    if smc_dir == 0:
                        smc_dir = 1
                    best = max(best, 0.68)
                    patterns.append(("FVG", 0.68))
                    del fvg_bull_t[i], fvg_bull_bt[i], fvg_bull_b[i]
                    break
            for i in range(len(fvg_bear_b) - 1, -1, -1):
                if h >= fvg_bear_bt[i] and c <= fvg_bear_t[i]:
                    if smc_dir == 0:
                        smc_dir = -1
                    best = max(best, 0.68)
                    patterns.append(("FVG", 0.68))
                    del fvg_bear_t[i], fvg_bear_bt[i], fvg_bear_b[i]
                    break
            # 3. BOS 0.60 (shared 5-bar cooldown lastBosBar)
            if prev_sh > DBL_MIN and c > prev_sh and t - last_bos_bar > 5:
                if smc_dir == 0:
                    smc_dir = 1
                best = max(best, 0.60)
                patterns.append(("BOS", 0.60))
                last_bos_bar = t
            if prev_sl < DBL_MAX and c < prev_sl and t - last_bos_bar > 5:
                if smc_dir == 0:
                    smc_dir = -1
                best = max(best, 0.60)
                patterns.append(("BOS", 0.60))
                last_bos_bar = t
            # 4. CHoCH 0.75
            if trend_dir == 1 and last_sl < DBL_MAX and c < last_sl:
                if smc_dir == 0:
                    smc_dir = -1
                best = max(best, 0.75)
                patterns.append(("CHoCH", 0.75))
            if trend_dir == -1 and last_sh > DBL_MIN and c > last_sh:
                if smc_dir == 0:
                    smc_dir = 1
                best = max(best, 0.75)
                patterns.append(("CHoCH", 0.75))
            # 5. Displacement 0.58
            if rng > 0 and body > 0.75 * rng and rng > 1.5 * atr_val:
                disp_dir = 1 if c > o else -1
                if smc_dir == 0:
                    smc_dir = disp_dir
                best = max(best, 0.58)
                patterns.append(("Displacement", 0.58))

            if patterns and smc_dir != 0 and not (smc_dir == last_smc_dir and bars_since < dup_win):
                best = min(best, 1.0)
                conf[t] = best
                struct[t] = float(smc_dir)
                if log:
                    events.append((t, "Signal", smc_dir, best, patterns, float("nan")))
                last_smc_dir = smc_dir
                bars_since = 0

        trend[t] = float(trend_dir)          # trendDirSeries[0] = smcTrendDir (QI 193)

    return conf, struct, trend


def smc(df, **params):
    """QI_SMC plots: confidence, structure (+1/-1/0) and the non-plot TrendDir series; NaN on bars < 50."""
    conf, struct, trend = _run_smc(df, **params)
    return pd.DataFrame({"confidence": conf, "structure": struct, "trend_dir": trend},
                        index=df.index, dtype=float)


def smc_events(df, **params):
    events = []
    _run_smc(df, events=events, **params)
    return _events_frame(events, df)


def smc_structure(df, **params):
    s = smc(df, **params)["structure"]
    s.name = "smc_structure"
    return s


# ============================================================================================
# QI_KeyLevels (QI_27_KeyLevels.cs: OnBarUpdate, UpdateKeyLevels, UpdatePrevDayHighLow,
# UpdateMonthlyHighLow, UpdateOrb, UpdateAsianSession, IsIn*Window, WriteLevelSeries)
# ============================================================================================
_T_0200 = 2 * 3600 * _NS
_T_1700 = 17 * 3600 * _NS
KEY_LEVEL_COLUMNS = ("PrevDayHigh", "PrevDayLow", "MonthlyHigh", "MonthlyLow",
                     "OrbHigh", "OrbLow", "AsianHigh", "AsianLow")
__all__ += ["key_levels"]


def key_levels(df, show_prev_day_levels=True, show_monthly_levels=True, show_orb_levels=True,
               show_asian_session_levels=True):
    """QI_27_KeyLevels exposed series (PrevDayHigh/Low, MonthlyHigh/Low, OrbHigh/Low, AsianHigh/Low):
    the tracked level after each bar's update, NaN while the C# still holds its double.MinValue /
    double.MaxValue sentinel. Bars < 50 are NaN (`if (CurrentBar < 50)` returns before any update).
    cstTime == BarTime (see the module notes); windows are on the bar CLOSE time t = TimeOfDay:

    * Prev day (Sat/Sun skipped): a new CST date rolls the finished RTH [08:30, 16:00) high/low into
      PrevDay* when that date had an RTH bar, then restarts today's tracking. The roll happens at
      the first weekday bar of the new calendar date, so Fri RTH becomes PrevDay* on Monday and
      the 17:00-24:00 evening bars still show the day-before's RTH levels.
    * Month: reset when the Month number changes; every bar (weekends included) raises the high
      and lowers the low, so the current bar is always inside the range.
    * ORB (Sat/Sun skipped): reset at each new CST date (NaN until the first window bar); bars in
      [08:30, 09:00) while not complete set it; complete at the first bar with t >= 09:00 once
      known. The current day's (live) values are exposed; prevOrbHigh/Low are not.
    * Asian (Sat/Sun skipped, so Sunday-evening bars never count): trading date = date + 1 for
      t >= 17:00, else date; a new trading date resets; bars with t >= 17:00 or t < 02:00 while not
      complete set it; complete at the first bar with 02:00 <= t < 17:00 once known.
    The Show* toggles skip the corresponding update (the series then stays NaN)."""
    _check(df)
    _, H, L, _, _ = _ohlcv(df)
    n = len(H)
    day, wday, month, tod = _time_parts(df)
    Hl, Ll = H.tolist(), L.tolist()

    nan = float("nan")
    out = {k: [nan] * n for k in KEY_LEVEL_COLUMNS}

    # State.DataLoaded initialisation (DateTime.MinValue -> None, klCurrentMonth = 0)
    prev_day_high, prev_day_low = DBL_MIN, DBL_MAX
    today_high, today_low = DBL_MIN, DBL_MAX
    today_date = None
    today_started = False
    mo_high, mo_low = DBL_MIN, DBL_MAX
    cur_month = 0
    orb_high, orb_low = DBL_MIN, DBL_MAX
    orb_complete = False
    orb_date = None
    asian_high, asian_low = DBL_MIN, DBL_MAX
    asian_complete = False
    asian_date = None

    for t in range(50, n):
        h = Hl[t]
        l = Ll[t]
        weekend = wday[t] >= 5                      # DayOfWeek.Saturday / Sunday

        # ---- UpdatePrevDayHighLow ----
        if show_prev_day_levels and not weekend:
            if day[t] != today_date:
                if today_started and today_high > DBL_MIN and today_low < DBL_MAX:
                    prev_day_high = today_high
                    prev_day_low = today_low
                today_high, today_low = DBL_MIN, DBL_MAX
                today_date = day[t]
                today_started = False
            if _T_0830 <= tod[t] < _T_1600:          # IsInRthWindow
                today_started = True
                if h > today_high:
                    today_high = h
                if l < today_low:
                    today_low = l

        # ---- UpdateMonthlyHighLow ----
        if show_monthly_levels:
            if month[t] != cur_month:
                mo_high, mo_low = DBL_MIN, DBL_MAX
                cur_month = month[t]
            if h > mo_high:
                mo_high = h
            if l < mo_low:
                mo_low = l

        # ---- UpdateOrb ----
        if show_orb_levels and not weekend:
            if day[t] != orb_date:
                # (archives a completed ORB into prevOrbHigh/Low: tracked, never exposed)
                orb_high, orb_low = DBL_MIN, DBL_MAX
                orb_complete = False
                orb_date = day[t]
            if _T_0830 <= tod[t] < _T_0900 and not orb_complete:     # IsInOrbWindow
                if h > orb_high:
                    orb_high = h
                if l < orb_low:
                    orb_low = l
            if not orb_complete and day[t] == orb_date:
                if tod[t] >= _T_0900 and orb_high > DBL_MIN:
                    orb_complete = True

        # ---- UpdateAsianSession ----
        if show_asian_session_levels and not weekend:
            trading_date = day[t] + 1 if tod[t] >= _T_1700 else day[t]
            if trading_date != asian_date:
                asian_high, asian_low = DBL_MIN, DBL_MAX
                asian_complete = False
                asian_date = trading_date
            if (tod[t] >= _T_1700 or tod[t] < _T_0200) and not asian_complete:   # IsInAsianWindow
                if h > asian_high:
                    asian_high = h
                if l < asian_low:
                    asian_low = l
            if not asian_complete and asian_date == trading_date:
                if _T_0200 <= tod[t] < _T_1700 and asian_high > DBL_MIN:
                    asian_complete = True

        # ---- WriteLevelSeries: sentinels -> NaN ----
        out["PrevDayHigh"][t] = prev_day_high if prev_day_high > DBL_MIN else nan
        out["PrevDayLow"][t] = prev_day_low if prev_day_low < DBL_MAX else nan
        out["MonthlyHigh"][t] = mo_high if mo_high > DBL_MIN else nan
        out["MonthlyLow"][t] = mo_low if mo_low < DBL_MAX else nan
        out["OrbHigh"][t] = orb_high if orb_high > DBL_MIN else nan
        out["OrbLow"][t] = orb_low if orb_low < DBL_MAX else nan
        out["AsianHigh"][t] = asian_high if asian_high > DBL_MIN else nan
        out["AsianLow"][t] = asian_low if asian_low < DBL_MAX else nan

    return pd.DataFrame({k: out[k] for k in KEY_LEVEL_COLUMNS}, index=df.index, dtype=float)
