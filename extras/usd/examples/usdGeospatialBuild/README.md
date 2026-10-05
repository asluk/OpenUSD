# Geospatial: local candidate evidence and remaining contracts

The revised local proposal supplies concrete placement fields, WKT string normalization and result/sampling rules. **Four missing contracts still prevent a complete model-placement implementation.** All 31 functional requirements were reviewed. Candidate definitions remain proposals for author review, rather than claims of group adoption.

Fresh execution: **64 tests passed**, with **37 cases and 168 queries per reader** in headless OpenUSD, native OpenUSD and a live OV stage. The 504 reader/query checks preserve source layers and fixture bytes. Direct anchor-origin projection is demonstrated. Full geometry placement, Hydra placement and resolved-scene export remain stopped by the missing contracts.

[Editable slides](delivery/geospatial-build.pptx) · [PDF](delivery/geospatial-build.pdf) · [Receipt](delivery/run-report.json) · [Proposal audit](QUALITY_REVIEW.md) · [Build loop](BUILD_LOOP.md)

## Concrete candidate answers

| Subject | Proposed contract |
|---|---|
| Placement fields | Varying crs:position double3 has no fallback. crs:orientation quatd defaults to identity. crs:scale double3 defaults to (1,1,1). Explicit blocks remain unavailable. |
| Coordinate components | Easting/northing/up, longitude/latitude/height, or geocentric XYZ. Use declared WKT units and height reference. Scene upAxis does not relabel the tuple. |
| Orientation and scale | Model scale precedes orientation. Source bases are projected grid axes, geographic geodetic ENU or geocentric XYZ. The stage-axis adapter still needs specification. |
| WKT string normalization | OGC preferred spelling and delimiters, preserved quoted content and node order, W3C exact canonical decimal/integer spelling. Token identity differs from CRS equivalence. |
| Comparison and sampling | Separate operation accuracy, approximation error and reader agreement. Actual timeSamples and explicit timeCodesPerSecond record the sampling schedule. |

Reference-based binding, ordinary transforms after CRS placement, source preservation and writer-authored unit/up-axis conformance retain their existing direction. Coordinate epochs remain roadmap work. No private epoch, coordinate-role relationship or dependency flag is introduced.

## Four contracts still required

| Contract | What remains unspecified |
|---|---|
| G03 / Q3: project-adjustment frame | Axes, units, pivot and controlling composed context for ordinary project adjustments, including nested bindings and output changes. Post-placement order is settled. |
| G04 / Q6: stage and placement bases | Exact mapping between stage axes/distances, the proposed source placement bases and resolved result bases. Coordinate tuples do not supply that mapping. |
| G06 / Q11: measurement association | Authored coordinate roles/domains for USD properties and external assets, including multiple domains and conflicting external CRS metadata. |
| G07 / Q12: dependency declaration | Authored carrier and conservative assembly/export maintenance through references, unloaded payloads and composition, readable without traversal. |

Question 9 separately concerns geographic scene geometry, frames and bounds. Geographic coordinate queries already belong to initial scope. The candidate closes former field-definition, lexical-normalization, result-comparison, sampling-record and 2D-illustration gaps for this derivation. Adoption review is separate from derivability.

## WKT string normalization evidence

The 24 WKT tests use hand-specified lexical expectations. Padding, keyword case, preferred aliases, delimiters and exponent spelling converge. Quoted spaces, escaped quotes, metadata and frame epochs survive. The decimal **6378137.12345678912345** survives exactly. A PROJ writer round trip is a negative preservation control because it rounds that value.

Different CRS names remain different tokens even when an engine establishes equivalent coordinate meaning. Fixed-point validation rejects non-normalized authored text. Coordinate-epoch wrappers and unknown syntax fail explicitly. Context-dependent legacy UNIT aliases are unsupported, and one strict parser is not proof of all OGC grammar coverage. Normalization and complete scene validation are separate claims.

## Executed reader coverage

| Control family | Cases per reader | Queries per reader | Expected failures |
|---|---|---|---|
| Binding and composition | 12 | 19 | 6 |
| Source placement values | 12 | 12 | 6 |
| Direct anchor-origin coordinates | 13 | 137 | 5 |

Composition controls cover references, stronger layers, variants, class inheritance, equivalent composed data, independent binding and unavailable unloaded content. Source controls cover requiredness, blocks, types, variability, finite values, singular signed scale, defaults, held/linear interpolation and quaternion slerp. Longitude 179 to -179 interpolates to zero without invented unwrapping.

