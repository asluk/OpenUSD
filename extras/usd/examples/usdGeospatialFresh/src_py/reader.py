"""Fresh proposal-derived reader. Runtime interfaces here are implementation choices.

Authority is ../authority/proposal.md, never a previous prototype. All source
properties are inputs from its tables. Results and diagnostics are transient.
"""
from __future__ import annotations

import bisect
import json
import math
import os
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import numpy as np
from pyproj import CRS, Transformer, network, datadir
from pxr import Gf, Plug, Sdf, Usd, UsdGeom, UsdShade, Vt

ROOT = Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT / 'schema'))
network.set_network_enabled(False)
datadir.append_data_dir(os.environ.get('GEOSPATIAL_RESOURCE_DIR',str(ROOT.parent/'geospatial-model-resources')))
CAP = 'usd.geospatial.crsResolution.v1'
PROFILE = 'usd.geospatial.publication.v1'


class ResolutionError(ValueError):
    pass


def require(test, message):
    if not test:
        raise ResolutionError(message)


# Exact decimal lexical rewriting deliberately does not round through floats.
LEX = re.compile(r'\s+|"(?:[^"]|"")*"|[A-Za-z_][A-Za-z_0-9]*|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?|[\[\](),]')
ALIASES = dict(PRIMEMERIDIAN='PRIMEM', GEODETICCRS='GEODCRS',
               GEOGRAPHICCRS='GEOGCRS', PROJECTEDCRS='PROJCRS',
               GEODETICDATUM='DATUM', TRF='DATUM', VERTICALDATUM='VDATUM',
               VRF='VDATUM', VERTICALCRS='VERTCRS', SPHEROID='ELLIPSOID', PROJECTION='METHOD',
               ENGINEERINGCRS='ENGCRS', ENGINEERINGDATUM='EDATUM',
               PARAMETRICCRS='PARAMETRICCRS', PARAMETRICDATUM='PDATUM',
               TIMEDATUM='TDATUM', TEMPORALQUANTITY='TIMEUNIT', VELOCITYGRID='MODEL')
ENUM = {k.lower(): k for k in ['Cartesian', 'ellipsoidal', 'spherical', 'vertical',
        'affine', 'ordinal', 'parametric', 'temporal', 'temporalDateTime',
        'temporalCount', 'temporalMeasure', 'north', 'northNorthEast', 'northEast',
        'eastNorthEast', 'east', 'eastSouthEast', 'southEast', 'southSouthEast',
        'south', 'southSouthWest', 'southWest', 'westSouthWest', 'west',
        'westNorthWest', 'northWest', 'northNorthWest', 'up', 'down',
        'geocentricX', 'geocentricY', 'geocentricZ', 'columnPositive',
        'columnNegative', 'rowPositive', 'rowNegative', 'displayRight',
        'displayLeft', 'displayUp', 'displayDown', 'forward', 'aft', 'port',
        'starboard', 'clockwise', 'counterClockwise', 'towards', 'awayFrom',
        'future', 'past', 'unspecified']}


