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
| `qibt/cli.py` | - | pipeline, outputs, `run` / `bootstrap` / `sensitivity` subcommands |
