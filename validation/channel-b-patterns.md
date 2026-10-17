# Channel B: pattern-module ports vs the ORIGINAL indicator (PT1-PT4)

Date: 2026-10-17. Claims: PT1-PT4 of `validation/backtest-claims-ledger.md` (frozen; not edited here).
Educational research only. Not financial advice. See DISCLAIMER.md.

## 1. What was tested

| item | value |
|---|---|
| Port under test | `backtest/qibt/patterns.py` sha256 `1ab1e331c5e23fbf0ebf899bff6183fe52341a19b4d8df64bae0ed1bcab02858` |
| Ported C# (read in full, not edited) | `indicators/QI_HedgingPressure.cs`, `QI_LiquiditySweep.cs`, `QI_OrderFlowPlus.cs`, `QI_SMC.cs` |
| Oracle | the six EveryBar exports `MES_1min_*.csv` written by ORIG = `C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\IBSFade.cs` (OnBarUpdate 533-651, HP 1015-1059, sweeps 2038-2404, OF+ 2411-2541, SMC 2548-2739) |
| Differential test | `backtest/tests/test_patterns_orig_differential.py` sha256 `d097576aad4528ce58c729b8a7e655f88a29f19e7aaf3404d66e1be8853861e5` |
| Unit tests | `backtest/tests/test_patterns_unit.py` sha256 `f5036893939807f93f90d9eaa853b3b5ff17fc061111905f6063d04475fba420` |
| ATR source | `validation/pytests/qi_ref.py` `atr` (sha256 `cb68b987...a559`), the NT8 @ATR.cs recursion; SMA is the NT8 @SMA.cs Minute-bars running-sum branch, implemented in `patterns.nt_sma` |
| Environment | python 3.9.13, numpy 2.0.2, pandas 2.3.3, pytest 8.4.2, run with `python -I` |

Public API (names used by `backtest/qibt/signals.py`): `hp_score(df)`, `liquidity_sweep(df)`
[confidence, structure], `order_flow_plus(df)` [confidence, structure], `smc(df)` [confidence, structure,
trend_dir], aliases `sweep_structure`, `ofp_structure`, `smc_structure`, and the event logs
`liquidity_sweep_events`, `order_flow_plus_events`, `smc_events`. Parameters default to the C# defaults
(SwingLookback 20, DuplicateBarWindow 5, ...). Speed on 379,144 bars: HP 1.0 s, LiquiditySweep 2.0 s,
OrderFlow+ 1.4 s, SMC 1.3 s.

## 2. Method (stated in the test module before the first comparison)

- Each yearly file is a separate chart run. The port runs on each file alone, never on the concatenation.
- Layout: bar rows are read by header name plus the per-row surplus field (`shift = len(row) - len(header)`),
  as in `validation/probes/diff_values.py`. Every bar row must pass "Price == shifted Close" and "field
  before the shifted Open is empty"; every signal row must have 20 fields; BarTime must be strictly
  increasing (one chart run). Result on all six files: one shift value (+1) on every bar row, 0 bad rows,
  no appended runs.
- Warm-up exclusion W: bars whose trading date (calendar date, +1 day after 17:00) is one of the first 2
  trading dates of the file are not compared (1,361-1,381 rows per file). Reason: ORIG starts at the first
  logged row with ATR/SMA history from bars that are not in the file; the port starts at row 50 with ATR/SMA
  seeded at row 0.
- PT1: |hp_score - databox_HPScore| <= 1e-3 on every compared bar.
- PT2: multiset of (BarTime, confidence to 2 dp, direction) of the port's LiquiditySweep End labels ==
  ORIG `LiqSweepEnd` rows; per bar, the port plots (confidence, structure) == ORIG's last End event of the
  bar ((0, 0) without one); per bar, confidence == databox_LiqSweep (F4 tolerance 0.5e-4).
