# Algorithm claims ledger — are the formulas the published ones, and does the code compute them?

status: FROZEN 2026-10-16 (second EGV pass; independent of claims-ledger.md, which covered port fidelity)
target: `indicators/QI_*.cs` as of commit 819ffcf (+ harness logging from bar 0)
environment: `validation/env-pin.txt`; Python reference/tests run under the machine's `python` 3.9.13 (pandas/numpy per `validation/pytests/requirements.txt`)
tier: 2 (dual channel). Mode 1: Channel A = documentation subagents (no execution); Channel B = a
      subagent that writes reference implementations FROM THIS LEDGER'S FORMULA STATEMENTS ONLY
      (no documentation lookup), with pytest unit tests on synthetic data and a differential test
      against the NinjaTrader harness CSV (`validation/runs/qi_dump_*.csv`, written by QI_EgvDump).

Each module carries two claims:
- **(a) definition claim** — "formula F below is the published definition from source S" (Channel A
  decides; Channel B marks N/A-by-construction).
- **(b) computation claim** — "the compiled QI module computes F on the chart's bars" (Channel B
  decides by reference implementation + harness differential; Channel A marks N/A-by-construction).
Per the convergence gate a module is ACCEPTED only when (a) and (b) are both ACCEPTED. A module
whose (a) is UNVERIFIABLE (no authoritative definition exists) can at most reach "(b) accepted,
definition not backed", and the final report must say so.

Notation: bars indexed 0 = current, k = k bars ago. `SMA_n`, `EMA_n` (alpha = 2/(n+1)),
`Wilder_n` = running average with weight 1/n on the new value. All "NT" formulas are claimed to be
what NinjaTrader 8.1.8.3 ships in `bin\Custom\Indicators\@*.cs`.

## Built-in blocks the modules depend on (claims B1–B9)

| ID | Claim (a): published definition | Claim (b): NT built-in computes it (as used by QI) | Source S to check |
|----|------|------|------|
| B1 | RSI_n = 100 − 100/(1+RS), RS = Wilder_n(up moves)/Wilder_n(down moves) (Wilder 1978); NT `RSI(input, n, smooth)` applies an extra EMA_smooth to the result, smooth = 1 ⇒ none | harness `QI_RSI2`, `QI_RSI14` values equal reference Wilder RSI after a 300-bar warm-up, |diff| ≤ 1e-3 | NT help `rsi.htm`, `@RSI.cs`; Wilder, *New Concepts in Technical Trading Systems* (1978) |
| B2 | EMA_n[0] = EMA_n[1] + 2/(n+1)·(x[0] − EMA_n[1]) | `QI_EMACross` Ema20/Ema50 equal reference EMA after warm-up, |diff| ≤ 1e-3 | NT help `ema.htm`, `@EMA.cs` |
| B3 | SMA_n = mean of last n values | `QI_SMA200Trend` Sma200 equals reference SMA exactly (≤ 1e-6) from bar 199 | NT help `sma.htm`, `@SMA.cs` |
| B4 | ATR_n: TR = max(H−L, |H−C[1]|, |L−C[1]|); NT ATR = ((min(bar, n−1))·ATR[1] + TR)/min(bar+1, n) (Wilder-style running average with linear warm-up) | reference ATR from the stated recursion equals harness-derived ATR (via `QI_WideRangeBar` = (H−L)/ATR14 and `QI_VRPProxy` = ATR5/ATR14) after warm-up, |diff| ≤ 1e-3 | NT help `atr.htm`, `@ATR.cs`; Wilder 1978 |
| B5 | StdDev_n = population standard deviation (divide by n) of the last n values | `QI_CompositeVol` priceZ reproduces with population std | NT help `stddev.htm`, `@StdDev.cs` |
| B6 | MACD(fast, slow, signal): line = EMA_fast − EMA_slow, signal = EMA_signal(line), histogram (`Diff`) = line − signal | `QI_MACDHistogram` equals reference after warm-up, |diff| ≤ 1e-3 | NT help `macd.htm`, `@MACD.cs`; Appel |
| B7 | Bollinger(numStdDev, n): middle = SMA_n(close), upper/lower = middle ± numStdDev·StdDev_n(close) | `QI_BollingerPctB` Upper/Middle/Lower equal reference (≤ 1e-6) from bar n−1 | NT help `bollinger.htm`, `@Bollinger.cs`; Bollinger, *Bollinger on Bollinger Bands* (2001) |
| B8 | StochasticsFast(periodD, periodK): %K = 100·(C − LL_K)/(HH_K − LL_K), %D = SMA_periodD(%K) (NT names: `StochasticsFast(3, 14)` ⇒ periodD = 3, periodK = 14) | `QI_StochFade` K, D equal reference (≤ 1e-6) | NT help `stochastics_fast.htm`, `@StochasticsFast.cs`; Lane |
| B9 | ADX_n = Wilder_n(DX), DX = 100·|+DI − −DI|/(+DI + −DI), with +DM/−DM/TR per Wilder (NT `@ADX.cs` recursion) | `QI_ChopIndex` Adx equals reference after warm-up, |diff| ≤ 1e-2 | NT help `adx.htm`, `@ADX.cs`; Wilder 1978 |

