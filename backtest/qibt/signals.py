"""signals.py - rules.yaml -> per-rule value series -> target positions p_t in {+1, 0, -1}.

Value names map to the validated reference implementations in validation/pytests/qi_ref.py
(imported here, the ONE place that touches sys.path for it) or, for the four pattern modules, to
backtest/qibt/patterns.py (imported lazily; a missing or failing port marks the rule "pending").

Condition grammar (tiny parser, never eval): "x < a", "x <= a", "x > a", "x >= a", "x == a",
"a < x < b", "never". A NaN value satisfies no condition, so it maps to position 0.
"""
from __future__ import annotations

import importlib
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

BACKTEST_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKTEST_DIR.parent
RULES_PATH = BACKTEST_DIR / "rules.yaml"
QI_REF_DIR = REPO_DIR / "validation" / "pytests"

# --- the ONE place qi_ref is made importable (appended, so it never shadows anything) --------
if str(QI_REF_DIR) not in sys.path:
    sys.path.append(str(QI_REF_DIR))
import qi_ref  # noqa: E402

PATTERN_VALUES = ("hp_score", "sweep_structure", "ofp_structure", "smc_structure")
FRAMES = ("D", "15m")


# ============================================================================================
# condition parser
# ============================================================================================
_NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_ONE_SIDED = re.compile(r"^\s*x\s*(<=|>=|==|<|>)\s*(%s)\s*$" % _NUM)
_RANGE = re.compile(r"^\s*(%s)\s*<\s*x\s*<\s*(%s)\s*$" % (_NUM, _NUM))
_NEVER = re.compile(r"^\s*never\s*$")

_OPS = {
    "<": np.less, "<=": np.less_equal, ">": np.greater, ">=": np.greater_equal, "==": np.equal,
}


@dataclass(frozen=True)
class Condition:
    text: str
    kind: str                 # "never" | "cmp" | "range"
    op: str = ""
    a: float = math.nan
    b: float = math.nan

    def mask(self, values):
        """Boolean array: True where the condition holds. NaN never holds."""
        v = np.asarray(values, dtype=float)
        if self.kind == "never":
            return np.zeros(v.shape, dtype=bool)
        with np.errstate(invalid="ignore"):
            if self.kind == "cmp":
                m = _OPS[self.op](v, self.a)
            else:
                m = (v > self.a) & (v < self.b)
        return np.asarray(m, dtype=bool) & ~np.isnan(v)

    __call__ = mask


def parse_condition(text):
    """Parse one rules.yaml condition string. Raises ValueError for anything outside the grammar."""
    if not isinstance(text, str):
        raise ValueError("condition must be a string, got %r" % (text,))
    if _NEVER.match(text):
        return Condition(text, "never")
    m = _ONE_SIDED.match(text)
    if m:
        a = float(m.group(2))
        if not math.isfinite(a):
            raise ValueError("non-finite threshold in %r" % text)
        return Condition(text, "cmp", op=m.group(1), a=a)
    m = _RANGE.match(text)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if not (math.isfinite(a) and math.isfinite(b)) or not a < b:
            raise ValueError("range condition needs finite a < b: %r" % text)
        return Condition(text, "range", a=a, b=b)
    raise ValueError("condition outside the grammar: %r" % text)


def to_positions(values, long_cond, short_cond):
    """p_t = +1 where long holds, -1 where short holds, else 0 (NaN -> 0)."""
    lo = long_cond.mask(values)
    sh = short_cond.mask(values)
    if np.any(lo & sh):
        raise ValueError("long %r and short %r both hold at %d bar(s)"
                         % (long_cond.text, short_cond.text, int(np.sum(lo & sh))))
    p = np.zeros(len(lo), dtype=np.int8)
    p[lo] = 1
    p[sh] = -1
    return p


# ============================================================================================
# rules.yaml
# ============================================================================================
@dataclass(frozen=True)
class Rule:
    module: str
    frame: str
    value: str
    long: Condition
    short: Condition
    orig: str = ""
    note: str = ""


