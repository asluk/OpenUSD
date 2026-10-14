"""Native associations use declared roles and named dimensions, never name guesses."""
from pathlib import Path
import json,re
import numpy as np
from pxr import Sdf,UsdGeom
from errors import ResolutionFailure
from geodesy import Definition,Operations,finite
from scene import uniform,direct,definition,placement_fields_valid,local,transform,stage_mapping,chain,timecode

def association(prim):
    if prim.GetTypeName()!='GeospatialDataSource' or not direct(prim):raise ResolutionFailure('invalid-measurement-role',str(prim.GetPath()))
    placement_fields_valid(prim)
    asset=uniform(prim,'data:asset',Sdf.ValueTypeNames.Asset)
    path=asset.resolvedPath
    if not path:raise ResolutionFailure('unresolved-asset',asset.path)
    fmt=str(uniform(prim,'data:format',Sdf.ValueTypeNames.Token))
    field=str(uniform(prim,'data:field',Sdf.ValueTypeNames.String))
    domain=str(uniform(prim,'data:coordinateDomain',Sdf.ValueTypeNames.String))
    if not field and fmt!='GeoJSON':raise ResolutionFailure('missing-field','Only GeoJSON geometry-only permits an empty field')
    if not domain:raise ResolutionFailure('missing-domain','Empty coordinate domain')
    return Path(path),fmt,field,domain,definition(prim)

def align(values,dims,field_dims,shape):
    if len(set(dims))!=len(dims) or any(d not in field_dims for d in dims):
        raise ResolutionFailure('coordinate-dimensions',str(dims))
    ordered=[d for d in field_dims if d in dims]
    a=np.asarray(values)
    if dims:a=np.transpose(a,[dims.index(d) for d in ordered])
    target=[shape[field_dims.index(d)] if d in dims else 1 for d in field_dims]
    try:return np.broadcast_to(a.reshape(target),shape)
    except ValueError as e:raise ResolutionFailure('coordinate-dimensions','Coordinate does not cover selected sample domain') from e

