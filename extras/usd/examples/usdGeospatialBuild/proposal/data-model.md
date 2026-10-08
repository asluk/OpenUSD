# Derived excerpt: no additional authority

Source SHA-256: 28768109389139a56d5c8e5f473446bfa46dd1ab46a48924165b97fb92cb7ae9

### Schema design

Three schemas are proposed:

| Schema | Type | Purpose |
|--------|------|---------|
| `GeospatialCRS` | Typed (IsA) | Defines a CRS as a first-class USD prim |
| `GeospatialCRSBindingAPI` | Applied (HasA) | Associates a CRS definition with model or external-data content |
| `GeospatialDataSource` | Typed, Xformable | Identifies an external absolute measurement domain |

This approach separates the CRS *definition*
from the CRS *usage*,
allowing a single CRS definition to be shared
across many prims and scenes via USD references.

### CRS library pattern

CRS definitions are intended to live in shared **library layers**
(e.g., `crs_library.usda`) that can be referenced by any scene:

```
crs_library.usda
├── /CRS/WGS84_UTM11N       (GeospatialCRS)
├── /CRS/NAD83_UTM11N        (GeospatialCRS)
├── /CRS/NAD83_CA_Zone5      (GeospatialCRS)
└── /CRS/WGS84_Geographic3D  (GeospatialCRS)
```

This pattern is analogous to shared material libraries in M&E workflows.
Authoring tools can ship standard CRS libraries,
and users can create custom ones for local/site-specific CRS definitions.

### CRS binding and inheritance

The `GeospatialCRSBindingAPI` is applied to a `UsdGeomXformable` prim and
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
that has one — analogous to `UsdShadeMaterialBindingAPI` resolution.

A child prim may override its parent's CRS
by applying its own `GeospatialCRSBindingAPI` with a different CRS reference.
This is how multi-CRS scenes are composed
(e.g., one subtree in UTM zone 11N, another in UTM zone 18N).

For model placement, a direct binding establishes an anchor, and an inherited
binding supplies coordinate context for ordinary offsets below it until the
next direct binding, as recorded in the decision on question 5. The authored position and geodetic attitude are defined in the placement table. These are
separate CRS placement attributes, not ordinary translate xformOps. A binding
does not prescribe an authoring helper that rewrites the ordinary transform stack.

