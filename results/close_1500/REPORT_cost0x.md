# Backtest report - P1, costs 0x, D close 1500 (15:00 CT one-minute close)

> Educational research only. Not financial advice. A backtest describes how a fixed rule would have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

Protocol: backtest/PROTOCOL.md (rules.yaml version 1, frozen 2026-10-17). Ranks order the rules; they are not significance-tested differences unless DSR says so.

| Item | Value |
|---|---|
| Run (local time) | 2026-10-17 22:27:52 |
| qibt version | 0.1.0 |
| Dataset | P1 (6 NinjaTrader EveryBar files, cache hit) |
| 1-minute bars | 2,142,391 (2020-01-03 16:00:00 -> 2026-02-24 14:53:00) |
| Trading dates in data / in window | 1578 / 1320 |
| Evaluation window | 2021-01-04 -> 2026-02-24 (H1 2021-01-04 -> 2023-07-31, H2 2023-08-01 -> 2026-02-24) |
| D-frame close | 1500 (15:00 CT one-minute close); window dates by branch: 1500 1264, last 56 of 1320 |
| D-frame close, all dates | 1500 1512, last 66 of 1578 |
| Cost per side | USD 2.25 x 0 = USD 0.00 |
| DSR trials N / V[SR per day] / SR0 per day | 25 / 0.000999 / 0.0631 |
| Missing weekdays (holidays + gaps) / longest run | 25 / 7 |
| Sessions with < 300 one-minute bars | 2020-01-03 (1), 2021-02-02 (1), 2022-02-01 (1), 2023-02-02 (1), 2024-03-04 (1), 2025-04-02 (1) |
| Wall time | 3.1 s |

## Ranking (SR on P1 at 0x costs, full window)