def normalize_wkt(text):
    tokens = []
    pos = 0
    for m in LEX.finditer(text):
        require(m.start() == pos, 'Invalid WKT lexical character')
        pos = m.end()
        if not m[0].isspace():
            tokens.append(m[0])
    require(pos == len(text) and tokens, 'Invalid WKT lexical input')
    stack, result = [], []
    for i, item in enumerate(tokens):
        if item[0] == '"':
            result.append(item)
        elif item[0] in '+-.0123456789':
            val = format(Decimal(item), 'f')
            if '.' in val:
                val = val.rstrip('0').rstrip('.')
            result.append('0' if Decimal(item) == 0 else val.lstrip('+'))
        elif item in '[(':
            stack.append(result[-1]); result.append('[')
        elif item in '])':
            require(bool(stack), 'Unbalanced WKT'); stack.pop(); result.append(']')
        elif item == ',':
            result.append(item)
        elif i + 1 < len(tokens) and tokens[i + 1] in '[(':
            key = ALIASES.get(item.upper(), item.upper())
            if key == 'UNIT':
                # WKT2 allows UNIT aliases in these grammatical contexts.
                parent = stack[-1] if stack else ''
                if parent in ('ELLIPSOID', 'VERTCRS', 'VDATUM'):
                    key = 'LENGTHUNIT'
                elif parent == 'PRIMEM':
                    key = 'ANGLEUNIT'
                else:
                    # Determine enclosing CS subtype rather than unit-name heuristics.
                    prefix = ''.join(result)
                    cs = list(re.finditer(r'CS\[(\w+),', prefix))
                    require(bool(cs), 'UNIT alias needs grammatical unit context')
                    key = 'ANGLEUNIT' if cs[-1][1] in ('ellipsoidal', 'spherical') else 'LENGTHUNIT'
            result.append(key)
        else:
            require(item.lower() in ENUM, 'Unsupported WKT enumeration: ' + item)
            result.append(ENUM[item.lower()])
    require(not stack, 'Unbalanced WKT')
    # PROJ supplies grammar/semantic validation; its serialization is not our output.
    CRS.from_wkt(text)
    return ''.join(result)


def finite(v, label='coordinate'):
    a = np.asarray(v, dtype=float)
    require(np.isfinite(a).all(), 'Non-finite ' + label)
    return a


class Definition:
    def __init__(self, wkt):
        require(isinstance(wkt, str) and bool(wkt), 'Missing CRS WKT')
        require('COORDINATEMETADATA' not in wkt.upper(), 'Coordinate epochs are outside initial scope')
        root=re.match(r'\s*(\w+)\s*[\[(]',wkt)
        require(root and root[1].upper() in {'GEOGCRS','GEOGRAPHICCRS','GEODCRS','GEODETICCRS','PROJCRS','PROJECTEDCRS','COMPOUNDCRS','BOUNDCRS','DERIVEDPROJCRS'},'A complete supported WKT2 CRS is required')
        self.wkt = wkt
        try:
            self.crs = CRS.from_wkt(wkt)
        except Exception as e:
            raise ResolutionError('Invalid WKT: ' + str(e)) from e
        self.axes = self.crs.axis_info
        dirs = [a.direction.lower() for a in self.axes]
        self.geo = self.crs.is_geographic
        if self.crs.is_geocentric:
            self.semantic = ['geocentricx', 'geocentricy', 'geocentricz']
        else:
            self.semantic = ['east', 'north'] + (['up'] if len(dirs) == 3 else [])
        require(len(dirs) in (2, 3) and sorted(dirs) == sorted(self.semantic),
                'Unsupported CRS directions/dimensionality: ' + str(dirs))
        self.order = [dirs.index(d) for d in self.semantic]
        self.units = np.array([self.axes[i].unit_conversion_factor for i in self.order])
        self.warnings = []
        try:
            if normalize_wkt(wkt) != wkt:
                self.warnings.append('Non-normal WKT spelling')
        except Exception as e:
            self.warnings.append('Normal-form check unavailable: ' + str(e))

    def native(self, coords):
        p = finite(coords)
        require(p.shape[-1] == len(self.order), 'Coordinate dimensionality mismatch')
        return p[..., np.argsort(self.order)]

    def semantic_tuple(self, coords):
        return np.asarray(coords)[..., self.order]

    @property
    def dimension(self):
        return len(self.axes)

    @property
    def geographic(self):
        g = self.crs.geodetic_crs
        require(g is not None, 'No Earth-referenced geodetic CRS')
        if g.is_geocentric:
            obj=g.to_json_dict();obj.pop('id',None);obj['type']='GeographicCRS'
            obj['coordinate_system']={'subtype':'ellipsoidal','axis':[
                {'name':'Geodetic latitude','abbreviation':'Lat','direction':'north','unit':'degree'},
                {'name':'Geodetic longitude','abbreviation':'Lon','direction':'east','unit':'degree'},
                {'name':'Ellipsoidal height','abbreviation':'h','direction':'up','unit':'metre'}]}
            g=CRS.from_json_dict(obj)
        return definition(g.to_3d().to_wkt())

    @property
    def geocentric(self):
        g = self.geographic.crs.to_json_dict()
        # Preserve the datum/ensemble and prime meridian, replace only the CS.
        g.pop('id', None); g.pop('area', None); g.pop('bbox', None)
        g['type'] = 'GeodeticCRS'
        g['coordinate_system'] = {'subtype': 'Cartesian', 'axis': [
            {'name': 'Geocentric ' + a, 'abbreviation': a, 'direction': 'geocentric' + a,
             'unit': 'metre'} for a in 'XYZ']}
        return definition(CRS.from_json_dict(g).to_wkt())


