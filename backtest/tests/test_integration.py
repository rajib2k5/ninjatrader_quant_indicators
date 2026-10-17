"""End-to-end on a deterministic synthetic dataset with hand-computed golden numbers.

Dataset: trading dates Mon 2024-01-08 .. Fri 2024-01-19 (10 dates, index i = 0..9). Each date d has
three 1-minute bars closing at (d-1 calendar day) 17:01, d 09:00 and d 16:00 (Mondays: Sunday 17:01).
D-frame opens O_i = 100 102 101 105 104 108 110 107 111 115; the three bars of date i open at
O_i, O_i + 1, O_i + 2, so each 1-minute bar is its own 15m bar and 15m bar k = 3i + b opens at O_i + b.

Toy rules (all on day_of_week of the trading date, Monday = 1):
    Alpha   D   long x == 1 (Monday close -> hold Tuesday), short never
    Bravo   D   long x <= 2, short x >= 3 (flips long <-> short)
    Charlie 15m long x == 2 (every Tuesday 15m bar), short never
Window 2024-01-09 .. 2024-01-18 (8 days), H1 01-09..01-12, H2 01-15..01-18, cost USD 2.25/side.

Hand computation, bar j = t+1, gross = p_t (O_{t+2} - O_{t+1}) * 5, cost = |p_t - p_{t-1}| * 2.25:
  Alpha: p = 1 0 0 0 0 1 0 0 0 0
    01-09: 1*(101-102)*5 = -5, entry 1 side -> -7.25 | 01-10: exit 1 side -> -2.25
    01-16: 1*(107-110)*5 = -15, entry -> -17.25     | 01-17: exit -> -2.25 ; others 0
    total -29.00 (gross -20, costs 9.00, 4 changes, 4 sides), exposure 2/8 = 25 %
  Bravo: p = 1 1 -1 -1 -1 1 1 -1 -1 -1
    gross  -5 +20 +5 -20 -10 -15 +20 -20 ; sides 1 0 2 0 0 2 0 2
    net -7.25 20 0.5 -20 -10 -19.5 20 -24.5 = -40.75 (gross -25, costs 15.75, 4 changes,
    7 sides), long gross +20, short gross -45, MDD: cum -7.25 12.75 13.25 -6.75 -16.75 -36.25
    -16.25 -40.75, peak 13.25 -> -40.75 = 54.00
  Charlie (15m): long on bars k = 3,4,5 (01-09) and 18,19,20 (01-16)
    01-09: bar4 1*(104-103)*5 = +5 - 2.25 entry, bar5 1*(101-104)*5 = -15 -> -12.25
    01-10: bar6 1*(102-101)*5 = +5, bar7 exit -2.25 -> 2.75
    01-16: +5 - 2.25 + 1*(107-112)*5 = -22.25 ; 01-17: 2.75 ; total -29.00 (gross -20, costs
    9.00, 4 changes), exposure 4/8 = 50 %, long bars 6/24 = 25 %
  Buy & hold: long from the 01-09 open: gross (115-102)*5 = 65, one side -> 62.75;
    daily -7.25 20 -5 20 10 -15 20 20
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qibt import cli, data, engine, metrics, signals

TS = pd.Timestamp
DATES = pd.bdate_range("2024-01-08", "2024-01-19")
O = [100, 102, 101, 105, 104, 108, 110, 107, 111, 115]
WINDOW = (TS("2024-01-09"), TS("2024-01-18"))
HALVES = {"H1": (TS("2024-01-09"), TS("2024-01-12")), "H2": (TS("2024-01-15"), TS("2024-01-18"))}
RULES_YAML = """
version: 1
frozen: "test"
rules:
  - {module: Alpha,   frame: D,   value: day_of_week, long: "x == 1", short: "never"}
  - {module: Bravo,   frame: D,   value: day_of_week, long: "x <= 2", short: "x >= 3"}
  - {module: Charlie, frame: 15m, value: day_of_week, long: "x == 2", short: "never"}
not_backtestable:
  - {module: Zulu, reason: "no class"}
