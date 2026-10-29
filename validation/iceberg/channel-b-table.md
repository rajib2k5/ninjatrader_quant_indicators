# Channel B (runtime auditor): QI_28 table panel claims T1–T21

ledger: `validation/iceberg/table-claims-ledger.md` (FROZEN 2026-10-29). Not edited.
auditor: Channel B, runtime evidence only. I did not consult the help guide, any web docs, any shipped `*.cs` under
`Documents\NinjaTrader 8\bin\Custom\`, or `channel-a-table.md`. NinjaTrader was not run or touched, and nothing was
written under `Documents\NinjaTrader 8`.
date: 2026-10-29

## Environment and toolchain

| item | value |
|---|---|
| NinjaTrader.Core.dll | assembly 8.1.8.4, sha256 `a9caa8c3fc84cd360f2e56e18c06996c1cb87b9ed8ff3de63c33431a89b00e84` |
| NinjaTrader.Gui.dll | assembly 8.1.8.4, sha256 `10b8dadc94e80d8d51a4d472328dcd7bfa9e5d266e28863e49ee259d88786d0a` |
| NinjaTrader.Custom.dll | assembly version reported **8.1.9.0**, file mtime 2026-10-29 10:58, sha256 `3c5df7ea7fa1e3f166bde84ae66b48c9033cdd671743620d727f6d22edead319` |
| SharpDX.dll / SharpDX.Direct2D1.dll | 2.6.3.0 (sha256 `05f4be90…a133e` / `71b21461…ad67eb`); also SharpDX.DXGI.dll, SharpDX.Direct3D10.dll. **No separate SharpDX.DirectWrite.dll: the `SharpDX.DirectWrite.*` types live in SharpDX.Direct2D1.dll** |
| compile probe | `validation/probes/compile_probe.sh` (sha256 `83ebf088…155f9`), Roslyn csc from SDK 8.0.100, `-langversion:latest` (C# 12), x64, refs = NT Core/Gui/Custom + net48 FW + WPF + SharpDX*.dll |
| reflection tool | `Reflect.exe` (net48 x64, built with the same csc), **ReflectionOnly** load context, so no NinjaTrader code (cctors or module initialisers) runs. Lookups are by type name. A naive `GetTypes` sweep is used only by `findtype` and `ext`, both with `ReflectionTypeLoadException` handling. No StackOverflow occurred. Tool sha256: Reflect.cs `38a78901…e6a8`, Reflect.exe `d98f3c68…2370` |

Scratch (all probes, outputs, falsifiers):
`C:\Users\rajib\AppData\Local\Temp\claude\C--Users-rajib-OneDrive-Documents\533a663d-5efe-42d6-aafd-bb6df2ee5fa2\scratchpad\table_chanB\`
(below written as `$SCRATCH\table_chanB\`)
- `Reflect.cs`, `Reflect.exe`, `reflect_tool.sha256`
- `run_reflect1.sh` / `out_reflect1.txt` (discovery), `run_reflect2.sh` / `out_reflect2.txt` (T1–T19), `run_reflect3.sh` / `out_reflect3.txt` (T20, T21 and supporting probes)
- `members_ChartPanel.txt`, `members_TextFixed.txt`, `members_DxExtensions.txt` (full member dumps)
- `cp\*.cs` compile probes (`*_pos` = claim, `*_mut*` = falsifier mutant), with checksums in `cp_sources.sha256`. `out_compile.txt` and `out_compile_using.txt` hold the verbatim csc output.
- `nt_assemblies.sha256`, `compile_probe.sha256`

Reflection tool exit codes: 0 = the condition holds, 1 = it does not, 2 = probe error (PROBE_INVALID).
Compile probes: rc = csc exit code.

Falsifier method: each falsifier is a separate mutant file (`*_mut*.cs`) or a mutated reflection argument. The
original probe file is never edited in place, so it needs no restore step. `cp_sources.sha256` fixes both versions.

PROBE_INVALID incident (recorded for transparency): my first T8 reflection run returned rc=2 with
`FileLoadException: Cannot resolve dependency to assembly 'System.Net.Http, Version=4.2.0.0'`. `Type.GetMember`
populates nested types, and a nested type of `NinjaTrader.Core.Globals` depends on System.Net.Http. I fixed the tool:
a framework-directory resolver fallback, plus property, field, method and event enumeration in place of `GetMember`.
I then re-ran **all** reflection batches with the final tool. The outputs below come from that final run, which has
0 `PROBE ERROR` lines across out_reflect1, 2 and 3.

---

## Verdict summary

| ID | Mat | Channel B verdict | Primary evidence | Falsifier rc |
|----|-----|-------------------|------------------|--------------|
| T1 | M | **CONFIRMED** | `protected virtual void IndicatorRenderBase.OnRender(ChartControl, ChartScale)`; override compiles rc=0 | refl 1; csc 1 (CS0115) |
| T2 | M | **CONFIRMED** | `public virtual void IndicatorRenderBase.OnRenderTargetChanged()`; override compiles rc=0 | refl 1; csc 1 (CS0115) |
| T3 | M | **N/A-by-construction** (pre-registered, until split) | supporting only: SharpDX `Brush`/`SolidColorBrush`/`TextLayout` implement `System.IDisposable` | n/a |
| T4 | M | **CONFIRMED** | `ChartPanel.X/Y/W/H : System.Int32`, public instance getters | refl 1 (Double; `Wd`); csc 1 (CS0029) |
| T5 | M | **N/A-by-construction** (pre-registered) | none decisive | n/a |
| T6 | M | **N/A-by-construction** (pre-registered) | supporting caveat: `ChartPanel.IsYAxisDisplayedOverlay` exists | n/a |
| T7 | M | **CONFIRMED** | `public SharpDX.DirectWrite.TextFormat SimpleFont.ToDirectWriteTextFormat()` | refl 1; csc 1 (CS0029) |
| T8 | M | **CONFIRMED** | `NinjaTrader.Core.Globals.DirectWriteFactory : SharpDX.DirectWrite.Factory`, static, public get, **property** (no setter) | refl 1 (instance; TextFormat); csc 1 (CS0029) |
| T9 | M | **CONFIRMED** | ctor `(Factory, String, TextFormat, Single, Single)` exists; `Metrics : TextMetrics`; `Width`, `Height : System.Single` (**public fields**) | refl 1 ×2; csc 1 (CS1061), 1 (CS1503) |
| T10 | M | **CONFIRMED** | `public static [Extension] SharpDX.Direct2D1.Brush NinjaTrader.Gui.DxExtensions.ToDxBrush(System.Windows.Media.Brush, SharpDX.Direct2D1.RenderTarget)` in **NinjaTrader.Core.dll**, namespace **NinjaTrader.Gui** | refl 1; csc 1 (CS1929), 1 (CS1503), 1 (CS1061 without `using NinjaTrader.Gui`) |
| T11 | M | **CONFIRMED** | all three exact overloads exist on `SharpDX.Direct2D1.RenderTarget`; call probe rc=0 | refl 1; csc 1 (CS1503) |
| T12 | M | **N/A-by-construction** (pre-registered) | supporting only: ChartControl derives from `System.Windows.Threading.DispatcherObject` | n/a |
| T13 | M | **CONFIRMED** | `IndicatorRenderBase.DrawObjects : IDrawObjects` (implements `IEnumerable<IDrawingTool>`, has `Count`); TextFixed `.TextPosition : TextPosition`, `.DisplayText : String`, `.Font : SimpleFont` | refl 1 ×2; csc 1 (CS1061) |
| T14 | M | **N/A-by-construction** (pre-registered) | supporting only: `DrawingTool.DrawnBy`, `IsUserDrawn`, `IsAttachedToNinjaScript`, `IsGlobalDrawingTool` exist | n/a |
| T15 | M | **N/A-by-construction** (pre-registered) | supporting only: `TextPosition` = {BottomLeft, BottomRight, Center, TopLeft, TopRight} | n/a |
| T16 | M | **N/A-by-construction** (pre-registered) | supporting only: `Text.YPixelOffset : Int32` exists; offset/padding values not observable at runtime without a render | n/a |
| T17 | M | **N/A-by-construction** (pre-registered) | none | n/a |
| T18 | M | **N/A-by-construction** (pre-registered) | supporting only: `MarketDataEventArgs.Time : System.DateTime` (public get, internal set); compiles | refl 1; csc 1 (CS0029) |
| T19 | m | **CONFIRMED** (existence/type half only) | `IndicatorRenderBase.IsInHitTest : System.Boolean` (public get/set). The "true during hit-test passes" semantics is not runtime-observable here | refl 1; csc 1 (CS0029) |
| T20 | m | **CONFIRMED** | `ChartControl.Properties : ChartControlProperties`; `.ChartBackground`, `.ChartText : System.Windows.Media.Brush` | refl 1 ×2; csc 1 (CS1061) |
| T21 | m | **CONFIRMED** | `public void IndicatorRenderBase.ForceRefresh()` | refl 1; csc 1 (CS0103) |

Gate note: the protocol (SKILL.md Step 5) says N/A-by-construction is legal only on sub-claims created by a split. T3,
T5, T6, T12, T14–T18 carry the ledger's pre-registered "N/A-by-construction **until split**" marker, so they cannot be
ACCEPTED as they stand. The orchestrator must split them, for example into an API-existence half (runtime-probeable,
partly covered by the supporting evidence below) and a semantic half (Channel A only). T19's verdict covers only its
existence-and-type half, and its semantic half has the same split requirement.

---

## Per-claim records

### T1: Indicator can override `OnRender(ChartControl, ChartScale)`
```
claim_id:      T1
probe_cmd:     ./Reflect.exe method NinjaTrader.NinjaScript.Indicators.Indicator OnRender NinjaTrader.Gui.Chart.ChartControl,NinjaTrader.Gui.Chart.ChartScale System.Void virtual
rc:            0
stdout:        |
  MATCH    protected virtual System.Void NinjaTrader.Gui.NinjaScript.IndicatorRenderBase.OnRender(NinjaTrader.Gui.Chart.ChartControl chartControl, NinjaTrader.Gui.Chart.ChartScale chartScale)  [assembly NinjaTrader.Gui]
  wanted OnRender(NinjaTrader.Gui.Chart.ChartControl,NinjaTrader.Gui.Chart.ChartScale) ret=System.Void virtual=True match=True
