from pathlib import Path
import json,math,os,subprocess,sys,shutil
import numpy as np,pytest
from pxr import Usd,UsdGeom,Gf,Sdf,Plug,UsdValidation,Vt
from pyproj import CRS,datadir
from geobuild.model import normalize_wkt,crs,validate,GeoError,binding
from geobuild.resolve import Resolver,convert,local_to_source,axis_factors
from geobuild.export import export
ROOT=Path(__file__).resolve().parents[1];T=json.loads((ROOT/'targets.json').read_text());P=json.loads((ROOT/'data/partner-controls.json').read_text())
if os.environ.get('GEOBUILD_GRIDS'):datadir.append_data_dir(os.environ['GEOBUILD_GRIDS'])
def stage(name):return Usd.Stage.Open(str(ROOT/'scenes'/f'{name}.usda'))
@pytest.mark.parametrize('name',[p.stem for p in (ROOT/'scenes').glob('*.usda') if p.stem!='instance-asset'])
def test_authored_inputs(name):assert validate(stage(name))==[]
def test_handwritten_noncommuting_placement():
    s=stage('composition');r=Resolver(s);root=s.GetPrimAtPath('/Project/Model')
    np.testing.assert_allclose(r.full_points(root,[[3,4,5]],T['utm31']).points,[[1003,2014,44]],rtol=0,atol=1e-8)
    np.testing.assert_allclose(r.geometry(s.GetPrimAtPath('/Project/Model/Child/Mesh'),T['utm31']).points[0],[1003,2016,44],rtol=0,atol=1e-8)
def test_ancestor_exclusion():
    s=stage('composition');s.GetPrimAtPath('/Project').SetTypeName('Xform');UsdGeom.Xformable(s.GetPrimAtPath('/Project')).AddTranslateOp().Set((100000,0,0));r=Resolver(s)
    np.testing.assert_allclose(r.full_points(s.GetPrimAtPath('/Project/Model'),[[0,0,0]],T['utm31']).points[0],[1007,2008,39],rtol=0,atol=1e-8)
def test_independent_bound_child():
    s=stage('composition');r=Resolver(s);p=s.GetPrimAtPath('/Project/Model/Independent/Mesh')
    np.testing.assert_allclose(r.geometry(p,T['utm31']).points[0],[20,40,5],rtol=0,atol=1e-8)
def test_time_source_before_nonlinear():
    s=stage('composition');r=Resolver(s);p=s.GetPrimAtPath('/Project/Model');p.GetAttribute('crs:position').Set((499000,0,30),0);p.GetAttribute('crs:position').Set((501000,0,30),10)
    middle=r.full_points(p,[[0,0,0]],T['ecef'],Usd.TimeCode(5)).points
    ends=(r.full_points(p,[[0,0,0]],T['ecef'],Usd.TimeCode(0)).points+r.full_points(p,[[0,0,0]],T['ecef'],Usd.TimeCode(10)).points)/2
    assert np.linalg.norm(middle-ends)>.05
def test_source_space_path_on_equator():
    source=CRS.from_epsg(4979);out=CRS.from_epsg(4978);mid,_=convert(source,out,[[0,0,0]]);ends,_=convert(source,out,[[-1,0,0],[1,0,0]])
    assert 970<np.linalg.norm(mid-ends.mean(axis=0))<972
@pytest.mark.parametrize('src,dst',[('France_01','France_02'),('France_01','France_03'),('France_01','France_04'),('Colorado_01','Colorado_02'),('Colorado_02','Colorado_03')])
def test_partner_controls(src,dst):
    actual,tr=convert(P[src]['wkt'],P[dst]['wkt'],P[src]['points']);expected=np.array(P[dst]['points']);err=(actual-expected)*axis_factors(CRS.from_wkt(P[dst]['wkt']))
    if CRS.from_wkt(P[dst]['wkt']).is_geographic:err[:,:2]*=6378137
    assert np.linalg.norm(err,axis=1).max()<.002,(src,dst,err.max(),tr.description)
def test_analytic_ecef_control():
    s=CRS.from_epsg(4979);target=CRS.from_epsg(4978);p=np.array([[2.47,48.82,80],[-105.1,39.9,1600],[179.9,0,0]])
    a=6378137.;inv=298.257223563;e=1-(1-1/inv)**2;lo=np.deg2rad(p[:,0]);la=np.deg2rad(p[:,1]);n=a/np.sqrt(1-e*np.sin(la)**2)
    expected=np.column_stack([(n+p[:,2])*np.cos(la)*np.cos(lo),(n+p[:,2])*np.cos(la)*np.sin(lo),(n*(1-e)+p[:,2])*np.sin(la)])
    actual,_=convert(s,target,p);np.testing.assert_allclose(actual,expected,rtol=0,atol=2e-8)
