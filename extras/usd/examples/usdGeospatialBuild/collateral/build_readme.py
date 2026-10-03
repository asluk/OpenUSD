"""Make the canonical narrative from a completed, source-bound run."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess

ROOT = Path(__file__).resolve().parents[1]

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-directory', required=True)
    args = parser.parse_args()
    run = Path(args.run_directory)
    report = json.loads((run/'delivery/run-report.json').read_text())
    for name, expected in report['source_files'].items():
        assert digest(ROOT/name) == expected, 'Source changed after execution: '+name
    assert report['tests']['failed'] == 0 and len(report['comparisons']) == 28
    shutil.copytree(run/'delivery', ROOT/'delivery', dirs_exist_ok=True)
    quality = report['proposal_quality']
    assert report['completion']['proposal_ready'] is False and report['completion']['requirements_build_complete'] is False
    assert digest(ROOT/'proposal-quality.json') == report['source_files']['proposal-quality.json']
    rows = report['comparisons']
    samples = sum(x['native']['samples'] for x in rows)
    native_max = max(x['native']['max_agreement_metres'] for x in rows)
    ov_max = max(x['ov']['max_agreement_metres'] for x in rows)
    comparisons = []
    for src, label in [('tower','Eiffel model + context'),('terrain','Colorado breaklines'),('railway','Original railway'),('city','Synthetic city imagery'),('climate','Global scalar grid'),('composition','Composition + time'),('instances','Native + point instances'),('default-output','Composed-default output')]:
        selected = [x for x in rows if x['source']==src]
        comparisons.append(f"| {label} | {len(selected)} | {selected[0]['native']['samples']:,} | {max(x['native']['max_agreement_metres'] for x in selected)*1000:.6f} | {max(x['ov']['max_agreement_metres'] for x in selected)*1000:.6f} |")
    selected = [x for x in rows if x['source'].startswith(('Colorado_', 'France_'))]
    comparisons.append(f"| Partner controls | {len(selected)} | 5 / 59 | {max(x['native']['max_agreement_metres'] for x in selected)*1000:.6f} | {max(x['ov']['max_agreement_metres'] for x in selected)*1000:.6f} |")
    compare_table = '\n'.join(comparisons)
    headless = json.loads((run/'headless-results.json').read_text())
    native = json.loads((run/'terrain-utm13-t0-native.json').read_text())
    live = next(x for x in json.loads((run/'ov-results.json').read_text())['jobs'] if x['name']=='terrain-utm13-t0')
    example = []
    for label, records in [('Headless USD',headless['terrain-utm13-t0']),('Native Hydra resolver',native),('Live OV resolver',live['records'])]:
        p = records['geometry']['/Terrain/Breaklines'][0]
        example.append(f"| {label} | {p[0]:.6f} | {p[1]:.6f} | {p[2]:.6f} |")
    controls = '\n'.join(f"| {x['source']} → {x['output']} | {x['controls']} | {x['max_csv_discrepancy_metres']*1000:.4f} |" for x in report['partner_controls'])
    extents = '\n'.join(f"| ±{x['half_extent_metres']:,.0f} m | {x['samples']} | {x['sampled_max_affine_discrepancy_metres']:.9g} m |" for x in report['extent_samples'])
    exports = '\n'.join(f"| {x['source']} | {x['output']} | {x['geometry_max_roundtrip_metres']*1e6:.2f} µm | {x['measurement_max_roundtrip_metres']*1e6:.2f} µm |" for x in report['exports'])
    credit = next(x for x in json.loads((ROOT/'data/manifest.json').read_text()) if x['path']=='data/tower.usdz')
    legacy = f'''# Geospatial meaning that survives USD composition

This complete experimental run derives fresh headless USD, native Hydra and live OV implementations from a frozen requirements-led model. It resolves the same authored datasets in all three, preserves source layers, produces analytic data and explicit exports, and exposes the remaining design decisions.

**Executed evidence:** {report['tests']['passed']} tests passed; 27 cross-runtime jobs compared {samples:,} coordinate samples; stock usdchecker discovered the validator and accepted/rejected the positive/negative scenes; five exports were opened and resolved by a fresh reader. Maximum native agreement discrepancy was {native_max*1000:.6f} mm; OV discrepancy was {ov_max*1000:.6f} mm. Agreement is not a geodetic accuracy claim.

[Editable slides](delivery/geospatial-build.pptx) · [PDF](delivery/geospatial-build.pdf) · [Run receipt](delivery/run-report.json) · [Reverse audit](AUDIT.md) · [Build contract](BUILD_LOOP.md)

The run source is `{report['source_commit']}`. Six [candidate documents](proposal/data-model.md) were frozen and hashed **before implementation**. Their exact fields, conventions and contracts remain experimental where the group has not agreed them. An executed candidate is not approval of a standard.

## The problem: numbers alone do not place an asset

A USD transform says how local geometry moves within a scene. It does not say which Earth reference defines a coordinate, which vertical datum defines its height, or how a site's calibrated grid relates to another project's coordinates.

Consider an ordinary point `(3,4,5)`, a child translate `(1,0,0)` and a model translate `(7,8,9)`. An unaware USD reader returns `(11,12,14)`. Add an explicit CRS position `(1000,2000,30)`, a 90° orientation and scale `(2,1,1)`: the candidate geospatial reader returns `(1003,2016,44)`. Swapping the order or resolving only the origin gives a different answer. The test is hand-worked and noncommuting; it does not copy an implementation's answer into the requirement.

The authored point, ordinary transforms and CRS facts stay intact. Consumers can inspect the source CRS and separately request resolved coordinates. Another output CRS must change the expression of the same physical placement, not quietly reinterpret ordinary adjustment numbers in a new set of axes.

## Three authored facts, followed by ordinary transforms

A complete WKT definition identifies the coordinate reference system. A binding identifies which definition applies. Separate position, orientation and scale place a model; ordinary USD transforms apply after geospatial placement and resolution.

| Authored fact | Experimental representation | Meaning |
|---|---|---|
| Complete CRS definition | `CoordinateReferenceSystem`, uniform token `crs:wkt` | Whole CRS WKT2 is authoritative; no duplicate datum, unit, projection or calibration fields. |
| Source association | `rel crs:binding` | Nearest direct binding wins for source coordinates; independently bound assets retain their source definition. |
| Model placement | `double3 crs:position`, `quatd crs:orientation`, `double3 crs:scale` | Absolute origin plus full oriented/scaled local frame; geometry remains ordinary local USD lengths. |
| Measurement coordinates | `rel crs:coordinateProperties` targets `double3[]` properties | Identify coordinate arrays explicitly; values, indices and recorded times remain dataset data. |
| Complete-asset dependency | root `customLayerData.geospatialResolutionRequired` | Writer-maintained declaration readable without discovering it through traversal. |

The relationship fields live in a codeless applied schema. This experiment does not propose callable API signatures as standard text. A directly bound model excludes its ancestors' ordinary xformOps; it does not author or alter `resetXformStack`. Its own ordinary matrix and descendant matrices remain ordinary USD data.

Projected tuples use easting/northing/up; geographic tuples use longitude/latitude/height; geocentric tuples use XYZ. CRS component units remain authoritative. Writers conform geometry to stage units and up-axis separately from CRS placement. The candidate specifies the working context used to transport post transforms between requested outputs; a labeled alternative that keeps post numbers unchanged in output axes fails the physical-placement control.

[Data model](proposal/data-model.md), [runtime behavior](proposal/runtime-behavior.md), [distinguishing examples](proposal/distinguishing-examples.md) and [requirement trace](proposal/traceability.md) are the normative description **of this experiment**, not implementation notes retrofitted into the proposal.

## Eiffel: see the placement and its coordinate context

The Eiffel model is placed at Lambert-93 E 648,237.125 m, N 6,862,251.890 m and IGN69 height 33.79 m, with a 45° CRS orientation. The same authored model resolves into Lambert-93, two UTM zones and ECEF.

![Native Hydra/Storm Eiffel render](delivery/tower-native.png)

![Resolved coordinate footprint and controls](delivery/tower-plan.png)

The first image is an actual native Hydra/Storm draw from the early candidate scene-index override, before instance propagation and flattening. The second is a headless query plot in named coordinate axes. Ground and cardinal controls are illustrative, not a surveyed Paris dataset. Both images are needed: appearance alone is insufficient evidence of correct placement.

The original model's erroneous `metersPerUnit=0.01` metadata remains untouched. Its known metre geometry and Y-up convention are handled by the writer's assembly corrective. Reader code does not infer correct units from the shape of a familiar building. Model credit: {credit.get('attribution')}; {credit.get('licence')}; [original source]({credit.get('url')}).

## Colorado and France: complete CRS definitions do real work

The partner data exercise geographic, projected, compound height and derived site-calibration definitions. Colorado keeps US survey feet and its full horizontal/vertical site calibration in WKT; France keeps Lambert-93/CC49 and IGN69 height meaning.

![Colorado original breaklines in native Hydra](delivery/terrain-native.png)

![Calibrated Colorado query plot](delivery/colorado-terrain.png)

The LandXML contains 14,359 vertices in 710 coordinate parts. It is displayed as original breaklines, without inventing a terrain TIN. Source N/E/H order is explicitly mapped to E/N/H, with metre local geometry and a double coordinate anchor. Five Colorado and 59 France controls are checked in their supplied reference systems.

| Supplied control comparison | Points | Maximum CSV discrepancy (mm) |
|---|---:|---:|
{controls}

The supplied CSVs were computed with PROJ 9.8.1. These comparisons test intake, association and rounding, not independent-engine or survey accuracy. Required height grids are [identified and hash-verified](delivery/resources.json); missing resources reject the whole result. Ordinary datum/height operations are exercised without adding USD properties for engine-selected grids.

## The same authored data reaches three consumers

Headless USD queries, the native C++ Hydra resolver and the separate live OV resolver agree across all 27 jobs. Each derives placements from the authored scene; neither runtime consumes a headless result snapshot.

| Dataset | Jobs | Samples per job | Native vs headless max (mm) | OV vs headless max (mm) |
|---|---:|---:|---:|---:|
{compare_table}

Partner controls account for seven of the 27 jobs. Sample counts include repeated output selections; they are not counts of distinct real-world observations. Full arrays, source-property associations, target definitions and engine-reported operations accompany the receipt in compressed coordinate artifacts.

For example, the **same first Colorado breakline vertex**, resolved into NAD83 / UTM zone 13N with ellipsoidal height, is:

| Implementation | Easting (m) | Northing (m) | Height (m) |
|---|---:|---:|---:|
{chr(10).join(example)}

Native rendering additionally checks the final scene-index geometry matrices and actual instancer transforms. Live OV reads geometry ingested into its runtime, writes derived placement/coordinate results there and reads them back. It exercises source edits, changed time/output requests, invalid-result removal and recovery. No OV screenshot or OV visual-render parity is claimed.

Runtime independence and geodetic-engine independence are different. All three use PROJ: native {rows[0]['native_proj_version']}, Python/OV {report['toolchain']['pyproj_proj']}. USD versions are headless {'.'.join(map(str,report['toolchain']['headless_usd'][1:]))}, native {'.'.join(map(str,report['toolchain']['native_usd'][1:]))}, OV {'.'.join(map(str,report['toolchain']['ov_usd'][1:]))}. Stock core source, native binary hashes and loaded-plugin exclusions are recorded; no retired geospatial runtime is used.

## City analysis returns data, not just a picture

A 64 × 64 synthetic red/NIR image yields 1,850 samples above NDVI 0.3. The result returns locations in the requested CRS while preserving source indices, values and observation times.

![City measurement analysis and requested coordinate results](delivery/city-analysis.png)

[Selected GeoJSON features](delivery/city-selected-features.geojson) and [the paired analysis product](delivery/city-analysis-product.json) are usable without a renderer. The heatmap is a scientific headless-query visualization. Its bands, observation time and 80 m ellipsoidal sample height are explicit synthetic inputs; it makes no real land-use claim.

The [original railway query](delivery/railway-query.png) carries all 15,822 vertices and 2,386 coordinate parts from the supplied GeoJSON into UTM, geographic and ECEF results. Its third coordinate is conditionally interpreted as WGS84 ellipsoidal height because the original EPSG:4326 label alone does not specify a height reference. Original topology and source coordinates remain available.

## Global measurements keep coordinates, values and time together

The original 37 × 72 scalar grid resolves all 2,664 locations globally in ECEF and geographic coordinates. Values remain associated with their coordinates and grid indices across two recorded times.

![Global coordinate coverage](delivery/global-ecef.png)

![Original values and explicitly synthetic change](delivery/climate-analysis.png)

The initial scalar field comes from the supplied NetCDF; its units and heights are not authored in that file. Positions use explicitly assumed zero ellipsoidal height. The second time is an explicitly synthetic perturbation, not an observed trend or forecast. [The analytic product](delivery/climate-analysis-product.json) preserves both value arrays with the same coordinate indices. These are scientific query plots, not Hydra renders and not one global tangent plane.

This exercises useful larger-scale data workflows alongside construction-site placement. Initial scope does not impose a site-sized domain on measurements or make later coordinate-epoch support impossible.

## Composition, edits and explicit export survive real consumption

Three USD native instances and three point instances share geometry while receiving distinct resolved placements. References, stronger opinions, variants, source interpolation, stage units and Y/Z up-axis are exercised with independent controls.

![Three native and three point instances consumed by Hydra](delivery/instances-native.png)

The native scene index recomputes on source notices; the rendered model's +10 m position edit is checked and restored. Live OV updates after authored edits and request changes; a broken definition reports failure, hides stale model results, clears stale measurement results, then recovers after restoration. The source's complete used-layer set matches its original contents after each test. Snapshot parity and filter-call counts alone are not accepted as consumption evidence.

Source position interpolation occurs **before** nonlinear CRS conversion. A hand-reasoned test distinguishes this from interpolating already-projected endpoints. Ordinary USD consumers continue to see exactly the original ordinary transform interpretation.

Five derived assets are written with the requested output WKT and explicit sample times 0, 5 and 10. They bake post transforms once, retain small local float geometry with double anchors, preserve measurement values/times and are resolved by a fresh reader. There is no private “already resolved” flag.

| Exported dataset | Output | Geometry roundtrip max | Measurement roundtrip max |
|---|---|---:|---:|
{exports}

These are sampled exports, with their interpolation policy recorded; arbitrary continuous-time equivalence is not implied. The stock validator checks authored facts, rather than certifying geodetic accuracy or discovering hidden unloaded dependencies.

## Precision is measured; a continuous extent bound remains open

Double coordinate anchors and small local floats preserve detail away from the origin. But one affine model frame approximates a nonlinear transformation, and the error grows with the model's spatial extent.

For a UTM frame projected into ECEF, 289 sampled points per square give:

| Sampled domain half-extent | Samples | Maximum affine discrepancy |
|---|---:|---:|
{extents}

At an absolute float coordinate around 481,948 m, one float step is 31.25 mm. Keeping a double anchor and small float geometry avoids that source of quantization. The frame uses a 1 m physical derivative probe; 0.25 m and 4 m probes are compared in tests. Probe stability and finite sample maxima are **not a certified continuous surface bound**.

R24 therefore remains a substantive design gap: the proposal needs a contract for extent, approximation/error reporting and when subdivision or another representation is required. All selected demonstrations ran; this question is not a deferred implementation task. Engine-attributed operation accuracy estimates also do not include ordinary post transforms, affine approximation or survey truth.

## Remaining decisions and the path forward

The executed candidate provides reviewable answers for exact placement fields, adjustment context, geographic/geocentric tuples, WKT string normalization, measurement association, dependency declarations and sampled export records. The group still needs to choose those contracts and settle the continuous extent/error requirement.

[The decision table](proposal/runtime-open-decisions.md) separates already retained answers from experimental choices and genuine gaps. WKT **string** normalization is lexical: it preserves quoted metadata, component order, identifiers, remarks and extensions, and does not claim semantic CRS equivalence. Tokens must already match that normal form. Different metadata can still produce different tokens for equivalent numerical operations.

Coordinate epochs are deferred in representation, interpretation and computation. `COORDINATEMETADATA` wrappers and requests that need time-dependent transformations fail explicitly. CRS `FRAMEEPOCH` information remains in WKT; it is not a coordinate epoch. No synthetic epoch attribute or default is introduced, and the separation of CRS definitions, source associations and recorded dataset times preserves the ability to add an authoritative epoch model later.

The reverse audit checks both directions: implementation facts/behavior must follow the frozen text, and that text must follow requirements and established data ownership rather than justify runtime conveniences. Corrections during this run fixed consumer integration and test-asset structure without adding new authored fields to rescue the implementation.

## Reproduce and inspect

The [build contract](BUILD_LOOP.md) describes the required stages. `run.py --help` lists dependency locations; execute it from a compiler-enabled environment with the recorded stock USD imaging SDK, Python dependencies, OV runtime, PROJ database and TIFF-enabled PROJ native library. Height grids are fetched separately from the recorded resource URLs, then verified by hash; network fallback is disabled during the run.

```text
cmake -S native -B <native-build> -G Ninja -DCMAKE_BUILD_TYPE=Release
      -DUSD_SDK=<usd-sdk> -Dpxr_DIR=<usd-sdk> -DCMAKE_PREFIX_PATH=<usd-sdk>
python -X utf8 run.py --grids <grid-directory> --usd-sdk <usd-sdk>
      --native-build <native-build> --native-proj <tiff-enabled-proj-install>
      --native-python <linked-python-dll-directory> --ov-sdk <ov-runtime>
      --python-dependencies <python-site-packages> --output <fresh-run-directory>
python collateral/build_readme.py --run-directory <fresh-run-directory>
python collateral/derive.py
```

The included original data, generated schema and authored stages allow a rerun without private attachment ZIPs. `intake.py` records the original attachment-to-stage authoring recipe. [Dataset sources, credits and assumptions](data/README.md), [original hashes](data/manifest.json), [frozen requirements](proposal/requirements.md) and [the immutable run receipt](delivery/run-report.json) accompany the implementation. README is the canonical narrative; `collateral/derive.py` derives the PR body and slide content from it, with the README hash recorded in collateral.
'''
    sections = legacy.split('## ')
    retained = {x.split('\n',1)[0]:x.split('\n',1)[1] for x in sections[1:]}
    sample_count = sum(x['native']['samples'] for x in rows)
    bounds = sum(x['native']['affine_leaf_bounds_compared'] for x in rows)
    relative = sum(x['native']['relative_frames_compared'] for x in rows)
    labels = [('G01','Binding carrier and contradictory legacy text'),('G02','Placement types, bases, defaults and frame meaning'),('G03','Working context and adjusted measurement placement'),('G04','Axis conventions and supported result domains'),('G05','OGC-grounded WKT string normal form'),('G06','Measurement property association and adapters'),('G07','Complete-asset declaration and assembly obligations'),('G08','Extent/error guarantee and comparable operations'),('G09','Structured export sampling and preservation coverage'),('G10','2D/3D coordinate meaning and height-frame support')]
    gap_rows = '\n'.join(f"| {i} | {label} | {', '.join(str(x) for x in next(g for g in quality['semantic_gaps'] if g['id']==i)['requirements'])} |" for i,label in labels)
    prefix=f'''# Geospatial proposal readiness and experimental evidence

**The proposal is not yet independently implementable.** This loop audits all 31 functional requirements and identifies ten open categories in the data model and normative runtime behavior. Most intended outcomes are already required; their missing representation, conventions and guarantees cannot be supplied by prototype choices. Proposal readiness and requirements-build completion both remain **false**.

[Proposal quality review](QUALITY_REVIEW.md) · [Editable slides](delivery/geospatial-build.pptx) · [PDF](delivery/geospatial-build.pdf) · [Run receipt](delivery/run-report.json) · [Implementation audit](AUDIT.md) · [Build gate](BUILD_LOOP.md)

The audit and corrective experimental delivery are complete. This is not a claim that the proposal-conformance build passed. The explicitly authorized experiment executed {report['tests']['passed']} tests, {len(rows)} three-consumer jobs and {len(report['exports'])} fresh-reader exports. It cannot close a shared semantic decision. Source `{report['source_commit']}` and every executed input are hash-bound to the receipt.

## Contracts still missing from the proposal

The agreed outcomes remain useful: complete WKT CRS definitions, separate model placement, ordinary USD transforms after resolution, preserved source data and both rendering and coordinate queries. The following contracts must be completed against those outcomes rather than copied from a convenient implementation.

| Gap | Shared contract to settle | Existing requirement numbers |
|---|---|---|
{gap_rows}

[The review](QUALITY_REVIEW.md) maps every requirement to executed evidence and its remaining gaps, with proposed closure for each. These are review categories, not ten new functional requirements or a proof that no further gap exists. The candidate remains an explicit experiment; freezing its choices before code never made them shared proposal authority.

## Why implementation did not stop

I substituted the frozen experimental candidate for shared-proposal authority and audited code against that candidate more thoroughly than the candidate against the actual proposal. Selecting only the requirements hid conflicting retained translate/reset/API sketches instead of reconciling the whole text.

I also failed to make known gaps block completion. The earlier audit recorded the R24 extent/error gap, but the README opened with a complete experimental run and the slides led with a render. Self-selected tests omitted bounds, relative frames and default-output behavior, and fixture-named export checks missed dropped properties. Permission to explore labeled alternatives did not authorize treating those choices as settled semantics. This was my process failure; it did not reflect missing cooperation from the group.

- Cite exact proposal authority for each required authored fact, default, scope, ordering, time rule, failure and acceptance criterion.
- When that authority is missing or conflicting, stop the dependent derivation and flag the affected requirement immediately.
- Continue independent work or authorized labeled experiments; keep their assumptions separate from proposal conformance.
- Review specification repairs from requirements and data ownership, freeze new semantics before code, and invalidate affected evidence.
- Keep missing tests classified as unfinished verification. Passing tests cannot approve model choices.

The default runner now stops before dependent execution while semantic gaps remain. An explicit experimental invocation records `proposal_ready=false` and `requirements_build_complete=false`; there is no successful-run override that changes those conclusions.

## Repairs and checks that did not require a new shared decision

A separate local proposal draft removes obsolete callable signatures, translate-based CRS placement, the helper that authored resetXformStack and rendering architecture prescriptions. It preserves the recorded separate-placement and post-transform direction and leaves the exact binding/field contract open. That proposal cleanup is committed locally, **not pushed or agreed**; its revision is recorded in the quality receipt.

Existing failure/source-preservation requirements justify rejecting a broken enclosing binding instead of treating it as absent, validating inherited coordinate roles, retaining arbitrary ordinary dataset property names/metadata/relationships, and avoiding duplicated output WKT in export metadata. The experiment also tests composed-default output precedence, affine leaf bounds including curve widths, relative model frames and standard USD instance export. Where a new experimental representation was necessary, it was specified and committed before affected code; it remains unapproved.

WKT **string** normalization now covers structural parentheses as well as square brackets while preserving quoted punctuation. OGC permits the former and prefers the latter; the installed projection engine rejects the parenthesis spelling directly. Parser capability therefore cannot define all OGC-valid text. The full lexical normalization profile remains G05, and lexical token identity is not semantic CRS equivalence. [OGC 18-010r11, clauses 6.3.4 and 6.4](https://docs.ogc.org/is/18-010r11/18-010r11.pdf).

## A newly exposed dependency: placed measurement data

Absolute sample coordinates and a model's local geometry are different kinds of data. The proposal does not yet fully define how model placement and ordinary project adjustments affect arrays of absolute measurement coordinates, including the working frame and pivot when a geographic context is involved.

The city/global fixtures used unadjusted datasets. Converting those arrays demonstrates coordinate queries and preserves values/indices/times, but does not demonstrate adjusted imagery under requirements 8 and 17. I stopped that dependent derivation and recorded it in G03/G06; no centroid, hidden origin, extra flag or new placement field was introduced to rescue it.

A related distinction is CRS definition validity versus the support needed for a requested result. A valid 2D definition does not supply physical height; geographic gravity-related height cannot silently become ellipsoidal Cartesian height. The three-component candidate does not establish universal 2D/compound-height model support. G10 requires result-specific information and failure semantics, not a schema restriction copied from vector3 code.

## Extent and error remain a proposal gate

Double anchors avoid absolute-coordinate float quantization, but an affine model frame approximates nonlinear per-point conversion. Requirement 24 calls for a stated placement error over a stated extent; the proposal has not yet supplied a complete contract for establishing that guarantee, its coverage or failure/subdivision behavior.

For a UTM model frame converted to ECEF, the experiment measures 289 points per square:

| Sampled domain half-extent | Samples | Maximum affine discrepancy |
|---|---:|---:|
{extents}

These are finite sampled discrepancies, not a bound on every point or surface in the extent. The ±100 km sample is about 1.57 km from the per-point result. Probe stability and small cross-runtime differences do not close the guarantee. Engine-attributed operation accuracy also excludes affine approximation, ordinary post transforms and survey truth; complete-chain reporting remains G08.

The added affine leaf-bounds controls use stock UsdGeom local extent, including curve widths, transformed by the same derived frame. They do not bound nonlinear per-point conversion or establish universal primitive, aggregate, angular or physics bounds.

## The same authored data reaches three consumers

The corrective experiment compares headless OpenUSD queries, an independent native Hydra resolver and an independent live OV resolver on the same authored data. It records {sample_count:,} positional samples across {len(rows)} jobs, {bounds:,} affine leaf-bound comparisons and {relative:,} relative-frame comparisons. Maximum native discrepancy is {native_max*1000:.6f} mm and maximum OV discrepancy is {ov_max*1000:.6f} mm.

| Same first Colorado breakline vertex | Easting (m) | Northing (m) | Height (m) |
|---|---:|---:|---:|
{chr(10).join(example)}

All three consumers use PROJ, and the supplied partner CSVs also use PROJ. This is independent authored-scene/runtime agreement, not independent geodetic-engine accuracy. Actual final Hydra matrices, instance transforms and extents are read back; live OV checks ingested geometry, widths, runtime matrices and coordinate results. No OV visual-render parity is claimed.

| Dataset | Jobs | First-job samples | Native max (mm) | OV max (mm) |
|---|---:|---:|---:|---:|
{compare_table}

Full arrays, source-property associations, operation reports, resource hashes and USD/PROJ versions accompany the receipt. Counts include repeated output selections, not distinct real-world observations.

'''
    sections_to_keep=['Eiffel: see the placement and its coordinate context','Colorado and France: complete CRS definitions do real work','City analysis returns data, not just a picture','Global measurements keep coordinates, values and time together']
    text=prefix+'\n'.join('## '+name+'\n'+retained[name] for name in sections_to_keep)
    text+=f'''## Composition, edits and sampled export

Three native USD instances and three point instances share ordinary geometry while resolving distinct placements. References, stronger opinions, variants, source interpolation, stage units/up-axis and explicit/default outputs have distinguishing controls. Native source notices and live OV source/request edits invalidate results; broken definitions remove stale successful results and recovery is exercised.

![Native and point instances consumed by Hydra](delivery/instances-native.png)

{len(report['exports'])} derived assets are reopened and resolved at explicit times 0, 5 and 10. Export preserves composed ordinary USD content, including standard instance data and arbitrary ordinary measurement properties/metadata/relationships; output placement and absolute coordinate arrays are sampled. The output CRS is recorded only in a typed definition and its bindings. No private resolved flag prevents double application. This is an experimental export representation, not an approved standard encoding.

| Exported dataset | Output | Geometry roundtrip max | Measurement roundtrip max |
|---|---|---:|---:|
{exports}

Fresh-reader instance-position checks are included. Equivalence to the original source-CRS trajectory between sample times is explicitly not promised. Generic external dataset adapter coverage and a shared structured sampling record remain G06/G09; they are not proved by these on-prim fixtures.

## What must be settled before proposal conformance

The next shared revision must reconcile the binding and placement model, define adjusted measurement/frame semantics and result support, prescribe WKT string normalization, and complete dependency, export and extent/operation guarantees. Every repair must cite existing requirements and USD/OGC semantics before affected implementation is rederived. Candidate choices and test success cannot settle those decisions.

Coordinate epochs remain deferred in representation, interpretation and computation. CRS frame epochs remain in WKT, and supported non-epoch datum/height operations use engine-managed resources. Large city/global coordinate datasets remain useful initial scope; the construction examples do not impose a site-sized domain. No deferred capability is made impossible by a hidden surrogate field.

The full requirement/gap map and why-stop investigation are in QUALITY_REVIEW.md. The run delivers auditable evidence and current collateral while honestly failing the proposal-readiness gate.

## Reproduce and inspect

The default runner stops on open semantic gaps. An explicitly authorized experiment adds `--experiment-with-open-specifications` to `run.py`; its receipt still records proposal readiness and requirements-build completion as false. Use a fresh output directory with the recorded stock USD imaging SDK, Python dependencies, OV runtime, PROJ database and TIFF-enabled native library. Required resources are hash-verified and network fallbacks disabled.

`collateral/build_readme.py --run-directory <run>` generates this canonical narrative from the source-bound receipt and quality audit. `collateral/derive.py` derives the PR body and slide content; the editable deck and PDF are rendered and inspected before delivery. No private email, original attachment ZIP or upstream issue/PR backlink accompanies delivery.

[Build contract](BUILD_LOOP.md), [datasets/credits/assumptions](data/README.md), [original hashes](data/manifest.json), [pinned requirements](proposal/requirements.md), [experimental data model](proposal/data-model.md), [experimental runtime behavior](proposal/runtime-behavior.md) and [immutable receipt](delivery/run-report.json) accompany the evidence.
'''
    (ROOT/'README.md').write_text(text, encoding='utf8', newline='\n')
    print('README and executed delivery copied:', report['source_commit'])

if __name__=='__main__':
    main()
