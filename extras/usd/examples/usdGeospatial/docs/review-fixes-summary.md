# Review-Fix Summary — Geospatial CRS USD Prototype

**Date:** 2026-06-23 · **Author:** claw1 (unattended run) · **Scope:** fixes for the
three top weaknesses in `docs/codex-review.md`.
**Status:** all three fixed, each independently verified with a test that has *teeth*
(can fail on the bug it targets). **Local only — nothing committed or pushed.**

Run everything (self-contained; schema auto-registers via `src/_schema_setup.py`):
```
source <geo-usd>/.venv/bin/activate
cd extras/usd/examples/usdGeospatialReencode
python3 src/reencode_georef.py --stride 40 --out out/earth2_georef.usda
python3 src/verify.py out/earth2_georef.usda            # A–E ALL PASS
python3 src/multi_crs_example.py out/multi_crs.usda     # non-circular PASS
python3 src/test_ancestor_compose.py                    # ancestor compose PASS
python3 src/resolve_runtime.py --in out/earth2_georef.usda
```

---

## Fix #1 — multi-CRS proof was circular → now non-circular  ✅
**File:** `src/multi_crs_example.py`
- Old: SiteB built by `GEO→UTM` then verified by `UTM→ECEF` — a tautology that
  "passed" even with Sydney forced through UTM 10N.
- New: **negative control** — SiteBad reuses SiteB's exact easting/northing but is bound
  to a deliberately *wrong* UTM zone. A correct resolver puts it **1,655 km** away; the
  test fails if it converges.
- **Teeth proven:** simulated a binding-ignoring resolver → collapses SiteBad onto SiteB
  (0 m) → test correctly reports FAIL.
- Auto UTM-zone selection from longitude (no more hard-coded zone). A↔B is now honestly
  labelled a self-consistency *sanity figure*, not the proof.
- *Honesty note:* SiteB's UTM numbers are still the canonical PROJ projection of the
  monument; I did **not** fabricate a fake "surveyed datasheet." The non-circular proof
  lives entirely in the negative control.

## Fix #2 — "coexists with Xformable" was unimplemented → now real + tested  ✅
**File:** `src/resolve_runtime.py`, test `src/test_ancestor_compose.py`
- Old resolver **ignored all ancestor transforms** and the docstring claimed behavior the
  code didn't have (target-from-stage, ancestor precedence).
- New resolution rule, actually implemented:
  `world = ancestor_local_to_world . reproject(crs:position)` — the georeferenced point is
  the prim's world anchor; true ancestor Cartesian transforms compose on top.
- **Target CRS now read from the stage** (`target_crs_for_stage`): explicit override →
  CRS bound to defaultPrim → ECEF fallback. `--target-epsg` default changed to `None`.
- **New test** places a CRS-bound prim under a translated+rotated ancestor:
  - T1 ancestor composition exact (0.000 mm),
  - T2 identity ancestor stays neutral,
  - T3 shows a **7,482 km** gap vs the old ignore-ancestor behavior (teeth).
- Docstrings rewritten to match the code; added the axis-order contract note.

## Fix #3 — schema fiction + axis-order landmine → real codeless schema + contract  ✅
**Files:** `schema/schema.usda` (source), `schema/resources/generatedSchema.usda`,
`schema/plugInfo.json`, `docs/axis-order.md`, `src/_schema_setup.py`, `src/verify.py`
- **Codeless schema** registers `CoordinateReferenceSystem` (concrete typed) and
  `CRSBindingAPI` (single-apply API, modelled on MaterialBindingAPI). After registration,
  `custom=False` is **truthful**: properties resolve from the prim definition; `ApplyAPI`
  works; `HasAPI` reports it.
  - *Gotchas for whoever ports this:* in `plugInfo.json`, `Root` must be `"."` (not `".."`)
    and the per-type `alias` block must be **dropped** for codeless (key==alias collides).
- **Compliance:** `UsdUtils.ComplianceChecker` and the newer `UsdValidation` framework both
  report **zero** CRS/unknown/schema errors on the generated scene. Authoring scripts now
  emit `prepend apiSchemas = ["CRSBindingAPI"]` and `custom`-free `crs:*` props; the only
  remaining `custom` is on `primvars:t2m` (genuinely custom). Both authoring paths stay
  **byte-identical** (md5 match — claim #4 preserved).
- **Axis-order contract** (`docs/axis-order.md`, normative): `crs:position` is ALWAYS
  `(lon/E, lat/N, h)` / east-north-up regardless of the bound CRS authority order.
- **verify.py check E** reads the *authored WKT* (not a hardcoded EPSG), detects EPSG:4979's
  lat-first authority order, and asserts an authority-order misread is detectably wrong.
  **Teeth proven:** data authored in `(lat,lon,h)` order → `radius=inf` → E FAILS.

---

## What I deliberately did NOT do
- No git ops, no commits, no pushes, no branch changes (per standing rule).
- Did not fabricate survey/benchmark coordinates to make #1 look more independent.
- Did not implement MaterialBindingAPI strength/purpose/collection semantics — that's the
  README's *next* scope, beyond these three fixes. The schema is shaped to accept them.

## Suggested next steps (for Aaron to decide)
1. Port binding *strength/purpose/collection* parity (the remaining MaterialBindingAPI gap).
2. Decide EPSG-vs-WKT precedence on mismatch (currently WKT authoritative, documented).
3. External-grid/datum-epoch transform story (time-dependent CRSs) — still open.
