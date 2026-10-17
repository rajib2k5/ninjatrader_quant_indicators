"""Stationary block bootstrap (qibt/bootstrap.py): determinism, degenerate series, block structure."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from qibt import bootstrap as bs


def _x(n=300, k=4, seed=0):
    rng = np.random.default_rng(seed)
    return rng.normal(0.5, 10.0, (n, k))


def test_seed_determinism():
    X = _x()
    a = bs.bootstrap_sharpe(X, 50, 10.0, seed=12345)
    b = bs.bootstrap_sharpe(X, 50, 10.0, seed=12345)
    c = bs.bootstrap_sharpe(X, 50, 10.0, seed=12346)
    assert np.array_equal(a, b) and not np.array_equal(a, c)
    assert bs.SEED == 12345 and bs.MEAN_BLOCK == 10.0 and bs.N_RESAMPLES == 1000


def test_indices_valid_and_circular():
    rng = np.random.default_rng(1)
    idx = bs.stationary_indices(50, 10.0, rng)
    assert len(idx) == 50 and idx.min() >= 0 and idx.max() < 50
    step = (idx[1:] == (idx[:-1] + 1) % 50)
    assert step.mean() > 0.6                          # mostly continuation, wrapping allowed


def test_zero_variance_series_never_ranks_first():
    X = _x(200, 3)
    X = np.column_stack([X, np.full(200, -2.25)])     # a rule that loses the same every day
    sr = bs.bootstrap_sharpe(X, 100, 10.0, seed=3)
    assert np.isnan(sr[:, 3]).all() and np.isfinite(sr[:, :3]).all()
    p = bs.p_first(sr)
    assert p[3] == 0.0 and p.sum() == pytest.approx(1.0)
    assert (bs.ranks(sr)[:, 3] == 4).all()
    assert all(math.isnan(v) for v in bs.interval(sr[:, 3]))
    s = bs.summarize(sr, ["a", "b", "c", "flat"], ["a", "b", "c", "flat"], top_k=4, top_pairs=4)
    assert s["p_rank1"]["flat"] == 0.0 and s["pairs"][-1][2] == 1.0


def check_iid(index_fn, n=4000, seed=7):
    """mean_block = 1: every day starts a new block, so the indices equal the iid reference
    draws (integers at k=0, then random() + integers() per day) and continuation is ~1/n."""
    idx = index_fn(n, 1.0, np.random.default_rng(seed))
    rng = np.random.default_rng(seed)
    ref = [int(rng.integers(n))]
    for _ in range(1, n):
        rng.random()
        ref.append(int(rng.integers(n)))
    cont = float(np.mean(idx[1:] == (idx[:-1] + 1) % n))
    return list(idx) == ref and cont < 0.01


def test_block_length_1_is_iid_resampling():
    assert check_iid(bs.stationary_indices)


def test_mean_block_sets_the_restart_rate():
    n, L = 100_000, 10.0
    idx = bs.stationary_indices(n, L, np.random.default_rng(5))
    cont = np.mean(idx[1:] == (idx[:-1] + 1) % n)
    assert cont == pytest.approx(1 - 1 / L, abs=0.005)


def test_all_rules_share_the_day_indices():
    x = _x(250, 1)[:, 0]
    X = np.column_stack([x, x, 2 * x])                 # identical / scaled copies
    sr = bs.bootstrap_sharpe(X, 200, 10.0, seed=9)
    assert np.array_equal(sr[:, 0], sr[:, 1]) and np.allclose(sr[:, 0], sr[:, 2])
    assert bs.p_greater(sr, 0, 1) == 0.0 and bs.p_greater(sr, 1, 0) == 0.0


def test_summary_hand_values():
    sr = np.array([[3.0, 2.0, 1.0],
                   [1.0, 2.0, 3.0],
                   [2.0, 3.0, 1.0],
                   [3.0, 1.0, np.nan]])
    names = ["A", "B", "C"]
    s = bs.summarize(sr, names, ["A", "B", "C"], top_k=2, top_pairs=3)
    assert s["p_rank1"] == {"A": 0.5, "B": 0.25, "C": 0.25}
    # top 2 = A, B: A wins rows 0 and 3, B rows 1 and 2; NaN ranks last (row 3: B > C)
    assert s["p_first_top"] == {"A": 0.5, "B": 0.5}
    assert s["p_exact_top"] == 0.5
    assert s["pairs"] == [("A", "B", 0.5), ("B", "C", 0.75)]
    assert s["ci"]["C"] == pytest.approx(tuple(np.percentile([1.0, 3.0, 1.0], [5, 95])))


def test_run_files_and_render(tmp_path):
    X = _x(120, 3, seed=11)
    d = pd.DataFrame(X, columns=["A", "B", "C"])
    d.insert(0, "date", pd.bdate_range("2024-01-01", periods=120).strftime("%Y-%m-%d"))
    d["BuyHold"] = 1.0
    d.to_csv(tmp_path / "daily.csv", index=False)
    pd.DataFrame({"rank": [1, 2, 3, 4], "module": ["B", "A", "C", "Chop"], "status": ["ok", "ok", "ok", "not_backtestable"],
                  "sr": [0.9, 0.5, 0.1, np.nan]}).to_csv(tmp_path / "ranking.csv", index=False)
    s, pub, n = bs.run_files(tmp_path / "daily.csv", tmp_path / "ranking.csv", 40, 5.0, 1)
    assert n == 120 and list(s["p_first_top"])[:3] == ["B", "A", "C"] and set(s["p_rank1"]) == {"A", "B", "C"}
    txt = bs.render(s, pub, dict(label="t", mean_block=5.0, resamples=40, seed=1, days=n, daily="d", ranking="r"))
    assert "P(rank 1 of 3)" in txt and "| 1 vs 2 | B > A |" in txt and "%%" not in txt


# --------------------------------------------------------------------------------------------
# falsifiers
# --------------------------------------------------------------------------------------------
def test_falsifier_never_restarting_blocks_is_detected():
    """A circular shift with one random start (no restarts) is not iid at block length 1."""
    def circular(n, mean_block, rng):
        i = int(rng.integers(n))
        return (i + np.arange(n)) % n
    assert not check_iid(circular)


def test_falsifier_independent_indices_per_rule_is_detected():
    """Resampling each rule on its own day indices breaks the joint structure: identical rules
    would get different SRs."""
    x = _x(250, 1)[:, 0]
    X = np.column_stack([x, x])
    rng = np.random.default_rng(9)
    sr = np.array([[bs.sharpe_columns(X[bs.stationary_indices(250, 10.0, rng)][:, [j]])[0] for j in range(2)]
                   for _ in range(50)])
    assert not np.array_equal(sr[:, 0], sr[:, 1])
