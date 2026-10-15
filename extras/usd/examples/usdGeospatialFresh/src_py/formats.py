"""Native-format decoding shared as transport by the two placement readers.

Returns raw semantic tuples with original sample identity, never resolves CRS.
The descriptor is runtime data, not a new authored USD property.
"""
import json
import re
from pathlib import Path
import numpy as np
from pyproj import CRS
from pxr import Sdf
from reader import read_attr,require,ResolutionError,crs_for,nearest,row_transform


def equivalent(a,b):
    return a.equals(b,ignore_axis_order=False)


def decode(prim):
    asset=read_attr(prim,'data:asset','asset',uniform=True)
    path=asset.resolvedPath
    if not path:
        attr=prim.GetAttribute('data:asset')
        layers=attr.GetPropertyStack()
        require(bool(layers),'Unresolved dataset asset')
        path=Sdf.ComputeAssetPathRelativeToLayer(layers[0].layer,asset.path)
    fmt=str(read_attr(prim,'data:format','token',uniform=True))
    field=str(read_attr(prim,'data:field','string',uniform=True))
    domain=str(read_attr(prim,'data:coordinateDomain','string',uniform=True))
    source=crs_for(prim)
    require(prim.GetTypeName()=='GeospatialDataSource','External data needs declared carrier type')
    rows=[]
    if fmt=='GeoJSON':
        require(domain=='geometry','Unsupported GeoJSON domain')
        doc=json.loads(Path(path).read_text(encoding='utf-8-sig'))
        if 'crs' in doc:
            legacy=doc['crs'];require(legacy.get('type')=='name','Unsupported legacy GeoJSON declaration')
            declared=CRS.from_user_input(legacy.get('properties',{}).get('name',''))
            require(declared.equals(CRS.from_epsg(4326),ignore_axis_order=True),
                    'Legacy GeoJSON with another CRS unsupported')
        embedded=CRS.from_epsg(4979 if source.dimension==3 else 4326)
        # RFC7946 defines lon/lat irrespective of EPSG storage axis order.
        require(source.crs.equals(embedded,ignore_axis_order=True),'GeoJSON/WKT CRS conflict')
        def walk(coords,prefix):
            if coords and isinstance(coords[0],(int,float)):
                require(len(coords)==source.dimension,'GeoJSON height dimensionality mismatch')
                yield prefix,coords
            else:
                for i,c in enumerate(coords):yield from walk(c,prefix+[i])
        for fi,feature in enumerate(doc['features']):
            require(not field or field in feature.get('properties',{}),'Missing feature field')
            geom=feature['geometry'];require(geom and 'coordinates' in geom,'Unsupported GeoJSON geometry')
            for gi,p in walk(geom['coordinates'],[]):
                rows.append({'index':[fi]+gi,'coordinates':p,'value':feature['properties'][field] if field else None,'mask':False,'observation_time':None})
    elif fmt=='CF':
        import netCDF4
        with netCDF4.Dataset(path) as ds:
            require(field in ds.variables and domain in ds.variables,'Missing CF field/domain')
            v=ds[field];mapping=getattr(v,'grid_mapping','')
            require(domain in re.findall(r'[A-Za-z_][\w]*',mapping),'Field/domain grid_mapping mismatch')
            crsvar=ds[domain];embedded=getattr(crsvar,'crs_wkt',None)
            if embedded is None:
                try:embedded=CRS.from_cf({k:crsvar.getncattr(k) for k in crsvar.ncattrs()}).to_wkt()
                except Exception as e:raise ResolutionError('CF CRS declaration unavailable') from e
            require(equivalent(CRS.from_wkt(embedded),source.crs),'CF/WKT CRS conflict')
            explicit=set(getattr(v,'coordinates','').split())
            require(all(name in ds.variables for name in explicit),'Missing CF coordinate variable')
            names={name for name in v.dimensions if name in ds.variables}|explicit
            # Expanded mapping explicitly associates the coordinates of a domain.
            if ':' in mapping:
                parts=re.split(r'(\w+)\s*:',mapping);selected=[]
                for i in range(1,len(parts),2):
                    if parts[i]==domain:selected=parts[i+1].split()
                require(bool(selected),'Missing expanded CF mapping association')
                names=set(selected)|set(v.dimensions)
            roles={};timevar=None
            for name in names:
                require(name in ds.variables,'Missing CF coordinate variable')
                c=ds[name];standard=getattr(c,'standard_name','');units=getattr(c,'units','')
                role={'longitude':'east','latitude':'north','projection_x_coordinate':'east',
                      'projection_y_coordinate':'north','height_above_reference_ellipsoid':'up',
                      'altitude':'up'}.get(standard)
                if role is None and getattr(c,'axis','')=='Z' and getattr(c,'positive','')=='up':
                    # A custom vertical reference comes from crs_wkt. Do not
                    # falsely label a site-calibrated ordinate as geoid altitude.
                    role='up'
                if standard=='time':timevar=c
                if role:
                    require(role not in roles,'Ambiguous CF coordinate role')
                    require(all(d in v.dimensions for d in c.dimensions),'Coordinate dimensions do not cover selected field')
                    roles[role]=c
            expected=source.semantic
            require(set(roles)==set(expected),'Missing or unsupported CF coordinate roles, including height')
            for role,c in roles.items():
                require(all(ds.dimensions[d].size==v.shape[v.dimensions.index(d)] for d in c.dimensions),'CF dimension extent mismatch')
                u=getattr(c,'units','')
                declared=source.units[expected.index(role)]
                if role in ('east','north') and source.geo:
                    require(u in ('degrees_east','degrees_north','degree_east','degree_north') and abs(declared-np.pi/180)<1e-14,'CF angular units conflict')
                else:
                    # CF permits UDUNITS scaled unit expressions. This decoder's
                    # supported length subset includes metre, foot and N m.
                    scaled=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s+m',u)
                    factor=1 if u in ('m','metre','meter') else .3048 if u in ('ft','foot') else float(scaled[1]) if scaled else None
                    require(factor is not None and abs(declared-factor)<1e-14,'CF length units conflict or unsupported unit expression')
            values=v[:]
            for index in np.ndindex(v.shape):
                def at(c):
                    sub=tuple(index[v.dimensions.index(d)] for d in c.dimensions)
                    return c[sub].item()
                coordinate=[at(roles[r]) for r in expected]
                require(np.isfinite(coordinate).all(),'Unavailable CF coordinate')
                masked=bool(np.ma.getmaskarray(values)[index])
                tv=None
                if timevar is not None:
                    tv={'value':at(timevar),'units':timevar.units,'calendar':getattr(timevar,'calendar','standard')}
                rows.append({'index':list(index),'coordinates':coordinate,'value':None if masked else values[index].item(),'mask':masked,'observation_time':tv})
    elif fmt=='GeoTIFF':
        import rasterio
        require(re.fullmatch(r'[1-9]\d*',field) and re.fullmatch(r'0|[1-9]\d*',domain),'Noncanonical TIFF selection')
        require(domain=='0','This decoder does not support additional TIFF IFDs')
        with rasterio.open(path) as ds:
            require(ds.crs is not None and equivalent(CRS(ds.crs),source.crs),'GeoTIFF/WKT CRS conflict')
            require(source.dimension==2,'Raster supplies no height coordinate')
            band=int(field);require(band<=ds.count,'Missing TIFF band');v=ds.read(band,masked=True)
            for row,col in np.ndindex(v.shape):
                # GDAL/rasterio normalizes RasterPixelIsPoint tiepoint placement.
                x,y=ds.xy(row,col,offset='center');masked=bool(np.ma.getmaskarray(v)[row,col])
                rows.append({'index':[row,col],'coordinates':[x,y],'value':None if masked else v[row,col].item(),'mask':masked,'observation_time':None})
    else:raise ResolutionError('Unsupported association profile: '+fmt)
    return {'asset':str(Path(path).resolve()),'format':fmt,'field':field,'domain':domain,'source_crs':source.wkt,'samples':rows}


def resolve(reader,prim,decoded=None):
    reader.validate_roles(prim,prim)
    raw=decode(prim) if decoded is None else decoded
    source=crs_for(prim);parent=nearest(prim.GetParent());work=crs_for(parent) if parent else source
    coordinates=np.array([r['coordinates'] for r in raw['samples']],dtype=float)
    points=reader.engine.transform(source,work,coordinates)
    points=reader.adjust(work,points,reader.local(prim))
    output=reader.engine.transform(work,reader.output,points)
    return {**raw,'samples':[{**s,'resolved_coordinates':p.tolist()} for s,p in zip(raw['samples'],output)]}
