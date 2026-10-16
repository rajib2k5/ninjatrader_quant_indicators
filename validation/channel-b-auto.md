# Channel B (runtime auditor) — automated probes

date: 2026-10-15
ledger: `validation/claims-ledger.md` (FROZEN 2026-10-15); env: `validation/env-pin.txt`
scope: C13, C17, C15, C16, and the compile-decidable halves of C1–C12. C14 and C18–C44 are NinjaTrader
runtime probes executed by the orchestrator and are listed here only as **pending runtime**.
No documentation, help guide, changelog or web page was consulted. No channel-a file was read.

## 0. Toolchain and sandbox actually in effect

```
dotnet --version                                  -> 8.0.100
dotnet exec ...\sdk\8.0.100\Roslyn\bincore\csc.dll -version -> 4.8.0-3.23524.11 (f43cd10b)   (C# 12 at -langversion:latest)
NinjaTrader.Core.dll  6,715,752 B  (Sep 29)   NinjaTrader.Gui.dll 14,060,392 B (Sep 29)   [FileVersion 8.1.8.3 per env-pin]
NinjaTrader.Custom.dll 1,422,848 B (Oct 11 13:52)
compile_probe.sh resolved refs: 17 (13 listed + 4 SharpDX*.dll); zero "WARN: missing reference" lines in any run
bash  = Git for Windows bash; grep = GNU grep (Git for Windows); sha256sum = coreutils
PowerShell 5.1.26100.9549, CLR 4.0.30319.42000 (used only for the supplementary C10 time-zone probe)
```

Sandbox note (deviation from the field manual's Linux `env -i … unshare --net` recipe, which does not exist on
this Windows host): every compile wrote its output DLL only under
`C:\Users\rajib\AppData\Local\Temp\claude\…\scratchpad\egv\chanB\` (via `OUT=`); every mutant was built from a
*copy* in that scratch tree; csc needs no network. Repo integrity is enforced instead by sha256 of all 27 originals
taken before the first probe and re-diffed after the mutant runs (section 6): **IDENTICAL**.

Wrapper self-test: the probe is shown to pass on real input (27/27 rc=0, section 1) *and* to fail on a known-bad
input (C13 type-error mutant, CS0029, rc=1, section 2) before any verdict is drawn from it.

## 1. C13 — every QI_*.cs compiles standalone (one file per csc invocation)

probe_cmd (per file, from repo root):
`OUT=<scratch>/out/<name>.dll bash validation/probes/compile_probe.sh indicators/<name>.cs`
Driver: `<scratch>/egv/chanB/run_c13.sh` (loops the exact command above over the 27 files; no other flags).

| file | rc | wall | csc diagnostics |
|---|---|---|---|
| QI_ATRRegime | 0 | 1.40s | (none) |
| QI_BollingerPctB | 0 | 1.41s | (none) |
| QI_ChopIndex | 0 | 1.43s | (none) |
| QI_CompositeVol | 0 | 1.52s | (none) |
| QI_ConnorsRSI | 0 | 1.30s | (none) |
| QI_ConsecDays | 0 | 1.29s | (none) |
| QI_EMACross | 0 | 1.38s | (none) |
| QI_HedgingPressure | 0 | 1.82s | (none) |
| QI_IBS | 0 | 2.12s | (none) |
| QI_KeyLevels | 0 | 1.53s | (none) |
| QI_LiquiditySweep | 0 | 1.54s | (none) |
| QI_MACDHistogram | 0 | 1.35s | (none) |
| QI_OrderFlowPlus | 0 | 1.36s | (none) |
| QI_OvernightGap | 0 | 1.96s | (none) |
| QI_RSI14 | 0 | 2.14s | (none) |
| QI_RSI2 | 0 | 2.42s | (none) |
| QI_RVZScore | 0 | 2.40s | (none) |
| QI_SMA200Trend | 0 | 1.74s | (none) |
| QI_SMC | 0 | 1.60s | (none) |
| QI_StochFade | 0 | 1.84s | (none) |
| QI_TurnOfMonth | 0 | 1.63s | (none) |
| QI_TurnaroundTuesday | 0 | 1.63s | (none) |
| QI_VRPProxy | 0 | 1.59s | (none) |
| QI_VWAPDistance | 0 | 1.53s | (none) |
| QI_VolumeDelta | 0 | 1.56s | (none) |
| QI_VolumeSpike | 0 | 1.55s | (none) |
| QI_WideRangeBar | 0 | 1.46s | (none) |

Verbatim stdout of one run (all 27 are identical apart from the `out:` path):
```
csc: /c/Program Files/dotnet/sdk/8.0.100/Roslyn/bincore/csc.dll
out: /c/Users/rajib/AppData/Local/Temp/claude/C--Users-rajib-OneDrive-Documents/533a663d-5efe-42d6-aafd-bb6df2ee5fa2/scratchpad/egv/chanB/out/QI_IBS.dll
refs: 17  sources: 1
rc=0
```
stderr: empty for all 27 (`wc -c` of every `.err` = 0). `grep -il "warn\|error"` over all 54 log files: no match.
Artifacts: 27 DLLs present in `<scratch>/out/` (e.g. QI_ATRRegime.dll 6,656 B).

C13 falsifier (pre-registered: one type error in a copy):
```
falsifier_cmd: cp indicators/QI_RSI2.cs <scratch>/mut/C13_typeerr/QI_RSI2.cs
               sed -i 's/Lines\[0\]\.Value = LowerThreshold;/Lines[0].Value = "oops";/' <that copy>
               OUT=<scratch>/mut/C13_typeerr/QI_RSI2.dll bash validation/probes/compile_probe.sh <that copy>
