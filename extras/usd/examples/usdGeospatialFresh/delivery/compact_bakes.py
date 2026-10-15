"""Lossless ordinary-USD serialization for convenient delivery, not resolution."""
from pathlib import Path
import numpy as np
from pxr import Usd,UsdGeom
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'inputs/authored'
for name in ['tower-native-bake','tower-placed-bake']:
    source=Usd.Stage.Open(str(F/(name+'.usda')))
    destination=F/(name+'.usdc')
    assert source.GetRootLayer().Export(str(destination))
    copied=Usd.Stage.Open(str(destination))
    for p in source.Traverse():
        mesh=UsdGeom.Mesh(p)
        if mesh:
            target=UsdGeom.Mesh(copied.GetPrimAtPath(p.GetPath()))
            assert np.array_equal(np.asarray(mesh.GetPointsAttr().Get()),np.asarray(target.GetPointsAttr().Get()))
            assert UsdGeom.XformCache().GetLocalToWorldTransform(p)==UsdGeom.XformCache().GetLocalToWorldTransform(target.GetPrim())
    view=Usd.Stage.Open(str(F/('tower-render.usda' if name=='tower-native-bake' else 'tower-placed-render.usda')))
    refs=view.GetPrimAtPath('/View/DisplayOrigin/Content').GetReferences();refs.ClearReferences();refs.AddReference(name+'.usdc');view.GetRootLayer().Save()
    print(destination.name,destination.stat().st_size,'bytes, geometry/transforms unchanged')
