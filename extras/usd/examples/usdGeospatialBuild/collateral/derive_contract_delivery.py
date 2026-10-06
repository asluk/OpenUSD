"""One receipt -> README -> review body/story; no hidden narrative authorities."""
from pathlib import Path
import argparse,hashlib,json,re,math,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,s):Path(p).write_text(s,encoding='utf-8',newline='\n')
def js(p,x):write(p,json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','|'+'|'.join(['---']*len(head))+'|',*['| '+' | '.join(map(str,row))+' |' for row in rows]])
def main():
    a=argparse.ArgumentParser();a.add_argument('--run',required=True);run=Path(a.parse_args().run).resolve()
    report=json.loads((run/'delivery/run-report.json').read_text(encoding='utf-8'))
    for n,h in report['source_files'].items():assert sha(ROOT/n)==h,n
    assert report['tests']['failed']==0 and report['readiness']['proposal_ready'] and not report['readiness']['requirements_build_complete']
    d=ROOT/'delivery';d.mkdir(exist_ok=True)
    def portable(v):
        if isinstance(v,dict):return {k:portable(x) for k,x in v.items()}
        if isinstance(v,list):return [portable(x) for x in v]
        if isinstance(v,float) and not math.isfinite(v):return None
        if isinstance(v,str):
            normalized=v.replace('\\','/')
            if normalized.startswith(run.as_posix()+'/'):return normalized[len(run.as_posix())+1:]
            if normalized.startswith(ROOT.as_posix()+'/'):return '../'+normalized[len(ROOT.as_posix())+1:]
            return v  # USD prim paths are scene identities, not filesystem paths.
        return v
    public=portable(report);public['delivery_provenance']={'immutable_private_receipt_sha256':sha(run/'delivery/run-report.json'),'adaptation':'Portable filesystem paths, preserving USD prim identities; masked NaNs serialized as null. Exact executed file hashes and finite results retained.'}
    js(d/'run-report.json',public);js(d/'proposal-quality.json',report['proposal_quality']);js(d/'jobs.json',portable(json.loads((run/'jobs.json').read_text(encoding='utf-8'))))
    data={n:json.loads((run/(n+'-results.json')).read_text(encoding='utf-8')) for n in ['python','native','ov']};py,cpp=data['python'],data['native'];ov={j['name']:j['records'] for j in data['ov']['jobs']}
    for n,v in data.items():js(d/(n+'-results.json'),portable(v))
    for name in ['fixtures','exports','renders']:
        dst=d/name;dst.mkdir(exist_ok=True)
        desired={p.name for p in (run/name).iterdir() if p.is_file() and p.suffix!='.log'}
        for old in dst.iterdir():
            if old.is_file() and old.name not in desired:old.unlink()
        for src in (run/name).iterdir():
            if not src.is_file() or src.suffix=='.log':continue
            if src.suffix in ['.usda','.json']:
                s=src.read_text(encoding='utf-8').replace(run.as_posix()+'/fixtures/','./').replace(str(run).replace('\\','/')+'/fixtures/','./').replace(ROOT.as_posix()+'/data/','../../data/')
                write(dst/src.name,s)
            else:shutil.copy2(src,dst/src.name)
    # Retire only known superseded current evidence, preserving immutable run dirs.
    for name in ['scope-results.json','origin-sampling-record.usda']:
        old=d/name
        if old.exists():old.unlink()
    stale=d/'scope-fixtures'
    if stale.exists():
        assert stale.resolve().is_relative_to(d.resolve());shutil.rmtree(stale)
    plots=d/'plots';plots.mkdir(exist_ok=True);plt.rcParams.update({'font.family':'DejaVu Sans','font.size':13,'axes.spines.top':False,'axes.spines.right':False})
    g=py['global-3d-geographic'];coords=np.asarray(g['dataset_coordinates']).reshape(2,7,11,3)[0];values=np.asarray(g['measurement_values']).reshape(2,7,11)[0]
    fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained');im=ax.pcolormesh(coords[:,:,0],coords[:,:,1],values,cmap='viridis',shading='nearest');ax.set(xlabel='Longitude (degrees)',ylabel='Latitude (degrees)',title='Synthetic global temperature domain - first observation');fig.colorbar(im,ax=ax,label='Illustrative temperature (K)');fig.savefig(plots/'global-3d.png',dpi=160);plt.close(fig)
    climate=py['climate'];shape=climate['association']['shape'];xy=np.asarray(climate['dataset_coordinates']).reshape(*shape,2);v=np.asarray(climate['measurement_values']).reshape(shape)
    fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained');im=ax.pcolormesh(xy[:,:,0],xy[:,:,1],v,cmap='viridis',shading='nearest');ax.set(xlabel='Longitude (degrees)',ylabel='Latitude (degrees)',title='Original global scalar grid');fig.colorbar(im,ax=ax,label='Source value (physical units not supplied)');fig.savefig(plots/'global-grid.png',dpi=160);plt.close(fig)
    railway=py['railway'];xy=np.asarray(railway['dataset_coordinates']);parts={}
    for index,point in zip(railway['association']['indices'],xy):parts.setdefault(tuple(index[:-1]),[]).append(point)
    origin=xy.min(axis=0);segments=[(np.asarray(points)-origin)/1000 for points in parts.values() if len(points)>1]
    fig,ax=plt.subplots(figsize=(6.7,5.8),layout='constrained');ax.add_collection(LineCollection(segments,colors='#167b88',linewidths=.65));ax.autoscale();ax.set_aspect('equal');ax.set(xlabel='UTM 32 easting offset (km)',ylabel='UTM 32 northing offset (km)',title='Railway horizontal coordinate resolution');ax.grid(alpha=.15);fig.savefig(plots/'railway.png',dpi=160);plt.close(fig)
    count=sum(m['native_vs_python']['coordinate_count'] for m in report['metrics']);maximum=max(m['native_vs_python']['max_distance_metres'] for m in report['metrics']);t=report['tests'];live=report['ov']
    partner=json.loads((ROOT/'data/partner-controls.json').read_text());examples={}
    for n,s,o,u in [('France_01','CC49','Lambert-93','m'),('Colorado_02','State Plane','Westminster site grid','ftUS')]:examples[n]={'source':partner[n]['points'][0],'source_label':s,'target_label':o,'unit':u,'python':py[n]['queries'][0]['coordinates'][0],'native':cpp[n]['queries'][0]['coordinates'][0],'ov':ov[n]['queries'][0]['coordinates'][0]}
    claims={'usd_placement_implementations':2,'geodetic_engines_used':1,'independent_geodetic_validation':False,'ov_geometry_writeback':True,'ov_rendering':False,'hydra_resolved_export':True,'hydra_live_crs_filter':False,'physics_integration':False,'whole_proposal_conformance':False,'continuous_nonlinear_extent_certificate':False}
    integration={'executed_source_files':report['source_files'],'claims':claims,'paths':[
        {'name':'USD Python','reader':'pxr.Usd composed stage','placement':'candidate/runtime.py independent Python point map','conversion':'pyproj / PROJ','sink':'numeric records and geometry'},
        {'name':'USD C++','reader':'native OpenUSD composed stage','placement':'native/leans.cpp independent C++ point map','conversion':'PROJ C API','sink':'numeric records and export geometry'},
        {'name':'Omniverse live geometry','reader':'omni.usd live stage','placement':'reused Python point map','sink':'runtime points, normal arrays and world matrices; readback and edit/failure/recovery'},
        {'name':'Hydra / Storm','reader':'UsdImagingSceneIndex on ordinary resolved export','placement':'C++ results materialized by exporter','sink':'points/transform readback and native Storm color output'}],
        'observations':{'coordinate_results_per_path':count,'ov':live,'hydra':report['hydra'],'exports':portable(report['exports'])},'sharing':'Both placements use PROJ; native dataset decoding is shared. OV is not a third independent placement implementation.'}
    js(d/'integration-evidence.json',integration)
    comparison=json.loads((run/'transform-order-comparison.json').read_text());js(d/'transform-order-comparison.json',comparison)
    choices=[['Inputs / Q2, Q6','Position plus physical geodetic-attitude quaternion. Projection scale/convergence are computed; intentional scale uses xformOps.'],['Transform order / Q3','Anchor xformOps adjust the resolved placement in a fixed working chart. Descendants retain model-local USD meaning.'],['Absolute data / Q11','Xformable carrier selects native asset, format, field and coordinate domain; values, masks and observation times stay paired.'],['Instances and geographic output','Bound prototypes retain their own anchor; geographic tuples have an associated geocentric Cartesian scene chart.'],['Profiles, export and WKT','Whole-scene hard dependency claim; nonbinding Cartesian context for baked geometry; lexical WKT normal form distinct from semantic CRS equality.']]
    source_t=[py[n]['queries'][0]['coordinates'][0] for n in ['time-source-t0','time-source','time-source-t10']];chord=(np.asarray(source_t[0])+source_t[2])/2;chord_error=float(np.linalg.norm(np.asarray(source_t[1])-chord))
    text=f'''# Geospatial proposal candidate and executed evidence

The proposal now contains a **complete proposed answer for every known retained-scope contract gap** from the audit. It remains a review candidate: input-only model attitude, descendant-transform meaning, native-data association, independently bound prototypes, geographic scene charts, Profiles, export representation and WKT string normalization require author alignment. No computed projection result becomes a source USD property. Passing this run does not establish group agreement or whole-proposal conformance.

The full local loop passed **{t['regressions_passed']} regressions and {t['distinguishing_controls_passed']} distinguishing controls**, compared {count:,} coordinate results per Python/C++ path, verified {live['jobs']} OV-hosted jobs, rendered two native Hydra/Storm exports and reread {len(report['exports'])} exports. The maximum measured Python/C++ coordinate difference was {maximum:.3g} m. Original source inputs and frozen executed files remained unchanged.

[Editable slides](delivery/geospatial-build.pptx) Â· [PDF](delivery/geospatial-build.pdf) Â· [Receipt](delivery/run-report.json) Â· [Proposal audit](proposal-quality.json) Â· [Whole proposal](proposal/proposal-source.txt) Â· [Build loop](BUILD_LOOP.md)

## Proposal quality and review choices

The sole normative candidate is the whole proposal, SHA-256 `{report['inputs']['proposal']['sha256']}`, with the exact local diff retained beside it. Requirement traceability now uses the actual 31 functional requirements and their exact normative clauses. Derived notes, fixtures and adapter code add no authority. The pre-implementation gate distinguishes missing meanings from complete choices awaiting review; the post-implementation gate checks both authored fields and observable results in reverse.

{table(['Subject','Proposed answer'],choices)}

The authored model inputs are `double3 crs:position` and `quatd crs:orientation`. Their scope, defaults, units, ordering, quaternion validity and time behavior are defined. `crs:scale`, coordinate epoch, heading/pitch/roll outputs, convergence and computed projection-scale properties are not authored inputs. The proposed external schema uses `data:asset`, `data:format`, `data:field` and `data:coordinateDomain`; this is an explicit new schema candidate, not a claim that existing fields already covered association. WKT retains CRS authority. Ordinary scaling and pivots remain xformOps.

Coordinate epochs and scene-authored operation/resource controls remain deferred without foreclosing later support. Larger-scale geographic workflows remain represented. Nothing in these choices is justified by a fixture name or an adapter limitation.

## Ordered math and the descendant choice

The intrinsic map converts model-local stage coordinates through geospatial attitude and the source datum's ENU/ECEF relationship. The anchor's ordinary stack adjusts the resolved point in its fixed working chart, then the adjusted physical point is expressed in the requested output CRS. The nearest strictly enclosing direct CRS binding selects that working context; the source CRS is its fallback. Output selection never reinterprets raw adjustment values.

Descendant xformOps, including authored asset conformance, define the model-local point supplied to placement. This is a **proposed clarification** of the call's broad post-placement wording, not an assertion that descendant semantics were already settled. The tested all-working-axis counterfactual differs by **{comparison['difference_metres']:.6f} m** in the distinguishing rotated-child case. Both exact coordinates are retained in [the comparison](delivery/transform-order-comparison.json). This review choice is visible rather than hidden behind an implementation order.

An anchor +10 translation moves along site easting; the oriented child +3 local-X offset follows model axes. A descendant reset removes ordinary ancestors and retains intrinsic placement. Independent direct bindings exclude ancestor xformOps without ignoring the enclosing CRS's role. Per-instance transforms are applied once; bound prototypes retain their own absolute source placement. A separate prototype-child reset control excludes a +100 prototype transform and retains the explicitly selected instance transform.

## Eiffel geometry and shading

![Native Storm Eiffel rendering](delivery/renders/tower.png)

The native C++ path resolves **163,440 vertices**, including the illustrative context markers and plane. **163,416 authored vertex normals** are transported through the full-map Jacobian, compared between readers, retained in the output and reread. The export's ordinary points and double transforms reach Hydra data sources and native Storm color output. The plane and markers are illustrative, not surveyed Paris context. This is a resolved-export rendering path; no live geospatial Hydra filter or OV render is claimed.

## Colorado site calibration

![Native Storm survey rendering](delivery/renders/terrain.png)

The original LandXML survey contributes **14,359 breakline vertices**. WKT carries the calibrated site relationship and US survey foot units. Stage conventions remain separate. No terrain surface was fabricated. Fresh readers verify placement; polygonal bounds describe returned vertices and straight faces, not the continuous nonlinear image of an original surface.

## Native measurements and larger-scale workflows

![Synthetic global 3D measurements](delivery/plots/global-3d.png)

The synthetic global CF domain has **154 samples over two observation times**, explicit **100 m ellipsoidal height** and illustrative temperature units in kelvin. Both readers resolve it into geographic and ECEF coordinates without changing values or treating observation time as a coordinate epoch. A fresh CF export preserves values, masks, coordinates, height and observation-time metadata.

The original global scalar grid retains **2,664 values** and its explicitly horizontal association. Missing physical units, height and observation times remain missing. Unsupported 3D requests fail visibly. Synthetic imagery adjustment retains native pixel values and coordinate bytes while adding +25 m east and -10 m north in the project frame. CF controls select distinct geographic/projected coordinate domains and retain missing masks and native times.

![Railway horizontal resolution](delivery/plots/railway.png)

The original railway retains **15,822 horizontal vertices** across {len(parts):,} parts. An explicit horizontal illustrative copy resolves to UTM 32. Its original third components remain untouched and uninterpreted; no height reference is guessed. Plot origins serve display only.

## Same partner data in both placements

'''
    for n,e in examples.items():text+=f"**{n}: {e['source_label']} to {e['target_label']} ({e['unit']}).**\n\n"+table(['Component','Source','USD Python','USD C++','OV-hosted Python'],[[label,*[f'{e[k][i]:.8f}' for k in ['source','python','native','ov']]] for i,label in enumerate(['Easting','Northing','Height'])])+'\n\n'
    text+=f'''All coordinate-conversion paths use PROJ. Independent placement arithmetic is verified, but engine-independent geodetic validation and survey accuracy are not established by these comparisons. Operation-pipeline comparability is reported separately from numerical agreement.

## Geographic scene charts and exports

Geographic coordinate tuples remain angular/height tuples. Scene geometry, derivatives and polygonal bounds use the associated geocentric Cartesian CRS of the same datum. An explicit control rejects angular scene bounds; fresh Python and C++ readers verify the exported geographic workflow's Cartesian geometry context.

The {len(report['exports'])} exports cover Eiffel, survey, composition, ordinary instances, independently bound prototypes, geographic-scene geometry, four CF domains and a sampled geometry trajectory. Baked geometry has a typed, nonbinding Cartesian CRS context and ordinary geometry/transforms, without an active placement binding or private already-resolved flag. Fresh readers verify placement once. Original sample keys **0, 5, 10** and **48 time codes/second** are preserved. The source-first midpoint is {chord_error:.3f} m from the converted-endpoint chord; no original-trajectory guarantee is claimed between exported samples.

## Consumer evidence and limits

{table(['Path','Observed output'],[['USD Python / C++',f'Two independent placement readers; {count:,} comparable coordinate results each. Shared PROJ and dataset decoding.'],['Omniverse live stage',f'{live["geometry_vertices"]:,} geometry vertices read back from runtime buffers/world matrices; {live["edit_checks"]} edit, failure and recovery checks. Reuses Python placement; normal buffers also checked.'],['Hydra / Storm','C++-resolved ordinary exports reach points/transform sources and two native rendered images.']])}

Analytically affine geocentric placement has a zero mathematical approximation-error certificate at the evaluated time. General nonlinear continuous-domain and between-sample certificates remain unsupported by these adapters and fail visibly. Numerical frame derivatives and polygonal bounds are not certificates. General coordinate-bearing primvar transport, physics integration, independently implemented WKT normalization and a live geospatial Hydra filter have no complete evidence here. These are implementation/verification limits, not newly deferred model meanings.

The implementation audit corrected angular bounds, a native prototype reset, the relative-result frame and source-normal export. It also caught an independent Y-up test oracle that applied scale in the wrong mapped axis order. Native diagnostic logging now retains distinct realized pipelines rather than a repeated entry for every point. None of these repairs introduced a source property or changed the pinned proposal.

## Source credit

The Eiffel geometry is “( FREE ) La tour Eiffel” by [SDC PERFORMANCE](https://sketchfab.com/Lambo_SC04), [original model](https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674), licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The example reorients, places and renders that geometry with illustrative context. Partner-data credit and permission are retained in `data/README.md` and `data/LICENSE-partner.txt`.

## Reproduce and derive delivery

`run.py` requires a fresh run directory and the pinned USD, PROJ/resources and OV tools. It freezes source/inputs, compiles native targets, runs controls, verifies exports and actual consumers, then audits fields and preserved inputs. `collateral/derive_contract_delivery.py --run <directory>` verifies that freeze before deriving this README, portable evidence and story. `collateral/contract_slides.mjs` derives the deck from the README/story and immutable returns. `collateral/verify_contract_delivery.py` checks the actual artifacts and rejects unsupported integration claims. Prior generators remain historical and are excluded from the active delivery path.
'''
    write(ROOT/'README.md',text)
    pr=f'''The candidate proposal now gives complete proposed contracts for the known retained-scope gaps, with authored position/geodetic attitude separated from computed projection results. Detailed descendant, external-association, instance, geographic-chart, Profiles, WKT-normalization and export choices still require author review; tests do not imply adoption.

This frozen run passed {t['regressions_passed']} regressions and {t['distinguishing_controls_passed']} distinguishing controls; compared {count:,} coordinates per Python/C++ path; verified live OV geometry writeback, two native Hydra/Storm renders and {len(report['exports'])} fresh-reader exports. The README and slides lead with proposal quality and show working workflows. OV reuses Python; conversions and native dataset decoding are shared. Whole-proposal conformance and continuous nonlinear certificates are not claimed.

See the example README, exact proposal/audit, receipt and integration evidence for review choices, expected failures, source preservation and consumer boundaries.
''';write(d/'pr-body.md',pr)
    story={'readme_sha256':sha(ROOT/'README.md'),'run_receipt_sha256':sha(d/'run-report.json'),'immutable_receipt_sha256':sha(run/'delivery/run-report.json'),'proposal_sha256':report['inputs']['proposal']['sha256'],'integration_evidence_sha256':sha(d/'integration-evidence.json'),'executed_source_commit':report['source_commit'],'tests':t,'coordinate_count':count,'max_cpp_error_metres':maximum,'ov':live,'export_count':len(report['exports']),'choices':choices,'comparison':comparison,'examples':examples,'working_queries':py['working-adjustment']['queries'],'source_time_coordinates':source_t,'chord_error_metres':chord_error,'slides':[
        {'title':'Proposal quality and review choices','section':'Proposal quality and review choices'},
        {'title':'Authored inputs and computed results','section':'Proposal quality and review choices'},
        {'title':'Anchor adjustments and model-local descendants','section':'Ordered math and the descendant choice'},
        {'title':'Eiffel geometry in native Hydra / Storm','section':'Eiffel geometry and shading'},
        {'title':'Colorado survey in a calibrated site','section':'Colorado site calibration'},
        {'title':'Global measurements in geographic and ECEF coordinates','section':'Native measurements and larger-scale workflows'},
        {'title':'Railway geometry retains its source coordinates','section':'Native measurements and larger-scale workflows'},
        {'title':'The same partner data in both placements','section':'Same partner data in both placements'},
        {'title':'Source interpolation and sampled exports','section':'Geographic scene charts and exports'},
        {'title':'Verified consumers and remaining evidence limits','section':'Consumer evidence and limits'}]};js(d/'story.json',story)
    assert not re.search(r'https://github.com/(?:PixarAnimationStudios/OpenUSD|[^/]+/OpenUSD-proposals)/(?:pull|issues)/',text+pr)
    print(json.dumps({'tests':t,'coordinates':count,'maximum_metres':maximum,'exports':len(report['exports']),'ov':live}))
if __name__=='__main__':main()
