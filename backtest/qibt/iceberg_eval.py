"""iceberg_eval.py - recall / false-alarm evaluation of the iceberg engine on simulated sessions (I3).

Educational research only. Not financial advice.

A planted iceberg is *detected* when a FLAG record has the same side and price and a seq inside the
episode's [start_seq, end_seq]. A decoy level is a *false alarm* under the same match. FLAGs that match
no labelled level (noise levels) are reported as `unlabelled_flags`.

    python -I -m qibt.iceberg_eval --sessions 200 --seed 20261028 [--hidden-ratio X --min-refills N ...]
    python -I -m qibt.iceberg_eval --dir DIR                      (DIR from qibt.booksim --out)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from .booksim import KINDS, simulate
from .iceberg import read_stream_csv, run_stream

EPS = 1e-9


def _flags(records: Sequence[str]) -> List[Tuple[str, float, int]]:
    out = []
    for r in records:
        f = r.split(",")
        if f[0] == "FLAG":
            out.append((f[1], float(f[2]), int(f[3])))
    return out


def evaluate(sessions, **params) -> Dict:
    """sessions: iterable of (rows, truth). Returns recall, false_alarm_rate and per-kind counts."""
    per_kind = {k: {"levels": 0, "flagged": 0} for k in KINDS}
    unlabelled = 0
    for rows, truth in sessions:
        flags = _flags(run_stream(rows, **params))
        used = set()
        for t in truth:
            hit = False
            for i, (side, price, seq) in enumerate(flags):
                if (side == t["side"] and abs(price - t["price"]) < EPS
                        and t["start_seq"] <= seq <= t["end_seq"]):
                    hit = True
                    used.add(i)
            per_kind[t["kind"]]["levels"] += 1
            per_kind[t["kind"]]["flagged"] += 1 if hit else 0
        unlabelled += len(flags) - len(used)
    n_ice = per_kind["iceberg"]["levels"]
    n_dec = sum(per_kind[k]["levels"] for k in KINDS if k != "iceberg")
    f_dec = sum(per_kind[k]["flagged"] for k in KINDS if k != "iceberg")
    return {
        "recall": (per_kind["iceberg"]["flagged"] / n_ice) if n_ice else float("nan"),
        "false_alarm_rate": (f_dec / n_dec) if n_dec else float("nan"),
        "n_icebergs": n_ice,
        "n_decoys": n_dec,
        "per_kind": per_kind,
        "unlabelled_flags": unlabelled,
    }


def load_dir(path) -> List[Tuple[list, list]]:
    d = Path(path)
    truth = json.loads((d / "truth.json").read_text())
    return [(read_stream_csv(d / (name + ".csv")), truth[name]) for name in sorted(truth)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="qibt.iceberg_eval")
    ap.add_argument("--sessions", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261028)
    ap.add_argument("--dir", default=None, help="read session_*.csv + truth.json instead of simulating")
    ap.add_argument("--hidden-ratio", type=float, default=2.0)
    ap.add_argument("--min-refills", type=int, default=2)
    ap.add_argument("--min-volume", type=int, default=20)
    ap.add_argument("--min-refill-size", type=int, default=1)
    a = ap.parse_args(argv)
    sessions = load_dir(a.dir) if a.dir else simulate(a.sessions, a.seed)
    res = evaluate(sessions, hidden_ratio=a.hidden_ratio, min_refills=a.min_refills,
                   min_volume=a.min_volume, min_refill_size=a.min_refill_size)
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
