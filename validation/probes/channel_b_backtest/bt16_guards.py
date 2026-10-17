"""BT16 static part: in every strategies/QS_*.cs, every order-submitting call is inside a method
whose FIRST statement is the realtime guard `if (BacktestOnly && State == State.Realtime) return;`,
BacktestOnly defaults to true in State.SetDefaults, and BacktestOnly is assigned nowhere else.

Own C# scanner: comments and string/char literals are blanked first; methods are found by brace
matching. Order calls searched: Enter*/Exit* managed calls, SubmitOrder*, ChangeOrder, SetStopLoss,
SetProfitTarget, SetTrailStop, Account.* order APIs, Flatten.
Usage: python -I -B bt16_guards.py [--strategies DIR]
"""
from __future__ import annotations

import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402

argv = sys.argv
sdir = os.path.join(_cb.REPO, "strategies")
if "--strategies" in argv:
    i = argv.index("--strategies"); sdir = argv[i + 1]; del argv[i:i + 2]
print("strategies: %s" % sdir)

ORDER_RE = re.compile(r"\b(Enter(?:Long|Short)\w*|Exit(?:Long|Short)\w*|SubmitOrder\w*|ChangeOrder|SetStopLoss|"
                      r"SetProfitTarget|SetTrailStop|Flatten|CreateOrder|Account\s*\.\s*Submit\w*)\s*\(")
GUARD_RE = re.compile(r"^\s*if\s*\(\s*(?:BacktestOnly\s*&&\s*State\s*==\s*State\.Realtime|"
                      r"State\s*==\s*State\.Realtime\s*&&\s*BacktestOnly)\s*\)\s*return\s*;")


def blank(src):
    """Replace comments and string/char literal contents with spaces (keeps offsets)."""
    out = list(src)
    i, n = 0, len(src)
    while i < n:
        if src.startswith("//", i):
            j = src.find("\n", i); j = n if j < 0 else j
            for k in range(i, j): out[k] = " "
            i = j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2); j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n": out[k] = " "
            i = j
        elif src[i] == '"' or (src[i] == "@" and i + 1 < n and src[i + 1] == '"'):
            verbatim = src[i] == "@"
            j = i + (2 if verbatim else 1)
            while j < n:
                if not verbatim and src[j] == "\\":
                    j += 2; continue
                if src[j] == '"':
                    if verbatim and j + 1 < n and src[j + 1] == '"':
                        j += 2; continue
                    break
                j += 1
            for k in range(i + 1, min(j, n)): out[k] = " "
            i = j + 1
        elif src[i] == "'":
            j = src.find("'", i + 1 + (1 if src[i + 1] == "\\" else 0))
            for k in range(i + 1, j): out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


def methods(code):
    """[(name, body_start, body_end)] for method-like blocks `name(...) { ... }` (not if/for/while/...)."""
    res = []
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\([^;{}()]*(?:\([^()]*\)[^;{}()]*)*\)\s*\{", code):
        name = m.group(1)
        if name in ("if", "for", "foreach", "while", "switch", "catch", "using", "lock", "fixed", "else"):
            continue
        start = m.end()
        depth, j = 1, start
        while j < len(code) and depth:
            if code[j] == "{": depth += 1
            elif code[j] == "}": depth -= 1
            j += 1
        res.append((name, start, j - 1))
    return res


c = _cb.Checker("BT16 BacktestOnly guards")
files = sorted(glob.glob(os.path.join(sdir, "QS_*.cs")))
c.check("found QS_*.cs files", len(files) > 0, "%d files" % len(files))
total_calls = 0
for p in files:
    name = os.path.basename(p)
    code = blank(open(p, encoding="utf-8").read())
    meths = methods(code)
    calls = [m for m in ORDER_RE.finditer(code)]
    total_calls += len(calls)
    bad = []
    for m in calls:
        enclosing = [x for x in meths if x[1] <= m.start() < x[2]]
        if not enclosing:
            bad.append("%s outside any method" % m.group(1)); continue
        mname, s, e = min(enclosing, key=lambda x: x[2] - x[1])   # innermost method
        if mname in ("OnStateChange",):
            bad.append("%s in %s" % (m.group(1), mname)); continue
        body = code[s:e]
        first = body.lstrip()
        if not GUARD_RE.match(first):
            bad.append("%s in %s() whose first statement is not the guard" % (m.group(1), mname))
    # default + no other assignment
    sd = re.search(r"if\s*\(\s*State\s*==\s*State\.SetDefaults\s*\)\s*\{", code)
    sd_ok = False
    if sd:
        depth, j = 1, sd.end()
        while depth:
            if code[j] == "{": depth += 1
            elif code[j] == "}": depth -= 1
            j += 1
        sd_ok = re.search(r"\bBacktestOnly\s*=\s*true\s*;", code[sd.end():j]) is not None
    assigns = re.findall(r"\bBacktestOnly\s*=(?!=)\s*([^;]+);", code)
    prop = re.search(r"public\s+bool\s+BacktestOnly\s*\{\s*get\s*;\s*set\s*;\s*\}", code) is not None
    ok = not bad and len(calls) > 0 and sd_ok and assigns == ["true"] and prop
    c.check("%s: %d order call(s) guarded; default true; single assignment" % (name, len(calls)), ok,
            "problems=%s sd_default_true=%s assignments=%s property=%s" % (bad, sd_ok, assigns, prop))
print("order calls scanned: %d" % total_calls)
sys.exit(c.close())
