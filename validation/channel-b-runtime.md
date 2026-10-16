# Channel B — NinjaTrader runtime probes (executed by the orchestrator)

Rules followed: channel-a-*.md were not read before these probes ran; the probe commands are the
ones pre-registered in claims-ledger.md; outputs are verbatim.

## C14 — all 27 files compile inside NinjaTrader's NinjaScript editor (LangVersion 13, real Custom project)

Setup: files copied to `Documents\NinjaTrader 8\bin\Custom\Indicators\quant_indicator\` (27 `QI_*.cs`)
and `quant_indicator\_validation\QI_EgvDump.cs`; the user pressed F5 in the NinjaScript editor
(NinjaTrader is view-only to the orchestrator). Evidence, 2026-10-15:

```
$ grep -cE "quant_indicator|QI_" NinjaTrader.Custom.csproj
28
$ ls -l --time-style=+%Y-%m-%d_%H:%M NinjaTrader.Custom.csproj  -> 2026-10-15_22:56
$ ls -l --time-style=+%Y-%m-%d_%H:%M NinjaTrader.Custom.dll     -> 2026-10-15_22:57   (was 2026-10-11_13:52 before)
$ python -I - (byte scan of NinjaTrader.Custom.dll for rb"QI_[A-Za-z0-9]+")
28 QI_ type names in NinjaTrader.Custom.dll:
QI_ATRRegime QI_BollingerPctB QI_ChopIndex QI_CompositeVol QI_ConnorsRSI QI_ConsecDays QI_EMACross
QI_EgvDump QI_HedgingPressure QI_IBS QI_KeyLevels QI_LiquiditySweep QI_MACDHistogram QI_OrderFlowPlus
QI_OvernightGap QI_RSI14 QI_RSI2 QI_RVZScore QI_SMA200Trend QI_SMC QI_StochFade QI_TurnOfMonth
QI_TurnaroundTuesday QI_VRPProxy QI_VWAPDistance QI_VolumeDelta QI_VolumeSpike QI_WideRangeBar
control IBSFade present: True
```

NinjaTrader only rewrites `NinjaTrader.Custom.dll` on a successful compile, and the project file
now lists every file; the DLL contains all 28 types. Falsifier: the same byte scan on the
pre-compile DLL (mtime 2026-10-11) could not have contained these names — they did not exist in
any source NinjaTrader had seen; not re-run because that DLL was overwritten. Screen check: the
NinjaScript editor's explorer tree shows `Indicators > quant_indicator` with all QI_ files.

Verdict: **CONFIRMED** (compile-side). Note: NinjaTrader did not append its generated-code region
to the externally-added files (it does so only when a file is saved from its editor); the
`.cs` files in the NinjaTrader folder therefore remain byte-identical to the repository.

## C2 / C4 / C5 / C8 / C9 / C10 behavioral halves, C18–C44 differential — pending the chart run
(filled in below as the runs happen)
