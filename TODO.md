# Work tracker — backtests, tests, ranking, relabel (started 2026-10-17)

Status: [ ] open · [~] in progress · [x] done (only with evidence run in-session) · [!] blocked

| # | Outcome | Owner | Status | Evidence |
|---|---------|-------|--------|----------|
| 1 | Protocol, rules.yaml and backtest claims ledger frozen before any run | main | [x] | backtest/PROTOCOL.md, backtest/rules.yaml, validation/backtest-claims-ledger.md (2026-10-17) |
| 2 | Online dataset shortlist with provenance/licence/size (docs/DATASETS.md) | agent: datasets (sonnet) | [x] | docs/DATASETS.md read by main: R1 Stooq SPY.US daily, R3 Stooq ES.F daily, no account-free intraday source |
| 3 | User approves which online datasets to download | user | [!] | approved R1+R3 (2026-10-17); curl got a Stooq bot-verification page (not solved, by policy) - user must download in a browser |
| 4 | Python ports of HP / LiquiditySweep / OrderFlowPlus / SMC, matched to ORIG on P1 (PT1–PT4) | agent: patterns (opus) | [x] | validation/channel-b-patterns.md: PT1-PT4 0 mismatches on 2,134,141 bars (at ORIG's window 6), falsifiers fail; main re-ran backtest fast suite 358 passed |
| 5 | Backtest engine + loader + metrics + ranking CLI with unit/integration tests | agent: engine (opus) | [x] | main re-ran: backtest/tests -m 'not slow' 358 passed; results/ written by qibt.cli |
| 6 | QS_* NinjaScript strategies generated from the QI modules + rules.yaml, all compile | agent: strategies (sonnet) | [x] | re-run by main: 25 QS files; compile_probe indicators+strategies rc=0; test_strategies_static.py 181 passed |
| 7 | Channel A on BT1–BT18, PT1–PT4 | agent: channel A (opus) | [~] | |
| 8 | Channel B on BT1–BT18 (independent probes from the ledger) | agent: channel B (opus) | [~] | |
| 9 | Primary backtest run on P1 + robustness runs; results/ written | main | [ ] | |
| 10 | Adversarial validation of the ranking numbers | agent: validator (opus) | [~] | |
| 11 | Relabel QI_NN_ / QS_NN_ / QIV_NN_ by rank; tests, harness, README, NT folder updated | main | [~] | tool backtest/relabel.py tested on a scratch copy: 27 renamed, compile rc=0, idempotent; awaiting ranking |
| 12 | Full test suite + compile probe green after relabel | main | [ ] | |
| 13 | Branch → PR → merge to main; NinjaTrader folder synced | main | [ ] | |
| 14 | User: F5 + Strategy Analyzer cross-check of one QS (BT5/BT15) | user | [ ] | |