@dataclass
class RuleSet:
    rules: list
    not_backtestable: list = field(default_factory=list)
    version: int = 1
    frozen: str = ""


def load_rules(path=RULES_PATH):
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    rules = []
    seen = set()
    for r in doc.get("rules", []):
        mod = str(r["module"])
        if mod in seen:
            raise ValueError("duplicate module %r" % mod)
        seen.add(mod)
        frame = str(r["frame"])
        if frame not in FRAMES:
            raise ValueError("%s: frame %r not in %s" % (mod, frame, FRAMES))
        value = str(r["value"])
        if value not in VALUE_FUNCTIONS and value not in PATTERN_VALUES:
            raise ValueError("%s: unknown value %r" % (mod, value))
        rules.append(Rule(mod, frame, value, parse_condition(r["long"]), parse_condition(r["short"]),
                          str(r.get("orig", "")), str(r.get("note", ""))))
    nb = [dict(module=str(x["module"]), reason=str(x.get("reason", "")))
          for x in doc.get("not_backtestable", []) or []]
    return RuleSet(rules, nb, int(doc.get("version", 1)), str(doc.get("frozen", "")))


# ============================================================================================
# value functions: frame DataFrame (TradingDate, BarTime, Open..Volume) -> array aligned to it
# ============================================================================================
def _close(f):
    return f["Close"].reset_index(drop=True)


def _ohlcv(f):
    return f[["BarTime", "Open", "High", "Low", "Close", "Volume"]].reset_index(drop=True)


def v_ibs_daily(f):
    """(C - L)/(H - L) of the (daily) bar, 0.5 if H == L (qi_ref.ibs_bar on the D frame)."""
    return qi_ref.ibs_bar(_ohlcv(f))


def bollinger_touch_from(close, upper, middle, lower, atr14):
    """-1 if Close <= Lower + 0.001*ATR14, else +1 if Close >= Upper - 0.001*ATR14, else 0
    (ORIG tests the Buy branch first); NaN where the middle band is undefined."""
    c, up, mid, lo, a = (np.asarray(x, dtype=float) for x in (close, upper, middle, lower, atr14))
    tol = 0.001 * a
    with np.errstate(invalid="ignore"):
        v = np.where(c <= lo + tol, -1.0, np.where(c >= up - tol, 1.0, 0.0))
    v[np.isnan(mid)] = np.nan
    return v


def v_bollinger_touch(f):
    """Band touch of Bollinger(Close, 2, 20) with the ORIG 0.001*ATR14 tolerance."""
    df = _ohlcv(f)
    upper, mid, lower = qi_ref.bollinger(df["Close"], 20, 2.0)
    return bollinger_touch_from(df["Close"], upper, mid, lower, qi_ref.atr(df, 14))


def session_start_flags(trading_dates):
    """1.0 on the first bar of each trading date, else 0.0."""
    td = pd.Series(pd.to_datetime(trading_dates)).reset_index(drop=True)
    return (td != td.shift(1)).astype(float).to_numpy()


def v_vwap_distance(f):
    """qi_ref.vwap_distance with the session-start flag set on the first bar of each trading date."""
    df = _ohlcv(f)
    df[qi_ref.SESSION_FLAG_COL] = session_start_flags(f["TradingDate"])
    return qi_ref.vwap_distance(df)


def v_day_of_week(f):
    """Trading-date weekday, Sunday = 0 .. Saturday = 6 (qi_ref default = .NET DayOfWeek, as ORIG),
    so Monday = 1 as the rule expects."""
    return qi_ref.day_of_week(pd.Series(pd.to_datetime(f["TradingDate"])).reset_index(drop=True),
                              sunday_zero=True)


def v_turn_of_month(f):
    return qi_ref.turn_of_month(pd.Series(pd.to_datetime(f["TradingDate"])).reset_index(drop=True))


