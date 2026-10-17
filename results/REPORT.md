# Backtest report - P1, costs 1x, D close settle (A1: NinjaTrader settlement close)

> Educational research only. Not financial advice. A backtest describes how a fixed rule would have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

Protocol: backtest/PROTOCOL.md (rules.yaml version 1, frozen 2026-10-17). Ranks order the rules; they are not significance-tested differences unless DSR says so.

| Item | Value |
|---|---|
| Run (local time) | 2026-10-17 18:17:30 |
| qibt version | 0.1.0 |
| Dataset | P1 (6 NinjaTrader EveryBar files, cache hit) |
| 1-minute bars | 2,142,391 (2020-01-03 16:00:00 -> 2026-02-24 14:53:00) |
| Trading dates in data / in window | 1578 / 1320 |
| Evaluation window | 2021-01-04 -> 2026-02-24 (H1 2021-01-04 -> 2023-07-31, H2 2023-08-01 -> 2026-02-24) |
| D-frame close | settle (A1: NinjaTrader settlement close); window dates by branch: settle 1306, 1500 5, last 9 of 1320 (fallback: off_grid 14) |
| D-frame close, all dates | settle 1558, 1500 9, last 11 of 1578 (fallback: off_grid 20) |
| Cost per side | USD 2.25 x 1 = USD 2.25 |
| DSR trials N / V[SR per day] / SR0 per day | 25 / 0.055090 / 0.4688 |
| Missing weekdays (holidays + gaps) / longest run | 25 / 7 |
| Sessions with < 300 one-minute bars | 2020-01-03 (1), 2021-02-02 (1), 2022-02-01 (1), 2023-02-02 (1), 2024-03-04 (1), 2025-04-02 (1) |
| Wall time | 3.5 s |

## Ranking (SR on P1 at 1x costs, full window)

