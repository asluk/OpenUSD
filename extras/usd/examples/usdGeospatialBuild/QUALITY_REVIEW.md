# Local candidate readiness

Four missing contracts. Five former gaps now have proposed candidate answers. Adoption is separate from derivability.

Exact full candidate SHA-256: `a5444966c41e3a067d7c4db5b2e9a300a08b17fcce377bd6fb24727b390e6904`. Publication and group adoption are separate.

## G01: Legacy contradictions (closed)

The baseline specifies data and observable runtime behavior, retains reference-based binding and excludes ancestor transforms without source edits. Do not use old callable examples or prototype behavior as authority.

No remaining legacy contradiction in this candidate.

## G02: Exact CRS placement property contract (closed)

Names, types, variability, fallbacks, required position, quaternion semantics, scale order, signed/singular policy and source interpolation are proposed in the README. Adoption pending does not mean no definitions exist. Exact stage-to-placement basis conversion remains a genuine behavior gap; ground/grid scale ownership also needs geospatial review.

Finite values, mixed component units, no duplicate projection factor, and no assumption that source R/S fields constrain resolved frames to R/S only.

## G03: Physical coordinate context of project adjustments (open)

Post-CRS order is decided. The controlling composed frame, adjustment axes/units/pivot and preservation across output changes are not. The complete xform stack must supply the intended adjustment; raw numeric reuse in another CRS is insufficient.

A 90-degree oriented model distinguishes a model-X adjustment from a grid-easting adjustment. The text identifies this precise choice rather than reopening placement order.

## G04: Remaining component conventions and scene result domain (open)

Geographic longitude/latitude/height and geocentric XYZ have proposed conventions. Canonical tuple order does not specify a Y-up or Z-up scene basis. Geographic coordinate queries are settled functional scope; using angular coordinates as a scene frame remains distinct.

Requirement 13 distinguishes coordinate components from scene axes. Returned query tuples use the same role order; unsupported component sets cannot be guessed.

## G05: Prescribed WKT string normalization profile (closed)

The local candidate contains a referenced lossless lexical profile, exact-decimal convention, fixed-point validation and separate serialized identity/CRS-equivalence comparison. No independent normalizer implementation or conformance result is claimed. Whole-definition sharing tradeoffs remain explicit.

Requirement 31 is one sentence; formatted WKT examples are labeled as illustrations requiring normalization before conforming authoring. Valid WKT cannot be simplified by silently dropping its defining conversion.

## G06: Measurement-coordinate association (open)

Subtree scope and measurement preservation are settled. The carrier identifying absolute coordinate properties or an external dataset domain is missing; neither API application nor float3 shape supplies that role. Coordinate-only data must not acquire a fake model anchor or receive crs:position twice.

Two bounded authored facts, multiple domains, retained format associations and the external-format/composed-binding authority conflict are stated. No new relation or generic measurement schema is invented.

## G07: Dependency declaration carrier and composition (open)

Coverage is already all placed content. The carrier, root/session interpretation, conservative assembly maintenance across composition/unloaded content, and export update rule are not specified. Traversal for detection is not the promised declaration.

Existing Core customLayerData is identified as a possible carrier, not selected as a normative key. Composition does not automatically aggregate it; no prototype layer flag is promoted.

## G08: Extent and comparable-result agreement contract (closed)

Engine operation/resource responsibility is settled. Draft rules separate operation-attributed accuracy, approximation error and implementation agreement; require complete-chain pointwise reference and actual extent coverage; and establish comparability before measuring drift. This does not prescribe an approximation algorithm or full uncertainty propagation.

Cartesian distance converts axis length units to metres. Geographic comparison proposes ellipsoidal horizontal distance plus a height residual; this convention is explicitly under review. Cases/requests state their acceptance distance before execution, without a new scene property.

## G09: Export sampling-record representation (closed)

Actual timeSamples keys and explicitly authored timeCodesPerSecond can record the exported schedule and scale. Core does not standardize an authored stage interpolation-mode field. Export sample interpolation does not recreate the original source-before-conversion trajectory.

Every baked effect is represented once; trajectory-preservation claims need a bound over the time range. Sampling-policy provenance or forcing reader interpolation would be a separate model requirement, not an undocumented export flag.

## G10: Existing dimensionality inconsistency (closed)

The 3D obligation applies to complete model placements; the UTM examples illustrate horizontal definitions/components only. A third numeric component supplies no vertical datum. No 2D model mode or measurement storage profile is implicitly introduced.

Background, typed-schema example and appendix now state the same dimensionality rule.
