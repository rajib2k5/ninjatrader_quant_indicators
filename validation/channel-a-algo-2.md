# Channel A (documentation audit) — algo-claims-ledger.md, definition halves (a) of M15–M27

auditor:   Channel A, second algorithm pass (no code executed; no channel-b*.md read)
ledger:    validation/algo-claims-ledger.md (FROZEN 2026-10-16)
retrieved: 2026-10-16 (all web and file evidence below)
scope:     claim (a) only — "formula F stated in the ledger is the published/official definition from source S".
           Claim (b) (does the compiled module compute F) is Channel B's and is N/A-by-construction here.

## Version pin and source tiers used

- NinjaTrader 8.1.8.3 (validation/env-pin.txt). Installed shipped sources read at
  `C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@*.cs` (tier 2; header "Copyright (C) 2026, NinjaTrader LLC").
- NinjaTrader 8 help guide (tier 1). Note for the ledger: `ninjatrader.com/support/helpGuides/nt8/*` now 301-redirects to
  `static.ninjatrader.com/...`, and the slugs the ledger cites do not exist: `vwap.htm`, `adx.htm`, `atr.htm` → 404.
  The live slugs are `order_flow_vwap.htm`, `average_directional_index_adx.htm`, `average_true_range_atr.htm`,
  `choppiness_index.htm`, `moving_average_convergence-divergence_macd.htm`, `moving_average_-_exponential_e.htm`,
  `moving_average_-_simple_sma.htm`, `volume.htm`. The help guide is unversioned (no 8.1.x selector); treated as current.
- NinjaTrader installed trading-hours templates (tier 2, installed artifact):
  `C:\Users\rajib\Documents\NinjaTrader 8\templates\TradingHours\CME US Index Futures RTH.xml` (Version 5120) and
  `...\CME US Index Futures ETH.xml` (Version 5119).
- CME Group E-mini S&P 500 contract specifications page (tier 1, official exchange page; read via the in-app browser
  because WebFetch timed out on cmegroup.com). CME Submission 20-018 to the CFTC (tier 1, exchange rule filing hosted at cftc.gov).
- Basu & Miffre (2013), J. Banking & Finance 37(7) 2652–2664, DOI 10.1016/j.jbankfin.2013.02.031: full text is paywalled
  (Elsevier; EDHEC working-paper PDF behind registration). Only the abstract was retrievable from the authors' institution page
  (tier 4, primary abstract). Two later peer-reviewed papers that restate the measure are quoted as SECONDARY corroboration only.
- NOT retrievable, therefore inadmissible for a CONFIRMED/REFUTED verdict: Dreiss's original Choppiness Index text
  (edwards-magee.com/ggu/dreisscaos.pdf → 404; no publisher copy found), Connors & Raschke *Street Smarts* (1995/1996, no
  primary text online), Crabel (1990, no primary text online), Wyckoff course (1931/1937, no primary scan found), JPX Tokyo
  trading-hours page (HTTP 403 on two URLs). Blog/vendor pages found for these (LuxAlgo, TradingView, Wealth-Lab,
  TrendSpider, Oxfordstrat, MQL5, Investopedia-style) are secondary and are cited below only as "secondary, not evidence".

Saved copies of the three PDFs read: `C:\Users\rajib\Downloads\egv_channel_a_sources\` (mpra_80555.pdf, city_jfm_2019.pdf,
cftc_cme_rule_092420.pdf).

## Tally

| verdict | claims |
|---|---|
| CONFIRMED | M17, M18, M19, M23 (CHOP formula; its 2-of-3 regime flag is unbacked — see record) |
| REFUTED | M15, M16 |
| UNVERIFIABLE | M20, M21, M22, M24, M25, M26, M27 (M27 has confirmed sub-parts; see record) |

---

## M15 — QI_HedgingPressure (a)

```
claim_id:    M15 (a)
verdict:     REFUTED
source:      https://climateinstitute.edhec.edu/publications/capturing-risk-premium-commodity-futures-role-hedging-pressure
             (authors' institutional page for Basu & Miffre 2013, JBF 37:2652–2664; abstract only — PDF requires registration)
source_tier: 4 (original paper; abstract retrieved, body paywalled)
version:     JBF 37(7), 2013; EDHEC working paper dated 01/02/2012
quote:       "It considers single sorts based on the open interests of either hedgers or speculators, as well as double sorts
             based on both positions."
retrieved:   2026-10-16
note:        Basu & Miffre's hedging pressure is a POSITIONING measure built from hedgers'/speculators' open interest (CFTC
             Commitments of Traders categories). The code (QI_HedgingPressure.cs lines 149–186) uses no positioning data at
             all: basisScore = clamp((Close−SMA20)/ATR14·−25), termScore = clamp((ΔSMA5−ΔSMA20)/ATR14·−50), a volume/price
             divergence term and a range-compression term, each ±25, sum ±100. That is a price/volume heuristic, not the
             paper's measure. The module header itself calls it "A four-component proxy for hedger positioning built only
             from price and volume".
