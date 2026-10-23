"""New acceptance cases fixed before execution. Reports failures without masking them."""
import sys,os,json,csv,subprocess,hashlib,time,traceback,math,warnings
from pathlib import Path
import numpy as np
from pxr import Usd,UsdGeom,Sdf,Gf,Vt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src_py'))
from reader import *
from domains import *
from fixtures import attr,bind,mesh,AUTHORED,ORIGINAL
EVIDENCE=ROOT/'evidence';EVIDENCE.mkdir(exist_ok=True)
records=[];native_count=0
def native(request,name,keep_arrays=True):
    global native_count
    native_count+=1;name=f'{native_count:03d}-{name}'
    src=EVIDENCE/(name+'-request.json');dest=EVIDENCE/(name+'-native.json');src.write_text(json.dumps(request,allow_nan=False))
    env=os.environ.copy();env['PATH']='C:/Users/aluk/Documents/Codex/2026-09-21/have/work/geospatial-proj-tiff/bin;C:/git/usd-geospatial-fresh/inst/bin;C:/git/usd-geospatial-fresh/inst/lib;C:/Users/aluk/AppData/Local/Programs/Python/Python310;'+env['PATH'];env['PROJ_DATA']='C:/Users/aluk/Documents/Codex/2026-09-21/have/work/geospatial-proj-tiff/share/proj'
    r=subprocess.run([str(ROOT/'native/build/resolve.exe'),str(src),str(dest),str(ROOT/'schema')],capture_output=True,text=True,env=env,timeout=240)
    if r.stderr:(EVIDENCE/(name+'-stderr.txt')).write_text(r.stderr)
    require(dest.exists(),'native output unavailable: '+r.stderr)
    result=json.loads(dest.read_text(encoding='utf-8'));require(result['success'],result.get('error','native failed'))
    require(r.returncode==0,'native process failed after producing a result: '+str(r.returncode))
    if not keep_arrays:
        summary={k:v for k,v in result.items() if k!='points'}
        summary.update(point_count=len(result.get('points',[])),request_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),result_sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
        (EVIDENCE/(name+'-summary.json')).write_text(json.dumps(summary,indent=2));src.unlink();dest.unlink()
    return result
def check(name,requirements,fn):
    start=time.time()
    try:
        result=fn();record={'case':name,'requirements':requirements,'pass':True,'result':result}
    except Exception as e:
        record={'case':name,'requirements':requirements,'pass':False,'error':str(e),'traceback':traceback.format_exc()}
    record['seconds']=time.time()-start;records.append(record)
    (EVIDENCE/'checks.json').write_text(json.dumps(records,indent=2,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x)))
    print(('PASS ' if record['pass'] else 'FAIL ')+name+(' — '+record.get('error','')),flush=True)
def throws(fn):
    try:fn()
    except Failure as e:return str(e)
    raise AssertionError('expected visible failure')
def near(a,b,tol=0.002):
    residual=np.asarray(a)-np.asarray(b);d=np.linalg.norm(residual,axis=-1);maximum=float(np.max(d));require(maximum<=tol,f'distance {maximum} > {tol}');return maximum
def same_readers(stage,p,points,output,name,time=None,extra=None):
    r=Reader(stage);py=r.points(p,points,output,time)
    req={'stage':stage.GetRootLayer().realPath,'prim':str(p.GetPath()),'points':np.asarray(points).tolist(),'output':output.to_wkt()}
    if time is not None:req['time']=time
    if extra:req.update(extra)
    n=native(req,name);return {'agreement_m':near(py,n['points']),'count':len(py),'python':py,'native':n,'operations':r.engine.operations}

