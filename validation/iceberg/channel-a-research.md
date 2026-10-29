# Channel A — documentation audit of research-claims-ledger.md (R1–R16)

auditor: Channel A (documentation only; no code executed, no DLLs read, no channel-b file read)
retrieved: 2026-10-28 (all records)
installed pin (from ledger): NinjaTrader 8.1.8.3
doc version match: the NT8 help guide is unversioned per page, but its release-notes page
(https://static.ninjatrader.com/support/helpGuides/nt8/release_notes.htm) lists "8.1.8" (July 21, 2026) as the newest
release, and https://static.ninjatrader.com/support/helpGuides/nt8/8_1_8.htm lists builds 8.1.8.0–8.1.8.4 (8.1.8.3 =
September 29, 2026). So the live guide covers the installed build. The 8.1.8 notes do not mention market depth, MBO,
OnMarketDepth, OnMarketData, Tick Replay, Market Replay, Playback or bid/ask, so I found no deprecation or change for
any API claim below. Version label used below: "NT8 help guide (current = 8.1.8.x)".
access caveats: forum.ninjatrader.com threads now 301-redirect to discourse.ninjatrader.com, which returns 404 for
the legacy thread URLs. **No NinjaTrader staff forum answer could be retrieved**, so none is cited as evidence. Search
snippets of staff posts (e.g. a "90 days" Market Replay limit, "MBO data cannot be accessed at this time ... SFT-1496")
are leads only. They are NOT admissible and decide nothing here.
quote method: pages fetched with WebFetch from static.ninjatrader.com (after following the ninjatrader.com 301) and
from the vendor/exchange sites named. Quotes are short spans from the fetched page text.

Verdict summary: CONFIRMED 12 (R1, R2, R3, R5, R6, R7, R10–R15), REFUTED 1 (R8), UNVERIFIABLE 3 (R4, R9, R16). Table at end.

---

```
claim_id:    R1
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/onmarketdata.htm
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x); page itself carries no version
quote:       "protected override void OnMarketData(MarketDataEventArgs marketDataUpdate)"
retrieved:   2026-10-28
note:        Documented as an overridable NinjaScript event method. The page does not name the declaring base class, so
             the "Indicator"/NinjaScriptBase placement is Channel B's to settle. No deprecation found.
```

```
claim_id:    R2
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/marketdataeventargs.htm
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       Ask: "A double value representing the ask price"; Bid: "A double value representing the bid price";
             Price: "A double value representing the price"; Time: "A DateTime structure representing the time";
             Volume: "A long value representing volume"; MarketDataType: "Possible values are:" ...
retrieved:   2026-10-28
note:        All six members are documented. Types: Ask/Bid/Price double, Volume long, Time DateTime. The page also lists
             Instrument and IsReset. Docs list no `.Size` member, which matches the ledger's falsifier.
```

```
claim_id:    R3
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/marketdataeventargs.htm
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       MarketDataType "Possible values are:" MarketDataType.Ask, MarketDataType.Bid, ... MarketDataType.Last ...
retrieved:   2026-10-28
note:        The listed values are Ask, Bid, DailyHigh, DailyLow, DailyVolume, Last, LastClose, Opening, OpenInterest and
             Settlement. Tip on the page: "Not all connectivity providers support all MarketDataTypes."
```

```
claim_id:    R4
verdict:     UNVERIFIABLE
source:      https://static.ninjatrader.com/support/helpGuides/nt8/marketdataeventargs.htm
             (also checked: onmarketdata.htm, getcurrentbidvolume.htm, docs.ninjatrader.com/ninjascript/marketdataeventargs)
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       Volume: "A long value representing volume"
retrieved:   2026-10-28
note:        No admissible source says what Volume means on Bid/Ask events. It is never called "size", "displayed
             quantity" or "contracts at the bid". The onmarketdata.htm example prints Price and Volume for the Ask and Bid
             branches ("Ask = {0} {1} ", "Bid = {0} {1}") with no explanation. getcurrentbidvolume.htm says "Returns the
             current real-time bid volume", but that is a different API and still says "volume", not size. Leads in search
             snippets (user/staff forum posts saying "number of contracts at the bid") could not be retrieved and are not
             admissible. The claim is plausible but undocumented.
```

```
claim_id:    R5
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/onmarketdepth.htm
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       "protected override void OnMarketDepth(MarketDepthEventArgs marketDepthUpdate)"
retrieved:   2026-10-28
note:        Definition on the page: called "for every change in level two market data". No deprecation found.
```

