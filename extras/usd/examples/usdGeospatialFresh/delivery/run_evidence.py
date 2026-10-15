"""Fresh end-to-end evidence. Geometry below is actual reader output, not an oracle."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
from pyproj import CRS
from pxr import Usd,UsdGeom,Gf,Sdf,UsdLux
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src_py'));sys.path.insert(0,str(ROOT/'tests'))
from reader import Reader,Engine,definition,normalize_wkt,export_geometry,publish_claim,row_transform
from test_contract import native
from make_inputs import bind
F=ROOT/'inputs/authored';E=ROOT/'evidence'

def main():
    # Explicit authoring/conformance. The artist asset declares centimetres but
    # has a numerical 300-unit height: 3m in that declaration. The demo separately
    # authors a 100x intended resize to illustrate a 300m tower. Neither reader
    # repairs source units or infers this physical size.
    original=Usd.Stage.Open(str(ROOT/'inputs/original/tower.usdz'))
    geographic=(ROOT/'inputs/original/France/04_RGF93v2b_Geographic3D_WKT2.txt').read_text()
    compound=CRS.from_wkt((ROOT/'inputs/original/France/02_RGF93v2b_Lambert93_IGN69_WKT2.txt').read_text())
    output=compound.sub_crs_list[0].to_3d().to_wkt()
    position=(2.2945,48.8584,33)
    origin=Engine().transform(definition(geographic),definition(output),position)
    source=Usd.Stage.CreateNew(str(F/'tower-source.usda'));UsdGeom.SetStageMetersPerUnit(source,1);UsdGeom.SetStageUpAxis(source,'Z')
    project=bind(source,'/Project',normalize_wkt(output),origin);source.SetDefaultPrim(project)
    tower=bind(source,'/Project/Tower',normalize_wkt(geographic),position,(30,0,0))
    adjust=UsdGeom.Xformable(tower);adjust.AddTranslateOp().Set((120,-60,0));adjust.AddRotateZOp().Set(20);adjust.AddScaleOp().Set((1.15,1.15,1.15))
    conform=UsdGeom.Xform.Define(source,'/Project/Tower/Conform');conform.AddRotateXOp().Set(90);conform.AddScaleOp().Set((.01,.01,.01))
    resize=UsdGeom.Xform.Define(source,'/Project/Tower/Conform/DisplaySize');resize.AddScaleOp().Set((100,100,100))
    asset=source.DefinePrim(str(resize.GetPath())+'/ArtistAsset');asset.GetReferences().AddReference('../original/tower.usdz')
    publish_claim(project,True);source.GetRootLayer().Save()
    meshes=[p for p in source.Traverse() if UsdGeom.Mesh(p)]
    before=source.GetRootLayer().ExportToString()
    print('Python full tower bake',sum(len(UsdGeom.Mesh(p).GetPointsAttr().Get()) for p in meshes),flush=True)
    r=Reader(source,output);out,selected_origin=export_geometry(r,meshes,F/'tower-python-bake.usda')
    print('Native full tower bake starting',flush=True)
    # C++ evaluates the original source stage itself, including all USD stacks.
    n=native(F/'tower-source.usda',[{'prim':str(tower.GetPath()),'kind':'bake','destination':str(F/'tower-native-bake.usda'),'meshes':[str(p.GetPath()) for p in meshes]}],output=output,tag='tower-full')
    if not n['results'][0]['success']:raise RuntimeError(n['results'][0])
    print('Native full tower bake complete',flush=True)
    native_stage=Usd.Stage.Open(str(F/'tower-native-bake.usda'));comparisons=[];bridge=[]
    for i,p in enumerate(meshes):
        py=out.GetPrimAtPath(f'/Context/Origin/Mesh{i}');cpp=native_stage.GetPrimAtPath(f'/Context/Origin/Mesh{i}')
        py_world=row_transform(np.asarray(UsdGeom.Mesh(py).GetPointsAttr().Get(),float),UsdGeom.XformCache().GetLocalToWorldTransform(py))
        cpp_world=row_transform(np.asarray(UsdGeom.Mesh(cpp).GetPointsAttr().Get(),float),UsdGeom.XformCache().GetLocalToWorldTransform(cpp))
        error=np.linalg.norm(py_world-cpp_world,axis=1);assert error.max()<.0001,error.max()
        comparisons.append({'path':str(p.GetPath()),'vertices':len(error),'max_reader_distance_m':float(error.max())})
        bridge.append({'path':str(py.GetPath()),'world_points':py_world.tolist()})
    assert source.GetRootLayer().ExportToString()==before
    (E/'ov-payload.json').write_text(json.dumps({'bake':str(F/'tower-python-bake.usda'),'meshes':bridge}))
    info={'status':'passed','source_position':position,'heading_pitch_roll_deg':[30,0,0],
      'ordinary_adjustment':{'scale':1.15,'rotateZ_degrees':20,'translation_m':[120,-60,0]},
      'asset_authoring':{'original_up_axis':'Y','original_meters_per_unit':.01,'numerical_height_units':300,'writer_conformance_scale':.01,'intentional_resize':100},
      'meshes':comparisons,'source_unchanged':True,'output_crs':output,'display_site_origin':origin.tolist(),
      'proof_scope':'finite mesh vertices and resulting ordinary polygonal bake; no nonlinear continuous-face certificate'}
    (E/'tower-proof.json').write_text(json.dumps(info,indent=2))
    # Baseline placed view has the same source location/attitude, no adjustment.
    placed=Usd.Stage.Open(source.Flatten());p=placed.GetPrimAtPath('/Project/Tower');UsdGeom.Xformable(p).ClearXformOpOrder()
    rr=Reader(placed,output);export_geometry(rr,[placed.GetPrimAtPath(m.GetPath()) for m in meshes],F/'tower-placed-bake.usda')
    print('Placed baseline generated; all source layers unchanged',flush=True)
    make_view(F/'tower-native-bake.usda',F/'tower-render.usda',origin)
    make_view(F/'tower-placed-bake.usda',F/'tower-placed-render.usda',origin)
    print('Evidence and ordinary render stages ready',flush=True)

def make_view(bake,destination,site_origin):
    # Pure ordinary USD viewing copy. This does no CRS evaluation or special reset.
    st=Usd.Stage.CreateNew(str(destination));UsdGeom.SetStageMetersPerUnit(st,1);UsdGeom.SetStageUpAxis(st,'Z')
    view=UsdGeom.Xform.Define(st,'/View');st.SetDefaultPrim(view.GetPrim())
    move=UsdGeom.Xform.Define(st,'/View/DisplayOrigin');move.AddTranslateOp().Set(Gf.Vec3d(*(-site_origin)))
    model=st.DefinePrim('/View/DisplayOrigin/Content');model.GetReferences().AddReference(Path(bake).name)
    # Neutral display colour improves readability where artist materials are
    # unavailable after selected-mesh baking. It is a presentation override.
    for p in st.Traverse():
        m=UsdGeom.Mesh(p)
        if m:
            m.GetDisplayColorAttr().Set([(0.42,.47,.50)]);p.GetRelationship('material:binding').ClearTargets(True)
    ground=UsdGeom.Mesh.Define(st,'/View/Ground');ground.CreatePointsAttr([(-330,-320,-1),(500,-320,-1),(500,400,-1),(-330,400,-1)]);ground.CreateFaceVertexCountsAttr([4]);ground.CreateFaceVertexIndicesAttr([0,1,2,3]);ground.CreateSubdivisionSchemeAttr('none');ground.GetDisplayColorAttr().Set([(.25,.34,.36)])
    for coord in range(-300,501,100):
        line=UsdGeom.BasisCurves.Define(st,'/View/GridE'+str(coord).replace('-','n'));line.CreateTypeAttr('linear');line.CreateCurveVertexCountsAttr([2]);line.CreatePointsAttr([(coord,-320,0),(coord,400,0)]);line.CreateWidthsAttr([.35]);line.GetDisplayColorAttr().Set([(.50,.60,.56)])
    for coord in range(-300,401,100):
        line=UsdGeom.BasisCurves.Define(st,'/View/GridN'+str(coord).replace('-','n'));line.CreateTypeAttr('linear');line.CreateCurveVertexCountsAttr([2]);line.CreatePointsAttr([(-330,coord,0),(500,coord,0)]);line.CreateWidthsAttr([.35]);line.GetDisplayColorAttr().Set([(.50,.60,.56)])
    for label,pts,col in [('East',[(-300,0,1),(450,0,1)],(.15,.48,.67)),('North',[(0,-280,1),(0,380,1)],(.78,.38,.12))]:
        line=UsdGeom.BasisCurves.Define(st,'/View/'+label);line.CreateTypeAttr('linear');line.CreateCurveVertexCountsAttr([2]);line.CreatePointsAttr(pts);line.CreateWidthsAttr([1.5]);line.GetDisplayColorAttr().Set([col])
    camera=UsdGeom.Camera.Define(st,'/View/Camera');camera.GetFocalLengthAttr().Set(40);camera.GetHorizontalApertureAttr().Set(36);camera.GetVerticalApertureAttr().Set(20.25)
    look=Gf.Matrix4d();look.SetLookAt(Gf.Vec3d(650,-900,440),Gf.Vec3d(60,-30,170),Gf.Vec3d(0,0,1));camera.AddTransformOp().Set(look.GetInverse())
    # The neutral recorder supplies one camera light. Avoid duplicate lights.
    st.GetRootLayer().Save()

if __name__=='__main__':main()
