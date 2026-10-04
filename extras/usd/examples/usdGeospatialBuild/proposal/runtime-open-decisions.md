# Derivation from the shared geospatial proposal

Authority: full proposal snapshot at `39c8fb816a9113b14c8f64b020270724b8357312`, retained verbatim in [proposal-source.txt](proposal-source.txt). This derivation records defined behavior and missing contracts. It is not an alternative specification.

## Missing contracts and existing inconsistency

### G02: Exact CRS placement property contract

Already defined: Separate CRS position, orientation and scale resolve before ordinary USD transforms. Direct binding sets the placement boundary; source positions interpolate before conversion.

Remaining: Property names, types, defaults or requiredness, applicability, and the bases and mutual order of orientation and scale are not defined. Internal differentiation or caching methods are implementation freedom.

Questions: 2, 6.

### G03: Physical coordinate context of project adjustments

Already defined: Ordinary project adjustments apply after CRS placement. The adjusted physical placement survives output selection, including adjusted imagery. An enclosing binding supplies working context without replacing an independent source CRS.

Remaining: The authored coordinate frame giving an adjustment its physical meaning, and its derivation through nested scopes and output changes, are not specified. Adjusted measurements are not a new functional scope question.

Questions: 3.

### G04: Remaining component conventions and scene result domain

Already defined: Projected X/Y/Z means easting/northing/up. Geographic source positions and geographic coordinate queries are supported. Writers author stage-convention correctives.

Remaining: Other CRS component sets lack a complete mapping to authored placement components. Geographic scene geometry, frames and bounds remain separate from permitted geographic coordinate queries.

Questions: 6, 9.

### G05: Prescribed WKT string normalization profile

Already defined: The complete WKT definition is authoritative. Requirement 31 requires normalized serialized text while preserving represented information. Token equality and geodetic equivalence are distinct.

Remaining: The required normal form is not prescribed or normatively referenced. A projection library round trip or a hand-chosen whitespace rule cannot establish proposal conformance.

Questions: 10.

### G06: Measurement-coordinate association

Already defined: Nearest direct binding defines composed subtree CRS scope. Measurement values retain their coordinate/time associations. Ordinary geometry vertices are offsets.

Remaining: The authored association identifying which properties or external-asset coordinates carry measurement positions is missing. Vector shape or property name cannot identify the role.

Questions: 11.

### G07: Dependency declaration carrier and composition

Already defined: A declaration must expose dependency without traversal and cover all placed content, including referenced and unloaded content and resolved export.

Remaining: The authored carrier and its composition rules are not specified. Searching for applied bindings does not satisfy a declaration promised without traversal.

Questions: 12.

### G08: Extent and comparable-result agreement contract

Already defined: The engine selects operations and manages transformation resources. Results identify the operation and attributed accuracy. Consumers share resolution. Placement distance and extent must be stated.

Remaining: The claimed approximation domain and its satisfaction/reporting, comparable operations and agreement measure remain unspecified, including geographic distance. Full placement-chain accuracy propagation is not a requirement-28 obligation. Missing consumer tests are verification work.

Questions: 13.

### G09: Export sampling-record representation

Already defined: Explicit export records its output CRS and sampling, preserves values and associations, and rereads without repeating source conversion or private resolved flags.

Remaining: The authored sampling record must distinguish interpolation of exported samples from resolution of original source samples. Lost properties and fixture-specific export names are implementation defects, not new functional gaps.

Questions: 14.

### G10: Existing dimensionality inconsistency

Already defined: The background requires 3D CRS definitions. Missing height or unsupported transformations must not be guessed.

Remaining: The detailed schema and UTM appendix contain two-axis WKT examples. Reconcile whether they illustrate horizontal components or permit complete bound definitions. Do not silently broaden scope. This run uses only complete 3D examples.

Questions: 2, 6, 11.

G01 is closed by the editorial revision. An internal implementation recipe, a preference for the retained prototype or absent verification does not reopen an agreed functional outcome. Coordinate epochs remain deferred under roadmap question 15.
