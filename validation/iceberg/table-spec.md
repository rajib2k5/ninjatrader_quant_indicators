# QI_28 table panel — specification (amendment A1 to spec.md §7, drawing only)

status: FROZEN 2026-10-29 after the T1–T21 gate (table-report.md), with amendment A2 (§4–§5 allowances). The engine (spec.md §1–§6) and its CSV
contract do not change; the I2 differential must stay at 0 mismatches.

> Educational use only — not financial advice. The table labels order-book behaviour; it never says buy or sell.

## 1. What changes

- The per-level price labels (`Iceberg bid 7012.25 ~340 hidden (...)`) are replaced by **one table in a box at the
  lower right of the price panel**, newest row first.
- At each flagged price the chart keeps a short line plus a small `#n` tag. `n` is the row's number in the table.
- The historical notice moves into the box (status line) instead of a separate `TopLeft` text, which would sit on
  NinjaTrader's indicator labels (T17).

## 2. Table model — `IcebergTable` (NT-free, namespace `...Engines`)

- `Apply(IcebergRecord r, DateTime t)`:
  - **FLAG** appends a row with:
    - `Id` = next integer, starting at 1;
    - `Detected` = t, `Side`, `Price`;
    - `Hidden` = HiddenEst, `Traded`, `Shown` = ShownMax, `Refills`, `Conf`;
    - `Status` = `active`, `Ended` = none;
    - `StartSeq` = r.StartSeq.
  - **FINAL** updates the row whose `Side` and `StartSeq` match and whose `Status` is `active`. Hidden, Traded,
    Shown, Refills and Conf take the final values, `Status` = r.Reason and `Ended` = t. With no matching row it
    does nothing.
- `Rows(int max)` returns at most `max` rows ordered by `Detected` descending, ties by `Id` descending.
  `Count` = total rows held.
- At most `Capacity` = 500 rows are held. The 501st row drops the oldest by `Detected`, then by `Id`.
- Cells (`Cells(row, Func<double,string> formatPrice)`, InvariantCulture):

  | Column | Header | Cell |
  |--------|--------|------|
  | 1 | `#` | `#` + Id |
  | 2 | `Detected` | `MM-dd HH:mm:ss` |
  | 3 | `Side` | `bid` / `ask` |
  | 4 | `Price` | formatPrice(Price) |
  | 5 | `Hidden` | `~` + Hidden |
  | 6 | `Traded` | Traded |
  | 7 | `Shown` | Shown |
  | 8 | `Refills` | Refills |
  | 9 | `Conf` | round(Conf×100, away from zero) + `%` |
  | 10 | `Status` | `active` / `held` / `broken` / `open` |
  | 11 | `Ended` | `-` if none; `HH:mm:ss` on the same date as Detected; else `MM-dd HH:mm:ss` |

  Columns 1 and 4–9 are right-aligned; the rest are left-aligned.
- Box text:
  - Title: `QI 28 Iceberg levels (probable) - newest first`.
  - Status line, only while the chart is not in State.Realtime: the spec.md §0 notice, verbatim.
  - With no rows, one line: `No probable iceberg levels yet.`
  - When `Count` > rows shown, a footer: `+K older not shown`.

## 3. Placement — `BoxLayout.Place(panel, w, h, occupied, margin, gap)` (NT-free)

Inputs: the panel rectangle (left, top, width, height in RenderTarget pixels, Y down), the box size, a list of
occupied rectangles, a margin and a gap. Output: a rectangle or none.

1. If `w > panel.W − 2·margin` or `h > panel.H − 2·margin` → none.
2. Start at the bottom-right corner: `x = panel.Right − margin − w`, `y = panel.Bottom − margin − h`.
3. Repeat:
   - Find the occupied rectangles that overlap the candidate grown by `gap` on every side. Overlap is strict:
     touching edges do not overlap.
   - If there are none → return the candidate.
   - Otherwise `y = min(top of those rectangles) − gap − h`. If `y < panel.Top + margin` → none.

Guarantees (tested as properties):
- the result lies inside the panel minus the margin;
- it overlaps no occupied rectangle;
- its right edge is `panel.Right − margin`;
- with no rectangle in the way, it is exactly the corner position;
- it is deterministic.

The indicator first tries `min(MaxTableRows, Count)` rows. If placement fails it drops one row at a time, keeping
title and header. If even zero rows do not fit, the box is not drawn that frame.

## 4. Occupied rectangles the indicator passes in (A2: every allowance over-reserves)

Constants: `margin` = 8 px, `gap` = 6 px. All values are in ChartPanel device pixels (T5).

1. **Other QI_28 instances.** The last-drawn box of every other QI_28 instance on the same ChartPanel that
   registered earlier. This is a static registry keyed by panel: an instance registers on its first OnRender and
   unregisters at State.Terminated. Later instances stack above earlier ones.
