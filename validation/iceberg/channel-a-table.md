# Channel A (documentation auditor): QI_28 table-panel ledger T1–T21

- ledger: `validation/iceberg/table-claims-ledger.md` (FROZEN 2026-10-29; not edited)
- mode: Mode 1 (dual subagent). This file was written without reading any Channel B output.
- installed: NinjaTrader 8.1.8.4 (`validation/env-pin.txt`)
- allowed evidence:
  - **HG** = official NinjaTrader 8 Help Guide, https://ninjatrader.com/support/helpGuides/nt8/. The guide is not versioned; it covers NT 8.x as published live on the retrieval date. The pages under "SharpDX SDK Reference" carry NT's own disclaimer that they were compiled from the official SharpDX docs.
  - **SRC** = vendor NinjaScript source that NinjaTrader 8.1.8.4 installs under `C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\` (files with an `@` prefix and the header `Copyright (C) 2026, NinjaTrader LLC`). This is the exact installed version.
  - **SKIN** = vendor skin resources at `C:\Users\rajib\Documents\NinjaTrader 8\templates\Skins\*\BluePrint.xaml` (installed with 8.1.8.4).
- method: fetched the pages with Python urllib and read the files. Nothing was executed, compiled or reflected.
- retrieved: 2026-10-29 (all records)

## Verdict table

| ID | Mat | Verdict | Primary source(s) | One-line basis |
|----|-----|---------|-------------------|----------------|
| T1 | M | CONFIRMED | HG onrender.htm; SRC Indicators\@PriceLine.cs:95 | The syntax is `protected override void OnRender(ChartControl chartControl, ChartScale chartScale)`. |
| T2 | M | CONFIRMED | HG onrendertargetchanged.htm; SRC @PriceLine.cs:128 | The syntax is `public override void OnRenderTargetChanged()`. It is **public**, not protected. |
| T3 | M | CONFIRMED | HG using_sharpdx_for_custom_chart_rendering.htm; onrendertargetchanged.htm | Brushes are device-dependent: they "must be created and dispose of any time the RenderTarget is updated", and NT gives no guarantee that it disposes them. |
| T4 | M | CONFIRMED | HG chartpanel.htm; SRC DrawingTools\@Lines.cs:264-265 | X, Y, W and H are documented in pixels. The vendor line `int totalWidth = chartPanel.W + chartPanel.X;` only compiles if they are integer-typed. |
| T5 | M | CONFIRMED | HG working_with_chart_object_coordinates.htm; using_sharpdx…htm | The origin is top-left and y grows downward. (ChartPanel.X, ChartPanel.Y) is the panel's top-left corner. Use ChartPanel X/Y/W/H "for full absolute device coordinates". |
| T6 | M | CONFIRMED (by inference) | HG working_with_chart_object_coordinates.htm; chartpanel.htm | The canvas is "bounded on the bottom by the x-axis, and on the right, left, or both by the y-axis", and the panel X/Y lie "on the chart canvas". Two pages combine to support this; no single sentence states it. |
| T7 | M | CONFIRMED | HG simplefont_class.htm, simplefont_todirectwritetextformat.htm; SRC @Text.cs:480 | The return value is "A DirectWrite.TextFormat object", which must be disposed. |
| T8 | M | CONFIRMED | HG directwritefactory.htm; SRC @Text.cs:481 | It is "A read-only SharpDX.DirectWrite.Factory", accessed through the type as `NinjaTrader.Core.Globals.DirectWriteFactory`, so it is static. |
| T9 | M | CONFIRMED | HG sharpdx_directwrite_textlayout.htm, …_textlayout_metrics.htm; SRC @Text.cs:481-484 | The constructor `new TextLayout(Factory factory, string text, TextFormat textFormat, float maxWidth, float maxHeight)` exists, and Metrics.Width and Metrics.Height are documented as "A float value". |
| T10 | M | CONFIRMED | HG dxextensions_todxbrush.htm; SRC ChartStyles\@CandleStyle.cs:176 | The syntax is `DxExtensions.ToDxBrush( this System.Windows.Media.Brush brush, RenderTarget renderTarget)` and it returns "A new SharpDX.Direct2D1.Brush". |
| T11 | M | CONFIRMED | HG sharpdx_direct2d1_rendertarget_fillrectangle / _drawrectangle / _drawtextlayout .htm; SRC @Text.cs:201,210,220 | All three overloads are listed verbatim in the syntax sections. |
| T12 | M | CONFIRMED (as "not guaranteed to be the same thread") | HG multi-threading.htm | Charts run on UI threads, while market data goes out on worker threads or a "randomly assigned UI thread", so "no guarantee" of the same thread. The docs do not say "always different". |
| T13 | M | CONFIRMED | HG drawingtools_drawobjects.htm, textfixed.htm; SRC @Text.cs:110,126,567 | DrawObjects is documented. TextFixed exposes TextPosition, DisplayText and Font (Font is of type `Gui.Tools.SimpleFont`). |
| T14 | M | CONFIRMED | HG drawingtools_drawobjects.htm | "all of the drawn chart objects on the chart, for all series … can be manually drawn or script generated". There is a load-order caveat (see the record). |
| T15 | M | CONFIRMED | SRC @Text.cs:520-563, 434-466 | Position comes only from TextPosition, the panel rectangle and the object's own text metrics. Nothing looks at other objects, so there is no stacking. |
| T16 | M | CONFIRMED (offset and box geometry are literal in source; the padding value is a resource lookup) | SRC @Text.cs:36,182,220,239,456,465,481-484,532,544-545,586; SKIN BluePrint.xaml | Offset is `const float padding = 10.5f`. Inner padding is `outlinePadding`, which comes from the resource "FontModalTitleMargin" with fallback `3f`. Numbers below. |
| T17 | M | UNVERIFIABLE | SRC @Text.cs:553 (comment only); HG working_with_indicators.htm, chart_properties.htm | The vendor TopLeft code moves down "to make enough room for labels", which implies labels at the top-left. No primary source states where labels are drawn. Overlap is not decidable, and the vendor code actually tries to avoid it. |
| T18 | M | UNVERIFIABLE | HG marketdataeventargs.htm; SRC MarketAnalyzerColumns\@TimeLastTick.cs:48 | Time is only "A DateTime structure representing the time". The vendor uses it as last-tick time. The Playback (replayed time) half is not documented. |
| T19 | m | CONFIRMED | HG isinhittest.htm, rendertarget.htm; SRC @AndrewsPitchfork.cs:481-484, @Arc.cs:157, @Polygon.cs:470 | It is a bool that is true while the panel is being clicked (the hit-test bitmap pass). Vendor tools skip fills and labels when it is true. |
| T20 | m | CONFIRMED | HG chartcontrol_properties.htm; SRC @Text.cs:448 | "ChartBackground — A Brush object used to paint the chart background"; "ChartText — A Brush object used to paint text on the chart". |
| T21 | m | CONFIRMED | HG forcerefresh.htm; SRC Indicators\@BarTimer.cs:107 | `ForceRefresh()` exists and an Indicator calls it. It re-queues the render rather than repainting immediately (up to 250 ms). |

Summary: 19 CONFIRMED (T6 and T12 with scoped wording, T16 with a caveat on the padding value), 2 UNVERIFIABLE (T17, T18), 0 REFUTED.

---

## T16 numbers (TextFixed placement, from `DrawingTools\@Text.cs`, NT 8.1.8.4)

Pipeline (Text.OnRender, lines 453-466):

1. `UpdateTextLayout(chartPanel.W)` (456). A TextLayout is created with maxWidth = panel width and maxHeight = font size (481). It is then trimmed to the measured text: `MaxWidth = Metrics.Width; MaxHeight = Metrics.Height` (483-484). So **text w = TextLayout.Metrics.Width and text h = TextLayout.Metrics.Height**. Per the HG Metrics page, Width ignores trailing whitespace, and per the SharpDX guide, Height includes the font's line spacing.
2. `GetTextDrawingPosition` (TextFixed override, 520-563) returns the text origin (x, y):
   - `const float padding = 10.5f;` (532), the "amount of padding from panel edges".
   - **BottomRight** (543-545): `x = chartPanel.X + chartPanel.W - padding - textWidth;` `y = chartPanel.Y + chartPanel.H - textHeight - padding;`. The text's right edge sits 10.5 px left of the panel's right edge, and its bottom edge 10.5 px above the panel's bottom edge. No multiplier applies to BottomRight.
   - BottomLeft (540-541): x = X + 10.5; y = Y + H − h − 10.5 × m, where m = 2 on the last panel and 1 otherwise ("make enough room for copyright"; PaddingMultiplier at 582-584).
   - TopLeft (552-553): x = X + 10.5; y = Y + 21 (`padding * 2 // make enough room for labels`).
   - TopRight (556-557): x = X + W − 10.5 − w; y = Y + (int)(10.5 × m), where m = 4 when it is panel 0 and `IsScrollArrowVisible`, so y = Y + 42; otherwise m = 1, so y = Y + 10.
   - Center (548-549): centred on the panel.
