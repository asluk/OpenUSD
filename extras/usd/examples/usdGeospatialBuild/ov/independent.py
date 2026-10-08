"""Independent OV implementation of the frozen text; imports no query-runtime code."""
import math,re
import numpy as np
from pyproj import CRS,Transformer
from pxr import Gf,Usd,UsdGeom

class OVResolver:
    def __init__(self,stage,output):
        self.stage=stage
        self.output=CRS.from_wkt(output) if output is not None else self.scope(stage.GetDefaultPrim())[1]
    def scope(self,p,allow_unbound=False):
        while p and not p.IsPseudoRoot():
            r=p.GetRelationship('crs:binding')
            if r and r.HasAuthoredTargets():
                a=r.GetTargets()
                if len(a)!=1:raise ValueError('Binding target count')
                w=self.stage.GetPrimAtPath(a[0]).GetAttribute('crs:wkt').Get()
                if not w or 'COORDINATEMETADATA' in w:raise ValueError('Missing CRS or deferred epoch wrapper')
                c=CRS.from_wkt(w)
                if len(c.axis_info)!=3:raise ValueError('Incomplete CRS')
                return p,c
            p=p.GetParent()
        if allow_unbound:return None,None
        raise ValueError('No binding/default output CRS')
    @staticmethod
    def factors(c):
        a=list(c.axis_info)
        if c.is_geocentric:return np.array([x.unit_conversion_factor for x in a])
        return np.array([next(x.unit_conversion_factor for x in a if x.direction.lower()=='east'),next(x.unit_conversion_factor for x in a if x.direction.lower()=='north'),a[-1].unit_conversion_factor])
    @staticmethod
    def tx(src,dst,xyz):
        t=Transformer.from_crs(src,dst,always_xy=True,only_best=True,allow_ballpark=False)
        if re.search(r'\b(t_epoch|dx|dy|dz|drx|dry|drz|ds)=',t.definition):raise ValueError('Epoch dependent operation deferred')
        p=np.asarray(xyz,dtype=float).reshape(-1,3)
        if CRS.from_user_input(src).is_geographic and np.any(abs(p[:,1]*OVResolver.factors(CRS.from_user_input(src))[1])>math.pi/2+1e-12):raise ValueError('Latitude outside coordinate domain')
        q=np.array(t.transform(p[:,0],p[:,1],p[:,2],errcheck=True)).T
        try:chosen=t.get_last_used_operation()
        except Exception:chosen=t
        if re.search(r'\b(t_epoch|dx|dy|dz|drx|dry|drz|ds)=',chosen.definition):raise ValueError('Epoch dependent operation deferred')
        if not np.isfinite(q).all():raise ValueError('Whole coordinate batch failed')
        return q,chosen
    @staticmethod
    def cart(c,p):
        f=OVResolver.factors(c);l,b=np.asarray(p)[:2]*f[:2];h=p[2]*f[2];a=c.ellipsoid.semi_major_metre;bb=c.ellipsoid.semi_minor_metre;e=1-(bb/a)**2;n=a/(1-e*math.sin(b)**2)**.5
        v=np.array([(n+h)*math.cos(b)*math.cos(l),(n+h)*math.cos(b)*math.sin(l),(n*(1-e)+h)*math.sin(b)])
        # columns are east, north, up. This implementation is independent of the query runtime.
        enu=np.array([[-math.sin(l),-math.sin(b)*math.cos(l),math.cos(b)*math.cos(l)],[math.cos(l),-math.sin(b)*math.sin(l),math.cos(b)*math.sin(l)],[0,math.cos(b),math.sin(b)]])
        return v,enu
    @staticmethod
    def uncart(c,xyz):
        a=c.ellipsoid.semi_major_metre;b=c.ellipsoid.semi_minor_metre;e=1-(b/a)**2;x=np.asarray(xyz);lo=np.arctan2(x[:,1],x[:,0]);r=np.hypot(x[:,0],x[:,1]);lat=np.arctan2(x[:,2],r*(1-e))
        for i in range(12):
            n=a/np.sqrt(1-e*np.sin(lat)**2);lat=np.arctan2(x[:,2]+e*n*np.sin(lat),r)
        n=a/np.sqrt(1-e*np.sin(lat)**2);h=np.where(abs(np.cos(lat))>1e-8,r/np.cos(lat)-n,abs(x[:,2])-b)
        return np.column_stack([lo,lat,h])/OVResolver.factors(c)
    def full(self,root,local,time):
        _,source=self.scope(root);p=root.GetAttribute('crs:position').Get(time)
        if p is None:raise ValueError('Missing source placement')
        a=root.GetAttribute('crs:scale');scale=np.array(a.Get(time) if a else [1,1,1])
        a=root.GetAttribute('crs:orientation');q=a.Get(time) if a else Gf.Quatd(1)
        if abs(q.GetLength()-1)>1e-9 or not np.isfinite(scale).all() or np.any(scale==0):raise ValueError('Invalid source orientation/scale')
        axes=np.eye(3) if UsdGeom.GetStageUpAxis(self.stage)=='Z' else np.array([[1,0,0],[0,0,-1],[0,1,0]])
        u=UsdGeom.GetStageMetersPerUnit(self.stage);v=np.asarray(local).reshape(-1,3)*scale@axes.T@np.array(Gf.Matrix3d(q))*u
        if source.is_geographic:
            o,b=self.cart(source,p);points=self.uncart(source,o+v@b.T)
        else:points=np.array(p)+v/self.factors(source)
        points,tr=self.tx(source,self.output,points);post=np.array(UsdGeom.Xformable(root).GetLocalTransformation(time))
        if not np.array_equal(post,np.eye(4)):
            _,work=self.scope(root.GetParent(),allow_unbound=True)
            if work is None:work=source
            w,_=self.tx(self.output,work,points)
            if work.is_geographic:
                origin,_=self.tx(source,work,[p]);o,b=self.cart(work,origin[0]);xyz=np.array([self.cart(work,k)[0] for k in w]);v=(xyz-o)@b@axes/u;v=(np.column_stack([v,np.ones(len(v))])@post[:,:3])@axes.T*u;w=self.uncart(work,o+v@b.T)
            else:
                v=w*self.factors(work)@axes/u;w=(np.column_stack([v,np.ones(len(v))])@post[:,:3])@axes.T*u/self.factors(work)
            points,_=self.tx(work,self.output,w)
        return points,tr
    def frame(self,root,time):
        u=UsdGeom.GetStageMetersPerUnit(self.stage);o,t=self.full(root,[[0,0,0]],time);m=np.eye(4);m[3,:3]=o[0]
        for i in range(3):
            v=np.zeros((2,3));v[0,i]=1/u;v[1,i]=-1/u;p,_=self.full(root,v,time);m[i,:3]=(p[0]-p[1])/(2/u)
        return m,t
    def records(self,time):
        results={'geometry':{},'measurements':{},'frames':{},'point_instances':{},'operations':{},'bounds':{},'relative_frames':{}}
        for p in self.stage.Traverse(Usd.TraverseInstanceProxies()):
            rel=p.GetRelationship('crs:coordinateProperties')
            if rel:
                _,source=self.scope(p)
                for a in rel.GetTargets():
                    q,t=self.tx(source,self.output,self.stage.GetAttributeAtPath(a).Get(time));results['measurements'][str(a)]=q.tolist();results['operations'][str(a)]={'description':t.description,'accuracy':t.accuracy}
            if p.GetAttribute('crs:position') and p.GetAttribute('crs:position').HasAuthoredValue():
                m,t=self.frame(p,time);results['frames'][str(p.GetPath())]=m.tolist();results['operations'][str(p.GetPath())]={'description':t.description,'accuracy':t.accuracy}
            if p.IsA(UsdGeom.PointInstancer):
                root,_=self.scope(p);frame,_=self.frame(root,time);local=Gf.Matrix4d(1);q=p
                while q!=root:
                    x=UsdGeom.Xformable(q)
                    if x:local=local*x.GetLocalTransformation(time)
                    q=q.GetParent()
                m=UsdGeom.PointInstancer(p).ComputeInstanceTransformsAtTime(time,time)
                results['point_instances'][str(p.GetPath())]=[list((k*local*Gf.Matrix4d(frame)).Transform(Gf.Vec3d(0))) for k in m]
            a=p.GetAttribute('points')
            if a and a.Get(time) is not None:
                root,_=self.scope(p,allow_unbound=True)
                if root is None:continue
                if not root.GetAttribute('crs:position').HasAuthoredValue():continue
                local=Gf.Matrix4d(1);q=p
                while q!=root:
                    x=UsdGeom.Xformable(q)
                    if x:
                        local=local*x.GetLocalTransformation(time)
                        if x.GetResetXformStack():break
                    q=q.GetParent()
                m,_=self.frame(root,time);v=np.array(a.Get(time));xyz=np.column_stack([v,np.ones(len(v))])@np.array(local)@m;results['geometry'][str(p.GetPath())]=xyz[:,:3].tolist()
                if not self.output.is_geographic and UsdGeom.Boundable(p):
                    extent=UsdGeom.Boundable.ComputeExtentFromPlugins(UsdGeom.Boundable(p),time)
                    b=Gf.BBox3d(Gf.Range3d(Gf.Vec3d(extent[0]),Gf.Vec3d(extent[1])),local*Gf.Matrix4d(m)).ComputeAlignedRange()
                    results['bounds'][str(p.GetPath())]=[list(b.GetMin()),list(b.GetMax())]
        keys=sorted(results['frames'])
        for i,key in enumerate(keys):
            for other in keys[i+1:]:results['relative_frames'][key+' relative to '+other]=np.array(Gf.Matrix4d(*np.array(results['frames'][key]).ravel().tolist())*Gf.Matrix4d(*np.array(results['frames'][other]).ravel().tolist()).GetInverse()).tolist()
        return results
