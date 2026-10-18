"""bootstrap.py - stationary block bootstrap of the rank order (Politis & Romano 1994).

Every resample draws ONE sequence of day indices and applies it to all rules' daily P&L series
together, so their cross-correlation is kept. Index draws, per resample:
    i_0 = U{0..n-1};  for k = 1..n-1: with probability 1/mean_block a new block starts at
    i_k = U{0..n-1}, otherwise i_k = (i_{k-1} + 1) mod n  (circular continuation).
The random calls are made in exactly that order on one numpy Generator(seed), so a run is
reproducible bit for bit (and matches validation/adversarial-ranking.md section 6, which used the
same draw order). mean_block = 1 restarts every day: iid uniform day indices.
A resample whose SR is undefined (zero variance) ranks that rule last.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

N_RESAMPLES = 1000
MEAN_BLOCK = 10.0
SEED = 12345
CI = (5.0, 95.0)          # 90 % interval
TOP_K = 4                 # "first among the top 4" / exact top-4 order
TOP_PAIRS = 8             # adjacent-rank pairs 1-2 .. 7-8, CIs for the top 8


def stationary_indices(n, mean_block, rng):
    """One stationary-bootstrap index sequence of length n (see module docstring)."""
    if n < 1:
        raise ValueError("n must be >= 1")
    if not mean_block >= 1:
        raise ValueError("mean_block must be >= 1")
    p = 1.0 / mean_block
    idx = np.empty(n, dtype=np.int64)
    i = int(rng.integers(n))
    idx[0] = i
    for k in range(1, n):
        if rng.random() < p:
            i = int(rng.integers(n))
        else:
            i = (i + 1) % n
        idx[k] = i
    return idx


def sharpe_columns(Y, periods=252):
    """Annualised SR of every column (ddof = 1); NaN where the column has zero variance."""
    mu = Y.mean(axis=0)
    sd = Y.std(axis=0, ddof=1)
    out = np.full(Y.shape[1], np.nan)
    ok = sd > 0
    out[ok] = mu[ok] / sd[ok] * math.sqrt(periods)
    return out


def bootstrap_sharpe(X, n_resamples=N_RESAMPLES, mean_block=MEAN_BLOCK, seed=SEED, periods=252):
    """(n_resamples x n_rules) matrix of resampled SRs; X = (n_days x n_rules) daily P&L."""
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise ValueError("X must be 2-D (days x rules)")
    rng = np.random.default_rng(seed)
    out = np.empty((n_resamples, X.shape[1]))
    for b in range(n_resamples):
        out[b] = sharpe_columns(X[stationary_indices(X.shape[0], mean_block, rng)], periods)
    return out


def _key(sr):
    return np.where(np.isnan(sr), -np.inf, sr)


def p_first(sr, cols=None):
    """Share of resamples in which each column (of `cols`, default all) has the highest SR."""
    k = _key(np.asarray(sr, float))
    cols = list(range(k.shape[1])) if cols is None else list(cols)
    win = np.argmax(k[:, cols], axis=1)
    return np.bincount(win, minlength=len(cols)) / k.shape[0]


def p_order(sr, cols):
    """Share of resamples with SR[cols[0]] > SR[cols[1]] > ... (strict)."""
    k = _key(np.asarray(sr, float))[:, list(cols)]
    return float(np.mean(np.all(k[:, :-1] > k[:, 1:], axis=1)))


def p_greater(sr, a, b):
    k = _key(np.asarray(sr, float))
    return float(np.mean(k[:, a] > k[:, b]))


def ranks(sr):
    """Rank (1 = best) of every column in every resample."""
    k = _key(np.asarray(sr, float))
    order = np.argsort(-k, axis=1, kind="stable")
    r = np.empty_like(order)
    rows = np.arange(k.shape[0])[:, None]
    r[rows, order] = np.arange(1, k.shape[1] + 1)
    return r


def interval(sr_col, q=CI):
    v = np.asarray(sr_col, float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return (math.nan, math.nan)
    lo, hi = np.percentile(v, q)
    return float(lo), float(hi)


def summarize(sr, names, order, top_k=TOP_K, top_pairs=TOP_PAIRS):
    """Everything BOOTSTRAP.md reports. order = rule names in published rank order."""
    ix = {n: i for i, n in enumerate(names)}
    top = [ix[n] for n in order[:top_k]]
    rk = ranks(sr)
    return {
        "p_rank1": dict(zip(names, p_first(sr))),
        "p_rank_le_k": {n: float(np.mean(rk[:, ix[n]] <= top_k)) for n in names},
        "median_rank": {n: float(np.median(rk[:, ix[n]])) for n in names},
        "p_first_top": dict(zip(order[:top_k], p_first(sr, top))),
        "p_exact_top": p_order(sr, top),
        "pairs": [(order[i], order[i + 1], p_greater(sr, ix[order[i]], ix[order[i + 1]]))
                  for i in range(min(top_pairs, len(order)) - 1)],
        "ci": {n: interval(sr[:, ix[n]]) for n in order[:top_pairs]},
    }


def _f(x, nd=3):
    return "n/a" if x is None or not math.isfinite(x) else ("%%.%df" % nd) % x


def render(summary, published, meta):
    """BOOTSTRAP.md text. published: DataFrame indexed by module with rank, sr."""
    order = [m for m in published.sort_values("rank").index]
    k = len(summary["p_first_top"])
    lines = [
        "# Block-bootstrap rank probabilities - %s" % meta["label"], "",
        "> Educational research only. Not financial advice. See DISCLAIMER.md.", "",
        "Stationary block bootstrap (Politis & Romano 1994): mean block %g days, %d resamples, seed %d; all %d "
        "rules resampled on the SAME day indices in each resample (cross-correlation kept); %d trading days of "
        "net daily P&L from `%s`, published ranks from `%s`. A resample with zero variance ranks that rule last. "
        "These are sampling-noise statements about this one P1 history, not forecasts."
        % (meta["mean_block"], meta["resamples"], meta["seed"], len(summary["p_rank1"]), meta["days"],
           meta["daily"], meta["ranking"]), "",
        "## P(rank 1 of %d) per rule" % len(summary["p_rank1"]), "",
        "| Published rank | Module | Published SR | P(rank 1) | P(rank <= %d) | Median bootstrap rank |" % k,
        "|---:|---|---:|---:|---:|---:|",
    ]
    for m in order:
        lines.append("| %d | %s | %s | %.3f | %.3f | %g |" % (published.loc[m, "rank"], m, _f(published.loc[m, "sr"]),
                     summary["p_rank1"][m], summary["p_rank_le_k"][m], summary["median_rank"][m]))
    lines += ["", "## The published top %d" % k, "",
              "| Module | P(first among the top %d) |" % k, "|---|---:|"]
    lines += ["| %s | %.3f |" % (m, p) for m, p in summary["p_first_top"].items()]
    lines += ["", "P(exact published top-%d order %s) = **%.3f**" % (
        k, " > ".join(summary["p_first_top"]), summary["p_exact_top"]), "",
        "## Adjacent published ranks", "", "| Ranks | Pair | P(SR_i > SR_j) |", "|---|---|---:|"]
    for i, (a, b, p) in enumerate(summary["pairs"], start=1):
        lines.append("| %d vs %d | %s > %s | %.3f |" % (i, i + 1, a, b, p))
    lines += ["", "## 90%% interval of the annualised SR (top %d)" % len(summary["ci"]), "",
              "| Rank | Module | Published SR | 5% | 95% |", "|---:|---|---:|---:|---:|"]
    for m, (lo, hi) in summary["ci"].items():
        lines.append("| %d | %s | %s | %s | %s |" % (published.loc[m, "rank"], m, _f(published.loc[m, "sr"]), _f(lo, 2), _f(hi, 2)))
    return "\n".join(lines) + "\n"


def run_files(daily_csv, ranking_csv, n_resamples=N_RESAMPLES, mean_block=MEAN_BLOCK, seed=SEED):
    """Bootstrap the ranked rules of a results folder. Returns (summary, published, n_days)."""
    d = pd.read_csv(daily_csv)
    rk = pd.read_csv(ranking_csv)
    rk = rk[rk["status"] == "ok"].copy()
    rk["rank"] = rk["rank"].astype(int)
    pub = rk.set_index("module")[["rank", "sr"]]
    names = [c for c in d.columns if c in pub.index]          # daily-file column order
    missing = sorted(set(pub.index) - set(names))
    if missing:
        raise ValueError("ranked rules missing from %s: %s" % (daily_csv, missing))
    sr = bootstrap_sharpe(d[names].to_numpy(float), n_resamples, mean_block, seed)
    order = list(pub.sort_values("rank").index)
    return summarize(sr, names, order), pub, len(d)


def main(args):
    res = Path(args.results)
    daily, ranking = res / "daily_pnl_P1.csv", res / "ranking.csv"
    summary, pub, n = run_files(daily, ranking, args.resamples, args.block, args.seed)
    out = Path(args.out) if args.out else res / "BOOTSTRAP.md"
    meta = dict(label=args.label, mean_block=args.block, resamples=args.resamples, seed=args.seed, days=n,
                daily=daily.as_posix(), ranking=ranking.as_posix())
    out.write_text(render(summary, pub, meta), encoding="utf-8")
    print("wrote: %s" % out)
    print("P(first among top %d): %s; P(exact order) %.3f" % (
        len(summary["p_first_top"]), {m: round(float(p), 3) for m, p in summary["p_first_top"].items()}, summary["p_exact_top"]))
    return 0
