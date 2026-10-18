#!/usr/bin/env python3
"""diff_values.py - Channel B runtime differential for ledger claims C18-C43.

Joins the ORIGINAL indicator's EveryBar CSV (IBSFade, CsvLogMode = EveryBar) with the harness
CSV (merge_runs.py output of the QIV_* runs on the SAME chart) and reports per claim: bars
compared, mismatches (|orig - new| > TOL), max abs diff, and the first mismatching bar.

Usage:
  python diff_values.py ORIG_CSV HARNESS_CSV [--tol 0.00005] [--min-bar 50] [--allow-mixed-shift]
  python diff_values.py --inspect ORIG_CSV          (layout + join-key report only, no harness)

ORIG EveryBar layout
  The HEADER (IBSFade.cs 509-511) names 53 fields:
    0 Timestamp,1 BarTime,2 Symbol,3 Timeframe,4 SignalType,5 Direction,6 Description,7 Price,
    8 IBS,9 AlphaCount,10 HpScore,11 Confidence,12 SweptLevel,13 Patterns,14 Open,15 High,16 Low,
    17 Close,18 Volume,19 ATR14,20..52 databox_* (33 names, ORIG_DATABOX below).
  The bar ROWS (SignalType empty; IBSFade.cs 2794-2803, format "{4},,,,,,,,{5}") carry ONE
  SURPLUS EMPTY FIELD among columns 8..14, so in every bar row of
  MES_150tick_20250202_20260224.csv Open..Volume sit at 15..19, ATR14 at 20 and the databox_*
  values at 21..53 (verified on all 358,038 bar rows on 2026-10-16: 54 fields each; header
  column Price equals the shifted Close on every row; the field just before the shifted Open
  is empty on every row). Signal rows (SignalType non-empty) have 20 fields and are skipped.

  This script does NOT hardcode either layout. Every bar row is aligned by its own surplus,
      shift = len(row) - len(header)
  and the column the header calls X is read at header.index(X) + shift. Each row must pass two
  independent alignment checks (Price == shifted Close, and the field just before the shifted
  Open is empty); the detected shift distribution and the check counts are always printed, and
  the run ABORTS (exit 3) if any row fails a check or if more than one shift value is seen
  (override the latter with --allow-mixed-shift). A future export with a different layout is
  therefore reported, never silently misread. The databox_* names in the header must equal
  ORIG_DATABOX in order, or the run aborts.

Join key
  150-tick bars can share a 1-second BarTime (this export: 15,782 consecutive same-BarTime
  pairs, 27,637 bars in groups of 2..14), so BarTime alone is NOT a key on tick charts and the
  former "LAST row per BarTime" policy dropped 15,782 real bars. Both files are in chart order,
  so rows are keyed by (BarTime, k), k = ordinal of the row inside its same-BarTime group: a
  positional join inside each second. ORIG logs no CurrentBar; the harness Bar column
  (CurrentBar) is carried, must be strictly increasing along the joined rows, and O/H/L/C/V
  equality on every joined bar is the proof that the pairing is right (reported as "sanity";
  a failure aborts with exit 4 before any claim is compared). The ORIG file is opened in append
  mode by the indicator, so repeated chart loads append whole runs; a run boundary is a BarTime
  that goes backwards, the ordinal restarts there and the later run overwrites earlier ones
  (count reported). On Minute charts BarTime is unique, k is always 0 and the key degenerates
  to BarTime.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, OrderedDict

ORIG_DATABOX = [
    "HPScore", "IBS", "RSI2", "ConnorsRSI", "StochK", "RVZScore", "CompositeVol", "TurnOfMonth",
    "ConsecDays", "OvernightGap", "Bollinger", "TurnaroundTue", "RSI14", "VRPProxy", "WideRange",
    "VWAPDist", "MACDHist", "EMA2050", "SMA200", "ATRRegime", "VolSpike", "VolDelta", "VolDeltaSMA",
    "AlphaCount", "LiqSweep", "ChopIndex", "ChoppyFlag", "OFSignal", "OFDetail", "SMCSignal",
    "SMCDetail", "TotalBuys", "TotalSells",
]
OHLCV = ["Open", "High", "Low", "Close", "Volume"]

# claim -> (ORIG databox name, harness column, note)
MAP = OrderedDict([
    ("C18", ("IBS",          "QI_10_IBS.Values[0]",               "")),
    ("C19", ("RSI2",         "QI_03_RSI2.Values[0]",              "")),
    ("C20", ("ConnorsRSI",   "QI_13_ConnorsRSI.Values[0]",        "")),
    ("C21", ("StochK",       "QI_11_StochFade.K",                 "%K only (ORIG logged no %D)")),
    ("C22", ("RVZScore",     "QI_09_RVZScore.Values[0]",          "")),
    ("C23", ("CompositeVol", "QI_08_CompositeVol.Values[0]",      "")),
    ("C24", ("TurnOfMonth",  "QI_15_TurnOfMonth.Values[0]",       "")),
    ("C25", ("ConsecDays",   "QI_01_ConsecDays.Values[0]",        "")),
    ("C26", ("OvernightGap", "QI_18_OvernightGap.Values[0]",      "")),
    ("C27", ("Bollinger",    "QI_21_BollingerPctB.PctB",          "")),
    ("C28", ("TurnaroundTue","QI_17_TurnaroundTuesday.Values[0]", "")),
    ("C29", ("RSI14",        "QI_02_RSI14.Values[0]",             "")),
    ("C30", ("VRPProxy",     "QI_06_VRPProxy.Values[0]",          "")),
    ("C31", ("WideRange",    "QI_04_WideRangeBar.Values[0]",      "")),
    ("C32", ("HPScore",      "QI_12_HedgingPressure.Values[0]",   "score only")),
    ("C33", ("VWAPDist",     "QI_23_VWAPDistance.VwapDistance",   "intraday chart only")),
    ("C34", ("MACDHist",     "QI_16_MACDHistogram.Values[0]",     "")),
    ("C35", ("EMA2050",      "QI_14_EMACross.Spread",             "")),
    ("C36", ("SMA200",       "QI_07_SMA200Trend.Distance",        "")),
    ("C37", ("ATRRegime",    "QI_05_ATRRegime.Values[0]",         "")),
    ("C38", ("VolSpike",     "QI_20_VolumeSpike.Values[0]",       "")),
    ("C39a",("VolDelta",     "QI_19_VolumeDelta.CumDelta20",      "")),
    ("C39b",("VolDeltaSMA",  "QI_19_VolumeDelta.DeltaSMA10",      "")),
    ("C40a",("ChopIndex",    "QI_26_ChopIndex.Values[0]",         "")),
    ("C40b",("ChoppyFlag",   "QI_26_ChopIndex.ChoppyFlag",        "")),
    ("C41", ("LiqSweep",     "QI_22_LiquiditySweep.Confidence",   "ORIG logs End events only; harness also writes Start events (0.35) -> counted separately as 'start-only'")),
    ("C42", ("OFSignal",     "QI_24_OrderFlowPlus.Confidence",    "")),
    ("C43", ("SMCSignal",    "QI_25_SMC.Confidence",              "")),
])


def die(msg, code=3):
    print("\n!!! ABORT: " + msg, file=sys.stderr)
    sys.exit(code)


def load_orig(path, allow_mixed_shift=False):
    """Bar rows of the ORIG EveryBar CSV keyed by (BarTime, k); values aligned per row by shift.

    Returns (rows, info). rows[(BarTime, k)] -> {databox name: str, Open..Volume: str}.
    info describes the layout actually found and is printed by report_orig_layout()."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        header = next(csv.reader(f))
    hidx = {name: i for i, name in enumerate(header)}
    for req in ["BarTime", "SignalType", "Price", "ATR14"] + OHLCV:
        if req not in hidx:
            die("ORIG header has no column %r: %s" % (req, header))
    db_in_header = [c[len("databox_"):] for c in header if c.startswith("databox_")]
    if db_in_header != ORIG_DATABOX:
        die("ORIG header databox_* names differ from ORIG_DATABOX:\n  header: %s\n  script: %s"
            % (db_in_header, ORIG_DATABOX))
    i_sig, i_bt, i_price = hidx["SignalType"], hidx["BarTime"], hidx["Price"]
    i_open, i_close = hidx["Open"], hidx["Close"]
    i_db = {name: hidx["databox_" + name] for name in ORIG_DATABOX}
    i_ohlcv = {c: hidx[c] for c in OHLCV}

    rows = OrderedDict()
    shifts = Counter()
    bad = []                      # (line number, reason)
    nsig = 0
    runs, overwrites = 1, 0
    prev_bt, k = None, 0
    group_sizes = Counter()
    gsize = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f)
        next(rd)
        for lineno, r in enumerate(rd, start=2):
            if len(r) <= i_sig:
                bad.append((lineno, "only %d fields" % len(r))); continue
            if r[i_sig] != "":
                nsig += 1; continue
            shift = len(r) - len(header)
            if shift < 0:
                bad.append((lineno, "bar row shorter than header (%d < %d)" % (len(r), len(header)))); continue
            # two independent alignment checks for THIS row's shift
            if r[i_price] != r[i_close + shift]:
                bad.append((lineno, "shift=%d: Price %r != shifted Close %r" % (shift, r[i_price], r[i_close + shift]))); continue
            if shift > 0 and r[i_open + shift - 1] != "":
                bad.append((lineno, "shift=%d: field before shifted Open is %r, not empty" % (shift, r[i_open + shift - 1]))); continue
            shifts[shift] += 1
            bt = r[i_bt]
            if prev_bt is None or bt > prev_bt:
                if gsize: group_sizes[gsize] += 1
                k, gsize = 0, 1
            elif bt == prev_bt:
                k += 1; gsize += 1
            else:                                   # BarTime went backwards: a new appended run
                runs += 1
                if gsize: group_sizes[gsize] += 1
                k, gsize = 0, 1
            prev_bt = bt
            key = (bt, k)
            if key in rows:
                overwrites += 1
            d = {name: r[i_db[name] + shift] for name in ORIG_DATABOX}
            for c in OHLCV:
                d[c] = r[i_ohlcv[c] + shift]
            rows[key] = d
    if gsize: group_sizes[gsize] += 1
    info = dict(header_len=len(header), bar_rows=sum(shifts.values()), signal_rows=nsig,
                shifts=dict(sorted(shifts.items())), bad=bad, runs=runs, overwrites=overwrites,
                group_sizes=dict(sorted(group_sizes.items())),
                i_open=i_open, i_atr=hidx["ATR14"], i_db0=i_db[ORIG_DATABOX[0]], i_dbN=i_db[ORIG_DATABOX[-1]])
    report_orig_layout(info)
    if bad:
        die("%d ORIG bar row(s) failed the alignment checks (first 5 shown above) - "
            "the export layout is not what this script understands" % len(bad))
    if len(shifts) > 1 and not allow_mixed_shift:
        die("ORIG bar rows show more than one field-count surplus %s "
            "(re-run with --allow-mixed-shift only if that is expected)" % info["shifts"])
    if not shifts:
        die("ORIG has no bar rows")
    return rows, info


