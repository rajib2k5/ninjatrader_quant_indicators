"""conftest.py - the `slow` marker and the P1 fixture for the backtest test suite.

Plain helpers (paths, synthetic bars) live in bt_helpers.py, imported by name.
Run from the repository root:
    python -I -m pytest backtest/tests -q -p no:cacheprovider -m "not slow"
    python -I -m pytest backtest/tests -q -p no:cacheprovider -m slow      (needs the P1 files)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from bt_helpers import p1_available  # noqa: E402  (also puts backtest/ on sys.path)


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: needs the P1 vendor files and/or runs for minutes")


@pytest.fixture(scope="session")
def p1_minute():
    """The cached P1 1-minute frame, or skip when the vendor files are absent."""
    if not p1_available():
        pytest.skip("P1 files not present")
    from qibt import data
    return data.load_p1()
