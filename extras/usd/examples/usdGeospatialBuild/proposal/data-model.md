# Experimental authored model

This is a complete candidate for this experiment, not an approved extension of
the standard. Its functional input is pinned separately. The October 2 direction
requires distinct CRS placement attributes and ordinary USD transforms after CRS
placement/resolution. The field definitions below are the tested answer to the
remaining representation questions. No implementation exists when this text is
first frozen. Callable interfaces are not part of this description.

## Authority and composition

The composed USD stage supplies all authored facts. A `CoordinateReferenceSystem`
prim has one `uniform token crs:wkt`, containing a complete CRS-only WKT2 value.
It contains no object placement. It is authoritative for its axes, units, datum,
ellipsoid, projection and embedded calibration. Parsed information is derived.
No independent copies of these facts are USD properties. An override replaces
the whole WKT value; its internal components do not compose independently.

`rel crs:binding` targets exactly one CRS prim. The nearest direct binding
determines source CRS scope, through ordinary reference, variant, layer and
instance composition. Broken/multiple targets are errors. Independently bound
content retains its source CRS when assembled under another bound subtree.
Unbound content retains ordinary USD behavior. A scope-only project container
may provide default/working CRS context without being a model placement.

## Model placement fields — candidate Q2

| Field | USD representation | Authored meaning and absence |
|---|---|---|
| `crs:position` | varying `double3` | Model origin in source CRS, required at a directly bound model. No implicit geographic or height value. |
| `crs:orientation` | varying `quatd` | Right-handed model-frame rotation relative to source local axes. Identity if absent; a non-unit/zero quaternion is invalid. |
| `crs:scale` | varying `double3` | Dimensionless model placement scale along its rotated local axes. `(1,1,1)` if absent; nonfinite or zero values are invalid. |

The position tuple is easting/northing/up for projected CRSs, longitude/latitude/
height for geographic CRSs, and geocentric X/Y/Z for geocentric CRSs. This fixed
tuple convention is candidate Q6 for the latter two families; it is not the WKT
storage-axis order. Each component uses its declared CRS unit and height surface.
Only complete 3D definitions are admitted. Promotion of a 2D dataset to a 3D test
fixture must state an independently chosen height assumption outside the source
data; it cannot become an undocumented runtime default.

Model geometry remains ordinary USD local geometry. Geographic angles appear
only in CRS attributes, never in length-valued xformOps or mesh points. Model
orientation uses grid axes for projected/engineering frames, local east/north/up
at a geographic position, and global Cartesian axes for geocentric frames.
Local geometry distances use the stage's declared length unit after the writer's
explicit asset conformance transforms. Interpreting the CRS's own units is part
of coordinate conversion, not permission to repair source asset metadata.

A directly bound model establishes the anchor and excludes ancestor xformOps.
Its own ordinary xformOps remain post-placement adjustments; descendant xformOps
remain ordinary offsets until another direct model binding. USD's authored
xformOpOrder, inverse operations and reset markers are honored as authored.
The runtime never authors a reset marker or changes any source value.

Conformance is authored by the writer/assembler in an ordinary child Xform and
is separate from instance placement. A suffix/name identifies a conformance
node in these fixtures for human review only; resolution cannot depend on it.
Incorrect asset units/up-axis cannot be inferred from geometry by the reader.

## Project adjustments — experimental Q3 alternatives

The chosen candidate uses the nearest enclosing direct CRS binding as the
working coordinate context for the bound model's ordinary post transform.
With no enclosing binding, the source model CRS supplies that context. A
geographic working context uses the position's derived local ENU length frame
for ordinary Cartesian adjustments. No coordinate epoch is assumed.

The intrinsic source placement is resolved into the consumer's requested CRS
first. The authored post transform then acts in its declared working context;
changing the requested output transports that operator rather than reusing its
numeric translation/rotation in different output axes. In notation, if `P` maps
the working context to the requested output, the post operator is
`P ∘ A ∘ P⁻¹`, applied to the intrinsic resolved point. This semantic order does
not mandate an engine's internal computational path. Ordinary child transforms
act relative to the resolved modelling frame, using normal USD matrix order.

The comparison candidate applies the unchanged post-transform numbers in the
requested output axes. It must be demonstrated as an alternative, including a
counterexample where output selection changes physical placement. It is not
accepted as satisfying requirement 8.

## Resolved modelling frame and result domains

A frame is the first derivative of full source placement and post adjustment
at the model origin. Its origin is double precision. Its three columns express
one stage-length-unit local displacement in output coordinates. In the model
frame, orientation precedes scale in column notation (`R * diag(scale)`).
The derivative uses a centered one-metre physical probe. That probe is a
numerical implementation parameter, reported and checked with smaller/larger
probes; it is not an authored fact or a promised approximation bound.

