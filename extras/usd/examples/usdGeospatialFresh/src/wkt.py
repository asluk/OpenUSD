"""Lossless lexical normalization derived from proposal lines 1830-1892."""
from decimal import Decimal
import re
from errors import ResolutionFailure

TOKEN = re.compile(r'\s+|"(?:[^"]|"")*"|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?|[A-Za-z][A-Za-z0-9_]*|[][(),]')
PREFERRED = {'PRIMEMERIDIAN':'PRIMEM','GEODETICDATUM':'DATUM','TRF':'DATUM','VERTICALDATUM':'VDATUM','VRF':'VDATUM','ENGINEERINGDATUM':'EDATUM','TIMEDATUM':'TDATUM','PARAMETRICDATUM':'PDATUM','GEODETICCRS':'GEODCRS','GEOGRAPHICCRS':'GEOGCRS','PROJECTEDCRS':'PROJCRS','VERTICALCRS':'VERTCRS','ENGINEERINGCRS':'ENGCRS'}
ENUM = {k.lower():k for k in ['Cartesian','ellipsoidal','spherical','vertical','parametric','temporal','ordinal','affine','cylindrical','polar','east','north','up','west','south','down','geocentricX','geocentricY','geocentricZ','future','past','unspecified','clockwise','counterClockwise','awayFrom','towards','columnPositive','rowPositive','displayRight','displayLeft','displayUp','displayDown','forward','aft','port','starboard']}

def tokens(text):
    result=[];end=0
    for m in TOKEN.finditer(text):
        if m.start()!=end:
            raise ResolutionFailure('invalid-wkt-lexeme', repr(text[end:m.start()]))
        end=m.end()
        if not m.group().isspace():result.append(m.group())
    if end!=len(text):raise ResolutionFailure('invalid-wkt-lexeme',repr(text[end:]))
    return result

def normalize(text):
    items=tokens(text)
    if not items:raise ResolutionFailure('missing-wkt','Empty definition')
    if items[0].upper()=='COORDINATEMETADATA':
        raise ResolutionFailure('deferred-coordinate-epoch','Coordinate metadata wrappers are outside initial scope')
    out=[]
    for i,t in enumerate(items):
        if t.startswith('"'):out.append(t)
        elif t in ('[','('):out.append('[')
        elif t in (']',')'):out.append(']')
        elif t==',':out.append(t)
        elif re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?',t):
            d=Decimal(t)
            n=format(d,'f')
            if '.' in n:n=n.rstrip('0').rstrip('.')
            n=n.lstrip('+')
            if d==0:n='0'
            out.append(n)
        elif i+1<len(items) and items[i+1] in ('[','('):
            out.append(PREFERRED.get(t.upper(),t.upper()))
        else:out.append(ENUM.get(t.lower(),t))
    return ''.join(out)