3. `y -= YPixelOffset` (463). The default is 0 (322), and Draw.TextFixed never sets it.
4. `layoutRect = new Rect(x, y, MaxWidth, MaxHeight)` (465).
5. Box rectangle (fill and outline): `TextFixedBase.GetCurrentRect` (586) is `new(layoutRect.X - outlinePadding, layoutRect.Y - outlinePadding, layoutRect.Width + outlinePadding * 2, layoutRect.Height + outlinePadding * 2)`. **The box is the text box grown by p on every side.**
6. The fill is drawn with `RenderTarget.FillRectangle(outlineRectDx, …)` (201) and the outline with `DrawRectangle(outlineRectDx, brush, outlineStroke.Width, …)` (210). Per HG drawrectangle.htm, "The stroke is centered on the rectangle's outline". The default OutlineStroke is `new Stroke(Brushes.Transparent, 2f)` (318). The 9-argument Draw.TextFixed passes outlineWidth 2 (989).
7. The text is drawn at `new SharpDX.Vector2(outlineRectDx.X + outlinePadding, outlineRectDx.Y + outlinePadding)` (220), which equals (x, y).

Inner padding p (`outlinePadding`), line 36 → 239:
`private static float GetPadding() => Application.Current.FindResource("FontModalTitleMargin") as float? ?? 3f;`
- Every shipped skin defines this key as a **Double**: `<system:Double x:Key="FontModalTitleMargin">5</system:Double>` (Dark:694, Light:689, NinjaTrader:677, NinjaTrader Dark:693, Slate Dark:696, Slate Gray:698, Slate Light:682).
- Under C# `as` semantics, a boxed `System.Double` does not unbox to `float?`, so the expression gives null and the fallback is used. **Deduced effective p = 3 px, not 5.** This is a reading of the language rule. It was not executed, so Channel B should measure it.

