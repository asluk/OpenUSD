# Proposal quality and the current execution boundary

Eight narrower missing contracts plus one existing dimensionality inconsistency. Earlier legacy contradictions are closed. These are not nine missing functional requirements.

The full published source is pinned at `39c8fb816a9113b14c8f64b020270724b8357312`. All 31 requirements are traced to their exact source clauses. The current audit corrects the earlier claim of ten broad gaps: placement ordering, geographic queries, adjusted imagery, writer conformance, source preservation, operation responsibility and export intent already have answers.

## G01: Legacy contradictions (closed)

The editorial revision removes obsolete callable interfaces, translate placement and binding-helper reset authoring. Reference-based binding remains the shared representation.

No remaining legacy contradiction in these sections. The earlier relationship carrier is an implementation departure, not an unspecified binding choice.

Authority: proposal/proposal-source.txt:1360 (### CRS binding and inheritance); proposal/proposal-source.txt:1467 (### CRS association and model placement); proposal/proposal-source.txt:1537 (### Transform stack and resetXformStack).

## G02: Exact CRS placement property contract (open)

Separate CRS position, orientation and scale resolve before ordinary USD transforms. Direct binding sets the placement boundary; source positions interpolate before conversion.

Property names, types, defaults or requiredness, applicability, and the bases and mutual order of orientation and scale are not defined. Internal differentiation or caching methods are implementation freedom.

Authority: proposal/proposal-source.txt:1176 (#### Decision on question 2:); proposal/proposal-source.txt:1467 (### CRS association and model placement); proposal/proposal-source.txt:886 (20. **Positions between recorded moments).

## G03: Physical coordinate context of project adjustments (open)

Ordinary project adjustments apply after CRS placement. The adjusted physical placement survives output selection, including adjusted imagery. An enclosing binding supplies working context without replacing an independent source CRS.

The authored coordinate frame giving an adjustment its physical meaning, and its derivation through nested scopes and output changes, are not specified. Adjusted measurements are not a new functional scope question.

Authority: proposal/proposal-source.txt:1242 (#### Decision on question 3:); proposal/proposal-source.txt:687 (8. **Brought-in data keeps its coordinates).

## G04: Remaining component conventions and scene result domain (open)

Projected X/Y/Z means easting/northing/up. Geographic source positions and geographic coordinate queries are supported. Writers author stage-convention correctives.

Other CRS component sets lack a complete mapping to authored placement components. Geographic scene geometry, frames and bounds remain separate from permitted geographic coordinate queries.

Authority: proposal/proposal-source.txt:781 (13. **One axis mapping); proposal/proposal-source.txt:1150 (For open question 6,); proposal/proposal-source.txt:1129 (Requirement 18 already permits geographic output).

## G05: Prescribed WKT string normalization profile (open)

The complete WKT definition is authoritative. Requirement 31 requires normalized serialized text while preserving represented information. Token equality and geodetic equivalence are distinct.

The required normal form is not prescribed or normatively referenced. A projection library round trip or a hand-chosen whitespace rule cannot establish proposal conformance.

Authority: proposal/proposal-source.txt:636 (31. **Same definition, same meaning); proposal/proposal-source.txt:1144 (Open question 10 covers).

## G06: Measurement-coordinate association (open)

Nearest direct binding defines composed subtree CRS scope. Measurement values retain their coordinate/time associations. Ordinary geometry vertices are offsets.

The authored association identifying which properties or external-asset coordinates carry measurement positions is missing. Vector shape or property name cannot identify the role.

Authority: proposal/proposal-source.txt:1200 (#### Decision on question 11:); proposal/proposal-source.txt:935 (30. **Measurements remain usable as data).

## G07: Dependency declaration carrier and composition (open)

A declaration must expose dependency without traversal and cover all placed content, including referenced and unloaded content and resolved export.

The authored carrier and its composition rules are not specified. Searching for applied bindings does not satisfy a declaration promised without traversal.

Authority: proposal/proposal-source.txt:999 (26. **Declares its dependency); proposal/proposal-source.txt:1157 (Open question 12 concerns).

## G08: Extent and comparable-result agreement contract (open)

The engine selects operations and manages transformation resources. Results identify the operation and attributed accuracy. Consumers share resolution. Placement distance and extent must be stated.

The claimed approximation domain and its satisfaction/reporting, comparable operations and agreement measure remain unspecified, including geographic distance. Full placement-chain accuracy propagation is not a requirement-28 obligation. Missing consumer tests are verification work.

Authority: proposal/proposal-source.txt:1285 (#### Decision on question 13:); proposal/proposal-source.txt:974 (24. **Extent under one position); proposal/proposal-source.txt:1025 (28. **A result says what produced it); proposal/proposal-source.txt:1043 (29. **Implementable from the text alone).

## G09: Export sampling-record representation (open)

Explicit export records its output CRS and sampling, preserves values and associations, and rereads without repeating source conversion or private resolved flags.

The authored sampling record must distinguish interpolation of exported samples from resolution of original source samples. Lost properties and fixture-specific export names are implementation defects, not new functional gaps.

Authority: proposal/proposal-source.txt:1219 (#### Decision on question 14:); proposal/proposal-source.txt:867 (19. **Resolution leaves the scene as authored).

## G10: Existing dimensionality inconsistency (open)

The background requires 3D CRS definitions. Missing height or unsupported transformations must not be guessed.

The detailed schema and UTM appendix contain two-axis WKT examples. Reconcile whether they illustrate horizontal components or permit complete bound definitions. Do not silently broaden scope. This run uses only complete 3D examples.

Authority: proposal/proposal-source.txt:167 (### 3D CRS types); proposal/proposal-source.txt:1409 (### GeospatialCRS typed schema); proposal/proposal-source.txt:1874 (### WGS 84 / UTM zone 11N).

## Why the earlier implementation did not stop

The earlier freeze pinned private candidate answers rather than demonstrating their derivation from the entire shared proposal. The audit then checked code against that candidate. A requirements-only intake omitted conflicting design text, and passing self-selected tests became the headline. Explicit experimental authorization did not establish shared-proposal conformance.

The current default gate validates the whole source and derivation hashes, stops dependent execution and produces a receipt for only the defined discovery controls. A failed nearest binding cannot be rescued by choosing a different source. The previous relationship reader is retained as historical code and tested as incompatible, not adopted as a new model.

Missing renderer, physics or export tests are unfinished verification. The shared text does not require a particular internal approximation algorithm or full-chain propagation of operation accuracy. Any repair must follow requirements and existing USD semantics, independently of the old implementation.
