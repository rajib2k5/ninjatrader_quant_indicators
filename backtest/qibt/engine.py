"""engine.py - execution, P&L and costs of backtest/PROTOCOL.md sections 4-6.

At the close of bar t the rule sets p_t. p_t is executed at Open_{t+1} and held until Open_{t+2}:
    gross P&L of bar t+1 (USD) = p_t * (Open_{t+2} - Open_{t+1}) * 5
    cost of bar t+1 (USD)      = |p_t - p_{t-1}| * cost_per_side * cost_mult,   p_{-1} = 0
The last bar of the data carries no P&L (it has no Open_{t+2}), but the change executed at its
open IS charged (PROTOCOL 5 charges every executed change); bar 0 carries nothing.
Bar values are booked on the trading date of the holding bar t+1; 15m bars are summed per date.
Only trading dates inside the evaluation window are counted; every date of the D-frame calendar
inside the window is present (flat days are 0).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

POINT_VALUE = 5.0                    # USD per index point, MES (ledger BT1)
TICK_SIZE = 0.25                     # index points (ledger BT2)
COMMISSION_PER_SIDE = 1.00           # USD, commission + exchange/NFA fees (assumption, BT3)
SLIPPAGE_PER_SIDE = TICK_SIZE * POINT_VALUE          # 1 tick = USD 1.25
COST_PER_SIDE = COMMISSION_PER_SIDE + SLIPPAGE_PER_SIDE  # USD 2.25
COST_MULTS = (0.0, 1.0, 2.0)

EVAL_WINDOW = (pd.Timestamp("2021-01-04"), pd.Timestamp("2026-02-24"))
HALVES = {
    "H1": (pd.Timestamp("2021-01-04"), pd.Timestamp("2023-07-31")),
    "H2": (pd.Timestamp("2023-08-01"), pd.Timestamp("2026-02-24")),
}


def bar_ledger(open_, pos, point_value=POINT_VALUE):
    """Per-bar arrays (held, gross, sides) indexed by the HOLDING (execution) bar j = t+1.

    held[j] = p_{j-1} and sides[j] = |p_{j-1} - p_{j-2}| for j = 1 .. n-1 (p_{-1} = 0);
    gross[j] = p_{j-1}*(O_{j+1} - O_j)*point_value for j = 1 .. n-2. Bar 0 is all 0; the last
    bar has gross 0 (no Open_{n}) but its execution is held and charged."""
    o = np.asarray(open_, dtype=float)
    p = np.asarray(pos, dtype=float)
    if o.shape != p.shape:
        raise ValueError("open and positions differ in length: %s vs %s" % (o.shape, p.shape))
    n = len(o)
    held = np.zeros(n)
    gross = np.zeros(n)
    sides = np.zeros(n)
    if n >= 2:
        pt = p[: n - 1]                                   # p_t for t = 0 .. n-2 (executed at bar t+1)
        prev = np.concatenate([[0.0], p[: n - 2]])       # p_{t-1}, p_{-1} = 0
        held[1:] = pt
        sides[1:] = np.abs(pt - prev)
        gross[1: n - 1] = pt[:-1] * (o[2:] - o[1: n - 1]) * point_value
    return held, gross, sides


def bar_costs(sides, cost_mult=1.0, cost_per_side=COST_PER_SIDE):
    return np.asarray(sides, dtype=float) * cost_per_side * cost_mult


def window_calendar(d_frame, window=EVAL_WINDOW):
    """Trading dates of the D frame inside the evaluation window (DatetimeIndex)."""
    d = pd.DatetimeIndex(pd.to_datetime(d_frame["TradingDate"]))
    return d[(d >= window[0]) & (d <= window[1])]


@dataclass
class DailyResult:
    """Daily aggregates of one position series on the window calendar."""
    dates: pd.DatetimeIndex
    gross: np.ndarray        # USD
    sides: np.ndarray        # contracts traded (|delta p| summed)
    changes: np.ndarray      # number of bars with p_t != p_{t-1} executed that day
    exposed: np.ndarray      # bool: some bar of the day was held with p != 0
    long_bars: np.ndarray
    short_bars: np.ndarray
    bars: np.ndarray         # frame bars of the day that are inside the data (incl. the flat ones)
    pnl_long: np.ndarray     # gross USD from bars held long
    pnl_short: np.ndarray    # gross USD from bars held short
    bar_gross_total: float   # sum over in-window bars (reconciliation)
    bar_sides_total: float

    def cost(self, cost_mult=1.0, cost_per_side=COST_PER_SIDE):
        return self.sides * cost_per_side * cost_mult

    def net(self, cost_mult=1.0, cost_per_side=COST_PER_SIDE):
        return self.gross - self.cost(cost_mult, cost_per_side)

    def series(self, cost_mult=1.0):
        return pd.Series(self.net(cost_mult), index=self.dates)


def run_positions(frame, pos, calendar, point_value=POINT_VALUE):
    """Aggregate one position series on its frame to the window calendar."""
    held, gross, sides = bar_ledger(frame["Open"].to_numpy(), pos, point_value)
    codes = calendar.get_indexer(pd.DatetimeIndex(pd.to_datetime(frame["TradingDate"])))
    ok = codes >= 0
    c = codes[ok]
    m = len(calendar)

    def agg(x):
        return np.bincount(c, weights=np.asarray(x, dtype=float)[ok], minlength=m)

    g = gross[ok]
    return DailyResult(
        dates=calendar,
        gross=agg(gross),
        sides=agg(sides),
        changes=agg(sides > 0),
        exposed=agg(held != 0) > 0,
        long_bars=agg(held > 0),
        short_bars=agg(held < 0),
        bars=agg(np.ones(len(held))),
        pnl_long=agg(np.where(held > 0, gross, 0.0)),
        pnl_short=agg(np.where(held < 0, gross, 0.0)),
        bar_gross_total=float(g.sum()),
        bar_sides_total=float(sides[ok].sum()),
    )


def buy_and_hold_positions(d_frame, window=EVAL_WINDOW):
    """+1 from the D bar before the first evaluation date on, so the single entry executes at
    the first evaluation open (one side) and is never closed."""
    d = pd.DatetimeIndex(pd.to_datetime(d_frame["TradingDate"]))
    i0 = int(np.searchsorted(d.values, np.datetime64(window[0]), side="left"))
    p = np.zeros(len(d), dtype=np.int8)
    p[max(i0 - 1, 0):] = 1
    return p
