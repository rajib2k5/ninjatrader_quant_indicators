# qibt - pre-registered backtest of the QI classifications

> Educational research only. Not financial advice. A backtest describes how a fixed rule would
> have behaved on past data under stated assumptions; it is not a forecast. See DISCLAIMER.md.

The specification is frozen: `PROTOCOL.md`, `rules.yaml` and `validation/backtest-claims-ledger.md`.
Where they are silent, the reading used is recorded in `IMPLEMENTATION_NOTES.md`.

## Install (once)

`python -I` removes the current directory from `sys.path`, so `python -I -m qibt.cli` only works
when qibt is installed. From the repository root:

```
python -s -m pip install -r backtest/requirements.txt
python -s -m pip install --no-deps --no-build-isolation -e backtest
```

The second command is an editable install: it adds `backtest/` to the global site-packages
(`easy-install.pth`), so code changes take effect without reinstalling. Remove it with
`python -s -m pip uninstall qibt`.

## Run (from the repository root)

The D-frame close follows PROTOCOL amendment A1 (`--close settle`, the default): NinjaTrader's
settlement close, inferred as snap_0.25(L + IBS_ORIG x (H - L)) from the original indicator's
`databox_IBS`, with the 15:00 CT one-minute close (then the last close) as fallback. `--close last`
is the pre-registered v1 (16:00 last trade); `--close 1500` is the 15:00 CT one-minute close.

```
# A1 (the ranking), v1 and the 15:00 variant, each at 1x / 0x / 2x costs
python -I -m qibt.cli run --dataset P1 --costs 1 --close settle --out results
python -I -m qibt.cli run --dataset P1 --costs 0 --close settle --out results
python -I -m qibt.cli run --dataset P1 --costs 2 --close settle --out results
python -I -m qibt.cli run --dataset P1 --costs 1 --close last --out results/v1_last_trade      (and 0, 2)
python -I -m qibt.cli run --dataset P1 --costs 1 --close 1500 --out results/close_1500         (and 0, 2)
# block-bootstrap rank probabilities of the A1 ranking, and v1 / A1 / 15:00 side by side
python -I -m qibt.cli bootstrap --results results          -> results/BOOTSTRAP.md
python -I -m qibt.cli sensitivity --results results        -> results/SENSITIVITY.md
```

| File | Content |
|---|---|
| `results/metrics_P1.csv` | one row per rule + the `BuyHold` benchmark: SR, PSR, DSR (+ `dsr_log`), P&L, MDD, exposure, trades, H1/H2 SR, 0x/1x/2x SR and P&L, correlation with buy-and-hold |
| `results/daily_pnl_P1.csv` | net daily USD P&L per rule on the evaluation calendar (flat days = 0) |
| `results/ranking.csv` | rank, module, status, SR, DSR, new names (`QI_NN_`, `QS_NN_`, `QIV_NN_`); input of `backtest/relabel.py` |
| `results/REPORT.md` | run facts, D-close branch counts, data coverage, ranking table, benchmark row |
| `results/BOOTSTRAP.md` | stationary block bootstrap (mean block 10 days, 1,000 resamples, seed 12345, all rules on the same days) |
| `results/SENSITIVITY.md` | SR and rank per rule under v1 / A1 / 15:00 at 0x/1x/2x, A1 H1/H2 |
| `results/v1_last_trade/`, `results/close_1500/` | the same files for v1 and the 15:00 variant |
| `results/equity_P1.png` | only if matplotlib imports under `python -I` |

`--costs` other than 1 writes the same files with the suffix `_cost0x` / `_cost2x`; the ranking of
PROTOCOL section 8 is the A1 `--costs 1` one. A rule whose pattern port (`qibt/patterns.py`) is missing
or raises is reported as `pending` (no rank) instead of failing the run. DSR/PSR below 0.001 are
printed in scientific notation; ties are decided on log DSR, so values that underflow still count.

Robustness datasets (plain OHLCV CSV, bar time = close time, US Central unless `--source-tz`):

```
python -I -m qibt.cli run --dataset path/to/file.csv --date-col Date --time-col Time --source-tz UTC --out results
```

Outputs are tagged with the file stem (`metrics_<stem>.csv`, `ranking_<stem>.csv`, `REPORT_<stem>.md`).
`--no-halt-check` disables the 16:00-17:00 CT halt check for markets with other hours.

Without installing: `cd backtest` and `python -m qibt.cli run ... --out ../results` (not isolated).

## Robustness datasets R1 / R3 (PROTOCOL A3)

