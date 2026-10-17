"""Independent re-computation of the full P1 ranking (PROTOCOL sections 3-8) - Channel B extra.

Channel B's own code for: trading dates, D and 15m frames, P&L, costs, daily aggregation, window,
metrics (SR, PSR, DSR, MDD, ...), benchmark and ranking. qibt is used ONLY for
signals.load_rules + signals.rule_positions(rule, <Channel B frames>) = each rule's target positions.

Cost convention: PROTOCOL 4 executes p_t at Open_{t+1}, PROTOCOL 5 charges |p_t - p_{t-1}| at every
change. Variant "literal" charges the change executed at the open of the LAST bar of the data too;
variant "nolast" does not (the engine docstring's convention). Both are compared.
Usage: python -I -B xcheck_ranking.py [--pkl RAW_PKL] [--results DIR] [--costs 1] [--json OUT]
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

argv = sys.argv
results_dir = os.path.join(_cb.REPO, "results")
if "--results" in argv:
    i = argv.index("--results"); results_dir = argv[i + 1]; del argv[i:i + 2]
base = 1.0
if "--costs" in argv:
    i = argv.index("--costs"); base = float(argv[i + 1]); del argv[i:i + 2]
jout = None
if "--json" in argv:
    i = argv.index("--json"); jout = argv[i + 1]; del argv[i:i + 2]
_cb.use_qibt(need_qi_ref=True)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from qibt import signals  # noqa: E402  (positions only)

PV, CPS = 5.0, 2.25
W0, W1 = np.datetime64("2021-01-04"), np.datetime64("2026-02-24")
H1 = (np.datetime64("2021-01-04"), np.datetime64("2023-07-31"))
H2 = (np.datetime64("2023-08-01"), np.datetime64("2026-02-24"))
MIN15 = np.int64(15 * 60 * 1_000_000_000)

m1, src = _cb.load_p1_frame(argv)
print("1-minute source: %s (%d bars)" % (src, len(m1)))
ns = m1["BarTime"].to_numpy().astype("datetime64[ns]").astype(np.int64)
td = _cb.trading_dates_ns(ns)
O, H, L, C, V = (m1[k].to_numpy(dtype=float) for k in ("Open", "High", "Low", "Close", "Volume"))


def frame_from_groups(start):
    end = np.r_[start[1:], len(ns)]
    return pd.DataFrame({
        "TradingDate": td[start].astype("datetime64[ns]"),
        "BarTime": ns[end - 1].astype("datetime64[ns]"),
        "Open": O[start], "High": np.maximum.reduceat(H, start), "Low": np.minimum.reduceat(L, start),
        "Close": C[end - 1], "Volume": np.add.reduceat(V, start), "Bars": (end - start).astype(np.int64)})


assert np.all(np.diff(ns) > 0) and np.all(np.diff(td) >= 0)
d_start = np.r_[0, np.where(np.diff(td) != 0)[0] + 1]
D = frame_from_groups(d_start)
lab = ((ns + MIN15 - 1) // MIN15) * MIN15
q_start = np.r_[0, np.where((np.diff(td) != 0) | (np.diff(lab) != 0))[0] + 1]
Q = frame_from_groups(q_start)
Q["BarTime"] = lab[q_start].astype("datetime64[ns]")
frames = {"D": D, "15m": Q}
print("own frames: D %d bars, 15m %d bars" % (len(D), len(Q)))

# --- frame parity with qibt.data (supports BT14 at P1 scale) ---------------------------------
from qibt import data as qdata  # noqa: E402
qf = qdata.build_frames(m1)
for k in ("D", "15m"):
    a, b = frames[k].reset_index(drop=True), qf[k].reset_index(drop=True)
    same = len(a) == len(b) and all(np.array_equal(a[c].to_numpy(), b[c].to_numpy()) for c in a.columns)
    print("FRAME PARITY %s: own vs qibt.data.build_frames %s (%d vs %d rows)" % (k, "IDENTICAL" if same else "DIFFERENT", len(a), len(b)))

cal = D["TradingDate"].to_numpy()
cal = cal[(cal >= W0) & (cal <= W1)]
ncal = len(cal)


def daily(frame, p, last_cost=True):
    o = frame["Open"].to_numpy()
    n = len(o)
    p = np.asarray(p, dtype=float)
    held = np.zeros(n); gross = np.zeros(n); sides = np.zeros(n)
    for j in range(1, n):
        held[j] = p[j - 1]
        prev = p[j - 2] if j >= 2 else 0.0
        if j <= n - 2:
            gross[j] = p[j - 1] * (o[j + 1] - o[j]) * PV
            sides[j] = abs(p[j - 1] - prev)
        elif last_cost:                               # j == n-1: executed at the last open, no P&L
            sides[j] = abs(p[j - 1] - prev)
    idx = np.searchsorted(cal, frame["TradingDate"].to_numpy())
    ok = (idx < ncal) & (cal[np.minimum(idx, ncal - 1)] == frame["TradingDate"].to_numpy())
    agg = lambda x: np.bincount(idx[ok], weights=np.asarray(x, float)[ok], minlength=ncal)
    heldw = held.copy()
    heldw[n - 1] = 0.0                                # last bar: nothing is held over a P&L interval
    return {"gross": agg(gross), "sides": agg(sides), "changes": agg(sides > 0),
            "exposed": agg(heldw != 0) > 0, "long": agg(heldw > 0), "short": agg(heldw < 0), "bars": agg(np.ones(n)),
            "pnl_long": agg(np.where(heldw > 0, gross, 0)), "pnl_short": agg(np.where(heldw < 0, gross, 0))}


def mets(dly, mult, bench=None):
    net = dly["gross"] - dly["sides"] * CPS * mult
    lst = list(net)
    srd = _cb.sr_daily(lst)
    g3, g4 = _cb.skew_kurt(lst)
    sel = lambda span: [x for x, d in zip(lst, cal) if span[0] <= d <= span[1]]
    out = {"sr": srd * math.sqrt(252) if math.isfinite(srd) else math.nan, "sr_daily": srd,
           "psr": _cb.psr_ref(srd, 0.0, len(lst), g3, g4), "skew": g3, "kurt": g4,
           "total_pnl": math.fsum(lst), "gross_pnl": float(dly["gross"].sum()),
           "total_costs": float((dly["sides"] * CPS * mult).sum()), "mdd": _cb.mdd_ref(lst), "n_days": len(lst),
           "exposure_pct": 100.0 * float(np.mean(dly["exposed"])),
           "long_pct": 100.0 * float(dly["long"].sum() / dly["bars"].sum()),
           "short_pct": 100.0 * float(dly["short"].sum() / dly["bars"].sum()),
           "pnl_long": float(dly["pnl_long"].sum()), "pnl_short": float(dly["pnl_short"].sum()),
           "changes": int(round(dly["changes"].sum())), "sides": int(round(dly["sides"].sum())),
           "sr_h1": _cb.sr_annual(sel(H1)), "sr_h2": _cb.sr_annual(sel(H2))}
    for m in (0.0, 1.0, 2.0):
        x = list(dly["gross"] - dly["sides"] * CPS * m)
        out["sr_cost%g" % m] = _cb.sr_annual(x)
        out["pnl_cost%g" % m] = math.fsum(x)
    if bench is not None:
        out["corr_bh"] = float(np.corrcoef(net, bench)[0, 1]) if np.std(net) > 0 else math.nan
    return out, net


# --- benchmark: +1 executed at the first evaluation open, one entry side, never closed ---------
i0 = int(np.searchsorted(D["TradingDate"].to_numpy(), W0))
pb = np.zeros(len(D)); pb[i0 - 1:] = 1.0                      # decided at the close before -> executed at Open_i0
res = {}
for variant, lastc in (("literal", True), ("nolast", False)):
    bd = daily(D, pb, lastc)
    bmet, bnet = mets(bd, base)
    rows = {}
    pos_cache = {}
    rs = signals.load_rules(os.path.join(_cb.REPO, "backtest", "rules.yaml"))
    for rule in rs.rules:
        if rule.module not in pos_cache:
            pos_cache[rule.module] = signals.rule_positions(rule, frames)[1]
        p = pos_cache[rule.module]
        dl = daily(frames[rule.frame], p, lastc)
        mt, _ = mets(dl, base, bnet)
        mt["frame"] = rule.frame
        last_change = abs(float(p[-2]) - float(p[-3])) if len(p) >= 3 else 0.0
        mt["last_bar_sides"] = last_change
        rows[rule.module] = mt
    srs = [r["sr_daily"] for r in rows.values()]
    m = _cb.mean(srs)
    var_sr = math.fsum((s - m) ** 2 for s in srs) / (len(srs) - 1)
    N = len(rs.rules)
    sr0 = _cb.sr0_ref(var_sr, N)
    for r in rows.values():
        r["dsr"] = _cb.psr_ref(r["sr_daily"], sr0, r["n_days"], r["skew"], r["kurt"])
    # ranking: SR desc; adjacent |dSR| < 0.005 chains form a tie cluster -> DSR desc, then name A->Z
    order = sorted(rows, key=lambda k: (-rows[k]["sr"], k))
    ranked, cluster = [], [order[0]]
    for k in order[1:]:
        if abs(rows[cluster[-1]]["sr"] - rows[k]["sr"]) < 0.005:
            cluster.append(k)
        else:
            ranked += sorted(cluster, key=lambda z: (-rows[z]["dsr"], z)); cluster = [k]
    ranked += sorted(cluster, key=lambda z: (-rows[z]["dsr"], z))
    ranked += sorted(x["module"] for x in rs.not_backtestable)
    res[variant] = {"rows": rows, "bench": bmet, "ranked": ranked, "var_sr": var_sr, "sr0": sr0}
    print("[%s] V[SR per day] = %.9f, N = %d, SR0 per day = %.9f" % (variant, var_sr, N, sr0))
    print("[%s] Channel B DSR (erfc Phi): %s" % (variant, ", ".join(
        "%s %.4e" % (k, rows[k]["dsr"]) for k in order[:6])))

# --- diff against the committed results ------------------------------------------------------
sfx = "" if base == 1 else "_cost%gx" % base
mt = pd.read_csv(os.path.join(results_dir, "metrics_P1%s.csv" % sfx))
rk = pd.read_csv(os.path.join(results_dir, "ranking%s.csv" % sfx))
TOL = {"sr": 1e-6}
cols = ["sr", "sr_daily", "psr", "dsr", "total_pnl", "gross_pnl", "total_costs", "mdd", "n_days", "exposure_pct",
        "long_pct", "short_pct", "pnl_long", "pnl_short", "changes", "sides", "sr_h1", "sr_h2", "sr_cost0",
        "sr_cost1", "sr_cost2", "pnl_cost0", "pnl_cost1", "pnl_cost2", "skew", "kurt", "corr_bh"]
rc = 0
summary = {}
for variant in ("literal", "nolast"):
    R = res[variant]
    diffs = []
    for _, row in mt.iterrows():
        mod = row["module"]
        mine = R["bench"] if mod == "BuyHold" else R["rows"].get(mod)
        if mine is None:
            diffs.append((mod, "missing in Channel B", "", "")); continue
        for col in cols:
            if col not in mine:
                continue
            a, b = float(mine[col]), float(row[col])
            if math.isnan(a) and math.isnan(b):
                continue
            tol = TOL.get(col, 1e-6 * max(1.0, abs(b)))
            if not (abs(a - b) <= tol):
                diffs.append((mod, col, a, b))
    mine_order = R["ranked"]
    theirs = list(rk.sort_values("rank")["module"])
    order_same = mine_order == theirs
    rk_sr = {r.module: r.sr for r in rk.itertuples() if isinstance(r.sr, float) and not math.isnan(r.sr)}
    sr_bad = [(k, R["rows"][k]["sr"], v) for k, v in rk_sr.items() if abs(R["rows"][k]["sr"] - v) > 1e-6]
    print("\n===== variant %s, costs %gx =====" % (variant, base))
    print("rank order identical to %s: %s" % (os.path.basename("ranking%s.csv" % sfx), order_same))
    if not order_same:
        for i, (a, b) in enumerate(zip(mine_order, theirs), 1):
            print("  rank %2d: Channel B %-18s results %-18s %s" % (i, a, b, "" if a == b else "<-- differs"))
    print("ranking.csv SR differences > 1e-6: %d %s" % (len(sr_bad), sr_bad))
    print("metrics_P1%s.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): %d" % (sfx, len(diffs)))
    for d in diffs:
        print("  %-18s %-13s Channel B %r   results %r" % d)
    summary[variant] = {"order_same": order_same, "n_metric_diffs": len(diffs), "n_sr_diffs": len(sr_bad)}
    if variant == "literal" and (not order_same or sr_bad):
        rc = 1
print("\nrules whose last frame bar executes a position change (cost charged only in 'literal'): %s" % (
    [(k, r["frame"], r["last_bar_sides"]) for k, r in res["literal"]["rows"].items() if r["last_bar_sides"] > 0],))
print("\nChannel B ranking (literal): " + ", ".join("%d %s %.6f" % (i, k, res["literal"]["rows"][k]["sr"]) if k in res["literal"]["rows"]
                                         else "%d %s" % (i, k) for i, k in enumerate(res["literal"]["ranked"], 1)))
if jout:
    with open(jout, "w") as fh:
        json.dump({v: {"ranked": res[v]["ranked"], "sr": {k: r["sr"] for k, r in res[v]["rows"].items()},
                       "dsr": {k: r["dsr"] for k, r in res[v]["rows"].items()}} for v in res}, fh, indent=1)
print("summary: %s" % summary)
sys.exit(rc)
