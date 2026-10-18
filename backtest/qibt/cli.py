"""cli.py - run the pre-registered backtest and write results.

    python -I -m qibt.cli run --dataset P1 --costs 1 --out results

(`python -I` drops the current directory from sys.path, so qibt must be installed - see
backtest/README.md - or run with `python -m qibt.cli` from backtest/.)

Outputs (suffix "" at costs 1, "_cost<m>x" otherwise; dataset tag P1 or the CSV stem):
    metrics_<DS><sfx>.csv    one row per rule + the buy-and-hold benchmark row
    daily_pnl_<DS><sfx>.csv  net daily USD P&L per rule (window calendar) + BuyHold
    ranking<sfx>.csv         P1 only (ranking_<DS><sfx>.csv for other datasets)
    REPORT<sfx>.md           P1 only (REPORT_<DS><sfx>.md otherwise)
    equity_<DS><sfx>.png     only if matplotlib imports
"""
from __future__ import annotations

import argparse
import datetime as _dt
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__, bootstrap, data, engine, metrics, rank, signals

BENCH = "BuyHold"
METRIC_COLUMNS = [
    "module", "frame", "value", "status", "reason", "sr", "sr_daily", "psr", "dsr", "dsr_log", "total_pnl",
    "gross_pnl", "total_costs", "mdd", "n_days", "exposure_pct", "long_pct", "short_pct",
    "pnl_long", "pnl_short", "changes", "sides", "sr_h1", "sr_h2", "sr_cost0", "sr_cost1",
    "sr_cost2", "pnl_cost0", "pnl_cost1", "pnl_cost2", "skew", "kurt", "corr_bh",
]


def _mask(dates, span):
    return (dates >= span[0]) & (dates <= span[1])


def daily_metrics(dr, bench_net, base_mult, halves):
    """Metric dict of one DailyResult (DSR filled in later, it needs all rules)."""
    net = dr.net(base_mult)
    n = len(net)
    sk, ku = metrics.moments(net)
    srd = metrics.sharpe_daily(net)
    out = {
        "sr": metrics.sharpe(net), "sr_daily": srd, "psr": metrics.psr(srd, 0.0, n, sk, ku),
        "dsr": math.nan, "dsr_log": math.nan, "total_pnl": float(net.sum()), "gross_pnl": float(dr.gross.sum()),
        "total_costs": float(dr.cost(base_mult).sum()), "mdd": metrics.max_drawdown(net),
        "n_days": n, "exposure_pct": 100.0 * float(np.mean(dr.exposed)) if n else math.nan,
        "long_pct": 100.0 * float(dr.long_bars.sum() / dr.bars.sum()) if dr.bars.sum() else math.nan,
        "short_pct": 100.0 * float(dr.short_bars.sum() / dr.bars.sum()) if dr.bars.sum() else math.nan,
        "pnl_long": float(dr.pnl_long.sum()), "pnl_short": float(dr.pnl_short.sum()),
        "changes": int(round(dr.changes.sum())), "sides": int(round(dr.sides.sum())),
        "skew": sk, "kurt": ku,
        "corr_bh": metrics.correlation(net, bench_net) if bench_net is not None else math.nan,
    }
    for name, span in halves.items():
        out["sr_" + name.lower()] = metrics.sharpe(net[_mask(dr.dates, span)])
    for m in engine.COST_MULTS:
        k = "%g" % m
        out["sr_cost" + k] = metrics.sharpe(dr.net(m))
        out["pnl_cost" + k] = float(dr.net(m).sum())
    return out


