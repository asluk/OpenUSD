"""Pointwise interpretation of the pinned proposal candidate.

Authored facts are read by USD, never from a fixture-name switch. Numerical
methods and caches are implementation choices, not additional scene facts.
"""
import math
import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom
from pyproj import CRS, Transformer, proj_version_str
from review.scope import discover, ScopeError
from review.placement_values import read
from review.wkt_profile import normalize,WKTProfileError

class ContractError(ValueError): pass

def bound(prim):
    if not prim: return False
    schemas=prim.GetMetadata('apiSchemas')
    return bool(schemas and 'GeospatialCRSBindingAPI' in schemas.GetAppliedItems())

def definition(prim):
    try: record=discover(prim)
    except ScopeError as e: raise ContractError(str(e)) from e
    wkt=record['wkt']
    try:
        if normalize(wkt)!=wkt: raise ContractError('WKT is not normalized')
    except WKTProfileError as e:raise ContractError('Invalid WKT: '+str(e)) from e
    if 'COORDINATEMETADATA' in wkt: raise ContractError('Coordinate epochs deferred')
    c=CRS.from_wkt(wkt)
    if c.is_bound: raise ContractError('BOUNDCRS interpretation not implemented; embedded operation retained')
    roles={a.direction for a in c.axis_info}
    if roles not in [{'east','north'}, {'east','north','up'}, {'geocentricX','geocentricY','geocentricZ'}]:
        raise ContractError('Unsupported component set')
    return prim.GetStage().GetPrimAtPath(record['binding_prim']),c

def factors(c):
    roles={a.direction:a.unit_conversion_factor for a in c.axis_info}
    names=['geocentricX','geocentricY','geocentricZ'] if c.is_geocentric else ['east','north','up']
    return np.array([roles[n] for n in names if n in roles])

def basis(stage):
    if UsdGeom.GetStageUpAxis(stage)==UsdGeom.Tokens.z: return np.eye(3)
    # Row vectors: stage -> ordered metric basis.
    return np.array([[1,0,0],[0,0,1],[0,-1,0]],float)

def ecef(c,xyz):
    if c.is_geographic and c.sub_crs_list:
        raise ContractError('Geographic gravity-related height needs an explicit ellipsoidal vertical conversion; this adapter does not construct that chart')
    v=np.asarray(xyz,float)*factors(c)
    lo,la,h=v[...,0],v[...,1],v[...,2]
    a=c.ellipsoid.semi_major_metre;b=c.ellipsoid.semi_minor_metre
    e2=1-(b/a)**2;n=a/np.sqrt(1-e2*np.sin(la)**2)
    return np.stack(((n+h)*np.cos(la)*np.cos(lo),(n+h)*np.cos(la)*np.sin(lo),(n*(1-e2)+h)*np.sin(la)),axis=-1)

def enu(c,origin):
    lo,la=(np.asarray(origin)*factors(c))[:2]
    if abs(abs(la)-math.pi/2)<1e-14: raise ContractError('ENU orientation undefined at a pole')
    return np.array([[-np.sin(lo),np.cos(lo),0],[-np.sin(la)*np.cos(lo),-np.sin(la)*np.sin(lo),np.cos(la)],[np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)]])

def from_ecef(c,xyz):
    # PROJ inverse geocentric conversion using the actual ellipsoid, not WGS84.
    tr=Transformer.from_pipeline('+proj=pipeline +step +inv +proj=cart '
        f'+a={c.ellipsoid.semi_major_metre:.17g} +b={c.ellipsoid.semi_minor_metre:.17g} '
        '+step +proj=unitconvert +xy_in=rad +xy_out=deg')
    x=np.asarray(xyz,float);v=np.stack(tr.transform(*x.T,errcheck=True),axis=-1)
    v[:,:2]*=math.pi/180
    return v/factors(c)

def local_source(c,origin,metric):
    if len(c.axis_info)!=3: raise ContractError('Model placement requires a complete 3D CRS')
    if c.is_geographic:
        if c.axis_info[-1].direction!='up' or 'gravity' in c.axis_info[-1].name.lower():
            raise ContractError('Ellipsoidal ENU needs an explicit vertical conversion')
        if not np.any(metric): return np.broadcast_to(origin,np.asarray(metric).shape).copy()
        return from_ecef(c,ecef(c,origin)+np.asarray(metric)@enu(c,origin))
    return np.asarray(origin)+np.asarray(metric)/factors(c)

