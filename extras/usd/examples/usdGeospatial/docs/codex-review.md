# Adversarial Review — Geospatial CRS USD Prototype

**Reviewer role:** independent adversary. Goal: break the prototype, not praise it.
**Repo:** `geo-usd` (clone of asluk/USD) · **Branch:** `aluk/geospatial-crs-prototype`
**Example:** `extras/usd/examples/usdGeospatialReencode/`
**Env:** usd-core 26.5, pyproj 3.7.1 / PROJ 9.5.1, numpy. All commands run from the example dir with the repo `.venv`.
**Date of review:** 2026-06-23.

I touched no tracked files and did not run git. Audit artifacts I generated live in
`out/_audit_default.usda`, `out/_audit_fast.usda` (untracked / gitignored) and scratch
scripts in `/tmp/codex_*.py`.

---

## A. What the design actually is (in my own words)

Three files carry the design; two are eye-candy renderers.

- **`src/reencode_georef.py`** — *authoring only*. Builds a stage:
  - `/World` (Xform, defaultPrim), `/World/CRS` (Scope) holding two prims typed
    `CoordinateReferenceSystem` (`WGS84_Geographic3D` = EPSG:4979, `WGS84_ECEF` = EPSG:4978).
    Each CRS prim carries `uniform token crs:wkt` (WKT2_2019), plus custom `crs:epsg`/`crs:displayName`.
  - `/World/GeoSamples/p_i_j` — one `Xform` per subsampled GFS grid cell. Each carries
    `rel crs:binding -> </World/CRS/WGS84_Geographic3D>`, `double3 crs:position = (lon, lat, h)`,
    and a custom `primvars:t2m`. **No `xformOp`, no `resetXformStack`.**
  - Two authoring paths claimed identical: default per-prim `Usd` API
    (`author_samples_usd`, line ~96) and `--fast` `Sdf` batch inside one `Sdf.ChangeBlock`
    (`author_samples_sdf`, line ~117).
- **`src/resolve_runtime.py`** — *runtime resolver*. Walks the stage; for each Xform with
  `crs:position`, follows `crs:binding` (with ancestor inheritance, `crs_of_prim`, line 33),
  reads the bound CRS's WKT, and reprojects `crs:position` → target CRS (default EPSG:4978)
  via a cached PROJ `Transformer` with `always_xy=True` (line 49/64). `--bake` optionally
  writes a renderable `UsdGeomPoints` cloud (scaled ECEF, z-up).
- **`src/verify.py`** — CI-style checks A–D (neutrality by text grep; binding/WKT parse;
  geodetic landmarks; round-trip).
- **`src/multi_crs_example.py`** — authors SiteA (geographic) and SiteB (UTM 10N) at "the
  same place," resolves both to ECEF, asserts distance < 1 cm and scene-neutral.
- `render_evidence.py`, `render_globe_ovrtx.py` — visualization; not load-bearing for claims.

**Design thesis (README):** *schema declares, runtime resolves*; CRS binding is a
relationship analogous to `UsdShadeMaterialBindingAPI`; position is data (`crs:position`);
no transform behavior baked into scene description. The authored layer is "CRS-neutral."

This thesis is **structurally delivered** (see D/E). The geodesy is **correct** (B). The
multi-CRS "proof" is **circular and proves much less than claimed** (C). Several headline
runtime claims in docstrings are **not implemented** (F).

---

## B. Independent geodesy re-derivation

I implemented WGS84 geodetic→ECEF from scratch (closed form, no prototype helpers), using
only the defining constants `a=6378137`, `f=1/298.257223563`, `b=a(1−f)`, `e²=f(2−f)`:

```
N = a / sqrt(1 − e² sin²φ)
X = (N+h) cosφ cosλ ;  Y = (N+h) cosφ sinλ ;  Z = (N(1−e²)+h) sinφ
```
(`/tmp/codex_geodesy.py`)

Results vs the PROJ path the prototype uses (EPSG:4979→4978, `always_xy`):

| check | result |
|---|---|
| derived `b` | `6356752.314245 m` (matches README/verify) |
| N pole: mine vs PROJ z | both `6356752.314245`, `z−b = 0.000e+00` |
| equator/0°: mine vs PROJ x | both `6378137.000000`, `x−a = 0.000e+00` |
| **worst \|mine − PROJ\|, 100k random global pts** (lat ±89.9, h −500..9000) | **1.317089e-09 m** |
| worst round-trip geo→ECEF→geo (PROJ) | **6.47e-12 deg, 8.54e-07 m** |

