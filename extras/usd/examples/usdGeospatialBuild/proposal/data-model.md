# Authored model derivation

Authority: the entire unpublished local candidate, SHA-256 `a5444966c41e3a067d7c4db5b2e9a300a08b17fcce377bd6fb24727b390e6904`, based on `39c8fb816a9113b14c8f64b020270724b8357312`. [proposal-source.txt](proposal-source.txt) is the sole proposal authority. These files record derivation and do not add normative choices. Proposed details remain under author review.

Existing uniform token `crs:wkt` arrives through reference-based binding and composed applied `GeospatialCRSBindingAPI`. New candidate placement properties belong to the directly bound Xformable anchor, not the CRS definition. No duplicate epoch, units, axes, role relationship or layer flag is introduced.

### CRS association and model placement

**Proposed detailed definitions, under review in questions 2 and 6.** Friday's
direction of new placement attributes and ordinary transforms afterward is
already decided. The following names, types, fallbacks and basis conventions
are concrete proposals to make that direction derivable.

#### Authored properties

`GeospatialCRSBindingAPI` defines the following placement properties on the
directly bound `UsdGeomXformable` anchor. The existing reference brings in the
source CRS definition; these properties describe an instance's placement in it.
They are not properties of the shared `CoordinateReferenceSystem` definition.

| Property | USD type | Variability | Fallback | Meaning |
|---|---|---|---|---|
| `crs:position` | `double3` | varying | None | Absolute source-CRS position of the model's placement origin. All three components must be supplied for a 3D placement. |
| `crs:orientation` | `quatd` | varying | Identity rotation | Right-handed rotation from the model's placement axes to the source placement basis defined below. |
| `crs:scale` | `double3` | varying | `(1, 1, 1)` | Dimensionless instance scale along the model's three placement axes, applied before orientation. |

These fields supply the authored position, orientation and scale required by
requirements 9–12 and 20. They do not duplicate axes, units, datum, projection
parameters or reference-frame metadata already represented in WKT. They do not
encode asset-convention repairs or output-dependent convergence and scale.

A directly bound anchor with no resolved position has an incomplete placement;
a reader must not invent a zero position or missing height. CRS library prims
that merely define a coordinate system do not require a model placement.
An explicitly blocked orientation or scale is unavailable; blocking a field
does not instruct a consumer to substitute its fallback.
Placement values must be finite and the orientation must represent a unit
quaternion under Core's rotation semantics. Invalid authored values are
validation failures, distinct from an engine discovering that a valid position
is outside an operation's domain.

#### Position components

Propose fixed semantic component order, independent of WKT storage order:

| Source coordinate system | `crs:position` component order |
|---|---|
| Projected or Cartesian system with easting, northing and up | easting, northing, up |
| Geographic 3D system | longitude, latitude, height |
| Geocentric Cartesian system | geocentric X, geocentric Y, geocentric Z |

For projected components, the first row carries forward requirement 13. The
geographic and geocentric rows are proposed answers to question 6. Geographic
longitude-first order is a proposal choice, not a recorded Friday decision.

Values use each component's declared WKT unit and height reference. A consumer
maps these semantic roles to the declared source axis order at the engine
boundary; it does not change the authored WKT to match USD axes. A latitude or
longitude component is never inserted into a length-valued xformOp.
Scene `upAxis` does not reorder `crs:position`.

This table must not be described as covering every OGC coordinate-system type.
Polar directions, differently directed axes and other component sets need an
explicit mapping before they can be claimed as supported. A two-axis CRS alone
does not supply the height reference for a 3D placement.

#### Orientation and scale basis

Propose the following bases so that an identity quaternion has a defined meaning:

- In a projected or derived Cartesian grid, orientation is relative to that
  grid's ordered placement axes. Grid north is not silently replaced by true
  north, and grid distance is not silently replaced by ground distance.
- At a geographic position, orientation is relative to the geodetic
  east–north–up tangent basis at that position. Up is the ellipsoid normal.
  Use the existing EPSG geocentric/topocentric construction; angular coordinate
  increments are not model distances. A gravity-related height remains a
  gravity-related height and any necessary vertical conversion must succeed
  explicitly before this ellipsoidal construction can be evaluated.
- In a geocentric Cartesian CRS, orientation is relative to geocentric X/Y/Z.
  An upright building in that CRS generally needs a non-identity orientation.

