"""test_patterns_sanity.py - sanity checks on the pattern/level modules M24-M26 (and M27).

The ledger gives no formula precise enough to re-implement these rule sets, so Channel B can
only check the harness output against the value sets the ledger implies. Exact replay is
UNVERIFIABLE on Channel B (recorded in validation/channel-b-algo.md). Skips without harness data.
"""
from __future__ import annotations

import numpy as np
import pytest

CONFIDENCES = {0, 0.35, 0.50, 0.55, 0.58, 0.60, 0.65, 0.68, 0.70, 0.72, 0.75, 0.78, 0.85}
STRUCTURES = {-1, 0, 1}
MODULES = {"M24": "QI_22_LiquiditySweep", "M25": "QI_24_OrderFlowPlus", "M26": "QI_25_SMC"}


def _cols(h, mod, name):
    for c in ("%s.%s" % (mod, name),):
        if c in h.columns:
            return h[c].astype(float)
    pytest.skip("UNVERIFIABLE: harness lacks %s.%s" % (mod, name))


@pytest.mark.parametrize("claim, mod", sorted(MODULES.items()))
def test_confidence_in_fixed_set(harness, claim, mod):
    conf = _cols(harness, mod, "Confidence").fillna(0.0).round(4)
    bad = sorted(set(conf.unique()) - {round(c, 4) for c in CONFIDENCES})
    assert not bad, "%s/%s: confidences outside the fixed set: %s" % (claim, mod, bad)


@pytest.mark.parametrize("claim, mod", sorted(MODULES.items()))
def test_structure_in_minus1_0_plus1(harness, claim, mod):
    s = _cols(harness, mod, "Structure").fillna(0.0)
    bad = sorted(set(s.unique()) - STRUCTURES)
    assert not bad, "%s/%s: structure values outside {-1,0,1}: %s" % (claim, mod, bad)


@pytest.mark.parametrize("claim, mod", sorted(MODULES.items()))
def test_confidence_positive_iff_structure_nonzero(harness, claim, mod):
    conf = _cols(harness, mod, "Confidence").fillna(0.0).to_numpy()
    s = _cols(harness, mod, "Structure").fillna(0.0).to_numpy()
    mismatch = np.flatnonzero((conf > 0) != (s != 0))
    assert len(mismatch) == 0, "%s/%s: Confidence>0 xor Structure!=0 at bars %s" % (claim, mod, mismatch[:10].tolist())


@pytest.mark.parametrize("claim, mod", sorted(MODULES.items()))
def test_plot_values_mirror_series(harness, claim, mod):
    """Values[0] / Values[1] are the Confidence / Structure plots."""
    h = harness
    for i, name in ((0, "Confidence"), (1, "Structure")):
        pc, sc = "%s.Values[%d]" % (mod, i), "%s.%s" % (mod, name)
        if pc in h.columns and sc in h.columns:
            a, b = h[pc].astype(float).fillna(0.0).to_numpy(), h[sc].astype(float).fillna(0.0).to_numpy()
            assert np.allclose(a, b), "%s/%s: %s differs from %s" % (claim, mod, pc, sc)


def test_M26_smc_trend_dir_in_minus1_0_plus1(harness):
    t = _cols(harness, "QI_25_SMC", "TrendDir").fillna(0.0)
    bad = sorted(set(t.unique()) - STRUCTURES)
    assert not bad, "M26/QI_25_SMC: TrendDir values outside {-1,0,1}: %s" % bad


@pytest.mark.parametrize("claim", ["M24", "M25", "M26", "M27"])
def test_exact_replay_unverifiable(claim):
    pytest.skip("UNVERIFIABLE on Channel B: ledger %s states rule families and fixed confidences, "
                "not a formula precise enough to replay bar-by-bar" % claim)


def test_falsifier_value_set_check_rejects_foreign_confidence():
    import pandas as pd
    conf = pd.Series([0.0, 0.35, 0.42]).round(4)
    assert sorted(set(conf.unique()) - {round(c, 4) for c in CONFIDENCES}) == [0.42]
