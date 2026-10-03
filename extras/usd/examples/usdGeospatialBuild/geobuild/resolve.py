"""Fresh OpenUSD query runtime. Independent native and OV code do not import this."""
from dataclasses import dataclass
import math, re
import numpy as np
from pyproj import CRS, Transformer, enums
from pxr import Gf, Usd, UsdGeom
from .model import GeoError, binding, crs

def axis_factors(c):
    a=list(c.axis_info)
    if c.is_geographic:
        return np.array([next(x.unit_conversion_factor for x in a if x.direction.lower()=='east'),
                         next(x.unit_conversion_factor for x in a if x.direction.lower()=='north'),a[-1].unit_conversion_factor])
    if c.is_geocentric:return np.array([x.unit_conversion_factor for x in a])
    return np.array([next(x.unit_conversion_factor for x in a if x.direction.lower()=='east'),
                     next(x.unit_conversion_factor for x in a if x.direction.lower()=='north'),a[-1].unit_conversion_factor])

def convert(c1,c2,points,inverse=False,transformer=None):
    pts=np.asarray(points,dtype=float).reshape(-1,3)
    if not np.isfinite(pts).all():raise GeoError('Nonfinite coordinate batch')
    source=CRS.from_user_input(c2 if inverse else c1)
    if source.is_geographic and np.any(np.abs(pts[:,1]*axis_factors(source)[1])>math.pi/2+1e-12):raise GeoError('Latitude outside the coordinate domain')
    try:
        tr=transformer or Transformer.from_crs(c1,c2,always_xy=True,allow_ballpark=False,only_best=True)
        # No epoch is passed. A time-dependent operation cannot be quietly used at a default epoch.
        if re.search(r'\b(t_epoch|dx|dy|dz|drx|dry|drz|ds)=',tr.definition):raise GeoError('Epoch-dependent coordinate operation is deferred')
        out=np.column_stack(tr.transform(*pts.T,errcheck=True,direction=enums.TransformDirection.INVERSE if inverse else enums.TransformDirection.FORWARD))
        chosen=operation_details(tr)
        if re.search(r'\b(t_epoch|dx|dy|dz|drx|dry|drz|ds)=',chosen.definition):raise GeoError('Epoch-dependent coordinate operation is deferred')
        if not np.isfinite(out).all():raise GeoError('Coordinate operation returned a partial/nonfinite batch')
        return out,tr
    except GeoError:raise
    except Exception as e:raise GeoError(f'Coordinate operation failed: {e}') from e

def operation_details(transformer):
    try:return transformer.get_last_used_operation()
    except Exception:return transformer

def local_to_source(c,anchor,local_metres):
    a=np.asarray(anchor,dtype=float); x=np.asarray(local_metres,dtype=float).reshape(-1,3)
    if not c.is_geographic:return a+x/axis_factors(c)
    fac=axis_factors(c); lon,lat=a[:2]*fac[:2]; h=a[2]*fac[2]
    ell=c.ellipsoid; aa=ell.semi_major_metre; bb=ell.semi_minor_metre; e2=1-bb*bb/(aa*aa)
    sl,cl,sp,cp=np.sin(lon),np.cos(lon),np.sin(lat),np.cos(lat)
    n=aa/np.sqrt(1-e2*sp*sp)
    base=np.array([(n+h)*cp*cl,(n+h)*cp*sl,(n*(1-e2)+h)*sp])
    basis=np.array([[-sl,-sp*cl,cp*cl],[cl,-sp*sl,cp*sl],[0,cp,sp]])
    xyz=base+x@basis.T
    # Independent ellipsoidal Cartesian inverse, no geodetic transformer here.
    lo=np.arctan2(xyz[:,1],xyz[:,0]); r=np.hypot(xyz[:,0],xyz[:,1]); la=np.arctan2(xyz[:,2],r*(1-e2))
    for _ in range(12):
        nv=aa/np.sqrt(1-e2*np.sin(la)**2)
        la=np.arctan2(xyz[:,2]+e2*nv*np.sin(la),r)
    nv=aa/np.sqrt(1-e2*np.sin(la)**2)
    hh=np.where(abs(np.cos(la))>1e-8,r/np.cos(la)-nv,abs(xyz[:,2])-bb)
    return np.column_stack([lo/fac[0],la/fac[1],hh/fac[2]])

