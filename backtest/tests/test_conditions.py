"""Condition grammar of rules.yaml and the value -> position mapping (PROTOCOL section 4)."""
from __future__ import annotations

import builtins
import math

import numpy as np
import pytest

from qibt import signals
from qibt.signals import Condition, parse_condition, to_positions

NAN = math.nan
CASES = [
    ("x < 0.20", [0.1, 0.2, 0.3, NAN], [True, False, False, False]),
    ("x <= -35", [-36, -35, -34, NAN], [True, True, False, False]),
    ("x > 2.0", [2.0, 2.0001, -5, NAN], [False, True, False, False]),
    ("x >= 35", [34.999, 35, 36, NAN], [False, True, True, False]),
    ("x == 1", [1, 0.999999, -1, NAN], [True, False, False, False]),
    ("x == -1", [-1, 1, 0], [True, False, False]),
    ("x < -0.3", [-0.31, -0.3, 0], [True, False, False]),
    ("-0.5 < x < 0", [-0.5, -0.49, 0, -0.1, NAN], [False, True, False, True, False]),
    ("0 < x < 0.5", [0, 0.25, 0.5, 0.4999], [False, True, False, True]),
    ("never", [0, 1, -1, NAN], [False, False, False, False]),
]


def check_parser(parse):
    """Failures of a parser implementation against the hand cases (empty list = all right)."""
    bad = []
    for text, vals, want in CASES:
        got = list(np.asarray(parse(text).mask(np.array(vals, dtype=float)), dtype=bool))
        if got != want:
            bad.append((text, vals, got, want))
    return bad


def test_parser_hand_cases():
    assert check_parser(parse_condition) == []


@pytest.mark.parametrize("text", ["x<0.2", "  x <  0.2 ", "x<.2", "x < 2e-1", "x < +0.2"])
def test_whitespace_and_number_forms(text):
    c = parse_condition(text)
    assert (c.kind, c.op, c.a) == ("cmp", "<", 0.2)


def test_range_form():
    c = parse_condition("-0.5<x<0")
    assert (c.kind, c.a, c.b) == ("range", -0.5, 0.0)


@pytest.mark.parametrize("text", [
    "x < a", "y < 1", "x << 1", "1 < x", "x != 1", "x =< 1", "0.5 < x < -0.5", "0 < x < 0",
    "x < 1 or True", "", "x", "x < nan", "x < inf", "x < 1e400", "never ever", "0 <= x < 1",
    "__import__('os').system('echo pwned')", "x < 1; import os",
])
def test_rejects_anything_outside_the_grammar(text):
    with pytest.raises(ValueError):
        parse_condition(text)


def test_rejects_non_string():
    with pytest.raises(ValueError):
        parse_condition(0.2)


def test_parser_never_uses_eval(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("eval/exec called")
    monkeypatch.setattr(builtins, "eval", boom)
    monkeypatch.setattr(builtins, "exec", boom)
    rs = signals.load_rules()
    assert len(rs.rules) == 25


def test_every_rules_yaml_condition_parses_and_matches_text():
    rs = signals.load_rules()
    assert len(rs.rules) == 25
    assert sorted(x["module"] for x in rs.not_backtestable) == ["ChopIndex", "KeyLevels"]
    by = {r.module: r for r in rs.rules}
    assert (by["HedgingPressure"].long.op, by["HedgingPressure"].long.a) == ("<=", -35.0)
    assert (by["RVZScore"].short.op, by["RVZScore"].short.a) == ("<", -1.5)
    assert (by["VWAPDistance"].long.kind, by["VWAPDistance"].long.a, by["VWAPDistance"].long.b) == ("range", -0.5, 0.0)
    assert by["TurnOfMonth"].short.kind == "never"
    long_only = {r.module for r in rs.rules if r.short.kind == "never"}
    assert long_only == {"TurnOfMonth", "TurnaroundTuesday", "WideRangeBar", "ATRRegime", "VolumeSpike"}


def test_to_positions_long_short_flat_nan():
    v = np.array([-1.0, 0.0, 1.0, NAN, 0.5])
    p = to_positions(v, parse_condition("x < 0"), parse_condition("x > 0.6"))
    assert p.tolist() == [1, 0, -1, 0, 0]


def test_long_only_rule_is_never_short():
    rng = np.random.default_rng(1)
    v = rng.normal(0, 3, 1000)
    p = to_positions(v, parse_condition("x > 1.2"), parse_condition("never"))
    assert set(np.unique(p)) <= {0, 1} and (p == 1).sum() == (v > 1.2).sum()


def test_overlapping_conditions_raise():
    with pytest.raises(ValueError):
        to_positions(np.array([0.5]), parse_condition("x > 0"), parse_condition("x < 1"))


# --------------------------------------------------------------------------------------------
# falsifiers: deliberately wrong parsers must be caught by the same hand cases
# --------------------------------------------------------------------------------------------
def test_falsifier_strict_vs_inclusive_confusion_is_detected():
    def sloppy(text):  # treats every strict comparison as inclusive
        c = parse_condition(text)
        if c.kind == "cmp" and c.op in ("<", ">"):
            return Condition(text, "cmp", op=c.op + "=", a=c.a)
        return c
    assert check_parser(sloppy) != []


def test_falsifier_nan_mapped_to_zero_is_detected():
    class NanAsZero:
        def __init__(self, c):
            self.c = c

        def mask(self, v):
            return self.c.mask(np.nan_to_num(np.asarray(v, dtype=float), nan=0.0))
    assert check_parser(lambda t: NanAsZero(parse_condition(t))) != []
