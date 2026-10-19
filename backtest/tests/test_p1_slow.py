"""End-to-end on P1 (slow; skipped when the vendor files are absent): determinism (ledger BT18),
reconciliation of daily P&L with the bar ledger, and the session facts BT4/BT17 rely on."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bt_helpers import p1_available
from qibt import cli, data, engine, signals

pytestmark = [pytest.mark.slow,
              pytest.mark.skipif(not p1_available(), reason="P1 files not present")]


@pytest.fixture(scope="module")
def two_runs():
    rs = signals.load_rules()
    a = cli.run_pipeline(data.load_p1(), rs)
    b = cli.run_pipeline(data.load_p1(), rs)     # second independent load (cache) + run
    return a, b


def test_p1_bars_unique_sorted_and_outside_the_halt(p1_minute):
    t = p1_minute["BarTime"]
    assert t.is_unique and t.is_monotonic_increasing
    assert not data.halt_mask(t).any()
    assert p1_minute[["Open", "High", "Low", "Close"]].notna().all().all()


def test_determinism_two_runs_identical(two_runs):
    a, b = two_runs
    ma, mb = a["metrics"], b["metrics"]
    assert list(ma["module"]) == list(mb["module"]) and list(ma["status"]) == list(mb["status"])
    num = ma.select_dtypes("number").columns
    np.testing.assert_allclose(ma[num].to_numpy(float), mb[num].to_numpy(float), rtol=0, atol=1e-9)
    da, db = a["daily"], b["daily"]
    assert list(da.columns) == list(db.columns)
    np.testing.assert_allclose(da.iloc[:, 1:].to_numpy(float), db.iloc[:, 1:].to_numpy(float), rtol=0, atol=1e-9)
    assert [(r["rank"], r["module"]) for r in a["ranking"]] == [(r["rank"], r["module"]) for r in b["ranking"]]


def _loop_ledger(frame, pos, cal):
    """Independent bar loop over execution bars j = 1..n-1 in the window: P&L p_{j-1}(O_{j+1}-O_j)*5
    (none on the last bar, which has no O_{j+1}) and |p_{j-1} - p_{j-2}| sides, counting every
    executed position change exactly once (incl. one executed at the last bar's open)."""
    o = frame["Open"].to_numpy(float)
    td = pd.DatetimeIndex(frame["TradingDate"])
    inwin = set(cal)
    gross = sides = changes = 0.0
    prev = 0.0
    for j in range(1, len(o)):
        p = float(pos[j - 1])
        if td[j] in inwin:
            if j < len(o) - 1:
                gross += p * (o[j + 1] - o[j]) * 5.0
            sides += abs(p - prev)
            changes += p != prev
        prev = p
    return gross, sides, changes


def test_reconciliation_daily_sum_equals_bar_ledger(two_runs):
    res, _ = two_runs
    cal = res["calendar"]
    m = res["metrics"].set_index("module")
    for mod, r in res["results"].items():
        if r["status"] != "ok":
            continue
        rule = next(x for x in signals.load_rules().rules if x.module == mod)
        g, s, c = _loop_ledger(res["frames"][rule.frame], r["positions"], cal)
        daily_sum = res["daily"][mod].sum()
        assert daily_sum == pytest.approx(g - s * engine.COST_PER_SIDE, abs=1e-6), mod
        assert m.loc[mod, "sides"] == s and m.loc[mod, "changes"] == c, mod
        assert m.loc[mod, "gross_pnl"] == pytest.approx(g, abs=1e-6), mod
    g, s, c = _loop_ledger(res["frames"]["D"], res["benchmark_positions"], cal)
    assert (s, c) == (1.0, 1.0)
    assert res["daily"][cli.BENCH].sum() == pytest.approx(g - engine.COST_PER_SIDE, abs=1e-6)


def test_every_window_date_present_once(two_runs):
    res, _ = two_runs
    d = pd.to_datetime(res["daily"]["date"])
    assert d.is_unique and d.is_monotonic_increasing
    assert d.iloc[0] == pd.Timestamp("2021-01-04") and d.iloc[-1] == pd.Timestamp("2026-02-24")
    assert len(d) == len(res["calendar"])


def test_cli_run_on_p1_writes_outputs(tmp_path):
    assert cli.main(["run", "--dataset", "P1", "--costs", "1", "--out", str(tmp_path)]) == 0
    for name in ("metrics_P1.csv", "daily_pnl_P1.csv", "ranking.csv", "REPORT.md"):
        assert (tmp_path / name).exists(), name
    rk = pd.read_csv(tmp_path / "ranking.csv")
    assert len(rk) == 27 and rk["module"].iloc[-2:].tolist() == ["ChopIndex", "KeyLevels"]


def test_settle_close_branches_on_p1(two_runs):
    """A1: the inferred settlement close is on the 0.25 grid on ~98.9% of window dates
    (validation/adversarial-ranking.md section 5); fallbacks are named."""
    res, _ = two_runs
    assert res["close_mode"] == "settle"
    w = res["close_report"]["window"]
    assert w["dates"] == len(res["calendar"])
    assert w["source"].get("settle", 0) / w["dates"] >= 0.985
    assert set(w["fallback_reason"]) <= {"off_grid", "ibs_missing", "h_eq_l"}
    assert sum(w["source"].values()) == w["dates"]


def test_bootstrap_reproduces_the_validators_v1_numbers(tmp_path):
    """Independent cross-check: validation/adversarial-ranking.md section 6 (own code, same draw
    order, seed 12345) published these numbers for the v1 (16:00 last-trade) ranking."""
    from qibt import bootstrap as bs
    res = cli.run_pipeline(data.load_p1(), signals.load_rules(), close_mode="last")
    res["daily"].to_csv(tmp_path / "daily.csv", index=False)
    rk = pd.DataFrame(res["ranking"]).reindex(columns=["rank", "module", "status", "sr"])
    rk.to_csv(tmp_path / "ranking.csv", index=False)
    s, _, n = bs.run_files(tmp_path / "daily.csv", tmp_path / "ranking.csv", 1000, 10.0, 12345)
    assert n == 1320
    assert {k: round(float(v), 3) for k, v in s["p_first_top"].items()} == {
        "RSI14": 0.520, "RSI2": 0.145, "ConsecDays": 0.188, "IBS": 0.147}
    assert tuple(round(x, 2) for x in s["ci"]["RSI14"]) == (0.27, 1.56)
    assert round(float(s["p_rank1"]["RSI14"]), 3) == 0.392
    # The validator ran on the pre-F3 engine (last-bar execution not charged) and the pre-F2 order
    # (ConsecDays 3, IBS 4). Rebuild exactly that input: add back the one charged last-bar side.
    names = [c for c in res["daily"].columns if c not in ("date", cli.BENCH)]
    X = res["daily"][names].to_numpy(float).copy()
    rules = {r.module: r for r in signals.load_rules().rules}
    for j, mod in enumerate(names):
        pos = res["results"][mod]["positions"].astype(float)
        X[-1, j] += abs(pos[-2] - pos[-3]) * engine.COST_PER_SIDE      # last bar is on the last date
        assert res["frames"][rules[mod].frame]["TradingDate"].iloc[-1] == res["calendar"][-1]
    ix = {k: i for i, k in enumerate(names)}
    top = [ix[k] for k in ("RSI14", "RSI2", "ConsecDays", "IBS")]
    pre = bs.bootstrap_sharpe(X, 1000, 10.0, 12345)
    assert round(bs.p_order(pre, top), 3) == 0.122
    assert [round(bs.p_greater(pre, a, b), 3) for a, b in zip(top, top[1:])] == [0.710, 0.604, 0.504]
    post = bs.bootstrap_sharpe(res["daily"][names].to_numpy(float), 1000, 10.0, 12345)
    assert abs(bs.p_order(post, top) - 0.122) <= 0.002                    # F3 moves SRs by < 3e-4


def test_cli_bootstrap_and_sensitivity_subcommands_on_p1(tmp_path):
    for close, sub in (("settle", "."), ("last", "v1_last_trade"), ("1500", "close_1500")):
        for c in ("0", "1", "2"):
            assert cli.main(["run", "--dataset", "P1", "--costs", c, "--close", close, "--out", str(tmp_path / sub)]) == 0
    assert cli.main(["bootstrap", "--results", str(tmp_path), "--resamples", "50"]) == 0
    assert cli.main(["sensitivity", "--results", str(tmp_path)]) == 0
    assert "P(exact published top-4 order" in (tmp_path / "BOOTSTRAP.md").read_text(encoding="utf-8")
    assert (tmp_path / "SENSITIVITY.md").read_text(encoding="utf-8").count("\n### ") == 25


def test_v1_tie_is_decided_by_dsr(tmp_path):
    """Channel B F2: v1 ConsecDays/IBS are an SR tie (|dSR| < 0.005); DSR(IBS) ~ 3.28e-58 >
    DSR(ConsecDays) ~ 1.71e-59 (scipy norm.cdf), so the frozen section 8 rule puts IBS 3rd."""
    res = cli.run_pipeline(data.load_p1(), signals.load_rules(), close_mode="last")
    m = res["metrics"].set_index("module")
    assert abs(m.loc["ConsecDays", "sr"] - m.loc["IBS", "sr"]) < 0.005
    assert m.loc["IBS", "dsr"] == pytest.approx(3.28e-58, rel=0.01)
    assert m.loc["ConsecDays", "dsr"] == pytest.approx(1.71e-59, rel=0.01)
    order = [r["module"] for r in res["ranking"]][:4]
    assert order == ["RSI14", "RSI2", "IBS", "ConsecDays"]
    ok = m["status"] == "ok"
    assert np.isfinite(m.loc[ok, "dsr_log"].astype(float)).all()           # ordered even if Phi underflows
    assert (m.loc[ok & (m["frame"] == "D"), "dsr"] > 0).all()