def homogeneous(points,matrix):
    x=np.asarray(points,dtype=float).reshape(-1,3)
    return np.column_stack([x,np.ones(len(x))])@np.array(matrix)[:,:3]

def native_to_stage_basis(stage):
    return np.eye(3) if UsdGeom.GetStageUpAxis(stage)=='Z' else np.array([[1,0,0],[0,0,-1],[0,1,0]])

@dataclass
class Result:
    points:np.ndarray
    operation:str
    accuracy:float
    output_wkt:str
    domain:str='target CRS native units, fixed tuple order'

class Resolver:
    def __init__(self,stage):self.stage=stage
    def output_definition(self,output):
        if output is not None:return crs(output)
        p=self.stage.GetDefaultPrim()
        if not p:raise GeoError('No composed defaultPrim supplies the default output CRS')
        return binding(p)[1]
    def measures(self,prim,output=None,time=Usd.TimeCode.Default()):
        _,source=binding(prim); out=self.output_definition(output)
        rel=prim.GetRelationship('crs:coordinateProperties')
        if not rel or not rel.GetTargets():raise GeoError('No authored measurement-coordinate association')
        results={}
        for path in rel.GetTargets():
            a=self.stage.GetAttributeAtPath(path)
            pts,tr=convert(source,out,a.Get(time))
            actual=operation_details(tr);results[str(path)]=Result(pts,actual.description,actual.accuracy,out.to_wkt())
        return results
    def model(self,prim):
        root,source=binding(prim)
        if not root.GetAttribute('crs:position'):raise GeoError('No authored model placement')
        return root,source
    def full_points(self,prim,local_points,output=None,time=Usd.TimeCode.Default(),post_context=True):
        root,source=self.model(prim); out=self.output_definition(output)
        anchor=root.GetAttribute('crs:position').Get(time)
        if anchor is None:raise GeoError('Missing placement at requested source time')
        q=root.GetAttribute('crs:orientation').Get(time) if root.GetAttribute('crs:orientation') else Gf.Quatd(1)
        scale=root.GetAttribute('crs:scale').Get(time) if root.GetAttribute('crs:scale') else Gf.Vec3d(1)
        if q is None or abs(q.GetLength()-1)>1e-9 or not np.isfinite(scale).all() or np.any(np.array(scale)==0):raise GeoError('Invalid placement orientation or scale')
        rot=np.array(Gf.Matrix3d(q))
        basis=native_to_stage_basis(self.stage)
        source_pts=local_to_source(source,anchor,(np.asarray(local_points)*scale)@basis.T@rot*UsdGeom.GetStageMetersPerUnit(self.stage))
        pts,tr=convert(source,out,source_pts)
        post=UsdGeom.Xformable(root).GetLocalTransformation(time)
        if not np.allclose(post,np.eye(4),atol=0,rtol=0):
            parent=root.GetParent()
            _,working=binding(parent,allow_unbound=True)
            if working is None:working=source
            if not post_context:working=out
            w,trw=convert(out,working,pts)
            unit=UsdGeom.GetStageMetersPerUnit(self.stage)
            if working.is_geographic:
                origin,_=convert(source,working,[anchor])
                # geographic working frame only supports local Cartesian post semantics.
                # derive ENU coordinates through ellipsoid Cartesian differences.
                ecef=CRS.from_dict({'proj':'geocent','a':working.ellipsoid.semi_major_metre,'b':working.ellipsoid.semi_minor_metre,'units':'m'})
                xyz,_=convert(working,ecef,w); o,_=convert(working,ecef,origin)
                lon,lat=origin[0,:2]*axis_factors(working)[:2]
                sl,cl,sp,cp=np.sin(lon),np.cos(lon),np.sin(lat),np.cos(lat)
                basis=np.array([[-sl,-sp*cl,cp*cl],[cl,-sp*sl,cp*sl],[0,cp,sp]])
                chart_basis=native_to_stage_basis(self.stage)
                adjusted=homogeneous((xyz-o)@basis@chart_basis/unit,post)@chart_basis.T*unit
                w=local_to_source(working,origin[0],adjusted)
            else:w=homogeneous(w*axis_factors(working)@native_to_stage_basis(self.stage)/unit,post)@native_to_stage_basis(self.stage).T*unit/axis_factors(working)
            pts,posttr=convert(working,out,w)
            operation=operation_details(tr).description+'; post context: '+operation_details(posttr).description
        else:operation=operation_details(tr).description
        return Result(pts,operation,operation_details(tr).accuracy,out.to_wkt())
    def frame(self,prim,output=None,time=Usd.TimeCode.Default(),probe=1.):
        root,_=self.model(prim); unit=UsdGeom.GetStageMetersPerUnit(self.stage)
        sample=np.vstack([np.zeros(3),np.eye(3)*probe/unit,-np.eye(3)*probe/unit])
        r=self.full_points(root,sample,output,time)
        m=np.eye(4);m[3,:3]=r.points[0];m[:3,:3]=(r.points[1:4]-r.points[4:7])/(2*probe/unit)
        return m,r
    def child_matrix(self,prim,root,time):
        m=Gf.Matrix4d(1);p=prim
        while p and p!=root:
            x=UsdGeom.Xformable(p)
            if x:
                m=m*x.GetLocalTransformation(time)
                if x.GetResetXformStack():break
            p=p.GetParent()
        return m
    def geometry(self,prim,output=None,time=Usd.TimeCode.Default(),exact=False):
        root,_=self.model(prim)
        a=prim.GetAttribute('points');v=a.Get(time)
        if v is None:raise GeoError('No geometry points at requested time')
        local=homogeneous(v,self.child_matrix(prim,root,time))
        if exact:return self.full_points(root,local,output,time)
        frame,r=self.frame(root,output,time)
        return Result(homogeneous(local,frame),r.operation,r.accuracy,r.output_wkt)
    def bounds(self,prim,output=None,time=Usd.TimeCode.Default()):
        out=self.output_definition(output)
        if out.is_geographic:raise GeoError('Angular scene bounds are not defined')
        root,_=self.model(prim)
        extent=UsdGeom.Boundable.ComputeExtentFromPlugins(UsdGeom.Boundable(prim),time)
        if extent is None or len(extent)!=2:raise GeoError('No supported ordinary UsdGeom local extent')
        frame,_=self.frame(root,out.to_wkt(),time)
        m=self.child_matrix(prim,root,time)*Gf.Matrix4d(frame)
        b=Gf.BBox3d(Gf.Range3d(Gf.Vec3d(extent[0]),Gf.Vec3d(extent[1])),m).ComputeAlignedRange()
        return np.array([b.GetMin(),b.GetMax()])
    def relative_frame(self,prim,relative_to,output=None,time=Usd.TimeCode.Default()):
        out=self.output_definition(output)
        if out.is_geographic:raise GeoError('Angular relative modelling frames are not defined')
        one,_=self.frame(prim,out.to_wkt(),time);other,_=self.frame(relative_to,out.to_wkt(),time)
        return np.array(Gf.Matrix4d(one)*Gf.Matrix4d(other).GetInverse())
    def scene_points(self,result,output=None):
        out=self.output_definition(output)
        if out.is_geographic:raise GeoError('Geographic angular query results cannot be a length-valued rendering frame')
        p=result.points*axis_factors(out)/UsdGeom.GetStageMetersPerUnit(self.stage)
        return p if UsdGeom.GetStageUpAxis(self.stage)=='Z' else p[:,[0,2,1]]*np.array([1,1,-1])
