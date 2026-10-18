"""merge_runs.py must join the per-module harness exports written by the QIV_NN_* indicators.

Regression for a defect found on 2026-10-18: after the rank relabel the export files are named
qiv_<NN>_<Module>_<INSTR>_<PERIOD>.csv and the old file-name pattern rejected every one of them,
so no qi_dump_*.csv was built and every NinjaTrader-export test skipped silently.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "validation" / "probes" / "merge_runs.py"


def _export(path: Path, cls: str, member: str, values):
    rows = ["BarTime,Bar,Open,High,Low,Close,Volume," + f"{cls}.{member}"]
    for i, v in enumerate(values):
        rows.append(f"2026-01-05 09:{i:02d}:00,{i},10,11,9,10.5,100,{v}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_merges_rank_numbered_exports(tmp_path):
    _export(tmp_path / "qiv_01_ConsecDays_MES_Minute-5.csv", "QI_01_ConsecDays", "Streak", [0, 1, 2])
    _export(tmp_path / "qiv_27_KeyLevels_MES_Minute-5.csv", "QI_27_KeyLevels", "OrbHigh", [5, 6, 7])
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    out = tmp_path / "qi_dump_MES_Minute-5.csv"
    assert out.exists(), r.stdout
    df = pd.read_csv(out)
    assert {"QI_01_ConsecDays.Streak", "QI_27_KeyLevels.OrbHigh"} <= set(df.columns)
    assert df["QI_27_KeyLevels.OrbHigh"].tolist() == [5, 6, 7]


def test_falsifier_old_pattern_rejects_numbered_names():
    old = re.compile(r"^qiv_(?P<mod>[A-Za-z0-9]+)_(?P<instr>[A-Za-z0-9]+)_(?P<period>[A-Za-z]+-\d+)\.csv$")
    assert old.match("qiv_27_KeyLevels_MES_Minute-5.csv") is None or \
        old.match("qiv_27_KeyLevels_MES_Minute-5.csv")["mod"] != "27_KeyLevels"
