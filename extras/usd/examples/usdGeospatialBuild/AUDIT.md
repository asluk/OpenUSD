# Implementation audit against the experiment and the proposal

**Proposal readiness: blocked.** Read [QUALITY_REVIEW.md](QUALITY_REVIEW.md)
first. It reviews all 31 requirements and distinguishes ten missing/contradictory
contracts from experimental implementation choices. This earlier candidate
audit was insufficient: defining a field before coding it does not establish
its authority in the shared proposal. The current runner stops by default; a
labeled experiment records that proposal-conformance completion is false.

| Authored fact or behavior | Necessary information and requirement | Shortcut challenged |
|---|---|---|
| Complete CRS WKT token | Definition identity, units, axes, datum and site calibration, R1–4/R31 | No separate projection, ellipsoid, height datum, calibration or epoch attributes. No EPSG code substitutes for authored WKT. |
| Binding relationship | Which complete definition describes coordinates, R5–8/R11 | References and stronger opinions resolve through ordinary USD; independent bindings retain source meaning. |
| Position / orientation / scale | Absolute model origin and full oriented/scaled placement, R9–15 | Geographic coordinates never become ordinary translates. Noncommuting controls reject origin-only placement and wrong transform order. Field choices were frozen before code but are not settled by the shared proposal. |
| Coordinate-property relationship | Identify absolute measurement arrays without guessing which vectors are positions, R12/R18/R30 | The runtime does not inspect dataset names, CSV columns, fixture paths or sidecars to resolve an authored scene. Values and recorded times remain ordinary dataset data. |
| Working-context post operator | Ordinary adjustments must retain physical meaning across output selection, R8/R16 | A labeled output-axis alternative is implemented and fails the distinguishing physical-placement control. The candidate context convention still needs group approval. |
| Writer conformance | USD stage units/up-axis, R14–15 | Original Eiffel metadata is retained; the assembler explicitly supplies the known asset corrective. Reader code cannot infer correct units from mesh appearance. |
| Dependency declaration | Discover the complete asset's need for geospatial resolution, R26 | Existing root-layer metadata is writer-maintained. Loaded-content checks cannot prove the absence of dependencies inside unloaded payloads; this limitation is explicit. |
| Export record | Output definition, sampled USD times and interpolation, R19–20 | A fresh asset contains ordinary authored facts. No private resolved/history flag changes later resolution. Coordinate/value/time associations are checked after re-import. |
| Resource and operation results | Supported non-epoch datum/height conversion and attributable operations, R21/R28 | Missing grids and time-dependent operations fail. Dependency configuration belongs to the engine. Engine accuracy estimates are not survey truth or approximation bounds. |
| Live runtime invalidation | Source edits and changed requests must reach consumers, R17/R19 | Native Hydra receives an early application scene-index override before instance propagation/flattening, with actual final geometry and instancer-transform readback; it observes source notices; OV ingests authored geometry, writes and reads live derived results, rejects stale successful results after invalid edits, and recovers. Snapshot transfer is not counted. |
| Precision and extent | Keep absolute coordinates in doubles and local geometry small, R22–24 | Global measurements use ECEF rather than a global tangent plane. Float quantization and six finite domains are measured. No vertex/sample maximum is called a continuous surface bound. |

The authored geospatial property inventory is exactly `crs:wkt`, `crs:binding`,
`crs:position`, `crs:orientation`, `crs:scale` and `crs:coordinateProperties`.
Every one is defined in the pre-implementation candidate. Data-format attributes
and live derived runtime state are separately identified; neither supplies an
undocumented authored geospatial fact. Coordinate epochs have no authored field
or computational default. CRS frame epochs remain in WKT.

The source algorithms are freshly derived. The native SDK's core source matches
the recorded stock 26.11 revision; its installed plugin directories contain no
retired geospatial module. The loaded native plugin inventory is checked on each
job. Python OpenUSD, the native imaging SDK and OV use different USD versions,
recorded in the run receipt. All three use PROJ, with the native version recorded
separately: their agreement is independent runtime evidence, not independent
geodetic-engine certification. Partner CSVs also used PROJ.

## Findings retained for design review

R24 is not fully specified: the candidate states an affine frame and finite
sample comparisons, but does not establish a certified bound over every surface
point. The measured discrepancy over larger extents shows why that distinction
matters. Reporting the gap is a result of the run, not a deferred demonstration.

The exact placement fields, project adjustment context, geographic/geocentric
tuple conventions, WKT string normalization profile, measurement association,
dependency-declaration coverage and export sampling record are experimental
answers. Their specifications precede the implementation, but this does not establish
proposal derivability. They need group review
before becoming standard text. Geographic queries are demonstrated; general
angular scene/bounds semantics are not claimed. Coordinate-epoch support remains
on the roadmap without introducing initial-scope surrogate fields.

Read `delivery/run-report.json` for executed evidence, source hashes, failures,
operation reports and conditional dataset assumptions. README and collateral
are generated from that receipt; they are not a new source of normative rules.

## Corrective review

Broken enclosing bindings now fail instead of being treated as absence. Inherited
coordinate-property roles receive authored validation. OGC-permitted structural
parentheses are normalized to preferred brackets while quoted content remains
unchanged. Engine parsing capability still does not define full OGC validity.

Default output and explicit precedence, ordinary affine leaf bounds including
curve widths, relative model frames, arbitrary dataset names/metadata and fresh
exports preserving ordinary USD geometry and instances are executed controls.
They do not specify general angular/aggregate/nonlinear bounds or a universal
dataset adapter contract. Absolute measurement arrays do not yet have a complete
placement/post-adjustment contract. The unadjusted city/global fixtures cannot
settle that behavior; dependent derivation is stopped and flagged under G03/G06.

The exporter preserves composed ordinary USD content, writes sampled output
placement using the pinned experimental record, and retains noncoordinate
properties/relationships. It carries output WKT only in the definition rather
than duplicating authority in root metadata. Round-trip samples do not promise
equivalent trajectories between samples. This encoding remains experimental.
