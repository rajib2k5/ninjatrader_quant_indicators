#!/usr/bin/env bash
# compile_probe.sh - Tier-0 / Channel-B build gate for ninjatrader_quant_indicators
#
# Compiles the given NinjaScript .cs files into a throw-away class library with the
# Roslyn csc shipped in the .NET 8 SDK, referencing the INSTALLED NinjaTrader 8 assemblies
# (see validation/env-pin.txt). It never touches NinjaTrader.Custom.dll or NinjaTrader itself.
#
# Usage:  compile_probe.sh FILE.cs [FILE2.cs ...]
#         OUT=/path/probe.dll compile_probe.sh ...   (override output path)
# Exit code is csc's exit code (0 = compiled). All diagnostics are printed verbatim.
#
# Caveat: the SDK 8.0.100 Roslyn supports up to C# 12 (`-langversion:latest`), while
# NinjaTrader 8.1.8.3's own build uses LangVersion 13. C# 12 is a strict subset, so a file
# that compiles here also compiles in NinjaTrader; the reverse is not guaranteed.
set -u

CSC="/c/Program Files/dotnet/sdk/8.0.100/Roslyn/bincore/csc.dll"
NT="/c/Program Files/NinjaTrader 8/bin"
CUSTOM="/c/Users/rajib/Documents/NinjaTrader 8/bin/Custom"
FW="/c/Windows/Microsoft.NET/Framework64/v4.0.30319"
OUT="${OUT:-$(dirname "$0")/_probe_out/probe.dll}"
mkdir -p "$(dirname "$OUT")"

REFS=(
	"$NT/NinjaTrader.Core.dll"
	"$NT/NinjaTrader.Gui.dll"
	"$CUSTOM/NinjaTrader.Custom.dll"
	"$FW/mscorlib.dll"
	"$FW/System.dll"
	"$FW/System.Core.dll"
	"$FW/System.Xml.dll"
	"$FW/System.Xml.Linq.dll"
	"$FW/System.ComponentModel.DataAnnotations.dll"
	"$FW/System.Xaml.dll"
	"$FW/WPF/WindowsBase.dll"
	"$FW/WPF/PresentationCore.dll"
	"$FW/WPF/PresentationFramework.dll"
)
# SharpDX (DirectX rendering types referenced by NinjaTrader.Gui signatures)
while IFS= read -r f; do REFS+=("$f"); done < <(find "$NT" -maxdepth 3 -iname "SharpDX*.dll" 2>/dev/null)

ARGS=()
for r in "${REFS[@]}"; do
	if [ -f "$r" ]; then ARGS+=("-r:$(cygpath -w "$r")"); else echo "WARN: missing reference $r" >&2; fi
done

SRCS=()
for s in "$@"; do SRCS+=("$(cygpath -w "$s")"); done

echo "csc: $CSC"
echo "out: $OUT"
echo "refs: ${#ARGS[@]}  sources: ${#SRCS[@]}"
dotnet exec "$(cygpath -w "$CSC")" -nologo -nostdlib -noconfig -target:library \
	-langversion:latest -platform:x64 -nowarn:1701,1702,1591 \
	-out:"$(cygpath -w "$OUT")" "${ARGS[@]}" "${SRCS[@]}"
rc=$?
echo "rc=$rc"
exit $rc