**Verdict B: HOLDS.** The geodesy is genuinely correct, independently reproduced to ~1.3 nm.
The README's "~3×10⁻⁹ m round-trip" and pole/equator landmark numbers are accurate.
Note this is a property of PROJ + WGS84, not of the USD design — the USD layer contributes
nothing to correctness here; it's a data carrier.

---

## C. Falsifying the multi-CRS claim

**Claim 3:** a point in WGS84 geographic and the *same* point in UTM 10N resolve to the
same ECEF (~0 cm).

### C1 — Diverse points, each in its *correct* UTM zone (`/tmp/codex_multicrs.py`)
11 points across both hemispheres and many zones (Sydney, Quito, Svalbard, Cape Horn,
Singapore, Anchorage, Tokyo, zone edges). Every case: **0.0000 cm**. So *if* you pick the
right zone, geographic↔projected↔ECEF agrees to sub-mm. Fine.

### C2 — The claim is **circular** (the important finding)
`multi_crs_example.py` builds SiteB by `e,n = Transformer(GEO→UTM10N).transform(LON,LAT,H)`
(line 73) and then resolves it by `Transformer(UTM10N→ECEF)`. The net path is
**`GEO → UTM10N → ECEF`** compared against **`GEO → ECEF`**. Since PROJ's UTM↔GEO is an
exact analytic inverse pair, the intermediate UTM step is mathematically annihilated. The
"test" can **never** fail as long as PROJ is self-consistent — it tests PROJ, not the
USD/CRS design.

Demonstration that the zone is irrelevant to the result: I forced **Sydney** (which belongs
in zone 56S) through the hard-coded **UTM 10N**:
```
Sydney: UTM10 E=-7032948.2  N=-9304914.2   (absurd, ~7000 km extrapolated)
        inverse -> lon=151.215300 lat=-33.856800   (recovers original exactly)
        SiteA vs SiteB distance: 0.0001 cm
```
A grossly wrong, physically meaningless UTM coordinate still "passes" at 0.0001 cm. The
example would print `MULTI-CRS COMPOSES ✅` even with a nonsensical projection, because it
never compares against an *independent* ground truth for SiteB.

Sanity that the harness *can* detect error at all: injecting a 100 m height into SiteB only
yields 10000.00 cm — so the metric works; it's the **construction of SiteB** that's circular.

**Verdict C: OVERSTATED.** Multi-CRS reprojection into one target frame is real and correct,
but the prototype's *proof* is self-referential. It demonstrates "PROJ round-trips," not
"two independently-authored CRS encodings of one place agree." A fully independent test
(an externally surveyed UTM benchmark, or a second projection library) is absent
(geographiclib not installed in env; could not substitute). Additionally:

- **Hard-coded zone assumption.** `multi_crs_example.py` pins EPSG:32610 (UTM 10N). There is
  no zone-selection logic anywhere; any real multi-site scene outside zone 10N would author
  physically-wrong eastings/northings that the circular check still "passes." A
  `utm_epsg_for(lon,lat)` helper exists only in *my* scratch script, not the prototype.

---

## D. Is there a hidden `xformOp` / `resetXformStack` / reference-binding?

Generated both paths at stride 30 (1200 samples):
```
python3 src/reencode_georef.py --stride 30 --out out/_audit_default.usda
python3 src/reencode_georef.py --stride 30 --fast --out out/_audit_fast.usda
```
Grep (both files):
```
grep -nE "xformOp|resetXformStack|references|payload|inherits|specializes" out/_audit_*.usda
  -> NONE FOUND (default)
  -> NONE FOUND (fast)
```
Binding is literally `rel crs:binding = </World/CRS/WGS84_Geographic3D>`; position is
`double3 crs:position = (...)` (e.g. `out/_audit_default.usda` p_0_0). No reference/payload
arc is used for binding; composition is untouched.

**Verdict D: HOLDS.** Claim 1 (no translate, no reset, no reference-based binding;
relationship + float64 position only) is **true** in the authored data of both paths.

**Caveat (schema fiction).** `crs:wkt`, `crs:binding`, `crs:position` are all authored with
`custom=False`, i.e. they advertise themselves as *schema-defined* properties. But there is
**no schema** (`/tmp/codex_struct.py`):
- `CoordinateReferenceSystem` prim: `GetPrimTypeInfo().GetSchemaType()` → **False**;
  `GetPrimDefinition().GetPropertyNames()` → **`[]`**.
So the type and all `crs:*` properties are unregistered. `custom=False` on undefined
properties is misleading to the composition/validation system; a strict `usdchecker`/schema
validation would flag these as unknown. "Neutral data" is true, but it's *untyped* data
wearing schema clothing.

---

