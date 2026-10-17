"""data.py - loaders and the bar/session builder of backtest/PROTOCOL.md sections 2-3.

P1 (primary dataset): the six NinjaTrader EveryBar exports MES_1min_*.csv. The header names 53
fields; BAR rows (SignalType empty) carry one surplus field, so every bar row is aligned by its own
    shift = len(row) - len(header)
and the column the header calls X is read at header.index(X) + shift, with the two per-row
alignment checks of validation/probes/diff_values.py (Price == shifted Close; the field just before
the shifted Open is empty). Signal rows are skipped. A row failing a check, or more than one shift
value in a file, aborts the load (LayoutError) - a different export layout is reported, never
silently misread.

Files are concatenated in file-name order (= chronological for these names), de-duplicated on
BarTime (first occurrence wins), sorted, and cached under backtest/data/ (git-ignored; raw vendor
data is never written anywhere else).

Sessions: trading date = calendar date of the bar close time, plus one day if the close time is
after 17:00 CT. D frame = one bar per trading date; 15m frame = right-labelled 15-minute bars
(a 1-minute bar closing at t belongs to the bar closing at ceil(t, 15 min)), never spanning a
trading date.
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

BACKTEST_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKTEST_DIR.parent
DATA_DIR = BACKTEST_DIR / "data"

P1_DIR = Path(r"C:\Users\rajib\OneDrive\Docs\futures_data\ninja_trader_signal_data\data")
P1_GLOB = "MES_1min_*.csv"
P1_CACHE_STEM = "P1_1min"
LOADER_VERSION = 2                  # v2 (A1): + databox_IBS of every bar row
IBS_ORIG_COL = "databox_IBS"        # ORIG's IBS of NinjaTrader's daily bar, logged on every 1-minute bar
P1_EXTRA_COLS = (IBS_ORIG_COL,)

OHLCV = ["Open", "High", "Low", "Close", "Volume"]
CENTRAL_TZ = "America/Chicago"
ROLL_HOUR = 17                      # Globex reopens 17:00 CT
HALT = ("16:00", "17:00")           # daily halt: no bar may close in (16:00, 17:00] CT
BAR_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# D-frame close (PROTOCOL A1)
CLOSE_MODES = ("settle", "last", "1500")
DEFAULT_CLOSE_MODE = "settle"
TICK = 0.25
IBS_ROUND = 0.00005                 # databox_IBS is exported to 4 decimals (half-unit error)
GRID_EPS = 1e-9                     # float slack on top of the rounding bound
# A1.1: an inferred close is on the 0.25 grid when its distance to the grid is within the error
# that 4-decimal IBS rounding can produce, i.e. <= IBS_ROUND * (H - L) + GRID_EPS (PROTOCOL §9).
SETTLE_BAR_TIME = "15:00"           # CME equity-index settlement window ends 15:00 CT


class LayoutError(RuntimeError):
    """The EveryBar export does not have the layout this loader understands."""


class SessionError(RuntimeError):
    """A bar violates the session definition (e.g. it closes inside the daily halt)."""


# ============================================================================================
# P1: NinjaTrader EveryBar export
# ============================================================================================
def read_everybar(path, extra_cols=()):
    """Bar rows of one EveryBar CSV as a DataFrame (BarTime, Open..Volume, *extra_cols).

    Returns (df, info). `extra_cols` are further header names (e.g. "databox_HPScore") read
    with the same per-row shift; empty cells become NaN."""
    path = Path(path)
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        hidx = {name: i for i, name in enumerate(header)}
        for req in ["BarTime", "SignalType", "Price"] + OHLCV + list(extra_cols):
            if req not in hidx:
                raise LayoutError("%s: header has no column %r" % (path.name, req))
        nh = len(header)
        i_sig, i_bt, i_price = hidx["SignalType"], hidx["BarTime"], hidx["Price"]
        i_o, i_h, i_l, i_c, i_v = (hidx[c] for c in OHLCV)
        i_x = [hidx[c] for c in extra_cols]
        bt, o, h, l, c, v = [], [], [], [], [], []
        xs = [[] for _ in i_x]
        shifts = Counter()
        bad = []
        nsig = 0
        for lineno, r in enumerate(rd, start=2):
            if len(r) <= i_sig:
                bad.append((lineno, "only %d fields" % len(r)))
                continue
            if r[i_sig] != "":
                nsig += 1
                continue
            s = len(r) - nh
            if s < 0:
                bad.append((lineno, "bar row shorter than header (%d < %d)" % (len(r), nh)))
                continue
            if r[i_price] != r[i_c + s]:
                bad.append((lineno, "shift=%d: Price %r != shifted Close %r" % (s, r[i_price], r[i_c + s])))
                continue
            if s > 0 and r[i_o + s - 1] != "":
                bad.append((lineno, "shift=%d: field before shifted Open is %r" % (s, r[i_o + s - 1])))
                continue
            shifts[s] += 1
            bt.append(r[i_bt])
            o.append(r[i_o + s]); h.append(r[i_h + s]); l.append(r[i_l + s])
            c.append(r[i_c + s]); v.append(r[i_v + s])
            for k, ix in enumerate(i_x):
                xs[k].append(r[ix + s])
    if bad:
        raise LayoutError("%s: %d bar row(s) failed the alignment checks, first: %s"
                          % (path.name, len(bad), bad[:5]))
    if len(shifts) > 1:
        raise LayoutError("%s: more than one field-count surplus %s" % (path.name, dict(shifts)))
    if not shifts:
        raise LayoutError("%s: no bar rows" % path.name)
    df = pd.DataFrame({
        "BarTime": pd.to_datetime(pd.Series(bt), format=BAR_TIME_FORMAT),
        "Open": np.asarray(o, dtype=float), "High": np.asarray(h, dtype=float),
        "Low": np.asarray(l, dtype=float), "Close": np.asarray(c, dtype=float),
        "Volume": np.asarray(v, dtype=float),
    })
    for name, vals in zip(extra_cols, xs):
        df[name] = pd.to_numeric(pd.Series(vals), errors="coerce").to_numpy()
    t = df["BarTime"].to_numpy()
    info = {
        "file": path.name, "header_fields": nh, "bar_rows": int(len(df)), "signal_rows": nsig,
        "shift": int(next(iter(shifts))),
        "backward_steps": int(np.count_nonzero(t[1:] < t[:-1])),
        "first": str(df["BarTime"].iloc[0]), "last": str(df["BarTime"].iloc[-1]),
    }
    return df, info


def p1_files(directory=P1_DIR):
    return sorted(Path(directory).glob(P1_GLOB))


def combine_bars(frames):
    """Concatenate in the given order, de-duplicate on BarTime (first wins), stable-sort."""
    df = pd.concat(frames, ignore_index=True)
    n0 = len(df)
    df = df.drop_duplicates("BarTime", keep="first")
    df = df.sort_values("BarTime", kind="mergesort").reset_index(drop=True)
    return df, n0 - len(df)


def _manifest_for(files):
    return {
        "loader_version": LOADER_VERSION,
        "pandas": pd.__version__,
        "sources": [{"name": f.name, "size": f.stat().st_size, "mtime_ns": f.stat().st_mtime_ns}
                    for f in files],
    }


def _cache_paths(stem):
    return DATA_DIR / (stem + ".pkl"), DATA_DIR / (stem + ".json")


def load_p1(directory=P1_DIR, use_cache=True, refresh=False, verbose=False):
    """The P1 1-minute frame (BarTime, Open..Volume, databox_IBS), cached under backtest/data/.

    df.attrs["info"] holds the per-file layout report, duplicates dropped and the cache state."""
    files = p1_files(directory)
    if not files:
        raise FileNotFoundError("no %s in %s" % (P1_GLOB, directory))
    manifest = _manifest_for(files)
    pkl, mjs = _cache_paths(P1_CACHE_STEM)
    if use_cache and not refresh and pkl.exists() and mjs.exists():
        try:
            saved = json.loads(mjs.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = None
        if saved and saved.get("key") == manifest:
            df = pd.read_pickle(pkl)
            df.attrs["info"] = dict(saved.get("info", {}), cache="hit")
            return df
    parts, infos = [], []
    for f in files:
        part, inf = read_everybar(f, extra_cols=P1_EXTRA_COLS)
        if verbose:
            print("  read %s: %d bar rows, %d signal rows, shift %+d"
                  % (f.name, inf["bar_rows"], inf["signal_rows"], inf["shift"]))
        parts.append(part)
        infos.append(inf)
    df, ndup = combine_bars(parts)
    info = {"files": infos, "duplicates_dropped": int(ndup), "bars": int(len(df)),
            "first": str(df["BarTime"].iloc[0]), "last": str(df["BarTime"].iloc[-1])}
    if use_cache:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = pkl.with_suffix(".pkl.tmp")
        df.to_pickle(tmp)
        os.replace(tmp, pkl)
        mjs.write_text(json.dumps({"key": manifest, "info": info}, indent=1), encoding="utf-8")
    df.attrs["info"] = dict(info, cache="miss" if use_cache else "off")
    return df


# ============================================================================================
# generic plain-OHLCV CSV (robustness datasets)
# ============================================================================================
def to_central(times, source_tz=None):
    """Naive US Central wall-clock times. Tz-aware input is converted; naive input is first
    localised to `source_tz` (if given) - naive input without source_tz is returned unchanged
    (it is taken to be Central already)."""
    t = pd.Series(pd.to_datetime(times))
    if t.dt.tz is None:
        if source_tz is None:
            return t
        t = t.dt.tz_localize(source_tz)
    return t.dt.tz_convert(CENTRAL_TZ).dt.tz_localize(None)


def load_ohlcv_csv(path, date_col="Date", time_col="Time", columns=None, datetime_format=None,
                   source_tz=None, label="close", bar_minutes=None, sep=","):
    """Plain OHLCV CSV -> (BarTime, Open..Volume) frame, BarTime = bar CLOSE time, US Central.

    columns: {"Open": "o", ...} to rename source columns; time_col=None when date_col already
    holds date and time; label="open" shifts open-labelled bars by `bar_minutes` to their close."""
    raw = pd.read_csv(path, sep=sep)
    cmap = {c: c for c in OHLCV}
    cmap.update(columns or {})
    if time_col is not None and time_col in raw.columns:
        stamp = raw[date_col].astype(str).str.strip() + " " + raw[time_col].astype(str).str.strip()
    else:
        stamp = raw[date_col].astype(str).str.strip()
    bt = pd.to_datetime(stamp, format=datetime_format)
    bt = to_central(bt, source_tz)
    if label == "open":
        if not bar_minutes:
            raise ValueError("label='open' needs bar_minutes")
        bt = bt + pd.Timedelta(minutes=bar_minutes)
    elif label != "close":
        raise ValueError("label must be 'close' or 'open'")
    df = pd.DataFrame({"BarTime": bt.to_numpy()})
    for c in OHLCV:
        df[c] = pd.to_numeric(raw[cmap[c]], errors="coerce").to_numpy(dtype=float)
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df["Volume"] = df["Volume"].fillna(0.0)
    df, ndup = combine_bars([df])
    df.attrs["info"] = {"file": Path(path).name, "bars": int(len(df)), "duplicates_dropped": int(ndup)}
    return df


# ============================================================================================
# sessions and frames (PROTOCOL section 3)
# ============================================================================================
def _tod(t):
    return t - t.dt.normalize()


def trading_date(times, roll_hour=ROLL_HOUR):
    """Calendar date of the close time, plus one day if the close time is AFTER roll_hour:00."""
    t = pd.Series(pd.to_datetime(times))
    d = t.dt.normalize()
    after = _tod(t) > pd.Timedelta(hours=roll_hour)
    return d + pd.to_timedelta(after.astype(np.int64), unit="D")


def halt_mask(times, halt=HALT):
    """True for bars whose close time-of-day lies in the half-open halt window (start, end]."""
    t = pd.Series(pd.to_datetime(times))
    lo, hi = pd.Timedelta(halt[0] + ":00"), pd.Timedelta(halt[1] + ":00")
    tod = _tod(t)
    return (tod > lo) & (tod <= hi)


def add_sessions(m1, roll_hour=ROLL_HOUR, halt=HALT):
    """Copy of the 1-minute frame with a TradingDate column. Raises SessionError if any bar closes
    inside the halt (start, end] (pass halt=None for markets without that halt)."""
    df = m1.reset_index(drop=True).copy()
    if halt is not None:
        bad = halt_mask(df["BarTime"], halt)
        if bad.any():
            raise SessionError("%d bar(s) close inside the halt (%s, %s], first: %s"
                               % (int(bad.sum()), halt[0], halt[1],
                                  df.loc[bad, "BarTime"].head(5).astype(str).tolist()))
    df["TradingDate"] = trading_date(df["BarTime"], roll_hour).to_numpy()
    return df


_AGG = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum",
        "BarTime": "last"}


def _close_at(m1s, hhmm, dates):
    """Close of the 1-minute bar ending exactly at hhmm on each trading date (NaN if absent)."""
    bt = m1s["BarTime"]
    sel = ((bt - bt.dt.normalize()) == pd.Timedelta(hhmm + ":00")) & (bt.dt.normalize() == m1s["TradingDate"])
    return m1s.loc[sel].groupby("TradingDate")["Close"].last().reindex(dates)


def snap_settle(low, high, ibs, tick=TICK, round_unit=IBS_ROUND, eps=GRID_EPS):
    """A1.1 settlement close snap_tick(L + IBS*(H - L)) and the reason it cannot be used.

    Returns (snapped, reason) arrays; reason "" = usable, else "ibs_missing", "h_eq_l" or
    "off_grid" (unsnapped value farther from the tick grid than 4-decimal IBS rounding can
    explain: |raw - snapped| > round_unit * (H - L) + eps)."""
    lo, hi, x = (np.asarray(v, dtype=float) for v in (low, high, ibs))
    raw = lo + x * (hi - lo)
    snapped = np.round(raw / tick) * tick
    reason = np.full(len(raw), "", dtype=object)
    reason[np.abs(raw - snapped) > round_unit * (hi - lo) + eps] = "off_grid"
    reason[hi == lo] = "h_eq_l"
    reason[np.isnan(x)] = "ibs_missing"
    return snapped, reason


def daily_frame(m1s, close_mode=DEFAULT_CLOSE_MODE):
    """D frame: one bar per trading date (first open, max, min, close, sum); BarTime = close time
    of the date's last 1-minute bar; Bars = number of 1-minute bars.

    close_mode (PROTOCOL A1):
      "last"   - close of the date's last 1-minute bar (v1, the 16:00 last trade);
      "settle" - snap_0.25(L + IBS_ORIG*(H - L)), IBS_ORIG = databox_IBS of the date's last
                 1-minute bar; if that is missing, H == L, or the unsnapped value is farther from
                 the grid than 0.00005*(H - L) (A1.1, the 4-decimal IBS rounding bound): the close
                 of the 1-minute bar ending 15:00 CT, else the last close;
      "1500"   - close of the 1-minute bar ending 15:00 CT, else the last close.
    CloseSource names the branch used ("settle" | "1500" | "last"); CloseReason why a settle
    date fell back ("off_grid" | "ibs_missing" | "h_eq_l", "" otherwise)."""
    if close_mode not in CLOSE_MODES:
        raise ValueError("close_mode must be one of %s, got %r" % (CLOSE_MODES, close_mode))
    g = m1s.groupby("TradingDate", sort=True)
    d = g.agg(_AGG)
    d["Bars"] = g.size()
    dates = d.index
    last = d["Close"].to_numpy(dtype=float)
    reason = np.full(len(d), "", dtype=object)
    if close_mode == "last":
        close, source = last, np.full(len(d), "last", dtype=object)
    else:
        c15 = _close_at(m1s, SETTLE_BAR_TIME, dates).to_numpy(dtype=float)
        has15 = ~np.isnan(c15)
        fallback = np.where(has15, c15, last)
        fb_src = np.where(has15, "1500", "last").astype(object)
        if close_mode == "1500":
            close, source = fallback, fb_src
        else:
            if IBS_ORIG_COL in m1s.columns:   # the date's LAST bar, even if its value is empty
                ibs = m1s.groupby("TradingDate", sort=True).tail(1).set_index("TradingDate")[IBS_ORIG_COL]
                ibs = pd.to_numeric(ibs, errors="coerce").reindex(dates).to_numpy(dtype=float)
            else:
                ibs = np.full(len(d), np.nan)
            snapped, reason = snap_settle(d["Low"], d["High"], ibs)
            ok = reason == ""
            close = np.where(ok, snapped, fallback)
            source = np.where(ok, "settle", fb_src).astype(object)
    d["Close"] = close
    d["CloseSource"] = source
    d["CloseReason"] = reason
    d = d.reset_index()
    return d[["TradingDate", "BarTime"] + OHLCV + ["Bars", "CloseSource", "CloseReason"]]


def close_report(d_frame, window=None):
    """Counts of the D-frame close branches (all dates, or the dates inside `window`)."""
    d = d_frame
    if window is not None:
        td = pd.to_datetime(d["TradingDate"])
        d = d[(td >= window[0]) & (td <= window[1])]
    src = d["CloseSource"].value_counts().to_dict()
    rsn = d.loc[d["CloseReason"] != "", "CloseReason"].value_counts().to_dict()
    return {"dates": int(len(d)), "source": {k: int(v) for k, v in src.items()},
            "fallback_reason": {k: int(v) for k, v in rsn.items()}}


def resample_frame(m1s, minutes=15):
    """Right-labelled N-minute bars: a 1-minute bar closing at t goes to the bar closing at
    ceil(t, N min); grouped by (TradingDate, label) so no bar spans a trading date."""
    label = m1s["BarTime"].dt.ceil("%dmin" % minutes)
    g = m1s.assign(_Label=label.to_numpy()).groupby(["TradingDate", "_Label"], sort=True)
    agg = dict(_AGG)
    del agg["BarTime"]
    f = g.agg(agg)
    f["Bars"] = g.size()
    f = f.reset_index().rename(columns={"_Label": "BarTime"})
    return f[["TradingDate", "BarTime"] + OHLCV + ["Bars"]]


def build_frames(m1, roll_hour=ROLL_HOUR, halt=HALT, close_mode=DEFAULT_CLOSE_MODE):
    """{'1m': sessioned 1-minute frame, 'D': daily frame, '15m': 15-minute frame (never depends
    on close_mode)}."""
    m1s = add_sessions(m1, roll_hour, halt)
    return {"1m": m1s, "D": daily_frame(m1s, close_mode), "15m": resample_frame(m1s, 15)}


def session_report(d_frame, short_bars=300):
    """Data-coverage facts for the report: weekday gaps and short sessions on the D frame."""
    dates = pd.DatetimeIndex(d_frame["TradingDate"])
    bdays = pd.bdate_range(dates[0], dates[-1])
    missing = bdays.difference(dates)
    weekend = dates[dates.dayofweek >= 5]
    pos = np.searchsorted(bdays.values, dates.values)
    max_gap = int(np.max(np.diff(pos)) - 1) if len(pos) > 1 else 0
    short = d_frame.loc[d_frame["Bars"] < short_bars, ["TradingDate", "Bars"]]
    return {
        "trading_dates": int(len(dates)), "first": str(dates[0].date()), "last": str(dates[-1].date()),
        "missing_weekdays": int(len(missing)), "max_consecutive_missing_weekdays": max_gap,
        "weekend_dates": int(len(weekend)), "short_sessions": int(len(short)),
        "short_session_list": [(str(r.TradingDate.date()), int(r.Bars)) for r in short.itertuples()],
    }
