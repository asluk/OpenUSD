"""Actual Omniverse context stage sink for externally computed Python results."""
import json
import math
from pathlib import Path
from pxr import Usd,UsdGeom,Plug,Gf
import omni.usd
import omni.kit.app
ROOT=Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT/'schema'))
payload=json.loads((ROOT/'evidence/ov-payload.json').read_text())
context=omni.usd.get_context();context.new_stage();target=context.get_stage()
source=Usd.Stage.Open(payload['bake']);target.GetRootLayer().TransferContent(source.GetRootLayer())
records=[]
cache=UsdGeom.XformCache()
for entry in payload['meshes']:
    p=target.GetPrimAtPath(entry['path']);points=UsdGeom.Mesh(p).GetPointsAttr().Get();m=cache.GetLocalToWorldTransform(p)
    error=max((m.Transform(Gf.Vec3d(point))-Gf.Vec3d(*expected)).GetLength() for point,expected in zip(points,entry['world_points']))
    if error>1e-7:raise RuntimeError('Stage write/readback mismatch')
    records.append({'path':entry['path'],'vertices':len(points),'max_write_readback_m':float(error)})
target.GetRootLayer().Export(str(ROOT/'inputs/authored/ov-context-stage.usda'))
(ROOT/'evidence/ov-consumer.json').write_text(json.dumps({'success':True,'sink':'omni.usd context stage geometry write/readback','placement_evaluator':'External fresh Python reader + PROJ, shared with Python results','independent_placement_reader':False,'meshes':records},indent=2))
print('FRESH_GEOSPATIAL_OV_CONTEXT_SUCCESS',flush=True)
omni.kit.app.get_app().post_quit(0)
