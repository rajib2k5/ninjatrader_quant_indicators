"""test_strategies_static.py - static checks of the generated NinjaTrader backtest strategies.

Educational research only. Not financial advice. See DISCLAIMER.md.

Checks strategies/QS_*.cs (made by backtest/gen_strategies.py) against backtest/rules.yaml and the
indicators/QI_*.cs they were transplanted from, WITHOUT importing the generator (the parsing here is a
separate implementation, so a generator bug cannot hide itself):

  * every rule has exactly one QS file (QS_<Module>.cs or, after the relabel, QS_<NN>_<Module>.cs) and
    no QS file exists without a rule;
  * every order call (Enter*/Exit*/Submit*/Set*) sits inside ApplyRule(), after the realtime guard;
  * `BacktestOnly = true` in SetDefaults, the property and the strategy defaults are present;
  * the C# threshold literals in ApplyRule equal rules.yaml (parity), and the value read is the expected
    series; test_falsifier_parity_detects_altered_threshold proves the parity check can fail;
  * the QI logic is transplanted unchanged (QiUpdate body, helpers, properties);
  * the DISCLAIMER block is copied verbatim into the header, the banner sentence is present;
  * no absolute user paths;
  * (slow) the QI + QS files compile with validation/probes/compile_probe.sh.

Run from the repo root:
    python -I -m pytest backtest/tests/test_strategies_static.py -q -p no:cacheprovider
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
RULES_PATH = REPO / "backtest" / "rules.yaml"
IND_DIR = REPO / "indicators"
STRAT_DIR = REPO / "strategies"
COMPILE_PROBE = REPO / "validation" / "probes" / "compile_probe.sh"

with warnings.catch_warnings():  # the marker is registered by validation/pytests/conftest.py, not here
    warnings.simplefilter("ignore")
    slow = pytest.mark.slow

_DOC = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
RULES = _DOC["rules"]
FROZEN = str(_DOC["frozen"])
FRAME_TEXT = {"D": "Day bars", "15m": "15 Minute bars"}

# rules.yaml `value` -> public Series<double> read with [0] (independent copy of the task's mapping).
# None = computed in ApplyRule (bollinger_touch).
EXPECTED_ACCESSOR = {
    "hp_score": "HPScore", "ibs_daily": "IBS", "rsi2": "RSI2", "connors_rsi": "CRSI", "stoch_k": "K",
    "rv_zscore": "RVZScore", "composite_vol": "CompositeVol", "turn_of_month": "TurnOfMonth",
    "consec_streak": "Streak", "overnight_gap_pct": "GapPct", "bollinger_touch": None,
    "day_of_week": "DayOfWeekValue", "rsi14": "RSI14", "vrp_proxy": "VRPProxy", "wide_range": "WideRange",
    "vwap_distance": "VwapDistance", "macd_hist": "Histogram", "ema_spread": "Spread",
    "sma200_distance": "Distance", "atr_regime": "ATRRegime", "volume_spike": "VolumeSpike",
    "cum_delta20": "CumDelta20", "sweep_structure": "Structure", "ofp_structure": "Structure",
    "smc_structure": "Structure",
}

REALTIME_GUARD = "if (BacktestOnly && !OrdersAllowed()) return;"
# BT16 (validation/channel-a-backtest.md): OrdersAllowed() must refuse every non-historical state,
# every account that is not Backtest/Sim*/Playback*, and the last two historical bars of a
# non-Backtest account; Configure must force StartBehavior.WaitUntilFlat when BacktestOnly.
ORDERS_ALLOWED_BODY = [
    "if (State != State.Historical) return false;",
    'string acct = Account != null ? Account.Name : string.Empty;',
    'bool backtest = acct == "Backtest";',
    'bool research = backtest || acct.StartsWith("Sim") || acct.StartsWith("Playback");',
    "if (!research) return false;",
    "if (!backtest && CurrentBars[0] >= BarsArray[0].Count - 2) return false;",
    "return true;",
]
ORDER_CALL_RE = re.compile(
    r"\b(?:Enter|Exit)(?:Long|Short)\w*\s*\(|\b(?:SubmitOrder\w*|SetStopLoss|SetProfitTarget|SetTrailStop|"
    r"ChangeOrder|CancelOrder|CancelAllOrders)\b")
STRATEGY_DEFAULTS = {
    "EntriesPerDirection": "1",
    "EntryHandling": "EntryHandling.AllEntries",
    "IsExitOnSessionCloseStrategy": "false",
    "StartBehavior": "StartBehavior.WaitUntilFlat",
    "BarsRequiredToTrade": "0",
    "Slippage": "1",
    "DefaultQuantity": "1",
    "BacktestOnly": "true",
    "TraceOrders": "false",
    "Calculate": "Calculate.OnBarClose",
}


# ---------------------------------------------------------------------------------------------
#  helpers
# ---------------------------------------------------------------------------------------------
def _find_one(directory: Path, prefix: str, module: str):
    pat = re.compile(r"^%s_(?:\d\d_)?%s\.cs$" % (prefix, re.escape(module)))
    return sorted(p for p in directory.glob(prefix + "_*.cs") if pat.match(p.name))


def qs_file(module):
    found = _find_one(STRAT_DIR, "QS", module)
    assert len(found) == 1, "%s: expected exactly one QS file, found %s" % (module, [p.name for p in found])
    return found[0]


def qi_file(module):
    found = _find_one(IND_DIR, "QI", module)
    assert len(found) == 1, "%s: expected exactly one QI file, found %s" % (module, [p.name for p in found])
    return found[0]


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def strip_code(text: str) -> str:
    """Remove comments and string-literal contents, keeping line numbers."""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), text, flags=re.S)
    out = []
    for ln in text.split("\n"):
        ln = re.sub(r'"(?:\\.|[^"\\])*"', '""', ln)
        ln = re.sub(r"//.*$", "", ln)
        out.append(ln)
    return "\n".join(out)


def method_span(lines, signature):
    """(start, end) line indexes of the 2-tab method whose signature line equals `signature`."""
    starts = [i for i, ln in enumerate(lines) if ln.strip() == signature and ln.startswith("\t\t") and
              not ln.startswith("\t\t\t")]
    assert len(starts) == 1, "%r found %d times" % (signature, len(starts))
    for j in range(starts[0] + 1, len(lines)):
        if lines[j] == "\t\t}":
            return starts[0], j
    raise AssertionError("no closing brace for %r" % signature)


def apply_rule_text(text: str) -> str:
    lines = text.split("\n")
    s, e = method_span(lines, "private void ApplyRule()")
    return "\n".join(lines[s:e + 1])


def set_defaults_text(text: str) -> str:
    m = re.search(r"if \(State == State\.SetDefaults\)(.*?)else if \(State == State\.Configure\)", text, re.S)
    assert m, "SetDefaults block not found"
    return m.group(1)


def header_text(text: str) -> str:
    """Header comment block (before `#region Using declarations`), `//` stripped, whitespace collapsed."""
    k = text.index("#region Using declarations")
    return re.sub(r"\s+", " ", re.sub(r"(?m)^//", "", text[:k])).strip()


# ---- parity ---------------------------------------------------------------------------------
_FLIP = {"<": ">", "<=": ">="}
_CS_PART = re.compile(r"^x\s*(<=|>=|==|<|>)\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)$")


def yaml_constraints(cond):
    """Canonical constraints on x for a rules.yaml condition: None (never) or a sorted [(op, number)]."""
    c = str(cond).strip()
    if c == "never":
        return None
    m = re.fullmatch(r"x\s*(<=|>=|==|<|>)\s*(\S+)", c)
    if m:
        return [(m.group(1), float(m.group(2)))]
    m = re.fullmatch(r"(\S+)\s*(<=|<)\s*x\s*(<=|<)\s*(\S+)", c)
    if m:
        return sorted([(_FLIP[m.group(2)], float(m.group(1))), (m.group(3), float(m.group(4)))])
    raise AssertionError("unsupported rules.yaml condition %r" % (cond,))


def cs_constraints(expr):
    """Same canonical form for the C# boolean expression of `bool goLong/goShort = <expr>;`."""
    e = expr.strip()
    if e == "false":
        return None
    parts = [p.strip().strip("()").strip() for p in e.split("&&")]
    out = []
    for p in parts:
        m = _CS_PART.match(p)
        if not m:
            raise AssertionError("unparseable C# condition part %r" % p)
        out.append((m.group(1), float(m.group(2))))
    return sorted(out)