Reported next to the ranking; they never change it. Needs `spy_us_d.csv` (R1, Stooq SPY.US daily)
and `es_f_d.csv` (R3, Stooq ES.F daily), downloaded in a browser (Stooq serves an HTML bot-check
page to scripts; the loader rejects such a file with a clear error). From the repository root:

```
python -I -m qibt.cli robustness --data-dir "C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_data\stooq" --p1-metrics results/metrics_P1.csv --out results/robustness
```

(`--data-dir` defaults to that folder.) Writes `results/robustness/{R1,R3,R3_unfiltered}_{full,p1window}_metrics.csv`
(the metrics columns plus `rank_sr`) and `results/robustness/ROBUSTNESS.md`: a MANIFEST (file,
SHA-256, data rows, first/last date) and, per dataset and window, each rule's SR and rank among the
18 D-frame rules and the Spearman rank correlation with P1's A1.1 SRs of the same rules.

Readings of A3 used by `qibt/robustness.py` (where A3 is silent):
- Stooq columns are read by header name; extra columns are ignored, rows with an empty OHLC value
  are dropped, duplicate dates keep the first row. R1 = OHLC x 10, Volume as delivered; R3 starts
  1997-09-09. Trading date = the row's Date (no 17:00 roll, no settlement inference).
- Warm-up: values are computed from the first bar; the full window starts at the date of bar 300
  (the 301st bar), so the first counted execution is the one decided at bar 299. The P1 window is
  2021-01-04 -> 2026-02-24 (clipped to the data).
- Roll window: +-5 trading days around the third Friday of Mar/Jun/Sep/Dec, anchored on the first
  trading date on or after that Friday (a holiday Friday anchors on the next trading date).
- Roll gap: |Open_t - Close_{t-1}| > 3 x the median of the previous 60 gaps (t-60 .. t-1; all 60 needed).
- "Open-to-open interval contains the roll date r": bar r-1 (Open_{r-1} -> Open_r, which carries
  the Close_{r-1} -> Open_r jump) and bar r (Open_r -> Open_{r+1}) get gross P&L 0 for every rule and
  for buy-and-hold; costs of executions on those bars are still charged.
- HedgingPressure on R3: status `not_available`, reason `n/a (no volume)`; left out of the R3 ranks
  and Spearman (17 rules). Rank = SR order (exact ties A->Z), no DSR tie-break; Spearman uses
  average ranks of the SRs; a rule that never trades (no SR) is left out of both.
- DSR on these datasets uses N = 18 and that run's V[SR]; H1/H2 SRs only for the P1 window.

## Data

P1 = the six `MES_1min_*.csv` NinjaTrader EveryBar exports (path in `qibt/data.py`). The first load
parses them (about 30 s) and caches the 1-minute frame in `backtest/data/P1_1min.pkl` (git-ignored;
rebuilt automatically when a source file's size or time changes; `--refresh-cache` forces it).
Raw data is never written anywhere else.

## Tests (from the repository root)

```
python -I -m pytest backtest/tests -q -p no:cacheprovider -m "not slow"
python -I -m pytest backtest/tests -q -p no:cacheprovider -m slow
```

The slow tests need the P1 files (skipped otherwise): two full P1 runs must agree to 1e-9 and the
daily P&L must reconcile with an independent bar loop. Each unit/property file has `test_falsifier_*`
tests that show a deliberately wrong variant is caught.

## Layout

| Module | PROTOCOL | Content |
|---|---|---|
| `qibt/data.py` | 2-3, 9 A1 | EveryBar reader (per-row shift, + databox_IBS), cache, generic CSV loader, trading date, D frame (close modes) and 15m frame |
| `qibt/signals.py` | 4 | rules.yaml, condition parser (no eval), value names -> `validation/pytests/qi_ref.py` / `qibt/patterns.py` |
| `qibt/engine.py` | 4-6 | execution at the next open, P&L, costs, window, daily aggregation, buy-and-hold |
| `qibt/metrics.py` | 7 | Sharpe, PSR, DSR, max drawdown, moments |
| `qibt/rank.py` | 8 | ranking with the tie rule, non-backtestable modules last |
| `qibt/bootstrap.py` | 9 A1 | stationary block bootstrap of the rank order |
| `qibt/robustness.py` | 9 A3 | Stooq loaders, R3 roll-gap filter, robustness runs, Spearman, ROBUSTNESS.md |
| `qibt/cli.py` | - | pipeline, outputs, `run` / `bootstrap` / `sensitivity` / `robustness` subcommands |
