# Derived excerpt — no additional authority

Source SHA-256: 2120953af221f83816486afbe88a06768e206d23cb570b5e39a193f254ba7a11

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

## Runtime coordinate transformation

The functional requirements and recorded decisions specify observable behavior,
including resolved coordinate queries and scene placement. They do not require
a particular library, callable API or rendering architecture.

A consumer-selected output CRS governs the requested result. When none is
selected, the existing scene-default pattern uses the CRS bound to the composed
`defaultPrim`, as described under question 8. Output selection does not replace
source CRS facts or reinterpret ordinary project adjustment numbers in different axes.
If no output is requested and the composed `defaultPrim` supplies no available
CRS binding, the output context is unspecified and the resolve request fails;
an engine must not invent a default geographic or projected CRS.

Rendering, bounds, instances, physics and non-visual queries use the same
resolution under requirement 17. Coordinate and relative-placement queries
follow requirement 18. Geographic coordinate queries are already supported;
geographic scene geometry, frames and bounds remain question 9.
Authored and returned CRS coordinate tuples use the semantic component order
in the position table. Axis-order adaptation at an engine boundary is reversed
before returning a query result; an engine's native array order does not become
an undocumented second convention. This does not relabel ordinary scene axes.

### Source placement evaluation and transform order

Read the three placement fields from composed values. For sampled fields, use
Core value resolution in the source representation: `double3` interpolation for
position/scale and quaternion slerp for orientation when linear interpolation is
selected; held interpolation remains held. Interpolate before CRS conversion,
as requirement 20 already specifies. Do not invent longitude unwrapping or a
motion model. Animation time is not a coordinate epoch.

Resolve the complete position, orientation and scale into the requested output
context, including the change of local axes and distance scale. Converting only
the position and retaining the original orientation and scale is insufficient.
The three source fields do not require every resolved frame to be decomposable
into a quaternion and diagonal scale. A conversion can introduce shear or
nonlinear distortion; neither may be discarded merely to fit those source
field types. A local affine result is an approximation subject to the stated
extent and error contract, not a new authored source placement.
Only after that CRS computation apply ordinary USD transforms, retaining their
authored order, pivots and ordinary reset semantics. A direct binding excludes
ancestor ordinary transforms at the independent absolute placement boundary;
resolution does not author a reset or modify the source xformOps.

Changing the output CRS recomputes the result without replacing these source
placement values. Applying a requested CRS conversion is separate from applying
an intentional project adjustment. The local candidate working-frame contract specifies the ordinary-adjustment
context for review, including output changes and descendant resets.
The proposed extent and result-comparison rules below address question 13;
the candidate working-frame contract supplies questions 3 and 6 for review.

### Observable outcomes and failures

Resolution leaves source layers unchanged. Unsupported requests, broken
bindings and failed or incomplete operations fail visibly. Operation reporting
must identify what was computed and distinguish engine estimates from the
placement/error guarantee required over the stated extent.

Explicit export is a separate act: it records the output CRS and time-sampling
meaning, preserves dataset values and associations, and can be resolved by a
fresh consumer without applying placement twice. The proposed sampling rules
are below; the candidate external association supplies question 11 for review.

These obligations need a complete data model and normative runtime specification
before independent implementation can claim proposal conformance. A prototype's
choice of a projection engine or affine approximation does not fill that gap.

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
points do not establish a bound over an entire extent. An implementation may
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
call. It does not establish a geographic scene frame under question 9.
An acceptance distance is supplied by the request or documented comparison
case, not guessed after seeing the results or stored in an undocumented scene
attribute.

### Explicit export and sampling

**Proposed clarification of question 14 using existing USD fields.** A resolved
export is a new authored dataset in its recorded output CRS. It retains the
ordinary interpretation of its geometry, coordinates and measurements. Every
baked placement effect is represented once: an effect included in exported
coordinate or geometry values cannot also remain as an unapplied placement or
ordinary transform that a fresh reader will apply again. This changes the
exported copy, not the source stage, and requires no private "already resolved"
flag. Output bindings, coordinate associations and the dependency summary must
describe what the exported copy actually requires.

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

