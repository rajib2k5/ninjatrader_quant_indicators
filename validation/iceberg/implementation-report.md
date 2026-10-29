# Phase 2 verdict — QI_28_IcebergDetector implementation claims (I1–I8)

spec: validation/iceberg/spec.md (FROZEN 2026-10-28; sha256 in frozen.sha256), unchanged during implementation.
independence: the C# engine (indicators/QI_28_IcebergDetector.cs) and the Python reference
(backtest/qibt/iceberg.py, booksim.py, iceberg_eval.py) were written by two separate agents from the
spec alone. Neither read the other's code. The main session wrote the differential and the C#-side tests.
environment: NinjaTrader 8.1.8.4 assemblies, Roslyn csc from .NET SDK 8.0.100, Python 3.9.13.

| ID | Claim | Evidence | Falsifier | Gate |
|----|-------|----------|-----------|------|
| I1 | compiles alone and with everything | compile_probe.sh: QI_28 alone rc=0, no warnings. All 28 indicators + 25 strategies + 28 QIV harness files rc=0 (only the expected CS0436 "type also in installed NinjaTrader.Custom.dll" warnings) | the probe returns csc's rc; the C# agent's build tests failed on planted type errors | **ACCEPTED** |
| I2 | C# engine == Python reference | `diff_engines.py`: 503 streams (200 booksim sessions, 300 fuzz streams for edge branches, 3 hand streams) × 2 parameter sets = 1,006 runs, 4,151 records (2,077 FLAG). **0 mismatched runs** | `--falsify` (C# HiddenRatio 1.9 vs Python 2.0): 540 of 1,006 runs differ | **ACCEPTED** |
| I3 | recall ≥ 0.90, false alarms ≤ 0.10 on simulated books | booksim 200 sessions, seed 20261028: recall 580/580 = 1.00. False alarms 0/1,210 = 0.00 (decoy_large 0/381, decoy_join 0/405, decoy_small_mm 0/424). 0 flags on noise levels | HiddenRatio 1.0 + MinRefills 0 → false-alarm rate 0.264 (319/405 joins flagged) | **ACCEPTED, with a caveat (below)** |
| I4 | no look-ahead | Python: 12 sessions, random cut points, two parameter sets. C#: 6 sessions × 3 prefixes through the exe; the records equal the full run's records up to the cut | the prefix test compares against the full run's own per-event emissions | **ACCEPTED** |
| I5 | every §3 rule branch | backtest/tests/test_iceberg.py: 47 tests (one per branch, plus the I3/I4/determinism tests). The I2 diff carries them to C#, and the C# hand streams have hand-computed expectations | the conf-formula and ordering tests use literal expected values | **ACCEPTED** |
| I6 | live-only, no OnMarketDepth | static tests: no `OnMarketDepth` override; `if (State != State.Realtime) return;` comes before any engine call in OnMarketData; the engine block uses no NinjaTrader types; the harness exe runs with no NinjaTrader DLL beside it | the planted-override and missing-guard strings are rejected | **ACCEPTED** |
| I7 | repo invariants | validation/pytests/test_repo_invariants.py (now 28 files) and the coverage gate pass for QI_28 | existing scanner falsifiers | **ACCEPTED** |
| I8 | works in NinjaTrader Playback | — | — | **UNRESOLVED — user run (TESTING.md section 4)** |

Caveat on I3: the simulator was written from the same definitions the detector encodes, so perfect
scores show that the rules separate the kinds *as defined*. They are not an estimate of recall or
false alarms on real order books. Examples a real book can contain that the simulator does not:
- refills that arrive late or at a smaller size;
- other orders joining the iceberg's level;
- a market maker re-quoting with large volume (documented limitation, indistinguishable on price-level data).

Python agent's note: an iceberg cut off after one refill is excluded from the planted set, because no
price-level detector can see it.

Ambiguities both agents reported, and how they were resolved. Each resolution matches in both
implementations; the I2 diff is evidence of that.
- **No flag check on level creation (§3.1b).** It can only matter with degenerate parameters.
- **Crossed or locked book (b ≥ a) and unknown bid/ask:** the trade is unclassified.
- **`pending` is cleared only by a counted refill.** A size decrease or a sub-MinRefillSize increase leaves it set.
- **Reset:** FINAL bid before FINAL ask, `end_seq` = the reset seq, reason `open`.

Indicator-only choices (C#, not part of the engine contract):
- **Calculate.OnEachTick:** needed for the session-reset rule (`Bars.IsFirstBarOfSession` on the first tick) and for live DataBox values.
- **IsSuspendedWhileInactive = false.**
- **A price of 0 from NinjaTrader is read as unknown.**
- **Plots are left unset on historical bars.**

Still open from phase 1, closed by the same user run: R4 (Bid/Ask `Volume` = displayed size), R9 (depth in
Playback), R16 (local ticks have no sizes; the design no longer depends on R16).