@lru_cache(maxsize=128)
def definition(wkt):
    return Definition(wkt)


class Engine:
    def __init__(self):
        self.operations = []
        self.cache = {}

    def transform(self, src, dst, points):
        points = finite(points)
        require(points.shape[-1] == src.dimension, 'Input dimensionality mismatch')
        require(src.dimension == dst.dimension, 'Missing height cannot be invented')
        if src.wkt == dst.wkt:
            return points.copy()
        key = src.wkt, dst.wkt
        try:
            if key not in self.cache:
                self.cache[key] = Transformer.from_crs(src.crs, dst.crs, always_xy=False,
                                                       allow_ballpark=False, only_best=True)
            t = self.cache[key]
            p = src.native(points)
            transformed = t.transform(*np.moveaxis(p, -1, 0), errcheck=True)
            result = dst.semantic_tuple(np.stack(transformed, axis=-1))
            used = t
            try:
                used = t.get_last_used_operation()
            except Exception:
                pass
            pipeline = used.definition
            require(not re.search(r'(?:^|\s)\+?(?:dx|dy|dz|drx|dry|drz|ds|t_epoch|dt)=', pipeline),
                    'Epoch-dependent operation outside initial scope')
            record = {'description': used.description, 'pipeline': pipeline,
                      'accuracy_m': None if used.accuracy < 0 else used.accuracy}
            if record not in self.operations:
                self.operations.append(record)
            return finite(result, 'operation result')
        except ResolutionError:
            raise
        except Exception as e:
            raise ResolutionError('Coordinate operation failed: ' + str(e)) from e


def quaternion(angles):
    h, p, r = np.radians(finite(angles, 'orientation')) / 2
    def mul(a, b):
        w, v = a[0], a[1:]; s, u = b[0], b[1:]
        return np.r_[w*s - v@u, w*u + s*v + np.cross(v,u)]
    return mul(mul(np.array([math.cos(h), 0, 0, -math.sin(h)]),
                   np.array([math.cos(p), math.sin(p), 0, 0])),
               np.array([math.cos(r), 0, math.sin(r), 0]))


def rotation(q):
    w, x, y, z = q / np.linalg.norm(q)
    # Column matrix, transposed for Core row vectors.
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]).T


def read_attr(prim, name, typename, time=Usd.TimeCode.Default(), uniform=False, fallback=None):
    a = prim.GetAttribute(name)
    if not a:
        require(fallback is not None, 'Missing ' + name)
        return fallback
    require(str(a.GetTypeName()) == typename, 'Wrong USD type for ' + name)
    stack=a.GetPropertyStack(time)
    require(not stack or str(stack[0].typeName)==typename,'Wrong authored USD type for '+name)
    expected=Sdf.VariabilityUniform if uniform else Sdf.VariabilityVarying
    require(a.GetVariability()==expected and (not stack or stack[0].variability==expected),'Wrong variability for '+name)
    if uniform:
        require(a.GetVariability() == Sdf.VariabilityUniform, 'Wrong variability for ' + name)
        require(not a.GetTimeSamples(), 'Uniform property has active samples: ' + name)
        time = Usd.TimeCode.Default()
    v = a.Get(time)
    require(v is not None, 'Blocked or unavailable ' + name)
    return v


