# Backtest report - P1, costs 2x, D close settle (A1: NinjaTrader settlement close)

> Educational research only. Not financial advice. A backtest describes how a fixed rule would have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

Protocol: backtest/PROTOCOL.md (rules.yaml version 1, frozen 2026-10-17). Ranks order the rules; they are not significance-tested differences unless DSR says so.

| Item | Value |
|---|---|
| Run (local time) | 2026-10-17 18:17:40 |
| qibt version | 0.1.0 |
| Dataset | P1 (6 NinjaTrader EveryBar files, cache hit) |
| 1-minute bars | 2,142,391 (2020-01-03 16:00:00 -> 2026-02-24 14:53:00) |
| Trading dates in data / in window | 1578 / 1320 |
| Evaluation window | 2021-01-04 -> 2026-02-24 (H1 2021-01-04 -> 2023-07-31, H2 2023-08-01 -> 2026-02-24) |
| D-frame close | settle (A1: NinjaTrader settlement close); window dates by branch: settle 1306, 1500 5, last 9 of 1320 (fallback: off_grid 14) |
| D-frame close, all dates | settle 1558, 1500 9, last 11 of 1578 (fallback: off_grid 20) |
| Cost per side | USD 2.25 x 2 = USD 4.50 |
| DSR trials N / V[SR per day] / SR0 per day | 25 / 0.191778 / 0.8746 |
| Missing weekdays (holidays + gaps) / longest run | 25 / 7 |
| Sessions with < 300 one-minute bars | 2020-01-03 (1), 2021-02-02 (1), 2022-02-01 (1), 2023-02-02 (1), 2024-03-04 (1), 2025-04-02 (1) |
| Wall time | 3.9 s |

## Ranking (SR on P1 at 2x costs, full window)

