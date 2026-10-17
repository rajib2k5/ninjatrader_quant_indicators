"""conftest.py - paths, markers and synthetic-bar helpers for the backtest test suite.

Run from the repository root:
    python -I -m pytest backtest/tests -q -p no:cacheprovider -m "not slow"
    python -I -m pytest backtest/tests -q -p no:cacheprovider -m slow      (needs the P1 files)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

TESTS_DIR = Path(__file__).resolve().parent
BACKTEST_DIR = TESTS_DIR.parent
REPO_DIR = BACKTEST_DIR.parent
if str(BACKTEST_DIR) not in sys.path:          # makes `import qibt` work without installing it
    sys.path.insert(0, str(BACKTEST_DIR))

OHLCV = ["Open", "High", "Low", "Close", "Volume"]


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: needs the P1 vendor files and/or runs for minutes")


def p1_available():
    from qibt import data
    return bool(data.p1_files())


@pytest.fixture(scope="session")
def p1_minute():
    """The cached P1 1-minute frame, or skip when the vendor files are absent."""
    if not p1_available():
        pytest.skip("P1 files not present")
    from qibt import data
    return data.load_p1()


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
