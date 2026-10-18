"""Ranking and tie rule (PROTOCOL section 8)."""
from __future__ import annotations

import importlib.util
import math

import pandas as pd
import pytest

from conftest import BACKTEST_DIR
from qibt import rank

NAN = math.nan


def rows(*spec):
    return [dict(module=m, sr=s, dsr=d, status="ok") for m, s, d in spec]


TIE_FIXTURE = rows(("Alpha", 1.000, 0.20), ("Bravo", 0.997, 0.60), ("Delta", 0.50, 0.10),
                   ("Charlie", 0.50, 0.10), ("Echo", -0.30, 0.0))
TIE_WANT = ["Bravo", "Alpha", "Charlie", "Delta", "Echo"]


def names(rs):
    return [r["module"] for r in rs]


def test_tie_rule_dsr_then_name():
    assert names(rank.order_rules(TIE_FIXTURE)) == TIE_WANT


def test_tie_threshold_is_strict():
    r = rows(("A", 0.5, 0.0), ("B", 0.505, 0.9))      # |dSR| = 0.005 is NOT a tie (0.505-0.5 >= 0.005)
    assert names(rank.order_rules(r)) == ["B", "A"]
    r = rows(("A", 0.5049, 0.0), ("B", 0.5, 0.9))     # |dSR| < 0.005 -> DSR decides
    assert names(rank.order_rules(r)) == ["B", "A"]
    r = rows(("A", 0.5049, 0.9), ("B", 0.5, 0.0))
    assert names(rank.order_rules(r)) == ["A", "B"]


def test_nan_dsr_loses_a_tie_and_nan_sr_goes_last():
    r = rows(("A", 0.300, NAN), ("B", 0.299, 0.1), ("C", NAN, 0.9), ("D", -2.0, 0.0), ("Ab", NAN, 0.0))
    assert names(rank.order_rules(r)) == ["B", "A", "D", "Ab", "C"]


def test_rank_table_non_backtestable_last_and_names():
    rr = rows(*[("M%02d" % i, 1.0 - i * 0.1, 0.5) for i in range(25)])
    nb = [{"module": "KeyLevels", "reason": "levels"}, {"module": "ChopIndex", "reason": "state"}]
    t = rank.rank_table(rr, nb)
    assert [r["rank"] for r in t] == list(range(1, 28))
    assert [r["module"] for r in t[-2:]] == ["ChopIndex", "KeyLevels"]
    assert t[0]["qi"] == "QI_01_M00" and t[-1]["qs"] == "QS_27_KeyLevels" and t[-1]["qiv"] == "QIV_27_KeyLevels"


def test_pending_rules_get_no_rank_and_do_not_shift_the_last_numbers():
    rr = rows(("A", 0.5, 0.1), ("B", 0.2, 0.1)) + [dict(module="P", sr=NAN, dsr=NAN, status="pending")]
    t = rank.rank_table(rr, [{"module": "ChopIndex"}])
    by = {r["module"]: r["rank"] for r in t}
    assert by == {"A": 1, "B": 2, "P": None, "ChopIndex": 4}


def test_ranking_csv_is_accepted_by_relabel(tmp_path):
    path = BACKTEST_DIR / "relabel.py"
    if not path.exists():
        pytest.skip("backtest/relabel.py not present")
    spec = importlib.util.spec_from_file_location("relabel_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rr = rows(*[("M%02d" % i, 1.0 - i * 0.1, 0.5) for i in range(25)])
    t = pd.DataFrame(rank.rank_table(rr, [{"module": "ChopIndex"}, {"module": "KeyLevels"}]))
    t["rank"] = t["rank"].astype("Int64")
    t.to_csv(tmp_path / "ranking.csv", index=False)
    got = mod.load_ranking(tmp_path / "ranking.csv")
    assert got["M00"]["qi"] == "QI_01_M00" and got["KeyLevels"]["rank"] == 27


# --------------------------------------------------------------------------------------------
# falsifiers
# --------------------------------------------------------------------------------------------
def test_falsifier_plain_sr_sort_is_detected():
    plain = sorted(TIE_FIXTURE, key=lambda r: -r["sr"])
    assert names(plain) != TIE_WANT


def test_falsifier_name_before_dsr_is_detected():
    wrong = sorted(TIE_FIXTURE, key=lambda r: (-round(r["sr"], 2), r["module"]))
    assert names(wrong) != TIE_WANT


def test_tiny_dsr_decides_the_tie():
    """v1 P1 case (Channel B F2): |dSR| < 0.005 and DSR 3.3e-58 vs 1.7e-59 -> the higher DSR first."""
    r = [dict(module="ConsecDays", sr=0.568885, dsr=1.7082e-59, status="ok"),
         dict(module="IBS", sr=0.565508, dsr=3.2798e-58, status="ok")]
    assert names(rank.order_rules(r)) == ["IBS", "ConsecDays"]


def test_dsr_log_decides_when_dsr_underflowed_to_zero():
    r = [dict(module="A", sr=0.5001, dsr=0.0, dsr_log=-900.0, status="ok"),
         dict(module="B", sr=0.5000, dsr=0.0, dsr_log=-850.0, status="ok")]
    assert names(rank.order_rules(r)) == ["B", "A"]
    r = [dict(module="A", sr=0.5001, dsr=0.0, status="ok"), dict(module="B", sr=0.5, dsr=0.0, status="ok")]
    assert names(rank.order_rules(r)) == ["A", "B"]          # both exactly 0, no log: A->Z


def test_falsifier_dsr_rounded_to_zero_is_detected():
    """Comparing the 3-decimal (or underflowed) DSR falls back to A->Z and gets the v1 order wrong."""
    r = [dict(module="ConsecDays", sr=0.568885, dsr=1.7082e-59), dict(module="IBS", sr=0.565508, dsr=3.2798e-58)]
    rounded = sorted(r, key=lambda x: (-round(x["dsr"], 3), x["module"]))
    assert names(rounded) != names(rank.order_rules([dict(x, status="ok") for x in r]))
