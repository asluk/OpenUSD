"""Fresh proposal-derived evaluator. Public callable signatures are NOT proposed USD APIs.

Authority anchors refer to sections in the frozen proposal identified by audit/authority.json.
Computed reports stay in memory/JSON evidence, never in the input USD schema.
"""
from __future__ import annotations
import bisect, json, math, os, re, warnings, subprocess, tempfile
from decimal import Decimal
from pathlib import Path
import numpy as np
from pyproj import CRS, Transformer, datadir
from pyproj.crs import CompoundCRS
from pyproj.transformer import TransformerGroup
from pxr import Usd, UsdGeom, Sdf, Gf, Vt, Plug

ROOT = Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT / 'schema'))
CAPABILITY = 'usd.geospatial.crsResolution.v1'
PROFILE = 'usd.geospatial.publication.v1'
if os.getenv('GEOSPATIAL_RESOURCE_DIR'):
    datadir.append_data_dir(os.environ['GEOSPATIAL_RESOURCE_DIR'])

class Failure(RuntimeError): pass
def require(ok, message):
    if not ok: raise Failure(message)
def finite(x):
    a=np.asarray(x,dtype=float)
    require(np.isfinite(a).all(), 'non-finite coordinate or placement')
    return a

# WKT string normalization: preserve quoted bytes, node order and exact decimals.
_tokens = re.compile(r'\s+|"(?:[^"]|"")*"|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[A-Za-z_][A-Za-z_0-9]*|[\[\](),]')
_enum = {v.lower():v for v in ('Cartesian','ellipsoidal','spherical','vertical','parametric','temporal','affine','ordinal','east','west','north','south','up','down','future','past','clockwise','counterClockwise','geocentricX','geocentricY','geocentricZ','columnPositive','columnNegative','rowPositive','rowNegative','displayRight','displayLeft','displayUp','displayDown','forward','aft','port','starboard','towards','awayFrom','unspecified','northNorthEast','northEast','eastNorthEast','eastSouthEast','southEast','southSouthEast','southSouthWest','southWest','westSouthWest','westNorthWest','northWest','northNorthWest')}
def normalize_wkt(text):
    out=[]; end=0
    for m in _tokens.finditer(text):
        require(m.start()==end, 'invalid WKT lexical character')
        end=m.end(); t=m.group()
        if t.isspace(): continue
        if t[0]=='"': out.append(t)
        elif t in '[(': out.append('[')
        elif t in '])': out.append(']')
        elif t==',': out.append(t)
        elif t[0].isdigit() or t[0] in '+-.':
            d=Decimal(t); n=format(d,'f')
            if '.' in n: n=n.rstrip('0').rstrip('.')
            out.append('0' if d==0 else n)
        else: out.append(_enum.get(t.lower(), t.upper()))
    require(end==len(text), 'invalid WKT trailing text')
    return ''.join(out)

def as_crs(value):
    if isinstance(value, CRS): return value
    require(isinstance(value,str) and value.strip(), 'missing WKT')
    require(not value.lstrip().upper().startswith('COORDINATEMETADATA'), 'coordinate epochs are deferred')
    try: c=CRS.from_wkt(value)
    except Exception as e: raise Failure('invalid or unsupported WKT: '+str(e)) from e
    dirs=[a.direction.lower() for a in c.axis_info]
    require(all(d in ('east','north','up','geocentricx','geocentricy','geocentricz') for d in dirs), 'unsupported component directions')
    require(c.geodetic_crs is not None, 'CRS has no computable geodetic relation')
    return c

def geodetic(c):
    c=as_crs(c).geodetic_crs
    j=c.to_json_dict()
    j['type']='GeographicCRS'; j.pop('id',None)
    j['coordinate_system']={'subtype':'ellipsoidal','axis':[
        {'name':'Geodetic latitude','abbreviation':'Lat','direction':'north','unit':'degree'},
        {'name':'Geodetic longitude','abbreviation':'Lon','direction':'east','unit':'degree'},
        {'name':'Ellipsoidal height','abbreviation':'h','direction':'up','unit':'metre'}]}
    return CRS.from_json_dict(j)

