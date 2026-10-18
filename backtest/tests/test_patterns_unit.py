"""test_patterns_unit.py - hand-built bar sequences for backtest/qibt/patterns.py.

Educational research only. Not financial advice. See DISCLAIMER.md.

Every expected value below is derived by hand from the C# rules in indicators/QI_12_HedgingPressure.cs,
QI_22_LiquiditySweep.cs, QI_24_OrderFlowPlus.cs and QI_25_SMC.cs (line references in the test docstrings), not
from the port's output.

Base sequence `tri(n)` (a contracting triangle) is chosen so that no rule fires on its own:
High = 110 - 0.01 t (strictly falling), Low = 90 + 0.01 t (strictly rising)  -> no swing high/low,
no Donchian / Wyckoff-range break, no gap, ranges ~16-18 so ATR14 ~17 (no impulse/displacement);
Close alternates 100.5 / 99.5 with Open = previous Close -> volDelta alternates +-1000 (no stacked
delta, no exhaustion); Volume 1000 (no spike). Bar times are on a Saturday unless a test needs RTH, so
the prev-day / ORB trackers skip them (QI 305-307, 365-367).

Run (repo root): python -I -m pytest backtest/tests -q -p no:cacheprovider -k patterns
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "backtest") not in sys.path:
    sys.path.insert(0, str(REPO / "backtest"))
from qibt import patterns as P  # noqa: E402

SAT = "2024-01-06 00:00:00"      # a Saturday


# ============================================================================================
# builders
# ============================================================================================
def tri(n):
    rows = []
    for t in range(n):
        even = t % 2 == 0
        rows.append([99.5 if even else 100.5, 110 - 0.01 * t, 90 + 0.01 * t, 100.5 if even else 99.5, 1000.0])
    return rows


def frame(rows, times=None, start=SAT):
    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"], dtype=float)
    if times is None:
        times = pd.date_range(start, periods=len(rows), freq="1min")
    df.insert(0, "BarTime", pd.to_datetime(times))
    return df


def put(rows, t, o, h, l, c, v=1000.0):
    rows[t] = [float(o), float(h), float(l), float(c), float(v)]


def spike_high(rows, t, h):
    rows[t][1] = float(h)


def spike_low(rows, t, l):
    rows[t][2] = float(l)


def events_at(ev, bar, kind=None):
    sel = ev[ev["bar"] == bar]
    if kind is not None:
        sel = sel[sel["kind"] == kind]
    return [(int(d), round(float(c), 10), [(n, round(float(x), 10)) for n, x in p])
            for d, c, p in zip(sel["direction"], sel["confidence"], sel["patterns"])]


def bars_with(ev, kind=None):
    sel = ev if kind is None else ev[ev["kind"] == kind]
    return sorted(set(int(b) for b in sel["bar"]))


# ============================================================================================
# API / warm-up
# ============================================================================================
def test_patterns_api_shapes_nan_warmup_and_aliases():
    df = frame(tri(120))
    hp = P.hp_score(df)
    ls = P.liquidity_sweep(df)
    of = P.order_flow_plus(df)
    sm = P.smc(df)
    assert isinstance(hp, pd.Series) and hp.index.equals(df.index)
    assert list(ls.columns) == ["confidence", "structure"]
    assert list(of.columns) == ["confidence", "structure"]
    assert list(sm.columns) == ["confidence", "structure", "trend_dir"]
    for out in (hp.to_frame(), ls, of, sm):
        assert out.index.equals(df.index)
        assert out.iloc[:50].isna().all().all()              # CurrentBar < 50 return (QI 137/248/158/178)
        assert out.iloc[50:].notna().all().all()
    # quiet base: plots are 0 on every computed bar (Values = 0 each bar, events only on rules)
    for out in (ls, of):
        assert (out.iloc[50:] == 0).all().all()
    assert (sm.iloc[50:][["confidence", "structure"]] == 0).all().all()
    assert sP_equal(P.sweep_structure(df), ls["structure"])
    assert sP_equal(P.ofp_structure(df), of["structure"])
    assert sP_equal(P.smc_structure(df), sm["structure"])
    with pytest.raises(KeyError):
        P.hp_score(df.drop(columns=["Volume"]))


def sP_equal(a, b):
    return bool(((a == b) | (a.isna() & b.isna())).all())


# ============================================================================================
# QI_12_HedgingPressure (QI 152-196)
# ============================================================================================
def _flat_hp(n=61):
    return [[100.0, 101.0, 99.0, 100.0, 100.0] for _ in range(n)]      # TR = 2 -> ATR14 = 2 exactly


def test_patterns_hp_zero_when_atr_zero_and_on_quiet_bars():
    df = frame([[100.0, 100.0, 100.0, 100.0, 100.0]] * 60)               # H = L -> ATR14 = 0 -> return 0
    hp = P.hp_score(df)
    assert hp.iloc[:50].isna().all() and (hp.iloc[50:] == 0.0).all()
    df = frame(_flat_hp(60))                                             # C = SMA, flat slopes, volRatio 1, rangeRatio 1
    assert (P.hp_score(df).iloc[50:] == 0.0).all()


def test_patterns_hp_basis_and_term_clamped_at_minus_25():
    """Bar 60: C=110 vs SMA20=100.5, ATR=37/14 -> basis -89.9 -> -25; slope term -28.4 -> -25; vp=rc=0 -> -50."""
    rows = _flat_hp(61)
    put(rows, 60, 100.0, 110.5, 99.5, 110.0, 100.0)
    hp = P.hp_score(frame(rows))
    a = (13 * 2.0 + 11.0) / 14.0                                         # TR60 = 11
    basis = (110.0 - 100.5) / a * -25.0
    term = ((102.0 - 100.0) / a - (100.5 - 100.0) / a) * -50.0
    assert basis < -25 and term < -25                                    # both raw terms beyond the clamp
    assert hp.iloc[60] == -50.0


def test_patterns_hp_vp_term_clamped_at_plus_25():
    """volRatio = 300/110 > 1.2, |C-O|/ATR = 0.25 < 0.5, C > O -> vp = +27.3 -> +25."""
    rows = _flat_hp(61)
    put(rows, 60, 100.0, 101.0, 99.0, 100.5, 300.0)
    hp = P.hp_score(frame(rows)).iloc[60]
    a = 2.0
    s20 = (19 * 100.0 + 100.5) / 20
    s5 = (4 * 100.0 + 100.5) / 5
    basis = max(-25.0, min(25.0, (100.5 - s20) / a * -25.0))
    term = max(-25.0, min(25.0, ((s5 - 100.0) / a - (s20 - 100.0) / a) * -50.0))
    vp_raw = 1.0 * (300.0 / 110.0) * 10.0
    assert vp_raw > 25
    assert hp == pytest.approx(basis + term + 25.0, abs=1e-12)


def test_patterns_hp_rc_and_vp_both_plus_25_gives_50():
    """Doji with range 0.5 (rangeRatio 0.26 < 0.6) and volRatio 2.73 (> 1.3): vp +25, rc +25, basis = term = 0."""
    rows = _flat_hp(61)
    put(rows, 60, 100.0, 100.25, 99.75, 100.0, 300.0)
    assert P.hp_score(frame(rows)).iloc[60] == 50.0


def test_patterns_hp_vp_and_rc_clamped_at_minus_25():
    """C < O and C < SMA20: vp = -27.3 -> -25 and rc = -(1-0.26)*50 = -37 -> -25."""
    rows = _flat_hp(61)
    put(rows, 60, 100.0, 100.15, 99.65, 99.9, 300.0)
    hp = P.hp_score(frame(rows)).iloc[60]
    a = (13 * 2.0 + 0.5) / 14.0
    s20 = (19 * 100.0 + 99.9) / 20
    s5 = (4 * 100.0 + 99.9) / 5
    basis = max(-25.0, min(25.0, (99.9 - s20) / a * -25.0))
    term = max(-25.0, min(25.0, ((s5 - 100.0) / a - (s20 - 100.0) / a) * -50.0))
    assert hp == pytest.approx(basis + term - 25.0 - 25.0, abs=1e-12)


def _hp_reference(df):
    """Independent HP from the QI formula text: own ATR loop, pandas rolling means (NT partial average)."""
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close", "Volume"))
    n = len(c)
    atr = np.empty(n)
    for t in range(n):
        if t == 0:
            atr[t] = h[0] - l[0]
        else:
            tr = max(abs(l[t] - c[t - 1]), max(h[t] - l[t], abs(h[t] - c[t - 1])))
            m = min(t + 1, 14)
            atr[t] = ((m - 1) * atr[t - 1] + tr) / m
    sma = lambda x, k: pd.Series(x).rolling(k, min_periods=1).mean().to_numpy()  # noqa: E731
    s20, s5, rs, vs = sma(c, 20), sma(c, 5), sma(h - l, 20), sma(v, 20)
    clamp = lambda x, lo, hi: min(hi, max(lo, x))                                 # noqa: E731
    out = np.full(n, np.nan)
    for t in range(50, n):
        if atr[t] <= 0 or s20[t] <= 0:
            out[t] = 0.0
            continue
        b = clamp((c[t] - s20[t]) / atr[t] * -25, -25, 25)
        tm = clamp(((s5[t] - s5[t - 1]) - (s20[t] - s20[t - 1])) / atr[t] * -50, -25, 25)
        vr = v[t] / vs[t] if vs[t] > 0 else 1.0
        vp = 0.0
        if vr > 1.2 and abs(c[t] - o[t]) / atr[t] < 0.5:
            vp = (-1 if c[t] < o[t] else 1) * vr * 10
        rr = (h[t] - l[t]) / rs[t] if rs[t] > 0 else 1.0
        rc = 0.0
        if rr < 0.6 and vr > 1.3:
            rc = clamp((-1 if c[t] < s20[t] else 1) * (1 - rr) * 50, -25, 25)
        out[t] = clamp(b + tm + clamp(vp, -25, 25) + rc, -100, 100)
    return out


def test_patterns_hp_matches_independent_reference_on_random_bars_and_is_within_75():
    rng = np.random.default_rng(7)
    n = 3000
    c = 4000 + np.cumsum(rng.choice([-0.5, -0.25, 0, 0.25, 0.5], n))
    o = np.r_[c[0], c[:-1]] + rng.choice([-0.25, 0, 0.25], n)
    h = np.maximum(o, c) + rng.choice([0, 0.25, 0.5, 1.0, 2.0], n)
    l = np.minimum(o, c) - rng.choice([0, 0.25, 0.5, 1.0, 2.0], n)
    v = rng.integers(10, 3000, n).astype(float)
    df = frame(np.c_[o, h, l, c, v].tolist())
    hp = P.hp_score(df).to_numpy()
    ref = _hp_reference(df)
    assert np.allclose(hp[50:], ref[50:], atol=1e-9, rtol=0)
    assert np.nanmax(np.abs(hp)) <= 75.0 + 1e-12          # basis and rc always oppose -> +-100 never binds


# ============================================================================================
# QI_22_LiquiditySweep (QI 426-705)
# ============================================================================================
def _swing_high_115():
    rows = tri(220)
    spike_high(rows, 100, 115.0)   # swing high confirmed at bar 120 (pivot +- 20 bars), lastSwingHigh = 115
    return rows


def test_patterns_sweep_swing_high_wick_volume_bearish():
    """Bar 150: H 116 > SH 115 > C 109, upper wick 7 = 70x body 0.1 (>= 2x), V 3000 > 1.5*SMA20 (1100).
    Fires 'Liq Sweep' 0.70 AND 'SFP' 0.50 (same price condition, QI 570/610) -> End conf min(1.2,1) = 1.0,
    structure -1. C >= Donchian high (108.7) and C > O avoid Turtle Soup / Upthrust. The bar also arms a
    VolDiv (absorbed) pending sweep (Start 0.35) which confirms on bar 151 (C < 115) -> End 0.55."""
    rows = _swing_high_115()
    put(rows, 150, 108.9, 116.0, 108.5, 109.0, 3000.0)
    df = frame(rows)
    ev = P.liquidity_sweep_events(df)
    assert events_at(ev, 150, "End") == [(-1, 1.0, [("Liq Sweep", 0.7), ("SFP", 0.5)])]
    assert events_at(ev, 150, "Start") == [(-1, 0.35, [("VolDiv (absorbed)", 0.35)])]
    assert events_at(ev, 151, "End") == [(-1, 0.55, [("VolDiv (absorbed)", 0.55)])]
    out = P.liquidity_sweep(df)
    assert tuple(out.iloc[150]) == (1.0, -1.0)
    assert tuple(out.iloc[151]) == (0.55, -1.0)


def test_patterns_sweep_swing_low_wick_volume_bullish():
    """Mirror: swing low 85 (pivot 100), bar 150 L 84 < 85 < C 91.0 <= Donchian low 91.3, lower wick 70x."""
    rows = tri(220)
    spike_low(rows, 100, 85.0)
    put(rows, 150, 91.1, 91.5, 84.0, 91.0, 3000.0)
    ev = P.liquidity_sweep_events(frame(rows))
    assert events_at(ev, 150, "End") == [(1, 1.0, [("Liq Sweep", 0.7), ("SFP", 0.5)])]
    assert events_at(ev, 151, "End") == [(1, 0.55, [("VolDiv (absorbed)", 0.55)])]


def test_patterns_sweep_sfp_alone():
    """Same bar as above but V = 1000 (no spike): only SFP 0.50 (QI 610-611); no VolDiv (not weak, not absorbed)."""
    rows = _swing_high_115()
    put(rows, 150, 108.9, 116.0, 108.5, 109.0, 1000.0)
    ev = P.liquidity_sweep_events(frame(rows))
    assert events_at(ev, 150) == [(-1, 0.5, [("SFP", 0.5)])]
    assert events_at(ev, 151) == []


def test_patterns_sweep_sfp_two_bar():
    """Bar 149 closes above SH 115 (H 117, C 116), bar 150 closes back below with H 114 -> SFP(2bar) 0.60 (QI 614-616)."""
    rows = _swing_high_115()
    put(rows, 149, 108.6, 117.0, 108.4, 116.0)
    put(rows, 150, 113.0, 114.0, 109.0, 110.0)
    ev = P.liquidity_sweep_events(frame(rows))
    assert events_at(ev, 149) == []
    assert events_at(ev, 150) == [(-1, 0.6, [("SFP(2bar)", 0.6)])]


def test_patterns_sweep_equal_high_trap_consumes_pool_entry():
    """Swing highs 115.00 (pivot 100) and 115.05 (pivot 150): |diff| 0.05 < 0.05*0.01*115.05 -> pool level
    115.025 added at bar 170 (QI 492-498). Bar 200: H 115.03 > 115.025 > C 109, H below lastSH 115.05 (no SFP)
    -> 'EqHigh Trap' 0.60 and the entry is removed (QI 628-630); the identical bar 210 fires nothing."""
    rows = tri(230)
    spike_high(rows, 100, 115.0)
    spike_high(rows, 150, 115.05)
    put(rows, 200, 108.1, 115.03, 108.0, 109.0)
    put(rows, 210, 108.1, 115.03, 108.0, 109.0)
    ev = P.liquidity_sweep_events(frame(rows))
    assert events_at(ev, 200) == [(-1, 0.6, [("EqHigh Trap", 0.6)])]
    assert events_at(ev, 210) == []


def test_patterns_sweep_wyckoff_spring_outside_consolidation():
    """Bar 150: L 85 < 40-bar low 91.1 < C 100, C > O -> Spring 0.60 (not in consolidation, QI 659-661).
    O 91.2 <= 20-bar low 91.3 so Turtle Soup's O > Donchian-low condition fails."""
    rows = tri(170)
    put(rows, 150, 91.2, 101.0, 85.0, 100.0)
    ev = P.liquidity_sweep_events(frame(rows))
    assert events_at(ev, 150) == [(1, 0.6, [("Spring", 0.6)])]