def run_pipeline(m1, ruleset, base_mult=1.0, window=engine.EVAL_WINDOW, halves=None,
                 n_trials=None, var_sr=None, roll_hour=data.ROLL_HOUR, halt=data.HALT,
                 close_mode=data.DEFAULT_CLOSE_MODE, verbose=False):
    """Everything except file output. Returns a dict (frames, results, metrics, ranking, ...)."""
    halves = engine.HALVES if halves is None else halves
    frames = data.build_frames(m1, roll_hour, halt, close_mode)
    cal = engine.window_calendar(frames["D"], window)
    if len(cal) == 0:
        raise ValueError("no trading dates inside the window %s" % (window,))
    bench_pos = engine.buy_and_hold_positions(frames["D"], window)
    bench = engine.run_positions(frames["D"], bench_pos, cal)
    bench_net = bench.net(base_mult)

    results, rows = {}, []
    for rule in ruleset.rules:
        t0 = time.time()
        row = {"module": rule.module, "frame": rule.frame, "value": rule.value}
        try:
            values, pos = signals.rule_positions(rule, frames)
        except signals.PendingValue as e:
            row.update(status="pending", reason=str(e))
            rows.append(row)
            results[rule.module] = {"status": "pending", "reason": str(e)}
            if verbose:
                print("  %-18s pending: %s" % (rule.module, e))
            continue
        dr = engine.run_positions(frames[rule.frame], pos, cal)
        row.update(status="ok", reason="")
        row.update(daily_metrics(dr, bench_net, base_mult, halves))
        rows.append(row)
        results[rule.module] = {"status": "ok", "values": values, "positions": pos, "daily": dr,
                                "seconds": time.time() - t0}
        if verbose:
            print("  %-18s %-4s SR %7.3f  net %10.2f  (%.1fs)"
                  % (rule.module, rule.frame, row["sr"], row["total_pnl"], time.time() - t0))

    n_trials = len(ruleset.rules) if n_trials is None else n_trials
    srs = [r["sr_daily"] for r in rows if r["status"] == "ok"]
    v = metrics.sample_variance(srs) if var_sr is None else float(var_sr)
    sr0 = metrics.expected_max_sr(v, n_trials) if n_trials >= 2 else math.nan
    for r in rows:
        if r["status"] == "ok":
            r["dsr"] = metrics.psr(r["sr_daily"], sr0, r["n_days"], r["skew"], r["kurt"])
            r["dsr_log"] = metrics.log_psr(r["sr_daily"], sr0, r["n_days"], r["skew"], r["kurt"])

    brow = {"module": BENCH, "frame": "D", "value": "buy_and_hold", "status": "benchmark", "reason": ""}
    brow.update(daily_metrics(bench, bench_net, base_mult, halves))
    mtab = pd.DataFrame(rows + [brow]).reindex(columns=METRIC_COLUMNS)

    ranking = rank.rank_table([{k: r.get(k) for k in ("module", "status", "sr", "dsr", "dsr_log", "psr", "frame", "value")}
                               for r in rows], ruleset.not_backtestable, len(ruleset.rules))
    daily = pd.DataFrame({"date": cal.strftime("%Y-%m-%d")})
    for rule in ruleset.rules:
        res = results[rule.module]
        if res["status"] == "ok":
            daily[rule.module] = res["daily"].net(base_mult)
    daily[BENCH] = bench_net
    return {
        "frames": frames, "calendar": cal, "results": results, "benchmark": bench,
        "benchmark_positions": bench_pos, "metrics": mtab, "ranking": ranking, "daily": daily,
        "var_sr": v, "n_trials": n_trials, "sr0": sr0, "base_mult": base_mult, "window": window,
        "halves": halves, "session_report": data.session_report(frames["D"]),
        "close_mode": close_mode, "close_report": {"all": data.close_report(frames["D"]),
                                                   "window": data.close_report(frames["D"], window)},
    }


# ============================================================================================
# output
# ============================================================================================
def _suffix(mult):
    return "" if mult == 1 else "_cost%gx" % mult


def _f(x, nd=3):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    return ("%%.%df" % nd) % x


