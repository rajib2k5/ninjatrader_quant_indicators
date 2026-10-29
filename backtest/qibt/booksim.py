"""booksim.py - deterministic order-book event simulator for the iceberg detector (spec section 1).

Educational research only. Not financial advice.

Each session is a sequence of price-level *episodes* on the bid and ask side, separated by noise
(random quote changes and small trades on both sides). Prices are integer ticks of 0.25 around 5000.
Ground truth labels every episode level as (kind, side, price, start_seq, end_seq, ...):

  iceberg         hidden total 100-400, displayed clip 5-20. Opposite-side aggressive trades of 1..clip
                  lots hit the level at its price (bid/ask fields set so they classify correctly);
                  when the displayed size is consumed it is refilled to the clip (a B/A update at the
                  same price, after a trade). Ends when the total is exhausted (level removed, price
                  moves away: "broken", sometimes via an explicit size-0 update) or, sometimes, when the
                  price moves away favourably ("held") once the order has absorbed at least
                  max(40% of its total, 4 clips) - an iceberg cut off after one refill is not
                  observable by any detector and is not planted.
  decoy_large     one resting order shown 150-300, traded down by less than its shown size, no refills.
  decoy_join      size increases at the same price (crowd joining), some of them after trades, plus a few
                  trades; total traded < 1.9 x the largest shown size.
  decoy_small_mm  small market-maker requote: clip 2-4, refills after trades, total traded < 20 lots.

Realism choices: a trade never takes a whole clip in one print at the start of a clip cycle (the
resulting c -> c "refill" would be a net-zero book update that no price-level detector can see), and the
displayed size is updated after every trade (as a Market Replay feed would).

Known limitation (documented, deliberately NOT generated as a decoy): a market maker that re-quotes
the same price after every fill with large volume is indistinguishable from an iceberg on price-level
data.

    python -I -m qibt.booksim --sessions 200 --seed 20261028 --out DIR
writes DIR/session_000.csv ... and DIR/truth.json (run from backtest/ or after the editable install).
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

from .iceberg import Row, write_stream_csv

TICK = 0.25
BASE_TICKS = 20000          # 5000.00
KINDS = ("iceberg", "decoy_large", "decoy_join", "decoy_small_mm")
Truth = List[Dict]


class _Sim:
    """Mutable best-bid/ask book that records every change as a stream row."""

    def __init__(self, rng: random.Random, start_ticks: int, spread: int):
        self.rng = rng
        self.rows: List[Row] = []
        self.seq = 0
        self.bp = start_ticks
        self.ap = start_ticks + spread
        self.bs = rng.randint(5, 60)
        self.as_ = rng.randint(5, 60)
        self.spread = spread

    # ---- low level emission
    def _next(self) -> int:
        self.seq += 1
        return self.seq

    def reset(self) -> None:
        self.rows.append((self._next(), "R", None, None, None, None))

    def snapshot(self) -> None:
        """Re-announce both quotes (as a feed does after a session start / reset)."""
        self.rows.append((self._next(), "B", self.bp * TICK, self.bs, None, None))
        self.rows.append((self._next(), "A", self.ap * TICK, self.as_, None, None))

    def put_bid(self, ticks: int, size: int) -> None:
        if (ticks, size) != (self.bp, self.bs):
            self.bp, self.bs = ticks, size
            self.rows.append((self._next(), "B", ticks * TICK, size, None, None))

    def put_ask(self, ticks: int, size: int) -> None:
        if (ticks, size) != (self.ap, self.as_):
            self.ap, self.as_ = ticks, size
            self.rows.append((self._next(), "A", ticks * TICK, size, None, None))

    def set_quotes(self, bp: int, bs: int, ap: int, as_: int) -> None:
        """Update both sides without ever showing a crossed book."""
        if bp >= self.ap:
            self.put_ask(ap, as_)
            self.put_bid(bp, bs)
        elif ap <= self.bp:
            self.put_bid(bp, bs)
            self.put_ask(ap, as_)
        else:
            self.put_bid(bp, bs)
            self.put_ask(ap, as_)

    def trade(self, price_ticks: int, volume: int, known: bool = True) -> None:
        bid = self.bp * TICK if known else None
        ask = self.ap * TICK if known else None
        self.rows.append((self._next(), "T", price_ticks * TICK, volume, bid, ask))

    # ---- side-generic accessors (sgn +1: bid side, -1: ask side)
    def price(self, sgn: int) -> int:
        return self.bp if sgn > 0 else self.ap

    def put(self, sgn: int, ticks: int, size: int) -> None:
        (self.put_bid if sgn > 0 else self.put_ask)(ticks, size)

    def hit(self, sgn: int, volume: int) -> None:
        """Aggressive trade into the sgn side's price (seller hits bid, buyer lifts ask)."""
        self.trade(self.price(sgn), volume)


