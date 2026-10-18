"""test_patterns_orig_differential.py - PT1-PT4: backtest/qibt/patterns.py vs the ORIGINAL indicator.

Educational research only. Not financial advice. See DISCLAIMER.md.

Oracle: the EveryBar CSV exports written by the ORIGINAL combined indicator (IBSFade.cs) on MES 1-minute
charts, one chart run per file (state resets per file), in
    C:\\Users\\rajib\\OneDrive\\Docs\\futures_data\\ninja_trader_signal_data\\data\\MES_1min_*.csv
(override the folder with QIBT_ORIG_DATA_DIR, restrict files with QIBT_ORIG_FILES=name1,name2).
The port runs on each file separately (never on the concatenation).

Layout (validation/probes/diff_values.py logic): bar rows (SignalType empty) carry one surplus empty
field vs the 53-field header, so a header column X is read at header.index(X) + (len(row) - len(header));
every bar row must pass Price == shifted Close and "field before the shifted Open is empty", every signal
row must have exactly 20 fields, BarTime must be strictly increasing (one chart run) - else the test errors.

Warm-up exclusion W (stated before any comparison was run): ORIG starts processing at the first row of
each file (its CurrentBars[1] >= 1 and bar-50 gates were passed before the first logged row, on bars
that are not in the file), the port starts at row 50 of the file with its ATR/SMA seeded at row 0. All
bars whose trading date (calendar date of BarTime, +1 day when the time is after 17:00) is one of the
first 2 trading dates of the file are excluded; everything after is compared.

PT1  |hp_score - databox_HPScore| <= 1e-3 on every compared bar (databox written with F4).
PT2  LiquiditySweep End events: multiset of (BarTime, confidence 2 dp, direction) of the port's End
     labels == ORIG LiqSweepEnd rows; and per bar, the port plots (confidence, structure) == ORIG's last
     End event of the bar (0, 0 without one) and confidence == databox_LiqSweep (F4).
PT3  OrderFlow+: (BarTime, confidence 2 dp, direction) of bars with ofp structure != 0 == ORIG
     "OrderFlow+" rows (Buy=+1, Sell=-1); per bar confidence == databox_OFSignal (F4).
PT4  SMC: same against ORIG "SMC" rows and databox_SMCSignal.
ORIG chart setting: ORIG has ONE DuplicateBarWindow shared by all its modules. It is inferred per file as the
window whose replay of ORIG's own HedgingPressure signal rule (IBSFade.cs 1064-1135, not part of the four
ports) on ORIG's own databox_HPScore reproduces the file's HedgingPressure rows exactly; the ports then run
with that window (all six exports: 6, while the C# default is 5). QIBT_DUP_WINDOW=<n> overrides it.
Diagnostics (not claims): LiquiditySweep Start events vs LiqSweepStart rows; port ATR14 vs ATR14 (F2).

Falsifiers: QIBT_PATTERNS_FILE=<path to a mutated copy of patterns.py> makes this module test that copy.

Run (repo root):
    python -I -m pytest backtest/tests -q -p no:cacheprovider -k patterns
    python -I backtest/tests/test_patterns_orig_differential.py        # verbose per-file report
"""
from __future__ import annotations

import csv
import importlib.util
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get(
    "QIBT_ORIG_DATA_DIR", r"C:\Users\rajib\OneDrive\Docs\futures_data\ninja_trader_signal_data\data"))
WARMUP_TRADING_DATES = 2
HP_TOL = 1e-3          # PT1 tolerance (F4 rounding allowance)
DB_TOL = 0.5e-4 + 1e-9  # F4 half-unit for the databox confidence columns
MIN_BARS = 200_000


def _orig_files():
    files = sorted(DATA_DIR.glob("MES_1min_*.csv")) if DATA_DIR.is_dir() else []
    only = os.environ.get("QIBT_ORIG_FILES")
    if only:
        keep = {s.strip() for s in only.split(",") if s.strip()}
        files = [f for f in files if f.name in keep]
    return files


def load_patterns_module():
    alt = os.environ.get("QIBT_PATTERNS_FILE")
    if alt:
        spec = importlib.util.spec_from_file_location("qibt_patterns_under_test", alt)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    bt = str(REPO / "backtest")
    if bt not in sys.path:
        sys.path.insert(0, bt)
    from qibt import patterns
    return patterns


