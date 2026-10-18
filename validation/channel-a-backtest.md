# Channel A (documentation audit): backtest claims ledger

Ledger: `validation/backtest-claims-ledger.md` (frozen 2026-10-17). Claims audited: BT1, BT2, BT3, BT4, BT5, BT6, BT9, BT10, BT11, BT13, BT16. There is also a completeness note on PROTOCOL §3.
Auditor: Channel A subagent. Retrieved on 2026-10-17. No code was executed. No file under `backtest/qibt` or `backtest/tests` was read. No `channel-b*.md` file was read.
Installed platform pin (from `validation/env-pin.txt`): NinjaTrader 8.1.8.3. The NT8 online help guide has no version selector, so it was read as the current 8.1.x guide.

How the sources were retrieved:
- NinjaTrader help pages: static HTML at `static.ninjatrader.com/support/helpGuides/nt8/`, read as text.
- CME pages: CME blocks scripted clients, so the pages were read in the built-in browser pane. The CME fee-schedule PDF was parsed in that browser by reading its text layer with coordinates. Values were then assigned to columns by x-position.
- Bailey and López de Prado papers: the authors' copies at davidhbailey.com. The equations were checked visually by rendering the pages with pdf.js.

## Verdict summary

| ID | Verdict | One-line basis |
|----|---------|----------------|
| BT1 | CONFIRMED | CME spec: "$5 x S&P 500 Index" |
| BT2 | CONFIRMED | CME spec: "Outright: 0.25 index points = $1.25" |
| BT3 | CONFIRMED (with caveat) | Published all-in per side: Free 0.94, Monthly 0.84, Lifetime 0.64 USD. Optional Rithmic or CQG routing adds 0.25 USD |
| BT4 | CONFIRMED (current hours; see historical caveat) | CME spec: Sun–Fri 5:00 p.m.–4:00 p.m. CT, maintenance 4:00–5:00 p.m. CT |
| BT5 | CONFIRMED (derived from 3 NT8 pages) | Backtest runs only at bar close. A market order fills at the bar Open in the backfill algorithm. Slippage is bounded by the next bar |
| BT6 | CONFIRMED | The Offset is a price difference (new close minus old close), so the adjustment is additive |
| BT9 | CONFIRMED (ddof not specified by source) | Lo: √12 annualisation is "correct only under very special circumstances". The multiplier depends on serial correlation |
| BT10 | CONFIRMED | Eq. (11) matches. ŜR is non-annualized. γ4 = E[(r−μ)^4]/σ^4 (non-excess) |
| BT11 | CONFIRMED | Eq. (2) and SR0 match. The numeric example is copied below |
| BT13 | CONFIRMED (25/25 rules) | Every threshold, operator and class equals ORIG |
| BT16 | CONFIRMED (state semantics only; see caveats) | Historical = historical or backtest processing. Realtime = real-time processing, where strategy orders go live |

Totals: 11 CONFIRMED, 0 REFUTED, 0 UNVERIFIABLE. Material caveats are in BT3, BT4, BT5, BT16 and in the §3 note.

---

## BT1: MES contract unit

```
claim_id:    BT1
verdict:     CONFIRMED
source:      https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.contractSpecs.html
source_tier: 1 (exchange contract specification)
version:     live page as retrieved 2026-10-17 (no version stamp; rulebook chapter "CME 353")
quote:       "CONTRACT UNIT $5 x S&P 500 Index"
retrieved:   2026-10-17
note:        The same page's intro says "The Micro E-mini S&P 500 futures contract is $5 x the S&P 500 Index".
```

## BT2: MES minimum price fluctuation

```
claim_id:    BT2
verdict:     CONFIRMED
source:      https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.contractSpecs.html
source_tier: 1
version:     live page, 2026-10-17
quote:       "MINIMUM PRICE FLUCTUATION Outright: 0.25 index points = $1.25"
retrieved:   2026-10-17
note:        The calendar-spread tick is different ("0.05 index points = $0.25"). It does not apply to outright fills.
```

## BT3: USD 1.00 per side covers commission plus exchange and NFA fees

