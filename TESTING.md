# Testing

Two kinds of tests: the ones that run anywhere with Python, and the ones that need values
exported from NinjaTrader. Python 3.9+; `pip install -r backtest/requirements.txt`
(pandas, numpy, pytest, hypothesis, pyyaml) and `pip install -e backtest` for the `qibt` package.

## 1. Run anywhere (no NinjaTrader)

```
python -I -m pytest tests/indicators -q -m "not slow"     # one test file per indicator
python -I -m pytest validation/pytests -q -m "not slow"   # reference formulas, properties, repo invariants
python -I -m pytest backtest/tests -q -m "not slow"       # backtest engine, metrics, strategies (static)
```

Add `-m slow` (or drop `-m`) to also compile every indicator and strategy against the installed
NinjaTrader assemblies (`validation/probes/compile_probe.sh`; needs Git Bash and the .NET 8 SDK)
and to run the P1 data tests (need the MES files on this machine).

Where the unit tests for each indicator are: `tests/indicators/test_<Name>.py`, e.g.
`tests/indicators/test_ConsecDays.py` for `QI_01_ConsecDays`. Each file has:

1. formula tests with hand-computed expected values;
2. the C# interface contract (plots, exposed series, reference lines, defaults);
3. a single-file compile (slow);
4. a comparison with values exported from NinjaTrader (skipped until you export — section 2);
5. at least one `test_falsifier_*` showing the formula tests reject a plausible wrong formula.

`tests/indicators/test_coverage.py` fails if any indicator lacks such a file.

## 2. Test the real NinjaScript code in NinjaTrader (the export comparison)

The C# runs only inside NinjaTrader. These steps make NinjaTrader write each indicator's values to
CSV so section 4 of every test file can compare them with the reference formulas.

1. Copy `indicators/*.cs` to `Documents\NinjaTrader 8\bin\Custom\Indicators\quant_indicator\` and
   `validation/harness/*.cs` to `...\Indicators\quant_indicator\_validation\`.
2. NinjaScript Editor → **F5**.
3. New chart: MES, **5 Minute**, about 30 days. Indicators… → add all 27 **`QIV NN … (validation)`**
   entries (they are subclasses of the real indicators that also write CSV) → OK. Wait until the
   chart has loaded.
4. In the repo:
   ```
   python -I validation/probes/merge_runs.py          # joins the 27 exports into validation/runs/qi_dump_MES_Minute-5.csv
   python -I -m pytest tests/indicators -q            # the export tests now run instead of skipping
   ```
5. Optional, daily frame: repeat step 3 on a **Day** chart; the export file is per bar period.

## 3. Backtest strategies in Strategy Analyzer

Copy `strategies/*.cs` to `...\bin\Custom\Strategies\quant_strategies\`, F5, then Strategy Analyzer
→ MES, Day bars (15 Minute for the 15m rules), 2021-01-04 → 2026-02-24, commission per your plan.
Compare with `results/REPORT.md` (expect small differences from NinjaTrader's fill model;
claims BT5/BT15 in `validation/backtest-report.md`).
