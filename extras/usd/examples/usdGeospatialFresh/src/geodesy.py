"""CRS authority, semantic order and operation observations; no scene edits."""
import json, math
import numpy as np
from pyproj import CRS, Transformer, datadir, network
from errors import ResolutionFailure
from wkt import normalize

network.set_network_enabled(False)

def configure_resources(path):
    datadir.append_data_dir(str(path))

def finite(values, name='coordinates'):
    v=np.asarray(values,dtype=np.float64)
    if not np.all(np.isfinite(v)):raise ResolutionFailure('non-finite',name)
    return v

class Definition:
    def __init__(self,text):
        self.authored=text
        self.normal=normalize(text)
        self.warning=None if self.normal==text else 'non-normal-wkt-spelling'
        try:self.crs=CRS.from_wkt(self.normal)
        except Exception as e:raise ResolutionFailure('invalid-wkt',str(e)) from e
        axes=self.crs.axis_info
        self.dimension=len(axes)
        self.directions=[a.direction for a in axes]
        self.units=np.array([a.unit_conversion_factor for a in axes])
        if self.crs.is_geocentric:self.order=self._order(('geocentricX','geocentricY','geocentricZ'));self.kind='geocentric'
        elif self.crs.is_geographic:
            self.order=self._order(('east','north','up'));self.kind='geographic'
        else:
            self.order=self._order(('east','north','up'));self.kind='cartesian'
        if self.dimension not in (2,3):raise ResolutionFailure('unsupported-components',self.directions)
        self.semantic_units=self.units[self.order]
        self.unit_names=[axes[i].unit_name for i in self.order]
        self.geo=self.crs.geodetic_crs
        if self.geo is None:raise ResolutionFailure('unrelated-engineering-crs','No declared geodetic relation')
        self.geo=self.geo.to_3d()
        if self.geo.is_geocentric:
            g=self.geo.to_json_dict();g['type']='GeographicCRS';g.pop('id',None)
            g['coordinate_system']={'subtype':'ellipsoidal','axis':[{'name':'Geodetic longitude','abbreviation':'Lon','direction':'east','unit':'degree'},{'name':'Geodetic latitude','abbreviation':'Lat','direction':'north','unit':'degree'},{'name':'Ellipsoidal height','abbreviation':'h','direction':'up','unit':'metre'}]}
            self.geo=CRS.from_json_dict(g)
        gd=self.geo.to_json_dict()
        gd['type']='GeodeticCRS'
        gd.pop('id',None);gd.pop('scope',None);gd.pop('area',None);gd.pop('bbox',None)
        gd['name']=self.geo.name+' associated geocentric'
        gd['coordinate_system']={'subtype':'Cartesian','axis':[{'name':'Geocentric '+c,'abbreviation':c,'direction':'geocentric'+c,'unit':'metre'} for c in 'XYZ']}
        self.ecef=CRS.from_json_dict(gd)

    def _order(self,directions):
        if any(d not in directions for d in self.directions):
            raise ResolutionFailure('unsupported-components',str(self.directions))
        result=[self.directions.index(d) for d in directions if d in self.directions]
        if len(result)!=len(self.directions) or len(set(self.directions))!=len(self.directions):
            raise ResolutionFailure('ambiguous-components',str(self.directions))
        return result

    def storage(self,v):
        v=finite(v)
        if v.shape[-1]!=self.dimension:raise ResolutionFailure('coordinate-dimension',f'{v.shape[-1]} vs {self.dimension}')
        return v[...,np.argsort(self.order)]

    def semantic(self,v):return np.asarray(v)[...,self.order]

    def equivalent(self,other):
        return self.crs.equals(other.crs,ignore_axis_order=False)

class Operations:
    def __init__(self):self.observations=[];self.cache={}

    def convert(self,values,source,target):
        v=finite(values);one=v.ndim==1
        if one:v=v[None,:]
        if source.dimension!=target.dimension:
            if source.dimension==2 and target.dimension==3:
                raise ResolutionFailure('missing-height','A 2D domain supplies no 3D point')
        key=(source.normal,target.normal)
        if key not in self.cache:
            try:self.cache[key]=Transformer.from_crs(source.crs,target.crs,always_xy=False,allow_ballpark=False,only_best=True)
            except Exception as e:raise ResolutionFailure('unavailable-operation',str(e)) from e
        tr=self.cache[key];p=source.storage(v)
        try:
            columns=tr.transform(*[p[:,i] for i in range(p.shape[1])],errcheck=True)
            out=target.semantic(np.column_stack(columns)[:,:target.dimension]);finite(out)
            last=tr.get_last_used_operation() if tr.description=='unavailable until proj_trans is called' else tr
            terms=[part.lstrip('+') for part in last.definition.split()]
            if any(part=='proj=deformation' or part.partition('=')[0] in ('dx','dy','dz','drx','dry','drz','ds') for part in terms):
                raise ResolutionFailure('deferred-epoch-operation','The selected time-dependent operation requires out-of-scope coordinate-epoch interpretation')
            obs={'source':source.normal,'output':target.normal,'description':last.description,'definition':last.definition,'attributed_accuracy_m':None if last.accuracy<0 else last.accuracy,'network_enabled':False}
            if obs not in self.observations:self.observations.append(obs)
        except Exception as e:
            if isinstance(e,ResolutionFailure):raise
            raise ResolutionFailure('operation-failed',str(e)) from e
        return out[0] if one else out

    def ecef(self,values,definition):return self.convert(values,definition,Definition(definition.ecef.to_wkt()))

def enu_frame(position,definition,ops):
    if definition.dimension!=3:raise ResolutionFailure('missing-height','Model placement requires three axes')
    p=finite(position)
    if definition.kind=='geocentric' and p[0]==0 and p[1]==0:
        raise ResolutionFailure('undetermined-pole-meridian','Geocentric pole does not determine ENU attitude')
    geo=Definition(definition.geo.to_wkt())
    llh=ops.convert(p,definition,geo)
    lon=llh[0]*geo.semantic_units[0];lat=llh[1]*geo.semantic_units[1]
    # CRS coordinate units are converted to radians at this engine-independent boundary.
    sl,cl,sp,cp=math.sin(lon),math.cos(lon),math.sin(lat),math.cos(lat)
    frame=np.array([[-sl,-sp*cl,cp*cl],[cl,-sp*sl,cp*sl],[0,cp,sp]])
    origin=ops.ecef(p,definition)
    return origin,frame
