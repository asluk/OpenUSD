# Review-Fix Progress Log

Tracking the fixes from `docs/codex-review.md` (adversarial review 2026-06-23).
Working unattended. Local only — NOTHING committed or pushed without Aaron's go-ahead.

Env: `source /home/horde/.openclaw/workspace-identifiers/geo-usd/.venv/bin/activate`,
run from `extras/usd/examples/usdGeospatialReencode/`. usd-core 26.5, pyproj 3.7.1.

## Fix #1 — multi-CRS non-circular  ✅ DONE (2026-06-23 ~04:11 UTC)
- Rewrote `src/multi_crs_example.py`. Negative control (SiteBad reuses SiteB E/N but wrong
  zone) MUST diverge >100km; proved a binding-ignoring resolver collapses it to 0m → FAIL.
- Auto zone selection from longitude. A↔B now honestly labelled a sanity figure.
- RESULT: MULTI-CRS COMPOSES (non-circular) ✅, exit 0.

## Fix #2 — Xformable coexistence (the big one)  ✅ DONE (~04:30 UTC)
- [x] 2a resolver composes ancestor xformOps (world = ancestor_L2W . reproject(pos))
- [x] 2b resolver reads Target CRS from stage defaultPrim binding (target_crs_for_stage)
- [x] 2c test_ancestor_compose.py: T1 exact, T3 shows 7482 km gap vs ignore-ancestor → teeth
- [x] 2d docstrings rewritten to match code; added axis-order contract note

## Fix #3 — axis order + real codeless schema
- [x] 3a codeless schema registers: CRS concrete typed + CRSBindingAPI single-apply.
      PROVEN custom=False truthful (props resolve from prim definition; ApplyAPI works).
      Files: schema/schema.usda (source), schema/resources/generatedSchema.usda, schema/plugInfo.json.
      Register via PXR_PLUGINPATH_NAME=$PWD/schema. Gotchas hit: Root must be "." (not "..");
      DROP the alias block for codeless (key==alias collides).
- [x] 3b crs:position lon/lat/h axis-order contract: docs/axis-order.md (normative) +
      schema doc strings + resolver docstring. Convention = east-north-up / always_xy.
- [x] 3c verify.py check E reads AUTHORED WKT (not hardcoded EPSG), detects EPSG:4979
      lat-first authority order, asserts authority-order misread is detectably wrong.
      PROVEN teeth: data authored in (lat,lon,h) order -> radius=inf -> E FAILS.

## Final
- [x] verify.py A-E all PASS on out/earth2_georef.usda (10512 samples)
- [x] usdchecker (UsdUtils.ComplianceChecker) + newer UsdValidation: 0 CRS/unknown errors
      on schema-typed scene; only generic upAxis/metersPerUnit remain (unrelated)
- [x] multi_crs_example.py non-circular PASS; test_ancestor_compose.py PASS
- [x] final consolidated re-run + summary doc for Aaron (docs/review-fixes-summary.md)

## DONE 2026-06-23 ~05:00 UTC — all three review fixes complete & verified.
- Authoring now uses the real codeless schema; both paths byte-identical (md5 17724bcc...).
- verify A-E PASS; multi_crs non-circular PASS; ancestor-compose PASS; compliance 0 errors.
- Self-contained via src/_schema_setup.py (no env var needed).
- Git untouched. Nothing pushed.
