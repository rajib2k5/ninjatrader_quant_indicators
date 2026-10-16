#!/usr/bin/env python3
"""diff_values.py - Channel B runtime differential for ledger claims C18-C43.

Joins the ORIGINAL indicator's EveryBar CSV (IBSFade, CsvLogMode = EveryBar) with the harness
CSV written by QI_EgvDump on the SAME chart, by BarTime, and reports per claim: bars compared,
mismatches (|orig - new| > TOL), max abs diff, and the first mismatching bar.

Usage: python diff_values.py ORIG_CSV HARNESS_CSV [--tol 0.00005] [--min-bar 50]

ORIG EveryBar row layout (IBSFade.cs lines 509-511, 2794-2803):
  0 Timestamp,1 BarTime,2 Symbol,3 Timeframe,4 SignalType,5 Direction,6 Description,7 Price,
  8 IBS,9 AlphaCount,10 HpScore,11 Confidence,12 SweptLevel,13 Patterns,14 Open,15 High,16 Low,
  17 Close,18 Volume,19 ATR14 per the HEADER - but the data rows have one extra empty field
  (format string "{4},,,,,,,,{5}"), so in the ROWS Open..Volume are 15..19, ATR 20 and the 33
  databox_* values are 21..53.
Signal rows (SignalType non-empty) have only 20 columns and are skipped. The ORIG file is
opened in append mode by the indicator, so repeated chart loads duplicate BarTimes: the LAST
row per BarTime (most recent run) is used, and the number of duplicates is reported.
"""
from __future__ import annotations

import csv
import sys
from collections import OrderedDict

ORIG_DATABOX = [
    "HPScore", "IBS", "RSI2", "ConnorsRSI", "StochK", "RVZScore", "CompositeVol", "TurnOfMonth",
    "ConsecDays", "OvernightGap", "Bollinger", "TurnaroundTue", "RSI14", "VRPProxy", "WideRange",
    "VWAPDist", "MACDHist", "EMA2050", "SMA200", "ATRRegime", "VolSpike", "VolDelta", "VolDeltaSMA",
    "AlphaCount", "LiqSweep", "ChopIndex", "ChoppyFlag", "OFSignal", "OFDetail", "SMCSignal",
    "SMCDetail", "TotalBuys", "TotalSells",
]

# claim -> (ORIG databox name, harness column, note)
MAP = OrderedDict([
    ("C18", ("IBS",          "QI_IBS.Values[0]",               "")),
    ("C19", ("RSI2",         "QI_RSI2.Values[0]",              "")),
    ("C20", ("ConnorsRSI",   "QI_ConnorsRSI.Values[0]",        "")),
    ("C21", ("StochK",       "QI_StochFade.K",                 "%K only (ORIG logged no %D)")),
    ("C22", ("RVZScore",     "QI_RVZScore.Values[0]",          "")),
    ("C23", ("CompositeVol", "QI_CompositeVol.Values[0]",      "")),
    ("C24", ("TurnOfMonth",  "QI_TurnOfMonth.Values[0]",       "")),
    ("C25", ("ConsecDays",   "QI_ConsecDays.Values[0]",        "")),
    ("C26", ("OvernightGap", "QI_OvernightGap.Values[0]",      "")),
    ("C27", ("Bollinger",    "QI_BollingerPctB.PctB",          "")),
    ("C28", ("TurnaroundTue","QI_TurnaroundTuesday.Values[0]", "")),
    ("C29", ("RSI14",        "QI_RSI14.Values[0]",             "")),
    ("C30", ("VRPProxy",     "QI_VRPProxy.Values[0]",          "")),
    ("C31", ("WideRange",    "QI_WideRangeBar.Values[0]",      "")),
    ("C32", ("HPScore",      "QI_HedgingPressure.Values[0]",   "score only")),
    ("C33", ("VWAPDist",     "QI_VWAPDistance.VwapDistance",   "intraday chart only")),
    ("C34", ("MACDHist",     "QI_MACDHistogram.Values[0]",     "")),
    ("C35", ("EMA2050",      "QI_EMACross.Spread",             "")),
    ("C36", ("SMA200",       "QI_SMA200Trend.Distance",        "")),
    ("C37", ("ATRRegime",    "QI_ATRRegime.Values[0]",         "")),
    ("C38", ("VolSpike",     "QI_VolumeSpike.Values[0]",       "")),
    ("C39a",("VolDelta",     "QI_VolumeDelta.CumDelta20",      "")),
    ("C39b",("VolDeltaSMA",  "QI_VolumeDelta.DeltaSMA10",      "")),
    ("C40a",("ChopIndex",    "QI_ChopIndex.Values[0]",         "")),
    ("C40b",("ChoppyFlag",   "QI_ChopIndex.ChoppyFlag",        "")),
    ("C41", ("LiqSweep",     "QI_LiquiditySweep.Confidence",   "ORIG logs End events only; harness also writes Start events (0.35) -> counted separately as 'start-only'")),
    ("C42", ("OFSignal",     "QI_OrderFlowPlus.Confidence",    "")),
    ("C43", ("SMCSignal",    "QI_SMC.Confidence",              "")),
])