# ============================================================================================
# ORIG loader
# ============================================================================================
DB_COLS = ["databox_HPScore", "databox_LiqSweep", "databox_OFSignal", "databox_SMCSignal"]


class LayoutError(RuntimeError):
    pass


def load_orig(path):
    """-> (bars DataFrame [BarTime str, OHLCV, ATR14, databox_*], signals list[(BarTime, type, dir, conf str)])."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f)
        header = next(rd)
        hidx = {c: i for i, c in enumerate(header)}
        for req in ["BarTime", "SignalType", "Direction", "Confidence", "Price", "Open", "High", "Low",
                    "Close", "Volume", "ATR14"] + DB_COLS:
            if req not in hidx:
                raise LayoutError("header has no column %r" % req)
        i_sig, i_bt, i_price, i_dir, i_conf = (hidx[c] for c in ("SignalType", "BarTime", "Price",
                                                                    "Direction", "Confidence"))
        i_o, i_h, i_l, i_c, i_v, i_atr = (hidx[c] for c in ("Open", "High", "Low", "Close", "Volume", "ATR14"))
        i_db = [hidx[c] for c in DB_COLS]
        nh = len(header)
        bt_l, o_l, h_l, l_l, c_l, v_l, atr_l = [], [], [], [], [], [], []
        db_l = [[] for _ in DB_COLS]
        signals = []
        shifts = Counter()
        prev = None
        for lineno, r in enumerate(rd, start=2):
            if len(r) <= i_sig:
                raise LayoutError("line %d: only %d fields" % (lineno, len(r)))
            if r[i_sig] != "":
                if len(r) != 20:
                    raise LayoutError("line %d: signal row with %d fields (expected 20)" % (lineno, len(r)))
                signals.append((r[i_bt], r[i_sig], r[i_dir], r[i_conf]))
                continue
            s = len(r) - nh
            if s < 0:
                raise LayoutError("line %d: bar row shorter than header" % lineno)
            if r[i_price] != r[i_c + s]:
                raise LayoutError("line %d: Price %r != shifted Close %r" % (lineno, r[i_price], r[i_c + s]))
            if s > 0 and r[i_o + s - 1] != "":
                raise LayoutError("line %d: field before shifted Open is not empty" % lineno)
            shifts[s] += 1
            bt = r[i_bt]
            if prev is not None and bt <= prev:
                raise LayoutError("line %d: BarTime %s not after %s (appended run?)" % (lineno, bt, prev))
            prev = bt
            bt_l.append(bt)
            o_l.append(float(r[i_o + s])); h_l.append(float(r[i_h + s])); l_l.append(float(r[i_l + s]))
            c_l.append(float(r[i_c + s])); v_l.append(float(r[i_v + s])); atr_l.append(float(r[i_atr + s]))
            for k, i in enumerate(i_db):
                db_l[k].append(float(r[i + s]))
    if len(shifts) != 1:
        raise LayoutError("bar rows show surplus-field counts %s (expected exactly one value)" % dict(shifts))
    bars = pd.DataFrame({"BarTimeStr": bt_l, "Open": o_l, "High": h_l, "Low": l_l, "Close": c_l,
                         "Volume": v_l, "ATR14": atr_l})
    for k, c in enumerate(DB_COLS):
        bars[c] = db_l[k]
    bars["BarTime"] = pd.to_datetime(bars["BarTimeStr"], format="%Y-%m-%d %H:%M:%S")
    layout = {"bar_rows": len(bars), "signal_rows": len(signals), "shift": dict(shifts)}
    return bars, signals, layout


def first_compared_row(bt):
    """Index of the first bar whose trading date is not among the first WARMUP_TRADING_DATES dates."""
    tod = bt.dt.hour * 3600 + bt.dt.minute * 60 + bt.dt.second
    tdate = bt.dt.normalize() + pd.to_timedelta((tod > 17 * 3600).astype(int), unit="D")
    firsts = tdate.drop_duplicates()
    if len(firsts) <= WARMUP_TRADING_DATES:
        return len(bt)
    cut = firsts.iloc[WARMUP_TRADING_DATES]
    return int(np.argmax((tdate >= cut).to_numpy()))


# ============================================================================================
# ORIG chart setting: DuplicateBarWindow (one property shared by every ORIG module)
# ============================================================================================
def simulate_orig_hp_signals(hp, bts, window, buy_thr=-35, sell_thr=35):
    """ORIG ProcessHpSignals (IBSFade.cs 1064-1135) on ORIG's own databox_HPScore, from row 0 (ORIG's first
    processed bar): barsSinceLastHp++; zone; suppress if same dir AND same zone AND barsSince < window."""
    out = []
    last_dir = last_zone = 0
    bs = 2147483647
    for i, s in enumerate(hp):
        bs = -2147483648 if bs == 2147483647 else bs + 1
        zone = -2 if s <= -35 else -1 if s <= -15 else 0 if s < 15 else 1 if s < 35 else 2
        buy, sell = s <= buy_thr, s >= sell_thr
        if not buy and not sell:
            continue
        d = 1 if buy else -1
        if d == last_dir and zone == last_zone and bs < window:
            continue
        out.append((bts[i], "Buy" if buy else "Sell"))
        last_dir, last_zone, bs = d, zone, 0
    return out


def infer_duplicate_window(bars, signals, candidates=range(1, 21)):
    """The DuplicateBarWindow of the ORIG chart run = the window(s) whose simulated HP signal stream equals the
    file's HedgingPressure rows exactly. Uses no ported code (HP signals are not part of the four modules)."""
    orig = Counter((bt, dr) for bt, st, dr, c in signals if st == "HedgingPressure")
    hp = bars["databox_HPScore"].tolist()
    bts = bars["BarTimeStr"].tolist()
    fits = {}
    for w in candidates:
        sim = Counter(simulate_orig_hp_signals(hp, bts, w))
        fits[w] = sum((orig - sim).values()) + sum((sim - orig).values())
    exact = [w for w, m in fits.items() if m == 0]
    return exact, fits


