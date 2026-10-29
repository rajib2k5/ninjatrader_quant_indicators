# Iceberg research ledger — Channel B (runtime auditor)

date: 2026-10-28
ledger: `validation/iceberg/research-claims-ledger.md` (FROZEN 2026-10-28; claims read verbatim, not reworded)
method: empirical only — reflection on the installed assemblies, compile probes with falsifiers
(`validation/probes/compile_probe.sh`), read-only inspection of local NinjaTrader data files. No
documentation, help pages, forums or web were consulted. No Channel A file was read.
scratch dir (all probe sources, mutants, DLLs, raw logs):
`C:\Users\rajib\AppData\Local\Temp\claude\C--Users-rajib-OneDrive-Documents\533a663d-5efe-42d6-aafd-bb6df2ee5fa2\scratchpad\iceberg_chanB\`
Nothing in `C:\Program Files\NinjaTrader 8` or `C:\Users\rajib\Documents\NinjaTrader 8` was modified
(reads only; compiled DLLs went to the scratch dir).

## Toolchain actually in effect

| item | observed |
|---|---|
| NinjaTrader.Core.dll | Assembly `NinjaTrader.Core, Version=8.1.8.4`, **FileVersion 8.1.8.4**, LastWriteTime 2026-10-19 00:35:26 |
| NinjaTrader.Gui.dll | `Version=8.1.8.4`, FileVersion 8.1.8.4 |
| NinjaTrader.Custom.dll | `Version=8.1.9.0` (no FileVersion) |
| compiler | Roslyn csc from .NET SDK 8.0.100 (`-langversion:latest` = C# 12), via compile_probe.sh, 17 refs |
| reflection host | Windows PowerShell 5.1 (.NET Framework 4.8 CLR) |

**ENVIRONMENT DRIFT (finding):** the ledger header and `validation/env-pin.txt` pin NinjaTrader
8.1.8.3; the installed Core/Gui are **8.1.8.4** (file written 2026-10-19, after the 2026-10-15
env-pin). All verdicts below are for 8.1.8.4. Channel A should match docs to 8.1.8.x; the env-pin
should be re-recorded.

Reflection note: `NinjaTrader.Gui.GetTypes()` raised ReflectionTypeLoadException
(`Could not load file or assembly 'System.Collections.Immutable, Version=9.0.0.0'`); the non-null
`.Types` were used (8,066 types total across Core+Gui+Custom). All types relevant to these claims
live in NinjaTrader.Core (loaded without error) or Custom, so this does not affect any verdict. A
first attempt with an AssemblyResolve handler died with `Process is terminated due to
StackOverflowException.` (handler recursion) — that run produced no data and was discarded; the
handler was removed and the script rerun.

## Verdict table

| ID | verdict | basis |
|----|---------|-------|
| R1 | **CONFIRMED** | `protected virtual void OnMarketData(MarketDataEventArgs marketDataUpdate)` declared on NinjaScriptBase, inherited by IndicatorBase → IndicatorRenderBase → Indicator; override compiles rc=0; misspelled override CS0115 rc=1 |
| R2 | **CONFIRMED** | public get-only properties MarketDataType (MarketDataType), Price (double), Volume (long), Time (DateTime), Bid (double), Ask (double); probe reading all six rc=0; `.Size` CS1061 rc=1 |
| R3 | **CONFIRMED** | enum NinjaTrader.Data.MarketDataType = Ask 0, Bid 1, Last 2, DailyHigh 3, DailyLow 4, DailyVolume 5, LastClose 6, Opening 7, OpenInterest 8, Settlement 9, Unknown 10; compile using Last/Bid/Ask rc=0; `MarketDataType.Trade` CS0117 rc=1 |
| R4 | N/A-by-construction (Channel A / NinjaTrader run) | |
| R5 | **CONFIRMED** | `protected virtual void OnMarketDepth(MarketDepthEventArgs marketDepthUpdate)` on NinjaScriptBase, inherited by Indicator; override compiles rc=0; misspelled override CS0115 rc=1 |
| R6 | **CONFIRMED** | public get-only MarketDataType, Operation (NinjaTrader.Cbi.Operation: Add 0, Update 1, Remove 2), Position (int), Price (double), Volume (long); probe reading all five rc=0; `.Postion` CS1061 rc=1 |
| R7 | **CONFIRMED** (API surface) | complete public member list of MarketDepthEventArgs (and base EventArgs/Object) has no order-id-like member; id-scan rc=0 (no hits) while the same scan on NinjaTrader.Cbi.Order fires (ClientId, Id, OrderId) rc=1; compile probes reading OrderId / OrderID / Id / OrderIdentifier / ExchangeOrderId all CS1061 rc=1, reading MarketMaker rc=0. Flag: `MarketMaker : string` is the only attribution-like field (a market-maker label, per-row, not per-order); its runtime contents on a CME feed were not observed |
| R8 | N/A-by-construction (Channel A / NinjaTrader run) | decisive probe = EgvTickReplayDiag (below). Supporting observation only: Core has `NinjaTrader.Data.TickReplayIterator` whose `Current` is `ReplayObject(DateTime time, double price, long volume, int barIndex, double bid, double ask)` |
| R9 | N/A-by-construction (Channel A / NinjaTrader run) | decisive probe = EgvTickReplayDiag. Supporting observation only: `NinjaTrader.Data.MarketReplay` exposes both `CurrentMarketData : MarketDataEventArgs` and `CurrentMarketDepth : MarketDepthEventArgs` from one `MoveNext()` |
| R10 | **UNVERIFIABLE** (supporting evidence for the L1+L2 half only) | three GC 04-26 `.nrd` files exist; the installed MarketReplay type carries an `L1;…` and an `L2;…` dump format, an `OnMarketDepth(position, marketMaker, operation, marketDataType, price, volume, timeLocal)` recorder and path formats `{0}\replay\{1}` / `{0}\{1}.nrd` — i.e. the .nrd pipeline handles L1 and L2 in one stream. File bodies are binary/compressed (no strings), so L2 presence in *these* files is not directly shown. "Downloadable from NinjaTrader's servers for free" is not testable at runtime without a download. |
| R11 | N/A-by-construction (Channel A / NinjaTrader run) | |
| R12 | N/A-by-construction (Channel A / NinjaTrader run) | |
| R13 | N/A-by-construction (Channel A / NinjaTrader run) | |
| R14 | N/A-by-construction (Channel A / NinjaTrader run) | |
| R15 | N/A-by-construction (Channel A / NinjaTrader run) | |
| R16 | **UNVERIFIABLE** on Channel B by file inspection — **evidence leans REFUTED** | the record encoding is opaque, so the bytes cannot prove absence of sizes. But: (a) all 107,601 files under db\tick (12,161 in ES*/MES*) are `<yyyyMMddHH00>.Last.ncd` — zero Bid/Ask series files; (b) a 1-trade file is 28-byte header + 3–4-byte record, too small to also hold absolute bid and ask sizes; (c) the tick-replay record type `ReplayObject` (all fields incl. non-public) is Time, Price, Volume, BarIndex, Bid, Ask — bid/ask **prices** as double, **no bid/ask size field**. Decisive probe: run EgvTickReplayDiag (Hist `BidVol>0` / `AskVol>0`). |

### Exact public members of `NinjaTrader.Data.MarketDepthEventArgs` (8.1.8.4)

Base chain: `MarketDepthEventArgs -> System.EventArgs -> System.Object` (no intermediate NinjaTrader base).

- Properties (all declared on MarketDepthEventArgs, all get-only): `Instrument : NinjaTrader.Cbi.Instrument`,
  `IsReset : bool`, `MarketDataType : NinjaTrader.Data.MarketDataType`, `MarketMaker : string`,
  `Operation : NinjaTrader.Cbi.Operation`, `Position : int`, `Price : double`, `Time : DateTime`,
  `Volume : long`
- Public fields: `Empty : EventArgs` (static, from EventArgs); `ojc= : string` (static, obfuscated name;
  value is the ToString format `instrument='{0}' type={1} mm='{2}' operation={3} pos={4} price={5} volume={6} time={7} isReset={8}`)
- Methods: `ToString()` (declared here), `Equals(object)`, `Equals(object, object)`, `GetHashCode()`,
  `GetType()`, `ReferenceEquals(object, object)` (from Object)
- Constructors: `()` and `(Instrument instrument, bool isReset, MarketDataType marketDataType, string marketMaker, Operation operation, int position, double price, DateTime time, long volume)`
- Events: none. Non-public properties: none. Non-public instance fields: only the nine auto-property backing fields.

For comparison `MarketDataEventArgs` publics: Ask, Bid, Instrument, IsReset, Last, MarketDataType,
Price, Time (DateTime), Volume (long); plus an **internal** `TickId : long` (not reachable from NinjaScript).

---

## Probe records

### P-REFL — reflection listing (R1, R2, R3, R5, R6, R7)

```
probe_cmd: powershell -NoProfile -ExecutionPolicy Bypass -File <scratch>\reflect.ps1 > <scratch>\reflect.out.txt 2>&1
rc: 0     wall_time: 2.9 s
```
stdout (verbatim excerpt; full 190 lines in `<scratch>\reflect.out.txt`):
```
LOADED NinjaTrader.Core, Version=8.1.8.4, Culture=neutral, PublicKeyToken=null | FileVersion 8.1.8.4
LOADED NinjaTrader.Gui, Version=8.1.8.4, Culture=neutral, PublicKeyToken=null | FileVersion 8.1.8.4
LOADED NinjaTrader.Custom, Version=8.1.9.0, Culture=neutral, PublicKeyToken=null | FileVersion 
RTLE in NinjaTrader.Gui: Could not load file or assembly 'System.Collections.Immutable, Version=9.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a' or one of its dependencies. The system cannot find the file specified.
TOTAL TYPES: 8066
=== TYPE NinjaTrader.Data.MarketDataEventArgs [NinjaTrader.Core]
  base chain: NinjaTrader.Data.MarketDataEventArgs -> System.EventArgs -> System.Object
  -- public properties (incl. inherited):
    P Ask : System.Double  (declared MarketDataEventArgs) get=True set=False
    P Bid : System.Double  (declared MarketDataEventArgs) get=True set=False
    P Instrument : NinjaTrader.Cbi.Instrument  (declared MarketDataEventArgs) get=True set=False
    P IsReset : System.Boolean  (declared MarketDataEventArgs) get=True set=False
    P Last : System.Double  (declared MarketDataEventArgs) get=True set=False
    P MarketDataType : NinjaTrader.Data.MarketDataType  (declared MarketDataEventArgs) get=True set=False
    P Price : System.Double  (declared MarketDataEventArgs) get=True set=False
    P Time : System.DateTime  (declared MarketDataEventArgs) get=True set=False
    P Volume : System.Int64  (declared MarketDataEventArgs) get=True set=False
  -- public fields:
    F Empty : System.EventArgs  (declared EventArgs)
    F oDc= : System.String  (declared MarketDataEventArgs)
  [... methods: Equals x2, GetHashCode, GetType, ReferenceEquals (Object), ToString (declared) ...]
  -- non-public instance fields (for info only):
    np-F <Ask>k__BackingField : Double
    np-F <Bid>k__BackingField : Double
    np-F <Instrument>k__BackingField : Instrument
    np-F <IsReset>k__BackingField : Boolean
    np-F <Last>k__BackingField : Double
    np-F <MarketDataType>k__BackingField : MarketDataType
    np-F <Price>k__BackingField : Double
    np-F <TickId>k__BackingField : Int64
    np-F <Time>k__BackingField : DateTime
    np-F <Volume>k__BackingField : Int64