| Rank | Module | Frame | SR | DSR | PSR(0) | Total P&L USD | MDD USD | Exposure % | Trades | SR H1 | SR H2 | SR 0x | SR 2x | Corr B&H |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | ConsecDays | D | 0.883 | 5.86e-70 | 0.991 | 9,294 | 2,279 | 24.9 | 346 | 1.480 | 0.464 | 0.957 | 0.809 | 0.22 |
| 2 | RSI14 | D | 0.656 | 1.03e-56 | 0.937 | 9,351 | 3,972 | 49.3 | 249 | 0.774 | 0.588 | 0.695 | 0.616 | 0.25 |
| 3 | RSI2 | D | 0.632 | 1.13e-56 | 0.929 | 10,577 | 3,910 | 62.3 | 628 | 1.184 | 0.188 | 0.724 | 0.539 | 0.22 |
| 4 | WideRangeBar | D | 0.409 | 1.85e-59 | 0.827 | 5,484 | 4,254 | 25.6 | 396 | 0.223 | 0.549 | 0.476 | 0.343 | 0.64 |
| 5 | ATRRegime | D | 0.392 | 1.10e-57 | 0.813 | 7,594 | 7,058 | 97.8 | 8 | 0.272 | 0.512 | 0.393 | 0.391 | 0.93 |
| 6 | VRPProxy | D | 0.288 | 3.89e-91 | 0.792 | 1,876 | 1,012 | 0.6 | 6 | 0.613 | 0.355 | 0.290 | 0.286 | 0.31 |
| 7 | SMA200Trend | D | 0.274 | 2.58e-60 | 0.734 | 5,716 | 8,400 | 100.0 | 36 | -0.012 | 0.526 | 0.282 | 0.266 | -0.00 |
| 8 | CompositeVol | D | 0.266 | 1.07e-74 | 0.751 | 2,169 | 2,305 | 13.9 | 115 | -0.205 | 0.539 | 0.298 | 0.234 | 0.14 |
| 9 | RVZScore | D | 0.128 | 9.67e-65 | 0.617 | 1,572 | 3,314 | 29.0 | 187 | 0.194 | 0.083 | 0.163 | 0.093 | 0.15 |
| 10 | IBS | D | 0.122 | 6.03e-63 | 0.609 | 1,722 | 4,477 | 49.2 | 817 | -0.067 | 0.323 | 0.275 | -0.031 | -0.02 |
| 11 | StochFade | D | 0.046 | 1.20e-64 | 0.542 | 758 | 7,194 | 71.8 | 330 | 0.172 | -0.052 | 0.092 | -0.000 | 0.15 |
| 12 | HedgingPressure | D | 0.031 | 1.43e-64 | 0.528 | 355 | 3,651 | 23.6 | 300 | -0.018 | 0.062 | 0.089 | -0.028 | -0.41 |
| 13 | ConnorsRSI | D | 0.003 | 2.86e-65 | 0.503 | 37 | 5,232 | 20.2 | 361 | -0.411 | 0.260 | 0.076 | -0.069 | 0.30 |
| 14 | EMACross | D | -0.160 | 2.82e-68 | 0.357 | -3,336 | 12,160 | 100.0 | 23 | -0.316 | -0.023 | -0.155 | -0.165 | -0.00 |
| 15 | TurnOfMonth | D | -0.266 | 9.01e-74 | 0.266 | -2,728 | 5,759 | 22.6 | 123 | 0.415 | -0.811 | -0.239 | -0.293 | 0.49 |
| 16 | MACDHistogram | D | -0.338 | 4.02e-71 | 0.220 | -7,053 | 10,144 | 100.0 | 124 | -0.117 | -0.533 | -0.311 | -0.365 | -0.36 |
| 17 | TurnaroundTuesday | D | -0.449 | 2.86e-73 | 0.152 | -3,637 | 3,893 | 20.0 | 527 | -0.326 | -0.581 | -0.303 | -0.596 | 0.39 |
| 18 | OvernightGap | D | -0.938 | 2.13e-145 | 0.002 | -9,337 | 9,454 | 7.7 | 181 | -1.394 | -0.876 | -0.895 | -0.981 | -0.02 |
| 19 | VolumeDelta | 15m | -2.255 | 5.51e-105 | 2.16e-07 | -50,039 | 51,106 | 100.0 | 14139 | -2.337 | -2.178 | 0.635 | -4.919 | -0.00 |
| 20 | VolumeSpike | 15m | -3.117 | 9.04e-133 | 2.39e-13 | -41,421 | 42,094 | 99.6 | 17696 | -3.222 | -3.020 | -0.121 | -6.108 | 0.69 |
| 21 | BollingerPctB | 15m | -3.716 | 1.11e-83 | 5.85e-11 | -36,168 | 36,351 | 99.6 | 14866 | -3.934 | -3.549 | -0.269 | -7.237 | 0.14 |
| 22 | LiquiditySweep | 15m | -7.408 | 1.64e-165 | 8.09e-43 | -60,848 | 60,968 | 99.6 | 22844 | -7.458 | -7.365 | -0.966 | -13.634 | -0.13 |
| 23 | VWAPDistance | 15m | -9.879 | 3.92e-152 | 5.76e-51 | -91,014 | 91,185 | 99.6 | 31013 | -9.695 | -10.106 | -0.375 | -18.720 | -0.06 |
| 24 | OrderFlowPlus | 15m | -10.748 | 7.13e-228 | 4.72e-81 | -101,505 | 101,505 | 99.6 | 40607 | -10.991 | -10.538 | -0.606 | -20.200 | 0.11 |
| 25 | SMC | 15m | -10.850 | 4.73e-120 | 1.24e-43 | -107,282 | 107,282 | 99.8 | 44682 | -11.051 | -10.695 | -0.155 | -20.616 | 0.11 |
| 26 | ChopIndex | - | not backtestable | | | | | | | | | | | |
| 27 | KeyLevels | - | not backtestable | | | | | | | | | | | |
| - | **Buy & hold (benchmark)** | D | 0.584 | - | 0.909 | 12,188 | 6,056 | 100.0 | 1 | 0.400 | 0.748 | 0.584 | 0.584 | 1.00 |

Not backtestable (last numbers, A->Z): ChopIndex - ORIG gives no Buy/Sell class (state only: CHOPPY/CAUTION/TRENDING); KeyLevels - price levels only; ORIG gives no class

Columns: SR annualised (sqrt 252, ddof 1) on daily net USD P&L; PSR(0) and DSR on the per-day SR; MDD of cumulative net P&L from 0; Exposure = %% of window days with a non-zero held position; Trades = position changes executed in the window; SR 0x/2x = same positions at 0x/2x costs; Corr B&H = Pearson correlation of daily net P&L with the benchmark.
