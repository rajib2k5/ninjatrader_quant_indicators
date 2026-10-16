# Channel B (runtime auditor) — algorithm claims B1–B9, M1–M27

status: written 2026-10-16 against `validation/algo-claims-ledger.md` (FROZEN 2026-10-16)
spec source: the ledger ONLY (formula column + B1–B9 definitions + "Pre-registered Channel B probes"). No documentation, help guides, papers or NinjaTrader `@*.cs` were consulted. `indicators/*.cs` were read as text in exactly one file, `test_repo_invariants.py`, never as a formula source. No `channel-a*.md` was read.
deliverable: `validation/pytests/` (self-contained; file list + sha256 in §7)

## 1. Commands and verbatim results

Environment: Windows 11, `python` = 3.9.13, numpy 2.0.2, pandas 2.3.3, pytest 8.4.2, hypothesis 6.141.1; Git bash `C:\Program Files\Git\bin\bash.exe`; dotnet SDK 8.0.100 Roslyn csc at the path in `validation/probes/compile_probe.sh`; NinjaTrader 8.1.8.3 assemblies present.

Environment incident (recorded, not a verdict): the first attempt `python -I -c "import sys,pandas,numpy,pytest,hypothesis"` failed with `ModuleNotFoundError: No module named 'pytest'` because pytest/hypothesis lived in the per-user site-packages (`%APPDATA%\Python\Python39\site-packages`), which `-I` hides. The coordinator then installed pytest 8.4.2 and hypothesis 6.141.1 into the interpreter's own site-packages; `python -I -c "import pytest,hypothesis"` now resolves to `C:\Users\rajib\AppData\Local\Programs\Python\Python39\lib\site-packages\pytest\__init__.py`. The `-I` flag was kept for every run below.

### Run 1 — whole suite

```
cd C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators
python -I -m pytest validation/pytests -q -rfEsxX -p no:cacheprovider
```
```
.............................ss.ss.ss.ssxss.ss.ss.sssssxss.sssssssssssss [ 16%]
ssssssssssssssssssssssssssssssssssssssssss.............................. [ 33%]
........................................................................ [ 50%]
........................................................................ [ 67%]
........................................................................ [ 84%]
..................................................................       [100%]
348 passed, 76 skipped, 2 xfailed in 56.40s
rc=0
```

### Run 2 — without the compile probes

```
python -I -m pytest validation/pytests -q -m "not slow" -rfEsxX -p no:cacheprovider
```
```
319 passed, 76 skipped, 29 deselected, 2 xfailed in 14.67s
rc=0
```

Collected: 426 tests (`--collect-only`), of which 26 are `test_falsifier_*`. **Failures in the final runs: none.** The 2 xfails are strict, documented data findings (§5), not errors.

### Skip summary of Run 1 (verbatim `-rs` block, grouped; every skip is a harness-data skip or a pre-registered UNVERIFIABLE)

```
SKIPPED [1] validation\pytests\test_data_integrity.py:68/73/78/85/99/105/111/116/134/147/154: harness file qi_dump_MES_Minute-15.csv has a header but no data rows   (x11)
SKIPPED [1] validation\pytests\test_data_integrity.py:68/73/78/85/99/105/111/116/134/147/154: harness file qi_dump_MES_Minute-60.csv has a header but no data rows   (x11)
SKIPPED [1] validation\pytests\test_data_integrity.py:122: not a time-based (Minute-N) series: MES_150tick_20250202_20260224.csv
SKIPPED [1] validation\pytests\test_data_integrity.py:157: harness-only check
SKIPPED [1] validation\pytests\test_data_integrity.py:(old-export-only checks on harness files)   (x2)
SKIPPED [1] validation\pytests\test_integration_harness.py:59 .. 279 (36 tests, one per claim incl. the P3 falsifier): UNVERIFIABLE: harness file qi_dump_MES_Minute-60.csv has a header but no data rows
SKIPPED [3] validation\pytests\test_patterns_sanity.py:24, :31, :38, :46 and [1] :57: UNVERIFIABLE: harness file qi_dump_MES_Minute-60.csv has a header but no data rows   (13 tests)
SKIPPED [1] validation\pytests\test_patterns_sanity.py:65: UNVERIFIABLE on Channel B: ledger M24/M25/M26/M27 states rule families and fixed confidences, not a formula precise enough to replay bar-by-bar   (x4)
XFAIL test_data_integrity.py::test_timestamps_strictly_increasing_no_duplicates[old_export:MES_150tick_20250202_20260224.csv] - tick-bar export: consecutive bars sharing a 1-s timestamp
XFAIL test_data_integrity.py::test_old_export_row_layout_matches_docstring[old_export:MES_150tick_20250202_20260224.csv] - bar rows have 54 fields vs 53 header fields: OHLCV at 15..19, not 14..18
```
(The raw 68-line block is in the pytest output; the grouping above loses no information.)