2. **TextFixed objects.** Every `TextFixed` object in `DrawObjects` (T13, T14), whatever its panel, so objects on
   other panels also reserve space; this is safe.
   - Text size `w × h` is measured the way the vendor code does: `Font.ToDirectWriteTextFormat()` and a
     `TextLayout` of `DisplayText` with maximum size panel W × H, using `Metrics.Width/Height`.
   - With `o = |YPixelOffset|`, the reserved rectangle is the union over p ∈ {3, 5} and the panel multipliers (T16):

     | TextPosition | x range | y range |
     |---|---|---|
     | BottomRight | `R − 10.5 − w − 5 … R − 5.5` | `B − 10.5 − h − 5 − o … B − 5.5 + o` |
     | BottomLeft | `X + 5.5 … X + 10.5 + w + 5` | `B − 21 − h − 5 − o … B − 5.5 + o` |
     | TopLeft | `X + 5.5 … X + 10.5 + w + 5` | `Y + 21 − 5 − o … Y + 21 + h + 5 + o` |
     | TopRight | `R − 10.5 − w − 5 … R − 5.5` | `Y + 10 − 5 − o … Y + 42 + h + 5 + o` |
     | Center | `X + (W − w)/2 − 5`, width `w + 10` | `Y + (H − h)/2 − 5 − o`, height `h + 10 + 2o` |

3. **Top strip.** The panel's top 48 px, full width. This covers the chart labels (T17) and the panel-0 scroll
   arrow (TopRight y + 42).
4. **Copyright strip.** The bottom-left strip `X … X + min(360, W/2)` by `B − 24 … B`, for the copyright text on
   the last panel.
5. **Overlay Y-axis.** When `ChartPanel.IsYAxisDisplayedOverlay`, a right strip 80 px wide over the full height
   (T6b).

## 5. Rendering (`OnRender`)

- Skip during hit-test passes (T19).
- Copy the rows under the indicator's lock; never hold the lock while drawing (T12).
- Measure every cell with DirectWrite `TextLayout` (T7–T9). Column width = widest cell + 2 × padding.
- Draw with RenderTarget (T11):
  - the background is the chart background colour at `TableOpacity` %;
  - the border uses the chart text colour;
  - the text uses the chart text colour, except Side and Price cells, which use BidBrush / AskBrush.
- Brushes are created in `OnRenderTargetChanged` and disposed there and at State.Terminated (T2, T3). `ToDxBrush`
  returns a new brush each call; every TextLayout and TextFormat created in OnRender is disposed in the same call.
- `using` aliases (T7–T11, Channel B): `DxBrush`, `RectangleF`, `Vector2`, `TextFormat`, `TextLayout`; write
  `NinjaTrader.Core.Globals` in full.
- Call `ForceRefresh()` after the table changes in OnMarketData (T21).
- Font: `Consolas`, `TableFontSize`.

## 6. Properties (amends spec.md §7)

| Property | Default | Notes |
|----------|---------|-------|
| `ShowTable` | true | |
| `MaxTableRows` | 8 | range 1–50 |
| `TableFontSize` | 11 | range 8–24 |
| `TableOpacity` | 85 | range 10–100 |
| `ShowLevelLines` | true | replaces `ShowLabels`; draws the line and the `#n` tag |

BidBrush, AskBrush and ShowDisclaimer are unchanged.

## 7. Claims

| ID | Mat | Claim | Probe |
|----|-----|-------|-------|
| P1 | M | Table rows and cells follow §2 exactly (FLAG appends, FINAL updates, order, capacity, formats) | C# test runner `TableTests.cs` (hand cases), written before the code; falsifier: a mutant that sorts ascending fails |
| P2 | M | `BoxLayout` meets every §3 guarantee | C# property loop: 20,000 random panels and occupied sets (seeded); falsifier: a mutant without the overlap loop fails |
| P3 | M | The engine CSV is unchanged | diff_engines.py 0 mismatches; the falsifier still fires |
| P4 | M | It compiles alone and with all 81 NinjaScript files | compile_probe.sh |
| P5 | M | No TopLeft notice remains; the historical notice text is inside the box; there are no per-level text labels with numbers | static tests in test_IcebergDetector.py |
| P6 | M | Every SharpDX resource the indicator creates is disposed | static test: each `new TextLayout` / `ToDxBrush` has a matching Dispose path, plus a code review |
| P7 | M | In NinjaTrader the box shows at the lower right, newest first, with no overlap of other boxes (e.g. QI_12 score panel, disclaimers) or of axes and labels | user screenshot, live/Playback (pending) |

## Amendment A3 (2026-10-29, after code review)

- **Historical notice.** The spec.md §0 notice is shown word for word, split into two lines at ` (` so the box
  stays narrow. The constant in the source is unchanged.
- **When brushes are made.** They are created on the first OnRender after a render-target change and disposed in
  `OnRenderTargetChanged` and at State.Terminated. This follows T3's lifetime rule. §5's "created in
  OnRenderTargetChanged" is relaxed because ChartControl may not be ready there. A set left half-built by an
  exception is disposed before the next try.
- **Thread safety.** Cell texts are built while `sync` is held, because FINAL updates rows in place on the data
  thread (review finding).
- **Reading DrawObjects.** It is copied with `DrawObjects.ToList()`, NinjaTrader's thread-safe copy (T13 member
  list). An object that cannot be measured is skipped.
- **Missing row.** A FINAL with no table row (dropped by the 500-row cap) draws no `#0` tag.