- PT3 / PT4: same for `OrderFlow+` / `SMC` rows (Buy = +1, Sell = -1) and databox_OFSignal / databox_SMCSignal.
- Diagnostics (not claims): LiquiditySweep Start labels vs `LiqSweepStart` rows; port ATR14 vs the
  exported ATR14 (F2).

## 3. Findings found during the run (reported, not tuned away)

### F1. The ORIG chart runs used DuplicateBarWindow = 6, not the C# default 5

First run with the C# default 5, file `MES_1min_20240229_20250331.csv`: PT1 matched, every LiquiditySweep
Start label matched (33,020 / 33,020), but the End / OF+ / SMC sets did not. Every mismatch had the same
shape: the port emitted a same-direction event exactly 5 bars after the previous one, ORIG emitted it at
6 bars or later (example: OF+ events at 18:59 in both; port 19:04, ORIG 19:05).

ORIG has one `DuplicateBarWindow` property shared by all its modules, including its HedgingPressure signal
rule (IBSFade.cs 1064-1135), which is not part of the four ports. Replaying that rule on ORIG's own
`databox_HPScore` reproduces the file's `HedgingPressure` rows exactly only for window 6, in every file
(mismatch count only_orig + only_sim by window, 2024 file: `{4: 11960, 5: 5036, 6: 0, 7: 4903}`; the
other five files give 0 only at 6 as well, see section 4). The differential therefore infers the window
per file from those rows and runs the ports with it. No tolerance was changed.

At the shipped default 5, verbatim (`QIBT_DUP_WINDOW=5 QIBT_ORIG_FILES=MES_1min_20240229_20250331.csv python -I backtest/tests/test_patterns_orig_differential.py`):
```
  PT2 LiqSweep End: orig events=28373 port events=29623 matched=27784 only_orig=589 only_port=1839 mismatched bars=2428 first={'BarTime': '2024-03-05 17:33:00', 'orig': [], 'port': [('2024-03-05 17:33:00', 1.0, 1)]}
  PT3 OrderFlow+: orig events=50186 port events=54036 matched=42043 only_orig=8143 only_port=11993 mismatched bars=20136 first={'BarTime': '2024-03-05 17:02:00', 'orig': [], 'port': [('2024-03-05 17:02:00', 0.65, -1)]}
  PT4 SMC: orig events=65368 port events=68715 matched=55506 only_orig=9862 only_port=13209 mismatched bars=23071 first={'BarTime': '2024-03-05 17:32:00', 'orig': [], 'port': [('2024-03-05 17:32:00', 0.72, -1)]}
```
This is a parameter difference between the ORIG chart and the QI defaults, not a port defect.
**Implication for the backtest (decision for the owner, not taken here):** `signals.py` calls the ports
with defaults (window 5, the shipping QI default). The ORIG classifications in these exports were made with
window 6. The protocol must state which one the ranking uses.

### F2. What the warm-up exclusion hides (rows 50 .. W-1 of each file)

| file | HP mismatches (rows) | port ATR vs exported ATR14 > 0.005 (rows) | LS / OF+ / SMC per-bar mismatches (last one) |
|---|---|---|---|
| 2020 | 93 (51..151) | 95 (0..106) | 2 (01-05 18:38) / 0 / 0 |
| 2021 | 45 (50..120) | 61 (0..73) | 0 / 0 / 0 |
| 2022 | 69 (50..125) | 68 (0..99) | 0 / 5 (02-01 18:38) / 4 (02-01 20:42) |
| 2023 | 48 (50..107) | 49 (0..84) | 5 (02-02 19:07) / 5 (02-02 18:03) / 7 (02-02 19:53) |
| 2024 | 70 (50..139) | 69 (0..74) | 2 (03-04 19:31) / 0 / 0 |
| 2025 | 70 (50..125) | 102 (0..127) | 0 / 2 (04-02 17:53) / 1 (04-02 17:52) |

