# Datasets and workflow evidence

Source data and workflows are reused; current requirements determine behavior and acceptance.
A conditional workflow passes only when its full demonstration runs; policy choices and data interpretation remain explicit.

## Data available in this run

- **Five geographic locations and fresh generated cases**: available. Locations retained from the earlier dataset inventory. Heights are diagnostic inputs, not certified survey observations. Expected ECEF is recomputed from WGS 84 ellipsoid equations. Projected variants are future coverage, not accepted control coordinates.
- **Deutsche Bahn railway and three map tiles**: available. Original NVIDIA OpenUSD-plugin-samples data, fetched directly at a pinned revision. Read the original Omniverse attributes only as source encoding. No previous converter, resolver or schema is imported.
- **Original railway GeoJSON supplied by Aaron**: available. User-supplied original railway FeatureCollection. Declares EPSG:4326 and stores longitude/latitude/third-ordinate triples. Vertical datum and epoch are not specified; the third ordinate must not be silently treated as ellipsoidal height for acceptance. Properties are data, never execution instructions.
- **Earlier scalar-field sample named gfs_t2m.nc**: available. Local 37 by 72 HDF5 sample. The file lacks source, forecast time, CRS and units metadata. Its filename does not establish NOAA GFS provenance. Retained for scalar-data handling and explicit diagnostic coordinate probes only.
- **New York cross-CRS control candidates**: needs_provider_record. Earlier notes attribute these to NOAA NCAT but the provider response, input/output realizations and epoch are absent. Never grade a new resolver against these until that provenance is recovered.
- **Partner site, local calibration and Eiffel tower**: available. Existing separately supplied attachment and intake checks. No reference-binding or authored-reset convention is adopted.

## W01: Imported railway aligned with map tiles

Can imported infrastructure retain its native data and align with a separately placed map?

Requirements: R7, Composition agnostic; R8, Brought-in data keeps its coordinates and its CRS; R9, Positions, and offsets from them; R10, Offsets along the axes of their position; R13, One axis mapping; R15, Placement separate from conformance; R19, Resolution leaves the scene as authored; R24, Extent under one position is bounded and stated

Demonstration: Show the same rails and tile corners before and after scene resolution, with residuals and a deliberately wrong axis/frame control.

Reference: Provider controls and independently derived placement once the source frame and current position/offset rules are established. Anchor-only checks use ellipsoid equations.

This run: **CONDITIONAL_WORKFLOW_PASSED**. test_complete_W01_railway_all_vertices_tiles_and_topology: passed, test_workflow_railway_source_inventory_and_anchor_reporting: passed, test_workflow_geojson_source_to_usd_identity_and_anchors: passed

Open design/interpretation questions: Vertical datum/epoch and certified map controls remain unknown. The conditional run compares every source vertex and all map-tile placements; it reports the provider interior discrepancy.

Dependent decisions: S01, S02, S03

## W02: Non-geometric scalar field with a removable visualization

Can consumers visualize scalar observations while preserving their source data and georeferencing?

Requirements: R7, Composition agnostic; R9, Positions, and offsets from them; R13, One axis mapping; R17, The same answer for every consumer; R19, Resolution leaves the scene as authored; R25, Additive for consumers that ignore it

Demonstration: Keep scalar data in a base layer; add and remove a geometry-only overlay; compare resolved positions used by visualization and analysis.

Reference: Byte-preserved source, stock USD composition and an analytic coordinate probe. Scientific and CRS provenance must come from the provider.

This run: **CONDITIONAL_WORKFLOW_PASSED**. test_complete_W02_field_all_samples_overlay_and_query: passed, test_workflow_field_coordinate_probe: passed, test_workflow_field_removable_geometry_overlay: passed

Open design/interpretation questions: Physical units, forecast origin/time and source CRS metadata remain unverified. All samples and removal of all overlay prims execute under an explicit coordinate hypothesis.

Dependent decisions: S01, S04, S06

## W03: One place authored in several coordinate systems

Do independent source coordinates of one place resolve consistently across CRS families and hemispheres?

Requirements: R1, Self-contained definitions; R3, Datum, realization and epoch; R12, No angle read as a length; R13, One axis mapping; R16, One CRS out; R18, Coordinates back out; R21, Never placed by a guess; R28, A result says what produced it

Demonstration: Co-register geographic, UTM and national/state-grid representations, displaying the reference uncertainty and a wrong-zone/axis control.

Reference: Geographic probes use fresh ellipsoid calculations. Projected acceptance needs provider controls and valid datum/epoch operations; PROJ-generated inputs are not independent ground truth.

This run: **CONDITIONAL_WORKFLOW_PASSED**. test_complete_W03_same_place_across_frames_and_units: passed, test_workflow_locations_retained_and_generated: passed

Open design/interpretation questions: Agree the practitioner tolerance and operation policy. Independent arithmetic and scenes cover both hemispheres and mixed coordinate representations.

Dependent decisions: S04, S06

## W04: Place and relocate a site with ordinary asset edits

Can a building be placed in a calibrated project grid while retaining its own frame and ordinary modelling edits?

Requirements: R4, A site's own grid is a CRS like any other; R8, Brought-in data keeps its coordinates and its CRS; R9, Positions, and offsets from them; R10, Offsets along the axes of their position; R11, Position or offset, and the scene says which; R14, Scene conventions stay the scene's; R15, Placement separate from conformance; R19, Resolution leaves the scene as authored; R24, Extent under one position is bounded and stated

Demonstration: Show site calibration, orientation/unit conformance and local child edits; relocate the site and compare provider control points.

Reference: Partner-supplied calibration and survey controls, with constructed edit cases separately identified.