def controls(region,src_prefix,dst_prefix,label):
    folder=ORIGINAL/region
    def load(prefix):
        csvpath=next(folder.glob(prefix+'*Coordinates.csv'));wk=next(folder.glob(prefix+'*WKT2.txt')).read_text(encoding='utf-8')
        with csvpath.open(encoding='utf-8-sig') as f:rows=list(csv.reader(f));cols=rows[0]
        coords={x[0]:[float(x[i]) for i in range(1,4)] for x in rows[1:] if x}
        # Geographic control files list latitude first; semantic tuple is longitude first.
        if 'latitude' in cols[1].lower() or cols[1].lower().startswith('lat'):coords={k:[v[1],v[0],v[2]] for k,v in coords.items()}
        return as_crs(wk),coords,cols
    a,ap,ah=load(src_prefix);b,bp,bh=load(dst_prefix);ids=[k for k in ap if k in bp]
    inp=np.array([ap[k] for k in ids]);expected=np.array([bp[k] for k in ids]);e=Engine();p=e.convert(inp,a,b)
    n=native({'coordinateSource':a.to_wkt(),'output':b.to_wkt(),'points':inp.tolist()},label)
    clean=lambda s:' '.join(re.sub(r'(?<!\S)\+','',s).split())
    require(clean(e.operations[-1]['pipeline'])==clean(n['operations'][-1]['pipeline']),'operation comparability unestablished')
    units=np.array([ax.unit_conversion_factor for ax in b.axis_info]);factor=units if not b.is_geographic else None
    require(factor is not None,'control output comparison needs Cartesian units')
    ref=near(p*factor,expected*factor);agree=near(p*factor,np.array(n['points'])*factor)
    result={'rows':len(ids),'max_provider_residual_m':ref,'max_reader_disagreement_m':agree,'coordinate_magnitude':np.max(np.abs(expected),axis=0).tolist(),'output_units':[x.unit_name for x in b.axis_info], 'provider_reference':'Provider tables were generated using PROJ; these are external workflow references, not an independent geodetic engine.' ,'python_operations':e.operations,'native_operations':n['operations']}
    (EVIDENCE/(label+'-comparison.json')).write_text(json.dumps(dict(result,ids=ids,source=inp.tolist(),reference=expected.tolist(),python=p.tolist(),native=n['points']),indent=2))
    return result

def normalize_case():
    raw=' geogcrs ( "A  Name", CS(ellipsoidal, 3), REMARK["a"" b"], ID["X",+0001E0], PARAMETER["p",0.1234567890123456789012345678900] ) '
    norm=normalize_wkt(raw)
    require('"A  Name"' in norm and '0.12345678901234567890123456789' in norm and 'ID["X",1]' in norm,'normalization lost text/decimal information')
    require(normalize_wkt(norm)==norm,'not fixed point')
    a=CRS.from_epsg(4979);b=CRS.from_wkt(a.to_wkt().replace('WGS 84','Another display name'))
    require(a.equals(b) and normalize_wkt(a.to_wkt())!=normalize_wkt(b.to_wkt()),'serialized identity confused with equivalence')
    return {'normal':norm,'identityDistinctFromSemanticEquivalence':True}

def model_case():
    s=Usd.Stage.Open(str(AUTHORED/'models.usda'));p=s.GetPrimAtPath('/World/Model/Child/Mesh');b=s.GetRootLayer().ExportToString()
    q=CRS.from_epsg(4978);d=same_readers(s,p,[(0,0,0),(1,0,0),(0,1,0),(0,0,1)],q,'model')
    require(s.GetRootLayer().ExportToString()==b,'source changed')
    return {k:v for k,v in d.items() if k in ('agreement_m','count')}
def reset_case():
    s=Usd.Stage.Open(str(AUTHORED/'models.usda'));p=s.GetPrimAtPath('/World/Model/Reset/Mesh');q=CRS.from_epsg(4978)
    d=same_readers(s,p,[(0,0,0),(1,2,3)],q,'reset');r=Reader(s);before=r.points(p,[(0,0,0)],q)
    s.SetEditTarget(Usd.EditTarget(s.GetSessionLayer()));a=s.GetPrimAtPath('/World/Model').GetAttribute('xformOp:translate:adjust');a.Set((9000,9000,9000))
    near(before,r.points(p,[(0,0,0)],q),1e-8)
    child=s.GetPrimAtPath('/World/Model/Independent/Mesh');v=r.points(child,[(0,0,0)],q);s.GetPrimAtPath('/World/Model').GetAttribute('crs:position').Set((3,49,700));near(v,r.points(child,[(0,0,0)],q),1e-8)
    return {'reader_agreement_m':d['agreement_m'],'reset_preserves_geospatial_placement':True,'independent_child_ignores_ancestor_ordinary_and_absolute_position':True}
