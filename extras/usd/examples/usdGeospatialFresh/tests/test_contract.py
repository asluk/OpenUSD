"""Controls declared from proposal semantics and source tables, before execution."""
import hashlib,json,math,os,subprocess,sys
from pathlib import Path
import numpy as np
import pytest
from pyproj import CRS
from pxr import Gf,Sdf,Usd,UsdGeom,Vt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src_py'))
from reader import *
from formats import decode,resolve
F=ROOT/'inputs/authored';E=ROOT/'evidence';E.mkdir(exist_ok=True)
G=(F/'geographic.wkt').read_text();C=(F/'ecef.wkt').read_text()

def s():return Usd.Stage.Open(str(F/'controls.usda'))
def reader(time=None,output=C):return Reader(s(),output,time)
def prim(r,path):return r.stage.GetPrimAtPath('/World/'+path)
def native(stage,queries,output=C,time=None,held=False,tag='query',load_none=False,without_grids=False):
    req={'stage':str(stage),'output_wkt':output,'queries':queries,'held':held}
    req['load_none']=load_none
    if time is not None:req['time']=time
    p=E/(tag+'-request.json');out=E/(tag+'-native.json');p.write_text(json.dumps(req),encoding='utf-8')
    env=os.environ.copy();projroot=Path(env.get('GEOSPATIAL_PROJ_ROOT',str(ROOT.parent/'geospatial-proj-tiff')));usdroot=Path(env.get('GEOSPATIAL_USD_ROOT','C:/git/usd-geospatial-fresh/inst'));pyroot=env.get('GEOSPATIAL_PYTHON_ROOT','C:/Users/aluk/AppData/Local/Programs/Python/Python310')
    env['PATH']=str(projroot/'bin')+';'+str(usdroot/'bin')+';'+str(usdroot/'lib')+';'+pyroot+';'+env['PATH']
    env['PROJ_DATA']=env.get('GEOSPATIAL_RESOURCE_DIR',str(ROOT.parent/'geospatial-model-resources'))+';'+str(projroot/'share/proj');env['PROJ_NETWORK']='OFF'
    if without_grids:env['PROJ_DATA']=str(projroot/'share/proj')
    result=subprocess.run([str(ROOT/'native/build/resolve.exe'),str(p),str(out),str(ROOT/'schema')],env=env,capture_output=True,text=True)
    (E/(tag+'-native-stderr.txt')).write_text(result.stderr,encoding='utf-8')
    assert result.returncode==0,result.stderr
    return json.loads(out.read_text())

def test_two_readers_analytic_controls():
    cases=[('Model',[0,0,0],[6378137,0,0]),('Heading',[0,10,0],[6378137,10,0]),
      ('Heading/Child',[0,0,0],[6378137,10,0]),('Adjusted',[0,0,0],[6378137,10,0]),
      ('Adjusted/Reset',[0,0,0],[6378137,0,20]),('Independent',[0,0,0],[6378237,0,0]),
      ('Independent/Child',[0,0,0],[6378157,0,0])]
    # /World geographic chart translates X east. Independent ECEF anchors instead
    # use enclosing geographic chart for their own identity adjustment only.
    r=reader();queries=[]
    for path,p,expected in cases:
        np.testing.assert_allclose(r.points(prim(r,path),[p]),[expected],atol=2e-7,rtol=0)
        queries.append({'prim':'/World/'+path,'points':[p]})
    n=native(F/'controls.usda',queries,tag='analytic')
    for case,result in zip(cases,n['results']):
        assert result['success'],result
        np.testing.assert_allclose(result['points'],[case[2]],atol=2e-7,rtol=0)

@pytest.mark.parametrize('path',['Broken','Model/BadRole','WrongType','Nonfinite','TwoD','Blocked','Pole'])
def test_invalid_inputs_fail_in_both_readers(path):
    r=reader()
    with pytest.raises((ResolutionError,ValueError)):r.points(prim(r,path),[[0,0,0]])
    result=native(F/'controls.usda',[{'prim':'/World/'+path,'points':[[0,0,0]]}],tag='invalid-'+path.replace('/','-'))['results'][0]
    assert not result['success'],result