def test_metres_not_survey_feet():
    c=CRS.from_wkt(P['Colorado_03']['wkt']);p=np.array(P['Colorado_03']['points'][0]);q=local_to_source(c,p,[[1,0,0]])
    assert q[0,0]-p[0]==pytest.approx(3937/1200,abs=1e-9)
def test_measurement_associations_and_values():
    s=stage('climate');p=s.GetPrimAtPath('/Climate');original=p.GetAttribute('data:values').Get(0);r=Resolver(s)
    a=r.measures(p,T['ecef'],Usd.TimeCode(0));b=r.measures(p,T['geographic'],Usd.TimeCode(10))
    assert len(next(iter(a.values())).points)==len(original)==2664
    assert list(original)==list(p.GetAttribute('data:values').Get(0));assert p.GetAttribute('data:values').Get(10)!=original
    assert np.isfinite(next(iter(b.values())).points).all()
def test_output_choice_preserves_post_context():
    s=stage('composition');r=Resolver(s);p=s.GetPrimAtPath('/Project/Model');p.GetAttribute('crs:position').Set((661101,6857834,37))
    a=r.full_points(p,[[0,0,0]],T['utm31']);b=r.full_points(p,[[0,0,0]],T['utm32']);back,_=convert(crs(T['utm32']),crs(T['utm31']),b.points)
    np.testing.assert_allclose(a.points,back,rtol=0,atol=3e-7)
    alternative=r.full_points(p,[[0,0,0]],T['utm32'],post_context=False);back,_=convert(crs(T['utm32']),crs(T['utm31']),alternative.points)
    assert np.linalg.norm(a.points-back)>.1
@pytest.mark.parametrize('output',['utm31','utm32','ecef','France_02'])
def test_source_preservation(output):
    s=stage('tower');layers={l.identifier:l.ExportToString() for l in s.GetUsedLayers()};r=Resolver(s)
    for p in s.Traverse():
        if p.GetAttribute('points'):r.geometry(p,T[output])
    assert layers=={l.identifier:l.ExportToString() for l in s.GetUsedLayers()}
def test_source_edit_invalidates_result():
    s=stage('composition');r=Resolver(s);p=s.GetPrimAtPath('/Project/Model');a=r.frame(p,T['utm31'])[0];p.GetAttribute('crs:position').Set((2000,3000,30));b=r.frame(p,T['utm31'])[0];assert not np.array_equal(a,b)
@pytest.mark.parametrize('which',['France_05','France_06'])
def test_epoch_wrapper_failure(which):
    with pytest.raises(GeoError,match='epoch'):crs(P[which]['wkt'])
def test_frame_epoch_retained():
    w=P['France_06']['wkt'];start=w.index('GEODCRS[');depth=0;end=start
    for i in range(start,len(w)):
        if w[i]=='[':depth+=1
        elif w[i]==']':
            depth-=1
            if depth==0:end=i+1;break
    n=normalize_wkt(w[start:end]);assert 'FRAMEEPOCH[2015]' in n
def test_wkt_normalization_preserves_quoted_metadata():
    w=T['ecef'];assert normalize_wkt(w.replace(',',', \n '))==w;assert normalize_wkt(w.replace('6378137','6378137.000'))==w
    changed=w.replace('WGS 84','WGS  84');assert normalize_wkt(changed)!=w
    assert normalize_wkt(normalize_wkt(w))==w
    with pytest.raises(GeoError):normalize_wkt('GEODCRS[broken]')
def test_meaningful_wkt_changes_not_normalized_away():
    w=T['ecef'];assert normalize_wkt(w.replace('6378137','6378138'))!=w
@pytest.mark.parametrize('defect',['target','position','quaternion','scale','normalization','declaration','role'])
def test_authored_negative_cases(defect):
    s=stage('composition');p=s.GetPrimAtPath('/Project/Model')
    if defect=='target':p.GetRelationship('crs:binding').SetTargets(['/NoSuchCRS'])
    if defect=='position':p.RemoveProperty('crs:position')
    if defect=='quaternion':p.GetAttribute('crs:orientation').Set(Gf.Quatd(0))
    if defect=='scale':p.GetAttribute('crs:scale').Set((1,0,1))
    if defect=='normalization':s.GetPrimAtPath('/CRS/Source').GetAttribute('crs:wkt').Set(T['utm31'].replace(',',', '))
    if defect=='declaration':s.GetRootLayer().customLayerData={}
    if defect=='role':p.CreateRelationship('crs:coordinateProperties',custom=True).SetTargets(['/Project/Model.crs:position'])
    assert validate(s)
def test_invalid_batch_not_partial():
    with pytest.raises(GeoError):convert(CRS.from_epsg(4979),CRS.from_epsg(32631).to_3d(),[[2,48,80],[2,100,80]])