def pose(prim, time, held):
    a = prim.GetAttribute('crs:orientation')
    if not a or not a.HasAuthoredValueOpinion():
        return quaternion((0, 0, 0))
    require(str(a.GetTypeName()) == 'double3', 'Wrong orientation type')
    stack=a.GetPropertyStack(time)
    require(not stack or (str(stack[0].typeName)=='double3' and stack[0].variability==Sdf.VariabilityVarying),'Invalid authored orientation field')
    samples = a.GetTimeSamples()
    def q(t):
        v = a.Get(t); require(v is not None, 'Blocked orientation'); return quaternion(v)
    if time.IsDefault() or not samples:
        return q(time)
    t = time.GetValue(); i = bisect.bisect_left(samples, t)
    if i == 0 or i == len(samples) or samples[i] == t:
        return q(Usd.TimeCode(samples[min(i, len(samples)-1)]))
    left, right = samples[i-1:i+1]
    q0 = q(Usd.TimeCode(left))
    if held:
        return q0
    q1 = q(Usd.TimeCode(right)); dot = float(q0 @ q1)
    require(abs(dot) > 1e-12, 'Ambiguous 180-degree pose interpolation; uncertainty 1e-12 quaternion dot')
    if dot < 0:
        q1 = -q1; dot = -dot
    alpha = (t-left)/(right-left)
    if dot > 1-1e-12:
        v = q0*(1-alpha)+q1*alpha
    else:
        theta = math.acos(min(1,dot))
        v = (q0*math.sin((1-alpha)*theta)+q1*math.sin(alpha*theta))/math.sin(theta)
    return v/np.linalg.norm(v)


def direct(prim):
    return 'GeospatialCRSBindingAPI' in list(prim.GetAppliedSchemas())


def nearest(prim):
    while prim and not prim.IsPseudoRoot():
        if direct(prim):
            return prim
        prim = prim.GetParent()
    return None


def crs_for(prim):
    return definition(str(read_attr(prim, 'crs:wkt', 'token', uniform=True)))


def row_transform(points, matrix):
    p = np.asarray(points, dtype=float)
    return p @ np.asarray(matrix)[:3,:3] + np.asarray(matrix)[3,:3]


