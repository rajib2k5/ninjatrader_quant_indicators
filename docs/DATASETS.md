# Robustness datasets for the 25-rule backtests

Researched 2026-10-17 (all "retrieved" dates below are 2026-10-17). Web research only: **no dataset
file was downloaded**. This is information, not legal advice. Needed for `backtest/PROTOCOL.md`
section 2 ("online datasets selected in `docs/DATASETS.md` and approved by the user before
download").

## Result at a glance

| Slot | Pick | Account? | Size | Rows | Licence constraint | Status |
|---|---|---|---|---|---|---|
| **R1** (long daily, real OHLCV) | Stooq `SPY.US` daily CSV | none seen | ~0.27 MB (est.) | 5,444 (2005-02-25 to 2026-10-16) | Stooq ToS 5.3: no redistribution. **Do not commit the raw file.** | Page and terms read directly. CSV endpoint not test-fetched (it is a download): may ask for CAPTCHA/API key. |
| **R2** (independent intraday <= 15 min) | **None found online without an account and with an acceptable licence.** | - | - | - | - | See "R2" below. Local fallback exists; online option needs a user-made account. |
| **R3** (second daily source) | Stooq `ES.F` daily CSV (price only, **Volume = 0**) | none seen | ~0.55 MB (est.) | ~11,800 (est.; about 1980 to 2026-10) | Same Stooq ToS. **Do not commit the raw file.** | Same CSV caveat. Pre-1997 rows cannot be E-mini data. |

Hard limits found: nothing account-free gives daily OHLCV with Volume before 2005; the long
S&P 500 history sources (Yahoo `^GSPC`/`SPY`, S&P DJI, CRSP) need a paid or registered account or
did not load (see "Not verified").

## How to read the evidence

Each fact carries a tag.

- **[R]** read directly on the provider's rendered page in a browser pane.
- **[F]** returned by the web-fetch tool, which summarises the page with a small model. Quotes
  marked [F] are as returned; re-check the exact wording before you rely on a clause.
- **[S]** web-search result summary (secondary; not the provider's own page).
- **[L]** read from a local file on this machine.
- **[I]** my inference or estimate; the basis is stated.
- **[U]** not verified. The 40-request research budget ran out, or the page would not load.

Quotes are kept short on purpose; follow the URL for the full text.

## What the candidates must be compared against

P1 = MES continuous 1-minute bars, 2020-01-03 to 2026-02-24, NinjaTrader, back-adjusted, US
Central time. The protocol builds its **D frame** from the Globex session (a trading date starts at
17:00 CT; Open = first 1-minute open; Volume = sum of contracts). Therefore:

- A daily file from another vendor will **not** reproduce P1's D-frame numbers bar for bar.
  SPY uses the 09:30-16:00 ET regular session and share volume; `ES.F` has no volume. Compare the
  sign, rank order and rough size of each rule's result, not exact P&L.
- Gap and open-based rules (overnight gap, turn-of-month entries at the open) are sensitive to the
  session definition. Say so when reporting.
- No candidate below is a back-adjusted futures series. Any futures series with roll gaps is
  unadjusted; do not mix it with P1's point-difference P&L method (protocol section 4).

## Candidate evaluation

### 1. Stooq, SPY.US daily (selected as R1)

- **Provider / terms page:** Stooq, https://stooq.com/terms.html [R].
- **Instrument:** State Street SPDR S&P 500 ETF Trust (`spy.us`). Page title: "SPY.US - State
  Street SPDR S&P 500 ETF Trust - Stooq" [R].
- **Bar size / range:** daily. First row No. 1 = 25 Feb 2005; last row No. 5444 = 16 Oct 2026 [R].
  So the history starts in 2005, not the 1990s.
- **Fields:** Date, Open, High, Low, Close, Volume (plus Change columns on the web page). High and
  Low are genuine ETF session values; Volume is real share volume, e.g. 110,044,865 on 3 Nov 2005
  and 64,384,579 on 16 Oct 2026 [R].
- **Format:** CSV, comma or semicolon separator selectable on the page [R]. Expected header
  `Date,Open,High,Low,Close,Volume` [I; matches the table columns, header not inspected].
- **Size:** ~0.27 MB (5,444 rows x ~50 bytes) [I].
- **Download URL (link target read from the page):** `https://stooq.com/q/d/l/?s=spy.us&i=d` [R].
  The HTML table (no login) is at `https://stooq.com/q/d/?s=spy.us`.
- **Account / key:** the page shows no login for the table and the CSV link has no key in its URL
  [R]. A search-result summary says "as of early 2026" a CAPTCHA-issued API key is required for
  the CSV interface, and another source disagrees [S]. **Not tested**, because testing means
  downloading. If the link returns a CAPTCHA, the user must download it by hand in a browser.
- **Licence:** ToS 5.3: "Redistribution of data found on the website is not allowed without the
  consent of Stooq." [R] ToS 5.1 disclaims accuracy. No clause on private research was found, and
  no clause on publishing derived statistics [R].
- **Adjustment:** the series looks dividend-adjusted. Close on 30 Dec 2005 is 96.07 [R]; I recall
  SPY closing near 125 that day [I], so prices are back-adjusted to today. The page offers a
  "Skip: splits / dividends" selector [R]; confirm what the CSV applies before use.
- **Quality note:** an ETF, not the futures contract: no overnight session, no roll, dividends
  folded into price. Good for daily OHLC and volume rules, weak for session-gap rules.

### 2. Stooq, ES.F daily (selected as R3)

- **Page:** `https://stooq.com/q/d/?s=es.f` titled "ES.F - S&P 500 E-Mini - Stooq" [R].
- **Range:** a query 1980-01-01 to 1991-03-01 returned 2,823 rows and one for 1990-01-01 to
  2010-12-31 returned 5,299 rows [R], so the series reaches back to about 1980 [I]. Last date
  not read. Estimated total ~11,800 rows [I].
- **Fields:** Open, High, Low, Close. **Volume reads 0** in every row sampled (1991 and 2010)
  [R]. Treat Volume as absent.
- **Download URL:** `https://stooq.com/q/d/l/?s=es.f&i=d` [I: same pattern as the SPY link that
  was read; this exact link was not inspected].
- **Account / licence:** as in item 1.
- **Quality note:** the E-mini launched in 1997 [I, general knowledge], so rows before then cannot
  be E-mini trades. A close of 370.5 on 1 Mar 1991 [R] looks like an index level. The series is
  a splice with no stated method. Prices near the index level suggest it is unadjusted (roll gaps
  present) [I]. Use only 1998 onward for any "futures" claim.

### 3. Stooq, ^SPX and bulk database (not usable as tried)

- Pages `https://stooq.com/q/d/?s=^spx` and `/q/?s=^spx` redirected to the symbol search with
  "Symbol ^SPX nie istnieje w bazie" (symbol not in the database) [R]. The index could not be
  confirmed on Stooq.
- A search summary says bulk ZIPs of the whole database are listed at `https://stooq.com/db/h/`
  [S]. The fetch of that page returned empty content [U].
- **Index data licence passed down by Stooq (ToS 6.1):** "may be used only for your own
  personal, non-commercial purposes." [R]

### 4. FRED, series SP500 (rejected)

- URL https://fred.stlouisfed.org/series/SP500 [F].
- **Fields:** "Daily, Close" only: no Open, High, Low or Volume. Price index, no dividends [F].
- **History:** the notes say FRED keeps "10 years of daily history" for S&P and Dow Jones series
  [F]. The latest point shown is 2026-10-16 (7,659.44) [F].
- **Licence:** "Data in this graph are copyrighted." and reproduction "is prohibited except with
  the prior written permission of S&P Dow Jones Indices LLC" [F].
- **Verdict:** close only, 10 years, copyright-restricted. Not useful for these rules.

### 5. Cboe, VIX daily history (auxiliary only)

- URL https://www.cboe.com/tradable_products/vix/vix_historical_data/ [F]. File
  `https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv`, "1990 to
  present, updated daily"; direct link, no login mentioned [F].
- **Content:** the VIX index, not S&P 500 prices. The page describes only "daily closing
  values"; whether the CSV has Open/High/Low columns is **not verified** [F/U]. No SPX file on
  that page [F].
- **Size:** ~0.5 MB (about 9,000 rows) [I].
- **Terms:** page footer "(c) 2026 Cboe Exchange, Inc. All rights reserved."; the linked "Use of
  Content" policy was not read [F/U].
- **Verdict:** can supply a volatility-regime filter for splitting results; not a price series for
  the 25 rules.

### 6. S&P Dow Jones Indices (not verified)

- https://www.spglobal.com/spdji/en/indices/equity/sp-500/ returned HTTP 403 to the fetch tool
  [F]. Whether the index-level download needs a login, and its terms, are **[U]**.
- Second-hand evidence of the licence: Stooq ToS 6.1 (above) and the FRED copyright note (above)
  both restrict S&P 500 index data to personal, non-commercial use / no reproduction.
- S&P DJI history is index levels (close), not OHLCV [U; general knowledge].

### 7. Yahoo Finance (rejected)

- Terms: https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html [F]. Short clauses returned:
  automated collection "using any automated means" is prohibited (section 2(d)); "you may not
  access or reuse the Services ... for any commercial purpose" (2(e)); copying or distributing
  content needs written permission (2(h)). Only the first 100,000 of 125,418 characters were
  read, and no Yahoo-Finance-specific "personal use only" clause was seen, so that phrase is not
  confirmed [F/U].
- Historical CSV download: a Yahoo help page says Gold subscribers can download historical data
  as CSV (https://help.yahoo.com/kb/SLN2311.html), and a Portfolio Performance help page says
  that since late 2024 prices cannot be downloaded as CSV without a paid subscription [S].
- **Verdict:** account and payment needed for the official download; unofficial libraries break
  the automated-access clause. Rejected.

### 8. NinjaTrader historical data (the P1 vendor): see "NinjaTrader terms" below

### 9. CME Group DataMine

- Pages https://www.cmegroup.com/market-data/datamine-historical-data.html and the licensing page
  timed out three times with the fetch tool [U]. Evidence is from CME's client wiki,
  https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457319709/CME+DataMine+Support
  [F]:
  - free data: "A limited amount of free historical data is available for download on the CME
    Group FTP site." No FTP address, instrument list or date range is given.
  - samples: "Data samples are available by data type on the DataMine website." Size and range
    of the E-mini S&P 500 samples are **[U]**.
  - account: "CME Group requires that users log in with their CME Group Login (SSO) before making
    data purchases." An API ID is also needed for API downloads.
  - redistribution: "CME does not currently restrict the distribution of historical End of Day
    or Time and Sales data", but "External redistribution requires vendor registration."
    (Hedged and from a wiki, not a licence agreement.)
- Pricing for ES/MES: **[U]** (not found). Contact listed on the wiki: CMEDataSales@cmegroup.com.
- **Verdict:** needs a CME login to buy; free sample content unconfirmed. Not recommended without
  a user decision.

### 10. Databento (the one independent intraday source that exists, but needs an account)

- Pricing page https://databento.com/pricing [F]: "New users get $125 in free credits that can
  be used towards historical data from any of our datasets." Credits "expire 6 months after
  signup." Billing: data is "priced ($/GB) by the data's uncompressed size (GB) in binary
  encoding." The page lists "OHLCV-1s/1m/1h/1d".
- Dataset page https://databento.com/catalog/cme/GLBX.MDP3 [F]: "Available from" 2010-06-06;
  schemas include OHLCV-1m; MES is in the product table; "A license isn't required to access
  historical data."
- **Account / key:** sign-up and an API key are needed [F]. The orchestrator cannot create
  accounts or enter keys. This is the blocker.
- **Size (estimate):** one continuous ES contract, 1-minute bars, 2020-01-03 to 2026-02-24 is
  about 2.1 million rows (~348,000 minute bars per year [I]) or ~0.12 GB in binary form
  (56 bytes per OHLCV record [I, general knowledge]); CSV roughly 150-250 MB [I]. Databento
  shows an exact cost before purchase; the dollar price per GB was **not** found [U].
- **Licence:** personal-research and redistribution terms for GLBX.MDP3 were not on the pages
  read (the page points to the "Data catalog" and a Plus plan with "External distribution")
  [F/U]. Assume no redistribution.
- **Verdict:** best independent intraday ES/MES source, but only after the user creates the
  account, copies the API key into their own environment, and approves the spend.

### 11. Kibot and FirstRate Data (free samples)

- **Kibot** free page https://www.kibot.com/free_historical_data.aspx [F]: "Free downloads - no
  registration". Free files: IBM and OIH 1-minute (most recent three months), IVE and WDC tick
  (most recent 30 days); a free guest account returns daily US stock and ETF data through the
  API. No ES, MES, SPY or index sample; futures samples "on request through the contact form".
  Adjusted by default, raw with `&unadjusted=1`.
  - Licence https://www.kibot.com/license.html [F]: "The Data is for the Licensee's own internal
    use only." and "will not resell or redistribute the Data". Does not mention guest data.
  - A guest SPY daily pull is possible in principle; its start date and exact endpoint were not
    verified [U]. The guest account is described as "for testing".
  - **Verdict:** free intraday is useless here (wrong instruments); guest daily is a possible
    cross-check but unverified.
- **FirstRate Data** free page http://firstratedata.com/free-intraday-data [F]: "No sign-up
  needed." The sample lists ES, SPX, SPY and VIX (MES not listed) at 1-, 5-, 30-minute, 1-hour
  and daily bars, **but only 21 Sep 2026 to 2 Oct 2026 (two weeks)**; timestamps mark the start of
  each bar. The licence text was not retrieved (`/license` returned 404) [U].
  - **Verdict:** two weeks (about 10 trading days) cannot validate 25 rules. Useful at most to
    check bar-time conventions. Not recommended.

### 12. Alpha Vantage (rejected)

- https://www.alphavantage.co/documentation/ [F]: every endpoint needs `apikey` ("Claim your free
  API key"). `TIME_SERIES_INTRADAY` is "a premium endpoint"; `TIME_SERIES_DAILY` full output "is
  available to premium keys" (compact is free); `TIME_SERIES_DAILY_ADJUSTED` is "a premium API
  function". Free daily request limit not seen [U].
- **Verdict:** key needed and long history is premium. Rejected.

### 13. Kenneth French Data Library (returns only)

- https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html [F]: factor and
  portfolio **returns** only (Fama/French factors, size/value/momentum portfolios, industries);
  no S&P 500 price series, no futures, no OHLCV. Legal notice: "Copyright Eugene F. Fama and
  Kenneth R. French". Not a price-level source. Rejected for these tests (could add a Rm-Rf
  market-return cross-check at most).

### 14. Not verified (no page read in the budget)

- **Kaggle** S&P 500 / ES datasets: licence is set per dataset, and many are copies of Yahoo
  data, so the upstream terms apply [U; general knowledge]. Download needs a Kaggle login
  [U; general knowledge]. Not recommended: the orchestrator cannot sign in.
- **Nasdaq Data Link:** needs an account/API key [U; general knowledge]; whether a free
  continuous ES series still exists was not checked.
- **WRDS / CRSP:** institutional subscription [U; general knowledge]. CRSP's S&P 500 daily series
  is a level and a return (no High/Low/Volume) [U; general knowledge].
- **University-hosted futures datasets:** none found in the budget.

## Recommendations

### R1: long daily dataset with real OHLCV, no account (provisional)

| Item | Value |
|---|---|
| Filename (suggested) | `stooq_spy_us_d.csv` |
| Source URL | `https://stooq.com/q/d/l/?s=spy.us&i=d` (page: `https://stooq.com/q/d/?s=spy.us`) |
| Expected size | ~0.27 MB (estimate) |
| Rows | 5,444 data rows, 2005-02-25 to 2026-10-16 (header extra) |
| Fields | Date, Open, High, Low, Close, Volume (real High/Low and share volume) |
| Licence constraint | Stooq ToS 5.3: redistribution not allowed. **Do not commit the raw file to the public repo.** Keep it next to P1 under `futures_data`; commit only its SHA-256, row count and download date. Publish aggregate metrics only. |
| Caveats | ETF, dividend-adjusted (inferred); regular-session bars; starts 2005, not the 1990s; CSV endpoint may demand a CAPTCHA/API key (untested). |

Why not earlier history: no account-free source with genuine High/Low **and** Volume reaching the
1990s was found. The routes that do exist (Yahoo Gold CSV for `^GSPC`/`SPY` from 1993, CRSP via a
university) need an account.

### R2: independent intraday dataset (<= 15 minutes)

**No online source that is both free of an account and under an acceptable licence exists** (checked:
Kibot free, FirstRate free, CME free area, Alpha Vantage free). They fail on instrument (Kibot),
length (FirstRate: two weeks), unknown content (CME), or premium status (Alpha Vantage).

Options, in order:

1. **Databento `GLBX.MDP3`, `ohlcv-1m`, `ES.c.0` (or `MES.c.0`)**, 2020-01-03 to 2026-02-24
   (~2.1 M rows, ~0.12 GB binary, CSV est. 150-250 MB). Needs the user to create an account and an
   API key and to accept the $125 free credit terms (6-month expiry). Do not commit raw output.
2. **Local, already on the machine, no download:** `USA500IDXUSD_M15.csv` (and `_M5`, `_D1`)
   described under "Local datasets". It is a different vendor from P1, but it is an index CFD
   with unreliable volume and overlaps P1 only until 2023-09-11. Use it for price-only rules and
   label it clearly as weaker evidence. Its provenance is not stated, so treat the licence as
   unknown (see below).

### R3: second daily source

| Item | Value |
|---|---|
| Filename (suggested) | `stooq_es_f_d.csv` |
| Source URL | `https://stooq.com/q/d/l/?s=es.f&i=d` (page: `https://stooq.com/q/d/?s=es.f`) |
| Expected size | ~0.55 MB (estimate) |
| Rows | ~11,800 (estimate; about 1980 to 2026-10) |
| Fields | Date, Open, High, Low, Close; **Volume is 0** |
| Licence constraint | Same Stooq ToS 5.3. **Do not commit the raw file.** |
| Caveats | Roll method unknown (looks unadjusted); rows before Sep 1997 cannot be E-mini; volume rules (OrderFlow, VWAP volume weighting, RVol) cannot be cross-checked on it; same vendor as R1, so R1 and R3 are not independent of each other (both are independent of NinjaTrader). |

A different-vendor SPY cross-check (Kibot guest API) is possible but unverified (date range,
endpoint) and its licence says "internal use only", so it is not recommended yet.

## NinjaTrader terms: may metrics be published when raw bars may not?

Official documents found:

- **NinjaTrader End User License Agreement** (licensor NinjaTrader, LLC; "Last updated: June 12,
  2026"), https://www.tradovate.com/nt-terms-and-eula/ [F]. The fetch found **no clause about
  market data, historical data, exchange data, redistribution of data, derived data, or
  publishing trading results**. Its restrictions concern the software: for example 2.1(c)
  forbids preparing "derivative works or improvements of the Software", and 2.1(b) forbids giving
  anyone access to the Software. The domain is Tradovate's (a NinjaTrader Group company [I]); NinjaTrader's own
  `ninjatrader.com/legal/` returned 404.
- **NinjaTrader API License Agreement**, https://partner.ninjatrader.com/connect/resources/legal/ninja-trader-api-license-agreement
  [F]. Section 3 bars distributing or transferring "the NinjaTrader Content (including any market data
  or derivative works based on or using such market data)" without NinjaTrader's prior written consent. This is a contract
  for API licensees. It does not clearly bind a desktop user, but it is the clearest written
  NinjaTrader position on redistributing market data and on "derivative works".
- **Upstream (CME):** see item 9: CME's wiki says it "does not currently restrict" distribution
  of historical End of Day / Time and Sales data but requires vendor registration for external
  redistribution [F]. The terms of the specific feed behind P1 (Continuum, Kinetick, a broker
  feed) were not found and may be stricter. **[U]**

Conclusion (not legal advice):

- **Raw bars: do not publish.** No document found grants redistribution, and the nearest
  NinjaTrader text forbids it. This matches the protocol ("Raw data is never committed").
- **Derived metrics: no document found forbids them, and none explicitly allows them.** The EULA
  is silent. The API agreement's "derivative works based on or using such market data" could be
  read broadly, but summary statistics (Sharpe, total P&L, drawdown, counts) do not reproduce
  prices. Safe practice: publish aggregate tables only; do not publish per-bar prices,
  indicator series on bars, or daily P&L series fine enough to rebuild prices. For certainty, ask
  NinjaTrader support in writing.

## Local datasets already on this machine

All paths read on 2026-10-17 [L]. None of these is committed to the repo.

**P1 (primary, from NinjaTrader).** `C:\Users\rajib\OneDrive\Docs\futures_data\ninja_trader_signal_data\data\`

| File | Bytes |
|---|---|
| `MES_1min_20200101_20260201.csv` | 179,097,656 |
| `MES_1min_20210131_20220131.csv` | 167,747,521 |
| `MES_1min_20220130_20230131.csv` | 170,715,448 |
| `MES_1min_20230131_20240229.csv` | 177,018,158 |
| `MES_1min_20240229_20250331.csv` | 180,922,978 |
| `MES_1min_20250331_20260224.csv` | 150,566,652 |

Total 1,026,068,413 bytes (~0.98 GiB). The first file overlaps the others; the protocol
de-duplicates (first occurrence wins). Header starts `Timestamp,BarTime,Symbol,Timeframe,
SignalType,...,Open,High,Low,Close,Volume,...` (signal columns present; bar rows only are used).
Vendor: NinjaTrader. Raw bars must not be published (see above).

**Other NinjaTrader-format files, same vendor family (not independent of P1):**
`futures_data\ninja_trader_signal_data\MES_150tick_20250202_20260224.csv` (168 MB);
`futures_data\ES_*_MIN_LAST.txt`, `train_data\ES_2025*_MINUTE_LAST.txt` (1.9-4.3 MB each) and
`ES_*_TICK_LAST.txt` (351 MB), plus MGC, MNQ, MYM, GC files. Format is
`yyyyMMdd HHmmss;O;H;L;C;Volume` [L]. They cover roughly 2025-03 to 2026-02 only (file names)
and add no independence. NinjaTrader's own database is at
`C:\Users\rajib\Documents\NinjaTrader 8\db` (per-contract folders for ES 03-24 to 12-26, MES 06-19 to
12-26, and others) [L, folder listing only].

**Third-party sample repository (different vendor, provenance unstated).**
`futures_data\Stocks-Futures-Financial-Time-series-Tick-Bar-Data\` (README: "Financial-Time-Series-Data-Features -
FREE Repository"; root `LICENSE` is MIT, "Copyright (c) 2022 Shay Ronen") [L]. The MIT notice covers
the repository owner's claim only; the files do not say where the prices came from, so the
data's own redistribution terms are **unknown**. Do not republish it.

- `indices\s&p500\USA500IDXUSD_*.csv`, tab-separated `Time Open High Low Close Volume`;
  README says timestamps are GMT and the 1-minute set is capped at 200,000 bars [L]. The file
  name matches Dukascopy's `USA500.IDX/USD` index CFD [I]; not stated in the repository.

| File | Range | Rows | Rows since 2020-01-03 | Bytes |
|---|---|---|---|---|
| `USA500IDXUSD_D1.csv` | 2013-05-23 to 2023-09-11 | 2,653 | 957 | 160,617 |
| `USA500IDXUSD_M15.csv` | 2013-08-14 to 2023-09-11 | 200,000 | 82,991 | 11,767,868 |
| `USA500IDXUSD_M5.csv` | 2020-09-24 to 2023-09-11 | 200,000 | all | 11,751,857 |
| `USA500IDXUSD_M1.csv` | 2023-02-01 to 2023-09-11 | 200,000 | all | 11,706,219 |

  Quality: CFD index, not futures; near-24-hour bars; the Volume column is tick-count style and
  holds odd values in the last rows (e.g. 14,200,000 on the final M15 bar) [L], so do not use it
  for any volume rule. Overlap with P1 is only 2020-01-03 to 2023-09-11 (M5 from 2020-09-24).
  This is the only independent intraday data on the machine and the fallback for R2.
- `tickdata\indicies\s&p-tick\SP.csv` (481,181,612 bytes, 13,802,502 data rows;
  `date,time,price,volume`, 2000-01-03 to 2019-12-31, times look like US Central) [L]. This is
  probably the full-size S&P 500 futures contract (name "SP") [I]. Volume is 0 for all rows before
  2003 and for roughly 35-50% of rows after; tick counts fall from ~1.75 M (2008) to ~17,600 (2019)
  [L]. It can be aggregated to daily bars for 2000-2019 (a pre-P1, out-of-sample period) but
  daily High/Low in 2012-2019 rest on a few thousand ticks a year and the roll handling is
  unknown. Treat as a weak, price-only extra, not a replacement for R1.
- `stock\sp500-stocks.csv` is a 28 KB list of index weights (no price history) [L].
- `tickdata\indicies\USA500.IDXUSD_Ticks_04.09.2023-04.09.2023.csv` (715 KB): one day of ticks.

## Not verified and blockers

1. **Stooq CSV endpoint:** not tested (downloading is out of scope). A search summary claims a
   CAPTCHA/API key; the page links show none. If a CAPTCHA appears the orchestrator must not try to
   solve it; the user downloads the two files in a browser.
2. **Stooq `^SPX`:** symbol not found with the URLs tried; S&P 500 index series on Stooq unconfirmed.
3. **S&P DJI (HTTP 403), CME DataMine pages (timeouts), FirstRate license (404), Databento
   redistribution terms, Cboe "Use of Content", Kaggle, Nasdaq Data Link, WRDS/CRSP, university
   futures datasets:** not verified.
4. **R2:** no account-free online source; Databento needs a user-made account and key.
5. **History before 2005 with real High/Low and Volume:** no account-free source found.
6. **Quote handling:** items tagged [F] came through a summarising fetch tool, not raw HTML. Only
   Stooq (all pages) and the local files were read directly.

## Request log (budget 40)

24 page fetches, 6 web searches and 9 browser page loads = 39 (limit 40). Fetch failures counted: S&P DJI
(403), CME x3 (timeouts), Stooq `/db/h/` (empty), Stooq `/q/d` via the fetch tool (empty),
NinjaTrader `/legal/` (404), FirstRate license (404), Databento licensing docs (truncated).