Resulting BottomRight box, with p = 3 (the deduced value) and p = 5 in brackets in case the resource were honoured:
- box right edge = panel right − 10.5 + p = **panel right − 7.5** [−5.5]
- box bottom edge = panel bottom − 10.5 + p = **panel bottom − 7.5** [−5.5]
- box width = w + 2p = **w + 6** [w + 10]; box height = h + 2p = **h + 6** [h + 10]
- box top-left = (X + W − 10.5 − w − p, Y + H − 10.5 − h − p)
- a 2 px outline stroke extends a further 1 px outside the box.

---

## Per-claim evidence records

```
claim_id:    T1
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/onrender.htm ; C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@PriceLine.cs:22,95
source_tier: 1 (HG) + 2 (SRC)
version:     HG unversioned NT8 (8.x, live); SRC = installed 8.1.8.4
quote:       "protected override void OnRender(ChartControl chartControl, ChartScale chartScale)"  /  SRC 22: "public class PriceLine : Indicator"  95: "protected override void OnRender(ChartControl chartControl, ChartScale chartScale)"
retrieved:   2026-10-29
note:        HG definition: "Used to render custom drawing to a chart from various chart objects, such as an Indicator". Tip: call base.OnRender() if the indicator also has Plots. No deprecation found.
```

```
claim_id:    T2
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/onrendertargetchanged.htm ; SRC Indicators\@PriceLine.cs:128
source_tier: 1 + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "You may override the method in your indicator with the following syntax: public override void OnRenderTargetChanged()" / "This method does not accept any parameters"  /  SRC 128: "public override void OnRenderTargetChanged()"
retrieved:   2026-10-29
note:        The access modifier is public (unlike OnRender, which is protected). Writing `protected override` would be a CS0507 error.
```