### Development-time failures (fixed before the final runs; recorded for auditability)

| test | failure | cause | fix |
|---|---|---|---|
| `test_B8_pct_k_100_at_range_high_0_at_range_low` | `assert nan == 50.0` | my test read %K at bar 10, inside the 14-bar warm-up | read bar 15 |
| `test_falsifier_chop_without_log_is_detected` | `0.0 > 1.0` | the oscillation case gives 100 under both the log and the linear formula — a non-discriminating falsifier | falsifier moved to the straight-trend case (log → 0, linear → 7.14) |
| `test_chop_in_0_100_and_adx_bounded` (hypothesis) | ADX = 100.00000000000001 | floating rounding on a mathematically ≤ 100 quantity; the ledger defines no clamp | bound checks in `test_properties.py` carry 1e-9 slack (`FP`); the reference is unchanged |
| `test_gap_pct_is_NOT_shift_invariant` | `FailedHealthCheck: 50 inputs filtered out` | the `bars()` strategy opens every bar at the previous close so gap% ≡ 0 and `assume` rejected everything | the test injects a one-tick gap on every bar instead of filtering |
| smoke of the differential (§3) | `M22/delta: ref=-6259 harness=-6258.75` | the old export's bar rows are shifted one column relative to the header (§5) | loader aligns by field-count surplus |

## 2. Mutation (falsifiability) check on the reference itself — runtime-audit.md §5

`qi_ref.py` sha256 before: `07b2cdf18b6e7b37c34d679bec3513da9b372c9b13b17d8e625bc789c57d0349`. Each mutant applied with `sed -i`, suite run with `python -I -B -m pytest validation/pytests/test_unit_builtins.py validation/pytests/test_unit_modules.py validation/pytests/test_properties.py -q -p no:cacheprovider`, original restored from a copy, checksum re-verified (`match=yes`).

