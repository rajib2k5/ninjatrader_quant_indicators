#!/usr/bin/env python3
"""merge_runs.py - join the per-module QIV_*.csv exports into one qi_dump_<INSTR>_<PERIOD>.csv.

Usage: python merge_runs.py [runs_dir]        (default: validation/runs next to this script's repo)

For every (instrument, period) pair found in qiv_<Module>_<INSTR>_<PERIOD>.csv files, the bar
columns (BarTime, Bar, Open, High, Low, Close, Volume) are taken from the first file and the
QI_<Module>.* columns of every file are joined (inner join - a bar must be present in all
modules' exports). Reports which modules are missing for each pair.

Join key: (BarTime, k), k = ordinal of the row inside its same-BarTime group in file order.
On tick charts consecutive bars can share a 1-second BarTime (MES 150-tick: groups of up to 14
bars), so a BarTime-only join with drop_duplicates would silently discard real bars; the QIV_*
files are written in chart order (StreamWriter(file, false): one run per file, never appended),
so the ordinal inside each second pairs the same bar across modules. Bar (CurrentBar) is checked
to agree across modules on every joined row and the output is kept in Bar order, so
diff_values.py can use the same (BarTime, k) key against the ORIG export. On Minute charts
BarTime is unique and k is always 0.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

NAME_RE = re.compile(r"^qiv_(?P<mod>(?:\d\d_)?[A-Za-z0-9]+)_(?P<instr>[A-Za-z0-9]+)_(?P<period>[A-Za-z]+-\d+)\.csv$")
BAR_COLS = ["BarTime", "Bar", "Open", "High", "Low", "Close", "Volume"]


def with_seq(df):
    """Add _k = ordinal of the row within its same-BarTime group (file order)."""
    df = df.copy()
    df["_k"] = df.groupby("BarTime", sort=False).cumcount()
    return df


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
        same_second = 0
        bar_disagree = 0
        for mod, f in files:
            df = pd.read_csv(f)
            if df.empty:
                bad.append(f"{mod} (0 rows)"); continue
            if (df["BarTime"].to_numpy()[1:] < df["BarTime"].to_numpy()[:-1]).any():
                print(f"  warning: {f.name} BarTime goes backwards (not a single chart run?)")
            df = with_seq(df)
            same_second = max(same_second, int((df["_k"] > 0).sum()))
            qcols = [c for c in df.columns if c.startswith("QI_")]
            part = df[["BarTime", "_k", "Bar"] + qcols].rename(columns={"Bar": f"_bar_{mod}"})
            if merged is None:
                merged = df[BAR_COLS + ["_k"]]
            merged = merged.merge(part, on=["BarTime", "_k"], how="inner")
            bar_disagree += int((merged[f"_bar_{mod}"] != merged["Bar"]).sum())
            merged = merged.drop(columns=[f"_bar_{mod}"])
        if merged is None:
            print(f"{instr} {period}: nothing to merge"); continue
        merged = merged.sort_values("Bar").drop(columns=["_k"]).reset_index(drop=True)
        out = runs / f"qi_dump_{instr}_{period}.csv"
        merged.to_csv(out, index=False)
        print(f"{out.name}: {len(merged)} bars x {len(merged.columns)} columns from {len(files) - len(bad)} modules"
              + (f"; EMPTY: {', '.join(bad)}" if bad else ""))
        print(f"  join key (BarTime,k): rows with k>0 (same-second bars kept) up to {same_second} per module; "
              f"Bar disagreements across modules: {bar_disagree}")
        if bar_disagree:
            print("  WARNING: modules were not run on the same bars (CurrentBar differs on joined rows) - "
                  "re-run all QIV_* on one chart load")
        expected = 27
        if len(files) - len(bad) != expected:
            print(f"  warning: {len(files) - len(bad)} of {expected} modules present")


if __name__ == "__main__":
    main()
