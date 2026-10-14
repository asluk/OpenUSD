"""Composed USD source evaluation, freshly derived from the pinned contract."""
from pathlib import Path
import numpy as np
from pxr import Gf, Plug, Sdf, Usd, UsdGeom
from errors import ResolutionFailure
from geodesy import Definition, Operations, enu_frame, finite
from attitude import from_angles, interpolate, matrix

Plug.Registry().RegisterPlugins(str(Path(__file__).resolve().parents[1]/'schema'))
BINDING='GeospatialCRSBindingAPI'
PLACEMENT=('crs:position','crs:orientation')

def direct(prim):return BINDING in prim.GetAppliedSchemas()

def chain(prim):
    while prim and not prim.IsPseudoRoot():
        yield prim
        prim=prim.GetParent()

def timecode(time):return Usd.TimeCode.Default() if time is None else Usd.TimeCode(time)

def uniform(prim,name,type_name):
    attr=prim.GetAttribute(name)
    if not attr or attr.GetTypeName()!=type_name:raise ResolutionFailure('property-type',f'{prim.GetPath()}.{name}')
    if attr.GetVariability()!=Sdf.VariabilityUniform:raise ResolutionFailure('property-variability',name)
    if attr.GetTimeSamples():raise ResolutionFailure('uniform-time-samples',name)
    value=attr.Get(Usd.TimeCode.Default())
    if value is None:raise ResolutionFailure('unavailable-property',name)
    return value

def definition(prim):return Definition(str(uniform(prim,'crs:wkt',Sdf.ValueTypeNames.Token)))

def placement_fields_valid(prim):
    if direct(prim) and not UsdGeom.Xformable(prim):
        raise ResolutionFailure('invalid-binding-role',str(prim.GetPath()))
    forbidden=(prim.GetTypeName()=='GeospatialDataSource' or not direct(prim))
    if prim.GetTypeName()=='CoordinateReferenceSystem' and not direct(prim):return
    if forbidden:
        for name in PLACEMENT:
            attr=prim.GetAttribute(name)
            if attr and attr.HasAuthoredValueOpinion():
                raise ResolutionFailure('invalid-placement-role',f'{prim.GetPath()}.{name}')

def sampled_vector(prim,name,time):
    attr=prim.GetAttribute(name)
    if not attr or attr.GetTypeName()!=Sdf.ValueTypeNames.Double3 or attr.GetVariability()!=Sdf.VariabilityVarying:
        raise ResolutionFailure('property-type',name)
    value=attr.Get(timecode(time))
    if value is None:raise ResolutionFailure('unavailable-placement',name)
    return finite(value,name)

def orientation(prim,time):
    attr=prim.GetAttribute('crs:orientation')
    if not attr or attr.GetTypeName()!=Sdf.ValueTypeNames.Double3 or attr.GetVariability()!=Sdf.VariabilityVarying:
        raise ResolutionFailure('property-type','crs:orientation')
    samples=attr.GetTimeSamples()
    if time is None or not samples:
        value=attr.Get(Usd.TimeCode.Default())
        if value is None:raise ResolutionFailure('unavailable-orientation','Blocked or missing default')
        return from_angles(value)
    if time<=samples[0]:return from_angles(attr.Get(samples[0]))
    if time>=samples[-1]:return from_angles(attr.Get(samples[-1]))
    lo,hi=attr.GetBracketingTimeSamples(time)
    a=attr.Get(lo)
    if a is None:raise ResolutionFailure('unavailable-orientation',str(lo))
    qa=from_angles(a)
    if lo==hi or prim.GetStage().GetInterpolationType()==Usd.InterpolationTypeHeld:return qa
    b=attr.Get(hi)
    if b is None:raise ResolutionFailure('unavailable-orientation',str(hi))
    return interpolate(qa,from_angles(b),(time-lo)/(hi-lo),(finite(a),finite(b)))

def local(prim,time):
    xf=UsdGeom.Xformable(prim)
    return np.asarray(xf.GetLocalTransformation(timecode(time)),dtype=float) if xf else np.eye(4)

def transform(points,m):
    a=finite(points);one=a.ndim==1
    if one:a=a[None,:]
    result=np.column_stack((a,np.ones(len(a))))@m
    if np.any(result[:,3]==0):raise ResolutionFailure('invalid-homogeneous-transform','Zero divisor')
    result=result[:,:3]/result[:,3,None]
    return result[0] if one else result

