import json,sys
import numpy as np
import pytest
from pyproj import CRS
from pxr import Gf,Sdf,Usd,UsdGeom,Vt
from test_contract import ROOT,F,E,G,C,native,reader,prim
from reader import *
from formats import decode,resolve
from make_inputs import bind,stage,wkt
import os,subprocess

def test_working_chart_scale_rotation_pivot_output_invariance():
    st=stage('order.usda');parent=bind(st,'/Project',C,(6378137,0,0));st.SetDefaultPrim(parent)
    p=bind(st,'/Project/Model',G,(0,0,0),(90,0,0));x=UsdGeom.Xformable(p)
    x.AddTranslateOp().Set((1,2,3));x.AddRotateZOp().Set(90);x.AddScaleOp().Set((2,2,2));st.GetRootLayer().Save()
    r=Reader(st,C);expected=np.array([6378118,2,3]);np.testing.assert_allclose(r.points(p,[0,10,0]),expected,atol=1e-7)
    rg=Reader(st,G);geographic=rg.points(p,[0,10,0]);back=rg.engine.transform(rg.output,definition(C),geographic)
    np.testing.assert_allclose(back,expected,atol=1e-7)
    n=native(F/'order.usda',[{'prim':'/Project/Model','points':[[0,10,0]]}],tag='order')
    np.testing.assert_allclose(n['results'][0]['points'],[expected],atol=1e-7)

def test_stage_axes_units_and_authored_conformance():
    results=[]
    for name,up,mpu,point in [('metre-z','Z',1,[0,10,0]),('cm-y','Y',.01,[0,0,-1000])]:
        st=stage(name+'.usda');UsdGeom.SetStageUpAxis(st,up);UsdGeom.SetStageMetersPerUnit(st,mpu)
        p=bind(st,'/Model',G,(0,0,0),(90,0,0));st.SetDefaultPrim(p);st.GetRootLayer().Save()
        r=Reader(st,C);result=r.points(p,point);np.testing.assert_allclose(result,[6378137,10,0],atol=1e-7);results.append(result)
        n=native(F/(name+'.usda'),[{'prim':'/Model','points':[point]}],tag=name);np.testing.assert_allclose(n['results'][0]['points'],[result],atol=1e-7)
    np.testing.assert_allclose(*results,atol=1e-7)

def test_composed_sample_time_offsets_and_native_instances():
    st=stage('composed.usda');p=st.DefinePrim('/Motion');p.GetReferences().AddReference(str(F/'controls.usda'),'/World/Moving',Sdf.LayerOffset(5,2));st.SetDefaultPrim(p)
    inst=st.DefinePrim('/Reusable');inst.GetReferences().AddReference(str(F/'controls.usda'),'/World/Heading');inst.SetInstanceable(True);st.GetRootLayer().Save()
    r=Reader(st,C,15);np.testing.assert_allclose(r.points(p,[0,0,0]),[6378137,0,0],atol=1e-7)
    proxy=st.GetPrimAtPath('/Reusable/Child');assert proxy.IsInstanceProxy();np.testing.assert_allclose(r.points(proxy,[0,0,0]),[6378137,10,0],atol=1e-7)
    n=native(F/'composed.usda',[{'prim':'/Motion','points':[[0,0,0]]},{'prim':'/Reusable/Child','points':[[0,0,0]]}],time=15,tag='composition')
    for value,expected in zip(n['results'],[[6378137,0,0],[6378137,10,0]]):assert value['success'],value;np.testing.assert_allclose(value['points'],[expected],atol=1e-7)

def test_uniform_samples_default_and_batch_failures():
    st=stage('invalid-uniform.usda');p=bind(st,'/Model',G,(0,0,0));p.GetAttribute('crs:wkt').Set(G,1);st.GetRootLayer().Save()
    with pytest.raises(ResolutionError,match='Uniform'):Reader(st,C).points(p,[0,0,0])
    n=native(F/'invalid-uniform.usda',[{'prim':'/Model','points':[[0,0,0]]}],tag='uniform-samples');assert not n['results'][0]['success']
    r=reader()
    with pytest.raises(ResolutionError,match='unavailable'):r.points(prim(r,'Moving'),[0,0,0])
    n=native(F/'controls.usda',[{'prim':'/World/Model','points':[[0,0,0]]},{'prim':'/World/Broken','points':[[0,0,0]]}],tag='partial-batch')
    assert n['results'][0]['success'] and not n['results'][1]['success']

