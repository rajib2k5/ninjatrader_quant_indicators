# Conventions and module map

Every indicator in `indicators/` is a faithful, standalone split of one signal module from the
original "IBSFade" multi-strategy indicator
(`C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\IBSFade.cs`, 3,230 lines,
referred to below as **ORIG** with line numbers). The split changes *packaging*, not *math*.

## Hard rules

1. **One module = one file = one class.** No shared helper files. Duplicate small helpers
   (`Clamp`, CST conversion, `DrawDisclaimerOnce`) inside each file so any single `.cs`
   can be dropped into NinjaTrader alone.
2. **Class and file name `QI_<Module>`** in namespace `NinjaTrader.NinjaScript.Indicators`
   (required by NinjaTrader). `Name = "QI_<Module>"`, `DisplayName => "QI <Module>"`.
3. **Preserve ORIG formulas exactly**, including quirks and warm-up guards (e.g. ConnorsRSI
   `pastRoc` indexing at ORIG 1288, CompositeVol constants at ORIG 1325-1326, Chop TR guard
   at ORIG 1466, VWAP `DayOfYear` reset at ORIG 1605, CST timezone conversion via
   `Core.Globals.GeneralOptions.TimeZoneInfo`, per-signal `CurrentBar` guards and their
   fallback values). Do **not** "improve" a formula. Document a quirk in the header comment
   instead.
4. **No Buy/Sell anything.** Removed from every module: `Draw.Text` Buy/Sell labels,
   `Draw.ArrowUp/Down`, TP/SL lines, trade-parameter strings (PT/SL ticks, lot size, "WR%"),
   Alpha Count / Multi-Alpha, Total Buys/Sells, CSV logging, hard-coded file paths,
   `TradeParamTag`/`FormatTradeParams`/`GetSignalTradeParams`/`DrawTpSlLines`, and the
   literature win-rate percentages. Keep the literature *source* (e.g. "Pagonidis 2013") in
   the header comment as a concept reference only.
5. **Thresholds become neutral reference lines.** Where ORIG classified a value as B/N/S,
   expose the boundary values as properties named `LowerThreshold` / `UpperThreshold`
   (or a single `Threshold`) with ORIG's defaults, add them with `AddLine(brush, value, name)`
   in `SetDefaults`, and apply the property values in `State.Configure` via
   `Lines[i].Value = ...`. Line names: "Lower Threshold", "Upper Threshold", "Zero".
6. **Pattern modules (LiquiditySweep, OrderFlowPlus, SMC)** keep their detection logic and
   draw labels on the price panel (`DrawOnPricePanel = true`) using **pattern names +
   confidence** only, e.g. `"Liq Sweep End: SFP + Spring (85%)"`, `"OF+ DeltaDiv (78%)"`,
   `"SMC OB Retest (72%)"`. No "Buy"/"Sell" words, no arrows (`\u2191`/`\u2193`), no TP/SL.
   Keep ORIG's `DuplicateBarWindow` suppression for labels. Plot `Confidence` (0..1) and
   `Structure` (+1 bullish structure, -1 bearish structure, 0 none) in the panel.
7. **Disclaimer in three places:** the file header block (copy verbatim from
   `indicators/QI_IBS.cs`), the end of `Description`
   (`"... Educational use only - not financial advice."`), and a `ShowDisclaimer` property
   (default `true`) that draws the fixed text once via `DrawDisclaimerOnce()` (copy from the
   template).
8. **Expose values** the module computes as public `Series<double>` properties tagged
   `[Browsable(false)] [XmlIgnore]` (plots via `Values[i]`; non-plot values via a private
   `Series<double>` created in `State.DataLoaded`). The validation harness reads these.