# ============================================================================================
# comparison
# ============================================================================================
_DIR = {"Buy": 1, "Sell": -1, "Bullish": 1, "Bearish": -1}


def _event_diff(orig_ev, port_ev):
    """Multiset compare of (BarTime, conf, dir) tuples; returns dict with counts and first mismatch."""
    co, cp = Counter(orig_ev), Counter(port_ev)
    only_o = co - cp
    only_p = cp - co
    first = None
    bad_times = sorted({e[0] for e in only_o} | {e[0] for e in only_p})
    if bad_times:
        t0 = bad_times[0]
        first = {"BarTime": t0,
                 "orig": sorted(e for e in orig_ev if e[0] == t0),
                 "port": sorted(e for e in port_ev if e[0] == t0)}
    return {"orig_events": len(orig_ev), "port_events": len(port_ev),
            "matched": sum((co & cp).values()),
            "only_orig": sum(only_o.values()), "only_port": sum(only_p.values()),
            "mismatched_bars": len(bad_times), "first": first,
            "bad_times": bad_times}


def analyze(path, P=None, dup_window=None):
    """dup_window None -> the window inferred from the file's HedgingPressure rows (must be unique)."""
    P = P or load_patterns_module()
    bars, signals, layout = load_orig(path)
    df = bars[["BarTime", "Open", "High", "Low", "Close", "Volume"]]
    n = len(df)
    start = first_compared_row(bars["BarTime"])
    if start < 50:
        raise AssertionError("warm-up exclusion ends before the port's bar-50 gate")
    t_start = bars["BarTimeStr"].iloc[start]
    bts = bars["BarTimeStr"].tolist()
    exact, fits = infer_duplicate_window(bars, signals)
    if dup_window is None and os.environ.get("QIBT_DUP_WINDOW"):
        dup_window = int(os.environ["QIBT_DUP_WINDOW"])          # evidence runs only (e.g. the C# default 5)
    if dup_window is None:
        if len(exact) != 1:
            raise AssertionError("cannot infer ORIG DuplicateBarWindow uniquely: exact=%s fits=%s" % (exact, fits))
        dup_window = exact[0]
    res = {"file": Path(path).name, "bars": n, "start_row": start, "start_time": t_start,
           "compared_bars": n - start, "layout": layout,
           "first_time": bts[0], "last_time": bts[-1],
           "dup_window_exact": exact, "dup_window_fit": {w: fits[w] for w in (4, 5, 6, 7) if w in fits},
           "dup_window_used": dup_window}

    # ---- diagnostics: ATR ----
    atr = P.nt_atr(df, 14)
    d_atr = np.abs(atr[start:] - bars["ATR14"].to_numpy()[start:])
    res["atr"] = {"n": int(len(d_atr)), "over_F2": int((d_atr > 0.005 + 1e-9).sum()), "max": float(d_atr.max())}

    # ---- PT1 HP ----
    hp = P.hp_score(df).to_numpy()
    ohp = bars["databox_HPScore"].to_numpy()
    d = np.abs(hp[start:] - ohp[start:])
    nan_ct = int(np.isnan(d).sum())
    bad = np.where(~(d <= HP_TOL))[0]
    pt1 = {"n": int(len(d)), "mismatches": int(len(bad)), "nan": nan_ct,
           "max_abs_diff": float(np.nanmax(d)) if len(d) else 0.0, "first": None}
    if len(bad):
        i = start + int(bad[0])
        pt1["first"] = {"BarTime": bts[i], "port": float(hp[i]), "orig": float(ohp[i])}
    res["PT1"] = pt1

    def orig_events(kind):
        return [(bt, round(float(c), 2), _DIR[dr]) for bt, st, dr, c in signals
                if st == kind and bt >= t_start]

    # ---- PT2 LiquiditySweep ----
    ev = P.liquidity_sweep_events(df, duplicate_bar_window=dup_window)
    ev = ev[ev["bar"] >= start]
    port_end = [(bts[b], round(float(c), 2), int(dr))
                for b, k, dr, c in zip(ev["bar"], ev["kind"], ev["direction"], ev["confidence"]) if k == "End"]
    port_start = [(bts[b], round(float(c), 2), int(dr))
                  for b, k, dr, c in zip(ev["bar"], ev["kind"], ev["direction"], ev["confidence"]) if k == "Start"]
    o_end = orig_events("LiqSweepEnd")
    pt2 = _event_diff(o_end, port_end)
    ls = P.liquidity_sweep(df, duplicate_bar_window=dup_window)
    pt2.update(_per_bar(ls, bars, start, bts, o_end, "databox_LiqSweep"))
    res["PT2"] = pt2
    res["LS_start"] = _event_diff(orig_events("LiqSweepStart"), port_start)

    # ---- PT3 OrderFlow+ ----
    of = P.order_flow_plus(df, duplicate_bar_window=dup_window)
    res["PT3"] = _signal_compare(of, bars, start, bts, orig_events("OrderFlow+"), "databox_OFSignal")

    # ---- PT4 SMC ----
    sm = P.smc(df, duplicate_bar_window=dup_window)
    res["PT4"] = _signal_compare(sm, bars, start, bts, orig_events("SMC"), "databox_SMCSignal")
    return res


