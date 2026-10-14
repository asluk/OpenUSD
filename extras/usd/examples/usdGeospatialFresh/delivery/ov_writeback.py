"""Omniverse stage writeback of the fresh Python reader's bridge payload.
This is stage integration, not an independent placement engine or Fabric path.
"""
from pathlib import Path
import json,numpy as np
from pxr import Usd,UsdGeom,Vt,Plug
ROOT=Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT/'schema'))
payload=json.loads((ROOT/'evidence/ov-input.json').read_text())
source=Usd.Stage.Open(str(ROOT/'fixtures/tower-source.usda'));target=Usd.Stage.CreateInMemory()
records=[]
for item in payload['meshes']:
 mesh=UsdGeom.Mesh(source.GetPrimAtPath(item['path']))
 if not mesh:raise RuntimeError('Missing source mesh: '+item['path'])
 written=np.asarray(item['points'],np.float32);out=UsdGeom.Mesh.Define(target,item['path'])
 out.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(written));out.GetFaceVertexCountsAttr().Set(mesh.GetFaceVertexCountsAttr().Get());out.GetFaceVertexIndicesAttr().Set(mesh.GetFaceVertexIndicesAttr().Get())
 reread=np.asarray(out.GetPointsAttr().Get(),float);records.append({'path':item['path'],'vertices':len(written),'write_readback_max_m':float(np.max(np.linalg.norm(reread-np.asarray(item['points']),axis=1)))})
target.GetRootLayer().Export(str(ROOT/'fixtures/ov-writeback.usda'))
(ROOT/'evidence/ov-writeback.json').write_text(json.dumps({'success':True,'path':'Omniverse in-process USD stage geometry writeback/readback','placement_evaluator':'Fresh Python + PROJ, evaluated externally and bridged as points; shared with Python path','native_binding_api':'No Fabric/ovstage integration claimed','meshes':records},indent=2),encoding='utf-8')
import omni.kit.app
omni.kit.app.get_app().post_quit(0)
