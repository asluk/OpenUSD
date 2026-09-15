# Hydra Plugin Implementation — Plan & Resume Point

_Created 2026-06-24 by claw1. This is the clean resume point for the usdGeospatial
**Hydra scene-index plugin** effort — a NEW phase, distinct from the codeless
Python reference-runtime work that is already landed and pushed._

---

## Where the codeless work left off (DONE — do not redo)
Branch `aluk/geospatial-crs-prototype` (origin = `asluk/USD`), HEAD **`3630afb88`**.
Full suite green (12 checks), 9 self-generated figures, schema in sync.
- Codeless schema `pxr/usd/usdGeospatial/` (`crs:binding` rel + `crs:position` + opaque WKT CRS prims).
- Python reference runtime `src/resolve_runtime.py` — the implementation-agnostic BEHAVIOR spec:
  `resolve_world_translation`, `anchor_frame`, `nearest_anchor`, `resolve_with_injection`
  (rigid ENU local-frame → ECEF, "inject don't bake").
- Engine seam `src/crs_engine.py` (pyproj as default `PyprojEngine`; `reproject()` + `local_frame_to_ecef()`).
- No-overfit proof: 7 datasets sub-mm vs closed-form geodesy, incl. the REAL converted NVIDIA
  Deutsche Bahn railway (rails on tiles) + 5 projected-CRS benchmarks. Renders: `railway_render.png`,
  `datasets_gallery.png`.
- **Visual==numeric by construction** (renders drawn from the SAME resolver output the assertions check).

## The goal of THIS phase
Build a **Hydra scene index** that performs geospatial resolution at render time — the
ILLUSTRATIVE C++ form of what `resolve_runtime` does in Python. It filters a scene and rewrites the
`xform` of geospatially-bound prims (and dirties their children) so a renderer shows them in the
right place WITHOUT baking transforms into the layer.

## The reference design (NVIDIA `omniGeoSceneIndex`, Apache-2.0)
Vendored read-only at (sparse-checkout): `/tmp/oups/src/hydra-plugins/omniGeoSceneIndex/`
(repo: NVIDIA-Omniverse/OpenUSD-plugin-samples). ~2,564 LOC. Architecture (maps 1:1 to our Python):
- **`OmniGeospatialSceneIndex : HdSingleInputFilteringSceneIndexBase`** — observes a *flattened*
  input scene; `GetPrim`/`GetChildPrimPaths` wrap prims; `_PrimsAdded/_Removed/_Dirtied` keep a
  `SdfPathTable<HdSceneIndexPrim>` cache; `_DirtyHierarchy` propagates xform invalidation to
  children. ⇔ our `resolve_with_injection` + child re-anchoring.
- **`HdOmniGeospatialDataSource`** — intercepts the `xform` locator, `_ComputeGeospatialXform()`
  produces the ECEF/ENU transform; `computedPrim` (the anchored prim) + `computedDependent`
  (children that ride the anchor). ⇔ our `anchor_frame`.
- **API-schema adapters** (`UsdImagingAPISchemaAdapter`, registered in `plugInfo.json`):
  `…ReferencePositionAPIAdapter` (anchor) + `…LocalPositionAPIAdapter` (placed prim). ⇔ our
  reading of `crs:binding`/`crs:position`. NOTE the reference targets the OLD `OmniWGS84*` API
  schemas — OURS must adapt **`crs:binding`/`crs:position`** instead.

## ⚠️ Hydra has changed a lot since this reference (Aaron's warning — confirmed in source)
`geospatialSceneIndex.h` itself flags it: "with Render Delegate 2.0 and the ability to pull data
from a non-flattened scene, this implementation will have to be revisited to work with the
unflattened xform representation." So:
- Treat `omniGeoSceneIndex` as a **design reference, NOT compile-as-is**. Expect API drift in
  `HdFilteringSceneIndex`, data-source locators, `HdXformSchema`, the flattening assumption, and
  `UsdImagingAPISchemaAdapter` registration.
- FIRST task in the new session = pin the **target USD/Hydra version** and check the current
  scene-index / xform-schema API against it before writing code.