def _side_name(sgn: int) -> str:
    return "bid" if sgn > 0 else "ask"


def _noise(sim: _Sim, n: int) -> None:
    """n random harmless events: quote moves, size changes, small trades on both sides."""
    rng = sim.rng
    for _ in range(n):
        r = rng.random()
        if r < 0.18:                                  # whole market steps one tick
            d = rng.choice((-1, 1))
            sim.set_quotes(sim.bp + d, rng.randint(5, 60), sim.ap + d, rng.randint(5, 60))
        elif r < 0.30:                                # spread wiggles
            sgn = rng.choice((1, -1))
            if sgn > 0:
                nb = sim.bp + rng.choice((-1, 1))
                if nb < sim.ap:
                    sim.put_bid(nb, rng.randint(5, 60))
            else:
                na = sim.ap + rng.choice((-1, 1))
                if na > sim.bp:
                    sim.put_ask(na, rng.randint(5, 60))
        elif r < 0.50:                                # displayed size changes at the same price
            if rng.random() < 0.5:
                sim.put_bid(sim.bp, max(1, sim.bs + rng.randint(-8, 8)))
            else:
                sim.put_ask(sim.ap, max(1, sim.as_ + rng.randint(-8, 8)))
        elif r < 0.92:                                # small aggressive trade
            sgn = rng.choice((1, -1))
            known = rng.random() < 0.9
            v = min(rng.randint(1, 3) if rng.random() < 0.9 else rng.randint(4, 8),
                    sim.bs if sgn > 0 else sim.as_)
            sim.hit(sgn, v) if known else sim.trade(sim.price(sgn), v, known=False)
            if sgn > 0:
                if sim.bs - v > 0:
                    sim.put_bid(sim.bp, sim.bs - v)
                else:
                    sim.put_bid(sim.bp - 1, rng.randint(5, 60))
            else:
                if sim.as_ - v > 0:
                    sim.put_ask(sim.ap, sim.as_ - v)
                else:
                    sim.put_ask(sim.ap + 1, rng.randint(5, 60))
        else:                                         # trade inside a 2-tick spread / odd print
            if sim.ap - sim.bp >= 2:
                sim.trade(sim.bp + 1, rng.randint(1, 3))
            else:
                sim.trade(sim.bp, rng.randint(1, 2), known=False)


def _open_level(sim: _Sim, sgn: int, size: int) -> int:
    """Start a level on side sgn at a new price (other side follows with a fresh spread)."""
    rng = sim.rng
    k = rng.choice([x for x in range(-4, 5) if x != 0])
    target = sim.price(sgn) + k
    spread = rng.choice((1, 1, 2))
    other = rng.randint(5, 60)
    if sgn > 0:
        sim.set_quotes(target, size, target + spread, other)
    else:
        sim.set_quotes(target - spread, other, target, size)
    return target


def _leave(sim: _Sim, sgn: int, favourable: bool) -> None:
    """Price moves away from the episode level: held (favourable) or broken."""
    rng = sim.rng
    p = sim.price(sgn)
    step = rng.randint(1, 3)
    new_p = p + sgn * step if favourable else p - sgn * step
    size = rng.randint(5, 60)
    if sgn > 0:
        # a bid rising to/through the ask drags the ask along (never crosses)
        sim.set_quotes(new_p, size, max(sim.ap, new_p + 1), sim.as_)
    else:
        sim.set_quotes(min(sim.bp, new_p - 1), sim.bs, new_p, size)