def test_angular_rendering_rejected():
    s=stage('city');r=Resolver(s);v=next(iter(r.measures(s.GetPrimAtPath('/Image'),T['geographic']).values()))
    with pytest.raises(GeoError,match='angular'):r.scene_points(v,T['geographic'])
def test_stock_validation_plugin():
    Plug.Registry().RegisterPlugins(str(ROOT/'geospatialValidation/plugInfo.json'));v=UsdValidation.ValidationRegistry().GetOrLoadValidatorByName('geospatialValidation:AuthoredGeospatial');assert v
    context=UsdValidation.ValidationContext([v]);s=stage('composition');assert context.Validate(s)==[];s.GetPrimAtPath('/Project/Model').RemoveProperty('crs:position');assert context.Validate(s)
def test_explicit_export_and_fresh_reader(tmp_path):
    s=stage('composition');d=export(s,tmp_path/'derived.usda',T['utm31'],[0.,5.,10.]);assert validate(d)==[]
    original=Resolver(s).geometry(s.GetPrimAtPath('/Project/Model/Child/Mesh'),T['utm31'],Usd.TimeCode(5)).points
    fresh=Usd.Stage.Open(str(tmp_path/'derived.usda'));r=Resolver(fresh);actual=r.geometry(fresh.GetPrimAtPath('/Project/Model/Child/Mesh'),T['utm31'],Usd.TimeCode(5)).points
    np.testing.assert_allclose(actual,original,rtol=0,atol=1e-5)
    assert not any('resolved' in a.GetName().lower() for p in fresh.Traverse() for a in p.GetAttributes())
    assert list(fresh.GetRootLayer().customLayerData['geospatialExport']['sampledTimeCodes'])==[0,5,10]
def test_dependency_unloaded_payload(tmp_path):
    s=Usd.Stage.CreateNew(str(tmp_path/'assembly.usda'));s.GetRootLayer().customLayerData={'geospatialResolutionRequired':True};p=s.DefinePrim('/Asset');p.GetPayloads().AddPayload(str(ROOT/'scenes/tower.usda'),'/Tower');s.Unload();assert s.GetRootLayer().customLayerData['geospatialResolutionRequired'] is True;assert not p.IsLoaded()
def test_float_precision_and_local_preservation():
    assert float(np.spacing(np.float32(481948)))==.03125
    assert float(np.float32(.001))!=0
@pytest.mark.parametrize('unit',[1.,.01,1200/3937])
@pytest.mark.parametrize('up',['Y','Z'])
def test_stage_units_axes_are_derived_frame_conventions(unit,up):
    s=stage('composition');UsdGeom.SetStageUpAxis(s,up);UsdGeom.SetStageMetersPerUnit(s,unit);p=s.GetPrimAtPath('/Project/Model');p.GetAttribute('crs:orientation').Set(Gf.Quatd(1));p.GetAttribute('crs:scale').Set((1,1,1));UsdGeom.Xformable(p).ClearXformOpOrder();UsdGeom.Xformable(p).AddTranslateOp(opSuffix='axisTest').Set((0,2,0) if up=='Y' else (0,0,2));r=Resolver(s)
    point=[0,1,0] if up=='Y' else [0,0,1];a=r.full_points(p,[point],T['utm31']);np.testing.assert_allclose(a.points[0],[1000,2000,30+3*unit],rtol=0,atol=1e-7)
def test_variant_authored_source_placement_composes():
    s=stage('composition');p=s.GetPrimAtPath('/Project/Model');v=p.GetVariantSets().AddVariantSet('placement')
    for name,x in [('first',1000),('second',2000)]:
        v.AddVariant(name);v.SetVariantSelection(name)
        with v.GetVariantEditContext():p.CreateAttribute('crs:scale',Sdf.ValueTypeNames.Double3).Set((x/1000,1,1))
    p.RemoveProperty('crs:scale');v.SetVariantSelection('first');r=Resolver(s);a=r.frame(p,T['utm31'])[0];v.SetVariantSelection('second');b=r.frame(p,T['utm31'])[0];assert abs(b[0,1]/a[0,1]-2)<1e-8
def test_reference_and_stronger_binding_opinion(tmp_path):
    s=Usd.Stage.CreateNew(str(tmp_path/'composed.usda'));p=s.DefinePrim('/Placed');p.GetReferences().AddReference(str(ROOT/'scenes/tower.usda'),'/Tower');assert p.GetAttribute('crs:position').Get()==Gf.Vec3d(648237.125,6862251.890,33.79)
    p.GetAttribute('crs:position').Set((648300,6862200,40));assert p.GetAttribute('crs:position').Get()==Gf.Vec3d(648300,6862200,40)