All are inside the first ~4 hours of each file, far inside W. Cause: the CSV starts at ORIG's first logged
bar, so ORIG's ATR had ~2 sessions of history the port cannot see (row-0 ATR, 2024 file: port 0.75, export
0.57); swing / zone / duplicate state also starts 50 bars later in the port. A QI chart loaded from the same
first bar as ORIG would not have this difference; it is a property of the exports, not of the port.

### F3. Rules and constants the oracle cannot see

- "Liq Sweep" 0.70 always co-fires with "SFP" 0.50 (identical price condition, QI 570 / 610), so its End
  confidence is always min(>= 1.2, 1.0) = 1.0. Check on the 2024 file: 765 End events contain "Liq Sweep",
  765 also contain "SFP", all 765 have confidence 1.0, minimum component sum 1.2; ORIG's `LiqSweepEnd`
  confidence histogram has no 0.70 at all (`{'0.50': 2115, '0.55': 16603, '0.60': 4264, '0.65': 73,
  '0.75': 61, '0.85': 107, '1.00': 5259}`). The suggested falsifier 0.70 -> 0.71 is therefore not
  detectable (section 5, PT2); SFP 0.50 -> 0.51 was used instead.
- "Sweep MoHigh/MoLow" can never fire (the month high/low is raised with the current bar before the check).
- OF+ "DeltaRev" can never fire (volDelta[0] < 0 implies Close[0] < Close[1], the rule needs Close[0] > Close[1]).
- HP: rc and basis always have opposite signs, so |HP| <= 75 and the +/-100 clamp never binds.
All four are kept as written in the C# and are covered by unit tests.

## 4. PT1-PT4 run (all six files)

Command (repo root): `python -I -m pytest backtest/tests -q -p no:cacheprovider -k patterns`
```
.................................................................        [100%]
65 passed, 355 deselected in 98.74s (0:01:38)
```
(35 unit tests + 6 files x 5 differential tests; the 355 deselected tests belong to other modules.)