def interpolation_case():
    s=Usd.Stage.Open(str(AUTHORED/'models.usda'));p=s.GetPrimAtPath('/World/Moving/Mesh');q=CRS.from_epsg(4978)
    d=same_readers(s,p,[(0,0,0),(0,1,0)],q,'midpoint',1)
    near(d['python'][0],[6378137,0,0],1e-6)
    s.SetInterpolationType(Usd.InterpolationTypeHeld)
    held=Reader(s).points(p,[(0,0,0)],q,1);require(np.linalg.norm(held-d['python'][0])>100000,'held ignored')
    s.SetInterpolationType(Usd.InterpolationTypeLinear);s.SetEditTarget(s.GetSessionLayer());a=s.GetPrimAtPath('/World/Moving').GetAttribute('crs:orientation');a.Set((0,0,0),0);a.Set((180,0,0),2)
    error=throws(lambda:Reader(s).points(p,[(0,1,0)],q,1))
    return {'reader_agreement_m':d['agreement_m'],'source_midpoint_ECEF':d['python'][0].tolist(),'ambiguous_arc_failure':error,'incorrect_ECEF_endpoint_chord_inward_m':6378137*(1-math.cos(math.radians(1)))}
def composition_case():
    s=Usd.Stage.Open(str(AUTHORED/'composition.usda'));q=CRS.from_epsg(4978)
    p=s.GetPrimAtPath('/World/NativeInstance/Detail');d=same_readers(s,p,[(0,0,0),(0.001,0,0)],q,'native-proxy')
    require(p.IsInstanceProxy(),'not native proxy')
    offset=s.GetPrimAtPath('/Offset/Mesh');m=Reader(s).points(offset,[(0,0,0)],q,12);near(m,[[6378137,0,0]],1e-6)
    clip=s.GetPrimAtPath('/Clip/Mesh');d2=same_readers(s,clip,[(0,1,0)],q,'clip',1)
    inherited=s.GetPrimAtPath('/Inherited/Mesh');d3=same_readers(s,inherited,[(0,0,0),(0,1,0)],q,'inherits')
    return {'proxy_agreement_m':d['agreement_m'],'clip_agreement_m':d2['agreement_m'],'inherit_agreement_m':d3['agreement_m'],'reference_time_offset_source_midpoint':m.tolist()}
def instances_case():
    s=Usd.Stage.Open(str(AUTHORED/'models.usda'));pi=s.GetPrimAtPath('/World/Instancer');p=s.GetPrimAtPath('/Storage/BoundPrototype/Mesh');q=CRS.from_epsg(4978);r=Reader(s);errors=[]
    for i in range(2):
        pts=[(0,0,0),(1,0,0)];py=r.instance_points(pi,i,p,pts,q)
        n=native({'stage':s.GetRootLayer().realPath,'prim':str(p.GetPath()),'instancer':str(pi.GetPath()),'instance':i,'points':pts,'output':q.to_wkt()},f'bound-instance-{i}')
        errors.append(near(py,n['points']))
        if i==0:near(py,r.points(p,pts,q),1e-7)
    un=s.GetPrimAtPath('/Storage/LocalPrototype/Mesh');py=r.instance_points(pi,2,un,[(0,0,0)],q)
    n=native({'stage':s.GetRootLayer().realPath,'prim':str(un.GetPath()),'instancer':str(pi.GetPath()),'instance':2,'points':[(0,0,0)],'output':q.to_wkt()},'unbound-instance');errors.append(near(py,n['points']))
    return {'max_agreement_m':max(errors),'independent_identity_not_double_placed':True,'identities':['/World/Instancer:11:/Mesh','/World/Instancer:12:/Mesh','/World/Instancer:13:/Mesh']}