Origin controls accept only directly bound top-level anchors without ordinary adjustments or geometry offsets. They cover France projections, Colorado site calibration, source-first geographic-to-ECEF conversion and defaultPrim output selection. Nested/descendant frame requests and ordinary adjustments stop while dependent model contracts are missing. Invalid latitude and absent default output fail without a substitute.

| Origin conversion | Origins | Max CSV discrepancy (mm) | Max reader difference (mm) |
|---|---|---|---|
| France_01 to France_02 | 59 | 0.0608 | 0.0000 |
| France_02 to France_01 | 59 | 0.0608 | 0.0000 |
| Colorado_02 to Colorado_03 | 5 | 0.0342 | 0.0000 |
| Colorado_03 to Colorado_02 | 5 | 0.0342 | 0.0000 |

Provider CSVs are PROJ-generated intake/rounding references, not survey truth. All readers use PROJ: native 9.4.1, headless and OV 9.8.1. Matching pipeline tokens are checked before comparing these results. Cases meet a predeclared 2 mm reference distance; analytic equatorial ECEF cases meet a separate 20 nm computational allowance. Neither threshold is geodetic accuracy. The geographic identity query is checked component-for-component in its declared units, without an angle-as-length metric.

## Same France origin in each runtime

France point 0 serves as an illustrative model-anchor origin. Source: RGF93 v2b / CC49 with NGF-IGN69 height. Output: Lambert-93 with the same height reference. Every displayed component is in metres.

| Component | Source CC49 | Headless USD | Native USD | Live OV |
|---|---|---|---|---|
| Easting | 1661099.0390 | 661101.1094 | 661101.1094 | 661101.1094 |
| Northing | 8180053.1170 | 6857834.2565 | 6857834.2565 | 6857834.2565 |
| Height | 37.2980 | 37.2980 | 37.2980 | 37.2980 |

All 59 origins are checked in both directions. Source values and definitions remain unchanged. This resolves coordinates only and supplies no measurement-coordinate carrier or Hydra/OV geometry ingestion. Unchanged height in this pair does not test a vertical-datum conversion.

## Source interpolation and the sampling record

A WGS84 anchor moves from longitude -1 degree to +1 degree on the equator at zero height. At time 5, Core linear source interpolation yields longitude zero before ECEF conversion. Each reader returns X = 6378137 m, Y = 0 m, Z = 0 m.

| Time code | Source longitude (degrees) | Resolved ECEF X (m) |
|---|---|---|
| 0 | -1 | 6377165.578842 |
| 5 | 0 | 6378137.000000 |
| 10 | 1 | 6377165.578842 |

Interpolating only the converted endpoints instead puts the midpoint **971.421158 m** away. A standalone USD coordinate record writes sample keys 0, 5 and 10 with explicit timeCodesPerSecond = 48; a fresh reader verifies both. This is a sampling-record control, not a resolved-scene export or a guarantee between export samples.

## Postimplementation audit and delivery boundary

The audit tightened the partial origin adapter to reject nested/descendant frame requests rather than applying an incomplete model. It also corrected geographic identity reporting to use exact component comparison instead of a length metric. These repairs change consumer support/reporting, add no scene fact and do not amend the proposal to match code. Source fixtures author only crs:wkt and the three candidate placement fields. Resolution rewrites no source xformOps, resetXformStack, definitions, bindings or sampling keys.

Full model frames, project-adjusted placement, geometry and bounds, Hydra/OV resolved geometry, measurement-associated data and conservative resolved-scene export depend on the four missing contracts. These partial tests do not certify near-unit quaternion validation policy or geographic-distance controls. Group adoption and geodetic accuracy remain distinct from passing execution.

## Reproduction and provenance

Full candidate: [proposal-source.txt](proposal/proposal-source.txt), SHA-256 `a5444966c41e3a067d7c4db5b2e9a300a08b17fcce377bd6fb24727b390e6904`, based on `39c8fb816a9113b14c8f64b020270724b8357312`. [The local patch](proposal/local-draft.patch) identifies unpublished edits. Derived notes cite that snapshot and add no normative choices. Executed source: `6d8323764ad44953887cac9781375b7c7176e928`.

Configure native/CMakeLists.txt against an OpenUSD SDK with PROJ, then run run.py with --output, --usd-sdk, --native-build, --native-python, --ov-sdk, --python-dependencies and --cmake from a Visual Studio developer environment on Windows. Use a fresh output directory. Python dependencies include pytest, pyproj and OpenUSD. The live OV reader loads its own USD bindings before the declared pyproj path. PROJ databases must be available; network lookup stays disabled for these controls.

Exit code 2 records passing controls with proposal readiness stopping full placement. A test, build or consumer failure produces no successful stopped receipt. Current delivery includes exact fixtures, independent returns and the receipt. Historical experiments remain historical evidence.