Counts: `python -I backtest/tests/test_patterns_orig_differential.py` (same `analyze()` the tests use;
two runs gave identical output), verbatim:
```
patterns module: C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators\backtest\qibt\patterns.py
MES_1min_20200101_20260201.csv: bars=373412 (2020-01-03 16:00:00 .. 2021-02-01 11:59:00), layout {'bar_rows': 373412, 'signal_rows': 238165, 'shift': {1: 373412}}; warm-up W excludes rows 0..1360 -> compared from 2020-01-06 17:01:00: 372051 bars
  ORIG DuplicateBarWindow: HedgingPressure rows reproduced exactly for window(s) [6]; only_orig+only_sim by window {4: 12190, 5: 5123, 6: 0, 7: 4963}; ports run with duplicate_bar_window=6
  diag ATR14 port vs CSV(F2): n=372051 over-0.005=0 max=0.005000
  PT1 HP: compared=372051 mismatches(>|1e-3|)=0 nan=0 max|diff|=5e-05 first=None
  PT2 LiqSweep End: orig events=27012 port events=27012 matched=27012 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=372051 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT3 OrderFlow+: orig events=50297 port events=50297 matched=50297 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=372051 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT4 SMC: orig events=66781 port events=66781 matched=66781 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=372051 mismatches=0 first=None; vs databox: mismatches=0 first=None
  diag LiqSweep Start: orig=31409 port=31409 matched=31409 only_orig=0 only_port=0 first=None
MES_1min_20210131_20220131.csv: bars=351347 (2021-02-02 16:00:00 .. 2022-01-31 15:59:00), layout {'bar_rows': 351347, 'signal_rows': 220341, 'shift': {1: 351347}}; warm-up W excludes rows 0..1365 -> compared from 2021-02-03 17:01:00: 349981 bars
  ORIG DuplicateBarWindow: HedgingPressure rows reproduced exactly for window(s) [6]; only_orig+only_sim by window {4: 11451, 5: 5032, 6: 0, 7: 4788}; ports run with duplicate_bar_window=6
  diag ATR14 port vs CSV(F2): n=349981 over-0.005=0 max=0.005000
  PT1 HP: compared=349981 mismatches(>|1e-3|)=0 nan=0 max|diff|=4.99996e-05 first=None
  PT2 LiqSweep End: orig events=23807 port events=23807 matched=23807 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=349981 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT3 OrderFlow+: orig events=45132 port events=45132 matched=45132 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=349981 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT4 SMC: orig events=61799 port events=61799 matched=61799 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=349981 mismatches=0 first=None; vs databox: mismatches=0 first=None
  diag LiqSweep Start: orig=29648 port=29648 matched=29648 only_orig=0 only_port=0 first=None
MES_1min_20220130_20230131.csv: bars=352006 (2022-02-01 16:00:00 .. 2023-01-31 15:59:00), layout {'bar_rows': 352006, 'signal_rows': 232490, 'shift': {1: 352006}}; warm-up W excludes rows 0..1380 -> compared from 2022-02-02 17:01:00: 350625 bars
  ORIG DuplicateBarWindow: HedgingPressure rows reproduced exactly for window(s) [6]; only_orig+only_sim by window {4: 10662, 5: 4448, 6: 0, 7: 4264}; ports run with duplicate_bar_window=6
  diag ATR14 port vs CSV(F2): n=350625 over-0.005=0 max=0.005000
  PT1 HP: compared=350625 mismatches(>|1e-3|)=0 nan=0 max|diff|=4.99999e-05 first=None
  PT2 LiqSweep End: orig events=28285 port events=28285 matched=28285 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=350625 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT3 OrderFlow+: orig events=49654 port events=49654 matched=49654 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=350625 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT4 SMC: orig events=62799 port events=62799 matched=62799 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=350625 mismatches=0 first=None; vs databox: mismatches=0 first=None
  diag LiqSweep Start: orig=30449 port=30449 matched=30449 only_orig=0 only_port=0 first=None
MES_1min_20230131_20240229.csv: bars=371074 (2023-02-02 16:00:00 .. 2024-02-29 15:59:00), layout {'bar_rows': 371074, 'signal_rows': 232125, 'shift': {1: 371074}}; warm-up W excludes rows 0..1380 -> compared from 2023-02-05 17:01:00: 369693 bars
  ORIG DuplicateBarWindow: HedgingPressure rows reproduced exactly for window(s) [6]; only_orig+only_sim by window {4: 11483, 5: 4937, 6: 0, 7: 4960}; ports run with duplicate_bar_window=6
  diag ATR14 port vs CSV(F2): n=369693 over-0.005=0 max=0.005000
  PT1 HP: compared=369693 mismatches(>|1e-3|)=0 nan=0 max|diff|=5e-05 first=None
  PT2 LiqSweep End: orig events=26300 port events=26300 matched=26300 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=369693 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT3 OrderFlow+: orig events=47459 port events=47459 matched=47459 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=369693 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT4 SMC: orig events=63258 port events=63258 matched=63258 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=369693 mismatches=0 first=None; vs databox: mismatches=0 first=None
  diag LiqSweep Start: orig=32849 port=32849 matched=32849 only_orig=0 only_port=0 first=None
MES_1min_20240229_20250331.csv: bars=379144 (2024-03-04 16:00:00 .. 2025-03-31 15:59:00), layout {'bar_rows': 379144, 'signal_rows': 237934, 'shift': {1: 379144}}; warm-up W excludes rows 0..1379 -> compared from 2024-03-05 17:01:00: 377764 bars
  ORIG DuplicateBarWindow: HedgingPressure rows reproduced exactly for window(s) [6]; only_orig+only_sim by window {4: 11960, 5: 5036, 6: 0, 7: 4903}; ports run with duplicate_bar_window=6
  diag ATR14 port vs CSV(F2): n=377764 over-0.005=0 max=0.005000
  PT1 HP: compared=377764 mismatches(>|1e-3|)=0 nan=0 max|diff|=4.99999e-05 first=None
  PT2 LiqSweep End: orig events=28373 port events=28373 matched=28373 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=377764 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT3 OrderFlow+: orig events=50186 port events=50186 matched=50186 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=377764 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT4 SMC: orig events=65368 port events=65368 matched=65368 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=377764 mismatches=0 first=None; vs databox: mismatches=0 first=None
  diag LiqSweep Start: orig=33020 port=33020 matched=33020 only_orig=0 only_port=0 first=None
MES_1min_20250331_20260224.csv: bars=315408 (2025-04-02 16:00:00 .. 2026-02-24 14:53:00), layout {'bar_rows': 315408, 'signal_rows': 199935, 'shift': {1: 315408}}; warm-up W excludes rows 0..1380 -> compared from 2025-04-03 17:01:00: 314027 bars
  ORIG DuplicateBarWindow: HedgingPressure rows reproduced exactly for window(s) [6]; only_orig+only_sim by window {4: 9712, 5: 4142, 6: 0, 7: 3892}; ports run with duplicate_bar_window=6
  diag ATR14 port vs CSV(F2): n=314027 over-0.005=0 max=0.005000
  PT1 HP: compared=314027 mismatches(>|1e-3|)=0 nan=0 max|diff|=5e-05 first=None
  PT2 LiqSweep End: orig events=25925 port events=25925 matched=25925 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=314027 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT3 OrderFlow+: orig events=43902 port events=43902 matched=43902 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=314027 mismatches=0 first=None; vs databox: mismatches=0 first=None
  PT4 SMC: orig events=54862 port events=54862 matched=54862 only_orig=0 only_port=0 mismatched bars=0 first=None
      per-bar plots vs ORIG last event: n=314027 mismatches=0 first=None; vs databox: mismatches=0 first=None
  diag LiqSweep Start: orig=27644 port=27644 matched=27644 only_orig=0 only_port=0 first=None
```
Totals over the six files: 2,134,141 compared bars; PT2 159,702 End events; PT3 286,630 events; PT4
374,867 events; LiquiditySweep Start labels 185,019; 0 mismatches in every row.

