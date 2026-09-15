# Axis-order contract for `crs:position`

**Status:** normative for this prototype. Fixes adversarial-review item F.4
(`docs/codex-review.md`), the "axis-order landmine."

## The problem

OGC WKT2 coordinate reference systems declare an authority axis order. For
EPSG:4979 (WGS84 geographic 3D) that order is:

```
AXIS["Geodetic latitude (Lat)", north]   # axis[0]
AXIS["Geodetic longitude (Lon)", east]    # axis[1]
AXIS["Ellipsoidal height (h)", up]        # axis[2]
```

i.e. **latitude first**. A consumer that honors the WKT axis order would read
`crs:position[0]` as *latitude*. If `crs:position` actually stores longitude in
slot 0 (e.g. `(-117.19, 34.05, 350)`), that consumer interprets latitude as
−117° — invalid — and reprojection yields `inf`. This is the single most common
class of GIS interop bug.

## The contract

> `crs:position` is **ALWAYS** ordered `(x, y, z)` =
> `(longitude / easting, latitude / northing, height)`,
> i.e. **east-north-up**, regardless of the bound CRS authority's declared axis
> order.

Equivalently: all reprojection MUST use PROJ `always_xy=True` (or the moral
equivalent in another library). A consumer MUST NOT consult the WKT axis order
to decide the meaning of `crs:position` slots.

## Why this convention (not authority order)

- It matches how virtually every real pipeline already stores data (GeoJSON,
  most game/3D engines, `always_xy` PROJ usage).
- It makes `crs:position` order independent of which CRS is bound, so a single
  data convention survives rebinding a prim to a different CRS.
- It avoids per-CRS branching in the runtime resolver.

The cost is that the convention is **not** self-describing from the WKT alone —
hence this document and the schema `doc` strings make it explicit, and
`verify.py` check **E** actively tests for violation rather than silently
relying on `always_xy=True` everywhere.

## Where it is enforced / documented

- `schema/schema.usda` — `crs:position` doc string states the ordering.
- `src/resolve_runtime.py` — module docstring "AXIS-ORDER CONTRACT" + the
  reprojection call comment.
- `src/verify.py` — check **E** reads the *authored* WKT, detects an
  authority-lat-first CRS, and asserts the data is consistent with the
  documented east-north-up convention (and that an authority-order
  interpretation would be detectably wrong, so the check has teeth).
