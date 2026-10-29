# QI_28_IcebergDetector — specification and implementation claims (phase 2)

status: FROZEN 2026-10-28 after the phase-1 verdicts (research-report.md). Changes only by dated
amendment at the end of this file. Two implementations are built from THIS file independently:
the C# `IcebergEngine` (in the indicator) and the Python reference `backtest/qibt/iceberg.py`.
Neither may be derived from the other.

> Educational use only — not financial advice. The indicator labels order-book behaviour; it never
> says buy or sell.

## 0. Scope decided by phase 1

- Detection needs best bid/ask **with displayed sizes**. NinjaTrader supplies them live and in Market
  Replay (Playback); Tick Replay does not (R8 rejected). The indicator therefore detects only in
  `State.Realtime` (which includes Playback). In `State.Historical` it detects nothing and draws one
  fixed notice: "Iceberg detection runs on live or Market Replay data (historical Tick Replay has no
  bid/ask sizes)."
- Depth is market-by-price (R7): every detection is a *probable* iceberg.

## 1. Event stream (shared format for both implementations and the simulator)

CSV, header `seq,type,price,size,bid,ask`, one event per row in arrival order:
- `type = B` — best-bid update: `price` = best bid price, `size` = displayed size (integer ≥ 0).
- `type = A` — best-ask update, mirrored.
- `type = T` — trade: `price` = trade price, `size` = traded volume (integer > 0), `bid`/`ask` = best
  bid/ask **prices** at the trade (may be empty = unknown).
- `type = R` — session reset (all other fields empty).
Prices are decimals; two prices are equal when `|a − b| < 1e-9`. Empty fields are blank.

## 2. Parameters (defaults)

`HiddenRatio = 2.0`, `MinRefills = 2`, `MinVolume = 20`, `MinRefillSize = 1`.

## 3. Per-side level state (bid side described; ask side mirrored)

The engine keeps one *current level* per side: `price p`, `start_seq`, `shown_max`, `last_shown`,
`traded`, `refills`, `refill_sizes` (list), `pending` (bool: an absorbed trade happened since the last
size increase), `flagged` (bool), `flag_conf`.

**B event (price q, size s):**
1. If there is no current level, or `q ≠ p`:
   a. if a current level exists, *finalize* it (§5) with end reason by comparing q to p:
      bid side: `q > p` → `held`, `q < p` → `broken`; ask side: `q < p` → `held`, `q > p` → `broken`.
   b. if `s > 0`, start a new level: `p = q`, `start_seq = seq`, `shown_max = last_shown = s`,
      `traded = 0`, `refills = 0`, `refill_sizes = []`, `pending = false`, `flagged = false`.
      If `s == 0`, there is no current level afterwards.
2. Else (`q == p`):
   a. if `s == 0`: finalize with reason `broken`; no current level afterwards.
   b. else if `s > last_shown` and `pending` and `(s − last_shown) ≥ MinRefillSize`:
      `refills += 1`, append `s` to `refill_sizes`, `pending = false`.
   c. in all `s > 0` cases: `last_shown = s`, `shown_max = max(shown_max, s)`; then evaluate the flag (§4).

**T event (price x, volume v, bid b, ask a):**
- Classification: seller-initiated if b known and `x ≤ b` (with equality tolerance); buyer-initiated if a
  known and `x ≥ a`; otherwise unclassified (count it in `unclassified`, do nothing else). If both
  hold (b ≥ a, crossed), treat as unclassified.
- Seller-initiated and a current bid level exists and `x == p_bid`: `traded_bid += v`, `pending_bid = true`,
  then evaluate the bid flag. Buyer-initiated and `x == p_ask`: same on the ask side.
- Trades at other prices change nothing.

**R event:** finalize both current levels with reason `open`; no current levels afterwards.

## 4. Flag rule (evaluated after every change to a level)

If not `flagged` and `shown_max > 0` and `traded ≥ HiddenRatio × shown_max` and `refills ≥ MinRefills`
and `traded ≥ MinVolume`: set `flagged = true`, `flag_conf = conf()`, emit a FLAG record.

`conf() = clamp(0.4 + 0.15 × (refills − MinRefills) + 0.1 × (traded / shown_max − HiddenRatio), 0.4, 1.0)`.

## 5. Finalize

Only flagged levels produce a FINAL record; unflagged levels are discarded silently.

## 6. Output records (both implementations must emit exactly these, in emission order)

`FLAG,side,price,seq,traded,shown_max,refills,conf`
`FINAL,side,price,start_seq,end_seq,traded,shown_max,hidden_est,refills,median_refill,reason,conf`

