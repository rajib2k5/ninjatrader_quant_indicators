# Backtest report - P1, costs 0x, D close settle (A1: NinjaTrader settlement close)

> Educational research only. Not financial advice. A backtest describes how a fixed rule would have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

Protocol: backtest/PROTOCOL.md (rules.yaml version 1, frozen 2026-10-17). Ranks order the rules; they are not significance-tested differences unless DSR says so.

| Item | Value |
|---|---|
| Run (local time) | 2026-10-17 18:17:35 |
| qibt version | 0.1.0 |
| Dataset | P1 (6 NinjaTrader EveryBar files, cache hit) |
| 1-minute bars | 2,142,391 (2020-01-03 16:00:00 -> 2026-02-24 14:53:00) |
| Trading dates in data / in window | 1578 / 1320 |
| Evaluation window | 2021-01-04 -> 2026-02-24 (H1 2021-01-04 -> 2023-07-31, H2 2023-08-01 -> 2026-02-24) |
| D-frame close | settle (A1: NinjaTrader settlement close); window dates by branch: settle 1306, 1500 5, last 9 of 1320 (fallback: off_grid 14) |
| D-frame close, all dates | settle 1558, 1500 9, last 11 of 1578 (fallback: off_grid 20) |
| Cost per side | USD 2.25 x 0 = USD 0.00 |
| DSR trials N / V[SR per day] / SR0 per day | 25 / 0.000936 / 0.0611 |
| Missing weekdays (holidays + gaps) / longest run | 25 / 7 |
| Sessions with < 300 one-minute bars | 2020-01-03 (1), 2021-02-02 (1), 2022-02-01 (1), 2023-02-02 (1), 2024-03-04 (1), 2025-04-02 (1) |
| Wall time | 3.0 s |

## Ranking (SR on P1 at 0x costs, full window)