falsifier_cmd: ./Reflect.exe method ...Indicator OnRender NinjaTrader.Gui.Chart.ChartControl,System.Int32 System.Void virtual
falsifier_rc:  1   (match=False)
probe_cmd:     OUT=$SCRATCH/table_chanB/cp_out/T1_pos.dll bash validation/probes/compile_probe.sh $SCRATCH/table_chanB/cp/T1_pos.cs
               (protected override void OnRender(NinjaTrader.Gui.Chart.ChartControl chartControl, NinjaTrader.Gui.Chart.ChartScale chartScale) { base.OnRender(chartControl, chartScale); })
rc:            0
falsifier_cmd: same with cp/T1_mut.cs  (second parameter `int chartScale`)
falsifier_rc:  1
falsifier_out: T1_mut.cs(6,27): error CS0115: 'EgvTbl_T1_mut.OnRender(ChartControl, int)': no suitable method found to override
verdict:       CONFIRMED
```
Base chain (supporting): `Indicator [NinjaTrader.Custom] → NinjaTrader.Gui.NinjaScript.IndicatorRenderBase [Gui] →
NinjaTrader.NinjaScript.IndicatorBase [Core] → NinjaScriptBase [Core] → NinjaScript [Core] → System.Object`.
Override access modifier must be **protected**.

### T2: parameterless `OnRenderTargetChanged()` overridable
```
claim_id:      T2
probe_cmd:     ./Reflect.exe method NinjaTrader.NinjaScript.Indicators.Indicator OnRenderTargetChanged "" System.Void virtual
rc:            0
stdout:        |
  MATCH    public virtual System.Void NinjaTrader.Gui.NinjaScript.IndicatorRenderBase.OnRenderTargetChanged()  [assembly NinjaTrader.Gui]
