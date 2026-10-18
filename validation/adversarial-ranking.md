# Adversarial validation of the P1 ranking

Date: 2026-10-17. Validator role: try to break the claim, not confirm it.

> Educational research only. Not financial advice.

## Claim under attack

"`results/ranking.csv` and `results/metrics_P1.csv` correctly state, per the frozen protocol
`backtest/PROTOCOL.md` and rules `backtest/rules.yaml`, how each of 25 indicator rules would have performed
on MES 2021-01-04 -> 2026-02-24, and the ranking (RSI14 first with annualised SR 0.845, RSI2 0.649,
ConsecDays 0.569, IBS 0.566 ... SMC last at -10.85) is not an artifact of a bug, look-ahead, data defect or
mis-specified rule."

## Verdict

| # | Attack | Result | Numbers that changed |
|---|---|---|---|
| 1 | Look-ahead (truncation, P&L timing, session builder) | SURVIVED | none |
| 2 | RSI14 anomaly (legs, independent RSI, direction, concentration) | SURVIVED | none |
| 3 | Data defects (adjustment, bad ticks, seams, 2023-04 gap, top days) | SURVIVED for the top 6; BROKEN for the full order | best-estimate repair: RSI14 0.845 -> 0.817, IBS 0.566 -> 0.514, ConsecDays 0.569 -> 0.606; ranks 7/8 and 13/14 swap |
| 4 | Costs and P&L arithmetic recomputed from scratch | SURVIVED | none (max abs diff 5.6e-17) |
| 5 | Rule fidelity against NinjaTrader's own values | BROKEN | on NT daily bars: ConsecDays 0.883 (#1), RSI14 0.656 (#2), RSI2 0.632 (#3), IBS 0.12-0.15 (#10); 13 of 25 ranks change |
| 6 | Robustness of the order (sensitivities, bootstrap) | BROKEN | P(first among top 4): RSI14 0.520, RSI2 0.145, ConsecDays 0.188, IBS 0.147; P(exact top-4 order) 0.122 |

Short form: the code does what the protocol says. The numbers reproduce exactly, there is no look-ahead, and
the arithmetic is right. But the order of ranks 2-4 is not a stable fact about these indicators:

- **Close definition.** The ranking changes when the daily close is NinjaTrader's own (settlement) close
  rather than the 16:00 CT last trade. For IBS, the original indicator reads that settlement-based daily bar.
- **Sampling noise.** The order changes inside the noise band.
- **Sub-periods and costs.** The order changes under the pre-registered H1, H2 and 0x-cost runs.

RSI14 is the most robust rank 1, but it comes first in only 52% of bootstrap resamples among the top 4.

