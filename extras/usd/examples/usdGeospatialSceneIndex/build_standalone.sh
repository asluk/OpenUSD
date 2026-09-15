#!/usr/bin/env bash
# build_standalone.sh -- build the parity tests out-of-tree against an installed
# USD (the from-source build at $USD_INST). This is the de-risked path used for
# the parity milestone; the in-tree CMakeLists.txt is the canonical example build.
#
# Usage:  USD_INST=/tmp/usd-build/inst ./build_standalone.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
I="${USD_INST:-/tmp/usd-build/inst}"
PYINC="$(python3 -c 'import sysconfig;print(sysconfig.get_path("include"))')"
OUT="${OUT:-/tmp}"

CXXFLAGS="-std=c++17 -O2 -fPIC -Wno-deprecated -DUSDGEOSPATIAL_SI_EXPORTS"
INCS="-I$I/include -I/usr/include -I$PYINC"
USDLIBS="-lusd_usd -lusd_usdGeom -lusd_usdImaging -lusd_hd -lusd_hf -lusd_sdf -lusd_gf -lusd_tf -lusd_vt -lusd_work -lusd_arch -lusd_plug -lusd_python"
LDLIBS="-L$I/lib $USDLIBS -lproj -lpython3.10 -Wl,-rpath,$I/lib"

echo "[build] crsEngine unit test"
g++ $CXXFLAGS $INCS "$HERE/testCrsEngine.cpp" "$HERE/crsEngine.cpp" \
    -L"$I/lib" -lusd_gf -lusd_tf -lusd_arch -lproj -Wl,-rpath,"$I/lib" -o "$OUT/testCrsEngine"

echo "[build] geoResolver parity (stage-level)"
g++ $CXXFLAGS $INCS "$HERE/testGeoResolver.cpp" "$HERE/geoResolver.cpp" "$HERE/crsEngine.cpp" "$HERE/geospatialSchema.cpp" \
    $LDLIBS -o "$OUT/testGeoResolver"

echo "[build] scene-index parity (through Hydra)"
g++ $CXXFLAGS $INCS "$HERE/testSceneIndexParity.cpp" "$HERE/geospatialSceneIndex.cpp" \
    "$HERE/geoResolver.cpp" "$HERE/crsEngine.cpp" "$HERE/geospatialSchema.cpp" \
    $LDLIBS -o "$OUT/testSceneIndexParity"

echo "[build] done: $OUT/testCrsEngine  $OUT/testGeoResolver  $OUT/testSceneIndexParity"