diff (original vs mutant):
  80c80
  < 				Lines[0].Value = LowerThreshold;
  ---
  > 				Lines[0].Value = "oops";
csc stdout: ...\mut\C13_typeerr\QI_RSI2.cs(80,22): error CS0029: Cannot implicitly convert type 'string' to 'double'
            rc=1
falsifier_rc: 1
sha256 of the untouched original, before and after: fddeeff3da54ecb3b43113505a2d2bc582d3421566d0d3f02f404da483cd4dd2 *indicators/QI_RSI2.cs
```
Caveat carried from the probe script itself: Roslyn here is C# 12; NinjaTrader builds at LangVersion 13 (superset), so
"compiles here" ⇒ "compiles there" for language features, but the Tier-0 F5 build (C14) remains the authoritative gate.

**verdict C13: CONFIRMED** (27/27 rc=0; falsifier rc=1 with CS0029).

## 2. Compile-decidable API claims — falsifier mutants

Common procedure for every row (driver `<scratch>/egv/chanB/run_mutants.sh`): copy the original into
`<scratch>/mut/<id>/`, apply exactly ONE `sed` edit, `diff` original vs copy (diff_rc=1 proves the copy changed),
compile the copy with the pre-registered probe (`OUT=` in scratch), record rc and csc output verbatim.
Positive side for every row = the unmodified file's C13 line above (rc=0). Lines quoted are from the originals.

### C1 — `AddLine(Brush, double, string)` exists, called inside `State.SetDefaults`
file: QI_RSI2.cs:75 `AddLine(Brushes.DodgerBlue, 25, "Lower Threshold");` (inside `if (State == State.SetDefaults)`) — C13 rc=0.
falsifier (pre-registered: rename to AddLinee): sed `s/AddLine(Brushes\.DodgerBlue, 25, "Lower Threshold");/AddLinee(…);/`
```
75c75  < AddLine(Brushes.DodgerBlue, 25, "Lower Threshold");   > AddLinee(Brushes.DodgerBlue, 25, "Lower Threshold");
QI_RSI2.cs(75,5): error CS0103: The name 'AddLinee' does not exist in the current context
rc=1
```
**verdict C1 (existence/signature/callable-from-SetDefaults half): CONFIRMED.** "the line is drawn" half: pending runtime.

### C2 — `Lines[i].Value` is a settable `double`
file: QI_RSI2.cs:80-81 `Lines[0].Value = LowerThreshold;` in `State.Configure` — C13 rc=0 (assignment compiles ⇒ settable).
Type evidence: the C13 mutant above (`= "oops"`) yields CS0029 'string' to **'double'** ⇒ the property type is double.
falsifier (member perturbed): sed `s/Lines\[1\]\.Value = UpperThreshold;/Lines[1].Valuee = UpperThreshold;/`
```
QI_RSI2.cs(81,14): error CS1061: 'Line' does not contain a definition for 'Valuee' and no accessible extension method 'Valuee' accepting a first argument of type 'Line' could be found (are you missing a using directive or an assembly reference?)
rc=1
```
**verdict C2 (compile half: settable double on `Line`): CONFIRMED.** "moves the drawn line" half: runtime probe pending (NinjaTrader run, executed by the orchestrator).

### C3 — `Draw.TextFixed(owner, tag, text, TextPosition, Brush, SimpleFont, Brush, Brush, int)` 9-arg signature
file: QI_RSI2.cs:107-109 (9 args) — C13 rc=0; same call shape in all 27 files (every file compiled).
falsifier (pre-registered: drop the 9th argument): sed `s/Brushes\.Transparent, Brushes\.Transparent, 0);/Brushes.Transparent, Brushes.Transparent);/`
```
109c109  < Brushes.Transparent, Brushes.Transparent, 0);   > Brushes.Transparent, Brushes.Transparent);
QI_RSI2.cs(107,9): error CS1501: No overload for method 'TextFixed' takes 8 arguments
rc=1
```
**verdict C3: CONFIRMED.**

### C4 — `DrawOnPricePanel` (compile half only)
file: QI_HedgingPressure.cs:95 `DrawOnPricePanel = true;` — C13 rc=0.
falsifier: sed `s/DrawOnPricePanel\t\t\t= true;/DrawOnPricePanel\t\t\t= 5;/`
```
95c95  < DrawOnPricePanel			= true;   > DrawOnPricePanel			= 5;
QI_HedgingPressure.cs(95,26): error CS0029: Cannot implicitly convert type 'int' to 'bool'
rc=1
```
**verdict C4 (compile half: assignable bool property exists): CONFIRMED.** Rendering-on-price-panel half: runtime probe pending (NinjaTrader run, executed by the orchestrator).

### C5 — `AddDataSeries(BarsPeriodType.Day, 1)` (compile half only)
file: QI_IBS.cs:82 `AddDataSeries(Data.BarsPeriodType.Day, 1);` in `State.Configure`; `Highs[1][0]`/`Lows[1][0]`/`Closes[1][0]`/`CurrentBars[1]`/`BarsInProgress` used in the same file — C13 rc=0.
falsifier: sed `s/AddDataSeries(Data\.BarsPeriodType\.Day, 1);/AddDataSeriess(Data.BarsPeriodType.Day, 1);/`
```
82c82  < AddDataSeries(Data.BarsPeriodType.Day, 1);   > AddDataSeriess(Data.BarsPeriodType.Day, 1);
QI_IBS.cs(82,6): error CS0103: The name 'AddDataSeriess' does not exist in the current context
rc=1
```
**verdict C5 (compile half): CONFIRMED.** "series index 1 is addressed correctly on an intraday chart, no error, IBS ∈ [0,1]": runtime probe pending (NinjaTrader run, executed by the orchestrator).

### C6 — `StochasticsFast(int, int)` exists and exposes `K`, `D`
file: QI_StochFade.cs:88 `stoch = StochasticsFast(3, 14);`, :100-101 `stoch.K[0]`, `stoch.D[0]` — C13 rc=0.
falsifier (pre-registered: `.KK`): sed `s/Values\[0\]\[0\] = stoch\.K\[0\];/Values[0][0] = stoch.KK[0];/`
```
100c100  < Values[0][0] = stoch.K[0];   > Values[0][0] = stoch.KK[0];
QI_StochFade.cs(100,25): error CS1061: 'StochasticsFast' does not contain a definition for 'KK' and no accessible extension method 'KK' accepting a first argument of type 'StochasticsFast' could be found (are you missing a using directive or an assembly reference?)
rc=1
```
supplementary (3-arg call): sed `s/StochasticsFast(3, 14);/StochasticsFast(3, 14, 99);/`
```
QI_StochFade.cs(88,31): error CS1503: Argument 1: cannot convert from 'int' to 'NinjaTrader.NinjaScript.ISeries<double>'
rc=1
```
(The 3-arg mutant is rejected; the diagnostic shows the only 3-arg overload begins with an `ISeries<double>` input.)
**verdict C6 (existence of the 2-int overload and of members K and D): CONFIRMED.** The index mapping `K => Values[1]`, `D => Values[0]` is not compile-decidable: UNVERIFIABLE by Channel B compile; it is exercised by the C21 runtime diff (pending) and is a Channel A shipped-source item.

### C7 — built-in indicator signatures and compositions
positive side (all C13 rc=0): `RSI(Close, 2, 1)` QI_RSI2:85, QI_RSI14:85, QI_ConnorsRSI:102/104 (`RSI(streakSeries, 2, 1)` on a custom Series);
`Bollinger(Close, 2, 20)` + `.Upper/.Lower` QI_BollingerPctB:91; `MACD(Close, 12, 26, 9).Diff` QI_MACDHistogram:83/95; `ADX(14)` QI_ChopIndex:103;
`StdDev(Close, 20)` QI_CompositeVol:101; `ATR(14)`/`ATR(5)` QI_VRPProxy:83-84; `EMA(Close, 20)` QI_EMACross:83; `SMA(Close, 200)` QI_SMA200Trend:81;
`SMA(atr14, 50)` (atr14 = ATR(14)) QI_ATRRegime:83; `SMA(Range(), 20)` QI_HedgingPressure:134; `SMA(Volume, 20)` QI_VolumeSpike:80.

falsifier 1 (pre-registered: RSI with two args): QI_RSI2 sed `s/RSI(Close, 2, 1);/RSI(Close, 2);/`
```
85c85  < rsi2 = RSI(Close, 2, 1);   > rsi2 = RSI(Close, 2);
QI_RSI2.cs(85,18): error CS1503: Argument 1: cannot convert from 'NinjaTrader.NinjaScript.ISeries<double>' to 'int'
rc=1
```
(Rejected. Side observation from the diagnostic: a 2-arg `RSI(int, int)` overload exists — the input-less form — which is why the error is CS1503 rather than CS1501.)

falsifier 2 (pre-registered: `Bollinger(Close, 20, 2)` "swapped"): QI_BollingerPctB sed `s/Bollinger(Close, 2, 20);/Bollinger(Close, 20, 2);/`
```
62c62  (Description string literal also matched the pattern; inert for compilation)
91c91  < boll = Bollinger(Close, 2, 20);   > boll = Bollinger(Close, 20, 2);
(no diagnostics)
rc=0        <-- MUTANT SURVIVED
```
**This pre-registered falsifier is non-discriminating**: both literals are `int`, and `int` converts implicitly to `double`, so a
`(ISeries<double>, double, int)` signature accepts either order. It therefore cannot support a verdict on the *order* of
`numStdDev`/`period`. Recorded as-is; not counted as REFUTED (the claim is about the signature, and the mutant is a
legal call of that same signature).

supplementary paired control for the ordering (not pre-registered; flagged for the orchestrator):
```
C7s_BollDoublePeriod: sed s/Bollinger(Close, 2, 20);/Bollinger(Close, 2, 20.5);/
  QI_BollingerPctB.cs(91,34): error CS1503: Argument 3: cannot convert from 'double' to 'int'      rc=1