```
claim_id:    R6
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/marketdeptheventargs.htm
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       Operation: "Represents the action you should take when building a level two book."; Position: "An int value
             representing the zero based position in the depth ladder."; Price: "A double value representing the price";
             Volume: "A long value representing volume"; MarketDataType (values MarketDataType.Ask / MarketDataType.Bid)
retrieved:   2026-10-28
note:        All five members are documented. Operation values: Operation.Add / Update / Remove. The page also lists
             Instrument, IsReset, MarketMaker and Time.
```

```
claim_id:    R7
verdict:     CONFIRMED (documented surface only — see note)
source:      https://static.ninjatrader.com/support/helpGuides/nt8/marketdeptheventargs.htm
             (cross-checked: https://docs.ninjatrader.com/ninjascript/marketdeptheventargs ; onmarketdepth.htm)
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       Position: "An int value representing the zero based position in the depth ladder."
             MarketMaker: "A string representing the market maker id"
retrieved:   2026-10-28
note:        The documented members are Instrument, IsReset, MarketDataType, MarketMaker, Operation, Position, Price, Time,
             Volume and ToString(). None of them is an order ID, and the page never mentions market-by-order (MBO).
             Position, a slot in the "depth ladder", plus Add/Update/Remove for "building a level two book" describe a
             price-level ladder (market-by-price). The 8.1.8 release notes mention no MBO addition.
             CAVEATS for the gate: (a) the one documented ID-like member is MarketMaker, a "market maker id" string. That is
             a participant/venue ID, not a per-order ID, but Channel B should report what it actually holds. (b) This
             confirmation rests on the docs enumerating the members. It cannot rule out undocumented public members, and
             Channel B's reflection decides those.
```

```
claim_id:    R8
verdict:     REFUTED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/developing_for__tick_replay.htm
             (concordant: onmarketdata.htm Note 3; marketdataeventargs.htm critical note)
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       "Tick Replay ONLY replays the Last market data event, and only stores the best inside bid/ask price at the time
             of the last trade event."  /  "Only bid and ask price is made available, bid and ask volume is NOT available."
retrieved:   2026-10-28
note:        OnMarketData IS called during Tick Replay. The dev page says "This mode also ensures the OnMarketData event is
             called after every OnBarUpdate event used to build the current bar", and onmarketdata.htm says "it can be
             called historically by using TickReplay". But it fires ONLY with MarketDataType.Last ("Tick Replay was only
             ONLY designed to work with MarketDataType.Last"; code comment "TickReplay events only occur on the "Last"
             market data type"). Bid/Ask are snapshot PRICES at each trade, with NO bid/ask volume. onmarketdata.htm Note 3
             says "historical bid/ask market data events (i..e, bid/ask volume) DO NOT work with Tick Replay". If the
             provider lacks bid/ask, NinjaTrader substitutes it ("Bid = Last price, Ask = Bid + 1 tick"). So the claim's
             "bid/ask/last events in their original sequence" is refuted. Doc tension: the user-facing tick_replay.htm says
             "the market data (bid/ask/last) that went into building a bar is loaded in the exact sequence of market data
             events". The more specific NinjaScript pages decide it: bid/ask is carried only as prices attached to Last
             events. Separate documented route: historical bid/ask series, AddDataSeries with MarketDataType.Bid/Ask,
             handled in OnBarUpdate. using_historical_bid_ask_serie.htm says "OnMarketData() events for the historical
             bid/ask series would only be triggered in real-time" and "A Tick Replay indicator or strategy CANNOT use a
             MarketDataType.Ask or MarketDataType.Bid series."
```