def parity_errors(rule, apply_text):
    """Mismatches between rules.yaml and the ApplyRule C# (empty list = parity holds)."""
    errs = []
    code = strip_code(apply_text)
    for side, var in (("long", "goLong"), ("short", "goShort")):
        m = re.search(r"\bbool\s+%s\s*=\s*([^;]+);" % var, code)
        if not m:
            errs.append("%s: no `bool %s = ...;` in ApplyRule" % (side, var))
            continue
        try:
            got = cs_constraints(m.group(1))
        except AssertionError as exc:
            errs.append("%s: %s" % (side, exc))
            continue
        want = yaml_constraints(rule[side])
        if got != want:
            errs.append("%s: C# %r != rules.yaml %r (%s)" % (side, got, want, rule[side]))
    if not re.search(r"if\s*\(goLong\)\s*target\s*=\s*1\s*;\s*else\s+if\s*\(goShort\)\s*target\s*=\s*-1\s*;", code):
        errs.append("target mapping goLong -> +1 / goShort -> -1 not found")
    acc = EXPECTED_ACCESSOR[rule["value"]]
    if acc is not None:
        if not re.search(r"if\s*\(%s\.IsValidDataPoint\(0\)\)\s*x\s*=\s*%s\[0\]\s*;" % (acc, acc), code):
            errs.append("value read `x = %s[0]` (guarded by IsValidDataPoint) not found" % acc)
    else:
        for needle in ("Close[0] <= Lower[0] + 0.001 * atr", "Close[0] >= Upper[0] - 0.001 * atr"):
            if needle not in code:
                errs.append("bollinger_touch expression %r not found" % needle)
    return errs