=== TYPE NinjaTrader.Data.MarketDepthEventArgs [NinjaTrader.Core]
  base chain: NinjaTrader.Data.MarketDepthEventArgs -> System.EventArgs -> System.Object
  -- public properties (incl. inherited):
    P Instrument : NinjaTrader.Cbi.Instrument  (declared MarketDepthEventArgs) get=True set=False
    P IsReset : System.Boolean  (declared MarketDepthEventArgs) get=True set=False
    P MarketDataType : NinjaTrader.Data.MarketDataType  (declared MarketDepthEventArgs) get=True set=False
    P MarketMaker : System.String  (declared MarketDepthEventArgs) get=True set=False
    P Operation : NinjaTrader.Cbi.Operation  (declared MarketDepthEventArgs) get=True set=False
    P Position : System.Int32  (declared MarketDepthEventArgs) get=True set=False
    P Price : System.Double  (declared MarketDepthEventArgs) get=True set=False
    P Time : System.DateTime  (declared MarketDepthEventArgs) get=True set=False
    P Volume : System.Int64  (declared MarketDepthEventArgs) get=True set=False
  -- public fields:
    F Empty : System.EventArgs  (declared EventArgs)
    F ojc= : System.String  (declared MarketDepthEventArgs)
  -- public methods (non-accessor):
    M Equals(Object obj) : Boolean  (declared Object)
    M Equals(Object objA, Object objB) : Boolean  (declared Object)
    M GetHashCode() : Int32  (declared Object)
    M GetType() : Type  (declared Object)
    M ReferenceEquals(Object objA, Object objB) : Boolean  (declared Object)
    M ToString() : String  (declared MarketDepthEventArgs)
  -- public events:
  -- ALL members via GetMembers(Public|Instance|Static|FlattenHierarchy):
    Constructor .ctor
    Field Empty
    Field ojc=
    Method Equals
    Method get_Instrument
    Method get_IsReset
    Method get_MarketDataType
    Method get_MarketMaker
    Method get_Operation
    Method get_Position
    Method get_Price
    Method get_Time
    Method get_Volume
    Method GetHashCode
    Method GetType
    Method ReferenceEquals
    Method ToString
    Property Instrument
    Property IsReset
    Property MarketDataType
    Property MarketMaker
    Property Operation
    Property Position
    Property Price
    Property Time
    Property Volume
  -- non-public instance fields (for info only):
    np-F <Instrument>k__BackingField : Instrument
    np-F <IsReset>k__BackingField : Boolean
    np-F <MarketDataType>k__BackingField : MarketDataType
    np-F <MarketMaker>k__BackingField : String
    np-F <Operation>k__BackingField : Operation
    np-F <Position>k__BackingField : Int32
    np-F <Price>k__BackingField : Double
    np-F <Time>k__BackingField : DateTime
    np-F <Volume>k__BackingField : Int64