## 5. Falsifiers (one line changed in a scratch copy; the shipped file was not touched)

Each mutant is `backtest/qibt/patterns.py` with exactly one line changed (`diff` output below), placed in a
scratch tree next to a copy of qi_ref.py, and tested on the 2024 yearly file (377,764 compared bars) with:
```
QIBT_PATTERNS_FILE=<scratch>/<mutant>/repo/backtest/qibt/patterns.py QIBT_ORIG_FILES=MES_1min_20240229_20250331.csv \
  python -I -m pytest backtest/tests -q -p no:cacheprovider -k patterns_orig_differential --tb=line
```
sha256 of the shipped `backtest/qibt/patterns.py` before and after all falsifier runs:
`1ab1e331c5e23fbf0ebf899bff6183fe52341a19b4d8df64bae0ed1bcab02858` (identical).

| mutant | diff | pytest result | report line (`python -I backtest/tests/test_patterns_orig_differential.py`, same env) |
|---|---|---|---|
| PT1 basis -25 -> -24 | `207c207 basis_dev * -25.0` -> `* -24.0` | `1 failed, 4 passed` (PT1 only) | `PT1 HP: compared=377764 mismatches(>\|1e-3\|)=194408 nan=0 max\|diff\|=1 first={'BarTime': '2024-03-05 17:11:00', 'port': -16.212932538369827, 'orig': -15.8468}` |
| PT2 "Liq Sweep" 0.70 -> 0.71 | `422c422` | `5 passed` (NOT detected) | `PT2 LiqSweep End: ... matched=28373 only_orig=0 only_port=0` - unobservable, see F3 |
| PT2 "SFP" 0.50 -> 0.51 | `465c465` | `1 failed, 4 passed` (PT2 only) | `PT2 LiqSweep End: orig events=28373 port events=28373 matched=27308 only_orig=1065 only_port=1065 mismatched bars=1065 first={'BarTime': '2024-03-06 06:43:00', 'orig': [('2024-03-06 06:43:00', 0.5, -1)], 'port': [('2024-03-06 06:43:00', 0.51, -1)]}` |
| PT3 DeltaDiv 0.78 -> 0.77 (high side) | `677c677` | `1 failed, 4 passed` (PT3 only) | `PT3 OrderFlow+: orig events=50186 port events=50186 matched=44239 only_orig=5947 only_port=5947 mismatched bars=5947 first={'BarTime': '2024-03-05 21:57:00', 'orig': [('2024-03-05 21:57:00', 0.78, -1)], 'port': [('2024-03-05 21:57:00', 0.77, -1)]}` |
| PT4 OB Retest 0.72 -> 0.71 (bullish) | `875c875` | `1 failed, 4 passed` (PT4 only) | `PT4 SMC: orig events=65368 port events=65368 matched=64070 only_orig=1298 only_port=1298 mismatched bars=1298 first={'BarTime': '2024-03-05 23:31:00', 'orig': [('2024-03-05 23:31:00', 0.72, 1)], 'port': [('2024-03-05 23:31:00', 0.71, 1)]}` |

