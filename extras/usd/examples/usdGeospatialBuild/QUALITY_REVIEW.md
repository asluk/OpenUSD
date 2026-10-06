# Local candidate readiness

Explicit candidate answers and group adoption remain separate. Exact source SHA-256: `2120953af221f83816486afbe88a06768e206d23cb570b5e39a193f254ba7a11`.

## G01: Legacy contradictions (closed)

The baseline specifies data and observable runtime behavior, retains reference-based binding and excludes ancestor transforms without source edits. Do not use old callable examples or prototype behavior as authority.

No remaining legacy contradiction in this candidate.

## G02: Exact CRS placement property contract (closed)

Candidate placement fields plus the explicit right-handed stage-to-basis table, units, scale-before-quaternion and complete point-map contract.

Group review of the concrete conventions is pending; production geospatial coverage must be tested independently.

## G03: Physical coordinate context of project adjustments (closed)

### Candidate working-frame and point-evaluation contract

Adoption remains pending. Execution and coverage must be assessed separately.

## G04: Remaining component conventions and scene result domain (closed)

### Candidate working-frame and point-evaluation contract

Q9 geographic scene frames/bounds remain separately open.

## G05: Prescribed WKT string normalization profile (closed)

The local candidate contains a referenced lossless lexical profile, exact-decimal convention, fixed-point validation and separate serialized identity/CRS-equivalence comparison. Python lexical normalizer is exercised by the contract tests; no second independent normalizer or universal WKT conformance is claimed. Whole-definition sharing tradeoffs remain explicit.

Requirement 31 is one sentence; formatted WKT examples are labeled as illustrations requiring normalization before conforming authoring. Valid WKT cannot be simplified by silently dropping its defining conversion.

## G06: Measurement-coordinate association (closed)

### Candidate external measurement association

Adoption remains pending. Execution and coverage must be assessed separately.

## G07: Dependency declaration carrier and composition (closed)

### Candidate Profiles dependency integration

Adoption remains pending. Execution and coverage must be assessed separately.

## G08: Extent and comparable-result agreement contract (closed)

Engine operation/resource responsibility is settled. Draft rules separate operation-attributed accuracy, approximation error and implementation agreement; require complete-chain pointwise reference and actual extent coverage; and establish comparability before measuring drift. This does not prescribe an approximation algorithm or full uncertainty propagation.

Cartesian distance converts axis length units to metres. Geographic comparison proposes ellipsoidal horizontal distance plus a height residual; this convention is explicitly under review. Cases/requests state their acceptance distance before execution, without a new scene property.

## G09: Export sampling-record representation (closed)

Actual timeSamples keys and explicitly authored timeCodesPerSecond can record the exported schedule and scale. Core does not standardize an authored stage interpolation-mode field. Export sample interpolation does not recreate the original source-before-conversion trajectory.

Every baked effect is represented once; trajectory-preservation claims need a bound over the time range. Sampling-policy provenance or forcing reader interpolation would be a separate model requirement, not an undocumented export flag.

## G10: Existing dimensionality inconsistency (closed)

The 3D obligation applies to complete model placements; the UTM examples illustrate horizontal definitions/components only. A third numeric component supplies no vertical datum. No 2D model mode or measurement storage profile is implicitly introduced.

Background, typed-schema example and appendix now state the same dimensionality rule.

## G11: Independently CRS-bound point-instancer prototypes (open)

Native instances and point-instanced local model geometry use the composed placement map; prototype indices and retained instance association survive resolution.

An absolute CRS-bound prototype combined with instancer placements has no defined precedence/transport contract. The candidate explicitly fails this specialized combination rather than inventing it.

## Verification boundary

- Q9 geographic scene geometry, frames and bounds remains a design question; geographic coordinate queries remain supported.
- Continuous nonlinear extent and between-sample trajectory guarantees are unsupported, with visible failure rather than an inferred certificate.
- C++ validation is not a second independent WKT normalizer. External format decoding is shared; Python and C++ share PROJ, while OV reuses the Python placement algorithm.
- Hydra consumes an ordinary resolved export; no live geospatial scene-index filter or physics integration is claimed.
- External adapters cover selected CF, single-IFD GeoTIFF and RFC 7946 domains, not all coordinate forms in those standards.
- Export preserves tested geometry/sample associations but materializes instances; authored shading-normal and general material/primvar semantics are not certified.

Current test and consumer evidence is in delivery/run-report.json. A completed candidate iteration is not a whole-requirement conformance certificate.
