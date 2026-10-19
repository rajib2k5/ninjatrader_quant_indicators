"""test_repo_invariants.py - static checks on indicators/*.cs encoding the project brief.

This is the ONE place in the suite that reads the C# sources - as text, never as a formula
source. Comments are stripped before string-literal checks so the DISCLAIMER header's own
wording ("buy or sell") does not trip the literal test.
"""
from __future__ import annotations

import re

import pytest

from vp_helpers import INDICATORS_DIR

FILES = sorted(INDICATORS_DIR.glob("QI_*.cs"))
assert FILES, "no indicators/QI_*.cs files found"

_COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
_LITERAL_RE = re.compile(r'@"(?:[^"]|"")*"|"(?:[^"\\\n]|\\.)*"')
_BUY_SELL_RE = re.compile(r"\b(buy|sell)\b", re.I)
_TP_SL_RE = re.compile(r"\b(TP|SL)\b|take[\s-]?profit|stop[\s-]?loss", re.I)


def _src(path):
    return path.read_text(encoding="utf-8")


def _code(path):
    return _COMMENT_RE.sub("", _src(path))


def _literals(path):
    return _LITERAL_RE.findall(_code(path))


def _is_overlay(path):
    m = re.findall(r"\bIsOverlay\s*=\s*(true|false)\s*;", _code(path))
    assert len(m) == 1, "%s: IsOverlay assigned %d times" % (path.name, len(m))
    return m[0] == "true"


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_no_buy_sell_string_literal(path):
    hits = [lit for lit in _literals(path) if _BUY_SELL_RE.search(lit)]
    assert not hits, "%s contains Buy/Sell literals: %s" % (path.name, hits[:5])


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_no_arrow_up_down_drawing(path):
    assert not re.search(r"Draw\.Arrow(Up|Down)\b", _code(path)), "%s draws arrows" % path.name


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_no_tp_sl_drawing(path):
    code = _code(path)
    hits = [lit for lit in _LITERAL_RE.findall(code) if _TP_SL_RE.search(lit)]
    assert not hits, "%s has TP/SL literals: %s" % (path.name, hits[:5])
    draw_lines = [ln for ln in code.splitlines() if "Draw." in ln and re.search(r"\b(TP|SL|TakeProfit|StopLoss|takeProfit|stopLoss)\b", ln)]
    assert not draw_lines, "%s draws TP/SL objects: %s" % (path.name, draw_lines[:3])


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_no_streamwriter_or_hardcoded_user_paths(path):
    code = _code(path)
    assert "StreamWriter" not in code, "%s uses StreamWriter" % path.name
    assert not re.search(r"C:\\+Users", _src(path), re.I), "%s has a hard-coded C:\\Users path" % path.name


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_disclaimer_header_and_property(path):
    head = "\n".join(_src(path).splitlines()[:25])
    assert re.search(r"^//\s*DISCLAIMER\s*$", head, re.M), "%s lacks the DISCLAIMER header" % path.name
    assert "educational" in head.lower() and "not financial" in head.lower()
    assert re.search(r"public\s+bool\s+ShowDisclaimer\s*\{\s*get;\s*set;\s*\}", _code(path)), (
        "%s lacks a ShowDisclaimer property" % path.name)


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_is_overlay_declared_exactly_once(path):
    assert len(re.findall(r"\bIsOverlay\s*=", _code(path))) == 1


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_overlay_has_no_addline_and_panel_has_visible_plot(path):
    code = _code(path)
    plots = re.findall(r"AddPlot\(([^;]*)\);", code)
    if _is_overlay(path):
        assert "AddLine(" not in code, "%s is an overlay but calls AddLine" % path.name
    else:
        visible = [p for p in plots if "Brushes.Transparent" not in p]
        assert visible, "%s is a panel indicator without a visible AddPlot" % path.name


def test_expected_module_count():
    assert len(FILES) == 27, [p.name for p in FILES]


def test_falsifier_literal_scanner_detects_planted_buy():
    """The literal scanner itself must flag a planted literal (and ignore it in a comment)."""
    assert _BUY_SELL_RE.search('"Buy signal"')
    assert not any(_BUY_SELL_RE.search(l) for l in _LITERAL_RE.findall(_COMMENT_RE.sub("", '// "Buy"\nx = "ok";')))
    assert any(_BUY_SELL_RE.search(l) for l in _LITERAL_RE.findall(_COMMENT_RE.sub("", 'x = "SELL now";')))
    assert not _BUY_SELL_RE.search('"Buyers"')
