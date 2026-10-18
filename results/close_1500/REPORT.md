# Backtest report - P1, costs 1x, D close 1500 (15:00 CT one-minute close)

> Educational research only. Not financial advice. A backtest describes how a fixed rule would have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

Protocol: backtest/PROTOCOL.md (rules.yaml version 1, frozen 2026-10-17). Ranks order the rules; they are not significance-tested differences unless DSR says so.

| Item | Value |
|---|---|
| Run (local time) | 2026-10-17 22:27:48 |
| qibt version | 0.1.0 |
| Dataset | P1 (6 NinjaTrader EveryBar files, cache hit) |
| 1-minute bars | 2,142,391 (2020-01-03 16:00:00 -> 2026-02-24 14:53:00) |
| Trading dates in data / in window | 1578 / 1320 |
| Evaluation window | 2021-01-04 -> 2026-02-24 (H1 2021-01-04 -> 2023-07-31, H2 2023-08-01 -> 2026-02-24) |
| D-frame close | 1500 (15:00 CT one-minute close); window dates by branch: 1500 1264, last 56 of 1320 |
| D-frame close, all dates | 1500 1512, last 66 of 1578 |
| Cost per side | USD 2.25 x 1 = USD 2.25 |
| DSR trials N / V[SR per day] / SR0 per day | 25 / 0.054871 / 0.4678 |
| Missing weekdays (holidays + gaps) / longest run | 25 / 7 |
| Sessions with < 300 one-minute bars | 2020-01-03 (1), 2021-02-02 (1), 2022-02-01 (1), 2023-02-02 (1), 2024-03-04 (1), 2025-04-02 (1) |
| Wall time | 3.4 s |

## Ranking (SR on P1 at 1x costs, full window)

