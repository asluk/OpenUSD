# Derived excerpt — no additional authority

Source SHA-256: 2120953af221f83816486afbe88a06768e206d23cb570b5e39a193f254ba7a11

### Schema design

The local candidate introduces three schemas for review:

| Schema | Type | Purpose |
|--------|------|---------|
| `GeospatialCRS` | Typed (IsA) | Defines a CRS as a first-class USD prim |
| `GeospatialCRSBindingAPI` | Applied (HasA) | Binds a CRS to a model anchor or the proposed external measurement association |
| `GeospatialDataSource` | Typed (IsA), non-Xformable | Identifies an external dataset, selected field and coordinate domain |

This separates the CRS *definition*
from the CRS *usage*,
allowing a single CRS definition to be shared
across many prims and scenes via USD references.

### CRS library pattern

CRS definitions are intended to live in shared **library layers**
(e.g., `crs_library.usda`) that can be referenced by any scene:

```
crs_library.usda
â”œâ”€â”€ /CRS/WGS84_UTM11N       (GeospatialCRS)
â”œâ”€â”€ /CRS/NAD83_UTM11N        (GeospatialCRS)
â”œâ”€â”€ /CRS/NAD83_CA_Zone5      (GeospatialCRS)
â””â”€â”€ /CRS/WGS84_Geographic3D  (GeospatialCRS)
```

This pattern is analogous to shared material libraries in M&E workflows.
Authoring tools can ship standard CRS libraries,
and users can create custom ones for local/site-specific CRS definitions.

### CRS binding and inheritance

The `GeospatialCRSBindingAPI` is applied to a `UsdGeomXformable` model prim
(or the proposed non-Xformable `GeospatialDataSource` for measurements) and
associates it with a CRS definition through a USD reference to a `GeospatialCRS`
prim, either in the same stage or in an external library layer. This is the
reference-based binding data representation described by this proposal;
it does not prescribe a callable binding interface or transform-stack edits.

A **direct binding** means that the composed prim itself has
`GeospatialCRSBindingAPI` applied. Its CRS definition is the associated composed
`crs:wkt` value; directness does not depend on which source layer authored a
reference arc or on whether that definition is valid.
Equivalent composed prim data establishes the same binding whether supplied
by a reference, an inherit or another Core composition mechanism. The reference
is the sharing mechanism, not a separate runtime coordinate-role marker.
A directly applied binding with an unavailable or invalid CRS definition is
an error, not an instruction to fall back to an ancestor's CRS.
Another direct model binding establishes a new anchor even when its CRS is
the same as its parent's; CRS identity does not make an absolute position an
ordinary relative offset.

CRS bindings inherit down the prim hierarchy.
A prim without a direct CRS binding
resolves its CRS by walking up to the nearest ancestor
that has one â€” analogous to `UsdShadeMaterialBindingAPI` resolution.

A child prim may override its parent's CRS
by applying its own `GeospatialCRSBindingAPI` with a different CRS reference.
This is how multi-CRS scenes are composed
(e.g., one subtree in UTM zone 11N, another in UTM zone 18N).

For model placement, a direct binding establishes an anchor, and an inherited
binding supplies coordinate context for ordinary offsets below it until the
next direct binding, as recorded in the decision on question 5. The candidate position,
orientation and scale fields at that anchor are detailed below for review. These are
separate CRS placement attributes, not ordinary translate xformOps. A binding
does not prescribe an authoring helper that rewrites the ordinary transform stack.

The candidate external measurement association below supplies non-visual
dataset roles; model binding alone does not identify source coordinate properties.

### Precision handling

USD mesh geometry uses `point3f[]` (float32),
which provides ~7 decimal digits of precision.
A UTM easting of 481,948.63 requires 8+ significant digits,
so storing geospatial coordinates directly in `point3f` causes visible artifacts.

The solution is a two-tier approach:

| Tier | Data | Type | Precision |
|------|------|------|-----------|
| **CRS placement** | Geospatial position, orientation and scale | Proposed `double3 crs:position`, `quatd crs:orientation` and `double3 crs:scale`, separate from xformOps | Precision sufficient for the stated extent and tolerance |
| **Detail** | Mesh vertices | `point3f[] points` | float32 (~7 digits) |

Large CRS coordinates are separated from ordinary local geometry and its
transform stack. The permitted local extent follows the required precision
and approximation contract in question 13; this does not impose a universal
1 km limit or change existing point storage types.

## Detailed design

### GeospatialCRS typed schema

A concrete typed schema that defines a CRS as a first-class USD prim.

**Prim type name:** `CoordinateReferenceSystem`

**Attributes:**