def geocentric(c):
    j=geodetic(c).to_json_dict(); j['type']='GeodeticCRS'; j.pop('id',None)
    j['coordinate_system']={'subtype':'Cartesian','axis':[
        {'name':'Geocentric '+a,'abbreviation':a,'direction':'geocentric'+a,'unit':'metre'} for a in 'XYZ']}
    return CRS.from_json_dict(j)

def model_crs(wkt):
    c=as_crs(wkt); assumed=len(c.axis_info)==2
    if assumed:
        unit=c.axis_info[0] if not c.is_geographic else None
        u='metre' if unit is None else unit.unit_name
        factor=1 if unit is None else unit.unit_conversion_factor
        vert=f'VERTCRS["EGM2008 height",VDATUM["EGM2008 geoid"],CS[vertical,1],AXIS["Gravity-related height",up,LENGTHUNIT["{u}",{factor:.17g}]]]'
        c=CompoundCRS('Horizontal with assumed EGM2008 height',[c,CRS.from_wkt(vert)])
        warnings.warn('missing vertical reference: assuming EGM2008 height (EPSG:3855)',stacklevel=2)
    require(len(c.axis_info)==3, 'model placement requires a complete three-component CRS')
    return c, assumed

def height_report(wkt, model=True):
    original=as_crs(wkt); c, assumed=model_crs(wkt) if model else (original,False)
    vertical=next((s for s in c.sub_crs_list if s.is_vertical),None)
    if c.is_geocentric or len(c.axis_info)<3:
        kind='none'; ref=None; unit=None
    elif vertical:
        kind='gravityRelated'; ref='EPSG:3855' if assumed else (':'.join(vertical.to_authority()) if vertical.to_authority() else vertical.name); unit=vertical.axis_info[0].unit_name
    else:
        kind='ellipsoidal'; ref={'ellipsoid':c.ellipsoid.name,'datum':c.datum.name}; unit=c.axis_info[2].unit_name
    return dict(heightModel=kind,heightReference=ref,heightUnit=unit,heightReferenceSource='assumed' if assumed else 'declared')

class Engine:
    def __init__(self): self.cache={}; self.operations=[]
    def convert(self, points, source, output):
        source=as_crs(source); output=as_crs(output); p=finite(points)
        one=p.ndim==1; p=np.atleast_2d(p)
        require(p.shape[1] in (2,3), 'coordinate domain must have two or three components')
        key=(source.srs,output.srs)
        if key not in self.cache:
            with warnings.catch_warnings(record=True):
                group=TransformerGroup(source,output,always_xy=True,allow_ballpark=False)
            require(bool(group.transformers) and group.best_available, 'required coordinate operation or grid unavailable; no lower-accuracy substitute')
            require(not re.search(r'(?:^|\s)(?:proj=(?:deformation|defmodel|velocitygrid)|d(?:x|y|z|rx|ry|rz|s)=)',group.transformers[0].definition),'coordinate-epoch-dependent operation outside initial scope')
            self.cache[key]=group.transformers[0]
        t=self.cache[key]
        try: q=np.array(t.transform(*p.T,errcheck=True)).T
        except Exception as e: raise Failure('coordinate operation failed: '+str(e)) from e
        finite(q)
        try: op=t.get_last_used_operation()
        except Exception: op=t
        self.operations.append(dict(description=op.description,pipeline=op.definition,accuracy_m=None if op.accuracy<0 else op.accuracy,
                                    source=source.name,output=output.name))
        return q[0] if one else q

def stage_basis(stage):
    # Columns here map vectors; equivalent to the proposal's Core row-vector mapping.
    m=UsdGeom.GetStageMetersPerUnit(stage)
    require(math.isfinite(m) and m>0,'invalid stage length unit')
    return (np.eye(3) if UsdGeom.GetStageUpAxis(stage)=='Z' else np.array([[1,0,0],[0,0,-1],[0,1,0]]))*m

def enu_basis(lon,lat):
    l,b=np.radians([lon,lat]); sl,cl,sb,cb=np.sin(l),np.cos(l),np.sin(b),np.cos(b)
    return np.array([[-sl,-sb*cl,cb*cl],[cl,-sb*sl,cb*sl],[0,cb,sb]])

def qmul(a,b):
    return np.r_[a[0]*b[0]-np.dot(a[1:],b[1:]),a[0]*b[1:]+b[0]*a[1:]+np.cross(a[1:],b[1:])]