def cf(path,field_name,domain_name,crs):
    import netCDF4
    with netCDF4.Dataset(path) as ds:
        if field_name not in ds.variables or domain_name not in ds.variables:
            raise ResolutionFailure('missing-native-association','CF variable or mapping unavailable')
        f=ds[field_name];mapping=str(getattr(f,'grid_mapping',''))
        coordinate_names=str(getattr(f,'coordinates','')).split()
        if ':' in mapping:
            choices=re.findall(r'([^\s:]+)\s*:\s*([^:]+?)(?=\s+[^\s:]+\s*:|$)',mapping)
            selected=[c.split() for m,c in choices if m==domain_name]
            if len(selected)!=1:raise ResolutionFailure('ambiguous-grid-mapping',mapping)
            coordinate_names=selected[0]
        elif mapping!=domain_name:raise ResolutionFailure('grid-mapping-selection',mapping)
        gm=ds[domain_name]
        embedded=getattr(gm,'crs_wkt',getattr(gm,'spatial_ref',None))
        if not embedded:
            from pyproj import CRS
            try:embedded=CRS.from_cf({a:gm.getncattr(a) for a in gm.ncattrs()}).to_wkt()
            except Exception as e:raise ResolutionFailure('unsupported-native-cf-declaration',str(e)) from e
        embedded_crs=Definition(str(embedded))
        if not crs.equivalent(embedded_crs):raise ResolutionFailure('native-crs-conflict','CF and composed WKT disagree')
        candidates=list(dict.fromkeys(coordinate_names+[d for d in f.dimensions if d in ds.variables]))
        roles={};times=[]
        for name in candidates:
            if name not in ds.variables:raise ResolutionFailure('missing-coordinate',name)
            var=ds[name];std=str(getattr(var,'standard_name',''));units=str(getattr(var,'units',''))
            role={'longitude':'east','latitude':'north','projection_x_coordinate':'east','projection_y_coordinate':'north','height_above_reference_ellipsoid':'up','altitude':'up','time':'time'}.get(std)
            if role is None:continue
            if role=='up':
                vertical_axes=[a for a in crs.crs.axis_info if a.direction=='up']
                ellipsoidal=bool(vertical_axes and 'ellipsoid' in vertical_axes[0].name.lower())
                if (std=='height_above_reference_ellipsoid')!=ellipsoidal:
                    raise ResolutionFailure('native-height-reference-conflict','CF vertical role and WKT height reference disagree')
            a=align(var[:],tuple(var.dimensions),tuple(f.dimensions),f.shape)
            if role=='time':
                if ' since ' not in units:raise ResolutionFailure('observation-time-units',units)
                times.append({'name':name,'values':a.reshape(-1).tolist(),'units':units,'calendar':str(getattr(var,'calendar','standard'))})
                continue
            if role in roles:raise ResolutionFailure('ambiguous-coordinate-role',role)
            factor={'degrees_east':np.pi/180,'degree_east':np.pi/180,'degrees_north':np.pi/180,'degree_north':np.pi/180,'degrees':np.pi/180,'degree':np.pi/180,'radian':1,'radians':1,'m':1,'metre':1,'meter':1,'ft':.3048,'US_survey_foot':1200/3937}.get(units)
            if factor is None:raise ResolutionFailure('unsupported-coordinate-unit',units)
            index=('east','north','up').index(role)
            roles[role]=np.asarray(a,dtype=float)*factor/crs.semantic_units[index]
        names=['east','north']+(['up'] if crs.dimension==3 else [])
        if any(n not in roles for n in names):raise ResolutionFailure('missing-coordinate-role',str(names))
        values=np.ma.asarray(f[:]);mask=np.ma.getmaskarray(values)
        coords=np.column_stack([roles[n].reshape(-1) for n in names])
        measurement=np.asarray(values.filled(np.nan)).reshape(-1)
        mask=mask.reshape(-1)|~np.isfinite(measurement)
        if np.any(~np.isfinite(coords[~mask])):raise ResolutionFailure('non-finite-native-coordinate','An unmasked sample has unavailable coordinates')
        return {'coordinates':coords,'values':measurement,'mask':mask,'indices':np.indices(f.shape).reshape(len(f.shape),-1).T.tolist(),'dimension_names':list(f.dimensions),'observation_times':times,'value_units':str(getattr(f,'units','unknown'))}

def geojson(path,field,domain,crs):
    if domain!='geometry':raise ResolutionFailure('geojson-domain',domain)
    data=json.loads(path.read_text(encoding='utf-8'))
    legacy=data.get('crs',{}).get('properties',{}).get('name','')
    allowed_legacy=r'(?:EPSG:4326|OGC:CRS84|urn:ogc:def:crs:EPSG:[0-9.]*:4326|urn:ogc:def:crs:OGC:[0-9.]*:CRS84|https?://www\.opengis\.net/def/crs/(?:EPSG/[0-9.]+/4326|OGC/[0-9.]+/CRS84))'
    if legacy and not re.fullmatch(allowed_legacy,legacy,re.IGNORECASE):
        raise ResolutionFailure('unsupported-legacy-geojson-crs',legacy)
    from pyproj import CRS
    expected=Definition(CRS.from_user_input('OGC:CRS84').to_wkt())
    if crs.dimension==3:expected=Definition(expected.crs.to_3d().to_wkt())
    if not crs.crs.equals(expected.crs,ignore_axis_order=True):raise ResolutionFailure('native-crs-conflict','RFC 7946 and composed WKT disagree after its longitude/latitude mapping')
    coords=[];values=[];indices=[]
    def walk(g,feature,path_parts,value):
        if g is None:return
        if g['type']=='GeometryCollection':
            for i,x in enumerate(g['geometries']):walk(x,feature,path_parts+[i],value)
            return
        def visit(c,index):
            if c and isinstance(c[0],(int,float)):
                if len(c)!=crs.dimension:raise ResolutionFailure('native-coordinate-dimension',str(len(c)))
                coords.append(c);values.append(value);indices.append([feature]+path_parts+index)
            else:
                for i,x in enumerate(c):visit(x,index+[i])
        visit(g['coordinates'],[])
    for i,f in enumerate(data.get('features',[])):
        if field and field not in f.get('properties',{}):raise ResolutionFailure('missing-feature-property',field)
        walk(f.get('geometry'),i,[],f.get('properties',{}).get(field) if field else None)
    return {'coordinates':finite(coords),'values':values,'mask':np.zeros(len(coords),bool),'indices':indices,'observation_times':[],'value_units':'native'}