```
claim_id:    T3
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/using_sharpdx_for_custom_chart_rendering.htm ; https://ninjatrader.com/support/helpGuides/nt8/onrendertargetchanged.htm
source_tier: 1
version:     HG NT8 live
quote:       "The following objects are associated with a specific RenderTarget . They must be created and dispose of any time the RenderTarget is updated: • Brush … • SolidColorBrush"  and  "there is no guarantee that NinjaTrader will be able to dispose of these unmanaged references for you."  and (OnRenderTargetChanged) "you should recreate these resource during OnRenderTargetChanged()"
retrieved:   2026-10-29
note:        Also relevant: TextFormat and TextLayout are listed as device-independent but must still be disposed ("NinjaTrader is NOT guaranteed to dispose of these resources for you!"). The OnRender docs allow the alternative of creating and disposing brushes inside OnRender.
```

```
claim_id:    T4
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/chartpanel.htm ; SRC DrawingTools\@Lines.cs:264-265
source_tier: 1 + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "H  Indicates the height (in pixels) of the chart panel" / "W  Indicates the width (in pixels) of the chart panel" / "X  Indicates the x-coordinate on the chart canvas at which the chart panel begins" / "Y  Indicates the y-coordinate …"  /  SRC 264: "int totalWidth = chartPanel.W + chartPanel.X;" 265: "int totalHeight = chartPanel.Y + chartPanel.H;"
retrieved:   2026-10-29
note:        HG does not print the C# type. The integer type is inferred because the vendor file compiles and C# has no implicit float/double/long → int conversion. The exact declaration (field or property; int or a narrower integral type) is for Channel B reflection.
```

```
claim_id:    T5
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/working_with_chart_object_coordinates.htm ; https://ninjatrader.com/support/helpGuides/nt8/using_sharpdx_for_custom_chart_rendering.htm
source_tier: 1
version:     HG NT8 live
quote:       "the origin point (coordinates 0,0) is in the top-left corner of the canvas, NOT the bottom-left. Moving down the canvas increases the y-coordinate"  and  "// creates a vector located at the top left corner of the chart panel startPoint = new SharpDX. Vector2 (ChartPanel.X, ChartPanel.Y); // creates a vector located at the bottom right corner of the chart panel endPoint = new SharpDX. Vector2 (ChartPanel.X + ChartPanel.W, ChartPanel.Y + ChartPanel.H);"  and  "Note : For full absolute device coordinates always use ChartPanel X, Y, W, H values. ChartScale and ChartControl properties return WPF units"
retrieved:   2026-10-29
note:        Caveat for implementers: ChartPanel values are device pixels, while ChartControl/ChartScale values are WPF units (they differ at non-96 DPI). Do not mix ChartControl.CanvasRight/AxisYRightWidth into ChartPanel math without converting.
```