def invert(m):
    try:return np.linalg.inv(m)
    except np.linalg.LinAlgError as e:raise ResolutionFailure('singular-required-inverse','Ordinary transform has no inverse') from e

def stage_mapping(stage):
    up=UsdGeom.GetStageUpAxis(stage);units=UsdGeom.GetStageMetersPerUnit(stage)
    if not np.isfinite(units) or units<=0:raise ResolutionFailure('invalid-stage-units',str(units))
    if up=='Z':mapping=np.eye(3)
    elif up=='Y':mapping=np.array([[1,0,0],[0,0,1],[0,-1,0]],float)
    else:raise ResolutionFailure('unsupported-stage-up',str(up))
    return mapping,units

class ModelMap:
    def __init__(self,stage,anchor,working,time,ordinary=None):
        self.stage,self.anchor,self.time=stage,anchor,time
        self.source=definition(anchor);self.working=working
        self.ops=Operations();self.mapping,self.unit=stage_mapping(stage)
        self.position=sampled_vector(anchor,'crs:position',time)
        if self.source.dimension!=3:raise ResolutionFailure('missing-height','Model needs a 3D CRS')
        self.origin,self.basis=enu_frame(self.position,self.source,self.ops)
        self.rotation=matrix(orientation(anchor,time))
        self.a=local(anchor,time) if ordinary is None else ordinary
        finite(self.a,'ordinary transform')
        self.ecef=Definition(self.source.ecef.to_wkt())
        self.origin_w=None;self.chart_basis=None
        if not np.array_equal(self.a,np.eye(4)):
            self.origin_w=self.ops.convert(self.position,self.source,working)
            if working.dimension!=3:raise ResolutionFailure('missing-height','Model adjustment needs complete working CRS')
            if working.kind=='geographic':
                self.chart_origin,self.chart_basis=enu_frame(self.origin_w,working,self.ops)
                self.chart_ecef=Definition(working.ecef.to_wkt())

    def chart(self,p):
        if self.working.kind=='geographic':
            e=self.ops.convert(p,self.working,self.chart_ecef)
            enu=(e-self.chart_origin)@self.chart_basis
            return enu@self.mapping.T/self.unit
        return ((p-self.origin_w)*self.working.semantic_units)@self.mapping.T/self.unit

    def unchart(self,p):
        enu=(p@self.mapping)*self.unit
        if self.working.kind=='geographic':
            e=self.chart_origin+enu@self.chart_basis.T
            return self.ops.convert(e,self.chart_ecef,self.working)
        return enu/self.working.semantic_units+self.origin_w

    def forward(self,points,output):
        x=finite(points)
        e=self.origin+((x@self.mapping)*self.unit)@self.rotation.T@self.basis.T
        if np.array_equal(self.a,np.eye(4)):
            native=self.ops.convert(e,self.ecef,self.source)
            return self.ops.convert(native,self.source,output)
        native=self.ops.convert(e,self.ecef,self.source)
        w=self.ops.convert(native,self.source,self.working)
        w=self.unchart(transform(self.chart(w),self.a))
        return self.ops.convert(w,self.working,output)

    def inverse(self,points,source):
        if np.array_equal(self.a,np.eye(4)):
            native=self.ops.convert(points,source,self.source)
            e=self.ops.convert(native,self.source,self.ecef)
        else:
            w=self.ops.convert(points,source,self.working)
            w=self.unchart(transform(self.chart(w),invert(self.a)))
            native=self.ops.convert(w,self.working,self.source)
            e=self.ops.convert(native,self.source,self.ecef)
        enu=((e-self.origin)@self.basis)@self.rotation
        return enu@self.mapping.T/self.unit

