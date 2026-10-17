#!/usr/bin/env python3
"""gen_strategies.py - generate one NinjaTrader 8 backtest strategy per rule in backtest/rules.yaml.

Educational research only. Not financial advice. See DISCLAIMER.md.

For every rule, strategies/QS_<Module>.cs is produced MECHANICALLY from indicators/QI_<Module>.cs
("transplant, do not re-implement"): the strategy computes exactly the value the indicator computes,
and only then maps it to a target position with the rule's frozen thresholds.

Transplant steps (all done on the QI source text, nothing is re-typed):
  1. `public class QI_X : Indicator` -> `public class QS_X : Strategy`; namespace ...Indicators ->
     ...Strategies; `using NinjaTrader.NinjaScript.Indicators;` is added (the NT8 strategy template has it;
     QI_BollingerPctB needs the `Bollinger` type).
  2. The indicator's `protected override void OnBarUpdate()` becomes `private void QiUpdate()`; a new
     `OnBarUpdate() { QiUpdate(); ApplyRule(); }` is inserted right after it.
  3. SetDefaults: Name -> "QS_X"; Description gets the research-strategy sentence appended; the strategy
     defaults are inserted after the `Calculate` line; indicator-only assignments listed in
     INDICATOR_ONLY_REMOVED are deleted; `BacktestOnly = true`.
  4. DisplayName "QI ..." -> "QS ..."; the `BacktestOnly` property is added at the top of
     `#region Properties`.
  5. Header: new banner + the DISCLAIMER block copied verbatim from the QI file; the rest of the QI
     header (title, lineage, formula, quirks) is kept under it.
  6. ApplyRule(): see render_apply_rule(). Thresholds are C# literals parsed from rules.yaml by a tiny
     regex parser (parse_condition); nothing is ever eval'd.

Indicator-only SetDefaults assignments removed. Found by compiling a naive QS_IBS transplant (class,
namespace and OnBarUpdate rename only, nothing removed) with validation/probes/compile_probe.sh; csc
rejected exactly these two on a Strategy, and nothing else is removed:
  - PaintPriceMarkers          error CS0103: name does not exist in the current context
  - IsSuspendedWhileInactive   error CS0103: name does not exist in the current context
Everything else the QI files assign or call (IsOverlay, DisplayInDataBox, DrawOnPricePanel,
ScaleJustification, ShowTransparentPlotsInDataBox, AddPlot, AddLine, Lines[i].Value, BackBrush, ...)
compiles on a Strategy (all 25 QS files compile, together with the QI files and each alone) and is kept.

Usage (from the repo root):
  python backtest/gen_strategies.py                          # all rules -> strategies/QS_*.cs
  python backtest/gen_strategies.py --names backtest/names.json
  python backtest/gen_strategies.py --only IBS,RSI2 --out C:/scratch/strat   # subset, no stale delete
  python backtest/gen_strategies.py --check                  # exit 1 if strategies/ is out of date

--names JSON: module name -> class name, optional, default identity (QI_<Module>/QS_<Module>). A value is
  "QI_01_IBS"  (QI class; QS class is the same with QI_ -> QS_)   or   "QS_01_IBS"  (QS class; QI derived)
  or "01_IBS"  (suffix; QI_/QS_ prepended)   or   {"qi": "QI_01_IBS", "qs": "QS_01_IBS"}.
With a mapping the generator reads indicators/<QI class>.cs and writes strategies/<QS class>.cs.

The generator is idempotent: it rewrites strategies/QS_*.cs byte-for-byte identically on every run
(files whose content is unchanged are not touched) and deletes stale QS_*.cs that no rule produces.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES_PATH = REPO / "backtest" / "rules.yaml"
INDICATORS_DIR = REPO / "indicators"
STRATEGIES_DIR = REPO / "strategies"

# Indicator-only assignments the compile probe rejected on a Strategy (see module docstring).
INDICATOR_ONLY_REMOVED = ("PaintPriceMarkers", "IsSuspendedWhileInactive")

FRAME_TEXT = {"D": "Day bars", "15m": "15 Minute bars"}

# rules.yaml `value` -> C# accessor (the module's public Series<double>, read with [0]).
# bollinger_touch is not a series: it is computed in ApplyRule (see render_apply_rule).
VALUE_SERIES = {
    "hp_score": "HPScore",
    "ibs_daily": "IBS",
    "rsi2": "RSI2",
    "connors_rsi": "CRSI",
    "stoch_k": "K",
    "rv_zscore": "RVZScore",
    "composite_vol": "CompositeVol",
    "turn_of_month": "TurnOfMonth",
    "consec_streak": "Streak",
    "overnight_gap_pct": "GapPct",
    "day_of_week": "DayOfWeekValue",
    "rsi14": "RSI14",
    "vrp_proxy": "VRPProxy",
    "wide_range": "WideRange",
    "vwap_distance": "VwapDistance",
    "macd_hist": "Histogram",
    "ema_spread": "Spread",
    "sma200_distance": "Distance",
    "atr_regime": "ATRRegime",
    "volume_spike": "VolumeSpike",
    "cum_delta20": "CumDelta20",
    "sweep_structure": "Structure",
    "ofp_structure": "Structure",
    "smc_structure": "Structure",
}
COMPUTED_VALUES = {"bollinger_touch"}

NINJA_USING = "using NinjaTrader.NinjaScript.Indicators;"
DESC_SUFFIX = ("Backtest research strategy generated from {qi} and backtest/rules.yaml. Not financial advice. "
               "Places no orders in real time unless Backtest Only is turned off.")

T = "\t"


class GenError(Exception):
    pass


# ----------------------------------------------------------------------------------------------
#  rules.yaml conditions: "x < a", "x <= a", "x > a", "x >= a", "x == a", "a < x < b", "never"
# ----------------------------------------------------------------------------------------------
_NUM = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_OP = r"<=|>=|==|<|>"
_RE_CMP = re.compile(r"^x\s*(%s)\s*(%s)$" % (_OP, _NUM))
_RE_RANGE = re.compile(r"^(%s)\s*(<=|<)\s*x\s*(<=|<)\s*(%s)$" % (_NUM, _NUM))
_FLIP = {"<": ">", "<=": ">="}


def cs_num(text: str) -> str:
    """C# double literal for a rules.yaml number, keeping the digits the author wrote."""
    t = text.strip()
    if t.startswith("+"):
        t = t[1:]
    if not re.search(r"[.eE]", t):
        t += ".0"
    elif t.endswith("."):
        t += "0"
    return t


