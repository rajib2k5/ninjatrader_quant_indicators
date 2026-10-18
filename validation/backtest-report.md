# Evidence-gated validation report — backtest pass

target:      backtest/ (qibt engine, patterns, rules.yaml, PROTOCOL.md v1 + A1/A1.1/A2), strategies/QS_NN_*.cs
environment: validation/env-pin.txt (NinjaTrader 8.1.8.3; Python 3.9.13, pandas 2.3.3, numpy 2.0.2, pytest 8.4.2, hypothesis 6.141.1)
mode:        Mode 1 (dual subagent): Channel A = documentation subagents (no execution); Channel B = probe
             subagent writing probes from the ledger, not from the engine's tests
ledger:      validation/backtest-claims-ledger.md (frozen 2026-10-17, 22 claims, all material)
channels:    channel-a-backtest.md, channel-a-patterns.md | channel-b-backtest.md, channel-b-patterns.md
adversary:   adversarial-ranking.md (separate Opus validator)

## Verdict: PASS for the ranking as a label order; 3 claims pending a NinjaTrader run; 1 data claim REJECTED (disclosed)

| ID | Claim (short) | A | B | Gate |
|----|---------------|---|---|------|
| BT1 | MES = USD 5 × index | CONFIRMED (CME MES specs) | CONFIRMED (1 pt = USD 5.00, falsifier ×50 fails) | ACCEPTED |
| BT2 | tick 0.25 = USD 1.25 | CONFIRMED | CONFIRMED | ACCEPTED |
| BT3 | USD 1.00/side covers commission + fees | CONFIRMED for default routing (Free 0.94 / Monthly 0.84 / Lifetime 0.64); exceeds with Rithmic/CQG on Free/Monthly (1.19 / 1.09) | engine charges 1.00 + 1.25 per side (bt08) | SPLIT → ACCEPTED for default routing; Rithmic/CQG case covered by the 2× sensitivity, disclosed in README |
| BT4 | Globex 17:00–16:00 CT, halt 16:00–17:00 | CONFIRMED (+ 15:15–15:30 CT halt before 2021-06-28, CME SER-8788R) | CONFIRMED (no bar in (16:00,17:00]; pre-2021 pause seen in P1) | ACCEPTED |
| BT5 | OnBarClose market order fills at next bar open in backtests | CONFIRMED (three NT8 help pages together) | pending: Strategy Analyzer run vs engine trade list | **UNRESOLVED — pending user run** |
| BT6 | Merge Back Adjusted is additive | CONFIRMED | CONFIRMED (0 of 8.57M OHLC values off the 0.25 grid; offsets consistent across files) | ACCEPTED |
| BT7 | P&L = p_t·(O_{t+2} − O_{t+1})·5 | definitional | CONFIRMED (hand fixtures; truncation metamorphic test; falsifier execute-at-O_t fails) | ACCEPTED (B-only, definitional) |
| BT8 | costs = |Δp| × 2.25 | definitional | CONFIRMED after fix F3 (last-bar execution now charged) | ACCEPTED (B-only, revised: yes) |
| BT9 | Sharpe ddof=1 × √252 | CONFIRMED (Lo 2002, publisher abstract/summary) | CONFIRMED (numpy fixture; falsifiers ddof=0, √365 fail) | ACCEPTED |
| BT10 | PSR formula | CONFIRMED (Bailey & López de Prado 2012) | CONFIRMED + paper example reproduced (0.982 / 0.913 / 0.953) | ACCEPTED |
| BT11 | DSR / SR0 formula | CONFIRMED (Bailey & López de Prado 2014) | CONFIRMED + paper example reproduced (SR0 0.1132, DSR 0.9004 / 0.9505) after fix F2 (Φ underflow) | ACCEPTED (revised: yes) |
| BT12 | max drawdown definition | definitional | CONFIRMED | ACCEPTED (B-only, definitional) |
| BT13 | rules.yaml thresholds = ORIG classification | CONFIRMED 25/25 (quotes of ORIG lines) | CONFIRMED (independent parser; rules.yaml ↔ QS literals) | ACCEPTED |
| BT14 | D/15m frames per §3 | notes CME holiday trade dates contradict a fixed 17:00 roll | CONFIRMED (hand fixtures incl. Sunday 17:01, DST weeks) | ACCEPTED as implementation of §3; holiday limitation disclosed (PROTOCOL §9) |
| BT15 | QS_* reproduce QI values and rules | n/a | compile CONFIRMED (79 files rc=0); runtime parity pending | **UNRESOLVED — pending Strategy Analyzer run** |
| BT16 | no realtime orders while BacktestOnly | CONFIRMED for State semantics, but showed a realtime-only guard is insufficient | after the OrdersAllowed() fix: static CONFIRMED (180 tests; falsifier fails); playback check pending | ACCEPTED (static, revised: yes); runtime check pending |
| BT17 | P1 has no gap > 3 trading dates | n/a | **REFUTED**: no bars 2023-04-05 13:03 → 2023-04-16 17:01 (7 weekdays), + seams | **REJECTED** — data defect; no synthetic bars (§3); disclosed |
| BT18 | ranking deterministic | n/a | CONFIRMED (two full runs identical; independent re-computation matches every metric to 1e-6) | ACCEPTED |
| PT1 | hp_score = ORIG HP | CONFIRMED (0 value-changing differences vs QI) | CONFIRMED (2,134,141 bars, 0 mismatches) | ACCEPTED |
| PT2 | sweep End events = ORIG | CONFIRMED | CONFIRMED at ORIG's window 6 (159,702 events, 0/0) | ACCEPTED |
| PT3 | order-flow events = ORIG | CONFIRMED | CONFIRMED (286,630 events, 0/0) | ACCEPTED |
| PT4 | SMC events = ORIG | CONFIRMED | CONFIRMED (374,867 events, 0/0) | ACCEPTED |

Claim count 22: 17 ACCEPTED (4 of them revised after a fix, flagged), 1 ACCEPTED-scoped (BT3),
3 UNRESOLVED pending a NinjaTrader run (BT5, BT15, runtime half of BT16), 1 REJECTED (BT17, data).

## Fixes made because of the validation

- F2: Φ underflow made every DSR 0 and broke the §8 tie rule (Channel B) → erfc/log-tail.
- F3: last-bar execution cost not charged (Channel B) → charged.
- A1: daily close = NinjaTrader settlement close (adversarial validator) — user-chosen, disclosed.
- A1.1: settlement-close grid tolerance = IBS rounding bound (engine agent + main verification).
- BT16: strategies' OrdersAllowed() guard + WaitUntilFlat (Channel A).

## Not validated

- Live or forward performance of any rule. Nothing here is evidence that a rule will be
  profitable; DSR ≈ 0 for all 25 rules.
- Robustness on independent data: the approved online daily datasets (Stooq) could not be
  downloaded by script (bot check); no account-free independent intraday source exists.
- Strategy Analyzer parity (BT5, BT15) and the playback check of the safety guard (BT16).
- The inferred settlement closes against an exact NinjaTrader Day-bar export.