class Runtime:
    def __init__(self,stage,output,time=0):
        self.stage=stage;self.time=Usd.TimeCode(time);self.unit=UsdGeom.GetStageMetersPerUnit(stage);self.B=basis(stage)
        if not math.isfinite(self.unit) or self.unit<=0: raise ContractError('Invalid stage metric')
        self.output=CRS.from_wkt(output) if output else definition(stage.GetDefaultPrim())[1]
        self.operations=[];self.cache={}

    def convert(self,source,target,points):
        x=np.asarray(points,float);was_vector=x.ndim==1;x=np.atleast_2d(x)
        if not np.isfinite(x).all(): raise ContractError('Nonfinite coordinate')
        if x.shape[1]!=len(source.axis_info) or len(source.axis_info)!=len(target.axis_info):
            raise ContractError('No implicit height or dimensional promotion')
        if source.is_geographic and np.any(np.abs(x[:,1]*factors(source)[1])>math.pi/2+1e-14):
            raise ContractError('Latitude outside domain')
        key=(source.srs,target.srs)
        tr=self.cache.get(key)
        if tr is None:
            tr=Transformer.from_crs(source,target,always_xy=True,allow_ballpark=False,only_best=True);self.cache[key]=tr
        v=x.copy()
        if source.is_geographic: v[:,:2]*=factors(source)[:2]*180/math.pi
        try: y=np.stack(tr.transform(*v.T,errcheck=True),axis=-1)
        except Exception as e: raise ContractError('Coordinate operation failed; no substitute') from e
        if not np.isfinite(y).all(): raise ContractError('Coordinate operation failed; whole batch rejected')
        try: op=tr.get_last_used_operation()
        except Exception: op=tr
        if any(t in op.definition for t in ['t_epoch=','+proj=deformation','+dx=','+dy=','+dz=','+drx=','+dry=','+drz=','+ds=']):
            raise ContractError('Epoch-dependent transformation deferred')
        self.operations.append({'description':op.description,'definition':op.definition,'accuracy_metres':op.accuracy if op.accuracy>=0 else None})
        if target.is_geographic: y[:,:2]/=factors(target)[:2]*180/math.pi
        return y[0] if was_vector else y

    def stack(self,prim,anchor):
        result=Gf.Matrix4d(1);reset=False;p=prim
        while p and p!=anchor:
            x=UsdGeom.Xformable(p)
            if x:
                result=result*x.GetLocalTransformation(self.time)
                if x.GetResetXformStack(): reset=True;break
            p=p.GetParent()
        return result,reset

    def placement(self,prim,points):
        anchor,source=definition(prim)
        if not UsdGeom.Xformable(anchor): raise ContractError('Data source is not a model anchor')
        try: record=read(anchor,self.time)
        except ScopeError as e: raise ContractError(str(e)) from e
        q=record['orientation'];quat=Gf.Quatd(q['real'],Gf.Vec3d(*q['imaginary']))
        # Rounding tolerance is a validator numerical limitation, not authoring normalization.
        if abs(quat.GetLength()-1)>8*np.finfo(float).eps: raise ContractError('Orientation is not unit length')
        D,reset=self.stack(prim,anchor)
        v=np.array([D.Transform(Gf.Vec3d(*map(float,p))) for p in np.atleast_2d(points)])
        metric=((v@self.B)*self.unit*np.array(record['scale']))@np.array(Gf.Matrix3d(quat))
        source_points=local_source(source,np.array(record['position']),metric)
        A=Gf.Matrix4d(1) if reset else UsdGeom.Xformable(anchor).GetLocalTransformation(self.time)
        parent=anchor.GetParent()
        while parent and not parent.IsPseudoRoot() and not bound(parent): parent=parent.GetParent()
        if parent and not parent.IsPseudoRoot(): context,work=definition(parent)
        else: context,work=anchor,source
        if A==Gf.Matrix4d(1): return self.convert(source,self.output,source_points)
        w=self.convert(source,work,source_points)
        if work.is_geographic:
            try: pivot=read(context,self.time)['position']
            except ScopeError as e: raise ContractError('Geographic adjustment chart has no origin') from e
            origin=np.array(pivot);E=enu(work,origin)
            chart=((ecef(work,w)-ecef(work,origin))@E.T)@self.B.T/self.unit
        else: chart=(w*factors(work))@self.B.T/self.unit
        adjusted=np.array([A.Transform(Gf.Vec3d(*map(float,p))) for p in chart])*self.unit@self.B
        if work.is_geographic: w=from_ecef(work,ecef(work,origin)+adjusted@E)
        else: w=adjusted/factors(work)
        return self.convert(work,self.output,w)

    def geometry(self):
        records={};self.geometry_sources={}
        instancers=[UsdGeom.PointInstancer(p) for p in self.stage.Traverse() if p.IsA(UsdGeom.PointInstancer)]
        prototype_roots={str(path) for inst in instancers for path in inst.GetPrototypesRel().GetTargets()}
        for prim in self.stage.Traverse(Usd.TraverseInstanceProxies()):
            if any(str(prim.GetPath())==path or str(prim.GetPath()).startswith(path+'/') for path in prototype_roots):continue
            a=prim.GetAttribute('points')
            if not a or not a.HasAuthoredValue(): continue
            try: definition(prim)
            except ContractError as e:
                if 'No CRS binding' in str(e): continue
                raise
            points=a.Get(self.time)
            if points is None: raise ContractError('Geometry sample unavailable')
            y=self.placement(prim,np.array(points));records[str(prim.GetPath())]=y.tolist();self.geometry_sources[str(prim.GetPath())]=str(prim.GetPath())
        for inst in instancers:
            prim=inst.GetPrim();transforms=inst.ComputeInstanceTransformsAtTime(self.time,self.time,UsdGeom.PointInstancer.IncludeProtoXform,UsdGeom.PointInstancer.IgnoreMask);indices=inst.GetProtoIndicesAttr().Get(self.time);prototypes=inst.GetPrototypesRel().GetTargets();mask=inst.ComputeMaskAtTime(self.time)
            for i,(matrix,index) in enumerate(zip(transforms,indices)):
                if mask and not mask[i]:continue
                proto=self.stage.GetPrimAtPath(prototypes[index])
                for mesh in Usd.PrimRange(proto):
                    if bound(mesh):raise ContractError('Independently CRS-bound point-instancer prototype is undefined')
                    a=mesh.GetAttribute('points')
                    if not a or not a.HasAuthoredValue():continue
                    local,_=self.stack(mesh,proto);composed=local*matrix
                    points=np.array([composed.Transform(Gf.Vec3d(*map(float,p))) for p in a.Get(self.time)])
                    path=str(prim.GetPath())+'/_ResolvedInstance'+str(i)+'/'+mesh.GetName()
                    if path in records:raise ContractError('Runtime instance output identity collision')
                    records[path]=self.placement(prim,points).tolist();self.geometry_sources[path]=str(mesh.GetPath())
        return records

    def inverse_placement(self,prim,coordinates):
        anchor,source=definition(prim);record=read(anchor,self.time);D,reset=self.stack(prim,anchor)
        q=record['orientation'];quat=Gf.Quatd(q['real'],Gf.Vec3d(*q['imaginary']))
        if abs(quat.GetLength()-1)>8*np.finfo(float).eps:raise ContractError('Orientation is not unit length')
        A=Gf.Matrix4d(1) if reset else UsdGeom.Xformable(anchor).GetLocalTransformation(self.time)
        if any(v==0 for v in record['scale']) or D.GetDeterminant()==0 or A.GetDeterminant()==0:
            raise ContractError('Singular placement has no inverse')
        parent=anchor.GetParent()
        while parent and not parent.IsPseudoRoot() and not bound(parent):parent=parent.GetParent()
        context,work=definition(parent) if parent and not parent.IsPseudoRoot() else (anchor,source)
        if A==Gf.Matrix4d(1):s=self.convert(self.output,source,coordinates)
        else:
            w=self.convert(self.output,work,coordinates)
            if work.is_geographic:
                origin=np.array(read(context,self.time)['position']);E=enu(work,origin)
                chart=((ecef(work,w)-ecef(work,origin))@E.T)@self.B.T/self.unit
            else:chart=(w*factors(work))@self.B.T/self.unit
            v=np.array([A.GetInverse().Transform(Gf.Vec3d(*map(float,p))) for p in np.atleast_2d(chart)])*self.unit@self.B
            w=from_ecef(work,ecef(work,origin)+v@E) if work.is_geographic else v/factors(work)
            s=self.convert(work,source,w)
        origin=np.array(record['position'])
        v=(ecef(source,s)-ecef(source,origin))@enu(source,origin).T if source.is_geographic else (s-origin)*factors(source)
        q=record['orientation'];R=np.array(Gf.Matrix3d(Gf.Quatd(q['real'],Gf.Vec3d(*q['imaginary']))))
        local=(v@R.T)/np.array(record['scale'])/self.unit@self.B.T
        return np.array([D.GetInverse().Transform(Gf.Vec3d(*map(float,p))) for p in np.atleast_2d(local)])

    def stage_coordinates(self,points,origin):
        if self.output.is_geographic: raise ContractError('Geographic scene geometry remains Q9')
        return (np.asarray(points)-np.asarray(origin))*factors(self.output)@self.B.T/self.unit

    def frame(self,prim):
        """Numerical derivative of the complete point map, not an extent bound."""
        if self.output.is_geographic or len(self.output.axis_info)!=3:
            raise ContractError('Geographic scene frames remain Q9; a 3D Cartesian frame is required')
        def derivative(step):
            offsets=np.eye(3)*step
            return (self.placement(prim,offsets)-self.placement(prim,-offsets))/(2*step)
        coarse=derivative(1.);fine=derivative(.5);matrix=(4*fine-coarse)/3
        return {'origin':self.placement(prim,[[0,0,0]])[0].tolist(),'jacobian':matrix.tolist(),
            'chart':'output CRS ordered Cartesian components','units':'declared output component units per stage unit',
            'method':'Richardson-refined central differences at 1 and 0.5 stage units',
            'convergence_residual':float(np.max(abs(fine-coarse))),
            'extent_certificate':False,'inverse_available':bool(np.linalg.det(matrix)!=0)}

    def snapshot(self):
        return {layer.identifier:layer.ExportToString() for layer in self.stage.GetUsedLayers()}

    def approximation_bound(self,prim,extent):
        """A structural exact-affine case; never promote a finite probe to a bound.

        This certifies mathematical approximation error, separately from engine
        accuracy, floating arithmetic and downstream vertex quantization.
        """
        anchor,source=definition(prim)
        if source.is_geographic or not source.equals(self.output,ignore_axis_order=False):
            raise ContractError('No continuous approximation certificate for this nonlinear operation')
        A=UsdGeom.Xformable(anchor).GetLocalTransformation(self.time)
        if A!=Gf.Matrix4d(1):
            parent=anchor.GetParent()
            while parent and not parent.IsPseudoRoot() and not bound(parent):parent=parent.GetParent()
            work=definition(parent)[1] if parent and not parent.IsPseudoRoot() else source
            if not work.equals(source,ignore_axis_order=False):raise ContractError('No continuous certificate for an intermediate CRS operation')
        if np.asarray(extent).shape!=(2,3) or not np.isfinite(extent).all():raise ContractError('Invalid requested extent')
        return {'extent':extent,'time':self.time.GetValue(),'affine_approximation_error_metres':0.,'basis':'Analytically affine point map with identical Cartesian source/working/output CRS','numeric_quantization_included':False,'operation_accuracy_included':False}

def dependency(stage):
    p=stage.GetDefaultPrim()
    if not p: raise ContractError('Publishable scene has no defaultPrim dependency carrier')
    schemas=p.GetMetadata('apiSchemas')
    usage=p.GetCustomDataByKey('profilesInfo:capabilityUsages:geospatial:crsResolution')
    # The capability includes a colon: get the dictionary without parsing that token as nested keys.
    d=p.GetCustomData().get('profilesInfo',{}).get('capabilityUsages',{})
    if not schemas or 'ClaimsAPI' not in schemas.GetAppliedItems() or d.get('geospatial:crsResolution')!='hard':
        raise ContractError('Missing/weak whole-scene Profiles dependency claim')
    return {'carrier':str(p.GetPath()),'capability':'geospatial:crsResolution','usage':'hard','traversal_required':False}
