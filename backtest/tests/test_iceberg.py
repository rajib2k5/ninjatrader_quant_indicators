"""Iceberg detector reference (validation/iceberg/spec.md): rule-branch unit tests, simulator, I3, I4.

Run from the repository root:  python -I -m pytest backtest/tests/test_iceberg.py -q
All test names carry the `iceberg` tag - the three suites share one pytest session.
"""
from __future__ import annotations

import random

import pytest

from bt_helpers import BACKTEST_DIR  # noqa: F401  (also puts backtest/ on sys.path)
from qibt import booksim
from qibt.iceberg import IcebergEngine, feed, main as iceberg_main, read_stream_csv, run_stream
from qibt.iceberg_eval import evaluate

SEED = 20261028
BP, AP = 100.0, 100.25            # bid / ask used by the hand-built streams


def fields(rec):
    return rec.split(",")


def mk_bid_flag(eng=None, seq0=1, price=BP, **params):
    """Bid level that flags at its last event: shown 10, two refills, traded 20.
    Returns (engine, all records, next seq)."""
    eng = eng or IcebergEngine(**params)
    recs, s = [], seq0
    recs += eng.on_bid(s, price, 10); s += 1
    for _ in range(2):
        recs += eng.on_trade(s, price, 6, price, price + 0.25); s += 1
        recs += eng.on_bid(s, price, 4); s += 1
        recs += eng.on_trade(s, price, 4, price, price + 0.25); s += 1
        recs += eng.on_bid(s, price, 10); s += 1
    return eng, recs, s


def mk_ask_flag(eng=None, seq0=1, price=AP, **params):
    """Mirror of mk_bid_flag on the ask side (buyer-initiated trades at the ask)."""
    eng = eng or IcebergEngine(**params)
    recs, s = [], seq0
    recs += eng.on_ask(s, price, 10); s += 1
    for _ in range(2):
        recs += eng.on_trade(s, price, 6, price - 0.25, price); s += 1
        recs += eng.on_ask(s, price, 4); s += 1
        recs += eng.on_trade(s, price, 4, price - 0.25, price); s += 1
        recs += eng.on_ask(s, price, 10); s += 1
    return eng, recs, s


# ------------------------------------------------------------------------------ §3 B/A events
def test_iceberg_level_start_and_zero_size_start():
    e = IcebergEngine()
    assert e.on_bid(1, BP, 10) == []
    assert e.levels["bid"].price == BP and e.levels["bid"].start_seq == 1
    assert e.levels["bid"].shown_max == 10 and e.levels["bid"].last_shown == 10
    assert e.on_bid(2, 99.0, 0) == []            # unflagged old level discarded, size 0 -> no level
    assert e.levels["bid"] is None
    assert e.on_ask(3, AP, 0) == [] and e.levels["ask"] is None


def test_iceberg_new_level_resets_counters():
    e, _, s = mk_bid_flag()
    e.on_bid(s, 101.0, 7)
    lvl = e.levels["bid"]
    assert (lvl.price, lvl.start_seq, lvl.shown_max, lvl.traded, lvl.refills, lvl.pending,
            lvl.flagged, lvl.refill_sizes) == (101.0, s, 7, 0, 0, False, False, [])


@pytest.mark.parametrize("maker,onq,new_price,reason", [
    (mk_bid_flag, "on_bid", BP + 0.25, "held"),
    (mk_bid_flag, "on_bid", BP - 0.25, "broken"),
    (mk_ask_flag, "on_ask", AP - 0.25, "held"),
    (mk_ask_flag, "on_ask", AP + 0.25, "broken"),
])
def test_iceberg_price_change_finalizes_held_or_broken(maker, onq, new_price, reason):
    e, recs, s = maker()
    side = "bid" if maker is mk_bid_flag else "ask"
    out = getattr(e, onq)(s, new_price, 9)
    assert len(out) == 1
    f = fields(out[0])
    assert f[0] == "FINAL" and f[1] == side and f[10] == reason
    assert int(f[3]) == 1 and int(f[4]) == s            # start_seq, end_seq
    assert getattr(e.levels[side], "price") == new_price  # new level started at the new price
    assert e.levels[side].start_seq == s


def test_iceberg_price_change_new_level_not_started_on_zero():
    e, _, s = mk_bid_flag()
    out = e.on_bid(s, BP - 1.0, 0)
    assert len(out) == 1 and fields(out[0])[10] == "broken"
    assert e.levels["bid"] is None