def _p(x):
    """Probability: 3 decimals, scientific below 0.001 (DSR/PSR often underflow the 3 decimals)."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    return "%.3f" % x if x >= 1e-3 or x == 0 else "%.2e" % x


def _usd(x):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    return "{:,.0f}".format(x)


CLOSE_LABEL = {"settle": "settle (A1: NinjaTrader settlement close)", "last": "last (v1: 16:00 last trade)",
               "1500": "1500 (15:00 CT one-minute close)"}


def _branches(rep):
    src = ", ".join("%s %d" % (k, rep["source"].get(k, 0)) for k in ("settle", "1500", "last") if rep["source"].get(k))
    why = ", ".join("%s %d" % kv for kv in sorted(rep["fallback_reason"].items()))
    return "%s of %d%s" % (src, rep["dates"], (" (fallback: %s)" % why) if why else "")


def render_report(res, dataset, meta):
    m = res["metrics"].set_index("module")
    sr_rep = res["session_report"]
    lines = [
        "# Backtest report - %s, costs %gx, D close %s" % (dataset, res["base_mult"], CLOSE_LABEL[res["close_mode"]]),
        "",
        "> Educational research only. Not financial advice. A backtest describes how a fixed rule "
        "would have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.",
        "",
        "Protocol: backtest/PROTOCOL.md (rules.yaml version %s, frozen %s). Ranks order the rules; "
        "they are not significance-tested differences unless DSR says so." % (meta["rules_version"], meta["rules_frozen"]),
        "",
        "| Item | Value |", "|---|---|",
        "| Run (local time) | %s |" % meta["run_at"],
        "| qibt version | %s |" % __version__,
        "| Dataset | %s (%s) |" % (dataset, meta["source"]),
        "| 1-minute bars | %s (%s -> %s) |" % ("{:,}".format(meta["bars"]), meta["first_bar"], meta["last_bar"]),
        "| Trading dates in data / in window | %d / %d |" % (sr_rep["trading_dates"], len(res["calendar"])),
        "| Evaluation window | %s -> %s (H1 %s -> %s, H2 %s -> %s) |" % (
            res["window"][0].date(), res["window"][1].date(),
            res["halves"]["H1"][0].date(), res["halves"]["H1"][1].date(),
            res["halves"]["H2"][0].date(), res["halves"]["H2"][1].date()),
        "| D-frame close | %s; window dates by branch: %s |" % (CLOSE_LABEL[res["close_mode"]], _branches(res["close_report"]["window"])),
        "| D-frame close, all dates | %s |" % _branches(res["close_report"]["all"]),
        "| Cost per side | USD %.2f x %g = USD %.2f |" % (engine.COST_PER_SIDE, res["base_mult"], engine.COST_PER_SIDE * res["base_mult"]),
        "| DSR trials N / V[SR per day] / SR0 per day | %d / %s / %s |" % (res["n_trials"], _f(res["var_sr"], 6), _f(res["sr0"], 4)),
        "| Missing weekdays (holidays + gaps) / longest run | %d / %d |" % (sr_rep["missing_weekdays"], sr_rep["max_consecutive_missing_weekdays"]),
        "| Sessions with < 300 one-minute bars | %s |" % (", ".join("%s (%d)" % x for x in sr_rep["short_session_list"]) or "none"),
        "| Wall time | %.1f s |" % meta["wall"],
        "",
        "## Ranking (SR on %s at %gx costs, full window)" % (dataset, res["base_mult"]),
        "",
        "| Rank | Module | Frame | SR | DSR | PSR(0) | Total P&L USD | MDD USD | Exposure % | Trades | SR H1 | SR H2 | SR 0x | SR 2x | Corr B&H |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in res["ranking"]:
        mod = r["module"]
        rk = "" if r["rank"] is None else str(r["rank"])
        if r["status"] == "ok":
            x = m.loc[mod]
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %d | %s | %s | %s | %s | %s |" % (
                rk, mod, x["frame"], _f(x["sr"]), _p(x["dsr"]), _p(x["psr"]), _usd(x["total_pnl"]),
                _usd(x["mdd"]), _f(x["exposure_pct"], 1), int(x["changes"]), _f(x["sr_h1"]), _f(x["sr_h2"]),
                _f(x["sr_cost0"]), _f(x["sr_cost2"]), _f(x["corr_bh"], 2)))
        elif r["status"] == "pending":
            lines.append("| %s | %s | %s | pending | | | | | | | | | | | |" % (rk, mod, m.loc[mod, "frame"]))
        else:
            lines.append("| %s | %s | - | not backtestable | | | | | | | | | | | |" % (rk, mod))
    b = m.loc[BENCH]
    lines.append("| - | **Buy & hold (benchmark)** | D | %s | - | %s | %s | %s | %s | %d | %s | %s | %s | %s | 1.00 |" % (
        _f(b["sr"]), _p(b["psr"]), _usd(b["total_pnl"]), _usd(b["mdd"]), _f(b["exposure_pct"], 1),
        int(b["changes"]), _f(b["sr_h1"]), _f(b["sr_h2"]), _f(b["sr_cost0"]), _f(b["sr_cost2"])))
    pend = [r for r in res["ranking"] if r["status"] == "pending"]
    if pend:
        lines += ["", "**Ranking incomplete:** %d rule(s) pending; DSR uses V[SR] of the %d computed rules "
                  "with N = %d." % (len(pend), sum(1 for r in res["ranking"] if r["status"] == "ok"), res["n_trials"]),
                  ""]
        for r in pend:
            lines.append("- %s: %s" % (r["module"], m.loc[r["module"], "reason"]))
    nb = [r for r in res["ranking"] if r["status"] == "not_backtestable"]
    if nb:
        lines += ["", "Not backtestable (last numbers, A->Z): " + "; ".join(
            "%s - %s" % (r["module"], r.get("reason", "")) for r in nb)]
    lines += ["", "Columns: SR annualised (sqrt 252, ddof 1) on daily net USD P&L; PSR(0) and DSR on the per-day SR; "
              "MDD of cumulative net P&L from 0; Exposure = %% of window days with a non-zero held position; "
              "Trades = position changes executed in the window; SR 0x/2x = same positions at 0x/2x costs; "
              "Corr B&H = Pearson correlation of daily net P&L with the benchmark.", ""]
    return "\n".join(lines)


def write_outputs(res, out_dir, dataset, meta):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sfx = _suffix(res["base_mult"])
    tag = dataset
    paths = {}
    paths["metrics"] = out / ("metrics_%s%s.csv" % (tag, sfx))
    res["metrics"].to_csv(paths["metrics"], index=False)
    paths["daily"] = out / ("daily_pnl_%s%s.csv" % (tag, sfx))
    res["daily"].to_csv(paths["daily"], index=False)
    rk_name = ("ranking%s.csv" % sfx) if dataset == "P1" else ("ranking_%s%s.csv" % (tag, sfx))
    paths["ranking"] = out / rk_name
    cols = ["rank", "module", "status", "sr", "dsr", "dsr_log", "psr", "frame", "value", "qi", "qs", "qiv"]
    rk = pd.DataFrame(res["ranking"]).reindex(columns=cols)
    rk["rank"] = rk["rank"].astype("Int64")
    rk.to_csv(paths["ranking"], index=False)
    rep_name = ("REPORT%s.md" % sfx) if dataset == "P1" else ("REPORT_%s%s.md" % (tag, sfx))
    paths["report"] = out / rep_name
    paths["report"].write_text(render_report(res, dataset, meta), encoding="utf-8")
    png = _plot_equity(res, out / ("equity_%s%s.png" % (tag, sfx)))
    if png:
        paths["equity"] = png
    return paths


def _plot_equity(res, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    d = res["daily"]
    x = pd.to_datetime(d["date"])
    fig, ax = plt.subplots(figsize=(11, 6))
    for c in d.columns[1:]:
        ax.plot(x, d[c].cumsum(), lw=1.6 if c == BENCH else 0.8, color="black" if c == BENCH else None,
                label=c if c == BENCH else None)
    ax.set_ylabel("cumulative net P&L, USD (1 MES)")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


# ============================================================================================
# SENSITIVITY.md: v1 / A1 / 15:00 close side by side
# ============================================================================================
VARIANTS = [("v1", "v1_last_trade", "16:00 last trade (v1, pre-registered section 3)"),
            ("A1", ".", "settlement close (A1, PROTOCOL section 9; the ranking)"),
            ("15:00", "close_1500", "15:00 CT one-minute close")]
COSTS_SFX = [("0x", "_cost0x"), ("1x", ""), ("2x", "_cost2x")]


def _variant_tables(folder, tag="P1"):
    out = {}
    for lab, sfx in COSTS_SFX:
        m = pd.read_csv(Path(folder) / ("metrics_%s%s.csv" % (tag, sfx))).set_index("module")
        rk = ("ranking%s.csv" % sfx) if tag == "P1" else ("ranking_%s%s.csv" % (tag, sfx))
        r = pd.read_csv(Path(folder) / rk).set_index("module")
        out[lab] = (m, r)
    return out


def half_ranks(m, col):
    """Rank by one SR column (no DSR for a half: tie clusters fall back to module A->Z)."""
    rows = [dict(module=k, sr=float(v), dsr=math.nan) for k, v in m[col].items()
            if k != BENCH and m.loc[k, "status"] == "ok"]
    return {r["module"]: i for i, r in enumerate(rank.order_rules(rows), start=1)}


def render_sensitivity(results_dir, tag="P1"):
    base = Path(results_dir)
    tabs = {v: _variant_tables(base / sub, tag) for v, sub, _ in VARIANTS}
    m1, r1 = tabs["A1"]["1x"]
    order = [k for k in r1.sort_values("rank").index if r1.loc[k, "status"] == "ok"]
    h1, h2 = half_ranks(m1, "sr_h1"), half_ranks(m1, "sr_h2")

    def cell(v, cost, mod, what):
        m, r = tabs[v][cost]
        if mod not in m.index or m.loc[mod, "status"] != "ok":
            return "n/a"
        return _f(m.loc[mod, "sr"]) if what == "sr" else str(int(r.loc[mod, "rank"]))

    lines = [
        "# Sensitivity of the %s ranking to the daily close and to costs" % tag, "",
        "> Educational research only. Not financial advice. See DISCLAIMER.md.", "",
        "Variants (D-frame close only; Open/High/Low/Volume and the 15m frame are the same in all three,",
        "so 15m rules have identical numbers):", "",
    ]
    lines += ["- **%s** = `%s/` - %s" % (v, (base / sub).as_posix(), desc) for v, sub, desc in VARIANTS]
    lines += ["", "SR = annualised Sharpe of daily net P&L over 2021-01-04 -> 2026-02-24. Rank at 0x / 2x = the rank "
              "in that cost run (section 8 tie rule inside the run). H1 / H2 ranks order the A1 rules by the "
              "half's SR (ties < 0.005 broken A->Z; no DSR per half).", "",
              "## Overview (1x costs, A1 rank order)", "",
              "| Module | Frame | A1 rank | A1 SR | v1 rank | v1 SR | 15:00 rank | 15:00 SR | A1 H1 SR (rank) | A1 H2 SR (rank) |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for mod in order:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s (%d) | %s (%d) |" % (
            mod, m1.loc[mod, "frame"], cell("A1", "1x", mod, "rank"), cell("A1", "1x", mod, "sr"),
            cell("v1", "1x", mod, "rank"), cell("v1", "1x", mod, "sr"), cell("15:00", "1x", mod, "rank"),
            cell("15:00", "1x", mod, "sr"), _f(m1.loc[mod, "sr_h1"]), h1[mod], _f(m1.loc[mod, "sr_h2"]), h2[mod]))
    lines += ["", "## Per rule", ""]
    for mod in order:
        lines += ["### %s. %s (%s frame)" % (cell("A1", "1x", mod, "rank"), mod, m1.loc[mod, "frame"]), "",
                  "| Close | SR 0x | Rank 0x | SR 1x | Rank 1x | SR 2x | Rank 2x |", "|---|---:|---:|---:|---:|---:|---:|"]
        for v, _, _ in VARIANTS:
            lines.append("| %s | %s |" % (v, " | ".join("%s | %s" % (cell(v, c, mod, "sr"), cell(v, c, mod, "rank"))
                                                       for c, _ in COSTS_SFX)))
        lines += ["", "A1 halves (1x): H1 SR %s (rank %d), H2 SR %s (rank %d)." % (
            _f(m1.loc[mod, "sr_h1"]), h1[mod], _f(m1.loc[mod, "sr_h2"]), h2[mod]), ""]
    nb = [k for k in r1.index if r1.loc[k, "status"] == "not_backtestable"]
    if nb:
        lines.append("Not backtestable (ranks %s): %s." % (", ".join(str(int(r1.loc[k, "rank"])) for k in nb), ", ".join(nb)))
    return "\n".join(lines) + "\n"


def sensitivity_main(args):
    out = Path(args.results) / "SENSITIVITY.md"
    out.write_text(render_sensitivity(args.results), encoding="utf-8")
    print("wrote: %s" % out)
    return 0


# ============================================================================================
# main
# ============================================================================================
def _load_dataset(args):
    if args.dataset.upper() == "P1":
        m1 = data.load_p1(use_cache=not args.no_cache, refresh=args.refresh_cache, verbose=True)
        info = m1.attrs.get("info", {})
        src = "%d NinjaTrader EveryBar files, cache %s" % (len(info.get("files", [])) or len(data.p1_files()),
                                                            info.get("cache", "?"))
        return "P1", m1, src
    path = Path(args.dataset)
    m1 = data.load_ohlcv_csv(path, date_col=args.date_col, time_col=args.time_col or None,
                             source_tz=args.source_tz)
    return path.stem, m1, str(path)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="qibt.cli", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run all rules on one dataset")
    r.add_argument("--dataset", default="P1", help="P1, or a plain OHLCV CSV path")
    r.add_argument("--costs", type=float, default=1.0, help="cost multiplier (0, 1, 2)")
    r.add_argument("--out", default="results")
    r.add_argument("--rules", default=str(signals.RULES_PATH))
    r.add_argument("--n-trials", type=int, default=None, help="DSR N (default: number of rules)")
    r.add_argument("--var-sr", type=float, default=None, help="DSR V[SR per day] (default: this run)")
    r.add_argument("--refresh-cache", action="store_true")
    r.add_argument("--no-cache", action="store_true")
    r.add_argument("--date-col", default="Date")
    r.add_argument("--time-col", default="Time")
    r.add_argument("--source-tz", default=None, help="tz of naive CSV times (default: US Central)")
    r.add_argument("--no-halt-check", action="store_true", help="skip the 16:00-17:00 CT halt check")
    r.add_argument("--close", choices=data.CLOSE_MODES, default=data.DEFAULT_CLOSE_MODE,
                   help="D-frame close: settle (A1, default), last (v1), 1500")
    b = sub.add_parser("bootstrap", help="stationary block bootstrap of the rank order -> BOOTSTRAP.md")
    b.add_argument("--results", default="results", help="folder with daily_pnl_P1.csv and ranking.csv")
    b.add_argument("--resamples", type=int, default=bootstrap.N_RESAMPLES)
    b.add_argument("--block", type=float, default=bootstrap.MEAN_BLOCK, help="mean block length, days")
    b.add_argument("--seed", type=int, default=bootstrap.SEED)
    b.add_argument("--out", default=None, help="output markdown (default <results>/BOOTSTRAP.md)")
    b.add_argument("--label", default="P1, A1 settlement close, 1x costs", help="title of the report")
    s = sub.add_parser("sensitivity", help="v1 / A1 / 15:00 side by side -> SENSITIVITY.md")
    s.add_argument("--results", default="results", help="A1 folder; v1_last_trade/ and close_1500/ inside it")
    rb = sub.add_parser("robustness", help="A3: R1 (Stooq SPY) and R3 (Stooq ES.F) daily datasets -> results/robustness/")
    rb.add_argument("--data-dir", default=None, help="folder with spy_us_d.csv and es_f_d.csv (default: the ninjatrader_quant_data stooq folder)")
    rb.add_argument("--p1-metrics", default="results/metrics_P1.csv", help="P1 A1.1 metrics for the Spearman reference")
    rb.add_argument("--out", default="results/robustness")
    rb.add_argument("--rules", default=str(signals.RULES_PATH))
    rb.add_argument("--costs", type=float, default=1.0)
    args = ap.parse_args(argv)
    if args.cmd == "robustness":
        from . import robustness
        if args.data_dir is None:
            args.data_dir = str(robustness.STOOQ_DIR)
        return robustness.main(args)
    if args.cmd == "bootstrap":
        return bootstrap.main(args)
    if args.cmd == "sensitivity":
        return sensitivity_main(args)

    t0 = time.time()
    dataset, m1, src = _load_dataset(args)
    print("loaded %s: %d bars in %.1fs" % (dataset, len(m1), time.time() - t0))
    ruleset = signals.load_rules(args.rules)
    res = run_pipeline(m1, ruleset, base_mult=args.costs, n_trials=args.n_trials, var_sr=args.var_sr,
                       halt=None if args.no_halt_check else data.HALT, close_mode=args.close, verbose=True)
    meta = {
        "run_at": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "source": src, "bars": len(m1),
        "first_bar": str(m1["BarTime"].iloc[0]), "last_bar": str(m1["BarTime"].iloc[-1]),
        "rules_version": ruleset.version, "rules_frozen": ruleset.frozen, "wall": time.time() - t0,
    }
    paths = write_outputs(res, args.out, dataset, meta)
    pend = [r["module"] for r in res["ranking"] if r["status"] == "pending"]
    print("D close %s: window %s | all %s" % (args.close, _branches(res["close_report"]["window"]),
                                              _branches(res["close_report"]["all"])))
    print("wrote: " + ", ".join(str(p) for p in paths.values()))
    if pend:
        print("PENDING (ranking incomplete): " + ", ".join(pend))
    print("wall time %.1fs" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
