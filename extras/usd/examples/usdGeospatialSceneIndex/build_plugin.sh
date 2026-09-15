#!/usr/bin/env bash
# build_plugin.sh -- build the usdGeospatialSceneIndex as a LOADABLE Hydra plugin
# .so (SI filter + keyless UsdImaging API-schema adapter + resolver + PROJ engine)
# against an installed from-source USD, and stage a plugInfo.json with the
# placeholders expanded so it can be discovered via PXR_PLUGINPATH_NAME.
#
# This is the Level-1 auto-insertion artifact: with this dir on PXR_PLUGINPATH_NAME,
# usdview / usdrecord auto-insert the scene index AND the adapter surfaces crs:*
# into Hydra -- no SetStage, no code editing the app.
#
# Usage: USD_INST=/tmp/usd-build/inst-current OUT=/tmp/geo-plugin ./build_plugin.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
I="${USD_INST:-/tmp/usd-build/inst-current}"
OUT="${OUT:-/tmp/geo-plugin}"
PYINC="$(python3 -c 'import sysconfig;print(sysconfig.get_path("include"))')"
PYVER="$(python3 -c 'import sys;print(f"python{sys.version_info.major}.{sys.version_info.minor}")')"

RESDIR="$OUT/usdGeospatialSceneIndex/resources"
mkdir -p "$RESDIR"
SO="$OUT/usdGeospatialSceneIndex/libusdGeospatialSceneIndex.so"

CXXFLAGS="-std=c++17 -O2 -fPIC -Wno-deprecated -DUSDGEOSPATIAL_SI_EXPORTS"
INCS="-I$I/include -I/usr/include -I$PYINC"
USDLIBS="-lusd_usd -lusd_usdGeom -lusd_usdImaging -lusd_hd -lusd_hf -lusd_sdf -lusd_gf -lusd_tf -lusd_vt -lusd_work -lusd_arch -lusd_plug -lusd_python"
LDLIBS="-L$I/lib $USDLIBS -lproj -l$PYVER -Wl,-rpath,$I/lib"

echo "[plugin] compiling shared library -> $SO"
g++ $CXXFLAGS $INCS -shared \
    "$HERE/geospatialSceneIndexPlugin.cpp" \
    "$HERE/geospatialSceneIndex.cpp" \
    "$HERE/geospatialAPISchemaAdapter.cpp" \
    "$HERE/geospatialSchema.cpp" \
    "$HERE/geoResolver.cpp" \
    "$HERE/crsEngine.cpp" \
    $LDLIBS -o "$SO"

echo "[plugin] staging plugInfo.json (placeholders expanded) -> $RESDIR/plugInfo.json"
# LibraryPath is relative to the resources dir's parent (Root=".."); use the
# built .so absolute path to be robust. ResourcePath ".", Root "..".
sed \
  -e "s|@PLUG_INFO_LIBRARY_PATH@|$SO|g" \
  -e "s|@PLUG_INFO_RESOURCE_PATH@|.|g" \
  -e "s|@PLUG_INFO_ROOT@|..|g" \
  "$HERE/plugInfo.json" > "$RESDIR/plugInfo.json"

echo "[plugin] done."
echo "  .so:        $SO"
echo "  plugInfo:   $RESDIR/plugInfo.json"
echo "  add to path: export PXR_PLUGINPATH_NAME=$RESDIR:\$PXR_PLUGINPATH_NAME"