def test_iceberg_size_zero_same_price_finalizes_broken():
    e, _, s = mk_bid_flag()
    out = e.on_bid(s, BP, 0)
    assert len(out) == 1 and fields(out[0])[10] == "broken" and int(fields(out[0])[4]) == s
    assert e.levels["bid"] is None
    e2, _, s2 = mk_ask_flag()
    out2 = e2.on_ask(s2, AP, 0)
    assert fields(out2[0])[1] == "ask" and fields(out2[0])[10] == "broken"


def test_iceberg_unflagged_level_finalizes_silently():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_trade(2, BP, 3, BP, AP)
    assert e.on_bid(3, BP, 0) == []
    e.on_bid(4, BP, 10)
    assert e.on_bid(5, BP + 0.25, 10) == []
    assert e.on_reset(6) == []


def test_iceberg_refill_requires_increase_after_trade():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_bid(2, BP, 15)                          # join: no trade since start -> not a refill
    assert e.levels["bid"].refills == 0 and e.levels["bid"].shown_max == 15
    e.on_trade(3, BP, 5, BP, AP)
    e.on_bid(4, BP, 10)                          # decrease: pending stays set
    assert e.levels["bid"].pending is True and e.levels["bid"].refills == 0
    e.on_bid(5, BP, 14)                          # increase after a trade -> refill
    lvl = e.levels["bid"]
    assert lvl.refills == 1 and lvl.refill_sizes == [14] and lvl.pending is False
    e.on_bid(6, BP, 18)                          # second increase, no new trade -> join
    assert lvl.refills == 1 and lvl.shown_max == 18 and lvl.last_shown == 18
    e.on_bid(7, BP, 18)                          # equal size: nothing
    assert lvl.refills == 1


def test_iceberg_min_refill_size_gate():
    e = IcebergEngine(min_refill_size=3)
    e.on_bid(1, BP, 10)
    e.on_trade(2, BP, 5, BP, AP)
    e.on_bid(3, BP, 12)                          # +2 < 3: ignored, still pending
    lvl = e.levels["bid"]
    assert lvl.refills == 0 and lvl.pending is True and lvl.last_shown == 12 and lvl.shown_max == 12
    e.on_bid(4, BP, 15)                          # +3 >= 3: counts
    assert lvl.refills == 1 and lvl.refill_sizes == [15]


def test_iceberg_ask_side_is_mirrored_for_refills():
    e = IcebergEngine()
    e.on_ask(1, AP, 10)
    e.on_trade(2, AP, 4, BP, AP)
    e.on_ask(3, AP, 6)
    e.on_ask(4, AP, 10)
    assert e.levels["ask"].refills == 1 and e.levels["bid"] is None


# ------------------------------------------------------------------------------ §3 T events
def test_iceberg_classification_seller_initiated_hits_bid_level():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_ask(2, AP, 10)
    e.on_trade(3, BP, 4, BP, AP)
    assert e.levels["bid"].traded == 4 and e.levels["bid"].pending is True
    assert e.levels["ask"].traded == 0 and e.unclassified == 0


def test_iceberg_classification_seller_below_bid_but_other_price_ignored():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_trade(2, BP - 0.25, 4, BP, AP)          # seller-initiated (x <= bid) but at another price
    assert e.levels["bid"].traded == 0 and e.unclassified == 0


def test_iceberg_classification_buyer_initiated_hits_ask_level():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_ask(2, AP, 10)
    e.on_trade(3, AP, 4, BP, AP)
    assert e.levels["ask"].traded == 4 and e.levels["ask"].pending is True
    assert e.levels["bid"].traded == 0


def test_iceberg_classification_buyer_with_unknown_bid_and_seller_with_unknown_ask():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_ask(2, AP, 10)
    e.on_trade(3, AP, 3, None, AP)               # buyer: ask known, x >= ask
    e.on_trade(4, BP, 2, BP, None)               # seller: bid known, x <= bid
    assert e.levels["ask"].traded == 3 and e.levels["bid"].traded == 2 and e.unclassified == 0


def test_iceberg_classification_inside_spread_is_unclassified():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_ask(2, 101.0, 10)
    assert e.on_trade(3, 100.5, 4, BP, 101.0) == []
    assert e.unclassified == 1
    assert e.levels["bid"].traded == 0 and e.levels["ask"].traded == 0


