"""conftest.py for tests/indicators - path setup and the `slow` marker only.

Helpers live in qi_helpers.py (a unique module name, so this suite can run in the same pytest
session as validation/pytests and backtest/tests, whose conftest modules have other contents).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import qi_helpers  # noqa: E402,F401  (adds validation/pytests and backtest to sys.path)


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: compiles NinjaScript or reads large files")
