"""test_compile_smoke.py - compile each indicator with validation/probes/compile_probe.sh
(dotnet Roslyn csc against the installed NinjaTrader 8 assemblies). Marked `slow`.

Skips when Git bash, the csc.dll path or the NinjaTrader assemblies named in the script are
missing. The script's exit code is csc's exit code (0 = compiled).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from vp_helpers import COMPILE_PROBE, INDICATORS_DIR

FILES = sorted(INDICATORS_DIR.glob("QI_*.cs"))
pytestmark = pytest.mark.slow


def _git_bash():
    for cand in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if os.path.exists(cand):
            return cand
    b = shutil.which("bash")
    if b and "system32" not in b.lower():  # WSL's launcher cannot see the Windows dotnet/cygpath
        return b
    return None


def _script_paths():
    """Return the csc/NT paths the script hard-codes, converted to Windows paths."""
    text = COMPILE_PROBE.read_text(encoding="utf-8")
    out = {}
    for key in ("CSC", "NT"):
        m = re.search(r'^%s="([^"]+)"' % key, text, re.M)
        if m:
            p = m.group(1)
            p = re.sub(r"^/([a-zA-Z])/", lambda mm: mm.group(1).upper() + ":/", p)
            out[key] = p
    return out


@pytest.fixture(scope="module")
def bash():
    b = _git_bash()
    if b is None:
        pytest.skip("Git bash not found")
    if not COMPILE_PROBE.exists():
        pytest.skip("compile_probe.sh missing")
    paths = _script_paths()
    if "CSC" not in paths or not os.path.exists(paths["CSC"]):
        pytest.skip("Roslyn csc.dll not found at the path in compile_probe.sh")
    if "NT" not in paths or not os.path.exists(os.path.join(paths["NT"], "NinjaTrader.Core.dll")):
        pytest.skip("NinjaTrader assemblies not found at the path in compile_probe.sh")
    if shutil.which("dotnet") is None:
        pytest.skip("dotnet not on PATH")
    return b


def _run(bash, src, out_dll):
    env = dict(os.environ, OUT=str(out_dll).replace("\\", "/"))
    proc = subprocess.run([bash, str(COMPILE_PROBE).replace("\\", "/"), str(src).replace("\\", "/")],
                          capture_output=True, text=True, env=env, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_indicator_compiles(bash, path, tmp_path):
    rc, out = _run(bash, path, tmp_path / "probe.dll")
    assert rc == 0, "%s failed to compile (rc=%d):\n%s" % (path.name, rc, out[-3000:])


def test_all_indicators_compile_together(bash, tmp_path):
    env = dict(os.environ, OUT=str(tmp_path / "all.dll").replace("\\", "/"))
    proc = subprocess.run([bash, str(COMPILE_PROBE).replace("\\", "/")] + [str(p).replace("\\", "/") for p in FILES],
                          capture_output=True, text=True, env=env, timeout=600)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-3000:]


def test_falsifier_mutant_must_fail_to_compile(bash, tmp_path):
    """A one-token mutation (dropped semicolon on the Name assignment) must make csc fail."""
    src = FILES[0].read_text(encoding="utf-8")
    mutant = re.sub(r'(Name\s*=\s*"[^"]*");', r"\1", src, count=1)
    assert mutant != src, "mutation did not apply"
    m = tmp_path / FILES[0].name
    m.write_text(mutant, encoding="utf-8")
    rc, out = _run(bash, m, tmp_path / "mutant.dll")
    assert rc != 0, "mutant compiled - the compile probe cannot fail:\n%s" % out[-2000:]
    assert "error" in out.lower()