def test_iceberg_classification_unknown_quotes_are_unclassified():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_trade(2, BP, 4, None, None)
    assert e.unclassified == 1 and e.levels["bid"].traded == 0


def test_iceberg_classification_crossed_book_is_unclassified():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_ask(2, AP, 10)
    e.on_trade(3, 100.1, 4, 100.5, 100.0)        # bid > ask: both inequalities hold
    e.on_trade(4, 100.0, 4, 100.0, 100.0)        # locked: also both
    assert e.unclassified == 2
    assert e.levels["bid"].traded == 0 and e.levels["ask"].traded == 0


def test_iceberg_trades_at_other_prices_change_nothing():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_ask(2, AP, 10)
    e.on_trade(3, BP + 1.0, 5, BP, AP)           # buyer-initiated?  x >= ask -> yes, but not at ask level
    e.on_trade(4, BP - 1.0, 5, BP, AP)
    assert e.levels["bid"].traded == 0 and e.levels["ask"].traded == 0
    assert e.levels["bid"].pending is False and e.levels["ask"].pending is False


def test_iceberg_trade_without_level_is_noop():
    e = IcebergEngine()
    assert e.on_trade(1, BP, 5, BP, AP) == []
    assert e.unclassified == 0


def test_iceberg_price_tolerance_1e9():
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_bid(2, BP + 5e-10, 12)                  # same level
    assert e.levels["bid"].start_seq == 1 and e.levels["bid"].shown_max == 12
    e.on_trade(3, BP - 5e-10, 3, BP + 2e-10, AP)  # within tolerance of p
    assert e.levels["bid"].traded == 3
    e.on_trade(4, BP, 2, BP - 5e-10, AP)         # equality tolerance in classification (x > b by 5e-10)
    assert e.levels["bid"].traded == 5
    e.on_bid(5, BP + 2e-9, 10)                   # outside tolerance -> new level
    assert e.levels["bid"].start_seq == 5


# ------------------------------------------------------------------------------ §4 flag rule
def test_iceberg_flag_record_and_default_conf():
    e, recs, s = mk_bid_flag()
    assert recs == ["FLAG,bid,100.0000,%d,20,10,2,0.4000" % (s - 1)]
    e2, recs2, s2 = mk_ask_flag()
    assert recs2 == ["FLAG,ask,100.2500,%d,20,10,2,0.4000" % (s2 - 1)]


def test_iceberg_flag_gates_each_individually():
    # ratio gate: traded 19 < 2*10
    e = IcebergEngine(min_volume=1)
    e.on_bid(1, BP, 10)
    out = []
    for i in range(2):
        out += e.on_trade(2 + 4 * i, BP, 6, BP, AP) + e.on_bid(3 + 4 * i, BP, 4)
        out += e.on_trade(4 + 4 * i, BP, 3 if i else 4, BP, AP) + e.on_bid(5 + 4 * i, BP, 10)
    assert out == [] and e.levels["bid"].traded == 19 and e.levels["bid"].refills == 2
    # refills gate
    e = IcebergEngine(min_volume=1)
    e.on_bid(1, BP, 10)
    assert e.on_trade(2, BP, 50, BP, AP) == [] and e.levels["bid"].refills == 0
    # volume gate (MinVolume above traded)
    e, recs, _ = mk_bid_flag(min_volume=21)
    assert recs == []
    # shown_max grows via join: 20 < 2*15
    e = IcebergEngine()
    e.on_bid(1, BP, 10)
    e.on_bid(2, BP, 15)
    for i in range(2):
        e.on_trade(3 + 3 * i, BP, 10, BP, AP)
        e.on_bid(4 + 3 * i, BP, 5)
        e.on_bid(5 + 3 * i, BP, 15)
    assert e.levels["bid"].refills == 2 and e.levels["bid"].traded == 20 and not e.levels["bid"].flagged


def test_iceberg_flag_is_emitted_once():
    e, recs, s = mk_bid_flag()
    assert len(recs) == 1
    more = e.on_trade(s, BP, 30, BP, AP) + e.on_bid(s + 1, BP, 4) + e.on_bid(s + 2, BP, 10)
    assert more == [] and e.levels["bid"].traded == 50