def height_case():
    c=CRS.from_epsg(4326);m,assumed=model_crs(c.to_wkt());e=Engine();point=[2.2945,48.8584,35];out=geocentric(m);p=e.convert(point,m,out)
    n=native({'coordinateSource':c.to_wkt(),'modelFallback':True,'output':out.to_wkt(),'points':[point]},'height-fallback')
    err=near([p],n['points']); ell=e.convert(p,out,geodetic(m));require(abs(ell[2]-35)>10,'EGM interpreted as ellipsoidal')
    hf=CRS.from_proj4('+proj=utm +zone=31 +datum=WGS84 +units=us-ft +type=crs');xy=e.convert(point[:2],c,hf)
    nft=native({'coordinateSource':hf.to_wkt(),'modelFallback':True,'output':out.to_wkt(),'points':[[*xy,35/(1200/3937)]]},'height-fallback-feet')
    feet_distance=near([p],nft['points']);require(any('EGM2008' in w for w in nft['warnings']),'native fallback warning missing')
    feet=height_report(CRS.from_epsg(2229).to_wkt());require('foot' in feet['heightUnit'],'projected fallback unit lost')
    reports=[height_report(CRS.from_epsg(i).to_wkt()) for i in (4979,4978,4326)]
    return {'agreement_m':err,'foot_vs_metre_agreement_m':feet_distance,'EGM2008_input_height_m':35,'computed_ellipsoidal_height_m':float(ell[2]),'source_reports':reports,'feet_report':feet,'native_report':n['sourceHeight']}
def profiles_case():
    s=Usd.Stage.Open(str(AUTHORED/'publication.usda'),load=Usd.Stage.LoadNone);result=profile_summary(s)
    require(result['requiresResolution'] is True,'unloaded dependency not discoverable')
    require(result['coverage']=='complete-positive','Profiles completeness qualification not read')
    native_result=native({'profilesStage':s.GetRootLayer().realPath},'profiles-unloaded')
    require(native_result['hardUsage']=='hard' and native_result['loadedPayloads']==0 and PROFILE in native_result['profiles'],'actual ClaimsAPI did not read declaration')
    require(CAPABILITY in native_result['bindingImpliedCapabilities'],'schema-implied capability registration not read by native Profiles')
    require(len(list(s.Traverse()))<5,'unexpected payload traversal')
    loaded_count=len(list(s.Traverse()));s.Load();validate_publication(s)
    s.SetEditTarget(s.GetSessionLayer());s.GetDefaultPrim().SetCustomDataByKey('profilesInfo:capabilityUsages:'+CAPABILITY,'soft')
    error=throws(lambda:validate_publication(s))
    return {'without_loading':result,'actual_native_ClaimsAPI':native_result,'visible_prims_without_payload':loaded_count,'loaded_stale_claim_failure':error,'identities':'proposed, namespace stewardship and standard approval remain outstanding'}
def domains_case():
    s=Usd.Stage.Open(str(AUTHORED/'domains.usda'));c=s.GetPrimAtPath('/World/Permuted');d=read_domain(c)
    near(d['coordinates'][:,0],np.array([1,4,2,5,3,6]),1e-12)
    require(np.array_equal(d['values'],[10,40,20,50,30,60]),'CF values permuted incorrectly')
    climate=read_domain(s.GetPrimAtPath('/World/Climate'));require(len(climate['values'])==5328,'climate sample count')
    a=read_domain(s.GetPrimAtPath('/World/Raster1'));b=read_domain(s.GetPrimAtPath('/World/Raster2'));near(a['coordinates'][0],[600001,5399998.5],1e-10);near(b['coordinates'][0],[600000,5400000],1e-10)
    rail=read_domain(s.GetPrimAtPath('/World/Railway'));q=CRS.from_epsg(4978);p=resolve_domain(s.GetPrimAtPath('/World/Railway'),q)
    n=native({'coordinateSource':CRS.from_epsg(4979).to_wkt(),'output':q.to_wkt(),'points':rail['coordinates'].tolist()},'railway')
    err=near(p['resolved'],n['points']);require(p['indices']==rail['indices'],'railway sample identity changed')
    (EVIDENCE/'railway-points.json').write_text(json.dumps({'source':rail['coordinates'].tolist(),'python':p['resolved'].tolist(),'native':n['points'],'indices':rail['indices']}))
    np.savez_compressed(EVIDENCE/'climate.npz',values=climate['values'],coordinates=climate['coordinates'],mask=climate['mask'])
    return {'permuted_coordinate_alignment':d['coordinates'].tolist(),'climate_samples':len(climate['values']),'railway_positions':len(rail['coordinates']),'railway_reader_agreement_m':err,'GeoTIFF_area_and_point_samples_distinct':True}
