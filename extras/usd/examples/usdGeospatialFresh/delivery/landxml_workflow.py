"""Explicit authoring conversion to the proposed CF association profile.
Original site-grid numbers/indices retained. LandXML is not a new schema profile.
"""
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import netCDF4
from pxr import Usd,UsdGeom,Sdf
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src_py'));sys.path.insert(0,str(ROOT/'tests'))
from reader import *
from formats import decode,resolve
from test_contract import native
from make_inputs import bind
F=ROOT/'inputs/authored';E=ROOT/'evidence';O=ROOT/'inputs/original/Colorado'
doc=ET.parse(O/'Trimble Westminster Park and Ride LandXML.xml');ns={'l':'http://www.landxml.org/schema/LandXML-1.2'}
nodes=doc.findall('.//l:Breakline/l:PntList3D',ns);raw=[];ids=[]
for line,node in enumerate(nodes):
    points=np.array([float(v) for v in node.text.split()]).reshape(-1,3)
    for index,point in enumerate(points):raw.append(point[[1,0,2]]);ids.append(f'breakline{line}/point{index}')
raw=np.array(raw) # LandXML north/east/height to semantic E/N/up.
source=(O/'03_Westminster_Site_Calibration_WKT2.txt').read_text();cr=definition(source)
with netCDF4.Dataset(F/'westminster.cf.nc','w') as n:
    n.Conventions='CF-1.12';n.comment='Derived association copy of Trimble LandXML design breaklines. Original site coordinates and breakline/point indices retained. No resampling or invented triangulation.';n.createDimension('point',len(raw))
    mapping=n.createVariable('site_crs','i4');mapping.crs_wkt=source
    for i,(name,standard) in enumerate([('easting','projection_x_coordinate'),('northing','projection_y_coordinate'),('height',None)]):
        v=n.createVariable(name,'f8',('point',));v.units='0.304800609601219 m';v[:]=raw[:,i]
        if standard:v.standard_name=standard
        else:v.axis='Z';v.positive='up';v.long_name='Site-calibrated vertical ordinate, reference defined by crs_wkt'
    v=n.createVariable('source_height','f8',('point',));v.grid_mapping='site_crs';v.coordinates='easting northing height';v.units='0.304800609601219 m';v[:]=raw[:,2]
    pid=n.createVariable('point_id',str,('point',));pid[:]=np.array(ids,dtype=object)
s=Usd.Stage.CreateNew(str(F/'westminster.usda'));UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.SetStageUpAxis(s,'Z')
p=bind(s,'/Site',normalize_wkt(source),typ='GeospatialDataSource');s.SetDefaultPrim(p)
for name,typ,val in [('asset',Sdf.ValueTypeNames.Asset,Sdf.AssetPath('westminster.cf.nc')),('format',Sdf.ValueTypeNames.Token,'CF'),('field',Sdf.ValueTypeNames.String,'source_height'),('coordinateDomain',Sdf.ValueTypeNames.String,'site_crs')]:p.CreateAttribute('data:'+name,typ,custom=False,variability=Sdf.VariabilityUniform).Set(val)
publish_claim(p,True);s.GetRootLayer().Save();decoded=decode(p);file=E/'Westminster-decoded.json';file.write_text(json.dumps(decoded));output=cr.geocentric.wkt
r=Reader(s,output);py=resolve(r,p,decoded);cpp=native(F/'westminster.usda',[{'prim':'/Site','kind':'measurement','decoded':str(file)}],output=output,tag='westminster');assert cpp['results'][0]['success'],cpp
actual=np.array([row['resolved_coordinates'] for row in cpp['results'][0]['samples']]);other=np.array([row['resolved_coordinates'] for row in py['samples']]);error=np.linalg.norm(actual-other,axis=1);assert error.max()<.0001
assert np.array_equal(np.array([row['coordinates'] for row in decoded['samples']]),raw)
(E/'Westminster-resolved.json').write_text(json.dumps(py));(E/'westminster-proof.json').write_text(json.dumps({'points':len(raw),'source_ids':ids,'max_reader_distance_m':float(error.max()),'original_coordinate_values_unchanged':True,'original_file_unchanged':True,'association':'Explicit derived CF copy, not native LandXML support','operations':r.engine.operations},indent=2));print('Westminster original design-breakline positions:',len(raw),'max reader distance (m):',error.max())
