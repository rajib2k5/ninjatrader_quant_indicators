# Backtest report - P1, costs 0x, D close last (v1: 16:00 last trade)

> Educational research only. Not financial advice. A backtest describes how a fixed rule would have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

Protocol: backtest/PROTOCOL.md (rules.yaml version 1, frozen 2026-10-17). Ranks order the rules; they are not significance-tested differences unless DSR says so.

| Item | Value |
|---|---|
| Run (local time) | 2026-10-17 22:27:40 |
| qibt version | 0.1.0 |
| Dataset | P1 (6 NinjaTrader EveryBar files, cache hit) |
| 1-minute bars | 2,142,391 (2020-01-03 16:00:00 -> 2026-02-24 14:53:00) |
| Trading dates in data / in window | 1578 / 1320 |
| Evaluation window | 2021-01-04 -> 2026-02-24 (H1 2021-01-04 -> 2023-07-31, H2 2023-08-01 -> 2026-02-24) |
| D-frame close | last (v1: 16:00 last trade); window dates by branch: last 1320 of 1320 |
| D-frame close, all dates | last 1578 of 1578 |
| Cost per side | USD 2.25 x 0 = USD 0.00 |
| DSR trials N / V[SR per day] / SR0 per day | 25 / 0.000957 / 0.0618 |
| Missing weekdays (holidays + gaps) / longest run | 25 / 7 |
| Sessions with < 300 one-minute bars | 2020-01-03 (1), 2021-02-02 (1), 2022-02-01 (1), 2023-02-02 (1), 2024-03-04 (1), 2025-04-02 (1) |
| Wall time | 2.5 s |

## Ranking (SR on P1 at 0x costs, full window)

