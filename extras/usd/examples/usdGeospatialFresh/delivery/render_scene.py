from pathlib import Path
import sys,numpy as np
from pxr import Usd,UsdGeom,UsdLux,Gf
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from scene import Reader
from geodesy import Definition
from pyproj import CRS
source=Usd.Stage.Open(str(ROOT/'fixtures/tower-baked.usda'));dest=Usd.Stage.Open(source.Flatten())
evidence=np.load(ROOT/'evidence/tower-cartesian.npz');origin=evidence['origin']
# Rendering recentering is an ordinary transform in a presentation copy. It
# rotates geocentric axes into the local site view; proof files remain unchanged.
lon,lat=np.radians([2.2945,48.8584]);basis=np.array([[-np.sin(lon),-np.sin(lat)*np.cos(lon),np.cos(lat)*np.cos(lon)],[np.cos(lon),-np.sin(lat)*np.sin(lon),np.cos(lat)*np.sin(lon)],[0,np.cos(lat),np.sin(lat)]])
root=dest.GetDefaultPrim();originPrim=next(p for p in root.GetChildren() if UsdGeom.Xformable(p));xf=UsdGeom.Xformable(originPrim);xf.ClearXformOpOrder()
m=np.eye(4);m[:3,:3]=basis;m[3,:3]=-origin@basis;xf.AddTransformOp().Set(Gf.Matrix4d(*m.reshape(-1).tolist()))
# Above root chart's absolute double origin was cleared, so compensate by using
# absolute points in the viewing copy (not the evaluated output artifact).
for p in dest.Traverse():
 mesh=UsdGeom.Mesh(p)
 if mesh and mesh.GetPointsAttr().HasValue():
  values=np.asarray(mesh.GetPointsAttr().Get(),float)+origin
  # Use a local double calculation, then ordinary metre geometry for precision.
  view=(values-origin)@basis;mesh.GetPointsAttr().Set(view.astype(np.float32).tolist())
xf.ClearXformOpOrder()
ground=UsdGeom.Mesh.Define(dest,'/View/Ground');ground.GetPointsAttr().Set([(-280,-230,-1),(280,-230,-1),(280,230,-1),(-280,230,-1)]);ground.GetFaceVertexCountsAttr().Set([4]);ground.GetFaceVertexIndicesAttr().Set([0,1,2,3]);ground.GetDisplayColorAttr().Set([(0.48,0.57,0.53)]);ground.CreateSubdivisionSchemeAttr().Set('none')
for axis,color in [('East',(0.25,0.64,0.78)),('North',(0.95,0.68,0.24))]:
 line=UsdGeom.BasisCurves.Define(dest,'/View/'+axis);line.CreateTypeAttr().Set('linear');line.GetCurveVertexCountsAttr().Set([2]);line.GetPointsAttr().Set([(-240,0,0),(240,0,0)] if axis=='East' else [(0,-190,0),(0,190,0)]);line.GetWidthsAttr().Set([2]);line.GetDisplayColorAttr().Set([color])
cam=UsdGeom.Camera.Define(dest,'/View/Camera');cam.GetProjectionAttr().Set('perspective');cam.GetFocalLengthAttr().Set(42);cam.GetHorizontalApertureAttr().Set(36)
eye=Gf.Vec3d(470,-630,380);center=Gf.Vec3d(0,0,150);look=Gf.Matrix4d();look.SetLookAt(eye,center,Gf.Vec3d(0,0,1));cam.AddTransformOp().Set(look.GetInverse())
light=UsdLux.DomeLight.Define(dest,'/View/Sky');light.GetIntensityAttr().Set(1.8)
sun=UsdLux.DistantLight.Define(dest,'/View/Sun');sun.GetIntensityAttr().Set(1.8);sun.AddRotateXYZOp().Set((20,-45,-20))
UsdGeom.SetStageUpAxis(dest,'Z');UsdGeom.SetStageMetersPerUnit(dest,1);dest.GetRootLayer().Export(str(ROOT/'fixtures/tower-render.usda'))
print('View copy uses the actual C++-resolved ordinary USD bake; site ground is illustrative.')