class Reader:
    def __init__(self, stage, output_wkt=None, time=None):
        self.stage = stage
        self.time = Usd.TimeCode.Default() if time is None else Usd.TimeCode(time)
        self.held = stage.GetInterpolationType() == Usd.InterpolationTypeHeld
        self.mpu = UsdGeom.GetStageMetersPerUnit(stage)
        self.yup = UsdGeom.GetStageUpAxis(stage) == 'Y'
        require(math.isfinite(self.mpu) and self.mpu > 0, 'Invalid scene unit')
        self.engine = Engine()
        if output_wkt is None:
            root = stage.GetDefaultPrim()
            require(root and (direct(root) or root.GetTypeName() == 'CoordinateReferenceSystem'),
                    'Output context unspecified')
            self.output = crs_for(root)
        else:
            self.output = definition(output_wkt)
        self.scene = self.output.geocentric if self.output.geo else self.output

    def to_enu(self, p):
        p = np.asarray(p, dtype=float)
        return (p[..., [0,2,1]] * [1,-1,1] if self.yup else p) * self.mpu

    def from_enu(self, p):
        p = np.asarray(p, dtype=float)/self.mpu
        return p[..., [0,2,1]] * [1,1,-1] if self.yup else p

    def local(self, prim):
        x = UsdGeom.Xformable(prim)
        return np.asarray(x.GetLocalTransformation(self.time)) if x else np.eye(4)

    def basis(self, source, position):
        require(source.dimension == 3, 'Model placement requires a complete 3D CRS')
        require(not (source.crs.is_geocentric and position[0] == position[1] == 0),
                'Geocentric pole does not determine ENU meridian')
        geo, gc = source.geographic, source.geocentric
        llh = self.engine.transform(source, geo, position)
        lon, lat = llh[:2] * geo.units[:2]
        require(abs(lat) <= math.pi/2+1e-12, 'Latitude outside domain')
        origin = self.engine.transform(source, gc, position)
        sl,cl,sp,cp = math.sin(lon),math.cos(lon),math.sin(lat),math.cos(lat)
        basis = np.array([[-sl,cl,0],[-sp*cl,-sp*sl,cp],[cp*cl,cp*sl,sp]])
        return gc, origin, basis

    def model_map(self, anchor, points, enclosing=None, skip_adjust=False):
        require(bool(UsdGeom.Xformable(anchor)),'Model binding requires Xformable prim')
        source = crs_for(anchor)
        require(anchor.GetTypeName() != 'GeospatialDataSource', 'Measurement carrier is not a model anchor')
        position = finite(read_attr(anchor, 'crs:position', 'double3', self.time), 'position')
        gc, origin, basis = self.basis(source, position)
        physical = self.to_enu(points) @ rotation(pose(anchor,self.time,self.held)) @ basis + origin
        src_points = self.engine.transform(gc, source, physical)
        parent = enclosing if enclosing is not None else nearest(anchor.GetParent())
        work = crs_for(parent) if parent else source
        if skip_adjust:
            return src_points,source
        work_points = self.engine.transform(source, work, src_points)
        work_origin = self.engine.transform(source, work, position)
        matrix = self.local(anchor)
        return self.adjust(work, work_points, matrix, work_origin), work

    def adjust(self, work, points, matrix, origin=None):
        if np.array_equal(matrix,np.eye(4)):
            return points
        if work.geo:
            require(origin is not None, 'Geographic measurement adjustment needs explicit Cartesian working CRS')
            gc, gc_origin, basis = self.basis(work, origin)
            p = self.engine.transform(work,gc,points)
            chart = self.from_enu((p-gc_origin) @ basis.T)
            adjusted = self.to_enu(row_transform(chart,matrix)) @ basis + gc_origin
            return self.engine.transform(gc,work,adjusted)
        dims = work.dimension
        require(dims in (2,3), 'Unsupported chart dimension')
        o = np.zeros(dims) if origin is None else origin
        chart = (points-o)*work.units
        if dims == 2:
            chart = np.concatenate([np.asarray(chart),np.zeros(np.asarray(chart).shape[:-1]+(1,))],axis=-1)
        adjusted = self.to_enu(row_transform(self.from_enu(chart),matrix))
        if dims == 2:
            require(np.all(np.abs(adjusted[...,2]) < 1e-12), '2D adjustment has out-of-plane coupling')
            adjusted = adjusted[...,:2]
        return adjusted/work.units+o

    def validate_roles(self, prim, anchor):
        current = prim
        while current and not current.IsPseudoRoot():
            invalid = current != anchor or current.GetTypeName() == 'GeospatialDataSource'
            if invalid:
                for name in ('crs:position','crs:orientation'):
                    a=current.GetAttribute(name)
                    require(not (a and a.HasAuthoredValueOpinion()), 'Placement field in invalid role: '+str(current.GetPath())+' '+name)
            if current == anchor:
                break
            current=current.GetParent()

    def points(self, prim, points, output=None):
        output = output or self.output
        # A recorded Cartesian bake context is already ordinary geometry. Its
        # nearest typed context takes precedence over a binding outside it.
        anchor=None;cursor=prim
        while cursor and not cursor.IsPseudoRoot():
            if direct(cursor):anchor=cursor;break
            if cursor.GetTypeName()=='CoordinateReferenceSystem':break
            cursor=cursor.GetParent()
        if not anchor:
            # A fully baked typed context keeps complete ordinary transforms.
            p=prim; context=None
            while p and not p.IsPseudoRoot():
                if p.GetTypeName() == 'CoordinateReferenceSystem': context=p;break
                p=p.GetParent()
            require(context is not None,'No placement binding or Cartesian bake context')
            c=crs_for(context);require(not c.geo,'Angular ordinary geometry is invalid')
            m=UsdGeom.XformCache(self.time).GetLocalToWorldTransform(prim)
            return self.engine.transform(c,output,self.to_enu(row_transform(points,m))/c.units)
        self.validate_roles(prim,anchor)
        require(anchor.GetTypeName() != 'GeospatialDataSource','Use measurement query for external domain')
        d=np.eye(4); current=prim; reset=False
        while current != anchor:
            d=d @ self.local(current)
            x=UsdGeom.Xformable(current)
            if x and x.GetResetXformStack(): reset=True;break
            current=current.GetParent()
        if reset:
            # Retain binding validity and intrinsic placement, remove ordinary A.
            p,w=self.model_map(anchor,row_transform(points,d),skip_adjust=True)
            return self.engine.transform(w,output,p)
        p,w=self.model_map(anchor,row_transform(points,d))
        return self.engine.transform(w,output,p)

    def scene_points(self, prim, points, origin=(0,0,0)):
        require(self.scene.dimension == 3,'Scene geometry needs 3D chart')
        return self.from_enu((self.points(prim,points,self.scene)-finite(origin))*self.scene.units)

    def derivative(self, prim, point, step=0.01):
        point=finite(point); cols=[]
        for i in range(3):
            d=np.zeros(3);d[i]=step
            cols.append((self.scene_points(prim,point+d)-self.scene_points(prim,point-d))/(2*step))
        return np.array(cols)  # row-vector derivative

    def transport(self, prim, point, vector, role):
        j=self.derivative(prim,point)
        if role == 'normal':
            require(abs(np.linalg.det(j))>1e-14,'Singular normal transport')
            v=finite(vector)@np.linalg.inv(j).T;return v/np.linalg.norm(v)
        require(role == 'vector','No implied role for arbitrary numeric triples')
        return finite(vector)@j

    def inverse(self, prim, target, guess=(0,0,0), tolerance_m=1e-5):
        target=finite(target);x=finite(guess).copy()
        gc=self.output.geocentric
        t=self.engine.transform(self.output,gc,target)
        for _ in range(25):
            f=self.engine.transform(self.output,gc,self.points(prim,x));r=t-f
            if np.linalg.norm(r)<=tolerance_m:return x
            eps=0.01; jac=[]
            for i in range(3):
                d=np.eye(3)[i]*eps
                jac.append((self.engine.transform(self.output,gc,self.points(prim,x+d))-
                            self.engine.transform(self.output,gc,self.points(prim,x-d)))/(2*eps))
            require(abs(np.linalg.det(jac))>1e-14,'Singular required inverse')
            x+=np.linalg.solve(np.array(jac).T,r)
        raise ResolutionError('Inverse failed to establish requested tolerance')

    def instance_points(self, instancer, index, prototype_prim, points):
        inst=UsdGeom.PointInstancer(instancer)
        matrices=inst.ComputeInstanceTransformsAtTime(self.time,self.time,UsdGeom.PointInstancer.ExcludeProtoXform,UsdGeom.PointInstancer.IgnoreMask)
        mask=inst.ComputeMaskAtTime(self.time)
        require(not mask or mask[index],'Masked instance is not consumed')
        matrix=np.array(matrices[index])
        targets=inst.GetPrototypesRel().GetTargets(); indices=inst.GetProtoIndicesAttr().Get(self.time)
        root=self.stage.GetPrimAtPath(targets[indices[index]])
        bound=nearest(prototype_prim)
        independent=bound and bound.GetPath().HasPrefix(root.GetPath())
        if not independent:
            d=np.eye(4);p=prototype_prim
            while True:
                d=d@self.local(p)
                if p==root:break
                p=p.GetParent()
            return self.points(instancer,row_transform(row_transform(points,d),matrix))
        # Override storage-parent binding with expanded occurrence context.
        d=np.eye(4);p=prototype_prim;reset=False
        while p!=bound:
            d=d@self.local(p)
            if UsdGeom.Xformable(p).GetResetXformStack():reset=True;break
            p=p.GetParent()
        enclosing=nearest(bound.GetParent())
        if bound==root or not (enclosing and enclosing.GetPath().HasPrefix(root.GetPath())):
            enclosing=nearest(instancer)
        b,w=self.model_map(bound,row_transform(points,d),enclosing,skip_adjust=reset)
        if np.array_equal(matrix,np.eye(4)):
            return self.engine.transform(w,self.output,b)
        ia=nearest(instancer); require(ia is not None,'Instance transport needs instancer model context')
        gc=crs_for(ia).geocentric
        saved=self.output;self.output=gc
        try:
            target=self.engine.transform(w,gc,b)
            values=[]
            for v in np.atleast_2d(target):
                x=self.inverse(instancer,v)
                values.append(self.points(instancer,row_transform(x,matrix),gc))
        finally:self.output=saved
        return self.engine.transform(gc,saved,np.array(values))

    def result_info(self):
        return {'coordinate_crs':self.output.wkt,'scene_chart':self.scene.wkt,
                'operations':self.engine.operations,'coverage':'finite requested points only',
                'continuous_bound_certified':False}

    def continuous_bound(self,*args,**kwargs):
        raise ResolutionError('Continuous-domain bound unsupported: no certified nonlinear enclosure')


