"""bt_helpers - paths and synthetic-bar helpers for the backtest test suite (import by name).

Kept out of conftest.py so this suite can share a pytest session with the other test folders.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

TESTS_DIR = Path(__file__).resolve().parent
BACKTEST_DIR = TESTS_DIR.parent
REPO_DIR = BACKTEST_DIR.parent
if str(BACKTEST_DIR) not in sys.path:          # makes `import qibt` work without installing it
    sys.path.insert(0, str(BACKTEST_DIR))

OHLCV = ["Open", "High", "Low", "Close", "Volume"]


def p1_available():
    from qibt import data
    return bool(data.p1_files())


# --------------------------------------------------------------------------------------------
# synthetic CME-style sessions (17:01 previous calendar day .. 16:00, bar time = close time)
# --------------------------------------------------------------------------------------------
def session_close_times(trading_dates, step_minutes=1):
    """Close times of every bar of each trading date's Globex session, naive US Central."""
    out = []
    for d in pd.DatetimeIndex(pd.to_datetime(trading_dates)):
        start = d - pd.Timedelta(days=1) + pd.Timedelta(hours=17)
        end = d + pd.Timedelta(hours=16)
        out.append(pd.date_range(start + pd.Timedelta(minutes=step_minutes), end,
                                 freq="%dmin" % step_minutes))
    return out[0].append(out[1:]) if len(out) > 1 else out[0]


def random_bars(times, seed=0, start=4000.0, tick=0.25, max_ticks=8):
    """Quarter-tick random-walk OHLCV bars at the given close times (deterministic)."""
    rng = np.random.default_rng(seed)
    n = len(times)
    steps = rng.integers(-max_ticks, max_ticks + 1, size=n) * tick
    close = start + np.cumsum(steps)
    open_ = np.concatenate([[start], close[:-1]]) + rng.integers(-1, 2, size=n) * tick
    hi = np.maximum(open_, close) + rng.integers(0, 4, size=n) * tick
    lo = np.minimum(open_, close) - rng.integers(0, 4, size=n) * tick
    vol = rng.integers(1, 500, size=n).astype(float)
    return pd.DataFrame({"BarTime": pd.DatetimeIndex(times), "Open": open_, "High": hi, "Low": lo,
                         "Close": close, "Volume": vol})


def weekday_dates(start, end):
    return pd.bdate_range(start, end)