```
claim_id:    BT3
verdict:     CONFIRMED (for the standard NinjaTrader routing; see caveat)
source:      (a) https://ninjatrader.com/pricing/commissions/   (b) https://ninjatrader.com/pricing/
             (c) https://www.cmegroup.com/company/files/cme-fee-schedule-2026-10-19.pdf (CME Equity page, p.3)
             (d) https://www.nfa.futures.org/faqs/members/nfa-assessment-fees.html
             (e) https://www.nfa.futures.org/rulebooksql/rules.aspx?Section=3&RuleID=BYLAW+1301
             (f) https://ninjatrader.com/pricing/account-fees/
source_tier: 1 (broker's published schedule, exchange fee schedule, regulator FAQ and bylaw)
version:     (a) "as of August 14, 2026"; (c) "CME Equity Product Fee Schedules as of October 19, 2026";
             (d) "As of July 1, 2026"; (e) current bylaw text (period July 1, 2026 - June 30, 2027)
quote:       (a) MES row: "MES  Micro E-mini S&P 500  CME  Micro Indices  $0.36  $0.19  $0.09  $0.29  $0.39  $0.64  $0.84  $0.94"
                 [columns: EXCH + NFA | CLEARING | COMMISSION (LIFETIME) | (MONTHLY) | (FREE) | ALL-IN LIFETIME | MONTHLY | FREE]
             (b) "$0.39 / Micro & e-Nano ... Commissions per side" (Free); "$0.29" (Monthly); "$0.09" (Lifetime)
             (c) "Fees are charged per side (both buy and sell side) per contract." Non-Members, Globex,
                 column "Micro E-mini Index Futures": $0.35
             (d) "the NFA assessment fee, payable by FCMs with respect to futures contracts, is $.01 per side"
retrieved:   2026-10-17
```

All-in per side, from the published figures:

| Plan | Commission | NT clearing | CME exchange (non-member, Globex) | NFA | Sum | NT's own "ALL-IN" column | vs 1.00 |
|------|-----------|-------------|-------------------------------|-----|-----|-------------------------|---------|
| Free | 0.39 | 0.19 | 0.35 | 0.01 | **0.94** | $0.94 | covered (margin 0.06) |
| Monthly ($99/mo) | 0.29 | 0.19 | 0.35 | 0.01 | **0.84** | $0.84 | covered |
| Lifetime ($1,499 once) | 0.09 | 0.19 | 0.35 | 0.01 | **0.64** | $0.64 | covered |

Check: NinjaTrader's "EXCH + NFA $0.36" equals CME 0.35 plus NFA 0.01 from the two independent primary sources.

Caveats the orchestrator should carry forward. None of them meets the ledger falsifier for the default setup.
1. **Order-routing and technology fees (source f).** These are not in the all-in column: "Order Routing / Rithmic: $0.25 per contract"; "CQG Desktop / $0.25 per futures contract"; "3rd Party Technology Integrations / Additional transaction fees vary from $.05 to $.25 per contract"; "Static: $0.10 per contract Trading Technologies licensing fee". **With Rithmic or CQG routing, the Free plan is 1.19 per side and the Monthly plan is 1.09 per side. Both are above 1.00.** The Lifetime plan is 0.89.
2. **NFA fee step-up (sources d and e).** "Effective July 1, 2027 ... will be $.02 per side". After that date the Free plan becomes 0.95.
3. **Time variation.** All rates are current snapshots. The backtest window is 2021–2026, and the fees charged during that window were not verified. The bylaw page shows only the current rates.
4. **Fixed costs are not per side.** These are the plan fees, market data ($12/month L1 bundle), and the Free-plan "$35" minimum-activity fee for 30 days with no live trade. They are outside the per-side claim.

## BT4: CME Globex equity index trading hours

```
claim_id:    BT4
verdict:     CONFIRMED (current specification)
source:      https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.contractSpecs.html
             https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html
source_tier: 1
version:     live pages, 2026-10-17
quote:       "CME Globex: Sunday 6:00 p.m. - Friday - 5:00 p.m. ET (5:00 p.m. - 4:00 p.m. CT) with a daily
             maintenance period from 5:00 p.m. - 6:00 p.m. ET (4:00 p.m. - 5:00 p.m. CT)"
retrieved:   2026-10-17
note:        The MES and ES pages have identical Globex hours.
```