def pose(hpr):
    h,p,r=np.radians(finite(hpr))/2
    return qmul(qmul(np.array([math.cos(h),0,0,-math.sin(h)]),np.array([math.cos(p),math.sin(p),0,0])),np.array([math.cos(r),0,math.sin(r),0]))
def rotation(q):
    w,x,y,z=q/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def value(attr,tc,typ,required=True):
    require(bool(attr) and attr.GetTypeName()==typ,'missing or wrongly typed '+str(attr.GetName()))
    v=attr.Get(tc)
    require(v is not None or not required,'blocked or unavailable '+str(attr.GetName()))
    return v
def attitude(prim,tc):
    a=prim.GetAttribute('crs:orientation')
    if not a or not a.HasAuthoredValueOpinion(): return np.eye(3)
    require(a.GetTypeName()==Sdf.ValueTypeNames.Double3,'wrongly typed orientation')
    def at(t):
        v=value(a,t,Sdf.ValueTypeNames.Double3); return pose(v)
    samples=a.GetTimeSamples()
    if tc.IsDefault() or not samples: return rotation(at(tc))
    t=tc.GetValue(); i=bisect.bisect_right(samples,t)
    if i==0: return rotation(at(samples[0]))
    if i==len(samples) or samples[i-1]==t or prim.GetStage().GetInterpolationType()==Usd.InterpolationTypeHeld:
        return rotation(at(samples[i-1]))
    qa,qb=at(samples[i-1]),at(samples[i]); dot=float(np.dot(qa,qb))
    require(abs(dot)>1e-12,'ambiguous 180-degree orientation arc; rotational uncertainty 2e-12 radians')
    if dot<0: qb=-qb;dot=-dot
    f=(t-samples[i-1])/(samples[i]-samples[i-1])
    if dot>1-1e-12: q=(1-f)*qa+f*qb
    else:
        theta=math.acos(min(1,dot));q=(math.sin((1-f)*theta)*qa+math.sin(f*theta)*qb)/math.sin(theta)
    return rotation(q)

def direct(p): return 'GeospatialCRSBindingAPI' in p.GetAppliedSchemas()
def controlling(p):
    while p and not p.IsPseudoRoot():
        if direct(p): return p
        p=p.GetParent()
    raise Failure('content outside a CRS binding')
def uniform(prim,name,typ):
    a=prim.GetAttribute(name)
    require(a and a.GetVariability()==Sdf.VariabilityUniform and a.GetTypeName()==typ, 'invalid uniform field '+name)
    require(not a.GetTimeSamples(),'active samples on uniform '+name)
    return value(a,Usd.TimeCode.Default(),typ)
def definition(p,model=True):
    w=str(uniform(p,'crs:wkt',Sdf.ValueTypeNames.Token))
    if normalize_wkt(w)!=w: warnings.warn('non-normal WKT spelling',stacklevel=2)
    return model_crs(w)[0] if model else as_crs(w)
def check_roles(p):
    for ancestor in [p]:
        authored=[n for n in ('crs:position','crs:orientation') if ancestor.GetAttribute(n) and ancestor.GetAttribute(n).HasAuthoredValueOpinion()]
        require(not authored or (direct(ancestor) and ancestor.GetTypeName()!='GeospatialDataSource'),'placement fields in an invalid role on '+str(p.GetPath()))
def apply_matrix(points,m):
    p=np.atleast_2d(finite(points)); h=np.c_[p,np.ones(len(p))]@np.asarray(m)
    require(np.all(np.abs(h[:,3])>1e-15),'unavailable projective point')
    return finite(h[:,:3]/h[:,3,None])