def load_orig(path):
    rows, dups = OrderedDict(), 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.reader(f):
            # ORIG's EveryBar format string has one comma too many ("{4},,,,,,,,{5}"), so each
            # row has 54 fields against a 53-field header: OHLCV sit at 15-19, ATR at 20 and the
            # 33 databox values at 21-53 (found by validation/pytests/test_data_integrity.py).
            if len(r) < 54 or r[0] == "Timestamp" or r[4] != "":
                continue
            bt = r[1]
            if bt in rows:
                dups += 1
            rows[bt] = {name: r[21 + i] for i, name in enumerate(ORIG_DATABOX)}
            rows[bt]["Close"] = r[18]
    return rows, dups


def load_harness(path):
    rows, dups = OrderedDict(), 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        for r in rd:
            bt = r["BarTime"]
            if bt in rows:
                dups += 1
            rows[bt] = r
    return rows, dups


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    orig_path, new_path = sys.argv[1], sys.argv[2]
    tol = float(sys.argv[sys.argv.index("--tol") + 1]) if "--tol" in sys.argv else 0.00005
    min_bar = int(sys.argv[sys.argv.index("--min-bar") + 1]) if "--min-bar" in sys.argv else 50

    orig, odups = load_orig(orig_path)
    new, ndups = load_harness(new_path)
    common = [bt for bt in new if bt in orig and int(new[bt]["Bar"]) >= min_bar]
    print(f"orig rows={len(orig)} (dup BarTimes overwritten={odups})  harness rows={len(new)} (dups={ndups})  joined bars>={min_bar}: {len(common)}")
    if not common:
        print("NO OVERLAP - check instrument/timeframe/date range"); sys.exit(1)
    # sanity: same bars? compare Close
    close_mis = sum(1 for bt in common if abs(num(orig[bt]["Close"]) - num(new[bt]["Close"])) > 0.0001)
    print(f"sanity Close mismatches: {close_mis}")

    print(f"\n{'claim':6} {'orig col':14} {'harness col':34} {'n':>5} {'mismatch':>8} {'maxdiff':>10}  first mismatch")
    overall_fail = False
    for cid, (oc, hc, note) in MAP.items():
        n = mism = 0; maxd = 0.0; first = ""
        start_only = 0
        for bt in common:
            o, h = num(orig[bt][oc]), num(new[bt].get(hc))
            if o is None or h is None:
                continue
            n += 1
            # C27 (ADD-2): QI_BollingerPctB deliberately uses the Middle band where ORIG used
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
                    first = f"{bt} orig={o} new={h} bar={new[bt]['Bar']}"
            maxd = max(maxd, d)
        flag = "" if mism == 0 else "  <-- MISMATCH"
        if mism: overall_fail = True
        extra = f"  (start-only events: {start_only})" if cid == "C41" else ""
        print(f"{cid:6} {oc:14} {hc:34} {n:5d} {mism:8d} {maxd:10.5f}  {first}{flag}{extra}")
        if note:
            print(f"{'':6} note: {note}")
    print("\nRESULT:", "FAIL (see MISMATCH rows)" if overall_fail else "all mapped claims match within tolerance")
    sys.exit(1 if overall_fail else 0)


if __name__ == "__main__":
    main()
