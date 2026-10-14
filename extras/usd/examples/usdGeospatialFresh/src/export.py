"""Explicit selected geometry baking; each retained effect appears once."""
from pathlib import Path
import numpy as np
from pxr import Gf,Sdf,Usd,UsdGeom,Vt
from scene import Reader,BINDING,timecode,definition,stage_mapping
from geodesy import Definition
from errors import ResolutionFailure
from profiles import declare

def geometry_bake(source,path,output,sample_times=(None,),numeric_origin=None):
    reader=Reader(source);q=reader.selected_output(output)
    chart=q if q.kind!='geographic' else Definition(q.ecef.to_wkt())
    if chart.dimension!=3:raise ResolutionFailure('missing-height','Geometry bake requires 3D Cartesian chart')
    mappings=[]
    if any(p.GetTypeName()=='GeospatialDataSource' for p in source.TraverseAll()):
        raise ResolutionFailure('retained-native-dependency','This geometry-only exporter cannot qualify a retained native measurement as known-none')
    if any(UsdGeom.PointInstancer(p) or p.IsInstance() for p in source.Traverse()):
        raise ResolutionFailure('use-occurrence-bake','Instanced geometry requires the occurrence export path')
    for p in source.Traverse():
        mesh=UsdGeom.Mesh(p)
        if mesh and mesh.GetPointsAttr().HasValue():
            for pv in UsdGeom.PrimvarsAPI(p).GetPrimvars():
                if pv.GetTypeName().role in ('Vector','Normal') and pv.HasValue():
                    raise ResolutionFailure('uncertified-primvar-transport','Semantic vector/normal primvars need their own derivative and interpolation handling')
            mappings.append((p,mesh))
    if not mappings:raise ResolutionFailure('no-geometry','No supported polygonal geometry')
    if numeric_origin is None:
        p,mesh=mappings[0]
        numeric_origin=np.asarray(reader.coordinates(str(p.GetPath()),[(0,0,0)],chart,sample_times[0])['coordinates'])[0]
    mapping,unit=stage_mapping(source)
    origin_stage=(np.asarray(numeric_origin)*chart.semantic_units)@mapping.T/unit
    layer=source.Flatten();dest=Usd.Stage.Open(layer)
    root=dest.GetDefaultPrim();root_path=str(root.GetPath())
    root.SetTypeName('CoordinateReferenceSystem')
    for prim in dest.TraverseAll():
        if BINDING in prim.GetAppliedSchemas():prim.RemoveAppliedSchema(BINDING)
        for name in list(prim.GetPropertyNames()):
            if name in ('crs:position','crs:orientation','crs:wkt') or name.startswith('xformOp:') or name=='xformOpOrder':prim.RemoveProperty(name)
    root.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=False,variability=Sdf.VariabilityUniform).Set(chart.normal)
    dest.SetMetadata('timeCodesPerSecond',source.GetTimeCodesPerSecond())
    origin_path=root_path+'/RecordedOrigin'
    if dest.GetPrimAtPath(origin_path):raise ResolutionFailure('export-path-collision','Exporter-selected origin path is occupied')
    origin=UsdGeom.Xform.Define(dest,origin_path)
    origin.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*origin_stage))
    editor=Sdf.BatchNamespaceEdit()
    old_children=[str(p.GetPath()) for p in root.GetChildren() if str(p.GetPath())!=origin_path]
    for child in old_children:editor.Add(child,origin_path+'/'+child.rsplit('/',1)[-1])
    if not layer.Apply(editor):raise ResolutionFailure('export-namespace','Failed ordinary hierarchy reparenting')
    def remap(path):
        for child in old_children:
            if path.HasPrefix(Sdf.Path(child)):
                return path.ReplacePrefix(Sdf.Path(child),Sdf.Path(origin_path+'/'+child.rsplit('/',1)[-1]))
        return path
    for prim in dest.TraverseAll():
        for rel in prim.GetRelationships():
            targets=rel.GetTargets()
            if targets:rel.SetTargets([remap(t) for t in targets])
        for attr in prim.GetAttributes():
            connections=attr.GetConnections()
            if connections:attr.SetConnections([remap(c) for c in connections])
    controls=[]
    for prim,mesh in mappings:
        old=str(prim.GetPath());new=origin_path+old[len(root_path):]
        output_mesh=UsdGeom.Mesh(dest.GetPrimAtPath(new))
        output_mesh.GetPointsAttr().Clear();output_mesh.GetNormalsAttr().Clear();output_mesh.GetExtentAttr().Clear()
        for t in sample_times:
            if np.linalg.det(reader.derivative(str(prim.GetPath()),q,t))<0:
                raise ResolutionFailure('unimplemented-reflected-topology','This exporter has not implemented reflected winding and orientation preservation')
            points=np.asarray(mesh.GetPointsAttr().Get(timecode(t)),float)
            result=reader.scene_points(old,points,q,t,numeric_origin)
            values=np.asarray(result['scene_points'],float)
            written=np.asarray(values,dtype=np.float32)
            error=np.max(np.linalg.norm((written.astype(float)-values)*unit,axis=1)) if len(values) else 0
            output_mesh.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(written),timecode(t))
            normals=mesh.GetNormalsAttr().Get(timecode(t))
            if normals is not None and len(normals):
                # Only a certified analytic derivative is accepted. The writer
                # does not invent normals for an uncertified nonlinear domain.
                n=reader.normal(old,np.asarray(normals),q,t)
                scene_n=n@mapping.T
                output_mesh.GetNormalsAttr().Set(Vt.Vec3fArray.FromNumpy(np.asarray(scene_n,np.float32)),timecode(t))
            if len(written):output_mesh.GetExtentAttr().Set([Gf.Vec3f(*written.min(axis=0).tolist()),Gf.Vec3f(*written.max(axis=0).tolist())],timecode(t))
            controls.append({'source_path':old,'export_path':new,'time':t,'vertices':len(points),'float32_write_error_m':float(error)})
    declare(root,required=False,complete=True)
    layer.Export(str(path))
    return {'path':str(path),'chart_wkt':chart.normal,'numeric_origin':np.asarray(numeric_origin).tolist(),'controls':controls,'source_changed':False,'coverage':'Selected polygonal samples; no continuous nonlinear surface or between-sample certificate'}

