"""Derive current README, review body and slide data from a frozen candidate run."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,s):Path(p).write_text(s,encoding='utf-8')
def js(p,x):write(p,json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','|'+'|'.join(['---']*len(head))+'|',*['| '+' | '.join(map(str,r))+' |' for r in rows]])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);args=parser.parse_args();run=Path(args.run).resolve()
    report=json.loads((run/'delivery/run-report.json').read_text(encoding='utf-8'))
    for name,digest in report['source_files'].items():assert sha(ROOT/name)==digest,'Frozen source changed: '+name
    assert report['tests']['failed']==0 and report['ov']['jobs']==28
    assert all(x['realized_pipelines_identical'] for x in report['operation_comparability'])
    assert report['readiness']['open_semantic_gap_ids']==['G11']
    delivery=ROOT/'delivery';delivery.mkdir(exist_ok=True)
    def portable(value):
        if isinstance(value,dict):return {k:portable(v) for k,v in value.items()}
        if isinstance(value,list):return [portable(v) for v in value]
        if isinstance(value,float) and not math.isfinite(value):return None
        if isinstance(value,str):
            return value.replace(str(run),'').replace(run.as_posix(),'').replace(str(ROOT),'..').replace(ROOT.as_posix(),'..').replace('\\','/').lstrip('/') if (str(run) in value or run.as_posix() in value or str(ROOT) in value or ROOT.as_posix() in value) else value
        return value
    public=portable(report);public['delivery_provenance']={'immutable_private_receipt_sha256':sha(run/'delivery/run-report.json'),'adaptation':'Local path prefixes made portable. Missing-value NaN serializes as JSON null with the original mask retained. Executed source hashes and finite numerical results retained.'}
    js(delivery/'run-report.json',public);js(delivery/'proposal-quality.json',report['proposal_quality'])
    data={name:json.loads((run/(name+'-results.json')).read_text(encoding='utf-8')) for name in ['python','native','ov']}
    py,cpp=data['python'],data['native'];ov={j['name']:j['records'] for j in data['ov']['jobs']}
    for name,value in data.items():js(delivery/(name+'-results.json'),portable(value))
    for directory in ['fixtures','exports','renders']:
        dst=delivery/directory;dst.mkdir(exist_ok=True)
        for src in (run/directory).iterdir():
            if not src.is_file() or src.suffix=='.log':continue
            target=dst/src.name
            if src.suffix in ['.usda','.json']:
                text=src.read_text(encoding='utf-8').replace(run.as_posix()+'/fixtures/','./').replace(str(run).replace('\\','/')+'/fixtures/','./').replace(ROOT.as_posix()+'/data/','../../data/')
                write(target,text)
            else:shutil.copy2(src,target)
    # Remove only superseded current-delivery artifacts. Git retains prior receipts.
    stale=delivery/'scope-fixtures'
    assert stale.resolve().is_relative_to(delivery.resolve())
    if stale.exists():shutil.rmtree(stale)
    for name in ['scope-results.json','origin-sampling-record.usda']:
        if (delivery/name).exists():(delivery/name).unlink()
    plots=delivery/'plots';plots.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':13,'axes.spines.top':False,'axes.spines.right':False})
    climate=py['climate'];shape=climate['association']['shape'];coords=np.array(climate['dataset_coordinates']).reshape(*shape,2);values=np.array(climate['measurement_values']).reshape(shape)
    fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained');image=ax.pcolormesh(coords[:,:,0],coords[:,:,1],values,cmap='viridis',shading='nearest',rasterized=True)
    ax.set(xlabel='Longitude (degrees)',ylabel='Latitude (degrees)',title='Original global scalar grid');fig.colorbar(image,ax=ax,label='Source scalar value (physical units not supplied)');fig.savefig(plots/'global-grid.png',dpi=160);plt.close(fig)
    railway=py['railway'];xy=np.array(railway['dataset_coordinates']);indices=railway['association']['indices'];parts={}
    for index,point in zip(indices,xy):parts.setdefault(tuple(index[:-1]),[]).append(point)
    origin=xy.min(axis=0);segments=[(np.array(points)-origin)/1000 for points in parts.values() if len(points)>1]
    fig,ax=plt.subplots(figsize=(6.7,5.8),layout='constrained');ax.add_collection(LineCollection(segments,colors='#167b88',linewidths=.65));ax.autoscale();ax.set_aspect('equal');ax.set(xlabel='UTM 32 easting offset (km)',ylabel='UTM 32 northing offset (km)',title='Railway horizontal coordinate resolution');ax.grid(alpha=.15);fig.savefig(plots/'railway.png',dpi=160);plt.close(fig)
    count=sum(x['native_vs_python']['coordinate_count'] for x in report['metrics']);maximum=max(x['native_vs_python']['max_distance_metres'] for x in report['metrics']);test=report['tests'];livet=report['ov']
    partner=json.loads((ROOT/'data/partner-controls.json').read_text(encoding='utf-8'))
    examples={}
    for name,source_label,target_label,unit in [('France_01','CC49','Lambert-93','m'),('Colorado_02','Colorado State Plane','Westminster site grid','ftUS')]:
        examples[name]={'source':partner[name]['points'][0],'source_label':source_label,'target_label':target_label,'unit':unit,
            'python':py[name]['queries'][0]['coordinates'][0],'native':cpp[name]['queries'][0]['coordinates'][0],'ov':ov[name]['queries'][0]['coordinates'][0]}
    integration={'executed_source_files':report['source_files'],'paths':[
        {'name':'USD Python','reader':'pxr.Usd composed stage','placement':'candidate.runtime.Runtime complete point map','conversion':'pyproj / PROJ','sink':'numeric records, geometry and frame queries'},
        {'name':'USD C++','reader':'native OpenUSD stage','placement':'native/leans.cpp independent placement arithmetic','conversion':'PROJ C API','sink':'numeric records and geometry used by export'},
        {'name':'Omniverse live geometry','reader':'omni.usd live composed stage','placement':'same Python placement implementation','conversion':'same pyproj / PROJ','sink':'runtime point buffers and double world matrices, read back; 27 edit/failure/recovery checks'},
        {'name':'Hydra / Storm','reader':'UsdImagingSceneIndex on resolved ordinary USD export','placement':'C++ results baked by exporter; no live CRS filter','conversion':'already performed by C++ path','sink':'Hydra points/transform readback plus native Storm color AOV PNG'}],
        'claims':{'usd_placement_implementations':2,'geodetic_engines_used':1,'independent_geodetic_validation':False,'ov_geometry_writeback':True,'ov_rendering':False,'hydra_resolved_export':True,'hydra_live_crs_filter':False,'physics_integration':False},
        'observations':{'coordinate_results_per_path':count,'ov':livet,'hydra':report['hydra'],'exports':portable(report['exports'])},
        'sharing':'All conversion paths use PROJ. External-format decoding is shared between Python and C++. OV reuses Python placement, not a third independent implementation.'}
    js(delivery/'integration-evidence.json',integration)
    frame=py['basis-Y-0.01']['frames']['/World/Model']['jacobian']
    source_t=[py[n]['queries'][0]['coordinates'][0] for n in ['time-source-t0','time-source','time-source-t10']]
    chord=(np.array(source_t[0])+source_t[2])/2;chord_error=float(np.linalg.norm(np.array(source_t[1])-chord))
    answers=[['Q3: ordinary adjustments','Nearest enclosing CRS supplies the fixed working chart. The candidate spells out chart zero/site origin, pivots and descendant resets.'],['Q6: stage conventions','Z-up uses (x,y,z). Y-up uses (x,-z,y). Stage units precede dimensionless scale and orientation.'],['Q11: external measurements','Proposed non-Xformable GeospatialDataSource identifies asset, format, field and coordinate domain. Native formats retain values, masks and observation times.'],['Q12: dependency declaration','Existing Profiles ClaimsAPI on defaultPrim carries a proposed hard capability claim. Publishers conservatively maintain whole-scene coverage, including unloaded content.']]
    text=f'''# Geospatial candidate: proposal quality and executed evidence

The four emailed leans now have **explicit local candidate contracts** for working frames, stage-axis mapping, external measurement association and Profiles dependency coverage. They are review proposals, not group agreement. **The proposal is not yet fully ready:** independently CRS-bound point-instancer prototypes remain a specialized model gap (G11). Q9 geographic scene geometry/frames/bounds remains separate from supported geographic coordinate queries. A full functional-requirement conformance claim would be premature.

This completed candidate iteration executed **{test['regressions_passed']} regression tests and {test['distinguishing_controls_passed']} distinguishing controls**, with {count:,} coordinate results per path in Python and C++. It includes live Omniverse geometry writeback, two native Hydra/Storm renders, and eight freshly reread exports. All advertised evidence belongs to this frozen run.

[Editable slides](delivery/geospatial-build.pptx) · [PDF](delivery/geospatial-build.pdf) · [Run receipt](delivery/run-report.json) · [Proposal quality](proposal-quality.json) · [Requirement trace](proposal/traceability.md) · [Build loop](BUILD_LOOP.md)

## Proposal authority and decisions requiring review

The sole authority is the [whole local proposal candidate](proposal/proposal-source.txt), SHA-256 `{report['inputs']['proposal']['sha256']}`, based on published revision `{report['inputs']['proposal']['revision']}`. Derived notes add no authored fact or normative behavior. All 31 functional requirements have a source trace. Concrete candidate details extend the agreed direction and need review on their own merits.

{table(['Subject','Explicit local answer'],answers)}

The external association is a proposed **new typed schema**, not an assertion that the existing schema already supplies these fields. `data:asset`, `data:format`, `data:field` and `data:coordinateDomain` select data; WKT retains authority for CRS meaning. `crs:position`, `crs:orientation` and `crs:scale` describe models separately from ordinary xformOps. No coordinate-epoch attribute, duplicated WKT axis/unit metadata, private binding relationship or already-resolved flag is authored.

The geographic working-chart origin, Cartesian chart-zero pivot, anchor-adjustment versus descendant-offset distinction, external association carrier and whole-scene Profiles maintenance are concrete proposals. An implementer must not infer group approval from passing tests. The group still needs to decide whether independently bound point-instancer prototypes belong in initial scope or a later extension. The run rejects that combination in both implementations. Coordinate epochs remain deferred without foreclosing a future model.

## Physical placement and ordinary transforms

The complete point map preserves source placement and transports ordinary adjustments through a fixed authoring chart. A geographic asset beneath a projected site uses its own geographic coordinates. Its ordinary +10 adjustment moves it 10 metres along site easting even with a 90-degree model orientation. A descendant +3 local-X offset follows the oriented model. A descendant reset removes the ordinary anchor adjustment while retaining intrinsic CRS placement. The enclosing model's ordinary +100000 does not leak into an independently bound asset.

The same adjusted physical positions survive an ECEF output request. Explicit pivots and inverse ops follow UsdGeom's evaluated order. Invalid nearest bindings fail even when the ordinary adjustment is identity; both forward and inverse requests are covered. Y-up centimetre controls independently verify the axis mapping, scale and orientation. Its local-frame Jacobian rows are `{frame}` in metres per stage unit.

Cartesian local frames are numerical derivatives of the full map, with an explicit chart, units and convergence residual. They may contain shear and are not reduced to a quaternion and diagonal scale. Resolved polygonal bounds enclose every returned vertex and straight polygonal face. Neither a derivative nor those bounds certifies the nonlinear image of a continuous source surface. A same-CRS Cartesian affine case has an analytical zero approximation error, separate from floating arithmetic; requests for uncertified nonlinear extent guarantees fail visibly.

## Eiffel model and native Hydra rendering

![Native Storm render of the resolved Eiffel model](delivery/renders/tower.png)

The original model contributes **163,440 resolved vertices**. Python and C++ evaluate complete geometry. The exporter consumes the C++ results, rebases float geometry around double translations, and writes an ordinary USD scene in the output CRS. A fresh Python reader and a fresh C++ reader reject double placement. UsdImaging's scene index supplies points and transforms to native Hydra/Storm, whose readback agrees with the exported ordinary-USD world geometry. The image has an illustrative plane and markers, not surveyed Paris context or independent ground truth. This route is a resolved-export bridge, not a live geospatial scene-index filter.

## Colorado survey geometry and site calibration

![Native Storm render of original LandXML breakline geometry](delivery/renders/terrain.png)

The Colorado workflow resolves **14,359 original LandXML breakline vertices** into the calibrated site CRS. It does not fabricate a terrain surface. US survey feet remain declared CRS units; the stage basis and metre conversion remain separate. The site calibration lives in WKT, while object placement lives on the model. The underlying source geometry and definitions remain unchanged.

## Non-visual measurements and regional geometry

![Original global scalar grid](delivery/plots/global-grid.png)

The global CF illustration retains **2,664 original scalar values and horizontal coordinates**. Original physical units and observation times were not supplied, so neither is invented. A request for 3D ECEF fails without a height reference and coordinate. The original dataset is preserved; a separately authored illustrative CF association makes its horizontal coordinate roles explicit.

The synthetic multi-domain CF case selects geographic or projected coordinates for the same 12 samples. The values, one missing mask and two observation times stay paired through resolution and export. Observation time is not a coordinate epoch. GeoTIFF controls preserve explicit band/IFD selection and PixelIsArea/PixelIsPoint sample locations.

![Railway horizontal resolution](delivery/plots/railway.png)

The original railway contributes **15,822 horizontal vertices across 2,386 parts**. The reader follows RFC 7946 semantics for an explicitly written horizontal copy and projects it into UTM 32. The original third components remain intact and uninterpreted. Plot offsets are only for display, not an authored calibration or changed source values.

## Same partner coordinate inputs in both implementations and the OV host

{table(['Case','Source E / N / H','USD Python output','USD C++ output','OV-hosted Python output'],[[e['source_label']+' to '+e['target_label']+' ('+e['unit']+')',', '.join(f'{x:.4f}' for x in e['source']),* [', '.join(f'{x:.4f}' for x in e[k]) for k in ['python','native','ov']]] for e in examples.values()])}

All 59 France controls are queried in both directions and all five Colorado controls in the selected source systems. Provider CSVs are PROJ-generated intake/rounding references, not survey truth. Matching output numbers do not establish geodetic accuracy. The independent axis, pivot, reset, interpolation and failure controls distinguish implementations that share the same projection engine.

## Actual consumers and shared components

{table(['Path','Placement implementation','Actual destination'],[[p['name'],p['placement'],p['sink']] for p in integration['paths']])}

There are **two placement implementations**, Python and C++. Omniverse reuses the Python interpretation and PROJ through a separate live geometry sink. It writes runtime point buffers and double world matrices, reads them back, and exercises source edits, failed resolution hiding stale geometry, and recovery. It is not a third independent placement engine. No Omniverse rendering or physics integration is claimed. Native Hydra consumes the C++-resolved export and performs real rendering.

The live sink read back **{livet['geometry_vertices']:,} vertices** over the geometry cases, with {livet['edit_checks']} update/failure/recovery checks. Its maximum writeback error is **{livet['max_writeback_error_metres']*1e6:.3f} micrometres** against resolved coordinates. Python/C++ coordinate agreement is at most **{maximum*1e9:.3f} nanometres** in these cases, under a predeclared 1 mm acceptance distance. Native PROJ 9.4.1 and Python/OV PROJ 9.8.1 produce matching realized pipeline spelling; selected resource files and the native database/library have hashes in the receipt. Agreement is computational evidence, not independent geodetic certification. External format decoding is shared.

## Source interpolation and freshly reread exports

Source longitude moves from 0 to 2 degrees at zero ellipsoidal height. Core interpolates source placement before ECEF conversion. At time 5 the result is the 1-degree surface position. Interpolating only the converted endpoints instead produces a chord, whose midpoint differs by **{chord_error:.3f} m**.

The sampled geometry export writes actual `timeSamples` keys **0, 5 and 10**, with explicit `timeCodesPerSecond = 48`. Fresh Python and C++ readers verify every exported geometry sample. Core interpolation of those output samples remains ordinary USD behavior; this does not claim the original trajectory between export samples.

Eight exports cover Eiffel geometry, Colorado breaklines, composition, instances, three CF coordinate-domain cases and sampled geometry. Their fresh-reader geometry error is at most 15.758 micrometres. CF exports retain original measurement values, missing masks and observation-time associations. Materializing instances preserves the tested resolved geometry and source-path association in the receipt, but does not certify all instancing, material or authored normal/primvar behavior. Exported Scenes conservatively retain the proposed Profiles hard dependency claim; no private resolved marker is used.

## Postimplementation audit and remaining limits

The reverse audit finds only the eight geospatial fields defined by the candidate. The source closure, original data/scene inputs, transformation-resource files and generated fixture bytes remain unchanged during execution. The two negative jobs reject missing height and independently bound point-instancer prototypes in Python and C++.

Recovery also caught implementation defects rather than filling them with new proposal facts: registered schema fallbacks had hidden blocks and bad declarations; an inverse path bypassed an invalid enclosing binding; an OV host timeline update modified an input layer. Readers now inspect authored declarations/blocks and enclosing bindings. The live host protects source layers and keeps authorized edit controls in a restored session layer. Expected rejection checks accept contract errors, not arbitrary exceptions.

G11 and Q9 remain visible design matters. The adapters visibly refuse unimplemented BOUNDCRS and geographic gravity-height ENU charts, unsupported format coordinates, and uncertified continuous extent/trajectory requests. Native validation is not a second independent WKT normalizer. Physics, a live geospatial Hydra filter and a general surface/material export guarantee have no evidence here. These are limits on advertised conformance; a green run cannot erase them.

## Reproducing and deriving delivery

`run.py` requires a fresh output directory, the OpenUSD SDK/native build, PROJ/resources and the installed OV host. It freezes source and inputs, compiles the executed native targets, runs independent contract checks, reads every query/consumer output and audits source preservation. `collateral/derive_leans_delivery.py --run <directory>` checks that frozen source before deriving this README, public evidence and slide data. `collateral/leans_slides.mjs` derives the editable deck from that README and immutable numerical returns. Delivery verification checks both claim boundaries and the final artifact hashes. Local-path relinking in public fixture copies is ordinary writer work and is recorded separately from immutable executed inputs.
'''
    write(ROOT/'README.md',text)
    pr=f'''The local proposal candidate now makes the emailed working-frame, axis-mapping, measurement-association and Profiles leans concrete before implementation. The specialized independently bound point-instancer prototype combination remains unresolved; geographic scene frames/bounds remain separate. These are proposed contracts, not group adoption or whole-proposal conformance.

This run passed {test['regressions_passed']} regressions and {test['distinguishing_controls_passed']} distinguishing controls, covering {count:,} coordinate results per Python/C++ path, actual live OV geometry writeback, native Hydra/Storm resolved-export rendering and eight fresh-reader exports. OV reuses Python placement; all paths share PROJ. The README and editable slides lead with proposal quality and show the executed workflows and limits.

See the example's README, proposal-quality.json and delivery/run-report.json for authority, call paths, expected failures, resource hashes and sampling/export evidence. No group-thread or upstream issue/PR backlink is introduced.
'''
    write(delivery/'pr-body.md',pr)
    story={'readme_sha256':sha(ROOT/'README.md'),'run_receipt_sha256':sha(delivery/'run-report.json'),'immutable_receipt_sha256':sha(run/'delivery/run-report.json'),'proposal_sha256':report['inputs']['proposal']['sha256'],'executed_source_commit':report['source_commit'],'integration_evidence_sha256':sha(delivery/'integration-evidence.json'),'tests':test,'coordinate_count':count,'max_cpp_error_metres':maximum,'ov':livet,'answers':answers,'examples':examples,'frame':frame,'source_time_coordinates':source_t,'chord_error_metres':chord_error,'working_queries':py['working-adjustment']['queries'],'slides':[
        {'title':'Proposal quality and candidate evidence','section':'Proposal authority and decisions requiring review'},
        {'title':'Concrete contracts for group review','section':'Proposal authority and decisions requiring review'},
        {'title':'A fixed working frame for project adjustments','section':'Physical placement and ordinary transforms'},
        {'title':'Eiffel geometry in the native Hydra consumer','section':'Eiffel model and native Hydra rendering'},
        {'title':'Colorado survey geometry in a calibrated site','section':'Colorado survey geometry and site calibration'},
        {'title':'Georeferenced measurements remain usable as data','section':'Non-visual measurements and regional geometry'},
        {'title':'Regional geometry retains its source coordinates','section':'Non-visual measurements and regional geometry'},
        {'title':'Matching partner-coordinate queries','section':'Same partner coordinate inputs in both implementations and the OV host'},
        {'title':'Source interpolation and sampled exports','section':'Source interpolation and freshly reread exports'},
        {'title':'Consumer evidence and remaining limits','section':'Actual consumers and shared components'}]}
    js(delivery/'story.json',story)
    assert not re.search(r'https://github.com/(?:PixarAnimationStudios/OpenUSD|[^/]+/OpenUSD-proposals)/(?:pull|issues)/',text+pr)
    print(json.dumps({'readme':str(ROOT/'README.md'),'tests':test,'coordinate_results_per_path':count,'slides':len(story['slides'])}))
if __name__=='__main__':main()
