# Work tracker — backtests, tests, ranking, relabel (started 2026-10-17)

Status: [ ] open · [~] in progress · [x] done (only with evidence run in-session) · [!] blocked

| # | Outcome | Owner | Status | Evidence |
|---|---------|-------|--------|----------|
| 1 | Protocol, rules.yaml and backtest claims ledger frozen before any run | main | [x] | backtest/PROTOCOL.md, backtest/rules.yaml, validation/backtest-claims-ledger.md (2026-10-17) |
| 2 | Online dataset shortlist with provenance/licence/size (docs/DATASETS.md) | agent: datasets (sonnet) | [~] | |
| 3 | User approves which online datasets to download | user | [ ] | |
| 4 | Python ports of HP / LiquiditySweep / OrderFlowPlus / SMC, matched to ORIG on P1 (PT1–PT4) | agent: patterns (opus) | [~] | |
| 5 | Backtest engine + loader + metrics + ranking CLI with unit/integration tests | agent: engine (opus) | [~] | |
| 6 | QS_* NinjaScript strategies generated from the QI modules + rules.yaml, all compile | agent: strategies (sonnet) | [~] | |
| 7 | Channel A on BT1–BT18, PT1–PT4 | agent: channel A (opus) | [~] | |
| 8 | Channel B on BT1–BT18 (independent probes from the ledger) | agent: channel B (opus) | [ ] | |
| 9 | Primary backtest run on P1 + robustness runs; results/ written | main | [ ] | |
| 10 | Adversarial validation of the ranking numbers | agent: validator (opus) | [ ] | |
| 11 | Relabel QI_NN_ / QS_NN_ / QIV_NN_ by rank; tests, harness, README, NT folder updated | main | [ ] | |
| 12 | Full test suite + compile probe green after relabel | main | [ ] | |
| 13 | Branch → PR → merge to main; NinjaTrader folder synced | main | [ ] | |
| 14 | User: F5 + Strategy Analyzer cross-check of one QS (BT5/BT15) | user | [ ] | |
