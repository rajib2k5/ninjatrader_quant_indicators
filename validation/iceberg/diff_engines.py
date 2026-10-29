"""diff_engines.py - claim I2: the C# IcebergEngine and the Python reference emit identical records.

Both engines were written independently from validation/iceberg/spec.md. This script feeds the same
event streams to both and diffs the FLAG/FINAL records (price, conf and median within 1e-4, every other
field exact, same order).

Streams: the 200 simulated sessions of qibt.booksim (seed 20261028) plus random "fuzz" streams that
hit the edge branches the simulator rarely produces (size 0, unknown or crossed bid/ask, resets, prices
off the level, joins after decreases). Each stream runs at the default parameters and at a loose set
that makes flags common.

Falsifier: --falsify runs the C# side with HiddenRatio 1.9 against Python at 2.0; the diff must be
non-empty, otherwise this check cannot see a real difference.

Usage (repo root, after `bash validation/iceberg/harness/build_harness.sh`):
    python -I validation/iceberg/diff_engines.py [--falsify] [--exe PATH]
Exit code 0 = no differences (or, with --falsify, differences found).
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "backtest"))

from qibt import booksim, iceberg  # noqa: E402

DEFAULT = {"hidden_ratio": 2.0, "min_refills": 2, "min_volume": 20, "min_refill_size": 1}
LOOSE = {"hidden_ratio": 1.0, "min_refills": 1, "min_volume": 5, "min_refill_size": 1}
FLOAT_FIELDS = {"FLAG": {2, 7}, "FINAL": {2, 9, 11}}


def fuzz_stream(rng: random.Random, n: int = 400):
    rows, seq = [], 0
    grid = [5000.0 + 0.25 * k for k in range(-3, 4)]
    for _ in range(n):
        seq += 1
        u = rng.random()
        if u < 0.02:
            rows.append((seq, "R", None, None, None, None))
        elif u < 0.30:
            rows.append((seq, "B", rng.choice(grid[:4]), rng.choice([0, 1, 2, 5, 8, 10, 12, 20]), None, None))
        elif u < 0.55:
            rows.append((seq, "A", rng.choice(grid[3:]), rng.choice([0, 1, 2, 5, 8, 10, 12, 20]), None, None))
        else:
            b = None if rng.random() < 0.05 else rng.choice(grid[:4])
            a = None if rng.random() < 0.05 else rng.choice(grid[3:])
            rows.append((seq, "T", rng.choice(grid), rng.randint(1, 12), b, a))
    return rows


def run_cs(exe: Path, path: Path, p: dict) -> list:
    args = [str(exe), str(path), "--hidden-ratio", repr(p["hidden_ratio"]), "--min-refills", str(p["min_refills"]),
            "--min-volume", str(p["min_volume"]), "--min-refill-size", str(p["min_refill_size"])]
    out = subprocess.run(args, capture_output=True, text=True, timeout=120, check=True).stdout
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def same(a: str, b: str) -> bool:
    fa, fb = a.split(","), b.split(",")
    if len(fa) != len(fb) or fa[0] != fb[0]:
        return False
    floats = FLOAT_FIELDS.get(fa[0], set())
    for i, (x, y) in enumerate(zip(fa, fb)):
        if i in floats:
            if abs(float(x) - float(y)) > 1e-4:
                return False
        elif x != y:
            return False
    return True


def diff(py: list, cs: list) -> list:
    bad = [(i, x, y) for i, (x, y) in enumerate(zip(py, cs)) if not same(x, y)]
    if len(py) != len(cs):
        bad.append((min(len(py), len(cs)), f"<{len(py)} records>", f"<{len(cs)} records>"))
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=str(HERE / "harness" / "_out" / "IcebergHarness.exe"))
    ap.add_argument("--falsify", action="store_true")
    ap.add_argument("--fuzz", type=int, default=300)
    a = ap.parse_args(argv)
    exe = Path(a.exe)
    if not exe.exists():
        print(f"missing {exe} - run validation/iceberg/harness/build_harness.sh"); return 2

    streams = [(f"sim_{i:03d}", rows) for i, (rows, _t) in enumerate(booksim.simulate(200, 20261028))]
    frng = random.Random(7)
    streams += [(f"fuzz_{i:03d}", fuzz_stream(frng)) for i in range(a.fuzz)]
    streams += [(p.stem, iceberg.read_stream_csv(p)) for p in sorted((HERE / "harness" / "streams").glob("*.csv"))]

    summary = {"streams": len(streams), "runs": 0, "records": 0, "flags": 0, "mismatched_runs": 0, "examples": []}
    with tempfile.TemporaryDirectory() as td:
        for name, rows in streams:
            path = Path(td) / f"{name}.csv"
            iceberg.write_stream_csv(path, rows)
            for pname, p in (("default", DEFAULT), ("loose", LOOSE)):
                py = iceberg.run_stream(rows, **p)
                cs_p = dict(p, hidden_ratio=p["hidden_ratio"] - 0.1) if a.falsify else p
                cs = run_cs(exe, path, cs_p)
                summary["runs"] += 1
                summary["records"] += len(py)
                summary["flags"] += sum(r.startswith("FLAG") for r in py)
                d = diff(py, cs)
                if d:
                    summary["mismatched_runs"] += 1
                    if len(summary["examples"]) < 5:
                        summary["examples"].append({"stream": name, "params": pname, "first": d[0]})
    print(json.dumps(summary, indent=1))
    ok = summary["mismatched_runs"] > 0 if a.falsify else summary["mismatched_runs"] == 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
