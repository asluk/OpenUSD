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
    a=argparse.ArgumentParser();a.add_argument('--run',required=True);a.add_argument('--assessment',default=str(ROOT/'collateral/delivery-assessment.json'));a.add_argument('--audit',default=str(ROOT/'delivery/independent-audit.json'));args=a.parse_args();run=Path(args.run).resolve()
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
    public=portable(report);public['ov']['implementation']='Python placement reader with separate stage geometry writeback and readback';public['delivery_provenance']={'immutable_private_receipt_sha256':sha(run/'delivery/run-report.json'),'adaptation':'Portable filesystem paths, preserving USD prim identities; masked NaNs serialized as null; OV integration label clarified as stage geometry writeback. Exact executed file hashes and finite results retained.'}
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
        {'name':'Omniverse stage geometry integration','reader':'omni.usd stage','placement':'reused Python point map','sink':'runtime points, normal arrays and world matrices; readback and edit/failure/recovery'},
        {'name':'Hydra / Storm','reader':'UsdImagingSceneIndex on ordinary resolved export','placement':'C++ results materialized by exporter','sink':'points/transform readback and native Storm color output'}],
        'observations':{'coordinate_results_per_path':count,'ov':live,'hydra':report['hydra'],'exports':portable(report['exports'])},'sharing':'Both placements use PROJ; native dataset decoding is shared. OV is not a third independent placement implementation.'}
    js(d/'integration-evidence.json',integration)
    comparison=json.loads((run/'transform-order-comparison.json').read_text());js(d/'transform-order-comparison.json',comparison)
    source_t=[py[n]['queries'][0]['coordinates'][0] for n in ['time-source-t0','time-source','time-source-t10']];chord=(np.asarray(source_t[0])+source_t[2])/2;chord_error=float(np.linalg.norm(np.asarray(source_t[1])-chord))
    base={'run_receipt_sha256':sha(d/'run-report.json'),'immutable_receipt_sha256':sha(run/'delivery/run-report.json'),'proposal_sha256':report['inputs']['proposal']['sha256'],'integration_evidence_sha256':sha(d/'integration-evidence.json'),'executed_source_commit':report['source_commit'],'tests':t,'coordinate_count':count,'max_cpp_error_metres':maximum,'ov':live,'export_count':len(report['exports']),'comparison':comparison,'examples':examples,'working_queries':py['working-adjustment']['queries'],'source_time_coordinates':source_t,'chord_error_metres':chord_error,'dataset_counts':{'global_samples':len(g['measurement_values']),'railway_vertices':len(xy),'railway_parts':len(parts)}}
    from human_delivery import publish
    story=publish(ROOT,base,args.assessment,args.audit)
    print(json.dumps({'narrative_version':story['narrative_version'],'cases':len(story['cases']),'slides':len(story['slides']),'frozen_source_verified':len(report['source_files'])}))
if __name__=='__main__':main()