# ---------------------------------------------------------------------------------------------
#  tests
# ---------------------------------------------------------------------------------------------
RULE_IDS = [r["module"] for r in RULES]


def test_rules_yaml_values_all_have_an_expected_accessor():
    assert {r["value"] for r in RULES} <= set(EXPECTED_ACCESSOR)


def test_every_rule_has_exactly_one_qs_file_and_no_extras():
    expected = {qs_file(r["module"]).name for r in RULES}
    assert len(expected) == len(RULES)
    on_disk = {p.name for p in STRAT_DIR.glob("QS_*.cs")}
    assert on_disk == expected, "stale or missing: %s" % sorted(on_disk ^ expected)


@pytest.mark.parametrize("module", RULE_IDS)
def test_class_name_matches_file_and_is_a_strategy(module):
    p = qs_file(module)
    text = read(p)
    assert re.search(r"^namespace NinjaTrader\.NinjaScript\.Strategies$", text, re.M)
    assert re.search(r"^\tpublic class %s : Strategy$" % re.escape(p.stem), text, re.M)
    assert re.search(r'^\t+Name\t+= "%s";$' % re.escape(p.stem), set_defaults_text(text), re.M)
    assert ": Indicator" not in strip_code(text)
    assert "Backtest research strategy generated from QI_" in text
    assert "Places no orders in real time unless Backtest Only is turned off." in text


