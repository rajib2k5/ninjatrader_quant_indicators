#!/usr/bin/env python3
"""merge_runs.py - join the per-module QIV_*.csv exports into one qi_dump_<INSTR>_<PERIOD>.csv.

Usage: python merge_runs.py [runs_dir]        (default: validation/runs next to this script's repo)

For every (instrument, period) pair found in qiv_<Module>_<INSTR>_<PERIOD>.csv files, the bar
columns (BarTime, Bar, Open, High, Low, Close, Volume) are taken from the first file and the
QI_<Module>.* columns of every file are joined on BarTime (inner join - a bar must be present in
all modules' exports). Reports which modules are missing for each pair.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

NAME_RE = re.compile(r"^qiv_(?P<mod>[A-Za-z0-9]+)_(?P<instr>[A-Za-z0-9]+)_(?P<period>[A-Za-z]+-\d+)\.csv$")


def main():
    runs = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "runs"
    groups = {}
    for f in sorted(runs.glob("qiv_*.csv")):
        m = NAME_RE.match(f.name)
        if not m:
            print(f"skip (name): {f.name}"); continue
        groups.setdefault((m["instr"], m["period"]), []).append((m["mod"], f))
    if not groups:
        print(f"no qiv_*.csv files in {runs}"); sys.exit(1)
    for (instr, period), files in groups.items():
        merged = None
        bad = []
        for mod, f in files:
            df = pd.read_csv(f)
            if df.empty:
                bad.append(f"{mod} (0 rows)"); continue
            cols = ["BarTime"] + [c for c in df.columns if c.startswith("QI_")]
            part = df[cols].drop_duplicates("BarTime", keep="last")
            if merged is None:
                merged = df[["BarTime", "Bar", "Open", "High", "Low", "Close", "Volume"]].drop_duplicates("BarTime", keep="last")
            merged = merged.merge(part, on="BarTime", how="inner")
        if merged is None:
            print(f"{instr} {period}: nothing to merge"); continue
        out = runs / f"qi_dump_{instr}_{period}.csv"
        merged.to_csv(out, index=False)
        print(f"{out.name}: {len(merged)} bars x {len(merged.columns)} columns from {len(files) - len(bad)} modules"
              + (f"; EMPTY: {', '.join(bad)}" if bad else ""))
        expected = 27
        if len(files) - len(bad) != expected:
            print(f"  warning: {len(files) - len(bad)} of {expected} modules present")


if __name__ == "__main__":
    main()