def test_profiles_registry_and_schema_implication():
    from pxr import UsdProfiles,Tf
    reg=UsdProfiles.ProfileRegistry
    assert reg.HasCapability(CAP) and reg.IsProfile(PROFILE)
    assert CAP in [str(x) for x in reg.GetSchemaImpliedCapabilities(Tf.Type.FindByName('FreshGeospatialBindingAPI'))]
    assert reg.GetSchemaImpliedCapabilities(Tf.Type.FindByName('FreshGeospatialCRS'))==set()

def test_time_sampled_bake_schedule_and_millimetre_detail():
    st=stage('sampled.usda');p=bind(st,'/Model',G);p.GetAttribute('crs:position').Set((-1,0,0),0);p.GetAttribute('crs:position').Set((1,0,0),10);st.SetDefaultPrim(p)
    m=UsdGeom.Mesh.Define(st,'/Model/Mesh');m.CreatePointsAttr([(0,0,0),(.001,0,0),(0,.001,0)]);m.CreateFaceVertexCountsAttr([3]);m.CreateFaceVertexIndicesAttr([0,1,2]);m.CreateSubdivisionSchemeAttr('none');st.GetRootLayer().Save()
    r=Reader(st,C,0);out,o=export_geometry(r,[m.GetPrim()],F/'sampled-bake.usda',times=[0,5,10]);target=out.GetPrimAtPath('/Context/Origin/Mesh0');attr_=UsdGeom.Mesh(target).GetPointsAttr()
    assert attr_.GetTimeSamples()==[0,5,10] and out.GetTimeCodesPerSecond()==24
    for t in [0,5,10]:
        rr=Reader(st,C,t);ordinary=row_transform(np.array(attr_.Get(t)),UsdGeom.XformCache(t).GetLocalToWorldTransform(target));expected=rr.points(m.GetPrim(),np.array(m.GetPointsAttr().Get()))
        err=np.linalg.norm(ordinary-expected,axis=1).max()
        assert err<1e-6
    # Static origin-separated local detail is preserved to sub-micrometre accuracy.
    r=Reader(st,C,0);out,o=export_geometry(r,[m.GetPrim()],F/'precision-bake.usda')
    points=np.array(UsdGeom.Mesh(out.GetPrimAtPath('/Context/Origin/Mesh0')).GetPointsAttr().Get(0))
    assert abs(np.linalg.norm(points[1]-points[0])-.001)<1e-7
    n=native(F/'sampled.usda',[{'prim':'/Model/Mesh','kind':'bake','destination':str(F/'native-sampled-bake.usda'),'meshes':['/Model/Mesh'],'times':[0,5,10]}],time=0,tag='native-sampling');assert n['results'][0]['success']
    # Sampling records equality at exported keys, never a continuous trajectory certificate.
    assert not n['continuous_bound_certified']

def test_measurement_conflict_missing_height_and_role():
    st=Usd.Stage.Open(str(F/'measurements.usda'));p=st.GetPrimAtPath('/Data/Raster');r=Reader(st,CRS.from_epsg(32631).to_wkt());raw=decode(p)
    UsdGeom.Xformable(p).AddRotateXOp().Set(10)
    with pytest.raises(ResolutionError,match='out-of-plane'):resolve(r,p,raw)
    p=st.GetPrimAtPath('/Data/Permutation');p.GetAttribute('crs:wkt').Set(C)
    with pytest.raises(ResolutionError,match='conflict'):decode(p)
    p.GetAttribute('crs:position').Block()
    with pytest.raises(ResolutionError,match='invalid role'):r.validate_roles(p,p)

def test_normals_tangents_and_singular_frame():
    r=reader();p=prim(r,'Heading')
    tangent=r.transport(p,[0,0,0],[0,1,0],'vector');np.testing.assert_allclose(tangent,[0,1,0],atol=1e-5)
    normal=r.transport(p,[0,0,0],[0,0,1],'normal');np.testing.assert_allclose(normal,[1,0,0],atol=1e-5)
    with pytest.raises(ResolutionError,match='Singular'):r.transport(prim(r,'Singular'),[0,0,0],[1,0,0],'normal')
    n=native(F/'controls.usda',[{'prim':'/World/Heading','kind':'normal','at':[0,0,0],'points':[[0,0,1]]},{'prim':'/World/Singular','kind':'normal','at':[0,0,0],'points':[[1,0,0]]}],tag='normal-transport')
    np.testing.assert_allclose(n['results'][0]['points'],[[1,0,0]],atol=1e-5);assert not n['results'][1]['success']