```

Secondary corroboration of the published definition (NOT evidence under the source hierarchy, recorded so the reader can
see the exact form of the measure the code is being compared against):

- Fan, Fernandez-Perez, Fuertes & Miffre (2020), "Speculative Pressure", *J. Futures Markets* 40(4), accepted MS at
  https://openaccess.city.ac.uk/23283/1/FINAL_JFM__Accepted_27Nov2019_SSRN.pdf, p. 19 (§5.1): "we obtain from the
  Futures-Only COT report the weekly long (L_i,w) and short (S_i,w) positions of large commercial traders (also called
  hedgers) to measure for each contract a standardized hedging pressure signal ... HS_i,t ≡ (1/52) Σ_{w=1}^{52}
  (S_i,w − L_i,w)/(L_i,w + S_i,w)". Same paper p. 6 fn 5 cites "Basu and Miffre (2013)" among papers documenting "A
  positive relation between the net short (long) positions of hedgers (speculators) and commodity futures returns".
- Chong, Tsui & Chan (2017), MPRA 80555, p. 12: "Reportable traders are further classified into commercial and
  non-commercial traders, also known as hedgers and speculators ... Based on the findings of Basu and Miffre (2013) ...
  Speculators' hedging pressure is defined as the number of speculators' long open interest divided by the total number
  of speculators' open interest."

Precise published definition (from the retrieved abstract plus the two restatements): hedging pressure of a trader group
= (long − short) or long/(long+short) open interest of that CFTC COT category (commercial = hedgers, non-commercial =
speculators), per contract, per report week. No price, moving-average, ATR, volume or range term appears in it. The ledger
column "A: REFUTED-as-cited or UNVERIFIABLE" resolves to REFUTED-as-cited: the name and citation are attached to a formula
the source does not define.

---

## M16 — QI_VWAPDistance (a)

```
claim_id:    M16 (a)
verdict:     REFUTED
source:      https://cftc.gov/filings/orgrules/rule092420cmedcm001.pdf  (CME Submission No. 20-018, Exhibit B,
             "CME S&P 500, E-Mini S&P 500, Micro E-mini S&P 500 Futures Daily Settlement Procedure")
source_tier: 1 (exchange rule filing; CME's own operational definition of VWAP)
version:     filed 2020-09-22, effective trade date 2020-10-26
quote:       "The volume-weighted average price ("VWAP") of all trades executed in the full-sized futures contract on the
             trading floor and in the E-mini futures contract executed on CME Globex will be calculated"
retrieved:   2026-10-16
note:        CME's VWAP is over TRADES (each trade's price weighted by its quantity). The code weights the BAR typical price
             (H+L+C)/3 by bar volume (QI_VWAPDistance.cs lines 147–151). That is an approximation of the exchange quantity,
             not its definition.
```

```
claim_id:    M16 (a) — second record, NinjaTrader's VWAP (the ledger cites "NT help vwap.htm"; that slug is 404)
verdict:     REFUTED (reset rule and price input differ)
source:      https://static.ninjatrader.com/support/helpGuides/nt8/order_flow_vwap.htm
source_tier: 1
version:     NT8 help guide (current), for 8.1.8.3
quote:       "A total of the dollars traded for every transaction (price multiplied by number of shares traded)"
             Reset Interval "Session": "Resets VWAP calculations every session"; Resolution "Tick" runs "on a 1-tick time
             frame of the input series".
