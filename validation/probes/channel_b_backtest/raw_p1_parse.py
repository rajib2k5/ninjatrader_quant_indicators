"""Independent re-read of the six raw P1 files (PROTOCOL section 2), no qibt import.

Bar rows = SignalType empty. Per-row shift = len(row) - len(header); a header column X that lies at
or after the surplus field is read at header.index(X) + shift. Checks per row: Price == shifted
Close; the surplus field (just before the shifted Open) is empty. Files are taken in file-name
order, de-duplicated on BarTime (first occurrence wins), sorted.

Writes <out>.pkl (BarTime, Open..Volume) to the given scratch path - never into the repo (vendor data).
Usage: python -I -B raw_p1_parse.py OUT_PKL
"""
from __future__ import annotations

import csv
import glob
import os
import sys
import time

import numpy as np
import pandas as pd

SRC = r"C:\Users\rajib\OneDrive\Docs\futures_data\ninja_trader_signal_data\data"
out = sys.argv[1]
t0 = time.time()
files = sorted(glob.glob(os.path.join(SRC, "MES_1min_*.csv")))
parts = []
total_bad = 0
for fp in files:
    with open(fp, newline="", encoding="utf-8-sig") as fh:
        rd = csv.reader(fh)
        h = next(rd)
        ix = {k: i for i, k in enumerate(h)}
        isig, ibt, ipr = ix["SignalType"], ix["BarTime"], ix["Price"]
        io, ih, il, ic, iv = ix["Open"], ix["High"], ix["Low"], ix["Close"], ix["Volume"]
        bt, o, hi, lo, cl, vo = [], [], [], [], [], []
        shifts = {}
        nsig = bad = 0
        for r in rd:
            if r[isig] != "":
                nsig += 1
                continue
            s = len(r) - len(h)
            shifts[s] = shifts.get(s, 0) + 1
            if r[ipr] != r[ic + s] or (s > 0 and r[io + s - 1] != ""):
                bad += 1
                continue
            bt.append(r[ibt]); o.append(r[io + s]); hi.append(r[ih + s]); lo.append(r[il + s])
            cl.append(r[ic + s]); vo.append(r[iv + s])
    df = pd.DataFrame({"BarTime": pd.to_datetime(pd.Series(bt), format="%Y-%m-%d %H:%M:%S"),
                       "Open": np.array(o, float), "High": np.array(hi, float), "Low": np.array(lo, float),
                       "Close": np.array(cl, float), "Volume": np.array(vo, float)})
    within_dup = int(df["BarTime"].duplicated().sum())
    t = df["BarTime"].to_numpy()
    print("%s: header %d fields, bar rows %d, signal rows %d, shifts %s, bad rows %d, within-file dup BarTime %d, "
          "non-increasing steps %d, first %s, last %s" % (
              os.path.basename(fp), len(h), len(df), nsig, shifts, bad, within_dup,
              int(np.count_nonzero(t[1:] <= t[:-1])), df["BarTime"].iloc[0], df["BarTime"].iloc[-1]))
    total_bad += bad
    parts.append(df)
allb = pd.concat(parts, ignore_index=True)
n0 = len(allb)
dedup = allb.drop_duplicates("BarTime", keep="first")
print("concatenated rows %d, duplicates on BarTime %d, after de-dup %d" % (n0, n0 - len(dedup), len(dedup)))
# identical-content duplicates vs conflicting duplicates
dups = allb[allb["BarTime"].duplicated(keep=False)]
if len(dups):
    conflicting = dups.groupby("BarTime").nunique().max(axis=1).gt(1).sum()
    print("duplicated BarTimes with conflicting OHLCV: %d" % int(conflicting))
dedup = dedup.sort_values("BarTime", kind="mergesort").reset_index(drop=True)
dedup.to_pickle(out)
print("bad rows total %d; wrote %s (%d bars) in %.1fs" % (total_bad, out, len(dedup), time.time() - t0))
sys.exit(0 if total_bad == 0 else 1)