9. **Header/usings:** copy the `#region Using declarations` block from the template
   verbatim (it is NinjaTrader's standard set and is known to compile).
10. **Style:** tabs for indentation, `State.SetDefaults` / `State.Configure` /
    `State.DataLoaded` ordering as in the template, no `#region NinjaScript generated code`
    (NinjaTrader appends it on compile), no `using System.IO`.
11. **Defaults:** `Calculate = Calculate.OnBarClose`, `IsSuspendedWhileInactive = true`,
    `DisplayInDataBox = true`, `PaintPriceMarkers = false`,
    `ScaleJustification = ScaleJustification.Right`. Panel modules: `IsOverlay = false`.
    Overlay modules: `IsOverlay = true`.

## Module map

Columns: class, ORIG plot index, ORIG source lines to port, panel/overlay, plots, reference
lines (defaults), notes. Dependencies listed are ORIG's private indicator instances to
re-create locally in `State.DataLoaded`.

| # | Class | ORIG plot | ORIG lines | Panel | Plots | Lines | Notes |
|---|-------|-----------|------------|-------|-------|-------|-------|
| 1 | `QI_IBS` | 1 | 325-328, 535-555, 601-608 | panel | `IBS` | 0.20 / 0.80 | **Template - already written.** Adds a 1-day series on intraday charts. |
| 2 | `QI_RSI2` | 2 | 342, 1272-1275 | panel | `RSI(2)` | 25 / 75 | `RSI(Close, 2, 1)`. |
| 3 | `QI_ConnorsRSI` | 3 | 342, 410-411, 1552-1568 (streak update, runs every bar before the value calc), 1277-1296 | panel | `ConnorsRSI` | 15 / 85 | `rsiStreak = RSI(streakSeries, 2, 1)`; value 50 until `CurrentBar >= 100`; keep the `pastRoc` indexing at 1288 exactly. |
| 4 | `QI_StochFade` | 4 | 350, 1298-1301 | panel | `%K`, `%D` | 30 / 70 | `StochasticsFast(3, 14)` => periodD=3, periodK=14; `K` = `.K`, `D` = `.D`. |
| 5 | `QI_RVZScore` | 5 | 347, 1573-1593 | panel | `RV Z-Score` | 2.0 / -1.5 | 0 until `CurrentBar >= 25`; lookback `Math.Min(20, CurrentBar)`; population std. |
| 6 | `QI_CompositeVol` | 6 | 1308-1330 + deps 416-418 (`SMA(Close,20)`, `StdDev(Close,20)`), 1573-1593 (rvZ), 1596 (`atrChangeSeries`) | panel | `CompositeVol` | 1.5 / -1.5 | 0 unless `CurrentBar >= 30 && stdDev > 0`; `0.40*rvZ + 0.35*(-priceZ) + 0.25*((vov-0.15)/0.10)`. |
| 7 | `QI_TurnOfMonth` | 7 | 370, 1332-1340 | panel | `Turn-of-Month` (1/0) | none | CST date; window `dom >= dim-3 \|\| dom <= 3`. Optional `ShadeWindow` (default true) sets `BackBrush` on window bars. |
| 8 | `QI_ConsecDays` | 8 | 1552-1568, 1342-1346 | panel | `Streak` (signed) | 3 / -3 | `streak = consecUp > 0 ? consecUp : -consecDown`; unchanged close keeps counts. |
| 9 | `QI_OvernightGap` | 9 | 1571, 1348-1351 | panel | `Gap %` | 0.3 / -0.3 | `(Open[0]-Close[1])/Close[1]*100`, 0 on bar 0. |
| 10 | `QI_BollingerPctB` | 10 | 349, 1353-1360 | panel | `%B` | 100 / -100 | `Bollinger(Close, 2, 20)`; value `(Close-mid)/(bandwidth*0.5)*100`, 0 if bandwidth<=0. |
| 11 | `QI_TurnaroundTuesday` | 11 | 1362-1366 | panel | `Day of Week` (0-6) | none | CST `DayOfWeek`. Optional `ShadeMonday` (default true) `BackBrush` on Mondays. |
| 12 | `QI_RSI14` | 12 | 343, 1368-1371 | panel | `RSI(14)` | 40 / 60 | `RSI(Close, 14, 1)`. |
| 13 | `QI_VRPProxy` | 13 | 347, 414, 1373-1377 | panel | `ATR5/ATR14` | 1.5 / 0.7 | 1.0 unless `CurrentBar >= 20 && atr14 > 0`. |
| 14 | `QI_WideRangeBar` | 14 | 347, 1379-1383 | panel | `Range/ATR14` | 1.2 | 1.0 if `atr14 <= 0`. |
| 15 | `QI_HedgingPressure` | 0 | 358, 363-367, 1015-1059, 1064-1080 (zone names only), 1141-1227 | panel + `DrawOnPricePanel=true` | `HP Score` | 35 / -35 / 15 / -15 | Keep Daily/Weekly/Monthly HP price lines, labels and the TopRight score panel (ORIG 1141-1227). Drop everything from ORIG 1082-1135 (Buy HP/Sell HP, TP/SL, CSV, counters). Properties: `ShowHpLines`, the three line brushes. |
| 16 | `QI_VWAPDistance` | 15 | 325 (intraday flag), 1603-1618, 1385-1397 | panel | `VWAP Dist (ATR)` | 0.5 / -0.5 / 0 | Manual session VWAP with ORIG's `DayOfYear` reset; value `(Close-vwap)/atr14` **only on intraday charts**, else 0 (ORIG gate). Expose non-plot `Vwap` series. |
| 17 | `QI_MACDHistogram` | 16 | 348, 1399-1402 | panel | `MACD Hist` (PlotStyle.Bar) | 0 | `MACD(Close, 12, 26, 9).Diff`. |
| 18 | `QI_EMACross` | 17 | 344-345, 1404-1408 | overlay | `EMA 20`, `EMA 50` | none | Expose non-plot `Spread` series = ema20-ema50. |
| 19 | `QI_SMA200Trend` | 18 | 346, 1410-1414 | overlay | `SMA 200` | none | Expose non-plot `Distance` series = `CurrentBar >= 200 ? Close-sma200 : 0`. |
| 20 | `QI_ATRRegime` | 19 | 347, 409, 1416-1420 | panel | `ATR14 / SMA50(ATR14)` | 1.5 | 1.0 unless `CurrentBar >= 50 && atrSma50 > 0`. |
| 21 | `QI_VolumeSpike` | 20 | 358, 1422-1426 | panel | `Vol / SMA20` | 1.5 | 1.0 if `volSma20 <= 0`. |
| 22 | `QI_VolumeDelta` | 21, 22 | 357-360, 1623-1634, 1428-1443 | panel | `Vol Delta` (Bar), `CumDelta 20`, `Delta SMA 10` | 0 | cum = sum of last 20 (0 if `CurrentBar <= 20`); SMA(volDelta,10) (0 if `CurrentBar < 10`). |
| 23 | `QI_ChopIndex` | 25, 26 | 358-359, 1453-1524 | panel | `CHOP` | 61.8 / 38.2 | Expose non-plot `ChoppyFlag` (0/0.5/1), `Adx`, `VolRatio`. Draw the state ("CHOPPY/CAUTION/TRENDING n/3") as `Draw.TextFixed` TopRight. |
| 24 | `QI_LiquiditySweep` | 24 | 137-165, 297-305, 420-448, 2038-2319, 2340-2404; needs its own copy of key-level tracking (656-860, no drawing) for "Sweep PDH/PDL/ORB/MoHigh/MoLow" | panel + `DrawOnPricePanel=true` | `Confidence`, `Structure` | none | Labels per rule 6. Keep Start/End connecting line (`Draw.Line`). Keep `DuplicateBarWindow`. |
| 25 | `QI_OrderFlowPlus` | 27, 28 | 167-171, 450-454, 2090-2137 (swing points incl. `cumDeltaAtLastSwing*`), 1623-1634, 2411-2541 | panel + `DrawOnPricePanel=true` | `Confidence`, `Structure` | none | Labels `"OF+ " + patterns[0] + " (" + conf + "%)"`. |
| 26 | `QI_SMC` | 29, 30 | 173-185, 456-461, 2090-2137 (swing points), 2548-2739 | panel + `DrawOnPricePanel=true` | `Confidence`, `Structure` | none | Labels `"SMC " + patterns[0] + " (" + conf + "%)"`. Expose non-plot `TrendDir`. |
| 27 | `QI_KeyLevels` | - | 81-120, 270-273, 285-295, 369-403, 656-1010 | overlay, no plots | none | none | PDH/PDL (RTH 8:30-16:00 CST), Monthly H/L, 30-min ORB, Asian session H/L lines + labels with ORIG toggles and brushes. |

## Validation harness

`validation/QI_EgvDump.cs` is **not** shipped as an indicator for users; it instantiates every
`QI_*` module and writes one CSV row per bar so the values can be diffed against ORIG's
`CsvLogMode = EveryBar` output. The output folder is a property (no hard-coded path).