retrieved:   2026-10-16
note:        NT's VWAP: (i) per transaction (or per bar of the input series in Standard resolution — the page names no
             typical-price formula), (ii) resets per SESSION as defined by the chart's Trading Hours template (or week/month).
             The code resets when Time[0].DayOfYear changes (lines 139–145): a calendar-day reset in the chart's time zone,
             not a session reset — for ES the Globex session starts 17:00 CT the previous calendar day, so the code's "session"
             splits the exchange session at midnight. The module header documents this ("the 'session' is the calendar day
             of the bar timestamp"). Note also that no `@VWAP.cs` / `@OrderFlowVWAP.cs` source ships in bin\Custom\Indicators
             (Order Flow+ indicators are compiled-only), so the NT help page is the only NT artifact available.
```

Precise published definition: VWAP = Σ(trade price × trade quantity) / Σ(trade quantity) over the session (CME: the
settlement window; NT: the Trading Hours session). The code's Σ((H+L+C)/3 · bar volume)/Σ(bar volume) over a calendar
day matches neither the price input nor the reset boundary. (dist = (C − VWAP)/ATR14 is the module's own normalisation;
no source claims it and none is needed.)

---

## M17 — QI_MACDHistogram (a)

```
claim_id:    M17 (a)
verdict:     CONFIRMED
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@MACD.cs  (lines 37–40, 55–60, 83–92)
source_tier: 2 (installed NinjaTrader source, 8.1.8.3)
version:     NinjaTrader 8.1.8.3 shipped source
quote:       "Fast = 12; ... Slow = 26; Smooth = 9;" / "constant1 = 2.0 / (1 + Fast);" /
             "double macd = fastEma0 - slowEma0; double macdAvg = constant5 * macd + constant6 * Avg[1];" /
             "Diff[0] = macd - macdAvg;"
retrieved:   2026-10-16
note:        The ledger's F = MACD(12,26,9).Diff with Diff = line − signal is exactly what NT computes. Help page
             (static.ninjatrader.com/support/helpGuides/nt8/moving_average_convergence-divergence_macd.htm, retrieved
             2026-10-16) corroborates the parameters: fast "The number of bars to calculate the fast EMA", slow "The numbers
             of bars to calculate the slow EMA", smooth "The number of bars to calculate the EMA signal line", ".Diff —
             Returns difference value". The Appel attribution in the ledger is NOT supported by the NT page (it credits
             "Courtesy of StockCharts" only) and Appel's own text was not retrieved; the attribution is unverified, the
             formula is confirmed.
```

---

## M18 — QI_EMACross (a)

```
claim_id:    M18 (a)
verdict:     CONFIRMED
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@EMA.cs  (lines 37–38, 42)
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source
quote:       "constant1 = 2.0 / (1 + Period); constant2 = 1 - 2.0 / (1 + Period);" /
             "Value[0] = CurrentBar == 0 ? Input[0] : Input[0] * constant1 + constant2 * Value[1];"
retrieved:   2026-10-16
note:        EMA_n[0] = EMA_n[1] + 2/(n+1)·(x[0] − EMA_n[1]) as the ledger states (B2), seeded with the first input.
             Spread = EMA20 − EMA50 is plain arithmetic on two EMAs; "standard" names no publication and none is required.
             Help page moving_average_-_exponential_e.htm (retrieved 2026-10-16) gives prose only: "In the exponential moving
             average equation the most recent market action is assigned greater importance".
```

---

## M19 — QI_SMA200Trend (a)

```
claim_id:    M19 (a)
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/moving_average_-_simple_sma.htm ; corroborated by
             C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@SMA.cs lines 61–62
source_tier: 1 (help) / 2 (source)
version:     NT8 help (current) / 8.1.8.3 source
quote:       help: "The Simple Moving Average is calculated by summing the closing prices of the security for a period of
             time and then dividing this total by the number of time periods."
             source: "sum = priorSum + Input[0] - (CurrentBar >= Period ? Input[Period] : 0); Value[0] = sum /
             (CurrentBar < Period ? CurrentBar + 1 : Period);"
