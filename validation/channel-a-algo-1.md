# Channel A (documentation audit) — algo-claims-ledger.md, claims B1–B9 (a) and M1–M14 (a)

status: COMMITTED 2026-10-16 before any Channel B file was read (no channel-b*.md opened)
auditor: Channel A subagent (no code executed; no QI_*.cs read)
ledger: `validation/algo-claims-ledger.md` (FROZEN 2026-10-16)
installed version audited: NinjaTrader 8.1.8.3 (`validation/env-pin.txt`); shipped indicator sources in
`C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@*.cs` (header: "Copyright (C) 2026, NinjaTrader LLC")
help guide: `https://ninjatrader.com/support/helpGuides/nt8/<page>` 301-redirects to `https://static.ninjatrader.com/support/helpGuides/nt8/<page>`;
the short page names in the ledger (rsi.htm, ema.htm, sma.htm, atr.htm, macd.htm, bollinger.htm, adx.htm) 404 — the real
page names were taken from the guide's own index (`indicators.htm`) and are cited below. `stddev.htm` exists but is the
TradesPerformance StdDev page, not the indicator. The help guide is unversioned (one NT8 guide); treated as matching 8.1.x.

Source tiers (docs-audit.md §4): 1 = official docs; 2 = installed source; 4 = original publication / publisher's own page.
Verdict counts: CONFIRMED 12, REFUTED 2, UNVERIFIABLE 9 (of 23).

Summary table