@pytest.mark.parametrize("module", RULE_IDS)
def test_order_calls_only_inside_apply_rule_after_realtime_guard(module):
    text = read(qs_file(module))
    lines = text.split("\n")
    s, e = method_span(lines, "private void ApplyRule()")
    code_lines = strip_code(text).split("\n")

    # the guard is the first statement of ApplyRule
    first = next(ln.strip() for ln in code_lines[s + 2:e] if ln.strip())
    assert first == REALTIME_GUARD, "first ApplyRule statement is %r" % first
    guard_line = s + 2 + next(i for i, ln in enumerate(code_lines[s + 2:e]) if ln.strip())

    calls = [(i, m.group(0)) for i, ln in enumerate(code_lines) for m in ORDER_CALL_RE.finditer(ln)]
    assert calls, "no order calls at all"
    for i, call in calls:
        assert guard_line < i < e, "order call %r at line %d is outside ApplyRule after the guard" % (call, i + 1)
    names = sorted(re.sub(r"\s*\($", "", c) for _, c in calls)
    assert names == ["EnterLong", "EnterShort", "ExitLong", "ExitShort"], names

    # exact order wiring
    block = "\n".join(code_lines[s:e + 1])
    for needle in ('EnterLong(DefaultQuantity, "")', 'EnterShort(DefaultQuantity, "")',
                   'ExitLong("", "")', 'ExitShort("", "")'):
        assert needle in block, needle
    raw = "\n".join(lines[s:e + 1])
    for needle in ('EnterLong(DefaultQuantity, "QS_L")', 'EnterShort(DefaultQuantity, "QS_S")',
                   'ExitLong("QS_XL", "QS_L")', 'ExitShort("QS_XS", "QS_S")',
                   "Position.MarketPosition != MarketPosition.Long", "Position.MarketPosition != MarketPosition.Short"):
        assert needle in raw, needle

    # ApplyRule is reached only from OnBarUpdate
    ob_s, ob_e = method_span(lines, "protected override void OnBarUpdate()")
    on_bar = "\n".join(lines[ob_s:ob_e + 1])
    assert re.search(r"QiUpdate\(\);\s*ApplyRule\(\);", on_bar)
    assert len(re.findall(r"\bApplyRule\s*\(", strip_code(text))) == 2  # declaration + the one call


@pytest.mark.parametrize("module", RULE_IDS)
def test_backtest_only_true_in_setdefaults_and_property_present(module):
    text = read(qs_file(module))
    sd = strip_code(set_defaults_text(text))
    assert re.search(r"\bBacktestOnly\s*=\s*true\s*;", sd)
    assert not re.search(r"\bBacktestOnly\s*=\s*false", text)
    for name, val in STRATEGY_DEFAULTS.items():
        assert re.search(r"^\s*%s\s*=\s*%s\s*;" % (name, re.escape(val)), sd, re.M), "%s = %s" % (name, val)
    assert ("\t\t[NinjaScriptProperty]\n"
            '\t\t[Display(Name = "Backtest Only", Order = 0, GroupName = "Safety")]\n'
            "\t\tpublic bool BacktestOnly { get; set; }\n") in text


@pytest.mark.parametrize("module", RULE_IDS)
def test_threshold_and_value_parity_with_rules_yaml(module):
    rule = next(r for r in RULES if r["module"] == module)
    text = read(qs_file(module))
    assert parity_errors(rule, apply_rule_text(text)) == []
    acc = EXPECTED_ACCESSOR[rule["value"]]
    if acc is not None:  # the accessor must be a public Series<double> of the QI module itself
        assert re.search(r"public Series<double> %s\b" % acc, read(qi_file(module))), (module, acc)
    else:
        assert re.search(r"^\t{4}atr14\t+= ATR\(14\);$", text, re.M)  # created in State.DataLoaded
        dl = re.search(r"else if \(State == State\.DataLoaded\)(.*?)\n\t\t\t\}", text, re.S)
        assert dl and "atr14" in dl.group(1)
        assert re.search(r"^\t\tprivate ATR\t+atr14;$", text, re.M)