```
mutant M1_sample_std :: sed 's/\.std(ddof=0)/.std(ddof=1)/' :: rc=1 :: 4 failed, 116 passed in 12.79s
    FAILED test_unit_builtins.py::test_B5_stddev_is_population_std
    FAILED test_unit_builtins.py::test_B5_stddev_hand_value
    FAILED test_unit_builtins.py::test_B7_bollinger_is_sma_pm_2_popstd
    FAILED test_unit_builtins.py::test_falsifier_bollinger_sample_std_is_detected
mutant M2_ema_alpha_1_over_n :: sed 's|alpha = 2.0 / (n + 1.0)|alpha = 1.0 / n|' :: rc=1 :: 2 failed, 118 passed in 14.25s
    FAILED test_unit_builtins.py::test_B2_ema_matches_closed_form
    FAILED test_unit_builtins.py::test_B2_ema_recursion_one_step
mutant M3_atr_no_linear_warmup :: sed 's|out[t] = (min(t, n - 1) * out[t - 1] + tr[t]) / min(t + 1, n)|out[t] = ((n - 1) * out[t - 1] + tr[t]) / n|' :: rc=1 :: 1 failed, 119 passed in 14.28s
    FAILED test_unit_builtins.py::test_B4_atr_warmup_recursion_hand_values
mutant M4_rsi_no_wilder :: sed 's|avg_up = avg_up + (up - avg_up) / n|avg_up = up|' :: rc=1 :: 1 failed, 119 passed in 14.11s
    FAILED test_unit_builtins.py::test_B1_rsi_hand_values_n2
mutant M5_cum20_boundary :: sed 's|cum[:21] = 0.0|cum[:20] = 0.0|' :: rc=1 :: 2 failed, 118 passed in 14.33s
    FAILED test_unit_modules.py::test_M22_cum20_strict_bar_gt_20_guard_and_window
    FAILED test_unit_modules.py::test_falsifier_cum20_at_bar_20_is_detected
restored sha256=07b2cdf18b6e7b37c34d679bec3513da9b372c9b13b17d8e625bc789c57d0349 match=yes
```
All five mutants killed (non-zero rc). In addition the 26 in-suite `test_falsifier_*` tests each assert that a deliberately wrong formula (sample std, EMA alpha 1/n, RSI without Wilder smoothing, ATR without linear warm-up, swapped MACD legs, raw DX for ADX, IBS with C−O, streak reset on unchanged close, CRSI with RSI(3), gap vs previous open, 3-day TOM window, CHOP without log, inverted VRP, cum20 at bar 20, VWAP on close, un-rescaled %B, swapped composite weights, un-normalised range under scaling, centred (look-ahead) average, sign-blind RSI, ATR/price under shift, planted "Buy" literal, foreign confidence value, dropped-semicolon C# mutant, RSI 14→13 differential) is rejected by the same assertions — all 26 pass in Run 1.

## 3. P2 differential — status and smoke

Harness files present: `validation/runs/qi_dump_MES_Minute-15.csv` and `qi_dump_MES_Minute-60.csv` (both 1,795 bytes, **header line only, 0 data rows**; 83 columns). The regenerated `validation/QI_EgvDump.cs` writes 90 columns (adds `QI_BollingerPctB.Values[1..3]`, `.Upper/.Middle/.Lower`), so these files are also stale. Every differential and pattern test therefore skipped with reason `UNVERIFIABLE: harness file ... has a header but no data rows`. Nothing was passed by default.

Smoke of the differential code path (NOT a verdict): a scratch CSV in the 90-column layout was generated from `qi_ref` itself on 1,500 de-duplicated bars of the old 150-tick export (values written with `%.4f`, like the harness) and fed through `QI_HARNESS_FILE=<scratch>/qi_dump_SMOKE.csv python -I -m pytest validation/pytests/test_integration_harness.py validation/pytests/test_patterns_sanity.py -q` → `47 passed, 6 skipped`. This shows (a) every column lookup, warm-up and tolerance path executes, (b) the F4 quantisation allowance `CSV_QUANT = 0.5e-4` is sufficient for a consistent oracle, and (c) `test_falsifier_differential` (reference RSI period 13 vs an RSI-14 column) does fail the check as required by P3. The scratch file lives outside the repository and must not be mistaken for harness data.

When a real dump exists: `python -I -m pytest validation/pytests/test_integration_harness.py validation/pytests/test_patterns_sanity.py -q -rA` gives one verdict per claim ID; a failure message quotes the first offending bar, both values, the diff and the max diff.

## 4. Verdicts per claim ID (claim (b): "the compiled QI module computes F")

P1 = synthetic unit/property tests of the reference against the ledger formula (CONFIRMS that `qi_ref` implements F and that the tests can fail). P2 = harness differential. Verdict column is claim (b).

| ID | P1 tests (all pass) | falsifier / mutant killed | P2 | verdict (b) |
|---|---|---|---|---|
| B1 RSI (Wilder) | `test_B1_*` (monotone→100/0, hand values n=2, bounds, smooth=1 identity), properties (bounds, scale/shift invariance, monotone in last move) | `test_falsifier_rsi_without_wilder_is_detected`; mutant M4 | skipped: no harness rows | UNVERIFIABLE |
| B2 EMA | `test_B2_*` (closed form, constant, one-step) | `test_falsifier_ema_alpha_1_over_n_is_detected`; mutant M2 | skipped | UNVERIFIABLE |
| B3 SMA | `test_B3_*` (numpy convolution, hand value), shift/scale equivariance | covered by M1 mutant chain (Bollinger) and causality falsifier | skipped | UNVERIFIABLE |
| B4 ATR (NT warm-up) | `test_B4_*` (constant range, warm-up hand values, Wilder after warm-up, gap TR) | `test_falsifier_atr_plain_wilder_from_bar0_is_detected`; mutant M3 | skipped (via WideRange/VRP columns) | UNVERIFIABLE |
| B5 StdDev (population) | `test_B5_*` | `test_falsifier_sample_std_is_detected`; mutant M1 | skipped | UNVERIFIABLE |
| B6 MACD | `test_B6_*` (constant → 0, component identities, trend sign) | `test_falsifier_macd_swapped_fast_slow_is_detected` | skipped | UNVERIFIABLE |
| B7 Bollinger | `test_B7_*` (= SMA ± 2·popstd, symmetry) | `test_falsifier_bollinger_sample_std_is_detected`; mutant M1 | skipped (`Upper/Middle/Lower` columns absent in the stale files; present in the regenerated harness) | UNVERIFIABLE |
| B8 StochasticsFast(3,14) | `test_B8_*` (100 at range high, 0 at low, hand value, %D = SMA3) | bounds/scale/shift property falsifiers | skipped | UNVERIFIABLE |
| B9 ADX | `test_B9_*` (flat → 0, straight trend → 100, DM rules, bounds) | `test_falsifier_adx_without_wilder_smoothing_of_dx_is_detected` | skipped | UNVERIFIABLE |
| M1 IBS | `test_M1_*` (0.25 bar, doji 0.5, forming daily range, 17:00 rollover) | `test_falsifier_ibs_close_minus_open_is_detected` | skipped | UNVERIFIABLE |
| M2 RSI2 | = B1 | = B1 | skipped | UNVERIFIABLE |
| M3 ConnorsRSI | `test_M3_*` (strict percent-rank, ties, 50 until bar 100, mean of three) | `test_falsifier_crsi_with_rsi3_of_price_is_detected` | skipped | UNVERIFIABLE |
| M4 StochFade | = B8 | = B8 | skipped | UNVERIFIABLE |
| M5 RVZScore | `test_M5_*` (0 for constant ATR, 0 until bar 25, z definition) | mutant M1 (popstd) | skipped | UNVERIFIABLE |
| M6 CompositeVol | `test_M6_*` (weights 0.40/0.35/0.25, part definitions) | `test_falsifier_composite_weights_swapped_is_detected` | skipped | UNVERIFIABLE |
| M7 TurnOfMonth | 16 parametrised dates incl. Feb 28/29-day and 30/31-day months | `test_falsifier_turn_of_month_window_of_last_3_days_is_detected` | skipped | UNVERIFIABLE |
| M8 ConsecDays | `test_M8_*` (runs, unchanged keeps count), property on every bar | `test_falsifier_streak_reset_on_unchanged_is_detected` | skipped | UNVERIFIABLE |
| M9 OvernightGap | `test_M9_*`, NOT-shift-invariant property | `test_falsifier_gap_vs_previous_open_is_detected` | skipped | UNVERIFIABLE |
| M10 BollingerPctB | `test_M10_*` (+100/−100/0 at bands, = 200·%b − 100) | `test_falsifier_pct_b_unscaled_is_detected` | skipped | UNVERIFIABLE |
| M11 TurnaroundTuesday | `test_M11_day_of_week_sunday_zero` | (both numberings implemented; the differential reports the alternate) | skipped | UNVERIFIABLE |
| M12 RSI14 | = B1 | = B1 | skipped | UNVERIFIABLE |
| M13 VRPProxy | `test_M13_*` (ratio, 1.0 before bar 20, constant range → 1) | `test_falsifier_vrp_inverted_ratio_is_detected` | skipped | UNVERIFIABLE |
| M14 WideRangeBar | `test_M14_*` (hand value, ATR ≤ 0 → 1) | scale-invariance falsifier | skipped | UNVERIFIABLE |
| M15 HedgingPressure | `test_M15_*` (basis/slope terms, ±25 and ±100 clamps), HP-clamp property | — | skipped; **formula under-specified in the ledger** (2 of 4 terms have no formula) → only the ±100 clamp is testable | UNVERIFIABLE (by construction) |
| M16 VWAPDistance | `test_M16_*` (hand values, calendar-day reset, ATR units) | `test_falsifier_vwap_with_close_instead_of_typical_is_detected` | skipped | UNVERIFIABLE |
| M17 MACDHistogram | = B6 + `test_M17_*` | = B6 | skipped | UNVERIFIABLE |
| M18 EMACross | = B2 + `test_M18_*` | = B2 | skipped | UNVERIFIABLE |
| M19 SMA200Trend | = B3 + `test_M19_*` (distance from bar 200), shift property | mutant chain | skipped | UNVERIFIABLE |
| M20 ATRRegime | `test_M20_*` (1.0 before bar 50, ratio) | scale-invariance falsifier | skipped | UNVERIFIABLE |
| M21 VolumeSpike | `test_M21_*` (ratio hand value, SMA ≤ 0 → 1) | — (zero-volume property) | skipped | UNVERIFIABLE |
| M22 VolumeDelta | `test_M22_*` (signs, strict bar > 20 guard, window, SMA10 from bar 10) | `test_falsifier_cum20_at_bar_20_is_detected`; mutant M5 | skipped | UNVERIFIABLE |
| M23 ChopIndex | `test_M23_*` (trend 0 / oscillation 100, trend < oscillation, 50 until 14, hand value, 3-condition state) | `test_falsifier_chop_without_log_is_detected` | skipped | UNVERIFIABLE |
| M24 LiquiditySweep | value-set sanity only (`test_patterns_sanity.py`) | `test_falsifier_value_set_check_rejects_foreign_confidence` | skipped | UNVERIFIABLE — exact replay impossible on Channel B |
| M25 OrderFlowPlus | same | same | skipped | UNVERIFIABLE — exact replay impossible on Channel B |
| M26 SMC (+TrendDir) | same | same | skipped | UNVERIFIABLE — exact replay impossible on Channel B |
| M27 KeyLevels | none possible | — | the harness exports **no `QI_KeyLevels.*` columns** | UNVERIFIABLE (insufficient columns) |

**CONFIRMED: none. REFUTED: none. UNVERIFIABLE: all 36 (B1–B9, M1–M27)** for claim (b), because no harness data row exists. The reference implementations and their tests are ready; the verdicts flip to CONFIRMED/REFUTED per claim the moment a populated `qi_dump_*.csv` is dropped into `validation/runs/` and Run 1 is repeated. Claim (a) is N/A on Channel B by construction.

Repo-brief invariants (not ledger claims, requested in the brief): 27 files × 7 static checks + count — all pass (no Buy/Sell literals, no Draw.ArrowUp/Down, no TP/SL drawing, no StreamWriter / `C:\Users` paths, DISCLAIMER header + `ShowDisclaimer` property in every file, `IsOverlay` assigned exactly once, overlay files have no `AddLine`, panel files have a visible `AddPlot`). Compile smoke: 27/27 indicators compile individually and together with the dotnet Roslyn csc; the dropped-semicolon mutant fails to compile (rc ≠ 0).

## 5. Data findings (bar data, not formulas)

1. **Harness dumps are empty and stale.** Both `qi_dump_MES_*.csv` have a header only (0 rows) and the 83-column header of the previous `QI_EgvDump` build, while the current `validation/QI_EgvDump.cs` writes 90 columns. The harness has to be re-run on a chart before Channel B can decide anything.
2. **Old export column shift.** `MES_150tick_20250202_20260224.csv` has a 53-field header but every bar row (SignalType empty) has 54 fields: Open/High/Low/Close/Volume are at columns 15–19, not 14–18 as `validation/probes/diff_values.py`'s docstring (and this task's brief) state. With the documented offsets, "Open" reads the real High and "Volume" reads the real ATR14. `conftest.load_old_export` aligns by the field-count surplus (`df.attrs["column_shift"] == [1]`, consistent across all 12,053 bar rows in the first 20,000 lines); `test_old_export_row_layout_matches_docstring` is a strict xfail that will flip if the layout is ever fixed.
   Verified on bar rows 1, 500 and 3000 (header name → actual value): `14 Open → ''`, `15 High → 6264.50` (the real Open), `19 ATR14 → 223` (the real Volume), `20 databox_HPScore → 1.75` (the real ATR14), `21 databox_IBS → 50.0000 / 29.5587 / -48.0615` (the real HP score), `22 databox_RSI2 → 0.9268` (the real IBS). The surplus empty field lies among columns 8–14, so EVERY field from Open onward is displaced by one.
   **Consequence for the earlier runtime differential:** `validation/probes/diff_values.py` line 74 reads the databox values by fixed position, `r[20 + i]`, so for every claim C18–C43 it compared the harness column against the ORIG column one to the LEFT of the intended one (HPScore ← ATR14, IBS ← HPScore, RSI2 ← IBS, …). Any pass/fail recorded from that script against this export is PROBE_INVALID until the indices are corrected (read `r[21 + i]`, or align by `len(row) - len(header)` as `conftest.load_old_export` does) and the diff is re-run. This file was not modified here; the finding is flagged as a separate task.
   **Resolved 2026-10-16:** `diff_values.py` now aligns every row by `len(row) - len(header)` with per-row checks and a loud layout report (abort on any deviation); no recorded verdict was affected because C18–C43 were never run. See channel-b-runtime.md, 2026-10-16 addendum.
