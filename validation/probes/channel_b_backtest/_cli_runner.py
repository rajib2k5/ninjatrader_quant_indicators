"""Run qibt.cli.main from a (mutant) package root: python -I -B _cli_runner.py --qibt-root DIR run ...

Only used for the BT18 falsifier. The mutant copy lives outside the repo, so its signals.py cannot
find validation/pytests (appended here) and its data.py would look for the P1 cache next to itself
(pointed back at the repo's backtest/data, read-only use: the cache key matches, so it is a hit).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

_cb.use_qibt(need_qi_ref=True)
from pathlib import Path  # noqa: E402

from qibt import cli, data  # noqa: E402

data.DATA_DIR = Path(_cb.REPO) / "backtest" / "data"
sys.exit(cli.main(sys.argv[1:]))
