"""Sampled experimental export preserving ordinary USD content and associations.

The representation is pinned in proposal/data-model.md before this implementation.
It is not an approved standard export encoding.
"""
from pathlib import Path
import numpy as np
from pxr import Usd,UsdGeom,Gf,Sdf,Vt
from .resolve import Resolver,axis_factors,native_to_stage_basis
from .model import crs,normalize_wkt,binding,GeoError

def export(stage,path,output,times):
    path=Path(path)
    if path.exists():raise GeoError('Export must create a new asset')
    times=sorted(set(float(t) for t in times))
    if not times or not np.isfinite(times).all():raise GeoError('Explicit finite export sample times required')
    out=crs(output);wkt=normalize_wkt(output);resolver=Resolver(stage)
    model_roots=[p for p in stage.Traverse(Usd.TraverseInstanceProxies())
                 if p.GetAttribute('crs:position') and p.GetAttribute('crs:position').HasAuthoredValue()]
    if out.is_geographic and model_roots:raise GeoError('Geographic model-frame export is not defined; coordinate-only export is supported')
    layer=stage.Flatten();dst=Usd.Stage.Open(layer)
    while True:
        instances=[p for p in dst.Traverse() if p.IsInstance()]
        if not instances:break
        for p in instances:p.SetInstanceable(False)
    definition=None
    for p in dst.Traverse():
        a=p.GetAttribute('crs:wkt')
        if a and a.Get()==wkt:definition=p;break
    if definition is None:
        name='/GeospatialExportCRS';i=0
        while dst.GetPrimAtPath(name):i+=1;name='/GeospatialExportCRS'+str(i)
        definition=dst.DefinePrim(name,'CoordinateReferenceSystem')
        definition.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=True,variability=Sdf.VariabilityUniform).Set(wkt)
    for p in dst.Traverse():
        rel=p.GetRelationship('crs:binding')
        if rel and rel.HasAuthoredTargets():
            binding(p)
            rel.SetTargets([definition.GetPath()])
    unit=UsdGeom.GetStageMetersPerUnit(stage);axes=native_to_stage_basis(stage)
    for source in model_roots:
        p=dst.GetPrimAtPath(source.GetPath())
        position=p.GetAttribute('crs:position');position.Clear()
        for name,value,typ in [('crs:orientation',Gf.Quatd(1),Sdf.ValueTypeNames.Quatd),
                               ('crs:scale',Gf.Vec3d(1),Sdf.ValueTypeNames.Double3)]:
            a=p.GetAttribute(name) or p.CreateAttribute(name,typ,custom=True)
            a.Clear();a.Set(value)
        x=UsdGeom.Xformable(p);x.ClearXformOpOrder()
        op=x.AddTransformOp(UsdGeom.XformOp.PrecisionDouble,'geospatialExport')
        for t in times:
            frame,_=resolver.frame(source,output,Usd.TimeCode(t))
            linear=(frame[:3,:3]*axis_factors(out)/unit)@axes
            anchor=(frame[3,:3]*axis_factors(out)/unit)@axes
            post=np.eye(4);post[:3,:3]=linear;post[3,:3]=anchor-anchor@linear
            position.Set(Gf.Vec3d(*frame[3,:3]),t)
            op.Set(Gf.Matrix4d(*post.ravel().tolist()),t)
    for source in stage.Traverse(Usd.TraverseInstanceProxies()):
        roles=source.GetRelationship('crs:coordinateProperties')
        if not roles or not roles.HasAuthoredTargets():continue
        for property_path in roles.GetTargets():
            a=dst.GetAttributeAtPath(property_path);a.Clear()
            for t in times:
                points=resolver.measures(source,output,Usd.TimeCode(t))[str(property_path)].points
                a.Set(Vt.Vec3dArray([Gf.Vec3d(*p) for p in points]),t)
    metadata=dict(layer.customLayerData)
    metadata.update(geospatialResolutionRequired=True,geospatialExport={
        'sampledTimeCodes':Vt.DoubleArray(times),
        'interpolation':'USD linear interpolation of derived placement/matrix/coordinate samples; not equivalence to the original source-CRS path between samples',
        'representation':'experimental preserved ordinary USD content'})
    layer.customLayerData=metadata
    if not layer.Export(str(path)):raise GeoError('Could not write derived asset')
    return Usd.Stage.Open(str(path))