def test_falsifier_parity_detects_altered_threshold():
    """The parity check must FAIL on a threshold / operator / value / side that differs from rules.yaml."""
    ibs = next(r for r in RULES if r["module"] == "IBS")
    good = apply_rule_text(read(qs_file("IBS")))
    assert parity_errors(ibs, good) == [], "clean IBS must pass, else the falsifier proves nothing"

    mutants = {
        "threshold 0.20 -> 0.21": good.replace("x < 0.20", "x < 0.21"),
        "upper threshold 0.80 -> 0.79": good.replace("x > 0.80", "x > 0.79"),
        "operator < -> <=": good.replace("x < 0.20", "x <= 0.20"),
        "sides swapped": good.replace("goLong  = x < 0.20", "goLong  = x > 0.80").replace(
            "goShort = x > 0.80", "goShort = x < 0.20"),
        "short disabled": good.replace("goShort = x > 0.80", "goShort = false"),
        "wrong series": good.replace("IBS.IsValidDataPoint(0)", "RSI2.IsValidDataPoint(0)").replace(
            "x = IBS[0]", "x = RSI2[0]"),
    }
    for label, mutant in mutants.items():
        assert mutant != good, "mutation %r did not change the text" % label
        assert parity_errors(ibs, mutant), "parity check missed: %s" % label

    # a range rule and a `never` rule must be covered as well
    vwap = next(r for r in RULES if r["module"] == "VWAPDistance")
    vgood = apply_rule_text(read(qs_file("VWAPDistance")))
    assert parity_errors(vwap, vgood) == []
    assert parity_errors(vwap, vgood.replace("x > -0.5 && x < 0.0", "x > -0.6 && x < 0.0"))
    tom = next(r for r in RULES if r["module"] == "TurnOfMonth")
    tgood = apply_rule_text(read(qs_file("TurnOfMonth")))
    assert parity_errors(tom, tgood) == []
    assert parity_errors(tom, tgood.replace("goShort = false", "goShort = x < 0.0"))


@pytest.mark.parametrize("module", RULE_IDS)
def test_header_disclaimer_banner_and_no_user_paths(module):
    p = qs_file(module)
    text = read(p)
    rule = next(r for r in RULES if r["module"] == module)
    hdr = header_text(text)

    # DISCLAIMER block copied verbatim from the QI file
    qi_text = read(qi_file(module))
    m = re.search(r"(?m)^//  DISCLAIMER\n(?://.*\n)*?//  DISCLAIMER\.md in the repository root\.$", qi_text)
    assert m, "no DISCLAIMER block in the QI header"
    block = m.group(0)
    assert block in text, "DISCLAIMER block is not verbatim in %s" % p.name
    assert "NOT financial, investment, or trading advice" in hdr

    banner = ("%s - BACKTEST RESEARCH STRATEGY. Rules: backtest/rules.yaml (frozen %s), the original IBSFade "
              "indicator's own classification. Home frame: %s. Generated by backtest/gen_strategies.py - "
              "do not edit by hand." % (p.stem, FROZEN, FRAME_TEXT[rule["frame"]]))
    assert banner in hdr, "banner sentence missing/wrong:\n%s" % hdr[:600]

    assert not re.search(r"[A-Za-z]:[\\/]+Users", text, re.I), "absolute user path in %s" % p.name
    assert "C:\\Users" not in text and "C:/Users" not in text


@pytest.mark.parametrize("module", RULE_IDS)
def test_indicator_logic_is_transplanted_unchanged(module):
    qs, qi = read(qs_file(module)), read(qi_file(module))
    qs_l, qi_l = qs.split("\n"), qi.split("\n")

    s1, e1 = method_span(qi_l, "protected override void OnBarUpdate()")
    s2, e2 = method_span(qs_l, "private void QiUpdate()")
    assert qi_l[s1 + 1:e1 + 1] == qs_l[s2 + 1:e2 + 1], "QiUpdate body differs from the indicator OnBarUpdate"

    for sig in ("private void DrawDisclaimerOnce()",):
        a, b = method_span(qi_l, sig), method_span(qs_l, sig)
        assert qi_l[a[0]:a[1] + 1] == qs_l[b[0]:b[1] + 1], sig

    def properties(t):
        return t[t.index("#region Properties"):t.index("#endregion", t.index("#region Properties"))]

    backtest_only = ("\t\t[NinjaScriptProperty]\n"
                     '\t\t[Display(Name = "Backtest Only", Order = 0, GroupName = "Safety")]\n'
                     "\t\tpublic bool BacktestOnly { get; set; }\n\n")
    assert properties(qs).replace(backtest_only, "", 1) == properties(qi)


def test_no_extra_data_series_or_state_handling_beyond_the_qi_source():
    """The strategies add no data series; the only added State test is OrdersAllowed's
    `State != State.Historical`."""
    for r in RULES:
        qs, qi = strip_code(read(qs_file(r["module"]))), strip_code(read(qi_file(r["module"])))
        assert qs.count("AddDataSeries(") == qi.count("AddDataSeries(")
        assert qs.count("State ==") == qi.count("State ==")
        assert qs.count("State != State.Historical") == 1