| Rank | Module | Frame | SR | DSR | PSR(0) | Total P&L USD | MDD USD | Exposure % | Trades | SR H1 | SR H2 | SR 0x | SR 2x | Corr B&H |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RSI2 | D | 0.743 | 0.273 | 0.958 | 12,425 | 3,731 | 62.5 | 637 | 1.325 | 0.275 | 0.743 | 0.556 | 0.22 |
| 2 | RSI14 | D | 0.717 | 0.253 | 0.953 | 10,248 | 3,990 | 49.2 | 253 | 0.880 | 0.621 | 0.717 | 0.638 | 0.25 |
| 3 | ConsecDays | D | 0.716 | 0.229 | 0.969 | 7,680 | 2,455 | 26.4 | 346 | 1.468 | 0.176 | 0.716 | 0.571 | 0.21 |
| 4 | VolumeDelta | 15m | 0.635 | 0.201 | 0.926 | 13,569 | 5,090 | 100.0 | 14139 | 0.593 | 0.674 | 0.635 | -4.919 | -0.01 |
| 5 | IBS | D | 0.485 | 0.121 | 0.864 | 6,978 | 3,625 | 49.4 | 831 | 0.432 | 0.544 | 0.485 | 0.181 | -0.01 |
| 6 | WideRangeBar | D | 0.476 | 0.112 | 0.864 | 6,375 | 4,189 | 25.6 | 396 | 0.305 | 0.606 | 0.476 | 0.343 | 0.64 |
| 7 | ATRRegime | D | 0.393 | 0.084 | 0.813 | 7,612 | 7,054 | 97.8 | 8 | 0.273 | 0.513 | 0.393 | 0.391 | 0.93 |
| 8 | VRPProxy | D | 0.307 | 0.023 | 0.810 | 2,002 | 1,012 | 0.7 | 6 | 0.820 | 0.357 | 0.307 | 0.303 | 0.31 |
| 9 | CompositeVol | D | 0.296 | 0.035 | 0.777 | 2,410 | 2,156 | 13.8 | 115 | -0.168 | 0.566 | 0.296 | 0.232 | 0.14 |
| 10 | SMA200Trend | D | 0.283 | 0.051 | 0.741 | 5,910 | 8,224 | 100.0 | 34 | 0.005 | 0.529 | 0.283 | 0.268 | -0.00 |
| 11 | RVZScore | D | 0.142 | 0.023 | 0.629 | 1,740 | 3,208 | 28.9 | 185 | 0.223 | 0.086 | 0.142 | 0.073 | 0.15 |
| 12 | StochFade | D | 0.124 | 0.022 | 0.612 | 2,061 | 6,166 | 72.0 | 330 | 0.271 | 0.012 | 0.124 | 0.032 | 0.15 |
| 13 | HedgingPressure | D | 0.045 | 0.014 | 0.541 | 521 | 3,556 | 23.2 | 300 | 0.068 | 0.034 | 0.045 | -0.072 | -0.41 |
| 14 | ConnorsRSI | D | -0.046 | 0.008 | 0.459 | -514 | 5,738 | 21.1 | 361 | -0.194 | 0.041 | -0.046 | -0.191 | 0.29 |
| 15 | VolumeSpike | 15m | -0.121 | 0.005 | 0.391 | -1,605 | 8,481 | 99.6 | 17696 | -0.247 | -0.001 | -0.121 | -6.108 | 0.69 |
| 16 | SMC | 15m | -0.155 | 0.004 | 0.362 | -1,496 | 5,220 | 99.8 | 44682 | 0.326 | -0.588 | -0.155 | -20.616 | 0.11 |
| 17 | EMACross | D | -0.184 | 0.003 | 0.336 | -3,850 | 12,070 | 100.0 | 25 | -0.310 | -0.074 | -0.184 | -0.195 | 0.00 |
| 18 | TurnOfMonth | D | -0.239 | 0.002 | 0.287 | -2,451 | 5,685 | 22.6 | 123 | 0.446 | -0.787 | -0.239 | -0.293 | 0.49 |
| 19 | BollingerPctB | 15m | -0.269 | 0.002 | 0.271 | -2,656 | 4,871 | 99.6 | 14866 | -0.162 | -0.361 | -0.269 | -7.237 | 0.13 |
| 20 | TurnaroundTuesday | D | -0.303 | 0.001 | 0.244 | -2,451 | 2,856 | 20.0 | 527 | -0.185 | -0.429 | -0.303 | -0.596 | 0.39 |
| 21 | MACDHistogram | D | -0.376 | 8.10e-04 | 0.195 | -7,842 | 11,131 | 100.0 | 126 | -0.045 | -0.668 | -0.376 | -0.430 | -0.35 |
| 22 | VWAPDistance | 15m | -0.375 | 7.54e-04 | 0.194 | -3,508 | 7,695 | 99.6 | 31013 | 0.622 | -1.234 | -0.375 | -18.720 | -0.07 |
| 23 | OrderFlowPlus | 15m | -0.606 | 1.20e-04 | 0.083 | -5,619 | 5,961 | 99.6 | 40607 | -0.412 | -0.785 | -0.606 | -20.200 | 0.11 |
| 24 | LiquiditySweep | 15m | -0.966 | 2.63e-06 | 0.013 | -7,919 | 8,780 | 99.6 | 22844 | -0.922 | -1.008 | -0.966 | -13.634 | -0.13 |
| 25 | OvernightGap | D | -1.132 | 3.18e-12 | 1.34e-04 | -11,389 | 11,510 | 7.7 | 183 | -1.346 | -1.188 | -1.132 | -1.216 | -0.01 |
| 26 | ChopIndex | - | not backtestable | | | | | | | | | | | |
| 27 | KeyLevels | - | not backtestable | | | | | | | | | | | |
| - | **Buy & hold (benchmark)** | D | 0.584 | - | 0.909 | 12,190 | 6,056 | 100.0 | 1 | 0.400 | 0.748 | 0.584 | 0.584 | 1.00 |

Not backtestable (last numbers, A->Z): ChopIndex - ORIG gives no Buy/Sell class (state only: CHOPPY/CAUTION/TRENDING); KeyLevels - price levels only; ORIG gives no class

Columns: SR annualised (sqrt 252, ddof 1) on daily net USD P&L; PSR(0) and DSR on the per-day SR; MDD of cumulative net P&L from 0; Exposure = %% of window days with a non-zero held position; Trades = position changes executed in the window; SR 0x/2x = same positions at 0x/2x costs; Corr B&H = Pearson correlation of daily net P&L with the benchmark.
