# Channel A — documentation audit, claims C1–C12 (API table)

status:    COMMITTED 2026-10-15, before any Channel B result was read
auditor:   Channel A (documentation / primary source only; no code executed, no probes run)
pin:       NinjaTrader 8.1.8.3 (validation/env-pin.txt); help guide https://ninjatrader.com/support/helpGuides/nt8/
           (every per-topic URL 301-redirects to https://static.ninjatrader.com/support/helpGuides/nt8/<page>.htm;
           quotes below were taken from the redirect target on 2026-10-15)
version note: the NT8 help guide carries no version selector and no per-page version stamp; it is the only
           official reference for 8.1.x. Where a page was silent or 404, the NinjaTrader-shipped sources in
           C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\**\@*.cs (copyright header "2026, NinjaTrader LLC",
           the files installed with 8.1.8.3) were used as tier-2 evidence.
code read: all 27 indicators/QI_*.cs (grep of every audited symbol, plus full reads of the OnStateChange /
           draw call sites in QI_IBS, QI_KeyLevels, QI_LiquiditySweep, QI_HedgingPressure, QI_TurnOfMonth,
           QI_StochFade, QI_MACDHistogram, QI_BollingerPctB, QI_ChopIndex, QI_VolumeDelta, QI_VWAPDistance).