## "cf the Gaussians work" — POINTER RESOLVED ✅
Aaron: the "Gaussians work" = Pixar's in-tree **`hdParticleField`** example:
`extras/imaging/examples/hdParticleField/` in PixarAnimationStudios/OpenUSD (dev).
Vendored read-only for reference at `/tmp/dev-hdpf/extras/imaging/examples/hdParticleField/`
(re-fetch: `git clone --filter=blob:none --sparse https://github.com/PixarAnimationStudios/OpenUSD`
then `git sparse-checkout set extras/imaging/examples/hdParticleField`).

**What it is:** a sample **render delegate** for a `particleField` prim type — the reference for
Gaussian-splat rendering, built to assist schema development. Registered as a plugin
(`HdParticleFieldRendererPlugin : HdRendererPlugin`, `plugInfo.json`), usable in usdview via
renderer discovery (`PXR_PLUGINPATH_NAME`). Files: `renderDelegate`, `renderer`, `gsRenderer`,
`renderPass`, `renderBuffer`, `hd3DGaussianSplat`, `rendererPlugin`, `renderParam.h`,
`CMakeLists.txt` (`pxr_plugin(...)`), `plugInfo.json`, plus `py3dgsPlyToUsd.py` / `py3dgsSpzToUsd.py`
converters (mirror our `convert_omni_geospatial.py`).

**⚠️ Key distinction — what to take vs not take from it:**
- `hdParticleField` is a **render DELEGATE** (it draws pixels for a prim type). Our geospatial work
  is a **scene-index FILTER** (it rewrites `xform`s; the renderer is unchanged). So Gaussians is
  NOT the runtime model.
- TAKE from Gaussians: the **in-tree plugin scaffolding pattern** — `extras/.../examples/<name>/`
  layout, `pxr_plugin(...)` CMake macro (we build *inside* `asluk/USD` so this Just Works, no
  external SDK needed), `plugInfo.json` registration, `PXR_PLUGINPATH_NAME` loading, and the
  `.py` converter + example-scene convention. It is CURRENT (tracks dev Hydra) — better build
  template than the NVIDIA plugin.
- TAKE the RUNTIME model from `omniGeoSceneIndex` (the scene-index filtering + anchor xform compute),
  but ported to current Hydra APIs.

**Build implication (big):** because we work inside the OpenUSD source tree (`asluk/USD`), our
plugin can live as a sibling in-tree example (e.g. `extras/usd/examples/usdGeospatialSceneIndex/` or
under `pxr/imaging`) and compile with the SAME `pxr_plugin` machinery as hdParticleField — IF a
full USD source build is available. The codeless venv (usd-core wheel) still can't compile it;
confirm a from-source USD build first.

## Proposed implementation plan (ordered)

### Phase 0 — BOOTSTRAP the build/render path on a known-good example (do this FIRST)
Prove the entire from-source USD + usdview + in-tree-plugin + render loop works on Pixar's own
`hdParticleField` BEFORE writing any geospatial code, so any environment problems surface on a
known-good target, not on our new plugin. Steps:
0a. **Build USD from source** (PixarAnimationStudios/OpenUSD dev) with imaging + usdview +
    examples enabled: `python build_scripts/build_usd.py --usdview --examples <inst>` (pulls
    PySide/PyOpenGL for usdview). This is the from-source build the whole phase needs; the
    codeless usd-core venv cannot compile plugins.
0b. **Confirm `hdParticleField` built** as a plugin under `<inst>/share/usd/examples/plugin/`
    (it ships in the examples tree). Set `PXR_PLUGINPATH_NAME=$PXR_PLUGINPATH_NAME:<inst>/share/usd/examples/plugin/hdParticleField/resources`.
0c. **Get a public 3DGS .ply** (a small Gaussian-splat point cloud — e.g. one of the standard
    public 3DGS sample scenes) and **convert to USD** with the example's own
    `py3dgsPlyToUsd.py` (a `.spz` path also exists via `py3dgsSpzToUsd.py`). License-check the
    chosen splat asset before vendoring.
