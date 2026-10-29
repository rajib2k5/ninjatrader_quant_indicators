# Phase 1 verdict — iceberg research claims

mode: Mode 1 (dual subagent). Evidence: channel-a-research.md (docs only), channel-b-research.md
(reflection on the installed assemblies, compile probes with falsifiers, local files).
environment note: Channel B found NinjaTrader **8.1.8.4** installed (updated 2026-10-19), not the
8.1.8.3 in env-pin.txt; the help guide covers 8.1.8. All runtime verdicts apply to 8.1.8.4.

| ID | Claim (short) | A | B | Gate |
|----|---------------|---|---|------|
| R1 | `OnMarketData` override exists | CONFIRMED | CONFIRMED (protected virtual on NinjaScriptBase; misspelled override → CS0115) | **ACCEPTED** |
| R2 | `MarketDataEventArgs` has MarketDataType/Price/Volume/Time/Bid/Ask | CONFIRMED | CONFIRMED (reflection; `.Size` → CS1061) | **ACCEPTED** |
| R3 | `MarketDataType` has Last/Bid/Ask | CONFIRMED | CONFIRMED (Ask=0, Bid=1, Last=2 of 11; missing value → CS0117) | **ACCEPTED** |
| R4 | Bid/Ask `Volume` = displayed best size | UNVERIFIABLE ("a long value representing volume") | N/A (needs a feed) | **UNRESOLVED → decided by the user's diagnostic run** |
| R5 | `OnMarketDepth` override exists | CONFIRMED | CONFIRMED | **ACCEPTED** |
| R6 | `MarketDepthEventArgs` has MarketDataType/Operation/Position/Price/Volume | CONFIRMED | CONFIRMED (also Instrument, IsReset, MarketMaker, Time) | **ACCEPTED** |
| R7 | depth events carry no per-order id (market-by-price) | CONFIRMED | CONFIRMED (complete member list; only `MarketMaker` string) | **ACCEPTED** |
| R8 | Tick Replay calls OnMarketData with bid/ask/last in sequence | **REFUTED** — developer docs: Tick Replay delivers `Last` events only; bid/ask are the prices at each trade; "bid and ask volume is NOT available" | N/A, but corroborating: replay record type `ReplayObject` has Bid/Ask **prices only** | **REJECTED** |
| R9 | OnMarketDepth not historical / Tick Replay, but in Market Replay | UNVERIFIABLE (only "not called on historical data") | N/A | **UNRESOLVED → diagnostic run in Playback** |
| R10 | Market Replay holds L1+L2, limited free download | CONFIRMED (L1+L2 exact sequence; "limited amount", common instruments) | UNVERIFIABLE for the download; installed code has L1 and L2 replay formats | **ACCEPTED** for "replay holds L1+L2"; free-download half accepted on Channel A only |
| R11 | record-for-replay option exists | CONFIRMED | N/A | accepted (minor) |
| R12 | CME Globex supports display-quantity orders | CONFIRMED | N/A | accepted (exchange fact) |
| R13 | Binance `icebergQty` | CONFIRMED | N/A | accepted (minor) |
| R14 | Coinbase full/level3 need auth | CONFIRMED | N/A | accepted (minor) |
| R15 | Databento free credit | CONFIRMED | N/A | accepted (minor) |
| R16 | local tick data has bid/ask with sizes | UNVERIFIABLE (no page says historical bid/ask includes sizes) | UNVERIFIABLE, leaning REFUTED: all 107,601 tick files are `*.Last.ncd`; 3–4-byte records | **UNRESOLVED → diagnostic run; design no longer depends on it** |

## Consequence for the design (correction of the earlier advice)

The earlier recommendation "start with a historical top-of-book detector on Tick Replay data you
already have" is **withdrawn**: R8 is rejected — Tick Replay supplies trades with bid/ask *prices* but
no displayed sizes, and the local tick store is trade-only. Without displayed size, "more traded than
shown" cannot be computed, so iceberg detection is **live and Market Replay (Playback) only**.
Depth (R6/R7) is market-by-price, so every detection is a *probable* iceberg.
Pending a NinjaTrader run of `EgvTickReplayDiag.cs`: R4, R9, R16.