| ID | Verdict | One-line reason |
|----|---------|-----------------|
| B1 | CONFIRMED (with 2 precision notes) | Wilder RSI per @RSI.cs; `smooth` only affects `.Avg`, never `Default`; first average is SMA(up/down, n) including the bar-0 zero |
| B2 | CONFIRMED | @EMA.cs line 42 is exactly the stated recursion, seeded with Input[0] |
| B3 | CONFIRMED | @SMA.cs: sum/Period; warm-up uses partial-window mean |
| B4 | CONFIRMED | @ATR.cs line 45 is exactly the stated recursion; help says Wilder k = 1/Period |
| B5 | CONFIRMED | @StdDev.cs line 55 divides by min(CurrentBar+1, Period) → population |
| B6 | CONFIRMED (seed note) | @MACD.cs; signal EMA seeded at 0 on bar 0 |
| B7 | CONFIRMED | @Bollinger.cs: SMA ± NumStdDev·StdDev (population) |
| B8 | CONFIRMED (edge-case note) | @StochasticsFast.cs; signature (periodD, periodK); den = 0 → carry K[1] (50 on bar 0) |
| B9 | CONFIRMED (NT-specific warm-up notes) | @ADX.cs recursion as stated; seeded 50; no 14-bar simple seed |
| M1 | UNVERIFIABLE | qusma.com (Pagonidis) unreachable (HTTP 522 ×5); quantifiedstrategies.com bot-walled |
| M2 | CONFIRMED | TradingMarkets (Connors' publisher): "the 2-period Wilder's RSI, or RSI(2)" |
| M3 | REFUTED | Publisher's ConnorsRSI code: price RSI period **3** (ledger 2); unchanged close **resets streak to 0** (ledger keeps counts) |
| M4 | CONFIRMED (as NT definition) | = B8; Lane 1984 article not retrievable |
| M5 | UNVERIFIABLE | no primary; "DthetaSpike" returns nothing |
| M6 | UNVERIFIABLE | unpublished composite |
| M7 | UNVERIFIABLE (deviation flagged) | H&Z 1996 / L&S 1988 full texts paywalled; all retrievable descriptions use **trading** days, ledger uses calendar days |
| M8 | UNVERIFIABLE (concept confirmed, tie rule not) | Connors (2007) counts "closed down ... consecutive days", silent on unchanged closes; 2008 book not retrievable |
| M9 | UNVERIFIABLE | cited "MDPI 2025" paper not locatable |
| M10 | REFUTED | Bollinger's %b is the Stochastics-form (C − lower)/(upper − lower); ledger's (C − middle)/half-width·100 is 200·%b − 100 |
| M11 | UNVERIFIABLE | French 1980 abstract/full text not retrievable (403 everywhere); paper does not define a Monday flag |
| M12 | CONFIRMED (via NT help/source; Wilder scan borrow-only) | = B1 with n = 14; NT help attributes formula to Wilder 1978, default Period = 14 |
| M13 | UNVERIFIABLE | proxy, no publication |
| M14 | UNVERIFIABLE | Crabel 1990 not retrievable; secondary describes a different (range-vs-prior-ranges) definition |

---

## B1 — RSI_n (Wilder) with NT `smooth`

```
claim_id:    B1
verdict:     CONFIRMED  (two precision notes below; neither changes the post-warm-up value of RSI(...)[0])
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@RSI.cs  lines 50-52, 78-106, 136-141
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source (file header "Copyright (C) 2026, NinjaTrader LLC")
quote:       line 80-81:  down[0] = Math.Max(input1 - input0, 0);  up[0] = Math.Max(input0 - input1, 0);
             line 90-95:  if (CurrentBar + 1 == Period) { avgDown[0] = smaDown[0]; avgUp[0] = smaUp[0]; }
             line 99-100: avgDown[0] = (avgDown[1] * constant3 + down[0]) / Period;  avgUp[0] = (avgUp[1] * constant3 + up[0]) / Period;   // constant3 = Period - 1 (line 52)
             line 104:    double value0 = avgDown0 == 0 ? 100 : 100 - 100 / (1 + avgUp[0] / avgDown0);
             line 105-106: Default[0] = value0;  Avg[0] = constant1 * value0 + constant2 * Avg[1];   // constant1 = 2/(1+Smooth), constant2 = 1 - 2/(1+Smooth) (lines 50-51)
             line 136:    public RSI RSI(int period, int smooth)
retrieved:   2026-10-16
source_2:    https://static.ninjatrader.com/support/helpGuides/nt8/relative_strength_index_rsi.htm  (tier 1)
quote_2:     "exponential moving average with a smoothing constant (k = 1/ Period)"; syntax "RSI(int period, int smooth)",
             "RSI(ISeries<double> input, int period, int smooth)", ".Avg[int barsAgo]"; parameters: period = "Number of bars
             used in the calculation", smooth = "The smoothing period".
note:        (1) The ledger says NT "applies an extra EMA_smooth to the result, smooth = 1 ⇒ none". Precisely: the EMA_smooth
             is applied ONLY to the secondary plot `.Avg` (line 106); the primary value `Default` / `RSI(...)[0]` (line 105)
             is NEVER smoothed, for any `smooth`. With smooth = 1, constant1 = 1, constant2 = 0 so Avg == Default. So the
             ledger's statement is true for `.Avg` and vacuous for `[0]`; a QI module reading `RSI(...)[0]` gets pure Wilder
             RSI regardless of `smooth`.
             (2) Warm-up: Default is unset (0) until CurrentBar + 1 == Period; the first averages are SMA(up, Period) /
             SMA(down, Period) (lines 60-61, 93-94), and up[0] = down[0] = 0 on bar 0 (lines 69-70), so the first average
             covers Period − 1 real changes plus one zero, divided by Period. Wilder's book seeds with the mean of the first
             n changes; NT's seed differs by that one zero. Decays geometrically with (n−1)/n; immaterial after the ledger's
             300-bar warm-up. (3) avgDown == 0 ⇒ 100 (line 104), i.e. a monotone-up series gives exactly 100.
             (4) Wilder (1978) itself: archive.org item newconceptsintec00wild is access-restricted (401 on djvu.txt;
             "No suitable files to display here"), so the book text was NOT retrieved; the Wilder attribution rests on the
             NT help page (tier 1).
```

## B2 — EMA_n

```
claim_id:    B2
verdict:     CONFIRMED
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@EMA.cs  lines 37-38, 42
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source
quote:       line 37-38: constant1 = 2.0 / (1 + Period); constant2 = 1 - 2.0 / (1 + Period);
             line 42:    protected override void OnBarUpdate() => Value[0] = CurrentBar == 0 ? Input[0] : Input[0] * constant1 + constant2 * Value[1];
retrieved:   2026-10-16
source_2:    https://static.ninjatrader.com/support/helpGuides/nt8/moving_average_-_exponential_e.htm  (tier 1)
quote_2:     "In the exponential moving average equation the most recent market action is assigned greater importance";
             "The oldest pricing data in the exponential moving average is however never removed." Syntax "EMA(int period)".
             (Page gives no numeric smoothing constant; the constant 2/(n+1) is established by the source, tier 2.)
note:        EMA[0] = α·x[0] + (1−α)·EMA[1] with α = 2/(n+1) is algebraically identical to the ledger's
             EMA[1] + α·(x[0] − EMA[1]). Seed = Input[0] on bar 0 (the ledger does not state the seed; the 1e-3 tolerance
             after warm-up makes it immaterial).
```

## B3 — SMA_n

```
claim_id:    B3
verdict:     CONFIRMED
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@SMA.cs  lines 43-63
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source
quote:       line 61-62: sum = priorSum + Input[0] - (CurrentBar >= Period ? Input[Period] : 0);
                         Value[0] = sum / (CurrentBar < Period ? CurrentBar + 1 : Period);
             line 51-53 (IsRemoveLastBarSupported branch): Value[0] = CurrentBar >= Period
                         ? (last + Input[0] - Input[Period]) / Math.Min(CurrentBar, Period)
                         : (last + Input[0]) / (Math.Min(CurrentBar, Period) + 1);
retrieved:   2026-10-16
source_2:    https://static.ninjatrader.com/support/helpGuides/nt8/moving_average_-_simple_sma.htm  (tier 1)
quote_2:     "The Simple Moving Average is calculated by summing the closing prices of the security for a period of time"
             (then divided by the number of periods, per the page's prose).
note:        From bar Period−1 onward Value = mean of the last Period inputs exactly (both code branches). During warm-up
             (CurrentBar < Period) NT returns the mean of the bars available so far, not 0/NaN — relevant to any reference
             that asserts equality "from bar 199" (ledger's B3(b) wording is consistent with this).
```

## B4 — ATR_n

```
claim_id:    B4
verdict:     CONFIRMED
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@ATR.cs  lines 39-46
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source
quote:       line 39-40: if (CurrentBar == 0) Value[0] = high0 - low0;
             line 44:    double trueRange = Math.Max(Math.Abs(low0 - close1), Math.Max(high0 - low0, Math.Abs(high0 - close1)));
             line 45:    Value[0] = ((Math.Min(CurrentBar + 1, Period) - 1 ) * Value[1] + trueRange) / Math.Min(CurrentBar + 1, Period);
retrieved:   2026-10-16
source_2:    https://static.ninjatrader.com/support/helpGuides/nt8/average_true_range_atr.htm  (tier 1)
quote_2:     True Range = "the largest of three values: the current high minus the current low, the absolute value of the current
             high minus the previous close, or the absolute value of the current low minus the previous close" (page prose);
             formula note: Wilder's exponential moving average with smoothing constant "k = 1/ Period".
note:        min(CurrentBar+1, n) − 1 == min(CurrentBar, n−1), so line 45 is literally the ledger's
             ((min(bar, n−1))·ATR[1] + TR)/min(bar+1, n). Bar 0 uses H−L (no prior close), which the ledger does not
             state but which is the only possible TR on bar 0. Wilder 1978 text not retrieved (see B1 note 4).
```

## B5 — StdDev_n (population)

```
claim_id:    B5
verdict:     CONFIRMED
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@StdDev.cs  lines 42-56
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source
quote:       line 49-50: sumSeries[0] = Input[0] + sumSeries[1] - (CurrentBar >= Period ? Input[Period] : 0);
                         double avg = sumSeries[0] / Math.Min(CurrentBar + 1, Period);
             line 52-53: for (int barsBack = Math.Min(CurrentBar, Period - 1); barsBack >= 0; barsBack--)
                             sum += (Input[barsBack] - avg) * (Input[barsBack] - avg);
             line 55:    Value[0] = Math.Sqrt(sum / Math.Min(CurrentBar + 1, Period));
retrieved:   2026-10-16
source_2:    https://static.ninjatrader.com/support/helpGuides/nt8/standard_deviation_stddev.htm  (tier 1)
quote_2:     "A low standard deviation indicates that the data points tend to be very close to the same value (the mean)";
             syntax "StdDev(int period)". The page "does not state whether the calculation uses the population or sample
             standard deviation" — the population choice is established only by the source (tier 2 wins per §4).
note:        Divisor is the window length N = min(CurrentBar+1, Period), not N−1 ⇒ population. Bar 0 returns 0 (line 44).
             Warm-up uses the partial window (same convention as SMA).
```

## B6 — MACD(fast, slow, signal)

```
claim_id:    B6
verdict:     CONFIRMED  (seed note)
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@MACD.cs  lines 55-60, 73-92, 168
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source
quote:       line 75-79 (bar 0): fastEma[0] = input0; slowEma[0] = input0; Value[0] = 0; Avg[0] = 0; Diff[0] = 0;
             line 83-86: double fastEma0 = constant1 * input0 + constant2 * fastEma[1];
                         double slowEma0 = constant3 * input0 + constant4 * slowEma[1];
                         double macd     = fastEma0 - slowEma0;
                         double macdAvg  = constant5 * macd + constant6 * Avg[1];
             line 90-92: Value[0] = macd; Avg[0] = macdAvg; Diff[0] = macd - macdAvg;
             line 168:   public MACD MACD(int fast, int slow, int smooth)
retrieved:   2026-10-16
source_2:    https://static.ninjatrader.com/support/helpGuides/nt8/moving_average_convergence-divergence_macd.htm  (tier 1)
quote_2:     "subtracting the longer moving average from the shorter moving average"; outputs Default (MACD), ".Avg" (signal),
             ".Diff"; parameters fast/slow = bars for the fast/slow EMA, smooth = bars for "the EMA signal line".
note:        Constants are 2/(1+Fast), 2/(1+Slow), 2/(1+Smooth) (lines 55-60) ⇒ standard EMAs. Deviation worth recording for
             a reference implementation: the signal EMA is seeded with Avg = 0 on bar 0 (line 78), NOT with the first MACD
             value, and the fast/slow EMAs are seeded with the first input. Effect decays as (1−2/(1+9))^k; immaterial at
             the ledger's 1e-3 tolerance after a few hundred bars. Appel's original text not retrieved; the ledger's F matches
             NT exactly, which is the source QI uses.
```

## B7 — Bollinger(numStdDev, n)

```
claim_id:    B7
verdict:     CONFIRMED
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@Bollinger.cs  lines 42-43, 49-54, 89
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source
quote:       line 42-43: sma = SMA(Period); stdDev = StdDev(Period);
             line 52-54: Upper[0] = sma0 + NumStdDev * stdDev0; Middle[0] = sma0; Lower[0] = sma0 - NumStdDev * stdDev0;
             line 89:    public Bollinger Bollinger(double numStdDev, int period)
retrieved:   2026-10-16
source_2:    https://static.ninjatrader.com/support/helpGuides/nt8/bollinger_bands.htm  (tier 1)
quote_2:     syntax "Bollinger(double numStdDev, int period)", ".Upper[int barsAgo]", ".Lower[int barsAgo]"; middle band
             described as a simple moving average, upper/lower as SMA plus/minus 2 standard deviations (page prose).
source_3:    https://www.bollingerbands.com/bollinger-bands  (tier 4, John Bollinger's own site)
quote_3:     "20 periods for the moving average with the bands set at plus and minus two standard deviations";
             "We use the population calculation for standard deviation."
note:        NT's StdDev is population (B5), so NT Bollinger matches Bollinger's published construction exactly. Input is the
             indicator's Input series (Close by default). `Middle` has no documented accessor on the help page but exists in
             source (line 64).
```

## B8 — StochasticsFast(periodD, periodK)

```
claim_id:    B8
verdict:     CONFIRMED  (edge-case note)
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@StochasticsFast.cs  lines 39-40, 51-53, 59-65, 95
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source
quote:       line 39-40: PeriodD = 3; PeriodK = 14;
             line 51-53: min = MIN(Low, PeriodK); max = MAX(High, PeriodK); smaK = SMA(K, PeriodD);
             line 60-61: nom[0] = Close[0] - min0; den[0] = max[0] - min0;
             line 63:    K[0] = den[0].ApproxCompare(0) == 0 ? CurrentBar == 0 ? 50 : K[1] : Math.Min(100, Math.Max(0, 100 * nom[0] / den[0]));
             line 65:    D[0] = smaK[0];
             line 95:    public StochasticsFast StochasticsFast(int periodD, int periodK)
retrieved:   2026-10-16
source_2:    https://static.ninjatrader.com/support/helpGuides/nt8/stochastics_fast.htm  (tier 1)
quote_2:     "StochasticsFast(int periodD, int periodK)", "StochasticsFast(ISeries<double> input, int periodD, int periodK)",
             ".K[int barsAgo]", ".D[int barsAgo]"; periodD = "The period for the moving average applied to %D"; page credits
             George C. Lane; "The page contains no formula."
note:        Parameter order periodD, periodK confirmed in both help and source ⇒ StochasticsFast(3, 14) is %D = SMA_3,
             %K over 14 bars, as the ledger states. %K uses Close/High/Low directly (ignores `input`). Edge case not in the
             ledger's F: when HH == LL, K carries the previous K (50 on bar 0) instead of being undefined; K is clamped to
             [0,100]. MIN/MAX (@MIN.cs/@MAX.cs line 63) use min(CurrentBar, Period−1) bars back during warm-up, i.e. the
             window shrinks to the available bars. Lane's 1984 S&C article ("Lane's Stochastics", May/June 1984) was not
             retrievable; the NT definition is the one the ledger claims and it is confirmed.
```

## B9 — ADX_n

```
claim_id:    B9
verdict:     CONFIRMED  (NT-specific warm-up/seed notes)
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@ADX.cs  lines 59-103
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source
quote:       line 67 (bar 0): Value[0] = 50;
             line 75-77: tr[0] = Math.Max(Math.Abs(low0 - close1), Math.Max(high0 - low0, Math.Abs(high0 - close1)));
                         dmPlus[0]  = high0 - high1 > low1 - low0 ? Math.Max(high0 - high1, 0) : 0;
                         dmMinus[0] = low1 - low0 > high0 - high1 ? Math.Max(low1 - low0, 0) : 0;
             line 79-83 (CurrentBar < Period): sumTr[0] = sumTr[1] + tr[0]; (same for sumDmPlus, sumDmMinus)
             line 91-93: sumTr[0] = sumTr1 - sumTr1 / Period + tr[0]; (same for DM+ and DM−)
             line 97-98: double diPlus = 100 * (sumTr0.ApproxCompare(0) == 0 ? 0 : sumDmPlus[0] / sumTr[0]); (diMinus likewise)
             line 102:   Value[0] = sum.ApproxCompare(0) == 0 ? 50 : ((Period - 1) * Value[1] + 100 * diff / sum) / Period;
retrieved:   2026-10-16
source_2:    https://static.ninjatrader.com/support/helpGuides/nt8/average_directional_index_adx.htm  (tier 1)
quote_2:     syntax "ADX(int period)"; "The page contains no formula text."
note:        Structure matches the ledger: DX = 100·|DI+ − DI−|/(DI+ + DI−), ADX = ((n−1)·ADX[1] + DX)/n (Wilder_n), with
             +DM/−DM/TR as Wilder's rules (the larger of the two moves wins, ties ⇒ 0). NT specifics a reference must
             reproduce to hit 1e-2: (i) ADX seeded at 50 on bar 0 and smoothed from bar 1 on — NO initial n-bar simple
             average of DX as in Wilder's worksheet; (ii) during CurrentBar < Period the DM/TR sums are plain cumulative
             sums, then Wilder's "sum − sum/n + new" (which is n·Wilder_n, and the n cancels in the DI ratio);
             (iii) DI+ + DI− == 0 ⇒ ADX = 50. Wilder's text not retrieved (B1 note 4).
```

---

## M1 — QI_IBS: IBS = (C − L)/(H − L) of the daily bar; 0.5 if H = L

```
claim_id:    M1
verdict:     UNVERIFIABLE
source:      https://qusma.com/2012/11/06/closing-price-in-relation-to-the-days-range-and-equity-index-mean-reversion/
             https://qusma.com/2013/09/11/paper-the-ibs-effect-mean-reversion-in-equity-etfs/
             https://qusma.com/tag/ibs-effect/
source_tier: 4 (intended)
version:     n/a
quote:       NOT RETRIEVED — all five attempts (two URLs, three retries spaced over the session) returned HTTP 522 from
             qusma.com. https://www.quantifiedstrategies.com/internal-bar-strength/ returned only a bot-check page
             ("Verifying that you are not a robot..."). web.archive.org is not fetchable from this tool.
retrieved:   2026-10-16
note:        Secondary, NOT evidence: a WebSearch result list for qusma.com shows the posts exist (titles "Closing Price in
             Relation to the Day's Range, and Equity Index Mean Reversion", 2012-11-06; "New Paper: The IBS Effect: Mean
             Reversion in Equity ETFs", 2013-09-11) and the search engine's summary states the formula as
             (close − low)/(high − low) on daily data; arXiv:2306.12434 (Pandey & Joshi 2023) cites Pagonidis 2013 the same
             way. The H = L ⇒ 0.5 convention and "read from the forming daily bar on intraday charts" are implementation
             choices that no source was found to define. Re-run this fetch when qusma.com is up; expected outcome CONFIRMED
             for the ratio, with the H = L rule remaining an undocumented convention.
```

## M2 — QI_RSI2: RSI_2 of close (B1)

```
claim_id:    M2
verdict:     CONFIRMED
source:      https://tradingmarkets.com/analytics/how-does-connorsrsi-compare-to-rsi2-1583255  (Matt Radtke, TradingMarkets,
             2014-01-02 — TradingMarkets/Connors Research is Connors' own publisher)
source_tier: 4
version:     web page as retrieved
quote:       "...replacing the 2-period Wilder's RSI, or RSI(2), with ConnorsRSI"; "Both ConnorsRSI and Wilder's RSI are
             oscillators whose values vary between 0 and 100."
retrieved:   2026-10-16
note:        Connors' RSI(2) is the 2-period Wilder RSI (on closes, as used throughout the publisher's material). With B1
             confirmed, "RSI_2 of close" is the published object. The book *Short Term Trading Strategies That Work* (2008)
             itself was not retrievable; its chapter list (secondary) includes "The 2-Period RSI". NT edge case for n = 2:
             @RSI.cs line 72-73 sets Avg[0] = 50 on bar 0 when Period < 3; Default starts on bar 1.
```

## M3 — QI_ConnorsRSI

```
claim_id:    M3
verdict:     REFUTED
source:      https://www.tradingmarkets.com/media/2012/CRHS.pdf  ("ConnorsRSI® Indicator for thinkorswim charts", The Connors
             Group / TradingMarkets, PDF metadata author Tyler Levinsky, 2013-03-08; 3 pages; saved locally as
             C:\Users\rajib\Downloads\egv-channel-a-tmp\CRHS.pdf, text extracted with the PDF tool)
source_tier: 4 (publisher's own reference implementation)
version:     2012/2013 publisher document
quote:       page 2, verbatim:
             input Price_RSI_Period = 3;
             input Streak_RSI_Period = 2;
             input Rank_Lookback = 100;
             # Component 1: the RSI of closing price
             def priceRSI = RSIWilder("price" = close, "length" = Price_RSI_Period);
             # Component 2: the RSI of the streak
             def upDay = if Close > Close[1] then 1 else 0;
             def downDay = if Close < Close[1] then -1 else 0;
             def upStreak = if upDay != 0 then upStreak[1] + upDay else 0;
             def downStreak = if downDay != 0 then downStreak[1] + downDay else 0;
             def streak = upStreak + downStreak;
             def streakRSI = RSIWilder("price" = streak, "length" = Streak_RSI_Period);
             # Component 3: The percent rank of the current return
             def ROC1 = Close/Close[1] - 1;
             def rank = fold i = 1 to Rank_Lookback+1 with r = 0 do r + (getValue(ROC1,i,Rank_Lookback) < ROC1) ;
             def pctRank = (rank / Rank_Lookback) * 100 ;
             plot ConnorsRSI = (priceRSI + streakRSI + pctRank) / 3;
retrieved:   2026-10-16
source_2:    https://tradingmarkets.com/introducing-connorsrsi-the-1st-quantified-oscillator-for-traders  (tier 4)
quote_2:     "ConnorsRSI is a composite indicator consisting of three components"; two use Wilder's RSI; the third "ranks the
             most recent price change on a scale of 0 to 100"; default label "ConnorsRSI(3,2,100)" (compare page).
note:        Two deviations from the published definition:
             (1) PRICE RSI PERIOD: published = 3 (Price_RSI_Period = 3, i.e. ConnorsRSI(3,2,100)); ledger F uses RSI_2(close).
                 Published formula: CRSI = ( RSI_3(close) + RSI_2(streak) + PercentRank_100(ROC_1) ) / 3.
             (2) STREAK TIE RULE: published — an unchanged close (Close == Close[1]) makes upDay = 0 AND downDay = 0, so both
                 upStreak and downStreak are reset to 0 and streak = 0; the next up/down close starts a new streak at ±1.
                 Ledger F: "unchanged close keeps counts" — this is NOT the published rule.
             Confirmed parts: streak sign convention (+ for consecutive higher closes, − for lower); ROC_1 = C/C[1] − 1;
             PercentRank = (count of the previous 100 one-bar ROCs strictly less than the current ROC)/100·100 (the `<`
             in the fold is strict, matching the ledger's "strictly-less"); equal-weight mean of the three. The ledger's
             "value 50 until bar 100" is a warm-up convention not present in the published code (thinkScript simply has
             no value until 100 prior ROCs exist).
             Orchestrator decision needed: change price-RSI period 2→3 and reset the streak on unchanged closes, OR document
             the module as a variant "CRSI(2,2,100) with tie-preserving streak" and not call it ConnorsRSI.
```

## M4 — QI_StochFade: %K, %D of StochasticsFast(3, 14)

```
claim_id:    M4
verdict:     CONFIRMED (as the NT definition, which is what the ledger names; Lane's own article not retrievable)
source:      @StochasticsFast.cs lines 39-40, 51-65, 95 (see B8) and
             https://static.ninjatrader.com/support/helpGuides/nt8/stochastics_fast.htm
source_tier: 2 / 1
version:     NinjaTrader 8.1.8.3
quote:       "StochasticsFast(int periodD, int periodK)"; line 63: K[0] = ... Math.Min(100, Math.Max(0, 100 * nom[0] / den[0]));
             line 65: D[0] = smaK[0];  with smaK = SMA(K, PeriodD) (line 53)
retrieved:   2026-10-16
note:        Identical to B8. Lane, "Lane's Stochastics", Technical Analysis of Stocks & Commodities, May/June 1984 pp. 87-90,
             could not be retrieved (no open copy); secondary descriptions (not evidence) agree that %K = 100·(C − LL)/(HH − LL)
             and %D = 3-period SMA of %K, and that Lane's original used a 5-bar %K, not 14 — the 14/3 setting is a platform
             default, not Lane's. Note the HH == LL carry-forward edge case from B8.
```

## M5 — QI_RVZScore

```
claim_id:    M5
verdict:     UNVERIFIABLE
source:      WebSearch for "DthetaSpike" OR "DeltaInvariantVol" (2026-10-16): no result mentions either name.
source_tier: none
version:     n/a
quote:       n/a — no primary source exists for the named construct.
retrieved:   2026-10-16
note:        The ledger already expects this. The z-score arithmetic itself, z = (x − mean_20)/popstd_20, is a textbook
             definition; the specific choice of ATR14 as the input, a 20-bar window and population std is the module's, not a
             publication's. Per the ledger's rule this module can at most reach "(b) accepted, definition not backed".
```

## M6 — QI_CompositeVol

```
claim_id:    M6
verdict:     UNVERIFIABLE
source:      none (ledger itself cites "v5_zscore framework", unpublished)
source_tier: none
version:     n/a
quote:       n/a
retrieved:   2026-10-16
note:        Weights 0.40/0.35/0.25 and the (vov − 0.15)/0.10 normalisation have no external definition. Sub-blocks (SMA20,
             popstd20, ATR14) are B3/B5/B4 and are confirmed. "(b) accepted, definition not backed" at best.
```

## M7 — QI_TurnOfMonth: flag = 1 if calendar day ≥ DaysInMonth−3 or ≤ 3

```
claim_id:    M7
verdict:     UNVERIFIABLE  (strong deviation flagged; see note)
source:      Hensel & Ziemba, "Investment Results from Exploiting Turn-of-the-Month Effects", *The Journal of Portfolio
             Management* 22(3):17-23, 1996, DOI 10.3905/jpm.1996.409556 (Crossref record retrieved; NOTE the venue is JPM,
             not FAJ — a CFA Digest summary of it exists at DOI 10.2469/dig.v27.n2.66). Landing page
             https://pm-research.com/content/iijpormgmt/22/3/17 redirects to a login (idp.sams-sigma.com); tandfonline 403.
             Lakonishok & Smidt, "Are Seasonal Anomalies Real? A Ninety-Year Perspective", *Review of Financial Studies*
             1(4):403-425, 1988, DOI 10.1093/rfs/1.4.403 — abstract retrieved from https://academic.oup.com/rfs/article-abstract/1/4/403/1573754
             and OpenAlex; full text paywalled.
source_tier: 4 (abstract only)
version:     1988 / 1996
quote:       L&S abstract (OUP page): "persistently anomalous returns around the turn of the week, around the turn of the month"
             — the abstract does not state which days constitute the turn of the month. H&Z abstract: not retrievable
             (Crossref/OpenAlex records carry no abstract; OpenAlex's abstract field is mis-linked to an unrelated tobacco paper).
retrieved:   2026-10-16
note:        No primary text defining the window was retrievable, so the verdict is UNVERIFIABLE by the §7 rule. However the
             ledger's own stated source definition ("last trading day through first 3 trading days") and every retrievable
             description of both papers (Quantpedia, Kunkel & Compton 1998, Chen/Shin/Sun — secondary, not evidence) define
             the window in TRADING days (L&S: −1 through +3; H&Z: −1 through +4). The ledger's F is in CALENDAR days and is a
             −4..+3 window (day ≥ DaysInMonth−3 covers the last FOUR calendar days; day ≤ 3 the first three). Three concrete
             differences for the orchestrator: (i) calendar vs trading days (weekends/holidays shift the set of flagged bars);
             (ii) the published windows start at the LAST trading day (−1), the module starts 4 calendar days before month-end;
             (iii) H&Z's window ends at +4, L&S's at +3 — the module matches neither exactly. If the orchestrator obtains
             either paper, expect REFUTED on (i)-(ii).
```

## M8 — QI_ConsecDays: signed count of consecutive higher/lower closes; unchanged close keeps counts

```
claim_id:    M8
verdict:     UNVERIFIABLE  (concept confirmed by the publisher; tie rule undefined in any retrievable source)
source:      https://tradingmarkets.com/recent/if_a_stock_drops_5_days_in_a_row_should_you_buy_it-674228
             (Larry Connors, TradingMarkets, 2007-01-26)
source_tier: 4
version:     web page as retrieved
quote:       "closed down exactly three consecutive days" (through seven); "We looked at over seven million trades from 1/1/95
             to 6/30/06"; "stocks that make 5+ Consecutive Down Days that are trading above their 200-day MA (bullish)".
             The article "does not address how flat closes (equal to the prior close) are treated."
retrieved:   2026-10-16
note:        *Short Term Trading Strategies That Work* (2008) was not retrievable; the Connors article confirms the published
             object is a count of consecutive lower (or higher) closes. The ledger's "unchanged close keeps counts" is not
             defined by any retrievable primary; the only Connors-published tie rule found (ConnorsRSI streak, M3 quote) RESETS
             on an unchanged close, which is evidence (from a different Connors product) that the module's tie rule is not
             Connors' convention. Orchestrator: either document the tie rule as a module convention or align with the
             ConnorsRSI reset rule.
```

## M9 — QI_OvernightGap: gap% = (O[0] − C[1])/C[1]·100

```
claim_id:    M9
verdict:     UNVERIFIABLE
source:      cited "MDPI 2025" paper — not located (two WebSearch passes incl. site:mdpi.com returned no MDPI paper).
source_tier: none retrieved
version:     n/a
quote:       n/a
retrieved:   2026-10-16
note:        The formula is the ordinary simple return from prior close to open; no primary source was retrieved that defines
             "overnight gap" (secondary trading-platform pages agree with it — not evidence). The ledger should either drop the
             MDPI citation or supply the DOI so it can be checked.
```

## M10 — QI_BollingerPctB: %B_here = (C − middle)/(half bandwidth)·100

```
claim_id:    M10
verdict:     REFUTED
source:      https://www.bollingerbands.com/bollinger-band-rules  (John Bollinger, "Bollinger Bands Rules", rule 15) and
             https://www.bollingerbands.com/bollinger-bands
source_tier: 4 (author's own site)
version:     web pages as retrieved
quote:       Rule 15: "%b tells us where we are in relation to the Bollinger Bands."; "The position within the bands is
             calculated using an adaptation of the formula for Stochastics". Rule 17: "Indicators can be normalized with %b,
             eliminating fixed thresholds in the process." bollinger-bands page: "I created %b, an indicator that depicted where
             price was in relation to the bands".
retrieved:   2026-10-16
note:        Bollinger's site states the construction (Stochastics form) rather than writing the algebra; the Stochastics
             formula is (C − LL)/(HH − LL) (B8, @StochasticsFast.cs line 60-63), so the published %b is
             %b = (C − lowerBB)/(upperBB − lowerBB), ranging 0 at the lower band, 0.5 at the middle, 1 at the upper band
             (the book *Bollinger on Bollinger Bands*, 2001, ch. 12, writes it this way; book not retrieved). The ledger's
             %B_here = (C − middle)/(numStdDev·σ)·100 = 200·%b − 100: −100 at the lower band, 0 at the middle, +100 at the
             upper. Same information, different affine scale and different thresholds (published 0/1 ⇔ module −100/+100;
             published 0.5 ⇔ module 0). REFUTED as "the published definition"; the orchestrator can either rescale to %b or
             document the module output as "%B (centred, ×100)" — but it should not be labelled Bollinger's %b as-is.
```

## M11 — QI_TurnaroundTuesday: day-of-week flag, Monday shaded

```
claim_id:    M11
verdict:     UNVERIFIABLE
source:      French, K. R., "Stock returns and the weekend effect", *Journal of Financial Economics* 8(1):55-69, March 1980
             (Crossref + RePEc + OpenAlex records retrieved: title/author/venue confirmed; "No abstract is available for this
             item" on RePEc; abstract_inverted_index null on OpenAlex; sciencedirect.com 403; Semantic Scholar 429).
source_tier: 4 (bibliographic record only)
version:     1980
quote:       none retrievable.
retrieved:   2026-10-16
note:        Even without the text, the claim as written is a category error the ledger already flags: French tests whether
             mean Monday returns are negative (calendar-time vs trading-time hypotheses); he does not define a "day-of-week
             0..6 with Monday shaded" indicator, and "Turnaround Tuesday" is not French's term. The day-of-week computation
             itself is deterministic calendar arithmetic (US Central conversion is a module choice). Recommend re-labelling
             the source as "motivation" rather than "definition".
```

## M12 — QI_RSI14: RSI_14 of close (B1)

```
claim_id:    M12
verdict:     CONFIRMED  (via NT help + source; Wilder's book not independently retrieved)
source:      https://static.ninjatrader.com/support/helpGuides/nt8/relative_strength_index_rsi.htm  (tier 1);
             @RSI.cs line 39 (tier 2)
source_tier: 1 / 2
version:     NinjaTrader 8.1.8.3
quote:       help: RSI "created by J. Welles Wilder and introduced in his 1978 book"; "exponential moving average with a
             smoothing constant (k = 1/ Period)". @RSI.cs line 39: Period = 14;
retrieved:   2026-10-16
note:        B1 confirmed ⇒ RSI_14 of close is Wilder's RSI at Wilder's canonical length (NT's default 14 and the help page's
             attribution are the evidence; archive.org's copy of Wilder 1978 is lending-only — 401 on the text file — so no
             verbatim book quote). If the orchestrator wants a book-level quote this downgrades to UNVERIFIABLE-against-Wilder,
             CONFIRMED-against-NT.
```

## M13 — QI_VRPProxy: ATR5/ATR14

```
claim_id:    M13
verdict:     UNVERIFIABLE
source:      none ("DeltaInvariantVol" — WebSearch returns nothing; ledger itself says proxy, not VRP)
source_tier: none
version:     n/a
quote:       n/a
retrieved:   2026-10-16
note:        The variance risk premium proper is implied minus realised variance; an ATR ratio is a short/long realised-range
             ratio with no published definition. "(b) accepted, definition not backed" at best; the name "VRP" is misleading
             and should be documented as a proxy.
```

## M14 — QI_WideRangeBar: (H − L)/ATR14

```
claim_id:    M14
verdict:     UNVERIFIABLE
source:      Crabel, T., *Day Trading with Short Term Price Patterns and Opening Range Breakout*, Traders Press, 1990 — no
             open copy (not on archive.org per search; used copies listed at $600-$2000).
source_tier: 4 (not retrieved)
version:     1990
quote:       none retrievable.
retrieved:   2026-10-16
note:        Secondary, NOT evidence (oxfordstrat.com "wide range pattern"): Crabel's WR_N is "the widest high-to-low range
             over N days, measured against the N-day periods within the prior 20 market days" — i.e. a rank of today's range
             against prior ranges, not a multiple of ATR. If that description is accurate, the ledger's (H−L)/ATR14 is a
             different statistic and the Crabel citation would be REFUTED-as-cited; without the book the verdict stays
             UNVERIFIABLE, as the ledger anticipated ("Crabel's WR definition is range vs prior ranges, not ATR multiple").
             The ATR14 denominator is B4 (confirmed).
```

---

## Retrieval log (what was tried and failed, so nobody re-does it)

- ninjatrader.com/support/helpGuides/nt8/{rsi,ema,sma,atr,macd,bollinger,adx}.htm → 301 to static.ninjatrader.com → 404.
  Real pages (from indicators.htm): relative_strength_index_rsi.htm, moving_average_-_exponential_e.htm,
  moving_average_-_simple_sma.htm, average_true_range_atr.htm, standard_deviation_stddev.htm,
  moving_average_convergence-divergence_macd.htm, bollinger_bands.htm, stochastics_fast.htm, average_directional_index_adx.htm,
  choppiness_index.htm (not audited here), order_flow_vwap2.htm (no plain VWAP page exists).
- qusma.com: HTTP 522 on every attempt (×5 over the session). web.archive.org: not fetchable from this tool.
- quantifiedstrategies.com: bot-check page only.
- archive.org newconceptsintec00wild (Wilder 1978): access-restricted; djvu.txt → 401. dspace.lib.uom.gr scan: Anubis bot wall.
- sciencedirect (French 1980): 403; Semantic Scholar: 429; RePEc/Crossref/OpenAlex: no abstract.
- tandfonline (CFA Digest of H&Z): 403; pm-research.com (JPM original): login redirect. OUP RFS (L&S 1988): abstract only.
- tradingmarkets.com/connorsrsi/ category page: empty; the formula lives only in the publisher's thinkScript PDF
  (/media/2012/CRHS.pdf) and the gated "An Introduction to ConnorsRSI" guidebook (not retrieved; a mirror of the related
  2012 "ConnorsRSI Pullbacks Guidebook" exists on c.mql5.com but is a third-party rehost and was not used).
- Crabel 1990, Lane 1984, Connors & Alvarez 2008, Appel: no open primary copy found.
