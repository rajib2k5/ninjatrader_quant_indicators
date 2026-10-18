#!/usr/bin/env python3
"""relabel.py - rename the indicators QI_<Module> -> QI_<NN>_<Module> in rank order.

Usage (from the repo root):
    python -I backtest/relabel.py results/ranking.csv            # dry run: prints the plan
    python -I backtest/relabel.py results/ranking.csv --apply    # renames files and rewrites text

ranking.csv must have columns `rank` and `module` (module = name without the QI_ prefix, as in
backtest/rules.yaml). Writes backtest/names.json:
    {"IBS": {"rank": 1, "qi": "QI_01_IBS", "qs": "QS_01_IBS", "qiv": "QIV_01_IBS",
             "display": "QI 01 IBS"}, ...}

Rewrites, with word-boundary matching (so QI_RSI2 never touches QI_RSI14):
  - indicators/*.cs: class name, Name = "...", DisplayName "QI <Module>" -> "QI <NN> <Module>"
    (each file is renamed with `git mv` so history follows);
  - the text files in REWRITE_GLOBS (tests, probes, README) for QI_/QS_/QIV_ identifiers.
Never rewritten: validation evidence files (ledgers, channel-*.md, addenda.md, runtime notes) -
they record what was audited under the names of the time; docs/CONVENTIONS.md (historical map).
Strategies and the validation harness are regenerated afterwards by their generators:
    python -I backtest/gen_strategies.py --names backtest/names.json
    python -I validation/probes/gen_harness.py indicators validation/harness
The script is idempotent: modules already carrying their rank prefix are left alone.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REWRITE_GLOBS = [
    "validation/pytests/*.py",
    "validation/probes/*.py",
    "backtest/tests/*.py",
    "README.md",
]


def load_ranking(path: Path) -> dict:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "rank" not in rows[0] or "module" not in rows[0]:
        raise SystemExit("ranking.csv needs columns rank,module")
    ranks = sorted(int(r["rank"]) for r in rows)
    if ranks != list(range(1, len(rows) + 1)):
        raise SystemExit(f"ranks must be 1..{len(rows)} with no gaps or ties, got {ranks}")
    names = {}
    for r in rows:
        m, nn = r["module"].strip(), int(r["rank"])
        names[m] = {"rank": nn, "qi": f"QI_{nn:02d}_{m}", "qs": f"QS_{nn:02d}_{m}",
                    "qiv": f"QIV_{nn:02d}_{m}", "display": f"QI {nn:02d} {m}"}
    return names


def substitutions(names: dict):
    subs = []
    for m, n in names.items():
        for prefix, new in (("QIV_", n["qiv"]), ("QS_", n["qs"]), ("QI_", n["qi"])):
            subs.append((re.compile(rf"\b{prefix}{re.escape(m)}\b"), new))
        subs.append((re.compile(rf'"QI {re.escape(m)}"'), f'"{n["display"]}"'))
    return subs


def rewrite(text: str, subs) -> str:
    for rx, new in subs:
        text = rx.sub(new, text)
    return text


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    apply = "--apply" in sys.argv
    names = load_ranking(ROOT / sys.argv[1] if not Path(sys.argv[1]).is_absolute() else Path(sys.argv[1]))
    subs = substitutions(names)
    plan = []
    for m, n in sorted(names.items(), key=lambda kv: kv[1]["rank"]):
        src, dst = ROOT / "indicators" / f"QI_{m}.cs", ROOT / "indicators" / f"{n['qi']}.cs"
        if dst.exists():
            plan.append(f"  keep   {dst.name} (already relabelled)")
        elif src.exists():
            plan.append(f"  rename {src.name} -> {dst.name}")
        else:
            raise SystemExit(f"neither {src.name} nor {dst.name} exists")
    print("plan:"); print("\n".join(plan))
    if not apply:
        print("dry run - pass --apply to execute"); return

    (ROOT / "backtest" / "names.json").write_text(json.dumps(names, indent=2), encoding="utf-8")
    for m, n in names.items():
        src, dst = ROOT / "indicators" / f"QI_{m}.cs", ROOT / "indicators" / f"{n['qi']}.cs"
        if src.exists() and not dst.exists():
            subprocess.run(["git", "mv", str(src), str(dst)], cwd=ROOT, check=True)
    changed = 0
    files = sorted(set((ROOT / "indicators").glob("QI_*.cs")))
    for g in REWRITE_GLOBS:
        files += sorted(ROOT.glob(g))
    for f in files:
        old = f.read_text(encoding="utf-8")
        new = rewrite(old, subs)
        if new != old:
            f.write_text(new, encoding="utf-8"); changed += 1
    print(f"names.json written; {changed} files rewritten")


if __name__ == "__main__":
    main()
