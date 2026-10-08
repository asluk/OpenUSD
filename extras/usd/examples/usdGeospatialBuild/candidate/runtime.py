"""Interpret the frozen input-only contract, without authored computed outputs."""
import math
import numpy as np
from pxr import Gf, Usd, UsdGeom
from pyproj import CRS, Transformer
from review.scope import discover, ScopeError
from review.placement_values import read
from review.wkt_profile import normalize, WKTProfileError

class ContractError(ValueError): pass

def bound(prim):
    if not prim:return False
    schemas=prim.GetMetadata('apiSchemas')
    return bool(schemas and 'GeospatialCRSBindingAPI' in schemas.GetAppliedItems())

def definition(prim):
    try:record=discover(prim)
    except ScopeError as e:raise ContractError(str(e)) from e
    wkt=record['wkt']
    try:
        if normalize(wkt)!=wkt:raise ContractError('WKT is not normalized')
    except WKTProfileError as e:raise ContractError('Invalid WKT: '+str(e)) from e
    if 'COORDINATEMETADATA' in wkt:raise ContractError('Coordinate epochs deferred')
    c=CRS.from_wkt(wkt)
    if c.is_bound:raise ContractError('BOUNDCRS unsupported; embedded operation retained')
    roles={a.direction for a in c.axis_info}
    if roles not in [{'east','north'},{'east','north','up'},{'geocentricX','geocentricY','geocentricZ'}]:
        raise ContractError('Unsupported component profile')
    return prim.GetStage().GetPrimAtPath(record['binding_prim']),c

def factors(c):
    roles={a.direction:a.unit_conversion_factor for a in c.axis_info}
    names=['geocentricX','geocentricY','geocentricZ'] if c.is_geocentric else ['east','north','up']
    return np.array([roles[n] for n in names if n in roles])

def basis(stage):
    return np.eye(3) if UsdGeom.GetStageUpAxis(stage)==UsdGeom.Tokens.z else np.array([[1,0,0],[0,0,1],[0,-1,0]],float)

def geodetic(c):
    g=c.geodetic_crs
    if g is None:raise ContractError('No geodetic relationship for model placement')
    if g.is_geocentric:
        d=g.to_json_dict();d['type']='GeographicCRS';d.pop('id',None)
        d['coordinate_system']={'subtype':'ellipsoidal','axis':[
            {'name':'Geodetic longitude','abbreviation':'Lon','direction':'east','unit':'degree'},
            {'name':'Geodetic latitude','abbreviation':'Lat','direction':'north','unit':'degree'},
            {'name':'Ellipsoidal height','abbreviation':'h','direction':'up','unit':'metre'}]}
        return CRS.from_json_dict(d)
    return g.to_3d()

def geocentric(c):
    d=geodetic(c).to_json_dict();d['type']='GeodeticCRS';d.pop('id',None)
    d['coordinate_system']={'subtype':'Cartesian','axis':[
        {'name':'Geocentric X','abbreviation':'X','direction':'geocentricX','unit':'metre'},
        {'name':'Geocentric Y','abbreviation':'Y','direction':'geocentricY','unit':'metre'},
        {'name':'Geocentric Z','abbreviation':'Z','direction':'geocentricZ','unit':'metre'}]}
    return CRS.from_json_dict(d)

def ecef(c,xyz):
    v=np.asarray(xyz,float)*factors(c);lo,la,h=v[...,0],v[...,1],v[...,2]
    a=c.ellipsoid.semi_major_metre;b=c.ellipsoid.semi_minor_metre;e2=1-(b/a)**2
    n=a/np.sqrt(1-e2*np.sin(la)**2)
    return np.stack(((n+h)*np.cos(la)*np.cos(lo),(n+h)*np.cos(la)*np.sin(lo),(n*(1-e2)+h)*np.sin(la)),axis=-1)

def enu(c,origin):
    lo,la=(np.asarray(origin)*factors(c))[:2]
    return np.array([[-np.sin(lo),np.cos(lo),0],[-np.sin(la)*np.cos(lo),-np.sin(la)*np.sin(lo),np.cos(la)],[np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)]])

def from_ecef(c,xyz):
    tr=Transformer.from_pipeline('+proj=pipeline +step +inv +proj=cart '+f'+a={c.ellipsoid.semi_major_metre:.17g} +b={c.ellipsoid.semi_minor_metre:.17g} '+ '+step +proj=unitconvert +xy_in=rad +xy_out=deg')
    x=np.atleast_2d(xyz);v=np.stack(tr.transform(*x.T,errcheck=True),axis=-1)
    v[:,:2]*=math.pi/180
    return v/factors(c)

