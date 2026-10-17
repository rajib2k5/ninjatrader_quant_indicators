"""Metamorphic / property tests of the engine and the signal pipeline (hypothesis), ledger BT7-BT9."""
from __future__ import annotations

import numpy as np
import pandas as pd
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qibt import engine, metrics, signals
from qibt.engine import bar_ledger

SETTINGS = settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@st.composite
def opens_and_positions(draw, min_n=3, max_n=60):
    n = draw(st.integers(min_n, max_n))
    ticks = draw(st.lists(st.integers(-40, 40), min_size=n, max_size=n))
    opens = 4000.0 + np.cumsum(ticks) * 0.25                     # quarter-tick grid
    pos = np.array(draw(st.lists(st.sampled_from([-1, 0, 1]), min_size=n, max_size=n)), dtype=float)
    return opens, pos


def lookahead_violations(ledger, opens, pos, t, new_opens, new_pos):
    """Mutate opens at index > t+2 and positions at index > t; P&L and costs of bars <= t+1
    must not change. Returns True if they changed (a look-ahead)."""
    o2, p2 = opens.copy(), pos.copy()
    o2[t + 3:] = new_opens[t + 3:]
    p2[t + 1:] = new_pos[t + 1:]
    _, g1, s1 = ledger(opens, pos)
    _, g2, s2 = ledger(o2, p2)
    k = t + 2
    return not (np.array_equal(g1[:k], g2[:k]) and np.array_equal(s1[:k], s2[:k]))


@SETTINGS
@given(opens_and_positions(min_n=4), st.data())
def test_no_lookahead_engine(op, d):
    opens, pos = op
    n = len(opens)
    t = d.draw(st.integers(0, n - 3))
    new_opens = opens + np.array(d.draw(st.lists(st.integers(-400, 400), min_size=n, max_size=n))) * 0.25
    new_pos = np.array(d.draw(st.lists(st.sampled_from([-1, 0, 1]), min_size=n, max_size=n)), dtype=float)
    assert not lookahead_violations(bar_ledger, opens, pos, t, new_opens, new_pos)


def _frame(ticks, vols, start="2024-01-08 09:15", freq="15min"):
    close = 4000.0 + np.cumsum(ticks) * 0.25
    open_ = np.concatenate([[4000.0], close[:-1]])
    hi = np.maximum(open_, close) + 0.5
    lo = np.minimum(open_, close) - 0.5
    bt = pd.date_range(start, periods=len(close), freq=freq)
    return pd.DataFrame({"TradingDate": (bt + pd.Timedelta(hours=7)).normalize(), "BarTime": bt,
                         "Open": open_, "High": hi, "Low": lo, "Close": close, "Volume": np.asarray(vols, float)})


CAUSAL_VALUES = ["rsi2", "bollinger_touch", "vwap_distance", "cum_delta20", "stoch_k", "consec_streak",
                 "macd_hist", "volume_spike", "rv_zscore", "ibs_daily"]


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.data())
def test_no_lookahead_full_pipeline(d):
    """Mutating any bar with index > t+2 never changes the P&L of bars <= t+1 (values -> p -> P&L)."""
    n = d.draw(st.integers(30, 90))
    ticks = d.draw(st.lists(st.integers(-12, 12), min_size=n, max_size=n))
    vols = d.draw(st.lists(st.integers(1, 900), min_size=n, max_size=n))
    t = d.draw(st.integers(0, n - 4))
    f1 = _frame(ticks, vols)
    f2 = f1.copy()
    k = np.arange(n) > t + 2
    jolt = np.array(d.draw(st.lists(st.integers(-200, 200), min_size=n, max_size=n))) * 0.25
    for c in ("Open", "High", "Low", "Close"):
        f2.loc[k, c] = f2.loc[k, c] + jolt[k]
    f2.loc[k, "High"] = f2.loc[k, ["Open", "High", "Low", "Close"]].max(axis=1)
    f2.loc[k, "Low"] = f2.loc[k, ["Open", "High", "Low", "Close"]].min(axis=1)
    f2.loc[k, "Volume"] = f2.loc[k, "Volume"] * 3 + 7
    cond_l, cond_s = signals.parse_condition("x < 0"), signals.parse_condition("x > 0")
    for name in CAUSAL_VALUES:
        v1 = signals.compute_value(name, f1)
        med = np.nanmedian(v1) if np.isfinite(v1).any() else 0.0   # same threshold for both runs
        p1 = signals.to_positions(v1 - med, cond_l, cond_s)
        p2 = signals.to_positions(signals.compute_value(name, f2) - med, cond_l, cond_s)
        _, g1, s1 = bar_ledger(f1["Open"].to_numpy(), p1)
        _, g2, s2 = bar_ledger(f2["Open"].to_numpy(), p2)
        assert np.array_equal(g1[: t + 2], g2[: t + 2]), name
        assert np.array_equal(s1[: t + 2], s2[: t + 2]), name