=== ENUM NinjaTrader.Data.MarketDataType [NinjaTrader.Core]
    Ask = 0
    Bid = 1
    Last = 2
    DailyHigh = 3
    DailyLow = 4
    DailyVolume = 5
    LastClose = 6
    Opening = 7
    OpenInterest = 8
    Settlement = 9
    Unknown = 10
=== ENUM NinjaTrader.Cbi.Operation [NinjaTrader.Core]
    Add = 0
    Update = 1
    Remove = 2
=== TYPE NinjaTrader.NinjaScript.NinjaScriptBase [NinjaTrader.Core]
  base chain: NinjaTrader.NinjaScript.NinjaScriptBase -> NinjaTrader.NinjaScript.NinjaScript -> System.Object
    protected virtual OnMarketData(NinjaTrader.Data.MarketDataEventArgs marketDataUpdate) : Void declared=NinjaTrader.NinjaScript.NinjaScriptBase virtual=True final=False abstract=False
    protected virtual OnMarketDepth(NinjaTrader.Data.MarketDepthEventArgs marketDepthUpdate) : Void declared=NinjaTrader.NinjaScript.NinjaScriptBase virtual=True final=False abstract=False
=== TYPE NinjaTrader.NinjaScript.IndicatorBase [NinjaTrader.Core]
  base chain: NinjaTrader.NinjaScript.IndicatorBase -> NinjaTrader.NinjaScript.NinjaScriptBase -> NinjaTrader.NinjaScript.NinjaScript -> System.Object
    protected virtual OnMarketData(...) : Void declared=NinjaTrader.NinjaScript.NinjaScriptBase virtual=True final=False abstract=False
    protected virtual OnMarketDepth(...) : Void declared=NinjaTrader.NinjaScript.NinjaScriptBase virtual=True final=False abstract=False