def _side_noise(sim: _Sim, sgn: int) -> None:
    """Quiet activity on the opposite side while an episode runs (no trades there)."""
    rng = sim.rng
    if rng.random() < 0.25:
        if sgn > 0:
            sim.put_ask(sim.ap, max(1, sim.as_ + rng.randint(-6, 6)))
        else:
            sim.put_bid(sim.bp, max(1, sim.bs + rng.randint(-6, 6)))


# ------------------------------------------------------------------------------------ episodes
def _clip_run(sim: _Sim, sgn: int, total: int, clip: int, stop_at: int, tag_noise: bool) -> int:
    """Execute a replenishing order of `total` lots with displayed `clip`; stop after `stop_at`
    lots executed (stop_at >= total means run to exhaustion). Return lots executed."""
    rng = sim.rng
    executed = 0
    disp = clip
    remaining = total - clip           # hidden remainder behind the displayed clip
    while True:
        # a trade: never the whole clip as the first print of a cycle
        hi = min(clip, disp)
        v = rng.randint(1, hi)
        if disp == clip and v == disp:
            v = max(1, disp - 1)
        sim.hit(sgn, v)
        executed += v
        disp -= v
        if disp > 0:
            sim.put(sgn, sim.price(sgn), disp)
        else:
            if remaining > 0:
                disp = min(clip, remaining)
                remaining -= disp
                sim.put(sgn, sim.price(sgn), disp)    # refill, after the trade
            else:
                return executed        # exhausted; caller removes the level
        if tag_noise:
            _side_noise(sim, sgn)
        if executed >= stop_at:
            return executed


def _episode_iceberg(sim: _Sim, sgn: int) -> Dict:
    rng = sim.rng
    total = rng.randint(100, 400)
    clip = rng.randint(5, 20)
    p = _open_level(sim, sgn, clip)
    held = rng.random() < 0.35
    stop = max(int(0.4 * total) + rng.randint(0, int(0.5 * total)), 4 * clip) if held else total
    stop = min(stop, total)
    start_seq = _first_level_seq(sim, sgn)
    executed = _clip_run(sim, sgn, total, clip, stop, True)
    if executed >= total or sim.price(sgn) != p:
        # exhausted: the level is removed
        if rng.random() < 0.5:
            sim.put(sgn, p, 0)
        _leave(sim, sgn, favourable=False)
        end = "broken"
    else:
        _leave(sim, sgn, favourable=True)
        end = "held"
    return dict(kind="iceberg", side=_side_name(sgn), price=p * TICK, start_seq=start_seq,
                end_seq=sim.seq, hidden_total=total, clip=clip, executed=executed, end=end)


def _first_level_seq(sim: _Sim, sgn: int) -> int:
    """Seq of the event that opened the level just created by _open_level (last event on that side)."""
    want = "B" if sgn > 0 else "A"
    for row in reversed(sim.rows):
        if row[1] == want:
            return row[0]
    raise RuntimeError("no level event")


def _episode_decoy_large(sim: _Sim, sgn: int) -> Dict:
    rng = sim.rng
    shown = rng.randint(150, 300)
    p = _open_level(sim, sgn, shown)
    start_seq = _first_level_seq(sim, sgn)
    budget = int(shown * rng.uniform(0.3, 0.9))
    done = 0
    cur = shown
    while done < budget:
        v = min(rng.randint(1, 30), budget - done)
        sim.hit(sgn, v)
        done += v
        cur -= v
        sim.put(sgn, p, cur)
        _side_noise(sim, sgn)
    _leave(sim, sgn, favourable=rng.random() < 0.5)
    return dict(kind="decoy_large", side=_side_name(sgn), price=p * TICK, start_seq=start_seq,
                end_seq=sim.seq, shown=shown, traded=done)