Scripts and full outputs are in the session scratchpad
`C:\Users\rajib\AppData\Local\Temp\claude\C--Users-rajib-OneDrive-Documents\533a663d-5efe-42d6-aafd-bb6df2ee5fa2\scratchpad\adversary\`
(`a*.py` and `out\a*.txt`). Each script ran as `python -I <script>` (Python 3.9.13, pandas 2.3.3,
numpy 2.0.2). Nothing under `backtest/qibt`, `validation/pytests` or `results/` was modified.

## 0. Reproduction (precondition)

`a0_reproduce.py` re-runs `qibt.cli.run_pipeline` on the cached P1. It then builds a second D frame from the
raw 1-minute pickle with independent code.

```
max |metrics(rerun) - metrics_P1.csv| over numeric cells: 1.4210854715202004e-14
daily rows 1320 1320 max |diff| 0.0
ranking order identical: True
D rows qibt/own: 1578 1578 same dates: True   (Open/High/Low/Close/Volume/Bars max|diff| 0)
bars closing in (16:00,17:00]: 0
first-bar close times of sessions: {'17:01': 1567, '16:00': 6, '18:52': 1, '18:08': 1, '17:04': 1, '18:09': 1, '21:52': 1}
```

## 1. Look-ahead: SURVIVED

**Truncation test** (`a1_lookahead.py`):

- **D-frame rules.** We tested the top 4 rules on 226 D-frame dates: 210 random window dates plus 16 special
  dates. The special dates are every file seam, every 1-bar stub session, the 2023-04-05 gap, Good Friday
  2021, 2025-01-09, 2026-02-16, 2022-11-07, 2025-11-28 and 2026-02-23. Each date was cut two ways:
  - The 1-minute data was truncated at the close time of D bar t.
  - The 1-minute data was also kept to 30 minutes into session t+1 (17:01-17:30). This tests whether
    next-session bars can leak into bar t.
- **Frames and values.** At each cut, the frames were rebuilt with `qibt.data` and the values recomputed
  with `qibt.signals`.
- **15m rules.** The two random other rules (seed 20261017) are **VolumeSpike** and **VolumeDelta**, both
  15m. They were tested on 236 15m bars, each cut at the bar's close time. The bars include the first and
  last bar of the special sessions.

```
D-frame rules: 226 dates x 2 cuts x 4 rules = 1808 value/position checks, mismatches: 0
15m rules: 236 bars x 2 rules = 472 checks, mismatches: 0
```

The D bar for date t (O/H/L/C/V/Bars) was identical under both cuts at every sampled date. So bars from the
next session never join date t. This holds at the 17:00 roll, at the halt, at the partial last session of
each file and at the 1-bar seam sessions.

**P&L timing** (`a1_timing.py`) fits the published daily P&L against candidate execution paths:

```
RSI14  protocol O[t+1]->O[t+2]                   SR   0.845  max|diff vs published|    0.00
       LEAK  O[t]->O[t+1] (p_t on its own bar)   SR  -4.945                         3067.50
       LEAK  O[t]->C[t] (same-day intraday)      SR  -4.998                         3042.50
       C[t]->C[t+1] (close-to-close)             SR   0.828                          483.75