```
claim_id:    R9
verdict:     UNVERIFIABLE (part 1 CONFIRMED; parts 2–3 not stated explicitly)
source:      https://static.ninjatrader.com/support/helpGuides/nt8/onmarketdepth.htm ;
             https://static.ninjatrader.com/support/helpGuides/nt8/playback.htm ;
             https://static.ninjatrader.com/support/helpGuides/nt8/developing_for__tick_replay.htm
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       onmarketdepth.htm: "This method is not called on historical data (backtest)"
             playback.htm: "orders, indicators, and strategies will calculate just as they were running in real-time."
retrieved:   2026-10-28
note:        (1) Not called on historical data: explicitly CONFIRMED.
             (2) Not called during Tick Replay: onmarketdepth.htm (and docs.ninjatrader.com/ninjascript/onmarketdepth) never
             mentions Tick Replay. The dev page's "Tick Replay ONLY replays the Last market data event" strongly implies no
             depth events, but it does not say so of OnMarketDepth.
             (3) Called during Market Replay/Playback: no page says so directly. The supporting chain is: playback.htm says
             "Market Replay data is the most accurate and holds both level I and level II (market depth) data" and that
             scripts calculate as in real time, and onmarketdepth.htm says the method fires "for every change in level two
             market data". That is an inference across pages, not a statement. Historical-data playback has no depth:
             set_up12.htm says "historical tick data can be used to playback chart data (without market depth)".
             Net: one conjunct is documented and two are inferred. A runtime check in Playback is needed.
```

```
claim_id:    R10
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/set_up12.htm  (Operations > Playback Connection > Set Up)
             (concordant: playback.htm)
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       "Market Replay data holds the exact sequence level I and Level II (market depth) data."
             "NinjaTrader offers a limited amount of Market Replay data free to download for playback purposes."
             "Only the most common instruments are currently available."
retrieved:   2026-10-28
note:        Download path per the page: Historical Data window > "Get Market Replay data" > pick instrument + date > OK.
             Not possible while connected to Playback, and "Enable market recording for playback" must be off first.
             LIMITS: the guide gives an instrument limit ("most common instruments") but NO date-range limit. A "90 days"
             figure appears only in non-retrievable forum snippets and is not admitted. Level 2: the guide defines Market
             Replay data as containing Level II, and playback.htm says "NinjaTrader stores level I and level II together in
             a single market replay file". No page says separately that every downloaded file includes depth for every
             instrument/date. Recording caveat on set_up12.htm: Level II is recorded only when a Level II, SuperDOM or FX
             Pro window is open and receiving data for that instrument.
```

```
claim_id:    R11
verdict:     CONFIRMED
source:      https://static.ninjatrader.com/support/helpGuides/nt8/options_marketdata.htm  (Settings > Market data)
             (concordant: set_up12.htm)
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       "Enables or disables market data recording for use with the Playback Connection"
             set_up12.htm: "In the Market Data category enable the option "Enable market recording for playback"."
retrieved:   2026-10-28
note:        On options_marketdata.htm the option is labelled "Enable market recording of playback" ("of", not "for"), a
             wording difference between pages. Reached via Tools > Options (options.htm lists "Market data:
             options_marketdata.htm").
```

```
claim_id:    R12
verdict:     CONFIRMED
source:      https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457218264/Order+Qualifiers
             (CME Group Client Systems Wiki)
source_tier: 1 (exchange's own technical documentation)
version:     page shows "Updated Mar 11" (year not shown)
quote:       "The display quantity specifies the given quantity of an order shown the market."
             "the next 10 enter the market as a new order at the bottom of the book."
retrieved:   2026-10-28
note:        Native exchange order qualifier on CME Globex. Worked example: buy 100, display 10. Replenishments re-enter at
             the back of the queue. Available for all products except listed FX (6A, 6B, 6C, 6E, 6J, 6S) and certain SOFR
             options contracts. ES/MES are not on the exclusion list. SOFR futures max display ratio 1:60. The CME education
             page (cmegroup.com/education/display-quantity-order-overview.html) timed out and is not cited.
```

```
claim_id:    R13
verdict:     CONFIRMED
source:      https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints
source_tier: 1
version:     Spot REST API (schema link path 1.0.0; page footer "© 2026"; no last-updated date)
quote:       icebergQty: "Used with `LIMIT`, `STOP_LOSS_LIMIT`, and `TAKE_PROFIT_LIMIT` to create an iceberg order."
             "Any order with an `icebergQty` MUST have `timeInForce` set to `GTC`."
retrieved:   2026-10-28
note:        Parameter of POST /api/v3/order. The page text also says LIMIT_MAKER orders can become icebergs.
```

```
claim_id:    R14
verdict:     CONFIRMED
source:      https://docs.cdp.coinbase.com/exchange/websocket-feed/channels
source_tier: 1
version:     Coinbase Exchange WebSocket feed docs (no date shown)
quote:       "Full Channel:Authentication Required" ; "Level3 Channel:Authentication Required"
retrieved:   2026-10-28
note:        Also on the page: "Level2 Channel:Authentication Required", while "The Level2 Batch Channel does not require
             authentication". So the only unauthenticated depth on Coinbase Exchange is batched L2.
```

