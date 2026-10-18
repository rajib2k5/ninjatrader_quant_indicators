# Backtest claims ledger (third EGV pass)

status: FROZEN 2026-10-17 (before any backtest run). Same rules as the other ledgers: no claim is
added, dropped or reworded after freeze; misses go to `validation/addenda.md`.
target: `backtest/` (engine, metrics, rules, data loader), `strategies/QS_*.cs`, `backtest/PROTOCOL.md`
tier: 2 (money, no oracle). Mode 1: Channel A = documentation subagent (no execution);
Channel B = probe subagent writing tests FROM THIS LEDGER, not from the engine code.

Every material claim starts REJECTED.

| ID | Cat | Mat | Claim | Falsifier | Channel A source to check | Channel B probe (pre-registered) |
|----|-----|-----|-------|-----------|---------------------------|----------------------------------|
| BT1 | env | M | The CME Micro E-mini S&P 500 (MES) contract unit is USD 5 × the S&P 500 index | spec page states another multiplier | CME Group MES contract specifications page | engine: 1-point move on 1 contract = USD 5.00 exactly |
| BT2 | env | M | MES minimum price fluctuation is 0.25 index points = USD 1.25 | spec states another tick | CME MES specs | cost model: 1-tick slippage = USD 1.25 |
| BT3 | env | M | The assumed USD 1.00 per side covers NinjaTrader's published MES commission plus CME exchange and NFA fees for a retail account | published all-in > 1.00 | NinjaTrader pricing / commissions page; CME fee schedule; NFA assessment fee | N/A-by-construction until split |
| BT4 | env | M | CME Globex equity index futures trade Sunday–Friday 17:00–16:00 CT with a daily 16:00–17:00 CT halt | CME publishes other hours | CME ES/MES trading hours page | session builder: no trading date contains a bar timestamped in (16:00, 17:00] CT on P1 |
| BT5 | sem | M | A NinjaTrader 8 strategy with Calculate.OnBarClose that submits a market order in OnBarUpdate is filled at the open of the next bar in historical backtests (Standard fill resolution) | docs say fill at same bar close | NT8 help: Calculate, "Understanding historical fill processing" | Strategy Analyzer run of one QS_* vs the Python engine trade list (user-run) |
| BT6 | sem | M | NinjaTrader's "Merge back adjusted" policy adds the roll difference to prior prices (additive), preserving point differences but not ratios | docs describe ratio adjustment | NT8 help: Merge Policy / Instruments | P1 has no quarterly roll jump > 3× median daily range at roll dates |
| BT7 | alg | M | Engine P&L of bar t+1 = p_t × (Open_{t+2} − Open_{t+1}) × 5, with p_t decided at bar t's close | hand-computed P&L differs | N/A-by-construction (definitional, PROTOCOL §4) | hand fixtures + no-look-ahead metamorphic test (mutating bars > t+2 never changes P&L ≤ t+1) |
| BT8 | alg | M | Costs are charged as |p_t − p_{t−1}| × USD 2.25 at execution | cost total differs from hand count | N/A-by-construction | flip long→short charges 2 sides; hold charges 0; 0×/2× scale linearly |
| BT9 | alg | M | Annualised Sharpe = mean/std(ddof=1) of daily P&L × √252, and the √252 scaling assumes iid daily returns | Lo (2002) states a different estimator/assumption | Lo, "The Statistics of Sharpe Ratios", FAJ 58(4) 2002 | numeric fixture vs numpy; scale invariance under P&L × k |
| BT10 | alg | M | PSR(SR*) = Φ((ŜR − SR*)·√(n−1) / √(1 − γ̂3·ŜR + (γ̂4 − 1)/4·ŜR²)) with ŜR non-annualised and γ̂4 non-excess kurtosis | paper's formula differs | Bailey & López de Prado (2012), "The Sharpe Ratio Efficient Frontier", J. of Risk 15(2) | PSR = 0.5 when ŜR = SR*; increases with n; matches paper numeric example if one exists |
| BT11 | alg | M | DSR = PSR(SR0), SR0 = √V[ŜR_n]·((1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(N·e))), γ = Euler–Mascheroni | paper's formula differs | Bailey & López de Prado (2014), "The Deflated Sharpe Ratio", J. Portfolio Mgmt 40(5) | DSR ≤ PSR(0); DSR decreases in N; reproduces the paper's numeric example to 3 decimals |
| BT12 | alg | M | Max drawdown = max over t of (running max of cumulative P&L − cumulative P&L) | hand fixture differs | N/A-by-construction | hand fixtures incl. monotone up (MDD 0) |
| BT13 | sem | M | Every rules.yaml threshold equals the ORIG UpdateDataBoxValues classification at the cited lines | ORIG line shows another threshold or comparison | ORIG source (static read) | rule table parsed from rules.yaml equals thresholds parsed from QS_*.cs (generated parity) |
| BT14 | sem | M | The D-frame aggregation (17:00 CT trading-date roll, first-open/max/min/last-close/sum) and 15m right-labelled bars are computed as PROTOCOL §3 states | fixture differs | N/A-by-construction | hand fixtures incl. a Sunday 17:01 bar, a DST-change week, and a 16:00 bar |
| BT15 | sem | M | Each QS_* strategy reproduces its QI module's value at every bar (transplanted code) and enters/exits per rules.yaml | Strategy Analyzer trades differ from the Python engine on the same bars beyond fill-model differences | N/A-by-construction | compile probe (all QS_*); user-run Strategy Analyzer vs engine trade list on P1 D frame |
| BT16 | sem | M | QS_* strategies cannot submit orders in State.Realtime while BacktestOnly = true (the default) | an order submitted in realtime with default settings | NT8 help: State, OnBarUpdate | static test: every order call is guarded; default true; user-run playback check |
| BT17 | env | M | P1 covers 2020-01-03 → 2026-02-24 with no gap > 3 trading dates and no duplicated bar after de-duplication | data shows otherwise | N/A-by-construction | data-integrity tests on the loaded P1 |
| BT18 | num | M | The ranking is a deterministic function of P1, rules.yaml and PROTOCOL (re-running yields the identical order and SRs to 1e-9) | two runs differ | N/A-by-construction | run twice, diff outputs |

Pattern-module ports (`backtest/qibt/patterns.py`: HP score, LiquiditySweep, OrderFlowPlus, SMC)
carry one more claim each, decided against the ORIG DataBox values in P1 (the files carry ORIG's
own per-bar `databox_HPScore`, `databox_LiqSweep`, `databox_OFSignal`, `databox_SMCSignal`):

| ID | Claim | Channel B probe |
|----|-------|-----------------|
| PT1 | `hp_score` equals ORIG databox_HPScore on P1 1-minute bars (bar ≥ 50) within 1e-3 | differential on ≥ 200,000 bars |
| PT2 | `sweep_structure`/confidence equal ORIG LiqSweep events (End events) on P1 1-minute bars | event-set equality (bar, confidence) |
| PT3 | `ofp_structure`/confidence equal ORIG OFSignal events on P1 1-minute bars | event-set equality |
| PT4 | `smc_structure`/confidence equal ORIG SMCSignal events on P1 1-minute bars | event-set equality |
Channel A for PT1–PT4: static side-by-side of the port vs ORIG source lines.

Claim count: 22 (all material).