| Attribute | Type | Variability | Description |
|-----------|------|-------------|-------------|
| `crs:wkt` | `token` | Uniform | OGC WKT 2 string (ISO 19162:2019) defining the CRS |

The `crs:wkt` attribute is `uniform` because a CRS definition
does not vary over time or across a mesh.
It is a `token` (not `string`) to enable efficient caching and comparison.

**USDA syntax (horizontal-component illustration):**

This example illustrates the typed CRS property and a 2D horizontal definition;
it does not provide a complete 3D placement binding. WKT examples in this
document are expanded for readability. Under the proposed normalization
profile, their text must be normalized before it is authored as a conforming
`crs:wkt` token; the displayed indentation is not itself conforming token text.

```usda
def CoordinateReferenceSystem "WGS84_UTM11N" (
    doc = "WGS 84 / UTM zone 11N (EPSG:32611)"
)
{
    uniform token crs:wkt = """PROJCRS["WGS 84 / UTM zone 11N",
        BASEGEOGCRS["WGS 84",
            DATUM["World Geodetic System 1984",
                ELLIPSOID["WGS 84",6378137,298.257223563,
                    LENGTHUNIT["metre",1.0]]],
            PRIMEMERIDIAN["Greenwich",0,
                ANGLEUNIT["degree",0.0174532925199433]],
            ID["EPSG",4326]],
        CONVERSION["UTM zone 11N",
            METHOD["Transverse Mercator",
                ID["EPSG",9807]],
            PARAMETER["Latitude of natural origin",0,
                ANGLEUNIT["degree",0.0174532925199433],
                ID["EPSG",8801]],
            PARAMETER["Longitude of natural origin",-117,
                ANGLEUNIT["degree",0.0174532925199433],
                ID["EPSG",8802]],
            PARAMETER["Scale factor at natural origin",0.9996,
                SCALEUNIT["unity",1.0],
                ID["EPSG",8805]],
            PARAMETER["False easting",500000,
                LENGTHUNIT["metre",1.0],
                ID["EPSG",8806]],
            PARAMETER["False northing",0,
                LENGTHUNIT["metre",1.0],
                ID["EPSG",8807]]],
        CS[Cartesian,2],
            AXIS["(E)",east,ORDER[1],
                LENGTHUNIT["metre",1.0]],
            AXIS["(N)",north,ORDER[2],
                LENGTHUNIT["metre",1.0]],
        ID["EPSG",32611]]"""
}
```

### CRS association and model placement

**Proposed detailed definitions, under review in questions 2 and 6.** Friday's
direction of new placement attributes and ordinary transforms afterward is
already decided. The following names, types, fallbacks and basis conventions
are concrete proposals to make that direction derivable. The working-frame
contract completes their stage-axis mapping and point evaluation.

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
requirements 9â€“12 and 20. They do not duplicate axes, units, datum, projection
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
  eastâ€“northâ€“up tangent basis at that position. Up is the ellipsoid normal.
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

