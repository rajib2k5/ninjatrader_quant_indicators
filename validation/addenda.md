# Ledger addenda (items raised after the freeze; each runs through both channels fresh)

## ADD-1 (2026-10-15) — C41 fix
Channel A (channel-a-fidelity-2.md) found QI_LiquiditySweep wrote `Values[0]/[1]` on Start labels
(QI 725-726) while ORIG wrote `Values[24]` only on End events (ORIG 2373-2385). The deviation came
from the orchestrator's CONVENTIONS spec, not from ORIG. Fix applied before any NinjaTrader run:
`if (!isStart) { Values[0][0] = confidence; Values[1][0] = direction; }`. Labels unchanged.
Fresh claim C41.1: "after the fix, QI_LiquiditySweep's Confidence equals ORIG Values[24] bar-for-bar
(no start-only extras)". A: static re-read of the edited lines. B: diff_values.py C41 row must show
0 mismatches AND 0 start-only events.

## ADD-2 (2026-10-15) — C27 deliberate deviation (user decision)
Channel A (channel-a-api.md, C7 side note → C27) found ORIG 1354 `double bollMid = boll[0];` resolves to
Bollinger.Values[0] = Upper (@Bollinger.cs:76), so ORIG's "%B" = (Close-Upper)/half-width*100. The user chose
to ship true %B. QI_BollingerPctB now uses `boll.Middle[0]`. C27 is re-scoped as C27.1: "QI_BollingerPctB
value equals ORIG Values[10] + 100 on every bar ≥ 50 where bandwidth > 0, and 0 where ORIG is 0".
A: static re-read. B: diff_values.py applies the +100 offset for C27 and must show 0 mismatches.

## ADD-3 (2026-10-15) — D0 intraday warm-up gate: documented deviation (user decision)
Channel A (channel-a-fidelity-1.md: C20, C23, C25 REFUTED on intraday charts; channel-a-fidelity-2.md: D0)
established that ORIG 537 gates on `CurrentBars[1] < 1` as well as bar 50 on intraday charts. The user chose
not to add a daily series to the stateful standalone modules. Scope change recorded, not a claim rewrite:
C20/C23/C25 remain REJECTED-on-intraday as audited; the accepted engineering claim is the documented one
("daily charts match exactly; intraday differs for ≈ the oldest session then converges"). Headers of
QI_ConnorsRSI, QI_ConsecDays, QI_CompositeVol, QI_VolumeDelta and README "Known quirks" updated.
B runtime check: diff_values.py on the 5-min chart must show the C20/C23/C25 mismatches confined to the
start of the series (first-mismatch bar reported) and zero mismatches on the daily chart.