## Modules (claims M1–M27)

| ID | Module | Formula F as implemented (this is what B implements; A compares it to S) | Claimed source S | Known deviation risk for A to rule on |
|----|--------|------|------|------|
| M1 | QI_IBS | IBS = (C − L)/(H − L) of the DAILY bar; 0.5 if H = L; on intraday charts read from the forming daily bar | Pagonidis, "Internal Bar Strength" (QuantifiedStrategies / original 2013 blog); Connors & Alvarez "IBS" | none expected |
| M2 | QI_RSI2 | RSI_2 of close (B1) | Connors & Alvarez, *Short Term Trading Strategies That Work* (2008): RSI(2) | none |
| M3 | QI_ConnorsRSI | CRSI = (RSI_2(close) + RSI_2(streak) + PercentRank_100(ROC_1))/3; streak = signed run of up/down closes (unchanged close keeps counts); PercentRank over the previous 100 one-bar changes, strictly-less count /100 ·100; value 50 until bar 100 | Connors Research, *ConnorsRSI* guide (2012): CRSI = (RSI(3) of close + RSI(2) of streak + PercentRank(100) of 1-day ROC)/3 | **price RSI period 2 vs published 3**; percent-rank tie handling |
| M4 | QI_StochFade | %K, %D of StochasticsFast(3, 14) (B8) | Lane; NT help | none |
| M5 | QI_RVZScore | z = (ATR14[0] − mean_20(ATR14))/popstd_20(ATR14); 0 until bar 25 | no formal publication (attributed to a practitioner "DthetaSpike"); z-score definition itself is standard | A: definition UNVERIFIABLE unless a primary source exists; z-score arithmetic verifiable |
| M6 | QI_CompositeVol | 0.40·z_RV + 0.35·(−priceZ) + 0.25·((vov − 0.15)/0.10); priceZ = (C − SMA20)/popstd20; vov = popstd_10(ΔATR14)/ATR14 | none ("v5_zscore framework", unpublished) | A: UNVERIFIABLE expected |
| M7 | QI_TurnOfMonth | flag = 1 if calendar day ≥ DaysInMonth−3 or ≤ 3 (US Central date) | Hensel & Ziemba, "Investment Results from Exploiting Turn-of-the-Month Effects" (1996); Lakonishok & Smidt (1988): last trading day through first 3 trading days | **calendar days vs trading days; window width** |
| M8 | QI_ConsecDays | signed count of consecutive higher/lower closes; unchanged close keeps counts | Connors & Alvarez (2008) "3 down days" setups | tie handling |
| M9 | QI_OvernightGap | gap% = (O[0] − C[1])/C[1]·100 | standard definition; cited "MDPI 2025" paper | none |
| M10 | QI_BollingerPctB | bands per B7; %B_here = (C − middle)/(half bandwidth)·100 | Bollinger: %b = (C − lower)/(upper − lower) | **scaling: %B_here = 200·%b − 100** (affine; same information) |
| M11 | QI_TurnaroundTuesday | day-of-week (US Central) 0..6; Monday shaded | French, "Stock returns and the weekend effect" (1980) | the module is a calendar flag, not French's test |
| M12 | QI_RSI14 | RSI_14 of close (B1) | Wilder 1978 | none |
| M13 | QI_VRPProxy | ATR5/ATR14; 1.0 before bar 20 | none ("DeltaInvariantVol" practitioner proxy; VRP proper = implied − realized variance) | A: UNVERIFIABLE expected (proxy, not VRP) |
| M14 | QI_WideRangeBar | (H − L)/ATR14; 1.0 if ATR ≤ 0 | Crabel, *Day Trading with Short Term Price Patterns* (1990) WR bars | Crabel's WR definition is range vs prior ranges, not ATR multiple |
| M15 | QI_HedgingPressure | composite of 4 clamped terms (basis deviation (C−SMA20)/ATR14·−25; slope diff (ΔSMA5−ΔSMA20)/ATR14·−50; vol/price divergence; range compression), each clamped ±25, sum clamped ±100 | cited Basu & Miffre (2013), which measures hedging pressure from CFTC COT positions | **the code is a price/volume proxy, not the paper's HP** → A: REFUTED-as-cited or UNVERIFIABLE |
| M16 | QI_VWAPDistance | VWAP = Σ(typical·vol)/Σvol with typical = (H+L+C)/3, reset on day-of-year change; dist = (C − VWAP)/ATR14 | VWAP standard definition (e.g., CFA/CME/NT help `vwap.htm`) | reset at calendar day vs session; typical price vs close |
| M17 | QI_MACDHistogram | MACD(12, 26, 9).Diff (B6) | Appel | none |
| M18 | QI_EMACross | EMA20, EMA50 (B2); Spread = EMA20 − EMA50 | standard | none |
| M19 | QI_SMA200Trend | SMA200 (B3); Distance = C − SMA200 from bar 200 | standard | none |
| M20 | QI_ATRRegime | ATR14/SMA50(ATR14); 1.0 before bar 50 | practitioner heuristic (cited "LuxAlgo") | A: UNVERIFIABLE expected |
| M21 | QI_VolumeSpike | Vol/SMA20(Vol); 1.0 if SMA ≤ 0 | standard relative-volume definition | none |
| M22 | QI_VolumeDelta | δ = +Vol if C > C[1], −Vol if C < C[1], else 0; Cum20 = Σ_{k=0..19} δ[k] (bar > 20); SMA10(δ) (bar ≥ 10) | practitioner proxy (true delta needs bid/ask) | A: UNVERIFIABLE as "volume delta"; arithmetic verifiable |
| M23 | QI_ChopIndex | CHOP_14 = 100·log10(ΣTR_14/(HH_14 − LL_14))/log10(14), clamped 0..100, 50 until bar 14; state: count of {CHOP > 61.8, ADX14 < 20, Vol < 0.7·SMA20(Vol)} | Dreiss, Choppiness Index (1993); NT help `choppinessindex.htm` | ATR(1) = TR; thresholds 61.8/38.2 are convention |
| M24 | QI_LiquiditySweep | 7 pattern rules (wick/body ratios, volume multiples, swing/level breaches) with fixed confidences | practitioner concepts (SFP, Wyckoff spring/upthrust, Turtle Soup — Connors & Raschke, *Street Smarts* 1995) | A: only Turtle Soup has a published rule set; rest UNVERIFIABLE |
| M25 | QI_OrderFlowPlus | 5 rules on δ (M22) and swing points with fixed confidences | practitioner | A: UNVERIFIABLE expected |
| M26 | QI_SMC | order block / FVG / BOS / CHoCH / displacement rules with fixed confidences | practitioner ("ICT") | A: UNVERIFIABLE expected |
| M27 | QI_KeyLevels | prev-day RTH high/low (08:30–16:00 CT), month high/low, 30-min opening range (08:30–09:00 CT), Asian session (17:00–02:00 CT) | CME Globex / RTH session times; Crabel ORB | session boundaries vs CME official hours |

