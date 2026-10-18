# Backtest report - P1, costs 2x, D close 1500 (15:00 CT one-minute close)

> Educational research only. Not financial advice. A backtest describes how a fixed rule would have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

Protocol: backtest/PROTOCOL.md (rules.yaml version 1, frozen 2026-10-17). Ranks order the rules; they are not significance-tested differences unless DSR says so.

| Item | Value |
|---|---|
| Run (local time) | 2026-10-17 22:27:56 |
| qibt version | 0.1.0 |
| Dataset | P1 (6 NinjaTrader EveryBar files, cache hit) |
| 1-minute bars | 2,142,391 (2020-01-03 16:00:00 -> 2026-02-24 14:53:00) |
| Trading dates in data / in window | 1578 / 1320 |
| Evaluation window | 2021-01-04 -> 2026-02-24 (H1 2021-01-04 -> 2023-07-31, H2 2023-08-01 -> 2026-02-24) |
| D-frame close | 1500 (15:00 CT one-minute close); window dates by branch: 1500 1264, last 56 of 1320 |
| D-frame close, all dates | 1500 1512, last 66 of 1578 |
| Cost per side | USD 2.25 x 2 = USD 4.50 |
| DSR trials N / V[SR per day] / SR0 per day | 25 / 0.191294 / 0.8735 |
| Missing weekdays (holidays + gaps) / longest run | 25 / 7 |
| Sessions with < 300 one-minute bars | 2020-01-03 (1), 2021-02-02 (1), 2022-02-01 (1), 2023-02-02 (1), 2024-03-04 (1), 2025-04-02 (1) |
| Wall time | 2.9 s |

## Ranking (SR on P1 at 2x costs, full window)

