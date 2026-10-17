"""BT13 (Channel B part = generated parity): every rules.yaml condition equals the condition literal
compiled into strategies/QS_<module>.cs, parsed by Channel B's own parsers (no qibt import).

rules.yaml grammar handled: "x OP a", "a < x < b", "never".   C# handled: `bool goLong  = <expr>;`
`bool goShort = <expr>;` with <expr> = false | x OP a | x OP a && x OP b. Both are canonicalised to
a sorted tuple of (op, value) atoms (a < x  ->  x > a). Also checked: the module set matches 1:1,
the frame named in the strategy header matches rules.yaml, long -> +1 / short -> -1 / NaN -> 0
wiring, and long/short are mutually exclusive on a dense grid.
NOTE: whether the thresholds equal ORIG IBSFade.cs (the claim's other half) is Channel A's static read.
Usage: python -I -B bt13_rule_parity.py [--strategies DIR] [--rules PATH]
"""
from __future__ import annotations

import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cb  # noqa: E402
import yaml  # noqa: E402

argv = sys.argv
sdir = os.path.join(_cb.REPO, "strategies")
rpath = os.path.join(_cb.REPO, "backtest", "rules.yaml")
if "--strategies" in argv:
    i = argv.index("--strategies"); sdir = argv[i + 1]; del argv[i:i + 2]
if "--rules" in argv:
    i = argv.index("--rules"); rpath = argv[i + 1]; del argv[i:i + 2]
print("strategies: %s\nrules: %s" % (sdir, rpath))

NUM = r"[-+]?\d+(?:\.\d+)?"
FLIP = {"<": ">", ">": "<", "<=": ">=", ">=": "<=", "==": "=="}


def canon_yaml(s):
    s = s.strip()
    if s == "never":
        return ()
    m = re.fullmatch(r"x\s*(<=|>=|==|<|>)\s*(%s)" % NUM, s)
    if m:
        return ((m.group(1), float(m.group(2))),)
    m = re.fullmatch(r"(%s)\s*<\s*x\s*<\s*(%s)" % (NUM, NUM), s)
    if m:
        return tuple(sorted([(">", float(m.group(1))), ("<", float(m.group(2)))]))
    raise ValueError("rules.yaml condition outside grammar: %r" % s)


def canon_cs(expr):
    expr = expr.strip()
    if expr == "false":
        return ()
    atoms = []
    for part in expr.split("&&"):
        part = part.strip()
        m = re.fullmatch(r"x\s*(<=|>=|==|<|>)\s*(%s)" % NUM, part)
        if m:
            atoms.append((m.group(1), float(m.group(2))))
            continue
        m = re.fullmatch(r"(%s)\s*(<=|>=|==|<|>)\s*x" % NUM, part)
        if m:
            atoms.append((FLIP[m.group(2)], float(m.group(1))))
            continue
        raise ValueError("C# condition outside grammar: %r" % expr)
    return tuple(sorted(atoms))


def holds(atoms, x):
    if not atoms:
        return False
    ops = {"<": x.__lt__, ">": x.__gt__, "<=": x.__le__, ">=": x.__ge__, "==": x.__eq__}
    return all(ops[o](v) for o, v in atoms)


doc = yaml.safe_load(open(rpath, encoding="utf-8"))
rules = {str(r["module"]): r for r in doc["rules"]}
files = {os.path.basename(p)[3:-3]: p for p in glob.glob(os.path.join(sdir, "QS_*.cs"))}
c = _cb.Checker("BT13 rules.yaml <-> QS_*.cs parity")
c.check("module sets equal (rules.yaml %d, QS files %d)" % (len(rules), len(files)), set(rules) == set(files),
        "only yaml: %s; only cs: %s" % (sorted(set(rules) - set(files)), sorted(set(files) - set(rules))))
frame_word = {"D": "Day", "15m": "15 Minute"}
for mod in sorted(set(rules) & set(files)):
    r = rules[mod]
    src = open(files[mod], encoding="utf-8").read()
    gl = re.findall(r"bool\s+goLong\s*=\s*([^;]+);", src)
    gs = re.findall(r"bool\s+goShort\s*=\s*([^;]+);", src)
    if len(gl) != 1 or len(gs) != 1:
        c.check("%s: exactly one goLong/goShort" % mod, False, "found %d/%d" % (len(gl), len(gs)))
        continue
    yl, ys = canon_yaml(str(r["long"])), canon_yaml(str(r["short"]))
    cl, cs = canon_cs(gl[0]), canon_cs(gs[0])
    hdr = re.search(r"Home frame:\s*([A-Za-z0-9 ]+?) bars", src)
    fr_ok = bool(hdr) and hdr.group(1).strip() == frame_word[str(r["frame"])]
    wired = (re.search(r"if\s*\(goLong\)\s*target\s*=\s*1\s*;", src) is not None
             and re.search(r"else\s+if\s*\(goShort\)\s*target\s*=\s*-1\s*;", src) is not None
             and re.search(r"int\s+target\s*=\s*0\s*;", src) is not None
             and re.search(r"if\s*\(!double\.IsNaN\(x\)\)", src) is not None)
    grid = [k / 100.0 for k in range(-20000, 20001)] + [-35.0, 35.0, 0.0, 1.0, -1.0]
    excl = not any(holds(yl, x) and holds(ys, x) for x in grid)
    ok = yl == cl and ys == cs and fr_ok and wired and excl
    c.check("%s: long %s | short %s | frame %s" % (mod, r["long"], r["short"], r["frame"]), ok,
            "cs long=%r short=%r header-frame=%r wiring=%s exclusive=%s"
            % (gl[0].strip(), gs[0].strip(), hdr.group(1) if hdr else None, wired, excl))
sys.exit(c.close())