def _episode_decoy_join(sim: _Sim, sgn: int) -> Dict:
    rng = sim.rng
    s0 = rng.randint(10, 40)
    p = _open_level(sim, sgn, s0)
    start_seq = _first_level_seq(sim, sgn)
    disp = s0
    shown_max = s0
    traded = 0
    n_join = 0
    for _ in range(rng.randint(6, 14)):
        if rng.random() < 0.5 or disp < 3:
            j = rng.randint(2, 15)
            disp += j
            shown_max = max(shown_max, disp)
            n_join += 1
            sim.put(sgn, p, disp)
        else:
            v = rng.randint(1, max(1, disp - 1))
            if traded + v > 1.9 * shown_max:
                continue
            sim.hit(sgn, v)
            traded += v
            disp -= v
            sim.put(sgn, p, disp)
        _side_noise(sim, sgn)
    if n_join < 2:                                   # guarantee crowd joining happened
        for _ in range(2 - n_join):
            disp += rng.randint(2, 15)
            shown_max = max(shown_max, disp)
            sim.put(sgn, p, disp)
    _leave(sim, sgn, favourable=rng.random() < 0.5)
    return dict(kind="decoy_join", side=_side_name(sgn), price=p * TICK, start_seq=start_seq,
                end_seq=sim.seq, shown_max=shown_max, traded=traded)


def _episode_small_mm(sim: _Sim, sgn: int) -> Dict:
    rng = sim.rng
    clip = rng.randint(2, 4)
    total = rng.randint(max(6, 2 * clip + 1), 19)
    p = _open_level(sim, sgn, clip)
    start_seq = _first_level_seq(sim, sgn)
    held = rng.random() < 0.4
    stop = rng.randint(2 * clip, total) if held else total
    executed = _clip_run(sim, sgn, total, clip, min(stop, total), True)
    exhausted = executed >= total
    if exhausted and rng.random() < 0.5:
        sim.put(sgn, p, 0)
    _leave(sim, sgn, favourable=(not exhausted))
    return dict(kind="decoy_small_mm", side=_side_name(sgn), price=p * TICK, start_seq=start_seq,
                end_seq=sim.seq, clip=clip, executed=executed)


_EPISODES = {
    "iceberg": _episode_iceberg,
    "decoy_large": _episode_decoy_large,
    "decoy_join": _episode_decoy_join,
    "decoy_small_mm": _episode_small_mm,
}


def simulate_session(rng: random.Random, n_iceberg: Tuple[int, int] = (2, 4),
                     n_decoy: Tuple[int, int] = (1, 3)) -> Tuple[List[Row], Truth]:
    """One session: (rows, truth). Counts per kind are drawn uniformly from the given ranges."""
    kinds: List[str] = ["iceberg"] * rng.randint(*n_iceberg)
    for k in KINDS[1:]:
        kinds += [k] * rng.randint(*n_decoy)
    rng.shuffle(kinds)
    spread = rng.choice((1, 2))
    sim = _Sim(rng, BASE_TICKS + rng.randint(-200, 200), spread)
    sim.reset()
    sim.snapshot()
    truth: Truth = []
    for i, kind in enumerate(kinds):
        _noise(sim, rng.randint(5, 25))
        if i > 0 and rng.random() < 0.15:            # mid-session reset between episodes
            sim.reset()
            sim.snapshot()
        sgn = rng.choice((1, -1))
        truth.append(_EPISODES[kind](sim, sgn))
    _noise(sim, rng.randint(3, 10))
    return sim.rows, truth


def simulate(n_sessions: int, seed: int) -> List[Tuple[List[Row], Truth]]:
    rng = random.Random(seed)
    return [simulate_session(rng) for _ in range(n_sessions)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="qibt.booksim", description="Write simulated iceberg event streams.")
    ap.add_argument("--sessions", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261028)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    truth_all = {}
    for i, (rows, truth) in enumerate(simulate(a.sessions, a.seed)):
        name = "session_%03d" % i
        write_stream_csv(out / (name + ".csv"), rows)
        truth_all[name] = truth
    with open(str(out / "truth.json"), "w") as fh:
        json.dump(truth_all, fh, indent=1)
    print("wrote %d sessions to %s" % (a.sessions, out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