class ModelMap:
    def __init__(self,prim,tc,engine,working=None):
        self.prim=prim;self.stage=prim.GetStage();self.tc=tc;self.e=engine
        require(bool(UsdGeom.Xformable(prim)),'direct model binding requires Xformable content')
        self.source=definition(prim); self.geo=geodetic(self.source);self.ecef=geocentric(self.source)
        self.position=finite(value(prim.GetAttribute('crs:position'),tc,Sdf.ValueTypeNames.Double3))
        if self.source.is_geocentric: require(not(self.position[0]==0 and self.position[1]==0),'geocentric pole does not determine an attitude meridian')
        llh=self.e.convert(self.position,self.source,self.geo)
        self.origin=self.e.convert(llh,self.geo,self.ecef)
        self.basis=enu_basis(*llh[:2]);self.att=attitude(prim,tc);self.axes=stage_basis(self.stage)
        self.A=np.asarray(UsdGeom.Xformable(prim).GetLocalTransformation(tc))
        if working is None:
            parent=prim.GetParent()
            while parent and not parent.IsPseudoRoot() and not direct(parent): parent=parent.GetParent()
            working=definition(parent) if parent and direct(parent) else self.source
        self.working=as_crs(working)
        self.worigin=None
    def prepare_chart(self):
        if self.worigin is not None:return
        self.worigin=self.e.convert(self.origin,self.ecef,self.working)
        self.wgeo=geodetic(self.working);self.wecef=geocentric(self.working)
        if self.working.is_geographic:
            wllh=self.e.convert(self.worigin,self.working,self.wgeo);self.wbasis=enu_basis(*wllh[:2]);self.weorigin=self.e.convert(self.worigin,self.working,self.wecef)
        else: self.units=np.array([a.unit_conversion_factor for a in self.working.axis_info])
    def chart(self,p):
        self.prepare_chart()
        if self.working.is_geographic: return (self.e.convert(p,self.working,self.wecef)-self.weorigin)@self.wbasis@np.linalg.inv(self.axes).T
        return (p-self.worigin)*self.units@np.linalg.inv(self.axes).T
    def unchart(self,p):
        self.prepare_chart()
        if self.working.is_geographic: return self.e.convert(self.weorigin+(p@self.axes.T)@self.wbasis.T,self.wecef,self.working)
        return self.worigin+(p@self.axes.T)/self.units
    def forward(self,points,output,D=None,reset=False):
        p=np.atleast_2d(finite(points));p=apply_matrix(p,np.eye(4) if D is None else D)
        ecef=self.origin+(p@self.axes.T@self.att.T)@self.basis.T
        if reset or np.array_equal(self.A,np.eye(4)): return self.e.convert(ecef,self.ecef,output)
        w=self.e.convert(ecef,self.ecef,self.working)
        return self.e.convert(self.unchart(apply_matrix(self.chart(w),self.A)),self.working,output)
    def inverse(self,points,input_crs,D=None,reset=False):
        w=self.e.convert(points,input_crs,self.working)
        if not reset:
            require(abs(np.linalg.det(self.A))>1e-15,'singular required inverse')
            w=self.unchart(apply_matrix(self.chart(w),np.linalg.inv(self.A)))
        e=self.e.convert(w,self.working,self.ecef)
        local=(e-self.origin)@self.basis@self.att@np.linalg.inv(self.axes).T
        if D is not None:
            require(abs(np.linalg.det(np.asarray(D)))>1e-15,'singular instancer inverse')
            local=apply_matrix(local,np.linalg.inv(np.asarray(D)))
        return local

