# validation/pytests — Channel B reference implementations and test suite

Self-contained pytest package (no imports from elsewhere in the repository) that implements
the built-in blocks B1–B9 and arithmetic modules M1–M23 of `validation/algo-claims-ledger.md`
**from the ledger's formula text only** and tests them on synthetic data, on trading-domain
invariants, and differentially against the NinjaTrader harness CSV.

## Run

From the repository root (`-I` isolates the interpreter from the current directory and
environment variables so no planted module can shadow a stdlib/third-party import):

```
python -I -m pytest validation/pytests -q              # everything (compile tests take ~1 min)
python -I -m pytest validation/pytests -q -m "not slow" # skip the C# compile probes
python -I -m pytest validation/pytests -q -k M23        # one claim
```

Requirements: `python -m pip install -r validation/pytests/requirements.txt`
(numpy 2.0.2, pandas 2.3.3, pytest 8.4.2, hypothesis 6.141.1 on python 3.9.13).

## Files

| file | purpose |
|---|---|
| `qi_ref.py` | pandas/numpy reference implementations, one function per ledger ID, assumptions documented inline |
| `conftest.py` | paths, CSV loaders (`harness`, `old_export` fixtures), synthetic bar helpers, `slow` marker, `CSV_QUANT` |
| `test_unit_builtins.py` | closed-form tests for B1–B9 + falsifiers |
| `test_unit_modules.py` | hand-constructed bars with known answers for M1–M23 + falsifiers |
| `test_properties.py` | hypothesis invariants: ranges, scale/shift (in)variance, causality, determinism, fallbacks, monotonicity + falsifiers |
| `test_data_integrity.py` | bar-data sanity of every `validation/runs/qi_dump_*.csv` and the first 20,000 rows of the original 150-tick export |
| `test_integration_harness.py` | P2 differential: one test per claim ID against the newest harness CSV; P3 falsifier (RSI 14→13) |
| `test_patterns_sanity.py` | value-set sanity for M24–M26 (exact replay is UNVERIFIABLE on Channel B) |
| `test_repo_invariants.py` | static brief checks on `indicators/*.cs` (the only place the C# is read, as text) |
| `test_compile_smoke.py` | `slow`: `validation/probes/compile_probe.sh` on every indicator + a mutant-must-fail test |

## Skips are not passes

The differential and pattern tests `pytest.skip` (verdict UNVERIFIABLE) when no
`validation/runs/qi_dump_*.csv` has data rows, or when the harness lacks the column a claim
needs. The harness writes values with `ToString("F4")`, so every differential tolerance is the
ledger tolerance plus `CSV_QUANT = 0.5e-4`.

`QI_HARNESS_FILE=<path>` makes the `harness` fixture read that file instead of the newest
`validation/runs/qi_dump_*.csv`. Use it only for smoke runs (e.g. a CSV generated from `qi_ref`
itself); a run against anything but a real NinjaTrader dump is not a verdict.

Known data findings (strict xfails in `test_data_integrity.py`): the original 150-tick export has
bar rows with one more field than its header (OHLCV at columns 15..19, not 14..18) and
consecutive tick bars sharing a 1-second timestamp; `conftest.load_old_export` aligns the columns
by the per-row field-count surplus.

Verdicts and verbatim run output: `validation/channel-b-algo.md`.
