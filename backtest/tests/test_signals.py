"""Value names -> qi_ref / derived values / qibt.patterns, on the rule's frame (PROTOCOL 3-4)."""
from __future__ import annotations

import math
import sys
import types

import numpy as np
import pandas as pd
import pytest

from bt_helpers import random_bars, session_close_times, weekday_dates
from qibt import data, signals
from qibt.signals import qi_ref

TS = pd.Timestamp


@pytest.fixture(scope="module")
def frames():
    dates = weekday_dates("2023-01-02", "2023-12-29")
    t = session_close_times(dates, step_minutes=15)            # 15-minute closes keep it fast
    return data.build_frames(random_bars(t, seed=21, max_ticks=12))


def test_every_rule_value_is_registered():
    rs = signals.load_rules()
    vals = {r.value for r in rs.rules}
    assert vals <= set(signals.VALUE_FUNCTIONS) | set(signals.PATTERN_VALUES)
    assert {r.value for r in rs.rules if r.value in signals.PATTERN_VALUES} == set(signals.PATTERN_VALUES)
    assert len(vals - set(signals.PATTERN_VALUES)) == 21


def test_qi_ref_is_the_validated_module():
    assert qi_ref.__file__.replace("\\", "/").endswith("validation/pytests/qi_ref.py")


# pass-through values must equal the direct qi_ref call on the same frame
PASS_THROUGH = {
    "rsi2": lambda f: qi_ref.rsi(f["Close"], 2),
    "rsi14": lambda f: qi_ref.rsi(f["Close"], 14),
    # connors_rsi is NOT a pass-through since ADD-10 (point-change rank, as the C#); see below
    "stoch_k": lambda f: qi_ref.stoch_fast(f, 3, 14)[0],
    "rv_zscore": lambda f: qi_ref.rv_zscore(f),
    "composite_vol": lambda f: qi_ref.composite_vol(f)["composite"],
    "consec_streak": lambda f: qi_ref.streak(f["Close"]),
    "overnight_gap_pct": lambda f: qi_ref.gap_pct(f),
    "vrp_proxy": lambda f: qi_ref.vrp_proxy(f),
    "wide_range": lambda f: qi_ref.wide_range(f),
    "macd_hist": lambda f: qi_ref.macd(f["Close"], 12, 26, 9)[2],
    "ema_spread": lambda f: qi_ref.ema(f["Close"], 20) - qi_ref.ema(f["Close"], 50),
    "sma200_distance": lambda f: qi_ref.sma200_trend(f["Close"])[1],
    "atr_regime": lambda f: qi_ref.atr_regime(f),
    "volume_spike": lambda f: qi_ref.volume_spike(f),
    "cum_delta20": lambda f: qi_ref.volume_delta(f)[1],
    "ibs_daily": lambda f: qi_ref.ibs_bar(f),
}


@pytest.mark.parametrize("name", sorted(PASS_THROUGH))
@pytest.mark.parametrize("frame", ["D", "15m"])
def test_pass_through_values_equal_qi_ref(frames, name, frame):
    f = frames[frame]
    got = signals.compute_value(name, f)
    want = np.asarray(PASS_THROUGH[name](f), dtype=float)
    np.testing.assert_array_equal(got, want)


def test_ibs_daily_hand_values():
    d = pd.DataFrame({"TradingDate": pd.to_datetime(["2024-01-02", "2024-01-03"]), "BarTime": pd.to_datetime(["2024-01-02 16:00", "2024-01-03 16:00"]),
                      "Open": [101, 5], "High": [110, 5], "Low": [100, 5], "Close": [102, 5], "Volume": [1, 1]})
    assert signals.compute_value("ibs_daily", d).tolist() == pytest.approx([0.2, 0.5])


def check_touch(fn):
    """close, upper, middle, lower, atr -> expected touch (ORIG: buy branch first, 0.001*ATR tol)."""
    cases = [
        ((95.0, 110, 100, 96, 10), -1.0),       # below lower
        ((96.005, 110, 100, 96, 10), -1.0),     # within +0.01 of lower
        ((96.02, 110, 100, 96, 10), 0.0),
        ((109.995, 110, 100, 96, 10), 1.0),     # within 0.01 of upper
        ((111.0, 110, 100, 96, 10), 1.0),
        ((100.0, 100, 100, 100, 10), -1.0),     # zero-width band: buy branch wins
        ((100.0, math.nan, math.nan, math.nan, 10), math.nan),
    ]
    bad = []
    for args, want in cases:
        got = float(fn(*[np.array([a], dtype=float) for a in args])[0])
        if not (got == want or (math.isnan(got) and math.isnan(want))):
            bad.append((args, got, want))
    return bad


def test_bollinger_touch_hand_cases():
    assert check_touch(signals.bollinger_touch_from) == []


