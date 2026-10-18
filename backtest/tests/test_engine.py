"""P&L arithmetic and cost charging on hand fixtures (PROTOCOL sections 4-6, ledger BT1/BT2/BT7/BT8)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qibt import engine
from qibt.engine import bar_costs, bar_ledger, buy_and_hold_positions, run_positions


def _frame(opens, dates):
    return pd.DataFrame({"TradingDate": pd.to_datetime(dates), "Open": np.asarray(opens, dtype=float)})


def check_hand_fixture(ledger):
    """opens 100 101 103 102 105 104, p = 1 1 -1 0 0 1 (decided at each bar close):
         bar j | held p_{j-1} | gross = p_{j-1}*(O_{j+1}-O_j)*5 | sides |p_{j-1}-p_{j-2}|
           0   |      0       |  0 (nothing executed yet)        | 0
           1   |      1       |  1*(103-101)*5 = +10             | |1-0|  = 1
           2   |      1       |  1*(102-103)*5 =  -5             | |1-1|  = 0
           3   |     -1       | -1*(105-102)*5 = -15             | |-1-1| = 2
           4   |      0       |  0*(104-105)*5 =   0             | |0+1|  = 1
           5   |      0       |  0 (last bar: no Open_6)         | |0-0|  = 0 (executed, charged)
                                                         (p_5 = 1 is never executed)
    Returns the list of mismatching quantities."""
    held, gross, sides = ledger([100, 101, 103, 102, 105, 104], [1, 1, -1, 0, 0, 1])
    bad = []
    if list(held) != [0, 1, 1, -1, 0, 0]:
        bad.append(("held", list(held)))
    if list(gross) != [0, 10, -5, -15, 0, 0]:
        bad.append(("gross", list(gross)))
    if list(sides) != [0, 1, 0, 2, 1, 0]:
        bad.append(("sides", list(sides)))
    return bad


def test_hand_fixture():
    assert check_hand_fixture(bar_ledger) == []


def test_one_point_on_one_contract_is_exactly_5_usd():
    _, gross, _ = bar_ledger([100.0, 100.0, 101.0], [1, 0, 0])
    assert gross[1] == 5.0 and engine.POINT_VALUE == 5.0


def test_cost_constants():
    assert engine.TICK_SIZE == 0.25
    assert engine.SLIPPAGE_PER_SIDE == 1.25
    assert engine.COMMISSION_PER_SIDE == 1.00
    assert engine.COST_PER_SIDE == 2.25 and 2 * engine.COST_PER_SIDE == 4.50


@pytest.mark.parametrize("pos,want_sides", [
    ([1, 1, 1, 1, 1], [0, 1, 0, 0, 0]),         # hold: one entry side, then 0
    ([0, 1, 1, 1, 1], [0, 0, 1, 0, 0]),         # flat -> long = 1 side
    ([1, -1, -1, -1, -1], [0, 1, 2, 0, 0]),     # long -> short = 2 sides
    ([-1, 0, 0, 0, 0], [0, 1, 1, 0, 0]),        # short -> flat = 1 side
    ([0, 0, 0, 0, 0], [0, 0, 0, 0, 0]),
])
def test_cost_sides(pos, want_sides):
    _, _, sides = bar_ledger([10, 11, 12, 13, 14], pos)
    assert list(sides) == want_sides


def test_cost_multiplier_is_linear():
    rng = np.random.default_rng(3)
    pos = rng.integers(-1, 2, 200)
    opens = 4000 + np.cumsum(rng.integers(-4, 5, 200)) * 0.25
    _, gross, sides = bar_ledger(opens, pos)
    c1 = bar_costs(sides, 1.0)
    assert np.array_equal(bar_costs(sides, 0.0), np.zeros_like(c1))
    assert np.allclose(bar_costs(sides, 2.0), 2 * c1)
    assert np.allclose(c1, sides * 2.25)


def test_first_bar_carries_nothing_and_last_bar_no_pnl():
    held, gross, sides = bar_ledger([1, 2, 3, 4], [1, 1, 1, 1])
    assert gross[0] == sides[0] == held[0] == 0 and gross[-1] == 0
    assert held[-1] == 1 and sides[-1] == 0


def check_last_bar_charged(ledger):
    """p = 0 0 1 1: p_2 = 1 is executed at the open of the LAST bar (PROTOCOL 4): PROTOCOL 5
    charges that side although the last bar carries no P&L (Channel B finding F3)."""
    held, gross, sides = ledger([10, 11, 12, 13], [0, 0, 1, 1])
    return list(sides) == [0, 0, 0, 1] and list(gross) == [0, 0, 0, 0] and list(held) == [0, 0, 0, 1]


def test_last_bar_execution_is_charged():
    assert check_last_bar_charged(bar_ledger)
    dates = pd.to_datetime(["2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11"])
    dr = run_positions(_frame([10, 11, 12, 13], dates), [0, 0, 1, 1], pd.DatetimeIndex(dates))
    assert list(dr.sides) == [0, 0, 0, 1] and list(dr.net(1.0)) == [0, 0, 0, -2.25]
    assert dr.bar_sides_total == 1


def test_daily_aggregation_books_holding_bar_date_and_fills_flat_days():
    # 3 intraday bars per date; the last bar of a date earns until the next date's first open
    dates = ["2024-01-08"] * 3 + ["2024-01-09"] * 3 + ["2024-01-10"] * 3
    opens = [100, 101, 102, 103, 104, 105, 106, 107, 108]
    pos = [1, 1, 1, 0, 0, 0, 0, 0, 0]
    f = _frame(opens, dates)
    cal = pd.DatetimeIndex(pd.to_datetime(["2024-01-08", "2024-01-09", "2024-01-10"]))
    dr = run_positions(f, pos, cal)
    # bar1 (01-08): +5, bar2 (01-08): +5, bar3 (01-09, first bar, held p2=1): +5; costs:
    # entry side at bar1 (01-08), exit side at bar4 (01-09)
    assert list(dr.gross) == [10, 5, 0]
    assert list(dr.sides) == [1, 1, 0]
    assert list(dr.net(1.0)) == [10 - 2.25, 5 - 2.25, 0]
    assert list(dr.exposed) == [True, True, False]
    assert dr.bar_gross_total == 15 and dr.bar_sides_total == 2


def test_window_filter_drops_out_of_window_bars():
    dates = ["2024-01-08"] * 2 + ["2024-01-09"] * 2 + ["2024-01-10"] * 2
    f = _frame([100, 101, 102, 103, 104, 105], dates)
    cal = pd.DatetimeIndex(pd.to_datetime(["2024-01-09"]))
    dr = run_positions(f, [1, 1, 1, 1, 1, 1], cal)
    # in-window bars: 2 (held p1=1: +5) and 3 (held p2=1: +5); the entry side was on 01-08
    assert list(dr.gross) == [10] and list(dr.sides) == [0]


def test_buy_and_hold_single_entry_cost():
    dates = pd.bdate_range("2020-12-28", "2021-01-08")
    opens = np.arange(len(dates)) * 2.0 + 3000
    f = _frame(opens, dates)
    cal = engine.window_calendar(f.assign(TradingDate=dates))
    p = buy_and_hold_positions(f)
    dr = run_positions(f, p, cal)
    i0 = list(dates).index(pd.Timestamp("2021-01-04"))
    assert p[: i0 - 1].sum() == 0 and p[i0 - 1:].min() == 1
    assert dr.sides.sum() == 1 and dr.sides[0] == 1
    assert dr.gross.sum() == (opens[-1] - opens[i0]) * 5


# --------------------------------------------------------------------------------------------
# falsifiers
# --------------------------------------------------------------------------------------------
def test_falsifier_same_bar_execution_is_detected():
    """p_t applied to the bar it was decided on (look-ahead) must fail the hand fixture."""
    def lookahead(open_, pos):
        o, p = np.asarray(open_, float), np.asarray(pos, float)
        n = len(o)
        held, gross, sides = np.zeros(n), np.zeros(n), np.zeros(n)
        held[: n - 1] = p[: n - 1]
        gross[: n - 1] = p[: n - 1] * (o[1:] - o[:-1]) * 5
        sides[: n - 1] = np.abs(p[: n - 1] - np.concatenate([[0], p[: n - 2]]))
        return held, gross, sides
    assert check_hand_fixture(lookahead) != []


def test_falsifier_cost_on_position_size_is_detected():
    """Charging |p_t| every bar instead of |p_t - p_{t-1}| must fail the hold = 0 sides case."""
    def per_bar(open_, pos):
        held, gross, _ = bar_ledger(open_, pos)
        return held, gross, np.abs(held)
    assert check_hand_fixture(per_bar) != []


def test_falsifier_uncharged_last_bar_execution_is_detected():
    """The pre-F3 engine (last bar carries neither P&L nor cost) must fail the last-bar check."""
    def old(open_, pos):
        held, gross, sides = bar_ledger(open_, pos)
        held[-1] = sides[-1] = 0.0
        return held, gross, sides
    assert not check_last_bar_charged(old)
