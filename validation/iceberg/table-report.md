# Phase T1 verdict — table-panel research claims (T1–T21)

mode: Mode 1 (dual subagent). Evidence:
- channel-a-table.md: NT8 help guide, plus the vendor NinjaScript source shipped with 8.1.8.4 (`@Text.cs` and others);
- channel-b-table.md: reflection-only loads of the installed assemblies, plus compile probes with falsifiers.

Neither channel saw the other's file.

| ID | Claim (short) | A | B | Gate |
|----|---------------|---|---|------|
| T1 | `OnRender(ChartControl, ChartScale)` override | CONFIRMED | CONFIRMED (protected; CS0115 falsifier) | **ACCEPTED** |
| T2 | `OnRenderTargetChanged()` override | CONFIRMED (public) | CONFIRMED (public; CS0115) | **ACCEPTED** |
| T3 | device brushes are recreated on target change and disposed by the script | CONFIRMED | N/A | split: T3a "the types are IDisposable" (B supporting, reflection) + T3b "lifetime rule" (A) → **ACCEPTED** |
| T4 | ChartPanel X/Y/W/H are ints | CONFIRMED | CONFIRMED | **ACCEPTED** |
| T5 | panel rect = RenderTarget coords, top-left, Y down | CONFIRMED (docs; device pixels) | N/A | split: T5a semantics (A) accepted; T5b rendered check → **UNRESOLVED → P7** |
| T6 | axes and scroll bar are outside the panel rect | CONFIRMED by inference | N/A; caveat: `IsYAxisDisplayedOverlay` exists | split: T6a default layout (A) accepted; T6b overlay Y-axis mode → **UNRESOLVED → allowance + P7** |
| T7–T11 | ToDirectWriteTextFormat, DirectWriteFactory, TextLayout.Metrics, ToDxBrush, RenderTarget draw calls | CONFIRMED | CONFIRMED (each with falsifier) | **ACCEPTED** |
| T12 | OnRender vs OnMarketData threads need synchronisation | CONFIRMED (no same-thread guarantee) | N/A; supporting: ChartControl is a UI-thread DispatcherObject | split: T12a "no guarantee" (A) + T12b "render is UI-thread-affine" (B supporting) → **ACCEPTED** (lock required) |
| T13 | DrawObjects + TextFixed.TextPosition/DisplayText/Font | CONFIRMED | CONFIRMED | **ACCEPTED** |
| T14 | DrawObjects includes other scripts' and user objects | CONFIRMED (user objects may arrive late during load) | N/A; supporting: DrawnBy/IsUserDrawn members | split: T14a members exist (B) + T14b content (A) → **ACCEPTED**; recompute every frame |
| T15 | TextFixed objects at one position are not stacked | CONFIRMED (source: no sibling lookup) | N/A | split: T15a source (A) accepted; T15b rendered → **UNRESOLVED → P7** (the design assumes no stacking and estimates every object at its corner) |
| T16 | TextFixed box geometry is readable from source | CONFIRMED: offset 10.5; box = text ± p, p = 3 (fallback; skins define 5 as Double, `as float?` → null) | N/A; supporting: `YPixelOffset` int exists | split: T16a offset/multipliers (A) accepted; T16b p value **UNRESOLVED** → the design uses the union of p = 3 and p = 5 |
| T17 | chart labels sit top-left | UNVERIFIABLE (vendor TopLeft adds 21 px "room for labels") | N/A | **UNRESOLVED** → allowance: reserve the panel's top 48 px (covers 21 px labels and the 42 px scroll-arrow offset); P7 |
| T18 | `MarketDataEventArgs.Time` = event time (Playback: replay time) | UNVERIFIABLE (only "a DateTime ... representing the time") | N/A; supporting: DateTime getter | **UNRESOLVED → P7** (the table shows `e.Time`; the user confirms it is replay time) |
| T19 | IsInHitTest bool, skip decoration | CONFIRMED (vendor pattern) | CONFIRMED (exists, bool) | accepted (minor) |
| T20 | ChartBackground / ChartText brushes | CONFIRMED | CONFIRMED | accepted (minor) |
| T21 | ForceRefresh() | CONFIRMED (repaint ≤ 250 ms later) | CONFIRMED | accepted (minor) |