def occurrence_bake(source,path,instancer_path,output,time=None,numeric_origin=(0,0,0)):
    reader=Reader(source);q=reader.selected_output(output)
    chart=q if q.kind!='geographic' else Definition(q.ecef.to_wkt())
    if chart.dimension!=3:raise ResolutionFailure('missing-height','Ordinary instance export requires Cartesian 3D')
    inst=UsdGeom.PointInstancer(source.GetPrimAtPath(instancer_path))
    indices=inst.GetProtoIndicesAttr().Get(timecode(time));targets=inst.GetPrototypesRel().GetTargets()
    mask=inst.ComputeMaskAtTime(timecode(time));ids=inst.GetIdsAttr().Get(timecode(time))
    flat=source.Flatten();dest=Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(dest,UsdGeom.GetStageUpAxis(source));UsdGeom.SetStageMetersPerUnit(dest,UsdGeom.GetStageMetersPerUnit(source))
    root=dest.DefinePrim('/Context','CoordinateReferenceSystem');dest.SetDefaultPrim(root)
    root.GetAttribute('crs:wkt').Set(chart.normal)
    mapping,unit=stage_mapping(source)
    origin=UsdGeom.Xform.Define(dest,'/Context/Origin');origin.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*((np.asarray(numeric_origin)*chart.semantic_units)@mapping.T/unit)))
    controls=[]
    for i,index in enumerate(indices):
        if len(mask) and not mask[i]:continue
        proto=source.GetPrimAtPath(targets[index])
        for p in Usd.PrimRange(proto):
            mesh=UsdGeom.Mesh(p)
            if not mesh or not mesh.GetPointsAttr().HasValue():continue
            points=np.asarray(mesh.GetPointsAttr().Get(timecode(time)),float)
            if mesh.GetNormalsAttr().HasValue():
                raise ResolutionFailure('uncertified-instance-normal-export','The occurrence exporter does not yet certify authored normal transport')
            resolved=reader.point_instance(instancer_path,i,str(p.GetPath()),points,chart,time)
            world=np.asarray(resolved['coordinates'])
            local=((world-numeric_origin)*chart.semantic_units)@mapping.T/unit
            rel=str(p.GetPath().MakeRelativePath(proto.GetPath())).replace('.','Root')
            destination='/Context/Origin/Instance_'+str(i)+'/'+rel
            parent=destination.rsplit('/',1)[0];dest.DefinePrim(parent,'Xform')
            Sdf.CopySpec(flat,p.GetPath(),dest.GetRootLayer(),Sdf.Path(destination))
            out=UsdGeom.Mesh(dest.GetPrimAtPath(destination))
            for name in list(out.GetPrim().GetPropertyNames()):
                if name.startswith('xformOp:') or name in ('xformOpOrder','crs:position','crs:orientation','crs:wkt'):out.GetPrim().RemoveProperty(name)
            if BINDING in out.GetPrim().GetAppliedSchemas():out.GetPrim().RemoveAppliedSchema(BINDING)
            out.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(np.asarray(local,np.float32)))
            if len(local):out.GetExtentAttr().Set([Gf.Vec3f(*local.min(axis=0)),Gf.Vec3f(*local.max(axis=0))])
            controls.append({'instance':i,'id':int(ids[i]) if ids is not None else i,'prototype_relative_path':str(p.GetPath().MakeRelativePath(proto.GetPath())),'export_path':destination,'vertices':len(points)})
    declare(root,False,True);dest.SetMetadata('timeCodesPerSecond',source.GetTimeCodesPerSecond());dest.GetRootLayer().Save()
    return {'path':str(path),'controls':controls,'chart_wkt':chart.normal,'numeric_origin':list(numeric_origin),'coverage':'Selected instance polygonal point samples; material-graph closure and continuous domains not claimed'}
