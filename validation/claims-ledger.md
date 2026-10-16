# Claims ledger — ninjatrader_quant_indicators

status: FROZEN 2026-10-15 (all 27 files present; no claim may be added, dropped or reworded —
        a missed claim is recorded separately in `validation/addenda.md` and run through both channels fresh)
harness: `validation/QI_EgvDump.cs` builds each module with `CacheIndicator<T>(new T(){defaults}, Input, ref cache)`,
        the same construction NinjaTrader's generated wrappers use, at ORIG's default parameters.
target: `indicators/QI_*.cs` (27 files) vs ORIG `C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\IBSFade.cs` (3,230 lines)
environment: `validation/env-pin.txt` (NinjaTrader 8.1.8.3, net48, LangVersion 13; probe compiler Roslyn from .NET SDK 8.0.100 at C# 12)
tier: 2 (full dual-channel) — NinjaScript is a low-usage API with no test oracle other than the
      original indicator, and the code is AI-generated and unreviewed by its author.
mode: dual-subagent (Mode 1) for Channel A and the automated part of Channel B; the NinjaTrader
      runtime probes (B-RT-*) are executed by the orchestrator AFTER channel-a.md is committed and
      without reading it. Convergence is still "dual-confirmed", never "independently proven".

Materiality: M = material (wrong ⇒ wrong values on a chart or the repo violates the brief), m = minor.
Every material claim starts REJECTED.

## Channel definitions for this ledger

- **Channel A (documentation / primary source, no execution):** NinjaTrader 8 help guide
  (https://ninjatrader.com/support/helpGuides/nt8/) matched to 8.1.x, the NinjaTrader-shipped
  indicator sources in `Documents\NinjaTrader 8\bin\Custom\Indicators\@*.cs`, and — for
  algorithmic claims — ORIG itself as the specification, audited by static side-by-side reading.
- **Channel B (runtime, no documentation):** `validation/probes/compile_probe.sh` (Roslyn against
  the installed assemblies, with a mutant falsifier), text probes, and the NinjaTrader runtime
  differential: ORIG with `CsvLogMode = EveryBar` and the harness `validation/QI_EgvDump.cs`
  on the same chart, values diffed bar-by-bar.

## A. API / environment claims (apply to every file that uses the symbol)

| ID | Cat | Mat | Claim | Falsifier | B probe (pre-registered) |
|----|-----|-----|-------|-----------|--------------------------|
| C1 | api | M | `Indicator.AddLine(Brush brush, double value, string name)` exists in NT 8.1.8.3 and may be called from `State.SetDefaults` | compile error CS1501/CS1503, or the line is not drawn | compile_probe on any panel module; falsifier: rename to `AddLinee` ⇒ rc≠0 |
| C2 | api | M | `Lines[i].Value` is a settable `double` and assigning it in `State.Configure` moves the drawn line to the property value | compile error, or line stays at the SetDefaults value when the property differs | compile_probe; runtime: set LowerThreshold=0.33 on QI_IBS in NT and read the line level |
| C3 | api | M | `Draw.TextFixed(NinjaScriptBase, string tag, string text, TextPosition, Brush textBrush, SimpleFont, Brush outline, Brush area, int areaOpacity)` exists with this 9-argument signature | CS1501/CS1503 | compile_probe (all files); falsifier: drop the last argument ⇒ rc≠0 |
| C4 | api | M | A non-overlay indicator with `DrawOnPricePanel = true` renders its `Draw.*` objects on the price panel | objects appear in the indicator panel instead | runtime: QI_HedgingPressure on a chart, HP lines visible on price panel |
| C5 | api | M | `AddDataSeries(BarsPeriodType.Day, 1)` in `State.Configure` adds series index 1; `BarsInProgress`, `CurrentBars[1]`, `Highs[1][0]`/`Lows[1][0]`/`Closes[1][0]` address it | compile error or runtime exception on an intraday chart | runtime: QI_IBS on a 5-min chart loads with no error and IBS ∈ [0,1] |
| C6 | api | M | `StochasticsFast(int periodD, int periodK)` exists and exposes `K` and `D` series (`K => Values[1]`, `D => Values[0]`) | shipped source or compile disagrees | compile_probe QI_StochFade; A: `@StochasticsFast.cs` lines 71-75 |
| C7 | api | M | `RSI(ISeries<double>, int period, int smooth)`, `Bollinger(input, double numStdDev, int period)` with `Upper`/`Lower`, `MACD(input, fast, slow, smooth)` with `Diff`, `ADX(int)`, `StdDev(input, int)`, `ATR(int)`, `EMA`/`SMA(input, int)`, `Range()` exist with these signatures, and `SMA(ATR(14), 50)` / `SMA(Range(), 20)` / `SMA(Volume, 20)` compose | shipped source or compile disagrees | compile_probe on the files using each; A: shipped `@*.cs` wrapper signatures |
| C8 | api | M | `BackBrush` is an assignable `Brush` on Indicator that colors the current bar's background | compile error or no shading in NT | compile_probe QI_TurnOfMonth; runtime: Monday bars shaded by QI_TurnaroundTuesday |
| C9 | api | M | `Bars.BarsType.IsIntraday` is readable in `State.Configure` | compile error / NullReference in Configure | compile_probe + runtime load of QI_IBS on daily and 5-min charts |
| C10 | api | M | `Core.Globals.GeneralOptions.TimeZoneInfo` exists and `TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time")` resolves on this machine | compile error / TimeZoneNotFoundException | compile_probe + runtime load of QI_KeyLevels (no log error) |
| C11 | api | M | `Draw.HorizontalLine(owner, tag, double y, Brush, DashStyleHelper, int width)`, `Draw.Text(owner, tag, bool autoScale, string, int barsAgo, double y, int yPixelOffset, Brush, SimpleFont, TextAlignment, Brush, Brush, int)` and `Draw.Line(owner, tag, bool autoScale, int barsAgo1, double y1, int barsAgo2, double y2, Brush, DashStyleHelper, int)` exist with these signatures | CS1501/CS1503 | compile_probe on QI_KeyLevels, QI_HedgingPressure, QI_LiquiditySweep |
| C12 | api | m | `Serialize.BrushToString` / `Serialize.StringToBrush` exist for the `[XmlIgnore]` brush + `*Serialize` string pattern | compile error | compile_probe on brush-bearing files |
| C13 | env | M | Every `QI_*.cs` compiles standalone (one file per compilation) against the installed NT 8.1.8.3 assemblies | any rc≠0 | compile_probe per file; falsifier: mutant with a type error rc≠0 (recorded 2026-10-15: CS0029) |
| C14 | env | M | All 27 files compile together inside NinjaTrader's own NinjaScript editor (LangVersion 13, with the real `NinjaTrader.Custom` project) | NinjaScript editor reports errors | runtime: copy to `Custom\Indicators\QuantIndicators\`, F5, zero errors in the output window |

## B. Semantic claims (the brief)

| ID | Cat | Mat | Claim | Falsifier | B probe (pre-registered) |
|----|-----|-----|-------|-----------|--------------------------|
| C15 | sem | M | No file draws or names a buy/sell signal: no string literal containing the words Buy/Sell, no `Draw.ArrowUp/ArrowDown`, no TP/SL lines, no win-rate strings, no alpha counting, no CSV writer, no hard-coded user path | any grep hit | `grep -nE '"[^"]*\b(Buy\|Sell)\b[^"]*"\|ArrowUp\|ArrowDown\|DrawTpSl\|%WR\|WR%\|AlphaCount\|csvWriter\|StreamWriter\|OneDrive' indicators/*.cs` ⇒ no output; falsifier: same grep on ORIG ⇒ hits |
| C16 | sem | M | Every file carries the disclaimer in all three places: header block, end of `Description`, and a `ShowDisclaimer` property whose default is `true` | any file missing one | grep counts per file: `^//  DISCLAIMER$` ==1, `Educational use only - not financial advice."` ==1, `ShowDisclaimer\s*=\s*true;` ==1 |
| C17 | sem | M | Each file is self-contained: no `QI_` file references a type defined in another `QI_` file | C13 fails for a file compiled alone | implied by C13 (one-file compilations) |

## C. Algorithmic claims — port fidelity (one per module)

Form of every row: "`<Class>`'s plotted/exposed value(s) equal ORIG `Values[k][0]` bar-for-bar
on the same chart (same instrument, period, data range, default parameters) for every bar ≥ 50,
to the 4 decimals ORIG writes in EveryBar CSV." Channel A = static side-by-side read of the
ported lines against ORIG's lines (CONVENTIONS.md module map). Channel B = runtime diff.
Falsifier for all: any bar ≥ 50 where |new − ORIG| > 0.00005, or a differing event list.
Pre-registered B falsifier: change one constant in one module (QI_RSI2 period 2→3) and re-run
the diff ⇒ mismatches must appear; restore and checksum.

| ID | Module | ORIG plot | Mat | Extra scope |
|----|--------|-----------|-----|-------------|
| C18 | `QI_IBS` | 1 | M | on an intraday chart, value comes from the daily series |
| C19 | `QI_RSI2` | 2 | M | |
| C20 | `QI_ConnorsRSI` | 3 | M | 50 until bar 100; streak counters start at bar 50 |
| C21 | `QI_StochFade` | 4 (%K) | M | %D has no ORIG DataBox value → compared to `StochasticsFast(3,14).D` directly |
| C22 | `QI_RVZScore` | 5 | M | |
| C23 | `QI_CompositeVol` | 6 | M | includes bars 50-58 where ORIG's series bleed is reproduced |
| C24 | `QI_TurnOfMonth` | 7 | M | |
| C25 | `QI_ConsecDays` | 8 | M | counters start at bar 50 |
| C26 | `QI_OvernightGap` | 9 | M | |
| C27 | `QI_BollingerPctB` | 10 | M | |
| C28 | `QI_TurnaroundTuesday` | 11 | M | |
| C29 | `QI_RSI14` | 12 | M | |
| C30 | `QI_VRPProxy` | 13 | M | |
| C31 | `QI_WideRangeBar` | 14 | M | |
| C32 | `QI_HedgingPressure` | 0 | M | score only; price lines compared by level in the runtime probe |
| C33 | `QI_VWAPDistance` | 15 | M | intraday chart only; 0 on daily |
| C34 | `QI_MACDHistogram` | 16 | M | |
| C35 | `QI_EMACross` | 17 | M | `Spread` (ema20−ema50) vs ORIG plot 17 |
| C36 | `QI_SMA200Trend` | 18 | M | `Distance` vs ORIG plot 18 |
| C37 | `QI_ATRRegime` | 19 | M | |
| C38 | `QI_VolumeSpike` | 20 | M | |
| C39 | `QI_VolumeDelta` | 21, 22 | M | CumDelta20 vs plot 21, DeltaSMA10 vs plot 22 |
| C40 | `QI_ChopIndex` | 25, 26 | M | CHOP vs plot 25, ChoppyFlag vs plot 26 |
| C41 | `QI_LiquiditySweep` | 24 | M | event list: (bar, start/end, patterns, confidence) equals ORIG's label events |
| C42 | `QI_OrderFlowPlus` | 27 | M | event list: (bar, patterns[0], confidence, direction) equals ORIG's |
| C43 | `QI_SMC` | 29 | M | event list: (bar, patterns[0], confidence, direction) equals ORIG's |
| C44 | `QI_KeyLevels` | — | M | the eight level values per bar equal ORIG's (PDH/PDL, MoH/MoL, ORB H/L, Asian H/L) |

Claim count: 44 (43 material, 1 minor). Granularity note: one algorithmic claim per module is the
finest unit at which a mechanical oracle (ORIG's own values) exists; splitting further would be
triviality inflation unless a module diverges, in which case the split axis is "term in the
formula" or "input subdomain (intraday vs daily)".