```
claim_id:    T6
verdict:     CONFIRMED (inference across two HG pages; no single sentence)
source:      https://ninjatrader.com/support/helpGuides/nt8/working_with_chart_object_coordinates.htm ; https://ninjatrader.com/support/helpGuides/nt8/chartpanel.htm ; https://ninjatrader.com/support/helpGuides/nt8/axisxheight.htm
source_tier: 1
version:     HG NT8 live
quote:       "The chart canvas covers the area in which bars, drawing objects, and indicator plots can be painted. It is bounded on the bottom by the x-axis, and on the right, left, or both by the y-axis."  /  "The y-axis extends vertically from the chart's horizontal scroll bar to the top of the chart canvas"  /  "The x-axis sits beneath the chart canvas"  /  ChartPanel X: "the x-coordinate on the chart canvas at which the chart panel begins"  /  AxisXHeight: "the distance (in pixels) between the x-axis and the top of the horizontal scroll bar near the bottom of the chart."
retrieved:   2026-10-29
note:        Chain: panel ⊂ canvas, and canvas excludes the y-axis, the x-axis and the scroll bar below it. Things the vendor source shows ARE inside the panel rectangle: the scroll arrow in the top-right of panel 0 (@Text.cs:557,584 multiplier 4) and the copyright text at the bottom-left of the last panel (@Text.cs:541,583). The bottom-right corner gets no such allowance. Recommend a Channel B rendered check.
```

```
claim_id:    T7
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/simplefont_todirectwritetextformat.htm ; https://ninjatrader.com/support/helpGuides/nt8/simplefont_class.htm ; SRC DrawingTools\@Text.cs:480
source_tier: 1 + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "Method Return Value  A DirectWrite.TextFormat object"  "Warning : The returned DirectWrite.TextFormat object should be disposed of immediately when finished drawing text."  /  SRC 480: "SharpDX.DirectWrite.TextFormat textFormat = Font.ToDirectWriteTextFormat();"  (488: "textFormat.Dispose();")
retrieved:   2026-10-29
note:        Type is NinjaTrader.Gui.Tools.SimpleFont. Size is "A double value … in WPF units".
```

```
claim_id:    T8
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/directwritefactory.htm ; SRC @Text.cs:481
source_tier: 1 + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "Property Value  A read-only SharpDX.DirectWrite.Factory used to create DirectWrite objects compatible with NinjaTrader rendering"  "Syntax  NinjaTrader.Core.Globals.DirectWriteFactory"  /  SRC 481: "new SharpDX.DirectWrite.TextLayout(Core.Globals.DirectWriteFactory, …"
retrieved:   2026-10-29
note:        It is static because it is accessed through the type name. "Read-only" suggests a get-only property; whether it is a field or a property is for Channel B. Scripts must not dispose this shared factory.
```

```
claim_id:    T9
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/sharpdx_directwrite_textlayout.htm ; https://ninjatrader.com/support/helpGuides/nt8/sharpdx_directwrite_textlayout_metrics.htm ; SRC @Text.cs:481-484
source_tier: 1 (HG SharpDX SDK Reference; NT disclaimer: compiled from SharpDX docs) + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "new TextLayout(Factory factory, string text, TextFormat textFormat, float maxWidth, float maxHeight)"  /  Metrics: "Width  A float value that indicates the width of the formatted text, while ignoring trailing whitespace at the end of each line." "Height  A float value that indicates the height of the formatted text."  /  SRC 483: "cachedTextLayout.MaxWidth = cachedTextLayout.Metrics.Width;"
retrieved:   2026-10-29
note:        TextLayout must be disposed (HG DisposeBase list).
```

```
claim_id:    T10
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/dxextensions_todxbrush.htm ; SRC ChartStyles\@CandleStyle.cs:176 ; ChartStyles\@HollowCandleStyle.cs:136
source_tier: 1 + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "DxExtensions.ToDxBrush( this System.Windows.Media.Brush brush, RenderTarget renderTarget)"  "Method Return Value  A new SharpDX.Direct2D1.Brush"  /  SRC 176: "dojiBrushDX = Gui.DxExtensions.ToDxBrush(DojiBrush, RenderTarget);"  HollowCandleStyle 136: "dojiBrushDX = DojiBrush.ToDxBrush(RenderTarget);"
retrieved:   2026-10-29
note:        Lives in NinjaTrader.Gui.DxExtensions. It returns a NEW brush each call, so the caller disposes it. HG warns about performance if called too often in one pass.
```