@pytest.mark.parametrize("module", RULE_IDS)
def test_orders_allowed_guard_is_complete(module):
    """BT16: the exact guard body, and the StartBehavior override as the first Configure statement."""
    text = read(qs_file(module))
    lines = text.split("\n")
    s, e = method_span(lines, "private bool OrdersAllowed()")
    # raw lines (strip_code blanks string literals, and the account names ARE the guard)
    body = [ln.strip() for ln in lines[s + 2:e] if ln.strip() and not ln.strip().startswith("//")]
    assert body == ORDERS_ALLOWED_BODY, body
    m = re.search(r"else if \(State == State\.Configure\)\s*\{\s*if \(BacktestOnly\)\s*StartBehavior = StartBehavior\.WaitUntilFlat;",
                  strip_code(text))
    assert m, "Configure does not start with the BacktestOnly StartBehavior override"


def test_falsifier_weak_guard_is_detected():
    """A realtime-only guard (the pre-BT16 form) fails the guard-completeness test's body check."""
    weak = ["if (State == State.Realtime) return false;", "return true;"]
    assert weak != ORDERS_ALLOWED_BODY


# ---- compile smoke (slow) ------------------------------------------------------------------
def _git_bash():
    for cand in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if os.path.exists(cand):
            return cand
    b = shutil.which("bash")
    if b and "system32" not in b.lower():  # WSL's launcher cannot see the Windows dotnet/cygpath
        return b
    return None


@pytest.fixture(scope="module")
def bash():
    b = _git_bash()
    if b is None:
        pytest.skip("Git bash not found")
    if shutil.which("dotnet") is None:
        pytest.skip("dotnet not on PATH")
    if not COMPILE_PROBE.exists():
        pytest.skip("compile_probe.sh missing")
    script = COMPILE_PROBE.read_text(encoding="utf-8")
    for key in ("CSC", "NT"):
        m = re.search(r'^%s="([^"]+)"' % key, script, re.M)
        if not m:
            pytest.skip("compile_probe.sh has no %s" % key)
        p = re.sub(r"^/([a-zA-Z])/", lambda mm: mm.group(1).upper() + ":/", m.group(1))
        if not os.path.exists(p):
            pytest.skip("%s not found: %s" % (key, p))
    return b


def _probe(bash_exe, files, out_dll):
    env = dict(os.environ, OUT=str(out_dll).replace("\\", "/"))  # OUT is under pytest tmp_path, never the repo
    proc = subprocess.run([bash_exe, str(COMPILE_PROBE).replace("\\", "/")] + [str(f).replace("\\", "/") for f in files],
                          capture_output=True, text=True, env=env, timeout=600)
    return proc.returncode, proc.stdout + proc.stderr


@slow
def test_compile_all_qi_and_qs_together(bash, tmp_path):
    files = sorted(IND_DIR.glob("QI_*.cs")) + sorted(STRAT_DIR.glob("QS_*.cs"))
    assert len(files) > len(RULES)
    rc, out = _probe(bash, files, tmp_path / "all.dll")
    assert rc == 0, out[-3000:]


QS_FILES = sorted(STRAT_DIR.glob("QS_*.cs"))


@slow
@pytest.mark.parametrize("path", QS_FILES, ids=[p.name for p in QS_FILES])
def test_each_qs_compiles_alone(bash, path, tmp_path):
    rc, out = _probe(bash, [path], tmp_path / "one.dll")
    assert rc == 0, "%s failed alone (rc=%d):\n%s" % (path.name, rc, out[-3000:])


@slow
def test_compile_probe_rejects_a_strategy_mutant(bash, tmp_path):
    """Control: a one-token mutation of a QS file must fail to compile, so rc=0 above means something."""
    src = read(QS_FILES[0])
    mutant = src.replace(REALTIME_GUARD, REALTIME_GUARD.replace("return;", "retur;"), 1)
    assert mutant != src
    m = tmp_path / QS_FILES[0].name
    m.write_bytes(mutant.encode("utf-8"))
    rc, out = _probe(bash, [m], tmp_path / "mutant.dll")
    assert rc != 0 and "error" in out.lower(), out[-1500:]
