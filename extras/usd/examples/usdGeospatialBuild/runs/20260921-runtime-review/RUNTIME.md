# Runtime traceability and implementation evidence

Draft derivation for review; no partner approval inferred.

Status: current draft derivation

The proposed normative prose is [RUNTIME-BEHAVIOR.md](RUNTIME-BEHAVIOR.md). This file maps that prose to requirements, experiments and evidence.

Unfinished rules are in [RUNTIME-OPEN-DECISIONS.md](RUNTIME-OPEN-DECISIONS.md). Both the non-Hydra runtime and Hydra adapter remain unbuilt.

## C01 — CRS definitions and coordinate metadata

R1 — Self-contained definitions; R2 — Defined once, and describing no object; R3 — Datum, realization and epoch; R4 — A site's own grid is a CRS like any other

Implementation: Engine accepts complete WKT only; increment 1 supports the WGS 84 geographic-3D/geocentric conversion. General CRS/epoch and site-grid operations remain unimplemented.

Evidence: E03, E04, E06
Stops: S02, S06

## C02 — Composed declarations and scope

R5 — A discoverable CRS; R6 — Declared for a subtree, not a prim; R7 — Composition agnostic; R8 — Brought-in data keeps its coordinates and its CRS

Implementation: Read-only single-target relationship inspector. Stock USD resolves relationship opinions and remaps reference paths. It does not identify position carriers or implement asset/project placement.

Evidence: E01, E08, E09, E10
Stops: S01, S02, S07

## C03 — Positions, offsets and asset conventions

R9 — Positions, and offsets from them; R10 — Offsets along the axes of their position; R11 — Position or offset, and the scene says which; R12 — No angle read as a length; R13 — One axis mapping; R14 — Scene conventions stay the scene's; R15 — Placement separate from conformance

Implementation: No anchor decoding, offset basis, placement matrix or scene-unit correction is implemented. These require the decisions listed below. The AECO example is checked only as an existing stock-USD fixture.

Evidence: E02, E06, E07, E08, E10
Stops: S01, S02, S03, S07

## C04 — Shared resolved results and coordinate queries

R16 — One CRS out; R17 — The same answer for every consumer; R18 — Coordinates back out

Implementation: Engine protocol and PROJ adapter for explicit named-coordinate reporting; no renderer. No scene-target precedence, resolved-stage store or relative-placement query yet.

Evidence: E03, E07, E09
Stops: S01, S04

## C05 — Time evaluation and authored-scene preservation

R19 — Resolution leaves the scene as authored; R20 — Positions between recorded moments

Implementation: Binding inspection is read-only. Analytic regression demonstrates the path difference in requirement 20, Positions between recorded moments, but does not implement an authored geographic carrier, USD sampling or baking.

Evidence: E01, E05, E08, E09, E10
Stops: S01, S05

## C06 — Failures and operation provenance

R21 — Never placed by a guess; R28 — A result says what produced it

Implementation: Explicit unsupported/unreadable/domain/batch failures in a bounded PROJ adapter, no ballpark operations, best-available check and operation provenance. This is not general missing-grid or datum-operation support.

Evidence: E03, E04, E07, E08
Stops: S06

## C07 — Project scale, local detail and placement extent

R22 — A CRS suited to the project's size; R23 — Detail that does not depend on location; R24 — Extent under one position is bounded and stated

Implementation: No approximation algorithm or acceptance tolerance has been selected. Analytic global coordinate probes are component checks, not site/regional/global scene coverage.

Evidence: E03
Stops: S03, S04, S06

## C08 — Dependency discovery and authored-data validation

R25 — Additive for consumers that ignore it; R26 — Declares its dependency; R27 — Checkable before use

Implementation: Stock-USD transform invariance and dangling-binding diagnostics are tested. Dependency encoding, complete validator and usdchecker registration remain pending.

Evidence: E01, E02, E09
Stops: S01, S05, S07

## C09 — Agreement between implementations

R29 — Implementable from the text alone

Implementation: Repeatable snapshot/brief/trace/test/report pipeline. PROJ numerical residuals are measured against analytic checks. No second-engine or OpenUSD/OV implementation agreement is claimed.

Evidence: E03
Stops: S06
