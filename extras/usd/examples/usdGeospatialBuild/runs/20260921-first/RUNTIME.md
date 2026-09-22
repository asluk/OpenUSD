# Runtime behavior derived from the functional requirements

Draft derivation for review; no partner approval inferred.

Status: current draft derivation

This is a partial runtime contract. Experimental implementation choices are not proposal decisions.

## C01

R1 — Self-contained definitions; R2 — Defined once, and describing no object; R3 — Datum, realization and epoch; R4 — A site's own grid is a CRS like any other

Keep complete CRS definitions distinct from object placement. Definitions may describe site calibration. Distinguish datum reference epoch, coordinate epoch and animation sample time; do not supply an absent epoch.

Implementation: Engine accepts complete WKT only; increment 1 supports the WGS 84 geographic-3D/geocentric conversion. General CRS/epoch and site-grid operations remain unimplemented.

Evidence: E03, E04, E06
Stops: S02, S06

## C02

R5 — A discoverable CRS; R6 — Declared for a subtree, not a prim; R7 — Composition agnostic; R8 — Brought-in data keeps its coordinates and its CRS

Read CRS definitions and binding scope from the composed stage. A nested declaration overrides the enclosing scope. Equivalent composed data must give equivalent CRS interpretation. Preserve imported coordinates and their native CRS.

Implementation: Read-only single-target relationship inspector. Stock USD resolves relationship opinions and remaps reference paths. It does not identify position carriers or implement asset/project placement.

Evidence: E01
Stops: S01, S02, S07

## C03

R9 — Positions, and offsets from them; R10 — Offsets along the axes of their position; R11 — Position or offset, and the scene says which; R12 — No angle read as a length; R13 — One axis mapping; R14 — Scene conventions stay the scene's; R15 — Placement separate from conformance

Separate absolute positions from ordinary offsets; nested positions cut off ancestor placement. Descendant offsets use the position CRS's axes and scale. No angle is a scene length; scene units/up axis remain authored; asset conformance and survey placement are separate.

Implementation: No anchor decoding, offset basis, placement matrix or scene-unit correction is implemented. These require the decisions listed below. The AECO example is checked only as an existing stock-USD fixture.

Evidence: E02, E06
Stops: S01, S02, S03, S07

## C04

R16 — One CRS out; R17 — The same answer for every consumer; R18 — Coordinates back out

A resolution produces one output CRS shared by all consumers without needing a renderer. Reporting an already resolved position in another supported CRS is distinct from selecting the scene resolution target. Relative queries operate on resolved placements.

Implementation: Engine protocol and PROJ adapter for explicit named-coordinate reporting; no renderer. No scene-target precedence, resolved-stage store or relative-placement query yet.

Evidence: E03
Stops: S01, S04

## C05

R19 — Resolution leaves the scene as authored; R20 — Positions between recorded moments

Read composed authored data without editing it. Evaluate a sampled native position before converting it; do not interpolate converted samples as a replacement. Export is a separate operation recording output CRS and sampling, without double transformation on re-resolution.

Implementation: Binding inspection is read-only. Analytic regression demonstrates the path difference in requirement 20, Positions between recorded moments, but does not implement an authored geographic carrier, USD sampling or baking.

Evidence: E01, E05
Stops: S01, S05

## C06

R21 — Never placed by a guess; R28 — A result says what produced it

Reject an uncomputable or incomplete operation rather than return a substitute placement. Separate authored-data diagnostics from engine failures; retain source. Successful output reports the actual operation and engine-attributed accuracy independently from measured residuals.

Implementation: Explicit unsupported/unreadable/domain/batch failures in a bounded PROJ adapter, no ballpark operations, best-available check and operation provenance. This is not general missing-grid or datum-operation support.

Evidence: E03, E04
Stops: S06

## C07

R22 — A CRS suited to the project's size; R23 — Detail that does not depend on location; R24 — Extent under one position is bounded and stated

Support project sizes without assuming a single flat plane; preserve authored asset-relative detail. A placement approximation needs both a distance bound and the extent where it holds.

Implementation: No approximation algorithm or acceptance tolerance has been selected. Analytic global coordinate probes are component checks, not site/regional/global scene coverage.

Evidence: E03
Stops: S03, S04, S06

## C08

R25 — Additive for consumers that ignore it; R26 — Declares its dependency; R27 — Checkable before use

Geospatial information leaves the scene seen by an unaware consumer unchanged. A discoverable dependency declaration covers every placed object. Validate what can be known from authored intent; do not claim to infer wrong but plausible survey coordinates.

Implementation: Stock-USD transform invariance and dangling-binding diagnostics are tested. Dependency encoding, complete validator and usdchecker registration remain pending.

Evidence: E01, E02
Stops: S01, S05, S07

## C09

R29 — Implementable from the text alone

Independent implementations using different engines report agreement as an output-unit distance at a stated coordinate magnitude, with operation identity so operation selection is not confused with numerical drift.

Implementation: Repeatable snapshot/brief/trace/test/report pipeline. PROJ numerical residuals are measured against analytic checks. No second-engine or OpenUSD/OV implementation agreement is claimed.

Evidence: E03
Stops: S06