## E. `--fast` vs default — structural identity (my own check)

Text/byte: identical.
```
md5sum out/_audit_default.usda out/_audit_fast.usda
a0575d53f97f149b20cc254d40efeccb  out/_audit_default.usda
a0575d53f97f149b20cc254d40efeccb  out/_audit_fast.usda
wc -l: 8430 / 8430
```
Semantic (independent of bytes, `/tmp/codex_struct.py`): opened both stages, traversed,
compared `(path, typeName, sorted(attrs), sorted(rels))` per prim:
```
prim count default/fast: 1205 / 1205
ordered structural equality: True
no per-prim diffs
```
Performance side note (not a claim, but observed): per-prim 479 prim/s vs Sdf-batch
9728 prim/s at this stride — the speed rationale is real.

**Verdict E: HOLDS.** Claim 4 is true: the two paths produce byte-identical and
semantically-identical output.

---

## F. Design critique vs the Esri AOUSD CRS proposal intent

Concrete weaknesses a Pixar/Esri reviewer would raise:

1. **`rel crs:binding` is *not* yet analogous to `UsdShadeMaterialBindingAPI` — only
   superficially.** Material binding is a real applied API schema with: well-defined
   *fallback/strength* (`bindMaterialAs` weaker/stronger-than-descendants), *purpose*
   (full/preview), *collection-based* binding, and documented composition/resolution order.
   Here `crs:binding` is a bare relationship with **none** of that. `crs_of_prim`
   (`resolve_runtime.py:33`) implements a single rule — nearest ancestor wins — and there is
   no strength, no purpose, no collection binding, no conflict resolution when multiple CRS
   relationships or list-edit ops appear across layers. The README's own "Status/next"
   admits this ("resolution-rule parity … strength/purpose/collection"), so the analogy is
   **aspirational, not delivered.**

