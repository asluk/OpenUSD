# CRS identity precedence: `crs:wkt` vs `crs:epsg`

**Status:** normative for this prototype. Resolves adversarial-review item F.5
("Choosing CRS by EPSG vs by WKT vs by both is unresolved — which wins on mismatch?").

## The rule

> **`crs:wkt` (OGC WKT2_2019) is authoritative. `crs:epsg` is an informational
> convenience hint.** When the two disagree, consumers MUST use `crs:wkt`.
> Authoring `crs:epsg` inconsistent with `crs:wkt` is invalid and is flagged by
> `verify.py` check F.

## Why WKT is authoritative (not EPSG)

- **WKT2 is self-contained and exact.** It fully specifies datum (including
  ensemble/realization), ellipsoid, prime meridian, axis order, and units. An
  EPSG code is only meaningful relative to a registry version and can be
  ambiguous across registry editions or for custom/compound CRSs.
- **Not every CRS has an EPSG code.** Custom, engineering, and many compound
  CRSs are expressible in WKT2 but have no EPSG identity. Making EPSG
  authoritative would make those CRSs unrepresentable.
- **Interop safety.** Pipelines that round-trip through PROJ already treat WKT as
  the ground truth; aligning the schema with that avoids a second source of
  truth.

## Practical guidance

- Author `crs:wkt` always. Author `crs:epsg` only as a hint, and keep it
  consistent (the example authors it from `CRS.to_epsg()` of the same CRS object,
  so they cannot drift).
- Tools may *display* or *index* by `crs:epsg`, but must *resolve geometry*
  through `crs:wkt`.
- `verify.py` check F fails the build if any CRS prim carries a `crs:epsg` that
  disagrees with its `crs:wkt`'s own EPSG identity — so a stale/wrong hint can't
  ship silently.

## Where enforced

- `src/resolve_runtime.py` reads `crs:wkt` exclusively for reprojection; `crs:epsg`
  is never consulted in the transform path.
- `src/verify.py` check F cross-checks `crs:epsg` against `CRS.from_wkt(...).to_epsg()`.
- `schema/schema.usda` `crs:epsg` doc string: "Informational; crs:wkt is
  authoritative if they disagree."
