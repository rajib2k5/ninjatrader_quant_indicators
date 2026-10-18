# Backtest report - P1, costs 1x, D close last (v1: 16:00 last trade)

> Educational research only. Not financial advice. A backtest describes how a fixed rule would have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

Protocol: backtest/PROTOCOL.md (rules.yaml version 1, frozen 2026-10-17). Ranks order the rules; they are not significance-tested differences unless DSR says so.

| Item | Value |
|---|---|
| Run (local time) | 2026-10-17 18:12:59 |
| qibt version | 0.1.0 |
| Dataset | P1 (6 NinjaTrader EveryBar files, cache hit) |
| 1-minute bars | 2,142,391 (2020-01-03 16:00:00 -> 2026-02-24 14:53:00) |
| Trading dates in data / in window | 1578 / 1320 |
| Evaluation window | 2021-01-04 -> 2026-02-24 (H1 2021-01-04 -> 2023-07-31, H2 2023-08-01 -> 2026-02-24) |
| D-frame close | last (v1: 16:00 last trade); window dates by branch: last 1320 of 1320 |
| D-frame close, all dates | last 1578 of 1578 |
| Cost per side | USD 2.25 x 1 = USD 2.25 |
| DSR trials N / V[SR per day] / SR0 per day | 25 / 0.055192 / 0.4692 |
| Missing weekdays (holidays + gaps) / longest run | 25 / 7 |
| Sessions with < 300 one-minute bars | 2020-01-03 (1), 2021-02-02 (1), 2022-02-01 (1), 2023-02-02 (1), 2024-03-04 (1), 2025-04-02 (1) |
| Wall time | 3.1 s |

## Ranking (SR on P1 at 1x costs, full window)