```
claim_id:    T11
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/sharpdx_direct2d1_rendertarget_fillrectangle.htm ; …_drawrectangle.htm ; …_drawtextlayout.htm ; SRC @Text.cs:201,210,220
source_tier: 1 (HG SharpDX SDK Reference) + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "RenderTarget.FillRectangle(RectangleF rect, Brush brush)"  /  "RenderTarget.DrawRectangle(RectangleF rect, Brush brush, float strokeWidth)"  /  "RenderTarget.DrawTextLayout(Vector2 origin, TextLayout textLayout, Brush defaultForegroundBrush)"
retrieved:   2026-10-29
note:        DrawRectangle: "The stroke is centered on the rectangle's outline." DrawTextLayout: origin = "upper-left corner of the text". Its default options do not clip.
```

```
claim_id:    T12
verdict:     CONFIRMED (scoped: "not guaranteed to be the same thread", which is enough for "needs synchronisation")
source:      https://ninjatrader.com/support/helpGuides/nt8/multi-threading.htm ; https://ninjatrader.com/support/helpGuides/nt8/drawingtools_drawobjects.htm
source_tier: 1
version:     HG NT8 live
quote:       "the NinjaTrader application will usually consist of multiple main UI threads, where various features like Charts or NinjaScript objects run, along with a number of background worker threads where events such as market data updates will be distributed"  and  "Since market data is distributed across the entire application by a randomly assigned UI thread, there is no guarantee that your object will be running on the same event thread that is calling the object."  and  "it is important to protect your resources from concurrent access"
retrieved:   2026-10-29
note:        The docs do not say OnRender and OnMarketData are ALWAYS on different threads. They say nothing guarantees the same thread, which is what makes synchronisation necessary. Corroboration: DrawObjects page: "DrawObjects.ToList() is thread safe … you can still run the risk of the collection being modified while you try to read it".
```

```
claim_id:    T13
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/drawingtools_drawobjects.htm ; https://ninjatrader.com/support/helpGuides/nt8/textfixed.htm ; SRC DrawingTools\@Text.cs:110,126,518,567
source_tier: 1 + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       DrawObjects: "Property Value  A collection of IDrawingTool objects."  "foreach (DrawingTool draw in DrawObjects.ToList())"  /  TextFixed: "DisplayText  A string value representing the text to be drawn" "Font  A Font object representing the font for the text" "TextPosition  Possible values are: …"  /  SRC 518: "public class TextFixed : TextFixedBase" 567: "public TextPosition TextPosition { get; set; }" 126: "public string DisplayText" 110: "public Gui.Tools.SimpleFont Font"
retrieved:   2026-10-29
note:        DisplayText and Font are inherited from Text (TextFixed → TextFixedBase → Text). The HG says "Font object" but the installed type is SimpleFont. Use DrawObjects.ToList() for thread-safe enumeration. HG warns that typecasting behaves differently in compiled DLLs.
```

```
claim_id:    T14
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/drawingtools_drawobjects.htm
source_tier: 1
version:     HG NT8 live
quote:       "A collection holding all of the drawn chart objects on the chart, for all series. The draw objects can be manually drawn or script generated objects."  and  "There is no guarantee a manually drawn object will be added to the DrawObjects collection before an indicator starts processing data."
retrieved:   2026-10-29
note:        "all … on the chart" covers objects from other scripts. The HG example tests draw.IsUserDrawn and draw.IsGlobalDrawingTool, so global and user-drawn objects appear too. Caveat: during load, user-drawn objects may not be present yet.
```