def test_bollinger_touch_on_frame_uses_bands_and_atr(frames):
    f = frames["15m"]
    up, mid, lo = qi_ref.bollinger(f["Close"], 20, 2.0)
    want = signals.bollinger_touch_from(f["Close"], up, mid, lo, qi_ref.atr(f, 14))
    got = signals.compute_value("bollinger_touch", f)
    np.testing.assert_array_equal(got, want)
    assert np.isnan(got[:19]).all() and set(np.unique(got[19:])) <= {-1.0, 0.0, 1.0}


def test_session_start_flags_first_bar_of_each_trading_date():
    d = pd.to_datetime(["2024-01-02"] * 2 + ["2024-01-03"] * 3 + ["2024-01-04"])
    assert signals.session_start_flags(d).tolist() == [1, 0, 1, 0, 0, 1]


def test_vwap_distance_resets_on_each_trading_date(frames):
    f = frames["15m"]
    got = signals.compute_value("vwap_distance", f)
    first = np.flatnonzero(signals.session_start_flags(f["TradingDate"]) == 1)
    typ = ((f["High"] + f["Low"] + f["Close"]) / 3).to_numpy()
    a14 = qi_ref.atr(f, 14).to_numpy()
    want = (f["Close"].to_numpy()[first] - typ[first]) / a14[first]
    np.testing.assert_allclose(got[first], want, rtol=0, atol=1e-9)   # (typ*vol)/vol rounding
    flagged = f[["BarTime", "Open", "High", "Low", "Close", "Volume"]].copy()
    flagged[qi_ref.SESSION_FLAG_COL] = signals.session_start_flags(f["TradingDate"])
    np.testing.assert_array_equal(got, qi_ref.vwap_distance(flagged).to_numpy())


def test_day_of_week_monday_is_1_on_trading_date():
    m1 = random_bars(session_close_times(weekday_dates("2024-03-11", "2024-03-15"), step_minutes=60))
    d = data.build_frames(m1)["D"]
    assert signals.compute_value("day_of_week", d).tolist() == [1, 2, 3, 4, 5]
    f15 = data.build_frames(m1)["15m"]
    sunday_evening = (f15["BarTime"] == TS("2024-03-10 18:00")).to_numpy()
    assert signals.compute_value("day_of_week", f15)[sunday_evening].tolist() == [1.0]


def test_turn_of_month_on_trading_date():
    d = pd.DataFrame({"TradingDate": pd.to_datetime(["2024-01-03", "2024-01-04", "2024-01-26", "2024-01-29", "2024-02-01"])})
    assert signals.compute_value("turn_of_month", d).tolist() == [1, 0, 0, 1, 1]


def test_overnight_gap_hand_value():
    d = pd.DataFrame({"BarTime": pd.to_datetime(["2024-01-02 16:00", "2024-01-03 16:00"]), "TradingDate": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                      "Open": [100.0, 101.0], "High": [102.0, 103.0], "Low": [99.0, 100.0], "Close": [100.0, 102.0], "Volume": [1.0, 1.0]})
    v = signals.compute_value("overnight_gap_pct", d)
    assert math.isnan(v[0]) and v[1] == pytest.approx(1.0)


def test_sma200_rule_is_flat_before_bar_200(frames):
    rs = signals.load_rules()
    rule = next(r for r in rs.rules if r.module == "SMA200Trend")
    _, pos = signals.rule_positions(rule, frames)
    assert (pos[:200] == 0).all() and (pos[200:] != 0).any()


# --------------------------------------------------------------------------------------------
# pattern values: lazy import, pending on any failure
# --------------------------------------------------------------------------------------------
def test_pattern_value_pending_when_module_missing(monkeypatch, frames):
    monkeypatch.setattr(signals, "PATTERNS_MODULE", "qibt._no_such_patterns_module")
    rule = next(r for r in signals.load_rules().rules if r.value == "hp_score")
    with pytest.raises(signals.PendingValue):
        signals.rule_positions(rule, frames)


def test_pattern_value_pending_when_function_raises_or_missing(monkeypatch, frames):
    fake = types.ModuleType("qibt_fake_patterns")

    def hp_score(df):
        raise ZeroDivisionError("boom")
    fake.hp_score = hp_score
    monkeypatch.setitem(sys.modules, "qibt_fake_patterns", fake)
    monkeypatch.setattr(signals, "PATTERNS_MODULE", "qibt_fake_patterns")
    with pytest.raises(signals.PendingValue, match="ZeroDivisionError"):
        signals.compute_value("hp_score", frames["D"])
    with pytest.raises(signals.PendingValue, match="no function"):
        signals.compute_value("smc_structure", frames["D"])


