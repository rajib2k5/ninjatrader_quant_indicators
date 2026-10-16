# Channel B — NinjaTrader runtime probes (executed by the orchestrator)

Rules followed: channel-a-*.md were not read before these probes ran; the probe commands are the
ones pre-registered in claims-ledger.md; outputs are verbatim.

## C14 — all 27 files compile inside NinjaTrader's NinjaScript editor (LangVersion 13, real Custom project)

Setup: files copied to `Documents\NinjaTrader 8\bin\Custom\Indicators\quant_indicator\` (27 `QI_*.cs`)
and `quant_indicator\_validation\QI_EgvDump.cs`; the user pressed F5 in the NinjaScript editor
(NinjaTrader is view-only to the orchestrator). Evidence, 2026-10-15:

```
$ grep -cE "quant_indicator|QI_" NinjaTrader.Custom.csproj
28
$ ls -l --time-style=+%Y-%m-%d_%H:%M NinjaTrader.Custom.csproj  -> 2026-10-15_22:56
$ ls -l --time-style=+%Y-%m-%d_%H:%M NinjaTrader.Custom.dll     -> 2026-10-15_22:57   (was 2026-10-11_13:52 before)
$ python -I - (byte scan of NinjaTrader.Custom.dll for rb"QI_[A-Za-z0-9]+")
28 QI_ type names in NinjaTrader.Custom.dll:
QI_ATRRegime QI_BollingerPctB QI_ChopIndex QI_CompositeVol QI_ConnorsRSI QI_ConsecDays QI_EMACross
QI_EgvDump QI_HedgingPressure QI_IBS QI_KeyLevels QI_LiquiditySweep QI_MACDHistogram QI_OrderFlowPlus
QI_OvernightGap QI_RSI14 QI_RSI2 QI_RVZScore QI_SMA200Trend QI_SMC QI_StochFade QI_TurnOfMonth
QI_TurnaroundTuesday QI_VRPProxy QI_VWAPDistance QI_VolumeDelta QI_VolumeSpike QI_WideRangeBar
control IBSFade present: True
```

NinjaTrader only rewrites `NinjaTrader.Custom.dll` on a successful compile, and the project file
now lists every file; the DLL contains all 28 types. Falsifier: the same byte scan on the
pre-compile DLL (mtime 2026-10-11) could not have contained these names — they did not exist in
any source NinjaTrader had seen; not re-run because that DLL was overwritten. Screen check: the
NinjaScript editor's explorer tree shows `Indicators > quant_indicator` with all QI_ files.

Verdict: **CONFIRMED** (compile-side). Note: NinjaTrader did not append its generated-code region
to the externally-added files (it does so only when a file is saved from its editor); the
`.cs` files in the NinjaTrader folder therefore remain byte-identical to the repository.

## C2 / C4 / C5 / C8 / C9 / C10 behavioral halves, C18–C44 differential — pending the chart run
(filled in below as the runs happen)

## 2026-10-16 addendum — diff_values.py probe defect (ORIG column shift) and the tick-chart join key

**Verdict changes for C18–C43: none.** No C18–C43 verdict was ever derived from `diff_values.py`
(this file and channel-b-auto.md §7 carry C18–C44 as "pending runtime"), so the invalid probe
tainted no recorded verdict. `validation/runs/` holds no harness CSV at all today (the two
header-only `qi_dump_MES_Minute-*.csv` noted in channel-b-algo.md §5 item 1 are gone), so the
differential could not be re-run; C18–C43 stay **pending the chart run**. Note for that run: the
ORIG export is MES **150-tick** only (`Symbol=MES, Timeframe=150t`, bar rows 2025-02-04 17:00:01 →
2025-04-17 14:00:20 despite the file name's 2026 date, which is the log-write Timestamp), so a
Minute-period dump can never join it; the 27 QIV_* modules must be run on a 150-tick MES chart
covering that range, merged with `merge_runs.py`, and diffed as
`python diff_values.py <ORIG> validation/runs/qi_dump_MES_Tick-150.csv`.

### Defect (as found)
`diff_values.py` read the ORIG databox values by fixed position (`r[20 + i]`, later patched to a
hardcoded `r[21 + i]`) while the bar rows carry one surplus empty field against the 53-field
header. With `20 + i` every C18–C43 comparison used the ORIG column one to the LEFT of the
intended one (HPScore ← ATR14, IBS ← HPScore, RSI2 ← IBS, …). A hardcoded `21 + i` is right for
this export but would misread any export with a different surplus just as silently.

### Fix (validation/probes/diff_values.py, validation/probes/merge_runs.py)
- Every ORIG bar row is aligned by its own surplus, `shift = len(row) - len(header)`; a header
  column X is read at `header.index(X) + shift` (no fixed indices anywhere; databox names are
  taken from the header and must equal `ORIG_DATABOX` in order, else abort exit 3).
- Two independent per-row alignment checks: header column `Price` must equal the shifted
  `Close`, and the field just before the shifted `Open` must be empty. Any failing row, or more
  than one shift value across rows, aborts with exit 3 (`--allow-mixed-shift` overrides only the
  latter). The detected layout is always printed (`--inspect ORIG_CSV` prints it without a harness).
- Join key is `(BarTime, k)`, k = ordinal of the row inside its same-BarTime group, in both
  `diff_values.py` (ORIG vs harness) and `merge_runs.py` (QIV_* across modules). Harness `Bar`
  (CurrentBar) must be strictly increasing along the joined rows and O/H/L/C/V must agree on every
  joined row, else exit 4 before any claim is compared.

### Evidence — layout report on the real export (verbatim, `--inspect`)
```
ORIG layout report
  header fields=53  bar rows=358038  signal rows skipped=209870
  surplus fields per bar row = +1 on 358038 rows -> Open..Volume at 15..19, ATR14 at 20, databox_* at 21..53
  alignment checks (Price == shifted Close; field before shifted Open empty): 358038 ok, 0 bad
  appended runs (BarTime went backwards)=1; (BarTime,k) keys overwritten by a later run=0
  same-BarTime groups: 27637 bars in 11855 groups of >=2 (largest 14); a BarTime-only join would drop 15782 bars -> keyed by (BarTime,k)
