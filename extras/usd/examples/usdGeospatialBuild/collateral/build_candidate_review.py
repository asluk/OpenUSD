"""Derive the README, then the review body and slide story, from one receipt."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
PREFIX='extras/usd/examples/usdGeospatialBuild/'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,text):path.write_bytes((text.rstrip()+'\n').encode('utf8'))
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+ '|'.join('---' for _ in headers)+'|\n'+''.join('| '+' | '.join(row)+' |\n' for row in rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-directory',required=True);run=Path(p.parse_args().run_directory)
    report=json.loads((run/'delivery/run-report.json').read_text())
    assert report['tests']['failed']==0 and report['source_files_unchanged']
    assert report['completion']['open_semantic_gap_ids']==['G03','G04','G06','G07']
    assert not report['completion']['proposal_ready'] and not report['completion']['requirements_build_complete']
    for name,value in report['source_files'].items():
        assert sha(ROOT/name)==value,'Executed source changed: '+name
        frozen=subprocess.check_output(['git','-C',str(ROOT),'show',report['source_commit']+':'+PREFIX+name])
        assert frozen.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),name
    destination=ROOT/'delivery';destination.mkdir(exist_ok=True)
    for file in (run/'delivery').iterdir():
        # Public text uses LF. The immutable private receipt retains exact bytes;
        # check JSON equality so this serialization change alters no evidence.
        target=destination/file.name
        target.write_bytes(file.read_bytes().replace(b'\r\n',b'\n'))
        assert json.loads(target.read_text())==json.loads(file.read_text())
    shutil.copytree(run/'scope-fixtures',destination/'scope-fixtures',dirs_exist_ok=True)
    shutil.copy2(run/'origin-sampling-record.usda',destination/'origin-sampling-record.usda')
    results=json.loads((destination/'scope-results.json').read_text())
    metrics=report['origin_metrics']; good=[m for m in metrics if m['successful_origins']]
    cases=len(report['scope_controls']);queries=report['scope_queries_per_reader'];checks=queries*3
    family=[]
    for key,label in [('discovery','Binding and composition'),('placement_values','Source placement values'),('origin_coordinates','Direct anchor-origin coordinates')]:
        rows=[row for row in report['scope_controls'] if row['kind']==key]
        family.append([label,str(len(rows)),str(sum(row['queries'] for row in rows)),str(sum(row['expected_failures'] for row in rows))])
    reference_rows=[[m['name'].replace('origins-','').replace('-to-',' to '),str(m['successful_origins']),f"{m['max_reference_discrepancy_metres']*1000:.4f}",f"{m['max_reader_agreement_metres']*1000:.4f}"] for m in good[:4]]
    source=json.loads((ROOT/'data/partner-controls.json').read_text())['France_01']['points'][0]
    resolved=[next(row for row in results[key] if row['name']=='origins-France_01-to-France_02')['queries'][0]['coordinates'] for key in ['headless','native_usd','live_ov']]
    coordinate_rows=[[label,f'{source[index]:.4f}',*[f'{value[index]:.4f}' for value in resolved]] for index,label in enumerate(['Easting','Northing','Height'])]
    chord=report['sampling_record_control']['endpoint_chord_midpoint_discrepancy_metres']
    candidate=report['inputs']['proposal'];freeze=report['source_commit']
    text=f'''# Geospatial: local candidate evidence and remaining contracts

The revised local proposal supplies concrete placement fields, WKT string normalization and result/sampling rules. **Four missing contracts still prevent a complete model-placement implementation.** All 31 functional requirements were reviewed. Candidate definitions remain proposals for author review, rather than claims of group adoption.

Fresh execution: **{report['tests']['passed']} tests passed**, with **{cases} cases and {queries} queries per reader** in headless OpenUSD, native OpenUSD and a live OV stage. The {checks} reader/query checks preserve source layers and fixture bytes. Direct anchor-origin projection is demonstrated. Full geometry placement, Hydra placement and resolved-scene export remain stopped by the missing contracts.

[Editable slides](delivery/geospatial-build.pptx) · [PDF](delivery/geospatial-build.pdf) · [Receipt](delivery/run-report.json) · [Proposal audit](QUALITY_REVIEW.md) · [Build loop](BUILD_LOOP.md)

## Concrete candidate answers

{table(['Subject','Proposed contract'],[
['Placement fields','Varying crs:position double3 has no fallback. crs:orientation quatd defaults to identity. crs:scale double3 defaults to (1,1,1). Explicit blocks remain unavailable.'],
['Coordinate components','Easting/northing/up, longitude/latitude/height, or geocentric XYZ. Use declared WKT units and height reference. Scene upAxis does not relabel the tuple.'],
['Orientation and scale','Model scale precedes orientation. Source bases are projected grid axes, geographic geodetic ENU or geocentric XYZ. The stage-axis adapter still needs specification.'],
['WKT string normalization','OGC preferred spelling and delimiters, preserved quoted content and node order, W3C exact canonical decimal/integer spelling. Token identity differs from CRS equivalence.'],
['Comparison and sampling','Separate operation accuracy, approximation error and reader agreement. Actual timeSamples and explicit timeCodesPerSecond record the sampling schedule.']])}
Reference-based binding, ordinary transforms after CRS placement, source preservation and writer-authored unit/up-axis conformance retain their existing direction. Coordinate epochs remain roadmap work. No private epoch, coordinate-role relationship or dependency flag is introduced.

## Four contracts still required

{table(['Contract','What remains unspecified'],[
['G03 / Q3: project-adjustment frame','Axes, units, pivot and controlling composed context for ordinary project adjustments, including nested bindings and output changes. Post-placement order is settled.'],
['G04 / Q6: stage and placement bases','Exact mapping between stage axes/distances, the proposed source placement bases and resolved result bases. Coordinate tuples do not supply that mapping.'],
['G06 / Q11: measurement association','Authored coordinate roles/domains for USD properties and external assets, including multiple domains and conflicting external CRS metadata.'],
['G07 / Q12: dependency declaration','Authored carrier and conservative assembly/export maintenance through references, unloaded payloads and composition, readable without traversal.']])}
Question 9 separately concerns geographic scene geometry, frames and bounds. Geographic coordinate queries already belong to initial scope. The candidate closes former field-definition, lexical-normalization, result-comparison, sampling-record and 2D-illustration gaps for this derivation. Adoption review is separate from derivability.

## WKT string normalization evidence

The {report['wkt_profile']['test_cases']} WKT tests use hand-specified lexical expectations. Padding, keyword case, preferred aliases, delimiters and exponent spelling converge. Quoted spaces, escaped quotes, metadata and frame epochs survive. The decimal **6378137.12345678912345** survives exactly. A PROJ writer round trip is a negative preservation control because it rounds that value.

Different CRS names remain different tokens even when an engine establishes equivalent coordinate meaning. Fixed-point validation rejects non-normalized authored text. Coordinate-epoch wrappers and unknown syntax fail explicitly. Context-dependent legacy UNIT aliases are unsupported, and one strict parser is not proof of all OGC grammar coverage. Normalization and complete scene validation are separate claims.

## Executed reader coverage

{table(['Control family','Cases per reader','Queries per reader','Expected failures'],family)}
Composition controls cover references, stronger layers, variants, class inheritance, equivalent composed data, independent binding and unavailable unloaded content. Source controls cover requiredness, blocks, types, variability, finite values, singular signed scale, defaults, held/linear interpolation and quaternion slerp. Longitude 179 to -179 interpolates to zero without invented unwrapping.

Origin controls accept only directly bound top-level anchors without ordinary adjustments or geometry offsets. They cover France projections, Colorado site calibration, source-first geographic-to-ECEF conversion and defaultPrim output selection. Nested/descendant frame requests and ordinary adjustments stop while dependent model contracts are missing. Invalid latitude and absent default output fail without a substitute.

{table(['Origin conversion','Origins','Max CSV discrepancy (mm)','Max reader difference (mm)'],reference_rows)}
Provider CSVs are PROJ-generated intake/rounding references, not survey truth. All readers use PROJ: native 9.4.1, headless and OV 9.8.1. Matching pipeline tokens are checked before comparing these results. Cases meet a predeclared 2 mm reference distance; analytic equatorial ECEF cases meet a separate 20 nm computational allowance. Neither threshold is geodetic accuracy. The geographic identity query is checked component-for-component in its declared units, without an angle-as-length metric.

## Same France origin in each runtime

France point 0 serves as an illustrative model-anchor origin. Source: RGF93 v2b / CC49 with NGF-IGN69 height. Output: Lambert-93 with the same height reference. Every displayed component is in metres.

{table(['Component','Source CC49','Headless USD','Native USD','Live OV'],coordinate_rows)}
All 59 origins are checked in both directions. Source values and definitions remain unchanged. This resolves coordinates only and supplies no measurement-coordinate carrier or Hydra/OV geometry ingestion. Unchanged height in this pair does not test a vertical-datum conversion.

## Source interpolation and the sampling record

A WGS84 anchor moves from longitude -1 degree to +1 degree on the equator at zero height. At time 5, Core linear source interpolation yields longitude zero before ECEF conversion. Each reader returns X = 6378137 m, Y = 0 m, Z = 0 m.

{table(['Time code','Source longitude (degrees)','Resolved ECEF X (m)'],[
['0','-1',f'{6378137-chord:.6f}'],['5','0','6378137.000000'],['10','1',f'{6378137-chord:.6f}']])}
Interpolating only the converted endpoints instead puts the midpoint **{chord:.6f} m** away. A standalone USD coordinate record writes sample keys 0, 5 and 10 with explicit timeCodesPerSecond = 48; a fresh reader verifies both. This is a sampling-record control, not a resolved-scene export or a guarantee between export samples.

## Postimplementation audit and delivery boundary

The audit tightened the partial origin adapter to reject nested/descendant frame requests rather than applying an incomplete model. It also corrected geographic identity reporting to use exact component comparison instead of a length metric. These repairs change consumer support/reporting, add no scene fact and do not amend the proposal to match code. Source fixtures author only crs:wkt and the three candidate placement fields. Resolution rewrites no source xformOps, resetXformStack, definitions, bindings or sampling keys.

Full model frames, project-adjusted placement, geometry and bounds, Hydra/OV resolved geometry, measurement-associated data and conservative resolved-scene export depend on the four missing contracts. These partial tests do not certify near-unit quaternion validation policy or geographic-distance controls. Group adoption and geodetic accuracy remain distinct from passing execution.

## Reproduction and provenance

Full candidate: [proposal-source.txt](proposal/proposal-source.txt), SHA-256 `{candidate['sha256']}`, based on `{candidate['base_commit']}`. [The local patch](proposal/local-draft.patch) identifies unpublished edits. Derived notes cite that snapshot and add no normative choices. Executed source: `{freeze}`.

Configure native/CMakeLists.txt against an OpenUSD SDK with PROJ, then run run.py with --output, --usd-sdk, --native-build, --native-python, --ov-sdk, --python-dependencies and --cmake from a Visual Studio developer environment on Windows. Use a fresh output directory. Python dependencies include pytest, pyproj and OpenUSD. The live OV reader loads its own USD bindings before the declared pyproj path. PROJ databases must be available; network lookup stays disabled for these controls.

Exit code 2 records passing controls with proposal readiness stopping full placement. A test, build or consumer failure produces no successful stopped receipt. Current delivery includes exact fixtures, independent returns and the receipt. Historical experiments remain historical evidence.
'''
    assert not re.search(r'https://github.com/[^\s)]+/(?:pull|issues)/\d+',text)
    write(ROOT/'README.md',text)
    sections={h:body.strip() for h,body in (s.split('\n',1) for s in text.split('\n## ')[1:])}
    headings=['Concrete candidate answers','Four contracts still required','WKT string normalization evidence','Executed reader coverage',
              'Same France origin in each runtime','Source interpolation and the sampling record','Postimplementation audit and delivery boundary']
    def slide(heading):
        body=sections[heading];blocks=body.split('\n\n');tables=[b for b in blocks if b.startswith('|')]
        vals=[] if not tables else [[c.strip() for c in line.strip('|').split('|')] for line in tables[0].splitlines() if not re.match(r'^\|[-|: ]+\|$',line)]
        return {'title':heading,'values':vals,'paragraphs':[b for b in blocks if not b.startswith('|')],'readme_section':heading}
    story={'title':text.splitlines()[0][2:],'readme_sha256':sha(ROOT/'README.md'),'run_receipt_sha256':sha(destination/'run-report.json'),
           'executed_source_commit':freeze,'slides':[{'title':'Geospatial proposal readiness','values':[],
           'paragraphs':['Four contracts still block complete model placement. The local candidate supplies concrete answers for five former gaps.',
                         f"{report['tests']['passed']} tests passed. {cases} cases and {queries} queries per reader, with source data unchanged.",
                         'Headless OpenUSD, native OpenUSD and live OV resolve direct anchor origins. Full model placement remains stopped.'],
           'readme_section':'Opening'}]+[slide(h) for h in headings]}
    write(destination/'story.json',json.dumps(story,indent=2))
    base='https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/'+PREFIX
    body=f'''The revised local geospatial proposal gives concrete placement and WKT string-normalization contracts. Four missing contracts still stop full model-placement derivation: project-adjustment frame, stage/basis mapping, measurement-coordinate association and dependency declaration. Candidate details remain under author review.

Fresh evidence: {report['tests']['passed']} tests and {checks} reader/query checks passed across headless OpenUSD, native OpenUSD and a live OV stage. Readers preserve source data and agree on France, Colorado and analytic ECEF anchor-origin conversions. The source-first interpolation example exposes a {chord:.3f} m error from interpolating only converted endpoints. Readers share PROJ, so this is no independent geodetic-engine certification.

Full model geometry, Hydra placement and resolved-scene export remain stopped. The README leads with proposal quality and separates proposed contracts, observed evidence and unresolved semantics.

[README]({base}README.md) · [Editable slides]({base}delivery/geospatial-build.pptx) · [PDF]({base}delivery/geospatial-build.pdf) · [Receipt]({base}delivery/run-report.json)

Candidate SHA-256: `{candidate['sha256']}`. Executed source: `{freeze}`. Proposal publication and group communications remain separate from fork delivery.
'''
    write(destination/'pr-body.md',body)
    print(json.dumps({'tests':report['tests']['passed'],'reader_checks':checks,'slides':len(story['slides']),'readme_sha256':story['readme_sha256']}))
if __name__=='__main__':main()