## ADD-4 (2026-10-16) — presentation re-assessment (user request after first chart review)
On a live chart the user found modules rendering in two places (price labels/lines AND a sub-panel
repeating the same information as bars) and the per-panel disclaimer text eating space. Changes
(presentation only; no formula, guard or event logic touched):
- Converted to IsOverlay = true with the computed values as `Brushes.Transparent` plots
  (`ShowTransparentPlotsInDataBox = true`, the original's own technique): QI_HedgingPressure
  (score; HP price lines + text panel unchanged), QI_LiquiditySweep / QI_OrderFlowPlus / QI_SMC
  (Confidence, Structure), QI_VWAPDistance (now plots the VWAP level on price as Values[0] when
  intraday and live; distance moved to Values[1]), QI_BollingerPctB (now plots Upper/Middle/Lower on
  price as Values[0..2]; %B moved to Values[3]), QI_TurnOfMonth / QI_TurnaroundTuesday (shading only).
- Removed the AddLine reference lines and their LowerThreshold/UpperThreshold properties from the
  converted modules (lines at ±35 / ±100 / ±0.5 would be drawn on the price scale).
- `ShowDisclaimer` default changed from true to false in all 27 files (header, Description,
  README and DISCLAIMER.md still carry the disclaimer). C16's third element is re-scoped to
  "a ShowDisclaimer property exists"; its B probe becomes `ShowDisclaimer\s*=\s*false;` == 1.
Ledger consequences: C4 (DrawOnPricePanel) is now moot for the converted modules; C27 and C33
harness columns are `QI_BollingerPctB.PctB` and `QI_VWAPDistance.VwapDistance` (diff_values.py
updated). New runtime claim C45 (material): "transparent overlay plots with non-price values
(HP score, confidence, %B, flags) do not stretch the price panel's auto-scale" — falsifier: the
price panel's visible range widens to include 0 / ±100 when such a module is added. B probe:
screenshot of the price panel before/after adding QI_HedgingPressure and QI_BollingerPctB.
Harness regenerated; all 28 files recompiled with compile_probe.sh after the change.

## ADD-5 (2026-10-16) — harness redesign (hosting refused by NinjaTrader) and diff offset bug
NinjaTrader's trace (2026-10-16 09:23:46) logged, for every module hosted by QI_EgvDump: "'QI_X' tried to
load additional data. All data must first be loaded by the hosting NinjaScript in its configure state."
The hosted harness therefore wrote header-only CSVs (0 rows) and every runtime differential so far is
PROBE_INVALID, not evidence. Replacement: validation/harness/QIV_<Module>.cs — one subclass per module
(`QIV_X : QI_X`) running the real compiled code as an ordinary chart indicator and appending its own
values per bar; validation/probes/merge_runs.py joins the 27 files into qi_dump_<INSTR>_<PERIOD>.csv
(the shape pytests/test_integration_harness.py and diff_values.py expect). All 54 files compile together
(compile_probe rc=0). Separately, pytests/test_data_integrity.py found that the ORIGINAL's EveryBar rows
have 54 fields vs a 53-field header, so diff_values.py's column offsets were one too low; fixed
(OHLCV 15-19, databox 21-53). Claims C18-C43 and all (b) halves of the algorithm ledger remain
pending a populated run.

## ADD-6 (2026-10-16) — diff_values.py probe defect: ORIG column shift and tick-chart join key
Channel B (channel-b-algo.md §5 items 2–3) found that the ORIG EveryBar bar rows carry one surplus
field against the 53-field header, so `diff_values.py`'s fixed-position read `r[20 + i]` compared every
C18–C43 harness column against the ORIG column one to the LEFT, and that 150-tick bars share 1-second
BarTimes, so its "LAST row per BarTime" join dropped real bars. No recorded verdict was affected
(C18–C43 were never run: no populated harness CSV exists). Fix: per-row alignment by
`len(row) - len(header)` with two independent per-row checks and a loud layout report/abort;
`(BarTime, k)` positional join inside same-second groups in `diff_values.py` and `merge_runs.py`,
with Bar monotonicity and O/H/L/C/V equality as pairing proof. Self-tests and the whole-file layout
report are in channel-b-runtime.md (2026-10-16 addendum). Fresh claim P1 (supersedes the ADD-5 note on the diff offset): "diff_values.py on a
populated 150-tick qi_dump reports 0 O/H/L/C/V mismatches and joins every harness bar ≥ 50 that
ORIG logged". A: static re-read of the loader. B: the sanity line and the joined count printed by
the first real run.


## ADD-6 (2026-10-16) — algorithm-definition decisions (user) after channel-a-algo-1/2
- M3 ConnorsRSI: keep the original's RSI(2)/streak-carry (not Connors' published RSI(3)/reset) — documented.
- M16 VWAP: CHANGED to reset on Bars.IsFirstBarOfSession (official session semantics); the module now
  exports a SessionStart series (1 on the first bar of a session) so qi_ref.vwap can replay the reset;
  test_integration_harness compares VWAP from the first session start after the bar-50 gate. New API
  claim C46 (material): "Bars.IsFirstBarOfSession is a readable bool in OnBarUpdate on NT 8.1.8.3" —
  A: help guide; B: compile + the exported flag has exactly one 1 per session on the 5-min chart.
  The port-fidelity claim C33 is now expected to show mismatches on the first bars after each
  midnight/session (deliberate); the ORIG differential for C33 is re-scoped to "equal except in
  bars between a calendar-midnight and the next session start".
- M15 Hedging Pressure: name kept; header states it is a price/volume composite, not Basu & Miffre's COT measure.
- M7 Turn-of-Month: calendar-day window kept; header states the literature uses trading days.
- All other definition findings documented as "Provenance" header lines (17 files) and in README.

## ADD-7 (2026-10-17) — backtest wave findings
- DuplicateBarWindow: the pattern ports reproduce ORIG exactly only at window 6 — the user's
  original charts ran with 6, while the code default (ORIG and QI) is 5. The ranking uses the
  shipped QI default 5 (it ranks the indicators as shipped); PT2-PT4 are confirmed at 6, which
  validates the port's logic, the window being a parameter. Recorded, no protocol change.
- BT17 data fact: P1 has no bars for 2023-04-06 -> 2023-04-14 (7 weekdays incl. Good Friday).
  No synthetic bars; a position held across the gap is marked open-to-open across it, as §4 says.
- DSR = 0.000 for all 25 rules: V[SR] (per §7, across the 25 trials) is dominated by the 15m
  rules' large negative SRs, so SR0 ≈ 0.469/day (≈ 7.4 annualised). Reported as is.
- Robustness downloads R1/R3 (Stooq) are blocked by a bot-verification page; not bypassed.
- Side effect to disclose: the engine agent ran `python -s -m pip install -e backtest`
  (package `qibt`, editable; undo with `python -m pip uninstall qibt`).

## ADD-8 (2026-10-17) — Channel B backtest findings acted on
- metrics: Φ via 0.5·(1+erf) underflowed to 0 for z < −8.26, so all DSRs printed 0 and the §8 tie
  rule fell back to A→Z; fixed to erfc/log-tail. On v1 the corrected tie rule puts IBS 3rd,
  ConsecDays 4th (DSR 3.3e-58 vs 1.7e-59). This is a bug fix, not a protocol change.
- engine: the change executed at the last bar's open was not charged; fixed per §5.
- BT17 REFUTED (data): no rows 2023-04-05 13:03 → 2023-04-16 17:01 (7 weekdays), 3 more missing
  weekdays and six one-bar sessions at the file seams. Kept as is (§3: no synthetic bars) and disclosed.