def _ratio(df):
    atr = P.nt_atr(df, 14)
    return atr / P.nt_sma(atr, 50)


def test_patterns_sweep_wyckoff_spring_inside_consolidation_is_075():
    """Triangle (range ~18) then a contracting 0.5-range zone: ATR14/SMA50(ATR14) < 0.6 -> consolidation
    (QI 527-535). Spring at tiny-bar 50 (bar 170) -> baseConf 0.75 (QI 659)."""
    rows = tri(120)
    for k in range(80):
        rows.append([100.0, 100.25 - 0.001 * k, 99.75 + 0.001 * k, 100.0, 1000.0])
    # rangeLow (bars 130..169) = 99.76, Donchian low (150..169) = 99.78
    put(rows, 170, 99.77, 100.1, 99.5, 100.0)
    df = frame(rows)
    r = _ratio(df)
    assert (r[140:171] < 0.6).all()                      # precondition: in consolidation and still extending
    ev = P.liquidity_sweep_events(df)
    assert events_at(ev, 170) == [(1, 0.75, [("Spring", 0.75)])]


def test_patterns_sweep_turtle_soup_and_duplicate_window():
    """Turtle Soup 0.55 (QI 670-671): H above the 20-bar high, O and C below it, C > O (no Upthrust).
    Bars 150 / 153 / 155 with rising highs 112 / 113 / 114: bar 153 is the same direction 3 bars later
    (barsSince 3 < 5) -> suppressed (QI 470); bar 155 (barsSince 5, not < 5) fires. Window 6 suppresses 155;
    window 2 lets all three through (155 is 2 bars after 153)."""
    rows = tri(170)
    for t, h in ((150, 112.0), (153, 113.0), (155, 114.0)):
        put(rows, t, 100.0, h, 99.0, 100.5)
    df = frame(rows)
    ev = P.liquidity_sweep_events(df)
    assert events_at(ev, 150) == [(-1, 0.55, [("Turtle Soup", 0.55)])]
    assert events_at(ev, 153) == []
    assert events_at(ev, 155) == [(-1, 0.55, [("Turtle Soup", 0.55)])]
    assert bars_with(P.liquidity_sweep_events(df, duplicate_bar_window=6), "End") == [150]
    assert bars_with(P.liquidity_sweep_events(df, duplicate_bar_window=2), "End") == [150, 153, 155]


