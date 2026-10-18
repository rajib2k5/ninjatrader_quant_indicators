"""Unit tests for QI_<NN>_OvernightGap - the open-to-previous-close gap in percent.

Spec (ledger M9; ORIG IBSFade.cs 1571, 1348-1351; README "Indicators"):
  gap% = (Open[0] - Close[1]) / Close[1] * 100        (percent, measured against the PREVIOUS CLOSE)
  Bar 0 has no Close[1]: the C# plots 0 ("Gap % ... 0 on the first bar"); the reference qi_ref.gap_pct returns NaN
  there (its docstring: "bar 0 is NaN") - the export test compares from bar 1 and checks the C# 0 separately.
  No warm-up gate (the module plots from bar 1). No divide-by-zero guard on Close[1] (preserved from ORIG).
Reference lines -0.3 / +0.3 (rules.yaml: long x < -0.3, short x > 0.3).
Reference: qi_ref.gap_pct.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from conftest import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "OvernightGap"


def _case():
    """Four bars whose prior Open differs from the prior Close, so the denominator choice matters."""
    close = [100, 102, 99, 99]
    open_ = [100, 103, 100.98, 99]
    return bars(close, open_=open_)


# ---- 1. formula --------------------------------------------------------------------------
def test_gap_hand_values():
    gap = R.gap_pct(_case()).to_numpy()
    # bar 1: (103 - 100) / 100 * 100 = 3.0
    # bar 2: (100.98 - 102) / 102 * 100 = -1.02 / 102 * 100 = -1.0        (against Close[1] = 102, not Open[1] = 103)
    # bar 3: (99 - 99) / 99 * 100 = 0.0
    assert np.isnan(gap[0])
    assert gap[1:] == pytest.approx([3.0, -1.0, 0.0], abs=1e-9)


def test_gap_is_in_percent_and_signed():
    df = bars([4000, 4000, 4000], open_=[4000, 4004, 3996])
    # bar 1: (4004 - 4000) / 4000 * 100 = +0.1 ; bar 2: (3996 - 4000) / 4000 * 100 = -0.1
    assert R.gap_pct(df).to_numpy()[1:] == pytest.approx([0.1, -0.1], abs=1e-12)


def test_no_gap_when_every_open_equals_the_previous_close():
    close = np.array([50.0, 51.0, 49.5, 49.5, 52.25])
    open_ = np.r_[close[0], close[:-1]]
    gap = R.gap_pct(bars(close, open_=open_)).to_numpy()
    assert (gap[1:] == 0.0).all()


def test_first_bar_has_no_gap_nan_in_the_reference_zero_in_the_csharp():
    assert np.isnan(R.gap_pct(_case()).to_numpy()[0])
    text = cs_contract(MODULE)["text"]
    # C# fallback documented in the header ("0 on bar 0") and in the code:
    assert re.search(r"CurrentBar\s*>=\s*1\s*\?\s*\(Open\[0\]\s*-\s*Close\[1\]\)\s*/\s*Close\[1\]\s*\*\s*100\.0\s*:\s*0\s*;", text)


def test_scale_invariance_of_the_percent_gap():
    df = _case()
    scaled = bars(df["Close"].to_numpy() * 7.0, open_=df["Open"].to_numpy() * 7.0)
    # (7*Open - 7*Close[1]) / (7*Close[1]) = (Open - Close[1]) / Close[1]: a unit change leaves the percent gap alone
    assert R.gap_pct(scaled).to_numpy()[1:] == pytest.approx(R.gap_pct(df).to_numpy()[1:], abs=1e-9)


def test_falsifier_wrong_denominator_or_unit_is_detected():
    """Plausible slips on the first hand case: a fraction instead of percent (bar 1 -> 0.03), dividing by the new Open
    (bar 1 -> 3/103*100 = 2.9126), or measuring against the previous Open (bar 2 -> (100.98-103)/103*100 = -1.9612).
    Each differs from the literals of test_gap_hand_values (3.0 and -1.0)."""
    gap = R.gap_pct(_case()).to_numpy()
    for wrong_bar1 in (0.03, 3.0 / 103.0 * 100.0):
        assert gap[1] != pytest.approx(wrong_bar1, abs=1e-6)
    assert gap[2] != pytest.approx(-1.9611650485436893, abs=1e-6)
    assert gap[1] == pytest.approx(3.0, abs=1e-9) and gap[2] == pytest.approx(-1.0, abs=1e-9)


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["Gap %"]
    assert c["series"] == ["GapPct"]                  # read by QS_*_OvernightGap and the harness
    assert c["lines"] == {"Lower Threshold": -0.3, "Upper Threshold": 0.3}
    assert c["defaults"]["LowerThreshold"] == "-0.3" and c["defaults"]["UpperThreshold"] == "0.3"
    assert c["defaults"]["ShowDisclaimer"] == "false"


def test_csharp_has_no_warmup_gate():
    text = cs_contract(MODULE)["text"]
    assert "if (CurrentBar <" not in text             # standalone plots from bar 1 (bar 0 -> 0)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "GapPct")
    # The reference is NaN at bar 0 and the C# is 0 there; from bar 1 both use the same formula (no gate).
    assert_close(R.gap_pct(df), got, start=1, tol=6e-5, label="OvernightGap.GapPct")


def test_export_has_the_csharp_zero_on_bar_zero():
    df = harness_frame()
    got = harness_col(df, MODULE, "GapPct")
    assert got.iloc[0] == pytest.approx(0.0, abs=1e-12)