- BT4 note: P1 shows CME's former 15:15–15:30 CT pause until ~June 2021 (real market structure).
- BT6 note: the pre-registered 3×-median-range threshold would miss a 14-point roll jump; the
  tick-grid check (0 of 8.57M OHLC values off grid) is the stronger evidence for additive adjustment.

## ADD-9 (2026-10-17) — Channel A backtest findings acted on
- A1.1: settlement-close grid tolerance = 4-decimal IBS rounding bound 0.00005·(H−L) (PROTOCOL §9);
  verified by main on all 1,578 dates: 7 dates change vs the fixed 0.01, 3 in the window; final A1.1
  ranking reproduces the validator's NinjaTrader-daily numbers (ConsecDays 0.883, RSI14 0.656, RSI2 0.632).
- BT10/BT11: the papers' numeric examples (Channel A) added as backtest/tests/test_paper_examples.py;
  engine reproduces DSR 0.9004 / 0.9505 and PSR 0.982 / 0.913 / 0.953 (7 passed).
- BT16: Channel A showed a realtime-only guard is insufficient (orders on the last historical bar carry
  into real time; account-sync start behaviours). Generator now emits OrdersAllowed(): historical only,
  Backtest/Sim*/Playback* accounts only, not on the last two historical bars of a non-Backtest
  account; Configure forces StartBehavior.WaitUntilFlat when BacktestOnly. Static tests 180 passed;
  falsifier (account check removed) fails; compile rc=0.
- BT3: default routing all-in per side Free 0.94 / Monthly 0.84 / Lifetime 0.64 (<= 1.00 assumed);
  Rithmic/CQG routing adds 0.25 -> Free 1.19 / Monthly 1.09 (> 1.00): covered by the 2x-cost
  sensitivity, disclosed in the README.
- A2: rules.yaml header wording (frame rule) corrected; holiday trade-date limitation documented.

## ADD-10 (2026-10-18) — backtest ConnorsRSI now matches the shipped indicator
The per-indicator tests (tests/indicators/test_ConnorsRSI.py) found that qi_ref.connors_rsi ranks
PERCENT one-bar changes (Connors' published form) while QI_13_ConnorsRSI.cs (as ORIG 1283-1292)
ranks POINT changes Close[0] - Close[1]. The backtest evaluates indicators as shipped, so
qibt.signals now uses v_connors_rsi (point-change rank; price/streak legs and warm-up unchanged).
qi_ref keeps the published form. Effect on P1 (A1.1): ConnorsRSI SR 0.003 -> 0.029, rank 13
unchanged (HedgingPressure 0.031 is within the 0.005 tie band; DSR decides as before); no rank
changed anywhere; bootstrap identical. All result variants regenerated. Tests:
backtest/tests/test_signals.py (point-rank hand case + falsifier on a level-shift series).
Other per-indicator findings recorded as strict xfails (no backtest effect in the window):
VWAP zero-volume session-start fallback (C#: Close; qi_ref: typical price), OvernightGap bar 0
(C#: 0; qi_ref: NaN), SMA200Trend distance before bar 200 (C#: 0; qi_ref: NaN), ChopIndex state
(qi_ref count 0-3 vs C# flag 0/0.5/1, mapped in the export test).

## ADD-11 (2026-10-18) — robustness run on R1 (Stooq SPY.US daily), per PROTOCOL A3
Input: spy_us_d.csv, sha256 f48ac8eb…3475b6, 5,444 rows 2005-02-25 → 2026-10-16, downloaded by the user
in a browser (Stooq refused CSV requests driven by the Chrome extension with "Access denied"); raw file
in the private repo rajib2k5/ninjatrader_quant_data (byte-for-byte, manifest verified on a fresh clone).
R3 (es_f_d.csv) not downloaded; the runner now runs whatever input exists and reports the rest
(tests: test_runs_with_only_the_spy_file_and_reports_the_missing_one + falsifier).
Result (results/robustness/ROBUSTNESS.md): Spearman vs P1 order 0.631 on the P1 window, 0.166 on the
full 2006-05-05 → 2026-10-16 window; SPY buy-and-hold SR 0.824 / 0.657 beats every rule in both.
Labels unchanged (§2: robustness never changes the ranking); README states the order is
period-specific.

## ADD-12 (2026-10-19) — R3 (Stooq ES.F daily) unavailable
Stooq's ES.F history page (https://stooq.com/q/d/?s=es.f) shows the table but has no "Download data in
csv file" link (the SPY.US page has one), and the direct CSV address https://stooq.com/q/d/l/?s=es.f&i=d
is refused both when driven by the Chrome extension ("Access denied") and when the user opens it in
their own browser. R3 and R3_unfiltered are therefore not run; robustness rests on R1 (ADD-11). No
substitute source was adopted: NinjaTrader's own ES daily data is not independent of P1, and Yahoo
Finance was rejected in docs/DATASETS.md on licence grounds. The runner needs no change if an ES.F CSV
appears later (it runs whichever inputs exist).
