# Backtest report - P1, costs 2x

> Educational research only. Not financial advice. A backtest describes how a fixed rule would have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

Protocol: backtest/PROTOCOL.md (rules.yaml version 1, frozen 2026-10-17). Ranks order the rules; they are not significance-tested differences unless DSR says so.

| Item | Value |
|---|---|
| Run (local time) | 2026-10-17 15:22:42 |
| qibt version | 0.1.0 |
| Dataset | P1 (6 NinjaTrader EveryBar files, cache hit) |
| 1-minute bars | 2,142,391 (2020-01-03 16:00:00 -> 2026-02-24 14:53:00) |
| Trading dates in data / in window | 1578 / 1320 |
| Evaluation window | 2021-01-04 -> 2026-02-24 (H1 2021-01-04 -> 2023-07-31, H2 2023-08-01 -> 2026-02-24) |
| Cost per side | USD 2.25 x 2 = USD 4.50 |
| DSR trials N / V[SR per day] / SR0 per day | 25 / 0.191952 / 0.8750 |
| Missing weekdays (holidays + gaps) / longest run | 25 / 7 |
| Sessions with < 300 one-minute bars | 2020-01-03 (1), 2021-02-02 (1), 2022-02-01 (1), 2023-02-02 (1), 2024-03-04 (1), 2025-04-02 (1) |
| Wall time | 3.3 s |

## Ranking (SR on P1 at 2x costs, full window)

