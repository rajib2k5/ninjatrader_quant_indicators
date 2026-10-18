"""Unit tests for QI_<NN>_RSI14 - 14-period Relative Strength Index (Wilder).

Spec (ledger B1 / M12, ORIG IBSFade.cs 343, 1368-1371):
  up_t = max(C_t - C_{t-1}, 0), down_t = max(C_{t-1} - C_t, 0)
  RS   = Wilder_14(up) / Wilder_14(down),   Wilder_n = running average with weight 1/n on the new value
  RSI  = 100 - 100 / (1 + RS);  NinjaTrader RSI(Close, 14, 1) adds no extra smoothing.
  The C# writes nothing before bar 50 (ORIG's module-wide gate).
Reference lines 40 / 60 (rules.yaml: long x < 40, short x > 60).

The ledger does not say how the Wilder averages are seeded, so no hand value below depends on the
seed: they use the steady state of an alternating +1/-1 series (the seed is forgotten like (13/14)^t)
and single steps taken from that steady state.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from conftest import (REPO, assert_close, assert_names, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "RSI14"


def alternating(n_bars):
    """10, 11, 10, 11, ...: odd positions are +1 moves, even positions (> 0) are -1 moves."""
    return 10.0 + (np.arange(n_bars) % 2)


# ---- 1. formula --------------------------------------------------------------------------
def test_alternating_closes_settle_at_the_wilder_steady_state():
    # Moves alternate +1 / -1 and the weight is w = 1/14. After an up bar the averages satisfy
    #   U_up = U_dn + (1 - U_dn)/14   and   U_dn = U_up * 13/14   ->  U_up = 14/27, U_dn = 13/27
    # and, mirrored, D_dn = 14/27, D_up = 13/27.
    # After an up bar:   RS = (14/27)/(13/27) = 14/13   RSI = 100 - 100/(1 + 14/13) = 100*14/27 = 1400/27
    # After a down bar:  RS = 13/14                     RSI = 100 - 100/(1 + 13/14) = 100*13/27 = 1300/27
    rsi = R.rsi(alternating(300), 14).to_numpy()     # position 299 is an up bar, 298 a down bar
    assert rsi[299] == pytest.approx(1400 / 27, abs=1e-6)    # 51.85185...
    assert rsi[298] == pytest.approx(1300 / 27, abs=1e-6)    # 48.14814...


def test_one_more_move_from_the_steady_state_uses_weight_one_fourteenth():
    # State after the alternating series (ends on 11, an up bar): avgUp = 14/27, avgDn = 13/27.
    # next close 12 (+1):  avgUp = 14/27 + (1 - 14/27)/14 = 196/378 + 13/378 = 209/378
    #                      avgDn = 13/27 * 13/14           = 169/378
    #                      RSI   = 100 * 209/(209 + 169)   = 100 * 209/378
    # then close 11 (-1):  avgUp = 209/378 * 13/14         = 2717/5292
    #                      avgDn = 169/378 + (1 - 169/378)/14 = 2366/5292 + 209/5292 = 2575/5292
    #                      RSI   = 100 * 2717/(2717 + 2575) = 100 * 2717/5292
    close = list(alternating(300)) + [12.0, 11.0]
    rsi = R.rsi(close, 14).to_numpy()
    assert rsi[300] == pytest.approx(100 * 209 / 378, abs=1e-6)      # 55.2910...
    assert rsi[301] == pytest.approx(100 * 2717 / 5292, abs=1e-6)    # 51.3416...


def test_monotone_series_reach_the_bounds():
    up = np.arange(1.0, 61.0)              # no down move ever: Wilder_14(down) = 0, RS infinite -> 100
    assert (R.rsi(up, 14).to_numpy()[1:] == 100.0).all()
    down = np.arange(60.0, 0.0, -1.0)      # no up move ever: RS = 0 -> RSI = 100 - 100 = 0
    assert (R.rsi(down, 14).to_numpy()[1:] == 0.0).all()


def test_values_stay_inside_0_100():
    rs = np.random.RandomState(11)
    close = 1000.0 + np.cumsum(rs.normal(0, 3, 500))
    close[200] *= 1.5                      # an outlier jump
    close[300:310] = close[300]            # a flat stretch
    v = R.rsi(close, 14).to_numpy()[1:]
    assert np.isfinite(v).all() and (v >= 0).all() and (v <= 100).all()


def test_scale_and_shift_invariance():
    close = np.concatenate([alternating(60), [12.0, 13.0, 12.5, 12.0]])
    base = R.rsi(close, 14).to_numpy()
    np.testing.assert_allclose(R.rsi(close * 7.0, 14).to_numpy(), base, atol=1e-9)      # only ratios of moves
    np.testing.assert_allclose(R.rsi(close + 1000.0, 14).to_numpy(), base, atol=1e-9)   # back-adjustment


def test_bar_zero_has_no_move_and_no_value():
    v = R.rsi(alternating(20), 14).to_numpy()
    assert np.isnan(v[0])                  # no previous close -> no move
    assert np.isfinite(v[1:]).all()


def test_falsifier_wrong_period_and_simple_average_variants_are_rejected():
    """Period 13 and Cutler's simple-average RSI are the plausible miscodings of Wilder RSI(14);
    the steady-state hand values of test 1 (51.852 / 48.148) tell them apart."""
    close = alternating(300)
    after_up, after_down = 1400 / 27, 1300 / 27
    # period 13: U_up = 13/25 -> RSI = 100*13/25 = 52.0 after an up bar, 48.0 after a down bar
    p13 = R.rsi(close, 13).to_numpy()
    assert abs(p13[299] - after_up) > 0.1 and abs(p13[298] - after_down) > 0.1
    # Cutler: plain mean of the last 14 moves = seven +1 and seven 0 -> RS = 1 -> RSI = 50
    d = np.diff(close)
    up, dn = np.maximum(d, 0.0)[-14:].mean(), np.maximum(-d, 0.0)[-14:].mean()
    cutler = 100.0 - 100.0 / (1.0 + up / dn)
    assert abs(cutler - after_up) > 1.0


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["RSI(14)"]
    assert "RSI14" in c["series"]                     # read by QS_*_RSI14 and the harness
    assert c["lines"] == {"Lower Threshold": 40.0, "Upper Threshold": 60.0}
    assert c["defaults"]["LowerThreshold"] == "40" and c["defaults"]["UpperThreshold"] == "60"
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


def test_csharp_keeps_the_original_bar_50_gate_and_period_14():
    text = cs_contract(MODULE)["text"]
    assert "if (CurrentBar < 50)" in text
    assert re.search(r"rsi14\s*=\s*RSI\(Close,\s*14,\s*1\)", text)       # period 14, no extra smoothing


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "RSI14")
    # The C# writes from bar 50, but NinjaTrader seeds its Wilder averages differently from the
    # reference's first-move seed (ledger B1 allows a 300-bar warm-up). The difference decays like
    # (13/14)^t, i.e. below 1e-8 RSI points at bar 300, so compare from there.
    start = 300
    if len(df) <= start:
        pytest.skip(f"export has {len(df)} bars; RSI14 is compared from bar {start}")
    ref = R.rsi(df["Close"].to_numpy(float), 14).to_numpy()
    assert_close(ref, got, start=start, tol=6e-5, label="RSI14")