def test_pattern_output_shapes_are_coerced():
    n = 3
    s = pd.Series([1.0, 0.0, -1.0])
    assert signals._coerce(s, "x", n).tolist() == [1, 0, -1]
    assert signals._coerce((s, s * 2), "x", n).tolist() == [1, 0, -1]
    assert signals._coerce({"structure": s}, "x", n).tolist() == [1, 0, -1]
    assert signals._coerce(pd.DataFrame({"confidence": s * 0, "structure": s}), "x", n).tolist() == [1, 0, -1]
    with pytest.raises(signals.PendingValue):
        signals._coerce(s[:2], "x", n)


def test_pipeline_marks_pending_rules(monkeypatch, frames):
    from qibt import cli
    monkeypatch.setattr(signals, "PATTERNS_MODULE", "qibt._no_such_patterns_module")
    rs = signals.load_rules()
    m1 = frames["1m"][["BarTime", "Open", "High", "Low", "Close", "Volume"]]
    res = cli.run_pipeline(m1, rs, window=(TS("2023-03-01"), TS("2023-12-29")),
                           halves={"H1": (TS("2023-03-01"), TS("2023-07-31")), "H2": (TS("2023-08-01"), TS("2023-12-29"))})
    st = {r["module"]: (r["status"], r["rank"]) for r in res["ranking"]}
    for mod in ("HedgingPressure", "LiquiditySweep", "OrderFlowPlus", "SMC"):
        assert st[mod] == ("pending", None)
    assert sorted(r for s, r in st.values() if s == "ok") == list(range(1, 22))
    assert st["ChopIndex"] == ("not_backtestable", 26) and st["KeyLevels"] == ("not_backtestable", 27)


# --------------------------------------------------------------------------------------------
# falsifiers
# --------------------------------------------------------------------------------------------
def test_falsifier_monday_zero_convention_is_detected():
    """ISO-style Monday = 0 would make the TurnaroundTuesday rule (x == 1) buy on Tuesdays."""
    m1 = random_bars(session_close_times(weekday_dates("2024-03-11", "2024-03-15"), step_minutes=60))
    d = data.build_frames(m1)["D"]
    wrong = qi_ref.day_of_week(d["TradingDate"], sunday_zero=False).to_numpy()
    assert wrong.tolist() != signals.compute_value("day_of_week", d).tolist()
    assert wrong.tolist()[0] != 1


def test_falsifier_touch_without_atr_tolerance_is_detected():
    def no_tol(c, up, mid, lo, a):
        v = np.where(c <= lo, -1.0, np.where(c >= up, 1.0, 0.0))
        v[np.isnan(mid)] = np.nan
        return v
    assert check_touch(no_tol) != []


# ---- ADD-10: ConnorsRSI ranks POINT changes, as the shipped C# does ------------------------
def test_connors_rsi_ranks_point_changes_not_percent():
    """Two series with the same percent changes but different point changes must rank
    differently: close 100 -> 101 (+1 pt, +1%) vs 200 -> 202 (+2 pt, +1%). With point ranking,
    a +2 pt move outranks earlier +1 pt moves; with percent ranking it ties them."""
    import numpy as np
    import pandas as pd
    from qibt.signals import v_connors_rsi
    c = np.concatenate([np.full(1, 100.0), 100.0 + np.cumsum(np.tile([1.0, -1.0], 60))])
    c = np.append(c, c[-1] + 2.0)          # last move +2 points, larger than every earlier move
    f = pd.DataFrame({"Close": c})
    v = v_connors_rsi(f).to_numpy()
    # previous 100 changes are +-1 point; +2 is strictly greater than all -> PercentRank 100
    rsi_p = __import__("qi_ref").rsi(c, 2).to_numpy()[-1]
    rsi_s = __import__("qi_ref").rsi(__import__("qi_ref").streak(c).to_numpy(), 2).to_numpy()[-1]
    assert v[-1] == pytest.approx((rsi_p + rsi_s + 100.0) / 3.0)


def test_falsifier_percent_rank_variant_differs_on_rising_prices():
    """Point and percent ranking disagree when the price level changes: +-2 point moves at ~100
    (2%) then +-5 point moves at ~1000 (0.5%). A final +5 move outranks the earlier +-2 moves by
    points but is below them by percent, so the two ConnorsRSI values differ by several points."""
    import numpy as np
    import pandas as pd
    import qi_ref
    from qibt.signals import v_connors_rsi
    low = 100.0 + np.cumsum(np.tile([2.0, -2.0], 40))
    high = 1000.0 + np.cumsum(np.tile([5.0, -5.0], 30))
    c = np.concatenate([low, high, [high[-1] + 5.0]])
    a = v_connors_rsi(pd.DataFrame({"Close": c})).to_numpy()[-1]
    b = qi_ref.connors_rsi(c).to_numpy()[-1]
    assert abs(a - b) > 3.0, (a, b)
