#!/usr/bin/env python3
"""
run_parity.py -- cross-platform driver for the usdGeospatialSceneIndex parity
proof (a Windows/PowerShell-friendly replacement for run_parity.sh), also usable
as a single ctest test (see pxr_register_test in CMakeLists.txt).

It (1) generates the closed-form + Python-reference oracle (gen_parity_cases.py,
dump_oracle.py), then (2) runs the compiled C++ parity tests against it:
  * testUsdGeospatialCrsEngine   -- CRS engine vs closed-form geodesy
  * testUsdGeospatialResolver     -- stage resolver vs oracle + ground truth
  * testUsdGeospatialSceneIndex   -- resolution THROUGH Hydra vs oracle + GT
All must agree to <= tol (default 5 mm; results are 0.0 mm). Exits non-zero if a
parity test reports a failure.

Environment (all optional; sensible defaults for a dev run):
  USD_INST     install prefix -> PROJ_DATA=<inst>/share/proj, plugin resources,
               and runtime DLLs (<inst>/bin;<inst>/lib on PATH).
  GEO_TEST_BIN dir holding the compiled test executables. Default <inst>/tests.
  GEO_SRC_DIR  dir holding gen_parity_cases.py + dump_oracle.py (the source tree).
               Default: this script's own directory. (Needed when this script is
               installed to <inst>/tests but the oracle generators live in-source.)
  GEO_TOL_MM   tolerance in mm (default 5.0).
Oracle artifacts are written under the current working directory.
"""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = ".exe" if os.name == "nt" else ""
TESTS = [
    ("testUsdGeospatialCrsEngine", "cases"),    # engine vs closed-form
    ("testUsdGeospatialResolver", "oracle"),    # stage resolver vs oracle+GT
    ("testUsdGeospatialSceneIndex", "oracle"),  # through Hydra (SetStage) vs oracle+GT
    ("testUsdGeospatialHydraAuto", "oracle"),   # auto-insert (NO SetStage) vs oracle+GT
]


def main():
    tol = os.environ.get("GEO_TOL_MM", "5.0")
    inst = os.environ.get("USD_INST", "")
    srcdir = os.environ.get("GEO_SRC_DIR", HERE)
    workdir = os.getcwd()

    # Schema registry + the built plugin must both be discoverable.
    schema_res = os.path.normpath(os.path.join(
        srcdir, "..", "..", "..", "..", "pxr", "usd", "usdGeospatial", "resources"))
    plugin_res = os.path.join(inst, "share", "usd", "examples", "plugin",
                              "usdGeospatialSceneIndex", "resources") if inst else ""
    sep = os.pathsep
    prev_pp = os.environ.get("PXR_PLUGINPATH_NAME", "")
    os.environ["PXR_PLUGINPATH_NAME"] = sep.join(
        [p for p in (plugin_res, schema_res, prev_pp) if p])
    if inst:
        os.environ.setdefault("PROJ_DATA", os.path.join(inst, "share", "proj"))
    # Ensure the runtime DLLs the test exes need are resolvable: the USD/PROJ
    # libs (<inst>/bin, <inst>/lib) and the Python DLL (next to this interpreter,
    # e.g. python3x.dll -- USD was built with Python support).
    for d in (os.path.join(inst, "bin") if inst else "",
              os.path.join(inst, "lib") if inst else "",
              os.path.dirname(sys.executable)):
        if d and os.path.isdir(d):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("PYTHONUTF8", "1")

    bindir = os.environ.get("GEO_TEST_BIN") or (
        os.path.join(inst, "tests") if inst else "")
    if not bindir or not os.path.isdir(bindir):
        print("run_parity: set GEO_TEST_BIN (or USD_INST) to the dir with the "
              "test executables", file=sys.stderr)
        return 2

    py = sys.executable
    # 1) generate oracle artifacts (into the current working directory)
    print("== [1/2] generating oracle (gen_parity_cases.py + dump_oracle.py) ==")
    cases_tsv = os.path.join(workdir, "parity_cases.tsv")
    with open(cases_tsv, "w") as f:
        rc = subprocess.call([py, os.path.join(srcdir, "gen_parity_cases.py")],
                             stdout=f, cwd=workdir)
    if rc != 0:
        print("gen_parity_cases.py failed", file=sys.stderr)
        return rc
    # dump_oracle.py writes ./out/parity relative to cwd; its imports resolve
    # relative to its own __file__ (in the source tree), so cwd may be anywhere.
    rc = subprocess.call([py, os.path.join(srcdir, "dump_oracle.py")], cwd=workdir)
    if rc != 0:
        print("dump_oracle.py failed", file=sys.stderr)
        return rc
    # dump_oracle.py writes out/parity relative to its OWN directory (srcdir),
    # not the cwd, so read the oracle from there.
    oracle_tsv = os.path.join(srcdir, "out", "parity", "oracle.tsv")

    # 2) run the compiled parity tests
    print("== [2/2] running C++ parity tests (tol %s mm) ==" % tol)
    fails = 0
    for name, kind in TESTS:
        exe = os.path.join(bindir, name + EXE)
        if not os.path.exists(exe):
            print("  MISSING: %s" % exe, file=sys.stderr)
            fails += 1
            continue
        arg = cases_tsv if kind == "cases" else oracle_tsv
        rc = subprocess.call([exe, arg, tol])
        status = "PASS" if rc == 0 else "FAIL(rc=%d)" % rc
        print("  %-32s %s" % (name, status))
        if rc != 0:
            fails += 1
    print("== parity %s ==" % ("GREEN" if fails == 0 else "RED (%d failing)" % fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