```
claim_id:    T15
verdict:     CONFIRMED
source:      SRC C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\DrawingTools\@Text.cs:520-563 (TextFixed.GetTextDrawingPosition), 453-466 (Text.OnRender), 891 (TextFixedCore)
source_tier: 2
version:     8.1.8.4 installed source
quote:       543 "case TextPosition.BottomRight:"  544 "x = chartPanel.X + chartPanel.W - padding - textWidth;"  545 "y = chartPanel.Y + chartPanel.H - textHeight - padding;"  …  562 "return new Point(x, y);"  /  458 "Point txtPoint = GetTextDrawingPosition(chartControl, chartPanel, chartScale);"  465 "layoutRect = new Rect(x, y, cachedTextLayout.MaxWidth, cachedTextLayout.MaxHeight);"
retrieved:   2026-10-29
note:        The inputs are only TextPosition, chartPanel X/Y/W/H, this object's own Metrics, PaddingMultiplier (panel index and scroll arrow) and YPixelOffset. No sibling objects or other DrawObjects are consulted, so there is no stacking or collision avoidance. Two TextFixed at the same position share the anchor corner: for BottomRight their right and bottom edges line up, and boxes of different sizes overlap. Distinct objects need distinct tags, because Draw.TextFixed with the same tag modifies the same object (891 GetByTagOrNew; HG draw_textfixed: "each time this tag is used, the same draw object is modified"). Z-order: 599 "ZOrderType = DrawingToolZOrder.AlwaysDrawnLast;".
```

```
claim_id:    T16
verdict:     CONFIRMED (offset literal 10.5; box = text metrics + p each side; p is a runtime resource lookup with literal fallback 3f)
source:      SRC DrawingTools\@Text.cs lines 36, 182, 201, 210, 220, 239, 318, 456, 463, 465, 481-484, 532, 544-545, 586 ; SKIN C:\Users\rajib\Documents\NinjaTrader 8\templates\Skins\<all 7>\BluePrint.xaml
source_tier: 2
version:     8.1.8.4 installed source and skins
quote:       532 "const float padding = 10.5f;"  531 "// amount of padding from panel edges"
             544 "x = chartPanel.X + chartPanel.W - padding - textWidth;"  545 "y = chartPanel.Y + chartPanel.H - textHeight - padding;"
             528-529 "float textWidth = cachedTextLayout.Metrics.Width;" "float textHeight = cachedTextLayout.Metrics.Height;"
             586 "protected override Rect GetCurrentRect(Rect layoutRect, double outlinePadding) => new(layoutRect.X - outlinePadding, layoutRect.Y - outlinePadding, layoutRect.Width + outlinePadding * 2, layoutRect.Height + outlinePadding * 2);"
             220 "RenderTarget.DrawTextLayout(new SharpDX.Vector2(outlineRectDx.X + outlinePadding, outlineRectDx.Y + outlinePadding), …"
             239 "private static float GetPadding() => Application.Current.FindResource("FontModalTitleMargin") as float? ?? 3f;"
             SKIN (Dark:694) "<system:Double x:Key="FontModalTitleMargin">5</system:Double>"
retrieved:   2026-10-29
note:        See the "T16 numbers" section. The skin value is a Double. Under C# `as float?`, a boxed Double gives null, so the effective p is deduced to be 3. This is a deduction, not observed. Channel B should confirm p = 3 vs 5 and the 7.5 px box-to-panel-edge gap.
```

```
claim_id:    T17
verdict:     UNVERIFIABLE
source:      SRC DrawingTools\@Text.cs:551-553 ; HG https://ninjatrader.com/support/helpGuides/nt8/working_with_indicators.htm ; https://ninjatrader.com/support/helpGuides/nt8/chart_properties.htm
source_tier: 2 (comment) + 1
version:     8.1.8.4 / HG NT8 live
quote:       SRC 553 "y = chartPanel.Y + padding * 2; // make enough room for labels"  /  HG: "Label  The label displayed on the chart." (no location given)  /  HG chart properties: "Show date range  Enables or disables showing the date range label in to the top left of chart."
retrieved:   2026-10-29
note:        No primary source says where the indicator/instrument labels are drawn; the label drawing is in compiled Gui code, not shipped source. The vendor comment implies labels sit near the top-left. That same code moves TopLeft text down 21 px precisely to make room for them, so "would overlap" is not established and partly cut against. Recommend a split: T17a, location (needs Channel B or a rendered check), and T17b, overlap with a TopLeft TextFixed.
```