**Prior missing frame definition, addressed by the local candidate below:** the mapping from a conformed
model's stage axes into this ordered source basis, and from a resolved basis
back to stage axes, is specified in the candidate working-frame contract below. In particular, an identity
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
[OGC 18-010r11 / ISO 19162, clauses 6â€“7 and Annex B](https://docs.ogc.org/is/18-010r11/18-010r11.pdf).
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

### Candidate working-frame and point-evaluation contract

**Local candidate for questions 3 and 6, not recorded group agreement.** These
definitions make the October 5 emailed leans testable. They retain source CRS
authority, the independent binding boundary and the October 2 placement order.

The working CRS for a directly bound model is the nearest strictly enclosing
direct binding's composed CRS, or the model's source CRS if none exists. An
invalid enclosing binding is an error, not a reason to try another ancestor.
It supplies adjustment axes and units, not an additional model position or
ancestor xform stack. Another requested output does not change this selection.

For a Cartesian working CRS, the adjustment chart is its absolute coordinates,
with each length component converted to metres and then to stage units and
axes. An ordinary rotation or scale without an authored pivot therefore acts
about that chart's zero, just as an ordinary USD transform does. A writer who
intends a site pivot must author it; a reader must not invent one. For a
geographic working CRS, use the ellipsoidal ENU chart about the enclosing
anchor's resolved source position, or the model's own source position in the
fallback case. The enclosing anchor's position supplies only this chart origin;
its orientation, scale and ordinary transforms are not inherited as an extra
absolute placement. A required unavailable origin or vertical conversion fails.
ENU orientation at a pole is unsupported; geographic coordinate queries at a
pole remain valid. These chart-origin and pivot choices require group review.

Stage vectors map to ordered metric placement-basis vectors as follows:

| Stage | Stage vector `(x,y,z)` in east/north/up or Cartesian X/Y/Z order |
|---|---|
| Z-up | `(x,y,z)` |
| Y-up | `(x,-z,y)` |

Multiply the entire evaluated stage vector by `metersPerUnit` when entering
the metric basis; divide by it and apply the inverse mapping when returning to
stage axes. In geocentric placement the ordered basis is X/Y/Z, not local ENU.
Use the same right-handed mapping for scale axes and quaternion interpretation:
stage-to-basis first, authored dimensionless scale second, authored orientation
third. This mapping interprets conformed content; it does not correct assets.

The following defines point evaluation without choosing a callable interface.
Let `F` map an anchor-local stage vector into its source CRS: map stage axes and
units as above, apply `S * R`, then add Cartesian offsets in the declared length
units, or use the established geographic-to-geocentric/topocentric construction
for geographic offsets. Let `Tsw` be the selected source-to-working operation,
`Cw` the working-CRS-to-stage adjustment chart, `A` the anchor's complete ordinary
local USD transform, and `Twq` the working-to-requested-output operation.
For an anchor-local point `x`, its resolved position is

`Twq(Cw^-1(A(Cw(Tsw(F(x))))))`.

This is transport of a fixed authored adjustment, not reuse of `A` in the
requested output's axes. A consumer can compute an equivalent transported
adjustment after source-to-output conversion; its computational path is free.
The CRS placement is evaluated before the anchor's ordinary adjustment. If
`A` is identity, working-context selection does not require an unnecessary
intermediate geodetic operation, chart construction or pole orientation.

For descendants, first resolve the anchor's placement map, then attach their
ordinary local transform stack in the existing USD local-frame hierarchy. In
point evaluation this supplies `x = D(vertex)`, where `D` contains the ordered
descendant matrices below the anchor. This preserves local model axes; it does
not reinterpret a child offset as an absolute coordinate or site-grid adjustment.
An ordinary descendant reset stops the ordinary ancestor stack, including `A`,
while retaining the inherited CRS placement boundary. A reset does not remove
the intrinsic source placement or turn vertices into absolute coordinates. A
new direct binding starts a new independent anchor, excluding every ordinary
ancestor transform, while retaining the enclosing CRS as working context.
These distinctions between anchor adjustments and descendant offsets are
explicit candidate semantics; the broad phrase "transforms afterward" alone
did not specify them. Ordinary pivots, inverse ops, scales and operation order
are evaluated by UsdGeom, rather than interpreted from individual raw translates.

Native USD instance proxies obey the same composed binding and ordinary
transform rules as equivalent non-instanced composed prim data. For a point
instancer inheriting its model anchor, its ordinary per-instance transforms and
prototype-local transforms supply descendant-local offsets to the same point
map; prototype geometry is evaluated for every retained instance, preserving
prototype indices and instance IDs. The uninstanced prototype is not an extra
placed copy. Materializing instances on explicit export is permitted if every
retained instance has the same resolved geometry and sample association.
This initial candidate does not define independently CRS-bound point-instancer
prototypes: such a request fails visibly, rather than guessing whether instance
transforms move an absolute prototype placement. That specialized combination
remains a model-contract gap to review; ordinary native instances and locally
instanced model geometry remain in scope.

An exact relative-position query evaluates the first placement map and inverts
the second map in reverse operation order. It returns a local offset in the
second model's stage axes and units, not a subtraction of unrelated native CRS
tuples. If any required inverse is singular or unavailable, the query fails.

Coordinate queries evaluate this point map. A local frame is its derivative at
the requested origin, reported with its chart and units; it is not a certificate
of accuracy over finite geometry. Singular scale permits forward points but
precludes an inverse frame. Exact per-vertex evaluation may be used without
claiming an affine extent certificate. Bounds of the resolved polygonal mesh
cover its resulting vertices and straight faces; they are not a guaranteed
bound on the nonlinear image of the original continuous face or an arbitrary
source bounding box. Such stronger claims require the stated extent/error
contract or a visible unsupported result. Geographic scene frames and bounds
remain question 9; geographic coordinate queries remain initial scope.

### Candidate external measurement association

**Local candidate for question 11, not recorded group agreement.** Introduce a
non-Xformable concrete typed prim `GeospatialDataSource`, with the existing
`GeospatialCRSBindingAPI` applicable to it as well as model anchors. Its composed
binding governs the selected absolute coordinate domain. This prim has no model
placement: `crs:position`, orientation, scale and xformOps are invalid on it.
The schema contains only the missing external association facts:

| Property | Type | Variability | Fallback | Meaning |
|---|---|---|---|---|
| `data:asset` | `asset` | uniform | None | External dataset, resolved by the ordinary USD asset resolver relative to its authoring layer. |
| `data:format` | `token` | uniform | None | Format association profile, initially `CF`, `GeoTIFF` or `GeoJSON`. |
| `data:field` | `string` | uniform | None | Selected measurement variable, raster band or feature-property selection. |
| `data:coordinateDomain` | `string` | uniform | None | Format-defined coordinate domain selected below, not a CRS definition. |

The format token selects interpretation rules, not a plugin or storage mandate.
CF uses the exact data-variable name as field and the exact `grid_mapping`
variable name as domain; the mapping's declared coordinate associations select
the domain if multiple mappings occur. GeoTIFF uses a one-based band number and
zero-based IFD number as decimal strings, with the IFD's raster-to-model mapping
and PixelIsArea/PixelIsPoint semantics retained. GeoJSON uses a feature-property
name (or the empty string for geometry-only extraction) and `geometry` as domain;
its RFC 7946 longitude/latitude interpretation is checked against the binding.
An ambiguous selection, missing required association, unavailable asset or
unsupported format fails visibly. A sample keeps its original domain/index,
measurement, missing-value mask, coordinate and observation-time association.
The format's coordinate units are converted to the binding's declared units;
units may not be inferred from a variable name or numerical magnitude.

The composed WKT is authoritative. An embedded coordinate-system definition
must be semantically equivalent with compatible component roles, units and vertical
reference; conflicting definitions fail. Format-defined tuple order is adapted
to the declared WKT storage order before comparison and conversion; neither
text inequality nor a storage-order difference alone proves a semantic conflict. No override flag is introduced. WKT
text differences alone are not conflicts. CF attributes and WKT must themselves
be mutually consistent under CF 1.12. A format supplies no missing CRS fact by
guessing; unsupported vertical coordinates such as pressure are not heights.
Absolute samples do not receive a model anchor or parent xform adjustment again.
An intentionally project-adjusted dataset must instead be represented as local
model content under the model-placement contract; this candidate does not
invent an adjustment mode on absolute samples.

Two-dimensional domains remain two-dimensional. A 2D-to-2D query is supported;
a 3D request without a specified height reference and coordinate fails. A third
GeoJSON component alone does not establish an arbitrary legacy dataset's height
datum. This preserves larger-scale and non-visual cases without synthetic height.
Observation time is retained as dataset metadata; it is not a coordinate epoch.

These fields are justified by requirements 11 and 30's unambiguous coordinate
role and external sample associations. They duplicate no WKT axes, units, datum
or epoch. The pattern follows an external-asset plus field selector, as in
UsdVolFieldAsset, without reusing that schema's volume-specific semantics.
Native source formats remain the measurement carrier; this is not a general
USD measurement-storage schema. An explicit export may create a new external
dataset with output-coordinate metadata and the same association fields.

### Candidate Profiles dependency integration

**Local candidate for question 12, not recorded group agreement.** Propose the
registered capability identity `geospatial:crsResolution`. Bindings and external
data-source schemas imply this identity in schema plugin metadata. The usage
strength is the existing Profiles `hard` class because ignoring required CRS
resolution gives incorrect placement. A bare CRS library definition does not
require resolution of content merely because it stores WKT.

Publishable geospatial scenes have a composed `defaultPrim` carrying `ClaimsAPI`
and `customData.profilesInfo.capabilityUsages["geospatial:crsResolution"] = "hard"`
whenever any retained content requires resolution. This declaration is a summary
of the whole composed scene, including content outside that prim's subtree;
it is found through `defaultPrim` without traversal or payload loading. Referenced
assemblies publish the same summary on their interface prim outside payloads.
The capability spelling is proposed for registry review, not an existing
registered AOUSD capability.

The publisher must maintain that summary when assembling, changing references,
selecting variants or exporting. It unions conservative interface summaries of
all retained dependencies; an unavailable summary is unknown and retains a hard
claim, not proof of no dependency. The publisher may load and inspect content
to discharge that uncertainty, but a consumer need not. Unloaded payloads and
negative claims cannot erase a known positive dependency. Profiles' automatic
discovery over composed descendants alone does not meet this coverage rule.
Composition still follows Core; validation detects a stronger layer dropping or
weakening a required summary rather than silently repairing authored metadata.

An exported Cartesian scene with every placement baked into ordinary local
geometry plus double-precision ordinary transforms can remove the claim only
if no retained dataset or model still requires CRS interpretation. Retained
absolute measurement domains keep the claim. A conservative hard claim is
permitted after baking; an omitted claim is not proof of a standalone asset.
No custom layer dependency flag or private already-resolved marker is added.

The Profiles carrier is established prior art; whole-scene coverage, publication
maintenance and this proposed capability identity are the geospatial contract
being reviewed. No callable Profiles interface is proposed as a USD standard.

