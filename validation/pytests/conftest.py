"""conftest.py for validation/pytests - registers the marker and the session fixtures.

Everything else (paths, loaders, synthetic-bar builders) lives in vp_helpers.py, imported by
name, so this suite can share one pytest session with tests/indicators and backtest/tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from vp_helpers import harness, old_export  # noqa: E402,F401  (fixtures: importing registers them)


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: compiles C# with the dotnet Roslyn csc (seconds per file)")