## Pre-registered Channel B probes

- P1 unit tests (synthetic): for each built-in B1–B9 and each arithmetic module, hand-constructed
  series with closed-form expected values (e.g. IBS of a known bar = 0.25; RSI of monotone up series
  = 100; %K at the range high = 100; CHOP of a perfectly trending series < CHOP of an oscillating
  series; SMA/EMA/StdDev against numpy/pandas). Every test must FAIL on a mutated reference
  (falsifiability check recorded in the test file as a `test_falsifier_*`).
- P2 differential (harness): `validation/pytests/test_differential.py` loads the newest
  `validation/runs/qi_dump_*.csv`, recomputes every module from its O/H/L/C/V columns with the
  reference implementations, and asserts |ref − harness| ≤ tolerance from the warm-up bar stated
  per claim. Skipped (not passed) when no harness file exists.
- P3 falsifier for P2: run P2 with one reference constant perturbed (RSI period 14→13) and confirm
  the assertion fails; restore and checksum.
Pattern/event modules (M24–M26) and M27: B is limited to a replay of the rule set in Python on the
harness bars, comparing event bars and confidences; if the harness columns are insufficient, B
records UNVERIFIABLE rather than PASS.

Claim count: 9 built-in + 27 module = 36 (72 half-claims). Materiality: all material.
