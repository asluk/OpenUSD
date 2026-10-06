"""Whole-candidate build, consumer verification, export and reverse authority audit."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
import numpy as np
from pxr import Usd,Plug
from pyproj import datadir,network
from .fixtures import build
from .execution import execute_python,native_job,compare,coordinate_error
from .controls import verify
from .runtime import ContractError
from .export import geometry_export,cf_export,sampled_geometry_export
from geobuild.quality import assessment,require_derivable_proposal

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def command(args,log,env=None,timeout=650):
    with Path(log).open('w',encoding='utf-8') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=timeout)
    if r.returncode:raise RuntimeError('Consumer command failed; inspect '+str(log))

def source_closure(root):
    paths=[*sorted((root/'candidate').glob('*.py')),*sorted((root/'review').glob('*.py')),*sorted((root/'schema').rglob('*.usda')),*sorted((root/'schema/generated').glob('*.json')),
           *[root/p for p in ['native/leans.cpp','native/leansRender.cpp','native/CMakeLists.txt','review/scope.py','review/placement_values.py','review/wkt_profile.py','review/test_contracts.py','review/test_wkt_contracts.py','run.py','inputs.json','proposal-quality.json','ov/geobuild.kit']],
           root/'geobuild/quality.py',*sorted((root/'proposal').glob('*'))]
    return {p.relative_to(root).as_posix():sha(p) for p in paths if p.is_file()}

def execute(root,args):
    root=Path(root);out=Path(args.output).resolve()
    if out.exists():raise RuntimeError('A fresh output directory is required; receipts are immutable')
    out.mkdir(parents=True);(out/'delivery').mkdir();(out/'exports').mkdir();(out/'renders').mkdir();(out/'native-results').mkdir()
    inputs=json.loads((root/'inputs.json').read_text());assert sha(root/'proposal/proposal-source.txt')==inputs['proposal']['sha256']
    for name,digest in inputs['derivation'].items():assert sha(root/'proposal'/name)==digest
    assert '### External measurement association' in (root/'proposal/proposal-source.txt').read_text()
    require_derivable_proposal(root)
    freeze=source_closure(root);write(out/'source-freeze.json',freeze)
    input_paths=[root/'targets.json',*sorted((root/'data').rglob('*')),*sorted((root/'scenes').rglob('*'))]
    input_freeze={p.relative_to(root).as_posix():sha(p) for p in input_paths if p.is_file()}
    resource_freeze={p.name:sha(p) for p in Path(args.grids).rglob('*') if p.is_file()}
    datadir.append_data_dir(args.grids);network.set_network_enabled(False);Plug.Registry().RegisterPlugins(str(root/'schema/generated/plugInfo.json'))
    env=os.environ.copy();env['PYTHONPATH']=str(root)
    # Rebuild the actual executed targets from this frozen source.
    buildcmd=out/'build-native.cmd'
    buildcmd.write_text('@echo off\ncall "C:/Program Files/Microsoft Visual Studio/18/Community/VC/Auxiliary/Build/vcvars64.bat" >nul\nif errorlevel 1 exit /b %errorlevel%\n"'+args.cmake+'" --build "'+args.native_build+'" --target leansNative leansRender\nexit /b %errorlevel%\n')
    command(['cmd','/c',str(buildcmd)],out/'native-build.log',env)
    command([sys.executable,'-X','utf8','-m','pytest',str(root/'review/test_contracts.py'),str(root/'review/test_wkt_contracts.py'),'-q','-p','no:cacheprovider','--basetemp='+str(out/'pytest'),'--junitxml='+str(out/'contracts.xml')],out/'contracts.log',env)
    tests=ET.parse(out/'contracts.xml').getroot().findall('.//testcase');assert not any(t.findall('failure') or t.findall('error') for t in tests)
    jobs,targets=build(root,out/'fixtures');write(out/'jobs.json',jobs)
    fixture_hashes={p.relative_to(out/'fixtures').as_posix():sha(p) for p in (out/'fixtures').rglob('*') if p.is_file()}
    native_env=env.copy();native_env['PATH']=';'.join([str(Path(args.native_proj)/'bin'),str(Path(args.usd_sdk)/'bin'),str(Path(args.usd_sdk)/'lib'),args.native_python,env['PATH']])
    resources=args.grids+';'+str(Path(args.native_proj)/'share/proj')
    python={};native={};metrics=[];failures=[]
    for job in jobs:
        print('Candidate query: '+job['name'],flush=True)
        if job.get('expect_failure'):
            expected_tokens=job.get('expect_error_tokens',['dimensional','height'])
            try:execute_python(job)
            except ContractError as e:
                if not any(t in str(e) for t in expected_tokens):raise
                pyerror=str(e)
            else:raise AssertionError('Missing height silently promoted')
            try:native_job(job,out/'native-results',Path(args.native_build)/'leansNative.exe',resources,native_env)
            except RuntimeError as e:
                if not any(t in str(e) for t in expected_tokens):raise
                failures.append({'name':job['name'],'python':pyerror,'native':str(e),'expected':True})
            else:raise AssertionError('Native missing height silently promoted')
            continue
        python[job['name']]=execute_python(job)
        native[job['name']]=native_job(job,out/'native-results',Path(args.native_build)/'leansNative.exe',resources,native_env)
        metrics.append({'name':job['name'],'native_vs_python':compare(python[job['name']],native[job['name']],job['output_wkt'])})
    checks=verify(jobs,python,targets,out/'fixtures')
    # Separate engine operation descriptions from numerical agreement; don't infer equivalence from agreement.
    operation_audit=[]
    for job in jobs:
        if job['name'] not in native:continue
        p={o['definition'].replace('+','') for o in python[job['name']]['operations']};n={o['definition'].replace('+','') for o in native[job['name']]['operations']}
        operation_audit.append({'name':job['name'],'realized_pipelines_identical':p==n,'comparability':'identical realized pipeline spelling and pinned grids' if p==n else 'unestablished by this audit; numerical agreement is observational','python_pipelines':sorted(p),'native_pipelines':sorted(n)})
    exports=[];renders=[]
    for name in ['tower','terrain','composition','instances','geographic-scene','instances-independent-prototype']:
        job=next(j for j in jobs if j['name']==name);record=native[name] # Consume C++ results in the Hydra/export path.
        receipt=geometry_export(job,record,out/'exports'/(name+'.usda'));exports.append(receipt)
        reread={**{k:v for k,v in job.items() if k not in ['frames','relative','dataset','expected']},'name':name+'-export','stage':receipt['path'],'queries':[],'geometry':True}
        read=native_job(reread,out/'native-results',Path(args.native_build)/'leansNative.exe',resources,native_env)
        receipt['native_fresh_reader_vertices']=sum(len(a) for a in read['geometry'].values())
        if receipt['native_fresh_reader_vertices']!=receipt['vertices']:raise AssertionError('Native export lost geometry')
        # Explicit comparison maps exported prim identity to its retained source identity.
        for new_path,old_path in receipt['source_paths'].items():
            error=coordinate_error(read['geometry'][new_path],native[name]['geometry'][old_path],job['output_wkt'])
            if error>.001:raise AssertionError('Native export double placement')
            normal=native[name].get('geometry_normals',{}).get(old_path)
            if normal:
                fresh=read.get('geometry_normals',{}).get(new_path)
                if not fresh or normal['interpolation']!=fresh['interpolation'] or np.max(abs(np.asarray(normal['values'])-fresh['values']))>1e-5:raise AssertionError('Native export lost or misinterpreted authored normals')
        if name in ['tower','terrain']:
            runtime=__import__('candidate.runtime',fromlist=['Runtime']).Runtime(Usd.Stage.Open(job['stage']),job['output_wkt'],job['time'])
            base=runtime.stage_coordinates(np.array(next(iter(record['geometry'].values()))[0]),[0,0,0]);eye=base+([600,-800,450] if name=='tower' else [500,-700,600]);aim=base+([0,0,130] if name=='tower' else [50,0,0])
            renderjob={'stage':receipt['path'],'time':job['time'],'render':str(out/'renders'/(name+'.png')),'camera_eye':eye.tolist(),'camera_aim':aim.tolist()}
            write(out/'renders'/(name+'-job.json'),renderjob);command([str(Path(args.native_build)/'leansRender.exe'),str(out/'renders'/(name+'-job.json')),str(out/'renders'/(name+'-readback.json'))],out/'renders'/(name+'.log'),native_env)
            renders.append({'name':name,**json.loads((out/'renders'/(name+'-readback.json')).read_text()),'image_sha256':sha(out/'renders'/(name+'.png'))})
    for name in ['climate','multi-geographic','multi-projected','global-3d-geographic']:
        job=next(j for j in jobs if j['name']==name);exports.append(cf_export(job,out/'exports'/(name+'.usda')))
    sample_jobs=[next(j for j in jobs if j['name']==name) for name in ['time-source-t0','time-source','time-source-t10']]
    sample_export=sampled_geometry_export(sample_jobs,[native[j['name']] for j in sample_jobs],out/'exports/time-sampled.usda')
    for job in sample_jobs:
        reread={**job,'name':'sample-export-'+str(job['time']),'stage':sample_export['path'],'queries':[],'geometry':True}
        read=native_job(reread,out/'native-results',Path(args.native_build)/'leansNative.exe',resources,native_env)
        for new_path,old_path in sample_export['source_paths'].items():
            if coordinate_error(read['geometry'][new_path],native[job['name']]['geometry'][old_path],job['output_wkt'])>.001:raise AssertionError('Native sampled export mismatch')
    sample_export['native_fresh_reader_sample_times']=[j['time'] for j in sample_jobs];exports.append(sample_export)
    # Real OV host, live stage, runtime point/matrix writeback and stale-result recovery.
    ov_env=env.copy();ov_env.update(GEOBUILD_OV_SDK=args.ov_sdk,GEOBUILD_OV_JOB=str(out/'ov-job.json'),GEOBUILD_OV_ERROR=str(out/'ov-error.txt'),PYTHONNOUSERSITE='1')
    cfg={'source':str(root),'python_paths':[args.python_dependencies,str(Path(sys.executable).parents[1]/'Lib/site-packages')],'grids':args.grids,'jobs':[j for j in jobs if not j.get('expect_failure')],'output':str(out/'ov-results.json')}
    write(out/'ov-job.json',cfg);command([str(Path(args.ov_sdk)/'python/python.exe'),'-s',str(root/'candidate/ov_launch.py')],out/'ov.log',ov_env)
    if (out/'ov-error.txt').exists():raise RuntimeError((out/'ov-error.txt').read_text())
    ov=json.loads((out/'ov-results.json').read_text())
    for j in ov['jobs']:
        job=next(x for x in jobs if x['name']==j['name']);metric=next(m for m in metrics if m['name']==j['name']);metric['ov_vs_python']=compare(python[j['name']],j['records'],job['output_wkt'])
    # Reverse authority audit, including the generated codeless schema and every authored geospatial field.
    allowed={'crs:wkt','crs:position','crs:orientation','data:asset','data:format','data:field','data:coordinateDomain'}
    field_uses={name:[] for name in allowed}
    for file in (out/'fixtures').glob('*.usda'):
        stage=Usd.Stage.Open(str(file))
        for p in stage.Traverse(Usd.TraverseInstanceProxies()):
            for a in p.GetAuthoredProperties():
                name=a.GetName()
                if name.startswith(('geo:','crs:')) or name in allowed:
                    if name not in allowed:raise AssertionError('Undocumented authored geospatial field '+name)
                    field_uses[name].append(str(p.GetPath())+'.'+name)
    assert freeze==source_closure(root),'Implementation or authority changed after freeze'
    assert input_freeze=={p.relative_to(root).as_posix():sha(p) for p in input_paths if p.is_file()},'Original data or scene inputs changed'
    assert resource_freeze=={p.name:sha(p) for p in Path(args.grids).rglob('*') if p.is_file()},'Coordinate-operation resources changed'
    assert fixture_hashes=={p.relative_to(out/'fixtures').as_posix():sha(p) for p in (out/'fixtures').rglob('*') if p.is_file() and not p.name.startswith('dependency-')},'Source fixture files changed'
    write(out/'python-results.json',python);write(out/'native-results.json',native)
    receipt={'status':'Candidate build loop executed; proposed contracts remain under review','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':inputs,'source_files':freeze,'source_commit':subprocess.check_output(['C:/progs/Git/cmd/git.exe','-c','safe.directory='+str(root.parents[3]).replace('\\','/'),'-C',str(root),'rev-parse','HEAD'],text=True).strip(),'source_is_uncommitted':True,'proposal_quality':json.loads((root/'proposal-quality.json').read_text()),'tests':{'regressions_passed':len(tests),'distinguishing_controls_passed':len(checks),'failed':0},'controls':checks,'expected_failures':failures,'metrics':metrics,'operation_comparability':operation_audit,'exports':exports,'hydra':renders,'ov':{'implementation':ov['implementation'],'jobs':len(ov['jobs']),'geometry_vertices':sum(sum(v['vertices'] for v in j['geometry_writeback'].values()) for j in ov['jobs']),'max_writeback_error_metres':max([v['max_metric_error'] for j in ov['jobs'] for v in j['geometry_writeback'].values()] or [0]),'edit_checks':sum(len(j['edit_checks']) for j in ov['jobs'])},'postimplementation_audit':{'undocumented_authored_fields':[],'field_usage_counts':{k:len(v) for k,v in field_uses.items()},'source_preserved':True,'source_freeze_preserved':True,'native_binary_sha256':sha(Path(args.native_build)/'leansNative.exe'),'hydra_binary_sha256':sha(Path(args.native_build)/'leansRender.exe')},'limitations':['Input-only attitude, working chart, descendant interpretation, external association, instance and geographic-chart contracts are proposed for author review.','Analytically affine geocentric placement has a zero mathematical-error certificate at the evaluated time. General nonlinear continuous-domain and between-sample certificates are unsupported by these adapters and fail visibly.','Python and C++ share PROJ; OV reuses the Python algorithm and external dataset decoding is shared. Pipeline equivalence is separately reported.','Hydra consumes a resolved ordinary-USD export from C++ results. This is not a live geospatial scene-index filter. OV runtime geometry writeback is verified; no OV render is claimed.','Export materializes instances. Authored vertex shading normals are transported and compared between Python/C++ and exported; broader coordinate-bearing primvar consumer coverage remains limited.','External original climate metadata is incomplete and original railway heights remain uninterpreted; explicit horizontal illustrative associations preserve their useful workflows.','Geographic output uses an associated geocentric scene chart. Coordinate epochs remain deferred.']}
    receipt.update(readiness=assessment(root),execution_authority='Explicitly authorized local run using emailed candidate leans; no group agreement or whole-proposal conformance asserted',input_data_sha256=input_freeze,transformation_resource_sha256=resource_freeze,
        toolchain={'native_proj_library_sha256':sha(Path(args.native_proj)/'bin/proj_9_4.dll'),'native_proj_database_sha256':sha(Path(args.native_proj)/'share/proj/proj.db'),'ov_app_version':ov['app_version']})
    receipt['limitations'].append('Independent bound prototypes now have a candidate contract and controls. Frame derivatives are numerical estimates, not continuous-domain certificates. Pending author decisions and implementation coverage remain separate.')
    write(out/'delivery/run-report.json',receipt)
    print('Candidate loop complete: '+str(out/'delivery/run-report.json'),flush=True)
    return receipt
