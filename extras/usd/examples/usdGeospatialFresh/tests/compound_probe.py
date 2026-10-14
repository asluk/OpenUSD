from pathlib import Path
import sys,json,numpy as np,csv
from pxr import UsdGeom
from pyproj import CRS
from pyproj.crs import CompoundCRS
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT/'src'))
from fixtures import stage,bind,wkt
from wkt import normalize
from geodesy import configure_resources
from scene import Reader
from run_workflows import native,dump
configure_resources(ROOT.parent/'geospatial-model-resources')
provider=CRS.from_wkt((ROOT/'data/France/01_RGF93v2b_CC49_IGN69_WKT2.txt').read_text());geog=CRS.from_wkt((ROOT/'data/France/04_RGF93v2b_Geographic3D_WKT2.txt').read_text()).to_2d();compound=CompoundCRS('RGF93v2b geographic + IGN69',[geog,provider.sub_crs_list[1]])
g=list(csv.DictReader((ROOT/'data/France/04_RGF93v2b_Geographic3D_Coordinates.csv').open()))[0];h=list(csv.DictReader((ROOT/'data/France/01_RGF93v2b_CC49_IGN69_Coordinates.csv').open()))[0]
position=[float(next(v for k,v in g.items() if 'Longitude' in k)),float(next(v for k,v in g.items() if 'Latitude' in k)),float(list(h.values())[3])]
s=stage();a=bind(s,'/World/A',normalize(compound.to_wkt()),position);UsdGeom.Xformable(a).AddTranslateOp().Set((10,0,0));path=ROOT/'fixtures/compound-geographic.usda';s.GetRootLayer().Export(str(path))
points=[[0,0,0],[10,0,0],[0,10,0]];output=normalize(CRS.from_wkt((ROOT/'data/France/03_RGF93v2b_Geocentric_WKT2.txt').read_text()).to_wkt())
py=Reader(s).coordinates('/World/A',points,output);cpp=native([{'kind':'model','stage':str(path),'path':'/World/A','points':points,'output_wkt':output}],'compound-geographic')[0]
error=float(np.max(np.linalg.norm(np.array(cpp['coordinates'])-py['coordinates'],axis=1))) if cpp['success'] else None
dump('compound-geographic.json',{'python':py,'native':cpp,'max_difference_m':error,'passed':error is not None and error<1e-7,'purpose':'Geographic compound with explicit orthometric height and post-placement ordinary adjustment; no angle-as-length chart'})
print(json.dumps({'max_difference_m':error,'native_success':cpp['success']}))