def test_iceberg_conf_formula_unclamped():
    # hidden_ratio 1.0, min_refills 1: flag at the refill with traded 15, shown_max 10, refills 1
    e = IcebergEngine(hidden_ratio=1.0, min_refills=1, min_volume=1)
    e.on_bid(1, BP, 10)
    e.on_trade(2, BP, 5, BP, AP)
    e.on_bid(3, BP, 5)
    e.on_trade(4, BP, 5, BP, AP)
    assert e.on_trade(5, BP, 5, BP, AP) == []
    out = e.on_bid(6, BP, 10)
    assert out == ["FLAG,bid,100.0000,6,15,10,1,%.4f" % (0.4 + 0.15 * 0 + 0.1 * (1.5 - 1.0))]
    assert fields(out[0])[-1] == "0.4500"


def test_iceberg_conf_formula_with_extra_refills_and_ratio():
    # min_refills 1, flagged at refills 1; FINAL later shows refills 3, traded 50: 0.4+0.3+0.1*(5-1)=1.1 -> 1.0
    e = IcebergEngine(hidden_ratio=1.0, min_refills=1, min_volume=1)
    e.on_bid(1, BP, 10)
    e.on_trade(2, BP, 5, BP, AP)
    e.on_bid(3, BP, 5)
    e.on_trade(4, BP, 5, BP, AP)
    e.on_bid(5, BP, 10)                           # flag: traded 10, refills 1 -> 0.4
    # refills 2 and 3 (after the flag), traded 24: conf = 0.4 + 0.15*(3-1) + 0.1*(2.4-1.0) = 0.84
    e.on_trade(6, BP, 7, BP, AP); e.on_bid(7, BP, 3); e.on_bid(8, BP, 10)
    e.on_trade(9, BP, 7, BP, AP); e.on_bid(10, BP, 3); e.on_bid(11, BP, 10)
    fin = e.on_bid(12, BP + 0.25, 3)
    f = fields(fin[0])
    assert f[0] == "FINAL" and int(f[5]) == 24 and int(f[8]) == 3
    assert float(f[-1]) == pytest.approx(0.84, abs=1e-4)


def test_iceberg_conf_clamps_at_one():
    e, recs, s = mk_bid_flag()
    for i in range(10):
        e.on_trade(s + 3 * i, BP, 6, BP, AP)
        e.on_bid(s + 3 * i + 1, BP, 4)
        e.on_bid(s + 3 * i + 2, BP, 10)
    f = fields(e.on_bid(s + 40, BP - 0.25, 5)[0])
    assert f[-1] == "1.0000" and int(f[8]) == 12 and int(f[5]) == 80


# ------------------------------------------------------------------------------ §5/§6 FINAL
def test_iceberg_final_record_fields():
    e, recs, s = mk_bid_flag()
    out = e.on_bid(s + 5, BP - 0.25, 12)
    assert out == ["FINAL,bid,100.0000,1,%d,20,10,10,2,10.0000,broken,0.4000" % (s + 5)]
    e2, _, s2 = mk_ask_flag()
    out2 = e2.on_ask(s2, AP - 0.5, 12)
    assert out2 == ["FINAL,ask,100.2500,1,%d,20,10,10,2,10.0000,held,0.4000" % s2]


def _flag_with_refills(sizes):
    """Level flagged by its first trade (hidden_ratio 0.1, min_refills 0, min_volume 1), then given refill sizes."""
    e = IcebergEngine(hidden_ratio=0.1, min_refills=0, min_volume=1)
    e.on_bid(1, BP, 2)
    s = 2
    last = 2
    for r in sizes:
        e.on_trade(s, BP, 1, BP, AP); s += 1
        e.on_bid(s, BP, 1); s += 1                  # decrease so the refill is an increase
        e.on_bid(s, BP, r); s += 1
    return e, s


def test_iceberg_median_odd_even_empty():
    e, s = _flag_with_refills([3, 9, 5])           # sorted 3,5,9 -> 5
    assert fields(e.on_reset(s)[0])[9] == "5.0000"
    e, s = _flag_with_refills([4, 10, 20, 6])      # sorted 4,6,10,20 -> 8
    assert fields(e.on_reset(s)[0])[9] == "8.0000"
    e, s = _flag_with_refills([4, 7])              # even, non-integer mean
    assert fields(e.on_reset(s)[0])[9] == "5.5000"
    e = IcebergEngine(hidden_ratio=1.0, min_refills=0, min_volume=1)
    e.on_bid(1, BP, 10)
    assert fields(e.on_trade(2, BP, 10, BP, AP)[0])[0] == "FLAG"
    assert fields(e.on_reset(3)[0])[9] == "0.0000"