"""
GOLD = {
    "Alpha": dict(daily=[-7.25, -2.25, 0, 0, 0, -17.25, -2.25, 0], total=-29.0, gross=-20.0, costs=9.0,
                  changes=4, sides=4, exposure=25.0),
    "Bravo": dict(daily=[-7.25, 20, 0.5, -20, -10, -19.5, 20, -24.5], total=-40.75, gross=-25.0, costs=15.75,
                  changes=4, sides=7, exposure=100.0, mdd=54.0, pnl_long=20.0, pnl_short=-45.0),
    "Charlie": dict(daily=[-12.25, 2.75, 0, 0, 0, -22.25, 2.75, 0], total=-29.0, gross=-20.0, costs=9.0,
                    changes=4, sides=4, exposure=50.0, long_pct=25.0),
    "BuyHold": dict(daily=[-7.25, 20, -5, 20, 10, -15, 20, 20], total=62.75, gross=65.0, costs=2.25,
                    changes=1, sides=1, exposure=100.0),
}


def synthetic_m1():
    rows = []
    for d, o in zip(DATES, O):
        times = [d - pd.Timedelta(days=1) + pd.Timedelta("17:01:00"), d + pd.Timedelta("09:00:00"),
                 d + pd.Timedelta("16:00:00")]
        for b, t in enumerate(times):
            op, cl = o + b, o + b + 0.5
            rows.append((t, float(op), cl + 0.25, op - 0.25, cl, 100.0))
    return pd.DataFrame(rows, columns=["BarTime", "Open", "High", "Low", "Close", "Volume"])


@pytest.fixture(scope="module")
def rules(tmp_path_factory):
    p = tmp_path_factory.mktemp("rules") / "toy_rules.yaml"
    p.write_text(RULES_YAML, encoding="utf-8")
    return signals.load_rules(p)


@pytest.fixture(scope="module")
def res(rules):
    return cli.run_pipeline(synthetic_m1(), rules, window=WINDOW, halves=HALVES)


def test_golden_daily_pnl_and_totals(res):
    m = res["metrics"].set_index("module")
    for mod, g in GOLD.items():
        assert res["daily"][mod].tolist() == g["daily"], mod
        assert m.loc[mod, "total_pnl"] == g["total"], mod
        assert m.loc[mod, "gross_pnl"] == g["gross"], mod
        assert m.loc[mod, "total_costs"] == g["costs"], mod
        assert m.loc[mod, "changes"] == g["changes"] and m.loc[mod, "sides"] == g["sides"], mod
        assert m.loc[mod, "exposure_pct"] == g["exposure"], mod
        assert m.loc[mod, "pnl_cost0"] == g["gross"], mod
        assert m.loc[mod, "pnl_cost2"] == g["gross"] - 2 * g["costs"], mod
    assert m.loc["Bravo", "mdd"] == 54.0
    assert (m.loc["Bravo", "pnl_long"], m.loc["Bravo", "pnl_short"]) == (20.0, -45.0)
    assert m.loc["Charlie", "long_pct"] == 25.0 and m.loc["Charlie", "short_pct"] == 0.0
    assert list(res["daily"]["date"]) == [d.strftime("%Y-%m-%d") for d in DATES[1:9]]


def test_golden_ratios_against_numpy(res):
    m = res["metrics"].set_index("module")
    bh = np.array(GOLD["BuyHold"]["daily"], float)
    for mod, g in GOLD.items():
        x = np.array(g["daily"], float)
        assert m.loc[mod, "sr"] == pytest.approx(x.mean() / x.std(ddof=1) * np.sqrt(252), rel=1e-12)
        assert m.loc[mod, "sr_h1"] == pytest.approx(x[:4].mean() / x[:4].std(ddof=1) * np.sqrt(252), rel=1e-12)
        assert m.loc[mod, "sr_h2"] == pytest.approx(x[4:].mean() / x[4:].std(ddof=1) * np.sqrt(252), rel=1e-12)
        assert m.loc[mod, "corr_bh"] == pytest.approx(np.corrcoef(x, bh)[0, 1], rel=1e-12)
    srd = [m.loc[k, "sr_daily"] for k in ("Alpha", "Bravo", "Charlie")]
    sr0 = metrics.expected_max_sr(np.var(srd, ddof=1), 3)
    assert res["sr0"] == pytest.approx(sr0) and res["n_trials"] == 3
    for k in ("Alpha", "Bravo", "Charlie"):
        assert m.loc[k, "dsr"] <= m.loc[k, "psr"]


def test_golden_ranking(res):
    m = res["metrics"].set_index("module")
    want = sorted(["Alpha", "Bravo", "Charlie"], key=lambda k: -m.loc[k, "sr"])
    got = [(r["rank"], r["module"]) for r in res["ranking"]]
    assert got == [(1, want[0]), (2, want[1]), (3, want[2]), (4, "Zulu")]


def test_reconciliation_on_synthetic(res):
    for mod in ("Alpha", "Bravo", "Charlie"):
        r = res["results"][mod]
        dr = r["daily"]
        assert dr.net(1.0).sum() == pytest.approx(dr.bar_gross_total - dr.bar_sides_total * engine.COST_PER_SIDE)


def test_cli_end_to_end_on_csv(tmp_path):
    """Same data through the CSV loader and the CLI with the PROTOCOL window: the extra calendar
    days 01-08 (bar 0) and 01-19 (last bar) carry no P&L, so the totals are the golden totals."""
    m1 = synthetic_m1()
    csv = tmp_path / "synth.csv"
    pd.DataFrame({"Date": m1["BarTime"].dt.strftime("%Y-%m-%d"), "Time": m1["BarTime"].dt.strftime("%H:%M:%S"),
                  "Open": m1["Open"], "High": m1["High"], "Low": m1["Low"], "Close": m1["Close"],
                  "Volume": m1["Volume"]}).to_csv(csv, index=False)
    rules_path = tmp_path / "toy_rules.yaml"
    rules_path.write_text(RULES_YAML, encoding="utf-8")
    out = tmp_path / "results"
    assert cli.main(["run", "--dataset", str(csv), "--rules", str(rules_path), "--out", str(out)]) == 0
    m = pd.read_csv(out / "metrics_synth.csv").set_index("module")
    d = pd.read_csv(out / "daily_pnl_synth.csv")
    for mod, g in GOLD.items():
        assert m.loc[mod, "total_pnl"] == g["total"], mod
        assert d[mod].tolist() == [0.0] + g["daily"] + [0.0], mod
    rk = pd.read_csv(out / "ranking_synth.csv")
    assert rk["rank"].tolist() == [1, 2, 3, 4] and rk["module"].iloc[-1] == "Zulu"
    rep = (out / "REPORT_synth.md").read_text(encoding="utf-8")
    assert "Buy & hold (benchmark)" in rep and "Not financial advice" in rep
    assert cli.main(["run", "--dataset", str(csv), "--rules", str(rules_path), "--out", str(out), "--costs", "2"]) == 0
    m2 = pd.read_csv(out / "metrics_synth_cost2x.csv").set_index("module")
    assert m2.loc["Bravo", "total_pnl"] == -25.0 - 2 * 15.75


def test_falsifier_booking_on_decision_date_is_detected(res):
    """Booking a bar's P&L on the date of the DECISION bar t (instead of the holding bar t+1)
    moves Charlie's overnight-bar P&L to the previous date and breaks the golden daily series."""
    f = res["frames"]["15m"]
    pos = res["results"]["Charlie"]["positions"]
    _, gross, sides = engine.bar_ledger(f["Open"].to_numpy(), pos)
    net = gross - sides * engine.COST_PER_SIDE
    dec_dates = pd.DatetimeIndex(f["TradingDate"]).to_series().shift(1).bfill()
    wrong = pd.Series(net).groupby(dec_dates.to_numpy()).sum().reindex(res["calendar"], fill_value=0.0)
    assert wrong.tolist() != GOLD["Charlie"]["daily"]


