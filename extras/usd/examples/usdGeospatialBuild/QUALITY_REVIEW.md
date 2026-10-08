# Proposal quality review

The run evaluates the full local model/runtime follow-up at bbe3e488d5267227a994992a837a637f0cf98dee, source SHA-256
28768109389139a56d5c8e5f473446bfa46dd1ab46a48924165b97fb92cb7ae9. The reduced requirements branch is intentionally not an agent-ready
implementation contract. All 31 requirement identifiers are retained.

Feedback agrees on geographic inputs, input-only placement with no scale
property, anchor project adjustments versus descendant model offsets, WKT site
calibration, and conservative dependency coverage. Agreement on those outcomes
does not approve every detailed carrier or evaluation convention.

The full candidate defines seven geospatial input fields: crs:wkt, crs:position,
crs:orientation and data:asset, data:format, data:field, data:coordinateDomain.
There is no epoch or computed-result property. The bake origin uses ordinary
USD double-precision translate. Its prim/op names are adapter choices.

The revised contract clarifies array dimension association and rejects invalid
descendant placement. It requires an ordinary USD bake for unaware readers,
with coordinate context, origin, precision and stated space/time coverage.
Heading matching checks authority freshness; it is not a completeness proof.
The preimplementation review compares outcomes, necessary representation,
evaluation order and observable failures before any adapter change.

Pending adoption: stored orientation and interpolation; detailed chart/reset/
instance rules; external-data carrier profiles; geographic scene chart; Profiles
identity/maintenance; WKT normal form; bake origin/coverage convention.

Postimplementation review must independently retry all seven prior defect
counterexamples, inventory the whole export, compare both placement readers,
and retain failed diagnostics. Normals sampling is a known adapter concern,
not permission to weaken the proposal. More general primvar/material baking
and continuous nonlinear certificates remain verification limits.