2. **Docstring claims that are not implemented (resolution fiction).**
   `resolve_runtime.py` docstring step 2 says it reads "the stage Target CRS (the CRS bound
   to the composed defaultPrim, or a supplied render CRS)." The code does **not**: target is
   taken solely from `--target-epsg` (default 4978); the authored `WGS84_ECEF` CRS prim is
   never read as a target (`resolve_runtime.py:72,81`). Step 4 claims it "composes with any
   ancestor Cartesian xformOps … geospatial position takes precedence … the same precedence
   rule omniGeoSceneIndex applied over resetXformStack." I checked the source of
   `resolve_world_translation`: it contains **no** `ComputeLocalToWorld` /
   `GetLocalTransformation` / `xformOp` handling (`/tmp/codex_claims.py` → `False`). It does
   pure point reprojection and **ignores all ancestor transforms entirely.** So the central
   "coexist with Xformable" claim — the whole point, per the README ("how a CRS reconciles
   with `UsdGeomXformable`… the answer is *coexist*, demonstrated rather than argued") — is
   **argued in comments, not demonstrated in code.** No test places a CRS-bound prim under a
   transformed ancestor and checks the result. Inheritance itself *does* work (verified:
   child with no binding inherits parent's CRS).

3. **`crs:position` on an `Xform` duplicates / fights `Xformable` semantics.** Putting an
   absolute geodetic position in `crs:position` on a prim that *is* a `UsdGeomXformable`
   means the prim now has two notions of "where it is": its (empty) xform stack and its
   `crs:position`. A `UsdGeomImageable`/`UsdGeomBBoxCache`/`ComputeWorldBound` consumer sees
   the prim at the **origin** (identity xform), because nothing in standard USD knows about
   `crs:position`. So every stock USD traversal, bbox, instancer, and Hydra prim is wrong
   until the bespoke resolver runs. That's not "coexist"; it's "shadow geometry the runtime
   must patch." A defensible alternative the reviewer would push: either (a) make the CRS
   resolution a real *scene index* that *writes* the xform (which the omniGeoSceneIndex PoC
   did, and which this explicitly avoids), or (b) define the separation rigorously so the
   authored Xformable is documented as intentionally identity and downstream tools opt in.
   As-is it silently disagrees with `Xformable`.

4. **Axis-order landmine (data contradicts its own declared CRS).** `crs:position` is
   authored `(lon, lat, h)` (e.g. north pole `= (0, 90, 0)`), but the authored WKT2 for
   EPSG:4979 declares axis order **`(latitude, longitude, height)`** (verified:
   `[('Geodetic latitude','north'),('Geodetic longitude','east'),('Ellipsoidal height','up')]`).
   The prototype only works because **every** transform hardcodes `always_xy=True`
   (8 call sites: `resolve_runtime.py:49`, `verify.py:56,75`, `multi_crs_example.py:55,73`,
   `render_*`). A spec-compliant consumer that honors the WKT axis order reads coordinate[0]
   as latitude = −117° (invalid) → ECEF = `[inf, inf, inf]` (`/tmp/codex_claims.py`). The
   schema nowhere states that `crs:position` is always lon/lat-ordered regardless of the
   bound CRS's authority axis order. For a standards proposal this is a serious unspecified
   ambiguity — the exact class of bug GIS interop is plagued by.

5. **WKT2 is heavy and duplicated; no external-grid / datum-transform path.** Each CRS prim
   inlines a ~1 KB WKT string; `crs:epsg` is also present but `custom`. There's no story for
   datum/epoch transformation grids, time-dependent CRSs, or the "external-grid-file asset
   path" the README lists as open. Choosing CRS by EPSG vs by WKT vs by both is unresolved
   (which wins on mismatch?).

6. **`verify.py` is partly self-confirming.** Check A is a raw text grep (fine, robust).
   But checks C/D re-derive ground truth with the *same* PROJ + the *same* `always_xy=True`
   and even hardcode `CRS.from_epsg(4979/4978)` rather than reading the prim's authored WKT —
   so they cannot catch the axis-order mismatch (#4) or a wrong authored WKT. Check B parses
   WKT but never checks it matches the data's coordinate ordering. The CI is greener than the
   design earns.

---

## VERDICT

| # | Claim | Status |
|---|---|---|
| 1 | Authored scene CRS-neutral: no `xformOp:translate`, no `resetXformStack`, relationship-based binding, float64 `crs:position` | **HOLDS** (data-level). Caveat: properties/type are unregistered yet authored `custom=False` — schema fiction. |
| 2 | Geodetic correctness (pole=b, equator=a, round-trip ~1e-9 m) | **HOLDS.** Independently reproduced to 1.3e-9 m. (Credit is PROJ/WGS84, not USD.) |
| 3 | Multi-CRS: geographic + UTM 10N resolve to same ECEF (~0 cm) | **OVERSTATED → effectively VACUOUS as a proof.** Numerically true but **circular**: SiteB is generated and inverted by the same PROJ pair, so it can't fail; a wrong zone (Sydney via UTM10N) still "passes." Hard-coded zone. |
| 4 | `--fast` Sdf-batch output identical to default | **HOLDS.** Byte- and structure-identical (md5 match, 1205/1205 prims equal). |

**Claims that are FALSE / unimplemented (in code, vs docstrings):**
- Resolver "reads the stage Target CRS bound to defaultPrim" — **false**, target is CLI-only.
- Resolver "composes with / takes precedence over ancestor Cartesian xformOps" — **false**,
  ancestor transforms are entirely ignored; the headline *coexist-with-Xformable* behavior is
  never exercised or tested.

### Top 3 weaknesses to fix (in priority order)

1. **Make the multi-CRS proof non-circular.** Drive SiteB from an *independent* source
   (an externally surveyed UTM/State-Plane benchmark, or a second geodesy library), and add
   automatic UTM-zone selection. Until then, claim only "PROJ reprojection is self-consistent,"
   not "multi-CRS composition is proven." Add a negative test (wrong-zone / wrong-axis) that
   must FAIL.

2. **Resolve the `crs:position` vs `Xformable` conflict explicitly, and either implement or
   delete the unimplemented resolution rules.** Right now stock USD sees these prims at the
   origin. Either (a) ship a real scene index / xformOp resolver that demonstrably composes
   with ancestor transforms (with a test under a translated/rotated ancestor), or (b) document
   the Xformable-identity contract precisely. Strip the docstring claims (target-from-stage,
   ancestor precedence) that the code does not do.

3. **Nail down axis order and make it a real (codeless) schema.** Define `crs:position` as
   canonically lon/lat/h (or honor authority order) *in writing*, register a codeless
   `CoordinateReferenceSystem` schema + `CRSBindingAPI` so `custom=False` is truthful and
   `usdchecker` passes, and have `verify.py` read the *authored* WKT (not hardcoded EPSG) so
   the axis-order trap is actually tested. Then port `MaterialBindingAPI`'s strength/purpose/
   collection semantics that the README promises.

*Bottom line:* the **structural** thesis (neutral, relationship-bound, dual-path-identical)
is genuinely delivered and the **geodesy** is correct. But the prototype's two most
rhetorically important claims — "multi-CRS composes" and "coexists with Xformable" — are,
respectively, **circular** and **unimplemented**. A Pixar/Esri reviewer would accept D/E/B
and send 3/F back for real evidence.