def test_iceberg_reset_finalizes_open_bid_before_ask():
    e, _, s = mk_bid_flag()
    mk_ask_flag(eng=e, seq0=s)
    s += 100
    out = e.on_reset(s)
    assert [fields(r)[1] for r in out] == ["bid", "ask"]
    assert all(fields(r)[10] == "open" and int(fields(r)[4]) == s for r in out)
    assert e.levels == {"bid": None, "ask": None}
    assert e.on_trade(s + 1, BP, 5, BP, AP) == [] and e.unclassified == 0


def test_iceberg_reset_discards_unflagged_and_empty():
    e = IcebergEngine()
    assert e.on_reset(1) == []
    e.on_bid(2, BP, 5)
    assert e.on_reset(3) == []
    assert e.levels["bid"] is None


def test_iceberg_record_order_bid_before_ask_and_new_level_after_reset_is_fresh():
    e, _, s = mk_ask_flag()
    mk_bid_flag(eng=e, seq0=s)
    out = e.on_reset(1000)
    assert [fields(r)[1] for r in out] == ["bid", "ask"]
    e.on_bid(1001, BP, 10)
    assert e.levels["bid"].start_seq == 1001


def test_iceberg_final_precedes_flag_when_one_event_does_both():
    # With all gates at zero a *new* level is not evaluated at start (spec 3.1b has no flag step),
    # so a single event never yields FINAL then FLAG; verify the FINAL comes out alone.
    e = IcebergEngine(hidden_ratio=0.0, min_refills=0, min_volume=0)
    e.on_bid(1, BP, 10)
    assert e.on_trade(2, BP, 1, BP, AP)[0].startswith("FLAG")
    out = e.on_bid(3, BP + 0.25, 5)
    assert [fields(r)[0] for r in out] == ["FINAL"]
    out2 = e.on_bid(4, BP + 0.25, 6)               # 2c on the new level: flag evaluated, FLAG emitted
    assert [fields(r)[0] for r in out2] == ["FLAG"]


def test_iceberg_final_hidden_est_is_traded_minus_shown_max():
    e, _, s = mk_bid_flag()
    e.on_trade(s, BP, 30, BP, AP)
    f = fields(e.on_bid(s + 1, BP - 0.25, 1)[0])
    assert int(f[5]) == 50 and int(f[6]) == 10 and int(f[7]) == 40


# ------------------------------------------------------------------------------ stream helpers
def test_iceberg_run_stream_csv_roundtrip_and_cli(tmp_path, capsys):
    rows, truth = booksim.simulate_session(random.Random(5))
    p = tmp_path / "s.csv"
    from qibt.iceberg import write_stream_csv
    write_stream_csv(p, rows)
    back = read_stream_csv(p)
    assert back == rows
    assert run_stream(back) == run_stream(rows)
    iceberg_main([str(p)])
    out = capsys.readouterr().out.splitlines()
    assert out == run_stream(rows) and len(out) > 0
    iceberg_main([str(p), "--hidden-ratio", "1.0", "--min-refills", "0"])
    assert capsys.readouterr().out.splitlines() == run_stream(rows, hidden_ratio=1.0, min_refills=0)


