# Robustness datasets R1 and R3 (PROTOCOL A3)

> Educational research only. Not financial advice. See DISCLAIMER.md.

Reported next to the ranking; robustness results **never change it** (PROTOCOL section 2). The 18 D-frame rules run on daily bars as delivered (trading date = the row's Date; no settlement inference), with the section 4-7 execution, costs (USD 2.25 x 1 per side), metrics and a 300-bar warm-up. P1 reference = the A1.1 SRs in `results/metrics_P1.csv`. Rank = SR order among the rules run (exact ties A->Z); Spearman = rank correlation of the dataset's SRs with P1's SRs of the same rules (average ranks for ties; rules without an SR are left out); rank change = dataset rank - P1 rank (+ = lower on the dataset).

- **R1** = Stooq SPY.US daily, Open/High/Low/Close x 10 (MES scale), Volume as delivered; Stooq's split/dividend adjustment taken as is.
- **R3** = Stooq ES.F daily from 1997-09-09; HedgingPressure n/a (no volume); roll-gap filter: 0 roll dates, 0 bars with gross P&L set to 0 (bars r-1 and r of each roll date r).
- **R3_unfiltered** = R3 without the roll-gap filter.

**Not run (input file not downloaded):** es_f_d.csv.

## MANIFEST

```
file: spy_us_d.csv  sha256: f48ac8eba9faee0c05dbbd72560d0254f80a0376411325a136c83984f73475b6  data rows: 5444  first: 2005-02-25  last: 2026-10-16  file mtime: 2026-10-18 21:26
```

Rows used: R1 5444. Run 2026-10-18 21:28:34.

## Agreement with P1

| Dataset | Window | First -> last date | Days | Rules with SR | Spearman vs P1 | Buy & hold SR |
|---|---|---|---:|---:|---:|---:|
| R1 | full | 2006-05-05 -> 2026-10-16 | 5144 | 18 | 0.166 | 0.657 |
| R1 | p1window | 2021-01-04 -> 2026-02-24 | 1291 | 18 | 0.631 | 0.824 |

## R1, full window

| Module | P1 SR | P1 rank (of 18) | R1 SR | R1 rank | Rank change |
|---|---:|---:|---:|---:|---:|
| ConsecDays | 0.883 | 1 | 0.107 | 7 | +6 |
| RSI14 | 0.656 | 2 | 0.043 | 10 | +8 |
| RSI2 | 0.632 | 3 | 0.103 | 8 | +5 |
| WideRangeBar | 0.409 | 4 | 0.027 | 11 | +7 |
| ATRRegime | 0.392 | 5 | 0.618 | 1 | -4 |
| VRPProxy | 0.288 | 6 | -0.086 | 14 | +8 |
| SMA200Trend | 0.274 | 7 | 0.371 | 2 | -5 |
| CompositeVol | 0.266 | 8 | -0.036 | 12 | +4 |
| RVZScore | 0.128 | 9 | 0.078 | 9 | +0 |
| IBS | 0.122 | 10 | -0.091 | 15 | +5 |
| StochFade | 0.046 | 11 | -0.049 | 13 | +2 |
| HedgingPressure | 0.031 | 12 | -0.431 | 18 | +6 |
| ConnorsRSI | 0.029 | 13 | 0.112 | 6 | -7 |
| EMACross | -0.160 | 14 | 0.262 | 5 | -9 |
| TurnOfMonth | -0.266 | 15 | 0.270 | 4 | -11 |
| MACDHistogram | -0.338 | 16 | -0.191 | 16 | +0 |
| TurnaroundTuesday | -0.449 | 17 | 0.323 | 3 | -14 |
| OvernightGap | -0.938 | 18 | -0.360 | 17 | -1 |

## R1, p1window window

| Module | P1 SR | P1 rank (of 18) | R1 SR | R1 rank | Rank change |
|---|---:|---:|---:|---:|---:|
| ConsecDays | 0.883 | 1 | 0.496 | 4 | +3 |
| RSI14 | 0.656 | 2 | 0.299 | 6 | +4 |
| RSI2 | 0.632 | 3 | 0.508 | 3 | +0 |
| WideRangeBar | 0.409 | 4 | 0.205 | 9 | +5 |
| ATRRegime | 0.392 | 5 | 0.572 | 1 | -4 |
| VRPProxy | 0.288 | 6 | 0.182 | 10 | +4 |
| SMA200Trend | 0.274 | 7 | 0.566 | 2 | -5 |
| CompositeVol | 0.266 | 8 | -0.087 | 13 | +5 |
| RVZScore | 0.128 | 9 | 0.266 | 7 | -2 |
| IBS | 0.122 | 10 | -0.130 | 14 | +4 |
| StochFade | 0.046 | 11 | 0.090 | 12 | +1 |
| HedgingPressure | 0.031 | 12 | -0.366 | 16 | +4 |
| ConnorsRSI | 0.029 | 13 | 0.142 | 11 | -2 |
| EMACross | -0.160 | 14 | 0.245 | 8 | -6 |
| TurnOfMonth | -0.266 | 15 | -0.233 | 15 | +0 |
| MACDHistogram | -0.338 | 16 | -0.631 | 18 | +2 |
| TurnaroundTuesday | -0.449 | 17 | 0.413 | 5 | -12 |
| OvernightGap | -0.938 | 18 | -0.402 | 17 | -1 |