Facts from the channels that change the design (recorded in table-spec.md §4–§5, amendment A2):
- **Copyright text.** NinjaTrader draws a copyright text at the bottom-left of the last panel. Vendor BottomLeft text is moved up 2 × 10.5 px to clear it. The design reserves a bottom-left strip.
- **Scroll arrow.** Panel 0 has a scroll arrow at the top-right (TopRight text moves to Y + 42). This is covered by the top reservation.
- **Name clashes.** A plain `using SharpDX...` makes `Brush`, `Factory`, `Color`, `Point` and `TextAlignment` ambiguous. Use aliases: `DxBrush`, `RectangleF`, `Vector2`, `TextFormat`, `TextLayout`, and write `NinjaTrader.Core.Globals` in full.
- **Coordinate units.** ChartPanel values are device pixels, as in vendor TextFixed rendering, which uses them directly with RenderTarget. The box uses the same coordinates.
- **Disposal.** `ToDxBrush` returns a new brush on every call; the caller disposes it.

Material claims still UNRESOLVED: T5b, T6b, T15b, T16b (bounded by the union), T17, T18. They are closed by one NinjaTrader screenshot (P7). The design does not need the exact answers: every allowance over-reserves.

# Phase T2 verdict — implementation claims P1–P7

Spec: table-spec.md (frozen 2026-10-29, with amendments A2 and A3). Tests were written before the code (TDD): every
test was first watched failing on missing code, then passing.

| ID | Claim | Evidence | Falsifier | Gate |
|----|-------|----------|-----------|------|
| P1 | The table model follows §2 | `harness/TableTests.cs`: hand cases (FLAG appends, FINAL updates, wrong-side, wrong-level and already-final FINALs ignored, newest-first with id tie-break, 500-row cap, header/alignment/cells, midpoint conf rounding, cross-date Ended, Apply returns the row id). 10,167 checks pass | the ascending-sort, no-capacity and banker's-rounding mutants each fail (rc=1); the first is also a slow pytest | **ACCEPTED** |
| P2 | BoxLayout and PanelReserve meet §3–§4 | hand cases plus a 20,000-case seeded property loop: inside the panel, no overlap, right-aligned, the corner when free, never below the corner, deterministic. Reserve geometry for all 5 TextPositions and the YPixelOffset, plus an end-to-end "table above a BottomRight note" case | the no-overlap-loop, touching-counts-as-overlap, BottomLeft-multiplier, p=3-only and no-YPixelOffset mutants each fail | **ACCEPTED** |
| P3 | The engine CSV is unchanged | diff_engines.py: 1,006 runs, 0 mismatches | `--falsify`: 540 runs differ | **ACCEPTED** |
| P4 | It compiles | QI_28 alone rc=0; all 81 NinjaScript files rc=0 (only the expected CS0436) | — | **ACCEPTED** |
| P5 | No price labels and no TopLeft notice; the notice is inside the box | static tests in test_IcebergDetector.py | — | **ACCEPTED** |
| P6 | Every SharpDX resource is disposed | static checker (brush fields ⊆ the DisposeDx array; disposal hooked into OnRenderTargetChanged and Terminated; every TextLayout/TextFormat in `using` or the `made` list), plus an independent code review | a planted dropped brush and a dropped `made.Add` are both flagged. The falsifier twice exposed a weak checker, and both were fixed | **ACCEPTED** |
| P7 | It renders correctly in NinjaTrader (lower right, newest first, no overlap with QI_12's score box, disclaimers, a second QI_28, axes or labels) | — | — | **UNRESOLVED → user screenshot** (also closes T5b, T6b, T15b, T16b, T17, T18) |

The independent code review (2026-10-29) found two thread-safety defects and three minor ones. All five were fixed
before this verdict (amendment A3): cells are built under `sync`; `DrawObjects.ToList()` is used with per-object
guards; brushes are all-or-nothing and null-safe; no `#0` tag is drawn; the notice split is documented.

Note on `frozen.sha256`: the hashes cover the files with LF line endings, because git converts them to CRLF on
Windows checkouts. Verify with
`for f in $(cut -d'*' -f2 validation/iceberg/frozen.sha256); do tr -d '\r' < $f | sha256sum; done` and compare.
Every frozen file is byte-identical, LF-normalized, to its freeze commit (f1bf106, 1a4d983).