falsifier_cmd: ./Reflect.exe method ...Indicator OnRenderTargetChange "" System.Void virtual
falsifier_rc:  1
probe_cmd:     compile_probe.sh cp/T2_pos.cs   (public override void OnRenderTargetChanged() { base.OnRenderTargetChanged(); })
rc:            0
falsifier_cmd: compile_probe.sh cp/T2_mut.cs   (public override void OnRenderTargetChange() { })
falsifier_rc:  1
falsifier_out: T2_mut.cs(6,24): error CS0115: 'EgvTbl_T2_mut.OnRenderTargetChange()': no suitable method found to override
verdict:       CONFIRMED
```
Override access modifier must be **public** (unlike OnRender).

### T3: SharpDX brushes must be (re)created on render-target change and disposed by the script
```
verdict:       N/A-by-construction (pre-registered "until split"; lifetime semantics)
supporting:    ./Reflect.exe bases SharpDX.Direct2D1.Brush  rc=0
                 BASE SharpDX.Direct2D1.Brush → SharpDX.Direct2D1.Resource → SharpDX.ComObject → SharpDX.CppObject → SharpDX.DisposeBase → System.Object
                 IFACE System.IDisposable / IFACE SharpDX.IUnknown
               ./Reflect.exe bases SharpDX.Direct2D1.SolidColorBrush  rc=0  (same chain, IDisposable)
               ./Reflect.exe bases SharpDX.DirectWrite.TextLayout  rc=0  (TextLayout → TextFormat → ComObject → … DisposeBase; IFACE System.IDisposable)
               NinjaTrader.Gui.DxExtensions also exposes `[Extension] bool IsValid(SharpDX.Direct2D1.Brush brush, SharpDX.Direct2D1.RenderTarget target)`,
               which is consistent with a brush being bound to one render target. Supporting only, not proof of the lifetime rule.
```

### T4: `ChartPanel` exposes integer X, Y, W, H
```
claim_id:      T4
probe_cmd:     ./Reflect.exe member NinjaTrader.Gui.Chart.ChartPanel {X|Y|W|H} System.Int32 instance
rc:            0, 0, 0, 0
stdout:        |
  MEMBER Property NinjaTrader.Gui.Chart.ChartPanel.X : System.Int32  static=False  access=get:public (no setter)  [assembly NinjaTrader.Gui]
  MEMBER Property NinjaTrader.Gui.Chart.ChartPanel.Y : System.Int32  static=False  access=get:public (no setter)  [assembly NinjaTrader.Gui]
  MEMBER Property NinjaTrader.Gui.Chart.ChartPanel.W : System.Int32  static=False  access=get:public set:private  [assembly NinjaTrader.Gui]
  MEMBER Property NinjaTrader.Gui.Chart.ChartPanel.H : System.Int32  static=False  access=get:public set:private  [assembly NinjaTrader.Gui]
falsifier_cmd: ./Reflect.exe member NinjaTrader.Gui.Chart.ChartPanel X System.Double instance   → rc=1 (match=False)
               ./Reflect.exe member NinjaTrader.Gui.Chart.ChartPanel Wd - instance              → rc=1 (found=0)
probe_cmd:     compile_probe.sh cp/T4_pos.cs   (int x = ChartPanel.X, y = ChartPanel.Y, w = ChartPanel.W, h = ChartPanel.H; inside OnRender)
rc:            0
falsifier_cmd: compile_probe.sh cp/T4_mut.cs   (string w = ChartPanel.W;)
falsifier_rc:  1
falsifier_out: T4_mut.cs(6,183): error CS0029: Cannot implicitly convert type 'int' to 'string'
verdict:       CONFIRMED
```
Supporting: on the indicator, `IndicatorRenderBase.ChartPanel : NinjaTrader.Gui.Chart.ChartPanel` (public get/set).

### T5: X/Y/W/H are the panel rectangle in RenderTarget coordinates, top-left origin, Y down
```
verdict:       N/A-by-construction (pre-registered; needs a rendered chart). No runtime evidence gathered.
```

### T6: price axis, time axis and scroll bar are outside the X/Y/W/H rectangle
```
verdict:       N/A-by-construction (pre-registered).
supporting (caveat, not evidence for or against): ChartPanel declares
               bool IsYAxisDisplayedLeft { get; }, bool IsYAxisDisplayedRight { get; }, bool IsYAxisDisplayedOverlay { get; }
               (members_ChartPanel.txt). An "overlay" Y-axis mode exists, and in that mode the axis may be drawn inside the
               panel. Channel A / the split should cover it.
```

### T7: `SimpleFont.ToDirectWriteTextFormat()` returns `SharpDX.DirectWrite.TextFormat`
```
claim_id:      T7
probe_cmd:     ./Reflect.exe method NinjaTrader.Gui.Tools.SimpleFont ToDirectWriteTextFormat "" SharpDX.DirectWrite.TextFormat
rc:            0
stdout:        MATCH    public SharpDX.DirectWrite.TextFormat NinjaTrader.Gui.Tools.SimpleFont.ToDirectWriteTextFormat()  [assembly NinjaTrader.Gui]
falsifier_cmd: ./Reflect.exe method NinjaTrader.Gui.Tools.SimpleFont ToDirectWriteTextFormat "" System.Int32   → rc=1
probe_cmd:     compile_probe.sh cp/T7_pos.cs   (SharpDX.DirectWrite.TextFormat tf = font.ToDirectWriteTextFormat();)
rc:            0
falsifier_cmd: compile_probe.sh cp/T7_mut.cs   (int tf = font.ToDirectWriteTextFormat();)
falsifier_rc:  1
falsifier_out: T7_mut.cs(6,60): error CS0029: Cannot implicitly convert type 'SharpDX.DirectWrite.TextFormat' to 'int'
verdict:       CONFIRMED
```
SimpleFont lives in `NinjaTrader.Gui.Tools` (NinjaTrader.Gui.dll). The returned TextFormat is IDisposable (see T3).

### T8: `NinjaTrader.Core.Globals.DirectWriteFactory` is a public static `SharpDX.DirectWrite.Factory`
```
claim_id:      T8
probe_cmd:     ./Reflect.exe member NinjaTrader.Core.Globals DirectWriteFactory SharpDX.DirectWrite.Factory static
rc:            0
stdout:        MEMBER Property NinjaTrader.Core.Globals.DirectWriteFactory : SharpDX.DirectWrite.Factory  static=True  access=get:public (no setter)  [assembly NinjaTrader.Core]
falsifier_cmd: ./Reflect.exe member NinjaTrader.Core.Globals DirectWriteFactory SharpDX.DirectWrite.Factory instance     → rc=1
               ./Reflect.exe member NinjaTrader.Core.Globals DirectWriteFactory SharpDX.DirectWrite.TextFormat static    → rc=1