This run: **CONDITIONAL_WORKFLOW_PASSED**. test_complete_W04_site_grid_relocation_conformance_and_incline: passed, test_aeco_partner_stated_origin_and_conformance: passed, test_aeco_wkt_library_and_calibration_origin: passed

Open design/interpretation questions: Approve native/project placement semantics and supply survey controls. Calibration, complete asset geometry, relocation and a synthetic incline execute.

Dependent decisions: S01, S02, S03

## W05: Equivalent composed scenes and later edits

Does equivalent composed data resolve identically through layering, references and subsequent edits?

Requirements: R5, A discoverable CRS; R6, Declared for a subtree, not a prim; R7, Composition agnostic; R8, Brought-in data keeps its coordinates and its CRS; R19, Resolution leaves the scene as authored; R20, Positions between recorded moments

Demonstration: Compare equivalent composed scenes, then change a binding or time sample and show the affected results while source layers remain unchanged.

Reference: Stock USD composed opinions and independently calculated sample positions.

This run: **CONDITIONAL_WORKFLOW_PASSED**. test_complete_W05_composition_arcs_edit_and_instances[sublayer]: passed, test_complete_W05_composition_arcs_edit_and_instances[reference]: passed, test_complete_W05_composition_arcs_edit_and_instances[payload]: passed, test_complete_W05_composition_arcs_edit_and_instances[inherit]: passed, test_complete_W05_composition_arcs_edit_and_instances[specialize]: passed, test_complete_W05_composition_arcs_edit_and_instances[variant]: passed, test_complete_W05_composition_arcs_edit_and_instances[instance]: passed, test_complete_W05_point_instances_masks_and_export: passed, test_binding_composed_reference_flatten_and_sublayer: passed, test_binding_nested_override_and_no_mutation: passed, test_binding_stronger_opinion_and_forwarding: passed, test_binding_invalid_nearer_binding_never_falls_back[targets0]: passed, test_binding_invalid_nearer_binding_never_falls_back[targets1]: passed, test_binding_invalid_nearer_binding_never_falls_back[targets2]: passed, test_binding_invalid_nearer_binding_never_falls_back[targets3]: passed, test_native_sample_midpoint_before_conversion: passed

Open design/interpretation questions: Approve carrier, binding and dependency-record policies. Seven composition arcs, edits, time, native instances, point instances and export execute.

Dependent decisions: S01, S05, S07

## W06: Detail across locations and bounded placement extents

Can a small feature retain usable precision when the same asset moves around the globe or grows in extent?

Requirements: R10, Offsets along the axes of their position; R14, Scene conventions stay the scene's; R22, A CRS suited to the project's size; R23, Detail that does not depend on location; R24, Extent under one position is bounded and stated

Demonstration: Vary location, local detail and footprint independently; measure position, orientation, scale and precision errors.

Reference: Independent control geometry and explicit workflow error budgets, never inherited prototype tolerances.

This run: **CONDITIONAL_WORKFLOW_PASSED**. test_complete_W06_extent_sweep_and_precision: passed

Open design/interpretation questions: Agree the offset basis and whether extent means authored vertices or a continuous surface. The run measures size/precision and compares affine with pointwise placement; no continuous bound is asserted.

Dependent decisions: S03, S04, S06

## W07: Same resolved scene for independent consumers

Do visualization, analytics and an independent runtime agree on one resolved scene?

Requirements: R16, One CRS out; R17, The same answer for every consumer; R18, Coordinates back out; R28, A result says what produced it; R29, Implementable from the text alone

Demonstration: Compare shared resolved positions through OpenUSD and OV, then a genuinely independent transformation engine, including operation provenance.

Reference: Provider controls and analytic cases establish correctness; implementation agreement establishes consistency only.

This run: **CONDITIONAL_WORKFLOW_PASSED**. test_complete_W07_native_storm_and_omniverse_fabric: passed

Open design/interpretation questions: Approve the shared consumer contract and independent-engine acceptance tolerance. Native Hydra/Storm, real Kit Fabric and independent Karney arithmetic execute.

Dependent decisions: S04, S06

## W08: Incorrect or unsupported inputs fail observably

Can a consumer explain why placement is unsafe instead of silently inventing a result?

Requirements: R1, Self-contained definitions; R3, Datum, realization and epoch; R11, Position or offset, and the scene says which; R12, No angle read as a length; R21, Never placed by a guess; R25, Additive for consumers that ignore it; R26, Declares its dependency; R27, Checkable before use; R28, A result says what produced it

Demonstration: Show malformed input, absent resources, ambiguous position/offset declarations and unaware consumers, alongside the smallest valid correction.

Reference: Current requirements and deliberately malformed fixtures; diagnostics identify the unsupported operation or missing decision.

This run: **CONDITIONAL_WORKFLOW_PASSED**. test_engine_reject_invalid_batch[bad0]: passed, test_engine_reject_invalid_batch[bad1]: passed, test_engine_reject_invalid_batch[bad2]: passed, test_engine_reject_invalid_batch[bad3]: passed, test_engine_reject_invalid_batch[bad4]: passed, test_engine_reject_codes_unsupported_and_empty: passed, test_engine_reject_unavailable_best_operation: passed, test_engine_reject_partial_result: passed, test_complete_W08_empty_binding_project_boundary_and_scope: passed, test_complete_W08_dynamic_epoch_and_missing_resources: passed, test_complete_W08_forwarding_and_time_export: passed

Open design/interpretation questions: Approve empty-binding, target-conflict and operation-selection policy. Negative cases reject bad scope, absent epoch, missing resources and forbidden fallbacks.

Dependent decisions: S01, S05, S06, S07
