# Derived excerpt: no additional authority

Source SHA-256: 28768109389139a56d5c8e5f473446bfa46dd1ab46a48924165b97fb92cb7ae9

## Runtime coordinate transformation

The functional requirements and recorded decisions specify observable behavior,
including resolved coordinate queries and scene placement. They do not require
a particular library, callable API or rendering architecture.

A consumer-selected output CRS governs the requested result. When none is
selected, the existing scene-default pattern uses the CRS bound to the composed
`defaultPrim`, as described under question 8. Output selection does not replace
source CRS facts or reinterpret ordinary project adjustment numbers in different axes.
For a standalone Cartesian export, the typed default CRS definition is the
default context under the explicit-export rule below. Otherwise, if no output
is requested and the composed `defaultPrim` supplies no available CRS binding,
the output context is unspecified and the resolve request fails;
an engine must not invent a default geographic or projected CRS.

Rendering, bounds, instances, physics and non-visual queries use the same
resolution under requirement 17. Coordinate and relative-placement queries
follow requirement 18. Geographic coordinate queries are already supported;
the proposed scene representation for geographic output is specified under
[question 9](#queries-scene-charts-and-instances).
Authored and returned CRS coordinate tuples use the semantic component order
in the position table. Axis-order adaptation at an engine boundary is reversed
before returning a query result; an engine's native array order does not become
an undocumented second convention. This does not relabel ordinary scene axes.

### Source placement evaluation and transform order

#### Placement-order illustration

**Informative.** The six views below explain the anchor example under [Evaluation](#evaluation).
They show contributions to one resolved result, not required intermediate prims
or a particular evaluator architecture. The source schema holds authoritative
position and model-attitude inputs; computed placement results are runtime data.

The source is a static RGF93 v2b realization. Both working and output contexts
are Lambert-93 in metres with ellipsoidal height, so this example needs no
working-to-output transport. Geometry is already conformed to stage metres and
Z-up; height, attitude and adjustments are illustrative. The quaternion encoding
remains proposed. This is not surveyed placement, an epoch or gravity-related
height conversion, or a finite-extent affine certificate.

Every panel uses the same camera and ground grid. Blue outlines show the
previous state; height guides, model-front markers and translation arrows make
each change visible.

##### 1. Local geometry

![Local Eiffel Tower geometry in an already-conformed metre and Z-up model frame](figures/math-order/01-local-model.png)

The 300-metre model starts in its local frame, without geographic placement.

##### 2. Geospatial model attitude

![The source model attitude turns the local Eiffel Tower model 30 degrees clockwise from true north](figures/math-order/02-authored-attitude.png)

The proposed authored `crs:orientation` represents a 30-degree clockwise heading
from true north, with zero pitch and roll, in local geodetic east/north/up.
Here model +Y is chosen as front, not prescribed as a general convention.
For this right-handed Z-up example, the attitude is a minus-30-degree turn about
local +Up. It is a placement input, distinct from the later ordinary USD rotation
about working-grid +Z. Heading/pitch/roll are an authoring presentation of the
model attitude; this illustration does not decide the stored encoding.

##### 3. CRS placement and resolution

![The bound CRS, authored position and model attitude resolve into Lambert-93, with computed coordinates and projection factors](figures/math-order/03-crs-resolved.png)

The bound `crs:wkt`, `crs:position` and model attitude resolve the model points
into Lambert-93. A change of coordinate representation alone does not move the
model physically. The displayed convergence and projection scale are local
diagnostic results, not authored source properties or a complete affine map.
View-origin subtraction changes only the display coordinates.

##### 4. Ordinary USD scale

![A previous-state outline and height guides show ordinary USD scale enlarging the Eiffel Tower from 300 to 345 metres around the explicitly authored base pivot](figures/math-order/03b-usd-scale.png)

`xformOp:scale:adjust = (1.15, 1.15, 1.15)` enlarges the model to 345 metres.
The explicitly authored ordinary pivot is chart zero, the resolved placement
origin in this example. The base stays fixed; the blue outline is the preceding
CRS-resolved state.

##### 5. Ordinary USD rotation

![After ordinary USD scale, a previous-state outline and plan-view front markers show a 20-degree counterclockwise turn around the explicitly authored base pivot](figures/math-order/04-usd-rotate-scale.png)

`xformOp:rotateZ:adjust = 20` turns the scaled model counterclockwise about
working-grid +Z. The base and scaled size stay fixed. The blue outline and
front markers distinguish this turn from the preceding model attitude.

##### 6. Ordinary USD translation

![The final ordinary USD translation moves the tower 120 metres east and 60 metres south, while its source geospatial properties remain unchanged](figures/math-order/05-usd-translate.png)

`xformOp:translate:adjust = (120, -60, 0)` moves the model 120 metres east and
60 metres south after scale and rotation. Rendering and non-visual coordinate
queries include that final adjustment; the source geospatial inputs stay
unchanged. The arrows illustrate components of one translation.

The example's stack below is listed in `xformOpOrder` order, from least local
to most local; a point encounters the operations in reverse order. It is the
anchor's post-placement adjustment in the origin-centred working chart. The
zero pivot is an ordinary authored input, not a maintained copy of the absolute
geospatial position. Equivalently, in row-vector absolute coordinates, a
resolved point `q` becomes `(q - P) * S * R + P + t`, where `P` is the placement
origin and `S`, `R` and `t` are the shown ordinary scale, rotation and translation.
Descendant, reset and independent-instance behavior is specified in Evaluation.

```usda
double3 xformOp:translate:adjust = (120, -60, 0)
double3 xformOp:translate:pivot = (0, 0, 0)
double xformOp:rotateZ:adjust = 20
double3 xformOp:scale:adjust = (1.15, 1.15, 1.15)
uniform token[] xformOpOrder = [
    "xformOp:translate:adjust",
    "xformOp:translate:pivot",
    "xformOp:rotateZ:adjust",
    "xformOp:scale:adjust",
    "!invert!xformOp:translate:pivot"
]
```

See [figure provenance and credits](figures/math-order/README.md) for the source
asset, inputs and reproduction record.

#### Evaluation

**Proposed complete evaluation contract for questions 3, 6, 9 and instances.**
Read composed placement values under Core resolution. Position interpolates in
its recorded CRS; quaternion orientation uses Core slerp when linear
interpolation is selected. Held remains held. Interpolate before conversion;
do not infer longitude unwrapping, a motion model or a coordinate epoch.

For a model, let `F(x)` be the intrinsic finite point map defined by the
placement position, stage-to-ENU mapping and geospatial attitude above. `x` is
the point in the prim's authored local stage coordinates, before ordinary
xformOps. Let `W` be the nearest strictly enclosing direct binding's CRS, or
the source CRS if none exists. An invalid controlling binding fails; it is not
skipped. A library reference alone is not another working-context declaration.
The requested output `Q` never changes `W`.

The model adjustment chart `C_W` has zero at the model-placement origin
converted to `W` before ordinary adjustments. For Cartesian `W`, subtract that
origin, convert each component's WKT length unit to metres, then use the inverse
stage-axis mapping and divide by `metersPerUnit`. For geographic `W`, use the
full geocentric-to-ENU chart at that converted origin, in stage axes and units.
Its inverse retains the vertical departure of curved geometry; it does not
flatten a surface. The placement origin is therefore the ordinary zero/pivot
unless an ordinary pivot is authored. There is no second CRS pivot attribute.

Let `A` be the anchor's own complete Core/UsdGeom ordinary transform product,
ordered as authored. The anchor's own stack is the post-placement adjustment in this chart.
Descendant stacks retain their ordinary model-local meaning: let `D` be their
Core product below the anchor, including writer-authored conformance. They
define the model-local point supplied to the intrinsic placement, `F(x * D)`.
Author feedback supports this distinction, which makes the broad
"transforms afterward" wording precise without changing an asset's ordinary
local-frame hierarchy. The complete chart and reset convention remains a
candidate; agreement on the distinction does not assert whole-contract adoption.
Interpreting raw child translations in working-grid axes would instead change
their meaning when the model's geospatial attitude changes. A descendant reset removes the
ordinary contributions above that reset, but retains inherited geospatial
placement; another direct model binding starts another absolute anchor and
excludes all ancestor ordinary transforms. A reset at the anchor does not
remove its own local stack. In row-vector form the resolved point is

`T_WQ(C_W^-1(C_W(T_SW(F(x * D))) * A))`.

Here `T_SW` converts source to working CRS and `T_WQ` working to output.
This formula specifies observable meaning, not a required engine path. An
equivalent transported computation may avoid an unnecessary intermediate
operation, especially when `A` is identity. It must preserve the same adjusted
physical position and report the actual operations it used. Descendant translations are model-local offsets and follow the model's
geospatial attitude. The anchor's ordinary translation is a working-chart
adjustment. A descendant reset terminates `D` at that reset and makes `A`
identity; it does not remove intrinsic placement. Reusing either stack's raw
numbers in arbitrary output axes describes a different scene. Ordinary pivots, inverse ops, signed scales
and reset markers follow UsdGeom. Finite singular transforms permit forward
points, but inverse/frame requests that need an inverse fail.

For an absolute measurement domain, replace `F(x)` with its native sample
coordinate and apply the carrier's own ordinary stack in `W`. A Cartesian
domain chart has the working CRS zero as origin, since the domain has no model
placement origin; use ordinary pivots to choose another adjustment origin.
A 3D geographic domain chart uses longitude/latitude/ellipsoidal height zero
of the working datum as its ENU origin. The required height conversion must
succeed. These chart origins are conventions, not inserted sample heights.
For a 2D Cartesian domain use its two horizontal length components and reject
out-of-plane coupling; no 3D position is created. Independent direct carrier
bindings exclude ancestor ordinary transforms just as independent model
bindings do. Its project adjustment is not a conversion of the stored dataset.

#### Queries, scene charts and instances

Coordinate queries return the requested CRS's semantic tuple and units.
A relative-position query returns both resolved origins in `Q` and their
component difference `from - to`, in `Q`'s declared units; it is not an inverse
of the second model's local frame. Geographic differences are angular/height
coordinate differences without implicit wrapping, not metric displacements.
Physical distance uses the separate comparison rule below. A relative-frame
query, when invertible, names its Cartesian chart and returns the full map or
local derivative in that chart, with its approximation domain explicitly stated.

For Cartesian output, scene geometry and bounds use that CRS's ordered length
components, a consumer-selected numeric output origin, and the stage-axis/unit
mapping. The default numeric output origin is zero. This origin is a runtime
representation parameter, not an edit to source placement.

**Proposed answer to question 9:** geographic output coordinates remain
geographic, while ordinary scene geometry, frames and bounds use the associated
geocentric Cartesian CRS of the same datum, ellipsoid and prime meridian, in
metres, with the same output-origin rule. Results identify both coordinate CRS
and scene chart. Angular tuples never become UsdGeom points or length matrices.
The associated geocentric representation preserves global curvature and adds
no source property. An explicit Cartesian export records its actual Cartesian
CRS. A consumer asking for an angular Euclidean frame receives an unsupported
request, rather than a fabricated length frame.

Native instance proxies evaluate as equivalent expanded composed prims.
Point-instancer instances use Core/UsdGeom positions, orientations, scales,
prototype indices, masks and time behavior. An unbound prototype uses the
instancer's inherited model placement; its ordinary prototype/instance product defines `D` in the instancer's local
model frame, while the instancer anchor's own stack defines `A`. A directly bound prototype instead keeps
its own absolute position and source CRS, using its nearest enclosing binding
as `W` (or its own source as fallback). Its ordinary prototype stack is followed
by the per-instance matrix, expressed in that same adjustment chart. The
instancer's anchor and ancestor xformOps do not add a second absolute placement.
Do not include the prototype's ordinary transform twice: evaluate its stack
once and use Core's instance matrix excluding that prototype transform. Bindings
inside a prototype follow the same independent-anchor rule. A resolved instance
identity includes instancer path, instance ID/index and full prototype-relative
prim path; names alone do not identify nested geometry uniquely.

Local derivatives and finite pointwise results need not be representable as a
quaternion and diagonal scale. Normal/tangent transport uses the derivative of
the complete map in the named Cartesian chart: tangent vectors use the forward
linear map, normals its inverse transpose and normalization. Singular normal
transport fails. Existing primvar interpolation, indexing, orientation and
face topology rules remain in force. A semantic point/vector/normal primvar
follows that role; arbitrary numeric triples do not silently acquire one.
Subdivision and curves require their consumed continuous domain to meet the
extent/error contract, rather than treating their controls as the whole surface.

### Observable outcomes and failures

Resolution leaves source layers unchanged. Unsupported requests, broken bindings
and failed or incomplete operations fail visibly. A batch may report individual
failures, but cannot return an unchanged failed coordinate as a successful
placement. Results identify coordinate CRS, scene chart where used, operation,
attributed accuracy and any spatial/temporal approximation claim. Unknown
accuracy is unknown, not zero.

Computed outputs are runtime data. A lightweight consumer can read an explicit
derived Cartesian export containing ordinary USD matrices/geometry, without
stored computed geospatial properties on the source. That export's once-only
placement and fresh-reader obligations are specified below.

### Extent and result comparison

**Proposed clarification of question 13.** These are observable result
obligations; they prescribe neither callable interfaces nor an engine's
approximation algorithm.

Operation-attributed accuracy, model-placement approximation and agreement
between implementations are reported separately. An unknown operation accuracy
is unknown, not zero. Requirement 28 does not require a full propagation of
geodetic uncertainty through every scene transform.

An approximation claim names its spatial extent, evaluated time or time range,
distance measure and bound. Its reference is pointwise evaluation of the same
source placement, coordinate operation and ordinary-transform chain, not just
conversion of the placement origin. The claim must cover the content actually
consumed, including transformed geometry and bounds. A few representative
points do not establish a bound over an entire extent. Finite sample/vertex
queries can report pointwise results without a continuous-domain claim. Bounds
on a resulting polygonal export cover its straight faces, not automatically
the nonlinear image of the original continuous faces. A continuous scene-bound
request must include those faces or the actual consumed subdivision/curve
domain. An implementation that cannot certify it reports that request as
unsupported; passing a sampled probe is not certification. An implementation may
refine an approximation or split the work; if it cannot establish the requested
bound for the requested extent, it reports that limitation instead of claiming
the bound. No universal tile size or private default tolerance follows from
this requirement.

Comparison cases fix the source and output definitions, sampled input values,
interpolation mode, ordinary adjustments, requested result and acceptance
distance before execution. They establish equivalent coordinate operations,
including the realized parameters and resource versions that affect results.
Different valid operations are reported as such, rather than classified as
floating-point disagreement. If equivalence cannot be established, comparability
is unestablished. Operation labels alone do not prove equivalence.

For Cartesian coordinate outputs, compare Euclidean distances after converting
each component's declared length unit to metres, and also report residual
components in the output's declared units and the coordinate magnitudes.
Mixing feet and metres in an unconverted norm is not a distance measure.

For geographic coordinate queries, propose reporting horizontal distance using
the existing [ellipsoidal inverse geodesic](https://proj.org/en/stable/geodesic.html)
on the output WKT's ellipsoid, height difference in metres in the same declared
vertical reference, and their Euclidean combination as the agreement distance.
Angular component residuals are reported separately; degrees and metres must
not be combined as Cartesian components. This is an explicit proposed comparison
convention, not an OGC-mandated error measure or a choice already agreed on the
call. Geographic scene results use the associated Cartesian chart specified above.
An acceptance distance is supplied by the request or documented comparison
case, not guessed after seeing the results or stored in an undocumented scene
attribute.

### Explicit export and sampling

**Proposed clarification of question 14 using existing USD fields.** A resolved
export is a new authored dataset in its recorded output CRS. Baking resolved
georeferencing into ordinary UsdGeom geometry and xformOps lets an unaware
consumer use the derived copy without geospatial computation, over its stated
spatial extent and time coverage. The export retains the ordinary interpretation
of its geometry, coordinates and measurements. Every baked placement effect is
represented once: an effect included in exported
coordinate or geometry values cannot also remain as an unapplied placement or
ordinary transform that a fresh reader will apply again. This changes the
exported copy, not the source stage, and requires no private "already resolved"
flag. Export retains unrelated authored USD properties and schema applications;
removing geospatial inputs after baking is not permission to remove other
semantics. Output bindings, coordinate associations and the dependency summary must
describe what the exported copy actually requires.

A standalone fully baked Cartesian geometry export uses a
`CoordinateReferenceSystem` prim as its `defaultPrim`, with the recorded output
`crs:wkt` and ordinary geometry/xforms beneath it. It carries no
`GeospatialCRSBindingAPI` or model-placement fields: its descendants are already
Cartesian scene content in that recorded context. Stage units/up-axis map those
ordinary coordinates to the WKT length components as specified above. A required
ordinary `Xform` beneath the context prim carries the explicitly recorded
origin as one double-precision translate xformOp, with no prescribed prim or
operation name.
Its value is that origin in the recorded Cartesian output context, mapped to
stage axes and stage units. Exported geometry and ordinary model transforms are
authored below it relative to that origin, so large absolute coordinates need
not enter float32 point arrays. The origin can be exporter-selected, but it must
be recorded and its selection must preserve the stated precision and coverage;
it is not inferred later or duplicated as a geospatial source property. The
ordinary origin translate is applied exactly once. A geographic coordinate
request uses the associated Cartesian scene chart for the baked geometry and
records that chart's CRS, never angular tuples in ordinary point arrays. The
definition records the coordinate system, not an object's placement. An ordinary
USD viewer can read the geometry and matrices; a geospatial reader can identify
the Cartesian context without a private flag and convert coordinates on request.
This explicit-export context is distinguished by its composed type, not a file
name or provenance layer. Referencing/assembling such a copy requires the writer
to retain its coordinate context or explicitly re-author it under the model or
measurement contract; an enclosing unrelated CRS must not silently reinterpret
its ordinary coordinate numbers.

For sampled output, the authored `timeSamples` keys record the actual exported
sample schedule and the export authors the stage's existing `timeCodesPerSecond`
to record its time-code scale explicitly. Each exported sample equals the
requested resolved source result at that time, subject to the stated result
bound; export is not required to reuse only the source sample times.
Observation dates and measurement values
retain their own associations and are not inferred from USD time codes.

A reader evaluates the exported authored samples under Core value resolution
in their recorded output CRS. This differs from interpolating the original
source samples before CRS conversion: the equatorial example in requirement
20 produces a surface midpoint from source longitude samples, but a chord
midpoint from two exported ECEF endpoints. An exporter claiming to preserve
the original trajectory between samples must provide sufficient samples to
meet a stated bound over that time range. Recording two sample times alone
does not establish that claim.

Core defines held and linear stage interpolation, with linear as the default,
but how a reader selects that stage setting is implementation-defined. This
proposal adds no authored interpolation-mode field. Sampling-policy provenance
or a requirement to force a reader's interpolation setting would be a separate
model decision; the proposed record here establishes the actual sample times
and time-code scale, not an unrecorded sample-generation history.