| Rank | Module | Frame | SR | DSR | PSR(0) | Total P&L USD | MDD USD | Exposure % | Trades | SR H1 | SR H2 | SR 0x | SR 2x | Corr B&H |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RSI14 | D | 0.803 | 0.000 | 0.970 | 11,352 | 4,166 | 48.9 | 260 | 1.127 | 0.594 | 0.886 | 0.803 | 0.26 |
| 2 | RSI2 | D | 0.555 | 0.000 | 0.901 | 9,090 | 3,567 | 61.4 | 638 | 0.924 | 0.264 | 0.744 | 0.555 | 0.22 |
| 3 | ConsecDays | D | 0.481 | 0.000 | 0.870 | 4,152 | 3,229 | 24.7 | 338 | 1.026 | -0.131 | 0.657 | 0.481 | 0.01 |
| 4 | IBS | D | 0.425 | 0.000 | 0.838 | 6,709 | 2,784 | 49.9 | 839 | 0.108 | 0.692 | 0.706 | 0.425 | 0.10 |
| 5 | ATRRegime | D | 0.391 | 0.000 | 0.812 | 7,575 | 7,063 | 97.7 | 8 | 0.271 | 0.511 | 0.393 | 0.391 | 0.93 |
| 6 | WideRangeBar | D | 0.362 | 0.000 | 0.798 | 4,854 | 4,939 | 26.0 | 400 | 0.204 | 0.480 | 0.496 | 0.362 | 0.64 |
| 7 | VRPProxy | D | 0.303 | 0.000 | 0.806 | 1,976 | 1,012 | 0.7 | 6 | 0.805 | 0.353 | 0.307 | 0.303 | 0.31 |
| 8 | SMA200Trend | D | 0.281 | 0.000 | 0.739 | 5,858 | 8,240 | 99.9 | 38 | 0.007 | 0.523 | 0.297 | 0.281 | 0.00 |
| 9 | CompositeVol | D | 0.250 | 0.000 | 0.736 | 2,039 | 3,072 | 13.9 | 110 | -0.339 | 0.587 | 0.310 | 0.250 | 0.14 |
| 10 | RVZScore | D | 0.136 | 0.000 | 0.624 | 1,663 | 3,893 | 28.6 | 189 | 0.179 | 0.107 | 0.206 | 0.136 | 0.15 |
| 11 | StochFade | D | 0.052 | 0.000 | 0.547 | 872 | 6,638 | 71.7 | 322 | 0.099 | 0.015 | 0.141 | 0.052 | 0.13 |
| 12 | EMACross | D | -0.165 | 0.000 | 0.353 | -3,440 | 12,250 | 99.9 | 23 | -0.321 | -0.027 | -0.155 | -0.165 | -0.00 |
| 13 | HedgingPressure | D | -0.254 | 0.000 | 0.279 | -3,016 | 4,014 | 22.9 | 300 | -0.393 | -0.184 | -0.140 | -0.254 | -0.42 |
| 14 | TurnOfMonth | D | -0.293 | 0.000 | 0.245 | -3,005 | 5,834 | 22.6 | 123 | 0.384 | -0.836 | -0.239 | -0.293 | 0.49 |
| 15 | ConnorsRSI | D | -0.317 | 0.000 | 0.226 | -3,041 | 7,162 | 21.0 | 387 | -0.123 | -0.472 | -0.134 | -0.317 | 0.18 |
| 16 | MACDHistogram | D | -0.413 | 0.000 | 0.172 | -8,626 | 10,508 | 99.9 | 126 | -0.204 | -0.599 | -0.359 | -0.413 | -0.35 |
| 17 | TurnaroundTuesday | D | -0.595 | 0.000 | 0.086 | -4,818 | 5,060 | 19.9 | 526 | -0.467 | -0.731 | -0.303 | -0.595 | 0.39 |
| 18 | OvernightGap | D | -0.806 | 0.000 | 0.005 | -5,170 | 5,344 | 3.1 | 78 | -0.853 | -0.945 | -0.752 | -0.806 | 0.25 |
| 19 | VolumeDelta | 15m | -4.919 | 0.000 | 0.000 | -113,646 | 114,470 | 100.0 | 14139 | -5.031 | -4.812 | 0.635 | -4.919 | -0.00 |
| 20 | VolumeSpike | 15m | -6.108 | 0.000 | 0.000 | -81,237 | 81,617 | 99.6 | 17696 | -6.192 | -6.030 | -0.121 | -6.108 | 0.70 |
| 21 | BollingerPctB | 15m | -7.237 | 0.000 | 0.000 | -69,679 | 69,831 | 99.6 | 14866 | -7.778 | -6.810 | -0.269 | -7.237 | 0.14 |
| 22 | LiquiditySweep | 15m | -13.634 | 0.000 | 0.000 | -113,777 | 113,857 | 99.6 | 22844 | -13.762 | -13.523 | -0.966 | -13.634 | -0.12 |
| 23 | VWAPDistance | 15m | -18.720 | 0.000 | 0.000 | -178,522 | 178,633 | 99.6 | 31013 | -19.123 | -18.461 | -0.375 | -18.720 | -0.05 |
| 24 | OrderFlowPlus | 15m | -20.201 | 0.000 | 0.000 | -197,386 | 197,386 | 99.6 | 40606 | -20.770 | -19.691 | -0.606 | -20.201 | 0.11 |
| 25 | SMC | 15m | -20.616 | 0.000 | 0.000 | -213,068 | 213,068 | 99.8 | 44682 | -21.377 | -19.968 | -0.155 | -20.616 | 0.11 |
| 26 | ChopIndex | - | not backtestable | | | | | | | | | | | |
| 27 | KeyLevels | - | not backtestable | | | | | | | | | | | |
| - | **Buy & hold (benchmark)** | D | 0.584 | - | 0.909 | 12,186 | 6,056 | 99.9 | 1 | 0.400 | 0.748 | 0.584 | 0.584 | 1.00 |

Not backtestable (last numbers, A->Z): ChopIndex - ORIG gives no Buy/Sell class (state only: CHOPPY/CAUTION/TRENDING); KeyLevels - price levels only; ORIG gives no class

Columns: SR annualised (sqrt 252, ddof 1) on daily net USD P&L; PSR(0) and DSR on the per-day SR; MDD of cumulative net P&L from 0; Exposure = %% of window days with a non-zero held position; Trades = position changes executed in the window; SR 0x/2x = same positions at 0x/2x costs; Corr B&H = Pearson correlation of daily net P&L with the benchmark.