def test_patterns_sweep_detection_gate_lookback_x2_plus_5():
    """With SwingLookback 25 the detection gate is CurrentBar >= 55 (QI 428), above the global bar-50 gate:
    a Turtle Soup bar at 54 is ignored, the same bar at 55 fires."""
    for t, expect in ((54, []), (55, [(-1, 0.55, [("Turtle Soup", 0.55)])])):
        rows = tri(80)
        put(rows, t, 100.0, 112.0, 99.0, 100.5)
        ev = P.liquidity_sweep_events(frame(rows), swing_lookback=25)
        assert events_at(ev, t) == expect


def test_patterns_ofp_and_smc_swings_only_from_lookback_x2_plus_5():
    """OF+/SMC update swing points only from CurrentBar >= SwingLookback*2+5 (QI OF+ 168, SMC 188). With
    SwingLookback 25 a pivot at bar 27 (confirmed at 52 < 55) is never recorded:
    OF+: bar 100 above it with negative cumDelta10 gives no DeltaDiv.
    SMC: pivot 60 (112, confirmed 85) becomes lastSwingHigh with prevSwingHigh still MinValue, so a close of
    116 at bar 120 (above the unrecorded 115) is not a BOS."""
    rows = tri(140)
    spike_high(rows, 27, 115.0)
    put(rows, 100, 100.0, 116.0, 98.5, 99.0)
    assert events_at(P.order_flow_plus_events(frame(rows), swing_lookback=25), 100) == []
    rows = tri(140)
    spike_high(rows, 27, 115.0)
    spike_high(rows, 60, 112.0)
    put(rows, 120, 100.5, 117.0, 100.0, 116.0)
    assert events_at(P.smc_events(frame(rows), swing_lookback=25), 120) == []
    rows = tri(140)                                     # control: pivots 60 and 90 both recorded -> BOS fires
    spike_high(rows, 60, 115.0)
    spike_high(rows, 90, 112.0)
    put(rows, 130, 100.5, 117.0, 100.0, 116.0)
    assert events_at(P.smc_events(frame(rows), swing_lookback=25), 130) == [(1, 0.6, [("BOS", 0.6)])]


