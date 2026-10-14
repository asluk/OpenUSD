"""New writer examples from original bytes and explicit producer facts."""
from pathlib import Path
import sys,json,xml.etree.ElementTree as ET
import numpy as np
from pxr import Gf,Sdf,Usd,UsdGeom
from pyproj import CRS
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
from fixtures import stage,bind,wkt,measurement,cf_dataset
from profiles import declare
from wkt import normalize

def make():
 d=ROOT/'fixtures';d.mkdir(exist_ok=True)
 # Retain the original third component separately. This declared supplement is
 # horizontal-only, because the original railway's vertical reference is unknown.
 original=json.loads((ROOT/'data/railway.geojson').read_text(encoding='utf-8'))
 def horizontal(x):
  if x and isinstance(x[0],(int,float)):return x[:2]
  return [horizontal(v) for v in x]
 for f in original['features']:f['geometry']['coordinates']=horizontal(f['geometry']['coordinates'])
 rail=d/'railway-horizontal.geojson';rail.write_text(json.dumps(original),encoding='utf-8')
 s=stage(d/'railway.usda');measurement(s,'/World/Railway',rail,'GeoJSON','','geometry',wkt(4326));declare(s.GetDefaultPrim(),True,True);s.GetRootLayer().Save()
 # LandXML gives north/east/height in US survey feet. This is an explicit writer
 # conversion into a CF association, not an extra runtime data:format.
 xml=ET.parse(ROOT/'data/Colorado/Trimble Westminster Park and Ride LandXML.xml');ns={'l':'http://www.landxml.org/schema/LandXML-1.2'}
 blocks=[np.fromstring(p.text,sep=' ').reshape(-1,3)[:,[1,0,2]] for p in xml.findall('.//l:PntList3D',ns)]
 coords=np.concatenate(blocks);starts=np.cumsum([0]+[len(p) for p in blocks]);np.savez(d/'landxml-domains.npz',coordinates=coords,starts=starts)
 site=(ROOT/'data/Colorado/03_Westminster_Site_Calibration_WKT2.txt').read_text()
 # Eiffel writer conformance is ordinary USD. Dataset provenance acknowledges
 # the asset's cm metadata is inconsistent with its metre-sized mesh.
 s=stage(d/'tower-source.usda');bind(s,'/World/Site',wkt(4979),(2.2945,48.8584,80))
 a=bind(s,'/World/Site/Tower',wkt(4979),(2.2945,48.8584,80),(30,0,0));UsdGeom.Xformable(a).AddTranslateOp().Set((35,15,0))
 conform=UsdGeom.Xform.Define(s,'/World/Site/Tower/WriterConformance');conform.AddRotateXOp().Set(90)
 conform.AddScaleOp(opSuffix='declaredCentimetres').Set((.01,.01,.01));conform.AddScaleOp(opSuffix='documentedUnitCorrection').Set((100,100,100))
 asset=s.DefinePrim(str(conform.GetPath())+'/Asset');asset.GetReferences().AddReference('../data/tower.usdz')
 declare(s.GetDefaultPrim(),True,True);s.GetRootLayer().Save()
 # Original climate bytes remain untouched; successful counterpart is synthetic.
 cf_dataset(d/'global-native.nc')
 s=stage(d/'climate.usda');measurement(s,'/World/Climate',d/'global-native.nc','CF','temperature','earth',wkt(4979));declare(s.GetDefaultPrim(),True,True);s.GetRootLayer().Save()
 import rasterio
 from rasterio.transform import from_origin
 y,x=np.indices((48,64));value=(15+18*np.exp(-((x-39)**2+(y-23)**2)/180)+2*np.sin(x/5)).astype('float32')
 value[2:6,3:9]=-9999
 with rasterio.open(d/'city-heat.tif','w',driver='GTiff',height=48,width=64,count=1,dtype='float32',crs='EPSG:2154',transform=from_origin(652000,6863000,10,10),nodata=-9999) as ds:ds.write(value,1);ds.set_band_unit(1,'degrees C')
 s=stage(d/'city.usda');measurement(s,'/World/Heat',d/'city-heat.tif','GeoTIFF','1','0',wkt(2154));declare(s.GetDefaultPrim(),True,True);s.GetRootLayer().Save()
 facts={'railway':'Explicit 2D derivative: no claimed height reference','landxml':{'vertices':len(coords),'parts':len(blocks),'native_tuple':'north/east/height','writer_mapping':'east/north/height','units':'US survey foot'},'eiffel':{'author_position':[2.2945,48.8584,80],'author_heading_pitch_roll_degrees':[30,0,0],'ordinary_adjustment_metres':[35,15,0],'writer_unit_correction':'Declared cm conformance multiplied by producer-known factor 100; no geospatial correction attribute','scene':'Illustrative Paris placement; no surveyed-site claim'},'climate':'Synthetic CF-1.12 fixture, not repaired original','city':'Synthetic 2D heat field; no terrain-height assumption'}
 (d/'writer-facts.json').write_text(json.dumps(facts,indent=2),encoding='utf-8');print(json.dumps(facts))
if __name__=='__main__':make()
