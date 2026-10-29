# Iceberg detector — research claims ledger (phase 1, before any implementation)

status: FROZEN 2026-10-28. No claim may be added, dropped or reworded after this line; misses go to
`validation/iceberg/addenda.md` and run through both channels fresh.
purpose: confirm the facts the free-iceberg-detection plan rests on, before code is written.
environment: `validation/env-pin.txt` (NinjaTrader 8.1.8.3, NinjaTrader.Core.dll / NinjaTrader.Gui.dll
FileVersion 8.1.8.3 in C:\Program Files\NinjaTrader 8\bin; .NET Framework 4.8; Roslyn from .NET SDK 8.0.100)
mode: Mode 1 (dual subagent). Channel A = documentation only (NinjaTrader help guide matched to 8.x,
exchange/vendor official pages). Channel B = runtime only (reflection on the installed NinjaTrader
assemblies, compile probes with falsifiers, local files) — no documentation.
Every material claim starts REJECTED.

| ID | Cat | Mat | Claim (one sentence) | Falsifier | Channel B probe (pre-registered) |
|----|-----|-----|----------------------|-----------|----------------------------------|
| R1 | api | M | NinjaScript `Indicator` has an overridable `OnMarketData(MarketDataEventArgs)` method. | no such virtual method on `NinjaScriptBase`/`Indicator` | reflection on NinjaTrader.Core.dll/Gui.dll; compile an override; falsifier: misspelled override → CS0115 |
| R2 | api | M | `MarketDataEventArgs` exposes `MarketDataType`, `Price`, `Volume`, `Time`, `Bid` and `Ask`. | any member missing | reflection listing public properties + types; compile a probe reading all six; falsifier: read `.Size` → CS1061 |
| R3 | api | M | The `MarketDataType` enum includes `Last`, `Bid` and `Ask`. | any value missing | reflection on the enum values |
| R4 | sem | M | For `MarketDataType.Bid`/`Ask` events, `Volume` is the displayed size at the best bid/ask (not a traded quantity). | docs define it otherwise | N/A-by-construction until split (semantic, docs-decidable; runtime needs a live feed) |
| R5 | api | M | NinjaScript has an overridable `OnMarketDepth(MarketDepthEventArgs)` method. | missing | reflection; compile override; falsifier misspelled → CS0115 |
| R6 | api | M | `MarketDepthEventArgs` exposes `MarketDataType`, `Operation`, `Position`, `Price`, `Volume` (price-level depth). | any member missing | reflection listing public properties |
| R7 | api | M | NinjaScript's depth events carry no per-order identifier (they are market-by-price, not market-by-order). | a public order-id-like member on `MarketDepthEventArgs` (e.g. OrderId, OrderID, Id) | reflection: list ALL public members of `MarketDepthEventArgs` and its base types; report any id-like member |
| R8 | sem | M | During Tick Replay, `OnMarketData` is called for historical bars with bid/ask/last events in their original sequence. | docs say Tick Replay calls only OnBarUpdate / no bid-ask | N/A-by-construction until split (docs; runtime needs NinjaTrader run) |
| R9 | sem | M | `OnMarketDepth` is NOT called for historical data or Tick Replay, but is called during Market Replay (Playback). | docs say otherwise | N/A-by-construction until split |
| R10 | env | M | Market Replay data holds Level 1 and Level 2 (depth) in exact sequence and can be downloaded from NinjaTrader's servers for free for a limited set of instruments and dates. | docs: no download / paid / L1 only | local probe: inspect C:\Users\rajib\Documents\NinjaTrader 8\db\replay (existing GC 04-26 files: names, sizes) — supporting only |
| R11 | env | m | NinjaTrader can record Market Replay data from a live connection (an option under Tools › Options › Market data). | no such option | N/A-by-construction (UI) |
| R12 | env | M | CME Globex supports a native display-quantity ("iceberg") limit order. | CME docs say no | N/A-by-construction (exchange fact) |
| R13 | env | m | Binance spot supports iceberg orders via an `icebergQty` order parameter. | official API docs lack it | N/A-by-construction |
| R14 | env | m | Coinbase Exchange's `full`/`level3` WebSocket channels require authentication. | official docs say unauthenticated | N/A-by-construction |
| R15 | env | m | Databento gives new accounts free usage credit. | pricing page says no | N/A-by-construction |
| R16 | data | M | The ES/MES tick data already on this machine contains historical bid/ask events with sizes (needed for a historical, backtestable top-of-book detector). | tick store holds last trades only | local probe: inspect C:\Users\rajib\Documents\NinjaTrader 8\db\tick (file names/sizes/structure only; binary format) — expected UNVERIFIABLE by file inspection; decisive probe = NinjaTrader run of a diagnostic indicator (user) |

Claim count: 16 (11 material, 5 minor).