def test_patterns_sweep_turtle_soup_bullish():
    rows = tri(170)
    put(rows, 150, 100.5, 101.0, 88.0, 100.0)            # L < 20-bar low 91.3; O, C above it; C < O (no Spring)
    ev = P.liquidity_sweep_events(frame(rows))
    assert events_at(ev, 150) == [(1, 0.55, [("Turtle Soup", 0.55)])]


def test_patterns_sweep_consolidation_breakout_trap():
    """Flat range-2 bars then flat range-0.5 bars: consolidation starts once ATR ratio < 0.6 (zone 99.75..100.25);
    later the ratio recovers to [0.6, 0.9) so the zone stops extending but has not ended (QI 529-537).
    Trap bar: H 101 > zone high 100.25 >= C 100.25 with V 5000 > 2*SMA20 -> 'Consol Trap' 0.65 bearish
    (QI 644-645). C == 100.25 equals lastSwingHigh / Donchian / 40-bar high / pool level, so SFP, Turtle Soup,
    Upthrust and EqHigh need C < level and do not fire."""
    rows = [[100.0, 101.0, 99.0, 100.0, 1000.0] for _ in range(120)]
    rows += [[100.0, 100.25, 99.75, 100.0, 1000.0] for _ in range(80)]
    k = 175
    put(rows, k, 100.0, 101.0, 99.75, 100.25, 5000.0)
    df = frame(rows)
    r = _ratio(df)
    start = next(t for t in range(50, k) if r[t] < 0.6)   # consolidation start (QI 531-532)
    assert all(not (r[t] >= 0.9 and t - start > 50) for t in range(start, k + 1))   # never ended
    assert 0.6 <= r[k] < 0.9                                # zone not extended by the trap bar itself
    assert all(rows[t][1] <= 100.25 for t in range(start, k))
    ev = P.liquidity_sweep_events(df)
    assert events_at(ev, k, "End") == [(-1, 0.65, [("Consol Trap", 0.65)])]


