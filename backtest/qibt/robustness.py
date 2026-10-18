"""robustness.py - PROTOCOL section 9 amendment A3: robustness datasets R1 and R3.

Robustness results are reported next to the ranking and never change it (PROTOCOL section 2).

R1 = Stooq SPY.US daily (spy_us_d.csv): Open/High/Low/Close x 10 (MES scale), Volume as delivered.
R3 = Stooq ES.F daily (es_f_d.csv): rows before 1997-09-09 dropped; HedgingPressure "n/a (no
     volume)"; roll-gap filter (and an unfiltered run, R3_unfiltered).
Daily bars are used as delivered: trading date = the row's Date, no 17:00 roll, no settlement
inference (A1 is P1 only). The 18 D-frame rules of rules.yaml run with the section 4-7 execution,
costs, metrics and a 300-bar warm-up, for (a) the full history after warm-up and (b) the P1 window.

Roll gap (R3): a roll date is a trading date within +-5 trading days of the third Friday of
Mar/Jun/Sep/Dec with |Open_t - Close_{t-1}| > 3 x the median of that quantity over the previous
60 bars. Every bar whose open-to-open interval contains a roll date r - bar r-1 (Open_{r-1} ->
Open_r, which carries the Close_{r-1} -> Open_r jump) and bar r (Open_r -> Open_{r+1}) - gets gross
P&L 0 for every rule and the benchmark; costs of executions on those bars are still charged.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import io
import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import cli, engine, metrics, signals

STOOQ_DIR = Path(r"C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_data\stooq")
FILES = {"R1": "spy_us_d.csv", "R3": "es_f_d.csv"}
R1_SCALE = 10.0
ES_LAUNCH = pd.Timestamp("1997-09-09")
WARMUP_BARS = 300
ROLL_MONTHS = (3, 6, 9, 12)
ROLL_HALF_WINDOW = 5          # trading days either side of the third Friday
GAP_LOOKBACK = 60
GAP_MULT = 3.0
NO_VOLUME = {"HedgingPressure": "n/a (no volume)"}
REQUIRED = ("Date", "Open", "High", "Low", "Close")
DATE_FORMAT = "%Y-%m-%d"
RUNS = ("R1", "R3", "R3_unfiltered")
WINDOWS = ("full", "p1window")


class StooqFormatError(ValueError):
    """The file is not a Stooq daily CSV (e.g. the HTML bot-check page Stooq serves to scripts)."""


# ============================================================================================
# loaders
# ============================================================================================
def read_stooq(path):
    """Stooq daily CSV -> (DataFrame Date, Open, High, Low, Close, Volume; info). Columns are read
    by header name (extra columns ignored); Date must be YYYY-MM-DD."""
    path = Path(path)
    raw = path.read_bytes()
    head = raw[:4096].lstrip(b"\xef\xbb\xbf").lstrip().lower()
    if head.startswith(b"<") or b"<html" in head or b"<!doctype" in head or b"<script" in head:
        raise StooqFormatError("%s is an HTML page, not a Stooq CSV (Stooq serves a bot-check page to "
                               "scripts): download it in a browser" % path.name)
    if not head:
        raise StooqFormatError("%s is empty" % path.name)
    try:
        df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except Exception as e:
        raise StooqFormatError("%s: not a CSV (%s)" % (path.name, e))
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise StooqFormatError("%s: header %s lacks %s (a Stooq 'No data' reply?)" % (path.name, list(df.columns), missing))
    n_rows = len(df)
    try:
        date = pd.to_datetime(df["Date"].str.strip(), format=DATE_FORMAT)
    except (ValueError, TypeError) as e:
        raise StooqFormatError("%s: Date is not YYYY-MM-DD (%s)" % (path.name, e))
    out = pd.DataFrame({"Date": date})
    for c in ("Open", "High", "Low", "Close"):
        out[c] = pd.to_numeric(df[c].str.strip(), errors="coerce").to_numpy(dtype=float)
    vol = df["Volume"].str.strip() if "Volume" in df.columns else pd.Series("0", index=df.index)
    out["Volume"] = pd.to_numeric(vol, errors="coerce").fillna(0.0).to_numpy(dtype=float)
    bad = out[["Open", "High", "Low", "Close"]].isna().any(axis=1)
    out = out[~bad]
    n_dup = int(out["Date"].duplicated().sum())
    out = out.drop_duplicates("Date", keep="first").sort_values("Date", kind="mergesort").reset_index(drop=True)
    info = {"file": path.name, "data_rows": n_rows, "rows_dropped_nan": int(bad.sum()), "duplicates_dropped": n_dup,
            "extra_columns": [c for c in df.columns if c not in REQUIRED + ("Volume",)],
            "volume_column": "Volume" in df.columns}
    return out, info


def daily_frame_from(bars):
    """D frame as the pipeline expects it; trading date = Date (bars used as delivered)."""
    d = pd.DataFrame({"TradingDate": pd.to_datetime(bars["Date"]).dt.normalize(),
                      "BarTime": pd.to_datetime(bars["Date"]).dt.normalize()})
    for c in ("Open", "High", "Low", "Close", "Volume"):
        d[c] = np.asarray(bars[c], dtype=float)
    d["Bars"] = 1
    d["CloseSource"] = "delivered"
    d["CloseReason"] = ""
    return d


def load_r1(path):
    bars, info = read_stooq(path)
    for c in ("Open", "High", "Low", "Close"):
        bars[c] = bars[c] * R1_SCALE
    info["rows_used"] = len(bars)
    return daily_frame_from(bars), info


def load_r3(path):
    bars, info = read_stooq(path)
    keep = bars["Date"] >= ES_LAUNCH
    info["rows_before_launch_dropped"] = int((~keep).sum())
    bars = bars[keep].reset_index(drop=True)
    info["rows_used"] = len(bars)
    return daily_frame_from(bars), info


def file_manifest(path):
    path = Path(path)
    raw = path.read_bytes()
    bars, info = read_stooq(path)
    return {"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "data_rows": info["data_rows"],
            "first": str(bars["Date"].iloc[0].date()) if len(bars) else "", "last": str(bars["Date"].iloc[-1].date()) if len(bars) else "",
            "mtime": _dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}


# ============================================================================================
# roll-gap filter (R3)
# ============================================================================================
def third_friday(year, month):
    first = pd.Timestamp(year=year, month=month, day=1)
    return first + pd.Timedelta(days=(4 - first.dayofweek) % 7 + 14)


def roll_window_mask(dates, half=ROLL_HALF_WINDOW, months=ROLL_MONTHS):
    """True for trading dates within +-half trading days of a quarterly third Friday. The anchor
    is the third Friday, or the first trading date after it when it is not a trading date."""
    d = pd.DatetimeIndex(pd.to_datetime(dates))
    n = len(d)
    mask = np.zeros(n, dtype=bool)
    if n == 0:
        return mask
    for y in range(d[0].year, d[-1].year + 1):
        for m in months:
            tf = third_friday(y, m)
            if tf < d[0] or tf > d[-1]:
                continue
            a = int(np.searchsorted(d.values, np.datetime64(tf), side="left"))
            mask[max(a - half, 0): min(a + half, n - 1) + 1] = True
    return mask


def open_gaps(d):
    """|Open_t - Close_{t-1}| (NaN on the first bar)."""
    o, c = np.asarray(d["Open"], float), np.asarray(d["Close"], float)
    g = np.full(len(o), np.nan)
    g[1:] = np.abs(o[1:] - c[:-1])
    return g


def roll_dates(d, lookback=GAP_LOOKBACK, mult=GAP_MULT):
    """Bool per bar: a roll date (inside a roll window AND gap > mult x median of the previous
    `lookback` gaps; needs `lookback` previous gaps)."""
    g = pd.Series(open_gaps(d))
    med = g.rolling(lookback, min_periods=lookback).median().shift(1).to_numpy()
    with np.errstate(invalid="ignore"):
        big = g.to_numpy() > mult * med
    return roll_window_mask(d["TradingDate"]) & np.nan_to_num(big, nan=0.0).astype(bool)


def roll_gross_mask(flags):
    """Bars whose open-to-open interval contains a roll date r: bar r-1 and bar r."""
    f = np.asarray(flags, dtype=bool)
    m = f.copy()
    m[:-1] |= f[1:]
    return m


# ============================================================================================
# agreement measure
# ============================================================================================
def spearman(a, b):
    """Spearman rank correlation of two Series on their common non-NaN index (average ranks
    for ties); NaN if fewer than 2 pairs or no rank variance."""
    df = pd.concat([pd.Series(a, dtype=float), pd.Series(b, dtype=float)], axis=1, join="inner").dropna()
    if len(df) < 2:
        return math.nan
    r = df.rank(method="average")
    x, y = r.iloc[:, 0].to_numpy(), r.iloc[:, 1].to_numpy()
    if not (np.std(x) > 0 and np.std(y) > 0):
        return math.nan
    return float(np.corrcoef(x, y)[0, 1])


def sr_ranks(sr):
    """1 = highest SR; exact ties A->Z; NaN SRs get no rank."""
    s = pd.Series(sr, dtype=float).dropna()
    order = sorted(s.index, key=lambda k: (-s[k], k))
    return pd.Series({k: i for i, k in enumerate(order, start=1)}, dtype=float).reindex(pd.Series(sr).index)


# ============================================================================================
# runs
# ============================================================================================
def d_rules(ruleset):
    return [r for r in ruleset.rules if r.frame == "D"]


def windows_for(d, warmup=WARMUP_BARS):
    """(a) full history after warm-up = from the date of bar `warmup` to the last date;
    (b) the P1 window, clipped to the same warm-up start and the data end."""
    td = pd.DatetimeIndex(pd.to_datetime(d["TradingDate"]))
    if len(td) <= warmup:
        raise ValueError("%d bars: not more than the %d-bar warm-up" % (len(td), warmup))
    start, end = td[warmup], td[-1]
    p1 = (max(engine.EVAL_WINDOW[0], start), min(engine.EVAL_WINDOW[1], end))
    return {"full": (start, end), "p1window": p1}


def run_dataset(d, rules, base_mult=1.0, gross_mask=None, na=None, warmup=WARMUP_BARS):
    """Positions once, then metrics per window. Returns {window: metrics DataFrame}."""
    na = na or {}
    frames = {"D": d}
    pos = {}
    for rule in rules:
        if rule.module in na:
            pos[rule.module] = ("not_available", na[rule.module])   # not "n/a": pandas reads that as NaN
            continue
        try:
            pos[rule.module] = ("ok", signals.rule_positions(rule, frames)[1])
        except signals.PendingValue as e:
            pos[rule.module] = ("pending", str(e))
    out = {}
    for wname, window in windows_for(d, warmup).items():
        cal = engine.window_calendar(d, window)
        halves = engine.HALVES if wname == "p1window" else {}
        bench = engine.run_positions(d, engine.buy_and_hold_positions(d, window), cal, gross_mask=gross_mask)
        bnet = bench.net(base_mult)
        rows = []
        for rule in rules:
            st, p = pos[rule.module]
            row = {"module": rule.module, "frame": rule.frame, "value": rule.value, "status": st,
                   "reason": "" if st == "ok" else p}
            if st == "ok":
                dr = engine.run_positions(d, p, cal, gross_mask=gross_mask)
                row.update(cli.daily_metrics(dr, bnet, base_mult, halves))
            rows.append(row)
        ok = [r for r in rows if r["status"] == "ok"]
        v = metrics.sample_variance([r["sr_daily"] for r in ok])
        sr0 = metrics.expected_max_sr(v, len(rules)) if len(rules) >= 2 else math.nan
        for r in ok:
            r["dsr"] = metrics.psr(r["sr_daily"], sr0, r["n_days"], r["skew"], r["kurt"])
            r["dsr_log"] = metrics.log_psr(r["sr_daily"], sr0, r["n_days"], r["skew"], r["kurt"])
        brow = {"module": cli.BENCH, "frame": "D", "value": "buy_and_hold", "status": "benchmark", "reason": ""}
        brow.update(cli.daily_metrics(bench, bnet, base_mult, halves))
        tab = pd.DataFrame(rows + [brow]).reindex(columns=cli.METRIC_COLUMNS)
        rk = sr_ranks(tab.set_index("module").loc[[r.module for r in rules], "sr"])
        tab["rank_sr"] = tab["module"].map(rk).astype("Int64")
        tab.attrs.update(window=window, days=len(cal), var_sr=v, sr0=sr0)
        out[wname] = tab
    return out


def load_p1_sr(path, modules):
    m = pd.read_csv(path).set_index("module")
    miss = [k for k in modules if k not in m.index]
    if miss:
        raise ValueError("%s lacks %s" % (path, miss))
    return m.loc[modules, "sr"].astype(float)


def run_all(data_dir=STOOQ_DIR, p1_metrics="results/metrics_P1.csv", out_dir="results/robustness",
            rules_path=signals.RULES_PATH, base_mult=1.0):
    data_dir, out_dir = Path(data_dir), Path(out_dir)
    rules = d_rules(signals.load_rules(rules_path))
    mods = [r.module for r in rules]
    p1 = load_p1_sr(p1_metrics, mods)
    r1, i1 = load_r1(data_dir / FILES["R1"])
    r3, i3 = load_r3(data_dir / FILES["R3"])
    flags = roll_dates(r3)
    gmask = roll_gross_mask(flags)
    res = {"R1": run_dataset(r1, rules, base_mult),
           "R3": run_dataset(r3, rules, base_mult, gross_mask=gmask, na=NO_VOLUME),
           "R3_unfiltered": run_dataset(r3, rules, base_mult, na=NO_VOLUME)}
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ds in RUNS:
        for w in WINDOWS:
            p = out_dir / ("%s_%s_metrics.csv" % (ds, w))
            res[ds][w].to_csv(p, index=False)
            paths.append(p)
    meta = {
        "manifest": [file_manifest(data_dir / FILES[k]) for k in ("R1", "R3")],
        "info": {"R1": i1, "R3": i3}, "frames": {"R1": r1, "R3": r3},
        "rolls": pd.DatetimeIndex(r3.loc[flags, "TradingDate"]), "bars_zeroed": int(gmask.sum()),
        "p1_metrics": Path(p1_metrics).as_posix(), "base_mult": base_mult,
        "run_at": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    rep = out_dir / "ROBUSTNESS.md"
    rep.write_text(render(res, p1, mods, meta), encoding="utf-8")
    return res, p1, meta, paths + [rep]


def _f(x, nd=3):
    return "n/a" if x is None or (isinstance(x, float) and not math.isfinite(x)) or pd.isna(x) else ("%%.%df" % nd) % x


def render(res, p1, mods, meta):
    p1_rank = sr_ranks(p1)
    lines = [
        "# Robustness datasets R1 and R3 (PROTOCOL A3)", "",
        "> Educational research only. Not financial advice. See DISCLAIMER.md.", "",
        "Reported next to the ranking; robustness results **never change it** (PROTOCOL section 2). The 18 "
        "D-frame rules run on daily bars as delivered (trading date = the row's Date; no settlement "
        "inference), with the section 4-7 execution, costs (USD %.2f x %g per side), metrics and a %d-bar "
        "warm-up. P1 reference = the A1.1 SRs in `%s`. Rank = SR order among the rules run (exact ties "
        "A->Z); Spearman = rank correlation of the dataset's SRs with P1's SRs of the same rules (average "
        "ranks for ties; rules without an SR are left out); rank change = dataset rank - P1 rank (+ = lower "
        "on the dataset)." % (engine.COST_PER_SIDE, meta["base_mult"], WARMUP_BARS, meta["p1_metrics"]),
        "",
        "- **R1** = Stooq SPY.US daily, Open/High/Low/Close x 10 (MES scale), Volume as delivered; Stooq's split/dividend adjustment taken as is.",
        "- **R3** = Stooq ES.F daily from 1997-09-09; HedgingPressure n/a (no volume); roll-gap filter: %d roll dates, %d bars with gross P&L set to 0 (bars r-1 and r of each roll date r)." % (len(meta["rolls"]), meta["bars_zeroed"]),
        "- **R3_unfiltered** = R3 without the roll-gap filter.", "",
        "## MANIFEST", "", "```",
    ]
    for m in meta["manifest"]:
        lines.append("file: %s  sha256: %s  data rows: %d  first: %s  last: %s  file mtime: %s"
                     % (m["file"], m["sha256"], m["data_rows"], m["first"], m["last"], m["mtime"]))
    lines += ["```", "",
              "Rows used: R1 %d; R3 %d (%d rows before 1997-09-09 dropped). Run %s." % (
                  meta["info"]["R1"]["rows_used"], meta["info"]["R3"]["rows_used"],
                  meta["info"]["R3"]["rows_before_launch_dropped"], meta["run_at"]), "",
              "## Agreement with P1", "",
              "| Dataset | Window | First -> last date | Days | Rules with SR | Spearman vs P1 | Buy & hold SR |",
              "|---|---|---|---:|---:|---:|---:|"]
    rho = {}
    for ds in RUNS:
        for w in WINDOWS:
            t = res[ds][w].set_index("module")
            sr = t.loc[mods, "sr"].astype(float)
            rho[(ds, w)] = spearman(sr, p1)
            win = t.attrs["window"]
            lines.append("| %s | %s | %s -> %s | %d | %d | %s | %s |" % (
                ds, w, win[0].date(), win[1].date(), t.attrs["days"], int(sr.notna().sum()),
                _f(rho[(ds, w)]), _f(t.loc[cli.BENCH, "sr"])))
    for ds in RUNS:
        for w in WINDOWS:
            t = res[ds][w].set_index("module")
            lines += ["", "## %s, %s window" % (ds, w), "",
                      "| Module | P1 SR | P1 rank (of 18) | %s SR | %s rank | Rank change |" % (ds, ds),
                      "|---|---:|---:|---:|---:|---:|"]
            for k in sorted(mods, key=lambda k: p1_rank[k]):
                st = t.loc[k, "status"]
                if st != "ok":
                    lines.append("| %s | %s | %d | %s | | |" % (k, _f(p1[k]), p1_rank[k], t.loc[k, "reason"] or st))
                    continue
                rk = t.loc[k, "rank_sr"]
                lines.append("| %s | %s | %d | %s | %s | %s |" % (
                    k, _f(p1[k]), p1_rank[k], _f(t.loc[k, "sr"]), "" if pd.isna(rk) else int(rk),
                    "" if pd.isna(rk) else "%+d" % (int(rk) - int(p1_rank[k]))))
    if len(meta["rolls"]):
        lines += ["", "## R3 roll dates (filter applied)", "", ", ".join(d.strftime("%Y-%m-%d") for d in meta["rolls"])]
    return "\n".join(lines) + "\n"


def main(args):
    res, p1, meta, paths = run_all(args.data_dir, args.p1_metrics, args.out, args.rules, args.costs)
    for ds in RUNS:
        for w in WINDOWS:
            sr = res[ds][w].set_index("module").loc[list(p1.index), "sr"].astype(float)
            print("%-14s %-8s Spearman vs P1 %s" % (ds, w, _f(spearman(sr, p1))))
    print("R3 roll dates: %d, bars zeroed: %d" % (len(meta["rolls"]), meta["bars_zeroed"]))
    print("wrote: " + ", ".join(str(p) for p in paths))
    return 0