class Runtime:
    def __init__(self,stage,output,time=0):
        self.stage=stage;self.time=Usd.TimeCode(time);self.unit=UsdGeom.GetStageMetersPerUnit(stage);self.B=basis(stage)
        if not math.isfinite(self.unit) or self.unit<=0:raise ContractError('Invalid stage metric')
        default=stage.GetDefaultPrim()
        self.output=CRS.from_wkt(output) if output else CRS.from_wkt(default.GetAttribute('crs:wkt').Get()) if default and default.GetTypeName()=='CoordinateReferenceSystem' and not bound(default) else definition(default)[1]
        self.scene_crs=geocentric(self.output) if self.output.is_geographic else self.output
        self.operations=[];self.cache={}

    def convert(self,source,target,points):
        x=np.asarray(points,float);was_vector=x.ndim==1;x=np.atleast_2d(x)
        if not np.isfinite(x).all():raise ContractError('Nonfinite coordinate')
        if x.shape[1]!=len(source.axis_info) or len(source.axis_info)!=len(target.axis_info):raise ContractError('No implicit height or dimensional promotion')
        if source.is_geographic and np.any(np.abs(x[:,1]*factors(source)[1])>math.pi/2+1e-14):raise ContractError('Latitude outside domain')
        key=(source.srs,target.srs);tr=self.cache.get(key)
        if tr is None:
            tr=Transformer.from_crs(source,target,always_xy=True,allow_ballpark=False,only_best=True);self.cache[key]=tr
        v=x.copy()
        if source.is_geographic:v[:,:2]*=factors(source)[:2]*180/math.pi
        try:y=np.stack(tr.transform(*v.T,errcheck=True),axis=-1)
        except Exception as e:raise ContractError('Coordinate operation failed; no substitute') from e
        if not np.isfinite(y).all():raise ContractError('Coordinate operation failed; whole batch rejected')
        try:op=tr.get_last_used_operation()
        except Exception:op=tr
        if any(t in op.definition for t in ['t_epoch=','+proj=deformation','+dx=','+dy=','+dz=','+drx=','+dry=','+drz=','+ds=']):raise ContractError('Epoch-dependent transformation deferred')
        self.operations.append({'description':op.description,'definition':op.definition,'accuracy_metres':op.accuracy if op.accuracy>=0 else None})
        if target.is_geographic:y[:,:2]/=factors(target)[:2]*180/math.pi
        return y[0] if was_vector else y

    def stack(self,prim,anchor):
        result=Gf.Matrix4d(1);reset=False;p=prim
        while p and p!=anchor:
            x=UsdGeom.Xformable(p)
            if x:
                result=result*x.GetLocalTransformation(self.time)
                if x.GetResetXformStack():reset=True;break
            p=p.GetParent()
        return result,reset

    def working(self,anchor,source):
        p=anchor.GetParent()
        while p and not p.IsPseudoRoot() and not bound(p):p=p.GetParent()
        return definition(p)[1] if p and not p.IsPseudoRoot() else source

    def rotation(self,anchor):
        try:r=read(anchor,self.time)
        except ScopeError as e:raise ContractError(str(e)) from e
        q=r['orientation'];quat=Gf.Quatd(q['real'],Gf.Vec3d(*q['imaginary']))
        if abs(quat.GetLength()-1)>8*np.finfo(float).eps:raise ContractError('Orientation is not unit length')
        return r,np.array(Gf.Matrix3d(quat))

    def chart(self,work,points,origin):
        if work.is_geographic:
            g=geodetic(work);w=self.convert(work,g,points);o=self.convert(work,g,origin)
            return ((ecef(g,w)-ecef(g,o))@enu(g,o).T)@self.B.T/self.unit
        return ((np.asarray(points)-origin)*factors(work))@self.B.T/self.unit

    def unchart(self,work,points,origin):
        metric=np.asarray(points)*self.unit@self.B
        if work.is_geographic:
            g=geodetic(work);o=self.convert(work,g,origin)
            return self.convert(g,work,from_ecef(g,ecef(g,o)+metric@enu(g,o)))
        return metric/factors(work)+origin

    def apply_adjustment(self,source,work,points,origin,matrix):
        if matrix==Gf.Matrix4d(1):return self.convert(source,self.output,points)
        w=self.convert(source,work,points);o=self.convert(source,work,origin)
        c=self.chart(work,w,o)
        a=np.array([matrix.Transform(Gf.Vec3d(*map(float,p))) for p in c])
        return self.convert(work,self.output,self.unchart(work,a,o))

    def export_context(self,prim):
        p=prim
        while p and not p.IsPseudoRoot():
            if bound(p):return None
            if p.GetTypeName()=='CoordinateReferenceSystem':return p
            p=p.GetParent()
        return None

    def ordinary_export(self,prim,points,context):
        c=CRS.from_wkt(context.GetAttribute('crs:wkt').Get())
        if c.is_geographic:raise ContractError('Baked ordinary geometry needs a Cartesian context')
        D,_=self.stack(prim,context)
        v=np.array([D.Transform(Gf.Vec3d(*map(float,p))) for p in np.atleast_2d(points)])
        native=v@self.B*self.unit/factors(c)
        return self.convert(c,self.output,native)

    def placement(self,prim,points,instance_matrix=None,descendants_in_working=False):
        context=self.export_context(prim)
        if context:return self.ordinary_export(prim,points,context)
        try: read(prim,self.time)
        except ScopeError as e: raise ContractError(str(e)) from e
        anchor,source=definition(prim)
        if anchor.GetTypeName()=='GeospatialDataSource':raise ContractError('Data source is not a model anchor')
        record,R=self.rotation(anchor);work=self.working(anchor,source)
        D,reset=self.stack(prim,anchor);v=np.atleast_2d(points)
        # The alternate branch is a fully labelled counterexample, not scene metadata.
        if not descendants_in_working:v=np.array([D.Transform(Gf.Vec3d(*map(float,p))) for p in v])
        g=geodetic(source);origin=np.array(record['position']);go=self.convert(source,g,origin)
        metric=(v@self.B*self.unit)@R
        s=self.convert(g,source,from_ecef(g,ecef(g,go)+metric@enu(g,go)))
        A=Gf.Matrix4d(1) if reset else UsdGeom.Xformable(anchor).GetLocalTransformation(self.time)
        if descendants_in_working:A=D*A
        if instance_matrix is not None:A=A*instance_matrix
        return self.apply_adjustment(source,work,s,origin,A)

    def measurement(self,prim,points,source):
        if not bound(prim):raise ContractError('Measurement carrier requires direct binding')
        work=self.working(prim,source);A=UsdGeom.Xformable(prim).GetLocalTransformation(self.time)
        if A==Gf.Matrix4d(1):return self.convert(source,self.output,points)
        w=self.convert(source,work,points);dim=len(work.axis_info)
        if dim==2:
            if work.is_geographic:raise ContractError('Geographic adjustment requires height')
            # Inspect the stage matrix in canonical E/N/U before using its planar part.
            M=np.array(A);S=np.eye(4);S[:3,:3]=self.B;C=np.linalg.inv(S)@M@S
            if not np.allclose(C[[0,1,3],2],0,rtol=0,atol=1e-14) or not np.allclose(C[2,[0,1]],0,rtol=0,atol=1e-14):raise ContractError('Nonplanar adjustment requires height')
            c=w*factors(work)/self.unit;a=c@C[:2,:2]+C[3,:2]
            return self.convert(work,self.output,a*self.unit/factors(work))
        origin=np.zeros(3)
        c=self.chart(work,w,origin);a=np.array([A.Transform(Gf.Vec3d(*map(float,p))) for p in c])
        return self.convert(work,self.output,self.unchart(work,a,origin))

    def inverse_placement(self,prim,coordinates):
        anchor,source=definition(prim);record,R=self.rotation(anchor);work=self.working(anchor,source)
        D,reset=self.stack(prim,anchor);A=Gf.Matrix4d(1) if reset else UsdGeom.Xformable(anchor).GetLocalTransformation(self.time)
        if D.GetDeterminant()==0 or A.GetDeterminant()==0:raise ContractError('Singular placement has no inverse')
        origin=np.array(record['position'])
        if A==Gf.Matrix4d(1):s=self.convert(self.output,source,coordinates)
        else:
            w=self.convert(self.output,work,coordinates);o=self.convert(source,work,origin);c=self.chart(work,w,o)
            v=np.array([A.GetInverse().Transform(Gf.Vec3d(*map(float,p))) for p in c])
            s=self.convert(work,source,self.unchart(work,v,o))
        g=geodetic(source);go=self.convert(source,g,origin);q=self.convert(source,g,s)
        metric=(ecef(g,q)-ecef(g,go))@enu(g,go).T@R.T
        local=metric/self.unit@self.B.T
        return np.array([D.GetInverse().Transform(Gf.Vec3d(*map(float,p))) for p in local])

    def geometry(self):
        records={};self.geometry_sources={};self.geometry_normals={}
        instancers=[UsdGeom.PointInstancer(p) for p in self.stage.Traverse() if p.IsA(UsdGeom.PointInstancer)]
        roots={str(path) for inst in instancers for path in inst.GetPrototypesRel().GetTargets()}
        for p in self.stage.Traverse(Usd.TraverseInstanceProxies()):
            if any(str(p.GetPath())==q or str(p.GetPath()).startswith(q+'/') for q in roots):continue
            a=p.GetAttribute('points')
            if not a or not a.HasAuthoredValue():continue
            try:
                if not self.export_context(p):definition(p)
            except ContractError as e:
                if 'No CRS binding' in str(e):continue
                raise
            v=a.Get(self.time)
            if v is None:raise ContractError('Geometry sample unavailable')
            path=str(p.GetPath());records[path]=self.placement(p,np.array(v)).tolist();self.geometry_sources[path]=path
            normals=self.geometry_normal(p,lambda x:self.placement(p,x))
            if normals:self.geometry_normals[path]=normals
        for inst in instancers:
            p=inst.GetPrim();matrices=inst.ComputeInstanceTransformsAtTime(self.time,self.time,UsdGeom.PointInstancer.ExcludeProtoXform,UsdGeom.PointInstancer.IgnoreMask)
            indices=inst.GetProtoIndicesAttr().Get(self.time);roots=inst.GetPrototypesRel().GetTargets();mask=inst.ComputeMaskAtTime(self.time)
            for i,(matrix,index) in enumerate(zip(matrices,indices)):
                if mask and not mask[i]:continue
                proto=self.stage.GetPrimAtPath(roots[index])
                for mesh in Usd.PrimRange(proto):
                    a=mesh.GetAttribute('points')
                    if not a or not a.HasAuthoredValue():continue
                    try: own,_=definition(mesh)
                    except ContractError as e:
                        if 'No CRS binding' not in str(e): raise
                        own=None
                    independent=bool(own and str(own.GetPath()).startswith(str(proto.GetPath())))
                    if independent:
                        values=self.placement(mesh,np.array(a.Get(self.time)),instance_matrix=matrix)
                    else:
                        local,reset=self.stack(mesh,proto)
                        P=UsdGeom.Xformable(proto).GetLocalTransformation(self.time) if not reset and UsdGeom.Xformable(proto) else Gf.Matrix4d(1)
                        C=local*P*matrix
                        v=np.array([C.Transform(Gf.Vec3d(*map(float,x))) for x in a.Get(self.time)])
                        values=self.placement(p,v)
                    # Full relative prim path preserves nested prototype identities.
                    path=str(p.GetPath())+'/_ResolvedInstance'+str(i)+'/'+str(mesh.GetPath().MakeRelativePath(proto.GetPath())).replace('.','Root')
                    records[path]=values.tolist();self.geometry_sources[path]=str(mesh.GetPath())
                    if independent:fn=lambda x:self.placement(mesh,x,instance_matrix=matrix)
                    else:fn=lambda x:self.placement(p,np.array([C.Transform(Gf.Vec3d(*map(float,z))) for z in x]))
                    normals=self.geometry_normal(mesh,fn)
                    if normals:self.geometry_normals[path]=normals
        return records

    def stage_coordinates(self,points,origin):
        x=self.convert(self.output,self.scene_crs,points) if self.output.is_geographic else np.asarray(points)
        o=self.convert(self.output,self.scene_crs,origin) if self.output.is_geographic else np.asarray(origin)
        return ((x-o)*factors(self.scene_crs))@self.B.T/self.unit

    def frame(self,prim):
        if len(self.output.axis_info)!=3:raise ContractError('3D Cartesian scene frame requires height')
        def f(x):
            v=self.placement(prim,x)
            return self.convert(self.output,self.scene_crs,v) if self.output.is_geographic else v
        offsets=np.eye(3);coarse=(f(offsets)-f(-offsets))/2;fine=f(offsets*.5)-f(-offsets*.5);J=(4*fine-coarse)/3
        return {'origin':self.placement(prim,[[0,0,0]])[0].tolist(),'jacobian':J.tolist(),'chart':'associated geocentric Cartesian' if self.output.is_geographic else 'output CRS ordered Cartesian components','units':'scene-chart component units per stage unit','method':'Richardson-refined central differences','convergence_residual':float(np.max(abs(fine-coarse))),'extent_certificate':False,'inverse_available':bool(np.linalg.det(J)!=0)}

    def normal(self,prim,positions,normals,point_map=None):
        positions=np.atleast_2d(positions);normals=np.atleast_2d(normals)
        fn=point_map or (lambda p:self.placement(prim,p));rows=[]
        for axis in np.eye(3):
            v=fn(positions+axis*.5);u=fn(positions-axis*.5)
            if self.output.is_geographic:v=self.convert(self.output,self.scene_crs,v);u=self.convert(self.output,self.scene_crs,u)
            rows.append((v-u)*factors(self.scene_crs)@self.B.T/self.unit)
        J=np.stack(rows,axis=1)
        if np.any(np.abs(np.linalg.det(J))<1e-15):raise ContractError('Singular normal transport')
        q=np.einsum('ni,nij->nj',normals,np.linalg.inv(J).transpose(0,2,1));length=np.linalg.norm(q,axis=1)
        if np.any(length==0):raise ContractError('Zero normal')
        return q/length[:,None]

    def geometry_normal(self,mesh,point_map):
        a=mesh.GetAttribute('normals')
        if not a or not a.HasAuthoredValue():return None
        n=np.array(a.Get(self.time));v=np.array(mesh.GetAttribute('points').Get(self.time));m=UsdGeom.Mesh(mesh)
        interpolation=m.GetNormalsInterpolation() if m else 'vertex'
        if interpolation in ['vertex','varying'] and len(n)==len(v):positions=v
        elif interpolation=='faceVarying':positions=v[np.array(m.GetFaceVertexIndicesAttr().Get(self.time))]
        elif interpolation=='uniform':
            indices=np.array(m.GetFaceVertexIndicesAttr().Get(self.time));counts=m.GetFaceVertexCountsAttr().Get(self.time);positions=[];offset=0
            for count in counts:positions.append(v[indices[offset:offset+count]].mean(axis=0));offset+=count
            positions=np.array(positions)
        elif interpolation=='constant' and len(n)==1:
            positions=v;n=np.broadcast_to(n,v.shape);interpolation='vertex'
        else:raise ContractError('Invalid normal interpolation domain')
        if len(n)!=len(positions):raise ContractError('Normal association mismatch')
        return {'values':self.normal(mesh,positions,n,point_map).tolist(),'interpolation':interpolation}

    def snapshot(self):return {l.identifier:l.ExportToString() for l in self.stage.GetUsedLayers()}

    def approximation_bound(self,prim,extent):
        anchor,source=definition(prim);work=self.working(anchor,source)
        A=UsdGeom.Xformable(anchor).GetLocalTransformation(self.time)
        if not self.output.is_geocentric or not geodetic(source).equals(geodetic(self.output),ignore_axis_order=False):raise ContractError('No continuous approximation certificate for this nonlinear operation')
        if A!=Gf.Matrix4d(1) and not work.is_geocentric:raise ContractError('No continuous certificate for projected/geographic working adjustment')
        if np.asarray(extent).shape!=(2,3) or not np.isfinite(extent).all():raise ContractError('Invalid requested extent')
        return {'extent':extent,'time':self.time.GetValue(),'affine_approximation_error_metres':0.,'basis':'ENU-to-geocentric map and Cartesian adjustments analytically affine at this time','numeric_quantization_included':False,'operation_accuracy_included':False}

def dependency(stage):
    p=stage.GetDefaultPrim()
    if not p:raise ContractError('Publishable scene has no defaultPrim dependency carrier')
    schemas=p.GetMetadata('apiSchemas');d=p.GetCustomData().get('profilesInfo',{}).get('capabilityUsages',{})
    if not schemas or 'ClaimsAPI' not in schemas.GetAppliedItems() or d.get('usd.geospatial.crsResolution')!='hard':raise ContractError('Missing/weak whole-scene Profiles dependency claim')
    return {'carrier':str(p.GetPath()),'capability':'usd.geospatial.crsResolution','usage':'hard','traversal_required':False}