(RSI2 / ConsecDays / IBS: protocol timing max|diff| 0.00 in every case; leak timings SR -5.7 to -10.2)
```

The published P&L is exactly p_t x (Open_{t+1} -> Open_{t+2}) x 5. Leaky timings give strongly negative
SRs, because these are contrarian rules. So any leak would have lowered the ranks, not raised them.

**Session builder** (`a0`, `a3_sessions.py`): no bar closes in (16:00, 17:00]. 1567 of 1578 sessions start
with the 17:01 bar. The six 1-bar 16:00 stubs keep their own calendar date. The trading-date rule is
`tod > 17:00 -> next day`.

## 2. RSI14 anomaly: SURVIVED

`a2_decomp.py`, `a2_episodes.py`.

**Independent RSI.** A textbook Wilder RSI (simple-mean seed of the first n moves, then
(prev*(n-1)+x)/n) on the same D closes gives these differences against `qi_ref.rsi`:

- RSI14: max abs difference 1.7e-8.
- RSI2: max abs difference 2.8e-14.

Positions are identical on 1320 of 1320 window days for both. The seed difference decays during the 2020
warm-up.

**Direction.** RSI14 is long on 162 decision days, all with x < 40. It is short on 482, all with x > 60.
There are 0 violations. RSI2 (313 long with x < 25, 497 short with x > 75), ConsecDays (121 / 205) and
IBS (234 / 425) also have 0 violations. These thresholds equal ORIG `IBSFade.cs` lines 1268-1370
(B/N/S classes).

**Legs by year** (gross USD by held position; net after costs):

| RSI14 | days long | days short | gross long | gross short | costs | net |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 7 | 129 | 1,390.00 | 332.50 | 114.75 | 1,607.75 |
| 2022 | 71 | 36 | 3,798.75 | 1,031.25 | 121.50 | 4,708.50 |
| 2023 | 33 | 92 | 140.00 | -1,261.25 | 96.75 | -1,218.00 |
| 2024 | 15 | 137 | 1,617.50 | 611.25 | 119.25 | 2,109.50 |
| 2025 | 34 | 88 | 1,847.50 | 1,690.00 | 121.50 | 3,416.00 |
| 2026 | 2 | 1 | 1,260.00 | 68.75 | 13.50 | 1,315.25 |
| all | 162 | 483 | 10,053.75 | 2,472.50 | 587.25 | 11,939.00 |

Other top-4 rules, net by leg:

| Rule | Long leg | Short leg | Costs | Net |
|---|---:|---:|---:|---:|
| RSI2 | +13,847.50 | -1,670.00 | 1,543.50 | 10,634 |
| ConsecDays | +7,913.75 | -2,241.25 | 760.50 | 4,912 |
| IBS | +8,556.25 | +2,585.00 | 2,216.25 | 8,925 |

Year-by-year tables are in `out\a2.txt`.

**Why RSI14 earns money while short 37% of days.** Mean next holding-bar P&L by RSI14 bucket:

| RSI14 bucket | Mean USD/day |
|---|---:|
| 0-30 | +78.3 |
| 30-40 | +59.1 |
| 40-50 | -6.9 |
| 50-60 | +15.3 |
| 60-70 | -3.4 |
| above 70 | -11.2 |

The rule earns from buying oversold days and from a small mean reversion of overbought days. It gives up
the 50-60 drift.

**Concentration.**

- The 10 best days carry USD 8,900 of 11,939. Buy-and-hold has the same fat-tail profile: its 10 best days
  carry USD 9,550 of 12,188.
- Without its 10 best days, RSI14 has SR 0.254.
- No single episode explains the result. SR without April 2025 is 0.988. SR without the 2022 bear market
  (2022-01-03 to 2022-10-12) is 0.824.
- The best days are real market events (see attack 3).

## 3. Data: SURVIVED for the top 6, BROKEN for the full order

**Adjustment and integrity** (`a3_data.py`, `a3_seam_offset.py`):

- 0 of 8,569,564 one-minute OHLC values are off the 0.25 tick grid. So the adjustment is additive; a ratio
  adjustment would leave the grid. There are 0 OHLC inconsistencies, 0 zero-volume bars, 0 zero-range D
  bars and 0 duplicated sessions (offset-removed path hash and volume hash).
- The reopen gap |Open_{t+1} - Close_t| has a median of 0.75 points. There is no jump at any roll date. The
  largest gaps are real weekend news (2025-04-04, 2025-10-10, 2025-06-20, 2025-05-09) or seams.
- The adjustment offset is consistent across the six export files. The offset is (MES_adj at 15:00 CT) minus
  (S&P 500 cash close, from public record). Across the 5 seams it moves +2.1, +0.9, -3.1, +7.1 and -4.7
  points. That is the size of basis noise: inside one file it moved 11.8 points from 2024-02-28 to
  2024-02-29. A file-specific roll offset (tens of points) would show as a step.
- 181 one-minute bars were flagged with a range above 25 x the rolling median or a close jump above 40
  points. They sit at 07:30/07:31 CT (data releases), 13:01 (FOMC), the April 2025 tariff days and the March
  2020 crash (warm-up). There are no isolated bad prints in the evaluation window.

**Top 10 absolute daily P&L days** (`a3_topdays.py`; columns: decision date, entry open, exit open, points):

- **RSI14:** 2025-04-09 +2,477.50 (long, 5176.25 -> 5671.75, +495.5 pts, the tariff-pause day);
  2025-04-04 -2,072.50 (-414.5); 2025-04-22 +957.75; 2026-02-06 +864.00; 2025-10-10 +741.25 (short);
  2024-08-08 +712.50; 2025-04-03 -666.25; 2022-06-24 +652.50; 2022-01-31 +645.00 (seam day); 2025-03-10
  -645.00.
- **RSI2:** 2025-04-09, 2025-04-04, 2022-11-10 (CPI, +216.25), 2025-04-10, 2025-04-22, 2022-09-13 (CPI,
  -180.75), 2022-05-18, 2026-02-06, 2022-06-10, 2024-11-06.
- **ConsecDays:** 2022-09-13, 2026-02-06, 2022-05-05, 2022-11-30, 2022-01-31 (seam, -647.25), 2024-09-03,
  2022-03-09, 2021-11-26, 2025-04-07, 2022-06-13.
- **IBS:** 2025-04-09, 2025-04-04, 2022-11-10, 2025-04-10, 2022-09-13, 2022-05-18, 2026-02-06, 2022-08-26,
  2022-06-10, 2024-11-06.

Each of these sessions has a full set of 1-minute bars (1,155-1,380). Their largest 1-minute moves sit at
known release times. Above the 5 x median line (median non-flat |P&L|: RSI14 $79.50, RSI2 $62.38,
ConsecDays $41.00, IBS $46.50) there are 47 / 118 / 81 / 176 days. This is the fat tail of real index moves
(kurtosis 22-56), not bad data. The one defect-driven day in any top 10 is 2022-01-31. Its single holding
bar spans two sessions (see below).

**Defects found** (`a3_sessions.py`):

- **The five file seams each lose 1-2 sessions.** Each new export starts logging only at the 16:00 bar of
  the second daily bar after chart start. The missing spans are:

  | Last bar kept | First bar after the gap | 1-bar stub session |
  |---|---|---|
  | 2021-02-01 11:59 | 2021-02-02 16:00 | 2021-02-02 |
  | 2022-01-31 15:59 | 2022-02-01 16:00 | 2022-02-01 |
  | 2023-01-31 15:59 | 2023-02-02 16:00 | 2023-02-02 (2023-02-01 fully missing) |
  | 2024-02-29 15:59 | 2024-03-04 16:00 | 2024-03-04 (2024-03-01 fully missing) |
  | 2025-03-31 15:59 | 2025-04-02 16:00 | 2025-04-02 (2025-04-01 fully missing) |

- **A 7-weekday gap in 2023.** Data stops at 2023-04-05 13:03 and resumes at 2023-04-16 17:01.
- **Other partial sessions.** Late starts on 2021-10-04, 2023-11-13, 2024-06-24, 2025-02-10 and 2026-02-16
  (21:52). Intra-session holes on 2022-11-07 (634 min) and 2025-11-28 (646 min).

Under the protocol (sessions with no bars are absent), each seam has three effects:

- Holding bar X books the stale position p_{X-1} over X plus the missing session(s).
- The stub Y books a 1-hour P&L.
- IBS on Y is computed from one 1-minute bar. On 2022-02-01 and 2023-02-02 it is 0.000, so a long
  signal; NinjaTrader's IBS for those days is 0.756 and 0.763.

**Impact** (`a3_seam_repair.py`, `a3_seam_sens2.py`):

| Treatment | RSI14 | RSI2 | ConsecDays | IBS | Rank changes vs published |
|---|---:|---:|---:|---:|---|
| Published | 0.845 | 0.649 | 0.569 | 0.566 | - |
| Best-estimate repair (split X at its last close; p_X held through the gap; NT IBS on the 5 stubs) | 0.817 | 0.653 | 0.606 | 0.514 | VRPProxy/SMA200Trend 7<->8, HedgingPressure/ConnorsRSI 13<->14 |
| Neutral: P&L of the 11 defect booking days set to 0 | 0.858 | 0.658 | **0.662** | 0.539 | RSI2/ConsecDays 2<->3 and 8 more (10 of 25) |

The order of the top 6 survives the best-estimate repair. The full 25-rule order does not. The published
SR values carry a data-defect error of up to about 0.05 for individual top-4 rules.

## 4. Costs and P&L arithmetic: SURVIVED

`own.py` + `a4_recompute.py` use our own code for every step:

- our own D-frame builder from the raw pickle;
- textbook indicators;
- our own position mapping;
- a naive loop P&L engine with |dp| x USD 2.25 costs;
- our own Sharpe (ddof 1, sqrt 252).

This code does not use `qibt.engine`, `qibt.metrics` or `qi_ref`. Results against `metrics_P1.csv`:

```
module      gross     costs   total      sr      sr_h1    sr_h2   (positions differ from qibt: 0)
RSI14     12526.25   587.25  11939.00  0.844658  1.181036  0.627640
RSI2      12177.50  1543.50  10634.00  0.649433  1.033086  0.347519
ConsecDays 5672.50   760.50   4912.00  0.568885  1.108974 -0.036390
IBS       11141.25  2216.25   8925.00  0.565508  0.264602  0.819673
BuyHold   12190.00     2.25  12187.75  0.584054  0.400064  0.748005
max |own - metrics_P1.csv| across gross/costs/total/sr/sr_h1/sr_h2: 5.55e-17 ; daily series max |diff| 0.0
```

The cost-sensitivity files match too: `metrics_P1_cost0x.csv` and `metrics_P1_cost2x.csv` SR equal the
`sr_cost0` and `sr_cost2` columns exactly.

## 5. Rule fidelity: BROKEN

**Formulas.** The formulas match ORIG on the bars ORIG used (`a5_formula.py`). The source CSVs carry
ORIG's per-bar databox values computed on the 1-minute chart. We ran `qi_ref` on the same 1-minute closes
and skipped the first 3,000 bars of each file for warm-up:

```
RSI14      2124391/2124391 within 6e-05 (databox is rounded to 4 decimals), max|d| 0.000050
RSI2       2124391/2124391 within 6e-05, max|d| 0.000050
ConsecDays 2124391/2124391 within 1e-09, max|d| 0.000000
```

**IBS: the D-frame value is not ORIG's value** (`a5_ibs.py`, `a5_ibs2.py`, `a5_ibs3.py`).

- ORIG reads IBS from NinjaTrader's daily series (`AddDataSeries(Day,1)`; `Closes[1][0]`, `Highs[1][0]`,
  `Lows[1][0]`).
- `databox_IBS` changes at the 16:00 bar on 1,505 sessions. So the value at a date's last bar is
  NinjaTrader's daily bar for that date.
- Over 1,320 window dates the D-frame IBS equals it on only **5.8%** of dates (within 5e-5). The B/N/S
  class agrees on **83.4%** of dates. IBS positions differ on **16.6%** of window days.
- The cause is the close (`a5_settle.py`, `a5_grid_alt.py`). Assume NT's daily H/L is the full
  17:00-16:00 one-minute H/L. Then NT's close = L + IBS x (H - L) lies on the 0.25 tick grid on
  **98.9%** of dates; chance is 2.8%. With RTH H/L it is 22%.
- That close is a median 0.75 points from the 15:00 CT one-minute close and 3.0 points from the 16:00 last
  trade. It is the settlement price. The protocol's D frame uses the 16:00 last trade.

**What the rules give on NinjaTrader's own daily bars** (`a5_ntdaily.py`, `a5_ntdaily_all.py`). Setup:

- Close = the inferred NT close; the 15:00 close is used on the 20 dates that are off the grid.
- IBS = `databox_IBS` directly in `a5_ntdaily.py`.
- Execution is the protocol's own, at the 17:00 reopen.

| Rule | Published SR (rank) | SR on NT daily bars (rank) | Positions differ | SR with a 15:00 one-minute close (rank) |
|---|---:|---:|---:|---:|
| ConsecDays | 0.569 (3) | **0.883 (1)** | 9.3% | 0.644 (3) |
| RSI14 | 0.845 (1) | **0.656 (2)** | 4.2% | 0.678 (1) |
| RSI2 | 0.649 (2) | **0.632 (3)** | 7.9% | 0.649 (2) |
| WideRangeBar | 0.429 (5) | 0.409 (4) | 0.4% | 0.409 (4) |
| IBS | 0.566 (4) | **0.122 (10)**; 0.148 with databox IBS directly | 16.1-16.6% | 0.333 (6) |

On NinjaTrader's own daily bars, 13 of 25 ranks change. IBS drops from rank 4 to rank 10. The top-4 order
is therefore set by the protocol's choice of the 16:00 last trade as the daily close.

For IBS this choice contradicts PROTOCOL section 1, which measures "the original IBSFade indicator's own
... classification of that indicator's value". The original reads the settlement-based daily bar. The
published numbers are correct per the protocol's D-frame definition (section 3). They are not the original
indicator's values. Rank 1 (RSI14) is also not stable under the close definition.

## 6. Robustness of the order: BROKEN

**Pre-registered sensitivities already in `results/`** (`a6_robust.py`):

```
sr        top-4: RSI14, RSI2, ConsecDays, IBS
sr_cost0  top-4: RSI14, RSI2, IBS, ConsecDays           (3<->4 swap)
sr_cost2  top-4: RSI14, RSI2, ConsecDays, IBS
sr_h1     top-4: RSI14, ConsecDays, RSI2, VRPProxy       (IBS rank 8, SR 0.265)
sr_h2     top-4: IBS, RSI14, CompositeVol, WideRangeBar  (RSI2 rank 8, ConsecDays rank 12, SR -0.036)
```

**Protocol tie.** ConsecDays - IBS = 0.0034, which is below the protocol tie band of 0.005. So ranks 3 and
4 are a tie under PROTOCOL section 8. The tie-break is useless here:

- DSR = 0.000 for all 25 rules. SR0 is 0.469 per day (about 7.4 annualised), because V[SR] is dominated by
  the cost-crushed 15m rules.
- So the tie was resolved by module name A->Z.
- Buy-and-hold (SR 0.584) beats both rank 3 and rank 4.

**Stationary block bootstrap.** Politis-Romano, mean block 10 days, 1,000 resamples, seed 12345. All 25
daily P&L series were resampled on the same day indices, which keeps their cross-correlation:

```
P(ranked 1st of the top 4): RSI14 0.520, RSI2 0.145, ConsecDays 0.188, IBS 0.147
P(ranked 1st of all 25):    RSI14 0.392, ConsecDays 0.141, IBS 0.102, RSI2 0.098, ATRRegime 0.091, SMA200Trend 0.056, ...
P(exact order RSI14 > RSI2 > ConsecDays > IBS): 0.122
P(SR RSI14 > RSI2) 0.710   P(RSI2 > ConsecDays) 0.604   P(ConsecDays > IBS) 0.504   P(RSI14 > IBS) 0.739
SR 90% CI: RSI14 [0.27, 1.56]  RSI2 [0.07, 1.26]  ConsecDays [-0.10, 1.28]  IBS [-0.03, 1.18]
```

The gaps between ranks 1-4 are smaller than the sampling noise. The order 2 > 3 > 4 is close to a coin
flip. RSI14's lead is the only one with odds better than 2 to 1, and even it comes first only 52% of the
time among the four.

## What a corrected statement looks like

The published files correctly report the pre-registered rules on P1 as the protocol defines P1. The
arithmetic, timing and causality are verified independently. However:

1. **IBS is not ORIG's value.** The D-frame IBS (and the daily close behind all D rules) is not
   NinjaTrader's daily bar: NT closes at settlement. On NT's own daily bars:
   - ConsecDays 0.883 is first, then RSI14 0.656 and RSI2 0.632.
   - IBS (0.12-0.15) falls to rank 10.
2. **Five export seams and one 7-weekday gap lose data.** The best-estimate repair keeps the top 6 but moves
   individual SRs by up to about 0.05 and swaps ranks 7/8 and 13/14.
3. **The top 4 are statistically indistinguishable.** P(first) is RSI14 0.52, RSI2 0.15, ConsecDays 0.19
   and IBS 0.15. Ranks 3/4 are a protocol tie resolved alphabetically. The order changes under H1, H2 and
   0x costs.

The ranking is safe to use only as a label order, which is what PROTOCOL section 8 permits. It is not
evidence that one indicator beats another.