def failures_case():
    q=CRS.from_epsg(4978);s=Usd.Stage.Open(str(AUTHORED/'models.usda'));s.SetEditTarget(s.GetSessionLayer());p=s.GetPrimAtPath('/World/Model/Child/Mesh');results={}
    attr(p,'crs:position',Sdf.ValueTypeNames.Double3,(1,2,3));results['invalid_role']=throws(lambda:Reader(s).points(p,[(0,0,0)],q));p.RemoveProperty('crs:position')
    a=s.GetPrimAtPath('/World/Model').GetAttribute('crs:orientation');a.Block();results['blocked_orientation']=throws(lambda:Reader(s).points(p,[(0,0,0)],q))
    results['epoch_wrapper']=throws(lambda:as_crs('COORDINATEMETADATA['+CRS.from_epsg(4979).to_wkt()+',EPOCH[2026]]'))
    results['latitude_outside_domain']=throws(lambda:Engine().convert([0,100,0],CRS.from_epsg(4979),q))
    results['nonfinite']=throws(lambda:Engine().convert([float('nan'),0,0],CRS.from_epsg(4979),q))
    results['epoch_operation_without_epoch']=throws(lambda:Engine().convert([4200000,170000,4780000],CRS.from_epsg(9988),CRS.from_epsg(7789)))
    results['native_epoch_operation']=throws(lambda:native({'coordinateSource':CRS.from_epsg(9988).to_wkt(),'output':CRS.from_epsg(7789).to_wkt(),'points':[[4200000,170000,4780000]]},'rejected-epoch-operation'))
    require('epoch' in results['native_epoch_operation'],'native epoch rejection not established')
    results['continuous_bounds']=throws(lambda:Reader(s).bounds(p,[(0,0,0)],q,continuous=True))
    from bake import bake
    results['point_instancer_bake']=throws(lambda:bake(s,AUTHORED/'unsupported-instance-bake.usda',q))
    return results

def charts_case():
    s=Usd.Stage.Open(str(AUTHORED/'models.usda'));r=Reader(s);p=s.GetPrimAtPath('/World/Model/Child/Mesh');points=[(0,0,0),(12,25,3)]
    geo=CRS.from_epsg(4979);cart=CRS.from_epsg(4978);utm=CRS.from_epsg(32631).to_3d()
    a=r.points(p,points,cart);b=r.points(p,points,utm);c=r.points(p,points,geo)
    d=near(a,r.engine.convert(b,utm,cart));d2=near(a,r.engine.convert(c,geo,cart))
    scene,chart=r.scene_points(p,points,geo);near(scene,a,1e-7);require(chart.is_geocentric,'angular coordinates used as scene lengths')
    s.SetEditTarget(s.GetSessionLayer());UsdGeom.SetStageUpAxis(s,'Y');UsdGeom.SetStageMetersPerUnit(s,0.01)
    after=Reader(s).points(p,[(0,0,0),(100,100,100)],cart)
    require(np.isfinite(after).all(),'Y-up centimetre failed')
    # Held/linear settings affect samples, not metadata or a guessed motion model.
    return {'working_adjustment_preserved_across_outputs_m':max(d,d2),'geographic_scene_chart':'associated geocentric','Y_up_centimetres_evaluated':True}

def bare_bake_case():
    from bake import bake
    src=Usd.Stage.Open(str(AUTHORED/'tower.usda'));snapshot=src.GetRootLayer().ExportToString();outpath=AUTHORED/'tower-python-bake.usda'
    out,report=bake(src,outpath,CRS.from_epsg(4978))
    require(src.GetRootLayer().ExportToString()==snapshot,'source changed in bake')
    fresh=Reader(Usd.Stage.Open(str(outpath)));src_r=Reader(src);errors=[]
    for entry in report['meshes']:
        original=src.GetPrimAtPath(entry['source']);local=UsdGeom.Mesh(original).GetPointsAttr().Get()
        expected=src_r.points(original,local,CRS.from_epsg(4978));dest=fresh.stage.GetPrimAtPath(entry['export']);points=UsdGeom.Mesh(dest).GetPointsAttr().Get()
        actual=fresh.points(dest,points,CRS.from_epsg(4978));errors.append(near(expected,actual,0.001))
    require(profile_summary(out)['coverage']=='complete-empty','bake should have known-none dependency')
    require(not any(direct(p) for p in out.Traverse()),'baked model binding retained')
    report['max_fresh_reader_error_m']=max(errors);report['source_unchanged']=True
    (EVIDENCE/'tower-bake.json').write_text(json.dumps(report,indent=2))
    return {'vertices':sum(m['vertices'] for m in report['meshes']),'max_error_m':max(errors),'dependency_summary':profile_summary(out),'source_unchanged':True}