def test_iceberg_read_stream_csv_blank_fields(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("seq,type,price,size,bid,ask\n1,R,,,,\n2,B,100,10,,\n3,T,100,4,100,\n")
    assert read_stream_csv(p) == [(1, "R", None, None, None, None), (2, "B", 100.0, 10, None, None),
                                  (3, "T", 100.0, 4, 100.0, None)]


# ------------------------------------------------------------------------------ simulator
@pytest.fixture(scope="module")
def sessions200():
    return booksim.simulate(200, SEED)


def test_iceberg_booksim_deterministic_same_seed():
    a = booksim.simulate(6, SEED)
    b = booksim.simulate(6, SEED)
    assert a == b
    assert booksim.simulate(2, SEED + 1) != booksim.simulate(2, SEED)


def test_iceberg_booksim_cli_writes_identical_files(tmp_path):
    d1, d2 = tmp_path / "a", tmp_path / "b"
    booksim.main(["--sessions", "3", "--seed", str(SEED), "--out", str(d1)])
    booksim.main(["--sessions", "3", "--seed", str(SEED), "--out", str(d2)])
    for name in ("session_000.csv", "session_001.csv", "session_002.csv", "truth.json"):
        assert (d1 / name).read_bytes() == (d2 / name).read_bytes()
    assert read_stream_csv(d1 / "session_000.csv") == booksim.simulate(3, SEED)[0][0]


def test_iceberg_booksim_streams_are_wellformed(sessions200):
    for rows, truth in sessions200[:40]:
        assert [r[0] for r in rows] == list(range(1, len(rows) + 1))
        bid = ask = None
        for seq, typ, price, size, b, a in rows:
            assert typ in "BATR"
            if typ in "BA":
                assert size >= 0 and abs(price / booksim.TICK - round(price / booksim.TICK)) < 1e-9
                if typ == "B":
                    bid = price
                else:
                    ask = price
                if bid is not None and ask is not None:
                    assert bid < ask, "crossed book at seq %d" % seq
            elif typ == "T":
                assert size > 0
        for t in truth:
            assert 1 <= t["start_seq"] <= t["end_seq"] <= len(rows)
            assert t["kind"] in booksim.KINDS and t["side"] in ("bid", "ask")


def test_iceberg_booksim_mix_per_session(sessions200):
    for _, truth in sessions200:
        kinds = [t["kind"] for t in truth]
        assert 2 <= kinds.count("iceberg") <= 4
        for k in booksim.KINDS[1:]:
            assert 1 <= kinds.count(k) <= 3


def test_iceberg_booksim_planted_parameters_in_range(sessions200):
    for _, truth in sessions200:
        for t in truth:
            if t["kind"] == "iceberg":
                assert 100 <= t["hidden_total"] <= 400 and 5 <= t["clip"] <= 20
            elif t["kind"] == "decoy_large":
                assert 150 <= t["shown"] <= 300 and t["traded"] < t["shown"]
            elif t["kind"] == "decoy_join":
                assert t["traded"] < 2 * t["shown_max"]
            else:
                assert 2 <= t["clip"] <= 4 and t["executed"] < 20


# ------------------------------------------------------------------------------ I3
def test_iceberg_i3_recall_and_false_alarm_at_defaults(sessions200):
    res = evaluate(sessions200)
    assert res["n_icebergs"] > 400 and res["n_decoys"] > 800
    assert res["recall"] >= 0.90, res
    assert res["false_alarm_rate"] <= 0.10, res


def test_iceberg_i3_falsifier_loose_params_raise_false_alarms(sessions200):
    res = evaluate(sessions200, hidden_ratio=1.0, min_refills=0)
    assert res["false_alarm_rate"] > 0.10, res
    assert sum(res["per_kind"][k]["flagged"] for k in booksim.KINDS[1:]) > 0   # it really fires
    base = evaluate(sessions200)
    assert res["false_alarm_rate"] > base["false_alarm_rate"]


# ------------------------------------------------------------------------------ I4 no look-ahead
def per_event_records(rows, **params):
    eng = IcebergEngine(**params)
    return [feed(eng, r) for r in rows]


def test_iceberg_i4_prefix_equals_full_run_prefix(sessions200):
    rnd = random.Random(4)
    nontrivial = 0
    for rows, _ in sessions200[:12]:
        per_event = per_event_records(rows)
        cuts = [1, len(rows)] + [rnd.randint(1, len(rows)) for _ in range(6)]
        for k in cuts:
            want = [r for emitted in per_event[:k] for r in emitted]
            assert run_stream(rows[:k]) == want
            nontrivial += 1 if want else 0
    assert nontrivial > 20


def test_iceberg_i4_prefix_equals_with_nondefault_params(sessions200):
    rows, _ = sessions200[7]
    params = dict(hidden_ratio=1.0, min_refills=0, min_volume=5, min_refill_size=2)
    per_event = per_event_records(rows, **params)
    for k in (10, 100, len(rows) // 2, len(rows)):
        want = [r for emitted in per_event[:k] for r in emitted]
        assert run_stream(rows[:k], **params) == want


def test_iceberg_i4_flags_never_depend_on_later_events():
    rows, _ = booksim.simulate_session(random.Random(11))
    full = per_event_records(rows)
    flagged_at = [i for i, em in enumerate(full) if any(r.startswith("FLAG") for r in em)]
    assert flagged_at
    k = flagged_at[0] + 1
    assert any(r.startswith("FLAG") for r in run_stream(rows[:k]))
    assert not any(r.startswith("FLAG") and int(r.split(",")[3]) > k for r in run_stream(rows[:k]))
    assert run_stream(rows[:k - 1]) == [r for em in full[:k - 1] for r in em]