probe_cmd:     compile_probe.sh cp/T8_pos.cs   (SharpDX.DirectWrite.Factory f = NinjaTrader.Core.Globals.DirectWriteFactory;)
rc:            0
falsifier_cmd: compile_probe.sh cp/T8_mut.cs   (SharpDX.DirectWrite.TextFormat f = NinjaTrader.Core.Globals.DirectWriteFactory;)
falsifier_rc:  1
falsifier_out: T8_mut.cs(6,49): error CS0029: Cannot implicitly convert type 'SharpDX.DirectWrite.Factory' to 'SharpDX.DirectWrite.TextFormat'
verdict:       CONFIRMED  (it is a static read-only *property*, not a field; source-compatible with the claim)
```
Note: there is also a non-public `NinjaTrader.Gui.Globals` class. Write `NinjaTrader.Core.Globals` in full.

### T9: `TextLayout(Factory, string, TextFormat, float, float)` and `.Metrics.Width/.Height` floats
```
claim_id:      T9
probe_cmd:     ./Reflect.exe ctor SharpDX.DirectWrite.TextLayout SharpDX.DirectWrite.Factory,System.String,SharpDX.DirectWrite.TextFormat,System.Single,System.Single
rc:            0
stdout:        |
  MATCH    public SharpDX.DirectWrite.TextLayout..ctor(SharpDX.DirectWrite.Factory factory, System.String text, SharpDX.DirectWrite.TextFormat textFormat, System.Single maxWidth, System.Single maxHeight)  [assembly SharpDX.Direct2D1]
  (other ctors: (+ Single pixelsPerDip, Boolean useGdiNatural); (+ Single pixelsPerDip, Nullable<SharpDX.Matrix> transform, Boolean useGdiNatural); (IntPtr))
probe_cmd:     ./Reflect.exe member SharpDX.DirectWrite.TextLayout Metrics SharpDX.DirectWrite.TextMetrics instance   → rc=0
               MEMBER Property SharpDX.DirectWrite.TextLayout.Metrics : SharpDX.DirectWrite.TextMetrics  static=False  access=get:public (no setter)
probe_cmd:     ./Reflect.exe member SharpDX.DirectWrite.TextMetrics {Width|Height} System.Single instance               → rc=0, 0
               MEMBER Field SharpDX.DirectWrite.TextMetrics.Width : System.Single  static=False  access=public
               MEMBER Field SharpDX.DirectWrite.TextMetrics.Height : System.Single  static=False  access=public
falsifier_cmd: ./Reflect.exe ctor SharpDX.DirectWrite.TextLayout ...,System.Double,System.Double   → rc=1
               ./Reflect.exe member SharpDX.DirectWrite.TextMetrics Width System.Double instance  → rc=1
probe_cmd:     compile_probe.sh cp/T9_pos.cs
               (using (var tl = new SharpDX.DirectWrite.TextLayout(NinjaTrader.Core.Globals.DirectWriteFactory, "x", tf, 100f, 50f)) { float w = tl.Metrics.Width; float h = tl.Metrics.Height; })
rc:            0
falsifier_cmd: compile_probe.sh cp/T9_mut.cs   (tl.Metrics.Widht)
falsifier_rc:  1
falsifier_out: T9_mut.cs(6,187): error CS1061: 'TextMetrics' does not contain a definition for 'Widht' ...
falsifier_cmd: compile_probe.sh cp/T9_mut2.cs  (100.0, 50.0 double literals)
falsifier_rc:  1
falsifier_out: T9_mut2.cs(6,152): error CS1503: Argument 4: cannot convert from 'double' to 'float'
               T9_mut2.cs(6,159): error CS1503: Argument 5: cannot convert from 'double' to 'float'
verdict:       CONFIRMED
```
`TextMetrics` is a struct, and Width and Height are public **fields**. The TextLayout type is in SharpDX.Direct2D1.dll
2.6.3.0. TextLayout derives from TextFormat and is IDisposable.

### T10: extension `ToDxBrush(this System.Windows.Media.Brush, RenderTarget)` returning `SharpDX.Direct2D1.Brush`
```
claim_id:      T10
probe_cmd:     ./Reflect.exe ext ToDxBrush
rc:            0
stdout:        |
  HIT public static [Extension] SharpDX.Direct2D1.Brush NinjaTrader.Gui.DxExtensions.ToDxBrush(System.Windows.Media.Brush brush, SharpDX.Direct2D1.RenderTarget renderTarget)  [assembly NinjaTrader.Core]  typePublic=True namespace=NinjaTrader.Gui
  HIT public static [Extension] SharpDX.Direct2D1.Brush NinjaTrader.Gui.DxExtensions.ToDxBrush(System.Windows.Media.Brush brush, SharpDX.Direct2D1.RenderTarget renderTarget, System.Single opacity)  [assembly NinjaTrader.Core]  typePublic=True namespace=NinjaTrader.Gui
  hits=2
