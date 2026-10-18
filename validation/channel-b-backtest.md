# Channel B (runtime audit) - backtest claims BT1-BT18

Date: 2026-10-17. Ledger: `validation/backtest-claims-ledger.md` (FROZEN). Spec: `backtest/PROTOCOL.md`
(as frozen, sha256 `a4510f51...`, i.e. before amendment A1), `backtest/rules.yaml`.

## 0. Charter, independence and the audited version

- Empirical only. No documentation, papers, help pages or web pages were consulted.
  `validation/channel-a*.md` was not read. `backtest/tests/` was not read.
- I read the `qibt` sources only to learn call names and signatures. Every expected value in every
  probe comes from the ledger or PROTOCOL text. Fixtures are hand-computed in the probe source.
  Reference maths (Phi via erfc, Phi^-1 by bisection, SR, moments, PSR, SR0, MDD) is my own code in
  `validation/probes/channel_b_backtest/_cb.py`. It never calls `qibt`.
- All Python ran as `python -I -B` (no bytecode writes). Mutants live only in the scratch folder
  `%SCRATCH%` = `C:\Users\rajib\AppData\Local\Temp\claude\C--Users-rajib-OneDrive-Documents\533a663d-5efe-42d6-aafd-bb6df2ee5fa2\scratchpad\chanB_bt`.
  In the verbatim blocks below, this prefix is abbreviated as `%SCRATCH%` (Windows form) or
  `$SCRATCH` (POSIX form). That is the only edit to the logs.
- Probe scripts: `validation/probes/channel_b_backtest/`. Full unabbreviated logs:
  `validation/probes/channel_b_backtest/logs/` (`channel_b_run.log`, `channel_b_pinned.log`, sha256 snapshots).
- Toolchain: python 3.9.13, numpy 2.0.2, pandas 2.3.3, pyyaml 6.0.3, scipy 1.13.1 (used only by
  `xcheck_dsr_tiebreak.py`), .NET SDK 8.0.100 Roslyn csc (`compile_probe.sh`). Repo HEAD at the start of the final run: `08c834e`.
- Exact argv: `run_channel_b.sh` and `run_data_falsifiers_pinned.sh` hold the exact command of every
  probe, with its quoting. The `$ ...` line in each block is that command as echoed (quotes dropped).
- Two probe scripts changed after the main run, in printing and plumbing only, not in any check.
  `bt04_session_halt.py` gained the monthly-share OBSERVATION line. `xcheck_ranking.py` gained a
  DSR print line and loads rules.yaml by explicit repo path, so it also runs against a copied
  package. The pinned blocks come from the current scripts. Their check results equal the main run.

### 0.1 Concurrent change of the code under test (read this first)

Someone else changed the repository while this audit ran:

| time (CT) | change | sha256 now |
|---|---|---|
| 17:46:07 | `backtest/PROTOCOL.md` amended (commit `130fd17` "Amend protocol (A1): daily close = NinjaTrader settlement close") | `03a8fde3...` |
| between 17:48:14 (last v1 copy) and 17:49:12 (first seen by my process); last write 17:49:35 | `backtest/qibt/data.py` rewritten (LOADER_VERSION 2, D close = settlement close) | `8384a211...` |
| 17:49:46 | `results/*` moved to `results/v1_last_trade/` (all 12 files are byte-identical to the audited ones, see section 4) | unchanged |
| 17:51 - 17:52 | `backtest/qibt/cli.py` changed, `backtest/qibt/bootstrap.py` added | `0d7de4ca...`, `5f9f1333...` |

**All verdicts below apply to the audited version v1:** the sha256 set in
`logs/sha256_before.txt`. That set has engine `10ebc194...`, metrics `9670a1c1...`, data `6fe54619...`,
cli `f76f9695...`, rank `e4bdd92b...`, signals `33613909...`, patterns `1ab1e331...`, and the results
files listed in section 4. They do **not** apply to data.py v2, cli.py v2 or PROTOCOL A1. Those need
a new pass, because amendment A1 changes the D-frame close that BT14 specifies.

Evidence that each verdict ran on v1:
- The final run (`logs/channel_b_run.log`) started at 17:45:32. All original-code probes, the three
  BT18 CLI runs, the cross-checks and every module-mutant copy were done by 17:48:15.
  The mutant copies made at 17:47-17:48 carry the v1 `data.py` hash `6fe54619...`
  (`pristine_hashes.txt` and the MUTANT blocks).
- The BT4, BT6 and BT17 data falsifiers at the end of that run started after data.py changed.
  The first of them ("BT4 falsifier A", log line 1548) reports `cache=miss`. **That process,
  started by me, imported the new v2 loader. The v2 loader's own `load_p1()` then rebuilt
  `backtest/data/P1_1min.pkl/.json` (v2 cache, 119,974,958 bytes).** No source file was written by
  any probe. Those falsifier results are therefore not used. Instead,
  `run_data_falsifiers_pinned.sh` re-ran BT4, BT6 and BT17 with probes and falsifiers against
  `%SCRATCH%\pristine_v1\qibt`. That copy is assembled from the v1 mutant copies, and its 8 `.py`
  files match `sha256_before.txt` exactly (`logs/pristine_hashes.txt`). The pinned runs used
  `%SCRATCH%\raw_p1.pkl`, my own raw re-parse of P1, which BT17 shows is identical to the v1 loaded P1.

## 1. Verdict summary