retrieved:   2026-10-16
note:        SMA_n = mean of last n values; before bar n−1 NT averages the available bars (the module header says the same).
             Distance = C − SMA200 is arithmetic; no publication claimed or needed.
```

---

## M20 — QI_ATRRegime (a)

```
claim_id:    M20 (a)
verdict:     UNVERIFIABLE
source:      none admissible. Searched for a primary definition of "ATR regime = ATR14 / SMA50(ATR14)"; only vendor/blog
             material exists (the ledger's "LuxAlgo" is a vendor site — secondary, not evidence).
source_tier: —
version:     —
quote:       (none — no primary source defines the ratio)
retrieved:   2026-10-16
note:        The two building blocks are documented: ATR per @ATR.cs line 44–45 ("trueRange = Math.Max(Math.Abs(low0 -
             close1), Math.Max(high0 - low0, Math.Abs(high0 - close1))); Value[0] = ((Math.Min(CurrentBar + 1, Period) - 1)
             * Value[1] + trueRange) / Math.Min(CurrentBar + 1, Period);") and the help page average_true_range_atr.htm
             ("The original Wilder formula for an exponential moving average with a smoothing constant (k = 1/ Period) is used
             to calculate the ATR."), SMA per M19. The ratio of the two, the 50-bar window and the 1.5 threshold are a
             practitioner heuristic with no authoritative definition. Honest status: "(b) at most accepted, definition not
             backed".
```

---

## M21 — QI_VolumeSpike (a)

```
claim_id:    M21 (a)
verdict:     UNVERIFIABLE
source:      https://static.ninjatrader.com/support/helpGuides/nt8/volume.htm (checked for a relative-volume definition)
source_tier: 1
version:     NT8 help (current)
quote:       "Volume is simply the number of shares (or contracts) traded during a specified time frame"
retrieved:   2026-10-16
note:        The page (and NT's VOLMA page it links to) defines volume and a volume moving average but no "relative volume"
             or "volume spike" ratio; no exchange/regulator/paper defines Vol/SMA20(Vol) as a named quantity. The arithmetic
             (SMA over Volume, M19 record) is trivially verifiable, but the ledger's source S is "standard relative-volume
             definition", and no primary document states it. Verdict follows the rule that absence of documentation is
             absence of evidence; this is a convention, not a published definition.
```

---

## M22 — QI_VolumeDelta (a)

```
claim_id:    M22 (a)
verdict:     UNVERIFIABLE (as "volume delta")
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@BuySellVolume.cs lines 51–58 (NT's own
             buy/sell volume definition, for contrast); @VolumeUpDown.cs lines 43–52
source_tier: 2
version:     NinjaTrader 8.1.8.3 shipped source
quote:       @BuySellVolume.cs: "OnMarketData(MarketDataEventArgs e) ... if(e.Price >= e.Ask) buys += ... e.Volume; else if
             (e.Price <= e.Bid) sells += ... e.Volume;"
             @VolumeUpDown.cs: "if (Close[0] >= Open[0]) { UpVolume[0] = ... Volume[0]; DownVolume.Reset(); } else {
             UpVolume.Reset(); DownVolume[0] = ... Volume[0]; }"
retrieved:   2026-10-16
note:        NinjaTrader's shipped notion of buy/sell volume is tick-level, classified against the bid/ask; its bar-level
             up/down volume classifies on Close vs OPEN of the same bar. The code (QI_VolumeDelta.cs lines 122–133) signs the
             whole bar's volume by Close vs PRIOR close (+Vol if C > C[1], −Vol if C < C[1], 0 if unchanged) — a third
             convention that matches neither NT definition and has no primary source. The ledger already labels it a proxy.
             CumDelta20 and SMA10 of the series are arithmetic. Verdict: no authoritative definition of "volume delta" equals
             F; the name is borrowed. (Not REFUTED because the ledger does not cite a specific source S that defines it
             differently; it cites "practitioner proxy".)
```

---

## M23 — QI_ChopIndex (a)

```
claim_id:    M23 (a)
verdict:     CONFIRMED (Choppiness Index formula); the 2-of-3 regime flag has no published definition (see note)
source:      C:\Users\rajib\Documents\NinjaTrader 8\bin\Custom\Indicators\@ChoppinessIndex.cs line 32; help
             https://static.ninjatrader.com/support/helpGuides/nt8/choppiness_index.htm
source_tier: 2 (source) / 1 (help)
version:     NinjaTrader 8.1.8.3 shipped source; NT8 help (current)
quote:       source: "Value[0] = (MAX(High, Period)[0] - MIN(Low, Period)[0]).ApproxCompare(0) == 0 || SUM(ATR(1),
             Period)[0].ApproxCompare(0) == 0 ? 0 : 100 * Math.Log10(SUM(ATR(1), Period)[0] / (MAX(High, Period)[0] -
             MIN(Low, Period)[0])) / Math.Log10(Period);"
             help: "The Choppiness Index is designed to determine if the market is choppy (trading sideways) or not choppy"
