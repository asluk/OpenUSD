# Executable candidate rules

This contract supplies explicit hypotheses for the complete build. It does not
select the final schema. `runtime-behavior.md` remains the proposed normative text;
`runtime-open-decisions.md` identifies the choices awaiting specification review.

## Definitions and composed scope — R1–R8, R25–R27

An experimental `GeospatialCRS` prim contains complete three-axis WKT in `crs:wkt`.
Definitions describe coordinates, independently of object placement. A registry
identifier alone is rejected. `crs:binding` resolves forwarded targets and requires
one definition prim. Search the prim and then its ancestors for the nearest composed
relationship. The `error` policy rejects an explicit empty relationship; `inherit`
continues searching. Both execute. A CRS change inside an existing offset chain
requires a new explicit position in this candidate.

USD supplies opinion strength and target remapping. Equivalent composed sublayer,
reference, payload, inherit, specialize, variant and native-instance cases resolve
identically. Portable references carry their definition within reference scope;
an out-of-scope relationship is not presumed to survive composition. Consuming
stages declare units/up-axis explicitly instead of assuming layer metadata composes.

Dependency candidates use root-layer `customLayerData.geospatialBuild` or
default-prim `customData.geospatialBuild`, with `required`, `roots` and `targetWkt`.
Their discovery requires no traversal. Subsequent validation checks coverage,
missing/stale declarations, missing definitions, nested positions and participating
geometry outside position scope. Unaware USD reads unchanged ordinary authored data.

## Position and asset conventions — R9–R15

`attribute` records `geo:position` as double3. `translate` records
`xformOp:translate:geoPosition` as double3, marked by `geo:isAnchor`; that marked
op is excluded from ordinary offsets. USD interpolates the native values before
conversion. The nearest absolute position cuts all ancestor placement. Ordinary
xform ops below it compose in USD order. A reset inside the offset chain resets
offsets while retaining the CRS position; this is an explicit candidate rule.

`scene_conventions` reconciles metres-per-unit and Y-up/Z-up once. Row-vector
Y-up offsets `(x,y,z)` map to `(x,-z,y)`. `author_conformed` requires metre-scale,
canonical-axis geometry already supplied by an asset adapter. The centimetre/Y-up
test exposes the physical-size error from choosing the wrong policy. Binding does
not edit scene metadata or source asset conformance.

At a geographic position this candidate interprets modelling offsets in a local
east/north/up metric basis. East uses `(N+h) cos(latitude)` and north uses `M+h`,
where N and M are the ellipsoid's prime-vertical and meridional radii from WKT.
Convert metres into the declared angular units at the operation input; ordinary
scene distances are never treated as angles. Projected/geocentric offsets use
their linear units. At a pole the geographic east basis is rejected; an explicitly
Cartesian position provides the tested alternative. These are choices about R10.

`offset_basis=cartesian_tangent` is a second geographic-offset interpretation.
Convert the anchor into the geocentric representation of its own declared datum,
construct orthonormal east/north/up vectors from its longitude/latitude, add the
metric offsets there, and then convert to the chosen output. This does not change
the native position or supply a missing datum. On every provider railway curve,
it reduces the mismatch with original source vertices from 16.7 cm under coordinate
linearization to about 42 micrometres, consistent with stored float-point precision.
That result supports selecting an offset rule; it does not establish survey accuracy.

Optional `geo:projectBinding` and `geo:projectTransform` on the anchor convert
native coordinates into a project CRS, apply placement there, and convert into
the consumer output. Native coordinates remain authored and asset corrections
remain child ops. The competing `ancestor_after_position` experiment deliberately
falsifies R11: a parent translation moves an absolute position by 1,000 m.

The AECO experiment uses supplied complete local-grid and compound Lambert-93/IGN69
WKT. Its base maps from `(1000,1000,33)` to approximately `(648200,6862200,33)`.
Site-grid offsets rotate/scale through calibration, so the same numerical offsets
in Lambert-93 mean a different location. The provider's explicit asset adapter
reconciles the tower's Y-up and misleading centimetre declaration. Relocation and
a constructed five-degree incline execute without editing the source asset.

## Shared result and consumers — R16–R19, R28–R29

`SceneResolver.resolve(time, target)` returns double matrices, local geometry,
topology, operation provenance, diagnostics, revision and the chosen profile.
`consumer_override` gives an explicit request precedence; `scene_locked` rejects
a target conflict. Geographic output is either rejected or returned as pointwise
coordinates, with Euclidean relative-placement queries rejected. Cartesian output
supports world positions, bounds, relative placement and coordinate reporting.