C7s_BollDoubleStd:    sed s/Bollinger(Close, 2, 20);/Bollinger(Close, 2.5, 20);/
  (no diagnostics)                                                                                  rc=0  (expected: positive control)
```
Together: argument 2 accepts a double, argument 3 is `int` ⇒ the overload bound is `(input, double, int)`, i.e.
`(input, numStdDev, period)` as claimed (the *names* are not compile-visible; only the types/positions are).

supplementary falsifiers for the other symbols:
```
C7s_MacdDifff  QI_MACDHistogram sed s/macd\.Diff\[0\]/macd.Difff[0]/
  QI_MACDHistogram.cs(95,24): error CS1061: 'MACD' does not contain a definition for 'Difff' ...   rc=1
C7s_SMA3args   QI_ATRRegime     sed s/SMA(atr14, 50);/SMA(atr14, 50, 1);/
  QI_ATRRegime.cs(83,17): error CS1501: No overload for method 'SMA' takes 3 arguments            rc=1
C7s_Rangee     QI_HedgingPressure sed s/SMA(Range(), 20);/SMA(Rangee(), 20);/
  QI_HedgingPressure.cs(134,22): error CS0103: The name 'Rangee' does not exist in the current context   rc=1
```
**verdict C7: CONFIRMED** for existence, arity and argument types of every listed signature and for the three compositions
(all compile; perturbations of RSI arity, MACD member, SMA arity, Range name and Bollinger period type are each rejected).
Caveat for the orchestrator: the Bollinger *parameter-order* sub-part rests on the supplementary paired control, because
the pre-registered swap falsifier survived (rc=0). ADX/StdDev/ATR/EMA signatures carry no dedicated falsifier beyond C13;
they are covered only by "the call compiles" plus the C13 falsifier showing the compiler does reject type errors.

### C8 — `BackBrush` assignable `Brush` (compile half only)
file: QI_TurnOfMonth.cs:106 `BackBrush = shadeBrush;` (shadeBrush is a frozen SolidColorBrush) — C13 rc=0; same in QI_TurnaroundTuesday:105.
falsifier (pre-registered: `BackBrush = 5`): sed `s/BackBrush = shadeBrush;/BackBrush = 5;/`
```
106c106  < BackBrush = shadeBrush;   > BackBrush = 5;
QI_TurnOfMonth.cs(106,17): error CS0029: Cannot implicitly convert type 'int' to 'System.Windows.Media.Brush'
rc=1
```
**verdict C8 (compile half: assignable, typed `System.Windows.Media.Brush`): CONFIRMED.** "colors the current bar's background" half: runtime probe pending (NinjaTrader run, executed by the orchestrator).

### C9 — `Bars.BarsType.IsIntraday` (compile half only)
file: QI_IBS.cs:80 `useDailySeries = Bars.BarsType.IsIntraday;` inside `State.Configure` (assigned to a `bool`) — C13 rc=0; also QI_VWAPDistance:102.
falsifier: sed `s/useDailySeries = Bars\.BarsType\.IsIntraday;/useDailySeries = Bars.BarsType.IsIntradayy;/`
```
80c80  < useDailySeries = Bars.BarsType.IsIntraday;   > useDailySeries = Bars.BarsType.IsIntradayy;
QI_IBS.cs(80,36): error CS1061: 'BarsType' does not contain a definition for 'IsIntradayy' and no accessible extension method 'IsIntradayy' accepting a first argument of type 'BarsType' could be found (are you missing a using directive or an assembly reference?)
rc=1
```
**verdict C9 (compile half: member exists on `BarsType`, bool-compatible): CONFIRMED.** "readable in Configure without NullReference (Bars non-null at that state)": runtime probe pending (NinjaTrader run, executed by the orchestrator).

### C10 — `Core.Globals.GeneralOptions.TimeZoneInfo` exists; `"Central Standard Time"` resolves on this machine
file: QI_KeyLevels.cs:142 `TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time")`, :198 `Core.Globals.GeneralOptions.TimeZoneInfo` — C13 rc=0 (also QI_TurnOfMonth, QI_TurnaroundTuesday, QI_LiquiditySweep).
falsifier (member perturbed): sed `s/Core\.Globals\.GeneralOptions\.TimeZoneInfo, cstZone);/Core.Globals.GeneralOptions.TimeZoneInfoo, cstZone);/`
```
198c198  < Core.Globals.GeneralOptions.TimeZoneInfo, cstZone);   > Core.Globals.GeneralOptions.TimeZoneInfoo, cstZone);
QI_KeyLevels.cs(198,33): error CS1061: 'GeneralOptions' does not contain a definition for 'TimeZoneInfoo' and no accessible extension method 'TimeZoneInfoo' accepting a first argument of type 'GeneralOptions' could be found (are you missing a using directive or an assembly reference?)
rc=1
```
supplementary runtime probe on this machine (PowerShell 5.1, CLR 4.0.30319 — .NET Framework 4.x, the same framework family as NT's net48; not NinjaTrader itself):
```
probe:     [TimeZoneInfo]::FindSystemTimeZoneById("Central Standard Time")
stdout:    OK Id=Central Standard Time BaseUtcOffset=-06:00:00 SupportsDST=True
rc=0
falsifier: [TimeZoneInfo]::FindSystemTimeZoneById("Central Standard Timee")
stdout:    EXC System.Management.Automation.MethodInvocationException: Exception calling "FindSystemTimeZoneById" with "1" argument(s): "The time zone ID 'Central Standard Timee' was not found on the local computer."
falsifier_rc=1
```
**verdict C10: CONFIRMED** for (a) the member exists and compiles (mutant rejected) and (b) the zone id resolves on this machine under .NET Framework 4.x. "QI_KeyLevels loads in NT with no log error": runtime probe pending (NinjaTrader run, executed by the orchestrator).

### C11 — `Draw.HorizontalLine(6 args)`, `Draw.Text(13 args)`, `Draw.Line(10 args)`
positive side: QI_KeyLevels.cs:427-428 HorizontalLine (6 args), :434-438 Text (13 args); QI_LiquiditySweep.cs:737-739 Line (10 args); QI_HedgingPressure.cs:272-279/296-308 — all C13 rc=0.
falsifier (pre-registered: drop an argument of Draw.HorizontalLine — the 6th, width): QI_KeyLevels sed `s/PrevDayHighBrush, DashStyleHelper\.DashDotDot, 2);/PrevDayHighBrush, DashStyleHelper.DashDotDot);/`
```
428c428  < PrevDayHighBrush, DashStyleHelper.DashDotDot, 2);   > PrevDayHighBrush, DashStyleHelper.DashDotDot);
QI_KeyLevels.cs(428,25): error CS1503: Argument 5: cannot convert from 'NinjaTrader.Gui.DashStyleHelper' to 'bool'
rc=1
```
supplementary:
```
C11s_HLineDropDash  sed s/PrevDayHighBrush, DashStyleHelper\.DashDotDot, 2);/PrevDayHighBrush, 2);/
  QI_KeyLevels.cs(428,25): error CS1503: Argument 5: cannot convert from 'int' to 'bool'                       rc=1
C11s_Text12args     sed 438s/Brushes\.Transparent, Brushes\.Transparent, 0);/Brushes.Transparent, Brushes.Transparent);/
  QI_KeyLevels.cs(434,10): error CS1501: No overload for method 'Text' takes 12 arguments                      rc=1
C11s_Line9args      QI_LiquiditySweep sed s/brush, DashStyleHelper\.Dash, 2);/brush, DashStyleHelper.Dash);/
  QI_LiquiditySweep.cs(739,6):  error CS1503: Argument 8: cannot convert from 'System.Windows.Media.Brush' to 'bool'
  QI_LiquiditySweep.cs(739,13): error CS1503: Argument 9: cannot convert from 'NinjaTrader.Gui.DashStyleHelper' to 'string'   rc=1
```
**verdict C11: CONFIRMED** (all three signatures bind; removing one argument from each is rejected).

### C12 — `Serialize.BrushToString` / `Serialize.StringToBrush` (minor)
positive side: QI_KeyLevels.cs:604 (and 7 more), QI_HedgingPressure:361/369/377, QI_LiquiditySweep:846/855, QI_OrderFlowPlus:401/409, QI_SMC:482/490 — all C13 rc=0.
falsifier: sed `604s/Serialize\.BrushToString(PrevDayHighBrush)/Serialize.BrushToStringg(PrevDayHighBrush)/`
```
604c604  ... Serialize.BrushToString(PrevDayHighBrush) ...   > ... Serialize.BrushToStringg(PrevDayHighBrush) ...
QI_KeyLevels.cs(604,28): error CS0117: 'Serialize' does not contain a definition for 'BrushToStringg'
rc=1
```
**verdict C12: CONFIRMED.**

### Mutant summary (all from `<scratch>/logs/mut_summary.tsv`)

| id | file | diff_rc | rc | error |
|---|---|---|---|---|
| C13_typeerr | QI_RSI2 | 1 | 1 | CS0029 string→double |
| C1_AddLinee | QI_RSI2 | 1 | 1 | CS0103 |
| C2_Valuee | QI_RSI2 | 1 | 1 | CS1061 on `Line` |
| C3_TextFixed8 | QI_RSI2 | 1 | 1 | CS1501 (8 args) |
| C4_DrawOnPricePanel5 | QI_HedgingPressure | 1 | 1 | CS0029 int→bool |
| C5_AddDataSeriess | QI_IBS | 1 | 1 | CS0103 |
| C6_KK | QI_StochFade | 1 | 1 | CS1061 on `StochasticsFast` |
| C6s_Stoch3args | QI_StochFade | 1 | 1 | CS1503 |
| C7_RSI2args | QI_RSI2 | 1 | 1 | CS1503 |
| **C7_BollSwap** | QI_BollingerPctB | 1 | **0** | (survived — non-discriminating, see C7) |
| C7s_BollDoublePeriod | QI_BollingerPctB | 1 | 1 | CS1503 arg 3 double→int |
| C7s_BollDoubleStd | QI_BollingerPctB | 1 | 0 | (positive control, expected) |
| C7s_MacdDifff | QI_MACDHistogram | 1 | 1 | CS1061 on `MACD` |
| C7s_SMA3args | QI_ATRRegime | 1 | 1 | CS1501 |
| C7s_Rangee | QI_HedgingPressure | 1 | 1 | CS0103 |
| C8_BackBrush5 | QI_TurnOfMonth | 1 | 1 | CS0029 int→Brush |
| C9_IsIntradayy | QI_IBS | 1 | 1 | CS1061 on `BarsType` |
| C10_TimeZoneInfoo | QI_KeyLevels | 1 | 1 | CS1061 on `GeneralOptions` |
| C11_HLine5args | QI_KeyLevels | 1 | 1 | CS1503 |
| C11s_HLineDropDash | QI_KeyLevels | 1 | 1 | CS1503 |
| C11s_Text12args | QI_KeyLevels | 1 | 1 | CS1501 (12 args) |
| C11s_Line9args | QI_LiquiditySweep | 1 | 1 | CS1503 ×2 |
| C12_BrushToStringg | QI_KeyLevels | 1 | 1 | CS0117 |

## 3. C15 — no buy/sell signals, arrows, TP/SL, win-rate, alpha counting, CSV writer, user paths

```
probe_cmd:  grep -nE '"[^"]*\b(Buy|Sell)\b[^"]*"|ArrowUp|ArrowDown|DrawTpSl|%WR|WR%|AlphaCount|csvWriter|StreamWriter|OneDrive' indicators/QI_*.cs
stdout:     (empty)
rc:         1          (GNU grep: 1 = no lines selected)
falsifier_cmd: same grep on "C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\IBSFade.cs"  (142,656 B, 3,230 lines)
falsifier_rc:  0 ; hit count: 62
  per alternative:  "…\b(Buy|Sell)\b…" 27 | ArrowUp 2 | ArrowDown 2 | DrawTpSl 5 | %WR 3 | WR% 2 | AlphaCount 8 | csvWriter 12 | StreamWriter 2 | OneDrive 1
  first hits verbatim:
  192:		private StreamWriter	csvWriter;
  475:						string folder = @"C:\Users\rajib\OneDrive\Docs\futures_data\ninja_trader_signal_data";
  506:						csvWriter = new StreamWriter(csvFilePath, true);
  509:							string hdr = "Timestamp,BarTime,Symbol,Timeframe,SignalType,Direction,Description,Price,IBS,AlphaCount,HpScore,...";
  570:				int dbAlphaCount = 0;
  578:					dbAlphaCount = Math.Max(buyCount, sellCount);
```
**verdict C15: CONFIRMED** (probe empty on all 27 files; identical probe returns 62 hits on ORIG).
Scope note: this is exactly the pre-registered pattern; it does not test e.g. lower-case "buy"/"sell" outside string literals
or `Draw.ArrowUp` spelled through an alias — nothing beyond the ledger text is claimed here.

## 4. C16 — disclaimer in header, Description tail, and `ShowDisclaimer = true`

probe (per file): `grep -cE '^//  DISCLAIMER$'` | `grep -cF 'Educational use only - not financial advice."'` | `grep -cE 'ShowDisclaimer\s*=\s*true;'`
Line-ending check: `file indicators/QI_RSI2.cs` → "ASCII text"; `grep -c $'\r'` → 0 (so the `$` anchor is sound).

| file | hdr | desc | prop |
|---|---|---|---|
| QI_ATRRegime.cs | 1 | 1 | 1 |
| QI_BollingerPctB.cs | 1 | 1 | 1 |
| QI_ChopIndex.cs | 1 | 1 | 1 |
| QI_CompositeVol.cs | 1 | 1 | 1 |
| QI_ConnorsRSI.cs | 1 | 1 | 1 |
| QI_ConsecDays.cs | 1 | 1 | 1 |
| QI_EMACross.cs | 1 | 1 | 1 |
| QI_HedgingPressure.cs | 1 | 1 | 1 |
| QI_IBS.cs | 1 | 1 | 1 |
| QI_KeyLevels.cs | 1 | 1 | 1 |
| QI_LiquiditySweep.cs | 1 | 1 | 1 |
| QI_MACDHistogram.cs | 1 | 1 | 1 |
| QI_OrderFlowPlus.cs | 1 | 1 | 1 |
| QI_OvernightGap.cs | 1 | 1 | 1 |
| QI_RSI14.cs | 1 | 1 | 1 |
| QI_RSI2.cs | 1 | 1 | 1 |
| QI_RVZScore.cs | 1 | 1 | 1 |
| QI_SMA200Trend.cs | 1 | 1 | 1 |
| QI_SMC.cs | 1 | 1 | 1 |
| QI_StochFade.cs | 1 | 1 | 1 |
| QI_TurnOfMonth.cs | 1 | 1 | 1 |
| QI_TurnaroundTuesday.cs | 1 | 1 | 1 |
| QI_VRPProxy.cs | 1 | 1 | 1 |
| QI_VWAPDistance.cs | 1 | 1 | 1 |
| QI_VolumeDelta.cs | 1 | 1 | 1 |
| QI_VolumeSpike.cs | 1 | 1 | 1 |
| QI_WideRangeBar.cs | 1 | 1 | 1 |

Files with any count ≠ 1: none. Falsifier: the same three greps on ORIG IBSFade.cs → `0 0 0`.
**verdict C16: CONFIRMED.** (Text-presence only; that `ShowDisclaimer = true;` sits inside `State.SetDefaults` is visible in the
source, e.g. QI_RSI2.cs:72, but the grep does not enforce placement.)

## 5. C17 — each file is self-contained (no QI_ file references a type defined in another QI_ file)

Implied by C13: each of the 27 files was compiled as the sole source (`sources: 1` in every log) against only the
installed NinjaTrader/.NET/SharpDX assemblies — no other QI_ file was on the command line. Any cross-file type reference
would have produced CS0246/CS0103 in that compilation. C13 rc list: 27 × rc=0 (section 1); the C1/C5/C7s_Rangee
mutants show that an unresolved name in this configuration does produce CS0103 (rc=1).
**verdict C17: CONFIRMED.**

## 6. Repo integrity (originals untouched)

`sha256sum indicators/QI_*.cs` recorded before the first probe (`<scratch>/sha256_pre.txt`) and re-run after the C13 loop,
after the 21-mutant batch, after the Bollinger control and after the C4 mutant:
`diff sha256_pre.txt <(sha256sum indicators/QI_*.cs)` → empty → **IDENTICAL** every time.
Reference values: QI_RSI2.cs fddeeff3da54ecb3b43113505a2d2bc582d3421566d0d3f02f404da483cd4dd2;
QI_KeyLevels.cs 08883b4bbb50c201c1d8d55974f570cf97424bde0193050e72ff2d91197a3786 (full list in `<scratch>/sha256_pre.txt`).
No file under the repo was written by this channel other than this report.

## 7. Verdict table

| claim | verdict (Channel B automated) | note |
|---|---|---|
| C1 | CONFIRMED (compile half) / pending runtime (line drawn) | AddLinee → CS0103 |
| C2 | CONFIRMED (compile half: settable `double`) / pending runtime (line moves) | Valuee → CS1061; "oops" → CS0029 to double |
| C3 | CONFIRMED | 8-arg → CS1501 |
| C4 | CONFIRMED (compile half: bool property) / pending runtime (renders on price panel) | `= 5` → CS0029 |
| C5 | CONFIRMED (compile half) / pending runtime (index-1 series, IBS ∈ [0,1]) | AddDataSeriess → CS0103 |
| C6 | CONFIRMED (overload + K/D exist) / UNVERIFIABLE by compile: K/D ↔ Values index mapping (→ C21 runtime, Channel A) | KK → CS1061 |
| C7 | CONFIRMED, with flag: pre-registered Bollinger swap falsifier survived (rc=0); ordering rests on supplementary paired control | RSI 2-arg → CS1503 |
| C8 | CONFIRMED (compile half: `Brush`-typed, assignable) / pending runtime (shading) | `= 5` → CS0029 |
| C9 | CONFIRMED (compile half) / pending runtime (non-null in Configure) | IsIntradayy → CS1061 |
| C10 | CONFIRMED (member compiles; zone id resolves on this machine) / pending runtime (NT load, no log error) | TimeZoneInfoo → CS1061; "…Timee" → not found |
| C11 | CONFIRMED | each dropped arg → CS1503/CS1501 |
| C12 | CONFIRMED | BrushToStringg → CS0117 |
| C13 | CONFIRMED | 27/27 rc=0; type-error mutant CS0029 rc=1 |
| C14 | pending runtime (orchestrator: NinjaScript editor F5) | |
| C15 | CONFIRMED | 0 hits vs 62 on ORIG |
| C16 | CONFIRMED | 27 × (1,1,1) vs ORIG (0,0,0) |
| C17 | CONFIRMED (via C13 single-source compilations) | |
| C18–C44 | pending runtime (orchestrator: ORIG EveryBar CSV vs QI_EgvDump diff) | |

Counts over the 16 claims assigned to this channel: CONFIRMED in full 8 (C3, C7*, C11, C12, C13, C15, C16, C17);
CONFIRMED compile-half with behavioral half pending runtime 8 (C1, C2, C4, C5, C6**, C8, C9, C10);
REFUTED 0; PROBE_INVALID 0; pending runtime (not attempted) 28 (C14, C18–C44).
\* C7: one pre-registered falsifier non-discriminating, documented. \*\* C6: index-mapping sub-part UNVERIFIABLE by compile.

Scratch evidence root (logs, diffs, mutants, DLLs): `C:\Users\rajib\AppData\Local\Temp\claude\C--Users-rajib-OneDrive-Documents\533a663d-5efe-42d6-aafd-bb6df2ee5fa2\scratchpad\egv\chanB\`