@SETTINGS
@given(opens_and_positions(), st.integers(-20000, 20000))
def test_additive_price_shift_leaves_pnl_unchanged(op, shift_ticks):
    opens, pos = op
    c = shift_ticks * 0.25                                         # back-adjustment shift
    _, g1, s1 = bar_ledger(opens, pos)
    _, g2, s2 = bar_ledger(opens + c, pos)
    assert np.array_equal(g1, g2) and np.array_equal(s1, s2)


@SETTINGS
@given(opens_and_positions(), st.floats(-5000, 5000, allow_nan=False))
def test_additive_arbitrary_shift_close(op, c):
    opens, pos = op
    _, g1, _ = bar_ledger(opens, pos)
    _, g2, _ = bar_ledger(opens + c, pos)
    assert np.allclose(g1, g2, atol=1e-6)


@SETTINGS
@given(opens_and_positions(), st.floats(0.01, 100, allow_nan=False))
def test_multiplicative_scale_scales_pnl_and_keeps_sr(op, k):
    opens, pos = op
    _, g1, _ = bar_ledger(opens, pos)
    _, g2, _ = bar_ledger(opens * k, pos)
    assert np.allclose(g2, k * g1, rtol=1e-9, atol=1e-9)
    s1, s2 = metrics.sharpe(g1), metrics.sharpe(g2)
    assert (np.isnan(s1) and np.isnan(s2)) or abs(s1 - s2) <= 1e-6 * max(1.0, abs(s1))


@SETTINGS
@given(opens_and_positions())
def test_zero_positions_zero_pnl(op):
    opens, _ = op
    held, g, s = bar_ledger(opens, np.zeros(len(opens)))
    assert not held.any() and not g.any() and not s.any()


@SETTINGS
@given(opens_and_positions(), st.floats(0, 5), st.floats(0, 5))
def test_more_cost_lower_or_equal_net(op, m1, m2):
    opens, pos = op
    lo, hi = min(m1, m2), max(m1, m2)
    dates = pd.date_range("2024-01-08", periods=len(opens), freq="D")
    f = pd.DataFrame({"TradingDate": dates, "Open": opens})
    dr = engine.run_positions(f, pos, pd.DatetimeIndex(dates))
    assert (dr.net(hi) <= dr.net(lo) + 1e-12).all()
    assert dr.net(hi).sum() <= dr.net(lo).sum() + 1e-9


# --------------------------------------------------------------------------------------------
# falsifiers: the same checks must catch deliberately wrong engines
# --------------------------------------------------------------------------------------------
def test_falsifier_lookahead_engine_is_detected():
    """An engine that applies p_{t+1} to bar t+1 (decision and fill on the same bar)."""
    def peek(open_, pos):
        o, p = np.asarray(open_, float), np.asarray(pos, float)
        n = len(o)
        held, gross, sides = np.zeros(n), np.zeros(n), np.zeros(n)
        held[1: n - 1] = p[1: n - 1]
        gross[1: n - 1] = p[1: n - 1] * (o[2:] - o[1: n - 1]) * 5
        return held, gross, sides
    opens = np.array([100.0, 101, 103, 102, 105, 104])
    pos = np.array([0.0, 0, 0, 0, 0, 0])
    assert lookahead_violations(peek, opens, pos, 0, opens, np.array([0.0, 1, 1, 1, 1, 1]))
    assert not lookahead_violations(bar_ledger, opens, pos, 0, opens, np.array([0.0, 1, 1, 1, 1, 1]))


def test_falsifier_percent_returns_break_shift_invariance():
    """Percent-return P&L (wrong for an additively back-adjusted series) changes under a shift."""
    def pct(open_, pos):
        o, p = np.asarray(open_, float), np.asarray(pos, float)
        g = np.zeros(len(o))
        g[1:-1] = p[:-2] * (o[2:] / o[1:-1] - 1.0) * 20000.0
        return g
    opens = np.array([4000.0, 4010, 4030, 4020, 4050])
    pos = np.array([1.0, 1, -1, 0, 0])
    assert not np.allclose(pct(opens, pos), pct(opens - 1500.0, pos))
    assert np.array_equal(bar_ledger(opens, pos)[1], bar_ledger(opens - 1500.0, pos)[1])