| Rank | Module | Frame | SR | DSR | PSR(0) | Total P&L USD | MDD USD | Exposure % | Trades | SR H1 | SR H2 | SR 0x | SR 2x | Corr B&H |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RSI14 | D | 0.845 | 4.19e-54 | 0.976 | 11,939 | 4,085 | 48.9 | 260 | 1.181 | 0.628 | 0.886 | 0.803 | 0.26 |
| 2 | RSI2 | D | 0.649 | 1.09e-56 | 0.935 | 10,632 | 3,418 | 61.4 | 639 | 1.033 | 0.347 | 0.744 | 0.555 | 0.22 |
| 3 | IBS | D | 0.565 | 3.27e-58 | 0.906 | 8,923 | 2,596 | 49.9 | 840 | 0.265 | 0.819 | 0.706 | 0.425 | 0.10 |
| 4 | ConsecDays | D | 0.569 | 1.71e-59 | 0.910 | 4,912 | 2,995 | 24.7 | 338 | 1.109 | -0.036 | 0.657 | 0.481 | 0.01 |
| 5 | WideRangeBar | D | 0.429 | 2.95e-59 | 0.839 | 5,754 | 4,327 | 26.0 | 400 | 0.287 | 0.539 | 0.496 | 0.362 | 0.64 |
| 6 | ATRRegime | D | 0.392 | 8.51e-58 | 0.813 | 7,593 | 7,058 | 97.7 | 8 | 0.272 | 0.512 | 0.393 | 0.391 | 0.93 |
| 7 | VRPProxy | D | 0.305 | 4.90e-93 | 0.808 | 1,989 | 1,012 | 0.7 | 6 | 0.812 | 0.355 | 0.307 | 0.303 | 0.31 |
| 8 | SMA200Trend | D | 0.289 | 3.71e-60 | 0.745 | 6,029 | 8,087 | 100.0 | 38 | 0.020 | 0.526 | 0.297 | 0.281 | 0.00 |
| 9 | CompositeVol | D | 0.280 | 2.74e-75 | 0.763 | 2,286 | 2,919 | 13.9 | 110 | -0.297 | 0.613 | 0.310 | 0.250 | 0.14 |
| 10 | RVZScore | D | 0.171 | 1.14e-64 | 0.655 | 2,093 | 3,821 | 28.6 | 189 | 0.219 | 0.140 | 0.206 | 0.136 | 0.15 |
| 11 | StochFade | D | 0.097 | 4.55e-64 | 0.588 | 1,616 | 6,183 | 71.7 | 322 | 0.149 | 0.055 | 0.141 | 0.052 | 0.13 |
| 12 | EMACross | D | -0.160 | 2.14e-68 | 0.357 | -3,336 | 12,160 | 100.0 | 23 | -0.316 | -0.023 | -0.155 | -0.165 | -0.00 |
| 13 | HedgingPressure | D | -0.197 | 4.74e-70 | 0.325 | -2,341 | 3,904 | 22.9 | 300 | -0.314 | -0.137 | -0.140 | -0.254 | -0.42 |
| 14 | ConnorsRSI | D | -0.226 | 1.13e-72 | 0.298 | -2,164 | 6,635 | 21.0 | 387 | -0.021 | -0.387 | -0.134 | -0.317 | 0.18 |
| 15 | TurnOfMonth | D | -0.266 | 6.70e-74 | 0.266 | -2,728 | 5,759 | 22.6 | 123 | 0.415 | -0.811 | -0.239 | -0.293 | 0.49 |
| 16 | MACDHistogram | D | -0.386 | 3.89e-72 | 0.189 | -8,060 | 10,157 | 100.0 | 126 | -0.177 | -0.572 | -0.359 | -0.413 | -0.35 |
| 17 | TurnaroundTuesday | D | -0.449 | 2.14e-73 | 0.152 | -3,637 | 3,893 | 20.0 | 527 | -0.326 | -0.581 | -0.303 | -0.596 | 0.39 |
| 18 | OvernightGap | D | -0.779 | 4.99e-147 | 0.007 | -4,994 | 5,179 | 3.1 | 78 | -0.806 | -0.919 | -0.752 | -0.806 | 0.25 |
| 19 | VolumeDelta | 15m | -2.255 | 3.93e-105 | 2.16e-07 | -50,039 | 51,106 | 100.0 | 14139 | -2.337 | -2.178 | 0.635 | -4.919 | -0.00 |
| 20 | VolumeSpike | 15m | -3.117 | 6.09e-133 | 2.39e-13 | -41,421 | 42,094 | 99.6 | 17696 | -3.222 | -3.020 | -0.121 | -6.108 | 0.69 |
| 21 | BollingerPctB | 15m | -3.716 | 8.78e-84 | 5.85e-11 | -36,168 | 36,351 | 99.6 | 14866 | -3.934 | -3.549 | -0.269 | -7.237 | 0.14 |
| 22 | LiquiditySweep | 15m | -7.408 | 1.15e-165 | 8.09e-43 | -60,848 | 60,968 | 99.6 | 22844 | -7.458 | -7.365 | -0.966 | -13.634 | -0.13 |
| 23 | VWAPDistance | 15m | -9.879 | 2.97e-152 | 5.76e-51 | -91,014 | 91,185 | 99.6 | 31013 | -9.695 | -10.106 | -0.375 | -18.720 | -0.06 |
| 24 | OrderFlowPlus | 15m | -10.748 | 4.80e-228 | 4.72e-81 | -101,505 | 101,505 | 99.6 | 40607 | -10.991 | -10.538 | -0.606 | -20.200 | 0.11 |
| 25 | SMC | 15m | -10.850 | 3.85e-120 | 1.24e-43 | -107,282 | 107,282 | 99.8 | 44682 | -11.051 | -10.695 | -0.155 | -20.616 | 0.11 |
| 26 | ChopIndex | - | not backtestable | | | | | | | | | | | |
| 27 | KeyLevels | - | not backtestable | | | | | | | | | | | |
| - | **Buy & hold (benchmark)** | D | 0.584 | - | 0.909 | 12,188 | 6,056 | 100.0 | 1 | 0.400 | 0.748 | 0.584 | 0.584 | 1.00 |

Not backtestable (last numbers, A->Z): ChopIndex - ORIG gives no Buy/Sell class (state only: CHOPPY/CAUTION/TRENDING); KeyLevels - price levels only; ORIG gives no class

Columns: SR annualised (sqrt 252, ddof 1) on daily net USD P&L; PSR(0) and DSR on the per-day SR; MDD of cumulative net P&L from 0; Exposure = %% of window days with a non-zero held position; Trades = position changes executed in the window; SR 0x/2x = same positions at 0x/2x costs; Corr B&H = Pearson correlation of daily net P&L with the benchmark.