def geotiff(path,field,domain,crs):
    import rasterio
    if not re.fullmatch(r'[1-9][0-9]*',field) or not re.fullmatch(r'0|[1-9][0-9]*',domain):
        raise ResolutionFailure('geotiff-selection','Use canonical decimal band and IFD')
    if domain!='0':raise ResolutionFailure('unsupported-ifd','This decoder exposes the root IFD only')
    if crs.dimension!=2:raise ResolutionFailure('missing-height','A two-axis raster mapping supplies no height')
    with rasterio.open(path) as ds:
        if not ds.crs:raise ResolutionFailure('missing-native-crs','GeoTIFF CRS unavailable')
        embedded=Definition(CRS_from_raster(ds.crs))
        if not crs.crs.equals(embedded.crs,ignore_axis_order=True):raise ResolutionFailure('native-crs-conflict','GeoTIFF disagrees after its raster axis mapping')
        a=ds.read(int(field),masked=True);row,col=np.indices(a.shape)
        x,y=rasterio.transform.xy(ds.transform,row.reshape(-1),col.reshape(-1),offset='center')
        return {'coordinates':np.column_stack([x,y]),'values':np.asarray(a.filled(np.nan)).reshape(-1),'mask':np.ma.getmaskarray(a).reshape(-1),'indices':np.column_stack([row.reshape(-1),col.reshape(-1)]).tolist(),'observation_times':[],'value_units':ds.units[int(field)-1] or 'unknown'}

def CRS_from_raster(crs):
    from pyproj import CRS
    return CRS.from_wkt(crs.to_wkt()).to_wkt()

def resolve(prim,output,time=None):
    path,fmt,field,domain,source=association(prim)
    loaders={'CF':cf,'GeoJSON':geojson,'GeoTIFF':geotiff}
    if fmt not in loaders:raise ResolutionFailure('unsupported-format',fmt)
    data=loaders[fmt](path,field,domain,source)
    q=output if isinstance(output,Definition) else Definition(output)
    working=next((definition(p) for p in list(chain(prim))[1:] if direct(p)),source)
    a=local(prim,time);ops=Operations();coords=data['coordinates']
    valid=~np.asarray(data['mask']);result=np.full((len(coords),q.dimension),np.nan)
    if not np.array_equal(a,np.eye(4)):
        if working.kind=='geographic':raise ResolutionFailure('missing-cartesian-working-context','Absolute geographic adjustment has no explicit Cartesian chart')
        w=ops.convert(coords[valid],source,working)
        mapping,unit=stage_mapping(prim.GetStage())
        if source.dimension==2:
            chart_matrix=np.eye(4);chart_matrix[:3,:3]=mapping.T
            enu_matrix=chart_matrix@a@np.linalg.inv(chart_matrix)
            if not np.allclose(enu_matrix[[0,1],2],0) or not np.allclose(enu_matrix[2,[0,1]],0) or enu_matrix[3,2]!=0:
                raise ResolutionFailure('out-of-plane-adjustment','2D coordinates cannot supply height')
            enu=np.column_stack([w*working.semantic_units,np.zeros(len(w))])
            v=enu@mapping.T/unit
            shifted=(transform(v,a)@mapping)[:,:2]*unit/working.semantic_units
        else:
            stage_values=(w*working.semantic_units)@mapping.T/unit
            shifted=(transform(stage_values,a)@mapping)*unit/working.semantic_units
        result[valid]=ops.convert(shifted,working,q)
    else:result[valid]=ops.convert(coords[valid],source,q)
    data['coordinates']=result;data['operations']=ops.observations;data['coordinate_wkt']=q.normal
    return data
