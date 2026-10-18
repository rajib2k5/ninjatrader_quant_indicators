# Channel A: static audit of patterns.py against the QI NinjaScript modules (PT1-PT4)

date: 2026-10-17. channel: A (static source auditor). method: side-by-side reading only. Nothing was executed.
frozen inputs (`scratchpad\pt_channel_a\`): `patterns.py`, `QI_HedgingPressure.cs`, `QI_LiquiditySweep.cs`,
`QI_OrderFlowPlus.cs`, `QI_SMC.cs`, `ORIG_IBSFade.cs`. All line numbers refer to these frozen copies.
not read (per the charter): any `channel-b*.md`, any test file, and `validation/pytests/qi_ref.py`. `patterns.py` imports
`atr()` from that file, but the file is outside the frozen set and sits in the pytests folder.
quoting: fragments are verbatim. Runs of tabs or spaces are collapsed to one space. In tables, `\|` is a literal `|`.
verdict rule (charter): CONFIRMED means no value-changing difference between the port and the QI module. REFUTED means
at least one. UNVERIFIABLE means reading cannot decide.

## Summary

| Claim | Verdict (port vs QI) | Value-changing differences found | Conditional (reading cannot decide) | Not value-changing | QI vs ORIG value-changing |
|---|---|---|---|---|---|
| PT1 `hp_score` | CONFIRMED | 0 | R1 ATR, R2 SMA | 3 | 0 on bars both write (A1 changes only which bars exist) |
| PT2 `liquidity_sweep` End | CONFIRMED | 0 | D2.1 time zone (R3); R1, R2 | 8 | 1 (A1 start gate) |
| PT3 `order_flow_plus` | CONFIRMED (bars 50-58: UNVERIFIABLE) | 0 | D3.1 Series default (R4); R1, R2 | 4 | 1 (A1) |
| PT4 `smc` | CONFIRMED | 0 | R1 | 5 | 1 (A1) |

The ledger words PT1-PT4 against the **ORIG DataBox values on P1**. The charter verdict above is against the **QI modules**.
Section 0.2 (A1) and section 0.3 (A2) show why a comparison against ORIG on P1 should give mismatches on the leading
rows after every ORIG run start. The port's code does not cause these mismatches. They come from where ORIG starts
processing and where its CSV rows start.

---

## 0. Cross-cutting findings

### 0.1 NT runtime semantics the port relies on (residuals R1-R5)

- **R1 ATR(14)** (all four claims). port 121-124 `def nt_atr(df, period=14):` ...
  `return qi_ref.atr(df[["High", "Low", "Close"]].reset_index(drop=True), period).to_numpy(dtype=float)`.
  The docstring (port 122-123) states `ATR[0] = H-L; ATR[t] = ((min(t+1,P)-1)*ATR[t-1] + TR[t]) / min(t+1,P)`. This is
  the NT8 @ATR.cs recursion. The code lives in `qi_ref.py`, which I did not read. Decided by: ledger B4 evidence on
  `qi_ref.atr`, or a reading of `qi_ref.py`.
- **R2 SMA** (PT1: SMA(C,20), SMA(C,5), SMA(Range,20), SMA(V,20); PT2: SMA(V,20), SMA(ATR,50); PT3: SMA(V,20)).
  port 116-117 `s = s + xl[t] - (xl[t - period] if t >= period else 0)` /
  `out[t] = s / (t + 1 if t < period else period)`. This is the NT8 @SMA.cs branch for bar types with
  IsRemoveLastBarSupported = false (`sum = priorSum + Input[0] - (CurrentBar >= Period ? Input[Period] : 0)`,
  `Value[0] = sum / (CurrentBar < Period ? CurrentBar + 1 : Period)`), with the same operation order. Both languages use
  IEEE binary64, so the values are bit-identical given identical inputs. @SMA.cs is not in the frozen set. The branch
  choice for Minute bars agrees with my knowledge of NT8, but the frozen files cannot prove it. The other branch is
  mathematically equal and differs only by about 1e-13 relative rounding. If the branch were wrong, PT1 within 1e-3
  would not change; an event claim could change only at an exact threshold tie.
- **R3 time zone** (PT2 only): see D2.1.
- **R4 unset `Series<double>` slots** (PT3 only): see D3.1.
- **R5 `int.MaxValue` `++`.** port 93-95 `_inc32` wraps to int.MinValue, as unchecked C# does (the default). This
  cannot change an output. Each `barsSince*` counter is used only in `dir == lastDir && barsSince < DuplicateBarWindow`,
  and `lastDir` is 0 until the first event, which also resets the counter to 0. Not value-changing.

### 0.2 A1: QI modules vs ORIG, start gate on intraday charts (value-changing for PT2-PT4)

- ORIG 325-327: `useDailySeries = Bars.BarsType.IsIntraday;` `if (useDailySeries)` `AddDataSeries(Data.BarsPeriodType.Day, 1);`
- ORIG 535-538: `if (useDailySeries)` `{` `if (CurrentBars[0] < 50 || CurrentBars[1] < 1)` `return;`
- QI, all four: `if (CurrentBar < 50)` `return;` (HP 137-138, LS 248-249, OF 158-159, SMC 178-179). The port uses the same
  gate: `for t in range(50, n)` (port 198, 287, 630, 794).

On 1-minute bars ORIG runs its multi-series branch. It processes nothing until the added daily series has closed its
second bar. On the same chart, ORIG therefore starts later than the QI modules and the port. In NT8 historical
processing this is typically about two sessions later. That timing comes from NT8 behaviour, not from these files.
- **HP:** stateless apart from the NT child indicators, which run from bar 0 in both. So bars that both write are
  identical. A1 changes only which bars have an ORIG value.
- **LS/OF/SMC:** all carried state starts later in ORIG. That state is the swing levels, the eq pool, the consolidation
  zone, the pending sweep, lastDir/barsSince, the OB/FVG lists, smcTrendDir and lastBosBar. **First differing
  condition:** QI confirms a swing high or low before ORIG's first processed bar. QI then holds
  `lastSwingHigh > double.MinValue` while ORIG still holds the sentinel. From that point SFP, Liq Sweep, VolDiv,
  DeltaDiv, Exhaustion, BOS and CHoCH can differ. The difference lasts until both have confirmed new swings, both have
  exited and re-entered consolidation, the zones have expired (50, 100 or 200 bars), and an event has reset the dup
  counters.

The rest of ORIG matches QI textually (details in each section). I grepped every assignment to the shared fields
(swings, key levels, volDelta, pending, consolidation, all dup counters, smcTrendDir, lastBosBar). They occur only at ORIG
372-461 (init), 696-788 (key levels), 2041-2087, 2111-2172, 2306-2313, 2423-2540 and 2551-2738. No other ORIG code
inside the same OnBarUpdate (ProcessBar, UpdateNewAlphas, UpdateDataBoxValues) writes state that these modules read.

### 0.3 A2: P1 row 0 is not NT bar 0 if P1 is ORIG's CSV (value-changing vs ORIG on P1, at the data level)

- port 15-16: `Row position t is NinjaTrader's CurrentBar; "x[k]" in the C#` / `(k bars ago) is row t-k here.`
- ORIG 596-597: `if (CsvLogMode == CsvLogModeEnum.EveryBar)` `LogEveryBarToCsv();`. This runs only after the gate at
  ORIG 537.
- Ledger lines 33-34: the P1 files carry ORIG's per-bar `databox_HPScore`, `databox_LiqSweep`, `databox_OFSignal` and
  `databox_SMCSignal`. These are the column names in ORIG's header at 511.

If P1 rows are ORIG EveryBar rows, then P1 row 0 is NT CurrentBar >= 50, and NT has bars before that row that P1 does
not contain. When the port runs on P1, it seeds at P1 row 0 while ORIG has more history:
- **PT1:** the port seeds ATR at P1 row 0 (`H-L`, then `min(t+1,14)` averaging); NT seeds it at NT bar 0. The gap
  shrinks by 13/14 per bar from row 13: x0.064 at row 50, about x1e-4 near row 137, about x1e-6 near row 200.
  |dHP| is about (|basis| + |term|) x the relative ATR error (at most 50 x the error), plus a possible vp jump when
  `priceChangePct` crosses 0.5. With an initial gap of 10-30% of ATR, I expect PT1's 1e-3 tolerance to fail on rows
  50 to about 200 after each ORIG run start. This is an estimate; nothing was executed. The SMA terms are exact after
  20 rows.
- **PT2-PT4:** ORIG can fire on P1 rows 0-49, which the port never evaluates (NaN). At P1 row 0, ORIG's swing test
  already looks back 40 NT bars that are not in P1. The warm-up of ATR, SMA(V,20) and SMA(ATR,50) also differs. All
  carried state then starts at different points, as in A1.
- **PT3:** the port reads volDelta 0.0 for rows below 50 (port 622). ORIG has real volDelta for P1 rows 0-49. So
  cumD10 differs at P1 rows 50-58.

Reading cannot decide how P1 was assembled. It could be one ORIG run, or several runs concatenated and de-duplicated
(BT17 mentions de-duplication). The loader is not in the frozen set. ORIG opens its CSV in append mode:
ORIG 505-506 `bool writeHeader = !File.Exists(csvFilePath);` `csvWriter = new StreamWriter(csvFilePath, true);`. Every
run start or splice in P1 is a point where ORIG's state resets and the continuously running port's state does not.
Decided by: an inventory of the P1 source files, plus Channel B reporting mismatches binned by distance from each ORIG
run start.

### 0.4 What ORIG's CSV can and cannot show

- The DataBox columns are written with F4: ORIG 2803 `row += "," + Values[i][0].ToString("F4");`. HP rounding is at
  most 5e-5, inside PT1's 1e-3. ORIG writes OHLC with F2 and Volume with F0 (2796-2799). This is lossless for MES
  (tick 0.25).
- The ORIG DataBox carries **confidence only**, with no direction: LS `Values[24][0] = confidence;` (2385), OF
  `Values[27][0] = bestConf;` (2529), SMC `Values[29][0] = bestConf;` (2726). The QI modules and the port add a separate
  Structure plot. So the `*_structure` half of PT2-PT4 **cannot** be checked against the `databox_*` columns. Direction
  exists only on the signal rows: `LiqSweepEnd` with `"Bullish"/"Bearish"` (2362-2363), and `"OrderFlow+"` / `"SMC"`
  with `"Buy"/"Sell"` (2535, 2733). Signal-row confidence is written with F2 (1663).
- ORIG writes the signal rows (1657-1668: 20 columns, no databox fields) into the same file during the bar, before that
  bar's EveryBar row. A loader that de-duplicates by BarTime must keep the EveryBar row.
- One bar can carry two LS End events: the pending-confirmation End at 0.55 (ORIG 2171), then an End from the checks
  in the opposite direction (2085). A same-direction End is blocked by the barsSince reset. `Values[24]` holds the last
  of the two, and so does port `conf[t]` (port 391, then 573). port `liquidity_sweep_events` lists both, as ORIG's
  signal rows do. This is not a difference, but a per-bar vs per-event comparison must allow for it.

### 0.5 ORIG run settings are not in any frozen input

The port uses the C# defaults: SwingLookback 20, SweepWickMultiple 2.0, SweepVolMultiple 1.5, EqualLevelTolerance 0.05,
ConsolidationAtrRatio 0.6, all levels on, DuplicateBarWindow 5. These equal the QI defaults (LS 156-170, OF 109-114,
SMC 126-131) and the ORIG defaults (ORIG 259, 268, 271-273, 298-303, 308, 313). The settings of the ORIG instance that
produced P1 are unknown. In ORIG, several toggles with display-style names also gate logic:
- `ShowPrevDayLevels` / `ShowMonthlyLevels` / `ShowOrbLevels` (661-668, 2192/2201/2210).
- `EnableLiquiditySweep` (586-587). This also drives the OF and SMC swing updates.
- `EnableHedgingPressure` (562-567). When it is false, HP = 0.

Decided by: the chart template or workspace used for the export run.

---

## PT1: `hp_score` (port 186-232) vs QI_HedgingPressure (QI 123-196); ORIG 1015-1059

Term-by-term comparison (every row is equal):

| Item | QI | port |
|---|---|---|
| warm-up gate | 137 `if (CurrentBar < 50)` 138 `return;` | 198 `for t in range(50, n):` |
| inputs | 123 `atr14 = ATR(14);` 124 `volSma20 = SMA(Volume, 20);` 127 `sma20hp = SMA(Close, 20);` 128 `closeSma5 = SMA(Close, 5);` 129 `closeSma20 = SMA(Close, 20);` 130 `rangeSma20 = SMA(Range(), 20);` | 191 `atr = nt_atr(df, 14).tolist()` 192 `sma20 = nt_sma(C, 20).tolist()` 193 `sma5 = nt_sma(C, 5).tolist()` 194 `rsma20 = nt_sma(H - L, 20).tolist()` 195 `vsma20 = nt_sma(V, 20).tolist()` |
| guard | 154 `if (atr14[0] <= 0 \|\| sma20hp[0] <= 0)` 155 `return 0;` | 201 `if a <= 0 or s20 <= 0:` 202 `out[t] = 0.0` |
| basis | 157 `double basisDev = (Close[0] - sma20hp[0]) / atr14[0];` 158 `double basisScore = Clamp(basisDev * -25.0, -25, 25);` | 206 `basis_dev = (c - s20) / a` 207 `basis_score = _clamp(basis_dev * -25.0, -25.0, 25.0)` |
| short slope | 160 `double shortSlope = (closeSma5[0] > 0 && CurrentBar > 5)` 161 `? (closeSma5[0] - closeSma5[1]) / atr14[0] : 0;` | 209 `short_slope = (sma5[t] - sma5[t - 1]) / a if (sma5[t] > 0 and t > 5) else 0.0` |
| long slope | 162 `double longSlope = (closeSma20[0] > 0 && CurrentBar > 20)` 163 `? (closeSma20[0] - closeSma20[1]) / atr14[0] : 0;` | 210 `long_slope = (s20 - sma20[t - 1]) / a if (s20 > 0 and t > 20) else 0.0` |
| term | 164 `double slopeDiff = shortSlope - longSlope;` 165 `double termScore = Clamp(slopeDiff * -50.0, -25, 25);` | 211 `slope_diff = short_slope - long_slope` 212 `term_score = _clamp(slope_diff * -50.0, -25.0, 25.0)` |
| price change | 167 `double priceChangePct = (atr14[0] > 0)` 168 `? Math.Abs(Close[0] - Open[0]) / atr14[0] : 1.0;` | 214 `price_change_pct = abs(c - o) / a if a > 0 else 1.0` |
| vol ratio | 169 `double volRatio = (volSma20[0] > 0) ? Volume[0] / volSma20[0] : 1.0;` | 215 `vs = vsma20[t]` 216 `vol_ratio = Vl[t] / vs if vs > 0 else 1.0` |
| vp | 171 `if (volRatio > 1.2 && priceChangePct < 0.5)` 173 `double direction = (Close[0] < Open[0]) ? -1.0 : 1.0;` 174 `vpDivergence = direction * volRatio * 10.0;` 176 `double vpScore = Clamp(vpDivergence, -25, 25);` | 218 `if vol_ratio > 1.2 and price_change_pct < 0.5:` 219 `direction = -1.0 if c < o else 1.0` 220 `vp_div = direction * vol_ratio * 10.0` 221 `vp_score = _clamp(vp_div, -25.0, 25.0)` |
| range ratio | 178 `double rangeRatio = (rangeSma20[0] > 0)` 179 `? (High[0] - Low[0]) / rangeSma20[0] : 1.0;` | 223 `rs = rsma20[t]` 224 `range_ratio = (Hl[t] - Ll[t]) / rs if rs > 0 else 1.0` |
| rc | 181 `if (rangeRatio < 0.6 && volRatio > 1.3)` 183 `double direction = (Close[0] < sma20hp[0]) ? -1.0 : 1.0;` 184 `rcScore = Clamp(direction * (1.0 - rangeRatio) * 50.0, -25, 25);` | 226 `if range_ratio < 0.6 and vol_ratio > 1.3:` 227 `direction = -1.0 if c < s20 else 1.0` 228 `rc_score = _clamp(direction * (1.0 - range_ratio) * 50.0, -25.0, 25.0)` |
| composite | 187 `double composite = basisScore + termScore + vpScore + rcScore;` 188 `return Clamp(composite, -100, 100);` | 230 `composite = basis_score + term_score + vp_score + rc_score` 231 `out[t] = _clamp(composite, -100.0, 100.0)` |
| Clamp | 193 `if (value < min) return min;` 194 `if (value > max) return max;` | 167-170 `if v < lo:` `return lo` `if v > hi:` `return hi` |

Every expression has the same operation order, and both languages use IEEE binary64. So given identical ATR and SMA
inputs (R1, R2), the score is bit-identical. Bar indexing is `closeSma5[1]` -> `sma5[t - 1]` and `closeSma20[1]` ->
`sma20[t - 1]`, with no off-by-one. No state is carried across bars except inside the NT indicators. No dup window
affects `Values[0]`.

Differences recorded:

| # | QI | port | Class |
|---|---|---|---|
| D1.1 | 127 `sma20hp = SMA(Close, 20);` and 129 `closeSma20 = SMA(Close, 20);` (two instances) | 192 `sma20 = nt_sma(C, 20).tolist()        # sma20hp == closeSma20 (same NT cached SMA(Close,20))` (one array) | Not value-changing: same input, same period, deterministic. |
| D1.2 | 137-138: bars < 50 are not written | 197 `out = [float("nan")] * n` | Not value-changing for the claim (bar >= 50). |
| D1.3 | 141 `hpScoreSeries[0] = hpScore;` 144 `ProcessHpZone(hpScore);` | not ported | Not value-changing: only DrawHpTimeframeLines reads `hpScoreSeries` (237, 248), and ProcessHpZone only draws. |
| D1.4 | 123 `atr14 = ATR(14);` (NT) | 124 `qi_ref.atr(...)` | Residual R1. Not decided here. |

**QI vs ORIG.** ORIG 1015-1052 is textually identical to QI 152-189, and ORIG 1054-1059 to QI 191-196. The indicator
construction is the same: ORIG 347 `atr14 = ATR(14);`, 358 `volSma20 = SMA(Volume, 20);`, and 363-366 match QI 123-130.
ORIG writes `Values[0][0] = hpScore;` (1263), with `hpScore` coming from 616/564. ORIG's HP dup suppression (1090) gates
only the label, not `Values[0]`. There is no value-changing difference on bars that both write. A1 only removes ORIG
bars. A2 (ATR seeding) is the expected source of PT1 mismatches against ORIG on P1.

**Verdict PT1: CONFIRMED.** 0 value-changing differences between the port and QI. Residuals: R1, R2.

---

## PT2: `liquidity_sweep` End events (port 238-580) vs QI_LiquiditySweep (QI 246-750); ORIG 656-808, 2038-2404

**OnBarUpdate order.**
- QI 248-258: `if (CurrentBar < 50)`, then `UpdateKeyLevels();`, `UpdateVolumeDelta();`, `Values[0][0] = 0;`,
  `Values[1][0] = 0;`, `DetectLiquiditySweeps();`.
- Inside DetectLiquiditySweeps (QI 428-475): the gate, `barsSinceLastSweep++;`, UpdateSwingPoints,
  UpdateConsolidationZone, UpdateDonchianChannel, CheckPendingSweepConfirmation, checks 1-7 (441-467), then the dup
  filter (469-475).
- port: loop at 287, key levels 294-329, `conf[t] = 0.0` / `struct[t] = 0.0` at 332-333, gate and counter 336-338,
  swings 341-363, consolidation 366-380, Donchian 383-384, pending 387-397, checks 408-566, dup filter 568-578.

The order is the same.

**Term-by-term comparison (every item is equal).**

Key levels:
- Weekend skip. QI 305-307 (prev day) and 365-367 (ORB): `if (cstTime.DayOfWeek == DayOfWeek.Saturday || cstTime.DayOfWeek == DayOfWeek.Sunday) return;`.
  port 294 `weekend = wday[t] >= 5`, 295 `if use_prev_day_levels and not weekend:`, 317
  `if use_orb_levels and not weekend:`. Monthly is not weekend-gated in either (QI 341-356, port 309-316).
- Day roll. QI 310 `if (cstTime.Date != todayRthDate)` and 313-315
  `if (todayRthStarted && todayRthHigh > double.MinValue && todayRthLow < double.MaxValue)`. port 296
  `if day[t] != today_date:` and 297 `if today_started and today_high > DBL_MIN and today_low < DBL_MAX:`. Resets:
  QI 323-326, port 300-302.
- RTH window. QI 413 `return t >= new TimeSpan(8, 30, 0) && t < new TimeSpan(16, 0, 0);`. port 303
  `if _T_0830 <= tod[t] < _T_1600:`.
- Month. QI 346 `if (barMonth != klCurrentMonth)`. port 310 `if month[t] != cur_month:`. Both update on every bar
  (QI 354-355, port 313-316).
- ORB. QI 370, 382-385, 389 `if (IsInOrbWindow(cstTime) && !orbComplete)`, and 396-399
  `if (!orbComplete && cstTime.Date == orbDate)` / `if (t >= new TimeSpan(9, 0, 0) && orbHigh > double.MinValue)`.
  port 318-321, 322 `if _T_0830 <= tod[t] < _T_0900 and not orb_complete:`, and 327-328
  `if not orb_complete and day[t] == orb_date:` / `if tod[t] >= _T_0900 and orb_high > DBL_MIN:`.

Gate and counter: QI 428 `if (CurrentBar < SwingLookback * 2 + 5) return;` and 429 `barsSinceLastSweep++;`. port 285
`gate = lb * 2 + 5` and 336-338.

Swings (QI 485-523; port 138-151, 341-363):
- Pivot. QI 485 `double candidateHigh = High[lb];` and 488
  `if (High[i] > candidateHigh) { isSwingHigh = false; break; }`. Strict `>` means a tie keeps the pivot. port 149
  `sh[2 * lb:] = H[lb:n - lb] >= mx`, over the window H[t-2lb..t] with candidate H[t-lb]. For lows, QI 506
  `if (Low[i] < candidateLow)` and port 150 `<= mn`. Equivalent.
- Equal levels. QI 492-493 `if (lastSwingHigh > double.MinValue && Math.Abs(candidateHigh - lastSwingHigh) < EqualLevelTolerance * 0.01 * candidateHigh)`.
  port 343 `if last_sh > DBL_MIN and abs(cand - last_sh) < eq_tol * 0.01 * cand:`. Lows: QI 510-511, port 353.
- Pool cap and add. QI 496 `if (eqPoolPrice.Count >= 10) { eqPoolPrice.RemoveAt(0); ... }` and 497
  `eqPoolPrice.Add(avgLvl); eqPoolBar.Add(CurrentBar); eqPoolIsHigh.Add(true);`. port 345-349
  `if len(pool_p) >= 10:` `del pool_p[0], pool_b[0], pool_hi[0]` `pool_p.append(avg)` `pool_b.append(t)`
  `pool_hi.append(True)`.
- Last level. QI 500 `lastSwingHigh = candidateHigh;`. port 350 `last_sh = cand`.
- Expiry. QI 521-522 `for (int i = eqPoolPrice.Count - 1; i >= 0; i--)` with `if (CurrentBar - eqPoolBar[i] > 200)`
  and `RemoveAt(i)`. port 361-363 `for i in range(len(pool_p) - 1, -1, -1):` `if t - pool_b[i] > 200:`.

Consolidation: QI 527 `if (CurrentBar < 50 || atrSma50[0] <= 0) return;` and 528-537. port 366-380
`if not (t < 50 or asma[t] <= 0):` `ratio = atr[t] / asma[t]` `if ratio < cons_ratio:` ...
`elif ratio >= cons_ratio * 1.5 and t - cons_start > 50:` `in_cons = False`.

Donchian: QI 543 `int limit = Math.Min(SwingLookback, CurrentBar);` with i = 1..limit (544-545). port 251
`_prior_extremes(H, L, lb)`, which at 161 is `hi[k:] = sliding_window_view(H[:-1], k).max(axis=1)` = H[t-k..t-1].
`limit` always equals lb, because the gate 2lb+5 is greater than lb.

Pending (QI 550-559; port 387-397):
- Expiry. `CurrentBar - pendingSweepBar > pendingSweepConfirmWindow` vs `t - pend_bar > pend_win`.
- Confirm. `(pendingSweepDir == 1 && Close[0] > pendingSweepLevel) || (pendingSweepDir == -1 && Close[0] < pendingSweepLevel)`
  vs `(pend_dir == 1 and c > pend_lvl) or (pend_dir == -1 and c < pend_lvl)`.
- On confirm, both write the plots 0.55/dir (QI 557 -> 731-732), then
  `lastSweepDir = pendingSweepDir; barsSinceLastSweep = 0; pendingSweepDir = 0;` (port 391-397). Neither applies the
  dup filter.

Check 1, Basic (QI 564-605; port 404-460):
- `bool volSpike = volSma20[0] > 0 && Volume[0] > SweepVolMultiple * volSma20[0];` vs
  `vol_spike = vs > 0 and v > vol_mult * vs`.
- `double wickThresh = body > 0 ? SweepWickMultiple : 1.0;` vs `wick_thresh = wick_mult if body > 0 else 1.0`.
- `double wr = body > 0 ? upperWick / body : (upperWick > 0 ? 99 : 0);` vs port 413-418.
- The branches come in the same order: swing high (0.70, `wr >= wickThresh && volSpike`), swing low, PDH/PDL inside
  `UsePrevDayLevels && prevDayHigh > double.MinValue` (0.85), ORB inside
  `UseOrbLevels && orbComplete && orbHigh > double.MinValue`, monthly inside
  `UseMonthlyLevels && klMonthlyHigh > double.MinValue`. Each uses strict comparisons (`High[0] > L && Close[0] < L`),
  and the first branch to fire returns (C#) or breaks (port 419-455).

Check 2, SFP (QI 610-619; port 464-471): confidences 0.50/0.50/0.60/0.60. The 2-bar case is
`CurrentBar >= 2 && ... High[1] > lastSwingHigh && Close[1] > lastSwingHigh && Close[0] < lastSwingHigh` vs
`t >= 2 and ... Hl[t - 1] > last_sh and Cl[t - 1] > last_sh and c < last_sh`.

Check 3, equal-level trap (QI 625-634; port 482-491): backwards loop; per entry the high test runs before the low test;
the first hit is removed and the loop stops.

Check 4, consolidation trap (QI 640-647; port 502-508):
`if (!isInConsolidation && CurrentBar - consolidationStartBar > 10) return false;`,
`if (consolidationHigh <= consolidationLow) return false;`, `Volume[0] > 2.0 * volSma20[0]`,
`High[0] > consolidationHigh && Close[0] <= consolidationHigh`, `Low[0] < consolidationLow && Close[0] >= consolidationLow`,
0.65. The port keeps `<=` and `>=`.

Check 5, Wyckoff (QI 653-663; port 519-527): `if (CurrentBar < rangeLen + 1) return false;`, range over i = 1..2lb,
`if (rangeHigh <= rangeLow) return false;`, `isInConsolidation ? 0.75 : 0.60` (taken after this bar's consolidation
update in both), Spring `Low[0] < rangeLow && Close[0] > rangeLow && Close[0] > Open[0]` tested before Upthrust.

Check 6, Turtle Soup (QI 669-673; port 538-542): `donchianHigh <= double.MinValue || donchianLow >= double.MaxValue`,
`High[0] > donchianHigh && Close[0] < donchianHigh && Open[0] < donchianHigh`, 0.55.

Check 7, VolDiv (QI 679-704; port 552-566): `if (pendingSweepDir != 0) return false;`; weak volume is
`Volume[0] < 0.8 * volSma20[0]`; absorbed volume is
`Volume[0] > SweepVolMultiple * volSma20[0] && range > 0 && body < 0.3 * range`; a new high takes precedence; window 3.
The check always returns false, so it never adds to `results`.

Accumulation (QI 443-467; port 456-549): check 1 sets `sweepDir=d1`; checks 2-7 set it only `if(sweepDir==0)`;
`totalConf+=c` in the same order; `sweptLevel` set only `if(sweptLevel==0)`.

Final (QI 469-475; port 568-578): `if (results.Count == 0 || sweepDir == 0) return;`,
`if (sweepDir == lastSweepDir && barsSinceLastSweep < DuplicateBarWindow) return;`,
`totalConf = Math.Min(totalConf, 1.0);`, then the plots (731-732). The port does the same with `dup_win`.

Duplicate window default: QI 170 `DuplicateBarWindow = 5;`, port 241 `duplicate_bar_window=5`, ORIG 268
`DuplicateBarWindow = 5;`.

Differences recorded:

| # | QI | port | Class / first differing condition |
|---|---|---|---|
| D2.1 | 284-285 `DateTime cstTime = TimeZoneInfo.ConvertTime(Time[0], Core.Globals.GeneralOptions.TimeZoneInfo, cstZone);` | 293 `# ---- UpdateKeyLevels (QI 282-404); cstTime == BarTime ----` with 249 `day, wday, month, tod = _time_parts(df)`. No conversion; the port justifies this at 36-37. | **Value-changing only if NT's GeneralOptions time zone is not US Central.** This NT setting can differ from the PC zone. First differing condition: a day, RTH or ORB boundary moves by the zone offset, which changes a PDH/PDL/ORB level and therefore a Sweep PDH/PDL/ORB-H/ORB-L. **UNVERIFIABLE by reading (R3).** Decided by: the NT8 Options time-zone setting of the export run, or BT4's probe (the 16:00-17:00 CT halt must appear at that hour in P1 BarTime). |
| D2.2 | 198 `todayRthDate = DateTime.MinValue;` 208 `orbDate = DateTime.MinValue;` | 269 `today_date = None` 275 `orb_date = None` | Not value-changing: on the first bar the comparison is unequal in both. |
| D2.3 | 253 `UpdateVolumeDelta();` | 330 `# (UpdateVolumeDelta: series maintained by the C# but never read by a sweep check)` | Not value-changing: QI_LiquiditySweep never reads volDelta (it only writes it, at 268-276). |
| D2.4 | 486-488 loop with `break` | 147-150 sliding-window max/min | Not value-changing for finite prices. A NaN in High or Low would make them differ. |
| D2.5 | 542-545 and 655-657 loops | 161-162 sliding windows (k = lb and 2lb) | Same NaN caveat. Otherwise equal. |
| D2.6 | 562-606: a separate `wr` per branch, each with `return true` | 409-455: `wr_up` and `wr_lo` computed once, then `while True` / `break` | Not value-changing: same values, same first-hit order. |
| D2.7 | 238 `barsSinceLastSweep = int.MaxValue;` 429 `barsSinceLastSweep++;` | 284 `bars_since = INT_MAX` 338 `bars_since = _inc32(bars_since)` | Not value-changing (R5). |
| D2.8 | 499/517 `prevSwingHigh/Low`; 480-481, 491, 509 `swingHigh/LowSeries`; 131-132 and 736-749 `pendingSweepStart*` | not ported | Not value-changing: no check and no plot reads any of them. |
| D2.9 | 729-733 `if (!isStart)` `{ Values[0][0] = confidence; Values[1][0] = direction; }` | 391-392 and 573-574 write conf/struct; 565-566 log Start without a plot write | Not a difference: Start writes no plot in either. |

Observations re-derived from the code, with no difference between port and QI:
- "Sweep MoHigh/MoLow" can never fire. UpdateKeyLevels raises klMonthlyHigh/Low to High[0]/Low[0] before the check
  runs (QI 354-355, with 252 before 258; ORIG 733-734, with 551 before 587).
- "Liq Sweep" on the swing levels always fires together with SFP, because the price condition is the same. Its End
  confidence is therefore min(1.2 + ..., 1.0) = 1.0.

**QI vs ORIG.**
- DetectLiquiditySweeps: ORIG 2038-2088 = QI 426-476.
- UpdateSwingPoints: ORIG 2090-2137 = QI 478-523, except that ORIG also computes
  `cumDeltaAtLastSwingHigh = ComputeCumDelta10();` (2113) and `cumDeltaAtLastSwingLow = ComputeCumDelta10();` (2132).
  That is OF state; LS does not read it.
- The remaining helpers: ORIG 2139-2319 = QI 525-705.
- Key levels: ORIG 681-808 = QI 302-421. ORIG gates them with `ShowPrevDayLevels` / `ShowMonthlyLevels` /
  `ShowOrbLevels` (661-668). ORIG 670-673 adds the Asian session and DrawKeyLevelLines; no check reads either.

Value-changing: A1 (start gate). Not value-changing but limiting: `databox_LiqSweep` is confidence only (0.4).

**Verdict PT2: CONFIRMED.** 0 value-changing differences between the port and QI at code level. D2.1 depends on R3,
and the result also depends on R1 and R2.

---

## PT3: `order_flow_plus` (port 607-743) vs QI_OrderFlowPlus (QI 156-347); ORIG 1623-1634, 2411-2541

**OnBarUpdate order.** QI 158-171: `if (CurrentBar < 50) return;`, `UpdateVolumeDelta();`, the plots set to 0,
`if (CurrentBar >= SwingLookback * 2 + 5)` `UpdateSwingPoints();`, then `ProcessOrderFlowSignals();`. port 630,
637-641, 643-644, 647-659 and 662-741 follow the same order.

**Term-by-term comparison (every item is equal).**
- volDelta. QI 181-189 `if (CurrentBar < 1) { volDelta[0] = 0; return; }`,
  `double priceChange = Close[0] - Close[1];`, then `> 0` -> `Volume[0]`, `< 0` -> `-Volume[0]`, else 0. port 637-641
  `pc = c - Cl[t - 1]` and `vd[t] = v if pc > 0 else (-v if pc < 0 else 0.0)`.
- Swings. QI 204-226 uses the same pivot rule as LS. The snapshot `cumDeltaAtLastSwingHigh = ComputeCumDelta10();` is
  taken after this bar's volDelta. port 647-659 `if sh_flag[t]:` `last_sh = Hl[t - lb]`, then
  `for i in range(min(10, t)):` `cd += vd[t - i]`.
- cumD10. QI 237-239 `int len = Math.Min(10, CurrentBar);` `for (int i = 0; i < len; i++)` `cd += volDelta[i];`.
  port 670-672, with the same summation order.
- Gate and counter. QI 245-246 `if (CurrentBar < 20) return;` `barsSinceLastOf++;`. port 662-664.
- DeltaDiv 0.78. QI 257-260 `lastSwingHigh > double.MinValue && High[0] > lastSwingHigh && cumD10 < cumDeltaAtLastSwingHigh`
  sets `ofDir = -1`. The low side, `cumD10 > cumDeltaAtLastSwingLow`, sets `ofDir = 1` unconditionally, so it can
  overwrite. port 675-682 is the same.
- Absorption 0.65. QI 263
  `volSma20[0] > 0 && Volume[0] > 1.5 * volSma20[0] && range > 0.5 * atr14[0] && range > 0 && body < 0.30 * range`,
  and 265 `Close[0] > Open[0] ? 1 : -1`. port 685-686.
- Exhaustion 0.60. QI 272-282 `CurrentBar >= 3`, `High[0] >= lastSwingHigh`, `Low[0] <= lastSwingLow`,
  `Math.Abs(volDelta[0]) < Math.Abs(volDelta[1]) && Math.Abs(volDelta[1]) < Math.Abs(volDelta[2])`,
  `newHigh ? -1 : 1`. port 692-701 keeps `>=`, `<=` and the strict `<`.
- Stacked delta 0.55. QI 287-302 and port 703-715: if / else-if, with first-come direction.
- DeltaRev 0.70. QI 306-321 `prev3Pos = volDelta[1] > 0 && volDelta[2] > 0 && volDelta[3] > 0`, then
  `prev3Pos && volDelta[0] < 0 && Close[0] > Close[1]`. port 717-729. It is unreachable in both, because
  volDelta[0] < 0 if and only if Close[0] < Close[1].
- Final. QI 324-346 and port 731-741: `ofDir == lastOfDir && barsSinceLastOf < DuplicateBarWindow`,
  `Math.Min(bestConf, 1.0)`, and `Values[1] = ofDir`.
- Dup default. QI 114 `DuplicateBarWindow = 5;`. port 607 `duplicate_bar_window=5`.

Differences recorded:

| # | QI | port | Class / first differing condition |
|---|---|---|---|
| D3.1 | 158-161: volDelta is first written at bar 50. Reads go up to 9 bars back (237-239), plus 276, 289-290 and 308-309. | 622 `vd = [0.0] * n                      # volDelta; unwritten (bars < 50) read as 0.0` | **Value-changing only if NT8 reads a never-set `Series<double>` slot as something other than 0.0.** Affected: cumD10 at bars 50-58; the Exhaustion and Stacked reads at bars 50-51; the DeltaRev reads at 50-52 (unreachable anyway); and the cumDelta snapshot of any swing confirmed at bars 50-58. That snapshot is kept until the next swing on the same side. **UNVERIFIABLE by reading (R4).** Decided by: NT8 `Series<T>` semantics, or a one-line NT `Print` of `volDelta[1]` at `CurrentBar == 50`. The port flags this assumption itself (39-41). |
| D3.2 | 168 `if (CurrentBar >= SwingLookback * 2 + 5)` and 202 `if (CurrentBar < lb * 2) return;` | 647 `if t >= gate and t >= lb * 2:` | Not value-changing. |
| D3.3 | 199-200, 210 and 222 swing series; 211 and 223 `prevSwing*` | not ported | Not value-changing: never read. |
| D3.4 | 206-207 and 218-219 loops | 147-150 vectorized | Same as D2.4. |
| D3.5 | 150 `barsSinceLastOf = int.MaxValue;` 246 `++` | 627 and 664 `_inc32` | Same as D2.7. |

**QI vs ORIG.**
- ProcessOrderFlowSignals: ORIG 2420-2541 = QI 243-347 in logic. Only the labels, brush names and the TP/SL drawing
  differ.
- ComputeCumDelta10: ORIG 2411-2418 = QI 234-241.
- volDelta: ORIG 1623-1634 = QI 179-190.
- In ORIG the swing state comes from the LS UpdateSwingPoints (2111-2113, 2130-2132). It runs inside
  DetectLiquiditySweeps (gate at 2040), before ProcessOrderFlowSignals (ORIG 586-591). QI reproduces this with its own
  gate at 168. The two are equivalent only while ORIG's `EnableLiquiditySweep` is true, which is the default (ORIG 298;
  see 0.5).

Value-changing: A1. Not value-changing but limiting: `databox_OFSignal` is confidence only.

**Verdict PT3: CONFIRMED.** 0 value-changing differences between the port and QI at code level. Bars 50-58, and their
swing snapshots, depend on R4, which reading cannot decide. The result also depends on R1 and R2.

---

## PT4: `smc` (port 767-947) vs QI_SMC (QI 176-428); ORIG 2548-2739

**OnBarUpdate order.** QI 178-193: the gate, UpdateVolumeDelta (never read), the plots set to 0, the gated swing update,
ProcessSmcSignals, then `trendDirSeries[0] = smcTrendDir;`. port 794-945 follows the same order without volDelta.

**Term-by-term comparison (every item is equal).**
- Swings. QI 226-246 `prevSwingHigh = lastSwingHigh; ...` `lastSwingHigh = candidateHigh;`. port 803-809
  `prev_sh = last_sh` `last_sh = Hl[t - lb]`. Lows are the same.
- Gate and counter. QI 256-257. port 812-813.
- Trend. QI 260-265:
  `if (lastSwingHigh > double.MinValue && prevSwingHigh > double.MinValue)`,
  `if (lastSwingHigh > prevSwingHigh && lastSwingLow > prevSwingLow) smcTrendDir = 1;`,
  `else if (lastSwingHigh < prevSwingHigh && lastSwingLow < prevSwingLow) smcTrendDir = -1;`. port 814-818.
- Order-block zones. QI 274 `CurrentBar >= 2 && range > 0 && body > 0.75 * range && range > 1.5 * atrVal`; 276
  `if (Close[0] > Open[0])`; 279 `if (Close[1] < Open[1])`; 281
  `if (obBullZoneHigh.Count >= 5) {...RemoveAt(0)...}`; 282
  `obBullZoneHigh.Add(High[1]); obBullZoneLow.Add(Low[1]); obBullBar.Add(CurrentBar - 1);`; the else branch at 288
  `if (Close[1] > Open[1])`. port 825-839: `Cl[t - 1] < Ol[t - 1]`, `del ...[0]`, `append(Hl[t - 1])`,
  `append(Ll[t - 1])`, `append(t - 1)`.
- FVG zones. QI 297-310: `CurrentBar >= 3`; `Low[0] > High[2]` ->
  `fvgBullTop.Add(Low[0]); fvgBullBottom.Add(High[2]); fvgBullBar.Add(CurrentBar);`; `High[0] < Low[2]` ->
  `fvgBearTop.Add(Low[2]); fvgBearBottom.Add(High[0]);`. port 841-853: `l > Hl[t - 2]`, `h < Ll[t - 2]`, `append(t)`.
- Expiry. QI 314-321 and port 855-866: backwards loops, `> 100` for OBs and `> 50` for FVGs.
- OB retest 0.72. Bull (QI 329-337): `Low[0] <= obBullZoneHigh[i] && Low[0] >= obBullZoneLow[i]` -> `smcDir = 1;`
  (unconditional), then RemoveAt and break. Bear (338-347): `High[0] >= obBearZoneLow[i] && High[0] <= obBearZoneHigh[i]`,
  `if (smcDir == 0) smcDir = -1;`. port 872-886.
- FVG entry 0.68. QI 350-369: `Low[0] <= fvgBullTop[i] && Close[0] >= fvgBullBottom[i]` and
  `High[0] >= fvgBearBottom[i] && Close[0] <= fvgBearTop[i]`. port 888-903.
- BOS 0.60. QI 372-383 `prevSwingHigh > double.MinValue && Close[0] > prevSwingHigh && CurrentBar - lastBosBar > 5`,
  then `lastBosBar = CurrentBar;`, so the second test sees the updated `lastBosBar`. port 905-916. Init: QI 168
  `lastBosBar = 0`, port 791.
- CHoCH 0.75. QI 386-395. port 918-927.
- Displacement 0.58. QI 398-403. port 929-934.
- Final. QI 405-427. port 936-943
  `if patterns and smc_dir != 0 and not (smc_dir == last_smc_dir and bars_since < dup_win):`.
- Dup default. QI 131 `DuplicateBarWindow = 5;`. port 767 `duplicate_bar_window=5`.

Differences recorded:

| # | QI | port | Class |
|---|---|---|---|
| D4.1 | 188 `if (CurrentBar >= SwingLookback * 2 + 5)` and 224 | 803 `if t >= gate and t >= lb * 2:` | Not value-changing. |
| D4.2 | 147-149, 181 and 201-212: `volSma20`, `atrSma50`, `volDelta` | not ported (comment at 799) | Not value-changing: the SMC logic reads only ATR. |
| D4.3 | 221-222, 232 and 243 swing series; 234 and 245 `*Bar` | not ported | Not value-changing. |
| D4.4 | 226-245 loops | 147-150 vectorized | Same as D2.4. |
| D4.5 | 168 `barsSinceLastSmc = int.MaxValue;` 257 `++` | 790 and 813 `_inc32` | Same as D2.7. |

Quirk re-derived from both sides, with no difference: a bull FVG created on bar t has top = Low[0] and
bottom = High[2] < Low[0] <= Close[0]. So the FVG-entry test on the same bar is always true, and every FVG fires and is
consumed on the bar that creates it. The bear case is symmetric.

**QI vs ORIG.** ProcessSmcSignals: ORIG 2548-2739 = QI 254-428 in logic. Only the labels and the TP/SL drawing differ.
The swing state comes from the LS UpdateSwingPoints, as for PT3. Value-changing: A1. Limiting: `databox_SMCSignal` is
confidence only.

**Verdict PT4: CONFIRMED.** 0 value-changing differences between the port and QI. Residual: R1.

---

## What would change these verdicts

- R1: if `qi_ref.atr` is not the NT8 @ATR.cs recursion, all four become REFUTED.
- R3 (PT2): if NT's GeneralOptions time zone is not US Central, PT2 becomes REFUTED.
- R4 (PT3): if NT does not read unset `Series<double>` slots as 0.0, PT3 becomes REFUTED on bars 50-58.
- **Against ORIG on P1, as the ledger words the claims:** A1 and A2 predict mismatches on the leading rows after every
  ORIG run start. For PT1 that is rows 50 to about 200. For PT2-PT4 it starts at row 0, because ORIG events on P1
  rows 0-49 have no port counterpart. A state transient of tens to hundreds of bars follows. Channel B should bin
  mismatches by distance from each run start. Nothing in this audit explains a mismatch far from every run start; such
  a mismatch would point at the port.