@pytest.mark.parametrize("k,fires", [(183, True), (184, False), (200, False)])
def test_patterns_sweep_consolidation_ends_only_at_ratio_09_after_50_bars(k, fires):
    """Same construction, trap bar later. The zone ends only when ratio >= 0.6*1.5 AND CurrentBar - start > 50
    (QI 536-537). Bar 183: 52 bars after the start but ratio 0.89 < 0.9 -> still in consolidation -> trap fires.
    Bar 184: its own ratio 0.90 >= 0.9 with 53 bars -> the zone ends on that bar (update runs before the check)
    -> no trap. Bar 200: ended earlier -> no trap (only the VolDiv Start label remains)."""
    rows = [[100.0, 101.0, 99.0, 100.0, 1000.0] for _ in range(120)]
    rows += [[100.0, 100.25, 99.75, 100.0, 1000.0] for _ in range(120)]
    put(rows, k, 100.0, 101.0, 99.75, 100.25, 5000.0)
    df = frame(rows)
    r = _ratio(df)
    start = next(t for t in range(50, k) if r[t] < 0.6)
    assert k - start > 50
    assert (max(r[start:k + 1]) < 0.9) == fires
    ev = P.liquidity_sweep_events(df)
    expected = [(-1, 0.65, [("Consol Trap", 0.65)])] if fires else []
    assert events_at(ev, k, "End") == expected
    assert events_at(ev, k, "Start") == [(-1, 0.35, [("VolDiv (absorbed)", 0.35)])]