```
So the whole file (not only the first 20,000 lines) has exactly one surplus field per bar row,
contains a single chart run (no append-mode duplicates in this export), and 15,782 bars would
have been dropped by the former "LAST row per BarTime" policy.

### Self-test of the probe (fixtures built from the export itself; NOT a Channel B result)
Harness-shaped files for the first 30,000 bar rows (18,783 interleaved signal rows), QI_* columns
copied from the ORIG databox values (C27 +100 applied):
- `good.csv` (databox read at header index + shift): joined 29,950 bars (Bar ≥ 50) including all
  1,685 same-second bars, Bar monotonic, O/H/L/C/V mismatches 0, **all 28 claim rows 0 mismatches**, exit 0.
- `wrong.csv` (databox read one column to the left, the original bug): every claim row MISMATCH,
  first rows verbatim:
```
C18    IBS            QI_IBS.Values[0]                   29950    29950   59.81750  2025-02-04 18:00:03#0 orig=0.9268 new=25.8501 bar=50  <-- MISMATCH
C19    RSI2           QI_RSI2.Values[0]                  29950    29950   99.84870  2025-02-04 18:00:03#0 orig=41.7906 new=0.9268 bar=50  <-- MISMATCH
C32    HPScore        QI_HedgingPressure.Values[0]       29950    29950   59.55410  2025-02-04 18:00:03#0 orig=25.8501 new=1.47 bar=50  <-- MISMATCH
```
  (`new` for IBS is the real HPScore, for RSI2 the real IBS, for HPScore the real ATR14 — the
  one-left chain described in channel-b-algo.md §5 item 2.) exit 1.
- ORIG slice with ONE bar row's surplus field removed: report shows `+0 on 1 rows` and
  `+1 on 29999 rows`, abort exit 3. ORIG slice with `databox_IBS` renamed: abort exit 3.
- `merge_runs.py` on three synthetic qiv_* files with same-second groups of 3 and 2 bars:
  8 of 8 bars kept in Bar order, 0 Bar disagreements (the old `drop_duplicates("BarTime")`
  would have kept 5).
- `pytest validation/pytests/test_data_integrity.py`: 7 passed, 13 skipped (no harness), 2 xfailed
  (the strict layout/tick-duplicate xfails) — unchanged.

### Decision — join on BarTime vs positional join (item 3 of the task)
A BarTime-only join is **not acceptable on tick charts**: 4.4 % of this export's bars share a
second with their predecessor (groups up to 14 bars) and "last row wins" silently discards the
rest. ORIG cannot be changed (originals untouched, channel-b-auto.md §6) and it logs no
CurrentBar; the harness already logs CurrentBar as `Bar`. Both files are in chart order, so the
ordinal inside each same-second group is a positional join that needs no new column, and
`Bar` monotonicity plus O/H/L/C/V equality on every joined row prove the pairing (exit 4
otherwise). Residual risk: if the harness chart loads a different bar range than ORIG's run so
that a same-second group is truncated at the start of the shorter load, k would misalign for
that group — the O/H/L/C/V sanity check catches it; the remedy is to load the same range. On
Minute charts k is always 0 and the key degenerates to BarTime.


## C45 — transparent overlay plots do not stretch the price auto-scale (ADD-4)
Probe: screenshot of the live MES DEC26 60-minute chart, 2026-10-16 12:29 local, after the overlay
recompile (`validation/runs/captures/capture_20261016_1229_MES60.jpg`). On the price panel:
QI_EMACross, QI_LiquiditySweep, QI_OrderFlowPlus, QI_SMC (their Confidence 0..1 and Structure ±1
plots are transparent). Observed price axis 7720–7880 for candles ranging ~7715–7885; no 0 or ±1
level pulled into view; labels render on the bars; no sub-panel for those modules. Panels present:
QI_ATRRegime (1.5 line), QI_ChopIndex (CAUTION 1/3 text), QI_IBS (0.2/0.8 lines, daily-series step).
Verdict: **CONFIRMED** for the four modules on screen. Not yet observed: QI_HedgingPressure (score
−100..100), QI_BollingerPctB (%B ±100), QI_VWAPDistance, QI_TurnOfMonth, QI_TurnaroundTuesday — those
remain pending a chart that includes them. Falsifier: a panel module's plot made overlay+visible
would widen the axis; not executed (would require a code change on the live chart).