class Reader:
    def __init__(self,stage): self.stage=stage;self.engine=Engine()
    def output(self,requested):
        if requested is not None: return as_crs(requested)
        p=self.stage.GetDefaultPrim();require(bool(p),'no output context')
        require(direct(p) or p.GetTypeName()=='CoordinateReferenceSystem','no default output CRS')
        return definition(p,model=False)
    def points(self,prim,points,output=None,time=None):
        tc=Usd.TimeCode.Default() if time is None else Usd.TimeCode(time)
        output=self.output(output); p=prim.GetPrim() if hasattr(prim,'GetPrim') else prim if hasattr(prim,'GetPath') else self.stage.GetPrimAtPath(prim)
        require(bool(p),'missing prim');check_roles(p)
        # An ordinary explicit bake has a typed Cartesian context, not an implicit reset.
        q=p; context=None
        while q and not q.IsPseudoRoot():
            if direct(q): break
            if q.GetTypeName()=='CoordinateReferenceSystem': context=q;break
            q=q.GetParent()
        if context:
            c=definition(context,False);require(not c.is_geographic,'ordinary bake requires Cartesian CRS')
            m=UsdGeom.XformCache(tc).GetLocalToWorldTransform(p)
            world=apply_matrix(points,m)@stage_basis(self.stage).T
            units=np.array([a.unit_conversion_factor for a in c.axis_info])
            return self.engine.convert(world/units,c,output)
        anchor=controlling(p);check_roles(anchor)
        require(anchor.GetTypeName()!='GeospatialDataSource','model query on measurement carrier')
        # Detect invalid input fields anywhere between the geometry and its anchor.
        q=p
        while q!=anchor: check_roles(q);q=q.GetParent()
        D,reset=UsdGeom.XformCache(tc).ComputeRelativeTransform(p,anchor)
        return ModelMap(anchor,tc,self.engine).forward(points,output,D,reset)
    def scene_points(self,prim,points,output=None,time=None,origin=(0,0,0)):
        output=self.output(output); chart=geocentric(output) if output.is_geographic else output
        p=self.points(prim,points,chart,time)
        units=np.array([a.unit_conversion_factor for a in chart.axis_info])
        return (p-finite(origin))*units@np.linalg.inv(stage_basis(self.stage)).T, chart
    def derivative(self,prim,point,output=None,time=None):
        # Numerical differentiation is an implementation method, not a source field.
        p=finite(point);eps=0.01
        return np.array([(self.scene_points(prim,[p+np.eye(3)[i]*eps],output,time)[0][0]-self.scene_points(prim,[p-np.eye(3)[i]*eps],output,time)[0][0])/(2*eps) for i in range(3)]).T
    def relative_positions(self,from_prim,to_prim,output=None,time=None):
        q=self.output(output);a=self.points(from_prim,[(0,0,0)],q,time)[0];b=self.points(to_prim,[(0,0,0)],q,time)[0]
        return {'from':a,'to':b,'difference':a-b,'coordinateCRS':q.to_wkt(),'meaning':'coordinate component difference; angular components are not a metric displacement'}
    def bounds(self,prim,points,output=None,time=None,continuous=False):
        require(not continuous,'continuous-domain bound not certified by this implementation; finite probes are insufficient')
        p,chart=self.scene_points(prim,points,output,time)
        return {'min':p.min(axis=0),'max':p.max(axis=0),'chart':chart.to_wkt(),'coverage':'supplied finite points and their straight polygonal hull only'}
    def vectors(self,prim,points,vectors,role,output=None,time=None):
        p=finite(points);v=finite(vectors);eps=0.01
        J=np.stack([(self.scene_points(prim,p+np.eye(3)[i]*eps,output,time)[0]-self.scene_points(prim,p-np.eye(3)[i]*eps,output,time)[0])/(2*eps) for i in range(3)],axis=2)
        if role=='normal':
            require(np.all(np.abs(np.linalg.det(J))>1e-15),'singular normal transport')
            x=np.linalg.solve(J.transpose(0,2,1),v[...,None])[...,0];x/=np.linalg.norm(x,axis=1)[:,None]
        elif role=='vector': x=np.einsum('nij,nj->ni',J,v)
        else: raise Failure('unrecognized semantic vector role')
        return finite(x)
    def instance_points(self,instancer,index,prototype_prim,points,output=None,time=None):
        tc=Usd.TimeCode.Default() if time is None else Usd.TimeCode(time);q=self.output(output)
        pi=UsdGeom.PointInstancer(instancer)
        ids=pi.GetIdsAttr().Get(tc); mask=pi.ComputeMaskAtTime(tc)
        require(not mask or mask[index], 'masked point instance')
        proto=prototype_prim; bound=None
        targets=pi.GetPrototypesRel().GetTargets();which=pi.GetProtoIndicesAttr().Get(tc)[index];root=self.stage.GetPrimAtPath(targets[which])
        p=proto
        while p and p.GetPath().HasPrefix(root.GetPath()):
            if direct(p): bound=p;break
            if p==root: break
            p=p.GetParent()
        matrices=pi.ComputeInstanceTransformsAtTime(tc,tc,UsdGeom.PointInstancer.ExcludeProtoXform,UsdGeom.PointInstancer.IgnoreMask)
        I=np.asarray(matrices[index]);anchor=controlling(instancer)
        H=ModelMap(anchor,tc,self.engine)
        instD,reset=UsdGeom.XformCache(tc).ComputeRelativeTransform(instancer,anchor)
        if bound:
            # Occurrence context walks inside prototype, then instancer ancestry.
            parent=bound.GetParent()
            while parent and parent.GetPath().HasPrefix(root.GetPath()) and not direct(parent): parent=parent.GetParent()
            W=definition(parent) if parent and parent.GetPath().HasPrefix(root.GetPath()) and direct(parent) else definition(anchor)
            B=ModelMap(bound,tc,self.engine,W)
            D,br=UsdGeom.XformCache(tc).ComputeRelativeTransform(proto,bound)
            fixed=geocentric(H.source); b=B.forward(points,fixed,D,br)
            if np.array_equal(I,np.eye(4)): return self.engine.convert(b,fixed,q)
            local=H.inverse(b,fixed,instD,reset)
            return H.forward(apply_matrix(local,I),q,instD,reset)
        D,_=UsdGeom.XformCache(tc).ComputeRelativeTransform(proto,root)
        P=UsdGeom.Xformable(root).GetLocalTransformation(tc)
        return H.forward(apply_matrix(points,np.asarray(D)@np.asarray(P)@I),q,instD,reset)