retrieved:   2026-10-16
note:        CHOP_n = 100·log10(Σ_n TR / (HH_n − LL_n)) / log10(n) with TR = ATR(1) (= true range per @ATR.cs line 44) is
             exactly the ledger's F. Differences the reader should know, all outside the formula proper: (1) NT returns 0
             (not 50) when HH = LL or ΣTR = 0 and has no 0..100 clamp; the code returns 50 for bar < 14 and clamps. (2) NT
             ships reference lines at 38.2 ("Strong") and 62.8 ("Choppy") — line 27–28 "AddLine(Brushes.DarkCyan, 38.2 ...);
             AddLine(Brushes.DarkCyan, 62.8 ...)" — i.e. NT's upper line is 62.8, not the 61.8 the code hard-codes; neither
             number is in the NT help text, and Dreiss's original (the ledger's "Dreiss 1993") could not be retrieved
             (edwards-magee.com/ggu/dreisscaos.pdf → 404; no publisher copy; TradingView/Wealth-Lab/TrendSpider restatements
             are secondary, not evidence), so the formula's attribution to Dreiss is unverified while the formula itself is
             confirmed against NT. (3) The regime flag count{CHOP > 61.8, ADX14 < 20, Vol < 0.7·SMA20(Vol)} is a heuristic:
             the only support for "ADX < 20" is NT's source comment in @ADX.cs lines 17–18 "A low ADX value (generally less
             than 20) can indicate a non-trending market with low volumes", which is guidance, not a definition; the 0.7
             volume ratio has no source. ADX itself: @ADX.cs lines 75–102 implement Wilder's smoothed DM/TR and
             "Value[0] = ... ((Period - 1) * Value[1] + 100 * diff / sum) / Period" (seeded at 50), consistent with the
             ledger's B9; help page average_directional_index_adx.htm gives prose only ("An indicator used in technical
             analysis as an objective value for the strength of trend.").
```

---

## M24 — QI_LiquiditySweep (a)

```
claim_id:    M24 (a)
verdict:     UNVERIFIABLE
source:      none admissible. Connors & Raschke, Street Smarts (Gordon Publishing, 1995/1996): no primary text retrievable
             (archive.org/library search returned catalog entries only). Wyckoff course (1931/1937): no primary scan found;
             the only archive.org Wyckoff scan is the 1925 "How I Trade and Invest in Stocks and Bonds", a different work.
             SFP, "equal-level trap", "consolidation breakout trap", "volume-divergence fakeout": no primary source exists.
