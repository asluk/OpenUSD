# Runtime traceability and implementation evidence

Draft derivation for review; no partner approval inferred.

Status: current draft derivation

The proposed normative prose is [RUNTIME-BEHAVIOR.md](RUNTIME-BEHAVIOR.md). This file maps that prose to requirements, experiments and evidence.

Unfinished rules are in [RUNTIME-OPEN-DECISIONS.md](RUNTIME-OPEN-DECISIONS.md). The non-Hydra runtime, native Hydra/Storm adapter and Kit Fabric consumer execute conditional policies documented in [the candidate contract](RUNTIME-EXPERIMENTS.md).

## C01 — CRS definitions and coordinate metadata

R1 — Self-contained definitions; R2 — Defined once, and describing no object; R3 — Datum, realization and epoch; R4 — A site's own grid is a CRS like any other

Implementation: Complete-WKT PROJ operations, explicit coordinate epochs and site calibration; independent PyGeodesy/Karney static same-datum operations. Missing grids and unsupported operations fail.

Evidence: E03, E04, E06, E11
Stops: S02, S06

## C02 — Composed declarations and scope

R5 — A discoverable CRS; R6 — Declared for a subtree, not a prim; R7 — Composition agnostic; R8 — Brought-in data keeps its coordinates and its CRS

Implementation: SceneResolver reads composed positions/bindings. Equivalent sublayers, references, payloads, inherits, specializes, variants and native instances are exercised with remapped in-scope definitions.

Evidence: E01, E08, E09, E10, E11
Stops: S01, S02, S07

## C03 — Positions, offsets and asset conventions

R9 — Positions, and offsets from them; R10 — Offsets along the axes of their position; R11 — Position or offset, and the scene says which; R12 — No angle read as a length; R13 — One axis mapping; R14 — Scene conventions stay the scene's; R15 — Placement separate from conformance

Implementation: Explicit attribute/translate carriers, absolute boundary, ordinary offsets, stage-convention/author-conformed candidates, local-grid/project transform and affine/pointwise geometry placement.

Evidence: E02, E06, E07, E08, E10, E11
Stops: S01, S02, S03, S07

## C04 — Shared resolved results and coordinate queries

R16 — One CRS out; R17 — The same answer for every consumer; R18 — Coordinates back out

Implementation: ResolvedScene provides world positions, relative placement, coordinate reporting and bounds; native Hydra/Storm and Kit Fabric consume its evaluated geometry and placements.

Evidence: E03, E07, E09, E11
Stops: S01, S04

## C05 — Time evaluation and authored-scene preservation

R19 — Resolution leaves the scene as authored; R20 — Positions between recorded moments

Implementation: Native USD interpolation precedes conversion. Object-change notices invalidate resolution. Explicit export records CRS and sample times; exported results are consumed without double placement.

Evidence: E01, E05, E08, E09, E10, E11
Stops: S01, S05

## C06 — Failures and operation provenance

R21 — Never placed by a guess; R28 — A result says what produced it

Implementation: Authored validation distinguishes scope/dependency errors from operation failures. Whole batches fail on bad coordinates, absent coordinate epoch or missing grids; provenance records selected operations.

Evidence: E03, E04, E07, E08, E11
Stops: S06

## C07 — Project scale, local detail and placement extent

R22 — A CRS suited to the project's size; R23 — Detail that does not depend on location; R24 — Extent under one position is bounded and stated

Implementation: Double placement with small local points preserves detail at global magnitude. Affine/pointwise alternatives measure all-vertex displacement and reject an exceeded budget. Continuous-surface semantics remain an actual design question.

Evidence: E03, E11
Stops: S03, S04, S06

## C08 — Dependency discovery and authored-data validation

R25 — Additive for consumers that ignore it; R26 — Declares its dependency; R27 — Checkable before use

Implementation: Constant-time layer/default-prim dependency candidates, coverage validation, explicit baked-state metadata and observable failure; unaware USD remains unchanged.

Evidence: E01, E02, E09, E11
Stops: S01, S05, S07

## C09 — Agreement between implementations

R29 — Implementable from the text alone

Implementation: PROJ and independent Karney geographic/ECEF/exact-TM coordinate math agree under stated static same-datum scope. Native Hydra and real Kit Fabric separately establish consumer consistency.

Evidence: E03, E11
Stops: S06