def report_orig_layout(info):
    print("ORIG layout report")
    print("  header fields=%d  bar rows=%d  signal rows skipped=%d"
          % (info["header_len"], info["bar_rows"], info["signal_rows"]))
    for s, n in info["shifts"].items():
        o, a, d0, dN = info["i_open"] + s, info["i_atr"] + s, info["i_db0"] + s, info["i_dbN"] + s
        print("  surplus fields per bar row = %+d on %d rows -> Open..Volume at %d..%d, ATR14 at %d, databox_* at %d..%d"
              % (s, n, o, o + 4, a, d0, dN))
    nbad = len(info["bad"])
    print("  alignment checks (Price == shifted Close; field before shifted Open empty): %d ok, %d bad"
          % (info["bar_rows"], nbad))
    for lineno, why in info["bad"][:5]:
        print("    line %d: %s" % (lineno, why))
    print("  appended runs (BarTime went backwards)=%d; (BarTime,k) keys overwritten by a later run=%d"
          % (info["runs"], info["overwrites"]))
    multi = {g: n for g, n in info["group_sizes"].items() if g > 1}
    bars_in_multi = sum(g * n for g, n in multi.items())
    dropped = sum((g - 1) * n for g, n in multi.items())
    if multi:
        print("  same-BarTime groups: %d bars in %d groups of >=2 (largest %d); a BarTime-only join would drop %d bars -> keyed by (BarTime,k)"
              % (bars_in_multi, sum(multi.values()), max(multi), dropped))
    else:
        print("  same-BarTime groups: none (BarTime is unique; key degenerates to BarTime)")