```
claim_id:    T18
verdict:     UNVERIFIABLE
source:      https://ninjatrader.com/support/helpGuides/nt8/marketdataeventargs.htm ; https://ninjatrader.com/support/helpGuides/nt8/playback_connection.htm ; SRC MarketAnalyzerColumns\@TimeLastTick.cs:46-48 ; SRC Indicators\@BarTimer.cs:150
source_tier: 1 + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "Time  A DateTime structure representing the time"  /  SRC 48: "CurrentValue = marketDataUpdate.Time.Subtract(reference).TotalSeconds;" (column "TimeLastTick")  /  Playback: "delivers this market data to all NinjaTrader windows as if it was happening in real-time"
retrieved:   2026-10-29
note:        Half (a), Time = the event's timestamp, is supported: the docs say "the time", and the vendor TimeLastTick column uses it as last-tick time. Half (b), that Time is the replayed time in Playback, is not stated anywhere. BarTimer:150 shows that wall-clock vs playback time needs Connection.PlaybackConnection.Now, but that concerns Globals.Now, not MarketDataEventArgs.Time. Recommend a split into (a) and (b), with (b) left to Channel B.
```

```
claim_id:    T19
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/isinhittest.htm ; https://ninjatrader.com/support/helpGuides/nt8/rendertarget.htm ; SRC DrawingTools\@AndrewsPitchfork.cs:481-484, @Arc.cs:157, @Polygon.cs:470, @GannFan.cs:425
source_tier: 1 + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "This property returns true to indicate that the chart panel in which the script resides is being clicked on; otherwise, false . Default set to false ."  /  RenderTarget: "WicRenderTarget  Used to render a bitmap … A user clicks on a chart area; a bitmap is used to do any hit detection"  /  SRC 481-483 "// If we're doing a hit test pass, don't draw price levels at all, we dont want those to count for // hit testing  if (IsInHitTest || PriceLevels == null || !PriceLevels.Any()) return;"
retrieved:   2026-10-29
note:        "Should skip decorative drawing" is the vendor's own pattern, not a documented rule. Vendor tools also sometimes draw with chartControl.SelectionBrush during hit test instead (@Text.cs:200,208,219).
```

```
claim_id:    T20
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/chartcontrol_properties.htm ; SRC DrawingTools\@Text.cs:448
source_tier: 1 + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "ChartBackground  A Brush object used to paint the chart background"  "ChartText  A Brush object used to paint text on the chart"  /  SRC 448: "TextBrush = chartControl.Properties.ChartText;"
retrieved:   2026-10-29
note:        HG warning: "These are UI properties … Attempting to modify these values through a custom script is NOT guaranteed to take effect." Reading them is fine. They are WPF brushes and need ToDxBrush before use in a RenderTarget.
```

```
claim_id:    T21
verdict:     CONFIRMED
source:      https://ninjatrader.com/support/helpGuides/nt8/forcerefresh.htm ; SRC Indicators\@BarTimer.cs:105-107
source_tier: 1 + 2
version:     HG NT8 live; SRC 8.1.8.4
quote:       "Syntax  ForceRefresh()"  "Calling ForceRefesh() simply re-queues the render event to trigger during the next timed event. In other words , it may take up to 250ms for the render event to function."  /  SRC 107: "ForceRefresh();" (inside Indicator BarTimer.OnTimerTick)
retrieved:   2026-10-29
note:        HG: "It is NOT recommended to invalidate the chart control directly as this could cause issues with threading which result in dead locks."
```

## Split recommendations for the orchestrator (no ledger edits made)

- T6: a rendered check that the y-axis and x-axis/scroll bar fall outside the ChartPanel rect at the bottom-right.
- T16: split into T16a (offset 10.5 and box = metrics + 2p: CONFIRMED by source) and T16b (effective p = 3, not the skin's 5: a deduction that needs Channel B).
- T17: split into location vs overlap.
- T18: split into event timestamp vs Playback semantics.