class Reader:
    def __init__(self,stage):
        self.stage=stage

    def selected_output(self,output):
        if output is not None:return output if isinstance(output,Definition) else Definition(output)
        root=self.stage.GetDefaultPrim()
        if root and (direct(root) or root.GetTypeName()=='CoordinateReferenceSystem'):return definition(root)
        raise ResolutionFailure('unspecified-output','No selected output or default binding/context')

    def context(self,prim,time):
        parts=list(chain(prim))
        return self.context_parts(parts,time)

    def context_parts(self,parts,time):
        anchor_index=next((i for i,p in enumerate(parts) if direct(p)),None)
        if anchor_index is None:raise ResolutionFailure('unbound-content',str(parts[0].GetPath()))
        anchor=parts[anchor_index]
        if anchor.GetTypeName()=='GeospatialDataSource':raise ResolutionFailure('measurement-not-model',str(anchor.GetPath()))
        for p in parts[:anchor_index+1]:placement_fields_valid(p)
        enclosing=next((p for p in parts[anchor_index+1:] if direct(p)),None)
        if enclosing:placement_fields_valid(enclosing)
        w=definition(enclosing) if enclosing else None
        w=w or definition(anchor)
        d=np.eye(4);reset=False
        for p in parts[:anchor_index]:
            d=d@local(p,time)
            xf=UsdGeom.Xformable(p)
            if xf and xf.GetResetXformStack():reset=True;break
        model=ModelMap(self.stage,anchor,w,time,np.eye(4) if reset else None)
        return model,d

    def coordinates(self,path,points,output=None,time=None):
        prim=self.stage.GetPrimAtPath(path)
        if not prim:raise ResolutionFailure('missing-prim',path)
        q=self.selected_output(output)
        parts=list(chain(prim))
        binding=next((p for p in parts if direct(p)),None)
        if binding:
            model,d=self.context(prim,time)
            result=model.forward(transform(points,d),q)
            return dict(success=True,coordinates=result.tolist(),coordinate_wkt=q.normal,units=q.unit_names,warnings=sorted(set(x.warning for x in (model.source,model.working,q) if x.warning)),operations=model.ops.observations)
        context=next((p for p in parts if p.GetTypeName()=='CoordinateReferenceSystem'),None)
        if context:
            source=definition(context)
            if source.kind=='geographic' or source.dimension!=3:raise ResolutionFailure('invalid-bake-context','Requires Cartesian 3D')
            m=np.eye(4)
            for p in parts:
                placement_fields_valid(p);m=m@local(p,time)
                xf=UsdGeom.Xformable(p)
                if xf and xf.GetResetXformStack():break
            stage_points=transform(points,m);mapping,unit=stage_mapping(self.stage)
            values=(stage_points@mapping)*unit/source.semantic_units
            ops=Operations();result=ops.convert(values,source,q)
            return dict(success=True,coordinates=result.tolist(),coordinate_wkt=q.normal,units=q.unit_names,warnings=[x.warning for x in (source,q) if x.warning],operations=ops.observations)
        raise ResolutionFailure('unbound-content',path)

    def scene_points(self,path,points,output=None,time=None,numeric_origin=(0,0,0)):
        q=self.selected_output(output)
        scene=q if q.kind!='geographic' else Definition(q.ecef.to_wkt())
        if scene.dimension!=3:raise ResolutionFailure('missing-height','Ordinary scene points require 3D Cartesian meaning')
        result=self.coordinates(path,points,scene,time)
        mapping,unit=stage_mapping(self.stage)
        p=np.asarray(result['coordinates'])
        out=((p-finite(numeric_origin))*scene.semantic_units)@mapping.T/unit
        result.update(scene_points=out.tolist(),scene_chart_wkt=scene.normal,numeric_origin=list(numeric_origin),coordinate_request_wkt=q.normal)
        return result

    def inverse_model(self,path,points,source,time=None):
        prim=self.stage.GetPrimAtPath(path);model,d=self.context(prim,time)
        return transform(model.inverse(points,source),invert(d))

    def derivative(self,path,output=None,time=None):
        prim=self.stage.GetPrimAtPath(path);model,d=self.context(prim,time)
        q=self.selected_output(output);chart=q if q.kind!='geographic' else Definition(q.ecef.to_wkt())
        if not chart.crs.equals(model.ecef.crs):
            raise ResolutionFailure('uncertified-derivative','This prototype certifies only its analytic affine ECEF map')
        mapping,unit=stage_mapping(self.stage)
        row=d[:3,:3]@mapping*unit@model.rotation.T@model.basis.T
        if not np.array_equal(model.a,np.eye(4)):
            if model.working.kind=='geographic' and model.chart_ecef.crs.equals(model.ecef.crs):
                to_chart=model.chart_basis@mapping.T/unit
                from_chart=mapping*unit@model.chart_basis.T
            elif model.working.kind=='geocentric' and model.working.crs.equals(model.ecef.crs):
                to_chart=np.diag(model.working.semantic_units)@mapping.T/unit
                from_chart=mapping*unit@np.diag(1/model.working.semantic_units)
            else:raise ResolutionFailure('uncertified-derivative','Working chart includes an uncertified nonlinear operation')
            row=row@to_chart@model.a[:3,:3]@from_chart
        # Return column derivative in Cartesian metres from local stage coordinates.
        return row.T

    def normal(self,path,normals,output=None,time=None):
        jac=self.derivative(path,output,time)
        try:normal_map=np.linalg.inv(jac).T
        except np.linalg.LinAlgError as e:raise ResolutionFailure('singular-normal-transport','Required inverse transpose unavailable') from e
        n=finite(normals)@normal_map.T
        lengths=np.linalg.norm(n,axis=-1,keepdims=True)
        if np.any(lengths==0):raise ResolutionFailure('zero-normal','Normalization unavailable')
        return n/lengths

    def point_instance(self,instancer_path,index,prototype_path,points,output=None,time=None):
        inst=self.stage.GetPrimAtPath(instancer_path);proto=self.stage.GetPrimAtPath(prototype_path)
        api=UsdGeom.PointInstancer(inst)
        matrices=api.ComputeInstanceTransformsAtTime(timecode(time),timecode(time),UsdGeom.PointInstancer.ExcludeProtoXform,UsdGeom.PointInstancer.IgnoreMask)
        if index>=len(matrices):raise ResolutionFailure('instance-index',str(index))
        mask=api.ComputeMaskAtTime(timecode(time))
        if len(mask) and not mask[index]:raise ResolutionFailure('masked-instance',str(index))
        im=np.asarray(matrices[index],float);q=self.selected_output(output)
        indices=api.GetProtoIndicesAttr().Get(timecode(time))
        targets=api.GetPrototypesRel().GetTargets()
        if indices is None or index>=len(indices) or indices[index]<0 or indices[index]>=len(targets):
            raise ResolutionFailure('prototype-index','Unavailable prototype selection')
        root=targets[indices[index]]
        if not proto.GetPath().HasPrefix(root):raise ResolutionFailure('prototype-path','Query is outside the selected prototype')
        proto_parts=[]
        for p in chain(proto):
            proto_parts.append(p)
            if p.GetPath()==root:break
        independent=any(direct(p) for p in proto_parts)
        if not independent:
            d=np.eye(4)
            for p in proto_parts:
                placement_fields_valid(p);d=d@local(p,time)
                xf=UsdGeom.Xformable(p)
                if xf and xf.GetResetXformStack():break
            p=transform(points,d);p=transform(p,im)
            result=self.coordinates(instancer_path,p,q,time)
        else:
            # Evaluate enclosing contexts on the expanded occurrence, excluding
            # storage ancestors above the prototype root.
            proto_map,proto_d=self.context_parts(proto_parts+list(chain(inst)),time)
            if np.array_equal(im,np.eye(4)):
                values=proto_map.forward(transform(points,proto_d),q)
                result=dict(success=True,coordinates=values.tolist(),coordinate_wkt=q.normal,units=q.unit_names,operations=proto_map.ops.observations,warnings=[])
                result['instance_identity']={'instancer':instancer_path,'index':index,'id':int(api.GetIdsAttr().Get(timecode(time))[index]) if api.GetIdsAttr().Get(timecode(time)) else index,'prototype_relative_path':str(proto.GetPath().MakeRelativePath(root))}
                return result
            inst_model,inst_d=self.context(inst,time)
            ecef=Definition(inst_model.source.ecef.to_wkt())
            absolute=proto_map.forward(transform(points,proto_d),ecef)
            if not np.array_equal(im,np.eye(4)):
                local_points=self.inverse_model(instancer_path,absolute,ecef,time)
                adjusted=transform(local_points,im)
                resolved=self.coordinates(instancer_path,adjusted,q,time)
                result=resolved
            else:
                ops=Operations();values=ops.convert(absolute,ecef,q)
                result=dict(success=True,coordinates=values.tolist(),coordinate_wkt=q.normal,units=q.unit_names,operations=ops.observations,warnings=[])
        result['instance_identity']={'instancer':instancer_path,'index':index,'id':int(api.GetIdsAttr().Get(timecode(time))[index]) if api.GetIdsAttr().Get(timecode(time)) else index,'prototype_relative_path':str(proto.GetPath().MakeRelativePath(root))}
        return result