- `side` ∈ {bid, ask}; `seq` = the event that triggered the flag; `end_seq` = the event that caused
  finalization; `hidden_est = traded − shown_max`; `median_refill` = median of `refill_sizes`
  (mean of the two middle values for an even count; 0 if empty); `conf` in FINAL = `conf()` with the final
  values (not clamped differently).
- Numbers: integers as integers; `price`, `conf`, `median_refill` formatted with exactly 4 decimals
  (`F4` / `%.4f`, round half away from zero is NOT required — compare numerically within 1e-4).
- When one event causes several records, order: bid side before ask side; FINAL before FLAG.

## 7. NinjaTrader indicator (C# only)

- Class/file `QI_28_IcebergDetector`; `IsOverlay = true`; `Calculate = Calculate.OnEachTick` is NOT
  needed — detection runs in `OnMarketData`; `OnBarUpdate` only advances plots.
- `OnMarketData`: map `MarketDataType.Bid/Ask` → B/A events (`e.Price`, `e.Volume`), `Last` → T event
  (`e.Price`, `e.Volume`, `e.Bid`, `e.Ask`). Only in `State.Realtime`. Session reset via `Bars.IsFirstBarOfSession`
  on the first tick of a new session → R event.
- Never overrides `OnMarketDepth` (depth is optional future work).
- Drawing: on FLAG a label at the price `Iceberg bid 7012.25 ~340 hidden (6 refills, 82%)` (no buy/sell
  words, no arrows) and a short horizontal line; on FINAL the label text is updated with the reason.
- DataBox-only (transparent) plots per bar: `IcebergBidVolume`, `IcebergAskVolume` (sum of `hidden_est`
  of levels FINALIZED in the bar), `IcebergCount` (FLAG records in the bar), `MaxConfidence`.
  Exposed as public `Series<double>` with those names.
- Properties: HiddenRatio, MinRefills, MinVolume, MinRefillSize, ShowLabels (true), BidBrush, AskBrush,
  ShowDisclaimer (false). Disclaimer header and Description sentence as in the other QI files.
- `IcebergEngine` is a top-level public class in the same file, depending on `System` only, with:
  `IcebergEngine(double hiddenRatio, int minRefills, long minVolume, long minRefillSize)`,
  `List<string> OnBid(long seq, double price, long size)`, `OnAsk(...)`,
  `OnTrade(long seq, double price, long volume, double bid, double ask)` (`double.NaN` = unknown),
  `OnReset(long seq)`, each returning the records it emitted as CSV lines per §6.

## 8. Implementation claims (I-claims)

| ID | Mat | Claim | Probe (pre-registered) |
|----|-----|-------|------------------------|
| I1 | M | `QI_28_IcebergDetector.cs` compiles standalone and with all indicators and strategies. | compile_probe.sh; falsifier: type error → rc≠0 |
| I2 | M | C# `IcebergEngine` and the Python reference emit identical records on the same event streams. | console harness: 200 simulated sessions through the compiled C# engine, diff vs Python (prices/conf within 1e-4, all else exact); falsifier: HiddenRatio 2.0→1.9 on one side → diff non-empty |
| I3 | M | On simulated books, recall of planted icebergs ≥ 0.90 and false-alarm rate on decoys ≤ 0.10 at default parameters. | booksim, 200 sessions, seed 20261028; decoys = large single resting order, crowd joining without trades, small market-maker requotes; falsifier: HiddenRatio 1.0, MinRefills 0 → false-alarm rate > 0.10 |
| I4 | M | No look-ahead: feeding a prefix of a stream yields exactly the records the full stream emits up to that prefix's last event. | metamorphic test, Python and C# |
| I5 | M | Classification and every rule in §3 hold on hand-built streams (one test per rule branch). | unit tests (Python) + the I2 diff carries them to C# |
| I6 | M | The indicator never overrides OnMarketDepth and detects only in State.Realtime. | static test |
| I7 | M | Repo invariants: disclaimer in three places, no buy/sell words or arrows, overlay flag. | tests/indicators/test_IcebergDetector.py + validation/pytests |
| I8 | M | In NinjaTrader Playback (Market Replay) the indicator receives Bid/Ask/Last events with sizes and flags levels without errors. | user run (pending), together with EgvTickReplayDiag (R4/R9/R16) |

Known limitation (documented, not tested as a false alarm): a market maker that re-quotes the same
price after every fill with large volume is indistinguishable from an iceberg on price-level data.