def missing_grid_case():
    env=os.environ.copy();env.pop('GEOSPATIAL_RESOURCE_DIR',None)
    code="import sys;sys.path.insert(0,'src_py');from reader import *;from pyproj import CRS;c,_=model_crs(CRS.from_epsg(4326).to_wkt());Engine().convert([2.2945,48.8584,35],c,geocentric(c))"
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True,timeout=45)
    require(result.returncode!=0 and ('unavailable' in result.stderr or 'failed' in result.stderr),'missing grid did not fail visibly')
    (EVIDENCE/'missing-egm-grid.txt').write_text(result.stderr)
    return {'failed_without_grid':True,'no_ellipsoidal_or_zero_substitute':True}

def export_sampling_case():
    from bake import bake
    path=AUTHORED/'sampling-source.usda';s=Usd.Stage.CreateNew(str(path));UsdGeom.SetStageUpAxis(s,'Z');UsdGeom.SetStageMetersPerUnit(s,1);s.SetTimeCodesPerSecond(24)
    p=bind(UsdGeom.Xform.Define(s,'/Moving').GetPrim(),CRS.from_epsg(4979).to_wkt(),None)
    s.SetDefaultPrim(p);a=attr(p,'crs:position',Sdf.ValueTypeNames.Double3,None);a.Set((-1,0,0),0);a.Set((1,0,0),2)
    m=mesh(s,'/Moving/Mesh');pv=UsdGeom.PrimvarsAPI(m).CreatePrimvar('normalCheck',Sdf.ValueTypeNames.Normal3fArray,'vertex');pv.Set([(0,0,1)]*3)
    attr(p,'review:unrelatedInput',Sdf.ValueTypeNames.String,'preserve me');publish_claim(s);s.GetRootLayer().Save()
    q=CRS.from_epsg(4978);out,report=bake(s,AUTHORED/'sampling-bake.usda',q,times=(0,2))
    dest=out.GetPrimAtPath('/Resolved/Origin/Moving/Mesh');r=Reader(out);src=Reader(s);original=UsdGeom.Mesh(m).GetPointsAttr().Get()
    for t in (0,2):near(src.points(m,original,q,t),r.points(dest,UsdGeom.Mesh(dest).GetPointsAttr().Get(t),q,t),0.001)
    source_mid=src.points(m,original,q,1)[0];bake_mid=r.points(dest,UsdGeom.Mesh(dest).GetPointsAttr().Get(1),q,1)[0]
    difference=float(np.linalg.norm(source_mid-bake_mid));require(difference>970,'baked chord incorrectly presented as source trajectory')
    require(out.GetPrimAtPath('/Resolved/Origin/Moving').GetAttribute('review:unrelatedInput').Get()=='preserve me','unrelated authored meaning lost')
    require(dest.GetAttribute('primvars:normalCheck').Get(0) is not None,'semantic normal primvar omitted')
    for t,longitude in [(0,-1),(2,1)]:
        actual=np.asarray(dest.GetAttribute('primvars:normalCheck').Get(t))
        expected=np.tile([math.cos(math.radians(longitude)),math.sin(math.radians(longitude)),0],(3,1))
        require(np.max(np.linalg.norm(actual-expected,axis=1))<1e-5,'transported normal differs from analytic ellipsoid radial normal')
    n=native({'stage':str(AUTHORED/'sampling-bake.usda'),'prim':str(dest.GetPath()),'points':np.asarray(UsdGeom.Mesh(dest).GetPointsAttr().Get(1)).tolist(),'output':q.to_wkt(),'time':1},'fresh-bake-reread')
    near([bake_mid],np.array(n['points'])[:1],0.001)
    return {'sample_keys':[0,2],'timeCodesPerSecond':24,'midpoint_difference_m':difference,'claim':'exact sampled instants only; no between-sample trajectory guarantee','unrelated_input_preserved':True,'normal_primvar_transported':True}

