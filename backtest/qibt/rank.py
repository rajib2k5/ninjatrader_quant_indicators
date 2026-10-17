"""rank.py - PROTOCOL section 8: order the backtestable rules, then the non-backtestable modules.

1. Rules with a finite SR (P1, base costs, full window): SR descending. Ties (|dSR| < 0.005):
   a tie cluster is a maximal run of that order whose ADJACENT SRs differ by < 0.005; inside a
   cluster the order is DSR descending (NaN last), then module name A->Z. DSR is compared on its
   log (row key "dsr_log" when present), so DSRs that underflow to 0.0 in floating point still
   decide the tie whenever they differ.
2. Rules whose SR is undefined (zero variance): after all finite ones, A->Z.
3. Pending rules (value not computable yet): no rank.
4. Non-backtestable modules: the last numbers (n_backtestable + 1 ...), A->Z.
"""
from __future__ import annotations

import math

TIE_SR = 0.005


def _finite(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def order_rules(rows, tie=TIE_SR):
    """rows: dicts with module, sr, dsr. Returns the rows in rank order (finite SR first)."""
    fin = sorted((r for r in rows if _finite(r["sr"])), key=lambda r: (-r["sr"], r["module"]))
    nan = sorted((r for r in rows if not _finite(r["sr"])), key=lambda r: r["module"])
    out, cluster = [], []
    for r in fin:
        if cluster and abs(cluster[-1]["sr"] - r["sr"]) >= tie:
            out.extend(_resolve(cluster))
            cluster = []
        cluster.append(r)
    out.extend(_resolve(cluster))
    return out + nan


def dsr_key(r):
    """log DSR used for tie-breaking: dsr_log if finite, else log(dsr) (-inf for 0.0), else None."""
    v = r.get("dsr_log")
    if _finite(v):
        return float(v)
    d = r.get("dsr")
    if _finite(d):
        return math.log(d) if d > 0 else -math.inf
    return None


def _resolve(cluster):
    def key(r):
        k = dsr_key(r)
        return (1, 0.0, r["module"]) if k is None else (0, -k, r["module"])
    return sorted(cluster, key=key)


def rank_table(rule_rows, not_backtestable, n_backtestable=None):
    """Full ranking: list of dicts (rank, module, status, sr, dsr, ...) for relabel.

    rule_rows: dicts with module, status ('ok' | 'pending'), sr, dsr (+ any extra keys, kept).
    n_backtestable: number of backtestable rules (defaults to len(rule_rows))."""
    n_bt = len(rule_rows) if n_backtestable is None else n_backtestable
    ok = [r for r in rule_rows if r.get("status") == "ok"]
    pending = sorted((r for r in rule_rows if r.get("status") != "ok"), key=lambda r: r["module"])
    table = []
    for i, r in enumerate(order_rules(ok), start=1):
        table.append(dict(r, rank=i))
    for r in pending:
        table.append(dict(r, rank=None))
    for j, nb in enumerate(sorted(not_backtestable, key=lambda x: x["module"]), start=1):
        table.append(dict(module=nb["module"], status="not_backtestable", sr=math.nan,
                          dsr=math.nan, reason=nb.get("reason", ""), rank=n_bt + j))
    for r in table:
        if r["rank"] is not None:
            nn = "%02d" % r["rank"]
            r["qi"] = "QI_%s_%s" % (nn, r["module"])
            r["qs"] = "QS_%s_%s" % (nn, r["module"])
            r["qiv"] = "QIV_%s_%s" % (nn, r["module"])
        else:
            r["qi"] = r["qs"] = r["qiv"] = ""
    return table