Historical caveat for P1 (2020-01-03 → 2026-02-24). This does not refute the claim, but it bears on the BT4, BT14 and BT17 probes.
- Source: CME SER-8788R, 24 June 2021, https://www.cmegroup.com/notices/market-regulation/2021/06/SER-8788R.pdf (tier 1). Quote: "effective June 28, 2021, CME and CBOT will eliminate the 3:15 p.m. – 3:30 p.m. Central Time (CT) trading halt on CME Globex which currently exists for certain Equity futures and options contracts."
- Source: CME Globex Notice 20210614, https://www.cmegroup.com/notices/electronic-trading/2021/06/20210614.html. Quote: "Effective Sunday, June 27 (trade date Monday, June 28) ... With this change, the affected Equity Futures and Options products will trade from Sunday-Friday, 5pm-4pm CT, daily, with a 4pm-5pm CT maintenance period."
- Consequence: before trade date 2021-06-28, P1 may contain no 1-minute bars stamped 15:16–15:30 CT. The probe's (16:00, 17:00] window is not affected. The 15m frame would have no 15:30 bar in that period. The notice lists the affected products only as "certain Equity futures", so whether MES was covered was not checked product by product.
- Holiday sessions follow separate schedules. One example is Thanksgiving 2026 for Equities: "12:00 PREOPEN / 17:00 OPEN" on Thursday and "12:15 CLOSED" on Friday (https://www.cmegroup.com/trading-hours.html). See the §3 note below.

## BT5: NT8 market order on bar close fills at the next bar's open (historical, Standard resolution)

```
claim_id:    BT5
verdict:     CONFIRMED (composed from three NT8 help pages; no single sentence states it verbatim)
source:      (a) https://static.ninjatrader.com/support/helpGuides/nt8/calculate.htm
             (b) https://static.ninjatrader.com/support/helpGuides/nt8/discrepancies_real-time_vs_bac.htm
             (c) https://static.ninjatrader.com/support/helpGuides/nt8/historical_order_backfill_logic.htm
             (d) https://static.ninjatrader.com/support/helpGuides/nt8/understanding_historical_fill_.htm
source_tier: 1 (vendor documentation)
version:     NT8 online help guide (unversioned, current 8.1.x); installed 8.1.8.3
quote:       (a) "State.Historical data processes OnBarUpdate() only on the close of each historical bar"
             (b) "During backtest, strategies can ONLY be processed at the close of each bar."
             (c) "if it's a Market Buy order, set the fill price to the lesser of the "next high price" or the bar Open"
                 [first pass: "next high price" = bar High if the bar moved up first, else bar Open, so the result is the Open]
             (c) "If it's a Market Sell order, set the fill price to the greater of the "next high price" or the bar Open"
             (d) "you cannot have more slippage then the high/low price of the next bar."
             (d) "Order fill resolution of " Standard (Fastest) " is the default setting"
retrieved:   2026-10-17
```

How the quotes combine. The order is submitted in OnBarUpdate at the close of bar t (a, b). The backfill algorithm then processes it against "the current bar being formed at the time" (c, Step 1.2), which is bar t+1. For a market order, the first pass gives a fill price equal to that bar's Open (c). Slippage in ticks is then added, capped at the next bar's high or low (d). Source (b) also says fills "are determined based on 4 data points, OHLC of a bar".
Residual: the help guide never writes "next bar's open" as one sentence. Page (c) also does not say that a market order filled in pass 1 skips passes 2–3. The Strategy Analyzer trade-list comparison (Channel B) is the decisive test. The NT "Slippage" property defaults to 0 ("Default value is set to 0", slippage.htm). PROTOCOL instead charges slippage as a cost of 1 tick = 1.25 USD.

## BT6: "Merge Back Adjusted" is additive

```
claim_id:    BT6
verdict:     CONFIRMED
source:      (a) https://static.ninjatrader.com/support/helpGuides/nt8/merge_policy.htm
             (b) https://static.ninjatrader.com/support/helpGuides/nt8/editing_instruments.htm
             (c) https://static.ninjatrader.com/support/helpGuides/nt8/mergepolicy.htm
source_tier: 1
version:     NT8 online help guide (current 8.1.x)
quote:       (a) "Offset values will be used to back adjust the historical price data to match the next front month"
             (b) "One day prior to the rollover date, calculate the difference between the close price of the new
                 expiry and the close price of the old expiry. This is the Offset value."
             (c) "MergeBackAdjusted / Merge policy is applied between contracts along with rollover offsets"
retrieved:   2026-10-17
```

Note: the offset is defined as a price **difference**, not a ratio. Shifting prior prices by a difference keeps point differences and does not keep ratios. No NT8 page describes ratio adjustment. Wording caveat: no sentence literally says "added to prior prices". The additive reading follows from the definition of the offset. Page (b) also says: "If minute data is not offered by the data provider, default Offset value will be 0", and offsets may be server-downloaded or user-overridden. Whether P1 was in fact exported with this policy is a data question for Channel B.

## BT9: Annualised Sharpe and √q scaling (Lo 2002)

```
claim_id:    BT9
verdict:     CONFIRMED (√q/iid part); ddof sub-point not decided by the source (immaterial asymptotically)
source:      https://www.tandfonline.com/doi/abs/10.2469/faj.v58.n4.2453  (publisher page: abstract + author's
             summary) and https://rpc.cfainstitute.org/research/financial-analysts-journal/2002/the-statistics-of-sharpe-ratios
source_tier: 4 (original paper, publisher page)
version:     Financial Analysts Journal 58(4), pp. 36-52, July 2002 (T&F online 02 Jan 2019); DOI 10.2469/faj.v58.n4.2453
quote:       "monthly Sharpe ratios cannot be annualized by multiplying by √12 except under very special circumstances"
             "the correct multiplier—which depends on the serial correlation of the portfolio's returns"
             "the usual Sharpe ratio estimator—sample mean excess return over sample standard deviation"
retrieved:   2026-10-17
```

Notes:
- The publisher text lists the assumption sets as "independently and identically distributed returns, stationary returns, and with time aggregation". It says √q scaling holds only in a special case and that the correct multiplier depends on serial correlation. So the claim that "√252 assumes iid daily returns" is consistent with Lo. Strictly, the binding condition named in the summary is the absence of serial correlation, which iid implies.
- The full article body was not available from an admissible copy: CFA member or T&F paywall, and no copy on the author's MIT site was found. The only full-text copy found is a third-party mirror at traders.studentorg.berkeley.edu (secondary, not evidence, and not used). Lo's explicit general multiplier η(q) and his variance formulas are therefore **not quoted here**.
- ddof: the source says "sample standard deviation" without fixing the divisor. ddof=1 vs 0 is not decided by the source.
- Suggestion (not a verdict): because the claim names the iid assumption, the results could also report the lag-1 autocorrelation of daily P&L.

## BT10: PSR formula (Bailey and López de Prado 2012)

```
claim_id:    BT10
verdict:     CONFIRMED
source:      https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf  (authors' copy; pp. 7, 9, 10, 36)
source_tier: 4 (original paper)
version:     "First version: May 2008 / This version: July 2012 / Forthcoming, Journal of Risk"
             (published J. of Risk 15(2), Winter 2012, per the citation in the 2014 DSR paper; published typeset version not accessed)
quote:       Eq. (11), transcribed from the rendered page:
               PSR^(SR*) = Z[ (SR^ − SR*)·√(n−1) / √(1 − γ^3·SR^ + ((γ^4 − 1)/4)·SR^²) ]
             "where Z is the cdf of the Standard Normal distribution"
             "greater SR^ (in the original sampling frequency, i.e. non-annualized)"
             p.7: "γ3 = E[r−μ]^3/σ^3 is skewness, and γ4 = E[r−μ]^4/σ^4 is kurtosis."
retrieved:   2026-10-17
```

- The kurtosis term is (γ̂4 − 1)/4 with γ̂4 = E[(r−μ)^4]/σ^4. This is the raw fourth standardized moment, which is **non-excess**. The paper's Normal case uses "(γ^3 = 0, γ^4 = 3)" (p.10).
- ŜR is non-annualized. The paper also says: "All calculations are done in the original frequency of the data, and there is no annualization."
- **PSR numeric example (p.10 and Figure 6, p.36), usable as a unit test:**
  - Inputs: monthly returns over "the last two years", so n = 24 is implied (the text does not print n). Figure 6 gives Mean 0.036, StDev 0.079, Skew −2.448, Kurt 10.164, SR 0.458, Ann. SR 1.585.
  - With SR^ = 0.458, SR* = 0 and the Normal case (γ3 = 0, γ4 = 3): PSR(0) = 0.982.
  - With γ3 = −2.448 and γ4 = 10.164: PSR(0) = 0.913.
  - With "3 years instead of 2" (n = 36 implied): PSR(0) = 0.953.

## BT11: DSR and SR0 (Bailey and López de Prado 2014), with numeric example

```
claim_id:    BT11
verdict:     CONFIRMED
source:      https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf  (authors' copy; pp. 7-10, 12-13)
source_tier: 4 (original paper)
version:     "First version: April 15, 2014 / This version: July 31, 2014 / Journal of Portfolio Management,
             Forthcoming, 2014"; SSRN 2460551 (published JPM 40(5) typeset version not accessed)
quote:       Eq. (2), transcribed from the rendered page:
               DSR^ ≡ PSR^(SR^0) = Z[ (SR^ − SR^0)·√(T−1) / √(1 − γ^3·SR^ + ((γ^4 − 1)/4)·SR^²) ]
               where SR^0 = √(V[{SR^n}]) · ( (1−γ)·Z^{-1}[1 − 1/N] + γ·Z^{-1}[1 − (1/N)·e^{-1}] )
             "where γ (approx. 0.5772) is the Euler-Mascheroni constant"; Snippet 1: emc=0.5772156649
             "V[{SR^n}] is the variance across the trials' estimated SR and N is the number of independent trials"
retrieved:   2026-10-17
```

- The ledger's SR0 matches eq. (2) term for term: Φ⁻¹(1−1/(N·e)) = Z⁻¹[1 − (1/N)e⁻¹], and γ is the Euler–Mascheroni constant. The DSR paper uses √(T−1) with T = sample length, which is the same as the PSR paper's √(n−1).
- **Numeric example (pp. 9–10). All inputs as printed:**
  - Story: a daily strategy over 5 years, "with 250 observations per year".
  - Selected strategy: annualized ŜR = 2.5. Many trials yield an annualized ŜR of 2.
  - "N = 100, V[{SR^n}] = 1/2, T=1250, γ^3 = −3 and γ^4 = 10".
  - De-annualisation as printed. SR0 uses √(1/(2·250)), meaning V = 1/2 divided by 250. ŜR enters as 2.5/√250. The numerator uses √1249.
  - Output: "SR^0 ≈ 0.1132, non-annualized (with 250 observations per year)". "DSR^ ≈ Z[ ((2.5/√250 − 0.1132)·√1249) / √(1 − (−3)·(2.5/√250) + ((10−1)/4)·(2.5/√250)²) ] = 0.9004 < 0.95".
  - Extra checkpoints: "Should the strategist have made his discovery after running only N=46 independent trials ... DSR would have been 0.9505". "If the strategy had exhibited Normal returns (γ^3 = 0, γ^4 = 3), DSR = 0.9505 after N=88 independent trials." The Normal case also confirms γ4 is non-excess.
  - Test advice: the paper rounds SR0 to 0.1132 in its displayed substitution. Compute SR0 unrounded, compare SR0 at about 5e-5 and DSR to 0.9004 at about 1e-3 (3 decimals, as pre-registered).
- Notes relevant to PROTOCOL §7 (N = 25; V[SR] = variance of the 25 per-day SRs):
  - V must be in the same non-annualized units as ŜR. The example converts annual V = 1/2 to 1/(2·250). PROTOCOL's per-day V is consistent with that.
  - The paper requires N to be the number of **independent** trials. A.3: "using M instead of N will overstate E[max{SR^n}]". If the 25 rules are correlated, N = 25 overstates SR0 and understates DSR, which is conservative.
  - The expected-maximum approximation is derived "for a large N" (A.1). Exhibit 3.1: "When the number of trials is very small (e.g., less than 50), the analytical result sometimes overestimates the empirical result, by a very small margin (less than 0.05 for an underlying process with variance 1)."

## BT13: rules.yaml thresholds vs ORIG (static read)

```
claim_id:    BT13
verdict:     CONFIRMED (25 of 25 rules: threshold, comparison operator and class all match)
source:      C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators\backtest\rules.yaml (lines 18-42)
             C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\IBSFade.cs (ORIG, 3,230 lines)
source_tier: 2 (source code)
version:     files as on disk 2026-10-17 (rules.yaml frozen 2026-10-17)
retrieved:   2026-10-17
```

| Module (rules.yaml line) | rules.yaml long / short | ORIG classification (line) | Match |
|---|---|---|---|
| HedgingPressure (18) | `x <= -35` / `x >= 35` | 1264 `hpScore <= HpBuyThreshold ? "B" : hpScore >= HpSellThreshold ? "S" : "N"`; defaults 260–261 `HpBuyThreshold = -35; HpSellThreshold = 35` | yes |
| IBS (19) | `x < 0.20` / `x > 0.80` | 1269 `ibs < BuyThreshold ? "B" : ibs > SellThreshold ? "S"`; defaults 251–252 `0.2` / `0.8` | yes |
| RSI2 (20) | `x < 25` / `x > 75` | 1274 `rsi2[0] < 25 ? "B" : rsi2[0] > 75 ? "S"` | yes |
| ConnorsRSI (21) | `x < 15` / `x > 85` | 1295 `crsiVal < 15 ? "B" : crsiVal > 85 ? "S"` (crsiVal = 50 when CurrentBar < 100, 1278–1279) | yes |
| StochFade (22) | `x < 30` / `x > 70` | 1300 `stoch.K[0] < 30 ? "B" : stoch.K[0] > 70 ? "S"` | yes |
| RVZScore (23) | `x > 2.0` / `x < -1.5` | 1305 `rvZscoreSeries[0] > 2.0 ? "B" : rvZscoreSeries[0] < -1.5 ? "S"` | yes |
| CompositeVol (24) | `x > 1.5` / `x < -1.5` | 1329 `compVal > 1.5 ? "B" : compVal < -1.5 ? "S"` | yes |
| TurnOfMonth (25) | `x == 1` / never | 1338 `Values[7][0] = tom ? 1 : 0`; 1339 `tom ? "B" : "N"` | yes |
| ConsecDays (26) | `x <= -3` / `x >= 3` | 1345 `consecDownDays >= 3 ? "B" : consecUpDays >= 3 ? "S"`; value 1343 `consecUpDays > 0 ? consecUpDays : -consecDownDays` | yes (equivalent; see note 1) |
| OvernightGap (27) | `x < -0.3` / `x > 0.3` | 1350 `overnightGapPct < -0.3 ? "B" : overnightGapPct > 0.3 ? "S"`; value in % (1571 `* 100.0`) | yes |
| BollingerPctB (28) | `x == -1` / `x == 1` (touch value per note) | 1358–1359 `Close[0] <= boll.Lower[0] + 0.001 * atr14[0] ? "B" : Close[0] >= boll.Upper[0] - 0.001 * atr14[0] ? "S"` | yes (rules.yaml note reproduces the test and B-first precedence) |
| TurnaroundTuesday (29) | `x == 1` / never | 1363 `int dow = (int)cstT.DayOfWeek`; 1365 `cstT.DayOfWeek == DayOfWeek.Monday ? "B" : "N"` (.NET Monday = 1) | yes (see note 2) |
| RSI14 (30) | `x < 40` / `x > 60` | 1370 `rsi14[0] < 40 ? "B" : rsi14[0] > 60 ? "S"` | yes |
| VRPProxy (31) | `x > 1.5` / `x < 0.7` | 1376 `vrpVal > 1.5 ? "B" : vrpVal < 0.7 ? "S"` | yes |
| WideRangeBar (32) | `x > 1.2` / never | 1382 `rangeAtrRatio > 1.2 ? "B" : "N"` | yes |
| VWAPDistance (33) | `-0.5 < x < 0` / `0 < x < 0.5` | 1394 `dist < 0 && Math.Abs(dist) < halfAtr` → B; 1395 `dist > 0 && dist < halfAtr` → S; value 1386–1387 `(Close[0] - manualVwap) / atr14[0]` | yes (dist/ATR vs ±0.5 is equivalent for ATR > 0) |
| MACDHistogram (34) | `x > 0` / `x < 0` | 1401 `macd.Diff[0] > 0 ? "B" : macd.Diff[0] < 0 ? "S"` | yes |
| EMACross (35) | `x > 0` / `x < 0` | 1407 `emaDiff > 0 ? "B" : emaDiff < 0 ? "S"` | yes |
| SMA200Trend (36) | `x > 0` / `x < 0` | 1413 `CurrentBar < 200 ? "N" : (Close[0] > sma200[0] ? "B" : Close[0] < sma200[0] ? "S"`; value 0 before bar 200 (1411) | yes |
| ATRRegime (37) | `x < 1.5` / never | 1419 `atrReg < 1.5 ? "B" : "N"` | yes (see note 3) |
| VolumeSpike (38) | `x > 1.5` / never | 1425 `volRatio > 1.5 ? "B" : "N"` | yes |
| VolumeDelta (39) | `x > 0` / `x < 0` | 1436 `CurrentBar <= 20 ? "N" : (cumDelta > 0 ? "B" : cumDelta < 0 ? "S"`; value 0 when CurrentBar ≤ 20 (1430) | yes |
| LiquiditySweep (40) | `x == 1` / `x == -1` (End events) | 2363 `direction == 1 ? "Bullish" : "Bearish"`; 2370 `if (direction == 1) totalBuys_LS++; else totalSells_LS++;`; 2373–2385 DataBox row 24 written only `if (!isStart)` | yes |
| OrderFlowPlus (41) | `x == 1` / `x == -1` | 2505 `bool isBuy = ofDir == 1;` 2508 `(isBuy ? "Buy" : "Sell")` | yes |
| SMC (42) | `x == 1` / `x == -1` | 2703 `bool isBuy = smcDir == 1;` 2706 `(isBuy ? "Buy" : "Sell")` | yes |

Notes. None of these changes the verdict.
1. **ConsecDays equivalence.** The equivalence needs the counters to be mutually exclusive. Lines 1556–1565 reset the opposite counter on every up or down close, and an unchanged close keeps both counters ("else: unchanged, keep counts"). Both start at 0 (406–407). So streak ≤ −3 is equivalent to consecDownDays ≥ 3, and streak ≥ 3 is equivalent to consecUpDays ≥ 3.
2. **TurnaroundTuesday label vs code.** The label text at 1366 shows `"S[Fri]"`, but the code never assigns "S". rules.yaml's `short: never` follows the code, which is correct. ORIG uses the calendar day of `Time[0]` converted to Central (1333–1334), not an explicit trading date. On a D bar these coincide only if the D bar's timestamp falls on the trading date.
3. **ATRRegime warm-up.** ORIG's value defaults to `1.0` when `CurrentBar < 50` (1417), which classifies as "B", so ORIG is long during warm-up. If the engine's value is NaN in warm-up, PROTOCOL maps NaN to 0 and the engine would be flat. On the D frame, 2020 warm-up is longer than 50 bars, so the evaluation window is unaffected.
4. **Thresholds are user properties.** HP and IBS thresholds come from user-editable properties. rules.yaml uses the defaults (251–252, 260–261).
5. **Pattern-rule citations.** The cited pattern ranges (2340–2404, 2420–2541, 2548–2739) are the DataBox-row writers (rows 24, 27–28, 29–30), not `UpdateDataBoxValues`. OF+ and SMC events are also suppressed by `if (ofDir == lastOfDir && barsSinceLastOf < DuplicateBarWindow) return;` (2502) and its SMC twin (2700). The default is `DuplicateBarWindow = 5` (268). The value functions must replicate this suppression (PT3/PT4).
6. **Frame rule wording (outside the BT13 scope, for the orchestrator).** The rules.yaml header says "home timeframe = first timeframe the ORIG DataBox label lists ... "D" when the list contains 1d, else "15m"". The two clauses disagree for 8 rules. The second clause is what was applied:
   - Stoch `|15m,1h,1d` → D
   - RSI14 `|1h,4h,1d` → D
   - MACD `|4h,1d` → D
   - EMA `|1h,4h,1d` → D
   - ATRRegime `|15m,1h,1d` → D
   - VWAP `|1m,15m,5000t` → 15m
   - VolSpike `|1m,15m,1h` → 15m
   - VolDelta `|1m,15m,5000t` → 15m

   LiqSweep's row-24 label carries no timeframe list. ORIG itself classifies every DataBox value on the chart's **primary** series (`if (BarsInProgress != 0) return;` at 547, then `UpdateDataBoxValues` at 581). The D/15m frame is therefore a PROTOCOL choice, not ORIG behaviour.

## BT16: State.Realtime vs State.Historical

```
claim_id:    BT16 (Channel A half: state semantics)
verdict:     CONFIRMED
source:      (a) https://static.ninjatrader.com/support/helpGuides/nt8/onstatechange.htm
             (b) https://static.ninjatrader.com/support/helpGuides/nt8/state.htm
             (c) https://static.ninjatrader.com/support/helpGuides/nt8/historical_order_backfill_logic.htm
             (d) https://static.ninjatrader.com/support/helpGuides/nt8/syncing_account_positions.htm
             (e) https://static.ninjatrader.com/support/helpGuides/nt8/running_a_ninjascript_strategy.htm
             (f) https://static.ninjatrader.com/support/helpGuides/nt8/getrealtimeorder.htm
source_tier: 1
version:     NT8 online help guide (current 8.1.x)
quote:       (a) "Historical is called once the object begins to process historical data." /
                 "This object is called multiple times when running a backtest optimization"
             (a) "Realtime is called once when the object begins to process realtime data."
             (c) "process order fills on historical data in two scenarios: when processing fills in the Strategy
                 Analyzer, or when processing historical orders for a live running strategy"
             (d) "Once a flat state is achieved ... all future orders will be placed live."
             (e) "A NinjaScript strategy is a self contained automated trading system, and orders generated are live."
retrieved:   2026-10-17
```

Caveats. These do not refute the state semantics, but they bear on the safety intent of "cannot submit orders in State.Realtime".
1. **Historical working orders can go live at the transition without a call made in Realtime.** Source (f): "you had a working order which was submitted historically and re-submitted in real-time as the strategy is enabled". Source (d), under "Immediately submit": "Any remaining active strategy orders that cannot be successfully paired will be submitted live". A guard that only blocks order calls while `State == State.Realtime` does not stop an order submitted on the last historical bar from being re-submitted live. The guard should also block in State.Historical when the strategy is attached live (not under Strategy Analyzer), or orders should be cancelled in State.Transition. This is for Channel B's static check.
2. **Sync-account orders are submitted by NinjaTrader itself.** Source (d): "NinjaTrader will submit a market order(s) to reconcile the Account Position to a flat state." Also: "The reconciliatory market order is submitted outside of the strategy". This applies under the "synchronize account" start behaviours. The default is "Wait until flat" ("These are the default settings for your strategies").
3. **Playback runs as real-time.** The Playback connection delivers data "as if it was happening in real-time" (playback_connection.htm). The help page does not name the State. The pre-registered user-run playback check is the right test.

---

## Completeness note: PROTOCOL §3 (trading-date roll at 17:00 CT) vs NT8 help and CME pages

1. **CME holiday trade dates contradict a fixed 17:00 calendar rule.**
   - Source: https://www.cmegroup.com/trading-hours.html (Globex holiday table, Thanksgiving 2026, Equities row; tier 1).
   - Wednesday 25 Nov: "TRADE DATE: WED 25 NOV 16:00 CLOSED / TRADE DATE: FRI 27 NOV 16:45 PREOPEN 17:00 OPEN".
   - Thursday 26 Nov: "TRADE DATE: FRI 27 NOV 12:00 PREOPEN 17:00 OPEN".
   - Friday 27 Nov: "TRADE DATE: FRI 27 NOV 12:15 CLOSED".
   - CME books Wed 17:00 through Fri 12:15 to a **single trade date (Friday)**. PROTOCOL §3 assigns Wed-evening and Thu-morning bars to a "Thursday" trading date that CME does not have. That creates an extra short D bar and shifts date-based features (TurnOfMonth, TurnaroundTuesday, OvernightGap) around holidays.
   - Only the 2026 Thanksgiving schedule was retrieved. Other holidays (MLK, Presidents, Memorial, Juneteenth, July 4, Labor Day) were listed on the page but not opened. Historical years were not checked.
2. **NT8 defines the trading day by template sessions, not by the clock.**
   - Source: https://static.ninjatrader.com/support/helpGuides/nt8/using_the_trading_hours_window.htm.
   - Quote: "on the last session of the day you would check mark "EOD(End of Day)". This tells NinjaTrader that this session signifies the ending session for the current trading day". Holidays: "Full Day / Any sessions between the EOD session of the Holidays Trading Date and the prior EOD marker are excluded."
   - So NT8 daily bars, ORIG's daily secondary series, and QS_* in Strategy Analyzer follow the trading-hours template, including its holiday rules. On holidays they can differ from PROTOCOL's D frame. This is relevant to BT15 differences beyond fill-model differences.
3. **Consistent, not a contradiction.**
   - Source: https://static.ninjatrader.com/support/helpGuides/nt8/how_bars_are_built.htm. Quote: "NinjaTrader stamps a bar with the closing time of the bar. For example, a minute bar with a time of 9:31:00 AM has data from 9:30:00 AM through 9:30:59 AM."
   - This supports PROTOCOL §2's "bar time = bar close". Under that convention, a bar stamped 17:00:00 holds 16:59 data (the maintenance halt), and the first new-session bar is stamped 17:01. The rule "close time after 17:00 → next date" therefore matches CME's regular session boundary on non-holiday days.
4. **Historical intraday pause.** Until trade date 2021-06-28 there was a 15:15–15:30 CT Globex halt for certain equity futures (see BT4). This does not change the 17:00 roll. It does affect 15m bars in 2020 through June 2021.

## Sources consulted but not used as evidence

- NinjaTrader support-forum threads and `ninjatrader.com/futures/blogs/how-much-does-ninjatrader-cost/`. These are secondary and not evidence. The blog's all-in figures (0.94/0.84/0.64) agree with the primary commission table.
- `traders.studentorg.berkeley.edu/papers/The-Statistics-of-Sharpe-Ratios.pdf`. This is a third-party mirror of Lo (2002). It is secondary and was not used.
- Web-search summaries (all claims). These are not evidence. Each figure above was read on the cited page itself.