Verbatim pytest failure lines:
```
test_patterns_orig_differential.py:386: AssertionError: {'first': {'BarTime': '2024-03-05 17:11:00', 'orig': -15.8468, 'port': -16.212932538369827}, 'max_abs_diff': 1.0000004599204075, 'mismatches': 194408, 'n': 377764, ...}
FAILED backtest\tests\test_patterns_orig_differential.py::test_patterns_PT1_hp_score[MES_1min_20240229_20250331.csv]
1 failed, 4 passed, 390 deselected in 14.13s
test_patterns_orig_differential.py:393: AssertionError: {'databox_first': {'BarTime': '2024-03-06 06:43:00', 'orig': 0.5, 'port': 0.51}, 'databox_mismatches': 1065, 'first': ...3:00', 'orig': [('2024-03-06 06:43:00', 0.5, -1)], 'port': [('2024-03-06 06:43:00', 0.51, -1)]}, 'matched': 27308, ...}
FAILED backtest\tests\test_patterns_orig_differential.py::test_patterns_event_sets[MES_1min_20240229_20250331.csv-PT2]
1 failed, 4 passed, 390 deselected in 19.58s
test_patterns_orig_differential.py:393: AssertionError: {'databox_first': {'BarTime': '2024-03-05 21:57:00', 'orig': 0.78, 'port': 0.77}, 'databox_mismatches': 5947, 'first':...:00', 'orig': [('2024-03-05 21:57:00', 0.78, -1)], 'port': [('2024-03-05 21:57:00', 0.77, -1)]}, 'matched': 44239, ...}
FAILED backtest\tests\test_patterns_orig_differential.py::test_patterns_event_sets[MES_1min_20240229_20250331.csv-PT3]
1 failed, 4 passed, 390 deselected in 18.45s
test_patterns_orig_differential.py:393: AssertionError: {'databox_first': {'BarTime': '2024-03-05 23:31:00', 'orig': 0.72, 'port': 0.71}, 'databox_mismatches': 1298, 'first':...31:00', 'orig': [('2024-03-05 23:31:00', 0.72, 1)], 'port': [('2024-03-05 23:31:00', 0.71, 1)]}, 'matched': 64070, ...}
FAILED backtest\tests\test_patterns_orig_differential.py::test_patterns_event_sets[MES_1min_20240229_20250331.csv-PT4]
1 failed, 4 passed, 390 deselected in 19.14s
0.70 -> 0.71 mutant:
5 passed, 390 deselected in 15.14s
```
Each detectable mutant fails its own claim and no other claim.

## 6. Unit tests (`backtest/tests/test_patterns_unit.py`, 35 tests, all pass)