def test_interpolate_source_before_projection():
    r=reader(5);p=prim(r,'Moving');np.testing.assert_allclose(r.points(p,[[0,0,0]]),[[6378137,0,0]],atol=1e-7)
    n=native(F/'controls.usda',[{'prim':'/World/Moving','points':[[0,0,0]]}],time=5,tag='source-midpoint')
    np.testing.assert_allclose(n['results'][0]['points'],[[6378137,0,0]],atol=1e-7)
    # Independent analytic error if endpoints are projected and then interpolated.
    assert 971 < 6378137*(1-math.cos(math.pi/180)) < 972

def test_pose_ambiguity_and_winding():
    r=reader(5)
    with pytest.raises(ResolutionError,match='180'):r.points(prim(r,'Turn'),[[0,10,0]])
    np.testing.assert_allclose(r.points(prim(r,'Wrap'),[[0,10,0]]),[[6378137,0,10]],atol=1e-7)
    n=native(F/'controls.usda',[{'prim':'/World/Turn','points':[[0,10,0]]},{'prim':'/World/Wrap','points':[[0,10,0]]}],time=5,tag='orientation')
    assert not n['results'][0]['success'];np.testing.assert_allclose(n['results'][1]['points'],[[6378137,0,10]],atol=1e-7)
    for t in [0,10]:assert np.isfinite(reader(t).points(prim(reader(t),'Turn'),[[0,0,0]])).all()
    r=reader(5);r.stage.SetInterpolationType(Usd.InterpolationTypeHeld);r=Reader(r.stage,C,5)
    np.testing.assert_allclose(r.points(prim(r,'Turn'),[[0,10,0]]),[[6378137,0,10]],atol=1e-7)

def test_original_survey_oracles():
    results=[]
    for case in json.loads((F/'survey-expectations.json').read_text()):
        source=definition(case['source_wkt']);target=definition(case['output_wkt']);engine=Engine()
        p=np.array([row['source'] for row in case['rows']]);expected=np.array([row['expected'] for row in case['rows']])
        actual=engine.transform(source,target,p);error=np.linalg.norm((actual-expected)*target.units,axis=1)
        assert max(error)<case['tolerance_m'],(case['name'],error)
        # Native treats origin-only model query as the same absolute coordinate.
        idx=len(results);queries=[{'prim':f'/Survey/Case{idx}','points':[[0,0,0]]}]
        n=native(F/'survey.usda',queries,output=case['output_wkt'],tag='survey-'+case['name'])
        assert n['results'][0]['success'],n
        residual=np.linalg.norm((np.array(n['results'][0]['points'][0])-expected[0])*target.units)
        assert residual<case['tolerance_m'],residual
        all_controls=native(F/'survey.usda',[{'prim':f'/Survey/Case{idx}','kind':'coordinate','points':p.tolist()}],output=case['output_wkt'],tag='all-survey-'+case['name'])
        assert all_controls['results'][0]['success'],all_controls
        native_error=np.linalg.norm((np.array(all_controls['results'][0]['points'])-expected)*target.units,axis=1)
        assert max(native_error)<case['tolerance_m']
        agreement=np.linalg.norm((np.array(all_controls['results'][0]['points'])-actual)*target.units,axis=1)
        assert max(agreement)<.0001
        results.append({'case':case['name'],'points':len(p),'max_control_error_m':float(max(error)),'native_first_control_error_m':float(residual),'native_all_control_error_m':float(max(native_error)),'reader_agreement_m':float(max(agreement)),'python_operations':engine.operations,'native_operations':all_controls['operations']})
    (E/'survey-controls.json').write_text(json.dumps(results,indent=2))

def test_normalization_is_lossless_decimal_and_fixed_point():
    raw=CRS.from_epsg(4979).to_wkt().replace('6378137,','+6.378137000E6,').replace('WGS 84','WGS  84')
    normalized=normalize_wkt(raw)
    assert '"WGS  84"' in normalized and '+6.378137000E6' not in normalized
    assert normalize_wkt(normalized)==normalized
    assert '6378137,' in normalized
    n=native(F/'controls.usda',[{'prim':'/World/Model','kind':'normalize','wkt':raw}],tag='normalization')
    assert n['results'][0]['wkt']==normalized
    assert definition(raw).warnings
    with pytest.raises(Exception):normalize_wkt('GEOGCRS[broken]')

