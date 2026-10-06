"""External associations, retaining native indices, values, masks and times."""
from pathlib import Path
import json, hashlib, re
import numpy as np
from pxr import Ar, Sdf
from pyproj import CRS
from .runtime import ContractError,definition

def required(prim,name,kind):
    a=prim.GetAttribute(name)
    if not a or a.GetTypeName()!=kind or a.GetVariability()!=Sdf.VariabilityUniform or a.Get() is None:
        raise ContractError('Missing or invalid external association '+name)
    return a.Get()

def equivalent(a,b):
    if not a.equals(b,ignore_axis_order=False): raise ContractError('External CRS conflicts with composed WKT')

def read_source(prim):
    if prim.GetTypeName()!='GeospatialDataSource': raise ContractError('No explicit external coordinate role')
    if any(prim.HasAttribute(n) and prim.GetAttribute(n).HasAuthoredValueOpinion() for n in ['crs:position','crs:orientation','crs:scale','xformOpOrder']):
        raise ContractError('Absolute measurement source cannot have model placement')
    asset=required(prim,'data:asset',Sdf.ValueTypeNames.Asset)
    profile=required(prim,'data:format',Sdf.ValueTypeNames.Token)
    field=required(prim,'data:field',Sdf.ValueTypeNames.String)
    domain=required(prim,'data:coordinateDomain',Sdf.ValueTypeNames.String)
    path=Path(asset.resolvedPath)
    if not asset.resolvedPath or not path.is_file(): raise ContractError('Dataset asset unavailable')
    _,crs=definition(prim)
    common={'asset':asset.path,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'field':field,'domain':domain,'profile':profile,'crs':crs}
    if profile=='CF':
        from netCDF4 import Dataset
        with Dataset(path) as nc:
            if field not in nc.variables or domain not in nc.variables: raise ContractError('Selected CF field/domain unavailable')
            v=nc[field];mapping=getattr(v,'grid_mapping','')
            selections={}
            if ':' in mapping:
                matches=list(re.finditer(r'(\S+)\s*:',mapping))
                for i,m in enumerate(matches):
                    end=matches[i+1].start() if i+1<len(matches) else len(mapping)
                    if m.group(1) in selections: raise ContractError('Ambiguous repeated CF coordinate domain')
                    selections[m.group(1)]=mapping[m.end():end].split()
                if domain not in selections: raise ContractError('Selected CF domain is not associated with field')
            elif mapping!=domain: raise ContractError('Selected CF domain is not associated with field')
            gm=nc[domain]
            embedded=getattr(gm,'crs_wkt',None)
            if not embedded: raise ContractError('CF association requires complete external CRS WKT in this adapter')
            external=CRS.from_wkt(embedded);equivalent(crs,external)
            # Where CF also supplies the projection, require mutual consistency.
            cfattrs={k:gm.getncattr(k) for k in gm.ncattrs() if k!='crs_wkt'}
            if 'grid_mapping_name' in cfattrs:
                try:
                    cf_crs=CRS.from_cf(cfattrs)
                    if not cf_crs.equals(external,ignore_axis_order=True): raise ContractError('CF/WKT projection metadata conflict')
                except Exception as e: raise ContractError('CF/WKT projection metadata conflict or unsupported definition') from e
            coordinate_names=selections.get(domain,str(getattr(v,'coordinates','')).split())
            # The observation-time association belongs to the field, independent of selected spatial mapping.
            for name in str(getattr(v,'coordinates','')).split():
                if name in nc.variables and getattr(nc[name],'standard_name','')=='time' and name not in coordinate_names: coordinate_names.append(name)
            roles={};times={}
            for name in coordinate_names:
                if name not in nc.variables: raise ContractError('CF associated coordinate missing')
                coord=nc[name];role=getattr(coord,'standard_name','')
                if role=='time': times[name]={'values':np.asarray(coord[:]).tolist(),'units':getattr(coord,'units',None),'calendar':getattr(coord,'calendar','standard')};continue
                if role not in ['longitude','latitude','projection_x_coordinate','projection_y_coordinate','height_above_reference_ellipsoid']: raise ContractError('Unsupported CF coordinate role; no inferred height')
                roles[role]=coord
            names=['longitude','latitude'] if crs.is_geographic else ['projection_x_coordinate','projection_y_coordinate']
            if len(crs.axis_info)==3: names+=['height_above_reference_ellipsoid']
            from .runtime import factors
            coords=[]
            for i,name in enumerate(names):
                if name not in roles: raise ContractError('Missing coordinate or height')
                coord=roles[name];units=getattr(coord,'units',None)
                factors_by_unit={'m':1.,'metre':1.,'km':1000.,'degrees_east':np.pi/180,'degrees_north':np.pi/180,'degree':np.pi/180,'radian':1.}
                if units not in factors_by_unit: raise ContractError('Missing/unsupported CF coordinate units')
                angular=name in ['longitude','latitude']
                if angular!=(units in ['degrees_east','degrees_north','degree','radian']):raise ContractError('CF coordinate unit has the wrong physical dimension')
                data=np.asarray(coord[:],float)
                # Coordinates must share the field's sample domain or be its one-dimensional dimension coordinates.
                shape=[1]*v.ndim
                for j,d in enumerate(coord.dimensions):
                    if d not in v.dimensions: raise ContractError('Coordinate does not cover selected field domain')
                    shape[v.dimensions.index(d)]=data.shape[j]
                data=np.broadcast_to(data.reshape(shape),v.shape).reshape(-1)
                coords.append(data*factors_by_unit[units]/factors(crs)[i])
            values=np.ma.asarray(v[:]);mask=np.ma.getmaskarray(values).reshape(-1)
            return {**common,'coordinates':np.stack(coords,axis=-1),'values':np.asarray(values.filled(np.nan)).reshape(-1),'mask':mask,'indices':np.arange(values.size),'times':times,'measurement_units':getattr(v,'units',None),'shape':list(v.shape)}
    if profile=='GeoTIFF':
        import rasterio
        if domain!='0' or not field.isdecimal() or int(field)<1: raise ContractError('Only IFD zero and explicit one-based band supported')
        with rasterio.open(path) as ds:
            if ds.subdatasets: raise ContractError('Multi-IFD selection unavailable in this adapter')
            if not ds.crs: raise ContractError('Raster CRS unavailable')
            # Raster CRS WKT often has opposite official geographic order; fix using the format-defined tuple convention, then compare.
            external=CRS.from_wkt(ds.crs.to_wkt())
            if not crs.equals(external,ignore_axis_order=True): raise ContractError('External CRS conflicts with composed WKT')
            if len(crs.axis_info)!=2: raise ContractError('Raster supplies no independent height')
            band=int(field)
            if band>ds.count: raise ContractError('Selected raster band unavailable')
            values=ds.read(band,masked=True);rows,cols=np.indices(values.shape)
            x,y=rasterio.transform.xy(ds.transform,rows.reshape(-1),cols.reshape(-1),offset='center')
            return {**common,'coordinates':np.stack([x,y],axis=-1),'values':np.asarray(values.filled(np.nan)).reshape(-1),'mask':np.ma.getmaskarray(values).reshape(-1),'indices':np.arange(values.size),'times':{},'shape':list(values.shape),'raster_type':ds.tags().get('AREA_OR_POINT','Area'),'transform':list(ds.transform)}
    if profile=='GeoJSON':
        data=json.loads(path.read_text(encoding='utf-8'))
        if domain!='geometry' or 'crs' in data: raise ContractError('Legacy GeoJSON CRS metadata is not RFC7946; height meaning is not assumed')
        dimension=len(crs.axis_info);expected=CRS.from_user_input('OGC:CRS84' if dimension==2 else 'OGC:CRS84h')
        if not crs.equals(expected,ignore_axis_order=True): raise ContractError('GeoJSON CRS conflicts with composed WKT')
        coords=[];values=[];index=[]
        def visit(a,feature,trail,val):
            if isinstance(a,list) and a and isinstance(a[0],(float,int)):
                if len(a)!=dimension: raise ContractError('GeoJSON coordinate dimensionality or height missing')
                coords.append(a);values.append(val);index.append([feature,*trail]);return
            for i,x in enumerate(a):visit(x,feature,[*trail,i],val)
        for i,f in enumerate(data.get('features',[])):
            if field and field not in f.get('properties',{}): raise ContractError('Feature measurement property unavailable')
            visit(f['geometry']['coordinates'],i,[],f.get('properties',{}).get(field) if field else None)
        return {**common,'coordinates':np.array(coords),'values':values,'mask':[False]*len(coords),'indices':index,'times':{},'shape':[len(coords)]}
    raise ContractError('Unsupported format profile')

def resolved(prim,runtime):
    record=read_source(prim)
    points=runtime.convert(record['crs'],runtime.output,record['coordinates'])
    return record,points
