"""Fresh full-data delivery. Neutral scene formatting is shared; placement is not."""
import sys,json,os,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf,Vt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src_py'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from reader import *
from domains import read_domain,resolve_domain
from bake import bake
from run import native,near
from fixtures import carrier,stage,bind,attr
E=ROOT/'evidence';A=ROOT/'inputs/authored';O=ROOT/'inputs/original'
class NativeReader(Reader):
    def points(self,prim,points,output=None,time=None):
        q=self.output(output);p=prim if hasattr(prim,'GetPath') else self.stage.GetPrimAtPath(prim)
        req={'stage':self.stage.GetRootLayer().realPath,'prim':str(p.GetPath()),'points':np.asarray(points).tolist(),'output':q.to_wkt()}
        if time is not None:req['time']=time
        report=native(req,'full-mesh',keep_arrays=False);return np.array(report['points'])

def render_scene(baked,path):
    """A stated presentation chart for actual resolved coordinates, no geospatial solver."""
    s=Usd.Stage.Open(str(baked));meshes=[p for p in s.Traverse() if p.IsA(UsdGeom.Mesh)]
    cache=UsdGeom.XformCache();worlds=[]
    for p in meshes:
        local=UsdGeom.Mesh(p).GetPointsAttr().Get();worlds.append(apply_matrix(local,cache.GetLocalToWorldTransform(p)))
    allpoints=np.concatenate(worlds);origin=allpoints.mean(axis=0);basis=enu_basis(2.2945,48.8584)
    # Camera display uses a local ENU chart, preserving the resolved geometry.
    display=[(x-origin)@basis for x in worlds];base=min(x[:,2].min() for x in display)
    out=Usd.Stage.CreateNew(str(path));UsdGeom.SetStageMetersPerUnit(out,1);UsdGeom.SetStageUpAxis(out,'Z')
    view=UsdGeom.Xform.Define(out,'/View');out.SetDefaultPrim(view.GetPrim())
    for i,(p,points) in enumerate(zip(meshes,display)):
        src=UsdGeom.Mesh(p);m=UsdGeom.Mesh.Define(out,f'/View/Tower{i}');m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points.astype(np.float32)))
        m.CreateFaceVertexCountsAttr(src.GetFaceVertexCountsAttr().Get());m.CreateFaceVertexIndicesAttr(src.GetFaceVertexIndicesAttr().Get());m.CreateSubdivisionSchemeAttr('none');m.CreateDisplayColorAttr([(0.42,0.35,0.27)]);m.CreateDoubleSidedAttr(True)
    ground=UsdGeom.Mesh.Define(out,'/View/Ground');ground.CreatePointsAttr([(-550,-550,base-0.5),(550,-550,base-0.5),(550,550,base-0.5),(-550,550,base-0.5)]);ground.CreateFaceVertexCountsAttr([4]);ground.CreateFaceVertexIndicesAttr([0,1,2,3]);ground.CreateDisplayColorAttr([(0.78,0.82,0.77)]);ground.CreateSubdivisionSchemeAttr('none')
    lines=UsdGeom.BasisCurves.Define(out,'/View/MetricGrid');pts=[]
    for x in range(-500,501,50):pts.extend([(x,-500,base), (x,500,base),(-500,x,base),(500,x,base)])
    lines.CreatePointsAttr(pts);lines.CreateCurveVertexCountsAttr([2]*(len(pts)//2));lines.CreateTypeAttr('linear');lines.CreateWidthsAttr([0.5]);lines.CreateDisplayColorAttr([(0.4,0.5,0.44)])
    sky=UsdGeom.Sphere.Define(out,'/View/Sky');sky.CreateRadiusAttr(4500);sky.CreateDoubleSidedAttr(True)
    material=UsdShade.Material.Define(out,'/View/SkyMaterial');shader=UsdShade.Shader.Define(out,'/View/SkyMaterial/Shader');shader.CreateIdAttr('UsdPreviewSurface');shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set((0,0,0));shader.CreateInput('emissiveColor',Sdf.ValueTypeNames.Color3f).Set((0.70,0.79,0.86));material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');UsdShade.MaterialBindingAPI.Apply(sky.GetPrim()).Bind(material)
    cam=UsdGeom.Camera.Define(out,'/View/Camera');eye=Gf.Vec3d(700,-1000,520);target=Gf.Vec3d(0,0,30)
    v=Gf.Matrix4d().SetLookAt(eye,target,Gf.Vec3d(0,0,1));cam.AddTransformOp().Set(v.GetInverse());cam.CreateClippingRangeAttr((1,10000));cam.CreateFocalLengthAttr(32)
    out.GetRootLayer().Save();return {'display_chart':'ENU at 2.2945E,48.8584N, centered for camera; not a surveyed Paris setting','grid_spacing_m':50,'vertices':len(allpoints),'origin_ECEF':origin.tolist()}

def landxml():
    root=ET.parse(O/'Colorado/Trimble Westminster Park and Ride LandXML.xml').getroot()
    segments=[]
    for item in root.iter():
        if item.tag.endswith('}PntList3D') and item.text:
            a=np.fromstring(item.text,sep=' ').reshape(-1,3);segments.append(a[:,[1,0,2]])
    coords=np.concatenate(segments);c=as_crs((O/'Colorado/03_Westminster_Site_Calibration_WKT2.txt').read_text(encoding='utf-8'))
    q=as_crs((O/'Colorado/02_NAD83-2011_ColoradoCentral_NAVD88_WKT2.txt').read_text(encoding='utf-8'))
    # LandXML is not one of the proposal's native association profiles. A query
    # client explicitly supplies original records plus the provider companion WKT.
    # Do not disguise this as a conforming CF representation of the site grid.
    engine=Engine();py={'resolved':engine.convert(coords,c,q)}
    n=native({'coordinateSource':c.to_wkt(),'output':q.to_wkt(),'points':coords.tolist()},'full-landxml');units=np.array([a.unit_conversion_factor for a in q.axis_info]);err=near(py['resolved']*units,np.array(n['points'])*units)
    np.savez_compressed(E/'westminster.npz',source=coords,output=py['resolved'],segment_lengths=np.array([len(x) for x in segments]))
    breaklines=[x for p in root.iter() if p.tag.endswith('}Breakline') for x in p.iter() if x.tag.endswith('}PntList3D')]
    return {'points':len(coords),'polylines':len(segments),'breakline_points':sum(len(np.fromstring(x.text,sep=' '))//3 for x in breaklines),'agreement_m':err,'adaptation':'Original LandXML records supplied to coordinate-query clients with provider companion WKT; original polyline values, order, US survey feet and associations preserved. No standard LandXML USD association is claimed.'}

def run():
    results={};source=Usd.Stage.Open(str(A/'tower.usda'));q=CRS.from_epsg(4978)
    out,report=bake(source,A/'tower-native-bake.usda',q,reader=NativeReader(source))
    results['native_bake']=report; (E/'native-bake.json').write_text(json.dumps(report,indent=2))
    py=Usd.Stage.Open(str(A/'tower-python-bake.usda'));nr=Reader(out);pr=Reader(py);errors=[]
    payload=[]
    for m in report['meshes']:
        p=out.GetPrimAtPath(m['export']);pts=UsdGeom.Mesh(p).GetPointsAttr().Get();n=nr.points(p,pts,q)
        pp=py.GetPrimAtPath(m['export']);ppts=UsdGeom.Mesh(pp).GetPointsAttr().Get();pv=pr.points(pp,ppts,q);errors.append(near(n,pv,0.001))
        payload.append({'path':m['export'],'world_points':pv.tolist()})
    results['all_meshes_reader_agreement_m']=max(errors)
    results['render_scene']=render_scene(A/'tower-native-bake.usda',A/'tower-storm-view.usda')
    results['landxml']=landxml()
    (E/'ov-payload.json').write_text(json.dumps({'bake':str(A/'tower-python-bake.usda'),'meshes':payload}))
    (E/'full-data.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({k:v for k,v in results.items() if k!='native_bake'},indent=2),flush=True)
if __name__=='__main__':run()