source_tier: —
version:     —
quote:       (none — no admissible source retrieved; secondary restatements of Turtle Soup at luxalgo.com and
             tradingview.com are "secondary, not evidence" and they also disagree with each other — four sessions vs an
             MQL5 article's three days — on the prior-low age rule)
retrieved:   2026-10-16
note:        Even taking the secondary descriptions at face value, the code's CheckTurtleSoup (lines 664–672) is not the
             book's rule set as those sources describe it: the code fires on any bar whose High exceeds the 20-bar Donchian
             high (or Low below the low) and closes/opens back inside, with no "prior extreme at least N days old"
             requirement, no entry-stop placement and no next-day variant; confidence 0.55 is the author's number. The
             Wyckoff spring/upthrust check (lines 648–662) is a 40-bar range breach with a reversed close — Wyckoff's
             terms are used, but no Wyckoff text was available to test the rule against. Verdict stays UNVERIFIABLE (not
             REFUTED) because no primary definition was retrievable to refute against.
```

---

## M25 — QI_OrderFlowPlus (a)

```
claim_id:    M25 (a)
verdict:     UNVERIFIABLE
source:      none. The five patterns (Delta Divergence 0.78, Absorption 0.65, Exhaustion 0.60, Stacked Delta 0.55, Delta
             Reversal 0.70 — module header lines 15–17) are defined only by the code, on the M22 proxy delta.
source_tier: —
version:     —
quote:       (none)
retrieved:   2026-10-16
note:        The name collides with NinjaTrader's licensed "Order Flow+" suite, whose help chapter
             (static.ninjatrader.com/support/helpGuides/nt8/order_flow_vwap.htm and siblings) defines tick/bid-ask based
             tools; the QI module does not use market-depth or bid/ask data (it is built on the close-to-close delta of M22),
             so NT's Order Flow+ documentation does not define any of its rules. The fixed confidences are the author's.
```

---

## M26 — QI_SMC (a)

```
claim_id:    M26 (a)
verdict:     UNVERIFIABLE
source:      none. "Order Block", "Fair Value Gap", "Break of Structure", "Change of Character", "Displacement" are
             ICT/SMC course terminology; no academic paper, exchange document or platform reference defines them.
source_tier: —
version:     —
quote:       (none)
retrieved:   2026-10-16
note:        The module header fixes its own thresholds (impulse bar = body > 0.75·range AND range > 1.5·ATR14; zones expire
             after 100/50 bars; confidences 0.72/0.68/0.60/0.75/0.58). These are the author's parameters. ICT/SMC course
             material is excluded by the charter as non-primary; nothing else exists. Expected UNVERIFIABLE; confirmed so.
```

---

## M27 — QI_KeyLevels (a)

Overall:

```
claim_id:    M27 (a)
verdict:     UNVERIFIABLE (overall) — with the sub-findings below: Globex hours CONFIRMED; "RTH 08:30–16:00 CT" matches
             NinjaTrader's shipped template but is NOT a CME-published definition (CME's cash-synchronised close is 15:00 CT);
             30-min opening range and "Asian session" have no official definition.
