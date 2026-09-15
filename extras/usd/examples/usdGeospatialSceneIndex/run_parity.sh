#!/usr/bin/env bash
# run_parity.sh -- the full parity proof, end to end.
#
#   1. dump_oracle.py  : materialize dataset stages + Python reference-runtime
#                        output + closed-form-geodesy GT  (the oracle).
#   2. build_standalone.sh : compile the C++ engine/resolver/scene-index tests.
#   3. run the three tests : engine vs closed-form, resolver vs oracle+GT,
#                            and the SAME datasets THROUGH the Hydra scene index.
#
# Exits nonzero if any parity check fails. Sub-mm tolerance (default 5 mm; the
# results are 0.0 mm). The Python runtime / closed-form geodesy is the ORACLE the
# C++ scene index must match -- non-circular (GT is closed-form, not a parallel
# PROJ call) and with teeth (negative control: stock Hydra puts these prims at
# the origin; see testSceneIndexParity / the README).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
VENV="$REPO/.venv"
USD_INST="${USD_INST:-/tmp/usd-build/inst}"
TOL_MM="${TOL_MM:-5.0}"

# schema registry + PROJ data
export PXR_PLUGINPATH_NAME="$REPO/pxr/usd/usdGeospatial/resources:${PXR_PLUGINPATH_NAME:-}"
export PROJ_DATA="${PROJ_DATA:-/usr/share/proj}"

echo "== [1/3] dump oracle (Python runtime + closed-form GT) =="
( source "$VENV/bin/activate" && cd "$HERE" && python3 dump_oracle.py )

echo "== [2/3] build C++ tests =="
USD_INST="$USD_INST" OUT=/tmp "$HERE/build_standalone.sh"

echo "== [3/3] run parity =="
echo "--- engine vs closed-form geodesy ---"
( source "$VENV/bin/activate" && cd "$HERE" && python3 gen_parity_cases.py > /tmp/parity_cases.tsv )
/tmp/testCrsEngine /tmp/parity_cases.tsv "$TOL_MM"
echo "--- GeoResolver (stage-level) vs Python oracle + GT ---"
/tmp/testGeoResolver "$HERE/out/parity/oracle.tsv" "$TOL_MM"
echo "--- Hydra scene index vs Python oracle + GT ---"
/tmp/testSceneIndexParity "$HERE/out/parity/oracle.tsv" "$TOL_MM"
echo "== PARITY GREEN =="
