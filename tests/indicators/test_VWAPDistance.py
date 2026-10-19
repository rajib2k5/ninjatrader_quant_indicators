"""Unit tests for QI_<NN>_VWAPDistance - session VWAP on price and (Close - VWAP) / ATR(14) in the DataBox.

Spec (ledger M16 + ADD-6; README "Deliberate changes"; header of the .cs):
  typical = (High + Low + Close) / 3                      (NOT the close)
  VWAP    = sum(typical * Volume) / sum(Volume) from the first bar of the trading SESSION (Bars.IsFirstBarOfSession,
            exported as the SessionStart series) - the original reset at calendar midnight (Time[0].DayOfYear), which
            is a deliberate change. Falls back to Close[0] while the session's cumulative volume is 0.
  value   = (Close - VWAP) / ATR14 when ATR14 > 0 and VWAP > 0, else 0 ; ATR14 = NinjaTrader ATR (ledger B4).
  Intraday charts only: on a daily chart the plot is 0. The C# accumulates from bar 50 (module gate), so the first
  session it sees is partial and the export test starts at the first session start at or after bar 50.
  The reference keys the reset on the SessionStart column when present (qi_ref.SESSION_FLAG_COL), else on the calendar
  day of BarTime (the original's behaviour).
Reference: qi_ref.vwap, qi_ref.vwap_distance.

Hand frame used below: every bar has H = 106, L = 100 (TR = 6 on every bar, so ATR14 = 6 throughout) and closes at the
low (typical 102) or the high (typical 104):
  bar:      0        1        2        3 (new session)   4 (after midnight, same session)
  close:   100      106      100      106                100
  typical: 102      104      102      104                102
  volume:   10       30       60       20                 20
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

import qi_ref as R
from qi_helpers import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "VWAPDistance"
TIMES = ["2026-01-06 14:00", "2026-01-06 15:00", "2026-01-06 16:00", "2026-01-06 17:00", "2026-01-07 01:00"]
FLAGS = [1, 0, 0, 1, 0]          # session starts: bar 0 and bar 3 (the 17:00 evening session, which crosses midnight)


def _hand_frame(with_flags=True):
    df = bars([100, 106, 100, 106, 100], high=[106] * 5, low=[100] * 5, volume=[10, 30, 60, 20, 20])
    df["BarTime"] = pd.to_datetime(TIMES)
    if with_flags:
        df[R.SESSION_FLAG_COL] = FLAGS
    return df


# ---- 1. formula --------------------------------------------------------------------------
def test_session_vwap_hand_values_reset_on_the_session_flag():
    # bar 0: 102
    # bar 1: (102 * 10 + 104 * 30) / 40 = 4140 / 40 = 103.5
    # bar 2: (4140 + 102 * 60) / 100 = 10260 / 100 = 102.6
    # bar 3 (new session): 104
    # bar 4: (104 * 20 + 102 * 20) / 40 = 103.0       <- the session continues past midnight
    assert R.vwap(_hand_frame()).tolist() == pytest.approx([102.0, 103.5, 102.6, 104.0, 103.0], abs=1e-12)


def test_distance_in_atr_units_hand_values():
    # ATR14 = 6 on every bar (TR = 6 each).  (close - vwap) / 6:
    # bar 0: (100 - 102) / 6 = -1/3 ; bar 1: (106 - 103.5) / 6 = 0.41666666666666667 ; bar 2: (100 - 102.6) / 6 = -0.43333333333333335
    # bar 3: (106 - 104) / 6 = 1/3 ; bar 4: (100 - 103) / 6 = -0.5
    expected = [-1.0 / 3.0, 0.4166666666666667, -0.43333333333333335, 1.0 / 3.0, -0.5]
    assert R.vwap_distance(_hand_frame()).tolist() == pytest.approx(expected, abs=1e-12)


def test_without_a_session_flag_column_the_reset_is_at_calendar_midnight():
    df = _hand_frame(with_flags=False)
    # bars 0-3 are on 2026-01-06 (cumulative, no reset at bar 3): bar 3 = (10260 + 104 * 20) / 120 = 12340 / 120 = 102.8333...
    # bar 4 is on 2026-01-07: the day key changes -> 102 (its own typical price)
    assert R.vwap(df).tolist() == pytest.approx([102.0, 103.5, 102.6, 102.83333333333333, 102.0], abs=1e-12)


@pytest.mark.xfail(strict=True, reason="spec-vs-reference: C# falls back to Close[0], qi_ref.vwap to the typical price (ASSUMPTION)")
def test_zero_volume_session_start_falls_back_to_the_close_per_the_csharp_header():
    """The C# (manualVwap = cumVol > 0 ? ... : Close[0]) and its header say VWAP = Close while the session's cumulative
    volume is 0. qi_ref.vwap documents an ASSUMPTION instead: the typical price. See the report: spec-vs-reference
    disagreement - strict xfail below until the reference is aligned to the C#."""
    df = bars([100, 106], high=[106, 106], low=[100, 100], volume=[0, 30])
    df["BarTime"] = pd.to_datetime(["2026-01-06 14:00", "2026-01-06 15:00"])
    df[R.SESSION_FLAG_COL] = [1, 0]
    # bar 0: no volume yet -> Close = 100 ; bar 1: (104 * 30) / 30 = 104 (the zero-volume bar adds nothing)
    assert R.vwap(df).tolist() == pytest.approx([100.0, 104.0], abs=1e-12)