probe_cmd:     ./Reflect.exe method NinjaTrader.Gui.DxExtensions ToDxBrush System.Windows.Media.Brush,SharpDX.Direct2D1.RenderTarget SharpDX.Direct2D1.Brush  → rc=0 (MATCH)
falsifier_cmd: ./Reflect.exe method NinjaTrader.Gui.DxExtensions ToDxBrush System.Windows.Media.Color,SharpDX.Direct2D1.RenderTarget SharpDX.Direct2D1.Brush → rc=1
probe_cmd:     compile_probe.sh cp/T10_pos.cs  (using NinjaTrader.Gui; ... SharpDX.Direct2D1.Brush b = System.Windows.Media.Brushes.Red.ToDxBrush(RenderTarget); b.Dispose();)
rc:            0
falsifier_cmd: compile_probe.sh cp/T10_mut.cs  (System.Windows.Media.Colors.Red.ToDxBrush(RenderTarget))
falsifier_rc:  1
falsifier_out: T10_mut.cs(6,160): error CS1929: 'Color' does not contain a definition for 'ToDxBrush' and the best extension method overload 'DxExtensions.ToDxBrush(Brush, RenderTarget)' requires a receiver of type 'System.Windows.Media.Brush'
falsifier_cmd: compile_probe.sh cp/T10_mut2.cs (Brushes.Red.ToDxBrush("rt"))
falsifier_rc:  1
falsifier_out: T10_mut2.cs(6,203): error CS1503: Argument 2: cannot convert from 'string' to 'SharpDX.Direct2D1.RenderTarget'
falsifier_cmd: compile_probe.sh cp/T10_mut3_nousing.cs (identical to pos but WITHOUT `using NinjaTrader.Gui;`)
falsifier_rc:  1
falsifier_out: T10_mut3_nousing.cs(6,193): error CS1061: 'SolidColorBrush' does not contain a definition for 'ToDxBrush' and no accessible extension method 'ToDxBrush' accepting a first argument of type 'SolidColorBrush' could be found (are you missing a using directive or an assembly reference?)
verdict:       CONFIRMED
```
Requested for the record: **ToDxBrush is in assembly NinjaTrader.Core.dll, class `NinjaTrader.Gui.DxExtensions`,
namespace `NinjaTrader.Gui`.** The probe file sits in namespace `NinjaTrader.NinjaScript.Indicators`, and from there
`using NinjaTrader.Gui;` is required (mut3 shows CS1061 without it). Every DxExtensions member: `IsValid(this Brush,
RenderTarget)`, `ToDxBrush` ×2 (with and without `float opacity`),
`ToDxGradientStopCollection(this System.Windows.Media.GradientStopCollection, RenderTarget)`,
`ToVector2(this System.Windows.Point)`, `TransformBrush(SharpDX.Direct2D1.Brush, SharpDX.RectangleF)`
(`members_DxExtensions.txt`).

### T11: `RenderTarget.FillRectangle(RectangleF, Brush)`, `DrawRectangle(RectangleF, Brush, float)`, `DrawTextLayout(Vector2, TextLayout, Brush)`
```
claim_id:      T11
probe_cmd:     ./Reflect.exe method SharpDX.Direct2D1.RenderTarget FillRectangle SharpDX.RectangleF,SharpDX.Direct2D1.Brush System.Void  → rc=0
               MATCH    public System.Void SharpDX.Direct2D1.RenderTarget.FillRectangle(SharpDX.RectangleF rect, SharpDX.Direct2D1.Brush brush)  [assembly SharpDX.Direct2D1]
probe_cmd:     ./Reflect.exe method SharpDX.Direct2D1.RenderTarget DrawRectangle SharpDX.RectangleF,SharpDX.Direct2D1.Brush,System.Single System.Void  → rc=0
               MATCH    public System.Void SharpDX.Direct2D1.RenderTarget.DrawRectangle(SharpDX.RectangleF rect, SharpDX.Direct2D1.Brush brush, System.Single strokeWidth)
               (other overloads: (RectangleF, Brush); (RectangleF, Brush, Single, StrokeStyle))
probe_cmd:     ./Reflect.exe method SharpDX.Direct2D1.RenderTarget DrawTextLayout SharpDX.Vector2,SharpDX.DirectWrite.TextLayout,SharpDX.Direct2D1.Brush System.Void  → rc=0
               MATCH    public System.Void SharpDX.Direct2D1.RenderTarget.DrawTextLayout(SharpDX.Vector2 origin, SharpDX.DirectWrite.TextLayout textLayout, SharpDX.Direct2D1.Brush defaultForegroundBrush)
               (other overload: (+ SharpDX.Direct2D1.DrawTextOptions options))
falsifier_cmd: ./Reflect.exe method SharpDX.Direct2D1.RenderTarget DrawTextLayout SharpDX.Vector2,System.String,SharpDX.Direct2D1.Brush System.Void  → rc=1
probe_cmd:     compile_probe.sh cp/T11_pos.cs  (ToDxBrush brush + TextLayout from ChartControl.Properties.LabelFont.ToDirectWriteTextFormat();
               RenderTarget.FillRectangle(rect, b); RenderTarget.DrawRectangle(rect, b, 1f); RenderTarget.DrawTextLayout(new SharpDX.Vector2(0f, 0f), tl, b);)
rc:            0
falsifier_cmd: compile_probe.sh cp/T11_mut.cs  (DrawTextLayout(new SharpDX.Vector2(0f, 0f), "text", b))
falsifier_rc:  1
falsifier_out: T11_mut.cs(14,62): error CS1503: Argument 2: cannot convert from 'string' to 'SharpDX.DirectWrite.TextLayout'
verdict:       CONFIRMED
```
Supporting: `IndicatorRenderBase.RenderTarget : SharpDX.Direct2D1.RenderTarget` (public get/set). `SharpDX.RectangleF`
and `SharpDX.Vector2` are structs in SharpDX.dll 2.6.3.0. The T11 probe also shows that `ChartControl.Properties.LabelFont`
has a `ToDirectWriteTextFormat()` call path. That is an incidental compile fact, not a ledger claim.

### T12: OnRender and OnMarketData run on different threads
```
verdict:       N/A-by-construction (pre-registered).
supporting:    ./Reflect.exe bases NinjaTrader.Gui.Chart.ChartControl → … System.Windows.DependencyObject → System.Windows.Threading.DispatcherObject (WPF, dispatcher-thread-affine)
               ./Reflect.exe method ...Indicator OnMarketData NinjaTrader.Data.MarketDataEventArgs System.Void virtual → rc=0
                 MATCH protected virtual System.Void NinjaTrader.NinjaScript.NinjaScriptBase.OnMarketData(NinjaTrader.Data.MarketDataEventArgs marketDataUpdate) [assembly NinjaTrader.Core]
               This suggests rendering is tied to the UI dispatcher, but it does not show which thread OnMarketData uses. Not evidence.
