#!/usr/bin/env bash
# render_overfit_glyphs.sh -- author 5 diverse-CRS non-geometric georef bases,
# overlay a geometry-only glyph via visualize_field_glyphs.py, and render each
# through the AUTO-INSERT scene index. SAME script, SAME plugin, ZERO code change
# between locales. Produces docs/overfit_<name>_autoinsert.png.
# NOTE: the reviewer-facing anti-overfit FIGURE is now src/fig_multicrs_positions.py
# (a Matplotlib plot of the five resolved ECEF positions). The per-locale renders
# here frame a single centred glyph on black, so they are pixel-identical and were
# retired as a montage; this script is kept as render infrastructure for a future
# real-globe render montage (Option A).
set -eo pipefail
source /tmp/geoenv.sh
source "$REPO/.venv/bin/activate" 2>/dev/null || true
GEO="$REPO/extras/usd/examples/usdGeospatial"
SI="$REPO/extras/usd/examples/usdGeospatialSceneIndex"
PLUG=/tmp/geo-plugin/usdGeospatialSceneIndex/resources
cd "$GEO"

pgrep -x Xvfb >/dev/null || setsid bash -c 'Xvfb :99 -screen 0 1920x1080x24 &' && sleep 1 || true

# 1. author the 5 non-geometric georef bases
python3 src/overfit_glyph_suite.py

# locale table: name lon lat h epsg framekm glyphkm
LOCALES=(
  "nyc -73.985656 40.748817 0.0 32618 300 40"
  "sydney 151.214000 -33.857000 58.0 32756 300 40"
  "wellington 174.776200 -41.286500 5.0 2193 300 40"
  "quito -78.467800 -0.180700 2850.0 32717 300 40"
  "svalbard 15.650000 78.220000 10.0 32633 300 40"
)

for row in "${LOCALES[@]}"; do
  set -- $row
  name=$1 lon=$2 lat=$3 h=$4 epsg=$5 framekm=$6 glyphkm=$7
  base=/tmp/overfit/${name}_base.usda
  ovl=/tmp/overfit/${name}_glyphs.usda
  cam=/tmp/overfit/${name}_cam.usda
  # 2. geometry-only overlay (no scalar field -> fixed bright glyph color)
  python3 src/visualize_field_glyphs.py "$base" "$ovl" \
      --glyph-km "$glyphkm" --glyph points --fixed-color 0.95,0.75,0.15 >/dev/null
  # confirm ZERO crs:* authored in this locale's overlay
  ncrs=$(grep -c 'crs:' "$ovl" || true)
  # 3. camera scene framing the point (SI does placement)
  python3 "$SI/make_render_scene_point.py" "$ovl" "$cam" "$lon" "$lat" "$h" "$framekm" >/dev/null
  # 4. render through auto-insert SI
  rm -f core.*
  export PXR_PLUGINPATH_NAME=$PLUG:$REPO/pxr/usd/usdGeospatial/resources
  usdrecord --camera /GeoCam --imageWidth 900 --renderer GL "$cam" \
      "docs/overfit_${name}_autoinsert.png" >/dev/null 2>&1 || true
  rm -f core.*
  cov=$(python3 -c "from PIL import Image;import numpy as np;im=np.asarray(Image.open('docs/overfit_${name}_autoinsert.png').convert('RGB')).astype(int);print(round((im.max(2)>50).mean()*100,2))")
  echo "[render] ${name}: EPSG:${epsg} overlay_crs_lines=${ncrs} coverage=${cov}%"
done

# no-plugin negative control for one locale (nyc)
unset PXR_PLUGINPATH_NAME || true
export PXR_PLUGINPATH_NAME=$REPO/pxr/usd/usdGeospatial/resources
rm -f core.*
usdrecord --camera /GeoCam --imageWidth 900 --renderer GL /tmp/overfit/nyc_cam.usda \
    docs/overfit_nyc_noplugin.png >/dev/null 2>&1 || true
rm -f core.*
covc=$(python3 -c "from PIL import Image;import numpy as np;im=np.asarray(Image.open('docs/overfit_nyc_noplugin.png').convert('RGB')).astype(int);print(round((im.max(2)>50).mean()*100,2))")
echo "[control] nyc no-plugin coverage=${covc}% (should be ~0 -> SI does placement)"
echo "DONE overfit renders"