def parse_condition(cond: str) -> str:
    """Return the C# boolean expression (over the double `x`) for one rules.yaml condition."""
    c = str(cond).strip()
    if c == "never":
        return "false"
    m = _RE_CMP.match(c)
    if m:
        return "x %s %s" % (m.group(1), cs_num(m.group(2)))
    m = _RE_RANGE.match(c)
    if m:
        lo, op1, op2, hi = m.group(1), m.group(2), m.group(3), m.group(4)
        return "x %s %s && x %s %s" % (_FLIP[op1], cs_num(lo), op2, cs_num(hi))
    raise GenError("unsupported condition %r (allowed: x OP a, a < x < b, never)" % (cond,))


# ----------------------------------------------------------------------------------------------
#  names mapping
# ----------------------------------------------------------------------------------------------
def load_names(path):
    if path is None:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise GenError("--names file must be a JSON object module -> class name")
    return data


def class_names(module: str, names: dict):
    """(qi_class, qs_class) for a module under an optional mapping."""
    v = names.get(module)
    if v is None:
        return "QI_" + module, "QS_" + module
    if isinstance(v, dict):
        qi, qs = v.get("qi"), v.get("qs")
        if not qi or not qs:
            raise GenError("names[%s] object needs both 'qi' and 'qs'" % module)
        return qi, qs
    if not isinstance(v, str) or not v:
        raise GenError("names[%s] must be a string or {qi, qs}" % module)
    if v.startswith("QI_"):
        return v, "QS_" + v[3:]
    if v.startswith("QS_"):
        return "QI_" + v[3:], v
    return "QI_" + v, "QS_" + v