| Rank | Module | Frame | SR | DSR | PSR(0) | Total P&L USD | MDD USD | Exposure % | Trades | SR H1 | SR H2 | SR 0x | SR 2x | Corr B&H |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RSI14 | D | 0.886 | 0.412 | 0.981 | 12,526 | 4,004 | 48.9 | 260 | 1.235 | 0.661 | 0.886 | 0.803 | 0.26 |
| 2 | RSI2 | D | 0.744 | 0.290 | 0.958 | 12,178 | 3,270 | 61.4 | 639 | 1.142 | 0.431 | 0.744 | 0.555 | 0.22 |
| 3 | IBS | D | 0.706 | 0.260 | 0.951 | 11,141 | 2,442 | 49.9 | 840 | 0.421 | 0.947 | 0.706 | 0.425 | 0.10 |
| 4 | ConsecDays | D | 0.657 | 0.221 | 0.940 | 5,672 | 2,761 | 24.7 | 338 | 1.192 | 0.058 | 0.657 | 0.481 | 0.01 |
| 5 | VolumeDelta | 15m | 0.635 | 0.214 | 0.926 | 13,569 | 5,090 | 100.0 | 14139 | 0.593 | 0.674 | 0.635 | -4.919 | -0.01 |
| 6 | WideRangeBar | D | 0.496 | 0.132 | 0.874 | 6,654 | 4,189 | 26.0 | 400 | 0.369 | 0.597 | 0.496 | 0.362 | 0.64 |
| 7 | ATRRegime | D | 0.393 | 0.092 | 0.813 | 7,611 | 7,054 | 97.7 | 8 | 0.273 | 0.513 | 0.393 | 0.391 | 0.93 |
| 8 | CompositeVol | D | 0.310 | 0.041 | 0.789 | 2,534 | 2,766 | 13.9 | 110 | -0.255 | 0.638 | 0.310 | 0.250 | 0.14 |
| 9 | VRPProxy | D | 0.307 | 0.027 | 0.810 | 2,002 | 1,012 | 0.7 | 6 | 0.820 | 0.357 | 0.307 | 0.303 | 0.31 |
| 10 | SMA200Trend | D | 0.297 | 0.060 | 0.751 | 6,200 | 7,934 | 100.0 | 38 | 0.034 | 0.529 | 0.297 | 0.281 | 0.00 |
| 11 | RVZScore | D | 0.206 | 0.035 | 0.685 | 2,522 | 3,749 | 28.6 | 189 | 0.258 | 0.173 | 0.206 | 0.136 | 0.15 |
| 12 | StochFade | D | 0.141 | 0.027 | 0.627 | 2,361 | 5,729 | 71.7 | 322 | 0.199 | 0.095 | 0.141 | 0.052 | 0.13 |
| 13 | ConnorsRSI | D | -0.056 | 0.009 | 0.449 | -529 | 5,570 | 20.9 | 387 | 0.131 | -0.203 | -0.056 | -0.240 | 0.19 |
| 14 | VolumeSpike | 15m | -0.121 | 0.006 | 0.391 | -1,605 | 8,481 | 99.6 | 17696 | -0.247 | -0.001 | -0.121 | -6.108 | 0.69 |
| 15 | HedgingPressure | D | -0.140 | 0.005 | 0.373 | -1,666 | 3,794 | 22.9 | 300 | -0.236 | -0.091 | -0.140 | -0.254 | -0.42 |
| 16 | SMC | 15m | -0.155 | 0.005 | 0.362 | -1,496 | 5,220 | 99.8 | 44682 | 0.326 | -0.588 | -0.155 | -20.616 | 0.11 |
| 17 | EMACross | D | -0.155 | 0.005 | 0.361 | -3,232 | 12,070 | 100.0 | 23 | -0.310 | -0.018 | -0.155 | -0.165 | -0.00 |
| 18 | TurnOfMonth | D | -0.239 | 0.002 | 0.287 | -2,451 | 5,685 | 22.6 | 123 | 0.446 | -0.787 | -0.239 | -0.293 | 0.49 |
| 19 | BollingerPctB | 15m | -0.269 | 0.002 | 0.271 | -2,656 | 4,871 | 99.6 | 14866 | -0.162 | -0.361 | -0.269 | -7.237 | 0.13 |
| 20 | TurnaroundTuesday | D | -0.303 | 0.002 | 0.244 | -2,451 | 2,856 | 20.0 | 527 | -0.185 | -0.429 | -0.303 | -0.596 | 0.39 |
| 21 | MACDHistogram | D | -0.359 | 0.001 | 0.206 | -7,492 | 9,806 | 100.0 | 126 | -0.149 | -0.545 | -0.359 | -0.413 | -0.35 |
| 22 | VWAPDistance | 15m | -0.375 | 8.93e-04 | 0.194 | -3,508 | 7,695 | 99.6 | 31013 | 0.622 | -1.234 | -0.375 | -18.720 | -0.07 |
| 23 | OrderFlowPlus | 15m | -0.606 | 1.45e-04 | 0.083 | -5,619 | 5,961 | 99.6 | 40607 | -0.412 | -0.785 | -0.606 | -20.200 | 0.11 |
| 24 | OvernightGap | D | -0.752 | 3.51e-08 | 0.010 | -4,819 | 5,015 | 3.1 | 78 | -0.759 | -0.893 | -0.752 | -0.806 | 0.25 |
| 25 | LiquiditySweep | 15m | -0.966 | 3.32e-06 | 0.013 | -7,919 | 8,780 | 99.6 | 22844 | -0.922 | -1.008 | -0.966 | -13.634 | -0.13 |
| 26 | ChopIndex | - | not backtestable | | | | | | | | | | | |
| 27 | KeyLevels | - | not backtestable | | | | | | | | | | | |
| - | **Buy & hold (benchmark)** | D | 0.584 | - | 0.909 | 12,190 | 6,056 | 100.0 | 1 | 0.400 | 0.748 | 0.584 | 0.584 | 1.00 |

Not backtestable (last numbers, A->Z): ChopIndex - ORIG gives no Buy/Sell class (state only: CHOPPY/CAUTION/TRENDING); KeyLevels - price levels only; ORIG gives no class

Columns: SR annualised (sqrt 252, ddof 1) on daily net USD P&L; PSR(0) and DSR on the per-day SR; MDD of cumulative net P&L from 0; Exposure = %% of window days with a non-zero held position; Trades = position changes executed in the window; SR 0x/2x = same positions at 0x/2x costs; Corr B&H = Pearson correlation of daily net P&L with the benchmark.