| Rank | Module | Frame | SR | DSR | PSR(0) | Total P&L USD | MDD USD | Exposure % | Trades | SR H1 | SR H2 | SR 0x | SR 2x | Corr B&H |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | ConsecDays | D | 0.809 | 3.28e-265 | 0.984 | 8,516 | 2,320 | 24.9 | 346 | 1.395 | 0.397 | 0.957 | 0.809 | 0.22 |
| 2 | RSI14 | D | 0.616 | 2.52e-210 | 0.925 | 8,791 | 3,986 | 49.3 | 249 | 0.725 | 0.554 | 0.695 | 0.616 | 0.25 |
| 3 | RSI2 | D | 0.539 | 1.07e-210 | 0.894 | 9,031 | 4,126 | 62.3 | 628 | 1.080 | 0.104 | 0.724 | 0.539 | 0.22 |
| 4 | ATRRegime | D | 0.391 | 1.95e-205 | 0.812 | 7,576 | 7,063 | 97.8 | 8 | 0.271 | 0.511 | 0.393 | 0.391 | 0.93 |
| 5 | WideRangeBar | D | 0.343 | 3.48e-214 | 0.785 | 4,593 | 4,857 | 25.6 | 396 | 0.141 | 0.491 | 0.476 | 0.343 | 0.64 |
| 6 | VRPProxy | D | 0.286 | 3.66e-322 | 0.790 | 1,863 | 1,012 | 0.6 | 6 | 0.607 | 0.353 | 0.290 | 0.286 | 0.31 |
| 7 | SMA200Trend | D | 0.266 | 6.00e-212 | 0.728 | 5,554 | 8,544 | 100.0 | 36 | -0.025 | 0.523 | 0.282 | 0.266 | -0.00 |
| 8 | CompositeVol | D | 0.234 | 6.93e-258 | 0.722 | 1,910 | 2,472 | 13.9 | 115 | -0.248 | 0.511 | 0.298 | 0.234 | 0.14 |
| 9 | RVZScore | D | 0.093 | 6.12e-223 | 0.585 | 1,147 | 3,507 | 29.0 | 187 | 0.157 | 0.049 | 0.163 | 0.093 | 0.15 |
| 10 | StochFade | D | -0.000 | 1.01e-221 | 0.500 | -4 | 7,672 | 71.8 | 330 | 0.121 | -0.094 | 0.092 | -0.000 | 0.15 |
| 11 | IBS | D | -0.031 | 5.73e-223 | 0.471 | -445 | 4,932 | 49.2 | 817 | -0.226 | 0.177 | 0.275 | -0.031 | -0.02 |
| 12 | HedgingPressure | D | -0.028 | 3.35e-223 | 0.475 | -320 | 3,766 | 23.6 | 300 | -0.095 | 0.012 | 0.089 | -0.028 | -0.41 |
| 13 | ConnorsRSI | D | -0.069 | 2.19e-221 | 0.438 | -782 | 5,745 | 20.2 | 361 | -0.501 | 0.196 | 0.076 | -0.069 | 0.30 |
| 14 | EMACross | D | -0.165 | 8.42e-228 | 0.353 | -3,440 | 12,250 | 100.0 | 23 | -0.321 | -0.027 | -0.155 | -0.165 | -0.00 |
| 15 | TurnOfMonth | D | -0.293 | 1.84e-245 | 0.245 | -3,005 | 5,834 | 22.6 | 123 | 0.384 | -0.836 | -0.239 | -0.293 | 0.49 |
| 16 | MACDHistogram | D | -0.365 | 3.07e-233 | 0.202 | -7,611 | 10,504 | 100.0 | 124 | -0.143 | -0.561 | -0.311 | -0.365 | -0.36 |
| 17 | TurnaroundTuesday | D | -0.596 | 2.67e-241 | 0.086 | -4,823 | 5,060 | 20.0 | 527 | -0.467 | -0.732 | -0.303 | -0.596 | 0.39 |
| 18 | OvernightGap | D | -0.981 | 0.000 | 0.001 | -9,769 | 9,881 | 7.7 | 181 | -1.466 | -0.912 | -0.895 | -0.981 | -0.02 |
| 19 | VolumeDelta | 15m | -4.919 | 0.000 | 1.72e-25 | -113,646 | 114,470 | 100.0 | 14139 | -5.031 | -4.812 | 0.635 | -4.919 | -0.00 |
| 20 | VolumeSpike | 15m | -6.108 | 0.000 | 1.23e-42 | -81,237 | 81,617 | 99.6 | 17696 | -6.192 | -6.030 | -0.121 | -6.108 | 0.70 |
| 21 | BollingerPctB | 15m | -7.237 | 6.28e-155 | 5.58e-20 | -69,679 | 69,831 | 99.6 | 14866 | -7.778 | -6.810 | -0.269 | -7.237 | 0.14 |
| 22 | LiquiditySweep | 15m | -13.634 | 9.42e-284 | 2.25e-71 | -113,777 | 113,857 | 99.6 | 22844 | -13.762 | -13.523 | -0.966 | -13.634 | -0.12 |
| 23 | VWAPDistance | 15m | -18.720 | 7.80e-221 | 2.53e-74 | -178,522 | 178,633 | 99.6 | 31013 | -19.123 | -18.461 | -0.375 | -18.720 | -0.05 |
| 24 | OrderFlowPlus | 15m | -20.200 | 0.000 | 3.74e-154 | -197,391 | 197,391 | 99.6 | 40607 | -20.770 | -19.689 | -0.606 | -20.200 | 0.11 |
| 25 | SMC | 15m | -20.616 | 1.76e-184 | 2.57e-67 | -213,068 | 213,068 | 99.8 | 44682 | -21.377 | -19.968 | -0.155 | -20.616 | 0.11 |
| 26 | ChopIndex | - | not backtestable | | | | | | | | | | | |
| 27 | KeyLevels | - | not backtestable | | | | | | | | | | | |
| - | **Buy & hold (benchmark)** | D | 0.584 | - | 0.909 | 12,186 | 6,056 | 100.0 | 1 | 0.400 | 0.748 | 0.584 | 0.584 | 1.00 |

Not backtestable (last numbers, A->Z): ChopIndex - ORIG gives no Buy/Sell class (state only: CHOPPY/CAUTION/TRENDING); KeyLevels - price levels only; ORIG gives no class

Columns: SR annualised (sqrt 252, ddof 1) on daily net USD P&L; PSR(0) and DSR on the per-day SR; MDD of cumulative net P&L from 0; Exposure = %% of window days with a non-zero held position; Trades = position changes executed in the window; SR 0x/2x = same positions at 0x/2x costs; Corr B&H = Pearson correlation of daily net P&L with the benchmark.