The external measurement type identifies absolute coordinate domains; see
[external association](#external-measurement-association).

### Precision handling

USD mesh geometry uses `point3f[]` (float32),
which provides ~7 decimal digits of precision.
A UTM easting of 481,948.63 requires 8+ significant digits,
so storing geospatial coordinates directly in `point3f` causes visible artifacts.

The solution is a two-tier approach:

| Tier | Data | Type | Precision |
|------|------|------|-----------|
| **CRS placement** | Geospatial position | Proposed `double3 crs:position`, separate from xformOps | Precision sufficient for the stated extent and tolerance |
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

**Proposed definitions for questions 2 and 6.** These properties contain inputs
only. Resolved positions, orientation, convergence, scale, distortion and bounds
are query results. They are not additional properties of the source schema.

#### Authored properties

`GeospatialCRSBindingAPI` on a directly bound model anchor defines:

| Property | USD type | Variability | Fallback | Meaning |
|---|---|---|---|---|
| `crs:position` | `double3` | varying | None | Absolute position of the model-placement origin, in the source WKT's units and height reference. |
| `crs:orientation` | `quatd` | varying | Identity | Geospatial model attitude: a right-handed unit rotation of ordered model east/north/up axes into geodetic east/north/up at that position. |

The quaternion encodes physical attitude, not grid convergence. Its value need
not change when an author re-expresses a placement position in another CRS of
the same physical reference frame. Correcting the WKT while keeping the numeric
position is a different authoring action and may move the placement. Neither
action is a write performed by resolution. A datum change must preserve or
explicitly revise the attitude's physical meaning; identical numbers alone do
not assert that distinct datum normals coincide.

No `crs:scale` is defined. Projection, calibration, elevation and unit factors
are derived from the authoritative WKT and position, as part of the full point
map. A scalar horizontal factor need not describe an arbitrary CRS conversion.
Intentional object scaling, reflection and pivots use ordinary USD xformOps.

A model position requires three finite components and a complete 3D CRS.
Missing or blocked position is an error. An unauthored orientation uses its
identity fallback; an explicitly blocked orientation is unavailable. Orientation
must be finite and unit length. These properties are invalid on measurement
carriers and on inherited-only model descendants: another absolute placement
requires another direct model binding. Validation must report an authored or
blocked placement field in either invalid role; resolution must reject that
invalid placement rather than silently omit the field and return success.
CRS library prims require neither field.

#### Position components

| Supported coordinate system | Semantic tuple |
|---|---|
| Projected/derived Cartesian horizontal plus declared vertical | easting, northing, up |
| Geographic 3D | longitude, latitude, height |
| Geocentric Cartesian | geocentric X, Y, Z |

Use the WKT unit for each component and its declared vertical reference.
Tuple order is independent of WKT storage order and stage `upAxis`; adapt to
the declared order at the engine boundary and reverse that adaptation on return.
The initial component profile covers east/north/up axes and geocentric X/Y/Z.
South-oriented axes are a known extension for a later component profile,
not a forgotten CRS family. Other directions and coordinate-system types are
unsupported by the initial profile and fail visibly rather than being guessed
or changed by WKT string normalization. A 2D CRS does not acquire height merely by adding a number.
Unrelated engineering coordinates cannot establish an Earth location.

#### Geospatial model attitude and stage axes

Use the source datum's ellipsoid-normal east/north/up (ENU) at the placement
position, including for projected and geocentric source CRSs. Establish that
position in the datum's 3D geographic CRS first; a required vertical conversion
must succeed. Deflection of the vertical is outside this ellipsoid-normal model.
The existing [geocentric/topocentric construction](https://proj.org/en/stable/operations/conversions/topocentric.html)
defines its origin and basis. At a geographic pole the recorded longitude
selects the reference meridian for the ENU basis. An unavailable geodetic
position or normal is an error, not a substitute basis.

Map a conformed stage vector to ordered model ENU as follows, multiplying by
`metersPerUnit` to obtain metres:

| Stage up axis | `(E,N,U)` from stage `(x,y,z)` |
|---|---|
| Z-up | `(x,y,z)` |
| Y-up | `(x,-z,y)` |

Both mappings are right-handed. Rotate this metric vector by the authored
quaternion, then embed it in the source datum's geocentric coordinates using
the ENU origin/basis. This defines the model's finite point map, not just an
origin or derivative. Convert those points through the source CRS as needed;
the WKT's projection, calibration and vertical conversions are retained.
Model distances are physical local lengths in scene units, not angular
increments or an assumed metre of projected grid. Absolute survey/grid samples
use the measurement role below instead of this local-model interpretation.

Heading/pitch/roll are a human-readable presentation of the quaternion, not
three additional authored authorities. For the proposed presentation, model
forward is ordered +N. Heading is clockwise from true north. Intrinsic heading,
pitch and roll correspond, in Core row-vector form, to
`R_N(roll) * R_E(pitch) * R_U(-heading)` with angles in degrees. A pure positive
pitch raises forward; positive roll follows the right-hand rule about forward.
The quaternion and its source-space slerp avoid an extra Euler interpolation
contract. The common matrix convention is the one in USD Core.

### External measurement association

**Proposed carrier for question 11.** Add a concrete typed
`GeospatialDataSource` derived from `UsdGeomXformable`, with a direct
`GeospatialCRSBindingAPI`. Its type identifies absolute external coordinates;
it is not a model anchor and has no `crs:position` or `crs:orientation`.

| Property | USD type | Variability | Fallback | Meaning |
|---|---|---|---|---|
| `data:asset` | `asset` | uniform | None | External dataset, resolved by the ordinary asset resolver relative to its authoring layer. |
| `data:format` | `token` | uniform | None | Association profile: `CF`, `GeoTIFF` or `GeoJSON`. |
| `data:field` | `string` | uniform | None | Selected measurement variable, raster band or feature property. |
| `data:coordinateDomain` | `string` | uniform | None | Selected format-defined coordinate domain. |

These are association facts, not duplicate CRS metadata or computed coordinates.
All are required; an empty field is permitted only for GeoJSON geometry-only
extraction. Blocked, missing or ambiguous associations fail. Several domains in
one container use separately bound carriers. Samples retain their original
indices, values, masks, coordinate associations and observation/forecast times.
Resolution performs no resampling, measurement interpolation or source writes.

For [CF 1.12](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.12/cf-conventions.html),
the field is the exact variable name and the domain the exact `grid_mapping`
variable name. Its associated coordinates, including expanded multiple-mapping
syntax, select the domain; dimension coordinates and auxiliary coordinates must
cover the selected variable's sample domain. Coordinate roles and units come
from CF metadata, not names or magnitudes. CF/WKT declarations must be mutually
consistent. The selected measurement variable's declared dimension names and
order identify each sample; every associated coordinate variable supplies its
own dimension declarations. Align coordinates to measurements by those named
dimensions, including declared permutations, before presenting tuples. Do not
associate independently flattened arrays by storage index. Missing or ambiguous
dimension associations fail. The native declarations supply this information;
no additional USD dimension-order property is introduced. Pressure or another
non-height vertical coordinate is not a height.

For [GeoTIFF 1.1](https://docs.ogc.org/is/19-008r4/19-008r4.html), the field is a
one-based band number and the domain a zero-based IFD number, both decimal
strings without padding. Raster-to-model mapping and PixelIsArea/PixelIsPoint
semantics determine sample locations. For [RFC 7946 GeoJSON](https://www.rfc-editor.org/rfc/rfc7946),
the domain is `geometry` and the field a feature-property name or the empty
string. Retain feature/geometry indices and RFC coordinate/height semantics;
legacy GeoJSON with another CRS is unsupported by this association profile.

The composed WKT is the sole authored CRS authority. An embedded format
definition must be semantically equivalent after its format-defined axis/unit
mapping, with a compatible vertical reference; otherwise fail. Text inequality
alone is not a conflict. No adapter may quietly override either declaration.

Dimensionality is retained. A 2D domain supports 2D coordinate queries and planar
adjustments in a Cartesian working CRS; it supplies no height or 3D frame.
A 3D request, non-planar adjustment or geographic working-frame adjustment that
requires an unavailable height fails. This is a known dimensional requirement,
not permission to invent zero height. Observation time is not coordinate epoch.

Ordinary transforms on the carrier adjust converted absolute sample locations
in the fixed working context defined below. The original dataset and its CRS
remain unchanged. Optional visualization and analytical queries consume these
same adjusted locations; adding a model anchor again would double-place them.

### Dependency declaration with Profiles

**Proposed integration for question 12.** Use the existing
[Profiles capability-usage carrier](https://openusd.org/release/user_guides/schemas/UsdProfiles/overview.html).
Propose the capability identity `usd.geospatial.crsResolution`, dependent on
`usd`; this spelling is for registry review, not a claim of existing registration.
Binding and measurement schemas imply that identity in schema plugin metadata.
A bare CRS library definition does not imply placed-content dependency.

A publishable scene's composed `defaultPrim` carries `ClaimsAPI` and
`customData.profilesInfo.capabilityUsages["usd.geospatial.crsResolution"] = "hard"`
if any retained content requires CRS resolution. The summary covers the entire
published composition, including content outside that subtree. Referenced
assemblies expose the same summary on their interface prim outside payloads.
The consumer reads this authored summary without traversal or loading payloads.
Capability usages are publisher claims; schema implications or runtime
discovery alone do not establish complete assembly coverage.

Writers maintain the conservative union when assembling, editing references,
selecting variants and exporting. An unavailable dependency summary is unknown
and retains the hard claim. A publisher may inspect/load content to discharge
uncertainty, but absence of a claim or an unloaded payload is not proof of no
dependency. Core composition still applies; validation reports a stronger
opinion that wrongly drops or weakens required coverage. Resolution never repairs
the authored claim. Export can remove it only after every retained use has
been baked into ordinary Cartesian data; absolute measurement domains retain it.

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