def test_patterns_sweep_voldiv_weak_pending_confirmation_suppresses_same_bar_check():
    """Bar 150: new high above SH 115 that closes above it with V 500 < 0.8*SMA20 -> Start 'VolDiv (weak)' 0.35,
    pending (QI 690-695), no End. Bar 151 closes below 115 -> End 0.55 drawn BEFORE the checks (QI 552-558);
    the SFP(2bar) that also fires on bar 151 is the same direction with barsSince 0 -> suppressed."""
    rows = _swing_high_115()
    put(rows, 150, 115.5, 117.0, 115.2, 116.0, 500.0)
    df = frame(rows)
    ev = P.liquidity_sweep_events(df)
    assert events_at(ev, 150, "End") == []
    assert events_at(ev, 150, "Start") == [(-1, 0.35, [("VolDiv (weak)", 0.35)])]
    assert events_at(ev, 151) == [(-1, 0.55, [("VolDiv (weak)", 0.55)])]
    assert tuple(P.liquidity_sweep(df).iloc[150]) == (0.0, 0.0)      # Start labels write no plot value


def _two_day_times(n_mon, n_tue):
    mon = pd.date_range("2024-01-08 08:30:00", periods=n_mon, freq="1min")
    tue = pd.date_range("2024-01-09 08:30:00", periods=n_tue, freq="1min")
    return mon.append(tue)


def test_patterns_sweep_prev_day_high():
    """Monday RTH bars 50..119 (bars < 50 are never processed) -> PDH 109.5. Tuesday 09:30 bar 180:
    H 110 > PDH > C 109 with wick 10x body and V spike -> 'Sweep PDH' 0.85 (QI 580-582)."""
    rows = tri(200)
    put(rows, 180, 108.9, 110.0, 108.5, 109.0, 3000.0)
    ev = P.liquidity_sweep_events(frame(rows, times=_two_day_times(120, 80)))
    assert events_at(ev, 180) == [(-1, 0.85, [("Sweep PDH", 0.85)])]
    ev_off = P.liquidity_sweep_events(frame(rows, times=_two_day_times(120, 80)), use_prev_day_levels=False)
    assert events_at(ev_off, 180) == []


def test_patterns_sweep_orb_high():
    """Tuesday ORB 08:30-08:59 = bars 120..149 -> ORB high 108.8, complete from 09:00 (QI 389-403).
    Bar 180: H 109.2 (< PDH 109.5) > ORB-H > C 108.5 -> 'Sweep ORB-H' 0.85."""
    rows = tri(200)
    put(rows, 180, 108.45, 109.2, 108.4, 108.5, 3000.0)
    ev = P.liquidity_sweep_events(frame(rows, times=_two_day_times(120, 80)))
    assert events_at(ev, 180) == [(-1, 0.85, [("Sweep ORB-H", 0.85)])]