| ID | Verdict (Channel B) | Key evidence | Falsifier rc |
|---|---|---|---|
| BT1 | CONFIRMED (engine arithmetic only; the CME spec is Channel A's) | 1 pt x 1 contract = 5.00, -5.00 short, 10 pt = 50.00 | 1 (POINT_VALUE 50) |
| BT2 | CONFIRMED (engine arithmetic only) | 0.25 pt = 1.25; slippage 1.25 + commission 1.00 = 2.25/side | 1 (TICK 0.50) |
| BT3 | pending (N/A by construction until split; needs the published fee schedule + a NinjaTrader account) | engine uses COMMISSION_PER_SIDE = 1.0 (BT2 output) | - |
| BT4 | CONFIRMED (P1 property) + observation O1 | 0 bars in (16:00,17:00], 0 Saturday, 0 Sunday <= 17:00, 0 Friday > 16:00 | 1 / 1 (pinned) |
| BT5 | pending (needs a NinjaTrader Strategy Analyzer run) | - | - |
| BT6 | CONFIRMED (P1 property), **low-power probe** (finding F4) | max roll-window jump 47.25 pt < 177.38 pt; all 8,569,564 OHLC on the 0.25 grid | 1 / 1 (pinned) |
| BT7 | CONFIRMED | hand fixtures exact; no look-ahead over 57 cut points | 1 / 1 |
| BT8 | CONFIRMED (pre-registered probes), **with boundary deviation F3** | flip = 2 sides, hold = 0, 0x/1x/2x linear; the last-bar execution is not charged | 1 |
| BT9 | CONFIRMED (estimator); the "iid assumption" half is UNVERIFIABLE at runtime | hand fixture 17.959955456515 (1e-12); 200 numpy series; scale invariance | 1 / 1 |
| BT10 | CONFIRMED | PSR(SR*=SR)=0.5; monotone in n; 5 numeric fixtures vs the ledger formula (1e-12); non-excess kurtosis | 1 |
| BT11 | CONFIRMED (properties; the paper example is not available = UNVERIFIABLE) + finding F2 | DSR <= PSR(0); non-increasing in N; DSR = PSR(0) at V = 0; SR0 = formula (5e-14) | 1 / 1 |
| BT12 | CONFIRMED | 6 hand fixtures + 300 random vs own loop; monotone up = 0 | 1 |
| BT13 | CONFIRMED (generated parity rules.yaml <-> QS_*.cs only; the ORIG half is Channel A's) | 25/25 modules: long/short atoms, frame, wiring, exclusivity | 1 / 1 |
| BT14 | CONFIRMED (PROTOCOL 3 as frozen, pre-A1) | 25 fixture checks; own D + 15m frames == qibt frames on all of P1 | 1 / 1 |
| BT15 | pending (Strategy Analyzer part); compile part rc=0 | 52 sources (25 QS + 27 QI) compile | 1 (CS0103) |
| BT16 | CONFIRMED (static part); playback part pending | 100 order calls in 25 files, all inside ApplyRule with the guard as its first statement; default true | 1 / 1 |
| BT17 | **REFUTED** | gap 2023-04-05 -> 2023-04-17 = 7 missing weekdays (> 3). Coverage and no-duplicates hold. | control passes; dup falsifier 1 |
| BT18 | CONFIRMED | 3 CLI runs (2 cache, 1 raw re-read, random hash seeds): byte-identical CSVs; == committed results | 1 (1e-6 noise) |

Counts: CONFIRMED 14 (BT1, BT2, BT4, BT6, BT7, BT8, BT9, BT10, BT11, BT12, BT13, BT14, BT16, BT18).
REFUTED 1 (BT17). Pending 3 (BT3, BT5, BT15). PROBE_INVALID 0 in the final record. One
intermediate BT18 falsifier was invalid and was fixed (section 2, BT18).

### Findings for the owner (Channel B view)

- **F1 - BT17 refuted (data hole).** No 1-minute bar exists in any of the six raw files between
  2023-04-05 13:03 and 2023-04-16 17:01. Trading dates 2023-04-06, 04-07 and 04-10..04-14 are
  missing (7 weekdays), inside the evaluation window (H1). Also: weekdays 2023-02-01, 2024-03-01
  and 2025-04-01 are missing at file boundaries. Six sessions hold a single bar (the 16:00 bar):
  2020-01-03, 2021-02-02, 2022-02-01, 2023-02-02, 2024-03-04, 2025-04-02. These become degenerate
  one-minute "daily" bars in the D frame. Sessions are truncated on 2021-02-01 (ends 11:59),
  2023-04-05 (13:03) and 2026-02-24 (14:53).
- **F2 - PROTOCOL 8 tie-break is a no-op in floating point. Ranks 3 and 4 are swapped relative to
  the letter of the protocol.** ConsecDays (SR 0.568885) and IBS (SR 0.565508) are a tie
  (|dSR| = 0.003377 < 0.005), so DSR must decide. The true values are DSR(IBS) = 3.28e-58 and
  DSR(ConsecDays) = 1.71e-59 (z = -16.04 vs -16.22, scipy `norm.cdf`). My own erfc implementation
  agrees: 3.2798e-58 vs 1.7082e-59 (pinned XCHECK block). `statistics.NormalDist().cdf` returns exactly 0.0 for z <= -8.26, so every committed DSR
  is 0.0, and the order falls through to "A->Z". The committed order is ConsecDays 3, IBS 4. By
  "higher DSR, then module name" it should be IBS 3, ConsecDays 4. This decides the
  `QI_03_` / `QI_04_` relabel. Whether 1e-58 vs 1e-59 should count as a tie needs a dated amendment;
  the frozen text does not say. Root cause of the degenerate DSR: SR0 = 0.469 per day (about 7.4
  annualised), because V[SR] = 0.0552 is dominated by the 15m rules (per-day SR down to -0.68).
- **F3 - BT8 boundary.** The protocol executes p_{n-2} at the open of the last bar (PROTOCOL 4), and
  PROTOCOL 5 charges every change. The engine does not charge that final execution (supplementary
  probe rc=1). On P1 this omits one side (USD 2.25) for IBS, RSI2 and TurnaroundTuesday (D, on
  2026-02-24) and for OrderFlowPlus (15m). SR changes by at most 2.8e-4 at 1x (1.1e-3 at 2x). No
  rank changes.
- **F4 - BT6 probe power.** The pre-registered threshold 3 x median daily range is 177.38 points. A
  synthetic 0.3 % ratio splice makes a 14.45-point jump on the roll date, and that splice passes the
  pre-registered check (pinned BT6 falsifier B). Only the supplementary tick-grid check catches it.
  The supplementary evidence shows no splice jump at any roll date: roll-date session-open gaps
  are at most 9.5 points (2023-06-08 is 0.25), and all 8,569,564 OHLC prices are on the 0.25 grid.
  That is consistent with an additive back-adjustment, and it rules out an unrounded ratio
  adjustment. It cannot tell an additive adjustment from a rounded ratio adjustment. The
  pre-registered probe on its own could not see a realistic calendar-spread jump.
- **O1 - BT4 observation.** From 2020-01 to 2021-06, P1 has almost no bars closing 15:16-15:30
  CT. The share of weekdays with >= 15 such bars is 0.00 in every month, except 2020-10 (0.18) and
  2021-06 (0.14). From 2021-07 on it is 0.88-1.00 every month (pinned BT4 block; the lowest is 2026-02, a partial month). So the data
  shows a second daily pause (15:15-15:30 CT) in the first ~6 months of the evaluation window.
  Channel A should check whether the BT4 hours statement covers 2020 to mid-2021.

## 2. Per-claim records

### BT1 - MES = USD 5 x index (runtime part: engine arithmetic)
Verdict: **CONFIRMED** (Channel B part). The CME specification itself is Channel A's.
Probe and output (`bt01_02_contract_arith.py`, prints BT1 and BT2):
```text
$ python -I -B validation/probes/channel_b_backtest/bt01_02_contract_arith.py
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
=== BT1 1 point x 1 contract = USD 5.00 ===
[PASS] long +1 point: gross of bar 1 == 5.00 exactly | gross=[0.0, 5.0, 0.0, 0.0]
[PASS] long: no other bar carries P&L
[PASS] short +1 point: gross of bar 1 == -5.00 exactly | gross=[0.0, -5.0, 0.0, 0.0]
[PASS] run_positions: daily gross == [0, 5, 0, 0] | daily gross=[0.0, 5.0, 0.0, 0.0]
[PASS] 10 points = 50.00 | gross=np.float64(50.0)
--- BT1 1 point x 1 contract = USD 5.00: 5 checks, 0 failed
=== BT2 1 tick (0.25 pt) = USD 1.25; 1-tick slippage = USD 1.25 ===
[PASS] 1-tick move on 1 contract == 1.25 exactly | gross=np.float64(1.25)
[PASS] cost model: slippage per side == 1.25 | SLIPPAGE_PER_SIDE=1.25
[PASS] one executed side costs 1.00 + 1.25 = 2.25 | cost(1 side)=2.25
[PASS] one side minus the USD 1.00 commission == 1.25 slippage | commission=1.0
--- BT2 1 tick (0.25 pt) = USD 1.25; 1-tick slippage = USD 1.25: 4 checks, 0 failed
rc=0  wall=1.34s
```
Falsifier (POINT_VALUE 5.0 -> 50.0), with sha256 of engine.py before and after:
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt1_pv50 engine.py POINT_VALUE = 5.0  POINT_VALUE = 50.0 
mutant: %SCRATCH%\mut_bt1_pv50\qibt\engine.py
  - POINT_VALUE = 5.0
  + POINT_VALUE = 50.0
sha256 original engine.py before 10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 original engine.py after  10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 mutant   engine.py        80afec884b19a74f40aa204382846b4883eedfbfe373089cb4ab17188d24d0f9
rc=0  wall=0.18s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt01_02_contract_arith.py --only BT1 --qibt-root %SCRATCH%\mut_bt1_pv50
qibt loaded from: %SCRATCH%\mut_bt1_pv50\qibt\__init__.py
=== BT1 1 point x 1 contract = USD 5.00 ===
[FAIL] long +1 point: gross of bar 1 == 5.00 exactly | gross=[0.0, 50.0, 0.0, 0.0]
[PASS] long: no other bar carries P&L
[FAIL] short +1 point: gross of bar 1 == -5.00 exactly | gross=[0.0, -50.0, 0.0, 0.0]
[FAIL] run_positions: daily gross == [0, 5, 0, 0] | daily gross=[0.0, 50.0, 0.0, 0.0]
[FAIL] 10 points = 50.00 | gross=np.float64(500.0)
--- BT1 1 point x 1 contract = USD 5.00: 5 checks, 4 failed: long +1 point: gross of bar 1 == 5.00 exactly; short +1 point: gross of bar 1 == -5.00 exactly; run_positions: daily gross == [0, 5, 0, 0]; 10 points = 50.00
rc=1  wall=1.45s
```

### BT2 - tick 0.25 = USD 1.25 (runtime part)
Verdict: **CONFIRMED** (Channel B part). Probe output: the BT2 block above.
Falsifier (TICK_SIZE 0.25 -> 0.50):
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt2_tick engine.py TICK_SIZE = 0.25  TICK_SIZE = 0.50 
mutant: %SCRATCH%\mut_bt2_tick\qibt\engine.py
  - TICK_SIZE = 0.25
  + TICK_SIZE = 0.50
sha256 original engine.py before 10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 original engine.py after  10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 mutant   engine.py        16158962d5f9d3b3a71bb2b9875cdd4dc86ed4b9ec1ae7179da46918b90075d3
rc=0  wall=0.22s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt01_02_contract_arith.py --only BT2 --qibt-root %SCRATCH%\mut_bt2_tick
qibt loaded from: %SCRATCH%\mut_bt2_tick\qibt\__init__.py
=== BT2 1 tick (0.25 pt) = USD 1.25; 1-tick slippage = USD 1.25 ===
[PASS] 1-tick move on 1 contract == 1.25 exactly | gross=np.float64(1.25)
[FAIL] cost model: slippage per side == 1.25 | SLIPPAGE_PER_SIDE=2.5
[FAIL] one executed side costs 1.00 + 1.25 = 2.25 | cost(1 side)=3.5
[FAIL] one side minus the USD 1.00 commission == 1.25 slippage | commission=1.0
--- BT2 1 tick (0.25 pt) = USD 1.25; 1-tick slippage = USD 1.25: 4 checks, 3 failed: cost model: slippage per side == 1.25; one executed side costs 1.00 + 1.25 = 2.25; one side minus the USD 1.00 commission == 1.25 slippage
rc=1  wall=1.41s
```

### BT3 - USD 1.00/side covers commission + exchange + NFA
Verdict: **pending**. The ledger marks it N/A by construction until the cost is split. It needs the
published NinjaTrader commission, CME and NFA fees, which are outside the Channel B charter, and a
NinjaTrader account check. Runtime fact recorded: `engine.COMMISSION_PER_SIDE == 1.0` (BT2 block above).

### BT4 - Globex hours, daily 16:00-17:00 CT halt (runtime part: a P1 property)
Verdict: **CONFIRMED** for the pre-registered P1 property. See observation O1 above.
Probe (v1 code and v1 cache, from the main run):
```text
$ python -I -B validation/probes/channel_b_backtest/bt04_session_halt.py
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
source: qibt.data.load_p1() cache=hit, 2142391 bars
=== BT4 P1 session / halt property ===
[PASS] session builder (qibt.data.build_frames) runs on P1 | 1m 2142391 bars, D 1578 dates, 15m 143136 bars
[PASS] no bar closes in (16:00, 17:00] CT | bars in halt=0
[PASS] no bar on Saturday | Saturday bars=0
[PASS] no Sunday bar closing at or before 17:00 | count=0
[PASS] no Friday bar closing after 16:00 | count=0
[PASS] builder TradingDate == own PROTOCOL-3 rule on every bar | mismatches=0
OBSERVATION: distinct close minutes-of-day present: 1380 of 1440; minutes 16:01..17:00 present: 0
OBSERVATION bars per close minute, years 2020..2026:
  15:14 [246, 249, 249, 239, 247, 245, 35]
  15:15 [246, 249, 249, 239, 247, 245, 35]
  15:16 [8, 131, 249, 239, 247, 245, 35]
  15:17 [4, 130, 249, 239, 247, 245, 35]
  15:18 [4, 130, 249, 239, 247, 245, 35]
  15:19 [4, 130, 249, 239, 246, 245, 35]
  15:20 [4, 129, 249, 239, 246, 245, 35]
  15:21 [4, 130, 249, 239, 246, 245, 35]
  15:22 [6, 130, 249, 239, 246, 245, 35]
  15:23 [6, 130, 249, 239, 246, 245, 35]
  15:24 [6, 130, 249, 239, 246, 245, 35]
  15:25 [6, 130, 249, 239, 246, 245, 35]
  15:26 [6, 130, 249, 239, 246, 245, 35]
  15:27 [6, 130, 249, 239, 246, 245, 35]
  15:28 [6, 130, 249, 239, 247, 245, 35]
  15:29 [6, 130, 249, 239, 247, 245, 35]
  15:30 [6, 130, 249, 239, 247, 245, 35]
  15:31 [248, 249, 249, 239, 247, 245, 35]
--- BT4 P1 session / halt property: 6 checks, 0 failed
rc=0  wall=3.58s
```
Same probe, pinned to the sha256-verified v1 copy and the raw re-parse:
```text
$ python -I -B validation/probes/channel_b_backtest/bt04_session_halt.py --qibt-root %SCRATCH%\pristine_v1 --pkl %SCRATCH%\raw_p1.pkl
qibt loaded from: %SCRATCH%\pristine_v1\qibt\__init__.py
source: pickle %SCRATCH%\raw_p1.pkl, 2142391 bars
=== BT4 P1 session / halt property ===
[PASS] session builder (qibt.data.build_frames) runs on P1 | 1m 2142391 bars, D 1578 dates, 15m 143136 bars
[PASS] no bar closes in (16:00, 17:00] CT | bars in halt=0
[PASS] no bar on Saturday | Saturday bars=0
[PASS] no Sunday bar closing at or before 17:00 | count=0
[PASS] no Friday bar closing after 16:00 | count=0
[PASS] builder TradingDate == own PROTOCOL-3 rule on every bar | mismatches=0
OBSERVATION: distinct close minutes-of-day present: 1380 of 1440; minutes 16:01..17:00 present: 0
OBSERVATION bars per close minute, years 2020..2026:
  15:14 [246, 249, 249, 239, 247, 245, 35]
  15:15 [246, 249, 249, 239, 247, 245, 35]
  15:16 [8, 131, 249, 239, 247, 245, 35]
  15:17 [4, 130, 249, 239, 247, 245, 35]
  15:18 [4, 130, 249, 239, 247, 245, 35]
  15:19 [4, 130, 249, 239, 246, 245, 35]
  15:20 [4, 129, 249, 239, 246, 245, 35]
  15:21 [4, 130, 249, 239, 246, 245, 35]
  15:22 [6, 130, 249, 239, 246, 245, 35]
  15:23 [6, 130, 249, 239, 246, 245, 35]
  15:24 [6, 130, 249, 239, 246, 245, 35]
  15:25 [6, 130, 249, 239, 246, 245, 35]
  15:26 [6, 130, 249, 239, 246, 245, 35]
  15:27 [6, 130, 249, 239, 246, 245, 35]
  15:28 [6, 130, 249, 239, 247, 245, 35]
  15:29 [6, 130, 249, 239, 247, 245, 35]
  15:30 [6, 130, 249, 239, 247, 245, 35]
  15:31 [248, 249, 249, 239, 247, 245, 35]
OBSERVATION monthly share of weekdays with >= 15 bars closing 15:16..15:30 CT:
  2020-01:0.00 2020-02:0.00 2020-03:0.00 2020-04:0.00 2020-05:0.00 2020-06:0.00 2020-07:0.00 2020-08:0.00 2020-09:0.00 2020-10:0.18 2020-11:0.00 2020-12:0.00 2021-01:0.00 2021-02:0.00 2021-03:0.00 2021-04:0.00 2021-05:0.00 2021-06:0.14 2021-07:0.95 2021-08:1.00 2021-09:0.95 2021-10:1.00 2021-11:0.91 2021-12:0.95 2022-01:0.95 2022-02:0.95 2022-03:1.00 2022-04:1.00 2022-05:0.95 2022-06:0.95 2022-07:0.95 2022-08:1.00 2022-09:0.95 2022-10:1.00 2022-11:0.91 2022-12:1.00 2023-01:0.95 2023-02:0.94 2023-03:1.00 2023-04:0.92 2023-05:0.96 2023-06:0.95 2023-07:0.90 2023-08:1.00 2023-09:0.95 2023-10:1.00 2023-11:0.91 2023-12:1.00 2024-01:0.95 2024-02:0.90 2024-03:1.00 2024-04:1.00 2024-05:0.96 2024-06:0.95 2024-07:0.91 2024-08:1.00 2024-09:0.95 2024-10:1.00 2024-11:0.90 2024-12:0.95 2025-01:0.91 2025-02:0.95 2025-03:1.00 2025-04:1.00 2025-05:0.95 2025-06:0.95 2025-07:0.91 2025-08:1.00 2025-09:0.95 2025-10:1.00 2025-11:0.90 2025-12:0.95 2026-01:0.95 2026-02:0.88
--- BT4 P1 session / halt property: 6 checks, 0 failed
rc=0
```
Falsifiers (data mutations, pinned):
```text
$ python -I -B validation/probes/channel_b_backtest/bt04_session_halt.py --qibt-root %SCRATCH%\pristine_v1 --pkl %SCRATCH%\raw_p1.pkl --inject halt
qibt loaded from: %SCRATCH%\pristine_v1\qibt\__init__.py
source: pickle %SCRATCH%\raw_p1.pkl, 2142391 bars
INJECTED: bar at 2021-06-14 16:30:00
=== BT4 P1 session / halt property ===
[FAIL] session builder (qibt.data.build_frames) runs on P1 | SessionError: 1 bar(s) close inside the halt (16:00, 17:00], first: ['2021-06-14 16:30:00']
[FAIL] no bar closes in (16:00, 17:00] CT | bars in halt=1
[PASS] no bar on Saturday | Saturday bars=0
[PASS] no Sunday bar closing at or before 17:00 | count=0
[PASS] no Friday bar closing after 16:00 | count=0
OBSERVATION: distinct close minutes-of-day present: 1381 of 1440; minutes 16:01..17:00 present: 1
OBSERVATION bars per close minute, years 2020..2026:
  15:14 [246, 249, 249, 239, 247, 245, 35]
  15:15 [246, 249, 249, 239, 247, 245, 35]
  15:16 [8, 131, 249, 239, 247, 245, 35]
  15:17 [4, 130, 249, 239, 247, 245, 35]
  15:18 [4, 130, 249, 239, 247, 245, 35]
  15:19 [4, 130, 249, 239, 246, 245, 35]
  15:20 [4, 129, 249, 239, 246, 245, 35]
  15:21 [4, 130, 249, 239, 246, 245, 35]
  15:22 [6, 130, 249, 239, 246, 245, 35]
  15:23 [6, 130, 249, 239, 246, 245, 35]
  15:24 [6, 130, 249, 239, 246, 245, 35]
  15:25 [6, 130, 249, 239, 246, 245, 35]
  15:26 [6, 130, 249, 239, 246, 245, 35]
  15:27 [6, 130, 249, 239, 246, 245, 35]
  15:28 [6, 130, 249, 239, 247, 245, 35]
  15:29 [6, 130, 249, 239, 247, 245, 35]
  15:30 [6, 130, 249, 239, 247, 245, 35]
  15:31 [248, 249, 249, 239, 247, 245, 35]
OBSERVATION monthly share of weekdays with >= 15 bars closing 15:16..15:30 CT:
  2020-01:0.00 2020-02:0.00 2020-03:0.00 2020-04:0.00 2020-05:0.00 2020-06:0.00 2020-07:0.00 2020-08:0.00 2020-09:0.00 2020-10:0.18 2020-11:0.00 2020-12:0.00 2021-01:0.00 2021-02:0.00 2021-03:0.00 2021-04:0.00 2021-05:0.00 2021-06:0.14 2021-07:0.95 2021-08:1.00 2021-09:0.95 2021-10:1.00 2021-11:0.91 2021-12:0.95 2022-01:0.95 2022-02:0.95 2022-03:1.00 2022-04:1.00 2022-05:0.95 2022-06:0.95 2022-07:0.95 2022-08:1.00 2022-09:0.95 2022-10:1.00 2022-11:0.91 2022-12:1.00 2023-01:0.95 2023-02:0.94 2023-03:1.00 2023-04:0.92 2023-05:0.96 2023-06:0.95 2023-07:0.90 2023-08:1.00 2023-09:0.95 2023-10:1.00 2023-11:0.91 2023-12:1.00 2024-01:0.95 2024-02:0.90 2024-03:1.00 2024-04:1.00 2024-05:0.96 2024-06:0.95 2024-07:0.91 2024-08:1.00 2024-09:0.95 2024-10:1.00 2024-11:0.90 2024-12:0.95 2025-01:0.91 2025-02:0.95 2025-03:1.00 2025-04:1.00 2025-05:0.95 2025-06:0.95 2025-07:0.91 2025-08:1.00 2025-09:0.95 2025-10:1.00 2025-11:0.90 2025-12:0.95 2026-01:0.95 2026-02:0.88
--- BT4 P1 session / halt property: 5 checks, 2 failed: session builder (qibt.data.build_frames) runs on P1; no bar closes in (16:00, 17:00] CT
rc=1
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt04_session_halt.py --qibt-root %SCRATCH%\pristine_v1 --pkl %SCRATCH%\raw_p1.pkl --inject saturday
qibt loaded from: %SCRATCH%\pristine_v1\qibt\__init__.py
source: pickle %SCRATCH%\raw_p1.pkl, 2142391 bars
INJECTED: bar at 2021-06-19 10:00:00
=== BT4 P1 session / halt property ===
[PASS] session builder (qibt.data.build_frames) runs on P1 | 1m 2142392 bars, D 1579 dates, 15m 143137 bars
[PASS] no bar closes in (16:00, 17:00] CT | bars in halt=0
[FAIL] no bar on Saturday | Saturday bars=1
[PASS] no Sunday bar closing at or before 17:00 | count=0
[PASS] no Friday bar closing after 16:00 | count=0
[PASS] builder TradingDate == own PROTOCOL-3 rule on every bar | mismatches=0
OBSERVATION: distinct close minutes-of-day present: 1380 of 1440; minutes 16:01..17:00 present: 0
OBSERVATION bars per close minute, years 2020..2026:
  15:14 [246, 249, 249, 239, 247, 245, 35]
  15:15 [246, 249, 249, 239, 247, 245, 35]
  15:16 [8, 131, 249, 239, 247, 245, 35]
  15:17 [4, 130, 249, 239, 247, 245, 35]
  15:18 [4, 130, 249, 239, 247, 245, 35]
  15:19 [4, 130, 249, 239, 246, 245, 35]
  15:20 [4, 129, 249, 239, 246, 245, 35]
  15:21 [4, 130, 249, 239, 246, 245, 35]
  15:22 [6, 130, 249, 239, 246, 245, 35]
  15:23 [6, 130, 249, 239, 246, 245, 35]
  15:24 [6, 130, 249, 239, 246, 245, 35]
  15:25 [6, 130, 249, 239, 246, 245, 35]
  15:26 [6, 130, 249, 239, 246, 245, 35]
  15:27 [6, 130, 249, 239, 246, 245, 35]
  15:28 [6, 130, 249, 239, 247, 245, 35]
  15:29 [6, 130, 249, 239, 247, 245, 35]
  15:30 [6, 130, 249, 239, 247, 245, 35]
  15:31 [248, 249, 249, 239, 247, 245, 35]
OBSERVATION monthly share of weekdays with >= 15 bars closing 15:16..15:30 CT:
  2020-01:0.00 2020-02:0.00 2020-03:0.00 2020-04:0.00 2020-05:0.00 2020-06:0.00 2020-07:0.00 2020-08:0.00 2020-09:0.00 2020-10:0.18 2020-11:0.00 2020-12:0.00 2021-01:0.00 2021-02:0.00 2021-03:0.00 2021-04:0.00 2021-05:0.00 2021-06:0.14 2021-07:0.95 2021-08:1.00 2021-09:0.95 2021-10:1.00 2021-11:0.91 2021-12:0.95 2022-01:0.95 2022-02:0.95 2022-03:1.00 2022-04:1.00 2022-05:0.95 2022-06:0.95 2022-07:0.95 2022-08:1.00 2022-09:0.95 2022-10:1.00 2022-11:0.91 2022-12:1.00 2023-01:0.95 2023-02:0.94 2023-03:1.00 2023-04:0.92 2023-05:0.96 2023-06:0.95 2023-07:0.90 2023-08:1.00 2023-09:0.95 2023-10:1.00 2023-11:0.91 2023-12:1.00 2024-01:0.95 2024-02:0.90 2024-03:1.00 2024-04:1.00 2024-05:0.96 2024-06:0.95 2024-07:0.91 2024-08:1.00 2024-09:0.95 2024-10:1.00 2024-11:0.90 2024-12:0.95 2025-01:0.91 2025-02:0.95 2025-03:1.00 2025-04:1.00 2025-05:0.95 2025-06:0.95 2025-07:0.91 2025-08:1.00 2025-09:0.95 2025-10:1.00 2025-11:0.90 2025-12:0.95 2026-01:0.95 2026-02:0.88
--- BT4 P1 session / halt property: 6 checks, 1 failed: no bar on Saturday
rc=1
```

### BT5 - NT8 OnBarClose market order fills at the next bar's open
Verdict: **pending**. This needs a Strategy Analyzer run of one QS_* strategy compared with the
engine trade list (user-run). The engine side of the timing is BT7 (CONFIRMED).

### BT6 - additive back-adjustment (runtime part: no roll jump > 3 x median daily range on P1)
Verdict: **CONFIRMED** for the pre-registered P1 property. Read with finding F4 (low power).
Roll date R = third Friday - 8 calendar days. The window is R +- 3 calendar days. D bars come from
my own PROTOCOL 3 aggregation.
```text
$ python -I -B validation/probes/channel_b_backtest/bt06_roll_jumps.py
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
source: qibt.data.load_p1() cache=hit, 2142391 bars
D bars 1578; median daily range 59.12 pts; threshold 3x = 177.38 pts
=== BT6 roll-date jumps ===
  roll 2020-03-12: window dates ['2020-03-09', '2020-03-10', '2020-03-11', '2020-03-12', '2020-03-13']; max session-open gap 47.25 (on 2020-03-09, percentile 99.0 of all gaps); max 1-min step 47.25
  roll 2020-06-11: window dates ['2020-06-08', '2020-06-09', '2020-06-10', '2020-06-11', '2020-06-12']; max session-open gap 6.75 (on 2020-06-08, percentile 90.0 of all gaps); max 1-min step 6.75
  roll 2020-09-10: window dates ['2020-09-07', '2020-09-08', '2020-09-09', '2020-09-10', '2020-09-11']; max session-open gap 16.00 (on 2020-09-09, percentile 96.3 of all gaps); max 1-min step 16.00
  roll 2020-12-10: window dates ['2020-12-07', '2020-12-08', '2020-12-09', '2020-12-10', '2020-12-11']; max session-open gap 5.25 (on 2020-12-11, percentile 86.6 of all gaps); max 1-min step 5.25
  roll 2021-03-11: window dates ['2021-03-08', '2021-03-09', '2021-03-10', '2021-03-11', '2021-03-12']; max session-open gap 13.25 (on 2021-03-08, percentile 95.4 of all gaps); max 1-min step 13.25
  roll 2021-06-10: window dates ['2021-06-07', '2021-06-08', '2021-06-09', '2021-06-10', '2021-06-11']; max session-open gap 4.00 (on 2021-06-07, percentile 83.8 of all gaps); max 1-min step 4.00
  roll 2021-09-09: window dates ['2021-09-06', '2021-09-07', '2021-09-08', '2021-09-09', '2021-09-10']; max session-open gap 1.00 (on 2021-09-09, percentile 58.1 of all gaps); max 1-min step 1.75
  roll 2021-12-09: window dates ['2021-12-06', '2021-12-07', '2021-12-08', '2021-12-09', '2021-12-10']; max session-open gap 9.75 (on 2021-12-06, percentile 93.1 of all gaps); max 1-min step 9.75
  roll 2022-03-10: window dates ['2022-03-07', '2022-03-08', '2022-03-09', '2022-03-10', '2022-03-11']; max session-open gap 9.75 (on 2022-03-07, percentile 93.1 of all gaps); max 1-min step 9.75
  roll 2022-06-09: window dates ['2022-06-06', '2022-06-07', '2022-06-08', '2022-06-09', '2022-06-10']; max session-open gap 2.75 (on 2022-06-06, percentile 77.6 of all gaps); max 1-min step 2.75
  roll 2022-09-08: window dates ['2022-09-05', '2022-09-06', '2022-09-07', '2022-09-08', '2022-09-09']; max session-open gap 2.50 (on 2022-09-05, percentile 75.8 of all gaps); max 1-min step 2.50
  roll 2022-12-08: window dates ['2022-12-05', '2022-12-06', '2022-12-07', '2022-12-08', '2022-12-09']; max session-open gap 6.50 (on 2022-12-05, percentile 89.6 of all gaps); max 1-min step 9.75
  roll 2023-03-09: window dates ['2023-03-06', '2023-03-07', '2023-03-08', '2023-03-09', '2023-03-10']; max session-open gap 3.25 (on 2023-03-06, percentile 81.4 of all gaps); max 1-min step 7.25
  roll 2023-06-08: window dates ['2023-06-05', '2023-06-06', '2023-06-07', '2023-06-08', '2023-06-09']; max session-open gap 1.75 (on 2023-06-09, percentile 70.5 of all gaps); max 1-min step 1.75
  roll 2023-09-07: window dates ['2023-09-04', '2023-09-05', '2023-09-06', '2023-09-07', '2023-09-08']; max session-open gap 1.50 (on 2023-09-04, percentile 67.0 of all gaps); max 1-min step 1.50
  roll 2023-12-07: window dates ['2023-12-04', '2023-12-05', '2023-12-06', '2023-12-07', '2023-12-08']; max session-open gap 0.50 (on 2023-12-08, percentile 42.1 of all gaps); max 1-min step 0.75
  roll 2024-03-07: window dates ['2024-03-04', '2024-03-05', '2024-03-06', '2024-03-07', '2024-03-08']; max session-open gap 34.50 (on 2024-03-04, percentile 98.7 of all gaps); max 1-min step 34.50
  roll 2024-06-13: window dates ['2024-06-10', '2024-06-11', '2024-06-12', '2024-06-13', '2024-06-14']; max session-open gap 2.00 (on 2024-06-10, percentile 73.1 of all gaps); max 1-min step 2.00
  roll 2024-09-12: window dates ['2024-09-09', '2024-09-10', '2024-09-11', '2024-09-12', '2024-09-13']; max session-open gap 5.25 (on 2024-09-09, percentile 86.6 of all gaps); max 1-min step 5.25
  roll 2024-12-12: window dates ['2024-12-09', '2024-12-10', '2024-12-11', '2024-12-12', '2024-12-13']; max session-open gap 5.50 (on 2024-12-13, percentile 87.4 of all gaps); max 1-min step 5.50
  roll 2025-03-13: window dates ['2025-03-10', '2025-03-11', '2025-03-12', '2025-03-13', '2025-03-14']; max session-open gap 18.75 (on 2025-03-10, percentile 97.1 of all gaps); max 1-min step 18.75
  roll 2025-06-12: window dates ['2025-06-09', '2025-06-10', '2025-06-11', '2025-06-12', '2025-06-13']; max session-open gap 1.25 (on 2025-06-10, percentile 62.6 of all gaps); max 1-min step 1.75
  roll 2025-09-11: window dates ['2025-09-08', '2025-09-09', '2025-09-10', '2025-09-11', '2025-09-12']; max session-open gap 4.75 (on 2025-09-08, percentile 85.5 of all gaps); max 1-min step 4.75
  roll 2025-12-11: window dates ['2025-12-08', '2025-12-09', '2025-12-10', '2025-12-11', '2025-12-12']; max session-open gap 9.50 (on 2025-12-12, percentile 92.7 of all gaps); max 1-min step 9.50
[PASS] no roll-window jump > 3 x median daily range (177.38) | largest 47.25 (gap, roll 2020-03-12)
OBSERVATION top-8 session-open gaps in all of P1: [('2025-04-07', 90.0), ('2020-03-02', 84.75), ('2023-02-02', 82.5), ('2025-10-13', 80.75), ('2025-04-02', 66.25), ('2021-02-02', 61.5), ('2023-04-17', 61.0), ('2025-06-23', 60.75)]
OBSERVATION session-open gaps: median 0.75, p95 12.30, p99 45.54, max 90.00; roll-window maxima percentiles: median 86.6, max 99.0
OBSERVATION session-open gap on the roll date R (Thu) and R+1 (Fri) [date, points, percentile among all Tue-Fri gaps]: [('2020-03-12', 1.25, 71.6), ('2020-03-13', 8.75, 97.2), ('2020-06-11', 1.25, 71.6), ('2020-06-12', 2.75, 87.0), ('2020-09-10', 2.0, 83.0), ('2020-09-11', 6.25, 95.6), ('2020-12-10', 1.25, 71.6), ('2020-12-11', 5.25, 94.3), ('2021-03-11', 1.0, 66.9), ('2021-03-12', 0.5, 48.6), ('2021-06-10', 0.0, 15.4), ('2021-06-11', 0.75, 59.5), ('2021-09-09', 1.0, 66.9), ('2021-09-10', 0.5, 48.6), ('2021-12-09', 1.0, 66.9), ('2021-12-10', 0.25, 35.2), ('2022-03-10', 0.5, 48.6), ('2022-03-11', 1.5, 76.8), ('2022-06-09', 1.75, 80.1), ('2022-06-10', 1.0, 66.9), ('2022-09-08', 0.5, 48.6), ('2022-09-09', 0.25, 35.2), ('2022-12-08', 0.25, 35.2), ('2022-12-09', 0.25, 35.2), ('2023-03-09', 0.25, 35.2), ('2023-03-10', 0.25, 35.2), ('2023-06-08', 0.25, 35.2), ('2023-06-09', 1.75, 80.1), ('2023-09-07', 0.5, 48.6), ('2023-09-08', 0.5, 48.6), ('2023-12-07', 0.25, 35.2), ('2023-12-08', 0.5, 48.6), ('2024-03-07', 1.5, 76.8), ('2024-03-08', 0.75, 59.5), ('2024-06-13', 1.75, 80.1), ('2024-06-14', 0.0, 15.4), ('2024-09-12', 0.25, 35.2), ('2024-09-13', 0.25, 35.2), ('2024-12-12', 0.75, 59.5), ('2024-12-13', 5.5, 94.8), ('2025-03-13', 0.25, 35.2), ('2025-03-14', 1.5, 76.8), ('2025-06-12', 0.0, 15.4), ('2025-06-13', 1.25, 71.6), ('2025-09-11', 0.5, 48.6), ('2025-09-12', 3.0, 89.0), ('2025-12-11', 5.25, 94.3), ('2025-12-12', 9.5, 97.6)]
OBSERVATION Tue-Fri session-open gaps: median 0.75, p90 3.25, p99 16.35; share of Tue-Fri gaps >= 10 points: 2.30%
[PASS] supplementary: every OHLC price on the 0.25 tick grid | off-grid prices=0 of 8569564
--- BT6 roll-date jumps: 2 checks, 0 failed
rc=0  wall=1.78s
```
Pinned re-run and falsifiers. A: +236.50 pt before the 2023-06-08 roll, caught by the
pre-registered check. B: x1.003 ratio before that roll, missed by the pre-registered check and
caught by the grid check.
```text
$ python -I -B validation/probes/channel_b_backtest/bt06_roll_jumps.py --qibt-root %SCRATCH%\pristine_v1 --pkl %SCRATCH%\raw_p1.pkl
qibt loaded from: %SCRATCH%\pristine_v1\qibt\__init__.py
source: pickle %SCRATCH%\raw_p1.pkl, 2142391 bars
D bars 1578; median daily range 59.12 pts; threshold 3x = 177.38 pts
=== BT6 roll-date jumps ===
  roll 2020-03-12: window dates ['2020-03-09', '2020-03-10', '2020-03-11', '2020-03-12', '2020-03-13']; max session-open gap 47.25 (on 2020-03-09, percentile 99.0 of all gaps); max 1-min step 47.25
  roll 2020-06-11: window dates ['2020-06-08', '2020-06-09', '2020-06-10', '2020-06-11', '2020-06-12']; max session-open gap 6.75 (on 2020-06-08, percentile 90.0 of all gaps); max 1-min step 6.75
  roll 2020-09-10: window dates ['2020-09-07', '2020-09-08', '2020-09-09', '2020-09-10', '2020-09-11']; max session-open gap 16.00 (on 2020-09-09, percentile 96.3 of all gaps); max 1-min step 16.00
  roll 2020-12-10: window dates ['2020-12-07', '2020-12-08', '2020-12-09', '2020-12-10', '2020-12-11']; max session-open gap 5.25 (on 2020-12-11, percentile 86.6 of all gaps); max 1-min step 5.25
  roll 2021-03-11: window dates ['2021-03-08', '2021-03-09', '2021-03-10', '2021-03-11', '2021-03-12']; max session-open gap 13.25 (on 2021-03-08, percentile 95.4 of all gaps); max 1-min step 13.25
  roll 2021-06-10: window dates ['2021-06-07', '2021-06-08', '2021-06-09', '2021-06-10', '2021-06-11']; max session-open gap 4.00 (on 2021-06-07, percentile 83.8 of all gaps); max 1-min step 4.00
  roll 2021-09-09: window dates ['2021-09-06', '2021-09-07', '2021-09-08', '2021-09-09', '2021-09-10']; max session-open gap 1.00 (on 2021-09-09, percentile 58.1 of all gaps); max 1-min step 1.75
  roll 2021-12-09: window dates ['2021-12-06', '2021-12-07', '2021-12-08', '2021-12-09', '2021-12-10']; max session-open gap 9.75 (on 2021-12-06, percentile 93.1 of all gaps); max 1-min step 9.75
  roll 2022-03-10: window dates ['2022-03-07', '2022-03-08', '2022-03-09', '2022-03-10', '2022-03-11']; max session-open gap 9.75 (on 2022-03-07, percentile 93.1 of all gaps); max 1-min step 9.75
  roll 2022-06-09: window dates ['2022-06-06', '2022-06-07', '2022-06-08', '2022-06-09', '2022-06-10']; max session-open gap 2.75 (on 2022-06-06, percentile 77.6 of all gaps); max 1-min step 2.75
  roll 2022-09-08: window dates ['2022-09-05', '2022-09-06', '2022-09-07', '2022-09-08', '2022-09-09']; max session-open gap 2.50 (on 2022-09-05, percentile 75.8 of all gaps); max 1-min step 2.50
  roll 2022-12-08: window dates ['2022-12-05', '2022-12-06', '2022-12-07', '2022-12-08', '2022-12-09']; max session-open gap 6.50 (on 2022-12-05, percentile 89.6 of all gaps); max 1-min step 9.75
  roll 2023-03-09: window dates ['2023-03-06', '2023-03-07', '2023-03-08', '2023-03-09', '2023-03-10']; max session-open gap 3.25 (on 2023-03-06, percentile 81.4 of all gaps); max 1-min step 7.25
  roll 2023-06-08: window dates ['2023-06-05', '2023-06-06', '2023-06-07', '2023-06-08', '2023-06-09']; max session-open gap 1.75 (on 2023-06-09, percentile 70.5 of all gaps); max 1-min step 1.75
  roll 2023-09-07: window dates ['2023-09-04', '2023-09-05', '2023-09-06', '2023-09-07', '2023-09-08']; max session-open gap 1.50 (on 2023-09-04, percentile 67.0 of all gaps); max 1-min step 1.50
  roll 2023-12-07: window dates ['2023-12-04', '2023-12-05', '2023-12-06', '2023-12-07', '2023-12-08']; max session-open gap 0.50 (on 2023-12-08, percentile 42.1 of all gaps); max 1-min step 0.75
  roll 2024-03-07: window dates ['2024-03-04', '2024-03-05', '2024-03-06', '2024-03-07', '2024-03-08']; max session-open gap 34.50 (on 2024-03-04, percentile 98.7 of all gaps); max 1-min step 34.50
  roll 2024-06-13: window dates ['2024-06-10', '2024-06-11', '2024-06-12', '2024-06-13', '2024-06-14']; max session-open gap 2.00 (on 2024-06-10, percentile 73.1 of all gaps); max 1-min step 2.00
  roll 2024-09-12: window dates ['2024-09-09', '2024-09-10', '2024-09-11', '2024-09-12', '2024-09-13']; max session-open gap 5.25 (on 2024-09-09, percentile 86.6 of all gaps); max 1-min step 5.25
  roll 2024-12-12: window dates ['2024-12-09', '2024-12-10', '2024-12-11', '2024-12-12', '2024-12-13']; max session-open gap 5.50 (on 2024-12-13, percentile 87.4 of all gaps); max 1-min step 5.50
  roll 2025-03-13: window dates ['2025-03-10', '2025-03-11', '2025-03-12', '2025-03-13', '2025-03-14']; max session-open gap 18.75 (on 2025-03-10, percentile 97.1 of all gaps); max 1-min step 18.75
  roll 2025-06-12: window dates ['2025-06-09', '2025-06-10', '2025-06-11', '2025-06-12', '2025-06-13']; max session-open gap 1.25 (on 2025-06-10, percentile 62.6 of all gaps); max 1-min step 1.75
  roll 2025-09-11: window dates ['2025-09-08', '2025-09-09', '2025-09-10', '2025-09-11', '2025-09-12']; max session-open gap 4.75 (on 2025-09-08, percentile 85.5 of all gaps); max 1-min step 4.75
  roll 2025-12-11: window dates ['2025-12-08', '2025-12-09', '2025-12-10', '2025-12-11', '2025-12-12']; max session-open gap 9.50 (on 2025-12-12, percentile 92.7 of all gaps); max 1-min step 9.50
[PASS] no roll-window jump > 3 x median daily range (177.38) | largest 47.25 (gap, roll 2020-03-12)
OBSERVATION top-8 session-open gaps in all of P1: [('2025-04-07', 90.0), ('2020-03-02', 84.75), ('2023-02-02', 82.5), ('2025-10-13', 80.75), ('2025-04-02', 66.25), ('2021-02-02', 61.5), ('2023-04-17', 61.0), ('2025-06-23', 60.75)]
OBSERVATION session-open gaps: median 0.75, p95 12.30, p99 45.54, max 90.00; roll-window maxima percentiles: median 86.6, max 99.0
OBSERVATION session-open gap on the roll date R (Thu) and R+1 (Fri) [date, points, percentile among all Tue-Fri gaps]: [('2020-03-12', 1.25, 71.6), ('2020-03-13', 8.75, 97.2), ('2020-06-11', 1.25, 71.6), ('2020-06-12', 2.75, 87.0), ('2020-09-10', 2.0, 83.0), ('2020-09-11', 6.25, 95.6), ('2020-12-10', 1.25, 71.6), ('2020-12-11', 5.25, 94.3), ('2021-03-11', 1.0, 66.9), ('2021-03-12', 0.5, 48.6), ('2021-06-10', 0.0, 15.4), ('2021-06-11', 0.75, 59.5), ('2021-09-09', 1.0, 66.9), ('2021-09-10', 0.5, 48.6), ('2021-12-09', 1.0, 66.9), ('2021-12-10', 0.25, 35.2), ('2022-03-10', 0.5, 48.6), ('2022-03-11', 1.5, 76.8), ('2022-06-09', 1.75, 80.1), ('2022-06-10', 1.0, 66.9), ('2022-09-08', 0.5, 48.6), ('2022-09-09', 0.25, 35.2), ('2022-12-08', 0.25, 35.2), ('2022-12-09', 0.25, 35.2), ('2023-03-09', 0.25, 35.2), ('2023-03-10', 0.25, 35.2), ('2023-06-08', 0.25, 35.2), ('2023-06-09', 1.75, 80.1), ('2023-09-07', 0.5, 48.6), ('2023-09-08', 0.5, 48.6), ('2023-12-07', 0.25, 35.2), ('2023-12-08', 0.5, 48.6), ('2024-03-07', 1.5, 76.8), ('2024-03-08', 0.75, 59.5), ('2024-06-13', 1.75, 80.1), ('2024-06-14', 0.0, 15.4), ('2024-09-12', 0.25, 35.2), ('2024-09-13', 0.25, 35.2), ('2024-12-12', 0.75, 59.5), ('2024-12-13', 5.5, 94.8), ('2025-03-13', 0.25, 35.2), ('2025-03-14', 1.5, 76.8), ('2025-06-12', 0.0, 15.4), ('2025-06-13', 1.25, 71.6), ('2025-09-11', 0.5, 48.6), ('2025-09-12', 3.0, 89.0), ('2025-12-11', 5.25, 94.3), ('2025-12-12', 9.5, 97.6)]
OBSERVATION Tue-Fri session-open gaps: median 0.75, p90 3.25, p99 16.35; share of Tue-Fri gaps >= 10 points: 2.30%
[PASS] supplementary: every OHLC price on the 0.25 tick grid | off-grid prices=0 of 8569564
--- BT6 roll-date jumps: 2 checks, 0 failed
rc=0
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt06_roll_jumps.py --qibt-root %SCRATCH%\pristine_v1 --pkl %SCRATCH%\raw_p1.pkl --inject jump
qibt loaded from: %SCRATCH%\pristine_v1\qibt\__init__.py
source: pickle %SCRATCH%\raw_p1.pkl, 2142391 bars
INJECTED: +236.50 points on every price before 2023-06-08 (1189244 bars)
D bars 1578; median daily range 59.12 pts; threshold 3x = 177.38 pts
=== BT6 roll-date jumps ===
  roll 2020-03-12: window dates ['2020-03-09', '2020-03-10', '2020-03-11', '2020-03-12', '2020-03-13']; max session-open gap 47.25 (on 2020-03-09, percentile 99.0 of all gaps); max 1-min step 47.25
  roll 2020-06-11: window dates ['2020-06-08', '2020-06-09', '2020-06-10', '2020-06-11', '2020-06-12']; max session-open gap 6.75 (on 2020-06-08, percentile 90.0 of all gaps); max 1-min step 6.75
  roll 2020-09-10: window dates ['2020-09-07', '2020-09-08', '2020-09-09', '2020-09-10', '2020-09-11']; max session-open gap 16.00 (on 2020-09-09, percentile 96.3 of all gaps); max 1-min step 16.00
  roll 2020-12-10: window dates ['2020-12-07', '2020-12-08', '2020-12-09', '2020-12-10', '2020-12-11']; max session-open gap 5.25 (on 2020-12-11, percentile 86.6 of all gaps); max 1-min step 5.25
  roll 2021-03-11: window dates ['2021-03-08', '2021-03-09', '2021-03-10', '2021-03-11', '2021-03-12']; max session-open gap 13.25 (on 2021-03-08, percentile 95.4 of all gaps); max 1-min step 13.25
  roll 2021-06-10: window dates ['2021-06-07', '2021-06-08', '2021-06-09', '2021-06-10', '2021-06-11']; max session-open gap 4.00 (on 2021-06-07, percentile 83.8 of all gaps); max 1-min step 4.00
  roll 2021-09-09: window dates ['2021-09-06', '2021-09-07', '2021-09-08', '2021-09-09', '2021-09-10']; max session-open gap 1.00 (on 2021-09-09, percentile 58.1 of all gaps); max 1-min step 1.75
  roll 2021-12-09: window dates ['2021-12-06', '2021-12-07', '2021-12-08', '2021-12-09', '2021-12-10']; max session-open gap 9.75 (on 2021-12-06, percentile 93.0 of all gaps); max 1-min step 9.75
  roll 2022-03-10: window dates ['2022-03-07', '2022-03-08', '2022-03-09', '2022-03-10', '2022-03-11']; max session-open gap 9.75 (on 2022-03-07, percentile 93.0 of all gaps); max 1-min step 9.75
  roll 2022-06-09: window dates ['2022-06-06', '2022-06-07', '2022-06-08', '2022-06-09', '2022-06-10']; max session-open gap 2.75 (on 2022-06-06, percentile 77.5 of all gaps); max 1-min step 2.75
  roll 2022-09-08: window dates ['2022-09-05', '2022-09-06', '2022-09-07', '2022-09-08', '2022-09-09']; max session-open gap 2.50 (on 2022-09-05, percentile 75.8 of all gaps); max 1-min step 2.50
  roll 2022-12-08: window dates ['2022-12-05', '2022-12-06', '2022-12-07', '2022-12-08', '2022-12-09']; max session-open gap 6.50 (on 2022-12-05, percentile 89.5 of all gaps); max 1-min step 9.75
  roll 2023-03-09: window dates ['2023-03-06', '2023-03-07', '2023-03-08', '2023-03-09', '2023-03-10']; max session-open gap 3.25 (on 2023-03-06, percentile 81.4 of all gaps); max 1-min step 7.25
  roll 2023-06-08: window dates ['2023-06-05', '2023-06-06', '2023-06-07', '2023-06-08', '2023-06-09']; max session-open gap 236.25 (on 2023-06-08, percentile 100.0 of all gaps); max 1-min step 236.25
  roll 2023-09-07: window dates ['2023-09-04', '2023-09-05', '2023-09-06', '2023-09-07', '2023-09-08']; max session-open gap 1.50 (on 2023-09-04, percentile 66.9 of all gaps); max 1-min step 1.50
  roll 2023-12-07: window dates ['2023-12-04', '2023-12-05', '2023-12-06', '2023-12-07', '2023-12-08']; max session-open gap 0.50 (on 2023-12-08, percentile 42.0 of all gaps); max 1-min step 0.75
  roll 2024-03-07: window dates ['2024-03-04', '2024-03-05', '2024-03-06', '2024-03-07', '2024-03-08']; max session-open gap 34.50 (on 2024-03-04, percentile 98.7 of all gaps); max 1-min step 34.50
  roll 2024-06-13: window dates ['2024-06-10', '2024-06-11', '2024-06-12', '2024-06-13', '2024-06-14']; max session-open gap 2.00 (on 2024-06-10, percentile 73.0 of all gaps); max 1-min step 2.00
  roll 2024-09-12: window dates ['2024-09-09', '2024-09-10', '2024-09-11', '2024-09-12', '2024-09-13']; max session-open gap 5.25 (on 2024-09-09, percentile 86.6 of all gaps); max 1-min step 5.25
  roll 2024-12-12: window dates ['2024-12-09', '2024-12-10', '2024-12-11', '2024-12-12', '2024-12-13']; max session-open gap 5.50 (on 2024-12-13, percentile 87.4 of all gaps); max 1-min step 5.50
  roll 2025-03-13: window dates ['2025-03-10', '2025-03-11', '2025-03-12', '2025-03-13', '2025-03-14']; max session-open gap 18.75 (on 2025-03-10, percentile 97.0 of all gaps); max 1-min step 18.75
  roll 2025-06-12: window dates ['2025-06-09', '2025-06-10', '2025-06-11', '2025-06-12', '2025-06-13']; max session-open gap 1.25 (on 2025-06-10, percentile 62.5 of all gaps); max 1-min step 1.75
  roll 2025-09-11: window dates ['2025-09-08', '2025-09-09', '2025-09-10', '2025-09-11', '2025-09-12']; max session-open gap 4.75 (on 2025-09-08, percentile 85.4 of all gaps); max 1-min step 4.75
  roll 2025-12-11: window dates ['2025-12-08', '2025-12-09', '2025-12-10', '2025-12-11', '2025-12-12']; max session-open gap 9.50 (on 2025-12-12, percentile 92.6 of all gaps); max 1-min step 9.50
[FAIL] no roll-window jump > 3 x median daily range (177.38) | largest 236.25 (gap, roll 2023-06-08)
OBSERVATION top-8 session-open gaps in all of P1: [('2023-06-08', 236.25), ('2025-04-07', 90.0), ('2020-03-02', 84.75), ('2023-02-02', 82.5), ('2025-10-13', 80.75), ('2025-04-02', 66.25), ('2021-02-02', 61.5), ('2023-04-17', 61.0)]
OBSERVATION session-open gaps: median 0.75, p95 12.50, p99 47.85, max 236.25; roll-window maxima percentiles: median 87.0, max 100.0
OBSERVATION session-open gap on the roll date R (Thu) and R+1 (Fri) [date, points, percentile among all Tue-Fri gaps]: [('2020-03-12', 1.25, 71.5), ('2020-03-13', 8.75, 97.1), ('2020-06-11', 1.25, 71.5), ('2020-06-12', 2.75, 86.9), ('2020-09-10', 2.0, 82.9), ('2020-09-11', 6.25, 95.5), ('2020-12-10', 1.25, 71.5), ('2020-12-11', 5.25, 94.2), ('2021-03-11', 1.0, 66.8), ('2021-03-12', 0.5, 48.5), ('2021-06-10', 0.0, 15.4), ('2021-06-11', 0.75, 59.4), ('2021-09-09', 1.0, 66.8), ('2021-09-10', 0.5, 48.5), ('2021-12-09', 1.0, 66.8), ('2021-12-10', 0.25, 35.1), ('2022-03-10', 0.5, 48.5), ('2022-03-11', 1.5, 76.7), ('2022-06-09', 1.75, 80.0), ('2022-06-10', 1.0, 66.8), ('2022-09-08', 0.5, 48.5), ('2022-09-09', 0.25, 35.1), ('2022-12-08', 0.25, 35.1), ('2022-12-09', 0.25, 35.1), ('2023-03-09', 0.25, 35.1), ('2023-03-10', 0.25, 35.1), ('2023-06-08', 236.25, 100.0), ('2023-06-09', 1.75, 80.0), ('2023-09-07', 0.5, 48.5), ('2023-09-08', 0.5, 48.5), ('2023-12-07', 0.25, 35.1), ('2023-12-08', 0.5, 48.5), ('2024-03-07', 1.5, 76.7), ('2024-03-08', 0.75, 59.4), ('2024-06-13', 1.75, 80.0), ('2024-06-14', 0.0, 15.4), ('2024-09-12', 0.25, 35.1), ('2024-09-13', 0.25, 35.1), ('2024-12-12', 0.75, 59.4), ('2024-12-13', 5.5, 94.7), ('2025-03-13', 0.25, 35.1), ('2025-03-14', 1.5, 76.7), ('2025-06-12', 0.0, 15.4), ('2025-06-13', 1.25, 71.5), ('2025-09-11', 0.5, 48.5), ('2025-09-12', 3.0, 88.9), ('2025-12-11', 5.25, 94.2), ('2025-12-12', 9.5, 97.5)]
OBSERVATION Tue-Fri session-open gaps: median 0.75, p90 3.25, p99 16.90; share of Tue-Fri gaps >= 10 points: 2.38%
[PASS] supplementary: every OHLC price on the 0.25 tick grid | off-grid prices=0 of 8569564
--- BT6 roll-date jumps: 2 checks, 1 failed: no roll-window jump > 3 x median daily range (177.38)
rc=1
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt06_roll_jumps.py --qibt-root %SCRATCH%\pristine_v1 --pkl %SCRATCH%\raw_p1.pkl --inject ratio
qibt loaded from: %SCRATCH%\pristine_v1\qibt\__init__.py
source: pickle %SCRATCH%\raw_p1.pkl, 2142391 bars
INJECTED: prices before 2023-06-08 x 1.003 (1189244 bars)
D bars 1578; median daily range 59.12 pts; threshold 3x = 177.38 pts
=== BT6 roll-date jumps ===
  roll 2020-03-12: window dates ['2020-03-09', '2020-03-10', '2020-03-11', '2020-03-12', '2020-03-13']; max session-open gap 47.39 (on 2020-03-09, percentile 99.0 of all gaps); max 1-min step 47.39
  roll 2020-06-11: window dates ['2020-06-08', '2020-06-09', '2020-06-10', '2020-06-11', '2020-06-12']; max session-open gap 6.77 (on 2020-06-08, percentile 89.9 of all gaps); max 1-min step 6.77
  roll 2020-09-10: window dates ['2020-09-07', '2020-09-08', '2020-09-09', '2020-09-10', '2020-09-11']; max session-open gap 16.05 (on 2020-09-09, percentile 96.3 of all gaps); max 1-min step 16.05
  roll 2020-12-10: window dates ['2020-12-07', '2020-12-08', '2020-12-09', '2020-12-10', '2020-12-11']; max session-open gap 5.27 (on 2020-12-11, percentile 86.4 of all gaps); max 1-min step 5.27
  roll 2021-03-11: window dates ['2021-03-08', '2021-03-09', '2021-03-10', '2021-03-11', '2021-03-12']; max session-open gap 13.29 (on 2021-03-08, percentile 95.4 of all gaps); max 1-min step 13.29
  roll 2021-06-10: window dates ['2021-06-07', '2021-06-08', '2021-06-09', '2021-06-10', '2021-06-11']; max session-open gap 4.01 (on 2021-06-07, percentile 83.6 of all gaps); max 1-min step 4.01
  roll 2021-09-09: window dates ['2021-09-06', '2021-09-07', '2021-09-08', '2021-09-09', '2021-09-10']; max session-open gap 1.00 (on 2021-09-09, percentile 57.0 of all gaps); max 1-min step 1.76
  roll 2021-12-09: window dates ['2021-12-06', '2021-12-07', '2021-12-08', '2021-12-09', '2021-12-10']; max session-open gap 9.78 (on 2021-12-06, percentile 93.0 of all gaps); max 1-min step 9.78
  roll 2022-03-10: window dates ['2022-03-07', '2022-03-08', '2022-03-09', '2022-03-10', '2022-03-11']; max session-open gap 9.78 (on 2022-03-07, percentile 93.0 of all gaps); max 1-min step 9.78
  roll 2022-06-09: window dates ['2022-06-06', '2022-06-07', '2022-06-08', '2022-06-09', '2022-06-10']; max session-open gap 2.76 (on 2022-06-06, percentile 77.2 of all gaps); max 1-min step 2.76
  roll 2022-09-08: window dates ['2022-09-05', '2022-09-06', '2022-09-07', '2022-09-08', '2022-09-09']; max session-open gap 2.51 (on 2022-09-05, percentile 75.4 of all gaps); max 1-min step 2.51
  roll 2022-12-08: window dates ['2022-12-05', '2022-12-06', '2022-12-07', '2022-12-08', '2022-12-09']; max session-open gap 6.52 (on 2022-12-05, percentile 89.5 of all gaps); max 1-min step 9.78
  roll 2023-03-09: window dates ['2023-03-06', '2023-03-07', '2023-03-08', '2023-03-09', '2023-03-10']; max session-open gap 3.26 (on 2023-03-06, percentile 81.4 of all gaps); max 1-min step 7.27
  roll 2023-06-08: window dates ['2023-06-05', '2023-06-06', '2023-06-07', '2023-06-08', '2023-06-09']; max session-open gap 14.45 (on 2023-06-08, percentile 95.8 of all gaps); max 1-min step 14.45
  roll 2023-09-07: window dates ['2023-09-04', '2023-09-05', '2023-09-06', '2023-09-07', '2023-09-08']; max session-open gap 1.50 (on 2023-09-04, percentile 64.0 of all gaps); max 1-min step 1.50
  roll 2023-12-07: window dates ['2023-12-04', '2023-12-05', '2023-12-06', '2023-12-07', '2023-12-08']; max session-open gap 0.50 (on 2023-12-08, percentile 35.4 of all gaps); max 1-min step 0.75
  roll 2024-03-07: window dates ['2024-03-04', '2024-03-05', '2024-03-06', '2024-03-07', '2024-03-08']; max session-open gap 34.50 (on 2024-03-04, percentile 98.7 of all gaps); max 1-min step 34.50
  roll 2024-06-13: window dates ['2024-06-10', '2024-06-11', '2024-06-12', '2024-06-13', '2024-06-14']; max session-open gap 2.00 (on 2024-06-10, percentile 71.0 of all gaps); max 1-min step 2.00
  roll 2024-09-12: window dates ['2024-09-09', '2024-09-10', '2024-09-11', '2024-09-12', '2024-09-13']; max session-open gap 5.25 (on 2024-09-09, percentile 86.4 of all gaps); max 1-min step 5.25
  roll 2024-12-12: window dates ['2024-12-09', '2024-12-10', '2024-12-11', '2024-12-12', '2024-12-13']; max session-open gap 5.50 (on 2024-12-13, percentile 87.1 of all gaps); max 1-min step 5.50
  roll 2025-03-13: window dates ['2025-03-10', '2025-03-11', '2025-03-12', '2025-03-13', '2025-03-14']; max session-open gap 18.75 (on 2025-03-10, percentile 97.0 of all gaps); max 1-min step 18.75
  roll 2025-06-12: window dates ['2025-06-09', '2025-06-10', '2025-06-11', '2025-06-12', '2025-06-13']; max session-open gap 1.25 (on 2025-06-10, percentile 60.0 of all gaps); max 1-min step 1.75
  roll 2025-09-11: window dates ['2025-09-08', '2025-09-09', '2025-09-10', '2025-09-11', '2025-09-12']; max session-open gap 4.75 (on 2025-09-08, percentile 85.2 of all gaps); max 1-min step 4.75
  roll 2025-12-11: window dates ['2025-12-08', '2025-12-09', '2025-12-10', '2025-12-11', '2025-12-12']; max session-open gap 9.50 (on 2025-12-12, percentile 92.4 of all gaps); max 1-min step 9.50
[PASS] no roll-window jump > 3 x median daily range (177.38) | largest 47.39 (gap, roll 2020-03-12)
OBSERVATION top-8 session-open gaps in all of P1: [('2025-04-07', 90.0), ('2020-03-02', 85.0), ('2023-02-02', 82.75), ('2025-10-13', 80.75), ('2025-04-02', 66.25), ('2021-02-02', 61.68), ('2023-04-17', 61.18), ('2025-06-23', 60.75)]
OBSERVATION session-open gaps: median 0.75, p95 12.51, p99 45.68, max 90.00; roll-window maxima percentiles: median 86.8, max 99.0
OBSERVATION session-open gap on the roll date R (Thu) and R+1 (Fri) [date, points, percentile among all Tue-Fri gaps]: [('2020-03-12', 1.25, 71.2), ('2020-03-13', 8.78, 97.1), ('2020-06-11', 1.25, 71.2), ('2020-06-12', 2.76, 86.7), ('2020-09-10', 2.01, 81.6), ('2020-09-11', 6.27, 95.5), ('2020-12-10', 1.25, 71.2), ('2020-12-11', 5.27, 94.1), ('2021-03-11', 1.0, 65.7), ('2021-03-12', 0.5, 43.4), ('2021-06-10', 0.0, 15.4), ('2021-06-11', 0.75, 59.4), ('2021-09-09', 1.0, 65.7), ('2021-09-10', 0.5, 48.5), ('2021-12-09', 1.0, 65.7), ('2021-12-10', 0.25, 35.1), ('2022-03-10', 0.5, 43.4), ('2022-03-11', 1.5, 76.7), ('2022-06-09', 1.76, 80.0), ('2022-06-10', 1.0, 65.7), ('2022-09-08', 0.5, 48.5), ('2022-09-09', 0.25, 35.1), ('2022-12-08', 0.25, 35.1), ('2022-12-09', 0.25, 25.5), ('2023-03-09', 0.25, 35.1), ('2023-03-10', 0.25, 35.1), ('2023-06-08', 14.45, 98.7), ('2023-06-09', 1.75, 78.4), ('2023-09-07', 0.5, 41.0), ('2023-09-08', 0.5, 41.0), ('2023-12-07', 0.25, 24.0), ('2023-12-08', 0.5, 41.0), ('2024-03-07', 1.5, 73.2), ('2024-03-08', 0.75, 53.4), ('2024-06-13', 1.75, 78.4), ('2024-06-14', 0.0, 15.4), ('2024-09-12', 0.25, 24.0), ('2024-09-13', 0.25, 24.0), ('2024-12-12', 0.75, 53.4), ('2024-12-13', 5.5, 94.6), ('2025-03-13', 0.25, 24.0), ('2025-03-14', 1.5, 73.2), ('2025-06-12', 0.0, 15.4), ('2025-06-13', 1.25, 68.9), ('2025-09-11', 0.5, 41.0), ('2025-09-12', 3.0, 87.9), ('2025-12-11', 5.25, 94.1), ('2025-12-12', 9.5, 97.4)]
OBSERVATION Tue-Fri session-open gaps: median 0.75, p90 3.26, p99 16.38; share of Tue-Fri gaps >= 10 points: 2.38%
[FAIL] supplementary: every OHLC price on the 0.25 tick grid | off-grid prices=4752247 of 8569564
--- BT6 roll-date jumps: 2 checks, 1 failed: supplementary: every OHLC price on the 0.25 tick grid
rc=1
```

### BT7 - P&L of bar t+1 = p_t x (Open_{t+2} - Open_{t+1}) x 5
Verdict: **CONFIRMED**.
```text
$ python -I -B validation/probes/channel_b_backtest/bt07_pnl_timing.py
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
=== BT7 P&L timing ===
[PASS] fixture A gross == [0, 10, 5, 0, -15, 0] | got [0.0, 10.0, 5.0, 0.0, -15.0, 0.0]
[PASS] fixture A held (position during bar j = p_{j-1}) == [0, 1, -1, 0, 1, 0] | got [0.0, 1.0, -1.0, 0.0, 1.0, 0.0]
[PASS] fixture B gross == [0, 25, 0, 0] (5 points from Open_1 to Open_2) | got [0.0, 25.0, 0.0, 0.0]
[PASS] fixture B: Open_0 (decision bar) does not enter P&L
[PASS] fixture C daily gross on calendar == [0, 5, -15, 0] | got [0.0, 5.0, -15.0, 0.0]
[PASS] fixture C, calendar [d2] only -> [-15] | got [-15.0]
[PASS] random n=400: gross[j] == p_{j-1}*(O_{j+1}-O_j)*5 for every j (exact) | max |diff| = 0
[PASS] mutating Open of bars > t+2 never changes P&L of bars <= t+1 (57 t values) | violations=0
[PASS] mutating decisions p_s, s > t never changes P&L of bars <= t+1 | violations=0
[PASS] High/Low/Close do not enter P&L
--- BT7 P&L timing: 10 checks, 0 failed
rc=0  wall=1.51s
```
Falsifier A (execute at Open_t: `o[2:] - o[1:n-1]` -> `o[1:n-1] - o[:n-2]`):
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt7_open_t engine.py gross[1: n - 1] = pt * (o[2:] - o[1: n - 1]) * point_value gross[1: n - 1] = pt * (o[1: n - 1] - o[: n - 2]) * point_value
mutant: %SCRATCH%\mut_bt7_open_t\qibt\engine.py
  - gross[1: n - 1] = pt * (o[2:] - o[1: n - 1]) * point_value
  + gross[1: n - 1] = pt * (o[1: n - 1] - o[: n - 2]) * point_value
sha256 original engine.py before 10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 original engine.py after  10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 mutant   engine.py        98451b958128b90e82c46b11bdd36b33e575225f8725b4695590cdff657abf88
rc=0  wall=0.21s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt07_pnl_timing.py --qibt-root %SCRATCH%\mut_bt7_open_t
qibt loaded from: %SCRATCH%\mut_bt7_open_t\qibt\__init__.py
=== BT7 P&L timing ===
[FAIL] fixture A gross == [0, 10, 5, 0, -15, 0] | got [0.0, 5.0, -10.0, -0.0, 40.0, 0.0]
[PASS] fixture A held (position during bar j = p_{j-1}) == [0, 1, -1, 0, 1, 0] | got [0.0, 1.0, -1.0, 0.0, 1.0, 0.0]
[FAIL] fixture B gross == [0, 25, 0, 0] (5 points from Open_1 to Open_2) | got [0.0, 500.0, 0.0, 0.0]
[FAIL] fixture B: Open_0 (decision bar) does not enter P&L
[FAIL] fixture C daily gross on calendar == [0, 5, -15, 0] | got [0.0, 15.0, 5.0, 0.0]
[FAIL] fixture C, calendar [d2] only -> [-15] | got [5.0]
[FAIL] random n=400: gross[j] == p_{j-1}*(O_{j+1}-O_j)*5 for every j (exact) | max |diff| = 62.5
[PASS] mutating Open of bars > t+2 never changes P&L of bars <= t+1 (57 t values) | violations=0
[PASS] mutating decisions p_s, s > t never changes P&L of bars <= t+1 | violations=0
[PASS] High/Low/Close do not enter P&L
--- BT7 P&L timing: 10 checks, 6 failed: fixture A gross == [0, 10, 5, 0, -15, 0]; fixture B gross == [0, 25, 0, 0] (5 points from Open_1 to Open_2); fixture B: Open_0 (decision bar) does not enter P&L; fixture C daily gross on calendar == [0, 5, -15, 0]; fixture C, calendar [d2] only -> [-15]; random n=400: gross[j] == p_{j-1}*(O_{j+1}-O_j)*5 for every j (exact)
rc=1  wall=1.38s
```
Falsifier B (look-ahead: hold p_{t+1} instead of p_t). This one is killed by the metamorphic check too:
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt7_lookahead engine.py pt = p[: n - 2]  pt = p[1: n - 1] 
mutant: %SCRATCH%\mut_bt7_lookahead\qibt\engine.py
  - pt = p[: n - 2]
  + pt = p[1: n - 1]
sha256 original engine.py before 10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 original engine.py after  10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 mutant   engine.py        116bbd5e1944b1f77bef9665c625f8aa4837360ec228add4583745576b849725
rc=0  wall=0.21s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt07_pnl_timing.py --qibt-root %SCRATCH%\mut_bt7_lookahead
qibt loaded from: %SCRATCH%\mut_bt7_lookahead\qibt\__init__.py
=== BT7 P&L timing ===
[FAIL] fixture A gross == [0, 10, 5, 0, -15, 0] | got [0.0, -10.0, -0.0, 40.0, -15.0, 0.0]
[FAIL] fixture A held (position during bar j = p_{j-1}) == [0, 1, -1, 0, 1, 0] | got [0.0, -1.0, 0.0, 1.0, 1.0, 0.0]
[FAIL] fixture B gross == [0, 25, 0, 0] (5 points from Open_1 to Open_2) | got [0.0, 0.0, 0.0, 0.0]
[PASS] fixture B: Open_0 (decision bar) does not enter P&L
[FAIL] fixture C daily gross on calendar == [0, 5, -15, 0] | got [0.0, 15.0, 0.0, 0.0]
[FAIL] fixture C, calendar [d2] only -> [-15] | got [0.0]
[FAIL] random n=400: gross[j] == p_{j-1}*(O_{j+1}-O_j)*5 for every j (exact) | max |diff| = 77.5
[PASS] mutating Open of bars > t+2 never changes P&L of bars <= t+1 (57 t values) | violations=0
[FAIL] mutating decisions p_s, s > t never changes P&L of bars <= t+1 | violations=38
[PASS] High/Low/Close do not enter P&L
--- BT7 P&L timing: 10 checks, 7 failed: fixture A gross == [0, 10, 5, 0, -15, 0]; fixture A held (position during bar j = p_{j-1}) == [0, 1, -1, 0, 1, 0]; fixture B gross == [0, 25, 0, 0] (5 points from Open_1 to Open_2); fixture C daily gross on calendar == [0, 5, -15, 0]; fixture C, calendar [d2] only -> [-15]; random n=400: gross[j] == p_{j-1}*(O_{j+1}-O_j)*5 for every j (exact); mutating decisions p_s, s > t never changes P&L of bars <= t+1
rc=1  wall=1.38s
```

### BT8 - costs = |p_t - p_{t-1}| x 2.25 at execution
Verdict: **CONFIRMED** on the pre-registered probes, **with boundary deviation F3**.
```text
$ python -I -B validation/probes/channel_b_backtest/bt08_costs.py
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
=== BT8 cost model (pre-registered) ===
[PASS] sides per execution bar == [0, 1, 2, 0, 1, 1, 0] | got [0.0, 1.0, 2.0, 0.0, 1.0, 1.0, 0.0]
[PASS] cost at 1x == [0, 2.25, 4.50, 0, 2.25, 2.25, 0] | got [0.0, 2.25, 4.5, 0.0, 2.25, 2.25, 0.0]
[PASS] flip long->short costs 2 sides = 4.50
[PASS] hold costs 0
[PASS] 0x costs are all 0 | got [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
[PASS] 2x costs == 2 * 1x costs | got [0.0, 4.5, 9.0, 0.0, 4.5, 4.5, 0.0]
[PASS] DailyResult.sides == [0,1,2,0,1,1,0] | got [0.0, 1.0, 2.0, 0.0, 1.0, 1.0, 0.0]
[PASS] DailyResult.gross == hand | got [0.0, 5.0, -5.0, -5.0, 0.0, 5.0, 0.0]
[PASS] net at 0x == gross - sides*2.25*0 | got [0.0, 5.0, -5.0, -5.0, 0.0, 5.0, 0.0]
[PASS] net at 1x == gross - sides*2.25*1 | got [0.0, 2.75, -9.5, -5.0, -2.25, 2.75, 0.0]
[PASS] net at 2x == gross - sides*2.25*2 | got [0.0, 0.5, -14.0, -5.0, -4.5, 0.5, 0.0]
[PASS] total cost 0x/1x/2x == 0 / 11.25 / 22.50 (5 sides) | got [0.0, 11.25, 22.5]
--- BT8 cost model (pre-registered): 12 checks, 0 failed
rc=0  wall=1.46s
```
Supplementary edge probe (not pre-registered; it does not change the verdict and is reported as F3):
```text
$ python -I -B validation/probes/channel_b_backtest/bt08_costs.py --edge
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
=== BT8 supplementary: change executed at the open of the last bar ===
[FAIL] last-bar execution charged 1 side | sides=[0.0, 0.0, 0.0, 0.0] gross=[0.0, 0.0, 0.0, 0.0]
--- BT8 supplementary: change executed at the open of the last bar: 1 checks, 1 failed: last-bar execution charged 1 side
rc=1  wall=1.39s
```
Falsifier (charge on every held bar: `abs(pt - prev)` -> `abs(pt)`):
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt8_everybar engine.py sides[1: n - 1] = np.abs(pt - prev) sides[1: n - 1] = np.abs(pt)
mutant: %SCRATCH%\mut_bt8_everybar\qibt\engine.py
  - sides[1: n - 1] = np.abs(pt - prev)
  + sides[1: n - 1] = np.abs(pt)
sha256 original engine.py before 10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 original engine.py after  10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 mutant   engine.py        87c479254c3fcd3d3433abe0d64ee8e0be3305a07cb4b73202a06221a48079f2
rc=0  wall=0.19s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt08_costs.py --qibt-root %SCRATCH%\mut_bt8_everybar
qibt loaded from: %SCRATCH%\mut_bt8_everybar\qibt\__init__.py
=== BT8 cost model (pre-registered) ===
[FAIL] sides per execution bar == [0, 1, 2, 0, 1, 1, 0] | got [0.0, 1.0, 1.0, 1.0, 0.0, 1.0, 0.0]
[FAIL] cost at 1x == [0, 2.25, 4.50, 0, 2.25, 2.25, 0] | got [0.0, 2.25, 2.25, 2.25, 0.0, 2.25, 0.0]
[FAIL] flip long->short costs 2 sides = 4.50
[FAIL] hold costs 0
[PASS] 0x costs are all 0 | got [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
[PASS] 2x costs == 2 * 1x costs | got [0.0, 4.5, 4.5, 4.5, 0.0, 4.5, 0.0]
[FAIL] DailyResult.sides == [0,1,2,0,1,1,0] | got [0.0, 1.0, 1.0, 1.0, 0.0, 1.0, 0.0]
[PASS] DailyResult.gross == hand | got [0.0, 5.0, -5.0, -5.0, 0.0, 5.0, 0.0]
[PASS] net at 0x == gross - sides*2.25*0 | got [0.0, 5.0, -5.0, -5.0, 0.0, 5.0, 0.0]
[FAIL] net at 1x == gross - sides*2.25*1 | got [0.0, 2.75, -7.25, -7.25, 0.0, 2.75, 0.0]
[FAIL] net at 2x == gross - sides*2.25*2 | got [0.0, 0.5, -9.5, -9.5, 0.0, 0.5, 0.0]
[FAIL] total cost 0x/1x/2x == 0 / 11.25 / 22.50 (5 sides) | got [0.0, 9.0, 18.0]
--- BT8 cost model (pre-registered): 12 checks, 8 failed: sides per execution bar == [0, 1, 2, 0, 1, 1, 0]; cost at 1x == [0, 2.25, 4.50, 0, 2.25, 2.25, 0]; flip long->short costs 2 sides = 4.50; hold costs 0; DailyResult.sides == [0,1,2,0,1,1,0]; net at 1x == gross - sides*2.25*1; net at 2x == gross - sides*2.25*2; total cost 0x/1x/2x == 0 / 11.25 / 22.50 (5 sides)
rc=1  wall=1.30s
```

### BT9 - SR = mean/std(ddof=1) x sqrt(252)
Verdict: **CONFIRMED** (estimator). The clause "the sqrt(252) scaling assumes iid daily returns" is
a literature statement (Lo 2002) and is **UNVERIFIABLE** at runtime.
```text
$ python -I -B validation/probes/channel_b_backtest/bt09_sharpe.py
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
=== BT9 annualised Sharpe ===
[PASS] hand fixture SR == 4/sqrt(12.5)*sqrt(252) = 17.959955456515 | got 17.959955456514919
[PASS] per-day SR == 4/sqrt(12.5) | got 1.131370849898476
[PASS] 200 random series vs numpy mean/std(ddof=1)*sqrt(252): rel err < 1e-12 | worst 0
[PASS] scale invariance SR(k x) == SR(x) for k > 0 | max diff 2.22e-16
[PASS] SR(-x) == -SR(x)
[PASS] constant series -> NaN (zero variance), not inf
--- BT9 annualised Sharpe: 6 checks, 0 failed
rc=0  wall=0.41s
```
Falsifier A (ddof=0) and B (sqrt 365). Scale invariance alone survives both; the numeric fixture kills them:
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt9_ddof0 metrics.py sd = float(np.std(a, ddof=1)) sd = float(np.std(a, ddof=0))
mutant: %SCRATCH%\mut_bt9_ddof0\qibt\metrics.py
  - sd = float(np.std(a, ddof=1))
  + sd = float(np.std(a, ddof=0))
sha256 original metrics.py before 9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 original metrics.py after  9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 mutant   metrics.py        f97f99d8ed5b79d9d4b7b78b9d008b8255268d8d35687590a1826d2262ce5e7b
rc=0  wall=0.20s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt09_sharpe.py --qibt-root %SCRATCH%\mut_bt9_ddof0
qibt loaded from: %SCRATCH%\mut_bt9_ddof0\qibt\__init__.py
=== BT9 annualised Sharpe ===
[FAIL] hand fixture SR == 4/sqrt(12.5)*sqrt(252) = 17.959955456515 | got 20.079840636817814
[FAIL] per-day SR == 4/sqrt(12.5) | got 1.264911064067352
[FAIL] 200 random series vs numpy mean/std(ddof=1)*sqrt(252): rel err < 1e-12 | worst 0.0377
[PASS] scale invariance SR(k x) == SR(x) for k > 0 | max diff 2.22e-16
[PASS] SR(-x) == -SR(x)
[PASS] constant series -> NaN (zero variance), not inf
--- BT9 annualised Sharpe: 6 checks, 3 failed: hand fixture SR == 4/sqrt(12.5)*sqrt(252) = 17.959955456515; per-day SR == 4/sqrt(12.5); 200 random series vs numpy mean/std(ddof=1)*sqrt(252): rel err < 1e-12
rc=1  wall=0.41s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt9_365 metrics.py ANNUALISATION = 252 ANNUALISATION = 365
mutant: %SCRATCH%\mut_bt9_365\qibt\metrics.py
  - ANNUALISATION = 252
  + ANNUALISATION = 365
sha256 original metrics.py before 9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 original metrics.py after  9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 mutant   metrics.py        ec7c9216ffd2ca1ad93645a181ac5ea0cc2a2e5766f407e966fdcda0f9ac9c8d
rc=0  wall=0.18s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt09_sharpe.py --qibt-root %SCRATCH%\mut_bt9_365
qibt loaded from: %SCRATCH%\mut_bt9_365\qibt\__init__.py
=== BT9 annualised Sharpe ===
[FAIL] hand fixture SR == 4/sqrt(12.5)*sqrt(252) = 17.959955456515 | got 21.614809737770074
[PASS] per-day SR == 4/sqrt(12.5) | got 1.131370849898476
[FAIL] 200 random series vs numpy mean/std(ddof=1)*sqrt(252): rel err < 1e-12 | worst 0.204
[PASS] scale invariance SR(k x) == SR(x) for k > 0 | max diff 4.44e-16
[PASS] SR(-x) == -SR(x)
[PASS] constant series -> NaN (zero variance), not inf
--- BT9 annualised Sharpe: 6 checks, 2 failed: hand fixture SR == 4/sqrt(12.5)*sqrt(252) = 17.959955456515; 200 random series vs numpy mean/std(ddof=1)*sqrt(252): rel err < 1e-12
rc=1  wall=0.48s
```

### BT10 - PSR formula, per-period SR, non-excess kurtosis
Verdict: **CONFIRMED**. The pre-registered properties (0.5 at SR = SR*, monotone in n) do **not**
detect the drop-the-(-1) mutant. The numeric fixtures against the ledger formula do (falsifier
output below). The paper's numeric example was not available to Channel B.
Observation: Phi is evaluated as `NormalDist().cdf`, which is exactly 0.0 for z <= -8.26. Absolute
accuracy is fine; ordering information in the far tail is lost (see F2).
```text
$ python -I -B validation/probes/channel_b_backtest/bt10_psr.py
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
=== BT10 PSR ===
[PASS] PSR(SR*=SR) == 0.5 (36 combos) | range [0.5, 0.5]
[PASS] SR > SR*: PSR strictly increasing in n (until it saturates at 1.0) | first/last 0.5334376085666499 / 0.9994162941157306
[PASS] SR < SR*: PSR strictly decreasing in n (until 0.0) | first/last 0.465959201330718 / 0.00047414571231430003
[PASS] psr(0.1, 0, n=253, g3=-0.5, g4=5) == ledger formula 0.938447224765 | got 0.938447224764729
[PASS] psr(0.05, 0.02, n=1320, g3=1.36, g4=39) == ledger formula 0.867462910914 | got 0.867462910913953
[PASS] psr(-0.03, 0, n=1320, g3=-1.8, g4=109.8) == ledger formula 0.134365888242 | got 0.134365888241798
[PASS] psr(0.2, 0.1, n=60, g3=0, g4=3) == ledger formula 0.776536084770 | got 0.776536084769989
[PASS] psr(0.0532, 0, n=1320, g3=0.3, g4=12) == ledger formula 0.973814274628 | got 0.973814274627547
[PASS] moments([-1,1]*50) == (0, 1) (non-excess kurtosis) | got (0.0, 1.0)
[PASS] normal sample: kurtosis ~ 3 (non-excess), |skew| < 0.02 | got skew 0.0035 kurt 2.9979
[PASS] moments == m3/m2^1.5, m4/m2^2 on a t5 sample | got (-0.140459932943, 7.047941075673) ref (-0.140459932943, 7.047941075673)
[PASS] psr_of(x) == formula on per-day SR | got 0.305385184529075 ref 0.305385184529075
--- BT10 PSR: 12 checks, 0 failed
rc=0  wall=0.40s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt10_drop1 metrics.py (kurt - 1.0) / 4.0 kurt / 4.0
mutant: %SCRATCH%\mut_bt10_drop1\qibt\metrics.py
  - (kurt - 1.0) / 4.0
  + kurt / 4.0
sha256 original metrics.py before 9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 original metrics.py after  9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 mutant   metrics.py        f8f9afc890b4eeb84a49174b01a351349935eb6e2b3519683152ce23e526e438
rc=0  wall=0.21s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt10_psr.py --qibt-root %SCRATCH%\mut_bt10_drop1
qibt loaded from: %SCRATCH%\mut_bt10_drop1\qibt\__init__.py
=== BT10 PSR ===
[PASS] PSR(SR*=SR) == 0.5 (36 combos) | range [0.5, 0.5]
[PASS] SR > SR*: PSR strictly increasing in n (until it saturates at 1.0) | first/last 0.5334229369190748 / 0.9994133589829755
[PASS] SR < SR*: PSR strictly decreasing in n (until 0.0) | first/last 0.46597468101233036 / 0.000476701412398306
[FAIL] psr(0.1, 0, n=253, g3=-0.5, g4=5) == ledger formula 0.938447224765 | got 0.938226340422027
[FAIL] psr(0.05, 0.02, n=1320, g3=1.36, g4=39) == ledger formula 0.867462910914 | got 0.867384810683517
[FAIL] psr(-0.03, 0, n=1320, g3=-1.8, g4=109.8) == ledger formula 0.134365888242 | got 0.134393631990619
[FAIL] psr(0.2, 0.1, n=60, g3=0, g4=3) == ledger formula 0.776536084770 | got 0.775428868827288
[FAIL] psr(0.0532, 0, n=1320, g3=0.3, g4=12) == ledger formula 0.973814274628 | got 0.973772223987644
[PASS] moments([-1,1]*50) == (0, 1) (non-excess kurtosis) | got (0.0, 1.0)
[PASS] normal sample: kurtosis ~ 3 (non-excess), |skew| < 0.02 | got skew 0.0035 kurt 2.9979
[PASS] moments == m3/m2^1.5, m4/m2^2 on a t5 sample | got (-0.140459932943, 7.047941075673) ref (-0.140459932943, 7.047941075673)
[FAIL] psr_of(x) == formula on per-day SR | got 0.305404500587890 ref 0.305385184529075
--- BT10 PSR: 12 checks, 6 failed: psr(0.1, 0, n=253, g3=-0.5, g4=5) == ledger formula 0.938447224765; psr(0.05, 0.02, n=1320, g3=1.36, g4=39) == ledger formula 0.867462910914; psr(-0.03, 0, n=1320, g3=-1.8, g4=109.8) == ledger formula 0.134365888242; psr(0.2, 0.1, n=60, g3=0, g4=3) == ledger formula 0.776536084770; psr(0.0532, 0, n=1320, g3=0.3, g4=12) == ledger formula 0.973814274628; psr_of(x) == formula on per-day SR
rc=1  wall=0.48s
```

### BT11 - DSR = PSR(SR0), SR0 formula with Euler-Mascheroni gamma
Verdict: **CONFIRMED** (properties: DSR <= PSR(0); non-increasing in N; DSR = PSR when the SR0
term is 0; SR0 equals the ledger formula with my own Phi^-1). "Reproduces the paper's numeric
example" is **UNVERIFIABLE** for Channel B. Falsifier A (swap gamma and 1-gamma) passes every
property check and is caught only by the SR0-vs-formula check. Falsifier B (negative SR0) breaks
the properties.
```text
$ python -I -B validation/probes/channel_b_backtest/bt11_dsr.py
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
=== BT11 DSR properties ===
[PASS] DSR <= PSR(0) for 5 series x 4 V x 5 N | violations=0
[PASS] DSR non-increasing in N (N = 2..399) | increases=0
[PASS] DSR strictly decreasing in N unless saturated at 0/1 | non-strict steps=0
[PASS] V = 0 (SR0 term 0): DSR == PSR(0) exactly | mismatches=0
[PASS] SR0 == ledger formula (own bisection Phi^-1), rel err < 1e-9 | worst rel err 4.99e-14
[PASS] SR0(V, N) > 0 for V > 0, N >= 2
--- BT11 DSR properties: 6 checks, 0 failed
rc=0  wall=0.59s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt11_swap metrics.py z = (1.0 - g) * _N.inv_cdf(1.0 - 1.0 / n_trials) + g * _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e)) z = g * _N.inv_cdf(1.0 - 1.0 / n_trials) + (1.0 - g) * _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
mutant: %SCRATCH%\mut_bt11_swap\qibt\metrics.py
  - z = (1.0 - g) * _N.inv_cdf(1.0 - 1.0 / n_trials) + g * _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
  + z = g * _N.inv_cdf(1.0 - 1.0 / n_trials) + (1.0 - g) * _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
sha256 original metrics.py before 9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 original metrics.py after  9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 mutant   metrics.py        0554bc3908fc2d5a553da99aae7e8df47c3e3ccf05363028947fbe875be90534
rc=0  wall=0.24s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt11_dsr.py --qibt-root %SCRATCH%\mut_bt11_swap
qibt loaded from: %SCRATCH%\mut_bt11_swap\qibt\__init__.py
=== BT11 DSR properties ===
[PASS] DSR <= PSR(0) for 5 series x 4 V x 5 N | violations=0
[PASS] DSR non-increasing in N (N = 2..399) | increases=0
[PASS] DSR strictly decreasing in N unless saturated at 0/1 | non-strict steps=0
[PASS] V = 0 (SR0 term 0): DSR == PSR(0) exactly | mismatches=0
[FAIL] SR0 == ledger formula (own bisection Phi^-1), rel err < 1e-9 | worst rel err 0.268
[PASS] SR0(V, N) > 0 for V > 0, N >= 2
--- BT11 DSR properties: 6 checks, 1 failed: SR0 == ledger formula (own bisection Phi^-1), rel err < 1e-9
rc=1  wall=0.94s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt11_neg metrics.py return math.sqrt(var_sr) * z return -math.sqrt(var_sr) * z
mutant: %SCRATCH%\mut_bt11_neg\qibt\metrics.py
  - return math.sqrt(var_sr) * z
  + return -math.sqrt(var_sr) * z
sha256 original metrics.py before 9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 original metrics.py after  9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 mutant   metrics.py        b40ad8d61bd2e4bf20cdfc06f2af686efda67063be1f7e055046449e070accf0
rc=0  wall=0.22s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt11_dsr.py --qibt-root %SCRATCH%\mut_bt11_neg
qibt loaded from: %SCRATCH%\mut_bt11_neg\qibt\__init__.py
=== BT11 DSR properties ===
[FAIL] DSR <= PSR(0) for 5 series x 4 V x 5 N | violations=100
[FAIL] DSR non-increasing in N (N = 2..399) | increases=3970
[FAIL] DSR strictly decreasing in N unless saturated at 0/1 | non-strict steps=3970
[PASS] V = 0 (SR0 term 0): DSR == PSR(0) exactly | mismatches=0
[FAIL] SR0 == ledger formula (own bisection Phi^-1), rel err < 1e-9 | worst rel err 2
[FAIL] SR0(V, N) > 0 for V > 0, N >= 2
--- BT11 DSR properties: 6 checks, 5 failed: DSR <= PSR(0) for 5 series x 4 V x 5 N; DSR non-increasing in N (N = 2..399); DSR strictly decreasing in N unless saturated at 0/1; SR0 == ledger formula (own bisection Phi^-1), rel err < 1e-9; SR0(V, N) > 0 for V > 0, N >= 2
rc=1  wall=0.99s
```

### BT12 - max drawdown
Verdict: **CONFIRMED**. Observation: the equity curve starts at 0, so MDD([-5, 3]) = 5. The ledger
text does not fix this convention.
```text
$ python -I -B validation/probes/channel_b_backtest/bt12_mdd.py
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
=== BT12 max drawdown ===
[PASS] MDD([5, -3, -4, 6, -1]) == 7 | got 7.0
[PASS] MDD([1, 2, 3, 4]) == 0 | got 0.0
[PASS] MDD([0, 0, 0]) == 0 | got 0.0
[PASS] MDD([1, -1, 1, -1]) == 1 | got 1.0
[PASS] MDD([10, -2, 5, -20, 3, 30, -4]) == 20 | got 20.0
[PASS] MDD([3, -1, -1, 4, -6, 1]) == 6 | got 6.0
[PASS] 300 random series vs own loop (equity from 0) | mismatches=0
[PASS] monotone up (strictly) -> 0
OBSERVATION: MDD([-5, 3]) = 5.0  (5 if the curve starts at 0; 0 if the running max starts at day 1)
--- BT12 max drawdown: 8 checks, 0 failed
rc=0  wall=0.33s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt12_end metrics.py return float(np.max(np.maximum.accumulate(cum) - cum)) return float(np.max(cum) - cum[-1])
mutant: %SCRATCH%\mut_bt12_end\qibt\metrics.py
  - return float(np.max(np.maximum.accumulate(cum) - cum))
  + return float(np.max(cum) - cum[-1])
sha256 original metrics.py before 9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 original metrics.py after  9670a1c115ff08d9e2cb63001b12874efab3fc027501d362acecbcd64f2e4ba7
sha256 mutant   metrics.py        9bdc9789f765cdbdd2ddab82571571ba00e77449387ea79b160933f2d994d0f7
rc=0  wall=0.25s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt12_mdd.py --qibt-root %SCRATCH%\mut_bt12_end
qibt loaded from: %SCRATCH%\mut_bt12_end\qibt\__init__.py
=== BT12 max drawdown ===
[FAIL] MDD([5, -3, -4, 6, -1]) == 7 | got 2.0
[PASS] MDD([1, 2, 3, 4]) == 0 | got 0.0
[PASS] MDD([0, 0, 0]) == 0 | got 0.0
[PASS] MDD([1, -1, 1, -1]) == 1 | got 1.0
[FAIL] MDD([10, -2, 5, -20, 3, 30, -4]) == 20 | got 4.0
[FAIL] MDD([3, -1, -1, 4, -6, 1]) == 6 | got 5.0
[FAIL] 300 random series vs own loop (equity from 0) | mismatches=279
[PASS] monotone up (strictly) -> 0
OBSERVATION: MDD([-5, 3]) = 2.0  (5 if the curve starts at 0; 0 if the running max starts at day 1)
--- BT12 max drawdown: 8 checks, 4 failed: MDD([5, -3, -4, 6, -1]) == 7; MDD([10, -2, 5, -20, 3, 30, -4]) == 20; MDD([3, -1, -1, 4, -6, 1]) == 6; 300 random series vs own loop (equity from 0)
rc=1  wall=0.57s
```

### BT13 - rules.yaml thresholds = ORIG classification (Channel B part: generated parity)
Verdict: **CONFIRMED** for the parity rules.yaml <-> `strategies/QS_*.cs`. My own parsers (yaml
grammar and C# `goLong`/`goShort` literals) check: canonical atoms, header frame, long->+1 /
short->-1 / NaN->0 wiring, and long/short exclusivity. Equality with ORIG IBSFade.cs at the cited
lines is the static read assigned to Channel A. It is not decided here.
```text
$ python -I -B validation/probes/channel_b_backtest/bt13_rule_parity.py
strategies: C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators\strategies
rules: C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators\backtest\rules.yaml
=== BT13 rules.yaml <-> QS_*.cs parity ===
[PASS] module sets equal (rules.yaml 25, QS files 25) | only yaml: []; only cs: []
[PASS] ATRRegime: long x < 1.5 | short never | frame D | cs long='x < 1.5' short='false' header-frame='Day' wiring=True exclusive=True
[PASS] BollingerPctB: long x == -1 | short x == 1 | frame 15m | cs long='x == -1.0' short='x == 1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] CompositeVol: long x > 1.5 | short x < -1.5 | frame D | cs long='x > 1.5' short='x < -1.5' header-frame='Day' wiring=True exclusive=True
[PASS] ConnorsRSI: long x < 15 | short x > 85 | frame D | cs long='x < 15.0' short='x > 85.0' header-frame='Day' wiring=True exclusive=True
[PASS] ConsecDays: long x <= -3 | short x >= 3 | frame D | cs long='x <= -3.0' short='x >= 3.0' header-frame='Day' wiring=True exclusive=True
[PASS] EMACross: long x > 0 | short x < 0 | frame D | cs long='x > 0.0' short='x < 0.0' header-frame='Day' wiring=True exclusive=True
[PASS] HedgingPressure: long x <= -35 | short x >= 35 | frame D | cs long='x <= -35.0' short='x >= 35.0' header-frame='Day' wiring=True exclusive=True
[PASS] IBS: long x < 0.20 | short x > 0.80 | frame D | cs long='x < 0.20' short='x > 0.80' header-frame='Day' wiring=True exclusive=True
[PASS] LiquiditySweep: long x == 1 | short x == -1 | frame 15m | cs long='x == 1.0' short='x == -1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] MACDHistogram: long x > 0 | short x < 0 | frame D | cs long='x > 0.0' short='x < 0.0' header-frame='Day' wiring=True exclusive=True
[PASS] OrderFlowPlus: long x == 1 | short x == -1 | frame 15m | cs long='x == 1.0' short='x == -1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] OvernightGap: long x < -0.3 | short x > 0.3 | frame D | cs long='x < -0.3' short='x > 0.3' header-frame='Day' wiring=True exclusive=True
[PASS] RSI14: long x < 40 | short x > 60 | frame D | cs long='x < 40.0' short='x > 60.0' header-frame='Day' wiring=True exclusive=True
[PASS] RSI2: long x < 25 | short x > 75 | frame D | cs long='x < 25.0' short='x > 75.0' header-frame='Day' wiring=True exclusive=True
[PASS] RVZScore: long x > 2.0 | short x < -1.5 | frame D | cs long='x > 2.0' short='x < -1.5' header-frame='Day' wiring=True exclusive=True
[PASS] SMA200Trend: long x > 0 | short x < 0 | frame D | cs long='x > 0.0' short='x < 0.0' header-frame='Day' wiring=True exclusive=True
[PASS] SMC: long x == 1 | short x == -1 | frame 15m | cs long='x == 1.0' short='x == -1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] StochFade: long x < 30 | short x > 70 | frame D | cs long='x < 30.0' short='x > 70.0' header-frame='Day' wiring=True exclusive=True
[PASS] TurnOfMonth: long x == 1 | short never | frame D | cs long='x == 1.0' short='false' header-frame='Day' wiring=True exclusive=True
[PASS] TurnaroundTuesday: long x == 1 | short never | frame D | cs long='x == 1.0' short='false' header-frame='Day' wiring=True exclusive=True
[PASS] VRPProxy: long x > 1.5 | short x < 0.7 | frame D | cs long='x > 1.5' short='x < 0.7' header-frame='Day' wiring=True exclusive=True
[PASS] VWAPDistance: long -0.5 < x < 0 | short 0 < x < 0.5 | frame 15m | cs long='x > -0.5 && x < 0.0' short='x > 0.0 && x < 0.5' header-frame='15 Minute' wiring=True exclusive=True
[PASS] VolumeDelta: long x > 0 | short x < 0 | frame 15m | cs long='x > 0.0' short='x < 0.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] VolumeSpike: long x > 1.5 | short never | frame 15m | cs long='x > 1.5' short='false' header-frame='15 Minute' wiring=True exclusive=True
[PASS] WideRangeBar: long x > 1.2 | short never | frame D | cs long='x > 1.2' short='false' header-frame='Day' wiring=True exclusive=True
--- BT13 rules.yaml <-> QS_*.cs parity: 26 checks, 0 failed
rc=0  wall=0.93s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py strategies %SCRATCH%\mut_bt13_rsi45 QS_RSI14.cs bool goLong  = x < 40.0; bool goLong  = x < 45.0;
mutant: %SCRATCH%\mut_bt13_rsi45\strategies\QS_RSI14.cs
  - bool goLong  = x < 40.0;
  + bool goLong  = x < 45.0;
sha256 original QS_RSI14.cs before 9a153e97094f7b42761078a4d9eef1c384737bf216dfa455c49050b1fb2abfa9
sha256 original QS_RSI14.cs after  9a153e97094f7b42761078a4d9eef1c384737bf216dfa455c49050b1fb2abfa9
sha256 mutant   QS_RSI14.cs        82404474d8c44ae7040650c23e2bfe4d5a7555479758cc11634d9173ba7d2f8b
rc=0  wall=0.16s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt13_rule_parity.py --strategies %SCRATCH%\mut_bt13_rsi45\strategies
strategies: %SCRATCH%\mut_bt13_rsi45\strategies
rules: C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators\backtest\rules.yaml
=== BT13 rules.yaml <-> QS_*.cs parity ===
[PASS] module sets equal (rules.yaml 25, QS files 25) | only yaml: []; only cs: []
[PASS] ATRRegime: long x < 1.5 | short never | frame D | cs long='x < 1.5' short='false' header-frame='Day' wiring=True exclusive=True
[PASS] BollingerPctB: long x == -1 | short x == 1 | frame 15m | cs long='x == -1.0' short='x == 1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] CompositeVol: long x > 1.5 | short x < -1.5 | frame D | cs long='x > 1.5' short='x < -1.5' header-frame='Day' wiring=True exclusive=True
[PASS] ConnorsRSI: long x < 15 | short x > 85 | frame D | cs long='x < 15.0' short='x > 85.0' header-frame='Day' wiring=True exclusive=True
[PASS] ConsecDays: long x <= -3 | short x >= 3 | frame D | cs long='x <= -3.0' short='x >= 3.0' header-frame='Day' wiring=True exclusive=True
[PASS] EMACross: long x > 0 | short x < 0 | frame D | cs long='x > 0.0' short='x < 0.0' header-frame='Day' wiring=True exclusive=True
[PASS] HedgingPressure: long x <= -35 | short x >= 35 | frame D | cs long='x <= -35.0' short='x >= 35.0' header-frame='Day' wiring=True exclusive=True
[PASS] IBS: long x < 0.20 | short x > 0.80 | frame D | cs long='x < 0.20' short='x > 0.80' header-frame='Day' wiring=True exclusive=True
[PASS] LiquiditySweep: long x == 1 | short x == -1 | frame 15m | cs long='x == 1.0' short='x == -1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] MACDHistogram: long x > 0 | short x < 0 | frame D | cs long='x > 0.0' short='x < 0.0' header-frame='Day' wiring=True exclusive=True
[PASS] OrderFlowPlus: long x == 1 | short x == -1 | frame 15m | cs long='x == 1.0' short='x == -1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] OvernightGap: long x < -0.3 | short x > 0.3 | frame D | cs long='x < -0.3' short='x > 0.3' header-frame='Day' wiring=True exclusive=True
[FAIL] RSI14: long x < 40 | short x > 60 | frame D | cs long='x < 45.0' short='x > 60.0' header-frame='Day' wiring=True exclusive=True
[PASS] RSI2: long x < 25 | short x > 75 | frame D | cs long='x < 25.0' short='x > 75.0' header-frame='Day' wiring=True exclusive=True
[PASS] RVZScore: long x > 2.0 | short x < -1.5 | frame D | cs long='x > 2.0' short='x < -1.5' header-frame='Day' wiring=True exclusive=True
[PASS] SMA200Trend: long x > 0 | short x < 0 | frame D | cs long='x > 0.0' short='x < 0.0' header-frame='Day' wiring=True exclusive=True
[PASS] SMC: long x == 1 | short x == -1 | frame 15m | cs long='x == 1.0' short='x == -1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] StochFade: long x < 30 | short x > 70 | frame D | cs long='x < 30.0' short='x > 70.0' header-frame='Day' wiring=True exclusive=True
[PASS] TurnOfMonth: long x == 1 | short never | frame D | cs long='x == 1.0' short='false' header-frame='Day' wiring=True exclusive=True
[PASS] TurnaroundTuesday: long x == 1 | short never | frame D | cs long='x == 1.0' short='false' header-frame='Day' wiring=True exclusive=True
[PASS] VRPProxy: long x > 1.5 | short x < 0.7 | frame D | cs long='x > 1.5' short='x < 0.7' header-frame='Day' wiring=True exclusive=True
[PASS] VWAPDistance: long -0.5 < x < 0 | short 0 < x < 0.5 | frame 15m | cs long='x > -0.5 && x < 0.0' short='x > 0.0 && x < 0.5' header-frame='15 Minute' wiring=True exclusive=True
[PASS] VolumeDelta: long x > 0 | short x < 0 | frame 15m | cs long='x > 0.0' short='x < 0.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] VolumeSpike: long x > 1.5 | short never | frame 15m | cs long='x > 1.5' short='false' header-frame='15 Minute' wiring=True exclusive=True
[PASS] WideRangeBar: long x > 1.2 | short never | frame D | cs long='x > 1.2' short='false' header-frame='Day' wiring=True exclusive=True
--- BT13 rules.yaml <-> QS_*.cs parity: 26 checks, 1 failed: RSI14: long x < 40 | short x > 60 | frame D
rc=1  wall=1.19s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py strategies %SCRATCH%\mut_bt13_ibsle QS_IBS.cs bool goLong  = x < 0.20; bool goLong  = x <= 0.20;
mutant: %SCRATCH%\mut_bt13_ibsle\strategies\QS_IBS.cs
  - bool goLong  = x < 0.20;
  + bool goLong  = x <= 0.20;
sha256 original QS_IBS.cs before 331c737be9faef4d779a9b43617537672ac73648f45c3e95baf7b2bb9b5502e0
sha256 original QS_IBS.cs after  331c737be9faef4d779a9b43617537672ac73648f45c3e95baf7b2bb9b5502e0
sha256 mutant   QS_IBS.cs        796236419924ee00682d31d1dacfa6f68e7af19980aed02628db16c033db1298
rc=0  wall=0.18s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt13_rule_parity.py --strategies %SCRATCH%\mut_bt13_ibsle\strategies
strategies: %SCRATCH%\mut_bt13_ibsle\strategies
rules: C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators\backtest\rules.yaml
=== BT13 rules.yaml <-> QS_*.cs parity ===
[PASS] module sets equal (rules.yaml 25, QS files 25) | only yaml: []; only cs: []
[PASS] ATRRegime: long x < 1.5 | short never | frame D | cs long='x < 1.5' short='false' header-frame='Day' wiring=True exclusive=True
[PASS] BollingerPctB: long x == -1 | short x == 1 | frame 15m | cs long='x == -1.0' short='x == 1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] CompositeVol: long x > 1.5 | short x < -1.5 | frame D | cs long='x > 1.5' short='x < -1.5' header-frame='Day' wiring=True exclusive=True
[PASS] ConnorsRSI: long x < 15 | short x > 85 | frame D | cs long='x < 15.0' short='x > 85.0' header-frame='Day' wiring=True exclusive=True
[PASS] ConsecDays: long x <= -3 | short x >= 3 | frame D | cs long='x <= -3.0' short='x >= 3.0' header-frame='Day' wiring=True exclusive=True
[PASS] EMACross: long x > 0 | short x < 0 | frame D | cs long='x > 0.0' short='x < 0.0' header-frame='Day' wiring=True exclusive=True
[PASS] HedgingPressure: long x <= -35 | short x >= 35 | frame D | cs long='x <= -35.0' short='x >= 35.0' header-frame='Day' wiring=True exclusive=True
[FAIL] IBS: long x < 0.20 | short x > 0.80 | frame D | cs long='x <= 0.20' short='x > 0.80' header-frame='Day' wiring=True exclusive=True
[PASS] LiquiditySweep: long x == 1 | short x == -1 | frame 15m | cs long='x == 1.0' short='x == -1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] MACDHistogram: long x > 0 | short x < 0 | frame D | cs long='x > 0.0' short='x < 0.0' header-frame='Day' wiring=True exclusive=True
[PASS] OrderFlowPlus: long x == 1 | short x == -1 | frame 15m | cs long='x == 1.0' short='x == -1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] OvernightGap: long x < -0.3 | short x > 0.3 | frame D | cs long='x < -0.3' short='x > 0.3' header-frame='Day' wiring=True exclusive=True
[PASS] RSI14: long x < 40 | short x > 60 | frame D | cs long='x < 40.0' short='x > 60.0' header-frame='Day' wiring=True exclusive=True
[PASS] RSI2: long x < 25 | short x > 75 | frame D | cs long='x < 25.0' short='x > 75.0' header-frame='Day' wiring=True exclusive=True
[PASS] RVZScore: long x > 2.0 | short x < -1.5 | frame D | cs long='x > 2.0' short='x < -1.5' header-frame='Day' wiring=True exclusive=True
[PASS] SMA200Trend: long x > 0 | short x < 0 | frame D | cs long='x > 0.0' short='x < 0.0' header-frame='Day' wiring=True exclusive=True
[PASS] SMC: long x == 1 | short x == -1 | frame 15m | cs long='x == 1.0' short='x == -1.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] StochFade: long x < 30 | short x > 70 | frame D | cs long='x < 30.0' short='x > 70.0' header-frame='Day' wiring=True exclusive=True
[PASS] TurnOfMonth: long x == 1 | short never | frame D | cs long='x == 1.0' short='false' header-frame='Day' wiring=True exclusive=True
[PASS] TurnaroundTuesday: long x == 1 | short never | frame D | cs long='x == 1.0' short='false' header-frame='Day' wiring=True exclusive=True
[PASS] VRPProxy: long x > 1.5 | short x < 0.7 | frame D | cs long='x > 1.5' short='x < 0.7' header-frame='Day' wiring=True exclusive=True
[PASS] VWAPDistance: long -0.5 < x < 0 | short 0 < x < 0.5 | frame 15m | cs long='x > -0.5 && x < 0.0' short='x > 0.0 && x < 0.5' header-frame='15 Minute' wiring=True exclusive=True
[PASS] VolumeDelta: long x > 0 | short x < 0 | frame 15m | cs long='x > 0.0' short='x < 0.0' header-frame='15 Minute' wiring=True exclusive=True
[PASS] VolumeSpike: long x > 1.5 | short never | frame 15m | cs long='x > 1.5' short='false' header-frame='15 Minute' wiring=True exclusive=True
[PASS] WideRangeBar: long x > 1.2 | short never | frame D | cs long='x > 1.2' short='false' header-frame='Day' wiring=True exclusive=True
--- BT13 rules.yaml <-> QS_*.cs parity: 26 checks, 1 failed: IBS: long x < 0.20 | short x > 0.80 | frame D
rc=1  wall=1.14s
```

### BT14 - D frame (17:00 CT roll; first/max/min/last/sum) and right-labelled 15m bars
Verdict: **CONFIRMED** against PROTOCOL 3 as frozen (pre-A1). Fixtures: Sunday 17:01; 16:59 / 17:00
/ 17:01; DST weeks March 2024 and November 2024 (naive CT and UTC input); 16:00 bar; midnight.
At P1 scale, my own D and 15m frames are identical to `qibt.data.build_frames` on every row and
column (1578 D bars, 143,136 15m bars; see the "FRAME PARITY" lines in the cross-check, section 3).
```text
$ python -I -B validation/probes/channel_b_backtest/bt14_sessions.py
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
=== BT14 sessions and frames ===
[PASS] F1 trading dates | got ['2024-01-05', '2024-01-05', '2024-01-08', '2024-01-08', '2024-01-08', '2024-01-08', '2024-01-09']
[PASS] F1 D dates == [01-05, 01-08, 01-09] | got ['2024-01-05', '2024-01-08', '2024-01-09']
[PASS] F1 D(01-08) = first open (Sun 17:01) / max / min / last close (Mon 16:00) / sum | got [102.0, 109.0, 101.0, 105.5, 18.0] exp [102.0, 109.0, 101.0, 105.5, 18.0]
[PASS] F1 D(01-05) aggregation
[PASS] F1 15m labels (right-labelled, ceil 15 min) | got ['2024-01-05 16:00:00', '2024-01-07 17:15:00', '2024-01-08 09:00:00', '2024-01-08 16:00:00', '2024-01-08 17:15:00']
[PASS] F1 15m trading dates | got ['2024-01-05', '2024-01-08', '2024-01-08', '2024-01-08', '2024-01-09']
[PASS] F1 15m bar 16:00 (Fri) = rows 0..1 aggregated | got [100.0, 104.0, 99.0, 101.5, 3.0]
[PASS] F2 trading_date 16:59 / 17:00 / 17:01 == 01-10 / 01-10 / 01-11 | got ['2024-01-10', '2024-01-10', '2024-01-11']
[PASS] F2 halt (16:00, 17:00]: 16:00 F, 16:01 T, 16:59 T, 17:00 T, 17:01 F | got [False, True, True, True, False]
[PASS] F2 a bar closing at 16:59 is rejected by the session builder
[PASS] F2 a bar closing at 17:00 is rejected by the session builder
[PASS] F2 16:00 and 17:01 bars are accepted
[PASS] F2 halt=None: 16:59 and 17:00 stay on 01-10, 17:01 on 01-11
[PASS] F3 March DST week (naive CT): roll stays at 17:00 wall clock | got ['2024-03-08', '2024-03-08', '2024-03-11', '2024-03-11', '2024-03-11', '2024-03-12', '2024-03-12']
[PASS] F4 November DST week (naive CT) | got ['2024-11-01', '2024-11-04', '2024-11-04', '2024-11-05', '2024-11-05']
[PASS] F3 UTC->CT: 22:00Z Fri = 16:00 CST; 22:01Z Sun = 17:01 CDT; 21:00Z Mon = 16:00 CDT; 22:01Z Mon = 17:01 CDT | got ['2024-03-08 16:00:00', '2024-03-10 17:01:00', '2024-03-11 16:00:00', '2024-03-11 17:01:00']
[PASS] F4 UTC->CT: 21:00Z Fri = 16:00 CDT; 23:01Z Sun = 17:01 CST; 22:00Z Mon = 16:00 CST | got ['2024-11-01 16:00:00', '2024-11-03 17:01:00', '2024-11-04 16:00:00']
[PASS] F3 UTC input trading dates == [03-08, 03-11, 03-11, 03-12] | got ['2024-03-08', '2024-03-11', '2024-03-11', '2024-03-12']
[PASS] F5 15m labels: 15:45 alone, 15:46..16:00 -> 16:00 | got ['2024-01-10 15:45:00', '2024-01-10 16:00:00']
[PASS] F5 16:00 15m bar aggregation (first open / max / min / last close / sum)
[PASS] F5 16:00 bar keeps its calendar date
[PASS] F5 D bar close == close of the 16:00 bar
[PASS] F6 midnight: labels [00:00, 00:00 -> one bar, 00:15] | got ['2024-01-09 00:00:00', '2024-01-09 00:15:00']
[PASS] F6 midnight: all three on trading date 01-09
[PASS] F6 15m bar counts (Bars) == [2, 1] | got [2, 1]
--- BT14 sessions and frames: 25 checks, 0 failed
rc=0  wall=1.19s
```
Falsifier A (ROLL_HOUR 17 -> 18) and B (`dt.ceil` -> `dt.floor`, left labels):
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt14_roll18 data.py ROLL_HOUR = 17  ROLL_HOUR = 18 
mutant: %SCRATCH%\mut_bt14_roll18\qibt\data.py
  - ROLL_HOUR = 17
  + ROLL_HOUR = 18
sha256 original data.py before 6fe54619ed0317be8f860a4e9aa23ff043bf4bd15d140311203210a6817d080c
sha256 original data.py after  6fe54619ed0317be8f860a4e9aa23ff043bf4bd15d140311203210a6817d080c
sha256 mutant   data.py        4dce682a13e91dbb9e65199583a160fa3a9c283c0aa69bb67a92165af7133f69
rc=0  wall=0.27s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt14_sessions.py --qibt-root %SCRATCH%\mut_bt14_roll18
qibt loaded from: %SCRATCH%\mut_bt14_roll18\qibt\__init__.py
=== BT14 sessions and frames ===
[FAIL] F1 trading dates | got ['2024-01-05', '2024-01-05', '2024-01-07', '2024-01-07', '2024-01-08', '2024-01-08', '2024-01-08']
[FAIL] F1 D dates == [01-05, 01-08, 01-09] | got ['2024-01-05', '2024-01-07', '2024-01-08']
[FAIL] F1 D(01-08) = first open (Sun 17:01) / max / min / last close (Mon 16:00) / sum | got [102.0, 106.0, 101.0, 103.5, 7.0] exp [102.0, 109.0, 101.0, 105.5, 18.0]
[PASS] F1 D(01-05) aggregation
[PASS] F1 15m labels (right-labelled, ceil 15 min) | got ['2024-01-05 16:00:00', '2024-01-07 17:15:00', '2024-01-08 09:00:00', '2024-01-08 16:00:00', '2024-01-08 17:15:00']
[FAIL] F1 15m trading dates | got ['2024-01-05', '2024-01-07', '2024-01-08', '2024-01-08', '2024-01-08']
[PASS] F1 15m bar 16:00 (Fri) = rows 0..1 aggregated | got [100.0, 104.0, 99.0, 101.5, 3.0]
[FAIL] F2 trading_date 16:59 / 17:00 / 17:01 == 01-10 / 01-10 / 01-11 | got ['2024-01-10', '2024-01-10', '2024-01-10']
[PASS] F2 halt (16:00, 17:00]: 16:00 F, 16:01 T, 16:59 T, 17:00 T, 17:01 F | got [False, True, True, True, False]
[PASS] F2 a bar closing at 16:59 is rejected by the session builder
[PASS] F2 a bar closing at 17:00 is rejected by the session builder
[PASS] F2 16:00 and 17:01 bars are accepted
[FAIL] F2 halt=None: 16:59 and 17:00 stay on 01-10, 17:01 on 01-11
[FAIL] F3 March DST week (naive CT): roll stays at 17:00 wall clock | got ['2024-03-08', '2024-03-08', '2024-03-10', '2024-03-11', '2024-03-11', '2024-03-11', '2024-03-12']
[FAIL] F4 November DST week (naive CT) | got ['2024-11-01', '2024-11-03', '2024-11-04', '2024-11-04', '2024-11-05']
[PASS] F3 UTC->CT: 22:00Z Fri = 16:00 CST; 22:01Z Sun = 17:01 CDT; 21:00Z Mon = 16:00 CDT; 22:01Z Mon = 17:01 CDT | got ['2024-03-08 16:00:00', '2024-03-10 17:01:00', '2024-03-11 16:00:00', '2024-03-11 17:01:00']
[PASS] F4 UTC->CT: 21:00Z Fri = 16:00 CDT; 23:01Z Sun = 17:01 CST; 22:00Z Mon = 16:00 CST | got ['2024-11-01 16:00:00', '2024-11-03 17:01:00', '2024-11-04 16:00:00']
[FAIL] F3 UTC input trading dates == [03-08, 03-11, 03-11, 03-12] | got ['2024-03-08', '2024-03-10', '2024-03-11', '2024-03-11']
[PASS] F5 15m labels: 15:45 alone, 15:46..16:00 -> 16:00 | got ['2024-01-10 15:45:00', '2024-01-10 16:00:00']
[PASS] F5 16:00 15m bar aggregation (first open / max / min / last close / sum)
[PASS] F5 16:00 bar keeps its calendar date
[PASS] F5 D bar close == close of the 16:00 bar
[PASS] F6 midnight: labels [00:00, 00:00 -> one bar, 00:15] | got ['2024-01-09 00:00:00', '2024-01-09 00:15:00']
[PASS] F6 midnight: all three on trading date 01-09
[PASS] F6 15m bar counts (Bars) == [2, 1] | got [2, 1]
--- BT14 sessions and frames: 25 checks, 9 failed: F1 trading dates; F1 D dates == [01-05, 01-08, 01-09]; F1 D(01-08) = first open (Sun 17:01) / max / min / last close (Mon 16:00) / sum; F1 15m trading dates; F2 trading_date 16:59 / 17:00 / 17:01 == 01-10 / 01-10 / 01-11; F2 halt=None: 16:59 and 17:00 stay on 01-10, 17:01 on 01-11; F3 March DST week (naive CT): roll stays at 17:00 wall clock; F4 November DST week (naive CT); F3 UTC input trading dates == [03-08, 03-11, 03-11, 03-12]
rc=1  wall=1.82s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt14_floor data.py label = m1s["BarTime"].dt.ceil( label = m1s["BarTime"].dt.floor(
mutant: %SCRATCH%\mut_bt14_floor\qibt\data.py
  - label = m1s["BarTime"].dt.ceil(
  + label = m1s["BarTime"].dt.floor(
sha256 original data.py before 6fe54619ed0317be8f860a4e9aa23ff043bf4bd15d140311203210a6817d080c
sha256 original data.py after  6fe54619ed0317be8f860a4e9aa23ff043bf4bd15d140311203210a6817d080c
sha256 mutant   data.py        c3742cf5106569f5e57d9ec6d3667a2ce76d35b3b70bbd942d4f8ff7cbb85fea
rc=0  wall=0.21s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt14_sessions.py --qibt-root %SCRATCH%\mut_bt14_floor
qibt loaded from: %SCRATCH%\mut_bt14_floor\qibt\__init__.py
=== BT14 sessions and frames ===
[PASS] F1 trading dates | got ['2024-01-05', '2024-01-05', '2024-01-08', '2024-01-08', '2024-01-08', '2024-01-08', '2024-01-09']
[PASS] F1 D dates == [01-05, 01-08, 01-09] | got ['2024-01-05', '2024-01-08', '2024-01-09']
[PASS] F1 D(01-08) = first open (Sun 17:01) / max / min / last close (Mon 16:00) / sum | got [102.0, 109.0, 101.0, 105.5, 18.0] exp [102.0, 109.0, 101.0, 105.5, 18.0]
[PASS] F1 D(01-05) aggregation
[FAIL] F1 15m labels (right-labelled, ceil 15 min) | got ['2024-01-05 15:45:00', '2024-01-05 16:00:00', '2024-01-07 17:00:00', '2024-01-08 09:00:00', '2024-01-08 16:00:00', '2024-01-08 17:00:00']
[FAIL] F1 15m trading dates | got ['2024-01-05', '2024-01-05', '2024-01-08', '2024-01-08', '2024-01-08', '2024-01-09']
[FAIL] F1 15m bar 16:00 (Fri) = rows 0..1 aggregated | got [100.0, 102.0, 99.0, 100.5, 1.0]
[PASS] F2 trading_date 16:59 / 17:00 / 17:01 == 01-10 / 01-10 / 01-11 | got ['2024-01-10', '2024-01-10', '2024-01-11']
[PASS] F2 halt (16:00, 17:00]: 16:00 F, 16:01 T, 16:59 T, 17:00 T, 17:01 F | got [False, True, True, True, False]
[PASS] F2 a bar closing at 16:59 is rejected by the session builder
[PASS] F2 a bar closing at 17:00 is rejected by the session builder
[PASS] F2 16:00 and 17:01 bars are accepted
[PASS] F2 halt=None: 16:59 and 17:00 stay on 01-10, 17:01 on 01-11
[PASS] F3 March DST week (naive CT): roll stays at 17:00 wall clock | got ['2024-03-08', '2024-03-08', '2024-03-11', '2024-03-11', '2024-03-11', '2024-03-12', '2024-03-12']
[PASS] F4 November DST week (naive CT) | got ['2024-11-01', '2024-11-04', '2024-11-04', '2024-11-05', '2024-11-05']
[PASS] F3 UTC->CT: 22:00Z Fri = 16:00 CST; 22:01Z Sun = 17:01 CDT; 21:00Z Mon = 16:00 CDT; 22:01Z Mon = 17:01 CDT | got ['2024-03-08 16:00:00', '2024-03-10 17:01:00', '2024-03-11 16:00:00', '2024-03-11 17:01:00']
[PASS] F4 UTC->CT: 21:00Z Fri = 16:00 CDT; 23:01Z Sun = 17:01 CST; 22:00Z Mon = 16:00 CST | got ['2024-11-01 16:00:00', '2024-11-03 17:01:00', '2024-11-04 16:00:00']
[PASS] F3 UTC input trading dates == [03-08, 03-11, 03-11, 03-12] | got ['2024-03-08', '2024-03-11', '2024-03-11', '2024-03-12']
[PASS] F5 15m labels: 15:45 alone, 15:46..16:00 -> 16:00 | got ['2024-01-10 15:45:00', '2024-01-10 16:00:00']
[FAIL] F5 16:00 15m bar aggregation (first open / max / min / last close / sum)
[PASS] F5 16:00 bar keeps its calendar date
[PASS] F5 D bar close == close of the 16:00 bar
[FAIL] F6 midnight: labels [00:00, 00:00 -> one bar, 00:15] | got ['2024-01-08 23:45:00', '2024-01-09 00:00:00']
[PASS] F6 midnight: all three on trading date 01-09
[FAIL] F6 15m bar counts (Bars) == [2, 1] | got [1, 2]
--- BT14 sessions and frames: 25 checks, 6 failed: F1 15m labels (right-labelled, ceil 15 min); F1 15m trading dates; F1 15m bar 16:00 (Fri) = rows 0..1 aggregated; F5 16:00 15m bar aggregation (first open / max / min / last close / sum); F6 midnight: labels [00:00, 00:00 -> one bar, 00:15]; F6 15m bar counts (Bars) == [2, 1]
rc=1  wall=1.66s
```

### BT15 - QS_* reproduce QI values and trade per rules.yaml
Verdict: **pending**. The Strategy Analyzer vs engine trade-list comparison is user-run. Compile
part: rc=0 for all 25 QS_* and 27 QI_* files. Falsifier: an undefined method in QS_RSI14 gives
CS0103, rc=1.
```text
$ env OUT=$SCRATCH/compile/all.dll bash validation/probes/compile_probe.sh strategies/QS_ATRRegime.cs strategies/QS_BollingerPctB.cs strategies/QS_CompositeVol.cs strategies/QS_ConnorsRSI.cs strategies/QS_ConsecDays.cs strategies/QS_EMACross.cs strategies/QS_HedgingPressure.cs strategies/QS_IBS.cs strategies/QS_LiquiditySweep.cs strategies/QS_MACDHistogram.cs strategies/QS_OrderFlowPlus.cs strategies/QS_OvernightGap.cs strategies/QS_RSI14.cs strategies/QS_RSI2.cs strategies/QS_RVZScore.cs strategies/QS_SMA200Trend.cs strategies/QS_SMC.cs strategies/QS_StochFade.cs strategies/QS_TurnOfMonth.cs strategies/QS_TurnaroundTuesday.cs strategies/QS_VRPProxy.cs strategies/QS_VWAPDistance.cs strategies/QS_VolumeDelta.cs strategies/QS_VolumeSpike.cs strategies/QS_WideRangeBar.cs indicators/QI_ATRRegime.cs indicators/QI_BollingerPctB.cs indicators/QI_ChopIndex.cs indicators/QI_CompositeVol.cs indicators/QI_ConnorsRSI.cs indicators/QI_ConsecDays.cs indicators/QI_EMACross.cs indicators/QI_HedgingPressure.cs indicators/QI_IBS.cs indicators/QI_KeyLevels.cs indicators/QI_LiquiditySweep.cs indicators/QI_MACDHistogram.cs indicators/QI_OrderFlowPlus.cs indicators/QI_OvernightGap.cs indicators/QI_RSI14.cs indicators/QI_RSI2.cs indicators/QI_RVZScore.cs indicators/QI_SMA200Trend.cs indicators/QI_SMC.cs indicators/QI_StochFade.cs indicators/QI_TurnOfMonth.cs indicators/QI_TurnaroundTuesday.cs indicators/QI_VRPProxy.cs indicators/QI_VWAPDistance.cs indicators/QI_VolumeDelta.cs indicators/QI_VolumeSpike.cs indicators/QI_WideRangeBar.cs
csc: /c/Program Files/dotnet/sdk/8.0.100/Roslyn/bincore/csc.dll
out: $SCRATCH/compile/all.dll
refs: 17  sources: 52
rc=0
rc=0  wall=3.64s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py strategies %SCRATCH%\mut_bt15_typo QS_RSI14.cs EnterLong(DefaultQuantity, "QS_L"); EnterLongTypo(DefaultQuantity, "QS_L");
mutant: %SCRATCH%\mut_bt15_typo\strategies\QS_RSI14.cs
  - EnterLong(DefaultQuantity, "QS_L");
  + EnterLongTypo(DefaultQuantity, "QS_L");
sha256 original QS_RSI14.cs before 9a153e97094f7b42761078a4d9eef1c384737bf216dfa455c49050b1fb2abfa9
sha256 original QS_RSI14.cs after  9a153e97094f7b42761078a4d9eef1c384737bf216dfa455c49050b1fb2abfa9
sha256 mutant   QS_RSI14.cs        66ff2e6e5faa11e106e674c8500fed554ecd6bb898c55af6f2618ddee1edeaa0
rc=0  wall=0.15s
```
```text
$ env OUT=$SCRATCH/compile/rsi14.dll bash validation/probes/compile_probe.sh strategies/QS_RSI14.cs
csc: /c/Program Files/dotnet/sdk/8.0.100/Roslyn/bincore/csc.dll
out: $SCRATCH/compile/rsi14.dll
refs: 17  sources: 1
rc=0
rc=0  wall=1.23s
```
```text
$ env OUT=$SCRATCH/compile/rsi14_mut.dll bash validation/probes/compile_probe.sh $SCRATCH/mut_bt15_typo/strategies/QS_RSI14.cs
csc: /c/Program Files/dotnet/sdk/8.0.100/Roslyn/bincore/csc.dll
out: $SCRATCH/compile/rsi14_mut.dll
refs: 17  sources: 1
%SCRATCH%\mut_bt15_typo\strategies\QS_RSI14.cs(153,5): error CS0103: The name 'EnterLongTypo' does not exist in the current context
rc=1
rc=1  wall=1.25s
```

### BT16 - no orders in State.Realtime while BacktestOnly = true (default)
Verdict: **CONFIRMED (static part)**. The playback check is pending (user-run). Limit of the static
probe: it proves the guard precedes every order call. It cannot say whether NinjaTrader calls
OnBarUpdate in states other than Realtime (for example Transition), and whether working
historical orders carry over. Those are documentation questions for Channel A and the playback check.
```text
$ python -I -B validation/probes/channel_b_backtest/bt16_guards.py
strategies: C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators\strategies
=== BT16 BacktestOnly guards ===
[PASS] found QS_*.cs files | 25 files
[PASS] QS_ATRRegime.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_BollingerPctB.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_CompositeVol.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_ConnorsRSI.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_ConsecDays.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_EMACross.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_HedgingPressure.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_IBS.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_LiquiditySweep.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_MACDHistogram.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_OrderFlowPlus.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_OvernightGap.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_RSI14.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_RSI2.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_RVZScore.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_SMA200Trend.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_SMC.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_StochFade.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_TurnOfMonth.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_TurnaroundTuesday.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VRPProxy.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VWAPDistance.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VolumeDelta.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VolumeSpike.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_WideRangeBar.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
order calls scanned: 100
--- BT16 BacktestOnly guards: 26 checks, 0 failed
rc=0  wall=0.20s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py strategies %SCRATCH%\mut_bt16_noguard QS_RSI14.cs \t\t\tif (BacktestOnly && State == State.Realtime) return;\n 
mutant: %SCRATCH%\mut_bt16_noguard\strategies\QS_RSI14.cs
  - if (BacktestOnly && State == State.Realtime) return;
  + 
sha256 original QS_RSI14.cs before 9a153e97094f7b42761078a4d9eef1c384737bf216dfa455c49050b1fb2abfa9
sha256 original QS_RSI14.cs after  9a153e97094f7b42761078a4d9eef1c384737bf216dfa455c49050b1fb2abfa9
sha256 mutant   QS_RSI14.cs        d84ef8d85df679b8eebf341ac04fe1f1e41284831252e175a0bfd8e1092f3835
rc=0  wall=0.14s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt16_guards.py --strategies %SCRATCH%\mut_bt16_noguard\strategies
strategies: %SCRATCH%\mut_bt16_noguard\strategies
=== BT16 BacktestOnly guards ===
[PASS] found QS_*.cs files | 25 files
[PASS] QS_ATRRegime.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_BollingerPctB.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_CompositeVol.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_ConnorsRSI.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_ConsecDays.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_EMACross.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_HedgingPressure.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_IBS.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_LiquiditySweep.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_MACDHistogram.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_OrderFlowPlus.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_OvernightGap.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[FAIL] QS_RSI14.cs: 4 order call(s) guarded; default true; single assignment | problems=['EnterLong in ApplyRule() whose first statement is not the guard', 'EnterShort in ApplyRule() whose first statement is not the guard', 'ExitLong in ApplyRule() whose first statement is not the guard', 'ExitShort in ApplyRule() whose first statement is not the guard'] sd_default_true=True assignments=['true'] property=True
[PASS] QS_RSI2.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_RVZScore.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_SMA200Trend.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_SMC.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_StochFade.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_TurnOfMonth.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_TurnaroundTuesday.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VRPProxy.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VWAPDistance.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VolumeDelta.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VolumeSpike.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_WideRangeBar.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
order calls scanned: 100
--- BT16 BacktestOnly guards: 26 checks, 1 failed: QS_RSI14.cs: 4 order call(s) guarded; default true; single assignment
rc=1  wall=0.46s
```
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py strategies %SCRATCH%\mut_bt16_deffalse QS_SMC.cs BacktestOnly\t\t\t\t= true; BacktestOnly\t\t\t\t= false;
mutant: %SCRATCH%\mut_bt16_deffalse\strategies\QS_SMC.cs
  - BacktestOnly				= true;
  + BacktestOnly				= false;
sha256 original QS_SMC.cs before 4f9543ad2c04d620b72b0b2bef3ad3ab8870834dcdc4b54d24cdcea09e91d5fc
sha256 original QS_SMC.cs after  4f9543ad2c04d620b72b0b2bef3ad3ab8870834dcdc4b54d24cdcea09e91d5fc
sha256 mutant   QS_SMC.cs        9468aab513beeecbc101c00d0b82dffa5a18a61484379110d3f0463ee4ff50c5
rc=0  wall=0.19s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt16_guards.py --strategies %SCRATCH%\mut_bt16_deffalse\strategies
strategies: %SCRATCH%\mut_bt16_deffalse\strategies
=== BT16 BacktestOnly guards ===
[PASS] found QS_*.cs files | 25 files
[PASS] QS_ATRRegime.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_BollingerPctB.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_CompositeVol.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_ConnorsRSI.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_ConsecDays.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_EMACross.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_HedgingPressure.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_IBS.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_LiquiditySweep.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_MACDHistogram.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_OrderFlowPlus.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_OvernightGap.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_RSI14.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_RSI2.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_RVZScore.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_SMA200Trend.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[FAIL] QS_SMC.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=False assignments=['false'] property=True
[PASS] QS_StochFade.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_TurnOfMonth.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_TurnaroundTuesday.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VRPProxy.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VWAPDistance.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VolumeDelta.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_VolumeSpike.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
[PASS] QS_WideRangeBar.cs: 4 order call(s) guarded; default true; single assignment | problems=[] sd_default_true=True assignments=['true'] property=True
order calls scanned: 100
--- BT16 BacktestOnly guards: 26 checks, 1 failed: QS_SMC.cs: 4 order call(s) guarded; default true; single assignment
rc=1  wall=0.42s
```

### BT17 - P1 covers 2020-01-03 -> 2026-02-24, no gap > 3 trading dates, no duplicates
Verdict: **REFUTED** (gap condition). These conditions hold: first and last trading date; 0
duplicated BarTime (also 0 before de-duplication: the six files do not overlap); strictly
increasing times; the loaded P1 equals my own raw re-parse exactly. No holiday calendar is
assumed: the gap is the count of Mon-Fri dates between consecutive trading dates. All gaps >= 1
are listed. The raw files were checked directly: no row of any kind (bar or signal) in any
`MES_1min_*.csv` has a BarTime between 2023-04-05 13:04 and 2023-04-16 17:00. The check prints
one count per file only when a file has such rows:
```text
$ cd C:\Users\rajib\OneDrive\Docs\futures_data\ninja_trader_signal_data\data
$ awk -F, 'FNR>1 && $2 >= "2023-04-05 13:04:00" && $2 <= "2023-04-16 17:00:00" {n[FILENAME]++} END {for (f in n) print f, n[f]; print "files scanned:", ARGC-1}' MES_1min_*.csv
files scanned: 6
rc=0
```
Independent raw re-parse (PROTOCOL 2 layout; no qibt):
```text
$ python -I -B validation/probes/channel_b_backtest/raw_p1_parse.py %SCRATCH%\raw_p1.pkl
MES_1min_20200101_20260201.csv: header 53 fields, bar rows 373412, signal rows 238165, shifts {1: 373412}, bad rows 0, within-file dup BarTime 0, non-increasing steps 0, first 2020-01-03 16:00:00, last 2021-02-01 11:59:00
MES_1min_20210131_20220131.csv: header 53 fields, bar rows 351347, signal rows 220341, shifts {1: 351347}, bad rows 0, within-file dup BarTime 0, non-increasing steps 0, first 2021-02-02 16:00:00, last 2022-01-31 15:59:00
MES_1min_20220130_20230131.csv: header 53 fields, bar rows 352006, signal rows 232490, shifts {1: 352006}, bad rows 0, within-file dup BarTime 0, non-increasing steps 0, first 2022-02-01 16:00:00, last 2023-01-31 15:59:00
MES_1min_20230131_20240229.csv: header 53 fields, bar rows 371074, signal rows 232125, shifts {1: 371074}, bad rows 0, within-file dup BarTime 0, non-increasing steps 0, first 2023-02-02 16:00:00, last 2024-02-29 15:59:00
MES_1min_20240229_20250331.csv: header 53 fields, bar rows 379144, signal rows 237934, shifts {1: 379144}, bad rows 0, within-file dup BarTime 0, non-increasing steps 0, first 2024-03-04 16:00:00, last 2025-03-31 15:59:00
MES_1min_20250331_20260224.csv: header 53 fields, bar rows 315408, signal rows 199935, shifts {1: 315408}, bad rows 0, within-file dup BarTime 0, non-increasing steps 0, first 2025-04-02 16:00:00, last 2026-02-24 14:53:00
concatenated rows 2142391, duplicates on BarTime 0, after de-dup 2142391
bad rows total 0; wrote %SCRATCH%\raw_p1.pkl (2142391 bars) in 25.7s
rc=0  wall=26.69s
```
Probe (v1 cache) and the same probe pinned to v1 plus the raw re-parse:
```text
$ python -I -B validation/probes/channel_b_backtest/bt17_integrity.py --raw %SCRATCH%\raw_p1.pkl
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
source: qibt.data.load_p1() cache=hit, 2142391 bars
=== BT17 P1 data integrity ===
bars 2142391, first bar 2020-01-03T16:00:00.000000000, last bar 2026-02-24T14:53:00.000000000, trading dates 1578 (2020-01-03 -> 2026-02-24)
[PASS] first trading date == 2020-01-03 | 2020-01-03
[PASS] last trading date == 2026-02-24 | 2026-02-24
[PASS] no duplicated BarTime | duplicates=0
[PASS] BarTime strictly increasing | non-increasing steps=0
trading dates on Sat/Sun: 0 []
gaps with >= 1 missing weekday (19):
  2020-04-09 (last bar 2020-04-09 16:00:00) -> 2020-04-13 (first bar 2020-04-12 17:01:00): 1 missing weekday(s)
  2020-12-24 (last bar 2020-12-24 12:15:00) -> 2020-12-28 (first bar 2020-12-27 17:01:00): 1 missing weekday(s)
  2020-12-31 (last bar 2020-12-31 16:00:00) -> 2021-01-04 (first bar 2021-01-03 17:01:00): 1 missing weekday(s)
  2021-12-23 (last bar 2021-12-23 16:00:00) -> 2021-12-27 (first bar 2021-12-26 17:01:00): 1 missing weekday(s)
  2022-04-14 (last bar 2022-04-14 16:00:00) -> 2022-04-18 (first bar 2022-04-17 17:01:00): 1 missing weekday(s)
  2022-12-23 (last bar 2022-12-23 16:00:00) -> 2022-12-27 (first bar 2022-12-26 17:01:00): 1 missing weekday(s)
  2022-12-30 (last bar 2022-12-30 16:00:00) -> 2023-01-03 (first bar 2023-01-02 17:01:00): 1 missing weekday(s)
  2023-01-31 (last bar 2023-01-31 15:59:00) -> 2023-02-02 (first bar 2023-02-02 16:00:00): 1 missing weekday(s)
  2023-04-05 (last bar 2023-04-05 13:03:00) -> 2023-04-17 (first bar 2023-04-16 17:01:00): 7 missing weekday(s)  <-- > 3
  2023-12-22 (last bar 2023-12-22 16:00:00) -> 2023-12-26 (first bar 2023-12-25 17:01:00): 1 missing weekday(s)
  2023-12-29 (last bar 2023-12-29 16:00:00) -> 2024-01-02 (first bar 2024-01-01 17:01:00): 1 missing weekday(s)
  2024-02-29 (last bar 2024-02-29 15:59:00) -> 2024-03-04 (first bar 2024-03-04 16:00:00): 1 missing weekday(s)
  2024-03-28 (last bar 2024-03-28 16:00:00) -> 2024-04-01 (first bar 2024-03-31 17:01:00): 1 missing weekday(s)
  2024-12-24 (last bar 2024-12-24 12:15:00) -> 2024-12-26 (first bar 2024-12-25 17:01:00): 1 missing weekday(s)
  2024-12-31 (last bar 2024-12-31 16:00:00) -> 2025-01-02 (first bar 2025-01-01 17:01:00): 1 missing weekday(s)
  2025-03-31 (last bar 2025-03-31 15:59:00) -> 2025-04-02 (first bar 2025-04-02 16:00:00): 1 missing weekday(s)
  2025-04-17 (last bar 2025-04-17 16:00:00) -> 2025-04-21 (first bar 2025-04-20 17:01:00): 1 missing weekday(s)
  2025-12-24 (last bar 2025-12-24 12:15:00) -> 2025-12-26 (first bar 2025-12-25 17:01:00): 1 missing weekday(s)
  2025-12-31 (last bar 2025-12-31 16:00:00) -> 2026-01-02 (first bar 2026-01-01 17:01:00): 1 missing weekday(s)
[FAIL] no gap > 3 trading dates | gaps > 3: [('2023-04-05 -> 2023-04-17', 7)]
OBSERVATION sessions with < 300 one-minute bars (6):
  2020-01-03: 1 bars (2020-01-03 16:00:00 -> 2020-01-03 16:00:00)
  2021-02-02: 1 bars (2021-02-02 16:00:00 -> 2021-02-02 16:00:00)
  2022-02-01: 1 bars (2022-02-01 16:00:00 -> 2022-02-01 16:00:00)
  2023-02-02: 1 bars (2023-02-02 16:00:00 -> 2023-02-02 16:00:00)
  2024-03-04: 1 bars (2024-03-04 16:00:00 -> 2024-03-04 16:00:00)
  2025-04-02: 1 bars (2025-04-02 16:00:00 -> 2025-04-02 16:00:00)
[PASS] loaded P1 == Channel B raw re-parse (BarTime + OHLCV exact) | raw 2142391 bars vs loaded 2142391
--- BT17 P1 data integrity: 6 checks, 1 failed: no gap > 3 trading dates
rc=1  wall=1.64s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt17_integrity.py --qibt-root %SCRATCH%\pristine_v1 --pkl %SCRATCH%\raw_p1.pkl
qibt loaded from: %SCRATCH%\pristine_v1\qibt\__init__.py
source: pickle %SCRATCH%\raw_p1.pkl, 2142391 bars
=== BT17 P1 data integrity ===
bars 2142391, first bar 2020-01-03T16:00:00.000000000, last bar 2026-02-24T14:53:00.000000000, trading dates 1578 (2020-01-03 -> 2026-02-24)
[PASS] first trading date == 2020-01-03 | 2020-01-03
[PASS] last trading date == 2026-02-24 | 2026-02-24
[PASS] no duplicated BarTime | duplicates=0
[PASS] BarTime strictly increasing | non-increasing steps=0
trading dates on Sat/Sun: 0 []
gaps with >= 1 missing weekday (19):
  2020-04-09 (last bar 2020-04-09 16:00:00) -> 2020-04-13 (first bar 2020-04-12 17:01:00): 1 missing weekday(s)
  2020-12-24 (last bar 2020-12-24 12:15:00) -> 2020-12-28 (first bar 2020-12-27 17:01:00): 1 missing weekday(s)
  2020-12-31 (last bar 2020-12-31 16:00:00) -> 2021-01-04 (first bar 2021-01-03 17:01:00): 1 missing weekday(s)
  2021-12-23 (last bar 2021-12-23 16:00:00) -> 2021-12-27 (first bar 2021-12-26 17:01:00): 1 missing weekday(s)
  2022-04-14 (last bar 2022-04-14 16:00:00) -> 2022-04-18 (first bar 2022-04-17 17:01:00): 1 missing weekday(s)
  2022-12-23 (last bar 2022-12-23 16:00:00) -> 2022-12-27 (first bar 2022-12-26 17:01:00): 1 missing weekday(s)
  2022-12-30 (last bar 2022-12-30 16:00:00) -> 2023-01-03 (first bar 2023-01-02 17:01:00): 1 missing weekday(s)
  2023-01-31 (last bar 2023-01-31 15:59:00) -> 2023-02-02 (first bar 2023-02-02 16:00:00): 1 missing weekday(s)
  2023-04-05 (last bar 2023-04-05 13:03:00) -> 2023-04-17 (first bar 2023-04-16 17:01:00): 7 missing weekday(s)  <-- > 3
  2023-12-22 (last bar 2023-12-22 16:00:00) -> 2023-12-26 (first bar 2023-12-25 17:01:00): 1 missing weekday(s)
  2023-12-29 (last bar 2023-12-29 16:00:00) -> 2024-01-02 (first bar 2024-01-01 17:01:00): 1 missing weekday(s)
  2024-02-29 (last bar 2024-02-29 15:59:00) -> 2024-03-04 (first bar 2024-03-04 16:00:00): 1 missing weekday(s)
  2024-03-28 (last bar 2024-03-28 16:00:00) -> 2024-04-01 (first bar 2024-03-31 17:01:00): 1 missing weekday(s)
  2024-12-24 (last bar 2024-12-24 12:15:00) -> 2024-12-26 (first bar 2024-12-25 17:01:00): 1 missing weekday(s)
  2024-12-31 (last bar 2024-12-31 16:00:00) -> 2025-01-02 (first bar 2025-01-01 17:01:00): 1 missing weekday(s)
  2025-03-31 (last bar 2025-03-31 15:59:00) -> 2025-04-02 (first bar 2025-04-02 16:00:00): 1 missing weekday(s)
  2025-04-17 (last bar 2025-04-17 16:00:00) -> 2025-04-21 (first bar 2025-04-20 17:01:00): 1 missing weekday(s)
  2025-12-24 (last bar 2025-12-24 12:15:00) -> 2025-12-26 (first bar 2025-12-25 17:01:00): 1 missing weekday(s)
  2025-12-31 (last bar 2025-12-31 16:00:00) -> 2026-01-02 (first bar 2026-01-01 17:01:00): 1 missing weekday(s)
[FAIL] no gap > 3 trading dates | gaps > 3: [('2023-04-05 -> 2023-04-17', 7)]
OBSERVATION sessions with < 300 one-minute bars (6):
  2020-01-03: 1 bars (2020-01-03 16:00:00 -> 2020-01-03 16:00:00)
  2021-02-02: 1 bars (2021-02-02 16:00:00 -> 2021-02-02 16:00:00)
  2022-02-01: 1 bars (2022-02-01 16:00:00 -> 2022-02-01 16:00:00)
  2023-02-02: 1 bars (2023-02-02 16:00:00 -> 2023-02-02 16:00:00)
  2024-03-04: 1 bars (2024-03-04 16:00:00 -> 2024-03-04 16:00:00)
  2025-04-02: 1 bars (2025-04-02 16:00:00 -> 2025-04-02 16:00:00)
--- BT17 P1 data integrity: 5 checks, 1 failed: no gap > 3 trading dates
rc=1
```
Anti-falsifier: the gap logic passes on a clean calendar and reports a 4-weekday hole as 4. This
shows the refutation is not a probe artefact. Falsifier: an injected duplicate is caught.
```text
$ python -I -B validation/probes/channel_b_backtest/bt17_integrity.py --qibt-root %SCRATCH%\pristine_v1 --control
qibt loaded from: %SCRATCH%\pristine_v1\qibt\__init__.py
=== BT17 control: synthetic weekday calendar with only 1-day holidays ===
[PASS] control: max gap == 1 (so the probe can PASS) | gaps=[(Timestamp('2021-04-01 00:00:00'), Timestamp('2021-04-05 00:00:00'), 1), (Timestamp('2021-12-23 00:00:00'), Timestamp('2021-12-27 00:00:00'), 1)]
[PASS] control: a 4-weekday hole is reported as gap 4 | gaps=[(Timestamp('2021-06-04 00:00:00'), Timestamp('2021-06-11 00:00:00'), 4)]
--- BT17 control: synthetic weekday calendar with only 1-day holidays: 2 checks, 0 failed
rc=0
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt17_integrity.py --qibt-root %SCRATCH%\pristine_v1 --pkl %SCRATCH%\raw_p1.pkl --inject dup
qibt loaded from: %SCRATCH%\pristine_v1\qibt\__init__.py
source: pickle %SCRATCH%\raw_p1.pkl, 2142391 bars
INJECTED: duplicated bar 2020-01-06 09:45:00
=== BT17 P1 data integrity ===
bars 2142392, first bar 2020-01-03T16:00:00.000000000, last bar 2026-02-24T14:53:00.000000000, trading dates 1578 (2020-01-03 -> 2026-02-24)
[PASS] first trading date == 2020-01-03 | 2020-01-03
[PASS] last trading date == 2026-02-24 | 2026-02-24
[FAIL] no duplicated BarTime | duplicates=1
[FAIL] BarTime strictly increasing | non-increasing steps=1
trading dates on Sat/Sun: 0 []
gaps with >= 1 missing weekday (19):
  2020-04-09 (last bar 2020-04-09 16:00:00) -> 2020-04-13 (first bar 2020-04-12 17:01:00): 1 missing weekday(s)
  2020-12-24 (last bar 2020-12-24 12:15:00) -> 2020-12-28 (first bar 2020-12-27 17:01:00): 1 missing weekday(s)
  2020-12-31 (last bar 2020-12-31 16:00:00) -> 2021-01-04 (first bar 2021-01-03 17:01:00): 1 missing weekday(s)
  2021-12-23 (last bar 2021-12-23 16:00:00) -> 2021-12-27 (first bar 2021-12-26 17:01:00): 1 missing weekday(s)
  2022-04-14 (last bar 2022-04-14 16:00:00) -> 2022-04-18 (first bar 2022-04-17 17:01:00): 1 missing weekday(s)
  2022-12-23 (last bar 2022-12-23 16:00:00) -> 2022-12-27 (first bar 2022-12-26 17:01:00): 1 missing weekday(s)
  2022-12-30 (last bar 2022-12-30 16:00:00) -> 2023-01-03 (first bar 2023-01-02 17:01:00): 1 missing weekday(s)
  2023-01-31 (last bar 2023-01-31 15:59:00) -> 2023-02-02 (first bar 2023-02-02 16:00:00): 1 missing weekday(s)
  2023-04-05 (last bar 2023-04-05 13:03:00) -> 2023-04-17 (first bar 2023-04-16 17:01:00): 7 missing weekday(s)  <-- > 3
  2023-12-22 (last bar 2023-12-22 16:00:00) -> 2023-12-26 (first bar 2023-12-25 17:01:00): 1 missing weekday(s)
  2023-12-29 (last bar 2023-12-29 16:00:00) -> 2024-01-02 (first bar 2024-01-01 17:01:00): 1 missing weekday(s)
  2024-02-29 (last bar 2024-02-29 15:59:00) -> 2024-03-04 (first bar 2024-03-04 16:00:00): 1 missing weekday(s)
  2024-03-28 (last bar 2024-03-28 16:00:00) -> 2024-04-01 (first bar 2024-03-31 17:01:00): 1 missing weekday(s)
  2024-12-24 (last bar 2024-12-24 12:15:00) -> 2024-12-26 (first bar 2024-12-25 17:01:00): 1 missing weekday(s)
  2024-12-31 (last bar 2024-12-31 16:00:00) -> 2025-01-02 (first bar 2025-01-01 17:01:00): 1 missing weekday(s)
  2025-03-31 (last bar 2025-03-31 15:59:00) -> 2025-04-02 (first bar 2025-04-02 16:00:00): 1 missing weekday(s)
  2025-04-17 (last bar 2025-04-17 16:00:00) -> 2025-04-21 (first bar 2025-04-20 17:01:00): 1 missing weekday(s)
  2025-12-24 (last bar 2025-12-24 12:15:00) -> 2025-12-26 (first bar 2025-12-25 17:01:00): 1 missing weekday(s)
  2025-12-31 (last bar 2025-12-31 16:00:00) -> 2026-01-02 (first bar 2026-01-01 17:01:00): 1 missing weekday(s)
[FAIL] no gap > 3 trading dates | gaps > 3: [('2023-04-05 -> 2023-04-17', 7)]
OBSERVATION sessions with < 300 one-minute bars (6):
  2020-01-03: 1 bars (2020-01-03 16:00:00 -> 2020-01-03 16:00:00)
  2021-02-02: 1 bars (2021-02-02 16:00:00 -> 2021-02-02 16:00:00)
  2022-02-01: 1 bars (2022-02-01 16:00:00 -> 2022-02-01 16:00:00)
  2023-02-02: 1 bars (2023-02-02 16:00:00 -> 2023-02-02 16:00:00)
  2024-03-04: 1 bars (2024-03-04 16:00:00 -> 2024-03-04 16:00:00)
  2025-04-02: 1 bars (2025-04-02 16:00:00 -> 2025-04-02 16:00:00)
--- BT17 P1 data integrity: 5 checks, 3 failed: no duplicated BarTime; BarTime strictly increasing; no gap > 3 trading dates
rc=1
```

### BT18 - ranking is deterministic
Verdict: **CONFIRMED**. Three full CLI runs: two with the v1 cache, one with `--no-cache` (raw CSV
re-read through the v1 loader). Each run is a separate `python -I` process with random hash seeds.
All output CSVs are byte-identical. REPORT.md is identical except the run-time, wall-time and
dataset/cache lines. run1's CSVs are byte-identical to the committed `results/` (now
`results/v1_last_trade/`, same sha256).
```text
$ python -I -B -m qibt.cli run --dataset P1 --costs 1 --out %SCRATCH%\bt18_run1
loaded P1: 2142391 bars in 0.0s
  HedgingPressure    D    SR  -0.197  net   -2341.25  (0.0s)
  IBS                D    SR   0.566  net    8925.00  (0.0s)
  RSI2               D    SR   0.649  net   10634.00  (0.0s)
  ConnorsRSI         D    SR  -0.226  net   -2163.75  (0.0s)
  StochFade          D    SR   0.097  net    1616.50  (0.0s)
  RVZScore           D    SR   0.171  net    2092.75  (0.0s)
  CompositeVol       D    SR   0.280  net    2286.25  (0.0s)
  TurnOfMonth        D    SR  -0.266  net   -2728.00  (0.0s)
  ConsecDays         D    SR   0.569  net    4912.00  (0.0s)
  OvernightGap       D    SR  -0.779  net   -4994.25  (0.0s)
  BollingerPctB      15m  SR  -3.716  net  -36167.75  (0.1s)
  TurnaroundTuesday  D    SR  -0.449  net   -3634.75  (0.0s)
  RSI14              D    SR   0.845  net   11939.00  (0.0s)
  VRPProxy           D    SR   0.305  net    1989.00  (0.0s)
  WideRangeBar       D    SR   0.429  net    5753.75  (0.0s)
  VWAPDistance       15m  SR  -9.879  net  -91014.50  (0.2s)
  MACDHistogram      D    SR  -0.386  net   -8059.50  (0.0s)
  EMACross           D    SR  -0.160  net   -3336.00  (0.0s)
  SMA200Trend        D    SR   0.289  net    6029.00  (0.0s)
  ATRRegime          D    SR   0.392  net    7593.25  (0.0s)
  VolumeSpike        15m  SR  -3.117  net  -41421.00  (0.0s)
  VolumeDelta        15m  SR  -2.255  net  -50038.75  (0.1s)
  LiquiditySweep     15m  SR  -7.408  net  -60847.75  (0.8s)
  OrderFlowPlus      15m  SR -10.749  net -101502.50  (0.7s)
  SMC                15m  SR -10.850  net -107282.25  (0.6s)
wrote: %SCRATCH%\bt18_run1\metrics_P1.csv, %SCRATCH%\bt18_run1\daily_pnl_P1.csv, %SCRATCH%\bt18_run1\ranking.csv, %SCRATCH%\bt18_run1\REPORT.md
wall time 3.4s
rc=0  wall=4.60s
```
```text
$ python -I -B -m qibt.cli run --dataset P1 --costs 1 --out %SCRATCH%\bt18_run2
loaded P1: 2142391 bars in 0.1s
  HedgingPressure    D    SR  -0.197  net   -2341.25  (0.0s)
  IBS                D    SR   0.566  net    8925.00  (0.0s)
  RSI2               D    SR   0.649  net   10634.00  (0.0s)
  ConnorsRSI         D    SR  -0.226  net   -2163.75  (0.0s)
  StochFade          D    SR   0.097  net    1616.50  (0.0s)
  RVZScore           D    SR   0.171  net    2092.75  (0.0s)
  CompositeVol       D    SR   0.280  net    2286.25  (0.0s)
  TurnOfMonth        D    SR  -0.266  net   -2728.00  (0.0s)
  ConsecDays         D    SR   0.569  net    4912.00  (0.0s)
  OvernightGap       D    SR  -0.779  net   -4994.25  (0.0s)
  BollingerPctB      15m  SR  -3.716  net  -36167.75  (0.2s)
  TurnaroundTuesday  D    SR  -0.449  net   -3634.75  (0.0s)
  RSI14              D    SR   0.845  net   11939.00  (0.0s)
  VRPProxy           D    SR   0.305  net    1989.00  (0.0s)
  WideRangeBar       D    SR   0.429  net    5753.75  (0.0s)
  VWAPDistance       15m  SR  -9.879  net  -91014.50  (0.2s)
  MACDHistogram      D    SR  -0.386  net   -8059.50  (0.0s)
  EMACross           D    SR  -0.160  net   -3336.00  (0.0s)
  SMA200Trend        D    SR   0.289  net    6029.00  (0.0s)
  ATRRegime          D    SR   0.392  net    7593.25  (0.0s)
  VolumeSpike        15m  SR  -3.117  net  -41421.00  (0.0s)
  VolumeDelta        15m  SR  -2.255  net  -50038.75  (0.1s)
  LiquiditySweep     15m  SR  -7.408  net  -60847.75  (0.8s)
  OrderFlowPlus      15m  SR -10.749  net -101502.50  (0.6s)
  SMC                15m  SR -10.850  net -107282.25  (0.6s)
wrote: %SCRATCH%\bt18_run2\metrics_P1.csv, %SCRATCH%\bt18_run2\daily_pnl_P1.csv, %SCRATCH%\bt18_run2\ranking.csv, %SCRATCH%\bt18_run2\REPORT.md
wall time 3.8s
rc=0  wall=5.54s
```
```text
$ python -I -B -m qibt.cli run --dataset P1 --costs 1 --no-cache --out %SCRATCH%\bt18_run3
  read MES_1min_20200101_20260201.csv: 373412 bar rows, 238165 signal rows, shift +1
  read MES_1min_20210131_20220131.csv: 351347 bar rows, 220341 signal rows, shift +1
  read MES_1min_20220130_20230131.csv: 352006 bar rows, 232490 signal rows, shift +1
  read MES_1min_20230131_20240229.csv: 371074 bar rows, 232125 signal rows, shift +1
  read MES_1min_20240229_20250331.csv: 379144 bar rows, 237934 signal rows, shift +1
  read MES_1min_20250331_20260224.csv: 315408 bar rows, 199935 signal rows, shift +1
loaded P1: 2142391 bars in 23.3s
  HedgingPressure    D    SR  -0.197  net   -2341.25  (0.0s)
  IBS                D    SR   0.566  net    8925.00  (0.0s)
  RSI2               D    SR   0.649  net   10634.00  (0.0s)
  ConnorsRSI         D    SR  -0.226  net   -2163.75  (0.0s)
  StochFade          D    SR   0.097  net    1616.50  (0.0s)
  RVZScore           D    SR   0.171  net    2092.75  (0.0s)
  CompositeVol       D    SR   0.280  net    2286.25  (0.0s)
  TurnOfMonth        D    SR  -0.266  net   -2728.00  (0.0s)
  ConsecDays         D    SR   0.569  net    4912.00  (0.0s)
  OvernightGap       D    SR  -0.779  net   -4994.25  (0.0s)
  BollingerPctB      15m  SR  -3.716  net  -36167.75  (0.2s)
  TurnaroundTuesday  D    SR  -0.449  net   -3634.75  (0.0s)
  RSI14              D    SR   0.845  net   11939.00  (0.0s)
  VRPProxy           D    SR   0.305  net    1989.00  (0.0s)
  WideRangeBar       D    SR   0.429  net    5753.75  (0.0s)
  VWAPDistance       15m  SR  -9.879  net  -91014.50  (0.2s)
  MACDHistogram      D    SR  -0.386  net   -8059.50  (0.0s)
  EMACross           D    SR  -0.160  net   -3336.00  (0.0s)
  SMA200Trend        D    SR   0.289  net    6029.00  (0.0s)
  ATRRegime          D    SR   0.392  net    7593.25  (0.0s)
  VolumeSpike        15m  SR  -3.117  net  -41421.00  (0.0s)
  VolumeDelta        15m  SR  -2.255  net  -50038.75  (0.0s)
  LiquiditySweep     15m  SR  -7.408  net  -60847.75  (1.0s)
  OrderFlowPlus      15m  SR -10.749  net -101502.50  (0.7s)
  SMC                15m  SR -10.850  net -107282.25  (0.6s)
wrote: %SCRATCH%\bt18_run3\metrics_P1.csv, %SCRATCH%\bt18_run3\daily_pnl_P1.csv, %SCRATCH%\bt18_run3\ranking.csv, %SCRATCH%\bt18_run3\REPORT.md
wall time 27.0s
rc=0  wall=28.41s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt18_diff_runs.py %SCRATCH%\bt18_run1 %SCRATCH%\bt18_run2
=== BT18 run-to-run diff: %SCRATCH%\bt18_run1 vs %SCRATCH%\bt18_run2 ===
[PASS] same file set | A=['REPORT.md', 'daily_pnl_P1.csv', 'metrics_P1.csv', 'ranking.csv'] B=['REPORT.md', 'daily_pnl_P1.csv', 'metrics_P1.csv', 'ranking.csv']
[PASS] both runs produced a ranking CSV and a metrics CSV (empty output = PROBE_INVALID, never a pass) | A=['REPORT.md', 'daily_pnl_P1.csv', 'metrics_P1.csv', 'ranking.csv']
[PASS] REPORT.md identical except run-time/wall-time/dataset lines | first diffs: []
[PASS] daily_pnl_P1.csv byte-identical
[PASS] daily_pnl_P1.csv numeric cells equal to 1e-9 (worst 0)
[PASS] metrics_P1.csv byte-identical
[PASS] metrics_P1.csv numeric cells equal to 1e-9 (worst 0)
[PASS] ranking.csv byte-identical
[PASS] ranking.csv numeric cells equal to 1e-9 (worst 0)
[PASS] ranking.csv rank order identical | A=['RSI14', 'RSI2', 'ConsecDays', 'IBS', 'WideRangeBar', 'ATRRegime'] | B=['RSI14', 'RSI2', 'ConsecDays', 'IBS', 'WideRangeBar', 'ATRRegime']
--- BT18 run-to-run diff: %SCRATCH%\bt18_run1 vs %SCRATCH%\bt18_run2: 10 checks, 0 failed
rc=0  wall=1.68s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt18_diff_runs.py %SCRATCH%\bt18_run1 %SCRATCH%\bt18_run3
=== BT18 run-to-run diff: %SCRATCH%\bt18_run1 vs %SCRATCH%\bt18_run3 ===
[PASS] same file set | A=['REPORT.md', 'daily_pnl_P1.csv', 'metrics_P1.csv', 'ranking.csv'] B=['REPORT.md', 'daily_pnl_P1.csv', 'metrics_P1.csv', 'ranking.csv']
[PASS] both runs produced a ranking CSV and a metrics CSV (empty output = PROBE_INVALID, never a pass) | A=['REPORT.md', 'daily_pnl_P1.csv', 'metrics_P1.csv', 'ranking.csv']
[PASS] REPORT.md identical except run-time/wall-time/dataset lines | first diffs: []
[PASS] daily_pnl_P1.csv byte-identical
[PASS] daily_pnl_P1.csv numeric cells equal to 1e-9 (worst 0)
[PASS] metrics_P1.csv byte-identical
[PASS] metrics_P1.csv numeric cells equal to 1e-9 (worst 0)
[PASS] ranking.csv byte-identical
[PASS] ranking.csv numeric cells equal to 1e-9 (worst 0)
[PASS] ranking.csv rank order identical | A=['RSI14', 'RSI2', 'ConsecDays', 'IBS', 'WideRangeBar', 'ATRRegime'] | B=['RSI14', 'RSI2', 'ConsecDays', 'IBS', 'WideRangeBar', 'ATRRegime']
--- BT18 run-to-run diff: %SCRATCH%\bt18_run1 vs %SCRATCH%\bt18_run3: 10 checks, 0 failed
rc=0  wall=1.64s
```
```text
$ bash -c for f in metrics_P1.csv daily_pnl_P1.csv ranking.csv; do cmp '$SCRATCH/bt18_run1/'$f results/$f && echo "$f identical"; done
metrics_P1.csv identical
daily_pnl_P1.csv identical
ranking.csv identical
rc=0  wall=0.35s
```
Falsifier: an engine mutant adds N(0, 1e-6) noise to gross P&L, and the mutant CLI runs twice.
An earlier attempt was PROBE_INVALID: the mutant CLI could not find rules.yaml, and the diff
passed on two empty folders. I fixed the runner (`--rules`) and added an "outputs exist" check, so
an empty output can never pass:
```text
$ python -I -B validation/probes/channel_b_backtest/_mutate.py backtest/qibt %SCRATCH%\mut_bt18_noise engine.py     return held, gross, sides     gross = gross + np.random.default_rng().normal(0.0, 1e-6, n)\n    return held, gross, sides
mutant: %SCRATCH%\mut_bt18_noise\qibt\engine.py
  - return held, gross, sides
  + gross = gross + np.random.default_rng().normal(0.0, 1e-6, n)
    return held, gross, sides
sha256 original engine.py before 10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 original engine.py after  10ebc194f3fad463b758bbb46db1c2a3fd31aa1c8a2c5cacdf977341c1512a1e
sha256 mutant   engine.py        b9f61eb9d8898d6bcacd06ffa6224e4a6c1bc62bfac68cbd585de645ce5b9a79
rc=0  wall=0.24s
```
```text
$ python -I -B validation/probes/channel_b_backtest/bt18_diff_runs.py %SCRATCH%\bt18_mutA %SCRATCH%\bt18_mutB
=== BT18 run-to-run diff: %SCRATCH%\bt18_mutA vs %SCRATCH%\bt18_mutB ===
[PASS] same file set | A=['REPORT.md', 'daily_pnl_P1.csv', 'metrics_P1.csv', 'ranking.csv'] B=['REPORT.md', 'daily_pnl_P1.csv', 'metrics_P1.csv', 'ranking.csv']
[PASS] both runs produced a ranking CSV and a metrics CSV (empty output = PROBE_INVALID, never a pass) | A=['REPORT.md', 'daily_pnl_P1.csv', 'metrics_P1.csv', 'ranking.csv']
[FAIL] REPORT.md identical except run-time/wall-time/dataset lines | first diffs: [(22, '| 2 | RSI2 | D | 0.649 | 0.000 | 0.935 | 10,634 | 3,418 | 61.4 | 638 | 1.033 | 0.348 | 0.744 | 0.555 | 0.22 |', '| 2 | RSI2 | D | 0.649 | 0.000 | 0.935 | 10,634 | 3,419 | 61.4 | 638 | 1.033 | 0.348 | 0.744 | 0.555 | 0.22 |'), (27, '| 7 | VRPProxy | D | 0.305 | 0.000 | 0.808 | 1,989 | 1,013 | 0.7 | 6 | 0.812 | 0.355 | 0.307 | 0.303 | 0.31 |', '| 7 | VRPProxy | D | 0.305 | 0.000 | 0.808 | 1,989 | 1,012 | 0.7 | 6 | 0.812 | 0.355 | 0.307 | 0.303 | 0.31 |'), (36, '| 16 | MACDHistogram | D | -0.386 | 0.000 | 0.189 | -8,059 | 10,157 | 99.9 | 126 | -0.177 | -0.572 | -0.359 | -0.413 | -0.35 |', '| 16 | MACDHistogram | D | -0.386 | 0.000 | 0.189 | -8,060 | 10,157 | 99.9 | 126 | -0.177 | -0.572 | -0.359 | -0.413 | -0.35 |')]
[FAIL] daily_pnl_P1.csv byte-identical
[FAIL] daily_pnl_P1.csv numeric cells equal to 1e-9 (worst 5.27e-05)
[FAIL] metrics_P1.csv byte-identical
[FAIL] metrics_P1.csv numeric cells equal to 1e-9 (worst 0.00117)
[FAIL] ranking.csv byte-identical
[FAIL] ranking.csv numeric cells equal to 1e-9 (worst 1.53e-07)
[PASS] ranking.csv rank order identical | A=['RSI14', 'RSI2', 'ConsecDays', 'IBS', 'WideRangeBar', 'ATRRegime'] | B=['RSI14', 'RSI2', 'ConsecDays', 'IBS', 'WideRangeBar', 'ATRRegime']
--- BT18 run-to-run diff: %SCRATCH%\bt18_mutA vs %SCRATCH%\bt18_mutB: 10 checks, 7 failed: REPORT.md identical except run-time/wall-time/dataset lines; daily_pnl_P1.csv byte-identical; daily_pnl_P1.csv numeric cells equal to 1e-9 (worst 5.27e-05); metrics_P1.csv byte-identical; metrics_P1.csv numeric cells equal to 1e-9 (worst 0.00117); ranking.csv byte-identical; ranking.csv numeric cells equal to 1e-9 (worst 1.53e-07)
rc=1  wall=1.11s
```

## 3. Extra cross-check: independent re-computation of the full P1 ranking (not a ledger claim)

`xcheck_ranking.py` is my own code for PROTOCOL 3-8: trading dates, D and 15m frames, P&L, costs,
daily aggregation, window, SR / PSR / DSR / MDD / exposure / H1 / H2 / 0x / 2x / correlation,
benchmark and ranking. Phi uses erfc and Phi^-1 uses bisection. `qibt` is used only for
`signals.load_rules` and for `signals.rule_positions(rule, <my frames>)`, which gives each rule's
target positions. Input: my raw re-parse of P1. I computed two cost conventions. "literal" charges
the execution at the last bar's open (PROTOCOL 4 + 5 read literally). "nolast" does not, which is
the engine's convention.

Result:
- **Frames:** D and 15m identical to qibt.
- **"nolast":** 0 differing cells in `metrics_P1.csv` (all rules and BuyHold, 27 metric columns,
  1e-6 rel; SR 1e-6 abs). Max |dSR| = 1.8e-15 (1x), 1.1e-16 (0x), 7.1e-15 (2x).
- **Rank order 1x:** identical **except ranks 3 and 4.** Channel B has IBS 3, ConsecDays 4; the
  committed ranking has ConsecDays 3, IBS 4. The cause is F2 (DSR underflow in the tie-break).
- **Rank order 0x and 2x:** identical.
- **"literal":** SR differs by 1.4e-4 to 2.8e-4 for IBS, RSI2, TurnaroundTuesday and OrderFlowPlus
  at 1x (finding F3). No other rank change.
- **Controls:** a results copy with ranks 3 and 4 swapped passes the tie-break check. A results copy
  with RSI14 SR + 2e-6 is reported as exactly 1 differing cell.

```text
$ python -I -B validation/probes/channel_b_backtest/xcheck_ranking.py --pkl %SCRATCH%\raw_p1.pkl --costs 1
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
1-minute source: pickle %SCRATCH%\raw_p1.pkl (2142391 bars)
own frames: D 1578 bars, 15m 143136 bars
FRAME PARITY D: own vs qibt.data.build_frames IDENTICAL (1578 vs 1578 rows)
FRAME PARITY 15m: own vs qibt.data.build_frames IDENTICAL (143136 vs 143136 rows)
[literal] V[SR per day] = 0.055192084, N = 25, SR0 per day = 0.469190333
[nolast] V[SR per day] = 0.055193041, N = 25, SR0 per day = 0.469194404

===== variant literal, costs 1x =====
rank order identical to ranking.csv: False
  rank  1: Channel B RSI14              results RSI14              
  rank  2: Channel B RSI2               results RSI2               
  rank  3: Channel B IBS                results ConsecDays         <-- differs
  rank  4: Channel B ConsecDays         results IBS                <-- differs
  rank  5: Channel B WideRangeBar       results WideRangeBar       
  rank  6: Channel B ATRRegime          results ATRRegime          
  rank  7: Channel B VRPProxy           results VRPProxy           
  rank  8: Channel B SMA200Trend        results SMA200Trend        
  rank  9: Channel B CompositeVol       results CompositeVol       
  rank 10: Channel B RVZScore           results RVZScore           
  rank 11: Channel B StochFade          results StochFade          
  rank 12: Channel B EMACross           results EMACross           
  rank 13: Channel B HedgingPressure    results HedgingPressure    
  rank 14: Channel B ConnorsRSI         results ConnorsRSI         
  rank 15: Channel B TurnOfMonth        results TurnOfMonth        
  rank 16: Channel B MACDHistogram      results MACDHistogram      
  rank 17: Channel B TurnaroundTuesday  results TurnaroundTuesday  
  rank 18: Channel B OvernightGap       results OvernightGap       
  rank 19: Channel B VolumeDelta        results VolumeDelta        
  rank 20: Channel B VolumeSpike        results VolumeSpike        
  rank 21: Channel B BollingerPctB      results BollingerPctB      
  rank 22: Channel B LiquiditySweep     results LiquiditySweep     
  rank 23: Channel B VWAPDistance       results VWAPDistance       
  rank 24: Channel B OrderFlowPlus      results OrderFlowPlus      
  rank 25: Channel B SMC                results SMC                
  rank 26: Channel B ChopIndex          results ChopIndex          
  rank 27: Channel B KeyLevels          results KeyLevels          
ranking.csv SR differences > 1e-6: 4 [('RSI2', 0.6492954724275234, 0.6494331452653861), ('IBS', 0.5653656441045931, 0.565508420361191), ('TurnaroundTuesday', -0.4494531758400351, -0.4491749935133323), ('OrderFlowPlus', -10.748309444046493, -10.748514317204751)]
metrics_P1.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): 54
  IBS                sr            Channel B 0.5653656441045931   results 0.565508420361191
  IBS                sr_daily      Channel B 0.03561468795525247   results 0.0356236820140163
  IBS                psr           Channel B 0.9061955601767337   results 0.9062518695404832
  IBS                total_pnl     Channel B 8922.75   results 8925.0
  IBS                total_costs   Channel B 2218.5   results 2216.25
  IBS                changes       Channel B 840.0   results 839.0
  IBS                sides         Channel B 986.0   results 985.0
  IBS                sr_h2         Channel B 0.8194102925601902   results 0.819673147033435
  IBS                sr_cost1      Channel B 0.5653656441045931   results 0.565508420361191
  IBS                sr_cost2      Channel B 0.42484080287115206   results 0.425126258032814
  IBS                pnl_cost1     Channel B 8922.75   results 8925.0
  IBS                pnl_cost2     Channel B 6704.25   results 6708.75
  IBS                skew          Channel B 1.3617174721262888   results 1.3616920919029012
  RSI2               sr            Channel B 0.6492954724275234   results 0.6494331452653861
  RSI2               sr_daily      Channel B 0.04090177017722435   results 0.040910442750826
  RSI2               psr           Channel B 0.9346133939057468   results 0.9346545125397911
  RSI2               total_pnl     Channel B 10631.75   results 10634.0
  RSI2               total_costs   Channel B 1545.75   results 1543.5
  RSI2               changes       Channel B 639.0   results 638.0
  RSI2               sides         Channel B 687.0   results 686.0
  RSI2               sr_h2         Channel B 0.3472694661382599   results 0.3475188306474339
  RSI2               sr_cost1      Channel B 0.6492954724275234   results 0.6494331452653861
  RSI2               sr_cost2      Channel B 0.5548683259643219   results 0.5551435803160815
  RSI2               pnl_cost1     Channel B 10631.75   results 10634.0
  RSI2               pnl_cost2     Channel B 9086.0   results 9090.5
  RSI2               skew          Channel B 1.1586576574937375   results 1.1586331400085024
  TurnaroundTuesday  sr            Channel B -0.4494531758400351   results -0.4491749935133323
  TurnaroundTuesday  sr_daily      Channel B -0.0283128887914504   results -0.0282953649520316
  TurnaroundTuesday  psr           Channel B 0.15170659863888086   results 0.1518558345868216
  TurnaroundTuesday  total_pnl     Channel B -3637.0   results -3634.75
  TurnaroundTuesday  total_costs   Channel B 1185.75   results 1183.5
  TurnaroundTuesday  changes       Channel B 527.0   results 526.0
  TurnaroundTuesday  sides         Channel B 527.0   results 526.0
  TurnaroundTuesday  sr_h2         Channel B -0.5807750779556102   results -0.5802011132942624
  TurnaroundTuesday  sr_cost1      Channel B -0.4494531758400351   results -0.4491749935133323
  TurnaroundTuesday  sr_cost2      Channel B -0.5957131821734067   results -0.5951570352525785
  TurnaroundTuesday  pnl_cost1     Channel B -3637.0   results -3634.75
  TurnaroundTuesday  pnl_cost2     Channel B -4822.75   results -4818.25
  TurnaroundTuesday  skew          Channel B -0.2479151991062988   results -0.2479675302135212
  OrderFlowPlus      sr            Channel B -10.748309444046493   results -10.748514317204751
  OrderFlowPlus      sr_daily      Channel B -0.6770798524598555   results -0.677092758255738
  OrderFlowPlus      total_pnl     Channel B -101504.75   results -101502.5
  OrderFlowPlus      total_costs   Channel B 95886.0   results 95883.75
  OrderFlowPlus      mdd           Channel B 101504.75   results 101502.5
  OrderFlowPlus      changes       Channel B 40607.0   results 40606.0
  OrderFlowPlus      sides         Channel B 42616.0   results 42615.0
  OrderFlowPlus      sr_h2         Channel B -10.537545667621183   results -10.537886079742496
  OrderFlowPlus      sr_cost1      Channel B -10.748309444046493   results -10.748514317204751
  OrderFlowPlus      sr_cost2      Channel B -20.199836364384183   results -20.20091150521209
  OrderFlowPlus      pnl_cost1     Channel B -101504.75   results -101502.5
  OrderFlowPlus      pnl_cost2     Channel B -197390.75   results -197386.25
  OrderFlowPlus      skew          Channel B -0.049370846957900845   results -0.0490823635584448
  OrderFlowPlus      kurt          Channel B 7.133649176636639   results 7.1335851486836725
  OrderFlowPlus      corr_bh       Channel B 0.1091611692246821   results 0.1091651171259057

===== variant nolast, costs 1x =====
rank order identical to ranking.csv: False
  rank  1: Channel B RSI14              results RSI14              
  rank  2: Channel B RSI2               results RSI2               
  rank  3: Channel B IBS                results ConsecDays         <-- differs
  rank  4: Channel B ConsecDays         results IBS                <-- differs
  rank  5: Channel B WideRangeBar       results WideRangeBar       
  rank  6: Channel B ATRRegime          results ATRRegime          
  rank  7: Channel B VRPProxy           results VRPProxy           
  rank  8: Channel B SMA200Trend        results SMA200Trend        
  rank  9: Channel B CompositeVol       results CompositeVol       
  rank 10: Channel B RVZScore           results RVZScore           
  rank 11: Channel B StochFade          results StochFade          
  rank 12: Channel B EMACross           results EMACross           
  rank 13: Channel B HedgingPressure    results HedgingPressure    
  rank 14: Channel B ConnorsRSI         results ConnorsRSI         
  rank 15: Channel B TurnOfMonth        results TurnOfMonth        
  rank 16: Channel B MACDHistogram      results MACDHistogram      
  rank 17: Channel B TurnaroundTuesday  results TurnaroundTuesday  
  rank 18: Channel B OvernightGap       results OvernightGap       
  rank 19: Channel B VolumeDelta        results VolumeDelta        
  rank 20: Channel B VolumeSpike        results VolumeSpike        
  rank 21: Channel B BollingerPctB      results BollingerPctB      
  rank 22: Channel B LiquiditySweep     results LiquiditySweep     
  rank 23: Channel B VWAPDistance       results VWAPDistance       
  rank 24: Channel B OrderFlowPlus      results OrderFlowPlus      
  rank 25: Channel B SMC                results SMC                
  rank 26: Channel B ChopIndex          results ChopIndex          
  rank 27: Channel B KeyLevels          results KeyLevels          
ranking.csv SR differences > 1e-6: 0 []
metrics_P1.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): 0

rules whose last frame bar executes a position change (cost charged only in 'literal'): [('IBS', 'D', 1.0), ('RSI2', 'D', 1.0), ('TurnaroundTuesday', 'D', 1.0), ('OrderFlowPlus', '15m', 1.0)]

Channel B ranking (literal): 1 RSI14 0.844658, 2 RSI2 0.649295, 3 IBS 0.565366, 4 ConsecDays 0.568885, 5 WideRangeBar 0.429089, 6 ATRRegime 0.392246, 7 VRPProxy 0.304731, 8 SMA200Trend 0.288767, 9 CompositeVol 0.279981, 10 RVZScore 0.170921, 11 StochFade 0.096565, 12 EMACross -0.159764, 13 HedgingPressure -0.196933, 14 ConnorsRSI -0.225851, 15 TurnOfMonth -0.266218, 16 MACDHistogram -0.386127, 17 TurnaroundTuesday -0.449453, 18 OvernightGap -0.779182, 19 VolumeDelta -2.255404, 20 VolumeSpike -3.117455, 21 BollingerPctB -3.716075, 22 LiquiditySweep -7.407985, 23 VWAPDistance -9.878645, 24 OrderFlowPlus -10.748309, 25 SMC -10.849793, 26 ChopIndex, 27 KeyLevels
summary: {'literal': {'order_same': False, 'n_metric_diffs': 54, 'n_sr_diffs': 4}, 'nolast': {'order_same': False, 'n_metric_diffs': 0, 'n_sr_diffs': 0}}
rc=1  wall=10.37s
```
```text
$ python -I -B validation/probes/channel_b_backtest/xcheck_ranking.py --pkl %SCRATCH%\raw_p1.pkl --costs 0
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
1-minute source: pickle %SCRATCH%\raw_p1.pkl (2142391 bars)
own frames: D 1578 bars, 15m 143136 bars
FRAME PARITY D: own vs qibt.data.build_frames IDENTICAL (1578 vs 1578 rows)
FRAME PARITY 15m: own vs qibt.data.build_frames IDENTICAL (143136 vs 143136 rows)
[literal] V[SR per day] = 0.000960996, N = 25, SR0 per day = 0.061911515
[nolast] V[SR per day] = 0.000960996, N = 25, SR0 per day = 0.061911515

===== variant literal, costs 0x =====
rank order identical to ranking_cost0x.csv: True
ranking.csv SR differences > 1e-6: 0 []
metrics_P1_cost0x.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): 24
  IBS                changes       Channel B 840.0   results 839.0
  IBS                sides         Channel B 986.0   results 985.0
  IBS                sr_cost1      Channel B 0.5653656441045931   results 0.565508420361191
  IBS                sr_cost2      Channel B 0.42484080287115206   results 0.425126258032814
  IBS                pnl_cost1     Channel B 8922.75   results 8925.0
  IBS                pnl_cost2     Channel B 6704.25   results 6708.75
  RSI2               changes       Channel B 639.0   results 638.0
  RSI2               sides         Channel B 687.0   results 686.0
  RSI2               sr_cost1      Channel B 0.6492954724275234   results 0.6494331452653861
  RSI2               sr_cost2      Channel B 0.5548683259643219   results 0.5551435803160815
  RSI2               pnl_cost1     Channel B 10631.75   results 10634.0
  RSI2               pnl_cost2     Channel B 9086.0   results 9090.5
  TurnaroundTuesday  changes       Channel B 527.0   results 526.0
  TurnaroundTuesday  sides         Channel B 527.0   results 526.0
  TurnaroundTuesday  sr_cost1      Channel B -0.4494531758400351   results -0.4491749935133323
  TurnaroundTuesday  sr_cost2      Channel B -0.5957131821734067   results -0.5951570352525785
  TurnaroundTuesday  pnl_cost1     Channel B -3637.0   results -3634.75
  TurnaroundTuesday  pnl_cost2     Channel B -4822.75   results -4818.25
  OrderFlowPlus      changes       Channel B 40607.0   results 40606.0
  OrderFlowPlus      sides         Channel B 42616.0   results 42615.0
  OrderFlowPlus      sr_cost1      Channel B -10.748309444046493   results -10.748514317204751
  OrderFlowPlus      sr_cost2      Channel B -20.199836364384183   results -20.20091150521209
  OrderFlowPlus      pnl_cost1     Channel B -101504.75   results -101502.5
  OrderFlowPlus      pnl_cost2     Channel B -197390.75   results -197386.25

===== variant nolast, costs 0x =====
rank order identical to ranking_cost0x.csv: True
ranking.csv SR differences > 1e-6: 0 []
metrics_P1_cost0x.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): 0

rules whose last frame bar executes a position change (cost charged only in 'literal'): [('IBS', 'D', 1.0), ('RSI2', 'D', 1.0), ('TurnaroundTuesday', 'D', 1.0), ('OrderFlowPlus', '15m', 1.0)]

Channel B ranking (literal): 1 RSI14 0.886051, 2 RSI2 0.743700, 3 IBS 0.705820, 4 ConsecDays 0.656947, 5 VolumeDelta 0.634616, 6 WideRangeBar 0.496138, 7 ATRRegime 0.393174, 8 CompositeVol 0.310224, 9 VRPProxy 0.306838, 10 SMA200Trend 0.296966, 11 RVZScore 0.206041, 12 StochFade 0.141075, 13 VolumeSpike -0.120550, 14 ConnorsRSI -0.134325, 15 HedgingPressure -0.140135, 16 SMC -0.155127, 17 EMACross -0.154810, 18 TurnOfMonth -0.239203, 19 BollingerPctB -0.268950, 20 TurnaroundTuesday -0.303020, 21 MACDHistogram -0.358902, 22 VWAPDistance -0.375129, 23 OrderFlowPlus -0.606059, 24 OvernightGap -0.752249, 25 LiquiditySweep -0.966081, 26 ChopIndex, 27 KeyLevels
summary: {'literal': {'order_same': True, 'n_metric_diffs': 24, 'n_sr_diffs': 0}, 'nolast': {'order_same': True, 'n_metric_diffs': 0, 'n_sr_diffs': 0}}
rc=0  wall=10.00s
```
```text
$ python -I -B validation/probes/channel_b_backtest/xcheck_ranking.py --pkl %SCRATCH%\raw_p1.pkl --costs 2
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
1-minute source: pickle %SCRATCH%\raw_p1.pkl (2142391 bars)
own frames: D 1578 bars, 15m 143136 bars
FRAME PARITY D: own vs qibt.data.build_frames IDENTICAL (1578 vs 1578 rows)
FRAME PARITY 15m: own vs qibt.data.build_frames IDENTICAL (143136 vs 143136 rows)
[literal] V[SR per day] = 0.191944770, N = 25, SR0 per day = 0.874981361
[nolast] V[SR per day] = 0.191951983, N = 25, SR0 per day = 0.874997801

===== variant literal, costs 2x =====
rank order identical to ranking_cost2x.csv: True
ranking.csv SR differences > 1e-6: 4 [('RSI2', 0.5548683259643219, 0.5551435803160815), ('IBS', 0.42484080287115206, 0.425126258032814), ('TurnaroundTuesday', -0.5957131821734067, -0.5951570352525785), ('OrderFlowPlus', -20.199836364384183, -20.20091150521209)]
metrics_P1_cost2x.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): 55
  IBS                sr            Channel B 0.42484080287115206   results 0.425126258032814
  IBS                sr_daily      Channel B 0.026762455028335328   results 0.0267804370132928
  IBS                psr           Channel B 0.8380714147884405   results 0.8382356343671061
  IBS                total_pnl     Channel B 6704.25   results 6708.75
  IBS                total_costs   Channel B 4437.0   results 4432.5
  IBS                changes       Channel B 840.0   results 839.0
  IBS                sides         Channel B 986.0   results 985.0
  IBS                sr_h2         Channel B 0.6913885294336933   results 0.691914040965615
  IBS                sr_cost1      Channel B 0.5653656441045931   results 0.565508420361191
  IBS                sr_cost2      Channel B 0.42484080287115206   results 0.425126258032814
  IBS                pnl_cost1     Channel B 8922.75   results 8925.0
  IBS                pnl_cost2     Channel B 6704.25   results 6708.75
  IBS                skew          Channel B 1.3524023814312078   results 1.3523513711341189
  RSI2               sr            Channel B 0.5548683259643219   results 0.5551435803160815
  RSI2               sr_daily      Channel B 0.0349534190687695   results 0.0349707584631038
  RSI2               psr           Channel B 0.9013352189847106   results 0.901447278096388
  RSI2               total_pnl     Channel B 9086.0   results 9090.5
  RSI2               total_costs   Channel B 3091.5   results 3087.0
  RSI2               changes       Channel B 639.0   results 638.0
  RSI2               sides         Channel B 687.0   results 686.0
  RSI2               sr_h2         Channel B 0.26353890801692126   results 0.264037577079154
  RSI2               sr_cost1      Channel B 0.6492954724275234   results 0.6494331452653861
  RSI2               sr_cost2      Channel B 0.5548683259643219   results 0.5551435803160815
  RSI2               pnl_cost1     Channel B 10631.75   results 10634.0
  RSI2               pnl_cost2     Channel B 9086.0   results 9090.5
  RSI2               skew          Channel B 1.158739341402076   results 1.1586902955273009
  TurnaroundTuesday  sr            Channel B -0.5957131821734067   results -0.5951570352525785
  TurnaroundTuesday  sr_daily      Channel B -0.03752640316080357   results -0.0374913691978291
  TurnaroundTuesday  psr           Channel B 0.0862968542982525   results 0.0864962207224659
  TurnaroundTuesday  total_pnl     Channel B -4822.75   results -4818.25
  TurnaroundTuesday  total_costs   Channel B 2371.5   results 2367.0
  TurnaroundTuesday  changes       Channel B 527.0   results 526.0
  TurnaroundTuesday  sides         Channel B 527.0   results 526.0
  TurnaroundTuesday  sr_h2         Channel B -0.7323047918429466   results -0.731157400222862
  TurnaroundTuesday  sr_cost1      Channel B -0.4494531758400351   results -0.4491749935133323
  TurnaroundTuesday  sr_cost2      Channel B -0.5957131821734067   results -0.5951570352525785
  TurnaroundTuesday  pnl_cost1     Channel B -3637.0   results -3634.75
  TurnaroundTuesday  pnl_cost2     Channel B -4822.75   results -4818.25
  TurnaroundTuesday  skew          Channel B -0.289175938636489   results -0.2892805452345432
  TurnaroundTuesday  corr_bh       Channel B 0.38841163232433623   results 0.3884101473471739
  OrderFlowPlus      sr            Channel B -20.199836364384183   results -20.20091150521209
  OrderFlowPlus      sr_daily      Channel B -1.2724700843895154   results -1.2725378118955872
  OrderFlowPlus      total_pnl     Channel B -197390.75   results -197386.25
  OrderFlowPlus      total_costs   Channel B 191772.0   results 191767.5
  OrderFlowPlus      mdd           Channel B 197390.75   results 197386.25
  OrderFlowPlus      changes       Channel B 40607.0   results 40606.0
  OrderFlowPlus      sides         Channel B 42616.0   results 42615.0
  OrderFlowPlus      sr_h2         Channel B -19.68920675359946   results -19.69108619211395
  OrderFlowPlus      sr_cost1      Channel B -10.748309444046493   results -10.748514317204751
  OrderFlowPlus      sr_cost2      Channel B -20.199836364384183   results -20.20091150521209
  OrderFlowPlus      pnl_cost1     Channel B -101504.75   results -101502.5
  OrderFlowPlus      pnl_cost2     Channel B -197390.75   results -197386.25
  OrderFlowPlus      skew          Channel B -0.12319953730824847   results -0.122717212684147
  OrderFlowPlus      kurt          Channel B 6.473801567872128   results 6.473697700674659
  OrderFlowPlus      corr_bh       Channel B 0.10626429265976191   results 0.1062713033531656

===== variant nolast, costs 2x =====
rank order identical to ranking_cost2x.csv: True
ranking.csv SR differences > 1e-6: 0 []
metrics_P1_cost2x.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): 0

rules whose last frame bar executes a position change (cost charged only in 'literal'): [('IBS', 'D', 1.0), ('RSI2', 'D', 1.0), ('TurnaroundTuesday', 'D', 1.0), ('OrderFlowPlus', '15m', 1.0)]

Channel B ranking (literal): 1 RSI14 0.803227, 2 RSI2 0.554868, 3 ConsecDays 0.480776, 4 IBS 0.424841, 5 ATRRegime 0.391318, 6 WideRangeBar 0.362006, 7 VRPProxy 0.302623, 8 SMA200Trend 0.280566, 9 CompositeVol 0.249715, 10 RVZScore 0.135805, 11 StochFade 0.052066, 12 EMACross -0.164718, 13 HedgingPressure -0.253737, 14 TurnOfMonth -0.293226, 15 ConnorsRSI -0.317260, 16 MACDHistogram -0.413349, 17 TurnaroundTuesday -0.595713, 18 OvernightGap -0.806045, 19 VolumeDelta -4.919169, 20 VolumeSpike -6.107502, 21 BollingerPctB -7.237357, 22 LiquiditySweep -13.633964, 23 VWAPDistance -18.720323, 24 OrderFlowPlus -20.199836, 25 SMC -20.615746, 26 ChopIndex, 27 KeyLevels
summary: {'literal': {'order_same': True, 'n_metric_diffs': 55, 'n_sr_diffs': 4}, 'nolast': {'order_same': True, 'n_metric_diffs': 0, 'n_sr_diffs': 0}}
rc=1  wall=10.14s
```
```text
$ python -I -B validation/probes/channel_b_backtest/xcheck_dsr_tiebreak.py
N = 25, V[SR per day] = 0.055193041, SR0 per day = 0.469194404
tie pair rank 3 ConsecDays (SR 0.568885) / rank 4 IBS (SR 0.565508): |dSR| = 0.003377
   ConsecDays   z = -16.223926  DSR(scipy cdf) = 1.708200e-59  log DSR = -135.3171  NormalDist.cdf = 0.0  committed dsr = np.float64(0.0)
   IBS          z = -16.041457  DSR(scipy cdf) = 3.279835e-58  log DSR = -132.3621  NormalDist.cdf = 0.0  committed dsr = np.float64(0.0)
   PROTOCOL 8 (higher DSR, then A->Z) puts IBS first; committed order does NOT follow it
statistics.NormalDist().cdf(x) == 0.0 for x <= -8.26 (scipy norm.cdf(-8.26) = 7.284e-17)
committed dsr values: [0.0]
rc=1  wall=2.90s
```
```text
$ python -I -B -c 
import pandas as pd, shutil, sys
S = sys.argv[1]
for f in ('metrics_P1.csv', 'ranking.csv', 'daily_pnl_P1.csv'):
    shutil.copy('results/' + f, S + '/xc_swap/' + f); shutil.copy('results/' + f, S + '/xc_perturb/' + f)
r = pd.read_csv(S + '/xc_swap/ranking.csv'); r.loc[r['rank'] == 3, 'rank'] = -4; r.loc[r['rank'] == 4, 'rank'] = 3; r.loc[r['rank'] == -4, 'rank'] = 4
r.sort_values('rank').to_csv(S + '/xc_swap/ranking.csv', index=False)
for f in ('metrics_P1.csv', 'ranking.csv'):
    d = pd.read_csv(S + '/xc_perturb/' + f); d.loc[d['module'] == 'RSI14', 'sr'] += 2e-6; d.to_csv(S + '/xc_perturb/' + f, index=False)
print('written', S + '/xc_swap', S + '/xc_perturb')
 %SCRATCH%
written %SCRATCH%/xc_swap %SCRATCH%/xc_perturb
rc=0  wall=1.59s
```
```text
$ python -I -B validation/probes/channel_b_backtest/xcheck_dsr_tiebreak.py --results %SCRATCH%\xc_swap
N = 25, V[SR per day] = 0.055193041, SR0 per day = 0.469194404
tie pair rank 3 IBS (SR 0.565508) / rank 4 ConsecDays (SR 0.568885): |dSR| = 0.003377
   IBS          z = -16.041457  DSR(scipy cdf) = 3.279835e-58  log DSR = -132.3621  NormalDist.cdf = 0.0  committed dsr = np.float64(0.0)
   ConsecDays   z = -16.223926  DSR(scipy cdf) = 1.708200e-59  log DSR = -135.3171  NormalDist.cdf = 0.0  committed dsr = np.float64(0.0)
   PROTOCOL 8 (higher DSR, then A->Z) puts IBS first; committed order follows it
statistics.NormalDist().cdf(x) == 0.0 for x <= -8.26 (scipy norm.cdf(-8.26) = 7.284e-17)
committed dsr values: [0.0]
rc=0  wall=2.66s
```
```text
$ python -I -B validation/probes/channel_b_backtest/xcheck_ranking.py --pkl %SCRATCH%\raw_p1.pkl --costs 1 --results %SCRATCH%\xc_perturb
qibt loaded from: c:\users\rajib\onedrive\documents\ninjatrader_quant_indicators\backtest\qibt\__init__.py
1-minute source: pickle %SCRATCH%\raw_p1.pkl (2142391 bars)
own frames: D 1578 bars, 15m 143136 bars
FRAME PARITY D: own vs qibt.data.build_frames IDENTICAL (1578 vs 1578 rows)
FRAME PARITY 15m: own vs qibt.data.build_frames IDENTICAL (143136 vs 143136 rows)
[literal] V[SR per day] = 0.055192084, N = 25, SR0 per day = 0.469190333
[nolast] V[SR per day] = 0.055193041, N = 25, SR0 per day = 0.469194404

===== variant literal, costs 1x =====
rank order identical to ranking.csv: False
  rank  1: Channel B RSI14              results RSI14              
  rank  2: Channel B RSI2               results RSI2               
  rank  3: Channel B IBS                results ConsecDays         <-- differs
  rank  4: Channel B ConsecDays         results IBS                <-- differs
  rank  5: Channel B WideRangeBar       results WideRangeBar       
  rank  6: Channel B ATRRegime          results ATRRegime          
  rank  7: Channel B VRPProxy           results VRPProxy           
  rank  8: Channel B SMA200Trend        results SMA200Trend        
  rank  9: Channel B CompositeVol       results CompositeVol       
  rank 10: Channel B RVZScore           results RVZScore           
  rank 11: Channel B StochFade          results StochFade          
  rank 12: Channel B EMACross           results EMACross           
  rank 13: Channel B HedgingPressure    results HedgingPressure    
  rank 14: Channel B ConnorsRSI         results ConnorsRSI         
  rank 15: Channel B TurnOfMonth        results TurnOfMonth        
  rank 16: Channel B MACDHistogram      results MACDHistogram      
  rank 17: Channel B TurnaroundTuesday  results TurnaroundTuesday  
  rank 18: Channel B OvernightGap       results OvernightGap       
  rank 19: Channel B VolumeDelta        results VolumeDelta        
  rank 20: Channel B VolumeSpike        results VolumeSpike        
  rank 21: Channel B BollingerPctB      results BollingerPctB      
  rank 22: Channel B LiquiditySweep     results LiquiditySweep     
  rank 23: Channel B VWAPDistance       results VWAPDistance       
  rank 24: Channel B OrderFlowPlus      results OrderFlowPlus      
  rank 25: Channel B SMC                results SMC                
  rank 26: Channel B ChopIndex          results ChopIndex          
  rank 27: Channel B KeyLevels          results KeyLevels          
ranking.csv SR differences > 1e-6: 5 [('RSI14', 0.8446575438079269, 0.8446595438079268), ('RSI2', 0.6492954724275234, 0.6494331452653861), ('IBS', 0.5653656441045931, 0.565508420361191), ('TurnaroundTuesday', -0.4494531758400351, -0.4491749935133323), ('OrderFlowPlus', -10.748309444046493, -10.748514317204751)]
metrics_P1.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): 55
  IBS                sr            Channel B 0.5653656441045931   results 0.565508420361191
  IBS                sr_daily      Channel B 0.03561468795525247   results 0.0356236820140163
  IBS                psr           Channel B 0.9061955601767337   results 0.9062518695404832
  IBS                total_pnl     Channel B 8922.75   results 8925.0
  IBS                total_costs   Channel B 2218.5   results 2216.25
  IBS                changes       Channel B 840.0   results 839.0
  IBS                sides         Channel B 986.0   results 985.0
  IBS                sr_h2         Channel B 0.8194102925601902   results 0.819673147033435
  IBS                sr_cost1      Channel B 0.5653656441045931   results 0.565508420361191
  IBS                sr_cost2      Channel B 0.42484080287115206   results 0.425126258032814
  IBS                pnl_cost1     Channel B 8922.75   results 8925.0
  IBS                pnl_cost2     Channel B 6704.25   results 6708.75
  IBS                skew          Channel B 1.3617174721262888   results 1.3616920919029012
  RSI2               sr            Channel B 0.6492954724275234   results 0.6494331452653861
  RSI2               sr_daily      Channel B 0.04090177017722435   results 0.040910442750826
  RSI2               psr           Channel B 0.9346133939057468   results 0.9346545125397911
  RSI2               total_pnl     Channel B 10631.75   results 10634.0
  RSI2               total_costs   Channel B 1545.75   results 1543.5
  RSI2               changes       Channel B 639.0   results 638.0
  RSI2               sides         Channel B 687.0   results 686.0
  RSI2               sr_h2         Channel B 0.3472694661382599   results 0.3475188306474339
  RSI2               sr_cost1      Channel B 0.6492954724275234   results 0.6494331452653861
  RSI2               sr_cost2      Channel B 0.5548683259643219   results 0.5551435803160815
  RSI2               pnl_cost1     Channel B 10631.75   results 10634.0
  RSI2               pnl_cost2     Channel B 9086.0   results 9090.5
  RSI2               skew          Channel B 1.1586576574937375   results 1.1586331400085024
  TurnaroundTuesday  sr            Channel B -0.4494531758400351   results -0.4491749935133323
  TurnaroundTuesday  sr_daily      Channel B -0.0283128887914504   results -0.0282953649520316
  TurnaroundTuesday  psr           Channel B 0.15170659863888086   results 0.1518558345868216
  TurnaroundTuesday  total_pnl     Channel B -3637.0   results -3634.75
  TurnaroundTuesday  total_costs   Channel B 1185.75   results 1183.5
  TurnaroundTuesday  changes       Channel B 527.0   results 526.0
  TurnaroundTuesday  sides         Channel B 527.0   results 526.0
  TurnaroundTuesday  sr_h2         Channel B -0.5807750779556102   results -0.5802011132942624
  TurnaroundTuesday  sr_cost1      Channel B -0.4494531758400351   results -0.4491749935133323
  TurnaroundTuesday  sr_cost2      Channel B -0.5957131821734067   results -0.5951570352525785
  TurnaroundTuesday  pnl_cost1     Channel B -3637.0   results -3634.75
  TurnaroundTuesday  pnl_cost2     Channel B -4822.75   results -4818.25
  TurnaroundTuesday  skew          Channel B -0.2479151991062988   results -0.2479675302135212
  RSI14              sr            Channel B 0.8446575438079269   results 0.8446595438079268
  OrderFlowPlus      sr            Channel B -10.748309444046493   results -10.748514317204751
  OrderFlowPlus      sr_daily      Channel B -0.6770798524598555   results -0.677092758255738
  OrderFlowPlus      total_pnl     Channel B -101504.75   results -101502.5
  OrderFlowPlus      total_costs   Channel B 95886.0   results 95883.75
  OrderFlowPlus      mdd           Channel B 101504.75   results 101502.5
  OrderFlowPlus      changes       Channel B 40607.0   results 40606.0
  OrderFlowPlus      sides         Channel B 42616.0   results 42615.0
  OrderFlowPlus      sr_h2         Channel B -10.537545667621183   results -10.537886079742496
  OrderFlowPlus      sr_cost1      Channel B -10.748309444046493   results -10.748514317204751
  OrderFlowPlus      sr_cost2      Channel B -20.199836364384183   results -20.20091150521209
  OrderFlowPlus      pnl_cost1     Channel B -101504.75   results -101502.5
  OrderFlowPlus      pnl_cost2     Channel B -197390.75   results -197386.25
  OrderFlowPlus      skew          Channel B -0.049370846957900845   results -0.0490823635584448
  OrderFlowPlus      kurt          Channel B 7.133649176636639   results 7.1335851486836725
  OrderFlowPlus      corr_bh       Channel B 0.1091611692246821   results 0.1091651171259057

===== variant nolast, costs 1x =====
rank order identical to ranking.csv: False
  rank  1: Channel B RSI14              results RSI14              
  rank  2: Channel B RSI2               results RSI2               
  rank  3: Channel B IBS                results ConsecDays         <-- differs
  rank  4: Channel B ConsecDays         results IBS                <-- differs
  rank  5: Channel B WideRangeBar       results WideRangeBar       
  rank  6: Channel B ATRRegime          results ATRRegime          
  rank  7: Channel B VRPProxy           results VRPProxy           
  rank  8: Channel B SMA200Trend        results SMA200Trend        
  rank  9: Channel B CompositeVol       results CompositeVol       
  rank 10: Channel B RVZScore           results RVZScore           
  rank 11: Channel B StochFade          results StochFade          
  rank 12: Channel B EMACross           results EMACross           
  rank 13: Channel B HedgingPressure    results HedgingPressure    
  rank 14: Channel B ConnorsRSI         results ConnorsRSI         
  rank 15: Channel B TurnOfMonth        results TurnOfMonth        
  rank 16: Channel B MACDHistogram      results MACDHistogram      
  rank 17: Channel B TurnaroundTuesday  results TurnaroundTuesday  
  rank 18: Channel B OvernightGap       results OvernightGap       
  rank 19: Channel B VolumeDelta        results VolumeDelta        
  rank 20: Channel B VolumeSpike        results VolumeSpike        
  rank 21: Channel B BollingerPctB      results BollingerPctB      
  rank 22: Channel B LiquiditySweep     results LiquiditySweep     
  rank 23: Channel B VWAPDistance       results VWAPDistance       
  rank 24: Channel B OrderFlowPlus      results OrderFlowPlus      
  rank 25: Channel B SMC                results SMC                
  rank 26: Channel B ChopIndex          results ChopIndex          
  rank 27: Channel B KeyLevels          results KeyLevels          
ranking.csv SR differences > 1e-6: 1 [('RSI14', 0.8446575438079269, 0.8446595438079268)]
metrics_P1.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): 1
  RSI14              sr            Channel B 0.8446575438079269   results 0.8446595438079268

rules whose last frame bar executes a position change (cost charged only in 'literal'): [('IBS', 'D', 1.0), ('RSI2', 'D', 1.0), ('TurnaroundTuesday', 'D', 1.0), ('OrderFlowPlus', '15m', 1.0)]

Channel B ranking (literal): 1 RSI14 0.844658, 2 RSI2 0.649295, 3 IBS 0.565366, 4 ConsecDays 0.568885, 5 WideRangeBar 0.429089, 6 ATRRegime 0.392246, 7 VRPProxy 0.304731, 8 SMA200Trend 0.288767, 9 CompositeVol 0.279981, 10 RVZScore 0.170921, 11 StochFade 0.096565, 12 EMACross -0.159764, 13 HedgingPressure -0.196933, 14 ConnorsRSI -0.225851, 15 TurnOfMonth -0.266218, 16 MACDHistogram -0.386127, 17 TurnaroundTuesday -0.449453, 18 OvernightGap -0.779182, 19 VolumeDelta -2.255404, 20 VolumeSpike -3.117455, 21 BollingerPctB -3.716075, 22 LiquiditySweep -7.407985, 23 VWAPDistance -9.878645, 24 OrderFlowPlus -10.748309, 25 SMC -10.849793, 26 ChopIndex, 27 KeyLevels
summary: {'literal': {'order_same': False, 'n_metric_diffs': 55, 'n_sr_diffs': 5}, 'nolast': {'order_same': False, 'n_metric_diffs': 1, 'n_sr_diffs': 1}}
rc=1  wall=10.33s
```

Pinned re-run on the sha256-verified v1 copy, against `results/v1_last_trade/` (the same 12 files):
```text
$ python -I -B validation/probes/channel_b_backtest/xcheck_ranking.py --qibt-root %SCRATCH%\pristine_v1 --pkl %SCRATCH%\raw_p1.pkl --costs 1 --results results/v1_last_trade
qibt loaded from: %SCRATCH%\pristine_v1\qibt\__init__.py
1-minute source: pickle %SCRATCH%\raw_p1.pkl (2142391 bars)
own frames: D 1578 bars, 15m 143136 bars
FRAME PARITY D: own vs qibt.data.build_frames IDENTICAL (1578 vs 1578 rows)
FRAME PARITY 15m: own vs qibt.data.build_frames IDENTICAL (143136 vs 143136 rows)
[literal] V[SR per day] = 0.055192084, N = 25, SR0 per day = 0.469190333
[literal] Channel B DSR (erfc Phi): RSI14 4.1868e-54, RSI2 1.0878e-56, ConsecDays 1.7124e-59, IBS 3.2725e-58, WideRangeBar 2.9492e-59, ATRRegime 8.5093e-58
[nolast] V[SR per day] = 0.055193041, N = 25, SR0 per day = 0.469194404
[nolast] Channel B DSR (erfc Phi): RSI14 4.1770e-54, RSI2 1.0903e-56, ConsecDays 1.7082e-59, IBS 3.2798e-58, WideRangeBar 2.9420e-59, ATRRegime 8.4894e-58

===== variant literal, costs 1x =====
rank order identical to ranking.csv: False
  rank  1: Channel B RSI14              results RSI14              
  rank  2: Channel B RSI2               results RSI2               
  rank  3: Channel B IBS                results ConsecDays         <-- differs
  rank  4: Channel B ConsecDays         results IBS                <-- differs
  rank  5: Channel B WideRangeBar       results WideRangeBar       
  rank  6: Channel B ATRRegime          results ATRRegime          
  rank  7: Channel B VRPProxy           results VRPProxy           
  rank  8: Channel B SMA200Trend        results SMA200Trend        
  rank  9: Channel B CompositeVol       results CompositeVol       
  rank 10: Channel B RVZScore           results RVZScore           
  rank 11: Channel B StochFade          results StochFade          
  rank 12: Channel B EMACross           results EMACross           
  rank 13: Channel B HedgingPressure    results HedgingPressure    
  rank 14: Channel B ConnorsRSI         results ConnorsRSI         
  rank 15: Channel B TurnOfMonth        results TurnOfMonth        
  rank 16: Channel B MACDHistogram      results MACDHistogram      
  rank 17: Channel B TurnaroundTuesday  results TurnaroundTuesday  
  rank 18: Channel B OvernightGap       results OvernightGap       
  rank 19: Channel B VolumeDelta        results VolumeDelta        
  rank 20: Channel B VolumeSpike        results VolumeSpike        
  rank 21: Channel B BollingerPctB      results BollingerPctB      
  rank 22: Channel B LiquiditySweep     results LiquiditySweep     
  rank 23: Channel B VWAPDistance       results VWAPDistance       
  rank 24: Channel B OrderFlowPlus      results OrderFlowPlus      
  rank 25: Channel B SMC                results SMC                
  rank 26: Channel B ChopIndex          results ChopIndex          
  rank 27: Channel B KeyLevels          results KeyLevels          
ranking.csv SR differences > 1e-6: 4 [('RSI2', 0.6492954724275234, 0.6494331452653861), ('IBS', 0.5653656441045931, 0.565508420361191), ('TurnaroundTuesday', -0.4494531758400351, -0.4491749935133323), ('OrderFlowPlus', -10.748309444046493, -10.748514317204751)]
metrics_P1.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): 54
  IBS                sr            Channel B 0.5653656441045931   results 0.565508420361191
  IBS                sr_daily      Channel B 0.03561468795525247   results 0.0356236820140163
  IBS                psr           Channel B 0.9061955601767337   results 0.9062518695404832
  IBS                total_pnl     Channel B 8922.75   results 8925.0
  IBS                total_costs   Channel B 2218.5   results 2216.25
  IBS                changes       Channel B 840.0   results 839.0
  IBS                sides         Channel B 986.0   results 985.0
  IBS                sr_h2         Channel B 0.8194102925601902   results 0.819673147033435
  IBS                sr_cost1      Channel B 0.5653656441045931   results 0.565508420361191
  IBS                sr_cost2      Channel B 0.42484080287115206   results 0.425126258032814
  IBS                pnl_cost1     Channel B 8922.75   results 8925.0
  IBS                pnl_cost2     Channel B 6704.25   results 6708.75
  IBS                skew          Channel B 1.3617174721262888   results 1.3616920919029012
  RSI2               sr            Channel B 0.6492954724275234   results 0.6494331452653861
  RSI2               sr_daily      Channel B 0.04090177017722435   results 0.040910442750826
  RSI2               psr           Channel B 0.9346133939057468   results 0.9346545125397911
  RSI2               total_pnl     Channel B 10631.75   results 10634.0
  RSI2               total_costs   Channel B 1545.75   results 1543.5
  RSI2               changes       Channel B 639.0   results 638.0
  RSI2               sides         Channel B 687.0   results 686.0
  RSI2               sr_h2         Channel B 0.3472694661382599   results 0.3475188306474339
  RSI2               sr_cost1      Channel B 0.6492954724275234   results 0.6494331452653861
  RSI2               sr_cost2      Channel B 0.5548683259643219   results 0.5551435803160815
  RSI2               pnl_cost1     Channel B 10631.75   results 10634.0
  RSI2               pnl_cost2     Channel B 9086.0   results 9090.5
  RSI2               skew          Channel B 1.1586576574937375   results 1.1586331400085024
  TurnaroundTuesday  sr            Channel B -0.4494531758400351   results -0.4491749935133323
  TurnaroundTuesday  sr_daily      Channel B -0.0283128887914504   results -0.0282953649520316
  TurnaroundTuesday  psr           Channel B 0.15170659863888086   results 0.1518558345868216
  TurnaroundTuesday  total_pnl     Channel B -3637.0   results -3634.75
  TurnaroundTuesday  total_costs   Channel B 1185.75   results 1183.5
  TurnaroundTuesday  changes       Channel B 527.0   results 526.0
  TurnaroundTuesday  sides         Channel B 527.0   results 526.0
  TurnaroundTuesday  sr_h2         Channel B -0.5807750779556102   results -0.5802011132942624
  TurnaroundTuesday  sr_cost1      Channel B -0.4494531758400351   results -0.4491749935133323
  TurnaroundTuesday  sr_cost2      Channel B -0.5957131821734067   results -0.5951570352525785
  TurnaroundTuesday  pnl_cost1     Channel B -3637.0   results -3634.75
  TurnaroundTuesday  pnl_cost2     Channel B -4822.75   results -4818.25
  TurnaroundTuesday  skew          Channel B -0.2479151991062988   results -0.2479675302135212
  OrderFlowPlus      sr            Channel B -10.748309444046493   results -10.748514317204751
  OrderFlowPlus      sr_daily      Channel B -0.6770798524598555   results -0.677092758255738
  OrderFlowPlus      total_pnl     Channel B -101504.75   results -101502.5
  OrderFlowPlus      total_costs   Channel B 95886.0   results 95883.75
  OrderFlowPlus      mdd           Channel B 101504.75   results 101502.5
  OrderFlowPlus      changes       Channel B 40607.0   results 40606.0
  OrderFlowPlus      sides         Channel B 42616.0   results 42615.0
  OrderFlowPlus      sr_h2         Channel B -10.537545667621183   results -10.537886079742496
  OrderFlowPlus      sr_cost1      Channel B -10.748309444046493   results -10.748514317204751
  OrderFlowPlus      sr_cost2      Channel B -20.199836364384183   results -20.20091150521209
  OrderFlowPlus      pnl_cost1     Channel B -101504.75   results -101502.5
  OrderFlowPlus      pnl_cost2     Channel B -197390.75   results -197386.25
  OrderFlowPlus      skew          Channel B -0.049370846957900845   results -0.0490823635584448
  OrderFlowPlus      kurt          Channel B 7.133649176636639   results 7.1335851486836725
  OrderFlowPlus      corr_bh       Channel B 0.1091611692246821   results 0.1091651171259057

===== variant nolast, costs 1x =====
rank order identical to ranking.csv: False
  rank  1: Channel B RSI14              results RSI14              
  rank  2: Channel B RSI2               results RSI2               
  rank  3: Channel B IBS                results ConsecDays         <-- differs
  rank  4: Channel B ConsecDays         results IBS                <-- differs
  rank  5: Channel B WideRangeBar       results WideRangeBar       
  rank  6: Channel B ATRRegime          results ATRRegime          
  rank  7: Channel B VRPProxy           results VRPProxy           
  rank  8: Channel B SMA200Trend        results SMA200Trend        
  rank  9: Channel B CompositeVol       results CompositeVol       
  rank 10: Channel B RVZScore           results RVZScore           
  rank 11: Channel B StochFade          results StochFade          
  rank 12: Channel B EMACross           results EMACross           
  rank 13: Channel B HedgingPressure    results HedgingPressure    
  rank 14: Channel B ConnorsRSI         results ConnorsRSI         
  rank 15: Channel B TurnOfMonth        results TurnOfMonth        
  rank 16: Channel B MACDHistogram      results MACDHistogram      
  rank 17: Channel B TurnaroundTuesday  results TurnaroundTuesday  
  rank 18: Channel B OvernightGap       results OvernightGap       
  rank 19: Channel B VolumeDelta        results VolumeDelta        
  rank 20: Channel B VolumeSpike        results VolumeSpike        
  rank 21: Channel B BollingerPctB      results BollingerPctB      
  rank 22: Channel B LiquiditySweep     results LiquiditySweep     
  rank 23: Channel B VWAPDistance       results VWAPDistance       
  rank 24: Channel B OrderFlowPlus      results OrderFlowPlus      
  rank 25: Channel B SMC                results SMC                
  rank 26: Channel B ChopIndex          results ChopIndex          
  rank 27: Channel B KeyLevels          results KeyLevels          
ranking.csv SR differences > 1e-6: 0 []
metrics_P1.csv cells differing (SR tol 1e-6 abs; others 1e-6 rel): 0

rules whose last frame bar executes a position change (cost charged only in 'literal'): [('IBS', 'D', 1.0), ('RSI2', 'D', 1.0), ('TurnaroundTuesday', 'D', 1.0), ('OrderFlowPlus', '15m', 1.0)]

Channel B ranking (literal): 1 RSI14 0.844658, 2 RSI2 0.649295, 3 IBS 0.565366, 4 ConsecDays 0.568885, 5 WideRangeBar 0.429089, 6 ATRRegime 0.392246, 7 VRPProxy 0.304731, 8 SMA200Trend 0.288767, 9 CompositeVol 0.279981, 10 RVZScore 0.170921, 11 StochFade 0.096565, 12 EMACross -0.159764, 13 HedgingPressure -0.196933, 14 ConnorsRSI -0.225851, 15 TurnOfMonth -0.266218, 16 MACDHistogram -0.386127, 17 TurnaroundTuesday -0.449453, 18 OvernightGap -0.779182, 19 VolumeDelta -2.255404, 20 VolumeSpike -3.117455, 21 BollingerPctB -3.716075, 22 LiquiditySweep -7.407985, 23 VWAPDistance -9.878645, 24 OrderFlowPlus -10.748309, 25 SMC -10.849793, 26 ChopIndex, 27 KeyLevels
summary: {'literal': {'order_same': False, 'n_metric_diffs': 54, 'n_sr_diffs': 4}, 'nolast': {'order_same': False, 'n_metric_diffs': 0, 'n_sr_diffs': 0}}
rc=1
```
```text
$ python -I -B validation/probes/channel_b_backtest/xcheck_dsr_tiebreak.py --results results/v1_last_trade
N = 25, V[SR per day] = 0.055193041, SR0 per day = 0.469194404
tie pair rank 3 ConsecDays (SR 0.568885) / rank 4 IBS (SR 0.565508): |dSR| = 0.003377
   ConsecDays   z = -16.223926  DSR(scipy cdf) = 1.708200e-59  log DSR = -135.3171  NormalDist.cdf = 0.0  committed dsr = np.float64(0.0)
   IBS          z = -16.041457  DSR(scipy cdf) = 3.279835e-58  log DSR = -132.3621  NormalDist.cdf = 0.0  committed dsr = np.float64(0.0)
   PROTOCOL 8 (higher DSR, then A->Z) puts IBS first; committed order does NOT follow it
statistics.NormalDist().cdf(x) == 0.0 for x <= -8.26 (scipy norm.cdf(-8.26) = 7.284e-17)
committed dsr values: [0.0]
rc=1
```

## 4. sha256 before / after

The before snapshot was taken at 17:21:45 CT, before any probe. The after snapshot was taken at
17:53:03 CT. Full lists: `logs/sha256_before.txt` and `logs/sha256_after.txt`. Every `_mutate.py`
block above also prints the sha256 of the original file before and after making the mutant
(always equal). Annotated condensation of `diff sha256_before.txt sha256_after.txt`:

```text
3,4c3,5   backtest/qibt/__pycache__/{cli,data}.cpython-39.pyc changed; bootstrap.cpython-39.pyc added  (other actor; all my runs used -B)
10,11c11,13
< f76f969556eae179cfb38aa9a8a93fd9c87c2af16f7a893d3077f1c1751b08bf *backtest/qibt/cli.py
< 6fe54619ed0317be8f860a4e9aa23ff043bf4bd15d140311203210a6817d080c *backtest/qibt/data.py
> 5f9f133381f65f0e7a458c4372e1aa982af7b3270e75ee3369d0200c698c4e64 *backtest/qibt/bootstrap.py
> 0d7de4cacac9ec47c6affa40c705edb7a269d06281f8e5ec0af49f83c5a70447 *backtest/qibt/cli.py
> 8384a2114bb0b43cb2ff186dd5140fae36f29e0be38a71824a55b762aae8525b *backtest/qibt/data.py
18c20
< a4510f51e4a9260e46294361f2d71ebe9ccb32dc2c69e6a9b1d7fa3877c0fe0f *backtest/PROTOCOL.md
> 03a8fde320540560b32d94bc377c0a7e0133fbb1be006c6c447ee98a6669e65a *backtest/PROTOCOL.md
20,21c22,23
< 979a5bba77b9aed490c1dc49a5fe538b5e97324cb20b7f193e9e5205d945f68d *backtest/data/P1_1min.pkl
< e8228c5f57c3980762b31790874b161b7b57be056f3fe4430d875a9c57d1ace4 *backtest/data/P1_1min.json
> a4a58d681bd44c4671ec037f6a79fa6fdb03aeaacf4445245205c5dc4fff11cc *backtest/data/P1_1min.pkl   (v2 cache, rebuilt by the v2 loader inside my "BT4 falsifier A" process, see 0.1)
> fa0564b435ccb4d47fba3f472aa379afa1e310098c1ecdfc14380c6a63e00438 *backtest/data/P1_1min.json
results/<12 files>  ->  results/v1_last_trade/<12 files>: every sha256 identical (moved by the other actor)
unchanged: backtest/qibt/{__init__,engine,metrics,patterns,rank,signals}.py, backtest/rules.yaml,
           validation/backtest-claims-ledger.md, strategies/QS_*.cs (25 files)
```

The 8 audited v1 `.py` files are preserved byte-identically in `%SCRATCH%\pristine_v1\qibt`
(`logs/pristine_hashes.txt` = the v1 lines of `sha256_before.txt`).

## 5. Reproduce

```bash
cd ninjatrader_quant_indicators          # the v1 sources must be in place, or pass --qibt-root <v1 copy>
bash validation/probes/channel_b_backtest/run_channel_b.sh <SCRATCH_DIR>
bash validation/probes/channel_b_backtest/run_data_falsifiers_pinned.sh <SCRATCH_DIR> <V1_QIBT_ROOT>
```
