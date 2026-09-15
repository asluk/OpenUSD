#!/usr/bin/env python3
"""
run_runtime_parity.py -- ctest driver for the VISUAL two-runtime parity gate on
the real railway stage (registered as testUsdGeospatialRuntimeParity).

Where run_parity.py checks the C++ engine/resolver/scene-index against the
closed-form + Python oracle on the parametric case grid, this driver checks the
Python reference runtime against the compiled Hydra scene index on the *actual
authored NVIDIA Deutsche Bahn railway stage*, per rail vertex + tile corner, and
FAILS (non-zero exit) if the worst disagreement exceeds the tolerance (1 mm).

It (1) converts the shipped railway asset into the crs:binding/crs:position
schema, (2) dumps the Hydra-resolved xforms via the compiled dumpHydraXforms,
then (3) runs ../usdGeospatial/fig_runtime_parity.py --check (numpy-only; no
matplotlib needed) which self-asserts the sub-mm gate.

Environment (all optional; sensible defaults for a dev run):
  USD_INST     install prefix -> PROJ_DATA=<inst>/share/proj, plugin resources,
               and runtime DLLs (<inst>/bin;<inst>/lib on PATH).
  GEO_TEST_BIN dir holding dumpHydraXforms. Default <inst>/tests.
  GEO_SRC_DIR  this script's dir (usdGeospatialSceneIndex). Default: __file__ dir.
  GEO_TOL_MM   parity tolerance in mm (default 1.0).
Work artifacts (converted stage, hydra tsv, throwaway figure) go under the cwd.
"""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = ".exe" if os.name == "nt" else ""


def main():
    tol = os.environ.get("GEO_TOL_MM", "1.0")
    inst = os.environ.get("USD_INST", "")
    srcdir = os.environ.get("GEO_SRC_DIR", HERE)
    workdir = os.getcwd()

    # The Python reference runtime + the converter live in ../usdGeospatial/src;
    # fig_runtime_parity.py sits in ../usdGeospatial.
    geo_dir = os.path.normpath(os.path.join(srcdir, "..", "usdGeospatial"))
    geo_src = os.path.join(geo_dir, "src")
    fig_parity = os.path.join(geo_dir, "fig_runtime_parity.py")
    railway_asset = os.path.join(geo_dir, "data", "thirdparty", "deutschebahn-rails.usda")

    # Schema registry + the built plugin must both be discoverable (same wiring as
    # run_parity.py): the codeless schema resources and the loaded C++ scene index.
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
    # Runtime DLLs the compiled dumper needs: USD/PROJ libs (<inst>/bin, <inst>/lib)
    # and the Python DLL (next to this interpreter).
    for d in (os.path.join(inst, "bin") if inst else "",
              os.path.join(inst, "lib") if inst else "",
              os.path.dirname(sys.executable)):
        if d and os.path.isdir(d):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("PYTHONUTF8", "1")

    bindir = os.environ.get("GEO_TEST_BIN") or (
        os.path.join(inst, "tests") if inst else "")
    dumper = os.path.join(bindir, "dumpHydraXforms" + EXE) if bindir else ""
    if not dumper or not os.path.exists(dumper):
        print("run_runtime_parity: set GEO_TEST_BIN (or USD_INST) to the dir with "
              "dumpHydraXforms", file=sys.stderr)
        return 2
    if not os.path.exists(railway_asset):
        print(f"run_runtime_parity: missing railway asset {railway_asset}",
              file=sys.stderr)
        return 2

    py = sys.executable

    # 1) convert the shipped railway asset into the codeless schema (into cwd).
    print("== [1/3] converting railway asset -> crs:binding/crs:position stage ==")
    stage = os.path.join(workdir, "railway_georef.usda")
    sys.path.insert(0, geo_src)
    try:
        import convert_omni_geospatial as cog
        cog.convert(railway_asset, stage)
    except Exception as e:                                  # pragma: no cover
        print(f"convert_omni_geospatial failed: {e}", file=sys.stderr)
        return 1
    if not os.path.exists(stage):
        print("converter produced no stage", file=sys.stderr)
        return 1

    # 2) dump the Hydra-resolved xforms for that stage.
    print("== [2/3] dumping Hydra-resolved xforms (compiled scene index) ==")
    tsv = os.path.join(workdir, "hydra_railway_xforms.tsv")
    with open(tsv, "w") as f:
        rc = subprocess.call([dumper, stage], stdout=f)
    if rc != 0:
        print(f"dumpHydraXforms failed (rc={rc})", file=sys.stderr)
        return rc

    # 3) run the numpy-only parity gate against the same authored stage.
    print("== [3/3] Python-reference vs Hydra parity gate (tol %s mm) ==" % tol)
    env = dict(os.environ)
    env["GEO_RAILWAY_STAGE"] = stage
    env["GEO_HYDRA_TSV"] = tsv
    env["GEO_PARITY_TOL_MM"] = tol
    # keep the committed docs/ figure untouched; --check draws nothing anyway.
    env["GEO_RUNTIME_PARITY_OUT"] = os.path.join(workdir, "runtime_parity.png")
    rc = subprocess.call([py, fig_parity, "--check"], env=env)
    print("== runtime parity %s ==" % ("GREEN" if rc == 0 else "RED"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