3. **Same-second tick bars.** In the first 20,000 lines (12,053 bar rows) there are 463 consecutive bar pairs with identical `BarTime` (second resolution; timestamps never go backwards). "Strictly increasing, no duplicates" therefore cannot hold for the 150-tick series; it is asserted for Minute-N series and recorded as a strict xfail for tick series. Consequence: `diff_values.py`'s "LAST row per BarTime" policy silently drops the earlier bar of every same-second pair — 463 real bars in this slice — so a join on `BarTime` alone is lossy for tick charts.
   **Resolved 2026-10-16:** `diff_values.py` and `merge_runs.py` now join on `(BarTime, k)`, k = ordinal inside the same-BarTime group (positional join; whole file: 15,782 such bars), with harness `Bar` monotonicity and O/H/L/C/V equality as the pairing proof. See channel-b-runtime.md, 2026-10-16 addendum.
4. OHLC sanity (High ≥ max(O,C), Low ≤ min(O,C), Volume ≥ 0, no NaN) holds on all 12,053 bar rows once the columns are aligned.

## 6. Assumptions where the ledger is silent (all documented in `qi_ref.py` docstrings)

- Seeds: EMA seeded with x[0]; Wilder averages (RSI, ADX) seeded with the first move; all recursive differentials start at bar 300 so seeds are immaterial (worst case EMA50: (49/51)^300 ≈ 6e-6 of the seed error).
- "X until/before bar N" read as the NinjaScript `CurrentBar < N` guard (positions t < N get X). CRSI's ROC at bar 0 taken as 0 so that 100 previous changes exist from bar 100.
- Fallbacks not stated: RSI = 100 if down-avg = 0 and up-avg > 0, 50 if both 0; %K = 50 when HH = LL; CHOP = 50 when HH = LL; RV-z = 0 when popstd = 0 (also the brief's expected value); priceZ = 0 when popstd = 0; vov = 0 when ATR = 0; VWAP = typical price while the day's volume is 0; %B = 0 when the bandwidth is 0; VRP/ATR-regime = 1.0 when the denominator is 0; DX = 0 when +DI + −DI = 0 (so a flat series gives ADX 0, as pre-registered).
- Bollinger parameters (2, 20) — the ledger names none for QI_BollingerPctB.
- M1 on intraday charts keyed by the CME trading day (17:00 rollover); the calendar-day variant is computed and quoted in the failure message if the primary disagrees. M16 is keyed by calendar day as the ledger says ("day-of-year change").
- M11: 0 = Sunday … 6 = Saturday; the Monday = 0 variant is quoted on disagreement. M7/M11 treat `BarTime` as already US Central (chart-local time).
- Harness quantisation: values are `ToString("F4")`, so each ledger tolerance is applied as tolerance + 0.5e-4 (`CSV_QUANT`), including the 1e-6 claims (B3, B7, B8, M9, M10, M19), which can only be tested to 5.1e-5 on this harness.
- Bounds in `test_properties.py` allow 1e-9 floating slack; CHOP (clamped by the ledger) is also asserted exactly.

## 7. Deliverable files (sha256 at the time of Run 1/Run 2)

```
cb49d404b78d0d0522cc53c73fb590ca27f5a77dea5770c0cf7bcf6633999e78  validation/pytests/conftest.py
07b2cdf18b6e7b37c34d679bec3513da9b372c9b13b17d8e625bc789c57d0349  validation/pytests/qi_ref.py
a8e14f550f489186568fbea070b5cb4e4210618a5029d7479c6fccf565444b1c  validation/pytests/test_compile_smoke.py
54106649d4484abc9afa8eca1c2f691cfb156c6d1d90b086451b89423b71bb00  validation/pytests/test_data_integrity.py
65e99b9c2679c5c056c525207daf1d8e2cb859d93819827ded2c0a0da39c91d5  validation/pytests/test_integration_harness.py
314d04d45a39f8f08e2f89bd627f8a8ed9cd2d4ef232dcb87999aafb3d8ea754  validation/pytests/test_patterns_sanity.py
d7c8858f0a37276dfbb406035a4f3d994817a881155113a1ed365641d1d86e15  validation/pytests/test_properties.py
afd4d16ab5b9926517112f40d9bfd00dcc3e9a5402c9a8a9d8952060d63872c2  validation/pytests/test_repo_invariants.py
19dde42fe44df862f171a4a590b3c98b1ca83b986ce02e9ee1e23ffeacb4f2d4  validation/pytests/test_unit_builtins.py
023c049f2f3918a621454b240a6a3a5c3197a516b55484cb1080d21e020c74fc  validation/pytests/test_unit_modules.py
822c92492ad81ad20eab0990491191676d16b5957d190946ab5938e3d717c4c0  validation/pytests/README.md   (re-hashed after adding the QI_HARNESS_FILE / data-findings notes; no test file changed after the runs)
b0cf0eda9147cc989d1c441c189aa0177213b49f1499a348bdbda4c1c66d609c  validation/pytests/requirements.txt
```
Side effects of running: hypothesis creates `.hypothesis/` in the repository root (its example database) and pytest leaves `validation/pytests/__pycache__/` (removed after the runs; `-B` avoids it). `conftest.py` honours `QI_HARNESS_FILE` to point the differential at a file outside `validation/runs/` — any such run is a smoke, never a verdict.