Hand-built sequences on a "contracting triangle" base that fires no rule by itself; each expected value is
derived from the C# rule text (line references in each test). Covered: HP zero gate (ATR 0), basis and
slope terms clamped at -25 (HP = -50 exactly), vp clamp +25, vp + rc = +50, vp and rc clamped at -25, an
independent HP re-implementation on 3,000 random bars (|diff| <= 1e-9, |HP| <= 75); LiquiditySweep: swing-high
sweep with wick >= 2x body and volume > 1.5x SMA20 (components "Liq Sweep" 0.70 + "SFP" 0.50, End confidence
1.0, -1, then the VolDiv-absorbed confirmation 0.55 on the next bar), the bullish mirror, SFP alone 0.50,
SFP(2bar) 0.60, equal-high trap 0.60 with pool consumption, Spring 0.60 and 0.75 (in consolidation),
Turtle Soup 0.55 both sides, consolidation trap 0.65 and the end rule (ratio >= 0.9 AND > 50 bars),
VolDiv weak pending -> End 0.55 that suppresses a same-bar SFP(2bar), Sweep PDH 0.85, Sweep ORB-H 0.85,
the SwingLookback*2+5 gate; duplicate suppression (barsSince 3 suppressed, 5 fires, window 6/2 variants);
OF+: DeltaDiv 0.78, Absorption 0.65 with duplicate window, StackedDelta 0.55, Exhaustion 0.60, swing gate;
SMC: FVG 0.68 + Displacement, later OB Retest 0.72, FVG alone, BOS 0.60 with the shared 5-bar cooldown,
CHoCH 0.75 with trend_dir, Displacement 0.58 with duplicate window, swing gate; the unreachable rules of F3.

Mutation check of the unit tests (scratch copies, same one-line method, run against the final test file):
34 mutants of rule constants, comparisons, gates and window logic; **34 caught**, unmutated copy 35 passed.
This includes "Liq Sweep" 0.70 -> 0.71, which the unit tests see through the event log's per-pattern
components although ORIG's output cannot show it (F3). History, for honesty: in the first sweep the three
SwingLookback*2+5 gate mutants survived (at SwingLookback 20 the gate 45 is below the global bar-50 gate, so
they are equivalent there) and so did `barsSince <= window` in the sweep filter (no test sat exactly at
barsSince 5); the SwingLookback-25 gate tests and the exact-boundary Turtle Soup test were added for them.

## 7. Verdicts

| claim | verdict | evidence |
|---|---|---|
| PT1 hp_score == databox_HPScore within 1e-3 | **CONFIRMED** | 6 files, 2,134,141 bars after W, 0 mismatches, max \|diff\| 5.0e-5 (= F4 half-unit); falsifier -25 -> -24: 194,408 mismatches. Inside W (not claimed): 45-93 bars per file in rows 50-151, caused by ATR seeding (F2). |
| PT2 LiquiditySweep End events == ORIG | **CONFIRMED** for the port run at ORIG's DuplicateBarWindow 6 | 159,702 events, 0 only_orig / 0 only_port; per-bar plots and databox 0 mismatches on 2,134,141 bars; falsifier SFP 0.50 -> 0.51: 1,065 mismatches. The 0.70 constant is not identifiable from this oracle (F3). At the C# default 5: REFUTED, 589 only_orig / 1,839 only_port on the 2024 file, cause F1. |
| PT3 OrderFlow+ events == ORIG | **CONFIRMED** for window 6 | 286,630 events, 0 / 0; per-bar and databox 0; falsifier 0.78 -> 0.77: 5,947 mismatches. At window 5: 8,143 / 11,993 (2024 file), cause F1. |
| PT4 SMC events == ORIG | **CONFIRMED** for window 6 | 374,867 events, 0 / 0; per-bar and databox 0; falsifier 0.72 -> 0.71: 1,298 mismatches. At window 5: 9,862 / 13,209 (2024 file), cause F1. |

Residual assumptions: unwritten Series<double> slots read as 0.0 (only affects bars 50-59, inside W);
TimeZoneInfo conversion = identity (PC zone is US Central). Neither is exercised by a compared bar.
