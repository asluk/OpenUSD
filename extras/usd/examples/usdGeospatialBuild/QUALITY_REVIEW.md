# Proposal quality review

The run evaluates the full local model/runtime follow-up at 0e955c68c9b0f07b313c43c2cf291eead868c8af, source SHA-256
0ed1dcda854e43bb82b7e830ba4b2224cdb8da0741fa9d6cb4fe459d4266ace0. The reduced requirements branch is intentionally not an agent-ready
implementation contract. All 31 requirement identifiers are retained.

Feedback agrees on geographic inputs, input-only placement with no scale
property, anchor project adjustments versus descendant model offsets, WKT site
calibration, and conservative dependency coverage. Agreement on those outcomes
does not approve every detailed carrier or evaluation convention.

The full candidate defines seven geospatial input fields: crs:wkt, crs:position,
crs:orientation and data:asset, data:format, data:field, data:coordinateDomain.
There is no epoch or computed-result property. The bake origin uses ordinary
USD double-precision translate. Its prim/op names are adapter choices.

The preferred double3 orientation records inspectable heading/pitch/roll inputs.
Its units, north/up, rotation order, Core sample selection, shortest-arc pose
interpolation, defaults and failures are explicit before execution. The previous
quaternion alternative remains an alignment comparison, not source authority.

The revised contract clarifies array dimension association and rejects invalid
descendant placement. It requires an ordinary USD bake for unaware readers,
with coordinate context, origin, precision and stated space/time coverage.
Heading matching checks authority freshness; it is not a completeness proof.
The preimplementation review compares outcomes, necessary representation,
evaluation order and observable failures before any adapter change.

Pending adoption: preferred HPR source orientation and pose interpolation; detailed chart/reset/
instance rules; external-data carrier profiles; geographic scene chart; Profiles
identity/maintenance; WKT normal form; bake origin/coverage convention.

Postimplementation review must independently retry all seven prior defect
counterexamples, inventory the whole export, compare both placement readers,
and retain failed diagnostics. Normals sampling is a known adapter concern,
not permission to weaken the proposal. More general primvar/material baking
and continuous nonlinear certificates remain verification limits.