The geographic basis proposal follows established
[EPSG/PROJ topocentric conversion](https://proj.org/en/stable/operations/conversions/topocentric.html).
It is a convention to confirm with the geospatial authors, particularly where
survey vertical and ellipsoid-normal vertical differ; Friday did not specify it.

The quaternion uses the existing OpenUSD unit-quaternion meaning, rather than a
new Euler-angle order. Scale acts along the model's placement axes before
rotation into the source basis: Core's row-vector convention orders these two
authored operations as `S * R`. This is their mutual order, not a complete
point-evaluation formula without the stage/basis mappings below. The placement
origin is the pivot; there is no additional CRS pivot attribute. An authored
ordinary USD pivot remains part of the later xform stack.

Position units do not set geometry units. Model offsets remain ordinary scene
distances under requirement 14. Their relation to source-CRS length units is a
unit conversion, separate from the dimensionless instance scale. Components
must be expressed in a common length unit before a Euclidean rotation; a
compound CRS can declare different horizontal and vertical units. A WKT
projection or site-calibration scale and an authored instance scale are
distinct: a reader must not apply the same conversion factor through both.
Unit/up-axis repairs for an imported asset remain the writer's or assembler's
responsibility.

**Remaining frame definition under question 6:** the mapping from a conformed
model's stage axes into this ordered source basis, and from a resolved basis
back to stage axes, still needs an exact convention. In particular, an identity
orientation in a Y-up stage cannot be derived solely from an east/north/up
tuple order. Ordering the authored scale and orientation does not silently
supply this missing mapping or define how scene-unit offsets become source
coordinates. No asset-correction transform may be inferred or authored by the
resolver to fill it.

Propose permitting finite signed scale components as ordinary geometric scale;
reflection does not change the CRS axis declaration. A zero component yields a
singular placement. Forward locations can still be computed, but a request
requiring its inverse must fail visibly. This policy, and the proposed identity
fallbacks, require review rather than being inferred from prototype behavior.


### WKT string normalization

**Proposed authoring profile, under review in question 10.** This section
specifies WKT text handling; coordinate resolution and CRS equivalence are
distinct operations.

#### Scope and source of the profile

Retain `uniform token crs:wkt`. Prescribe a **lossless lexical normal form** for
complete CRS WKT, using the grammar and preferred spellings in
[OGC 18-010r11 / ISO 19162, clauses 6–7 and Annex B](https://docs.ogc.org/is/18-010r11/18-010r11.pdf).
That document permits multiple spellings and recommends writer conventions;
it does not prescribe a unique canonical CRS identity string.

This is a proposed USD authoring profile of those conventions. It does not
establish a new geospatial equivalence algorithm or require a particular engine.

1. Emit preferred WKT keywords in uppercase and enumerations in their prescribed
   spelling; emit square brackets and no padding outside quoted text.
2. Preserve quoted content exactly, including names, remarks, case and internal
   whitespace. Use the WKT escaping rules. Preserve all represented nodes and
   their meaningful order; do not drop identifiers, units, axis declarations,
   datum metadata, usage metadata or reference-frame epochs.
3. Preserve numeric values exactly. For productions requiring integers, use
   [W3C canonical integer spelling](https://www.w3.org/TR/xmlschema-2/#integer-canonical-representation).
   For real-valued productions, expand any finite decimal exponent exactly and
   use [W3C canonical decimal spelling](https://www.w3.org/TR/xmlschema-2/#decimal-canonical-representation).
   Do not round through binary floating point. This numeric convention is an
   explicit proposed profile choice, not an OGC or PROJ requirement.
4. Preserve the declared coordinate interpretation. An authority lookup must
   not replace the supplied definition. Axis reordering, unit conversion and
   the resolution of a CRS are not WKT string normalization.

Examples of the numeric convention: real-valued `1`, `1.0` and `1E0` emit `1.0`;
integer-valued `ORDER[1]` remains `ORDER[1]`. An ellipsoid value
`6378137.12345678912345` keeps that exact value. Unsupported syntax must be
reported rather than silently discarded by the normalizer.

The proposal can reference these established lexical rules without prescribing
a novel transformation algorithm. An implementation can use an existing WKT
parser/tokenizer and exact-decimal library; conformance depends on the specified
output and preservation, not the library name.

#### What token comparison establishes

Equal normalized tokens establish identity of the preserved serialized
definition. Unequal tokens establish only that those serialized definitions
differ. They must not, by themselves, establish that the CRSs differ in
coordinate meaning.

For example, changing a CRS display name leaves different authored information
that normalization must retain, while an established geospatial engine can
still recognize equivalent coordinate meaning. Structural alternatives, such
as permitted parameter-order differences, also require semantic comparison
unless a further structural normal form is prescribed.

Use established engine comparison for that distinct question. PROJ's
[comparison criteria](https://proj.org/en/stable/development/reference/cpp/util.html)
are prior art: equivalence need not require identical names and identifiers.
Report the comparison criterion, retain coordinate-axis/unit interpretation,
and do not use the criterion that disregards geographic axis order as an
unqualified placement equality test. An engine's tolerance-based comparison
does not certify lossless WKT normalization or authorize dropping an operation.
If equivalence cannot be established, report it as unestablished rather than
claiming that a text difference proves different CRS meaning.

Even identical WKT does not authorize omitting required placement, project
adjustment, resource-dependent processing or any future epoch-dependent work.

A conforming authored `crs:wkt` token must be a fixed point of this profile:
normalizing it produces the same token. Validation checks both grammar validity
and that equality. Importers may normalize valid external WKT before conforming
authoring; resolution does not rewrite source layers. A simplified WKT export,
database replacement or visualization-axis rewrite is not this normalizer.

CRS-only authority does not authorize silently discarding an authored conversion
or transformation embedded in an otherwise valid WKT form. The site-grid
conversion is part of its CRS meaning. A form whose interpretation cannot be
honored in the supported profile must be reported as unsupported, rather than
replaced with an embedded base CRS. Coordinate-epoch wrappers remain outside
the initial profile.

An engine writer may be used only if it satisfies the prescribed preservation
and output rules. Its output must not be assumed lossless merely because it is
valid WKT or the parsed objects compare equivalent. Numeric values and metadata
must survive independently of tolerance-based CRS comparison.
