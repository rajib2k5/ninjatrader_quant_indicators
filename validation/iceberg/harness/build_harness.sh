#!/usr/bin/env bash
# Builds IcebergHarness.exe (x64 net48) from Program.cs + the indicator file, same csc/refs as compile_probe.sh.
set -u
S="$(cd "$(dirname "$0")" && pwd)"
OUT="${OUT:-$S/_out/IcebergHarness.exe}"
REPO="$(cd "$S/../../.." && pwd)"
IND="${IND:-$REPO/indicators/QI_28_IcebergDetector.cs}"
CSC="/c/Program Files/dotnet/sdk/8.0.100/Roslyn/bincore/csc.dll"
NT="/c/Program Files/NinjaTrader 8/bin"
CUSTOM="/c/Users/rajib/Documents/NinjaTrader 8/bin/Custom"
FW="/c/Windows/Microsoft.NET/Framework64/v4.0.30319"
mkdir -p "$(dirname "$OUT")"
REFS=("$NT/NinjaTrader.Core.dll" "$NT/NinjaTrader.Gui.dll" "$CUSTOM/NinjaTrader.Custom.dll"
  "$FW/mscorlib.dll" "$FW/System.dll" "$FW/System.Core.dll" "$FW/System.Xml.dll" "$FW/System.Xml.Linq.dll"
  "$FW/System.ComponentModel.DataAnnotations.dll" "$FW/System.Xaml.dll"
  "$FW/WPF/WindowsBase.dll" "$FW/WPF/PresentationCore.dll" "$FW/WPF/PresentationFramework.dll")
while IFS= read -r f; do REFS+=("$f"); done < <(find "$NT" -maxdepth 3 -iname "SharpDX*.dll" 2>/dev/null)
ARGS=(); for r in "${REFS[@]}"; do [ -f "$r" ] && ARGS+=("-r:$(cygpath -w "$r")"); done
dotnet exec "$(cygpath -w "$CSC")" -nologo -nostdlib -noconfig -target:exe -langversion:latest -platform:x64 \
  -nowarn:1701,1702,1591 -out:"$(cygpath -w "$OUT")" "${ARGS[@]}" \
  "$(cygpath -w "$S/Program.cs")" "$(cygpath -w "$IND")"
rc=$?; echo "rc=$rc"; exit $rc
