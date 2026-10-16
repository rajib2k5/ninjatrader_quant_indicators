# Channel A — static fidelity audit, claims C32–C44

date: 2026-10-15
auditor: Channel A (static source auditor, read-only; nothing executed)
spec: ORIG = `C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\IBSFade.cs` (3,230 lines)
code under audit: `C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators\indicators\QI_*.cs`
claim form: `validation/claims-ledger.md` section C ("plotted/exposed value(s) equal ORIG `Values[k][0]`
bar-for-bar ... for every bar ≥ 50"; pattern modules: event list equal)
pointer: `docs/CONVENTIONS.md` module map (treated as a pointer only; corrections in §1)

Verdict key: CONFIRMED = no difference found that can change a plotted value or an event on any bar
ORIG processes; REFUTED = a difference that changes a value or event, first condition named;
UNVERIFIABLE = not decidable by reading, decider named.

Summary: C34, C35, C36, C37, C38, C39, C40, C42, C43, C44, C32 CONFIRMED (11); C41 REFUTED (plot
value on "Liq Sweep Start" bars); C33 CONFIRMED-with-D0 (its whole scope is the intraday chart, where
the cross-cutting gate difference D0 below bites). D0 itself is a reading-visible difference whose
reach on a given chart is runtime-dependent; it is reported once (§0) and cross-referenced per claim.

---

## 0. Cross-cutting difference D0 — ORIG's intraday warm-up gate is not reproduced

ORIG 535-548 (intraday chart; `useDailySeries = Bars.BarsType.IsIntraday`, ORIG 325):

```
			if (useDailySeries)
			{
				if (CurrentBars[0] < 50 || CurrentBars[1] < 1)
					return;

				if (BarsInProgress == 1)
				{ ... dailyIBS ...; return; }

				if (BarsInProgress != 0)
					return;
```

ORIG 599-602 (non-intraday chart):

```
			else
			{
				if (CurrentBar < 50)
					return;
```

Every QI module under audit gates only on the primary series: `if (CurrentBar < 50) return;`
(QI_HedgingPressure 141, QI_VWAPDistance 123, QI_MACDHistogram 91, QI_VolumeDelta 96,
QI_LiquiditySweep 245, QI_OrderFlowPlus 156, QI_SMC 176, QI_KeyLevels 183) or has no gate at all
(QI_EMACross, QI_SMA200Trend, QI_ATRRegime, QI_VolumeSpike, QI_ChopIndex). None adds the daily series
and none reproduces the `CurrentBars[1] < 1` term.

Consequence by reading: on an intraday chart ORIG executes *nothing* (no state update, no `Values`
write, no label, no CSV row — `LogEveryBarToCsv` at 597 is after the gate) on any primary bar for
which `CurrentBars[1] < 1`, i.e. until the daily series has registered its second bar. The daily
series is loaded over the same range as the primary, so the primary bars of the first one-to-two
sessions are skipped by ORIG but processed by the QI modules. Whenever the first loaded session
holds more than 50 primary bars (any ≤ 25-minute chart on a 23-hour session; any ≤ 7-minute chart on
an RTH-only session) bars ≥ 50 fall inside that window and the ledger wording "every bar ≥ 50" is
violated: ORIG's plot value on those bars is the series default 0 and its EveryBar CSV has no row,
while the QI module writes a value.

What this does per module once ORIG's gate opens (the "carry-over"):

| module | carry-over after ORIG's first processed bar |
|---|---|
| C34 MACD, C35 EMACross, C36 SMA200, C37 ATRRegime, C38 VolumeSpike, C40 ChopIndex | none — built-in indicators update regardless of the host's early return; values equal from ORIG's first processed bar |
| C32 HedgingPressure | score equal immediately; Weekly/Monthly HP line levels differ for 5 / 20 bars (ORIG's `hpScoreSeries` is 0 on the skipped bars, QI's holds real scores) |
| C33 VWAPDistance | differs until the first `Time[0].DayOfYear` change after ORIG's gate opens (ORIG starts accumulating mid-session; QI started at bar 50) |
| C39 VolumeDelta | ORIG's `volDelta` is 0 on skipped bars → CumDelta20 differs for 20 bars, DeltaSMA10 for 10 bars |
| C41/C42/C43 pattern modules | swing structure (`lastSwing*`, `prevSwing*`), equal-level pool (≤ 200 bars), OB zones (≤ 100 bars), FVG zones (≤ 50 bars), `prevDayHigh/Low` (one session), `klMonthlyHigh/Low` (rest of the month), consolidation state, pending sweep, `lastBosBar`, duplicate-window counters all seeded at different bars → event lists can differ for hundreds of bars |
| C44 KeyLevels | `prevDayHigh/Low` one session late in ORIG; `orbHigh/Low` and Asian H/L of the skipped session(s) absent in ORIG; `klMonthlyHigh/Low` differ for the rest of the month if a skipped session set the month's extreme |

Decidable by reading: the gate difference exists (quoted above). Not decidable by reading: on which
primary bar `CurrentBars[1]` first reaches 1 for a given chart (NinjaTrader's secondary-series
synchronisation and the loaded range). Decider for Channel B: the bar index of the first row in
ORIG's EveryBar CSV on the intraday chart. If it is > 50, D0 bites from bar 50 to that row, plus
the per-module carry-over above. On non-intraday charts D0 is void (ORIG 601 equals the QI gate).

Recommendation to the orchestrator (not a code finding): either re-scope the intraday comparison to
"every bar from ORIG's first processed bar plus the module's carry-over window", or add a
`CurrentBars[1] < 1`-equivalent warm-up to the harness. Neither changes the verdicts below, which
are given for the bars ORIG processes.

---

## 1. Module-map corrections (CONVENTIONS.md, "ORIG lines" column)

The map is a usable pointer but incomplete in these places:

- No row points at the OnBarUpdate gates 535-548 / 599-602; the intraday `CurrentBars[1] < 1`
  term (D0) is therefore invisible from the map.
- Row 15 (HP) omits 347 (`atr14 = ATR(14)`), which `ComputeHedgingPressure` reads at 1017-1042,
  and omits the call sites 561-567 / 613-619 where `hpScoreSeries[0] = hpScore` is written.
- Row 16 (VWAP) omits 557 (the only call of `UpdateManualVwap`, intraday path) — the "only on
  intraday charts" rule comes from that call site, not from 1385-1397.
- Row 24 (LiquiditySweep) omits 347, 358, 409 (`atr14`, `volSma20`, `atrSma50`) and 2411-2418
  (`ComputeCumDelta10`, called from `UpdateSwingPoints` 2113/2132).
- Row 25 (OrderFlowPlus) omits 347, 358 and the gate at 2040 that controls when swings update.
- Row 26 (SMC) omits 347 and the gate at 2040.
- Rows 17-21, 22, 23, 27: complete.

---

## C32 — `QI_HedgingPressure` (ORIG plot 0)

**Verdict: CONFIRMED** (score; price lines by formula). D0 impact: score immediate, lines 5/20-bar
transient.

### ORIG evidence

Construction (ORIG 347, 358, 363-367):
```
				atr14		= ATR(14);
				volSma20	= SMA(Volume, 20);
				sma20hp		= SMA(Close, 20);
				closeSma5	= SMA(Close, 5);
				closeSma20	= SMA(Close, 20);
				rangeSma20	= SMA(Range(), 20);
				hpScoreSeries = new Series<double>(this);
```
State order (ORIG 561-567, same at 613-619):
```
				double hpScore = 0;
				if (EnableHedgingPressure)
				{
					hpScore = ComputeHedgingPressure();
					hpScoreSeries[0] = hpScore;
					ProcessHpSignals(hpScore);
				}
```
then 1263 `Values[0][0] = hpScore;`. Nothing executed before 561 (`UpdateKeyLevels`,
`UpdateManualVwap`, `UpdateVolumeDelta`, `UpdateNewAlphas`) is read by `ComputeHedgingPressure`
(1015-1052), which reads only `atr14`, `sma20hp`, `closeSma5`, `closeSma20`, `volSma20`,
`rangeSma20`, `Close/Open/High/Low/Volume`, `CurrentBar`.

Zones (ORIG 1072-1076), lines (1141-1227): `dailyPrice = fairValue + (dailyHpScore / 100.0) * 2.0 * atr`,
weekly = mean of `hpScoreSeries[0..4]` when `CurrentBar >= 5`, monthly = mean of `[0..19]` when
`CurrentBar >= 20`, redraw when any line moves > 0.25.

### QI evidence

QI 127-135 constructs the same six instances with the same arguments. QI 141-148: gate, `hpScore =
ComputeHedgingPressure(); hpScoreSeries[0] = hpScore; Values[0][0] = hpScore; ProcessHpZone(hpScore);`.
QI 156-200 `ComputeHedgingPressure` + `Clamp`: textually identical to ORIG 1015-1059 (checked term by
term: `-25.0`, `CurrentBar > 5`, `CurrentBar > 20`, `-50.0`, `1.2`/`0.5`, `10.0`, `0.6`/`1.3`,
`50.0`, clamps ±25 / ±100, fallbacks `0`, `1.0`, `1.0`). QI 227-313 `DrawHpTimeframeLines`: textually
identical to ORIG 1141-1227.

### Differences

1. ORIG 1072-1076 `zoneBrush = HpBuyBrush` / `HpSellBrush` (properties, defaults Cyan / Yellow at
   280-281) vs QI 213-217 `zoneBrush = Brushes.Cyan` / `Brushes.Yellow`. Cosmetic (colour of the
   TopRight text only); equal at defaults.
2. ORIG 1066 `barsSinceLastHp++;` and 1082-1135 (Buy/Sell HP labels, CSV, counters, TP/SL,
   `lastHpDir/lastHpZone`) are absent from QI. None of them feed the score or the line levels.
3. ORIG 562 `if (EnableHedgingPressure)` (default true, 259) vs QI unconditional. Equal at defaults.
4. ORIG 1265 `Plots[0].Name = ...` mutation absent. Cosmetic.
5. QI 110-113 adds four reference lines (±35 property-driven, ±15 fixed). No value effect.
6. Gate: ORIG 537/601 vs QI 141 — D0.

Extra scope ("price lines compared by level in the runtime probe"): line formulas identical; the
weekly/monthly averages read `hpScoreSeries[i]`, which is 0 for bars < 50 in both (neither writes it
before bar 50). Post-D0 only the carry-over in §0 applies.

---

## C33 — `QI_VWAPDistance` (ORIG plot 15)

**Verdict: CONFIRMED for every bar ORIG processes; D0 applies to the whole claim scope** (the ledger
scopes this claim to the intraday chart, which is exactly where D0 lives). The formula and the
accumulator are verbatim; the only difference is the start bar of accumulation.

### ORIG evidence

ORIG 325 `useDailySeries = Bars.BarsType.IsIntraday;`. ORIG 352-355 init `cumTypicalPriceVol = 0;
cumVol = 0; manualVwap = 0; vwapSessionDayOfYear = -1;`. Call site ORIG 557 `UpdateManualVwap();` —
present on the intraday path only; the daily path (599-650) never calls it, so `manualVwap` stays 0
there and 1386 yields 0. ORIG 1603-1618:
```
			int today = Time[0].DayOfYear;
			if (today != vwapSessionDayOfYear)
			{ cumTypicalPriceVol = 0; cumVol = 0; vwapSessionDayOfYear = today; }
			double typicalPrice = (High[0] + Low[0] + Close[0]) / 3.0;
			cumTypicalPriceVol += typicalPrice * Volume[0];
			cumVol             += Volume[0];
			manualVwap = (cumVol > 0) ? cumTypicalPriceVol / cumVol : Close[0];
```
ORIG 1386-1388:
```
			double vwapDist = (useDailySeries && atr14[0] > 0 && manualVwap > 0)
				? (Close[0] - manualVwap) / atr14[0] : 0;
			Values[15][0] = vwapDist;
```

### QI evidence

QI 102 `isIntraday = Bars.BarsType.IsIntraday;` (Configure, as ORIG). QI 109-114 same init. QI
127-134: `if (isIntraday) UpdateManualVwap(); vwapSeries[0] = manualVwap; double vwapDist =
(isIntraday && atr14[0] > 0 && manualVwap > 0) ? (Close[0] - manualVwap) / atr14[0] : 0;`. QI
142-157 `UpdateManualVwap` textually identical to ORIG 1603-1618.

### Differences

1. Accumulation start: ORIG first executes 557 on the first primary bar with `CurrentBars[0] >= 50
   && CurrentBars[1] >= 1 && BarsInProgress == 0`; QI first executes 128 at `CurrentBar == 50`. If
   those bars differ (D0), `manualVwap` differs on every bar until the next `DayOfYear` change after
   ORIG's first accumulation, and ORIG's plot 15 is 0 on the bars it skipped. First failing bar:
   bar 50 itself, when ORIG is still gated. Equal thereafter.
2. ORIG 1389-1397 (`vwapClass` B/N/S text) absent. Cosmetic.
3. QI adds a non-plot `Vwap` series (no ORIG counterpart).

Decider: as D0 (bar index of ORIG's first EveryBar row on the intraday chart), plus the bar of the
first day change after it.

---

## C34 — `QI_MACDHistogram` (ORIG plot 16)

**Verdict: CONFIRMED.** D0 impact: none after ORIG's gate opens.

ORIG 348 `macd = MACD(Close, 12, 26, 9);`; ORIG 1400 `Values[16][0] = macd.Diff[0];`.
QI 83 `macd = MACD(Close, 12, 26, 9);`; QI 91-95 `if (CurrentBar < 50) return; Values[0][0] = macd.Diff[0];`.

Differences: no differences (ORIG 1401-1402 B/N/S text absent, cosmetic).

---

## C35 — `QI_EMACross` (ORIG plot 17, compared via `Spread`)

**Verdict: CONFIRMED.** D0 impact: none.

ORIG 344-345 `ema20 = EMA(Close, 20); ema50 = EMA(Close, 50);`; ORIG 1405-1406
`double emaDiff = ema20[0] - ema50[0]; Values[17][0] = emaDiff;`.
QI 83-84 same constructors; QI 96-97 `double emaDiff = ema20[0] - ema50[0]; spreadSeries[0] = emaDiff;`.

Differences:
1. QI has no `CurrentBar < 50` gate (writes from bar 0). Out of the ledger's bar ≥ 50 scope; no
   effect on bars ≥ 50 because the value is stateless given the two EMA instances.
2. QI plots the two EMAs (no ORIG plot). Not compared.

---

## C36 — `QI_SMA200Trend` (ORIG plot 18, compared via `Distance`)

**Verdict: CONFIRMED.** D0 impact: none.

ORIG 346 `sma200 = SMA(Close, 200);`; ORIG 1411-1412
`double sma200Dist = CurrentBar >= 200 ? Close[0] - sma200[0] : 0; Values[18][0] = sma200Dist;`.
QI 81 same constructor; QI 92-93 `double sma200Dist = CurrentBar >= 200 ? Close[0] - sma200[0] : 0;
distanceSeries[0] = sma200Dist;`.

Differences: no gate at 50 (out of scope, stateless); SMA plot added. No value differences.

---

## C37 — `QI_ATRRegime` (ORIG plot 19)

**Verdict: CONFIRMED.** D0 impact: none.

ORIG 347 `atr14 = ATR(14);`, 409 `atrSma50 = SMA(atr14, 50);`; ORIG 1417-1418
`double atrReg = CurrentBar >= 50 && atrSma50[0] > 0 ? atr14[0] / atrSma50[0] : 1.0; Values[19][0] = atrReg;`.
QI 82-83 same constructors (SMA built on the ATR instance, as ORIG); QI 91-92 identical expression.

Differences: no gate at 50 in QI, but the expression's own `CurrentBar >= 50` term makes bars < 50
read 1.0 — out of scope anyway. No value differences.

---

## C38 — `QI_VolumeSpike` (ORIG plot 20)

**Verdict: CONFIRMED.** D0 impact: none.

ORIG 358 `volSma20 = SMA(Volume, 20);`; ORIG 1423-1424
`double volRatio = volSma20[0] > 0 ? Volume[0] / volSma20[0] : 1.0; Values[20][0] = volRatio;`.
QI 80 same constructor; QI 88-89 identical expression.

Differences: no gate at 50 (out of scope, stateless). No value differences.

---

## C39 — `QI_VolumeDelta` (ORIG plots 21, 22)

**Verdict: CONFIRMED.** D0 impact: 20-bar / 10-bar transient after ORIG's gate opens (§0).

### ORIG evidence

ORIG 357, 360 `volDelta = new Series<double>(this); ... volDeltaSma = SMA(volDelta, 10);`.
`UpdateVolumeDelta()` called at 558 / 610 on every processed bar, before `UpdateDataBoxValues`
(581 / 633). ORIG 1623-1634:
```
			if (CurrentBar < 1) { volDelta[0] = 0; return; }
			double priceChange = Close[0] - Close[1];
			if (priceChange > 0)      volDelta[0] = Volume[0];
			else if (priceChange < 0) volDelta[0] = -Volume[0];
			else                      volDelta[0] = 0;
```
ORIG 1429-1435, 1440-1441:
```
			double cumDelta = 0;
			if (CurrentBar > 20)
			{ for (int i = 0; i < 20; i++) cumDelta += volDelta[i]; }
			Values[21][0] = cumDelta;
			...
			double vdSmaVal = CurrentBar >= 10 ? volDeltaSma[0] : 0;
			Values[22][0] = vdSmaVal;
```

### QI evidence

QI 87-88 same series and `SMA(volDelta, 10)`. QI 96-114: gate at 50, `UpdateVolumeDelta()` (QI
120-131 textually identical to ORIG 1623-1634), `Values[0][0] = volDelta[0]`, then the two blocks
textually identical to ORIG 1429-1435 and 1440-1441. Relative order "write `volDelta[0]`, then read
`volDeltaSma[0]`" is the same as ORIG, so the child SMA sees the same input in both.

Because both ORIG and QI first write `volDelta` at bar 50, `volDelta[i]` for bars < 50 is the
series default 0 in both, and the 20-bar sum on bars 50-69 and the SMA on bars 50-58 agree.

### Differences

1. QI header comment lines 23-25 ("only the per-signal guards are kept here"; "that global gate ...
   volDelta series stayed 0 before bar 50") contradicts the code: QI 96-97 does reproduce the
   50-bar gate. Documentation-only; the code is the one that matches ORIG.
2. ORIG 1436-1437, 1442-1443 B/N/S text absent. Cosmetic.
3. Gate: D0.

No value-affecting differences.

---

## C40 — `QI_ChopIndex` (ORIG plots 25, 26)

**Verdict: CONFIRMED.** D0 impact: none (stateless).

ORIG 358-359 `volSma20 = SMA(Volume, 20); adx14 = ADX(14);`. ORIG 1456-1480 (CHOP), 1483-1488
(ADX class, `volRatioChop`, `lowVolume = volRatioChop < 0.7`), 1498-1521 (2-of-3 flag). QI 102-103
same constructors; QI 116-140 textually identical to ORIG 1456-1480 including
`if (i < CurrentBar)` (ORIG 1466 / QI 126), `Math.Log10(sumTR / range) / Math.Log10(chopPeriod)`,
`Math.Max(0, Math.Min(100, chopVal))`; QI 143-148 identical to ORIG 1483-1488; QI 155-182 identical
to ORIG 1498-1521 (`> 61.8`, `< 20`, `lowVolume`; `>= 2 → 1`, `== 1 → 0.5`, else `0`).
`Values[0][0] = chopVal` ↔ ORIG `Values[25][0]`; `choppyFlagSeries[0] = chopFlag` ↔ ORIG `Values[26][0]`.

Differences:
1. No gate at 50 in QI; ORIG's own `CurrentBar >= chopPeriod` guard is reproduced. Out of scope.
2. ORIG 1490-1494 / 1522-1524 `Plots[].Name` strings replaced by a `Draw.TextFixed` (QI 184-196)
   with different wording and a `\u2014` dropped. Cosmetic.
3. QI adds `Adx`, `VolRatio` non-plot series. No ORIG counterpart.

No value-affecting differences.

---

## C41 — `QI_LiquiditySweep` (ORIG plot 24; event list)

**Verdict: REFUTED — plotted `Confidence` differs from ORIG `Values[24][0]` on every bar that
carries a "Liq Sweep Start" label. Event list (bar, start/end, patterns, confidence, direction):
CONFIRMED.** D0 impact: long carry-over (§0).

### ORIG evidence

Construction: 347 `atr14 = ATR(14)`, 358 `volSma20 = SMA(Volume, 20)`, 409 `atrSma50 = SMA(atr14, 50)`,
421-448 sweep state (`pendingSweepConfirmWindow = 3`, `barsSinceLastSweep = int.MaxValue`, ...),
372-396 key-level state. Order per bar: 551 `UpdateKeyLevels()` → 558 `UpdateVolumeDelta()` → ...
→ 1451 `Values[24][0] = 0;` → 586-587 `if (EnableLiquiditySweep) DetectLiquiditySweeps();`.
Inside (2038-2088): gate `CurrentBar < SwingLookback * 2 + 5`, `barsSinceLastSweep++`,
`UpdateSwingPoints(); UpdateConsolidationZone(); UpdateDonchianChannel(); CheckPendingSweepConfirmation();`
then the seven checks in order, `results.Count == 0 || sweepDir == 0` return, duplicate window,
`totalConf = Math.Min(totalConf, 1.0); DrawSweepLabel(...false)`.

Value write, ORIG 2372-2387 — only on End labels:
```
			// DataBox row 24: detail on End events
			if (!isStart)
			{
				...
				Values[24][0] = confidence;
				Plots[24].Name = detail;
			}
```
Start labels are drawn from inside `CheckVolumeDivergenceFakeout` (ORIG 2308, 2315,
`DrawSweepLabel(-1, 0.35, ..., true)` / `DrawSweepLabel(1, 0.35, ..., true)`) and leave
`Values[24][0]` at the 0 written at 1451.

### QI evidence

QI 182-185 same four instances/series; QI 188-237 same state init (key levels and sweep state,
value-for-value). QI 245-255 order: gate 50 → `UpdateKeyLevels()` → `UpdateVolumeDelta()` →
`Values[0][0] = 0; Values[1][0] = 0;` → `DetectLiquiditySweeps()`.
QI 423-473 `DetectLiquiditySweeps`: textually identical to ORIG 2038-2088.
QI 475-520 `UpdateSwingPoints`: identical to ORIG 2090-2137 except the two
`cumDeltaAtLastSwing* = ComputeCumDelta10();` lines (ORIG 2113, 2132) are omitted — no sweep check
reads them. Equal-level pool (cap 10, 200-bar expiry, `EqualLevelTolerance * 0.01 * candidate`) identical.
QI 522-535 `UpdateConsolidationZone`, 537-543 `UpdateDonchianChannel`, 545-557
`CheckPendingSweepConfirmation`: identical to ORIG 2139-2174.
QI 559-603 `CheckBasicLiquiditySweep`: identical to ORIG 2176-2220 with `ShowPrevDayLevels /
ShowOrbLevels / ShowMonthlyLevels` renamed `UsePrevDayLevels / UseOrbLevels / UseMonthlyLevels`
(defaults true in both: ORIG 271-273, QI 160-162). Confidences 0.70 / 0.85, names "Liq Sweep",
"Sweep PDH/PDL/ORB-H/ORB-L/MoHigh/MoLow", `wickThresh = body > 0 ? SweepWickMultiple : 1.0`, the
`99`/`0` wick-ratio fallbacks: identical.
QI 605-702 SFP (0.50/0.60), EqualLevelTrap (0.60, removes the hit entry), ConsolidationBreakoutTrap
(0.65, `2.0 * volSma20`, `!isInConsolidation && CurrentBar - consolidationStartBar > 10`),
Wyckoff (0.75/0.60, `rangeLen = SwingLookback * 2`), TurtleSoup (0.55), VolumeDivergenceFakeout
(`0.8`, `0.3 * range`, pending window 3, Start label 0.35): identical to ORIG 2222-2319.
Key-level tracking QI 279-418: identical to ORIG 656-808 minus Asian session and minus
`DrawKeyLevelLines()` (neither read by any check).

Event identity: every `Draw.Text` in ORIG (2357, called from 2085, 2171, 2308, 2315) has the same
call in QI (720, from 470, 554, 691, 698) on the same bar with the same `direction`, `confidence`,
`patterns` and `isStart`; brush/anchor/offset selection (QI 716-719) equals ORIG 2353-2356. Only the
label text differs (below).

### Differences

1. **Value-affecting.** QI 724-726 writes the plots on every label including Start:
   ```
   			// Panel plots: confidence and structure direction for this bar
   			Values[0][0] = confidence;
   			Values[1][0] = direction;
   ```
   whereas ORIG 2373/2385 writes `Values[24][0] = confidence;` only `if (!isStart)`. First condition
   where a value changes: the first bar ≥ 50 on which `CheckVolumeDivergenceFakeout` fires
   (`pendingSweepDir == 0`, `High[0] > lastSwingHigh` or `Low[0] < lastSwingLow`, and
   `Volume[0] < 0.8 * volSma20[0]` or the absorbed-volume condition) and no End label is drawn later
   on that bar: QI `Confidence` = 0.35, ORIG `Values[24][0]` = 0 (|Δ| = 0.35 ≫ 0.00005). A second
   form: a bar where `CheckPendingSweepConfirmation` draws End (0.55) and the checks then draw a
   Start: ORIG 0.55, QI 0.35. Fix candidate (one guard): wrap QI 725-726 in `if (!isStart)` — or
   the ledger must say explicitly that `Confidence` includes Start confidences. Not value-affecting
   on bars that carry no Start label.
2. Label text: ORIG 2350 `header + arrow + " (" + tfInner + " - " + confPct + "%)"` vs QI 713
   `header + ": " + string.Join(" + ", patterns) + " (" + confPct + "%)"`. Wording only; same event.
3. ORIG 2343 `GetTimeframeLabel()` (2321-2338) absent. Cosmetic.
4. Property renames `Show* → Use*`; `EnableLiquiditySweep` (ORIG 586, default true) absent.
   Equal at defaults.
5. ORIG 2113/2132 `cumDeltaAtLastSwing* = ComputeCumDelta10();` omitted. Not read by sweeps.
6. ORIG 670-671 `UpdateAsianSession`, 673 `DrawKeyLevelLines` omitted. Not read by sweeps.
7. ORIG 2361-2370 CSV + counters, 2375-2386 `Plots[24].Name` detail absent. Cosmetic.
8. QI `Values[1]` (Structure) is new; no ORIG plot to compare.
9. Gate: D0. Note the carry-over here is the longest of all modules (§0).

---

## C42 — `QI_OrderFlowPlus` (ORIG plot 27; event list)

**Verdict: CONFIRMED.** D0 impact: carry-over via swing structure and `volDelta` history (§0).

### ORIG evidence

Construction: 347 `atr14`, 358 `volSma20`, 357 `volDelta`, 451-454 `cumDeltaAtLastSwingHigh = 0;
cumDeltaAtLastSwingLow = 0; lastOfDir = 0; barsSinceLastOf = int.MaxValue;`. Order per bar:
558 `UpdateVolumeDelta()` → 1527 `Values[27][0] = 0;` → 586-587 `DetectLiquiditySweeps()` (which,
after its 2040 gate, calls 2043 `UpdateSwingPoints()` — the only caller) → 590-591
`if (EnableOrderFlow) ProcessOrderFlowSignals();`. Swing snapshot ORIG 2113 / 2132
`cumDeltaAtLastSwingHigh = ComputeCumDelta10();` taken on the confirming bar, after `lastSwingHigh`
is updated. ORIG 2411-2418 `ComputeCumDelta10`: `len = Math.Min(10, CurrentBar)`, sum of `volDelta[0..len-1]`.
ORIG 2420-2541 five patterns (0.78 / 0.65 / 0.60 / 0.55 / 0.70), first-come direction, duplicate
window, `Values[27][0] = bestConf;` (2529).

### QI evidence

QI 127-130 same instances; QI 145-148 same init. QI 156-169 order: gate 50 → `UpdateVolumeDelta()`
(QI 177-188 identical to ORIG 1623-1634) → `Values[0][0] = 0; Values[1][0] = 0;` →
`if (CurrentBar >= SwingLookback * 2 + 5) UpdateSwingPoints();` (equivalent to ORIG 2040's
`< ... return`) → `ProcessOrderFlowSignals()`.
QI 195-225 `UpdateSwingPoints`: ORIG 2090-2137 minus the equal-level pool (not read by OF+);
`cumDeltaAtLastSwing*` snapshot at the same point (QI 211, 223).
QI 232-239 `ComputeCumDelta10` identical. QI 241-345 `ProcessOrderFlowSignals`: patterns 1-5
textually identical to ORIG 2433-2499 (DeltaDiv `cumD10 < cumDeltaAtLastSwingHigh` /
`> cumDeltaAtLastSwingLow`, both halves may overwrite `ofDir`; Absorption `1.5 * volSma20`,
`range > 0.5 * atr14[0]`, `body < 0.30 * range`; Exhaustion `>=`/`<=` swing touch + strictly
declining |delta| over 3 bars; StackedDelta; DeltaRev with `Close[0] > Close[1]` / `< Close[1]`);
QI 322-323 same two returns; QI 325 `Math.Min(bestConf, 1.0)`; QI 340 `Values[0][0] = bestConf;`;
QI 343-344 `lastOfDir = ofDir; barsSinceLastOf = 0;`.

Event identity: ORIG 2515 `Draw.Text(this, tag, true, label, 0, anchor, offset, brush, ...)` ↔ QI
335; `anchor`/`offset` (±45) identical; fires on the same bars with the same `patterns[0]`,
`confPct`, direction.

### Differences

1. Label: ORIG 2508 `"OF+ " + (isBuy ? "Buy" : "Sell") + arrow + " (" + patterns[0] + " - " + confPct + "%)"`
   vs QI 328 `"OF+ " + patterns[0] + " (" + confPct + "%)"`. Wording only.
2. Tags `OFBuy_/OFSell_` → `OF_Bull_/OF_Bear_`; brushes `OfBuyBrush/OfSellBrush` →
   `OfBullishBrush/OfBearishBrush` (defaults Cyan / Magenta in both, ORIG 309-310, QI 116-117). Cosmetic.
3. ORIG 2520-2526 TP/SL, 2530-2531 `Plots[]` names, 2534-2538 CSV + counters absent.
4. Equal-level pool bookkeeping (ORIG 2104-2110, 2123-2129, 2135-2136) omitted. Not read by OF+.
5. ORIG's swing update is additionally gated by `EnableLiquiditySweep` (586) and the OF+ call by
   `EnableOrderFlow` (590), both default true; QI unconditional. Equal at defaults (if a user had
   disabled Liquidity Sweep in ORIG, OF+ would never have seen a swing — not reproducible and not
   in the default-parameter claim).
6. QI 129 `atrSma50 = SMA(atr14, 50)` is constructed but never read. Harmless.
7. QI `Values[1]` (Structure) new.
8. Gate: D0.

No value- or event-affecting differences at default parameters.

---

## C43 — `QI_SMC` (ORIG plot 29; event list)

**Verdict: CONFIRMED.** D0 impact: carry-over via swing structure, OB/FVG lists, `lastBosBar` (§0).

### ORIG evidence

Construction: 347 `atr14`, 457-461 lists + `smcTrendDir = 0; lastSmcDir = 0; barsSinceLastSmc =
int.MaxValue; lastBosBar = 0;`. Order: 1531 `Values[29][0] = 0;` → 586-587 `DetectLiquiditySweeps()`
(→ `UpdateSwingPoints`) → 592-593 `if (EnableSmc) ProcessSmcSignals();` (after OF+; OF+ writes no
SMC state). ORIG 2548-2739: trend update (HH+HL → 1, LH+LL → −1, else unchanged), OB maintenance
(`CurrentBar >= 2 && range > 0 && body > 0.75 * range && range > 1.5 * atrVal`, cap 5 per side,
records bar `CurrentBar - 1`), FVG (`Low[0] > High[2]` / `High[0] < Low[2]`, cap 5), expiry
`> 100` / `> 50`, patterns OB Retest 0.72 (consume + break), FVG 0.68, BOS 0.60 on **prev** swing
with shared `lastBosBar` cooldown `> 5`, CHoCH 0.75, Displacement 0.58; duplicate window;
`Values[29][0] = bestConf;` (2726).

### QI evidence

QI 144-147 instances, 162-166 same init. QI 176-191 order: gate 50 → `UpdateVolumeDelta()` →
`Values[0][0] = 0; Values[1][0] = 0;` → `if (CurrentBar >= SwingLookback * 2 + 5) UpdateSwingPoints();`
→ `ProcessSmcSignals();` → `trendDirSeries[0] = smcTrendDir;`.
QI 217-245 `UpdateSwingPoints`: ORIG 2090-2137 minus equal-level pool and minus `cumDeltaAtLastSwing*`
(neither read by SMC); `prevSwing*`/`lastSwing*` updated identically.
QI 252-426 `ProcessSmcSignals`: textually identical to ORIG 2548-2700 (checked each threshold,
each list cap/expiry, each `break`, each `if (smcDir == 0)`, the two BOS blocks and `lastBosBar`
updates), then QI 403-404 same two returns, QI 406 `Math.Min`, QI 421 `Values[0][0] = bestConf;`,
QI 424-425 `lastSmcDir = smcDir; barsSinceLastSmc = 0;`.

Event identity: ORIG 2713 `Draw.Text(... anchor, offset(±20) ...)` ↔ QI 416, same bars, same
`patterns[0]`, `confPct`, direction.

### Differences

1. Label: ORIG 2706 `"SMC " + (isBuy ? "Buy" : "Sell") + arrow + " (" + patterns[0] + " - " + confPct + "%)"`
   vs QI 409 `"SMC " + patterns[0] + " (" + confPct + "%)"`. Wording only.
2. Tags `SmcBuy_/SmcSell_` → `SMC_Bull_/SMC_Bear_`; brushes renamed, defaults DeepSkyBlue /
   OrangeRed in both (ORIG 314-315, QI 133-134). Cosmetic.
3. ORIG 2718-2723 TP/SL, 2727-2729 `Plots[]` names, 2732-2736 CSV + counters absent.
4. `EnableLiquiditySweep` / `EnableSmc` gates (defaults true) absent. Equal at defaults.
5. QI 145-147 `volSma20`, `atrSma50`, `volDelta` constructed/maintained but not read by SMC logic.
   Harmless.
6. QI `Values[1]` (Structure) and `TrendDir` series new.
7. Gate: D0.

No value- or event-affecting differences at default parameters.

---

## C44 — `QI_KeyLevels` (no ORIG plot; eight level values)

**Verdict: CONFIRMED by reading** (all eight level trackers and the drawing are textually identical).
D0 impact: on intraday charts ORIG's `prevDayHigh/Low` lag one session, `orbHigh/Low` and Asian H/L
of the skipped session(s) are absent, and `klMonthlyHigh/Low` can differ for the rest of the month (§0).

### ORIG evidence

Init ORIG 370-403 (`cstZone = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time")`,
MinValue/MaxValue/NaN seeds, `klCurrentMonth = 0`). Call ORIG 551 / 605 `UpdateKeyLevels();` first
thing after the gate. ORIG 656-674 dispatcher (CST conversion via
`Core.Globals.GeneralOptions.TimeZoneInfo`), 681-715 prev-day RTH (weekend skip, date roll with
`todayRthStarted` guard, window `8:30 ≤ t < 16:00`), 720-735 monthly (reset on `cstTime.Month`
change), 749-791 ORB (weekend skip, archive to `prevOrb*` only if `orbComplete`, window
`8:30 ≤ t < 9:00`, complete at `t >= 9:00 && orbHigh > MinValue`), 815-860 Asian (trading-date
roll at 17:00, window `t >= 17:00 || t < 2:00`, complete `2:00 ≤ t < 17:00`), 869-1010 drawing
(`minMove = TickSize > 0 ? TickSize : 0.25`, redraw when moved `> minMove`, labels every bar).

### QI evidence

QI 142-175 same init value-for-value. QI 183-187 gate 50 → `UpdateKeyLevels()`. QI 195-213
dispatcher identical (same four toggles, defaults true, ORIG 271-273/295 ↔ QI 120-123). QI 220-254,
259-274, 287-329, 334-346, 353-398: textually identical to ORIG 681-860. QI 408-549
`DrawKeyLevelLines`: textually identical to ORIG 869-1010 (same tags, dash styles, widths,
offsets ±5, label formats `"... - $" + x.ToString("F2")`, same brush properties with the same
defaults ORIG 285-292 ↔ QI 127-134).

### Differences

1. No code differences in tracking or drawing. (Header research bullets at ORIG 740-744 trimmed —
   comment only.)
2. Observability note for Channel B, not a fidelity difference: QI_KeyLevels exposes no
   `Series<double>` for the eight levels (CONVENTIONS rule 8 is not applied here), so "the eight
   level values per bar" are only reachable through the drawn `HorizontalLine` objects (updated only
   when a level moves by more than one tick) or the label strings (`F2`). The ledger's 4-decimal
   comparison cannot be made from the published surface as written.
3. Gate: D0 (with the long carry-over listed above).

---

## Verdict table

| claim | module | verdict (bars ORIG processes) | D0 carry-over on intraday charts |
|---|---|---|---|
| C32 | QI_HedgingPressure | CONFIRMED | lines 5/20 bars |
| C33 | QI_VWAPDistance | CONFIRMED (formula); D0 governs the whole intraday scope | until next day change |
| C34 | QI_MACDHistogram | CONFIRMED | none |
| C35 | QI_EMACross | CONFIRMED | none |
| C36 | QI_SMA200Trend | CONFIRMED | none |
| C37 | QI_ATRRegime | CONFIRMED | none |
| C38 | QI_VolumeSpike | CONFIRMED | none |
| C39 | QI_VolumeDelta | CONFIRMED | 20 / 10 bars |
| C40 | QI_ChopIndex | CONFIRMED | none |
| C41 | QI_LiquiditySweep | **REFUTED** (plot on Start-label bars); events CONFIRMED | long |
| C42 | QI_OrderFlowPlus | CONFIRMED | long |
| C43 | QI_SMC | CONFIRMED | long |
| C44 | QI_KeyLevels | CONFIRMED (code); levels not exposed for the harness | long |

Open item for the orchestrator: D0 (§0) — decide whether the intraday comparison window starts at
bar 50 (then every stateful module above fails on a 5-minute chart) or at ORIG's first processed bar
plus the per-module carry-over.
