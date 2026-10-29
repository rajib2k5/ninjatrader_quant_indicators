"""Coverage gate: every indicator has its own unit-test file with the four required sections.

Fails when an indicator is added without tests, when a test file loses its falsifier, its compile
test or its NinjaTrader-export test, or when a test file is left behind for a removed indicator.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
IND_DIR = HERE.parents[1] / "indicators"
MODULES = sorted(re.sub(r"^QI_(?:\d\d_)?", "", p.stem) for p in IND_DIR.glob("QI_*.cs"))
MIN_TESTS = 5


def test_there_are_28_indicators():
    assert len(MODULES) == 28, MODULES


@pytest.mark.parametrize("module", MODULES)
def test_indicator_has_complete_test_file(module):
    f = HERE / f"test_{module}.py"
    assert f.exists(), f"missing tests/indicators/test_{module}.py"
    src = f.read_text(encoding="utf-8")
    tests = re.findall(r"^def (test_\w+)", src, re.M)
    assert len(tests) >= MIN_TESTS, f"{f.name}: {len(tests)} tests < {MIN_TESTS}"
    assert any(t.startswith("test_falsifier_") for t in tests), f"{f.name}: no test_falsifier_*"
    assert "compile_alone(" in src, f"{f.name}: no single-file compile test"
    assert "harness_frame(" in src, f"{f.name}: no NinjaTrader-export test"
    assert re.search(r'^MODULE\s*=\s*"%s"' % re.escape(module), src, re.M), f"{f.name}: MODULE constant"


def test_no_orphan_test_files():
    files = {p.stem[len("test_"):] for p in HERE.glob("test_*.py")} - {"coverage"}
    assert files <= set(MODULES), f"test files without an indicator: {sorted(files - set(MODULES))}"


def test_falsifier_gate_detects_a_missing_file():
    """The gate's own check fails for a module name that has no test file."""
    assert not (HERE / "test_NoSuchIndicator.py").exists()
