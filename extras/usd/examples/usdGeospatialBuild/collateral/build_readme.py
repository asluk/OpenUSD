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
    assert report['tests']['failed'] == 0 and len(report['comparisons']) == 27
    shutil.copytree(run/'delivery', ROOT/'delivery', dirs_exist_ok=True)
    rows = report['comparisons']
    samples = sum(x['native']['samples'] for x in rows)
    native_max = max(x['native']['max_agreement_metres'] for x in rows)
    ov_max = max(x['ov']['max_agreement_metres'] for x in rows)
    comparisons = []
    for src, label in [('tower','Eiffel model + context'),('terrain','Colorado breaklines'),('railway','Original railway'),('city','Synthetic city imagery'),('climate','Global scalar grid'),('composition','Composition + time'),('instances','Native + point instances')]:
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
    text = f'''# Geospatial meaning that survives USD composition

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
    (ROOT/'README.md').write_text(text, encoding='utf8', newline='\n')
    print('README and executed delivery copied:', report['source_commit'])

if __name__=='__main__':
    main()
