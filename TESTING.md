# Testing

Two kinds of tests: the ones that run anywhere with Python, and the ones that need values
exported from NinjaTrader. Python 3.9+; `pip install -r backtest/requirements.txt`
(pandas, numpy, pytest, hypothesis, pyyaml) and `pip install -e backtest` for the `qibt` package.

## 1. Run anywhere (no NinjaTrader)

```
python -I -m pytest -q -m "not slow"                     # everything below, from the repo root (pytest.ini)
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
3. New chart: MES, **5 Minute**, about 30 days. Indicators… → add all 28 **`QIV NN … (validation)`**
   entries (they are subclasses of the real indicators that also write CSV) → OK. Wait until the
   chart has loaded.
4. In the repo:
   ```
   python -I validation/probes/merge_runs.py          # joins the 28 exports into validation/runs/qi_dump_MES_Minute-5.csv
   python -I -m pytest tests/indicators -q            # the export tests now run instead of skipping
   ```
5. Optional, daily frame: repeat step 3 on a **Day** chart; the export file is per bar period.

## 3. Backtest strategies in Strategy Analyzer

Copy `strategies/*.cs` to `...\bin\Custom\Strategies\quant_strategies\`, F5, then Strategy Analyzer
→ MES, Day bars (15 Minute for the 15m rules), 2021-01-04 → 2026-02-24, commission per your plan.
Compare with `results/REPORT.md` (expect small differences from NinjaTrader's fill model;
claims BT5/BT15 in `validation/backtest-report.md`).

## 4. Iceberg detector (QI_28) — needs a NinjaTrader run

The rules are fully tested without NinjaTrader:

```
python -I -m pytest backtest/tests/test_iceberg.py -q                 # rules, simulator recall/false alarms, no look-ahead
bash validation/iceberg/harness/build_harness.sh                      # builds the C# engine as a console exe
python -I validation/iceberg/diff_engines.py                          # C# engine vs Python reference, 1,006 runs
python -I validation/iceberg/diff_engines.py --falsify                # must report differences (HiddenRatio 1.9 vs 2.0)
bash validation/iceberg/harness/build_tests.sh && validation/iceberg/harness/_out/TableTests.exe   # table + box placement
```

Three facts can only be checked inside NinjaTrader (claims R4, R9, R16 and I8 in
`validation/iceberg/`). The diagnostic indicator `validation/iceberg/EgvTickReplayDiag.cs` only counts
events and prints them to the Output window. It places no orders.

1. Copy `validation/iceberg/EgvTickReplayDiag.cs` to `...\Indicators\quant_indicator\_validation\`,
   F5. Open **New › NinjaScript Output**.
2. **Tick Replay run (R8 / R16):** MES chart, 1 Minute, 2 days, *Tick Replay* ticked in Data Series.
   Add `EgvTickReplayDiag`. Copy the lines starting `EGV|` from the Output window. Expected from
   the docs: in the `Hist` bucket `Bid=0 Ask=0`, or `BidVol>0=0 AskVol>0=0` (no historical sizes).
3. **Market Replay run (R4 / R9 / I8):** Connections › Playback. Use a Market Replay day you already have (this PC has GC 04-26)
   or download one in Tools › Historical Data. Open a 1 Minute chart of that instrument and add both
   `EgvTickReplayDiag` and `QI 28 IcebergDetector`. Press Play for 15–30 minutes of market time.
   Expected: in the `Realtime` bucket `BidVol>0` and `AskVol>0` are non-zero and `Depth` > 0; the QI 28 table box
   sits at the lower right of the price panel, newest row first, with `#n` tags at the flagged prices and
   no errors in the Log tab. To check the overlap rules, also add `QI 12 HedgingPressure` (score box, top right),
   switch on `Show Disclaimer`, and add a second QI 28 (its box must stack above the first). Take one screenshot
   (claims P7, T5/T6/T15–T18 in `validation/iceberg/table-report.md`).
4. Paste the `EGV|` lines (and a screenshot) back to the assistant. They are recorded in
   `validation/iceberg/addenda.md` to close R4/R9/R16/I8.