# ----------------------------------------------------------------------------------------------
#  text helpers
# ----------------------------------------------------------------------------------------------
def _one_line(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def _sub1(pattern, repl, text, what, flags=re.M):
    new, n = re.subn(pattern, repl, text, count=0, flags=flags)
    if n != 1:
        raise GenError("expected exactly one %s, found %d" % (what, n))
    return new


def _method_end(lines, start):
    """Index of the line closing the 2-tab method that starts at lines[start] (`\\t\\t}`)."""
    for i in range(start + 1, len(lines)):
        if lines[i] == T * 2 + "}":
            return i
    raise GenError("method starting at line %d has no closing brace at 2-tab indent" % (start + 1))


def build_header(qs, qi, frame_text, frozen, qi_header):
    """New banner + the QI DISCLAIMER block verbatim + the rest of the QI header."""
    h = qi_header
    if not (h and h[0].startswith("// ====") and h[-1].startswith("// ====")):
        raise GenError("%s: header comment block not in the expected '// ====' frame" % qi)
    try:
        s = next(i for i, ln in enumerate(h) if ln.strip() == "//  DISCLAIMER")
        e = next(i for i in range(s, len(h)) if "DISCLAIMER.md in the repository root." in h[i])
    except StopIteration:
        raise GenError("%s: DISCLAIMER block not found in header" % qi)
    disclaimer = h[s:e + 1]
    rest = [ln for i, ln in enumerate(h[1:-1], start=1)
            if not (s <= i <= e) and ln.strip() != "//  Part of ninjatrader_quant_indicators"]
    # drop blank '//' lines left adjacent to the removed disclaimer so no double blank remains
    cleaned = []
    for ln in rest:
        if ln.strip() == "//" and (not cleaned or cleaned[-1].strip() == "//"):
            continue
        cleaned.append(ln)
    while cleaned and cleaned[-1].strip() == "//":
        cleaned.pop()

    banner = ("%s - BACKTEST RESEARCH STRATEGY. Rules: backtest/rules.yaml (frozen %s), the original "
              "IBSFade indicator's own classification. Home frame: %s. Generated by "
              "backtest/gen_strategies.py - do not edit by hand." % (qs, frozen, frame_text))
    wrapped = textwrap.wrap(banner, width=96, break_long_words=False, break_on_hyphens=False)
    out = [h[0]]
    out += ["//  " + w for w in wrapped]
    out += ["//  Part of ninjatrader_quant_indicators", "//"]
    out += disclaimer
    out += ["//",
            "//  The indicator logic below is transplanted unchanged from %s (indicators/%s.cs);" % (qi, qi),
            "//  its own documentation follows.",
            "//"]
    out += cleaned
    out += [h[-1]]
    return out


def append_description(sd, suffix):
    """Append ` + " <suffix>"` as a new continuation line to the SetDefaults Description statement."""
    lines = sd.split("\n")
    start = next((i for i, ln in enumerate(lines) if re.match(r"^\t+Description\t+= ", ln)), None)
    if start is None:
        raise GenError("SetDefaults has no Description assignment")
    end = start
    while not lines[end].rstrip().endswith(";"):
        end += 1
        if end >= len(lines):
            raise GenError("Description statement is not terminated")
    last = lines[end].rstrip()
    lines[end] = last[:-1]  # drop the terminating ';'
    cont = re.match(r"^(\t+)\+ ", lines[end])
    indent = cont.group(1) if cont else T * 11
    lines.insert(end + 1, '%s+ " %s";' % (indent, suffix.replace("\\", "\\\\").replace('"', '\\"')))
    return "\n".join(lines)


def strategy_defaults_block():
    return "\n".join([
        T * 4 + "// Strategy defaults (backtest research; generated)",
        T * 4 + "EntriesPerDirection\t\t\t= 1;",
        T * 4 + "EntryHandling\t\t\t\t= EntryHandling.AllEntries;",
        T * 4 + "IsExitOnSessionCloseStrategy = false;",
        T * 4 + "StartBehavior\t\t\t\t= StartBehavior.WaitUntilFlat;",
        T * 4 + "BarsRequiredToTrade\t\t\t= 0;",
        T * 4 + "Slippage\t\t\t\t\t= 1;",
        T * 4 + "DefaultQuantity\t\t\t\t= 1;",
        T * 4 + "BacktestOnly\t\t\t\t= true;",
        T * 4 + "TraceOrders\t\t\t\t\t= false;",
    ])


def edit_set_defaults(body, qi, qs):
    m1 = re.search(r"^\t\t\tif \(State == State\.SetDefaults\)\n\t\t\t\{\n", body, re.M)
    m2 = re.search(r"^\t\t\t\}\n\t\t\telse if \(State == State\.Configure\)", body, re.M)
    if not m1 or not m2 or m2.start() < m1.end():
        raise GenError("SetDefaults block not found in the expected layout")
    sd = body[m1.end():m2.start()]

    # Name
    sd = _sub1(r'^(\t+Name\t+= )"%s";' % re.escape(qi), r'\1"%s";' % qs, sd, 'Name = "%s"' % qi)
    # Description
    sd = append_description(sd, DESC_SUFFIX.format(qi=qi))
    # indicator-only assignments rejected by the compile probe
    for prop in INDICATOR_ONLY_REMOVED:
        sd = re.sub(r"^\t+%s\t*= [^\n]*;\n" % re.escape(prop), "", sd, flags=re.M)
    # Calculate must already be OnBarClose; strategy defaults go right after it
    sd = _sub1(r"^(\t+Calculate\t+= Calculate\.OnBarClose;\n)", lambda m: m.group(1) + strategy_defaults_block() + "\n",
               sd, "Calculate = Calculate.OnBarClose line")
    return body[:m1.end()] + sd + body[m2.start():]


def render_apply_rule(rule, qi_text):
    """ApplyRule()/OnBarUpdate() text (2-tab indented) plus the extra fields/DataLoaded lines."""
    module, value = rule["module"], rule["value"]
    long_cs = parse_condition(rule["long"])
    short_cs = parse_condition(rule["short"])
    note = ("; note: " + _one_line(rule["note"])) if rule.get("note") else ""
    orig = rule.get("orig", "?")

    fields, dataloaded = [], []
    if value in COMPUTED_VALUES:
        if value != "bollinger_touch":
            raise GenError("no computed-value template for %r" % value)
        for acc in ("Upper", "Lower"):
            if not re.search(r"public Series<double> %s\b" % acc, qi_text):
                raise GenError("%s: QI source has no public Series<double> %s" % (module, acc))
        fields = ["private ATR\t\tatr14;"]
        dataloaded = ["atr14\t\t\t= ATR(14);"]
        read = [
            "// bollinger_touch: -1 if Close <= Lower + 0.001*ATR(14), +1 if Close >= Upper - 0.001*ATR(14), else 0",
            "double x = double.NaN;",
            "if (Upper.IsValidDataPoint(0) && Lower.IsValidDataPoint(0) && atr14 != null)",
            "{",
            T + "double atr = atr14[0];",
            T + "if (!double.IsNaN(atr))",
            T + "{",
            T * 2 + "if (Close[0] <= Lower[0] + 0.001 * atr)",
            T * 3 + "x = -1.0;",
            T * 2 + "else if (Close[0] >= Upper[0] - 0.001 * atr)",
            T * 3 + "x = 1.0;",
            T * 2 + "else",
            T * 3 + "x = 0.0;",
            T + "}",
            "}",
        ]
        src = "computed from Lower/Upper and ATR(14)"
    else:
        acc = VALUE_SERIES.get(value)
        if acc is None:
            raise GenError("%s: rules.yaml value %r has no series mapping in VALUE_SERIES" % (module, value))
        if not re.search(r"public Series<double> %s\b" % re.escape(acc), qi_text):
            raise GenError("%s: QI source has no public Series<double> %s (value %s)" % (module, acc, value))
        read = [
            "double x = double.NaN;",
            "if (%s.IsValidDataPoint(0))" % acc,
            T + "x = %s[0];" % acc,
        ]
        src = "%s[0]" % acc

    L = []
    a = L.append
    a(T * 2 + "// ------------------------------------------------------------------------------")
    a(T * 2 + "//  Backtest rule (generated from backtest/rules.yaml - do not edit by hand)")
    a(T * 2 + "//  module %s | frame %s | value %s = %s | ORIG lines %s%s" % (
        module, rule["frame"], value, src, orig, note))
    a(T * 2 + "//  long : %s" % _one_line(rule["long"]))
    a(T * 2 + "//  short: %s" % _one_line(rule["short"]))
    a(T * 2 + "// ------------------------------------------------------------------------------")
    a(T * 2 + "protected override void OnBarUpdate()")
    a(T * 2 + "{")
    a(T * 3 + "QiUpdate();")
    a(T * 3 + "ApplyRule();")
    a(T * 2 + "}")
    a("")
    a(T * 2 + "private void ApplyRule()")
    a(T * 2 + "{")
    a(T * 3 + "if (BacktestOnly && State == State.Realtime) return;")
    a(T * 3 + "if (BarsInProgress != 0) return;")
    a("")
    L.extend(T * 3 + ln if ln else "" for ln in read)
    a("")
    a(T * 3 + "// A NaN / unset value maps to a flat target.")
    a(T * 3 + "int target = 0;")
    a(T * 3 + "if (!double.IsNaN(x))")
    a(T * 3 + "{")
    a(T * 4 + "bool goLong  = %s;" % long_cs)
    a(T * 4 + "bool goShort = %s;" % short_cs)
    a(T * 4 + "if (goLong)")
    a(T * 5 + "target = 1;")
    a(T * 4 + "else if (goShort)")
    a(T * 5 + "target = -1;")
    a(T * 3 + "}")
    a("")
    a(T * 3 + "if (target == 1 && Position.MarketPosition != MarketPosition.Long)")
    a(T * 4 + 'EnterLong(DefaultQuantity, "QS_L");')
    a(T * 3 + "else if (target == -1 && Position.MarketPosition != MarketPosition.Short)")
    a(T * 4 + 'EnterShort(DefaultQuantity, "QS_S");')
    a(T * 3 + "else if (target == 0)")
    a(T * 3 + "{")
    a(T * 4 + "if (Position.MarketPosition == MarketPosition.Long)")
    a(T * 5 + 'ExitLong("QS_XL", "QS_L");')
    a(T * 4 + "else if (Position.MarketPosition == MarketPosition.Short)")
    a(T * 5 + 'ExitShort("QS_XS", "QS_S");')
    a(T * 3 + "}")
    a(T * 2 + "}")
    return "\n".join(L), fields, dataloaded


BACKTEST_ONLY_PROP = "\n".join([
    T * 2 + "[NinjaScriptProperty]",
    T * 2 + '[Display(Name = "Backtest Only", Order = 0, GroupName = "Safety")]',
    T * 2 + "public bool BacktestOnly { get; set; }",
])


def transplant(rule, qi_raw, qi, qs, frozen):
    """Return the text of QS_<Module>.cs (LF line endings, no BOM) built from the QI source."""
    text = qi_raw.replace("\r\n", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]

    marker = "#region Using declarations\n"
    k = text.find(marker)
    if k < 0:
        raise GenError("%s: '#region Using declarations' not found" % qi)
    qi_header = text[:k].rstrip("\n").split("\n")
    body = text[k:]

    # 1. class / namespace / using
    body = _sub1(r"^\tpublic class %s : Indicator$" % re.escape(qi), "\tpublic class %s : Strategy" % qs,
                 body, "class %s : Indicator" % qi)
    body = _sub1(r"^namespace NinjaTrader\.NinjaScript\.Indicators$", "namespace NinjaTrader.NinjaScript.Strategies",
                 body, "Indicators namespace line")
    body = body.replace("// This namespace holds Indicators in this folder and is required. Do not change it.",
                        "// This namespace holds Strategies in this folder and is required. Do not change it.")
    if NINJA_USING not in body:
        body = _sub1(r"^using NinjaTrader\.NinjaScript\.DrawingTools;$",
                     NINJA_USING + "\nusing NinjaTrader.NinjaScript.DrawingTools;", body,
                     "DrawingTools using line")

    # 2. SetDefaults edits (Name, Description, strategy defaults)
    body = edit_set_defaults(body, qi, qs)

    # 3. DisplayName QI -> QS
    body = _sub1(r'^(\t\t\tget \{ return )"QI( [^"]*)"; \}$', r'\1"QS\2"; }', body, "DisplayName getter")

    # 4. OnBarUpdate -> QiUpdate, then insert the rule block after it
    lines = body.split("\n")
    idxs = [i for i, ln in enumerate(lines) if ln == T * 2 + "protected override void OnBarUpdate()"]
    if len(idxs) != 1:
        raise GenError("%s: expected exactly one OnBarUpdate, found %d" % (qi, len(idxs)))
    s = idxs[0]
    e = _method_end(lines, s)
    lines[s] = T * 2 + "private void QiUpdate()"
    rule_text, fields, dataloaded = render_apply_rule(rule, text)
    lines[e + 1:e + 1] = [""] + rule_text.split("\n")
    body = "\n".join(lines)

    # 5. BacktestOnly property
    body = _sub1(r"^(\t\t#region Properties\n\n)", lambda m: m.group(1) + BACKTEST_ONLY_PROP + "\n\n", body,
                 "#region Properties")

    # 6. extra field / DataLoaded lines (bollinger_touch needs ATR(14))
    if fields:
        body = _sub1(r"^(\tpublic class %s : Strategy\n\t\{\n)" % re.escape(qs),
                     lambda m: m.group(1) + "".join(T * 2 + f + "\n" for f in fields), body, "class opening brace")
    if dataloaded:
        body = _sub1(r"^(\t\t\telse if \(State == State\.DataLoaded\)\n\t\t\t\{\n)",
                     lambda m: m.group(1) + "".join(T * 4 + d + "\n" for d in dataloaded), body,
                     "State.DataLoaded block")

    header = build_header(qs, qi, FRAME_TEXT[rule["frame"]], frozen, qi_header)
    return "\n".join(header) + "\n" + body


# ----------------------------------------------------------------------------------------------
#  driver
# ----------------------------------------------------------------------------------------------
def load_rules(path):
    import yaml  # PyYAML
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    rules = data["rules"]
    mods = [r["module"] for r in rules]
    if len(set(mods)) != len(mods):
        raise GenError("duplicate module in rules.yaml")
    for r in rules:
        if r["frame"] not in FRAME_TEXT:
            raise GenError("%s: unknown frame %r" % (r["module"], r["frame"]))
    return str(data.get("frozen", "")), rules


def generate(rules_path, ind_dir, names, only=None):
    frozen, rules = load_rules(rules_path)
    out = {}
    for rule in rules:
        mod = rule["module"]
        if only and mod not in only:
            continue
        qi, qs = class_names(mod, names)
        src = Path(ind_dir) / (qi + ".cs")
        if not src.is_file():
            raise GenError("%s: indicator source %s not found" % (mod, src))
        try:
            out[qs] = transplant(rule, src.read_bytes().decode("utf-8"), qi, qs, frozen)
        except GenError as exc:
            raise GenError("%s (%s): %s" % (mod, src.name, exc))
    if only:
        missing = set(only) - {r["module"] for r in rules}
        if missing:
            raise GenError("--only names not in rules.yaml: %s" % ", ".join(sorted(missing)))
    return out


def write_all(out_dir, files, prune):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    changed, removed = [], []
    for qs, text in sorted(files.items()):
        p = out_dir / (qs + ".cs")
        data = text.encode("utf-8")
        if p.is_file() and p.read_bytes() == data:
            continue
        p.write_bytes(data)  # bytes: keep LF on Windows
        changed.append(p.name)
    if prune:
        keep = {q + ".cs" for q in files}
        for p in sorted(out_dir.glob("QS_*.cs")):
            if p.name not in keep:
                p.unlink()
                removed.append(p.name)
    return changed, removed


def check(out_dir, files):
    out_dir = Path(out_dir)
    bad = []
    for qs, text in sorted(files.items()):
        p = out_dir / (qs + ".cs")
        if not p.is_file() or p.read_bytes() != text.encode("utf-8"):
            bad.append(p.name)
    keep = {q + ".cs" for q in files}
    bad += ["stale:" + p.name for p in sorted(out_dir.glob("QS_*.cs")) if p.name not in keep]
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rules", default=str(RULES_PATH))
    ap.add_argument("--indicators", default=str(INDICATORS_DIR))
    ap.add_argument("--out", default=str(STRATEGIES_DIR))
    ap.add_argument("--names", default=None, help="JSON module -> class name map (optional, default identity)")
    ap.add_argument("--only", default=None, help="comma-separated module names (no stale deletion)")
    ap.add_argument("--check", action="store_true", help="do not write; exit 1 if --out is out of date")
    args = ap.parse_args(argv)

    only = {s.strip() for s in args.only.split(",") if s.strip()} if args.only else None
    try:
        files = generate(args.rules, args.indicators, load_names(args.names), only)
        if args.check:
            bad = check(args.out, files) if not only else [
                n for n in check(args.out, files) if not n.startswith("stale:")]
            if bad:
                print("out of date: " + ", ".join(bad), file=sys.stderr)
                return 1
            print("up to date: %d strategies" % len(files))
            return 0
        changed, removed = write_all(args.out, files, prune=not only)
    except GenError as exc:
        print("gen_strategies: error: %s" % exc, file=sys.stderr)
        return 2
    print("generated %d strategies in %s (%d written, %d unchanged, %d stale removed)" % (
        len(files), args.out, len(changed), len(files) - len(changed), len(removed)))
    for n in removed:
        print("  removed stale " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