def test_cli_close_modes_sensitivity_and_bootstrap(tmp_path):
    """--close settle|last|1500 into the A1 / v1_last_trade / close_1500 layout, then SENSITIVITY
    and the bootstrap on the A1 folder. The synthetic bars have no databox_IBS and no 15:00 bar,
    so every close falls back to the last close: the three variants must agree exactly."""
    from qibt import bootstrap as bs
    m1 = synthetic_m1()
    csv = tmp_path / "synth.csv"
    pd.DataFrame({"Date": m1["BarTime"].dt.strftime("%Y-%m-%d"), "Time": m1["BarTime"].dt.strftime("%H:%M:%S"),
                  "Open": m1["Open"], "High": m1["High"], "Low": m1["Low"], "Close": m1["Close"],
                  "Volume": m1["Volume"]}).to_csv(csv, index=False)
    rules_path = tmp_path / "toy_rules.yaml"
    rules_path.write_text(RULES_YAML, encoding="utf-8")
    base = tmp_path / "results"
    for close, sub in (("settle", "."), ("last", "v1_last_trade"), ("1500", "close_1500")):
        for c in ("0", "1", "2"):
            assert cli.main(["run", "--dataset", str(csv), "--rules", str(rules_path), "--out", str(base / sub),
                             "--costs", c, "--close", close]) == 0
    rep = (base / "REPORT_synth.md").read_text(encoding="utf-8")
    assert "D close settle (A1" in rep and "last 10 of 10 (fallback: ibs_missing 10)" in rep
    a1 = pd.read_csv(base / "metrics_synth.csv").set_index("module")
    v1 = pd.read_csv(base / "v1_last_trade" / "metrics_synth.csv").set_index("module")
    pd.testing.assert_series_equal(a1["sr"], v1["sr"])
    txt = cli.render_sensitivity(base, tag="synth")
    assert txt.count("\n### ") == 3 and "| v1 |" in txt and "| A1 |" in txt and "| 15:00 |" in txt
    assert "Rank 0x" in txt and "A1 halves (1x)" in txt
    s, pub, n = bs.run_files(base / "daily_pnl_synth.csv", base / "ranking_synth.csv", 30, 10.0, 12345)
    assert n == 10 and set(s["p_rank1"]) == {"Alpha", "Bravo", "Charlie"}
    assert sum(s["p_rank1"].values()) == pytest.approx(1.0)
