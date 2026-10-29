# QI_28 table panel — research claims ledger (phase T1, before any implementation)

status: FROZEN 2026-10-29. No claim may be added, dropped or reworded after this line; misses go to
`validation/iceberg/addenda.md` and run through both channels fresh.
purpose: confirm the NinjaTrader rendering facts a bottom-right table box rests on, before code is written.
request: move the iceberg label text into a table inside a rectangle at the lower right of the chart, with
timestamps, newest first, never overlapping earlier boxes or other chart UI.
environment: `validation/env-pin.txt` (NinjaTrader **8.1.8.4**, assemblies in C:\Program Files\NinjaTrader 8\bin;
compiled custom code in C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\NinjaTrader.Custom.dll; .NET Framework 4.8;
Roslyn from .NET SDK 8.0.100).
mode: Mode 1 (dual subagent).
- Channel A = documentation and vendor source only: the NinjaTrader 8 help guide, plus the NinjaScript source files
  NinjaTrader ships in Documents\NinjaTrader 8\bin\Custom\ (e.g. DrawingTools\@Text.cs).
- Channel B = runtime only: reflection on the installed assemblies, compile probes with falsifiers. No help guide and
  no shipped `.cs` source.

Every material claim starts REJECTED.

| ID | Cat | Mat | Claim (one sentence) | Falsifier | Channel B probe (pre-registered) |
|----|-----|-----|----------------------|-----------|----------------------------------|
| T1 | api | M | An Indicator can override `OnRender(ChartControl chartControl, ChartScale chartScale)`. | no such virtual / different signature | reflection on the base types of `Indicator`; compile an override; falsifier: wrong parameter type → CS0115 |
| T2 | api | M | An Indicator can override a parameterless `OnRenderTargetChanged()`. | missing | reflection + compile override; falsifier misspelled → CS0115 |
| T3 | sem | M | SharpDX device resources (brushes) created from `RenderTarget` must be (re)created when the render target changes and disposed by the script. | docs say NT manages them / no such requirement | N/A-by-construction until split (lifetime semantics; docs) |
| T4 | api | M | `ChartPanel` exposes integer `X`, `Y`, `W`, `H` members. | any missing / not numeric | reflection on the `ChartPanel` type (member types) |
| T5 | sem | M | `ChartPanel.X/Y/W/H` are the panel's drawing rectangle in OnRender's RenderTarget coordinates, origin top-left, Y growing downward. | docs define another origin/unit | N/A-by-construction until split (needs a rendered chart) |
| T6 | sem | M | The price (Y) axis, the time (X) axis and the horizontal scroll bar are outside the `ChartPanel` X/Y/W/H rectangle. | docs/source draw them inside | N/A-by-construction until split |
| T7 | api | M | `SimpleFont` has a method `ToDirectWriteTextFormat()` returning `SharpDX.DirectWrite.TextFormat`. | missing / other return type | reflection; compile a call; falsifier: assign to `int` → CS0029 |
| T8 | api | M | `NinjaTrader.Core.Globals.DirectWriteFactory` is a public static `SharpDX.DirectWrite.Factory`. | missing / other type | reflection on `NinjaTrader.Core.Globals` |
| T9 | api | M | `SharpDX.DirectWrite.TextLayout(Factory, string, TextFormat, float, float)` exists and `.Metrics` exposes `Width` and `Height` floats. | ctor or members missing | reflection on the SharpDX.DirectWrite assembly NT ships; compile a probe |
| T10 | api | M | An extension method `ToDxBrush(this System.Windows.Media.Brush, SharpDX.Direct2D1.RenderTarget)` returning a `SharpDX.Direct2D1.Brush` is available to NinjaScript. | missing | reflection for the static extension; compile a call; falsifier: wrong arg type → CS1929/CS1503 |
| T11 | api | M | `RenderTarget` offers `FillRectangle(RectangleF, Brush)`, `DrawRectangle(RectangleF, Brush, float)` and `DrawTextLayout(Vector2, TextLayout, Brush)`. | any missing | reflection on SharpDX.Direct2D1.RenderTarget; compile a probe |
| T12 | sem | M | `OnRender` runs on a different thread from `OnMarketData`, so shared state needs synchronisation. | docs say same thread / serialised | N/A-by-construction until split |
| T13 | api | M | The indicator can enumerate the chart's drawing objects through a `DrawObjects` collection, and each `NinjaTrader.NinjaScript.DrawingTools.TextFixed` exposes `TextPosition`, `DisplayText` and `Font`. | missing collection or members | reflection on NinjaScriptBase / IndicatorRenderBase and on TextFixed in NinjaTrader.Custom.dll |
| T14 | sem | M | `DrawObjects` includes draw objects created by other scripts and by the user on the same chart, not only this script's own. | docs/source say own objects only | N/A-by-construction until split |
| T15 | sem | M | Two `TextFixed` objects at the same `TextPosition` are drawn at the same spot (NinjaTrader does not stack them). | source stacks them | N/A-by-construction until split |
| T16 | sem | M | `TextFixed` places its box a fixed pixel offset from the panel corner and pads the text inside it; the offset and padding can be read from the shipped source. | source computes it otherwise / not readable | N/A-by-construction until split |
| T17 | sem | M | NinjaTrader draws the chart's indicator/instrument labels in the top-left corner of the price panel, where a `TopLeft` TextFixed would overlap them. | docs/source place them elsewhere | N/A-by-construction until split |
| T18 | sem | M | `MarketDataEventArgs.Time` is the event's timestamp (in Playback, the replayed time). | docs define otherwise | N/A-by-construction until split |
| T19 | api | m | `IsInHitTest` is a bool property that is true during hit-test render passes, which should skip decorative drawing. | missing | reflection |
| T20 | api | m | `ChartControl.Properties` exposes `ChartBackground` and `ChartText` brushes for theme-matched colours. | missing | reflection on the ChartControl properties type |
| T21 | api | m | `ForceRefresh()` exists on the indicator to request a repaint. | missing | reflection |

Claim count: 21 (18 material T1–T18, 3 minor T19–T21).
