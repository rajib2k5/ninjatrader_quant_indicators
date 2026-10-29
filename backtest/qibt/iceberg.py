"""iceberg.py - Python reference for the QI_28 iceberg detector (validation/iceberg/spec.md, sections 1-6).

Educational research only. Not financial advice. The engine labels order-book behaviour; it does not
say buy or sell.

Event stream (CSV header ``seq,type,price,size,bid,ask``): B/A best-bid/ask updates with displayed
size, T trades (bid/ask prices at the trade, blank = unknown), R session reset. The engine keeps one
current price level per side and emits ``FLAG`` / ``FINAL`` CSV records exactly as in spec section 6.

    eng = IcebergEngine()
    eng.on_bid(1, 5000.0, 10); eng.on_trade(2, 5000.0, 4, 5000.0, 5000.25); ...
    records = run_stream(rows)                     # rows = list of (seq, type, price, size, bid, ask)

CLI (run from backtest/, or after the editable install of backtest/):
    python -I -m qibt.iceberg STREAM.csv [--hidden-ratio X --min-refills N --min-volume N --min-refill-size N]

Known limitation (documented, not tested as a false alarm): a market maker that re-quotes the same
price after every fill with large volume is indistinguishable from an iceberg on price-level data.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from typing import List, Optional, Sequence, Tuple

EPS = 1e-9
HEADER = "seq,type,price,size,bid,ask"

# One stream row: (seq:int, type:str, price:float|None, size:int|None, bid:float|None, ask:float|None)
Row = Tuple[int, str, Optional[float], Optional[int], Optional[float], Optional[float]]


def _eq(a: float, b: float) -> bool:
    return abs(a - b) < EPS


def _known(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


class _Level:
    """The current price level of one side (spec section 3)."""

    __slots__ = ("price", "start_seq", "shown_max", "last_shown", "traded", "refills",
                 "refill_sizes", "pending", "flagged", "flag_conf")

    def __init__(self, price: float, start_seq: int, size: int):
        self.price = price
        self.start_seq = start_seq
        self.shown_max = size
        self.last_shown = size
        self.traded = 0
        self.refills = 0
        self.refill_sizes: List[int] = []
        self.pending = False
        self.flagged = False
        self.flag_conf = 0.0


def _median(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2:
        return float(s[n // 2])
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


class IcebergEngine:
    def __init__(self, hidden_ratio: float = 2.0, min_refills: int = 2, min_volume: int = 20,
                 min_refill_size: int = 1):
        self.hidden_ratio = float(hidden_ratio)
        self.min_refills = int(min_refills)
        self.min_volume = min_volume
        self.min_refill_size = min_refill_size
        self.levels = {"bid": None, "ask": None}
        self.unclassified = 0

    # ---------------------------------------------------------------- public event API
    def on_bid(self, seq: int, price: float, size: int) -> List[str]:
        return self._quote("bid", seq, price, size)

    def on_ask(self, seq: int, price: float, size: int) -> List[str]:
        return self._quote("ask", seq, price, size)

    def on_trade(self, seq: int, price: float, volume: int, bid: Optional[float],
                 ask: Optional[float]) -> List[str]:
        sell = _known(bid) and (price <= bid or _eq(price, bid))
        buy = _known(ask) and (price >= ask or _eq(price, ask))
        if sell == buy:                       # neither, or both (crossed): unclassified
            self.unclassified += 1
            return []
        side = "bid" if sell else "ask"
        lvl = self.levels[side]
        if lvl is None or not _eq(price, lvl.price):
            return []
        lvl.traded += volume
        lvl.pending = True
        return self._evaluate_flag(side, lvl, seq)

    def on_reset(self, seq: int) -> List[str]:
        out: List[str] = []
        for side in ("bid", "ask"):          # bid side before ask side
            lvl = self.levels[side]
            if lvl is not None:
                out.extend(self._finalize(side, lvl, seq, "open"))
                self.levels[side] = None
        return out

    # ---------------------------------------------------------------- internals
    def _quote(self, side: str, seq: int, q: float, s: int) -> List[str]:
        out: List[str] = []
        lvl = self.levels[side]
        if lvl is None or not _eq(q, lvl.price):
            if lvl is not None:
                if side == "bid":
                    reason = "held" if q > lvl.price else "broken"
                else:
                    reason = "held" if q < lvl.price else "broken"
                out.extend(self._finalize(side, lvl, seq, reason))
                self.levels[side] = None
            if s > 0:
                self.levels[side] = _Level(q, seq, s)
            return out
        if s == 0:
            out.extend(self._finalize(side, lvl, seq, "broken"))
            self.levels[side] = None
            return out
        if s > lvl.last_shown and lvl.pending and (s - lvl.last_shown) >= self.min_refill_size:
            lvl.refills += 1
            lvl.refill_sizes.append(s)
            lvl.pending = False
        lvl.last_shown = s
        lvl.shown_max = max(lvl.shown_max, s)
        out.extend(self._evaluate_flag(side, lvl, seq))
        return out

    def _conf(self, lvl: _Level) -> float:
        c = (0.4 + 0.15 * (lvl.refills - self.min_refills)
             + 0.1 * (lvl.traded / lvl.shown_max - self.hidden_ratio))
        return min(1.0, max(0.4, c))

    def _evaluate_flag(self, side: str, lvl: _Level, seq: int) -> List[str]:
        if (not lvl.flagged and lvl.shown_max > 0
                and lvl.traded >= self.hidden_ratio * lvl.shown_max
                and lvl.refills >= self.min_refills
                and lvl.traded >= self.min_volume):
            lvl.flagged = True
            lvl.flag_conf = self._conf(lvl)
            return ["FLAG,%s,%.4f,%d,%d,%d,%d,%.4f" % (
                side, lvl.price, seq, lvl.traded, lvl.shown_max, lvl.refills, lvl.flag_conf)]
        return []

    def _finalize(self, side: str, lvl: _Level, end_seq: int, reason: str) -> List[str]:
        if not lvl.flagged:
            return []
        return ["FINAL,%s,%.4f,%d,%d,%d,%d,%d,%d,%.4f,%s,%.4f" % (
            side, lvl.price, lvl.start_seq, end_seq, lvl.traded, lvl.shown_max,
            lvl.traded - lvl.shown_max, lvl.refills, _median(lvl.refill_sizes), reason,
            self._conf(lvl))]


# -------------------------------------------------------------------------------- stream helpers
def feed(engine: IcebergEngine, row: Row) -> List[str]:
    """Dispatch one stream row to the engine and return the records it emitted."""
    seq, typ, price, size, bid, ask = row
    if typ == "B":
        return engine.on_bid(seq, price, size)
    if typ == "A":
        return engine.on_ask(seq, price, size)
    if typ == "T":
        return engine.on_trade(seq, price, size, bid, ask)
    if typ == "R":
        return engine.on_reset(seq)
    raise ValueError("unknown event type %r" % (typ,))


def run_stream(rows: Sequence[Row], **params) -> List[str]:
    """Run a whole stream through a fresh engine; return all records in emission order."""
    eng = IcebergEngine(**params)
    out: List[str] = []
    for row in rows:
        out.extend(feed(eng, row))
    return out


def _f(txt: str):
    return float(txt) if txt.strip() != "" else None


def _i(txt: str):
    return int(txt) if txt.strip() != "" else None


def read_stream_csv(path) -> List[Row]:
    """Read a section-1 event CSV into a list of row tuples (empty fields become None)."""
    rows: List[Row] = []
    with open(str(path), newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd, None)
        if header is None or [h.strip() for h in header] != HEADER.split(","):
            raise ValueError("bad header in %s: %r" % (path, header))
        for rec in rd:
            if not rec:
                continue
            rec = (rec + [""] * 6)[:6]
            rows.append((int(rec[0]), rec[1].strip(), _f(rec[2]), _i(rec[3]), _f(rec[4]), _f(rec[5])))
    return rows


def write_stream_csv(path, rows: Sequence[Row]) -> None:
    def fmt(x):
        return "" if x is None else ("%.4f" % x).rstrip("0").rstrip(".") if isinstance(x, float) else str(x)

    with open(str(path), "w", newline="") as fh:
        fh.write(HEADER + "\n")
        for seq, typ, price, size, bid, ask in rows:
            fh.write("%d,%s,%s,%s,%s,%s\n" % (seq, typ, fmt(price), fmt(size), fmt(bid), fmt(ask)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="qibt.iceberg", description="Run the iceberg engine on an event CSV.")
    ap.add_argument("stream")
    ap.add_argument("--hidden-ratio", type=float, default=2.0)
    ap.add_argument("--min-refills", type=int, default=2)
    ap.add_argument("--min-volume", type=int, default=20)
    ap.add_argument("--min-refill-size", type=int, default=1)
    a = ap.parse_args(argv)
    recs = run_stream(read_stream_csv(a.stream), hidden_ratio=a.hidden_ratio, min_refills=a.min_refills,
                      min_volume=a.min_volume, min_refill_size=a.min_refill_size)
    sys.stdout.write("".join(r + "\n" for r in recs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
