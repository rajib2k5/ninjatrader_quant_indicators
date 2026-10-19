"""Unit tests for QI_<NN>_VolumeSpike - bar volume relative to its 20-bar average.

Spec (ledger M21; ORIG IBSFade.cs 358, 1422-1426; README "Indicators"):
  ratio = Volume[0] / SMA(Volume, 20)[0]  when the SMA > 0, else 1.0
  The 20-bar window INCLUDES the current bar. No CurrentBar guard in the C# (NinjaTrader's SMA averages the bars
  available during the first 19 bars); the reference is NaN until 20 bars exist, so the export test starts at bar 19.
Reference line 1.5 (rules.yaml: long when x > 1.5, never short).
Reference: qi_ref.volume_spike.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

import qi_ref as R
from qi_helpers import (assert_close, assert_names, bars, compile_alone, cs_contract, harness_col, harness_frame,
                      indicator_file)

MODULE = "VolumeSpike"


def _vol(values):
    values = np.asarray(values, dtype=float)
    return bars(np.full(len(values), 100.0), volume=values)


# ---- 1. formula --------------------------------------------------------------------------
def test_spike_hand_value_2_727():
    v = [100.0] * 19 + [300.0]
    # SMA20 at bar 19 = (19 * 100 + 300) / 20 = 2200 / 20 = 110 ; ratio = 300 / 110 = 30/11
    ratio = R.volume_spike(_vol(v)).to_numpy()
    assert ratio[19] == pytest.approx(30.0 / 11.0, abs=1e-12)
    assert ratio[19] == pytest.approx(2.727272727272727, abs=1e-12)


def test_below_threshold_hand_value_and_constant_volume():
    # SMA20 = (19 * 100 + 150) / 20 = 2050 / 20 = 102.5 ; ratio = 150 / 102.5 = 1.4634146341463414 (< the 1.5 line)
    ratio = R.volume_spike(_vol([100.0] * 19 + [150.0])).to_numpy()
    assert ratio[19] == pytest.approx(1.4634146341463414, abs=1e-12)
    # constant volume: SMA = volume -> ratio 1.0 on every bar that has a full window
    flat = R.volume_spike(_vol([250.0] * 30)).to_numpy()
    assert flat[19:].tolist() == pytest.approx([1.0] * 11, abs=1e-12)


def test_undefined_for_the_first_19_bars_and_one_when_the_average_is_zero():
    ratio = R.volume_spike(_vol([100.0] * 25)).to_numpy()
    assert np.isnan(ratio[:19]).all() and not np.isnan(ratio[19:]).any()      # SMA20 needs 20 bars
    # SMA20 = 0 (twenty zero-volume bars) -> the fallback 1.0, not a division by zero
    z = R.volume_spike(_vol([0.0] * 20)).to_numpy()
    assert z[19] == 1.0
    # bar 20 has volume 100 after zero bars: SMA20 over bars 1..20 = 100 / 20 = 5 -> ratio 100 / 5 = 20.0
    z2 = R.volume_spike(_vol([0.0] * 20 + [100.0])).to_numpy()
    assert z2[19] == 1.0 and z2[20] == pytest.approx(20.0, abs=1e-12)


def test_range_is_zero_to_twenty_and_scale_invariant():
    rng = np.random.default_rng(3)
    v = rng.integers(0, 5000, 200).astype(float)
    r = R.volume_spike(_vol(v)).to_numpy()
    ok = ~np.isnan(r)
    # Volume[0] is one of the 20 terms of its own average, so 0 <= ratio <= 20 (= 20 when all other 19 bars are 0)
    assert (r[ok] >= 0.0).all() and (r[ok] <= 20.0 + 1e-9).all()
    # a unit change of the volume (contracts -> lots) leaves the ratio alone
    assert R.volume_spike(_vol(v * 7.0)).to_numpy()[ok] == pytest.approx(r[ok], abs=1e-9)


def test_ratio_is_above_one_exactly_when_volume_exceeds_its_average():
    v = [100.0] * 19 + [101.0, 99.0, 100.0]
    # bar 19: SMA = (1900 + 101) / 20 = 100.05 < 101 -> > 1 ; bar 20: SMA(bars 1..20) = (1800 + 101 + 99) / 20 = 100.0 > 99 -> < 1
    r = R.volume_spike(_vol(v)).to_numpy()
    assert r[19] > 1.0 and r[20] < 1.0
    assert r[20] == pytest.approx(99.0 / 100.0, abs=1e-12)


def test_falsifier_average_of_the_previous_twenty_bars_is_detected():
    """Dividing by the 20 bars BEFORE the current one is the plausible slip. With twenty bars of 100 then 300:
    spec (window includes the bar) = 300 / ((19 * 100 + 300) / 20) = 2.7273 ; the slip = 300 / 100 = 3.0."""
    ratio = R.volume_spike(_vol([100.0] * 20 + [300.0])).to_numpy()
    assert ratio[20] != pytest.approx(3.0, abs=1e-6)
    assert ratio[20] == pytest.approx(30.0 / 11.0, abs=1e-12)


# ---- 2. C# interface contract --------------------------------------------------------------
def test_csharp_contract():
    c = cs_contract(MODULE)
    assert_names(MODULE, c)
    assert c["overlay"] is False                      # panel indicator
    assert c["plots"] == ["Vol / SMA20"]
    assert c["series"] == ["VolumeSpike"]             # read by QS_*_VolumeSpike and the harness
    assert c["lines"] == {"Upper Threshold": 1.5}
    assert c["defaults"]["Threshold"] == "1.5"
    assert c["defaults"]["ShowDisclaimer"] == "false"


def test_csharp_formula_and_fallback():
    text = cs_contract(MODULE)["text"]
    assert re.search(r"volSma20\s*=\s*SMA\(Volume,\s*20\)", text)
    assert re.search(r"volSma20\[0\]\s*>\s*0\s*\?\s*Volume\[0\]\s*/\s*volSma20\[0\]\s*:\s*1\.0", text)
    assert "if (CurrentBar <" not in text             # no warm-up gate (ORIG's global gate is not reproduced)


# ---- 3. compile ----------------------------------------------------------------------------
@pytest.mark.slow
def test_compiles_alone():
    r = compile_alone(indicator_file(MODULE))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


# ---- 4. NinjaTrader export -----------------------------------------------------------------
def test_matches_ninjatrader_export():
    df = harness_frame()
    got = harness_col(df, MODULE, "VolumeSpike")
    # No C# gate, but the reference needs 20 bars for SMA20 (NinjaTrader averages fewer bars before that): from bar 19.
    assert_close(R.volume_spike(df), got, start=19, tol=6e-5, label="VolumeSpike.VolumeSpike")