0d. **Render in usdview** with the hdParticleField renderer selected (renderer discovery /
    `--renderer`), **capture a screenshot**, and send it to Aaron. usdview needs GL/display —
    on a headless host use an offscreen/virtual GL path (e.g. xvfb / EGL) or `usdrecord` with the
    particleField renderer to produce the image.
  → **Deliverable: a screenshot of a public gsplat .ply rendered in usdview via hdParticleField.**
     This validates: from-source build OK, usdview OK, in-tree example plugin loads + renders OK,
     `.ply→USD` converter pattern OK. Everything our scene-index plugin depends on, de-risked.

### Phase 1+ — the geospatial scene-index plugin (after Phase 0 is green)
0. **Inputs (now mostly known):** from-source USD build = established in Phase 0; target USD
   version pinned; Gaussians pointer RESOLVED (`hdParticleField`).
1. **Scaffold** an in-tree plugin mirroring `hdParticleField`'s layout: `CMakeLists.txt` with
   `pxr_plugin(...)`, `plugInfo.json`, `api.h`. BUT register an `HdSceneIndexPlugin` (+ API-schema
   adapters) — NOT an `HdRendererPlugin` (that part follows `omniGeoSceneIndex`, not Gaussians).
2. **Adapters** for OUR schema: read `crs:binding` (rel → CRS prim → WKT) + `crs:position` into
   Hydra data sources (replacing the `OmniWGS84*` adapters in the reference).
3. **Engine call:** the C++ side needs the CRS engine. Decide: link PROJ directly, or call out to a
   small engine lib mirroring `crs_engine.py`. Keep WKT opaque to USD (engine consumes it) — same
   contract as the Python side.
4. **Scene index:** filtering scene index that, for bound prims, computes the ENU→ECEF anchor xform
   (port `anchor_frame`) and overrides the `xform` locator; dirty children on change.
5. **Parity harness (the teeth):** load the SAME scenes used by `generalization_suite.py`
   (Earth-2, the converted railway, the 5 projected benchmarks) through the scene index and assert
   the resolved transforms match the Python runtime / closed-form geodesy to sub-mm. The Python
   suite is the oracle — C++ must agree with it. Reuse `out/railway_georef.usda` etc.
6. **Visual parity (optional, high-value):** if a renderer is available, capture an image and show
   the rails-on-tiles render matches `railway_render.png` — closes the "second runtime produces the
   same picture" loop.

## Hard constraints (carry over — do NOT violate)
- Push only to `aluk/geospatial-crs-prototype` (origin = `asluk/USD`). Never `mistafunk/USD`. No
  force, no PR, commit as `claw1` (`claw1@users.noreply.github.com`).
- Do NOT mention NanoUSD in any tracked writeup/code.
- Keep WKT opaque to USD; engine is the only consumer.
- Proofs non-circular + with teeth (numeric thresholds + negative controls); the Python runtime /
  closed-form geodesy is the oracle the C++ must match.
- nonclaw pushed an OV-PLC doc update but has NOT seen the multi-dataset/render work; HOLD briefing
  until reachable, then reconcile.

## Key paths
- This repo/dir: `/home/horde/.openclaw/workspace-identifiers/geo-usd/extras/usd/examples/usdGeospatial/`
- Codeless schema: `pxr/usd/usdGeospatial/`
- Reference plugin / RUNTIME model (read-only): `/tmp/oups/src/hydra-plugins/omniGeoSceneIndex/`
  (sparse checkout of NVIDIA-Omniverse/OpenUSD-plugin-samples; re-add with
  `git sparse-checkout add src/hydra-plugins`)
- Reference SCAFFOLDING / build template (read-only): `/tmp/dev-hdpf/extras/imaging/examples/hdParticleField/`
  (Pixar OpenUSD dev "Gaussians" example = the hdParticleField render delegate)
- Python venv (NO C++ build headers): `source /home/horde/.openclaw/workspace-identifiers/geo-usd/.venv/bin/activate`
- Memory: `memory/2026-06-24.md` (this session's detail), `MEMORY.md` (backlog index).
