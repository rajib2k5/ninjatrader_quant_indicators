"""Unit tests for QI_<NN>_ConsecDays - signed count of consecutive higher (+) / lower (-) closes.

Spec (ledger M8, ORIG IBSFade.cs 1552-1568, 1343-1346):
  Close > previous Close  -> up += 1, down = 0
  Close < previous Close  -> down += 1, up = 0
  Close == previous Close -> both counts unchanged
  Streak = up if up > 0 else -down; bar 0 = 0; the C# computes nothing before bar 50.
Reference lines -3 / +3 (rules.yaml: long x <= -3, short x >= 3).
"""
from __future__ import annotations

import numpy as np
import pytest

import qi_ref as R
from conftest import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col,
                      harness_frame, indicator_file)

MODULE = "ConsecDays"


# ---- 1. formula --------------------------------------------------------------------------
def test_streak_hand_values():
    close = [10, 11, 12, 12, 11, 10, 9, 10]
    # bar:   0   1   2   3    4    5    6   7
    # move:  -   up  up  =    dn   dn   dn  up
    # count: 0  +1  +2  +2   -1   -2   -3  +1   (unchanged close at bar 3 keeps +2)
    assert R.consec_days(close).tolist() == [0, 1, 2, 2, -1, -2, -3, 1]


def test_unchanged_close_inside_a_down_run_keeps_the_count():
    close = [10, 9, 8, 8, 8, 7]
    # counts: 0, -1, -2, -2, -2, -3
    assert R.consec_days(close).tolist() == [0, -1, -2, -2, -2, -3]


def test_a_reversal_restarts_the_count_at_one():
    close = [1, 2, 3, 4, 3, 4]
    # counts: 0, +1, +2, +3, -1, +1
    assert R.consec_days(close).tolist() == [0, 1, 2, 3, -1, 1]


def test_scale_and_shift_invariance():
    close = np.array([5.0, 5.5, 5.25, 5.25, 6.0, 4.0, 4.0, 3.5])
    base = R.consec_days(close).tolist()
    assert R.consec_days(close * 7.0).tolist() == base      # only signs of differences matter
    assert R.consec_days(close + 1000.0).tolist() == base   # back-adjustment does not change it


def test_falsifier_reset_on_unchanged_close_is_detected():
    """Connors' published rule resets on an unchanged close; the original keeps the count.
    A reset variant gives 0 at bar 3 of the first hand case, so test 1 tells them apart."""
    close = [10, 11, 12, 12, 11]
    reset_variant = [0, 1, 2, 0, -1]
    assert R.consec_days(close).tolist() != reset_variant


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["Streak"]
    assert "Streak" in c["series"]                    # read by QS_*_ConsecDays and the harness
    assert c["lines"] == {"Lower Threshold": -3.0, "Upper Threshold": 3.0}
    assert c["defaults"]["LowerThreshold"] == "-3" and c["defaults"]["UpperThreshold"] == "3"
    assert c["defaults"]["ShowDisclaimer"] == "false"


def test_csharp_keeps_the_original_bar_50_gate():
    text = cs_contract(MODULE)["text"]
    assert "if (CurrentBar < 50)" in text


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "Streak")
    # The C# starts counting at bar 50 (comparing bar 50 with bar 49), so the reference is the
    # streak of the closes from bar 49 on, aligned to the export.
    close = df["Close"].to_numpy(float)
    ref = np.full(len(close), np.nan)
    ref[49:] = R.consec_days(close[49:]).to_numpy()
    ref[49] = np.nan
    assert_close(ref, got, start=50, tol=1e-9, label="ConsecDays.Streak")
