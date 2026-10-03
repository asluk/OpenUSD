"""Execute the frozen candidate, all datasets, independent runtimes and reverse audit."""
from pathlib import Path
import argparse,os,sys,json,hashlib,subprocess,datetime,xml.etree.ElementTree as ET,shutil,csv
import numpy as np
from pxr import Usd,UsdGeom,Gf,Vt,Sdf
from pyproj import CRS,datadir,proj_version_str,network
from geobuild.model import crs,validate,normalize_wkt
from geobuild.resolve import Resolver,axis_factors,convert,operation_details,homogeneous
from geobuild.export import export
ROOT=Path(__file__).parent.resolve()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def composition_copy():
    layer=Sdf.Layer.CreateAnonymous('composition-test.usda');layer.ImportFromString((ROOT/'scenes/composition.usda').read_text());return Usd.Stage.Open(layer)
def records(stage,output,t):
    r=Resolver(stage);tc=Usd.TimeCode(t);result={'geometry':{},'measurements':{},'frames':{},'point_instances':{},'operations':{}}
    for p in stage.Traverse(Usd.TraverseInstanceProxies()):
        rel=p.GetRelationship('crs:coordinateProperties')
        if rel and rel.HasAuthoredTargets():
            for key,v in r.measures(p,output,tc).items():result['measurements'][key]=v.points.tolist();result['operations'][key]={'description':v.operation,'accuracy':v.accuracy}
        a=p.GetAttribute('crs:position')
        if a and a.HasAuthoredValue():
            m,v=r.frame(p,output,tc);result['frames'][str(p.GetPath())]=m.tolist();result['operations'][str(p.GetPath())]={'description':v.operation,'accuracy':v.accuracy}
        if p.IsA(UsdGeom.PointInstancer):
            root,_=r.model(p);m,_=r.frame(root,output,tc);local=r.child_matrix(p,root,tc);a=UsdGeom.PointInstancer(p).ComputeInstanceTransformsAtTime(tc,tc);result['point_instances'][str(p.GetPath())]=[list((q*local*Gf.Matrix4d(m)).Transform(Gf.Vec3d(0))) for q in a]
        a=p.GetAttribute('points')
        if a and a.Get(tc) is not None:
            v=r.geometry(p,output,tc)
            result['geometry'][str(p.GetPath())]=v.points.tolist()
    return result
def compare(a,b,output):
    total=0;maxerr=0.;components=np.zeros(3);magnitude=0.;c=crs(output)
    for domain in ['measurements','geometry','point_instances']:
        if set(a[domain])!=set(b.get(domain,{})):raise AssertionError(f'{domain} source associations differ')
        for k,aa in a[domain].items():
            x=np.asarray(aa);y=np.asarray(b[domain][k]);assert x.shape==y.shape
            total+=len(x);delta=x-y;components=np.maximum(components,np.max(abs(delta),axis=0));magnitude=max(magnitude,float(np.max(abs(x))))
            if c.is_geographic:
                xx,_=convert(c,CRS.from_epsg(4978),x);yy,_=convert(c,CRS.from_epsg(4978),y);err=np.linalg.norm(xx-yy,axis=1)
            else:err=np.linalg.norm(delta*axis_factors(c),axis=1)
            maxerr=max(maxerr,float(err.max()))
    assert maxerr<.001,(maxerr,components)
    for key in a['frames']:
        assert key in b['frames'];assert np.allclose(a['frames'][key],b['frames'][key],rtol=0,atol=2e-6),key
    return {'samples':total,'max_agreement_metres':maxerr,'max_native_component_difference':components.tolist(),'max_native_coordinate_magnitude':magnitude,'metric':'Euclidean target-length distance; geographic coordinates compared after common ECEF conversion. Numerical agreement, not geodetic accuracy.'}
def command(args,log,env=None,timeout=600):
    with Path(log).open('w',encoding='utf8') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=timeout)
    if r.returncode:raise RuntimeError(f'Command failed ({r.returncode}); see {Path(log).name}')
