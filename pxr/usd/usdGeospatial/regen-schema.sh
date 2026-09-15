#!/usr/bin/env bash
# regen-schema.sh -- regenerate the CODELESS usdGeospatial schema registry files
# (generatedSchema.usda + plugInfo.json) from schema.usda using usdGenSchema.
#
# This is the usdGeospatial library (pxr/usd/usdGeospatial), file-layout-aligned
# with Simon Haegler's mistafunk/USD `geospatial-prototype` branch, but authored
# CODELESS (skipCodeGeneration = true) -> no C++ build required.
#
# The usd-core wheel ships pxr/Usd/usdGenSchema.py but NOT as a console script,
# does NOT bundle the jinja2 codegen templates, and does NOT ship the base
# usd/schema.usda meta-schema. This bootstraps all three without a full build.
#
# Usage:  ./regen-schema.sh            # regenerate in place
#         ./regen-schema.sh --check    # regenerate to temp and diff (CI sync check)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # .../pxr/usd/usdGeospatial
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"                   # geo-usd
VENV="$REPO_ROOT/.venv"
USDGENSCHEMA="$VENV/lib/python3.10/site-packages/pxr/Usd/usdGenSchema.py"
USD_VERSION_TAG="v26.05"   # must match usd-core in the venv
TMPL_DIR="${USDGS_TEMPLATE_DIR:-/tmp/usdtmpl}"

# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"

# --- 1. ensure codegen templates + base meta-schema are present ---------------
if [[ ! -f "$TMPL_DIR/plugInfo.json" ]]; then
  echo "[bootstrap] fetching codegen templates ($USD_VERSION_TAG) -> $TMPL_DIR"
  mkdir -p "$TMPL_DIR/usd"
  base="https://raw.githubusercontent.com/PixarAnimationStudios/OpenUSD/$USD_VERSION_TAG/pxr/usd/usd"
  for t in plugInfo.json schemaClass.h schemaClass.cpp wrapSchemaClass.cpp \
           tokens.h tokens.cpp wrapTokens.cpp api.h moduleDeps.cpp module.cpp; do
    curl -fsSL "$base/codegenTemplates/$t" -o "$TMPL_DIR/$t"
  done
  curl -fsSL "$base/schema.usda" -o "$TMPL_DIR/usd/schema.usda"
fi

# The subLayer @usd/schema.usda@ must resolve next to schema.usda.
mkdir -p "$HERE/usd"
cp -f "$TMPL_DIR/usd/schema.usda" "$HERE/usd/schema.usda"

run_gen() {  # $1 = output dir
  ( cd "$HERE" && python3 "$USDGENSCHEMA" schema.usda "$1" -t "$TMPL_DIR" )
}

substitute() {  # standalone plugInfo: resources next to plugInfo, root '.'
        # Also injects the SdfMetadata registration for the binding-strength field
        # `bindCRSAs` (usdGenSchema does not emit SdfMetadata; hand-maintained,
        # mirroring how usdShade registers `bindMaterialAs`).
  sed -e 's#@PLUG_INFO_LIBRARY_PATH@##' \
      -e 's#@PLUG_INFO_RESOURCE_PATH@#resources#' \
      -e 's#@PLUG_INFO_ROOT@#.#' \
      -e 's#"Info": {#"Info": {\n                "SdfMetadata": {\n                    "bindCRSAs": {\n                        "appliesTo": ["relationships"],\n                        "displayGroup": "Geospatial",\n                        "documentation": "Strength of a crs:binding relative to bindings on descendant prims: weakerThanDescendants (default) or strongerThanDescendants.",\n                        "type": "token"\n                    }\n                },#' \
      "$1"
}

if [[ "${1:-}" == "--check" ]]; then
  tmp="$(mktemp -d)"
  run_gen "$tmp" >/dev/null
  ok=1
  diff <(cat "$tmp/generatedSchema.usda") "$HERE/resources/generatedSchema.usda" \
    >/dev/null || { echo "[check] generatedSchema.usda OUT OF SYNC"; ok=0; }
  diff <(substitute "$tmp/plugInfo.json") "$HERE/plugInfo.json" \
    >/dev/null || { echo "[check] plugInfo.json OUT OF SYNC"; ok=0; }
  rm -rf "$tmp"
  [[ $ok -eq 1 ]] && { echo "[check] schema resources in sync ✅"; exit 0; } || exit 1
fi

# --- 2. regenerate in place ---------------------------------------------------
tmp="$(mktemp -d)"
run_gen "$tmp"
mkdir -p "$HERE/resources"
cp -f "$tmp/generatedSchema.usda" "$HERE/resources/generatedSchema.usda"
substitute "$tmp/plugInfo.json" > "$HERE/plugInfo.json"
rm -rf "$tmp"
echo "[regen] wrote resources/generatedSchema.usda and plugInfo.json ✅"