Ordinary descendant matrices multiply this resolved frame in USD order.
For noncommuting conformance and placement, the conformance matrix acts on
asset-local geometry, then placement orientation/scale, then the resolved
frame; the bound model's own ordinary matrix is the transported post operator.
A full per-point conversion of the corresponding source-local geometry supplies
the comparison control. It is deliberately distinct from the affine rendering
frame. Reset markers stop the descendant matrix accumulation as in USD.

Coordinate-query results use target CRS native units and fixed tuple convention.
Rendering is supported for output CRSs with three length axes. Rendering values
convert those CRS lengths to the stage length unit, with an explicit stage
up-axis permutation (ENU to X/up/-north for Y-up). No source asset conformance is
guessed by this consumer adaptation. Geographic query outputs stay angular;
they cannot be supplied to a length-valued rendering frame.

Working-context post transforms operate on Cartesian lengths in stage units.
For projected/geocentric working contexts, convert all native coordinates to
stage units before applying the ordinary USD matrix and convert back afterward.
For geographic contexts, use local ENU at the unadjusted model origin, with its
ellipsoid-derived Cartesian anchor. Moving a model changes that derived origin.
This is a candidate convention requiring group review, not hidden authoring state.

## Measurements — experimental Q11 association

A bound measurement prim authors `rel crs:coordinateProperties`, whose targets
are `double3[]` attributes on that prim. The relationship identifies absolute
source coordinate arrays explicitly, including composed property paths. A vector
property not targeted by it is not inferred to be a coordinate. Ordinary USD
attributes hold measurement values and observation times; the dataset's existing
index/time association is preserved. Names of those non-coordinate properties
are fixture/data-format metadata, not a geospatial schema prescription.

Each targeted array has the fixed source tuple convention and CRS-defined units.
Resolution changes derived coordinates only, never values, recorded observation
times or source arrays. Fixed grids with changing measurements and moving
positions are distinct. USD time interpolation of placement does not prescribe
scientific interpolation/resampling of measurements. Results retain the original
recorded measurement samples and their association.

The city/global functional intent and requirement 30 are already established.
This experiment tests a possible authored association; it does not reopen
Devin's use-case confirmation or require renderable geometry.

## Dependency declaration — experimental Q12

The root layer authors `customLayerData.geospatialResolutionRequired = true`
for an assembled/exported asset containing geospatial placement/coordinates,
including referenced or unloaded payload content. This existing USD layer
metadata representation is a writer-maintained complete-asset declaration,
readable without scene traversal. It is not claimed to compose automatically.
Assembly writers propagate it; validators check it against available content and
identify unloaded coverage rather than inventing a declaration. A test includes
the stale/missing declaration and the complete unloaded-payload declaration.

## WKT normal form — experimental Q10

The lexical profile validates the original WKT before normalization. It removes
permitted whitespace outside quoted strings, uppercases unquoted keywords and
axis direction identifiers, and gives decimal numeric lexemes a unique value-
preserving spelling using decimal arithmetic. Quoted text and ordering are
preserved, including names, IDs, remarks and extensions. Double-quote escaping
is preserved. Normalization is idempotent and never repairs invalid syntax.

Stored WKT must equal this normal form; validation reports a difference without
rewriting it. This is an additional USD authored-data restriction, not an OGC
requirement. It gives fast identity for this defined lexical class, not semantic
equality of all CRS definitions. Different method encodings, names or metadata
can remain different tokens despite engine equivalence. Meaningful changes in
axes, units or datum must not normalize away.

Coordinate metadata wrappers/coordinate epochs are deferred in full. A frame
reference epoch inside CRS WKT is retained. Observation times and animation
samples are not coordinate epochs. Epoch-dependent requests fail explicitly.
Initial fields must not obstruct a later OGC coordinate-metadata association.

## Export and results — experimental Q13/Q14

Explicit export is a new derived asset, not a source edit. It records complete
output CRS, sampled USD time codes and the sampling/interpolation record in root
customLayerData. Resolved coordinate arrays are authored in that output CRS.
Resolved model geometry retains double anchors and small local float geometry.
Post adjustments are baked once; the exported bound model has identity post
adjustments. It uses ordinary declared CRS/binding/placement facts, with no
private already-resolved flag. A fresh reader resolves it without double
conversion. Flattening composition alone is not this operation.

Results expose their CRS, values/units, operation choice, attributed operation
accuracy and failures. Numerical coordinate agreement, source/control residuals
and model approximation error are separate quantities. A derivative-frame
approximation is compared with per-point coordinate conversion over a stated
finite test domain. Sampled discrepancy is explicitly sampled evidence, not a
certified maximum over every surface point. General certified bounds remain a
design finding; passing vertex tests cannot silently settle requirement 24.