=== TYPE NinjaTrader.NinjaScript.Indicators.Indicator [NinjaTrader.Custom]
  base chain: NinjaTrader.NinjaScript.Indicators.Indicator -> NinjaTrader.Gui.NinjaScript.IndicatorRenderBase -> NinjaTrader.NinjaScript.IndicatorBase -> NinjaTrader.NinjaScript.NinjaScriptBase -> NinjaTrader.NinjaScript.NinjaScript -> System.Object
    protected virtual OnMarketData(NinjaTrader.Data.MarketDataEventArgs marketDataUpdate) : Void declared=NinjaTrader.NinjaScript.NinjaScriptBase virtual=True final=False abstract=False
    protected virtual OnMarketDepth(NinjaTrader.Data.MarketDepthEventArgs marketDepthUpdate) : Void declared=NinjaTrader.NinjaScript.NinjaScriptBase virtual=True final=False abstract=False
=== TYPE NinjaTrader.Gui.NinjaScript.IndicatorRenderBase [NinjaTrader.Gui]
  [same two lines, declared=NinjaTrader.NinjaScript.NinjaScriptBase virtual=True final=False]
=== Types with name containing 'Depth' or 'Level2' or 'OrderBook' (for R7 context):
    [NinjaTrader.Data.MarketDepth`1, NinjaTrader.Data.MarketDepthEventArgs, NinjaTrader.Data.MarketDepthRow,
     NinjaTrader.Gui.Level2.*, NinjaTrader.Gui.DepthChart.*, plus CQG.ProtoBuf *Symbol* types matched by 'Mbo' substring; no MarketByOrder/OrderBook type]
```
The falsifier for this listing is the compile-probe set below (a listing alone cannot fail).

### P-REFL2 — static fields, non-public properties, constructors (R2, R6, R7)

```
probe_cmd: powershell -NoProfile -ExecutionPolicy Bypass -File <scratch>\reflect2.ps1
rc: 0
```
```
=== NinjaTrader.Data.MarketDepthEventArgs
  public static fields:
    ojc= : String IsLiteral=False IsInitOnly=False value='instrument='{0}' type={1} mm='{2}' operation={3} pos={4} price={5} volume={6} time={7} isReset={8}'
  ALL properties incl non-public:
    Instrument : Instrument getter=public
    IsReset : Boolean getter=public
    MarketDataType : MarketDataType getter=public
    MarketMaker : String getter=public
    Operation : Operation getter=public
    Position : Int32 getter=public
    Price : Double getter=public
    Time : DateTime getter=public
    Volume : Int64 getter=public
  public ctors:
    ()
    (Instrument instrument, Boolean isReset, MarketDataType marketDataType, String marketMaker, Operation operation, Int32 position, Double price, DateTime time, Int64 volume)
  non-public ctors:
=== NinjaTrader.Data.MarketDataEventArgs
  public static fields:
    oDc= : String IsLiteral=False IsInitOnly=False value='instrument='{0}' type={1} price={2} volume={3} time='{4}' bid={5} ask={6} isReset={7}'
  ALL properties incl non-public:
    Ask : Double getter=public
    Bid : Double getter=public
    Instrument : Instrument getter=public
    IsReset : Boolean getter=public
    Last : Double getter=public
    MarketDataType : MarketDataType getter=public
    Price : Double getter=public
    TickId : Int64 getter=internal
    Time : DateTime getter=public
    Volume : Int64 getter=public
  public ctors:
    ()
    (Double last, Double ask, Double bid, Instrument instrument, Boolean isReset, MarketDataType marketDataType, Double price, DateTime time, Int64 volume, Int64 tickId)
  non-public ctors:
=== NinjaTrader.Data.MarketDepthRow
  public static fields:
    ozc= : String IsLiteral=False IsInitOnly=False value='mm='{0}' price={1} volume={2} time={3}'
  ALL properties incl non-public:
    MM : MarketMaker getter=internal
    MarketMaker : String getter=public
    Price : Double getter=public
    Time : DateTime getter=public
    Volume : Int64 getter=public
  public ctors:
    ()
  non-public ctors:
=== MarketDepth`1 public members:
    Method System.Collections.Generic.List`1[T] get_Asks()
    Method System.Collections.Generic.List`1[T] get_Bids()
    Method NinjaTrader.Cbi.Instrument get_Instrument()
    Method Void add_Update(System.EventHandler`1[NinjaTrader.Data.MarketDepthEventArgs])
    Method Void remove_Update(System.EventHandler`1[NinjaTrader.Data.MarketDepthEventArgs])
    Constructor Void .ctor(NinjaTrader.Cbi.Instrument)
    Property System.Collections.Generic.List`1[T] Asks
    Property System.Collections.Generic.List`1[T] Bids
    Property NinjaTrader.Cbi.Instrument Instrument
    Event System.EventHandler`1[NinjaTrader.Data.MarketDepthEventArgs] Update
```

### P-COMPILE — base probe (R1, R2, R3, R5, R6)

Probe source `<scratch>\EgvIcebergProbe.cs` (sha256 `f8a85debcfc460b8eb84a2f080db92be9e5aa4fd320a86e385b9f22bbb32dc27`,
unchanged after the falsifier runs — mutants were written as separate files): class
`EgvIcebergProbe : Indicator` in `NinjaTrader.NinjaScript.Indicators`, `protected override void
OnMarketData(MarketDataEventArgs e)` reading MarketDataType/Price/Volume/Time/Bid/Ask and comparing
to `MarketDataType.Last|Bid|Ask`; `protected override void OnMarketDepth(MarketDepthEventArgs e)`
reading MarketDataType/Operation/Position/Price/Volume and comparing to `Operation.Add|Update|Remove`.

```
$ OUT=<scratch>/out_EgvIcebergProbe.dll bash C:/Users/rajib/OneDrive/Documents/ninjatrader_quant_indicators/validation/probes/compile_probe.sh <scratch>/EgvIcebergProbe.cs
csc: /c/Program Files/dotnet/sdk/8.0.100/Roslyn/bincore/csc.dll
out: <scratch>/out_EgvIcebergProbe.dll
refs: 17  sources: 1
rc=0
```

Falsifiers (one targeted mutation each, same command with the mutant file; class renamed per mutant):

| claim | mutant | verbatim compiler output | rc |
|---|---|---|---|
| R1 | `OnMarketData` → `OnMarketDta` | `F_R1_misspelled_OnMarketData.cs(16,27): error CS0115: 'EgvIcebergProbe_F_R1_misspelled_OnMarketData.OnMarketDta(MarketDataEventArgs)': no suitable method found to override` | 1 |
| R2 | `e.Volume` → `e.Size` | `F_R2_read_Size.cs(21,15): error CS1061: 'MarketDataEventArgs' does not contain a definition for 'Size' and no accessible extension method 'Size' accepting a first argument of type 'MarketDataEventArgs' could be found (are you missing a using directive or an assembly reference?)` | 1 |
| R3 | `MarketDataType.Last` → `MarketDataType.Trade` | `F_R3_enum_Trade.cs(26,30): error CS0117: 'MarketDataType' does not contain a definition for 'Trade'` | 1 |
| R5 | `OnMarketDepth` → `OnMarketDepht` | `F_R5_misspelled_OnMarketDepth.cs(32,27): error CS0115: 'EgvIcebergProbe_F_R5_misspelled_OnMarketDepth.OnMarketDepht(MarketDepthEventArgs)': no suitable method found to override` | 1 |
| R6 | `e.Position` → `e.Postion` | `F_R6_read_Postion.cs(37,16): error CS1061: 'MarketDepthEventArgs' does not contain a definition for 'Postion' and no accessible extension method 'Postion' accepting a first argument of type 'MarketDepthEventArgs' could be found (are you missing a using directive or an assembly reference?)` | 1 |

Full log: `<scratch>\compile_runs.txt`.

### P-R7 — order-id probes

Compile probes: `class EgvIcebergProbe…: Indicator { protected override void OnMarketDepth(MarketDepthEventArgs e) { Sink = e.<M>; } }`.

| member M | verbatim output | rc | expected for claim to survive |
|---|---|---|---|
| OrderId (`R7_m1.cs`) | `R7_m1.cs(7,76): error CS1061: 'MarketDepthEventArgs' does not contain a definition for 'OrderId' and no accessible extension method 'OrderId' accepting a first argument of type 'MarketDepthEventArgs' could be found (are you missing a using directive or an assembly reference?)` | 1 | ≠0 ✔ |
| OrderID (`R7_m2.cs`) | `R7_m2.cs(7,76): error CS1061: 'MarketDepthEventArgs' does not contain a definition for 'OrderID' and no accessible extension method 'OrderID' ...` | 1 | ≠0 ✔ |
| Id | `R7_Id.cs(7,76): error CS1061: 'MarketDepthEventArgs' does not contain a definition for 'Id' ...` | 1 | ≠0 ✔ |
| OrderIdentifier | `R7_OrderIdentifier.cs(7,76): error CS1061: 'MarketDepthEventArgs' does not contain a definition for 'OrderIdentifier' ...` | 1 | ≠0 ✔ |
| ExchangeOrderId | `R7_ExchangeOrderId.cs(7,76): error CS1061: 'MarketDepthEventArgs' does not contain a definition for 'ExchangeOrderId' ...` | 1 | ≠0 ✔ |
| **falsifier:** MarketMaker (real member) | `rc=0` | 0 | =0 ✔ (shows the probe can pass) |

Probe-hygiene incident (recorded, corrected): the first batch wrote `R7_OrderId.cs` and
`R7_OrderID.cs`, which are the **same file on NTFS (case-insensitive)**; the "OrderId" run actually
compiled the OrderID text (its error message names 'OrderID'). Those two runs were discarded as
PROBE_INVALID and rerun under distinct names `R7_m1.cs` / `R7_m2.cs` (results above, log
`<scratch>\compile_runs_r7fix.txt`).

Reflection id-scan (exit code encodes verdict: 0 = no id-like member; regex, case-sensitive,
`Id$|ID$|^Id|Identifier|Sequence|Seq$|OrderRef|Token|Mbo|Uid|Guid` over public instance+static
flattened Property/Field/Method names):
```
$ powershell -File r7_idscan.ps1 -TypeName NinjaTrader.Data.MarketDepthEventArgs
type=NinjaTrader.Data.MarketDepthEventArgs members=Empty,Equals,GetHashCode,GetType,Instrument,IsReset,MarketDataType,MarketMaker,ojc=,Operation,Position,Price,ReferenceEquals,Time,ToString,Volume
id-like hits: (none)
rc=0
$ powershell -File r7_idscan.ps1 -TypeName NinjaTrader.Data.MarketDepthRow
type=NinjaTrader.Data.MarketDepthRow members=Equals,GetHashCode,GetType,MarketMaker,ozc=,Price,ReferenceEquals,Time,ToString,Volume
id-like hits: (none)
rc=0
$ (falsifier) powershell -File r7_idscan.ps1 -TypeName NinjaTrader.Cbi.Order
type=NinjaTrader.Cbi.Order members=Account,AverageFillPrice,...,Id,...,OrderId,...,ClientId,...   [list trimmed]
id-like hits: ClientId,Id,OrderId
rc=1
```
Scope of R7 verdict: the NinjaScript-visible event type is market-by-price (Position + Price +
Volume + Operation, plus a MarketMaker string). Runtime values of MarketMaker on the user's CME feed
were not observed (needs a live/playback run); EgvTickReplayDiag does not print it.

### P-R10 — Market Replay folder (supporting only)

```
$ find "C:/Users/rajib/Documents/NinjaTrader 8/db/replay" -type f -printf '%s\t%TY-%Tm-%Td\t%p\n'
83775800	2026-02-02	.../replay/GC 04-26/20260201.nrd
103849542	2026-02-03	.../replay/GC 04-26/20260202.nrd
19027186	2026-02-03	.../replay/GC 04-26/20260203.nrd
count files: 3
rc: 0
```
First 64 bytes (`xxd -l 64`):
```
20260201.nrd
00000000: 9a99 9999 995b b240 629d 2200 cdcc cccc  .....[.@b.".....
00000010: 4c36 b340 0000 0000 00fd b140 cdcc cccc  L6.@.......@....
00000020: 4c36 b340 0000 0000 0000 f03f 9a99 9999  L6.@.......?....
00000030: 9999 b93f 0100 0000 38cd e662 b161 de08  ...?....8..b.a..
20260202.nrd
00000000: cdcc cccc cce0 b240 01a3 2a00 0000 0000  .......@..*.....
00000010: 0012 b340 9a99 9999 9948 b140 3333 3333  ...@.....H.@3333
00000020: b35b b240 0000 0000 0000 f03f 9a99 9999  .[.@.......?....
00000030: 9999 b93f 0100 0000 c0dc 07eb 1762 de08  ...?.........b..
20260203.nrd
00000000: 6766 6666 66e4 b340 c7a7 1a00 cdcc cccc  gffff..@........
00000010: cce6 b340 0000 0000 00e0 b240 3333 3333  ...@.......@3333
00000020: b3e1 b240 0000 0000 0000 f03f 9a99 9999  ...@.......?....
00000030: 9999 b93f 0100 0000 0039 7215 e162 de08  ...?.....9r..b..
```
Header decode (python struct, little-endian; my field labels are guesses from values, not from docs):
```
20260201.nrd d0=4699.60 int@8=2268514 d@12..=['4918.30', '4605.00', '4918.30', '1.00'] d@44=0.1000 int@52=1 int64@56->DateTime 2026-02-01 16:46:02.958776  entropy(bytes64..65600)=5.03 bits/byte
20260202.nrd d0=4832.80 int@8=2794241 d@12..=['4882.00', '4424.60', '4699.70', '1.00'] d@44=0.1000 int@52=1 int64@56->DateTime 2026-02-02 05:00:00.012000  entropy(bytes64..65600)=5.03 bits/byte
20260203.nrd d0=5092.40 int@8=1746887 d@12..=['5094.80', '4832.00', '4833.70', '1.00'] d@44=0.1000 int@52=1 int64@56->DateTime 2026-02-03 05:00:00.016000  entropy(bytes64..65600)=4.20 bits/byte
```
(GC-range prices, 0.1 = GC tick size, a .NET DateTime start stamp, ~1.7–2.8 M per-file count.)
String scan of the first 4 MB of 20260203.nrd: `distinct runs 3` (`gffffB`, `@gffffB`, `Gi@!(J`),
`utf16 runs 0` — the body is packed binary; no L1/L2 tags visible.

Installed-code evidence (`reflect r16_params.ps1`, rc=0):
```
MarketReplay.OnMarketData(MarketDataType marketDataType, Double price, Int64 volume, DateTime timeLocal)
MarketReplay.OnMarketDepth(Int32 position, String marketMaker, Operation operation, MarketDataType marketDataType, Double price, Int64 volume, DateTime timeLocal)
MarketReplay.DumpMarketData(Instrument instrument, DateTime from, DateTime to, String path)
MarketReplay.DumpMarketDepth(Instrument instrument, DateTime from, DateTime to, String path)
MarketReplay static string fields:
   tTc= = '{0}\replay\{1}'
   ujc= = 'L2;{0};{1};{2};{3};{4};{5};{6};{7}'
   uzc= = 'L1;{0};{1};{2};{3};{4}'
   vDc= = 'L2'
   vTc= = '{0}\{1}.nrd'
   wjc= = 'MarketReplay.OnMarketDepth: MarketData ({0}) for '{1}' at {2} exceeds max price gap ({3}/{4})'
   wzc= = 'Data.MarketDepthBuf.Write: ERROR: {0}'
   [other format/error strings trimmed]
MarketReplay members: CurrentMarketData : MarketDataEventArgs, CurrentMarketDepth : MarketDepthEventArgs, MoveNext(), Start(), Stop(), DoInitMarketDepth
```
Size cross-check (weak — different contract): `MGC 04-26` tick files dated 20260202 = 23 files,
5,950,588 bytes; the GC 04-26 replay file for the same date = 103,849,542 bytes (~17×).
No falsifier: R10 is supporting-only and its load-bearing half ("free download from NinjaTrader's
servers") is untestable here → UNVERIFIABLE.

### P-R16 — tick store (ES/MES)

Folder census (`find … | sed | uniq -c`, rc=0):
```
$ suffix census over ALL files in db/tick (name pattern <stamp>.<X>.ncd):
 107601 Last
non-.ncd files in tick:
$ census of second-dot tokens over all of db:
 155697 Last.ncd
    461 Last.ntb
      3 (other) nrd
      1 (other) sqlite
extensions in ES/MES:  12161 ncd
```
ES/MES folders (files / total bytes): ES 03-26 232 / 45,929,466; ES 09-25 0; ES 12-25 0; MES 0;
MES 12-25 1,526 / 184,142,023; MES 03-26 1,224 / 148,219,962; MES 12-26 113 / 12,407,219; plus
MES 03-20 … MES 12-24 (not sized). One file per hour, name `yyyyMMddHH00.Last.ncd`.
(`find db -iname '*bid*'` matched only db\cache bar-cache names such as
`Minute_1_1_Last_Close_Tick_BidAsk_Minute_1.20260201.20260202.Last.ncd` — those are also `.Last.ncd`.)

First 64 bytes (`xxd -l 64`):
```
MES 12-25/202509140300.Last.ncd  (size 32)
00000000: 0100 0000 0000 0000 0000 d03f 0000 0000  ...........?....
00000010: 40f5 b940 8ada bc53 38f3 dd08 3020 2201  @..@...S8...0 ".
MES 12-25/202509140900.Last.ncd  (size 32)
00000000: 0100 0000 0000 0000 0000 d03f 0000 0000  ...........?....
00000010: 40f5 b940 4dbc 14bc 6af3 dd08 3020 2201  @..@M...j...0 ".
MES 03-26/202512141200.Last.ncd  (size 31)
00000000: 0100 0000 0000 0000 0000 d03f 0000 0000  ...........?....
00000010: 40ed ba40 7d6b 7b0c 033b de08 0020 01    @..@}k{..;... .
MES 12-25/202509141600.Last.ncd  (size 52)
00000000: 0100 0000 0000 0000 0000 d03f 0000 0000  ...........?....
00000010: 40f5 b940 0e73 18fa a0f3 dd08 3020 2201  @..@.s......0 ".
00000020: 3320 43bd f272 2201 3420 0000 0003 9e39  3 C..r".4 .....9
00000030: c57a 2201                                .z".
MES 03-26/202512141700.Last.ncd  (size 52)
00000000: 0100 0000 0000 0000 0000 d03f 0000 0000  ...........?....
00000010: 40ed ba40 3821 1bd8 2b3b de08 3020 2101  @..@8!..+;..0 !.
00000020: 3320 0008 3569 2101 3320 129a f68f 2101  3 ..5i!.3 ....!.
00000030: 3020 2101                                0 !.
ES 03-26/202601140100.Last.ncd  (size 27134)
00000000: 0100 0000 0000 0000 0000 d03f 0000 0000  ...........?....
00000010: 404a bb40 c0d4 f4dc ff52 de08 0020 0100  @J.@.....R... ..
00000020: 2001 4b31 000f 4240 0143 2f00 2bf2 0001   .K1..B@.C/.+...
00000030: 0020 0103 2000 33e1 4001 0320 0022 2e00  . .. .3.@.. ."..
MES 12-26/202610161300.Last.ncd  (size 511860)
00000000: 0100 0000 0000 0000 0000 d03f 0000 0000  ...........?....
00000010: c034 be40 c096 2b01 7d2b df08 0820 0e08  .4.@..+.}+... ..
00000020: 2001 0820 0808 2001 0820 0108 2001 0820   .. .. .. .. .. 
00000030: 0a08 2001 0820 0108 2001 0820 0108 2001  .. .. .. .. .. .
```
Observed structure (empirical reading, not a spec): 28-byte header = int32 1 | double 0.25 (ES/MES
tick size, bytes 4–11) | double first price (e.g. 0x40b9f540… = 6645.25) | int64 .NET DateTime;
then variable-length delta records of 3–12 bytes. A file holding a single print is 31–32 bytes
(record `00 20 01` or `30 20 22 01`). Whether one of those bytes encodes a bid/ask **price** offset
cannot be decided without the codec; a single-print record of 3–4 bytes has no room for two
absolute size integers alongside price/time/volume, but delta-against-implicit-state encodings make
that argument suggestive, not conclusive.

Installed-code evidence (`r16_members.ps1`, `r16_params.ps1`, rc=0):
```
=== NinjaTrader.Data.TickReplayIterator : base System.Object
    Method NinjaTrader.Data.ReplayObject get_Current()
    Method Boolean MoveNext()
    Constructor Void .ctor(NinjaTrader.Data.Bars)
    Field System.String 3jY=        (value '.ntt')
ReplayObject ctor params: DateTime time, Double price, Int64 volume, Int32 barIndex, Double bid, Double ask
ReplayObject ALL instance fields (incl non-public): Double <Ask>k__BackingField, Int32 <BarIndex>k__BackingField, Double <Bid>k__BackingField, Double <Price>k__BackingField, DateTime <Time>k__BackingField, Int64 <Volume>k__BackingField
ReplayObject ALL properties (incl non-public): Double Ask, Int32 BarIndex, Double Bid, Double Price, DateTime Time, Int64 Volume
ReplayObject format string field: Time: '{0}' Open: '{1}' Ask: '{2}' Bid: '{3}' Volume: '{4}' BarIndex: '{5}'
=== NinjaTrader.Data.PlaybackIterator : Current : MarketDataEventArgs, Instrument, MoveNext()
```
(`.ntt` files under db: 0.) Bars also exposes `bool IsTickReplay` and `bool IsInReplayMode`.

Verdict reasoning: the bytes cannot show presence/absence of bid/ask sizes → per the pre-registered
expectation, **UNVERIFIABLE** on Channel B. Three independent observations point the same way —
trades-only file naming, record size, and a tick-replay record type with bid/ask *prices* but no
*size* fields — so the evidence leans REFUTED for "bid/ask events **with sizes**". The decisive test
is EgvTickReplayDiag: `Hist: BidVol>0=0 AskVol>0=0` with `Hist: Bid>0 Ask>0` would refute R16;
non-zero `BidVol>0/AskVol>0` in Hist would confirm it.

---

## Diagnostic indicator for the user (R16 decisive, R8, R9)

File: `C:\Users\rajib\OneDrive\Documents\ninjatrader_quant_indicators\validation\iceberg\EgvTickReplayDiag.cs`
(sha256 `b2641f953d879b528ce0eb11181670f002a69ef132dde46290e3887f97429406`, NOT installed).

`class EgvTickReplayDiag : Indicator` — per State bucket (Historical / Realtime / Other) counts
OnMarketData by MarketDataType, Bid/Ask events with Volume > 0 vs ≤ 0, Last with Volume > 0, type
switches between consecutive events, time regressions, IsReset events, and OnMarketDepth calls
(total / Bid / Ask). Prints `EGV|HEADER|…` at DataLoaded (instrument, period, Bars.IsTickReplay,
Bars.IsInReplayMode, bar count), the first 5 historical Bid/Ask events as `EGV|SAMPLE|…`, and
`EGV|SUMMARY|…` at the State.Realtime transition, every 5,000 events (data + depth), and at Terminated.

```
$ OUT=<scratch>/out_EgvTickReplayDiag.dll bash C:/Users/rajib/OneDrive/Documents/ninjatrader_quant_indicators/validation/probes/compile_probe.sh C:/Users/rajib/OneDrive/Documents/ninjatrader_quant_indicators/validation/iceberg/EgvTickReplayDiag.cs
csc: /c/Program Files/dotnet/sdk/8.0.100/Roslyn/bincore/csc.dll
out: <scratch>/out_EgvTickReplayDiag.dll
refs: 17  sources: 1
rc=0
```
Falsifier (mutant `<scratch>\F_Diag_Size.cs`, line 141 `e.Volume` → `e.Size`):
```
F_Diag_Size.cs(141,12): error CS1061: 'MarketDataEventArgs' does not contain a definition for 'Size' and no accessible extension method 'Size' accepting a first argument of type 'MarketDataEventArgs' could be found (are you missing a using directive or an assembly reference?)
rc=1
```
Original file checksum identical before and after the falsifier run.

Suggested runs (also in the file header): (A) ES/MES chart with Tick Replay ON; (B) same with Tick
Replay OFF as control; (C) Playback connection on the GC 04-26 Market Replay data for R9. Reading
guide: R8 → Hist Bid/Ask/Last all > 0 with TypeSwitches > 0 and TimeRegressions = 0 in run A;
R9 → Hist Depth = 0 in A and B, Depth > 0 in run C; R16 → Hist BidVol>0 / AskVol>0 in run A.
Caveat: this compiles under C# 12/Roslyn 8.0.100 against 8.1.8.4; it has not been compiled inside
NinjaTrader's own editor.