def test_missing_resources_and_epoch_dependent_requests_fail():
    dst=(ROOT/'inputs/original/France/04_RGF93v2b_Geographic3D_WKT2.txt').read_text()
    n=native(F/'survey.usda',[{'prim':'/Survey/Case1','kind':'coordinate','points':[[1661099.039,8180053.117,37.298]]}],output=dst,tag='missing-grid',without_grids=True)
    assert not n['results'][0]['success'],n
    empty=E/'empty-resources';empty.mkdir(exist_ok=True)
    env=os.environ.copy();env['GEOSPATIAL_RESOURCE_DIR']=str(empty)
    run=subprocess.run([sys.executable,str(ROOT/'src_py/reader.py'),str(F/'survey.usda'),'/Survey/Case1','--output-wkt',str(ROOT/'inputs/original/France/04_RGF93v2b_Geographic3D_WKT2.txt')],env=env,capture_output=True,text=True)
    assert run.returncode!=0,run.stdout
    with pytest.raises(ResolutionError,match='epochs'):definition('COORDINATEMETADATA['+G+',EPOCH[2026]]')
    with pytest.raises(ResolutionError,match='Epoch-dependent'):
        Engine().transform(definition(CRS.from_epsg(7789).to_wkt()),definition(CRS.from_epsg(9988).to_wkt()),[4203715,181349,4777419])

def test_post_implementation_reverse_audit_guards():
    st=Usd.Stage.Open(str(F/'controls.usda'));copy=stage('reverse-audit.usda');copy.GetRootLayer().TransferContent(st.GetRootLayer())
    proto=copy.GetPrimAtPath('/Storage/Prototype');UsdGeom.Xformable(proto).AddTranslateOp().Set((0,50,0))
    child=UsdGeom.Xform.Define(copy,'/Storage/Prototype/Reset');child.SetResetXformStack(True);child.AddTranslateOp().Set((0,3,0));copy.GetRootLayer().Save()
    r=Reader(copy,C);i=copy.GetPrimAtPath('/World/Instances');actual=r.instance_points(i,0,child.GetPrim(),[[0,0,0]])
    baseline=Reader(st,C).points(st.GetPrimAtPath('/Storage/Prototype'),[[0,3,0]])
    np.testing.assert_allclose(actual,baseline,atol=1e-5)
    n=native(F/'reverse-audit.usda',[{'prim':str(child.GetPath()),'kind':'instance','instancer':'/World/Instances','index':0,'points':[[0,0,0]]}],tag='prototype-reset');assert n['results'][0]['success'],n;np.testing.assert_allclose(n['results'][0]['points'],baseline,atol=1e-5)
    data=Usd.Stage.Open(str(F/'measurements.usda'));p=data.GetPrimAtPath('/Data/Permutation');raw=decode(p);raw['asset']=str(F/'climate.cf.nc');bad=E/'bad-decoder-association.json';bad.write_text(json.dumps(raw));n=native(F/'measurements.usda',[{'prim':'/Data/Permutation','kind':'measurement','decoded':str(bad)}],tag='asset-identity');assert not n['results'][0]['success']
    mesh=copy.GetPrimAtPath('/World/Heading/Triangle');pv=UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('direction',Sdf.ValueTypeNames.Vector3fArray);pv.Set([(1,0,0)])
    with pytest.raises(ResolutionError,match='primvar export unsupported'):export_geometry(Reader(copy,C),[mesh],F/'unsupported-primvar-bake.usda')