def test_profiles_unloaded_and_stale_claim():
    stage=Usd.Stage.CreateInMemory();p=stage.DefinePrim('/Asset','Xform');stage.SetDefaultPrim(p)
    p.GetPayloads().AddPayload(str(F/'controls.usda'),'/World');stage.Unload()
    publish_claim(p,True);assert dependency_summary(p)=='required' and not p.IsLoaded()
    check_publication(p,['unknown'])
    publish_claim(p,False);assert dependency_summary(p)=='known-none'
    with pytest.raises(ResolutionError,match='Stale'):check_publication(p,['required'])
    p.ClearCustomData();assert dependency_summary(p)=='unknown'
    path=F/'profiles-unloaded.usda';stage.GetRootLayer().Export(str(path));publish_claim(p,True);stage.GetRootLayer().Export(str(path))
    n=native(path,[{'prim':'/Asset','kind':'summary'}],tag='profiles',load_none=True)
    assert n['results'][0]['state']=='required' and not n['results'][0]['payload_loaded']

def test_native_data_association_and_permutation():
    stage=Usd.Stage.Open(str(F/'measurements.usda'));results=[]
    for name,output in [('Permutation',C),('Railway',C),('Climate',C),('Raster',CRS.from_epsg(32631).to_wkt())]:
        p=stage.GetPrimAtPath('/Data/'+name);raw=decode(p);path=E/(name+'-decoded.json');path.write_text(json.dumps(raw))
        r=Reader(stage,output);resolved=resolve(r,p,raw)
        n=native(F/'measurements.usda',[{'prim':'/Data/'+name,'kind':'measurement','decoded':str(path)}],output=output,tag='measurement-'+name)
        assert n['results'][0]['success'],n['results'][0]
        native_samples=n['results'][0]['samples'];assert len(native_samples)==len(raw['samples'])
        np.testing.assert_allclose([x['resolved_coordinates'] for x in native_samples],[x['resolved_coordinates'] for x in resolved['samples']],atol=.0001,rtol=0)
        assert [(x['index'],x['value'],x['mask'],x['observation_time']) for x in native_samples]==[(x['index'],x['value'],x['mask'],x['observation_time']) for x in raw['samples']]
        if name=='Permutation':
            assert raw['samples'][5]['coordinates']==[2.1,1,10] and raw['samples'][5]['value']==5
            assert raw['samples'][-1]['mask'] and raw['samples'][-1]['observation_time']['value']==6
        if name=='Raster':
            assert raw['samples'][0]['coordinates']==[500005,5399995]
            with pytest.raises(ResolutionError):resolve(Reader(stage,C),p,raw)
        (E/(name+'-resolved.json')).write_text(json.dumps(resolved))
        results.append({'dataset':name,'samples':len(raw['samples']),'native_values_indices_masks_times_preserved':True})
    (E/'measurement-controls.json').write_text(json.dumps(results,indent=2))

def test_independent_point_instancer_transport():
    r=reader();i=prim(r,'Instances');p=r.stage.GetPrimAtPath('/Storage/Prototype')
    base=r.instance_points(i,0,p,[[0,0,0]])
    actual=r.instance_points(i,1,p,[[0,0,0]])
    # At equator, +10 local east is +10 geocentric Y around instancer origin.
    np.testing.assert_allclose(actual-base,[[0,10,0]],atol=1e-5,rtol=0)
    n=native(F/'controls.usda',[{'prim':'/Storage/Prototype','kind':'instance','instancer':'/World/Instances','index':j,'points':[[0,0,0]]} for j in [0,1]],tag='independent-instance')
    for expected,value in zip([base,actual],n['results']):assert value['success'],value;np.testing.assert_allclose(value['points'],expected,atol=1e-5,rtol=0)

