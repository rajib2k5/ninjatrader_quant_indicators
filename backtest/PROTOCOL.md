# Backtest protocol (pre-registered)

Frozen 2026-10-17, before any backtest was run. Rules: `backtest/rules.yaml`. Claims audited in
`validation/backtest-claims-ledger.md`. Changes only by dated amendment in section 9.

> Educational research only. Not financial advice. A backtest describes how a fixed rule would
> have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

## 1. Question

For each indicator, take the original IBSFade indicator's own Buy/Neutral/Sell classification of
that indicator's value (no new rules, no parameter search) and measure how a one-contract MES
position following that classification would have performed, net of costs. Use the result only
to **order** the indicators (QI_01 … QI_25), never as a performance promise.

## 2. Data

- **Primary (ranking) dataset P1:** MES continuous, 1-minute bars, 2020-01-03 → 2026-02-24,
  exported by NinjaTrader 8 (back-adjusted merge; bar time = bar close, US Central Time) — the six
  `MES_1min_*.csv` files in `C:\Users\rajib\OneDrive\Docs\futures_data\ninja_trader_signal_data\data\`.
  Bar rows only (SignalType empty); OHLCV read by header name with the per-row surplus-field shift
  (`validation/probes/diff_values.py` layout logic). Overlapping timestamps across files are
  de-duplicated (first occurrence wins). Raw data is **never committed** (vendor data, personal use).
- **Robustness datasets** (reported, never used for the ranking): online datasets selected in
  `docs/DATASETS.md` and approved by the user before download; any other local market files.

## 3. Bars and sessions

- Trading date of a 1-minute bar = its calendar date, plus one day if its close time is after
  17:00 CT (Globex reopens 17:00 CT). Sessions with no bars are absent (no synthetic bars).
- **D frame:** one bar per trading date. Open = first 1-minute open, High = max, Low = min,
  Close = last close, Volume = sum.
- **15m frame:** 15-minute bars labelled by their close time; a 1-minute bar closing at t belongs
  to the bar closing at ceil(t, 15 min). Same OHLCV aggregation. Bars never span a trading date.
- Indicator values are computed on the frame's bars from the first bar of P1 (warm-up uses 2020).

## 4. Positions and execution

- At the close of bar t the rule maps the indicator value to a target position p_t ∈ {+1, 0, −1}
  (−1 never for long-only rules). A NaN/unset value maps to 0.
- p_t is executed at the **open of bar t+1** and held until the open of bar t+2, where p_{t+1}
  takes over. No intrabar stops or targets. One MES contract.
- Gross P&L of bar t+1 (USD) = p_t × (Open_{t+2} − Open_{t+1}) × 5. The last bar of the data
  carries no P&L.
- Point differences are used (not percent returns) because P1 is additively back-adjusted.

## 5. Costs

Per contract per side, charged at every change of position by |p_t − p_{t−1}| sides:
- commission and exchange/NFA fees: **USD 1.00** (assumption; must be ≥ the published all-in
  rate — ledger BT3);
- slippage: **1 tick = 0.25 index points = USD 1.25**;
- base total **USD 2.25 per side** (USD 4.50 per round turn). Sensitivity runs: 0× and 2×.

## 6. Evaluation window and aggregation

- P&L is counted for trading dates 2021-01-04 → 2026-02-24 only (same window for every rule and
  both frames; 2020 is warm-up). Stability halves: H1 2021-01-04 → 2023-07-31, H2 2023-08-01 →
  2026-02-24.
- 15m P&L is summed per trading date, so every rule produces one daily USD P&L series over the
  same set of trading dates (flat days are 0 and are included).

## 7. Metrics (per rule, per dataset)

- Annualised Sharpe SR = mean(daily P&L) / std(daily P&L, ddof=1) × √252.
- Probabilistic Sharpe Ratio PSR(0) and Deflated Sharpe Ratio DSR (Bailey & López de Prado 2012,
  2014) on the per-day (non-annualised) SR with sample skewness and (non-excess) kurtosis;
  DSR's trial count N = 25 and V[SR] = sample variance of the 25 per-day SRs on P1.
- Also: total net P&L (USD), max drawdown of cumulative P&L (USD), number of position changes,
  exposure (% of days with p ≠ 0), long/short split, SR on H1 and H2, SR at 0× and 2× costs.
- Benchmark: buy-and-hold one MES from the first evaluation open (one entry cost), reported
  alongside; every rule's correlation with it is reported (long-biased rules inherit drift).

## 8. Ranking and relabel

- Rank the 25 backtestable rules by **SR on P1 at base costs over the full window**, highest
  first. Ties (|ΔSR| < 0.005): higher DSR, then module name A→Z.
- The two non-backtestable modules (ChopIndex, KeyLevels) take the last numbers, A→Z.
- Relabel: class/file/Name `QI_<NN>_<Module>` (NN = 01…27), strategies `QS_<NN>_<Module>`,
  harness `QIV_<NN>_<Module>`. The README shows the full metrics table, DSR, the benchmark, and
  states that ranks are not significance-tested differences unless DSR says so.

## 9. Amendments

### A1 (2026-10-17) — D-frame close = NinjaTrader's daily settlement close

**Why.** §1 measures the original indicator's own classification. The original reads NinjaTrader's
daily bars, and the adversarial validation (`validation/adversarial-ranking.md` §5) showed that those
bars close at the CME **settlement** price, not at the 16:00 CT last trade that §3 used: the close
implied by the original's own IBS values lies on the 0.25 tick grid on 98.9% of dates (chance 2.8%),
a median 0.75 points from the 15:00 CT one-minute close. §3 therefore contradicted §1.

**Disclosure.** This amendment was made after the v1 results and the validator's preview of the
amended results had been seen, and the user chose it among four options (keep v1; 15:00 proxy;
inferred settlement; wait for an exact NinjaTrader Day-bar export).

**Change.** For each trading date, the D-frame Close is
`snap_0.25(L + IBS_ORIG × (H − L))`, where H and L are the D-frame high and low (full 17:00–16:00
session, unchanged) and IBS_ORIG is the original indicator's `databox_IBS` on that date's last
1-minute bar in P1. If the unsnapped value is more than 0.01 points from the 0.25 grid, or IBS_ORIG
is missing, or H = L, the Close is the close of the 1-minute bar ending at 15:00 CT (CME's equity
index settlement window ends at 15:00 CT); if that bar is missing too, the last close. Open, High,
Low and Volume are unchanged. The 15m frame is unchanged.

**Reporting.** v1 (16:00 last trade) is kept in `results/v1_last_trade/`. The ranking (§8) uses A1.
The README shows v1, A1 and a 15:00-close variant side by side, with the block-bootstrap rank
probabilities. A later exact NinjaTrader Day-bar export, when available, is a cross-check of the
inferred closes (expected: equal on every on-grid date).
