"""test_data_integrity.py - properties any exported NinjaTrader bar CSV must satisfy before it
is used as an oracle.

Parametrised over every validation/runs/qi_dump_*.csv (skipped, not passed, when a file has
no data rows) and over the first 20,000 rows of the original-indicator 150-tick export.
"""
from __future__ import annotations

import os
import re

import numpy as np
import pandas as pd
import pytest

from conftest import OHLCV, OLD_EXPORT, harness_files, load_harness, load_old_export

# --------------------------------------------------------------------------------------------
# data sources
# --------------------------------------------------------------------------------------------
_SOURCES = [("harness", p) for p in harness_files()]
if not _SOURCES:
    _SOURCES = [("harness", None)]
if OLD_EXPORT.exists():
    _SOURCES.append(("old_export", str(OLD_EXPORT)))

_CACHE = {}


def _load(kind, path):
    key = (kind, path)
    if key not in _CACHE:
        if kind == "harness":
            if path is None:
                pytest.skip("no validation/runs/qi_dump_*.csv harness file exists")
            df = load_harness(path)
            if len(df) == 0:
                pytest.skip("harness file %s has a header but no data rows" % os.path.basename(path))
        else:
            df = load_old_export(path)
        _CACHE[key] = df
    return _CACHE[key]


def _ids():
    return ["%s:%s" % (k, os.path.basename(p) if p else "none") for k, p in _SOURCES]


@pytest.fixture(params=_SOURCES, ids=_ids())
def source(request):
    kind, path = request.param
    return kind, path, _load(kind, path)


def _is_tick_series(kind, path):
    name = os.path.basename(path or "")
    return kind == "old_export" or "tick" in name.lower()


def _minute_period(path):
    m = re.search(r"Minute-(\d+)", os.path.basename(path or ""))
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------------------------
def test_has_required_columns(source):
    _, _, df = source
    assert set(["BarTime"] + OHLCV) <= set(df.columns)


def test_no_nan_in_ohlc(source):
    _, _, df = source
    assert not df[["Open", "High", "Low", "Close"]].isna().any().any()


def test_timestamps_nondecreasing(source):
    _, _, df = source
    t = df["BarTime"].to_numpy()
    back = np.flatnonzero(t[1:] < t[:-1])
    assert len(back) == 0, "timestamps go backwards at rows %s" % back[:10].tolist()


def test_timestamps_strictly_increasing_no_duplicates(source, request):
    kind, path, df = source
    if _is_tick_series(kind, path):
        # 150-tick bars can close within the same second; the export has second resolution.
        # strict=True so that the suite notices if this data finding ever stops holding.
        request.node.add_marker(pytest.mark.xfail(
            strict=True, reason="tick-bar export: consecutive bars sharing a 1-s timestamp "
                                "(data finding recorded in channel-b-algo.md)"))
    t = df["BarTime"]
    dup = t[t.duplicated(keep=False)]
    assert t.is_monotonic_increasing and t.is_unique, (
        "%d duplicate timestamps, e.g. %s" % (len(dup), dup.head(5).tolist()))


def test_high_ge_max_open_close(source):
    _, _, df = source
    bad = df[df["High"] < df[["Open", "Close"]].max(axis=1)]
    assert len(bad) == 0, bad.head()


def test_low_le_min_open_close(source):
    _, _, df = source
    bad = df[df["Low"] > df[["Open", "Close"]].min(axis=1)]
    assert len(bad) == 0, bad.head()


def test_volume_nonnegative(source):
    _, _, df = source
    assert (df["Volume"].fillna(-1) >= 0).all()


def test_minute_bar_spacing_within_session(source):
    """Minute-N series: consecutive bars are N minutes apart except across a session
    boundary (the gap must contain the 17:00 session open, i.e. the trading day changes)."""
    kind, path, df = source
    n = _minute_period(path)
    if n is None:
        pytest.skip("not a time-based (Minute-N) series: %s" % os.path.basename(path or ""))
    t = df["BarTime"]
    dt = t.diff().dt.total_seconds().div(60).to_numpy()[1:]
    tday = (t + pd.Timedelta(hours=7)).dt.normalize().to_numpy()
    boundary = tday[1:] != tday[:-1]
    bad = np.flatnonzero((dt != n) & ~boundary)
    assert len(bad) == 0, "non-%d-minute spacing inside a session at rows %s (minutes: %s)" % (
        n, (bad + 1)[:10].tolist(), dt[bad][:10].tolist())
    assert (dt > 0).all()
    assert (dt[~boundary] == n).all()


def test_old_export_row_layout_matches_docstring(source, request):
    """diff_values.py documents Open..Volume at columns 14..18; the bar rows actually carry one
    surplus field (54 vs 53 header fields). Recorded as a strict xfail data finding so the suite
    notices if the file is ever re-exported with an aligned layout."""
    kind, path, df = source
    if kind != "old_export":
        pytest.skip("old-export-only check")
    request.node.add_marker(pytest.mark.xfail(
        strict=True, reason="bar rows have 54 fields vs 53 header fields: OHLCV at 15..19, not 14..18"))
    assert df.attrs["column_shift"] == [0], "column shift(s) %s with header length %d" % (
        df.attrs["column_shift"], df.attrs["header_len"])


def test_old_export_single_consistent_shift(source):
    kind, path, df = source
    if kind != "old_export":
        pytest.skip("old-export-only check")
    assert len(df.attrs["column_shift"]) == 1, df.attrs["column_shift"]


def test_harness_bar_column_is_contiguous(source):
    kind, path, df = source
    if kind != "harness":
        pytest.skip("harness-only check")
    assert "Bar" in df.columns
    np.testing.assert_array_equal(df["Bar"].to_numpy(), np.arange(len(df)))