def test_bake_ordinary_reader_and_reassembly():
    r=reader();mesh=prim(r,'Heading/Triangle');out,origin=export_geometry(r,[mesh],F/'baked.usda')
    p=out.GetPrimAtPath('/Context/Origin/Mesh0');m=UsdGeom.Mesh(p);points=np.array(m.GetPointsAttr().Get())
    ordinary=row_transform(points,UsdGeom.XformCache().GetLocalToWorldTransform(p))
    expected=r.points(mesh,np.array(UsdGeom.Mesh(mesh).GetPointsAttr().Get()),r.scene)
    np.testing.assert_allclose(ordinary,expected,atol=1e-6,rtol=0)
    assert p.GetAttribute('purposeNote').Get()=='Unrelated property retained'
    assert not direct(p) and dependency_summary(out.GetDefaultPrim())=='known-none'
    aware=Reader(out,C);np.testing.assert_allclose(aware.points(p,points),expected,atol=1e-6)
    assembly=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(assembly,1);UsdGeom.SetStageUpAxis(assembly,'Z')
    root=UsdGeom.Xform.Define(assembly,'/Assembly');root.AddTranslateOp().Set((7,8,9));copy=assembly.DefinePrim('/Assembly/Copy');copy.GetReferences().AddReference(str(F/'baked.usda'))
    p=assembly.GetPrimAtPath('/Assembly/Copy/Origin/Mesh0');rr=Reader(assembly,C)
    np.testing.assert_allclose(rr.points(p,points),expected+[7,8,9],atol=1e-6)
    n=native(F/'baked.usda',[{'prim':'/Context/Origin/Mesh0','points':points.tolist()}],tag='ordinary-bake')
    np.testing.assert_allclose(n['results'][0]['points'],expected,atol=1e-6)
    native_bake=native(F/'controls.usda',[{'prim':'/World/Heading/Triangle','kind':'bake','destination':str(F/'native-baked.usda'),'meshes':['/World/Heading/Triangle']}],tag='native-bake')
    assert native_bake['results'][0]['success'],native_bake
    ns=Usd.Stage.Open(str(F/'native-baked.usda'));np_=ns.GetPrimAtPath('/Context/Origin/Mesh0')
    npoints=np.array(UsdGeom.Mesh(np_).GetPointsAttr().Get());np.testing.assert_allclose(row_transform(npoints,UsdGeom.XformCache().GetLocalToWorldTransform(np_)),expected,atol=1e-6)

def test_inverse_and_bound_failure():
    r=reader();p=prim(r,'Heading');x=[1,2,3];target=r.points(p,x)
    np.testing.assert_allclose(r.inverse(p,target),x,atol=1e-5)
    with pytest.raises(ResolutionError,match='Singular'):r.inverse(prim(r,'Singular'),[6378138,1,2])
    with pytest.raises(ResolutionError,match='Continuous'):r.continuous_bound(p)
    n=native(F/'controls.usda',[{'prim':'/World/Heading','kind':'inverse','points':[target.tolist()]},{'prim':'/World/Model','kind':'continuous_bound'}],tag='inverse-bounds')
    np.testing.assert_allclose(n['results'][0]['points'],[x],atol=1e-5);assert not n['results'][1]['success']

def test_composition_directness_and_no_source_mutation():
    base=Usd.Stage.Open(str(F/'controls.usda'));before=base.GetRootLayer().ExportToString()
    st=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(st,1);UsdGeom.SetStageUpAxis(st,'Z')
    p=st.DefinePrim('/Imported');p.GetReferences().AddReference(str(F/'controls.usda'),'/World/Model')
    r=Reader(st,C);assert direct(p);np.testing.assert_allclose(r.points(p,[[0,0,0]]),[[6378137,0,0]],atol=1e-7)
    c=st.CreateClassPrim('/Class');c.AddAppliedSchema('GeospatialCRSBindingAPI');c.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=False,variability=Sdf.VariabilityUniform).Set(G);c.CreateAttribute('crs:position',Sdf.ValueTypeNames.Double3).Set((0,0,0));child=UsdGeom.Xform.Define(st,'/Inherited').GetPrim();child.GetInherits().AddInherit('/Class')
    assert direct(child);np.testing.assert_allclose(r.points(child,[[0,0,0]]),[[6378137,0,0]],atol=1e-7)
    assert base.GetRootLayer().ExportToString()==before