```

### T13: `DrawObjects` enumerable; TextFixed exposes TextPosition, DisplayText, Font
```
claim_id:      T13
probe_cmd:     ./Reflect.exe member NinjaTrader.NinjaScript.Indicators.Indicator DrawObjects - any → rc=0
               MEMBER Property NinjaTrader.Gui.NinjaScript.IndicatorRenderBase.DrawObjects : NinjaTrader.Gui.NinjaScript.IDrawObjects  static=False  access=get:public (no setter)  [assembly NinjaTrader.Gui]
probe_cmd:     ./Reflect.exe bases NinjaTrader.Gui.NinjaScript.IDrawObjects → rc=0
               IFACE System.Collections.IEnumerable
               IFACE System.Collections.Generic.IEnumerable`1[[NinjaTrader.NinjaScript.DrawingTools.IDrawingTool, NinjaTrader.Gui, ...]]
               ./Reflect.exe members NinjaTrader.Gui.NinjaScript.IDrawObjects → Count : Int32 { get; }, Item : IDrawingTool { get; } (indexer), List<IDrawingTool> ToList()
probe_cmd:     ./Reflect.exe member NinjaTrader.NinjaScript.DrawingTools.TextFixed TextPosition - instance → rc=0
               MEMBER Property NinjaTrader.NinjaScript.DrawingTools.TextFixed.TextPosition : NinjaTrader.NinjaScript.DrawingTools.TextPosition  access=get:public set:public  [assembly NinjaTrader.Custom]
               ./Reflect.exe member ...TextFixed DisplayText System.String instance → rc=0
               MEMBER Property NinjaTrader.NinjaScript.DrawingTools.Text.DisplayText : System.String  access=get:public set:public  [assembly NinjaTrader.Custom]
               ./Reflect.exe member ...TextFixed Font NinjaTrader.Gui.Tools.SimpleFont instance → rc=0
               MEMBER Property NinjaTrader.NinjaScript.DrawingTools.Text.Font : NinjaTrader.Gui.Tools.SimpleFont  access=get:public set:public  [assembly NinjaTrader.Custom]
falsifier_cmd: ./Reflect.exe member ...TextFixed DisplayTxt - instance             → rc=1 (found=0)
               ./Reflect.exe member ...TextFixed Font System.String instance       → rc=1
probe_cmd:     compile_probe.sh cp/T13_pos.cs
               (foreach (NinjaTrader.NinjaScript.DrawingTools.IDrawingTool d in DrawObjects) { var t = d as ...TextFixed; ... TextPosition p = t.TextPosition; string s = t.DisplayText; SimpleFont f = t.Font; } int n = DrawObjects.Count;)
rc:            0
falsifier_cmd: compile_probe.sh cp/T13_mut.cs  (t.DisplayTxt)
falsifier_rc:  1
falsifier_out: T13_mut.cs(13,18): error CS1061: 'TextFixed' does not contain a definition for 'DisplayTxt' ...
verdict:       CONFIRMED
```
DrawObjects is declared on `IndicatorRenderBase` (NinjaTrader.Gui.dll), not on NinjaScriptBase. TextFixed's base
chain is `TextFixed → TextFixedBase → Text [all NinjaTrader.Custom] → DrawingTool → ChartObject [Gui] →
NinjaScript [Core]`, and it implements `IDrawingTool` and `IDisposable`.

### T14: DrawObjects includes other scripts' and user-drawn objects
```
verdict:       N/A-by-construction (pre-registered).
supporting:    DrawingTool (base of TextFixed) declares NinjaScriptBase DrawnBy { get; set; }, bool IsUserDrawn { get; },
               bool IsAttachedToNinjaScript { get; }, bool IsGlobalDrawingTool { get; } (members_TextFixed.txt).
               These let a consumer tell origins apart, which hints that mixed origins exist. Not evidence about DrawObjects contents.
```

### T15: two TextFixed at the same TextPosition are drawn at the same spot
```
verdict:       N/A-by-construction (pre-registered).
supporting:    ./Reflect.exe members NinjaTrader.NinjaScript.DrawingTools.TextPosition → enum {BottomLeft, BottomRight, Center, TopLeft, TopRight} [NinjaTrader.Custom]
```

### T16: TextFixed fixed pixel offset and padding readable from shipped source
```
verdict:       N/A-by-construction (pre-registered; a source-reading claim, Channel A's domain).
supporting:    Text declares int YPixelOffset { get; set; }, Stroke OutlineStroke, Brush AreaBrush, int AreaOpacity,
               System.Windows.TextAlignment Alignment (members_TextFixed.txt). No offset or padding values are runtime-observable
               without a render, and I did not decompile IL, because that would amount to reading the shipped source.
```

### T17: chart indicator/instrument labels drawn top-left of price panel
```
verdict:       N/A-by-construction (pre-registered). No runtime evidence.
```

### T18: `MarketDataEventArgs.Time` is the event timestamp (replayed time in Playback)
```
verdict:       N/A-by-construction (pre-registered; semantic).
supporting:    ./Reflect.exe member NinjaTrader.Data.MarketDataEventArgs Time System.DateTime instance → rc=0
                 MEMBER Property NinjaTrader.Data.MarketDataEventArgs.Time : System.DateTime  static=False  access=get:public set:internal  [assembly NinjaTrader.Core]
               falsifier ./Reflect.exe member ... Tim System.DateTime instance → rc=1
               compile_probe.sh cp/T18_pos.cs (protected override void OnMarketData(MarketDataEventArgs e) { System.DateTime t = e.Time; }) → rc=0
               compile_probe.sh cp/T18_mut.cs (int t = e.Time;) → rc=1: T18_mut.cs(6,90): error CS0029: Cannot implicitly convert type 'System.DateTime' to 'int'
               These records confirm the existence and type half only. They do not establish the "replayed time" semantics.
```

