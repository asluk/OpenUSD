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

## E07 — geographically diverse analytic component probes

R13 — One axis mapping; R18 — Coordinates back out; R28 — A result says what produced it

Oracle: Fresh WGS 84 ellipsoid calculations for five retained locations and seeded generated locations. No previous projected outputs or thresholds.

Expected: Explicit geographic coordinate reporting agrees within the existing component numerical tolerance; axis and height variations exercise one engine path.

Limit: Projected CRS families and provider-certified survey controls remain pending. These are diagnostic coordinates, not a chosen USD position carrier.

This run: test_workflow_locations_retained_and_generated: passed

## E08 — original external railway intake and anchor probes

R8 — Brought-in data keeps its coordinates and its CRS; R13 — One axis mapping; R19 — Resolution leaves the scene as authored; R28 — A result says what produced it

Oracle: Pinned provider assets and independently calculated geographic anchor coordinates.

Expected: Original geometry/imagery can be read unchanged; source lat-first attributes are explicitly decoded; anchor reporting agrees analytically.

Limit: No adopted legacy schema or converter; no full rail/tile placement, orientation or independent survey accuracy claim.

This run: test_workflow_railway_source_inventory_and_anchor_reporting: passed

## E09 — local scalar-field intake and stock USD visualization overlay

R7 — Composition agnostic; R17 — The same answer for every consumer; R19 — Resolution leaves the scene as authored; R25 — Additive for consumers that ignore it

Oracle: Original scalar values, source hash, stock USD composition and constructed WGS 84 coordinate probes.

Expected: Read all field samples without modifying the source; preserve the base data when adding/removing glyph geometry.

Limit: File provenance/units/CRS are incomplete. Geographic coordinates at height zero are explicitly diagnostic assumptions; no scientific or full-runtime validation.

This run: test_workflow_field_coordinate_probe: passed, test_workflow_field_removable_geometry_overlay: passed

## E10 — original railway source-to-USD preservation checks

R8 — Brought-in data keeps its coordinates and its CRS; R13 — One axis mapping; R19 — Resolution leaves the scene as authored

Oracle: User-supplied original GeoJSON feature identities and coordinate arrays, compared directly with the provider USD; no previous converter or resolved result.

Expected: Every original feature ID is present once, geometry kinds agree, LineString vertex counts are retained and first coordinates equal source anchors after explicit axis reordering.

Limit: Does not validate polygon topology or interior vertex placement. Source EPSG:4326 does not establish the third ordinate vertical datum or epoch.

This run: test_workflow_geojson_source_to_usd_identity_and_anchors: passed

## E11 — Complete conditional scene workflows and policy experiments

R1 — Self-contained definitions; R2 — Defined once, and describing no object; R3 — Datum, realization and epoch; R4 — A site's own grid is a CRS like any other; R5 — A discoverable CRS; R6 — Declared for a subtree, not a prim; R7 — Composition agnostic; R8 — Brought-in data keeps its coordinates and its CRS; R9 — Positions, and offsets from them; R10 — Offsets along the axes of their position; R11 — Position or offset, and the scene says which; R12 — No angle read as a length; R13 — One axis mapping; R14 — Scene conventions stay the scene's; R15 — Placement separate from conformance; R16 — One CRS out; R17 — The same answer for every consumer; R18 — Coordinates back out; R19 — Resolution leaves the scene as authored; R20 — Positions between recorded moments; R21 — Never placed by a guess; R22 — A CRS suited to the project's size; R23 — Detail that does not depend on location; R24 — Extent under one position is bounded and stated; R25 — Additive for consumers that ignore it; R26 — Declares its dependency; R27 — Checkable before use; R28 — A result says what produced it; R29 — Implementable from the text alone

Oracle: Raw original source vertices, provider calibration, stock composition semantics, independent Karney arithmetic and explicit constructed counterexamples.

Expected: All eight workflow families execute through complete scenes and every required consumer with no skipped in-scope work.

Limit: Unaccepted candidate rules; unknown survey metadata remains unknown. Vertex displacement is not a certified continuous-surface bound.

