"""Unit tests for QI_<NN>_WideRangeBar - bar range relative to ATR(14).

Spec (ledger M14 + B4, ORIG IBSFade.cs 347, 1379-1383):
  WR = (High - Low) / ATR14,  1.0 when ATR14 <= 0
  TR  = max(H - L, |H - C[1]|, |L - C[1]|)  (bar 0: H - L)
  ATR[t] = (min(t, 13) * ATR[t-1] + TR[t]) / min(t + 1, 14),  ATR[0] = TR[0]   (NinjaTrader ATR)
There is no CurrentBar guard in the C# (only the ATR > 0 check).
Reference line 1.2 (rules.yaml: long x > 1.2, short never).
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (REPO, assert_close, assert_names, bars, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "WideRangeBar"


def spike_bars():
    """Bars 0-4: H=12 L=10 C=11 (range 2). Bar 5: H=16 L=10 C=13 (range 6). Bar 6: H=14 L=12 C=13."""
    return bars([11, 11, 11, 11, 11, 13, 13], high=[12, 12, 12, 12, 12, 16, 14], low=[10, 10, 10, 10, 10, 10, 12])


# ---- 1. formula --------------------------------------------------------------------------
def test_wide_bar_after_quiet_bars_hand_values():
    # bars 0-4: TR = 2 each (bar 0: H-L = 2; later max(2, |12-11|, |10-11|) = 2), ATR = 2, WR = 2/2 = 1
    # bar 5: TR = max(6, |16-11| = 5, |10-11| = 1) = 6
    #        ATR = (5*2 + 6)/6 = 16/6 = 8/3     WR = 6/(8/3) = 18/8 = 2.25
    # bar 6: prev close 13, TR = max(2, |14-13| = 1, |12-13| = 1) = 2
    #        ATR = (6*(8/3) + 2)/7 = 18/7       WR = 2/(18/7) = 14/18 = 7/9
    wr = R.wide_range(spike_bars()).to_numpy()
    np.testing.assert_allclose(wr, [1, 1, 1, 1, 1, 2.25, 7 / 9], atol=1e-12)


def test_gap_enters_the_true_range():
    # bar 0: H=11 L=9 C=10  -> TR = 2, ATR = 2, WR = 1
    # bar 1: H=21 L=19 C=20 (gap up) -> TR = max(2, |21-10| = 11, |19-10| = 9) = 11
    #        ATR = (1*2 + 11)/2 = 6.5   WR = (21-19)/6.5 = 2/6.5 = 4/13
    wr = R.wide_range(bars([10, 20], high=[11, 21], low=[9, 19])).to_numpy()
    assert wr[0] == pytest.approx(1.0, abs=1e-12)
    assert wr[1] == pytest.approx(4 / 13, abs=1e-12)           # 0.3077


def test_first_bar_is_always_exactly_one():
    # ATR[0] = TR[0] = H - L, so WR[0] = (H - L)/(H - L) = 1 for any bar with a range
    for h, l in [(12.0, 10.0), (5000.25, 4990.0), (1.01, 1.0)]:
        wr = R.wide_range(bars([l], high=[h], low=[l])).to_numpy()
        assert wr[0] == pytest.approx(1.0, abs=1e-12)


def test_zero_atr_falls_back_to_one():
    # all bars flat: TR = 0, ATR = 0 -> 1.0 (not 0/0)
    flat = bars([10.0] * 20, high=[10.0] * 20, low=[10.0] * 20)
    assert (R.wide_range(flat).to_numpy() == 1.0).all()
    # once a bar has a range the ratio is computed again:
    # bars 0-2 flat (ATR 0 -> 1.0); bar 3: H=12 L=10 C=10, TR = max(2, |12-10|, |10-10|) = 2,
    # ATR = (3*0 + 2)/4 = 0.5, WR = 2/0.5 = 4
    resume = bars([10, 10, 10, 10], high=[10, 10, 10, 12], low=[10, 10, 10, 10])
    np.testing.assert_allclose(R.wide_range(resume).to_numpy(), [1, 1, 1, 4.0], atol=1e-12)


def test_scale_and_shift_invariance():
    base = R.wide_range(spike_bars()).to_numpy()
    s = spike_bars()
    scaled = bars(s["Close"] * 5.0, high=s["High"] * 5.0, low=s["Low"] * 5.0)       # ratio of ranges
    shifted = bars(s["Close"] + 1000.0, high=s["High"] + 1000.0, low=s["Low"] + 1000.0)  # TR unchanged
    np.testing.assert_allclose(R.wide_range(scaled).to_numpy(), base, atol=1e-12)
    np.testing.assert_allclose(R.wide_range(shifted).to_numpy(), base, atol=1e-12)


def test_ratio_is_non_negative_and_bounded_by_the_atr_weight():
    # ATR[t] >= TR[t]/min(t+1, 14) >= (H - L)/min(t+1, 14)  =>  0 <= WR[t] <= min(t+1, 14)
    rs = np.random.RandomState(5)
    n = 400
    mid = 1000.0 + np.cumsum(rs.normal(0, 2, n))
    rng = rs.pareto(1.5, n) + 0.01                      # heavy-tailed ranges, occasional huge bars
    high, low = mid + rng / 2, mid - rng / 2
    close = low + rs.uniform(0, 1, n) * rng
    wr = R.wide_range(bars(close, high=high, low=low)).to_numpy()
    cap = np.minimum(np.arange(n) + 1, 14)
    assert (wr >= 0).all() and (wr <= cap + 1e-9).all()


def test_falsifier_range_over_plain_range_average_ignores_gaps_and_is_rejected():
    """A WR built on the mean of (H - L) instead of ATR(14) misses the gap in the hand case:
    bar 1 would be 2/mean(2, 2) = 1.0 where the true-range ATR gives 4/13."""
    df = bars([10, 20], high=[11, 21], low=[9, 19])
    rng = (df["High"] - df["Low"]).to_numpy()
    plain = rng / np.cumsum(rng) * np.arange(1, len(rng) + 1)       # range / running mean of range
    assert plain[1] == pytest.approx(1.0)
    assert abs(plain[1] - 4 / 13) > 0.5
    assert abs(R.wide_range(df).to_numpy()[1] - plain[1]) > 0.5


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["Range/ATR14"]
    assert "WideRange" in c["series"]                 # read by QS_*_WideRangeBar and the harness
    assert c["lines"] == {"Upper Threshold": 1.2}
    assert c["defaults"]["Threshold"] == "1.2"        # single threshold, no Lower/Upper pair
    assert c["defaults"]["ShowDisclaimer"] == "false"


def test_reference_lines_and_panel_match_rules_yaml_and_readme():
    c = cs_contract(MODULE)
    num = r"-?\d+(?:\.\d+)?"
    rule = next(l for l in (REPO / "backtest" / "rules.yaml").read_text(encoding="utf-8").splitlines()
                if f"module: {MODULE}," in l)
    from_rules = sorted(float(v) for s in re.findall(r'(?:long|short): "([^"]*)"', rule) for v in re.findall(num, s))
    row = next(l for l in (REPO / "README.md").read_text(encoding="utf-8").splitlines()
               if l.startswith(f"| `{c['class']}` |")).split("|")
    from_readme = sorted(float(v) for v in re.findall(num, row[3]))
    assert from_rules == from_readme == sorted(c["lines"].values())
    assert row[4].strip() == "Panel"


def test_csharp_has_no_warmup_gate_and_falls_back_to_one():
    text = cs_contract(MODULE)["text"]
    body = text[text.index("protected override void OnBarUpdate"):].split("DrawDisclaimerOnce();")[0]
    assert "CurrentBar" not in body                   # only the ATR > 0 check, no bar-count guard
    assert re.search(r"atr14\[0\]\s*>\s*0\s*\?\s*\(High\[0\]\s*-\s*Low\[0\]\)\s*/\s*atr14\[0\]\s*:\s*1\.0", body)
    assert re.search(r"atr14\s*=\s*ATR\(14\)", text)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "WideRange")
    # No CurrentBar gate in the C#, and NinjaTrader's ATR warm-up is the ledger recursion from
    # bar 0, so the whole export is comparable.
    ref = R.wide_range(df).to_numpy()
    assert_close(ref, got, start=0, tol=6e-5, label="WideRangeBar.WideRange")