| Rank | Module | Frame | SR | DSR | PSR(0) | Total P&L USD | MDD USD | Exposure % | Trades | SR H1 | SR H2 | SR 0x | SR 2x | Corr B&H |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | ConsecDays | D | 0.957 | 0.486 | 0.995 | 10,072 | 2,239 | 24.9 | 346 | 1.566 | 0.532 | 0.957 | 0.809 | 0.22 |
| 2 | RSI2 | D | 0.724 | 0.283 | 0.954 | 12,122 | 3,792 | 62.3 | 628 | 1.288 | 0.272 | 0.724 | 0.539 | 0.22 |
| 3 | RSI14 | D | 0.695 | 0.261 | 0.948 | 9,911 | 3,959 | 49.3 | 249 | 0.823 | 0.622 | 0.695 | 0.616 | 0.25 |
| 4 | VolumeDelta | 15m | 0.635 | 0.222 | 0.926 | 13,569 | 5,090 | 100.0 | 14139 | 0.593 | 0.674 | 0.635 | -4.919 | -0.01 |
| 5 | WideRangeBar | D | 0.476 | 0.127 | 0.864 | 6,375 | 4,189 | 25.6 | 396 | 0.305 | 0.606 | 0.476 | 0.343 | 0.64 |
| 6 | ATRRegime | D | 0.393 | 0.096 | 0.813 | 7,612 | 7,054 | 97.8 | 8 | 0.273 | 0.513 | 0.393 | 0.391 | 0.93 |
| 7 | CompositeVol | D | 0.298 | 0.042 | 0.778 | 2,428 | 2,139 | 13.9 | 115 | -0.162 | 0.566 | 0.298 | 0.234 | 0.14 |
| 8 | VRPProxy | D | 0.290 | 0.027 | 0.794 | 1,890 | 1,012 | 0.6 | 6 | 0.618 | 0.357 | 0.290 | 0.286 | 0.31 |
| 9 | SMA200Trend | D | 0.282 | 0.058 | 0.739 | 5,878 | 8,256 | 100.0 | 36 | 0.001 | 0.529 | 0.282 | 0.266 | -0.00 |
| 10 | IBS | D | 0.275 | 0.057 | 0.734 | 3,889 | 4,102 | 49.2 | 817 | 0.093 | 0.469 | 0.275 | -0.031 | -0.02 |
| 11 | RVZScore | D | 0.163 | 0.030 | 0.647 | 1,998 | 3,151 | 29.0 | 187 | 0.232 | 0.116 | 0.163 | 0.093 | 0.15 |
| 12 | HedgingPressure | D | 0.089 | 0.022 | 0.580 | 1,030 | 3,536 | 23.6 | 300 | 0.058 | 0.111 | 0.089 | -0.028 | -0.41 |
| 13 | StochFade | D | 0.092 | 0.022 | 0.583 | 1,521 | 6,718 | 71.8 | 330 | 0.223 | -0.009 | 0.092 | -0.000 | 0.15 |
| 14 | ConnorsRSI | D | 0.076 | 0.020 | 0.569 | 856 | 4,719 | 20.2 | 361 | -0.321 | 0.324 | 0.076 | -0.069 | 0.30 |
| 15 | VolumeSpike | 15m | -0.121 | 0.006 | 0.391 | -1,605 | 8,481 | 99.6 | 17696 | -0.247 | -0.001 | -0.121 | -6.108 | 0.69 |
| 16 | SMC | 15m | -0.155 | 0.005 | 0.362 | -1,496 | 5,220 | 99.8 | 44682 | 0.326 | -0.588 | -0.155 | -20.616 | 0.11 |
| 17 | EMACross | D | -0.155 | 0.005 | 0.361 | -3,232 | 12,070 | 100.0 | 23 | -0.310 | -0.018 | -0.155 | -0.165 | -0.00 |
| 18 | TurnOfMonth | D | -0.239 | 0.002 | 0.287 | -2,451 | 5,685 | 22.6 | 123 | 0.446 | -0.787 | -0.239 | -0.293 | 0.49 |
| 19 | BollingerPctB | 15m | -0.269 | 0.003 | 0.271 | -2,656 | 4,871 | 99.6 | 14866 | -0.162 | -0.361 | -0.269 | -7.237 | 0.13 |
| 20 | TurnaroundTuesday | D | -0.303 | 0.002 | 0.244 | -2,451 | 2,856 | 20.0 | 527 | -0.185 | -0.429 | -0.303 | -0.596 | 0.39 |
| 21 | MACDHistogram | D | -0.311 | 0.002 | 0.238 | -6,495 | 9,784 | 100.0 | 124 | -0.092 | -0.505 | -0.311 | -0.365 | -0.36 |
| 22 | VWAPDistance | 15m | -0.375 | 9.72e-04 | 0.194 | -3,508 | 7,695 | 99.6 | 31013 | 0.622 | -1.234 | -0.375 | -18.720 | -0.07 |
| 23 | OrderFlowPlus | 15m | -0.606 | 1.60e-04 | 0.083 | -5,619 | 5,961 | 99.6 | 40607 | -0.412 | -0.785 | -0.606 | -20.200 | 0.11 |
| 24 | OvernightGap | D | -0.895 | 8.40e-09 | 0.003 | -8,905 | 9,026 | 7.7 | 181 | -1.321 | -0.840 | -0.895 | -0.981 | -0.02 |
| 25 | LiquiditySweep | 15m | -0.966 | 3.74e-06 | 0.013 | -7,919 | 8,780 | 99.6 | 22844 | -0.922 | -1.008 | -0.966 | -13.634 | -0.13 |
| 26 | ChopIndex | - | not backtestable | | | | | | | | | | | |
| 27 | KeyLevels | - | not backtestable | | | | | | | | | | | |
| - | **Buy & hold (benchmark)** | D | 0.584 | - | 0.909 | 12,190 | 6,056 | 100.0 | 1 | 0.400 | 0.748 | 0.584 | 0.584 | 1.00 |

Not backtestable (last numbers, A->Z): ChopIndex - ORIG gives no Buy/Sell class (state only: CHOPPY/CAUTION/TRENDING); KeyLevels - price levels only; ORIG gives no class

Columns: SR annualised (sqrt 252, ddof 1) on daily net USD P&L; PSR(0) and DSR on the per-day SR; MDD of cumulative net P&L from 0; Exposure = %% of window days with a non-zero held position; Trades = position changes executed in the window; SR 0x/2x = same positions at 0x/2x costs; Corr B&H = Pearson correlation of daily net P&L with the benchmark.