def load_harness(path):
    rows = OrderedDict()
    backwards = overwrites = 0
    prev_bt, k = None, 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            bt = r["BarTime"]
            if prev_bt is None or bt > prev_bt:
                k = 0
            elif bt == prev_bt:
                k += 1
            else:
                backwards += 1; k = 0
            prev_bt = bt
            key = (bt, k)
            if key in rows:
                overwrites += 1
            rows[key] = r
    print("harness rows=%d  BarTime went backwards %d time(s)  (BarTime,k) overwritten=%d"
          % (len(rows), backwards, overwrites))
    if backwards:
        print("  WARNING: harness rows are not in chart order; merge_runs.py output should be monotonic")
    return rows


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def main():
    argv = sys.argv[1:]
    allow_mixed = "--allow-mixed-shift" in argv
    if "--inspect" in argv:
        argv.remove("--inspect")
        if not argv:
            print(__doc__); sys.exit(2)
        load_orig(argv[0], allow_mixed_shift=allow_mixed)
        sys.exit(0)
    if len(argv) < 2:
        print(__doc__); sys.exit(2)
    orig_path, new_path = argv[0], argv[1]
    tol = float(argv[argv.index("--tol") + 1]) if "--tol" in argv else 0.00005
    min_bar = int(argv[argv.index("--min-bar") + 1]) if "--min-bar" in argv else 50

    orig, _ = load_orig(orig_path, allow_mixed_shift=allow_mixed)
    new = load_harness(new_path)
    common = [key for key in new if key in orig and int(new[key]["Bar"]) >= min_bar]
    print("orig bar rows=%d  harness rows=%d  joined on (BarTime,k) with Bar>=%d: %d"
          % (len(orig), len(new), min_bar, len(common)))
    if not common:
        print("NO OVERLAP - check instrument/timeframe/date range"); sys.exit(1)
    # sanity 1: harness Bar (CurrentBar) strictly increasing along the joined rows
    bars = [int(new[key]["Bar"]) for key in common]
    non_mono = sum(1 for a, b in zip(bars, bars[1:]) if b <= a)
    # sanity 2: same bars? O/H/L/C/V must agree on every joined row
    ohlcv_mis = {c: 0 for c in OHLCV}
    first_bad = ""
    for key in common:
        for c in OHLCV:
            o, h = num(orig[key][c]), num(new[key].get(c))
            if o is None or h is None or abs(o - h) > 0.0001:
                ohlcv_mis[c] += 1
                if not first_bad:
                    first_bad = "%s#%d %s: orig=%s harness=%s bar=%s" % (
                        key[0], key[1], c, orig[key][c], new[key].get(c), new[key]["Bar"])
    print("sanity: Bar non-monotonic steps=%d  O/H/L/C/V mismatches=%s%s"
          % (non_mono, ohlcv_mis, ("  first: " + first_bad) if first_bad else ""))
    if non_mono or any(ohlcv_mis.values()):
        die("joined rows are not the same bars (positional (BarTime,k) pairing failed) - "
            "claims were NOT compared", code=4)

    print("\n%-6s %-14s %-34s %5s %8s %10s  first mismatch"
          % ("claim", "orig col", "harness col", "n", "mismatch", "maxdiff"))
    overall_fail = False
    for cid, (oc, hc, note) in MAP.items():
        n = mism = 0; maxd = 0.0; first = ""
        start_only = 0
        for key in common:
            o, h = num(orig[key][oc]), num(new[key].get(hc))
            if o is None or h is None:
                continue
            n += 1
            # C27 (ADD-2): QI_21_BollingerPctB deliberately uses the Middle band where ORIG used
            # the Upper band, so new = orig + 100 whenever the bandwidth is > 0 (both 0 otherwise).
            if cid == "C27" and not (o == 0.0 and h == 0.0):
                h = h - 100.0
            d = abs(o - h)
            if cid == "C41" and o == 0.0 and abs(h - 0.35) <= tol:
                start_only += 1
                continue
            if d > tol:
                mism += 1
                if not first:
                    first = "%s#%d orig=%s new=%s bar=%s" % (key[0], key[1], o, h, new[key]["Bar"])
            maxd = max(maxd, d)
        flag = "" if mism == 0 else "  <-- MISMATCH"
        if mism: overall_fail = True
        extra = "  (start-only events: %d)" % start_only if cid == "C41" else ""
        print("%-6s %-14s %-34s %5d %8d %10.5f  %s%s%s" % (cid, oc, hc, n, mism, maxd, first, flag, extra))
        if note:
            print("%-6s note: %s" % ("", note))
    print("\nRESULT:", "FAIL (see MISMATCH rows)" if overall_fail else "all mapped claims match within tolerance")
    sys.exit(1 if overall_fail else 0)


if __name__ == "__main__":
    main()