### T19: `IsInHitTest` bool property
```
claim_id:      T19
probe_cmd:     ./Reflect.exe member NinjaTrader.NinjaScript.Indicators.Indicator IsInHitTest System.Boolean any → rc=0
               MEMBER Property NinjaTrader.Gui.NinjaScript.IndicatorRenderBase.IsInHitTest : System.Boolean  static=False  access=get:public set:public  [assembly NinjaTrader.Gui]
falsifier_cmd: ./Reflect.exe member ...Indicator IsInHitTest System.Int32 any → rc=1
probe_cmd:     compile_probe.sh cp/T19_pos.cs  (bool b = IsInHitTest; if (b) return;)  → rc=0
falsifier_cmd: compile_probe.sh cp/T19_mut.cs  (int b = IsInHitTest;)
falsifier_rc:  1
falsifier_out: T19_mut.cs(6,140): error CS0029: Cannot implicitly convert type 'bool' to 'int'
verdict:       CONFIRMED for existence and type. The "true during hit-test passes, so skip decorative drawing" semantics is not
               runtime-observable here, so that half needs Channel A or a split.
```
(Also present on ChartObject, so drawing tools have it as well.)

### T20: `ChartControl.Properties` exposes ChartBackground and ChartText brushes
```
claim_id:      T20
probe_cmd:     ./Reflect.exe member NinjaTrader.Gui.Chart.ChartControl Properties - instance → rc=0
               MEMBER Property NinjaTrader.Gui.Chart.ChartControl.Properties : NinjaTrader.Gui.Chart.ChartControlProperties  access=get:public set:public  [assembly NinjaTrader.Gui]
probe_cmd:     ./Reflect.exe member NinjaTrader.Gui.Chart.ChartControlProperties ChartBackground System.Windows.Media.Brush instance → rc=0
               MEMBER Property NinjaTrader.Gui.Chart.ChartControlProperties.ChartBackground : System.Windows.Media.Brush  access=get:public set:public
               ./Reflect.exe member NinjaTrader.Gui.Chart.ChartControlProperties ChartText System.Windows.Media.Brush instance → rc=0
               MEMBER Property NinjaTrader.Gui.Chart.ChartControlProperties.ChartText : System.Windows.Media.Brush  access=get:public set:public
falsifier_cmd: ./Reflect.exe member ...ChartControlProperties ChartBackgroundX - instance → rc=1 (found=0)
               ./Reflect.exe member ...ChartControlProperties ChartText System.String instance → rc=1
probe_cmd:     compile_probe.sh cp/T20_pos.cs  (System.Windows.Media.Brush bg = chartControl.Properties.ChartBackground; ... fg = chartControl.Properties.ChartText;) → rc=0
falsifier_cmd: compile_probe.sh cp/T20_mut.cs  (chartControl.Properties.ChartBackgroundX)
falsifier_rc:  1
falsifier_out: T20_mut.cs(6,188): error CS1061: 'ChartControlProperties' does not contain a definition for 'ChartBackgroundX' ...
verdict:       CONFIRMED
```

### T21: `ForceRefresh()` exists on the indicator
```
claim_id:      T21
probe_cmd:     ./Reflect.exe method NinjaTrader.NinjaScript.Indicators.Indicator ForceRefresh "" - → rc=0
               MATCH    public System.Void NinjaTrader.Gui.NinjaScript.IndicatorRenderBase.ForceRefresh()  [assembly NinjaTrader.Gui]
falsifier_cmd: ./Reflect.exe method ...Indicator ForceRefreshX "" - → rc=1
probe_cmd:     compile_probe.sh cp/T21_pos.cs  (ForceRefresh();) → rc=0
falsifier_cmd: compile_probe.sh cp/T21_mut.cs  (ForceRefreshX();)
falsifier_rc:  1
falsifier_out: T21_mut.cs(6,14): error CS0103: The name 'ForceRefreshX' does not exist in the current context
verdict:       CONFIRMED (existence; "requests a repaint" is the name-implied semantics, not runtime-observed)
```

---

## Supporting record: `using` resolution and ambiguities (compile probes)

Header under test: the standard NinjaScript `using` block, taken from lines 36–56 of `indicators/QI_28_IcebergDetector.cs`.
It includes `System.Windows`, `System.Windows.Media`, `NinjaTrader.Gui`, `NinjaTrader.Gui.Chart`, `NinjaTrader.Gui.Tools`,
`NinjaTrader.NinjaScript.DrawingTools` and others. Verbatim output is in `out_compile_using.txt`.

| probe | extra usings | rc | key diagnostics |
|---|---|---|---|
| U2_stdonly | none | 1 | CS0246 'RectangleF', 'Vector2', 'TextFormat' and 'TextLayout' could not be found. The standard header does not import SharpDX. |
| U1_allns | `using SharpDX; using SharpDX.Direct2D1; using SharpDX.DirectWrite;` | 1 | `CS0104: 'Brush' is an ambiguous reference between 'SharpDX.Direct2D1.Brush' and 'System.Windows.Media.Brush'`; `CS0104: 'Factory' is an ambiguous reference between 'SharpDX.Direct2D1.Factory' and 'SharpDX.DirectWrite.Factory'`. RectangleF, Vector2, TextFormat and TextLayout resolved without errors. |
| U3_sharpdx_dw | `using SharpDX; using SharpDX.DirectWrite;` + common WPF names | 1 | CS0104 on `Color` (System.Windows.Media vs SharpDX), `Point` (SharpDX vs System.Windows), `TextAlignment` (SharpDX.DirectWrite vs System.Windows), `FontWeight` (SharpDX.DirectWrite vs System.Windows) |
| **U4_alias** | aliases (below) + common WPF names (Brush, Brushes, Color, Colors, Point, TextAlignment, FontWeight, Rect) + full draw sequence | **0** | only warning CS0219 (unused local) |
| U4_alias_mut (falsifier) | same minus the `RectangleF` alias | 1 | CS0246 'RectangleF' could not be found |

