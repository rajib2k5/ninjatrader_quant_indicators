# Ledger addenda (items raised after the freeze; each runs through both channels fresh)

## ADD-1 (2026-10-15) — C41 fix
Channel A (channel-a-fidelity-2.md) found QI_LiquiditySweep wrote `Values[0]/[1]` on Start labels
(QI 725-726) while ORIG wrote `Values[24]` only on End events (ORIG 2373-2385). The deviation came
from the orchestrator's CONVENTIONS spec, not from ORIG. Fix applied before any NinjaTrader run:
`if (!isStart) { Values[0][0] = confidence; Values[1][0] = direction; }`. Labels unchanged.
Fresh claim C41.1: "after the fix, QI_LiquiditySweep's Confidence equals ORIG Values[24] bar-for-bar
(no start-only extras)". A: static re-read of the edited lines. B: diff_values.py C41 row must show
0 mismatches AND 0 start-only events.

## ADD-2 (2026-10-15) — C27 deliberate deviation (user decision)
Channel A (channel-a-api.md, C7 side note → C27) found ORIG 1354 `double bollMid = boll[0];` resolves to
Bollinger.Values[0] = Upper (@Bollinger.cs:76), so ORIG's "%B" = (Close-Upper)/half-width*100. The user chose
to ship true %B. QI_BollingerPctB now uses `boll.Middle[0]`. C27 is re-scoped as C27.1: "QI_BollingerPctB
value equals ORIG Values[10] + 100 on every bar ≥ 50 where bandwidth > 0, and 0 where ORIG is 0".
A: static re-read. B: diff_values.py applies the +100 offset for C27 and must show 0 mismatches.

## ADD-3 (2026-10-15) — D0 intraday warm-up gate: documented deviation (user decision)
Channel A (channel-a-fidelity-1.md: C20, C23, C25 REFUTED on intraday charts; channel-a-fidelity-2.md: D0)
established that ORIG 537 gates on `CurrentBars[1] < 1` as well as bar 50 on intraday charts. The user chose
not to add a daily series to the stateful standalone modules. Scope change recorded, not a claim rewrite:
C20/C23/C25 remain REJECTED-on-intraday as audited; the accepted engineering claim is the documented one
("daily charts match exactly; intraday differs for ≈ the oldest session then converges"). Headers of
QI_ConnorsRSI, QI_ConsecDays, QI_CompositeVol, QI_VolumeDelta and README "Known quirks" updated.
B runtime check: diff_values.py on the 5-min chart must show the C20/C23/C25 mismatches confined to the
start of the series (first-mismatch bar reported) and zero mismatches on the daily chart.

## ADD-4 (2026-10-16) — presentation re-assessment (user request after first chart review)
On a live chart the user found modules rendering in two places (price labels/lines AND a sub-panel
repeating the same information as bars) and the per-panel disclaimer text eating space. Changes
(presentation only; no formula, guard or event logic touched):
- Converted to IsOverlay = true with the computed values as `Brushes.Transparent` plots
  (`ShowTransparentPlotsInDataBox = true`, the original's own technique): QI_HedgingPressure
  (score; HP price lines + text panel unchanged), QI_LiquiditySweep / QI_OrderFlowPlus / QI_SMC
  (Confidence, Structure), QI_VWAPDistance (now plots the VWAP level on price as Values[0] when
  intraday and live; distance moved to Values[1]), QI_BollingerPctB (now plots Upper/Middle/Lower on
  price as Values[0..2]; %B moved to Values[3]), QI_TurnOfMonth / QI_TurnaroundTuesday (shading only).
- Removed the AddLine reference lines and their LowerThreshold/UpperThreshold properties from the
  converted modules (lines at ±35 / ±100 / ±0.5 would be drawn on the price scale).
- `ShowDisclaimer` default changed from true to false in all 27 files (header, Description,
  README and DISCLAIMER.md still carry the disclaimer). C16's third element is re-scoped to
  "a ShowDisclaimer property exists"; its B probe becomes `ShowDisclaimer\s*=\s*false;` == 1.
Ledger consequences: C4 (DrawOnPricePanel) is now moot for the converted modules; C27 and C33
harness columns are `QI_BollingerPctB.PctB` and `QI_VWAPDistance.VwapDistance` (diff_values.py
updated). New runtime claim C45 (material): "transparent overlay plots with non-price values
(HP score, confidence, %B, flags) do not stretch the price panel's auto-scale" — falsifier: the
price panel's visible range widens to include 0 / ±100 when such a module is added. B probe:
screenshot of the price panel before/after adding QI_HedgingPressure and QI_BollingerPctB.
Harness regenerated; all 28 files recompiled with compile_probe.sh after the change.