def test_invariances_and_bounds_on_random_sessions():
    rng = np.random.default_rng(4)
    n = 96
    close = 4000 + np.cumsum(rng.choice([-1.0, -0.25, 0.25, 1.0], n))
    high = close + rng.choice([0.25, 0.5, 1.0], n)
    low = close - rng.choice([0.25, 0.5, 1.0], n)
    vol = rng.integers(1, 800, n).astype(float)
    flag = (np.arange(n) % 24 == 0).astype(int)                   # a new session every 24 bars
    df = bars(close, high=high, low=low, volume=vol, start="2026-01-05 00:00", freq="1h")
    df[R.SESSION_FLAG_COL] = flag
    v = R.vwap(df)
    typ = (df["High"] + df["Low"] + df["Close"]) / 3.0
    sid = np.cumsum(flag)
    # VWAP is a volume-weighted mean of the session's typical prices so far: it lies between their running min and max,
    # and on the first bar of a session it IS that bar's typical price
    assert (v >= typ.groupby(sid).cummin() - 1e-9).all() and (v <= typ.groupby(sid).cummax() + 1e-9).all()
    assert v[flag == 1].to_numpy() == pytest.approx(typ[flag == 1].to_numpy(), abs=1e-9)
    # scaling every volume by a constant changes nothing
    df2 = df.copy()
    df2["Volume"] = vol * 13.0
    assert R.vwap(df2).to_numpy() == pytest.approx(v.to_numpy(), abs=1e-9)
    # the ATR-normalised distance ignores a price shift (back-adjustment) and a price scale
    d = R.vwap_distance(df).to_numpy()
    for k, s in ((1.0, 500.0), (4.0, 0.0)):
        shifted = df.copy()
        for c in ("Open", "High", "Low", "Close"):
            shifted[c] = df[c] * k + s
        assert R.vwap_distance(shifted).to_numpy() == pytest.approx(d, abs=1e-9)


def test_falsifier_close_price_or_calendar_midnight_reset_is_detected():
    """Two plausible slips on the hand frame. (1) Weighting the CLOSE instead of the typical price gives
    (100 * 10 + 106 * 30) / 40 = 104.5 at bar 1 instead of 103.5. (2) Resetting at calendar midnight instead of at the
    session start gives 102.0 at bar 4 instead of 103.0 (and no reset at bar 3: 102.83 instead of 104)."""
    v = R.vwap(_hand_frame()).tolist()
    assert v[1] != pytest.approx(104.5, abs=1e-6)
    assert v[4] != pytest.approx(102.0, abs=1e-6)
    assert v[3] != pytest.approx(102.83333333333333, abs=1e-6)
    assert v[1] == pytest.approx(103.5, abs=1e-12) and v[3] == pytest.approx(104.0, abs=1e-12) \
        and v[4] == pytest.approx(103.0, abs=1e-12)


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is True                       # VWAP line on the price chart, no sub-panel
    assert c["plots"] == ["VWAP", "VWAP Dist (ATR)"]  # the distance plot is transparent, DataBox only
    assert sorted(c["series"]) == ["SessionStart", "Vwap", "VwapDistance"]   # read by QS_*_VWAPDistance and the harness
    assert c["lines"] == {}
    assert c["defaults"]["ShowDisclaimer"] == "false"
    assert c["defaults"]["ShowTransparentPlotsInDataBox"] == "true"


def test_csharp_resets_on_the_session_uses_typical_price_and_is_intraday_only():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"sessionStartSeries\[0\]\s*=\s*Bars\.IsFirstBarOfSession\s*\?\s*1\s*:\s*0\s*;", text)
    assert re.search(r"if\s*\(Bars\.IsFirstBarOfSession\)\s*\{[^}]*cumTypicalPriceVol\s*=\s*0;[^}]*cumVol\s*=\s*0;", text)
    assert re.search(r"typicalPrice\s*=\s*\(High\[0\]\s*\+\s*Low\[0\]\s*\+\s*Close\[0\]\)\s*/\s*3\.0", text)
    assert re.search(r"manualVwap\s*=\s*\(cumVol\s*>\s*0\)\s*\?\s*cumTypicalPriceVol\s*/\s*cumVol\s*:\s*Close\[0\]", text)
    assert re.search(r"isIntraday\s*=\s*Bars\.BarsType\.IsIntraday", text)
    assert re.search(r"\(isIntraday\s*&&\s*atr14\[0\]\s*>\s*0\s*&&\s*manualVwap\s*>\s*0\)\s*\?\s*\(Close\[0\]\s*-\s*manualVwap\)\s*/\s*atr14\[0\]\s*:\s*0", text)
    assert "if (CurrentBar < 50)" in text             # accumulation starts at bar 50 (first session partial)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got_dist = harness_col(df, MODULE, "VwapDistance")
    times = pd.to_datetime(df["BarTime"])
    if not (times.diff().dropna().median() < pd.Timedelta(days=1)):
        # VWAP is live on intraday charts only: on a daily/weekly export the C# plot is 0 from bar 50
        assert np.nan_to_num(got_dist.to_numpy(float)[50:]).tolist() == [0.0] * (len(df) - 50)
        return
    flag = harness_col(df, MODULE, "SessionStart").to_numpy(float)
    ref_df = df[["BarTime", "Open", "High", "Low", "Close", "Volume"]].copy()
    ref_df[R.SESSION_FLAG_COL] = flag                 # mirror the C# reset exactly (the column name is rank independent here)
    starts = np.flatnonzero(flag[50:] > 0.5)
    if starts.size == 0:
        pytest.skip("no session start at or after bar 50 in the export")
    start = 50 + int(starts[0])                       # the C# accumulates from bar 50: the first full session begins here
    assert_close(R.vwap(ref_df), harness_col(df, MODULE, "Vwap"), start=start, tol=6e-5, label="VWAPDistance.Vwap")
    assert_close(R.vwap_distance(ref_df), got_dist, start=start, tol=6e-5, label="VWAPDistance.VwapDistance")