def _per_bar(out, bars, start, bts, o_events, db_col):
    """Per-bar plots vs ORIG's last event of the bar and vs the databox column."""
    last = {}
    for bt, c, dr in o_events:
        last[bt] = (c, dr)                      # rows are in log order -> the last one wins
    conf = out["confidence"].to_numpy()
    st = out["structure"].to_numpy()
    db = bars[db_col].to_numpy()
    n_bad_plot = n_bad_db = 0
    first_plot = first_db = None
    for i in range(start, len(bts)):
        oc, od = last.get(bts[i], (0.0, 0))
        pc, pd_ = round(float(conf[i]), 2), int(st[i])
        if pc != oc or pd_ != od:
            n_bad_plot += 1
            if first_plot is None:
                first_plot = {"BarTime": bts[i], "port": (pc, pd_), "orig": (oc, od)}
        if not (abs(conf[i] - db[i]) <= DB_TOL):
            n_bad_db += 1
            if first_db is None:
                first_db = {"BarTime": bts[i], "port": float(conf[i]), "orig": float(db[i])}
    return {"per_bar_n": len(bts) - start, "per_bar_mismatches": n_bad_plot, "per_bar_first": first_plot,
            "databox_mismatches": n_bad_db, "databox_first": first_db}


def _signal_compare(out, bars, start, bts, o_events, db_col):
    conf = out["confidence"].to_numpy()
    st = out["structure"].to_numpy()
    idx = np.where(st[start:] != 0)[0] + start
    port_ev = [(bts[i], round(float(conf[i]), 2), int(st[i])) for i in idx]
    r = _event_diff(o_events, port_ev)
    r.update(_per_bar(out, bars, start, bts, o_events, db_col))
    return r