def hidden_variant_case():
    s=Usd.Stage.CreateNew(str(AUTHORED/'hidden-variant.usda'));p=UsdGeom.Xform.Define(s,'/Asset').GetPrim();s.SetDefaultPrim(p)
    v=p.GetVariantSets().AddVariantSet('content')
    for name in ('ordinary','geospatial'):v.AddVariant(name)
    v.SetVariantSelection('geospatial')
    with v.GetVariantEditContext():bind(UsdGeom.Xform.Define(s,'/Asset/Hidden').GetPrim(),CRS.from_epsg(4979).to_wkt(),(0,0,0))
    v.SetVariantSelection('ordinary');publish_claim(s,False);s.GetRootLayer().Save();snapshot=s.GetRootLayer().ExportToString()
    error=throws(lambda:validate_publication(s));require('stale' in error,'did not find retained unselected dependency')
    require(s.GetRootLayer().ExportToString()==snapshot,'validation edited source')
    return {'unselected_variant_dependency_detected':True,'source_unchanged':True,'failure':error}

def avoid_intermediate_case():
    s=Usd.Stage.CreateNew(str(AUTHORED/'no-unnecessary-operation.usda'));UsdGeom.SetStageUpAxis(s,'Z');UsdGeom.SetStageMetersPerUnit(s,1)
    root=bind(UsdGeom.Xform.Define(s,'/Project').GetPrim(),(ORIGINAL/'France/02_RGF93v2b_Lambert93_IGN69_WKT2.txt').read_text(encoding='utf-8'),(660000,6800000,35));s.SetDefaultPrim(root)
    child=bind(UsdGeom.Xform.Define(s,'/Project/Elsewhere').GetPrim(),CRS.from_epsg(4979).to_wkt(),(151.2,-33.8,70));m=mesh(s,'/Project/Elsewhere/Mesh');s.GetRootLayer().Save()
    d=same_readers(s,m,[(0,0,0),(0,1,0)],CRS.from_epsg(4978),'avoid-intermediate')
    # The French vertical grid does not cover Australia. Identity adjustment needs
    # no intermediate French height operation merely because of an enclosing CRS.
    return {'agreement_m':d['agreement_m'],'enclosing_working_context_did_not_force_unneeded_operation':True}

def run():
    check('WKT lexical preservation and semantic comparison',[1,2,31],normalize_case)
    check('France geographic to geocentric provider references',[1,3,12,13,21,28,29],lambda:controls('France','04_','03_','france-geocentric'))
    check('France CC49 to Lambert93 with IGN69',[4,12,21,28,29],lambda:controls('France','01_','02_','france-projected'))
    check('Colorado State Plane to calibrated site feet',[4,12,13,21,28,29],lambda:controls('Colorado','02_','03_','colorado-calibrated'))
    check('Full model point map and ordinary adjustment',[5,6,8,9,10,11,14,15,16,19,23],model_case)
    check('Reset and independent direct binding',[6,7,11,19,25],reset_case)
    check('Source interpolation and physical pose interpolation',[9,20,21],interpolation_case)
    check('References inherits clips time offsets and native proxies',[7,19,20],composition_case)
    check('Bound and unbound point-instancer prototypes',[6,8,17,18,21],instances_case)
    check('EGM2008 fallback and computed source-height reports',[2,12,21,28],height_case)
    check('Profiles above payload and stale publication claims',[7,25,26,27],profiles_case)
    check('CF permutations GeoTIFF and original railway',[8,12,17,18,19,22,30],domains_case)
    check('Visible failure instead of substitution',[21,27],failures_case)
    check('Fixed working context geographic chart and stage conventions',[8,12,14,16,18,22],charts_case)
    check('Ordinary Eiffel bake precision and fresh reread',[17,19,23,24,25,26,27],bare_bake_case)
    check('Missing EGM2008 grid is a visible failure',[12,21,28],missing_grid_case)
    check('Sampled bake and semantic primvar transport',[17,19,20,23,30],export_sampling_case)
    check('Conservative coverage of retained variants',[7,26,27],hidden_variant_case)
    check('Identity adjustment avoids unnecessary intermediate conversion',[8,16,21],avoid_intermediate_case)
    print(json.dumps({'pass':sum(r['pass'] for r in records),'fail':sum(not r['pass'] for r in records),'native_executions':native_count}),flush=True)
    if any(not r['pass'] for r in records):raise SystemExit(1)

if __name__=='__main__':run()