def _random_session_bars(n=6000, seed=3):
    rng = np.random.default_rng(seed)
    c = 4000 + np.cumsum(rng.choice([-1.0, -0.5, -0.25, 0, 0.25, 0.5, 1.0], n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.choice([0, 0.25, 0.5, 1.5, 4.0], n)
    l = np.minimum(o, c) - rng.choice([0, 0.25, 0.5, 1.5, 4.0], n)
    v = rng.choice([50, 200, 800, 1500, 6000], n).astype(float)
    times = pd.date_range("2024-01-02 07:00:00", periods=n, freq="1min")   # crosses RTH, ORB, nights, a weekend
    return frame(np.c_[o, h, l, c, v].tolist(), times=times)


def test_patterns_quirks_unreachable_rules_never_fire():
    """'Sweep MoHigh/MoLow' (month high updated with the bar before the check) and OF+ 'DeltaRev'
    (volDelta[0] < 0 contradicts Close[0] > Close[1]) can never fire; every other rule does fire here."""
    df = _random_session_bars()
    names = {n for p in P.liquidity_sweep_events(df)["patterns"] for n, _ in p}
    assert not names & {"Sweep MoHigh", "Sweep MoLow"}
    assert {"Liq Sweep", "SFP", "Turtle Soup", "Spring", "Upthrust"} <= names
    of_names = {n for p in P.order_flow_plus_events(df)["patterns"] for n, _ in p}
    assert "DeltaRev" not in of_names
    assert {"DeltaDiv", "Absorption", "Exhaustion", "StackedDelta"} <= of_names


# ============================================================================================
# QI_24_OrderFlowPlus (QI 243-347)
# ============================================================================================
def test_patterns_ofp_delta_divergence():
    """SH 115 confirmed at bar 120 with cumDelta10 snapshot 0 (alternating +-1000, QI 213). Bar 150: H 116 > SH,
    down close (volDelta -1000) -> cumDelta10 = -2000 < 0 -> DeltaDiv 0.78 bearish (QI 257-258)."""
    rows = _swing_high_115()
    put(rows, 150, 100.0, 116.0, 98.5, 99.0)
    out = P.order_flow_plus(frame(rows))
    ev = P.order_flow_plus_events(frame(rows))
    assert events_at(ev, 150) == [(-1, 0.78, [("DeltaDiv", 0.78)])]
    assert tuple(out.iloc[150]) == (0.78, -1.0)


def test_patterns_ofp_absorption_and_duplicate_window():
    """Absorption 0.65 (QI 263-268): V 3000 > 1.5*SMA20, range 10 > 0.5*ATR14 (~16.5), body 1 < 0.3*range,
    C > O -> +1. Same bar shape at 150, 153, 155: 153 is suppressed (barsSince 3 < 5), 155 fires (5 >= 5)."""
    rows = tri(170)
    for t in (150, 153, 155):
        put(rows, t, 100.0, 105.0, 95.0, 101.0, 3000.0)
    df = frame(rows)
    ev = P.order_flow_plus_events(df)
    assert events_at(ev, 150) == [(1, 0.65, [("Absorption", 0.65)])]
    assert events_at(ev, 153) == []
    assert events_at(ev, 155) == [(1, 0.65, [("Absorption", 0.65)])]
    assert bars_with(P.order_flow_plus_events(df, duplicate_bar_window=1)) == [150, 153, 155]


def test_patterns_ofp_stacked_delta():
    """Three up closes in a row (bars 148-150) -> volDelta[0..2] > 0 -> StackedDelta 0.55 bullish (QI 289-295)."""
    rows = tri(170)
    put(rows, 149, 100.5, 108.51, 91.49, 101.0)
    put(rows, 150, 101.0, 108.5, 91.5, 101.5)
    ev = P.order_flow_plus_events(frame(rows))
    assert events_at(ev, 149) == []
    assert events_at(ev, 150) == [(1, 0.55, [("StackedDelta", 0.55)])]


def test_patterns_ofp_exhaustion():
    """|volDelta| 1400 > 1200 > 1000 on bars 148-150 with bar 150 at a new high (H 116 >= SH 115) and
    cumDelta10 = +200 (not < snapshot 0, so no DeltaDiv) -> Exhaustion 0.60, direction -1 (QI 274-282)."""
    rows = _swing_high_115()
    rows[148][4] = 1400.0
    rows[149][4] = 1200.0
    put(rows, 150, 99.5, 116.0, 99.0, 100.5, 1000.0)
    ev = P.order_flow_plus_events(frame(rows))
    assert events_at(ev, 148) == [] and events_at(ev, 149) == []
    assert events_at(ev, 150) == [(-1, 0.6, [("Exhaustion", 0.6)])]


# ============================================================================================
# QI_25_SMC (QI 254-428)
# ============================================================================================
def test_patterns_smc_fvg_then_order_block_retest():
    """Bar 150 bullish impulse (range 32 > 1.5*ATR14 ~28, body 30.5 > 0.75*range) after the bearish bar 149
    -> bullish OB zone [91.49, 108.51] (QI 274-283); its L 109 > H[2] 108.52 -> bullish FVG, entered on the
    same bar (L <= top, C >= bottom) -> FVG 0.68 + Displacement 0.58 -> conf 0.68, +1.
    Bars 151-155 dojis at 139 (bar 151's own FVG is suppressed: same dir, barsSince 1).
    Bar 156 drops with L 100 inside the OB zone -> 'OB Retest' 0.72 first (sets +1), Displacement (-1) only
    raises nothing -> conf 0.72, +1 (barsSince 6)."""
    rows = tri(170)
    put(rows, 150, 109.5, 141.0, 109.0, 140.0)
    for t in range(151, 156):
        put(rows, t, 139.0, 140.0, 138.0, 139.0)
    put(rows, 156, 138.0, 139.0, 100.0, 101.0)
    df = frame(rows)
    ev = P.smc_events(df)
    assert events_at(ev, 150) == [(1, 0.68, [("FVG", 0.68), ("Displacement", 0.58)])]
    assert bars_with(ev[(ev["bar"] > 150) & (ev["bar"] < 156)]) == []
    assert events_at(ev, 156) == [(1, 0.72, [("OB Retest", 0.72), ("Displacement", 0.58)])]
    ev1 = P.smc_events(df, duplicate_bar_window=1)
    assert events_at(ev1, 151) == [(1, 0.68, [("FVG", 0.68)])]


def test_patterns_smc_fvg_alone():
    """Bar 151 L 109 > H[2] (bar 149) 108.51, small range (no displacement) -> FVG 0.68 bullish (QI 300-304, 352-357)."""
    rows = tri(170)
    put(rows, 150, 100.5, 113.0, 100.0, 112.0)
    put(rows, 151, 110.0, 112.0, 109.0, 111.0)
    ev = P.smc_events(frame(rows))
    assert events_at(ev, 150) == []
    assert events_at(ev, 151) == [(1, 0.68, [("FVG", 0.68)])]


def test_patterns_smc_bos_and_shared_cooldown():
    """Swing highs 115 (pivot 100) then 112 (pivot 150) -> prevSwingHigh 115 from bar 170. Bar 200 closes at
    116 > 115 -> BOS 0.60 bullish, lastBosBar = 200 (QI 372-377). Bar 203 closes above again but
    CurrentBar - lastBosBar = 3 <= 5 -> no BOS, so no signal even with a 1-bar duplicate window."""
    rows = tri(220)
    spike_high(rows, 100, 115.0)
    spike_high(rows, 150, 112.0)
    put(rows, 200, 100.5, 117.0, 100.0, 116.0)
    put(rows, 203, 100.5, 117.0, 100.0, 116.0)
    df = frame(rows)
    ev = P.smc_events(df)
    assert events_at(ev, 200) == [(1, 0.6, [("BOS", 0.6)])]
    assert events_at(P.smc_events(df, duplicate_bar_window=1), 203) == []


def test_patterns_smc_choch_and_trend_dir():
    """Swing lows 85 (pivot 90) and 87 (pivot 140), swing highs 115 (pivot 100) and 117 (pivot 150):
    at bar 170 HH + HL -> smcTrendDir = 1 (QI 260-263). Bar 200 closes at 86 < lastSwingLow 87 (but above
    prevSwingLow 85, no BOS) -> CHoCH 0.75 bearish (QI 386-390)."""
    rows = tri(220)
    spike_low(rows, 90, 85.0)
    spike_high(rows, 100, 115.0)
    spike_low(rows, 140, 87.0)
    spike_high(rows, 150, 117.0)
    put(rows, 200, 99.0, 100.0, 85.5, 86.0)
    df = frame(rows)
    out = P.smc(df)
    assert (out["trend_dir"].iloc[50:170] == 0).all() and (out["trend_dir"].iloc[170:] == 1).all()
    ev = P.smc_events(df)
    assert events_at(ev, 200) == [(-1, 0.75, [("CHoCH", 0.75)])]
    assert tuple(out[["confidence", "structure"]].iloc[200]) == (0.75, -1.0)


def test_patterns_smc_displacement_and_duplicate_window():
    """Bearish impulse bars (range 35 > 1.5*ATR14, body 33 > 0.75*range) at 150, 153, 155 -> Displacement 0.58,
    -1 (QI 398-403). Bar 150 follows a bearish bar (no OB). Bar 153 follows the bullish bar 152, so a bearish OB
    [91.52, 108.48] is recorded (its zone is below 153's high, no retest on 153); bar 154's high 108.46 lies in it
    -> OB Retest -1 on 154. With the default window, 153 (barsSince 3) and 154 (4) are suppressed and 155 (5)
    fires; with a 1-bar window all four bars emit."""
    rows = tri(170)
    for t in (150, 153, 155):
        put(rows, t, 125.0, 126.0, 91.0, 92.0)
    df = frame(rows)
    ev = P.smc_events(df)
    assert events_at(ev, 150) == [(-1, 0.58, [("Displacement", 0.58)])]
    assert events_at(ev, 153) == [] and events_at(ev, 154) == []
    assert events_at(ev, 155) == [(-1, 0.58, [("Displacement", 0.58)])]
    ev1 = P.smc_events(df, duplicate_bar_window=1)
    assert events_at(ev1, 153) == [(-1, 0.58, [("Displacement", 0.58)])]
    assert events_at(ev1, 154) == [(-1, 0.72, [("OB Retest", 0.72)])]
    assert bars_with(ev1[(ev1["bar"] >= 150) & (ev1["bar"] <= 155)]) == [150, 153, 154, 155]
