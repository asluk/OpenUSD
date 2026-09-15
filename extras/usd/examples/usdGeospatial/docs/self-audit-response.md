# Self-Audit Response (2026-06-23)

After the 7 review-fix commits, an independent adversarial self-audit
(`/tmp/selfaudit-findings.md`, fresh-eyes subagent) re-reviewed the changes. It
found **no outright-false claims** but 1 overstatement + several gaps/bugs. This
doc records what was found and how each was resolved.

## Defects found and fixed

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| **D0** | spec-correctness | **Collection-vs-direct precedence was BACKWARDS.** UsdShadeMaterialBindingAPI rule [4] (and `materialBindingAPI.cpp` ~L803): at the *same prim*, a collection binding that includes the prim is STRONGER than a direct binding. The resolver returned direct first and test S7 asserted "direct beats collection." | Rewrote `_binding_rel_for_purpose` precedence ladder to: purpose-collection > purpose-direct > all-collection > all-direct. Fixed S7 to author both bindings on the *same* prim and assert the collection wins. (The audit itself missed this by conflating purpose tiers; caught by reading the spec source directly.) |
| **D1** | medium | `verify.py` check E **false-positive** on valid `lon≈lat` data (the swap-detectability "teeth" test used the authored coordinate, which is undetectable when lon≈lat) → would block CI on legitimate near-diagonal coordinates. | Teeth check now uses a **synthetic probe point** (-123.4, 17.6) with distinct lon/lat; the authored data is still validated for the contract (`conv_ok`), but detectability is judged on the probe, not the data value. |
| **D2** | low | Resolver **crashed** with an opaque pyproj `TypeError` when `crs:binding` targeted a non-CRS / WKT-less prim. | `crs_of_prim` now guards missing/None/invalid WKT, emits a `[resolve] WARNING ... skipping` to stderr, and returns no binding. |
| **D3** | low/perf | `UsdGeom.XformCache()` rebuilt per-prim in `ancestor_local_to_world` → no reuse across a full-stage resolve. | `ancestor_local_to_world` accepts a shared `xform_cache`; `main()` and `resolve_world_translation` thread one cache through the traverse. |
| **D4** | framing | dynamic-CRS docs/test called the epoch effect "plate motion / fast plate," inflating a mm/yr ITRF-realization-rate (~7 mm vert / 30 yr) into ~cm/yr plate motion. | Reworded `docs/dynamic-crs.md` + `test_dynamic_crs.py` to state the magnitude honestly (mm/yr-scale realization difference, not plate motion). Mechanism was always correct. |
| **D5** | latent | Collection tie-break used `cands[0]` (USD relationship iteration order), not UsdShade's documented **lexicographically-smallest binding name** rule [5]/[6]. Worked only by accident of USD's sorted iteration. | Collection candidates now explicitly sorted by binding name before selection. |

## Audit findings accepted as-is (not defects)

- **Claim 2 semantic caveat:** ancestor rotation is applied to the absolute ECEF
  vector, so a 90° rig rotate swings the site around Earth's axis. This is the
  literal, intended meaning of `world = ancestor_L2W · reproject(pos)` and is the
  documented design; noted for reviewers but not "wrong."
- **Claim 1 nuance:** the non-circular teeth come from the `pass_pos ∧ pass_neg`
  conjunction, not the negative control alone. The test is sound; narration in the
  example already credits both checks.
- **Schema regen needs network on first run** (fetches templates/base layer). True
  and documented in `regen-schema.sh`; the committed files reproduce offline once
  cached.

## Still genuinely open (need out-of-environment resources)

- A compiled `usdchecker`-discoverable validator plugin (needs a C++ build).
- An end-to-end grid-*applied* transform (needs GDAL / a real PROJ GeoTIFF grid).

(Cross-layer / list-edited binding coverage — previously listed here — is now
closed by `src/test_binding_composition.py`: L1 sublayer override, L2 list-edit
prepend, L3 list-edit delete all pass; `crs_of_prim` reads composed targets.)

All fixes verified: full suite green, both authoring paths byte-identical, schema
resources in sync.