def test_bake_preserves_material_dependency():
    from pxr import UsdShade
    st=stage('material-source.usda');p=bind(st,'/Model',G,(0,0,0));st.SetDefaultPrim(p);mesh=UsdGeom.Mesh.Define(st,'/Model/Mesh');mesh.CreatePointsAttr([(0,0,0),(1,0,0),(0,1,0)]);mesh.CreateFaceVertexCountsAttr([3]);mesh.CreateFaceVertexIndicesAttr([0,1,2]);mesh.CreateNormalsAttr([(0,0,1)]);mesh.SetNormalsInterpolation('constant');mesh.CreateSubdivisionSchemeAttr('none')
    material=UsdShade.Material.Define(st,'/Looks/Steel');shader=UsdShade.Shader.Define(st,'/Looks/Steel/Surface');shader.CreateIdAttr('UsdPreviewSurface');shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set((.2,.3,.4));material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material);st.GetRootLayer().Save()
    out,_=export_geometry(Reader(st,C),[mesh.GetPrim()],F/'material-bake.usda');target=out.GetPrimAtPath('/Context/Origin/Mesh0');bound,_=UsdShade.MaterialBindingAPI(target).ComputeBoundMaterial();assert bound and bound.GetPath().HasPrefix('/Context/Materials') and bound.GetSurfaceOutput().GetConnectedSources()[0]
    np.testing.assert_allclose(UsdGeom.Mesh(target).GetNormalsAttr().Get(),[[1,0,0]]*3,atol=1e-5)
    n=native(F/'material-source.usda',[{'prim':'/Model/Mesh','kind':'bake','destination':str(F/'native-material-bake.usda'),'meshes':['/Model/Mesh']}],tag='material-preservation');assert n['results'][0]['success'],n
    out=Usd.Stage.Open(str(F/'native-material-bake.usda'));assert out.GetPrimAtPath('/Context/Materials/Material0/Surface')
    assembly=Usd.Stage.CreateInMemory();p=assembly.DefinePrim('/Imported');p.GetReferences().AddReference(str(F/'native-material-bake.usda'));target=assembly.GetPrimAtPath('/Imported/Origin/Mesh0');bound,_=UsdShade.MaterialBindingAPI(target).ComputeBoundMaterial();assert bound and bound.GetSurfaceOutput().GetConnectedSources()[0]

def test_two_dimensional_queries_never_return_a_height():
    output=CRS.from_epsg(32631).to_wkt()
    n=native(F/'measurements.usda',[{'prim':'/Data/Raster','kind':'coordinate','points':[[500005,5399995]]},{'prim':'/Data/Raster','kind':'scene','points':[[0,0,0]]}],output=output,tag='two-dimensional-query')
    assert n['results'][0]['success'],n
    assert n['results'][0]['points']==[[500005,5399995]]
    assert not n['results'][1]['success']

def test_baked_context_preserved_under_unrelated_project_binding():
    bake=stage('recorded-bake-context.usda');context=bake.DefinePrim('/Context','CoordinateReferenceSystem');bake.SetDefaultPrim(context);context.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=False,variability=Sdf.VariabilityUniform).Set(C);origin=UsdGeom.Xform.Define(bake,'/Context/Origin');origin.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set((6378137,0,0));m=UsdGeom.Mesh.Define(bake,'/Context/Origin/Mesh0');m.CreatePointsAttr([(0,0,0),(1,0,0),(0,1,0)]);m.CreateFaceVertexCountsAttr([3]);m.CreateFaceVertexIndicesAttr([0,1,2]);bake.GetRootLayer().Save()
    st=stage('baked-under-binding.usda');project=bind(st,'/Project',G,(90,45,100));st.SetDefaultPrim(project);UsdGeom.Xformable(project).AddTranslateOp().Set((7,8,9));p=st.DefinePrim('/Project/Imported');p.GetReferences().AddReference('recorded-bake-context.usda');st.GetRootLayer().Save()
    mesh=st.GetPrimAtPath('/Project/Imported/Origin/Mesh0');points=np.array(UsdGeom.Mesh(mesh).GetPointsAttr().Get());expected=row_transform(points,UsdGeom.XformCache().GetLocalToWorldTransform(mesh));r=Reader(st,C)
    np.testing.assert_allclose(r.points(mesh,points),expected,atol=1e-6)
    n=native(F/'baked-under-binding.usda',[{'prim':str(mesh.GetPath()),'points':points.tolist()}],tag='bake-bound-project');assert n['results'][0]['success'],n;np.testing.assert_allclose(n['results'][0]['points'],expected,atol=1e-6)