def format_report(res):
    L = []
    L.append("%s: bars=%d (%s .. %s), layout %s; warm-up W excludes rows 0..%d -> compared from %s: %d bars"
             % (res["file"], res["bars"], res["first_time"], res["last_time"], res["layout"],
                res["start_row"] - 1, res["start_time"], res["compared_bars"]))
    L.append("  ORIG DuplicateBarWindow: HedgingPressure rows reproduced exactly for window(s) %s; "
             "only_orig+only_sim by window %s; ports run with duplicate_bar_window=%d"
             % (res["dup_window_exact"], res["dup_window_fit"], res["dup_window_used"]))
    a = res["atr"]
    L.append("  diag ATR14 port vs CSV(F2): n=%d over-0.005=%d max=%.6f" % (a["n"], a["over_F2"], a["max"]))
    p = res["PT1"]
    L.append("  PT1 HP: compared=%d mismatches(>|1e-3|)=%d nan=%d max|diff|=%.6g first=%s"
             % (p["n"], p["mismatches"], p["nan"], p["max_abs_diff"], p["first"]))
    for key, name in (("PT2", "LiqSweep End"), ("PT3", "OrderFlow+"), ("PT4", "SMC")):
        q = res[key]
        L.append("  %s %s: orig events=%d port events=%d matched=%d only_orig=%d only_port=%d "
                 "mismatched bars=%d first=%s"
                 % (key, name, q["orig_events"], q["port_events"], q["matched"], q["only_orig"],
                    q["only_port"], q["mismatched_bars"], q["first"]))
        L.append("      per-bar plots vs ORIG last event: n=%d mismatches=%d first=%s; vs %s: mismatches=%d first=%s"
                 % (q["per_bar_n"], q["per_bar_mismatches"], q["per_bar_first"],
                    "databox", q["databox_mismatches"], q["databox_first"]))
    s = res["LS_start"]
    L.append("  diag LiqSweep Start: orig=%d port=%d matched=%d only_orig=%d only_port=%d first=%s"
             % (s["orig_events"], s["port_events"], s["matched"], s["only_orig"], s["only_port"], s["first"]))
    return "\n".join(L)


# ============================================================================================
# pytest
# ============================================================================================
FILES = _orig_files()
_CACHE = {}


@pytest.fixture(scope="module", params=FILES, ids=[f.name for f in FILES] or None)
def orig_result(request):
    path = request.param
    if path not in _CACHE:
        _CACHE[path] = analyze(path)
        print("\n" + format_report(_CACHE[path]))
    return _CACHE[path]


pytestmark = [pytest.mark.slow,
              pytest.mark.skipif(not FILES, reason="ORIG MES_1min_*.csv exports not present (UNVERIFIABLE)")]


def test_patterns_orig_file_is_full_year(orig_result):
    assert orig_result["compared_bars"] >= MIN_BARS, orig_result["compared_bars"]


def test_patterns_PT1_hp_score(orig_result):
    p = orig_result["PT1"]
    assert p["n"] >= MIN_BARS
    assert p["nan"] == 0
    assert p["mismatches"] == 0, p


@pytest.mark.parametrize("key", ["PT2", "PT3", "PT4"])
def test_patterns_event_sets(orig_result, key):
    q = orig_result[key]
    assert q["orig_events"] > 0
    assert q["only_orig"] == 0 and q["only_port"] == 0, {k: q[k] for k in q if k != "bad_times"}
    assert q["per_bar_mismatches"] == 0, q["per_bar_first"]
    assert q["databox_mismatches"] == 0, q["databox_first"]


if __name__ == "__main__":
    P = load_patterns_module()
    print("patterns module:", P.__file__)
    for f in FILES:
        print(format_report(analyze(f, P)))