| Rank | Module | Frame | SR | DSR | PSR(0) | Total P&L USD | MDD USD | Exposure % | Trades | SR H1 | SR H2 | SR 0x | SR 2x | Corr B&H |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RSI14 | D | 0.638 | 3.89e-209 | 0.931 | 9,109 | 4,188 | 49.2 | 253 | 0.782 | 0.552 | 0.717 | 0.638 | 0.25 |
| 2 | ConsecDays | D | 0.571 | 9.18e-250 | 0.926 | 6,123 | 2,950 | 26.4 | 346 | 1.298 | 0.046 | 0.716 | 0.571 | 0.21 |
| 3 | RSI2 | D | 0.556 | 9.23e-210 | 0.902 | 9,306 | 4,007 | 62.5 | 637 | 1.115 | 0.106 | 0.743 | 0.556 | 0.22 |
| 4 | ATRRegime | D | 0.391 | 6.56e-205 | 0.812 | 7,576 | 7,063 | 97.8 | 8 | 0.271 | 0.511 | 0.393 | 0.391 | 0.93 |
| 5 | WideRangeBar | D | 0.343 | 1.23e-213 | 0.785 | 4,593 | 4,857 | 25.6 | 396 | 0.141 | 0.491 | 0.476 | 0.343 | 0.64 |
| 6 | VRPProxy | D | 0.303 | 0.000 | 0.806 | 1,976 | 1,012 | 0.7 | 6 | 0.805 | 0.353 | 0.307 | 0.303 | 0.31 |
| 7 | SMA200Trend | D | 0.268 | 2.56e-211 | 0.730 | 5,604 | 8,494 | 100.0 | 34 | -0.019 | 0.523 | 0.283 | 0.268 | -0.00 |
| 8 | CompositeVol | D | 0.232 | 6.96e-257 | 0.720 | 1,892 | 2,489 | 13.8 | 115 | -0.255 | 0.511 | 0.296 | 0.232 | 0.14 |
| 9 | IBS | D | 0.181 | 3.40e-214 | 0.660 | 2,604 | 3,769 | 49.4 | 831 | 0.119 | 0.249 | 0.485 | 0.181 | -0.01 |
| 10 | RVZScore | D | 0.073 | 3.85e-222 | 0.567 | 898 | 3,563 | 28.9 | 185 | 0.148 | 0.021 | 0.142 | 0.073 | 0.15 |
| 11 | StochFade | D | 0.032 | 1.85e-220 | 0.529 | 536 | 7,129 | 72.0 | 330 | 0.166 | -0.071 | 0.124 | 0.032 | 0.15 |
| 12 | HedgingPressure | D | -0.072 | 4.53e-225 | 0.434 | -829 | 3,777 | 23.2 | 300 | -0.089 | -0.065 | 0.045 | -0.072 | -0.41 |
| 13 | ConnorsRSI | D | -0.191 | 2.22e-219 | 0.334 | -2,152 | 6,754 | 21.1 | 361 | -0.387 | -0.083 | -0.046 | -0.191 | 0.29 |
| 14 | EMACross | D | -0.195 | 2.39e-228 | 0.327 | -4,075 | 12,250 | 100.0 | 25 | -0.321 | -0.085 | -0.184 | -0.195 | 0.00 |
| 15 | TurnOfMonth | D | -0.293 | 7.34e-245 | 0.245 | -3,005 | 5,834 | 22.6 | 123 | 0.384 | -0.836 | -0.239 | -0.293 | 0.49 |
| 16 | MACDHistogram | D | -0.430 | 7.55e-235 | 0.163 | -8,976 | 11,869 | 100.0 | 126 | -0.097 | -0.726 | -0.376 | -0.430 | -0.35 |
| 17 | TurnaroundTuesday | D | -0.596 | 1.01e-240 | 0.086 | -4,823 | 5,060 | 20.0 | 527 | -0.467 | -0.732 | -0.303 | -0.596 | 0.39 |
| 18 | OvernightGap | D | -1.216 | 0.000 | 3.30e-05 | -12,253 | 12,365 | 7.7 | 183 | -1.484 | -1.259 | -1.132 | -1.216 | -0.01 |
| 19 | VolumeDelta | 15m | -4.919 | 0.000 | 1.72e-25 | -113,646 | 114,470 | 100.0 | 14139 | -5.031 | -4.812 | 0.635 | -4.919 | -0.00 |
| 20 | VolumeSpike | 15m | -6.108 | 0.000 | 1.23e-42 | -81,237 | 81,617 | 99.6 | 17696 | -6.192 | -6.030 | -0.121 | -6.108 | 0.70 |
| 21 | BollingerPctB | 15m | -7.237 | 1.12e-154 | 5.58e-20 | -69,679 | 69,831 | 99.6 | 14866 | -7.778 | -6.810 | -0.269 | -7.237 | 0.14 |
| 22 | LiquiditySweep | 15m | -13.634 | 2.15e-283 | 2.25e-71 | -113,777 | 113,857 | 99.6 | 22844 | -13.762 | -13.523 | -0.966 | -13.634 | -0.12 |
| 23 | VWAPDistance | 15m | -18.720 | 1.34e-220 | 2.53e-74 | -178,522 | 178,633 | 99.6 | 31013 | -19.123 | -18.461 | -0.375 | -18.720 | -0.05 |
| 24 | OrderFlowPlus | 15m | -20.200 | 0.000 | 3.74e-154 | -197,391 | 197,391 | 99.6 | 40607 | -20.770 | -19.689 | -0.606 | -20.200 | 0.11 |
| 25 | SMC | 15m | -20.616 | 2.69e-184 | 2.57e-67 | -213,068 | 213,068 | 99.8 | 44682 | -21.377 | -19.968 | -0.155 | -20.616 | 0.11 |
| 26 | ChopIndex | - | not backtestable | | | | | | | | | | | |
| 27 | KeyLevels | - | not backtestable | | | | | | | | | | | |
| - | **Buy & hold (benchmark)** | D | 0.584 | - | 0.909 | 12,186 | 6,056 | 100.0 | 1 | 0.400 | 0.748 | 0.584 | 0.584 | 1.00 |

Not backtestable (last numbers, A->Z): ChopIndex - ORIG gives no Buy/Sell class (state only: CHOPPY/CAUTION/TRENDING); KeyLevels - price levels only; ORIG gives no class

Columns: SR annualised (sqrt 252, ddof 1) on daily net USD P&L; PSR(0) and DSR on the per-day SR; MDD of cumulative net P&L from 0; Exposure = %% of window days with a non-zero held position; Trades = position changes executed in the window; SR 0x/2x = same positions at 0x/2x costs; Corr B&H = Pearson correlation of daily net P&L with the benchmark.
