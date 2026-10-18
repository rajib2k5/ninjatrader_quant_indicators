"""Published numeric examples (Channel A, validation/channel-a-backtest.md, BT10/BT11).

The inputs and outputs below were copied by the documentation channel from the papers; the
engine's author never saw them, so these tests are an independent check of qibt.metrics.
- Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio", J. Portfolio Mgmt 40(5):
  annualised SR 2.5 on daily data (250/yr), T = 1250, N = 100, annual V[SR] = 1/2,
  skew -3, kurtosis 10 (non-excess) -> SR0 ~ 0.1132 (per day), DSR ~ 0.9004; N = 46 -> 0.9505.
- Bailey & Lopez de Prado (2012), "The Sharpe Ratio Efficient Frontier", J. of Risk 15(2):
  monthly SR 0.458, n = 24 -> PSR(0) = 0.982 (normal: skew 0, kurt 3) and 0.913
  (skew -2.448, kurt 10.164); n = 36 -> 0.953.
Tolerances are the papers' printed precision (3 decimals; SR0 to 4).
"""
from __future__ import annotations

import math

import pytest

import qibt.metrics as M

SR_DAY = 2.5 / math.sqrt(250)
VAR_DAY = 0.5 / 250


def test_dsr_example_sr0():
    assert M.expected_max_sr(VAR_DAY, 100) == pytest.approx(0.1132, abs=5e-5)


@pytest.mark.parametrize("n_trials,want", [(100, 0.9004), (46, 0.9505)])
def test_dsr_example(n_trials, want):
    sr0 = M.expected_max_sr(VAR_DAY, n_trials)
    assert M.psr(SR_DAY, sr0, 1250, -3.0, 10.0) == pytest.approx(want, abs=1e-3)


@pytest.mark.parametrize("n,skew,kurt,want", [
    (24, 0.0, 3.0, 0.982),
    (24, -2.448, 10.164, 0.913),
    (36, -2.448, 10.164, 0.953),
])
def test_psr_example(n, skew, kurt, want):
    assert M.psr(0.458, 0.0, n, skew, kurt) == pytest.approx(want, abs=1e-3)


def test_falsifier_kurtosis_term_without_minus_one_is_detected():
    """(kurt)/4 instead of (kurt - 1)/4 misses the paper's 0.913 by more than the tolerance."""
    sr, n, skew, kurt = 0.458, 24, -2.448, 10.164
    z = sr * math.sqrt(n - 1) / math.sqrt(1 - skew * sr + kurt / 4 * sr ** 2)
    wrong = 0.5 * math.erfc(-z / math.sqrt(2))
    assert abs(wrong - 0.913) > 1e-3
    assert M.psr(sr, 0.0, n, skew, kurt) == pytest.approx(0.913, abs=1e-3)