def profile_summary(stage):
    p=stage.GetDefaultPrim(); d=p.GetCustomDataByKey('profilesInfo') or {}
    usages=d.get('capabilityUsages'); compat=d.get('profileCompatibility',{})
    ap=p.GetMetadata('apiSchemas')
    complete=ap is not None and 'ClaimsAPI' in ap.GetAppliedItems() and isinstance(usages,dict) and PROFILE in compat and not compat[PROFILE]
    hard=isinstance(usages,dict) and usages.get(CAPABILITY)=='hard'
    return {'coverage':'complete-positive' if complete and hard else 'complete-empty' if complete else 'unknown','requiresResolution': True if hard else False if complete else None}
def publish_claim(stage,requires=True,complete=True):
    # The native existing ClaimsAPI authors the exact VtToken/VtTokenArray types.
    # Python 26.5 lacks these bindings: a lookalike string dictionary is NOT proof.
    stage.GetRootLayer().Save()
    request={'publishStage':stage.GetRootLayer().realPath,'requires':requires,'complete':complete}
    env=os.environ.copy();env['PATH']='C:/git/usd-geospatial-fresh/inst/bin;C:/git/usd-geospatial-fresh/inst/lib;C:/Users/aluk/AppData/Local/Programs/Python/Python310;C:/Users/aluk/Documents/Codex/2026-09-21/have/work/geospatial-proj-tiff/bin;'+env['PATH']
    with tempfile.TemporaryDirectory() as td:
        src=Path(td)/'request.json';dest=Path(td)/'result.json';src.write_text(json.dumps(request))
        cmd=[str(ROOT/'native/build/resolve.exe'),str(src),str(dest),str(ROOT/'schema')]
        completed=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60)
        require(completed.returncode==0,'native Profiles publication failed ('+str(completed.returncode)+'): '+completed.stderr)
    stage.GetRootLayer().Reload(True)
def validate_publication(stage):
    summary=profile_summary(stage)
    if summary['requiresResolution'] is True:return summary
    # Inspect all retained variants in private sessions at publication time.
    # Consumer summary reads never invoke this traversal or load any payload.
    session=Sdf.Layer.CreateAnonymous();session.TransferContent(stage.GetSessionLayer())
    pending=[session];seen=set();dependent=False
    while pending:
        current=pending.pop();signature=current.ExportToString()
        if signature in seen:continue
        seen.add(signature)
        require(len(seen)<=4096,'coverage unknown: too many variant combinations; retain hard usage')
        copy=Usd.Stage.Open(stage.GetRootLayer(),current,load=Usd.Stage.LoadAll)
        require(not copy.GetCompositionErrors(),'coverage unknown: unresolved composition; retain hard usage')
        for p in copy.TraverseAll():
            dependent=dependent or direct(p) or p.GetTypeName()=='GeospatialDataSource'
            require(not dependent,'stale or missing dependency summary')
            for name in p.GetVariantSets().GetNames():
                v=p.GetVariantSet(name)
                for choice in v.GetVariantNames():
                    if choice==v.GetVariantSelection():continue
                    next_session=Sdf.Layer.CreateAnonymous();next_session.TransferContent(current)
                    candidate=Usd.Stage.Open(stage.GetRootLayer(),next_session,load=Usd.Stage.LoadAll);candidate.SetEditTarget(next_session)
                    candidate.GetPrimAtPath(p.GetPath()).GetVariantSet(name).SetVariantSelection(choice)
                    if next_session.ExportToString() not in seen:pending.append(next_session)
    return summary