```
claim_id:    R15
verdict:     CONFIRMED
source:      https://databento.com/pricing
source_tier: 1
version:     pricing page as served 2026-10-28 (no date shown)
quote:       "New users get $125 in free credits that can be used towards historical data from any of our datasets."
retrieved:   2026-10-28
note:        Conditions: historical data only, "Credits expire 6 months after signup and each team is eligible for one set of
             credits."
```

```
claim_id:    R16
verdict:     UNVERIFIABLE
source:      https://static.ninjatrader.com/support/helpGuides/nt8/data_by_provider.htm ;
             https://static.ninjatrader.com/support/helpGuides/nt8/playback.htm ;
             https://static.ninjatrader.com/support/helpGuides/nt8/using_historical_bid_ask_serie.htm ;
             https://static.ninjatrader.com/support/helpGuides/nt8/developing_for__tick_replay.htm
source_tier: 1
version:     NT8 help guide (current = 8.1.8.x)
quote:       data_by_provider.htm footnote: "*Historical bid/ask comes from associated value at each historical last tick
             value."  /  using_historical_bid_ask_serie.htm: "The historical bid/ask series holds all bid/ask events sent
             out by the exchange."
retrieved:   2026-10-28
note:        The claim is about files on this machine, which documentation cannot decide. Relevant documented facts:
             - Data by Provider table: the "NinjaTrader" connectivity provider = Historical Bid/Ask Tick Data YES and
               Bid/Ask Stamped Tick Data YES. Same for Continuum/CQG and Rithmic. Kinetick and IQFeed = "*YES", meaning
               bid/ask attached to each last tick (footnote). BarChart, eSignal, Interactive Brokers and Schwab = NO for
               Historical Bid/Ask Tick, and IB = NO historical tick at all. Footnote: "There are various limitations on data
               from each provider and data is subject to change."
             - playback.htm: if tick data "is stamped with ask and bid data then NinjaTrader will use that", otherwise it
               simulates "by setting it either to last price or last price +/- 1 tick at random". So stamped bid/ask is
               PRICE, and the docs say nothing about sizes.
             - Tick Replay: "Only bid and ask price is made available, bid and ask volume is NOT available."
             - The historical bid/ask series holds every bid/ask event, but no page says whether its bar Volume carries
               bid/ask SIZE.
             So whether bid/ask SIZES exist in historical tick data is undocumented for every provider. Whether this
             machine's db\tick store holds a bid/ask series at all depends on which provider and series were downloaded.
             Decisive check = the user's NinjaTrader run (as pre-registered).
```

---

## Verdict table

| ID | Verdict | Deciding source |
|----|---------|-----------------|
| R1 | CONFIRMED | onmarketdata.htm signature |
| R2 | CONFIRMED | marketdataeventargs.htm member list |
| R3 | CONFIRMED | marketdataeventargs.htm MarketDataType values |
| R4 | UNVERIFIABLE | Volume documented only as "A long value representing volume" |
| R5 | CONFIRMED | onmarketdepth.htm signature |
| R6 | CONFIRMED | marketdeptheventargs.htm member list |
| R7 | CONFIRMED (documented surface) | no order-id member documented; Position = depth-ladder slot; MarketMaker string flagged |
| R8 | REFUTED | developing_for__tick_replay.htm: Tick Replay replays Last only; bid/ask volume NOT available |
| R9 | UNVERIFIABLE | historical "not called" documented; Tick Replay / Market Replay behaviour only inferable |
| R10 | CONFIRMED | set_up12.htm: L1+L2 exact sequence; limited free download; most common instruments only |
| R11 | CONFIRMED | options_marketdata.htm / set_up12.htm |
| R12 | CONFIRMED | CME Client Systems Wiki, Order Qualifiers: display quantity |
| R13 | CONFIRMED | Binance Spot API: icebergQty |
| R14 | CONFIRMED | Coinbase Exchange WS channels: full/level3 "Authentication Required" |
| R15 | CONFIRMED | Databento pricing: $125 free credits (historical, 6-month expiry) |
| R16 | UNVERIFIABLE | machine-specific; docs document bid/ask prices per provider, never sizes |

Counts: CONFIRMED 12, REFUTED 1, UNVERIFIABLE 3.