```

Sub-record 1 — CME Globex hours (the 17:00 CT start used by the Asian-session window, and the 16:00 CT end):

```
source:      https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html  (Trading Hours row; read from
             the page DOM in the in-app browser, 2026-10-16 11:05 CT per the page's own timestamp)
source_tier: 1
version:     live page, 2026-10-16
quote:       "CME Globex: Sunday 6:00 p.m. - Friday - 5:00 p.m. ET (5:00 p.m. - 4:00 p.m. CT) with a daily maintenance
             period from 5:00 p.m. - 6:00 p.m. ET (4:00 p.m. - 5:00 p.m. CT)"
retrieved:   2026-10-16
note:        CONFIRMED: the Globex trading day opens 17:00 CT and closes 16:00 CT. The code's Asian window starts at 17:00 CT
             (IsInAsianWindow, line 397) = the Globex open, and its RTH window ends 16:00 CT = the Globex daily close. The
             CME page contains NO "RTH"/"regular trading hours" row for ES at all.
```

Sub-record 2 — "RTH" 08:30–16:00 CT:

```
source:      C:\Users\rajib\Documents\NinjaTrader 8\templates\TradingHours\CME US Index Futures RTH.xml  lines 1700–1739
source_tier: 2 (installed NinjaTrader artifact, Version 5120)
version:     template Version 5120 (shipped with 8.1.8.3 install)
quote:       "<Name>CME US Index Futures RTH</Name> ... <BeginDay>Monday</BeginDay> <BeginTime>830</BeginTime>
             <EndDay>Monday</EndDay> <EndTime>1600</EndTime> ... <TimeZone>Central Standard Time</TimeZone>"
             (identical 830–1600 sessions for Tuesday–Friday; the ETH template, Version 5119, is Sunday 1700 → Monday 1600 etc.)
retrieved:   2026-10-16
note:        The code's RTH window (IsInRthWindow, line 338: t >= 08:30 && t < 16:00, after converting to "Central Standard
             Time") reproduces NinjaTrader's shipped RTH template exactly, including the time-zone id. That is a platform
             convention, not an exchange definition: CME does not publish an RTH for ES (sub-record 1), and CME's own
             "regular" day-end marker is 15:00 CT — CME Submission 20-018 (cftc.gov/filings/orgrules/rule092420cmedcm001.pdf,
             p. 2): "the Exchanges are implementing amendments to change the daily settlement price determination period of
             the Contracts from 3:15 p.m. Central Time (CT) to 3:00 p.m. CT. The amendments will synchronize settlement times
             of the Contracts with the related cash equity market." Exhibit B: VWAP "calculated for the designated lead month
             contract from 14:59:30 to 15:00:00 Central Time ('CT'), the settlement period". So "previous-day RTH high/low"
             as the exchange would frame it ends at 15:00 CT, and the code's 15:00–16:00 CT hour is post-settlement Globex
             trading. The 08:30 CT start coincides with the cash-equity open that CME synchronises to; no CME text states it
             for ES. Ledger wording "CME Globex / RTH session times" is therefore half right: Globex yes, RTH is NT's.
```

Sub-record 3 — 30-minute opening range 08:30–09:00 CT, "Crabel ORB":

```
source:      none admissible. Crabel, Day Trading with Short Term Price Patterns and Opening Range Breakout (Traders Press,
             1990): no primary text retrievable. Secondary descriptions (oxfordstrat.com, x-trader.net — not evidence)
             describe Crabel's ORB as a breakout of the OPEN ± a "stretch", not a 30-minute high/low range.
source_tier: —
quote:       (none)
retrieved:   2026-10-16
note:        The code's ORB (lines 287–346) is the high/low of the first 30 minutes of NT's RTH template. "30 minutes" is a
             practitioner choice (the module's own comment cites "Academic study (2019)" and "Practitioner consensus" without
             a reference). UNVERIFIABLE; the Crabel attribution is at best loose and could not be tested.
```

Sub-record 4 — "Asian session" 17:00–02:00 CT:

```
source:      CME page in sub-record 1 (for the 17:00 CT open only). JPX trading-hours page
             (https://www.jpx.co.jp/english/equities/trading/domestic-stocks/trading-hours/) returned HTTP 403 twice — not
             retrievable.
source_tier: 1 (CME, partial) / —
quote:       CME: "Sunday 6:00 p.m. ... ET (5:00 p.m. ... CT)" (Globex open)
retrieved:   2026-10-16
note:        No exchange or regulator defines an "Asian session" for CME equity index futures; it is an FX-market colloquialism.
             The 17:00 CT start is simply the Globex open (confirmed). The 02:00 CT end is the module's own choice; its
             comment "Globex open through Tokyo close" could not be checked against JPX (403), and in any case 02:00 CST =
             17:00 JST while CDT gives 16:00 JST, so the fixed CST boundary cannot track a Tokyo close across US DST.
             UNVERIFIABLE.
```

---

## Notes for the convergence gate

- M15 and M16 are REFUTED as definitions: the cited sources define the named quantities from different inputs (COT
  positions; per-trade VWAP with session reset). Channel B's arithmetic checks on these modules, if they pass, can only
  reach "(b) accepted, definition refuted-as-cited".
- M17, M18, M19 are CONFIRMED against NinjaTrader's own source/help; the "Appel" and "standard" attributions were not
  independently sourced, but the ledger's F equals NT's definition, which is the claim.
- M23: the Choppiness Index formula is CONFIRMED against NT; NT ships a 62.8 upper line where the code hard-codes 61.8, and
  the regime flag is a heuristic. Dreiss's original text was unreachable.
- M20, M21, M22, M24, M25, M26 are UNVERIFIABLE — proxies/heuristics with no authoritative definition. M27 is UNVERIFIABLE
  overall, with CME Globex hours confirmed and the RTH window traced to NinjaTrader's shipped template rather than CME.
- Ledger hygiene: the NT help slugs cited in the ledger (vwap.htm, adx.htm, atr.htm, choppinessindex.htm) do not resolve;
  correct slugs are listed at the top of this file.
