# Dynamic CRS: coordinate epoch and external grids

**Status:** prototype feature. Addresses adversarial-review item F.5 (no story for
datum/epoch transformation grids or time-dependent CRSs).

## Why this matters

Modern geodesy uses **dynamic reference frames** (ITRF realizations, GDA2020,
NATRF2022). In these, a point's coordinates change over time (the frame and the
crust move relative to each other). A coordinate is only fully specified by a CRS
**plus a coordinate epoch** (decimal year). Ignoring the epoch introduces error
that accumulates over time. High-accuracy datum transforms also need
**transformation grids** (geoid/datum-shift assets) that are too large to inline in WKT.

## Schema additions on `CoordinateReferenceSystem`

- `uniform double crs:epoch` — coordinate epoch in decimal years (e.g. `2020.0`).
  `0`/unset means *static / unspecified*; the runtime then uses a plain 3D
  transform.
- `asset[] crs:gridFiles` — optional PROJ transformation-grid asset paths the
  runtime should make available to PROJ when building the transform.

## Resolution behaviour

`src/resolve_runtime.py`:
- If the bound source CRS prim carries a non-zero `crs:epoch`, the resolver issues
  a **4D PROJ transform**, passing the epoch as the time coordinate
  (`transform(x, y, z, epoch)`).
- If `crs:epoch` is unset, the transform is the ordinary 3D one — the epoch path
  is strictly **opt-in** (verified by test D3).

## Demonstration (`src/test_dynamic_crs.py`)

Two CRS prims share the same source WKT (ITRF2014 geographic 3D, EPSG:7912) but
carry **different epochs** (2000.0 vs 2030.0). Resolving to ITRF2008 (EPSG:7911, a
different dynamic realization) yields **different** positions — the displacement
between the two epochs under the ITRF2014↔ITRF2008 time-dependent transform.
Checks:

- **D1/D2 (teeth):** epoch 2000 vs 2030 differ by a non-zero amount; an
  epoch-ignoring (3D) resolver would produce identical results.
- **D3:** a CRS prim with `crs:epoch` unset resolves identically to a plain 3D
  transform — the feature does not perturb static CRSs.

### Magnitude, stated honestly

The demonstrated effect is **small** — the ITRF2014↔ITRF2008 realization difference
is a **millimetre-per-year-scale** rate (the example shows ~7 mm vertical over
30 yr), NOT the ~7 cm/yr absolute plate motion of a fast tectonic plate. The test
proves the epoch is *honoured* (it changes the result, and an epoch-ignoring
resolver would not); it does not claim a large displacement. A transform between
frames with a large relative plate-motion model would show more.

### Important nuance (kept honest)

The epoch only changes the result when **both endpoints are realization-specific
dynamic frames** (e.g. ITRF2014 → ITRF2008). Transforming straight to generic
WGS84 **ECEF (EPSG:4978)** collapses to a static transform and washes the epoch
out — which is itself correct behaviour, and why the test targets a specific
realization rather than 4978.

## Grid plumbing (wired)

`crs:gridFiles` is read by `resolve_runtime._register_grid_files`: each authored
asset path is resolved and its containing directory is appended to PROJ's data-dir
search path before the transformer is built, so PROJ can locate external
transformation grids. Proven by `src/test_grid_files.py` (G1 asset read, G2
directory registered).

## Not yet done (honest)

- An actual grid-*applied* transform is not demonstrated end-to-end: PROJ applies
  a grid only when the grid file exists and an operation selects it, and authoring
  a real GeoTIFF grid needs GDAL / network grid data not available in this
  environment. The plumbing (asset read + PROJ search-path registration) is wired
  and tested; bundling a real grid to exercise an applied shift is a follow-up.