def main():
    p=argparse.ArgumentParser();p.add_argument('--grids',required=True);p.add_argument('--usd-sdk',required=True);p.add_argument('--native-build',required=True);p.add_argument('--native-proj',required=True,help='PROJ install with TIFF support');p.add_argument('--native-python',required=True,help='DLL directory for the Python version linked by the native USD SDK');p.add_argument('--ov-sdk',required=True);p.add_argument('--python-dependencies',required=True);p.add_argument('--output',required=True);p.add_argument('--cmake',default='cmake');a=p.parse_args();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);pub=out/'delivery';pub.mkdir(exist_ok=True)
    inputs=json.loads((ROOT/'inputs.json').read_text())
    for name,value in inputs['candidate'].items():assert sha(ROOT/'proposal'/name)==value,'Candidate changed since freeze: '+name
    resources=json.loads((ROOT/'data/resources.json').read_text())
    for resource in resources['resources']:
        path=Path(a.grids)/resource['name']
        assert path.stat().st_size==resource['bytes'] and sha(path)==resource['sha256'],'Resource mismatch: '+resource['name']
    (pub/'resources.json').write_text(json.dumps(resources,indent=2)+'\n')
    network.set_network_enabled(False)
    datadir.append_data_dir(a.grids);targets=json.loads((ROOT/'targets.json').read_text());env=os.environ.copy();env['GEOBUILD_GRIDS']=a.grids;env['PYTHONPATH']=str(ROOT);env['PROJ_NETWORK']='OFF'
    command([a.cmake,'--build',a.native_build],out/'native-build.log')
    command([sys.executable,'-X','utf8','-m','pytest',str(ROOT/'tests'),'-q','--junitxml='+str(out/'tests.xml')],out/'tests.log',env)
    suite=ET.parse(out/'tests.xml').getroot();cases=suite.findall('.//testcase');assert all(not x.findall('failure') and not x.findall('error') for x in cases)
    pairs=[('Colorado_01','Colorado_02',0),('Colorado_02','Colorado_03',0),('Colorado_03','Colorado_02',0),('France_01','France_02',0),('France_01','France_03',0),('France_01','France_04',0),('France_02','France_03',0),('tower','France_02',0),('tower','utm31',0),('tower','utm32',0),('tower','ecef',0),('terrain','Colorado_03',0),('terrain','Colorado_02',0),('terrain','utm13',0),('railway','utm32',0),('railway','ecef',0),('railway','geographic',0),('city','utm31',0),('city','geographic',0),('climate','ecef',0),('climate','ecef',10),('climate','geographic',0),('composition','utm31',0),('composition','utm31',5),('composition','ecef',5),('instances','utm31',0),('instances','ecef',0)]
    jobs=[];headless={};summary=[];native_env=env.copy();native_env['PATH']=str(Path(a.native_proj)/'bin')+';'+str(Path(a.usd_sdk)/'bin')+';'+str(Path(a.usd_sdk)/'lib')+';'+a.native_python+';'+os.environ.get('PATH','')
    native_exe=Path(a.native_build)/'candidateNative.exe';assert native_exe.exists()
    checker_env=native_env.copy();checker_env['PXR_PLUGINPATH_NAME']=str(Path(a.native_build)/'plugInfo.json')+';'+str(ROOT/'schema/generated/plugInfo.json');checker_env['PROJ_DATA']=datadir.get_data_dir()
    checker=Path(a.usd_sdk)/'bin/usdchecker.exe'
    command([str(checker),'--includeKeywords','geospatial','--dumpRules',str(ROOT/'scenes/composition.usda')],out/'usdchecker-valid.log',checker_env)
    assert 'candidateValidation:AuthoredGeospatial' in (out/'usdchecker-valid.log').read_text()
    bad=composition_copy();bad.GetPrimAtPath('/Project/Model').RemoveProperty('crs:position');bad.GetRootLayer().Export(str(out/'invalid-authored.usda'))
    with (out/'usdchecker-invalid.log').open('w') as log:invalid=subprocess.run([str(checker),'--includeKeywords','geospatial',str(out/'invalid-authored.usda')],stdout=log,stderr=subprocess.STDOUT,env=checker_env)
    assert invalid.returncode!=0 and 'placement position' in (out/'usdchecker-invalid.log').read_text()
    native_failures=[]
    for kind in ['invalid_batch','missing_grid','epoch_wrapper','epoch_operation','orientation_value']:
        if kind=='orientation_value':
            bad=composition_copy();pbad=bad.GetPrimAtPath('/Project/Model');pbad.GetAttribute('crs:orientation').Set(Gf.Quatd(0));target=targets['utm31'];expected='orientation/scale'
        else:
            layer=Sdf.Layer.CreateAnonymous('negative.usda');bad=Usd.Stage.Open(layer);bad.GetRootLayer().customLayerData={'geospatialResolutionRequired':True};c=bad.DefinePrim('/CRS','CoordinateReferenceSystem');pbad=bad.DefinePrim('/Coordinates','Scope');pbad.CreateRelationship('crs:binding',custom=True).SetTargets(['/CRS']);coord=pbad.CreateAttribute('data:coordinates',Sdf.ValueTypeNames.Double3Array,custom=True);pbad.CreateRelationship('crs:coordinateProperties',custom=True).SetTargets([coord.GetPath()])
            if kind=='invalid_batch':source=targets['geographic'];points=[[2,48,80],[2,100,80]];target=targets['utm31'];expected='outside domain'
            elif kind=='missing_grid':controls=json.loads((ROOT/'data/partner-controls.json').read_text());source=controls['France_01']['wkt'];points=controls['France_01']['points'];target=targets['France_03'];expected='failed'
            elif kind=='epoch_wrapper':controls=json.loads((ROOT/'data/partner-controls.json').read_text());source=controls['France_05']['wkt'];points=controls['France_05']['points'];target=targets['ecef'];expected='epochs deferred'
            else:source=normalize_wkt(CRS.from_epsg(7789).to_wkt());points=[[4210000,170000,4770000]];target=normalize_wkt(CRS.from_epsg(9988).to_wkt());expected='Epoch dependent'
            c.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=True,variability=Sdf.VariabilityUniform).Set(source);coord.Set(Vt.Vec3dArray([Gf.Vec3d(*p) for p in points]))
        path=out/('negative-'+kind+'.usda');bad.GetRootLayer().Export(str(path));job=out/('negative-'+kind+'.json');dest=out/('negative-'+kind+'-result.json');job.write_text(json.dumps({'stage':str(path),'output_wkt':target,'resources':datadir.get_data_dir().split(os.pathsep)[0] if kind=='missing_grid' else datadir.get_data_dir(),'schema_directory':(ROOT/'schema/generated/plugInfo.json').as_posix()}))
        with (out/('negative-'+kind+'.log')).open('w') as log:failed=subprocess.run([str(native_exe),str(job),str(dest)],stdout=log,stderr=subprocess.STDOUT,env=native_env)
        assert failed.returncode!=0 and not dest.exists();assert expected.lower() in (out/('negative-'+kind+'.log')).read_text().lower()
        native_failures.append({'case':kind,'whole_result_rejected':True,'successful_output_absent':True})
    for source,output,t in pairs:
        name=f'{source}-{output}-t{t}';stage=Usd.Stage.Open(str(ROOT/'scenes'/f'{source}.usda'));assert not validate(stage)
        before={l.identifier:l.ExportToString() for l in stage.GetUsedLayers()};headless[name]=records(stage,targets[output],float(t));assert before=={l.identifier:l.ExportToString() for l in stage.GetUsedLayers()}
        cfg={'name':name,'stage':str(ROOT/'scenes'/f'{source}.usda'),'output_wkt':targets[output],'time':float(t),'resources':datadir.get_data_dir()+';'+a.grids,'schema_directory':(ROOT/'schema/generated/plugInfo.json').as_posix()}
        if (source,output) in [('tower','France_02'),('terrain','Colorado_03'),('instances','utm31')]:
            first=next(iter(headless[name]['frames'].values()));origin=np.array(first)[3,:3]*axis_factors(crs(targets[output]));cfg.update(render=str(pub/(source+'-native.png')),plugin_directory=(Path(a.native_build)/'plugInfo.json').as_posix(),render_origin=origin.tolist())
            if source=='terrain':cfg.update(camera_eye=[250,-450,250],camera_aim=[0,0,0])
            if source=='instances':cfg.update(camera_eye=[60,-90,70],camera_aim=[10,20,0])
        job=out/(name+'-native-job.json');job.write_text(json.dumps(cfg));dest=out/(name+'-native.json');command([str(native_exe),str(job),str(dest)],out/(name+'-native.log'),native_env)
        native=json.loads(dest.read_text());assert native['source_unchanged'];assert not any(x in native['loaded_plugins'] for x in ['usdGeospatial','hdGeospatial'])
        if 'render' in cfg:
            assert native['hydra_geometry_readback'] or native['hydra_instance_readback']['native_instances']
            if source=='instances':assert native['hydra_instance_readback']=={'native_instances':3,'point_instances':3}
        metric=compare(headless[name],native,targets[output]);summary.append({'name':name,'source':source,'output':output,'time':t,'native':metric,'native_proj_version':native['proj_version'],'hydra_filter_reads':native.get('filter_reads',0),'hydra_geometry_readback':native.get('hydra_geometry_readback',{}),'hydra_instance_readback':native.get('hydra_instance_readback',{}),'hydra_live_edit':native.get('live_edit'),'source_unchanged':True,'operations':headless[name]['operations'],'native_operations':native['operations']})
        # Full arrays are retained privately and compressed with source associations for public reproducibility.
        arrays={domain+'|'+k:np.array(v) for domain in ['geometry','measurements','frames','point_instances'] for k,v in headless[name][domain].items()};np.savez_compressed(pub/(name+'-coordinates.npz'),**arrays)
        jobs.append(cfg);print(name,metric['samples'],metric['max_agreement_metres'],flush=True)
    ovjob={'source':ROOT.as_posix(),'python_dependencies':a.python_dependencies,'grids':a.grids,'jobs':jobs,'output':str(out/'ov-results.json')};(out/'ov-job.json').write_text(json.dumps(ovjob));oven=env.copy();oven.update(GEOBUILD_OV_JOB=str(out/'ov-job.json'),GEOBUILD_OV_ERROR=str(out/'ov-error.txt'),GEOBUILD_OV_SDK=a.ov_sdk,PYTHONNOUSERSITE='1')
    command([str(Path(a.ov_sdk)/'python/python.exe'),'-s',str(ROOT/'ov/launch.py')],out/'ov.log',oven)
    assert not (out/'ov-error.txt').exists();ov=json.loads((out/'ov-results.json').read_text());assert len(ov['jobs'])==len(jobs)
    for row,job in zip(summary,ov['jobs']):
        assert row['name']==job['name'];assert job['source_unchanged'] and job['source_ingested'];row['ov']=compare(headless[row['name']],job['records'],targets[row['output']]);row['ov_live_updates']=job['live_updates'];row['ov_edits']=job['edits'];row['ov_request_changes']=job['requests'];row['ov_failure_recovery']=job['failures'];row['ov_geometry_readback']=job['live_runtime'].get('geometry_readback',{});row['ov_measurement_properties_readback']=job['live_runtime'].get('measurement_readback',0)
    controls=json.loads((ROOT/'data/partner-controls.json').read_text());control_report=[]
    for src,dst in [('Colorado_01','Colorado_02'),('Colorado_02','Colorado_03'),('France_01','France_02'),('France_01','France_03'),('France_01','France_04')]:
        actual,tr=convert(controls[src]['wkt'],controls[dst]['wkt'],controls[src]['points']);expected=np.array(controls[dst]['points']);c=CRS.from_wkt(controls[dst]['wkt'])
        if c.is_geographic:actual,_=convert(c,CRS.from_epsg(4978),actual);expected,_=convert(c,CRS.from_epsg(4978),expected);err=np.linalg.norm(actual-expected,axis=1)
        else:err=np.linalg.norm((actual-expected)*axis_factors(c),axis=1)
        control_report.append({'source':src,'output':dst,'controls':len(expected),'max_csv_discrepancy_metres':float(err.max()),'reference':'Provider CSVs were computed with PROJ 9.8.1. This is intake/rounding evidence, not independent-engine or survey certification.'})
    extent=[];s=composition_copy();root=s.GetPrimAtPath('/Project/Model');root.GetAttribute('crs:position').Set((500000,5400000,80));root.GetAttribute('crs:orientation').Set(Gf.Quatd(1));root.GetAttribute('crs:scale').Set((1,1,1));UsdGeom.Xformable(root).ClearXformOpOrder();r=Resolver(s)
    for distance in [1.,10.,100.,1000.,10000.,100000.]:
        sample=np.array([[x,y,0] for x in np.linspace(-distance,distance,17) for y in np.linspace(-distance,distance,17)]);frame,rr=r.frame(root,targets['ecef']);full=r.full_points(root,sample,targets['ecef']);affine=homogeneous(sample,frame);err=np.linalg.norm(full.points-affine,axis=1);extent.append({'half_extent_metres':distance,'samples':len(sample),'sampled_max_affine_discrepancy_metres':float(err.max()),'claim':'Sampled finite domain only; no certified continuous surface bound'})
    exports=[]
    for source,output in [('composition','utm31'),('tower','utm31'),('terrain','Colorado_02'),('city','utm31'),('climate','ecef')]:
        s=Usd.Stage.Open(str(ROOT/'scenes'/f'{source}.usda'));path=pub/(source+'-export.usda');d=export(s,path,targets[output],[0.,5.,10.]);assert not validate(d);fresh=Usd.Stage.Open(str(path));rr=records(fresh,targets[output],5.)
        # Match exported geometry in traversal order, independently re-resolving the new asset.
        before=records(s,targets[output],5.);one=[v for v in before['geometry'].values()];two=[v for v in rr['geometry'].values()];maxerr=0.
        for x,y in zip(one,two):maxerr=max(maxerr,float(np.linalg.norm((np.array(x)-np.array(y))*axis_factors(crs(targets[output])),axis=1).max()))
        assert len(one)==len(two);assert maxerr<.002
        measurement_error=0.;preserved=0
        for t in [0.,5.,10.]:
            original=records(s,targets[output],t);derived=records(fresh,targets[output],t)
            assert len(original['measurements'])==len(derived['measurements'])
            for x,y in zip(original['measurements'].values(),derived['measurements'].values()):
                measurement_error=max(measurement_error,float(np.linalg.norm((np.array(x)-np.array(y))*axis_factors(crs(targets[output])),axis=1).max()))
        for src,dst in zip([p for p in s.Traverse() if p.GetRelationship('crs:coordinateProperties') and p.GetRelationship('crs:coordinateProperties').HasAuthoredTargets()],[p for p in fresh.Traverse() if p.GetRelationship('crs:coordinateProperties') and p.GetRelationship('crs:coordinateProperties').HasAuthoredTargets()]):
            roles=set(src.GetRelationship('crs:coordinateProperties').GetTargets())
            for attr in src.GetAttributes():
                if attr.GetName().startswith('data:') and attr.GetPath() not in roles:
                    copied=dst.GetAttribute(attr.GetName());assert copied and copied.GetTimeSamples()==attr.GetTimeSamples()
                    for t in [Usd.TimeCode.Default(),*[Usd.TimeCode(x) for x in attr.GetTimeSamples()]]:assert np.array_equal(np.array(attr.Get(t)),np.array(copied.Get(t)))
                    preserved+=1
        assert measurement_error<.002
        ex={'source':source,'output':output,'samples':[0,5,10],'geometry_max_roundtrip_metres':maxerr,'measurement_max_roundtrip_metres':measurement_error,'noncoordinate_properties_preserved':preserved,'fresh_reader':True,'no_private_resolved_flag':True,'measurement_properties':len(rr['measurements'])};exports.append(ex)
    from geobuild.evidence import plots_and_products
    analysis=plots_and_products(ROOT,pub,headless,targets)
    public_files={p.name:sha(p) for p in sorted(pub.iterdir()) if p.is_file()}
    source_files={p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*') if p.is_file() and p.suffix in ['.py','.cpp','.h','.usda','.json','.md','.txt','.npz','.nc','.usdz','.geojson','.csv','.xml','.kit'] and not (p.parent==ROOT and p.name=='README.md') and not any(x in p.parts for x in ['__pycache__','.pytest_cache','delivery','results','.codex-finalizer','collateral'])}
    report={'status':'executed candidate; approval and continuous-bound questions remain explicit','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'inputs':inputs,'source_files':source_files,'toolchain':{'headless_usd':list(Usd.GetVersion()),'python':sys.version.split()[0],'pyproj_proj':proj_version_str,'ov_usd':ov['usd_version'],'native_usd':[0,26,11],'native_usd_core_source':'c58778b6b5c667123430b6bbed810778bf336e9c','native_executable_sha256':sha(native_exe),'native_projection_dll_sha256':sha(Path(a.native_proj)/'bin/proj_9_4.dll'),'native_projection_TIFF_support':True,'frame_probe_metres':1.,'probe_checks_metres':[.25,4.]},'tests':{'passed':len(cases),'failed':0},'stock_usdchecker':{'valid_scene_accepted':True,'invalid_placement_rejected':True,'native_validator_discovered_by_keyword':True},'native_failures':native_failures,'comparisons':summary,'partner_controls':control_report,'extent_samples':extent,'exports':exports,'analysis':analysis,'delivery_files':public_files,'limitations':['Independent authored-scene runtimes share PROJ; this is not independent geodetic-engine certification.','R24 continuous surface/error-bound guarantee remains unresolved; finite samples do not settle it.','Experimental field definitions, post context, lexical normal form, measurement carrier, declaration and export record require group review.','Coordinate epochs are explicitly unsupported; frame epochs are preserved.','Rail height interpretation and generated measurement times/heights are conditional and labeled.','Operation accuracy fields are engine-attributed estimates, not combined bounds for post transforms, affine approximation or survey truth.']}
    (pub/'run-report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'headless-results.json').write_text(json.dumps(headless)+'\n');print(json.dumps({'tests':len(cases),'comparison_jobs':len(summary),'delivery':str(pub)},indent=2))
if __name__=='__main__':main()