def dependency_summary(prim):
    """Constant-interface read. Deliberately does not traverse or load payloads."""
    info=prim.GetCustomData().get('profilesInfo',{})
    usages=info.get('capabilityUsages')
    compatibility=info.get('profileCompatibility',{})
    hard=isinstance(usages,dict) and usages.get(CAP)=='hard'
    qualified=('ClaimsAPI' in prim.GetAppliedSchemas() and isinstance(usages,dict) and
               PROFILE in compatibility and len(compatibility[PROFILE])==0)
    return 'required' if hard else ('known-none' if qualified else 'unknown')


def publish_claim(prim, needs_resolution):
    prim.AddAppliedSchema('ClaimsAPI')
    prim.SetCustomDataByKey('profilesInfo',{
        'capabilityUsages':{CAP:'hard'} if needs_resolution else {},
        'profileCompatibility':{PROFILE:Vt.StringArray()}})


def check_publication(prim, retained_requirements):
    # Publisher supplies complete retained composition/variant coverage. Unknown
    # retained content conservatively requires resolution; reader never discovers it.
    needs=any(x in ('required','unknown') for x in retained_requirements)
    require(not needs or dependency_summary(prim)=='required',
            'Stale or incomplete publisher claim omits retained dependency')
    return True


def export_geometry(reader, source_meshes, destination, times=None):
    """Explicit finite polygonal bake. Continuous error certification is separate."""
    out=Usd.Stage.CreateNew(str(destination));UsdGeom.SetStageMetersPerUnit(out,reader.mpu)
    UsdGeom.SetStageUpAxis(out,'Y' if reader.yup else 'Z')
    out.SetTimeCodesPerSecond(reader.stage.GetTimeCodesPerSecond())
    context=out.DefinePrim('/Context','CoordinateReferenceSystem');out.SetDefaultPrim(context)
    context.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=False,variability=Sdf.VariabilityUniform).Set(normalize_wkt(reader.scene.wkt))
    origin=np.array(reader.points(source_meshes[0],[(0,0,0)],reader.scene)[0])
    root=UsdGeom.Xform.Define(out,'/Context/Origin')
    root.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*reader.from_enu(origin*reader.scene.units)))
    schedule=[None if reader.time.IsDefault() else reader.time.GetValue()] if times is None else times
    materials={}
    for i,mesh_prim in enumerate(source_meshes):
        mesh=UsdGeom.Mesh(mesh_prim);target=UsdGeom.Mesh.Define(out,f'/Context/Origin/Mesh{i}')
        for pv in UsdGeom.PrimvarsAPI(mesh_prim).GetPrimvars():
            require(pv.GetTypeName().role not in ('Point','Vector','Normal'),
                    'Semantic geometric primvar export unsupported in this prototype: '+pv.GetName())
        # Preserve all unrelated properties and schema applications as composed data.
        tmp=reader.stage.Flatten();Sdf.CopySpec(tmp,mesh_prim.GetPath(),out.GetRootLayer(),target.GetPath())
        target=UsdGeom.Mesh(out.GetPrimAtPath(target.GetPath()))
        material,_=UsdShade.MaterialBindingAPI(mesh_prim).ComputeBoundMaterial()
        if material:
            source_material=material.GetPath()
            if source_material not in materials:
                material_path=Sdf.Path('/Context/Materials/Material'+str(len(materials)))
                out.DefinePrim('/Context/Materials','Scope')
                require(Sdf.CopySpec(tmp,source_material,out.GetRootLayer(),material_path),'Material dependency copy failed')
                materials[source_material]=material_path
            UsdShade.MaterialBindingAPI.Apply(target.GetPrim()).Bind(UsdShade.Material(out.GetPrimAtPath(materials[source_material])))
        for name in ['crs:position','crs:orientation','crs:wkt']:
            target.GetPrim().RemoveProperty(name)
        target.GetPrim().RemoveAppliedSchema('GeospatialCRSBindingAPI')
        UsdGeom.Xformable(target).ClearXformOpOrder()
        target.GetPointsAttr().Clear()
        offset=UsdGeom.Xformable(target).AddTranslateOp(UsdGeom.XformOp.PrecisionDouble,'resolvedOffset')
        for t in schedule:
            r=Reader(reader.stage,reader.output.wkt,t)
            pts=mesh.GetPointsAttr().Get(r.time)
            mesh_origin=r.points(mesh_prim,[(0,0,0)],r.scene)[0]
            offset.Set(Gf.Vec3d(*r.from_enu((mesh_origin-origin)*r.scene.units)),r.time)
            resolved=r.scene_points(mesh_prim,np.array(pts),mesh_origin)
            target.GetPointsAttr().Set([Gf.Vec3f(*x) for x in resolved],r.time)
            normals=mesh.GetNormalsAttr().Get(r.time)
            if normals:
                interpolation=mesh.GetNormalsInterpolation()
                counts=mesh.GetFaceVertexCountsAttr().Get(r.time);indices=mesh.GetFaceVertexIndicesAttr().Get(r.time)
                selected=[];corner=0
                for face,count in enumerate(counts):
                    for _ in range(count):
                        vertex=indices[corner]
                        ni=0 if interpolation=='constant' else face if interpolation=='uniform' else corner if interpolation=='faceVarying' else vertex
                        require(ni<len(normals),'Invalid normal interpolation/indexing')
                        selected.append(ni)
                        corner+=1
                source_points=np.asarray(pts);derivatives=[]
                for axis in np.eye(3):
                    derivatives.append((r.scene_points(mesh_prim,source_points+axis*.01)-r.scene_points(mesh_prim,source_points-axis*.01))/.02)
                jac=np.stack(derivatives,axis=-2)
                require(np.all(np.abs(np.linalg.det(jac))>1e-14),'Singular normal transport')
                invt=np.swapaxes(np.linalg.inv(jac),-1,-2)[np.asarray(indices)]
                transformed=np.einsum('ni,nij->nj',np.asarray(normals)[selected],invt)
                transformed/=np.linalg.norm(transformed,axis=1)[:,None]
                transported=[Gf.Vec3f(*v) for v in transformed]
                target.GetNormalsAttr().Set(transported,r.time);target.SetNormalsInterpolation('faceVarying')
            # A copied local extent would describe pre-placement geometry.
            a=np.asarray(resolved);target.GetExtentAttr().Set([Gf.Vec3f(*a.min(axis=0)),Gf.Vec3f(*a.max(axis=0))],r.time)
    publish_claim(context,False);out.GetRootLayer().Save()
    return out,origin


if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('stage');a.add_argument('prim');a.add_argument('--output-wkt');a.add_argument('--time',type=float);a.add_argument('--point',nargs=3,type=float,default=[0,0,0]);args=a.parse_args()
    try:
        stage=Usd.Stage.Open(args.stage);r=Reader(stage,Path(args.output_wkt).read_text() if args.output_wkt else None,args.time)
        print(json.dumps({'success':True,'points':r.points(stage.GetPrimAtPath(args.prim),[args.point]).tolist(),**r.result_info()}))
    except Exception as e:
        print(json.dumps({'success':False,'error':str(e)}));raise SystemExit(1)
