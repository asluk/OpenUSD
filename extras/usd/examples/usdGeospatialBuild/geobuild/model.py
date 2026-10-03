"""Authored-only checks derived from the frozen candidate."""
from decimal import Decimal
import re, math
from pyproj import CRS
from pxr import Usd, UsdGeom, Sdf

class GeoError(ValueError): pass

_LEX=re.compile(r'"(?:[^"\n]|"")*"|[A-Za-z_][A-Za-z_0-9]*|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?|[\[\](),]|\s+')
def normalize_wkt(text):
    if not isinstance(text,str) or not text: raise GeoError('Missing WKT')
    if re.match(r'\s*COORDINATEMETADATA\b',text,re.I):
        raise GeoError('Coordinate epochs/wrappers are outside the initial scope')
    try: CRS.from_wkt(text)
    except Exception as e: raise GeoError(f'Invalid CRS WKT: {e}') from e
    parts=[]; end=0
    for m in _LEX.finditer(text):
        if m.start()!=end: raise GeoError('Unsupported WKT lexical token')
        s=m.group(); end=m.end()
        if s.isspace(): continue
        if s[0]=='"': parts.append(s)
        elif s[0].isalpha() or s[0]=='_': parts.append(s.upper())
        elif s[0] in '[](),': parts.append(s)
        else:
            d=Decimal(s)
            if not d.is_finite(): raise GeoError('Nonfinite WKT number')
            v=format(d,'f'); v=v.rstrip('0').rstrip('.') if '.' in v else v
            parts.append('0' if d==0 else v)
    if end!=len(text): raise GeoError('Unsupported WKT lexical suffix')
    return ''.join(parts)

def crs(text):
    normalize_wkt(text)
    c=CRS.from_wkt(text)
    if len(c.axis_info)!=3: raise GeoError('A complete three-axis CRS is required')
    return c

def binding(prim):
    p=prim
    while p and not p.IsPseudoRoot():
        r=p.GetRelationship('crs:binding')
        if r and r.HasAuthoredTargets():
            targets=r.GetTargets()
            if len(targets)!=1: raise GeoError(f'{p.GetPath()}: binding requires exactly one target')
            q=p.GetStage().GetPrimAtPath(targets[0])
            if not q or not q.GetAttribute('crs:wkt'): raise GeoError(f'{p.GetPath()}: broken CRS target')
            return p,crs(q.GetAttribute('crs:wkt').Get())
        p=p.GetParent()
    raise GeoError(f'{prim.GetPath()}: no CRS binding')

def validate(stage):
    errors=[]; dependent=False
    for p in stage.Traverse(Usd.TraverseInstanceProxies()):
        try:
            w=p.GetAttribute('crs:wkt')
            if w:
                v=w.Get(); crs(v)
                if w.GetTypeName()!=Sdf.ValueTypeNames.Token or w.GetVariability()!=Sdf.VariabilityUniform:
                    raise GeoError('WKT must be a uniform token')
                if normalize_wkt(v)!=v: raise GeoError('WKT string is not in the candidate lexical normal form')
            r=p.GetRelationship('crs:binding')
            if r and r.HasAuthoredTargets():
                dependent=True; binding(p)
                coords=p.GetRelationship('crs:coordinateProperties')
                if UsdGeom.Xformable(p) and not (coords and coords.HasAuthoredTargets()):
                    a=p.GetAttribute('crs:position')
                    if not a or not a.HasAuthoredValue(): raise GeoError('Direct model binding requires crs:position')
                    if a.GetTypeName()!=Sdf.ValueTypeNames.Double3: raise GeoError('Placement position must be double3')
                    for t in [Usd.TimeCode.Default(),*[Usd.TimeCode(x) for x in a.GetTimeSamples()]]:
                        v=a.Get(t)
                        if v is not None and not all(math.isfinite(x) for x in v):raise GeoError('Nonfinite placement')
                    a=p.GetAttribute('crs:orientation')
                    if a:
                        if a.GetTypeName()!=Sdf.ValueTypeNames.Quatd:raise GeoError('Orientation must be quatd')
                        for t in [Usd.TimeCode.Default(),*[Usd.TimeCode(x) for x in a.GetTimeSamples()]]:
                            q=a.Get(t)
                            if q is not None and (not math.isfinite(q.GetLength()) or abs(q.GetLength()-1)>1e-9):raise GeoError('Orientation must be a unit quaternion')
                    a=p.GetAttribute('crs:scale')
                    if a:
                        if a.GetTypeName()!=Sdf.ValueTypeNames.Double3:raise GeoError('Scale must be double3')
                        for t in [Usd.TimeCode.Default(),*[Usd.TimeCode(x) for x in a.GetTimeSamples()]]:
                            v=a.Get(t)
                            if v is not None and not all(math.isfinite(x) and x!=0 for x in v):raise GeoError('Invalid placement scale')
                if coords and coords.HasAuthoredTargets():
                    if not coords.GetTargets():raise GeoError('Coordinate properties cannot be empty')
                    for path in coords.GetTargets():
                        a=stage.GetAttributeAtPath(path)
                        if path.GetPrimPath()!=p.GetPath() or not a or a.GetTypeName()!=Sdf.ValueTypeNames.Double3Array:
                            raise GeoError('Coordinate association must target a double3[] property on the measurement prim')
                        for t in [Usd.TimeCode.Default(),*[Usd.TimeCode(x) for x in a.GetTimeSamples()]]:
                            v=a.Get(t)
                            if v is not None and not all(math.isfinite(x) for row in v for x in row):raise GeoError('Nonfinite measurement coordinate')
        except Exception as e: errors.append((str(p.GetPath()),str(e)))
    if dependent and stage.GetRootLayer().customLayerData.get('geospatialResolutionRequired') is not True:
        errors.append(('/', 'Missing complete-asset dependency declaration'))
    return errors
