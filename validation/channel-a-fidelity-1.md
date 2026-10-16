# Channel A — static fidelity audit, claims C18–C31

Auditor: Channel A (static source reading only; nothing executed).
Specification: ORIG = `C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\IBSFade.cs` (3,230 lines).
Code under audit: `C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators\indicators\QI_*.cs`.
Also read (shipped source, allowed for Channel A): `...\bin\Custom\Indicators\@RSI.cs` lines 44-113, only to bound how long a streak-state difference persists inside `RSI(streakSeries, 2, 1)`.

Verdict rule applied: CONFIRMED = no difference that can change any plotted value on any bar ≥ 50 on any chart the claim covers; REFUTED = a difference that changes a value, with the first bar/condition named; UNVERIFIABLE = cannot be decided by reading.

Summary: CONFIRMED 11 (C18, C19, C21, C22, C24, C26, C27, C28, C29, C30, C31); REFUTED 3 (C20, C23, C25 — all three fail only on intraday charts, for the same reason, and are confirmed on daily/non-intraday charts); UNVERIFIABLE 0.

---

## 0. Cross-cutting finding: ORIG's warm-up gate has a second term on intraday charts

ORIG runs every module from a single `OnBarUpdate` with two branches:

ORIG 535-538 (intraday chart, `useDailySeries == true`, set at ORIG 325 `useDailySeries = Bars.BarsType.IsIntraday;`):
```
if (useDailySeries)
{
    if (CurrentBars[0] < 50 || CurrentBars[1] < 1)
        return;
```
ORIG 599-602 (daily / non-intraday chart):
```
else
{
    if (CurrentBar < 50)
        return;
```

Everything the C18–C31 values depend on (`UpdateNewAlphas()` at ORIG 559/611, which owns `consecUpDays`, `consecDownDays`, `streakSeries`, `overnightGapPct`, `rvZscoreSeries`, `atrChangeSeries`; and `UpdateDataBoxValues()` at ORIG 581/633) runs only after this gate. A grep of ORIG confirms no other statement writes those fields: `consecUpDays`/`consecDownDays` are written only at ORIG 406-407 (init) and 1558-1564; `streakSeries[0]` only at 1555/1568; `rvZscoreSeries[0]` only at 1588/1592; `atrChangeSeries[0]` only at 1596; `overnightGapPct` only at 408/1571; `dailyIBS` only at 331/543/555.

Of the fourteen ported files, only `QI_IBS.cs` reproduces the intraday term (`QI_IBS.cs` 99: `if (CurrentBars[0] < 50 || CurrentBars[1] < 1)`). The other thirteen either gate on `CurrentBar < 50` alone or have no gate.