def test_native_instances_share_geometry_not_placement():
    s=stage('instances');r=Resolver(s);points=[]
    for i in range(3):
        p=s.GetPrimAtPath(f'/Native{i}/Asset');assert p.IsInstance();points.append(r.geometry(s.GetPrimAtPath(f'/Native{i}/Asset/Geometry'),T['utm31']).points[0])
    np.testing.assert_allclose(np.array(points)[:,0],[650000,650010,650020],rtol=0,atol=1e-7)
def test_point_instances_standard_local_offsets():
    s=stage('instances');r=Resolver(s);p=s.GetPrimAtPath('/PointModels/Instances');inst=UsdGeom.PointInstancer(p);m=inst.ComputeInstanceTransformsAtTime(Usd.TimeCode(0),Usd.TimeCode(0));frame,_=r.frame(s.GetPrimAtPath('/PointModels'),T['utm31']);a=np.array([(q*Gf.Matrix4d(frame)).Transform(Gf.Vec3d(0)) for q in m]);np.testing.assert_allclose(a[:,0],[650000,650010,650020],rtol=0,atol=1e-7)

def test_native_angular_units_are_not_assumed_degrees():
    c=CRS.from_epsg(4807).to_3d();a=np.array([[2.5,50.,80.]])
    e,_=convert(c,CRS.from_epsg(4978),a);back,_=convert(CRS.from_epsg(4978),c,e)
    np.testing.assert_allclose(back,a,rtol=0,atol=.002)
    assert abs(axis_factors(c)[0]-math.pi/200)<1e-14

def test_time_dependent_operation_without_wrapper_is_deferred():
    # Complete CRS WKT alone must not activate a time-dependent Helmert at a guessed epoch.
    with pytest.raises(GeoError,match='Epoch-dependent'):
        convert(CRS.from_epsg(7789),CRS.from_epsg(9988),[[4210000.,170000.,4770000.]])

def test_equivalent_spelling_and_distinct_metadata():
    c=CRS.from_wkt(T['geographic']);variant=T['geographic'].replace(',',', \n ');remark=T['geographic'][:-1]+',REMARK["Source metadata retained"]]'
    assert normalize_wkt(variant)==T['geographic'];assert normalize_wkt(remark)!=T['geographic']
    for w in [variant,remark]:
        a,_=convert(c,CRS.from_epsg(4978),[[2.47,48.82,80]]);b,_=convert(CRS.from_wkt(w),CRS.from_epsg(4978),[[2.47,48.82,80]]);np.testing.assert_array_equal(a,b)

def test_frame_probe_stability_is_not_a_surface_bound():
    s=stage('tower');r=Resolver(s);p=s.GetPrimAtPath('/Tower');m,_=r.frame(p,T['ecef'])
    for h in [.25,4.]:
        q,_=r.frame(p,T['ecef'],probe=h);assert np.max(abs(m[:3,:3]-q[:3,:3]))<1e-6

def test_unaware_reader_keeps_ordinary_usd_interpretation():
    s=stage('composition');p=s.GetPrimAtPath('/Project/Model/Child/Mesh');cache=UsdGeom.XformCache(Usd.TimeCode(5));before=cache.GetLocalToWorldTransform(p);Resolver(s).geometry(p,T['ecef'],Usd.TimeCode(5));cache.Clear();assert cache.GetLocalToWorldTransform(p)==before

def test_missing_height_resource_is_visible_failure(tmp_path):
    # A fresh process gets only proj.db, no grid cache, no network and no prior transformer.
    data=tmp_path/'data';data.mkdir();shutil.copyfile(Path(datadir.get_data_dir().split(os.pathsep)[0])/'proj.db',data/'proj.db')
    config=tmp_path/'input.json';config.write_text(json.dumps({'source':P['France_01']['wkt'],'output':P['France_03']['wkt'],'points':P['France_01']['points'],'data':str(data)}))
    code='import json,sys;from pyproj import datadir;from geobuild.resolve import convert;from geobuild.model import GeoError;j=json.load(open(sys.argv[1]));datadir.set_data_dir(j["data"]);\ntry:convert(j["source"],j["output"],j["points"])\nexcept GeoError:print("EXPECTED_RESOURCE_FAILURE");sys.exit(0)\nraise RuntimeError("Missing grid silently succeeded")'
    env=os.environ.copy();env.update(PROJ_NETWORK='OFF',PROJ_USER_WRITABLE_DIRECTORY=str(tmp_path/'cache'),PYTHONPATH=str(ROOT))
    r=subprocess.run([sys.executable,'-c',code,str(config)],env=env,capture_output=True,text=True);assert r.returncode==0,r.stderr;assert 'EXPECTED_RESOURCE_FAILURE' in r.stdout
