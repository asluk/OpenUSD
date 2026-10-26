"""Neutral real Omniverse stage sink. No CRS resolver is implemented here."""
import json
from pathlib import Path
from pxr import Usd,UsdGeom,Gf
import omni.usd
import omni.kit.app
root=Path(__file__).resolve().parents[1];payload=json.loads((root/'evidence/ov-payload.json').read_text(encoding='utf-8'))
context=omni.usd.get_context();context.new_stage();stage=context.get_stage()
source=Usd.Stage.Open(payload['bake']);stage.GetRootLayer().TransferContent(source.GetRootLayer())
cache=UsdGeom.XformCache();records=[]
for item in payload['meshes']:
    p=stage.GetPrimAtPath(item['path']);pts=UsdGeom.Mesh(p).GetPointsAttr().Get();matrix=cache.GetLocalToWorldTransform(p)
    error=max((matrix.Transform(Gf.Vec3d(x))-Gf.Vec3d(*y)).GetLength() for x,y in zip(pts,item['world_points']))
    if error>1e-7:raise RuntimeError('Omniverse stage readback differs from resolved payload')
    records.append({'path':item['path'],'vertices':len(pts),'maximum_readback_error_m':error})
(root/'evidence/omniverse.json').write_text(json.dumps({'success':True,'consumer':'real omni.usd stage','placement_reader':'external fresh Python reader','independent_reader':False,'meshes':records},indent=2))
print('USD_GEOSPATIAL_OMNIVERSE_SUCCESS',flush=True)
omni.kit.app.get_app().post_quit(0)