Consequence. On an intraday chart (NT's `IsIntraday` is true for minute, second, tick, range, renko… bar types), `CurrentBars[1]` cannot reach 1 until the 1-day secondary series has advanced past its first bar, i.e. not within the first session day. For any bar period with more than 50 primary bars in the first session day (1-min, 5-min, 15-min, 30-min on 24h data, tick/range charts), `CurrentBars[1] < 1` is still true at `CurrentBars[0] == 50`, so ORIG's first executed bar is some S > 50 (the first primary bar after the daily series index reaches 1), while the QI files start at bar 50 (or 0). Define S that way below. The exact value of S depends on NinjaTrader's secondary-series indexing (whether `CurrentBars[1]` counts the forming daily bar or only closed ones); reading cannot pin S to a number, but reading does establish S > 50 on the chart types just listed, which is all the verdicts below need.

Effect by module class:
- Stateless modules (value recomputed from built-in indicator outputs and the current bar only: C19, C21, C22, C24, C26, C27, C28, C29, C30, C31): on bars 50..S-1 of an intraday chart ORIG assigns no value at all (and its EveryBar CSV at ORIG 596-597 writes no row, since the logger is also behind the gate), so there is nothing to compare; on bars ≥ S the computations are identical. No value difference on any bar where ORIG has a value. CONFIRMED, with this scope note.
- Stateful modules (value depends on counters or private series accumulated across bars: C20, C23, C25): ORIG's state starts accumulating at S, the QI file's at 50 (or 0). The values differ from bar S for the duration stated in each section. REFUTED on intraday charts; CONFIRMED on daily/non-intraday charts, where both gates reduce to `CurrentBar < 50`.

Module map (CONVENTIONS.md): the line ranges given for each module are correct pointers to the construction and value lines, but the map never cites ORIG 535-538 / 599-602, and in particular not the `CurrentBars[1] < 1` term. Three file headers (QI_ConnorsRSI 28-30, QI_CompositeVol 28-30, QI_ConsecDays 21-25) and the map's "counters start at bar 50" notes (ledger C20, C25) describe only the non-intraday branch. The map is incomplete in exactly the place where the port diverges.

---

## C18 — `QI_IBS` vs ORIG plot 1

Verdict: CONFIRMED.

Extra scope (ledger): "on an intraday chart, value comes from the daily series" — reproduced, see (b) below.

(a) Construction. ORIG 325-327:
```
useDailySeries = Bars.BarsType.IsIntraday;
if (useDailySeries)
    AddDataSeries(Data.BarsPeriodType.Day, 1);
```
ORIG 331: `dailyIBS = 0.5;`
QI_IBS 80-82: `useDailySeries = Bars.BarsType.IsIntraday; if (useDailySeries) AddDataSeries(Data.BarsPeriodType.Day, 1);` QI_IBS 89: `dailyIBS = 0.5;`

(b) State updates, intraday branch. ORIG 537-555:
```
if (CurrentBars[0] < 50 || CurrentBars[1] < 1) return;
if (BarsInProgress == 1)
{
    double range = High[0] - Low[0];
    dailyIBS = (range > 0) ? (Close[0] - Low[0]) / range : 0.5;
    return;
}
if (BarsInProgress != 0) return;
...
double liveRange = Highs[1][0] - Lows[1][0];
if (liveRange > 0)
    dailyIBS = (Closes[1][0] - Lows[1][0]) / liveRange;
```
QI_IBS 99-116: identical text, same order (gate → BIP 1 recompute-and-return → BIP ≠ 0 return → live update from `Highs[1][0]`/`Lows[1][0]`/`Closes[1][0]`). ORIG's `UpdateKeyLevels()` at 551 sits between the BIP check and the live update; it does not touch `dailyIBS` (grep above), so its removal is value-neutral.

Daily branch. ORIG 601-608: `if (CurrentBar < 50) return; ... double range = High[0] - Low[0]; double ibs = (range > 0) ? (Close[0] - Low[0]) / range : 0.5;` QI_IBS 122-126: identical, assigned straight into `Values[0][0]`.

(c) Value. ORIG 1268: `Values[1][0] = ibs;` where `ibs` is `dailyIBS` (ORIG 581) or the local `ibs` (ORIG 633). QI_IBS 118 / 126: `Values[0][0] = dailyIBS;` / `Values[0][0] = (range > 0) ? ... : 0.5;`

Differences: no differences.

---

## C19 — `QI_RSI2` vs ORIG plot 2

Verdict: CONFIRMED.

(a) ORIG 342: `rsi2 = RSI(Close, 2, 1);` — QI_RSI2 85: `rsi2 = RSI(Close, 2, 1);`
(b) No module state. Gate: ORIG 601 `if (CurrentBar < 50)` — QI_RSI2 93 `if (CurrentBar < 50)`. Intraday: ORIG 537 has the extra `CurrentBars[1] < 1` term; QI does not (see §0; stateless, so no value difference on any bar where ORIG has a value).
(c) ORIG 1273: `Values[2][0] = rsi2[0];` — QI_RSI2 97: `Values[0][0] = rsi2[0];`

Differences:
1. Gate term (ORIG 537 `|| CurrentBars[1] < 1` absent at QI_RSI2 93). Value-neutral: `rsi2` is a child indicator that updates on every bar regardless of the parent's gate, and the plotted value is `rsi2[0]` with no carried state. On bars 50..S-1 of an intraday chart ORIG has no value; on every bar where it has one the two are equal.

---

## C20 — `QI_ConnorsRSI` vs ORIG plot 3

Verdict: REFUTED on intraday charts (first differing bar: S, defined in §0, whenever S ≥ 100; see below); CONFIRMED on daily/non-intraday charts.

Extra scope (ledger): "50 until bar 100; streak counters start at bar 50" — both true on non-intraday charts only.

(a) Construction. ORIG 342 `rsi2 = RSI(Close, 2, 1);`, 406-407 `consecDownDays = 0; consecUpDays = 0;`, 410-411 `streakSeries = new Series<double>(this); rsiStreak = RSI(streakSeries, 2, 1);`
QI_ConnorsRSI 100-104: `consecDownDays = 0; consecUpDays = 0; rsi2 = RSI(Close, 2, 1); streakSeries = new Series<double>(this); rsiStreak = RSI(streakSeries, 2, 1);` — identical.

(b) State update and order. ORIG: gate (537/601) → `UpdateNewAlphas()` (559/611) → `UpdateDataBoxValues()` (581/633). `UpdateNewAlphas` 1555-1568:
```
if (CurrentBar < 1) { streakSeries[0] = 0; return; }
if (Close[0] > Close[1]) { consecUpDays++; consecDownDays = 0; }
else if (Close[0] < Close[1]) { consecDownDays++; consecUpDays = 0; }
// else: unchanged, keep counts
streakSeries[0] = consecUpDays > 0 ? consecUpDays : -consecDownDays;
```
QI_ConnorsRSI 112-116 gate then `UpdateStreak()`; 141-157 identical text to ORIG 1555-1568. Order (streak update before value) preserved.

(c) Value. ORIG 1278-1294 vs QI_ConnorsRSI 119-135: compared token by token — `double crsiVal = 50;`, `if (CurrentBar >= 100)`, `rsiP = rsi2[0]`, `rsiS = rsiStreak[0]`, `tRoc = Close[0] - Close[1]`, `total = Math.Min(100, CurrentBar)`, loop `for (int i = 1; i <= total; i++)`, `pRoc = Close[i] - (i + 1 < CurrentBar ? Close[i + 1] : Close[i])`, `if (pRoc < tRoc) below++`, `pRank = (double)below / total * 100.0`, `crsiVal = (rsiP + rsiS + pRank) / 3.0`, `Values[3][0] = crsiVal` ↔ `Values[0][0] = crsiVal`. Identical.

Differences:
1. Gate. ORIG 537: `if (CurrentBars[0] < 50 || CurrentBars[1] < 1) return;` — QI_ConnorsRSI 112: `if (CurrentBar < 50) return;`. On daily charts ORIG uses 601 `if (CurrentBar < 50)`, identical.
   Effect on intraday charts: QI increments the counters and writes `streakSeries[0]` from bar 50; ORIG first does so at bar S > 50, and ORIG's `streakSeries` on bars < S is never assigned (reads as the series default). Two state channels then differ:
   - Counters: at bar S ORIG's counter is 1 (or both 0 on an unchanged close); QI's is the run length accumulated since bar 50. Equal again only after the first close-to-close reversal at or after S.
   - `rsiStreak`: `@RSI.cs` 99-100 with Period 2 is `avgDown[0] = (avgDown[1] * 1 + down[0]) / 2; avgUp[0] = (avgUp[1] * 1 + up[0]) / 2;` — a recursion that halves any past difference each bar. ORIG's `up`/`down` inputs on bars 50..S-1 are the differences of unassigned (default) values, QI's are differences of real streak values; so `rsiStreak[0]` differs at bar S by an amount of order tens of RSI points, and after the inputs agree it still differs by a factor 2^-n per bar, which stays above the ledger tolerance (0.00005 on a value divided by 3) for roughly 20 bars.
   First differing plotted bar: `crsiVal` is 50 until `CurrentBar >= 100` in both files, so the first differing plotted bar is bar S when S ≥ 100 (true for 1-min, 5-min and 15-min charts, where S is at least one full session day of bars), and bar 100 if 50 < S < 100 and the state has not yet converged (not decidable by reading; it depends on when the first reversal after S falls).
2. Header comment QI_ConnorsRSI 28-30 ("streak counting also starts at bar 50 exactly as it did in ORIG") is true only for the non-intraday branch. Documentation only.

---

## C21 — `QI_StochFade` vs ORIG plot 4 (%K), %D vs `StochasticsFast(3,14).D`

Verdict: CONFIRMED.

(a) ORIG 350: `stoch = StochasticsFast(3, 14);` — QI_StochFade 88: `stoch = StochasticsFast(3, 14);` (same argument order: periodD = 3, periodK = 14).
(b) No module state. Gate: ORIG 601 / QI_StochFade 96 `if (CurrentBar < 50)`; intraday term absent (see §0, stateless).
(c) ORIG 1299: `Values[4][0] = stoch.K[0];` — QI_StochFade 100: `Values[0][0] = stoch.K[0];`. Extra scope: QI_StochFade 101 `Values[1][0] = stoch.D[0];` is exactly the ledger's comparator (`StochasticsFast(3,14).D`), read from the same instance.

Differences:
1. Gate term (ORIG 537 `|| CurrentBars[1] < 1` absent at QI_StochFade 96). Value-neutral, as for C19.

---

## C22 — `QI_RVZScore` vs ORIG plot 5

Verdict: CONFIRMED.

(a) ORIG 347: `atr14 = ATR(14);`, 418: `rvZscoreSeries = new Series<double>(this);` — QI_RVZScore 89: `atr14 = ATR(14);` (no private series; the value goes straight to the plot).
(b) ORIG 1574-1593 inside `UpdateNewAlphas` (after the gate and after the 1555 bar-0 early return):
```
if (CurrentBar >= 25)
{
    double atrMean = 0;
    int lookback = Math.Min(20, CurrentBar);
    for (int i = 0; i < lookback; i++) atrMean += atr14[i];
    atrMean /= lookback;
    double atrSumSq = 0;
    for (int i = 0; i < lookback; i++) { double diff = atr14[i] - atrMean; atrSumSq += diff * diff; }
    double atrStd = Math.Sqrt(atrSumSq / lookback);
    rvZscoreSeries[0] = atrStd > 0 ? (atr14[0] - atrMean) / atrStd : 0;
}
else { rvZscoreSeries[0] = 0; }
```
QI_RVZScore 97-117: identical statements (`rvZ` local instead of `rvZscoreSeries[0]`).
(c) ORIG 1304: `Values[5][0] = rvZscoreSeries[0];` — QI_RVZScore 119: `Values[0][0] = rvZ;`

Differences:
1. QI_RVZScore has no `CurrentBar < 50` gate at all (ORIG 537/601). Value-neutral for bars ≥ 50: the value is a pure function of `atr14[0..19]` and `CurrentBar` on the current bar; `atr14` is a child indicator unaffected by the parent gate; no state carries across bars. Bars < 50 are out of the ledger scope. Intraday term also absent; same argument.

---

## C23 — `QI_CompositeVol` vs ORIG plot 6

Verdict: REFUTED on intraday charts (first differing bar: S, defined in §0); CONFIRMED on daily/non-intraday charts, including the ledger's extra scope "bars 50-58 where ORIG's series bleed is reproduced".

(a) Construction. ORIG 347 `atr14 = ATR(14);`, 415 `atrChangeSeries = new Series<double>(this);`, 416-418 `closeSma20z = SMA(Close, 20); closeStdDev20 = StdDev(Close, 20); rvZscoreSeries = new Series<double>(this);` — QI_CompositeVol 99-103: `atr14 = ATR(14); closeSma20z = SMA(Close, 20); closeStdDev20 = StdDev(Close, 20); rvZscoreSeries = new Series<double>(this); atrChangeSeries = new Series<double>(this);` Identical.

(b) State update and order. ORIG: gate → `UpdateNewAlphas()` which sets `rvZscoreSeries[0]` (1588/1592, quoted under C22) and 1596 `atrChangeSeries[0] = CurrentBar >= 2 ? atr14[0] - atr14[1] : 0;` → `UpdateDataBoxValues()`. QI_CompositeVol 111-115: gate `if (CurrentBar < 50) return;` then `UpdateVolSeries()` (144-177: rvZ block identical to ORIG 1574-1593; 176 `atrChangeSeries[0] = CurrentBar >= 2 ? atr14[0] - atr14[1] : 0;`), then the value. Order preserved. QI 146-151 (`if (CurrentBar < 1) { rvZscoreSeries[0] = 0; atrChangeSeries[0] = 0; return; }`) differs textually from ORIG 1555 (which returns without assigning those two series) but is unreachable behind the bar-50 gate in both files.

Bars 50-58 on a daily chart: in ORIG, `atrChangeSeries[i]` for bars < 50 is never assigned (only writer is 1596, behind the gate); in QI likewise (only writer is 176, behind the gate at 111). Both files read the same unassigned-series default for the same `i` in the `ccvLen = Math.Min(10, CurrentBar)` window, so the "bleed" is reproduced exactly, whatever that default is.

(c) Value. ORIG 1309-1328 vs QI_CompositeVol 118-137, token by token: `compVal = 0`; `if (CurrentBar >= 30 && closeStdDev20[0] > 0)`; `cc1 = rvZscoreSeries[0]`; `cc2 = (Close[0] - closeSma20z[0]) / closeStdDev20[0]`; `ccvLen = Math.Min(10, CurrentBar)`; mean loop over `atrChangeSeries[i]`; `ccvovMean /= ccvLen`; sum-of-squares loop; `ccvov = atr14[0] > 0 ? Math.Sqrt(ccvovSumSq / ccvLen) / atr14[0] : 0`; `cc3z = (ccvov - 0.15) / 0.10`; `compVal = 0.40 * cc1 + 0.35 * (-cc2) + 0.25 * cc3z`; `Values[6][0] = compVal` ↔ `Values[0][0] = compVal`. Identical; constants 0.40/0.35/0.25/0.15/0.10 verbatim.

Differences:
1. Gate. ORIG 537 `if (CurrentBars[0] < 50 || CurrentBars[1] < 1) return;` — QI_CompositeVol 111 `if (CurrentBar < 50) return;`. On intraday charts QI assigns `atrChangeSeries[0]` on bars 50..S-1; ORIG leaves them unassigned. At bar S ORIG's vol-of-vol window therefore contains up to 9 default entries where QI's contains `atr14[0]-atr14[1]` of real bars, so `ccvov`, `cc3z` and `compVal` differ at bar S and on each bar through S+8 (the 10-bar window), unless those nine ATR changes are all exactly zero. `rvZscoreSeries[0]` (cc1) is same-bar and does not contribute to the difference.
2. Header comment QI_CompositeVol 28-30 ("only the per-signal guards are kept here, as in the template") contradicts the code at 110-112, which does keep the bar-50 gate. The code is what was audited; the comment is wrong, not the value.

---

## C24 — `QI_TurnOfMonth` vs ORIG plot 7

Verdict: CONFIRMED.

(a) ORIG 370: `cstZone = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");` — QI_TurnOfMonth 85: identical.
(b) No module state.
(c) ORIG 1333-1338:
```
DateTime cstT = TimeZoneInfo.ConvertTime(Time[0], Core.Globals.GeneralOptions.TimeZoneInfo, cstZone);
int dom = cstT.Day;
int dim = DateTime.DaysInMonth(cstT.Year, cstT.Month);
bool tom = dom >= (dim - 3) || dom <= 3;
Values[7][0] = tom ? 1 : 0;
```
QI_TurnOfMonth 98-103: identical (`Values[0][0]`). QI 105-106 additionally sets `BackBrush` — display only, no effect on the plotted series.

Differences:
1. No `CurrentBar < 50` gate in QI (ORIG 537/601). Value-neutral for bars ≥ 50: pure function of `Time[0]`. Intraday term likewise.

---

## C25 — `QI_ConsecDays` vs ORIG plot 8

Verdict: REFUTED on intraday charts (first differing bar: S, defined in §0, when bar S continues or is flat relative to bar S-1); CONFIRMED on daily/non-intraday charts.

Extra scope (ledger): "counters start at bar 50" — true on non-intraday charts only.

(a) ORIG 406-407: `consecDownDays = 0; consecUpDays = 0;` — QI_ConsecDays 90-91: identical.
(b) ORIG 1555-1565 (quoted under C20) — QI_ConsecDays 103-114: identical text, including the dead `if (CurrentBar < 1)` line (103) that ORIG also has behind the gate. ORIG 1568 writes `streakSeries[0]`, which QI omits; nothing in plot 8 reads it.
(c) ORIG 1343-1344: `int streak = consecUpDays > 0 ? consecUpDays : -consecDownDays; Values[8][0] = streak;` — QI_ConsecDays 117-118: identical (`Values[0][0]`).

Differences:
1. Gate. ORIG 537 `if (CurrentBars[0] < 50 || CurrentBars[1] < 1) return;` — QI_ConsecDays 99 `if (CurrentBar < 50) return;`. On intraday charts QI's counters accumulate from bar 50, ORIG's from bar S > 50. At bar S: ORIG's counter is 1 (direction of bar S) or stays 0 (flat close, streak 0); QI's is the run length since bar 50 in that direction, or the previous run on a flat close. The plotted values differ at bar S whenever bar S-1 closed in the same direction as bar S, or bar S is a flat close — and then on every following bar until the first close-to-close reversal, after which both reset to 1 and agree permanently. If bar S itself is a reversal relative to S-1, both are 1 and no difference ever appears.
2. Header comment QI_ConsecDays 21-25 ("this standalone starts at bar 1, so values can differ from ORIG until the first close-to-close reversal after bar 50") contradicts the code at 99, which gates at bar 50. Comment is wrong, code is the non-intraday port.

---

## C26 — `QI_OvernightGap` vs ORIG plot 9

Verdict: CONFIRMED.

(a) ORIG 408: `overnightGapPct = 0;` — no construction needed in QI (local).
(b) ORIG 1571: `overnightGapPct = CurrentBar >= 1 ? (Open[0] - Close[1]) / Close[1] * 100.0 : 0;` — QI_OvernightGap 90: `double overnightGapPct = CurrentBar >= 1 ? (Open[0] - Close[1]) / Close[1] * 100.0 : 0;`
(c) ORIG 1349: `Values[9][0] = overnightGapPct;` — QI_OvernightGap 91: `Values[0][0] = overnightGapPct;`

Differences:
1. No `CurrentBar < 50` gate in QI (ORIG 537/601). Value-neutral for bars ≥ 50: ORIG recomputes the field on every executed bar from `Open[0]`/`Close[1]` only, so no earlier state is read. Intraday term likewise.

---

## C27 — `QI_BollingerPctB` vs ORIG plot 10

Verdict: CONFIRMED.

(a) ORIG 349: `boll = Bollinger(Close, 2, 20);` — QI_BollingerPctB 91: `boll = Bollinger(Close, 2, 20);`
(b) No module state. Gate: ORIG 601 / QI 99 `if (CurrentBar < 50)`.
(c) ORIG 1354-1357:
```
double bollMid = boll[0];
double bollBandWidth = boll.Upper[0] - boll.Lower[0];
double bollPct = bollBandWidth > 0 ? (Close[0] - bollMid) / (bollBandWidth * 0.5) * 100.0 : 0;
Values[10][0] = bollPct;
```
QI_BollingerPctB 103-106: identical (`Values[0][0]`). ORIG 1358-1359 (the `0.001 * atr14[0]` band-touch classification) only feeds the plot *name*, not the value, so its omission is value-neutral.

Differences:
1. Gate term (ORIG 537 `|| CurrentBars[1] < 1` absent at QI 99). Value-neutral, stateless.

---

## C28 — `QI_TurnaroundTuesday` vs ORIG plot 11

Verdict: CONFIRMED.

(a) ORIG 370 (cstZone) — QI_TurnaroundTuesday 84: identical.
(b) No module state.
(c) ORIG 1333-1334 (conversion, quoted under C24) and 1363-1364: `int dow = (int)cstT.DayOfWeek; Values[11][0] = dow;` — QI_TurnaroundTuesday 97-102: identical conversion and `int dow = (int)cstT.DayOfWeek; Values[0][0] = dow;`. QI 104-105 `BackBrush` on Monday is display only.

Differences:
1. No `CurrentBar < 50` gate in QI (ORIG 537/601). Value-neutral for bars ≥ 50: pure function of `Time[0]`.

---

## C29 — `QI_RSI14` vs ORIG plot 12

Verdict: CONFIRMED.

(a) ORIG 343: `rsi14 = RSI(Close, 14, 1);` — QI_RSI14 85: `rsi14 = RSI(Close, 14, 1);`
(b) No module state. Gate: ORIG 601 / QI 93 `if (CurrentBar < 50)`.
(c) ORIG 1369: `Values[12][0] = rsi14[0];` — QI_RSI14 97: `Values[0][0] = rsi14[0];`

Differences:
1. Gate term (ORIG 537 `|| CurrentBars[1] < 1` absent at QI 93). Value-neutral, stateless.

---

## C30 — `QI_VRPProxy` vs ORIG plot 13

Verdict: CONFIRMED.

(a) ORIG 347: `atr14 = ATR(14);`, 414: `atr5 = ATR(5);` — QI_VRPProxy 83-84: `atr5 = ATR(5); atr14 = ATR(14);`
(b) No module state.
(c) ORIG 1374-1375: `double vrpVal = CurrentBar >= 20 && atr14[0] > 0 ? atr5[0] / atr14[0] : 1.0; Values[13][0] = vrpVal;` — QI_VRPProxy 92-93: `double vrpVal = CurrentBar >= 20 && atr14[0] > 0 ? atr5[0] / atr14[0] : 1.0; Values[0][0] = vrpVal;`

Differences:
1. No `CurrentBar < 50` gate in QI (ORIG 537/601). Value-neutral for bars ≥ 50: pure function of two child-indicator outputs on the current bar.

---

## C31 — `QI_WideRangeBar` vs ORIG plot 14

Verdict: CONFIRMED.

(a) ORIG 347: `atr14 = ATR(14);` — QI_WideRangeBar 80: `atr14 = ATR(14);`
(b) No module state.
(c) ORIG 1380-1381: `double rangeAtrRatio = atr14[0] > 0 ? (High[0] - Low[0]) / atr14[0] : 1.0; Values[14][0] = rangeAtrRatio;` — QI_WideRangeBar 88-89: `double rangeAtrRatio = atr14[0] > 0 ? (High[0] - Low[0]) / atr14[0] : 1.0; Values[0][0] = rangeAtrRatio;`

Differences:
1. No `CurrentBar < 50` gate in QI (ORIG 537/601). Value-neutral for bars ≥ 50: pure function of the current bar and `atr14[0]`.

---

## What would settle the three REFUTED rows

A runtime diff on an intraday chart (5-min is enough) for QI_ConnorsRSI, QI_CompositeVol and QI_ConsecDays against ORIG's EveryBar CSV, looking at ORIG's first logged bar S and the following ~20 bars. The same diff on a daily chart should show zero mismatches for all fourteen. If the ledger's intended scope for C20/C23/C25 is daily charts only, the split axis is the one the ledger already names ("input subdomain (intraday vs daily)"), and the daily half of each row is CONFIRMED by this reading. The fix, if intraday fidelity is wanted, is mechanical: reproduce ORIG 325-327 (`useDailySeries`, `AddDataSeries(Day, 1)`) and the two-term gate of ORIG 537 in those three files, as `QI_IBS.cs` 80-82 / 99 already does.