Recommended (U4, rc=0):
```csharp
// standard NinjaScript header (keeps System.Windows.Media.Brush as "Brush"; NinjaTrader.Gui brings ToDxBrush)
using DxBrush    = SharpDX.Direct2D1.Brush;
using RectangleF = SharpDX.RectangleF;
using Vector2    = SharpDX.Vector2;
using TextFormat = SharpDX.DirectWrite.TextFormat;
using TextLayout = SharpDX.DirectWrite.TextLayout;
```

## Supporting record: full public member lists

### `NinjaTrader.Gui.Chart.ChartPanel` (NinjaTrader.Gui.dll 8.1.8.4; base `System.Windows.Controls.ContentControl`)
Members declared on ChartPanel (`members_ChartPanel.txt`). The dump also lists 387 inherited properties, fields and events (declared-in System.*) and 81 inherited methods from WPF
`ContentControl`/`Control`/`FrameworkElement`/`UIElement`/…, plus 27 obfuscator-generated `static string` fields such
as `c0Q=`. Both are omitted here.
```
ctor     ChartPanel(NinjaTrader.Gui.Chart.ChartControl chartControl)
property NinjaTrader.Gui.Chart.ChartControl ChartControl { get; }
property IList<NinjaTrader.Gui.NinjaScript.IChartObject> ChartObjects { get; }
property double DelayedButtonHeight { get; }
property double DelayedButtonWidth { get; }
property int    H { get; }
property bool   IsDelayedButtonVisible { get; }
property bool   IsMaximized { get; set; }
property bool   IsWaitingForBars { get; set; }
property bool   IsYAxisDisplayedLeft { get; }
property bool   IsYAxisDisplayedOverlay { get; }
property bool   IsYAxisDisplayedRight { get; }
property double MaxValue { get; set; }
property double MinValue { get; set; }
property int    PanelIndex { get; set; }
property NinjaTrader.Gui.Chart.ChartScaleCollection Scales { get; }
property int    W { get; }
property int    X { get; }
property int    Y { get; }
method   double GetYWpfSnapped(double checkX, double initialY, ChartScale chartScale, DrawingTool dt, bool ignoreSnapBarPrice)
method   double GetYWpfSnappedToBarPrice(double checkX, double initialY)
method   bool   SnapToBar(ChartAnchor dataPoint, DrawingToolAttachedTo _)
method   bool   SnapToPrice(ChartAnchor dataPoint, ChartScale _, DrawingTool dt)
method   override string ToString()
```

### `NinjaTrader.NinjaScript.DrawingTools.TextFixed` (NinjaTrader.Custom.dll; base TextFixedBase → Text → DrawingTool → ChartObject → NinjaScript)
The full list is in `members_TextFixed.txt`, which contains every public property, field and method, including inherited
ones. These are the public properties, with the declaring type in brackets:
```
TextAlignment Alignment [Text]; ChartAnchor Anchor [Text]; IEnumerable<ChartAnchor> Anchors [Text]; AnchorsSafe [DrawingTool];
Brush AreaBrush [Text]; string AreaBrushSerialize [Text]; int AreaOpacity [Text]; DrawingToolAttachedTo AttachedTo [DrawingTool];
ChartPanel ChartPanel [ChartObject]; string Description, DisplayName [NinjaScript]; bool DisplayOnChartsMenus [DrawingTool];
string DisplayText [Text]; DrawingState DrawingState [DrawingTool]; NinjaScriptBase DrawnBy [DrawingTool]; string EditGuid [NinjaScript];
SimpleFont Font [Text]; long GlobalLastSeenSerialize, string GlobalWorkspace [DrawingTool]; object Icon [Text]; string Id [DrawingTool];
bool IgnoresSnapping, IgnoresUserInput [DrawingTool]; ChartAnchor InitialMouseDownAnchor [DrawingTool];
bool IsAttachedToNinjaScript, IsAttachedToVisible [DrawingTool]; bool IsAutoScale [ChartObject]; bool IsGlobalDrawingTool [DrawingTool];
bool IsInHitTest [ChartObject]; bool IsLocked [DrawingTool]; bool IsOwnerVisible, IsSelected, IsSeparateZOrder [ChartObject];
static bool IsStopWatchEnabled [NinjaScript]; bool IsUserDrawn [DrawingTool]; bool IsVisible [NinjaScript]; Brush LastBrush [Text];
string LogTypeName [ChartObject]; bool ManuallyDrawn [Text]; double MaxValue, MinValue [ChartObject]; string Name [NinjaScript];
Stroke OutlineStroke [Text]; int PanelIndex [DrawingTool]; PrintTo PrintTo [NinjaScript]; RenderTarget RenderTarget (get) [ChartObject];
ScaleJustification ScaleJustification [DrawingTool]; State State [NinjaScript]; static StopwatchTimes [NinjaScript];
bool SupportsAlerts [DrawingTool]; string Tag [DrawingTool]; string Template [DrawingTool]; Brush TextBrush [Text];
string TextBrushSerialize [Text]; TextPosition TextPosition [TextFixed]; static int UnitializedZOrder [ChartObject];
bool UseChartTextBrush, UseChartTextBrushSerialize [Text]; int YPixelOffset [Text]; int ZOrder [ChartObject];
DrawingToolZOrder ZOrderType [DrawingTool]
```
Notable methods: `virtual void OnRender(ChartControl, ChartScale)` [Text], `virtual void OnRenderTargetChanged()`
[ChartObject], `sealed void Render(RenderTarget, ChartControl, ChartScale)` [ChartObject],
`virtual bool IsVisibleOnChart(ChartControl, ChartScale, DateTime, DateTime)` [TextFixedBase],
`virtual void OnCalculateMinMax()` [TextFixedBase], `void ForceRefresh()` [DrawingTool], `sealed void Dispose()` [DrawingTool].

### ToDxBrush location
Assembly **NinjaTrader.Core.dll** (8.1.8.4), type **`NinjaTrader.Gui.DxExtensions`**, namespace **`NinjaTrader.Gui`**.
