# Block-bootstrap rank probabilities - P1, A1 settlement close, 1x costs

> Educational research only. Not financial advice. See DISCLAIMER.md.

Stationary block bootstrap (Politis & Romano 1994): mean block 10 days, 1000 resamples, seed 12345; all 25 rules resampled on the SAME day indices in each resample (cross-correlation kept); 1320 trading days of net daily P&L from `results/daily_pnl_P1.csv`, published ranks from `results/ranking.csv`. A resample with zero variance ranks that rule last. These are sampling-noise statements about this one P1 history, not forecasts.

## P(rank 1 of 25) per rule

| Published rank | Module | Published SR | P(rank 1) | P(rank <= 4) | Median bootstrap rank |
|---:|---|---:|---:|---:|---:|
| 1 | ConsecDays | 0.883 | 0.450 | 0.855 | 2 |
| 2 | RSI14 | 0.656 | 0.185 | 0.665 | 3 |
| 3 | RSI2 | 0.632 | 0.105 | 0.619 | 3.5 |
| 4 | WideRangeBar | 0.409 | 0.052 | 0.356 | 6 |
| 5 | ATRRegime | 0.392 | 0.099 | 0.357 | 6 |
| 6 | VRPProxy | 0.288 | 0.004 | 0.162 | 7 |
| 7 | SMA200Trend | 0.274 | 0.051 | 0.256 | 8 |
| 8 | CompositeVol | 0.266 | 0.003 | 0.202 | 8 |
| 9 | RVZScore | 0.128 | 0.019 | 0.114 | 10 |
| 10 | IBS | 0.122 | 0.008 | 0.125 | 10 |
| 11 | StochFade | 0.046 | 0.000 | 0.045 | 11 |
| 12 | HedgingPressure | 0.031 | 0.015 | 0.104 | 11 |
| 13 | ConnorsRSI | 0.029 | 0.000 | 0.034 | 11 |
| 14 | EMACross | -0.160 | 0.003 | 0.044 | 14 |
| 15 | TurnOfMonth | -0.266 | 0.002 | 0.031 | 14 |
| 16 | MACDHistogram | -0.338 | 0.002 | 0.025 | 15 |
| 17 | TurnaroundTuesday | -0.449 | 0.001 | 0.004 | 16 |
| 18 | OvernightGap | -0.938 | 0.001 | 0.002 | 18 |
| 19 | VolumeDelta | -2.255 | 0.000 | 0.000 | 19 |
| 20 | VolumeSpike | -3.117 | 0.000 | 0.000 | 20 |
| 21 | BollingerPctB | -3.716 | 0.000 | 0.000 | 21 |
| 22 | LiquiditySweep | -7.408 | 0.000 | 0.000 | 22 |
| 23 | VWAPDistance | -9.879 | 0.000 | 0.000 | 23 |
| 24 | OrderFlowPlus | -10.748 | 0.000 | 0.000 | 24 |
| 25 | SMC | -10.850 | 0.000 | 0.000 | 25 |

## The published top 4

| Module | P(first among the top 4) |
|---|---:|
| ConsecDays | 0.548 |
| RSI14 | 0.223 |
| RSI2 | 0.134 |
| WideRangeBar | 0.095 |

P(exact published top-4 order ConsecDays > RSI14 > RSI2 > WideRangeBar) = **0.146**

## Adjacent published ranks

| Ranks | Pair | P(SR_i > SR_j) |
|---|---|---:|
| 1 vs 2 | ConsecDays > RSI14 | 0.685 |
| 2 vs 3 | RSI14 > RSI2 | 0.528 |
| 3 vs 4 | RSI2 > WideRangeBar | 0.673 |
| 4 vs 5 | WideRangeBar > ATRRegime | 0.526 |
| 5 vs 6 | ATRRegime > VRPProxy | 0.559 |
| 6 vs 7 | VRPProxy > SMA200Trend | 0.582 |
| 7 vs 8 | SMA200Trend > CompositeVol | 0.501 |

## 90% interval of the annualised SR (top 8)

| Rank | Module | Published SR | 5% | 95% |
|---:|---|---:|---:|---:|
| 1 | ConsecDays | 0.883 | 0.35 | 1.39 |
| 2 | RSI14 | 0.656 | 0.07 | 1.29 |
| 3 | RSI2 | 0.632 | 0.09 | 1.25 |
| 4 | WideRangeBar | 0.409 | -0.14 | 1.07 |
| 5 | ATRRegime | 0.392 | -0.26 | 1.15 |
| 6 | VRPProxy | 0.288 | -0.07 | 0.67 |
| 7 | SMA200Trend | 0.274 | -0.43 | 0.89 |
| 8 | CompositeVol | 0.266 | -0.59 | 0.81 |