The headless resolver requires no renderer. A compiled C++ filtering scene index
overlays its result on retained input and emits added/removed/dirtied notices.
Stock Storm renders that scene index directly. A separate real Kit process writes
the same result into Fabric: the full linear transform, including shear, is folded
into small float points; world placement stays double. Fabric points, positions
and extents are read back. Neither adapter changes authored USD or loads the retired
geospatial implementation. These are shared-result consumers, not independent solvers.

The independent numerical adapter uses PyGeodesy's Karney ECEF and exact transverse
Mercator arithmetic. It supports static, same-datum geographic/ECEF/projected
conversions and rejects unsupported datum/grid/projection operations. WKT parameter
parsing is shared; PROJ coordinate arithmetic is not. Both hemispheres and full
scene origins are compared, with residual distance distinct from operation accuracy.
This is numerical independence in the stated scope, not independent authorship or
approved full-requirement conformance.

## Time, edits, instances and export — R7, R19–R20

USD object-change notices invalidate cached resolution. Output CRS and time are
cache keys. Invalidation is conservative; every consumer receives the next complete
evaluated frame. Native instance proxies and point-instance transforms/masks expand
into resolved geometry; prototype geometry is not also counted as a visible instance.

Export explicitly creates a new stage with output WKT, sample times and disclosure
that interpolation between baked samples differs from native-CRS evaluation.
`geospatialBuildResolved` identifies already resolved coordinates. Re-reading in
that CRS uses the exported ordinary transforms; another output converts once from
the baked CRS. Original placement is not applied again. Source data remains unchanged.

## Extent and failure — R21–R24, R28

`affine` derives a basis from symmetric 0.25 m coordinate probes and retains a
double anchor with local geometry. `per_vertex` transforms every evaluated vertex,
retaining a double origin plus small local points. Topology and polygon ring
grouping survive fixture preparation. Curves retain linear segments; nonlinear
transformation of unsampled continuous edges is not claimed to be identical.
Unsupported geometry evaluators fail explicitly.

Each geometry result reports maximum affine-versus-pointwise vertex distance in
metres and the sampled local extent. An explicit finite nonnegative
`geo:maxErrorMetres` budget rejects affine placement when a vertex exceeds it.
The 20 km cube exhibits about 40 m displacement while centimetre detail remains
measurable at Earth-sized coordinate magnitude. The bound applies to listed
vertices at the evaluated time. A continuous surface guarantee or universal
suitability threshold is not invented; R24's domain is an actual design question.

PROJ selects the best locally available non-ballpark operation, with downloads
disabled. `require_unique` additionally rejects multiple operations. Missing grids,
nonfinite coordinates, missing coordinate epochs for dynamic definitions, malformed
geometry and domain errors reject the entire result. The ITRF case changes with
explicit coordinate epoch; animation time never supplies it. Missing grids produce
no horizontal-only substitute. Operation provenance accompanies successful results.

## Dataset hypotheses

Railway source bytes, object identities and every original coordinate are retained,
including polygon grouping. Fresh fixture preparation explicitly interprets the
third ordinate as WGS84 ellipsoidal height and selects UTM for local modelling,
while retaining the original geographic array. This does not establish missing
vertical reference or epoch. Provider USD is resolved separately and all its curve
interiors are compared to the original source.

The scalar field retains all raw values in non-geometric records. Its removable
visualization covers all 2,664 samples. Explicit WGS84/zero-height preparation uses
ECEF so poles need no guessed east direction. Physical units, forecast origin and
timestamp remain unknown. Consistency does not replace certified accuracy controls.

Primary references: [Karney ECEF](https://mrjean1.github.io/PyGeodesy/docs/pygeodesy.ecef.EcefKarney-class.html),
[exact transverse Mercator](https://mrjean1.github.io/PyGeodesy/docs/pygeodesy.etm.ExactTransverseMercator-class.html),
[PROJ operation selection](https://pyproj4.github.io/pyproj/stable/api/transformer.html),
[time-dependent Helmert](https://proj.org/en/stable/operations/transformations/helmert.html),
and [Fabric geometry](https://docs.omniverse.nvidia.com/kit/docs/usdrt.scenegraph/7.6.2/fabricsd/usdrt_fsd_geometry.html).