inadmissible, not consulted: blogs, forum posts, Stack Overflow, tutorials, the ORIG IBSFade.cs (it is the
           code under audit's parent, not a reference), and model memory.

Pages that could not be retrieved (404 at both hosts on 2026-10-15): isintraday.htm, brushtostring.htm,
barstype.htm, barstype_isintraday.htm, iseriest.htm was fine; understanding_the_lifecycle_of_your.htm 404.
Substitutes used: bars.htm, bars_type.htm, working_with_brushes.htm, onstatechange.htm, value.htm, iseriest.htm.

## Tally

| verdict      | claims                                   |
|--------------|------------------------------------------|
| CONFIRMED    | C1, C3, C4, C5, C6, C7, C8, C12          |
| REFUTED      | C9, C11                                  |
| UNVERIFIABLE | C2, C10                                  |

Usage findings that the docs say are invalid (details under the claim): C9 (QI_IBS line 80, QI_VWAPDistance
line 102 read `Bars` in State.Configure); C5 (QI_IBS line 81-82 calls AddDataSeries conditionally on a
run-time value, which the docs say to avoid); C11 (eleven `Draw.HorizontalLine` calls use a 6-argument form
that is not in the documented overload list); C8 (BackBrush shades the indicator's own panel, not the price
panel, for the two non-overlay files that use it).

---

```
claim_id:    C1
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/addline.htm
source_tier: 1
version:     NT8 help guide (unversioned; current 8.1.x guide)
quote:       "AddLine(Brush brush, double value, string name)"
             "This method should ONLY be called within the OnStateChange() method during State.SetDefaults or State.Configure"
retrieved:   2026-10-15
note:        All 21 QI files that call AddLine do so inside `if (State == State.SetDefaults)` with
             (Brushes.X, <double literal>, "<name>") — e.g. QI_IBS.cs:74-75, QI_RSI2.cs:75-76,
             QI_HedgingPressure.cs:110-113, QI_VolumeDelta.cs:80. Argument order and state match the page.
             Deprecation check: page carries no deprecated/removed notice; the shipped @RSI.cs:45-46 and
             @StochasticsFast.cs:44-45 use the identical 3-arg Brush overload in State.SetDefaults.
```

```
claim_id:    C2
verdict:     UNVERIFIABLE
source:      https://static.ninjatrader.com/support/helpGuides/nt8/line_class.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/lines.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/addline.htm
source_tier: 1 (plus a tier-2 negative search of the shipped sources)
version:     NT8 help guide (unversioned)
quote:       line_class.htm, Value row: "A double representing the value of the line"
             lines.htm, Syntax: "Lines[int index]"
             addline.htm, Note: "Alternatively, you may use custom public Brush, Stroke or value properties which are accessible in the"
             "State.SetDefaults and pass those values to AddLine() during State.Configure."
retrieved:   2026-10-15
note:        What the docs decide: `Lines[i]` exists and `Line.Value` is a double (CONFIRMED sub-part).
             What the docs do NOT decide: (a) that `Value` has a public setter — the Line Class page lists
             it as a property without stating get/set; the only mutation the Lines page demonstrates is
             `Lines[1].Brush` / `Lines[1].Width` from OnBarUpdate; (b) that assigning `Lines[i].Value` in
             State.Configure relocates the drawn line. The documented pattern for a property-driven line
             level is to call AddLine() itself in State.Configure with the property value (addline.htm
             Note, quoted above) — the opposite of what the QI files do (AddLine in SetDefaults, then
             `Lines[0].Value = LowerThreshold;` in State.Configure: QI_IBS.cs:84-85, QI_RSI2.cs:80-81,
             QI_HedgingPressure.cs:117-118 and 15 other files). A grep of all 122 shipped @*.cs for
             `Lines[...].Value =` returns no match, so there is no primary-source precedent either way.
             Absence of documentation is not evidence; this is exactly the pre-registered B runtime probe
             ("set LowerThreshold=0.33 on QI_IBS and read the line level").
```

```
claim_id:    C3
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/draw_textfixed.htm
source_tier: 1 (tier-2 corroboration: @CandleStickPattern.cs:235-236)
version:     NT8 help guide (unversioned)
quote:       "Draw.TextFixed(NinjaScriptBase owner, string tag, string text, TextPosition textPosition, Brush textBrush, SimpleFont "
             "font, Brush outlineBrush, Brush areaBrush, int areaOpacity)"
             areaOpacity: "Valid values between 0 - 100. (0 = completely transparent, 100 = no opacity)"
retrieved:   2026-10-15
note:        Nine parameters in exactly the claimed order. Every QI file calls
             `Draw.TextFixed(this, "QI_Disclaimer", "<string>", TextPosition.BottomLeft, Brushes.Gray,
             new SimpleFont("Arial", 9), Brushes.Transparent, Brushes.Transparent, 0)` (e.g. QI_IBS.cs:137-139);
             QI_HedgingPressure.cs:288-290 and QI_ChopIndex.cs:193-195 use the same overload with
             TextPosition.TopRight. Calls are made from OnBarUpdate (a documented draw context). The shipped
             @CandleStickPattern.cs:235 uses the identical 9-argument call.
```

```
claim_id:    C4
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/drawonpricepanel.htm
source_tier: 1
version:     NT8 help guide (unversioned)
quote:       "Determines the chart panel the draw objects renders"
             "This property returns true if the indicator paints draw objects on the price panel;"
             "otherwise when false, draw objects are painted on the actual indicator panel itself."
             "This property should ONLY be set from the OnStateChange() method during State.SetDefaults."
retrieved:   2026-10-15
note:        The page ties the behaviour to the property alone and never conditions it on IsOverlay, so a
             non-overlay indicator with DrawOnPricePanel = true draws on the price panel per the docs.
             QI_HedgingPressure.cs:93,95 (IsOverlay=false, DrawOnPricePanel=true), QI_LiquiditySweep.cs:145,147,
             QI_OrderFlowPlus.cs:100,102, QI_SMC.cs:117,119 all set it inside State.SetDefaults as required.
             The overlays QI_KeyLevels, QI_EMACross, QI_SMA200Trend also set it in SetDefaults.
```

```
claim_id:    C5
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/adddataseries.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/barsinprogress.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/currentbars.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/closes.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/highs.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/lows.htm
source_tier: 1
version:     NT8 help guide (unversioned)
quote:       adddataseries.htm: "AddDataSeries(BarsPeriodType periodType, int period)"
             "This method should ONLY be called from the OnStateChange() method during State.Configure"
             "// Add a 5 minute Bars object - BarsInProgress index = 1"
             barsinprogress.htm: "An index value of the current Bars object that has called the OnBarUpdate() method."
             currentbars.htm: "CurrentBars[int barSeriesIndex]"
             "In multi series processing, the CurrentBars starting value will be -1 until all series have processed the first bar."
             closes.htm: "Closes[int barSeriesIndex][int barsAgo]"
             highs.htm: "Highs[int barSeriesIndex][int barsAgo]"   lows.htm: "Lows[int barSeriesIndex][int barsAgo]"
retrieved:   2026-10-15
note:        Signature, required state (QI_IBS.cs:77-82 is inside State.Configure), index assignment
             (first added series = 1, primary = 0) and the four accessors all match the QI_IBS usage at
             lines 99-116. The `CurrentBars[1] < 1` guard at line 99 is consistent with the documented -1
             start value.
             INVALID-USAGE FLAG (does not change the verdict on the claim as worded, which is about the
             symbols): adddataseries.htm Warning —
             "Arguments supplied to AddDataSeries() should be hardcoded and NOT dependent on run-time variables"
             "(e.g., Instrument, Bars, or user input)."
             "Attempting to add a data series dynamically is NOT guaranteed and therefore should be avoided."
             "Trying to load bars dynamically may result in an error similar to: Unable to load bars series."
             QI_IBS.cs:80-82 executes `AddDataSeries(Data.BarsPeriodType.Day, 1)` only `if (useDailySeries)`
             where `useDailySeries = Bars.BarsType.IsIntraday` — the call's presence depends on `Bars`, which
             the page says to avoid. The shipped @CamarillaPivots.cs:82-83 also adds a Day series
             conditionally, but on a user property (`priorDayHlc`), not on `Bars`. See C9 for the second,
             independent problem with that same line.
```

```
claim_id:    C6
verdict:     CONFIRMED
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@StochasticsFast.cs
source_tier: 2 (installed library source, NinjaTrader-shipped, header "Copyright (C) 2026, NinjaTrader LLC")
version:     files installed with NinjaTrader 8.1.8.3 (env-pin.txt)
quote:       line 95:  "public StochasticsFast StochasticsFast(int periodD, int periodK)"
             line 100: "public StochasticsFast StochasticsFast(ISeries<double> input, int periodD, int periodK)"
             line 71:  "public Series<double> D => Values[0];"
             line 75:  "public Series<double> K => Values[1];"
             line 42-43: "AddPlot(Brushes.DodgerBlue, Custom.Resource.StochasticsD);" / "AddPlot(Brushes.Goldenrod, Custom.Resource.StochasticsK);"
             line 63:  "K[0] = den[0].ApproxCompare(0) == 0 ? CurrentBar == 0 ? 50 : K[1] : Math.Min(100, Math.Max(0, 100 * nom[0] / den[0]));"
             line 65:  "D[0] = smaK[0];"   (line 53: "smaK = SMA(K, PeriodD);")
retrieved:   2026-10-15
note:        QI_StochFade.cs:88 `stoch = StochasticsFast(3, 14);` → periodD = 3, periodK = 14, matching the
             (periodD, periodK) parameter order at line 95. QI_StochFade.cs:100-101 read `stoch.K[0]` and
             `stoch.D[0]`, which are Values[1] and Values[0] respectively — exactly as the claim states.
             No deprecation marker in the file.
```

```
claim_id:    C7
verdict:     CONFIRMED
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@RSI.cs, @Bollinger.cs, @MACD.cs,
             @ADX.cs, @StdDev.cs, @ATR.cs, @EMA.cs, @SMA.cs, @Range.cs, @TMA.cs, @APZ.cs, @VolumeOscillator.cs
             https://static.ninjatrader.com/support/helpGuides/nt8/iseriest.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/value.htm
source_tier: 2 for signatures (installed shipped source), 1 for the ISeries/Value semantics
version:     files installed with NinjaTrader 8.1.8.3; NT8 help guide (unversioned)
quote:       @RSI.cs:141        "public RSI RSI(ISeries<double> input, int period, int smooth)"
             @Bollinger.cs:94   "public Bollinger Bollinger(ISeries<double> input, double numStdDev, int period)"
             @Bollinger.cs:76   "public Series<double> Upper => Values[0];"
             @Bollinger.cs:64   "public Series<double> Middle => Values[1];"
             @Bollinger.cs:60   "public Series<double> Lower => Values[2];"
             @MACD.cs:173       "public MACD MACD(ISeries<double> input, int fast, int slow, int smooth)"
             @MACD.cs:116       "public Series<double> Diff => Values[2];"
             @MACD.cs:92        "Diff[0] = macd - macdAvg;"
             @ADX.cs:121        "public ADX ADX(int period)"
             @StdDev.cs:79      "public StdDev StdDev(ISeries<double> input, int period)"
             @ATR.cs:64         "public ATR ATR(int period)"
             @EMA.cs:64         "public EMA EMA(ISeries<double> input, int period)"
             @SMA.cs:86         "public SMA SMA(ISeries<double> input, int period)"
             @Range.cs:42       "public Range Range()"
             composition precedents: @TMA.cs:52 "sma = SMA(SMA(Inputs[0], p1), p2);"
                                     @APZ.cs:45 "emaRange = EMA(Range(), Period);"
                                     @VolumeOscillator.cs:45 "smaFast = SMA(Volume, Fast);"
             iseriest.htm Tip:  "you can then pass in an array of closing prices, an indicator, or a user defined data series"
             value.htm:         "A collection of historical references to the first ISeries object Values[0] in the indicator."
retrieved:   2026-10-15
note:        Every QI call site matches: RSI(Close, 14, 1) / RSI(Close, 2, 1) / RSI(streakSeries, 2, 1)
             (QI_RSI14.cs:85, QI_RSI2.cs:85, QI_ConnorsRSI.cs:102,104); Bollinger(Close, 2, 20) with
             .Upper/.Lower (QI_BollingerPctB.cs:91,104); MACD(Close, 12, 26, 9).Diff (QI_MACDHistogram.cs:83,95);
             ADX(14) (QI_ChopIndex.cs:103); StdDev(Close, 20) (QI_CompositeVol.cs:101); ATR(14)/ATR(5)
             (QI_VRPProxy.cs:83-84 et al.); EMA(Close, 20/50) (QI_EMACross.cs:83-84); SMA(Close, 200)
             (QI_SMA200Trend.cs:81). Compositions SMA(atr14, 50) (QI_ATRRegime.cs:83), SMA(Range(), 20)
             (QI_HedgingPressure.cs:134), SMA(Volume, 20) (QI_VolumeSpike.cs:80) and SMA(volDelta, 10) over a
             Series<double> (QI_VolumeDelta.cs:88) each have a shipped precedent of the same shape (quoted
             above), and the ISeries<T> page states an indicator is an acceptable input. All QI
             instantiations are in State.DataLoaded, the state onstatechange.htm names for
             "instantiating indicators". No deprecation markers in any of the ten shipped files.
             OBSERVATION for the owner of C27 (not a C7 defect): QI_BollingerPctB.cs:103 reads
             `double bollMid = boll[0];`. By value.htm the indexer on an indicator is Values[0], and by
             @Bollinger.cs:76 Values[0] of Bollinger is `Upper`, not `Middle` (Values[1]). The variable name
             and the file's header comment ("(Close - mid)") say middle band; the symbol resolves to the
             upper band. Whether this reproduces ORIG is a C27 question, not a C7 one.
```

```
claim_id:    C8
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/backbrush.htm
source_tier: 1
version:     NT8 help guide (unversioned)
quote:       "Sets the brush used for painting the chart panel's background color for the current bar."
             "A Brush object that represents the color of the current chart bar."
             "BackBrush = Brushes.PaleGreen;"
             "Note: This property will only set the back color for the panel the indicator is running."
             "To set background color for all panels, please see the BackBrushAll property."
retrieved:   2026-10-15
note:        `BackBrush = shadeBrush;` at QI_TurnOfMonth.cs:106 and QI_TurnaroundTuesday.cs:105, assigned
             from OnBarUpdate with a frozen SolidColorBrush cached in State.DataLoaded (QI_TurnOfMonth.cs:87-89),
             which also respects the page's warning to cache custom brushes (65,535-instance limit).
             SCOPE NOTE for the pre-registered B probe ("Monday bars shaded by QI_TurnaroundTuesday"): both
             files are IsOverlay = false (QI_TurnOfMonth.cs:68, QI_TurnaroundTuesday.cs:67), so per the Note
             quoted above the shading appears in the indicator's own panel, not on the price panel. A probe
             that looks for shading on the price panel will report a false negative.
```

```
claim_id:    C9
verdict:     REFUTED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/bars.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/onstatechange.htm
             (tier 2, member existence only) C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@CurrentDayOHL.cs
source_tier: 1
version:     NT8 help guide (unversioned)
quote:       bars.htm Warning: "The Bars object and its member should NOT be accessed within the OnStateChange() method"
             "before the State has reached State.DataLoaded"
             onstatechange.htm, State.DataLoaded: "Use for logic that needs to access data related objects like Bars, Instruments, BarsPeriod, TradingHours"
             @CurrentDayOHL.cs:63-65: "else if (State == State.Historical)" / "if (!Bars.BarsType.IsIntraday)"
retrieved:   2026-10-15
note:        The claim is "`Bars.BarsType.IsIntraday` is readable in State.Configure". The member itself
             exists (shipped @CurrentDayOHL.cs:65,75, @BarTimer.cs:46, @CamarillaPivots.cs:96 read it — in
             State.Historical, State.Realtime and OnBarUpdate; none of the 122 shipped files reads `Bars`
             in State.Configure). The docs state directly that `Bars` must not be accessed in OnStateChange
             before State.DataLoaded; State.Configure precedes DataLoaded. Two QI files do exactly what the
             page forbids:
               QI_IBS.cs:80          `useDailySeries = Bars.BarsType.IsIntraday;`   (State.Configure)
               QI_VWAPDistance.cs:102 `isIntraday = Bars.BarsType.IsIntraday;`       (State.Configure)
             Because QI_IBS then conditions AddDataSeries on that value (C5 flag), and AddDataSeries may
             only be called in State.Configure, there is no documented state in which the file's design can
             be made compliant without restructuring (e.g. always add the Day series, or decide from a
             user property as @CamarillaPivots.cs:82-83 does). No dedicated IsIntraday page could be located
             (isintraday.htm and barstype_isintraday.htm 404; bars_type.htm lists IsTimebased only).
```

```
claim_id:    C10
verdict:     UNVERIFIABLE
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@CamarillaPivots.cs (symbol)
             C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@BarTimer.cs (namespace resolution)
             https://static.ninjatrader.com/support/helpGuides/nt8/timezoneinfo.htm (documents a different member)
             https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/default-time-zones (did not decide it)
source_tier: 2 for the symbol; no admissible source for the machine-specific half
version:     files installed with NinjaTrader 8.1.8.3
quote:       @CamarillaPivots.cs:14  "using NinjaTrader.Core;"
             @CamarillaPivots.cs:231 "sessionDateTmp = TimeZoneInfo.ConvertTime(cacheSessionEnd.AddSeconds(-1), Globals.GeneralOptions.TimeZoneInfo, Bars.TradingHours.TimeZoneInfo).Date;"
             @BarTimer.cs:22         "private DateTime now = Core.Globals.Now;"   (file has no `using NinjaTrader.Core;`, lines 6-12)
             timezoneinfo.htm Syntax: "Bars.TradingHours.TimeZoneInfo"
retrieved:   2026-10-15
note:        Sub-verdict (a) CONFIRMED at tier 2: `NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo`
             exists and is of a type accepted by `TimeZoneInfo.ConvertTime(DateTime, TimeZoneInfo, TimeZoneInfo)`,
             because the shipped @CamarillaPivots.cs:231 passes it to that exact .NET overload. The QI
             files write it as `Core.Globals.GeneralOptions.TimeZoneInfo` from inside
             `namespace NinjaTrader.NinjaScript.Indicators` (QI_KeyLevels.cs:197-198, QI_TurnOfMonth.cs:98-99,
             QI_TurnaroundTuesday.cs:97-98, QI_LiquiditySweep.cs:281-282); the shipped @BarTimer.cs:22 uses the
             same `Core.Globals` spelling from the same namespace without a `using NinjaTrader.Core;`, so the
             partial qualification is a shipped precedent. The help guide's timezoneinfo.htm documents only
             `Bars.TradingHours.TimeZoneInfo`; no page for GeneralOptions was found.
             Sub-verdict (b) UNVERIFIABLE: "`TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time")`
             resolves on this machine" is a property of this Windows installation's time-zone registry, not
             of any document. The Microsoft default-time-zones page lists per-region defaults only (it has
             "Central Standard Time (Mexico)" and US rows for Mountain/Pacific but no row for the ID
             "Central Standard Time"), so it neither confirms nor refutes. Channel A may not run `tzutil /l`
             or read the registry; this half is the pre-registered B runtime probe (QI_KeyLevels load, no
             log error). The conjunction is therefore recorded as UNVERIFIABLE; it must not be read as a
             defect finding.
```

```
claim_id:    C11
verdict:     REFUTED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/draw_horizontalline.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/draw_text.htm
             https://static.ninjatrader.com/support/helpGuides/nt8/draw_line.htm
             (tier-2 negative search) C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\**\@*.cs
source_tier: 1
version:     NT8 help guide (unversioned)
quote:       draw_horizontalline.htm, the complete Syntax section (5 overloads):
             "Draw.HorizontalLine(NinjaScriptBase owner, string tag, double y, Brush brush)"
             "Draw.HorizontalLine(NinjaScriptBase owner, string tag, bool isAutoScale, double y, Brush brush, DashStyleHelper dashStyle, int width)"
             "Draw.HorizontalLine(NinjaScriptBase owner, string tag, bool isAutoscale, double y, Brush brush, bool drawOnPricePanel)"
             "Draw.HorizontalLine(NinjaScriptBase owner, string tag, double y, Brush brush, DashStyleHelper dashStyle, int width, bool drawOnPricePanel)"
             "Draw.HorizontalLine(NinjaScriptBase owner, string tag, double y, bool isGlobal, string templateName)"
             draw_text.htm:
             "Draw.Text(NinjaScriptBase owner, string tag, bool isAutoScale, string text, int barsAgo, double y, int yPixelOffset, Brush textBrush, SimpleFont font, TextAlignment alignment, Brush outlineBrush, Brush areaBrush, int areaOpacity)"
             draw_line.htm, overload 2 (parameter names as listed):
             "owner, tag, isAutoScale, startBarsAgo, startY, endBarsAgo, endY, brush, dashStyle, width"
retrieved:   2026-10-15
note:        The claim is a conjunction of three signatures.
             Draw.Text 13-arg: CONFIRMED — QI_KeyLevels.cs:434-438 `Draw.Text(this, "KL_PrevDayHighLbl", false,
               "<text>", 0, prevDayHigh, 5, PrevDayHighBrush, labelFont, TextAlignment.Right,
               Brushes.Transparent, Brushes.Transparent, 0)` matches the documented overload type-for-type;
               same at QI_HedgingPressure.cs:296-312, QI_LiquiditySweep.cs:720-722, QI_OrderFlowPlus.cs:335,
               QI_SMC.cs:416. Shipped @CandleStickPattern.cs:29-30 uses the same overload.
             Draw.Line 10-arg: CONFIRMED — QI_LiquiditySweep.cs:737-739 `Draw.Line(this, tag, true, barsBack,
               pendingSweepStartPrice, 0, anchor, brush, DashStyleHelper.Dash, 2)` matches overload 2.
             Draw.HorizontalLine 6-arg `(owner, tag, double y, Brush, DashStyleHelper, int width)`: REFUTED —
               the documented Syntax section lists exactly five overloads (recounted on a second fetch) and
               none has this parameter list. The two nearest documented forms each require one more
               argument: `bool isAutoScale` inserted after `tag` (overload 2) or `bool drawOnPricePanel`
               appended (overload 4). The QI call form appears eleven times:
               QI_KeyLevels.cs:427-430, 461-464, 496-499, 530-533 and QI_HedgingPressure.cs:272-279, e.g.
               `Draw.HorizontalLine(this, "KL_PrevDayHigh", prevDayHigh, PrevDayHighBrush, DashStyleHelper.DashDotDot, 2);`
               A grep of all 122 shipped @*.cs for `Draw.HorizontalLine(` returns no call at all, so there is
               no tier-2 evidence of an undocumented overload. If the 8.1.8.3 assembly does expose such an
               overload, the help guide does not document it; Channel B's compile probe on QI_KeyLevels and
               QI_HedgingPressure is the deciding test. The pre-registered falsifier for C11 (CS1501/CS1503)
               is precisely the error this call form would raise if the documented list is exhaustive.
```

```
claim_id:    C12
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/working_with_brushes.htm
             C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@MACD.cs
source_tier: 1 (tier-2 corroboration)
version:     NT8 help guide (unversioned); files installed with NinjaTrader 8.1.8.3
quote:       working_with_brushes.htm:
             "[XmlIgnore]" / "public Brush MyBrush { get; set; }" / "[Browsable(false)]" / "public string MyBrushSerialize"
             "get { return Serialize.BrushToString(MyBrush); }" / "set { MyBrush = Serialize.StringToBrush(value); }"
             "the object itself cannot be serialized directly to the .xml file and will result in errors"
             @MACD.cs:135: "public string PositiveIncreasingBrushSerialize { get => Serialize.BrushToString(PositiveIncreasingBrush); set => PositiveIncreasingBrush = Serialize.StringToBrush(value); }"
retrieved:   2026-10-15
note:        brushtostring.htm 404s; the pattern is documented on the Working with Brushes page and is the
             exact shape used at QI_KeyLevels.cs:598-604 (and the other seven brush pairs there),
             QI_HedgingPressure.cs:361-377, QI_LiquiditySweep.cs:846-855, QI_OrderFlowPlus.cs:401-409,
             QI_SMC.cs:482-490. `Serialize` lives in NinjaTrader.Gui (shipped @CandleStyle.cs:184 writes it as
             `Gui.Serialize.BrushToString`); every QI file carries `using NinjaTrader.Gui;` (e.g.
             QI_KeyLevels.cs:44). Minor-materiality claim; no deprecation notice on the page.
```

---

## Cross-claim usage notes (for the convergence gate)

1. QI_IBS.cs:77-86 (State.Configure) violates two documented rules at once: it reads `Bars` before
   State.DataLoaded (bars.htm; C9 REFUTED) and makes the AddDataSeries call conditional on that run-time
   value (adddataseries.htm Warning; flagged under C5). QI_VWAPDistance.cs:102 has the first violation only.
2. Eleven `Draw.HorizontalLine` calls (QI_KeyLevels, QI_HedgingPressure) use an overload the help guide
   does not list (C11 REFUTED). Adding `false` as the third argument (overload 2) or appending
   `DrawOnPricePanel` as a seventh (overload 4) would map each call onto a documented form.
3. `Lines[i].Value = <property>` in State.Configure (18 files) is undocumented in both directions (C2
   UNVERIFIABLE); the documented alternative is to call AddLine() with the property value in
   State.Configure (addline.htm Note).
4. BackBrush in the two non-overlay files shades the indicator panel, not the price panel (backbrush.htm
   Note); the B probe for C8 must look there.
5. QI_BollingerPctB.cs:103 `boll[0]` is Bollinger.Values[0] = Upper per @Bollinger.cs:76 and value.htm,
   although named and commented as the middle band — handed to C27.
