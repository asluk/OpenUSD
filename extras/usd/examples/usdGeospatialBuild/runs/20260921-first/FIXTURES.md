# Fixture matrix

No row certifies a complete requirement. Expected values and their provenance are separate from the runtime.

## E01 — synthetic USD component tests

R5 — A discoverable CRS; R6 — Declared for a subtree, not a prim; R7 — Composition agnostic; R19 — Resolution leaves the scene as authored; R27 — Checkable before use

Oracle: Stock USD composition plus directly authored relationship targets; not partner control points

Expected: Flattened/reference/sublayer representations of equivalent composed data give the same binding. Nested declaration wins; dangling binding fails; reading changes no layer.

Limit: Does not decide or implement an anchor carrier; composition coverage is sampled, not every arc/variant/instance.

This run: test_binding_composed_reference_flatten_and_sublayer: passed, test_binding_nested_override_and_no_mutation: passed, test_binding_stronger_opinion_and_forwarding: passed, test_binding_invalid_nearer_binding_never_falls_back[targets0]: passed, test_binding_invalid_nearer_binding_never_falls_back[targets1]: passed, test_binding_invalid_nearer_binding_never_falls_back[targets2]: passed, test_binding_invalid_nearer_binding_never_falls_back[targets3]: passed

## E02 — synthetic USD component test

R25 — Additive for consumers that ignore it

Oracle: Stock USD XformCache before and after additive metadata

Expected: Same ordinary transform before and after CRS declaration/binding metadata.

Limit: No geospatial placement is resolved.

This run: test_additive_metadata_leaves_stock_transform_unchanged: passed

## E03 — analytic engine checks

R18 — Coordinates back out; R28 — A result says what produced it

Oracle: WGS 84 ellipsoid equations/constants; expected coordinates calculated without PROJ

Expected: 3D metre residual <= 1e-6 at Earth-scale magnitude; reporting back to geographic agrees with the analytic input.

Limit: Harness numerical tolerance only, not a proposal-wide conformance threshold or independent partner dataset.

This run: test_engine_analytic_global_points_and_provenance: passed, test_engine_analytic_geographic_reporting: passed

## E04 — negative engine component tests

R1 — Self-contained definitions; R21 — Never placed by a guess

Oracle: Explicitly invalid input or injected unavailable/partial engine result

Expected: Whole batch fails; no substitute, partial result, authority-only definition, assumed height or unsupported operation succeeds.

Limit: Missing-resource fault injection tests the adapter guard, not a real datum-grid operation.

This run: test_engine_reject_invalid_batch[bad0]: passed, test_engine_reject_invalid_batch[bad1]: passed, test_engine_reject_invalid_batch[bad2]: passed, test_engine_reject_invalid_batch[bad3]: passed, test_engine_reject_invalid_batch[bad4]: passed, test_engine_reject_codes_unsupported_and_empty: passed, test_engine_reject_unavailable_best_operation: passed, test_engine_reject_partial_result: passed

## E05 — requirement-case analytic check

R20 — Positions between recorded moments

Oracle: Requirement 20, Positions between recorded moments: equatorial +/-1 degree example; WGS 84 equatorial radius

Expected: Convert interpolated native midpoint gives height zero; interpolate converted endpoints produces a chord about 971 m below it.

Limit: Does not establish geographic authored positions are permitted or select a carrier/interpolator.

This run: test_native_sample_midpoint_before_conversion: passed

## E06 — partner-authored attachment baseline

R2 — Defined once, and describing no object; R4 — A site's own grid is a CRS like any other; R14 — Scene conventions stay the scene's; R15 — Placement separate from conformance; R19 — Resolution leaves the scene as authored

Oracle: Sébastien's README: origin (648237.125, 6862251.890, 33.790), approximately 300 m tower; local-grid origin (1000,1000) corresponds to (648200,6862200)

Expected: Stock USD reproduces the stated placement; separate conformance rotation maps asset Y-up to scene Z-up. Inspect complete WKT without running attachment scripts.

Limit: Existing reference-based binding/reset conventions are not adopted. This is not new-runtime conformance; raw survey points, inclined-plane calibration and redistribution permission are absent.

This run: test_aeco_partner_stated_origin_and_conformance: passed, test_aeco_wkt_library_and_calibration_origin: passed

## Requirement coverage

| Requirement | Contract | Component evidence | Open stops |
|---|---|---|---|
| R1 — Self-contained definitions | C01 | E04 |  |
| R2 — Defined once, and describing no object | C01 | E06 | S02 |
| R3 — Datum, realization and epoch | C01 | not exercised | S02, S06 |
| R4 — A site's own grid is a CRS like any other | C01 | E06 | S02, S06 |
| R5 — A discoverable CRS | C02 | E01 | S01, S02, S07 |
| R6 — Declared for a subtree, not a prim | C02 | E01 | S01, S02, S07 |
| R7 — Composition agnostic | C02 | E01 | S07 |
| R8 — Brought-in data keeps its coordinates and its CRS | C02 | not exercised | S01, S02, S06 |
| R9 — Positions, and offsets from them | C03 | not exercised | S01, S03 |
| R10 — Offsets along the axes of their position | C03 | not exercised | S03 |
| R11 — Position or offset, and the scene says which | C03 | not exercised | S01, S02 |
| R12 — No angle read as a length | C03 | not exercised | S01, S03 |
| R13 — One axis mapping | C03 | not exercised | S03 |
| R14 — Scene conventions stay the scene's | C03 | E06 | S03, S06 |
| R15 — Placement separate from conformance | C03 | E06 | S03 |
| R16 — One CRS out | C04 | not exercised | S04, S06 |
| R17 — The same answer for every consumer | C04 | not exercised | S04 |
| R18 — Coordinates back out | C04 | E03 | S04 |
| R19 — Resolution leaves the scene as authored | C05 | E01, E06 | S01, S05 |
| R20 — Positions between recorded moments | C05 | E05 | S01 |
| R21 — Never placed by a guess | C06 | E04 | S04, S06, S07 |
| R22 — A CRS suited to the project's size | C07 | not exercised | S03, S04, S06 |
| R23 — Detail that does not depend on location | C07 | not exercised | S03, S04, S06 |
| R24 — Extent under one position is bounded and stated | C07 | not exercised | S03, S06 |
| R25 — Additive for consumers that ignore it | C08 | E02 | S05 |
| R26 — Declares its dependency | C08 | not exercised | S05 |
| R27 — Checkable before use | C08 | E01 | S01, S05, S07 |
| R28 — A result says what produced it | C06 | E03 | S06 |
| R29 — Implementable from the text alone | C09 | not exercised | S06 |

## Dataset follow-up

- Sébastien: additional calibration/control points, current-epoch ITRF example and inclined-plane case; public sharing permission remains pending.
- Tamrat: Redlands scene/script, source WKT and dataset with expected placements.
- Devin: facility, city, region and world cases remain pending.
- NVIDIA: second engine and independent OV implementation; shared-consumer/invalidation integration after the runtime contract supports it.
