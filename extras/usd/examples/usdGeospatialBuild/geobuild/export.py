"""Explicit derived asset. No private resolved state is authored."""
import numpy as np
from pxr import Usd,UsdGeom,Gf,Sdf,Vt
from .resolve import Resolver,axis_factors,native_to_stage_basis
from .model import crs,normalize_wkt
def export(stage,path,output,times):
    out=crs(output)
    if out.is_geographic:raise ValueError('This candidate supports angular coordinate export; geographic model-frame export is not defined')
    dst=Usd.Stage.CreateNew(str(path));UsdGeom.SetStageMetersPerUnit(dst,UsdGeom.GetStageMetersPerUnit(stage));UsdGeom.SetStageUpAxis(dst,UsdGeom.GetStageUpAxis(stage))
    dst.GetRootLayer().customLayerData={'geospatialResolutionRequired':True,'geospatialExport':{'sampledTimeCodes':Vt.DoubleArray(times),'interpolation':'USD linear interpolation of derived sampled positions/geometry; not the original source-CRS path','outputCRS':normalize_wkt(output)}}
    p=dst.DefinePrim('/CRS/Output','CoordinateReferenceSystem');p.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=True,variability=Sdf.VariabilityUniform).Set(normalize_wkt(output))
    resolver=Resolver(stage);count=0
    for source in stage.Traverse(Usd.TraverseInstanceProxies()):
        rel=source.GetRelationship('crs:coordinateProperties')
        if rel and rel.HasAuthoredTargets():
            p=UsdGeom.Scope.Define(dst,'/Measurements/M'+str(count)).GetPrim();count+=1;p.CreateRelationship('crs:binding',custom=True).SetTargets(['/CRS/Output']);paths=[]
            for a in source.GetAttributes():
                if a.GetName().startswith('data:'):
                    b=p.CreateAttribute(a.GetName(),a.GetTypeName(),custom=True,variability=a.GetVariability())
                    if a.Get() is not None:b.Set(a.Get())
                    for t in a.GetTimeSamples():b.Set(a.Get(t),t)
            for source_path in rel.GetTargets():
                a=stage.GetAttributeAtPath(source_path);b=p.GetAttribute(a.GetName());paths.append(b.GetPath())
                for t in times:b.Set(Vt.Vec3dArray([Gf.Vec3d(*q) for q in resolver.measures(source,output,Usd.TimeCode(t))[str(source_path)].points]),t)
            p.CreateRelationship('crs:coordinateProperties',custom=True).SetTargets(paths)
        a=source.GetAttribute('points')
        if not a or a.Get() is None:continue
        try:resolver.model(source)
        except ValueError:continue
        p=UsdGeom.Xform.Define(dst,'/Models/M'+str(count)).GetPrim();count+=1;p.CreateRelationship('crs:binding',custom=True).SetTargets(['/CRS/Output']);position=p.CreateAttribute('crs:position',Sdf.ValueTypeNames.Double3,custom=True)
        geo=dst.DefinePrim(str(p.GetPath())+'/Geometry',source.GetTypeName());points=geo.CreateAttribute('points',Sdf.ValueTypeNames.Point3fArray)
        for name in ['faceVertexCounts','faceVertexIndices','subdivisionScheme','curveVertexCounts','type','basis','wrap','widths','primvars:displayColor']:
            b=source.GetAttribute(name)
            if b and b.Get() is not None:geo.CreateAttribute(name,b.GetTypeName()).Set(b.Get())
        for t in times:
            resolved=resolver.geometry(source,output,Usd.TimeCode(t));anchor=resolved.points[0];local=((resolved.points-anchor)*axis_factors(out)/UsdGeom.GetStageMetersPerUnit(stage))@native_to_stage_basis(stage)
            position.Set(Gf.Vec3d(*anchor),t);points.Set(Vt.Vec3fArray([Gf.Vec3f(*q) for q in local]),t)
    dst.GetRootLayer().Save();return dst