This run: test_complete_W01_railway_all_vertices_tiles_and_topology: passed, test_complete_W02_field_all_samples_overlay_and_query: passed, test_complete_W03_same_place_across_frames_and_units: passed, test_complete_W04_site_grid_relocation_conformance_and_incline: passed, test_complete_W05_composition_arcs_edit_and_instances[sublayer]: passed, test_complete_W05_composition_arcs_edit_and_instances[reference]: passed, test_complete_W05_composition_arcs_edit_and_instances[payload]: passed, test_complete_W05_composition_arcs_edit_and_instances[inherit]: passed, test_complete_W05_composition_arcs_edit_and_instances[specialize]: passed, test_complete_W05_composition_arcs_edit_and_instances[variant]: passed, test_complete_W05_composition_arcs_edit_and_instances[instance]: passed, test_complete_W05_point_instances_masks_and_export: passed, test_complete_W07_native_storm_and_omniverse_fabric: passed, test_complete_W06_extent_sweep_and_precision: passed, test_complete_W08_empty_binding_project_boundary_and_scope: passed, test_complete_W08_dynamic_epoch_and_missing_resources: passed, test_complete_W08_forwarding_and_time_export: passed

## Requirement coverage

| Requirement | Contract | Component evidence | Open stops |
|---|---|---|---|
| R1 — Self-contained definitions | C01 | E04, E11 |  |
| R2 — Defined once, and describing no object | C01 | E06, E11 | S02 |
| R3 — Datum, realization and epoch | C01 | E11 | S02, S06 |
| R4 — A site's own grid is a CRS like any other | C01 | E06, E11 | S02, S06 |
| R5 — A discoverable CRS | C02 | E01, E11 | S01, S02, S07 |
| R6 — Declared for a subtree, not a prim | C02 | E01, E11 | S01, S02, S07 |
| R7 — Composition agnostic | C02 | E01, E09, E11 | S07 |
| R8 — Brought-in data keeps its coordinates and its CRS | C02 | E08, E10, E11 | S01, S02, S06 |
| R9 — Positions, and offsets from them | C03 | E11 | S01, S03 |
| R10 — Offsets along the axes of their position | C03 | E11 | S03 |
| R11 — Position or offset, and the scene says which | C03 | E11 | S01, S02 |
| R12 — No angle read as a length | C03 | E11 | S01, S03 |
| R13 — One axis mapping | C03 | E07, E08, E10, E11 | S03 |
| R14 — Scene conventions stay the scene's | C03 | E06, E11 | S03, S06 |
| R15 — Placement separate from conformance | C03 | E06, E11 | S03 |
| R16 — One CRS out | C04 | E11 | S04, S06 |
| R17 — The same answer for every consumer | C04 | E09, E11 | S04 |
| R18 — Coordinates back out | C04 | E03, E07, E11 | S04 |
| R19 — Resolution leaves the scene as authored | C05 | E01, E06, E08, E09, E10, E11 | S01, S05 |
| R20 — Positions between recorded moments | C05 | E05, E11 | S01 |
| R21 — Never placed by a guess | C06 | E04, E11 | S04, S06, S07 |
| R22 — A CRS suited to the project's size | C07 | E11 | S03, S04, S06 |
| R23 — Detail that does not depend on location | C07 | E11 | S03, S04, S06 |
| R24 — Extent under one position is bounded and stated | C07 | E11 | S03, S06 |
| R25 — Additive for consumers that ignore it | C08 | E02, E09, E11 | S05 |
| R26 — Declares its dependency | C08 | E11 | S05 |
| R27 — Checkable before use | C08 | E01, E11 | S01, S05, S07 |
| R28 — A result says what produced it | C06 | E03, E07, E08, E11 | S06 |
| R29 — Implementable from the text alone | C09 | E11 | S06 |

## Dataset follow-up

- Dataset inventory and workflow demonstrations: see [WORKFLOWS.md](WORKFLOWS.md). Reused datasets do not carry old implementation semantics or acceptance thresholds.
- Sébastien: additional calibration/control points, current-epoch ITRF example and inclined-plane case; public sharing permission remains pending.
- Tamrat: Redlands scene/script, source WKT and dataset with expected placements.
- Devin: facility, city, region and world cases remain pending.
- Independent numerical and Kit Fabric consumers now run. Additional practitioner-certified controls remain an external evidence question.
