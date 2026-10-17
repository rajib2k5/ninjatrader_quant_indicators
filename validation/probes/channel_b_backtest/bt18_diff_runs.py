"""BT18: the ranking is a deterministic function of P1, rules.yaml and PROTOCOL - two full CLI runs
must give the identical rank order and SRs to 1e-9 (and, stronger, byte-identical CSVs).

Usage: python -I -B bt18_diff_runs.py DIR_A DIR_B
Compares every CSV byte-for-byte; ranking*.csv rank order exactly; every numeric cell of
metrics/ranking/daily CSVs to 1e-9 abs; REPORT*.md line-by-line except the two lines that carry the
run's wall-clock (Run (local time), Wall time) and the cache state.
"""
from __future__ import annotations

import filecmp
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402
import pandas as pd  # noqa: E402

a, b = sys.argv[1], sys.argv[2]
c = _cb.Checker("BT18 run-to-run diff: %s vs %s" % (a, b))
fa = sorted(os.path.basename(p) for p in glob.glob(os.path.join(a, "*")))
fb = sorted(os.path.basename(p) for p in glob.glob(os.path.join(b, "*")))
c.check("same file set", fa == fb, "A=%s B=%s" % (fa, fb))
need = [n for n in fa if n.startswith("ranking") and n.endswith(".csv")]
c.check("both runs produced a ranking CSV and a metrics CSV (empty output = PROBE_INVALID, never a pass)",
        bool(need) and any(n.startswith("metrics_") for n in fa) and set(fa) <= set(fb), "A=%s" % (fa,))
for name in fa:
    if name not in fb:
        continue
    pa, pb = os.path.join(a, name), os.path.join(b, name)
    if name.endswith(".csv"):
        c.check("%s byte-identical" % name, filecmp.cmp(pa, pb, shallow=False))
        da, db = pd.read_csv(pa), pd.read_csv(pb)
        ok = list(da.columns) == list(db.columns) and len(da) == len(db)
        worst = 0.0
        if ok:
            for col in da.columns:
                if pd.api.types.is_numeric_dtype(da[col]) and pd.api.types.is_numeric_dtype(db[col]):
                    for x, y in zip(da[col], db[col]):
                        if (isinstance(x, float) and math.isnan(x)) and (isinstance(y, float) and math.isnan(y)):
                            continue
                        worst = max(worst, abs(float(x) - float(y)))
                else:
                    ok = ok and da[col].astype(str).tolist() == db[col].astype(str).tolist()
        c.check("%s numeric cells equal to 1e-9 (worst %.3g)" % (name, worst), ok and worst <= 1e-9)
        if name.startswith("ranking"):
            c.check("%s rank order identical" % name, da["module"].tolist() == db["module"].tolist(),
                    "A=%s | B=%s" % (da["module"].tolist()[:6], db["module"].tolist()[:6]))
    elif name.endswith(".md"):
        skip = ("| Run (local time) |", "| Wall time |", "| Dataset |")
        la = [l for l in open(pa, encoding="utf-8").read().splitlines() if not l.startswith(skip)]
        lb = [l for l in open(pb, encoding="utf-8").read().splitlines() if not l.startswith(skip)]
        diff = [(i, x, y) for i, (x, y) in enumerate(zip(la, lb)) if x != y]
        c.check("%s identical except run-time/wall-time/dataset lines" % name, la == lb and not diff,
                "first diffs: %s" % (diff[:3],))
sys.exit(c.close())