| Rank | Module | Frame | SR | DSR | PSR(0) | Total P&L USD | MDD USD | Exposure % | Trades | SR H1 | SR H2 | SR 0x | SR 2x | Corr B&H |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RSI14 | D | 0.678 | 3.98e-56 | 0.943 | 9,678 | 4,089 | 49.2 | 253 | 0.831 | 0.587 | 0.717 | 0.638 | 0.25 |
| 2 | RSI2 | D | 0.649 | 3.49e-56 | 0.934 | 10,866 | 3,844 | 62.5 | 637 | 1.220 | 0.191 | 0.743 | 0.556 | 0.22 |
| 3 | ConsecDays | D | 0.644 | 3.13e-68 | 0.951 | 6,902 | 2,702 | 26.4 | 346 | 1.383 | 0.111 | 0.716 | 0.571 | 0.21 |
| 4 | WideRangeBar | D | 0.409 | 3.22e-59 | 0.827 | 5,484 | 4,254 | 25.6 | 396 | 0.223 | 0.549 | 0.476 | 0.343 | 0.64 |
| 5 | ATRRegime | D | 0.392 | 1.87e-57 | 0.813 | 7,594 | 7,058 | 97.8 | 8 | 0.272 | 0.512 | 0.393 | 0.391 | 0.93 |
| 6 | IBS | D | 0.333 | 7.88e-59 | 0.776 | 4,790 | 3,697 | 49.4 | 831 | 0.275 | 0.397 | 0.485 | 0.181 | -0.01 |
| 7 | VRPProxy | D | 0.305 | 1.74e-92 | 0.808 | 1,989 | 1,012 | 0.7 | 6 | 0.812 | 0.355 | 0.307 | 0.303 | 0.31 |
| 8 | SMA200Trend | D | 0.276 | 4.86e-60 | 0.735 | 5,757 | 8,359 | 100.0 | 34 | -0.007 | 0.526 | 0.283 | 0.268 | -0.00 |
| 9 | CompositeVol | D | 0.264 | 2.53e-74 | 0.749 | 2,151 | 2,323 | 13.8 | 115 | -0.211 | 0.539 | 0.296 | 0.232 | 0.14 |
| 10 | RVZScore | D | 0.107 | 1.37e-64 | 0.598 | 1,319 | 3,370 | 28.9 | 185 | 0.185 | 0.053 | 0.142 | 0.073 | 0.15 |
| 11 | StochFade | D | 0.078 | 6.21e-64 | 0.571 | 1,298 | 6,648 | 72.0 | 330 | 0.219 | -0.030 | 0.124 | 0.032 | 0.15 |
| 12 | HedgingPressure | D | -0.013 | 2.32e-65 | 0.488 | -154 | 3,666 | 23.2 | 300 | -0.011 | -0.016 | 0.045 | -0.072 | -0.41 |
| 13 | ConnorsRSI | D | -0.118 | 1.07e-65 | 0.394 | -1,333 | 6,246 | 21.1 | 361 | -0.291 | -0.021 | -0.046 | -0.191 | 0.29 |
| 14 | EMACross | D | -0.190 | 1.40e-68 | 0.332 | -3,962 | 12,160 | 100.0 | 25 | -0.316 | -0.079 | -0.184 | -0.195 | 0.00 |
| 15 | TurnOfMonth | D | -0.266 | 1.69e-73 | 0.266 | -2,728 | 5,759 | 22.6 | 123 | 0.415 | -0.811 | -0.239 | -0.293 | 0.49 |
| 16 | MACDHistogram | D | -0.403 | 4.94e-72 | 0.178 | -8,410 | 11,500 | 100.0 | 126 | -0.071 | -0.697 | -0.376 | -0.430 | -0.35 |
| 17 | TurnaroundTuesday | D | -0.449 | 5.27e-73 | 0.152 | -3,637 | 3,893 | 20.0 | 527 | -0.326 | -0.581 | -0.303 | -0.596 | 0.39 |
| 18 | OvernightGap | D | -1.174 | 2.44e-172 | 6.74e-05 | -11,821 | 11,938 | 7.7 | 183 | -1.415 | -1.224 | -1.132 | -1.216 | -0.01 |
| 19 | VolumeDelta | 15m | -2.255 | 1.13e-104 | 2.16e-07 | -50,039 | 51,106 | 100.0 | 14139 | -2.337 | -2.178 | 0.635 | -4.919 | -0.00 |
| 20 | VolumeSpike | 15m | -3.117 | 2.09e-132 | 2.39e-13 | -41,421 | 42,094 | 99.6 | 17696 | -3.222 | -3.020 | -0.121 | -6.108 | 0.69 |
| 21 | BollingerPctB | 15m | -3.716 | 1.82e-83 | 5.85e-11 | -36,168 | 36,351 | 99.6 | 14866 | -3.934 | -3.549 | -0.269 | -7.237 | 0.14 |
| 22 | LiquiditySweep | 15m | -7.408 | 3.45e-165 | 8.09e-43 | -60,848 | 60,968 | 99.6 | 22844 | -7.458 | -7.365 | -0.966 | -13.634 | -0.13 |
| 23 | VWAPDistance | 15m | -9.879 | 7.05e-152 | 5.76e-51 | -91,014 | 91,185 | 99.6 | 31013 | -9.695 | -10.106 | -0.375 | -18.720 | -0.06 |
| 24 | OrderFlowPlus | 15m | -10.748 | 1.66e-227 | 4.72e-81 | -101,505 | 101,505 | 99.6 | 40607 | -10.991 | -10.538 | -0.606 | -20.200 | 0.11 |
| 25 | SMC | 15m | -10.850 | 7.33e-120 | 1.24e-43 | -107,282 | 107,282 | 99.8 | 44682 | -11.051 | -10.695 | -0.155 | -20.616 | 0.11 |
| 26 | ChopIndex | - | not backtestable | | | | | | | | | | | |
| 27 | KeyLevels | - | not backtestable | | | | | | | | | | | |
| - | **Buy & hold (benchmark)** | D | 0.584 | - | 0.909 | 12,188 | 6,056 | 100.0 | 1 | 0.400 | 0.748 | 0.584 | 0.584 | 1.00 |

Not backtestable (last numbers, A->Z): ChopIndex - ORIG gives no Buy/Sell class (state only: CHOPPY/CAUTION/TRENDING); KeyLevels - price levels only; ORIG gives no class

Columns: SR annualised (sqrt 252, ddof 1) on daily net USD P&L; PSR(0) and DSR on the per-day SR; MDD of cumulative net P&L from 0; Exposure = %% of window days with a non-zero held position; Trades = position changes executed in the window; SR 0x/2x = same positions at 0x/2x costs; Corr B&H = Pearson correlation of daily net P&L with the benchmark.