VALUE_FUNCTIONS = {
    "ibs_daily": v_ibs_daily,
    "rsi2": lambda f: qi_ref.rsi(_close(f), 2),
    "connors_rsi": lambda f: qi_ref.connors_rsi(_close(f)),
    "stoch_k": lambda f: qi_ref.stoch_fast(_ohlcv(f), 3, 14)[0],
    "rv_zscore": lambda f: qi_ref.rv_zscore(_ohlcv(f)),
    "composite_vol": lambda f: qi_ref.composite_vol(_ohlcv(f))["composite"],
    "turn_of_month": v_turn_of_month,
    "consec_streak": lambda f: qi_ref.consec_days(_close(f)),
    "overnight_gap_pct": lambda f: qi_ref.gap_pct(_ohlcv(f)),
    "bollinger_touch": v_bollinger_touch,
    "day_of_week": v_day_of_week,
    "rsi14": lambda f: qi_ref.rsi(_close(f), 14),
    "vrp_proxy": lambda f: qi_ref.vrp_proxy(_ohlcv(f)),
    "wide_range": lambda f: qi_ref.wide_range(_ohlcv(f)),
    "vwap_distance": v_vwap_distance,
    "macd_hist": lambda f: qi_ref.macd_hist(_close(f)),
    "ema_spread": lambda f: qi_ref.ema_cross(_close(f))[2],
    "sma200_distance": lambda f: qi_ref.sma200_trend(_close(f))[1],
    "atr_regime": lambda f: qi_ref.atr_regime(_ohlcv(f)),
    "volume_spike": lambda f: qi_ref.volume_spike(_ohlcv(f)),
    "cum_delta20": lambda f: qi_ref.volume_delta(_ohlcv(f))[1],
}


# ============================================================================================
# pattern values (qibt.patterns, lazily)
# ============================================================================================
class PendingValue(Exception):
    """The value cannot be computed yet (pattern port missing or failing)."""


PATTERNS_MODULE = "qibt.patterns"


def _coerce(out, name, n):
    if isinstance(out, tuple):
        out = out[0]
    if isinstance(out, dict):
        for k in (name, "value", "structure", "score"):
            if k in out:
                out = out[k]
                break
        else:
            raise PendingValue("%s returned a dict without a %r key" % (name, name))
    if isinstance(out, pd.DataFrame):
        for k in (name, "value", "structure", "score"):
            if k in out.columns:
                out = out[k]
                break
        else:
            if out.shape[1] != 1:
                raise PendingValue("%s returned a DataFrame without a %r column" % (name, name))
            out = out.iloc[:, 0]
    arr = np.asarray(out, dtype=float).reshape(-1)
    if len(arr) != n:
        raise PendingValue("%s returned %d values for %d bars" % (name, len(arr), n))
    return arr


def pattern_value(name, f):
    try:
        mod = importlib.import_module(PATTERNS_MODULE)
    except Exception as e:  # missing file, syntax error, import-time failure
        raise PendingValue("%s not importable (%s: %s)" % (PATTERNS_MODULE, type(e).__name__, e))
    fn = getattr(mod, name, None)
    if not callable(fn):
        raise PendingValue("%s has no function %s" % (PATTERNS_MODULE, name))
    try:
        out = fn(_ohlcv(f))
    except Exception as e:
        raise PendingValue("%s.%s raised %s: %s" % (PATTERNS_MODULE, name, type(e).__name__, e))
    return _coerce(out, name, len(f))


def compute_value(name, f):
    """Value series of `name` on frame f as a float array aligned to f's rows."""
    if name in PATTERN_VALUES:
        return pattern_value(name, f)
    out = VALUE_FUNCTIONS[name](f)
    arr = np.asarray(out, dtype=float).reshape(-1)
    if len(arr) != len(f):
        raise RuntimeError("%s returned %d values for %d bars" % (name, len(arr), len(f)))
    return arr


def rule_positions(rule, frames):
    """(values, positions) of a rule on its home frame. Raises PendingValue for pending ports."""
    f = frames[rule.frame]
    values = compute_value(rule.value, f)
    return values, to_positions(values, rule.long, rule.short)
