from pathlib import Path
import sys,numpy as np
from pxr import Usd,UsdGeom,Gf,UsdProfiles,Sdf
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT/'src'))
from fixtures import stage,bind,wkt,points
from export import geometry_bake
from scene import Reader
from profiles import declare,discover,CAPABILITY,PUBLICATION

def test_bake_retains_only_requested_samples(tmp_path):
 s=stage();a=bind(s,'/World/A');mesh=UsdGeom.Mesh(points(a,[(0,0,0),(1,0,0),(0,1,0)]))
 for t in [0,5,10]:mesh.GetPointsAttr().Set([(t,0,0),(t+1,0,0),(t,1,0)],t)
 a.GetAttribute('crs:position').Set((-1,0,0),0);a.GetAttribute('crs:position').Set((1,0,0),10)
 receipt=geometry_bake(s,tmp_path/'sampled.usda',wkt(4978),(0,10),numeric_origin=(6378137,0,0))
 fresh=Usd.Stage.Open(str(tmp_path/'sampled.usda'));out=UsdGeom.Mesh(fresh.GetPrimAtPath(receipt['controls'][0]['export_path']))
 assert out.GetPointsAttr().GetTimeSamples()==[0,10];assert fresh.GetTimeCodesPerSecond()==s.GetTimeCodesPerSecond()
 for t in [0,10]:
  expected=Reader(s).coordinates(str(mesh.GetPath()),np.array(mesh.GetPointsAttr().Get(t),float),wkt(4978),t)['coordinates']
  actual=Reader(fresh).coordinates(str(out.GetPath()),np.array(out.GetPointsAttr().Get(t),float),wkt(4978),t)['coordinates']
  np.testing.assert_allclose(actual,expected,atol=.01,rtol=0)

def test_nonconforming_profiles_value_not_known_none():
 s=stage();declare(s.GetDefaultPrim(),False,True);api=UsdProfiles.ClaimsAPI(s.GetDefaultPrim());info=api.GetProfilesInfo();info['capabilityUsages'][CAPABILITY]='soft';api.SetProfilesInfo(info)
 assert discover(s)['state']=='unknown'

def test_rate_operation_is_deferred_without_coordinate_epoch():
 import pytest
 from pyproj import CRS
 from geodesy import Definition,Operations
 from errors import ResolutionFailure
 with pytest.raises(ResolutionFailure,match='deferred-epoch-operation'):
  Operations().convert([6378137,100,100],Definition(CRS.from_epsg(7789).to_wkt()),Definition(CRS.from_epsg(9988).to_wkt()))

def test_legacy_geojson_authority_is_not_substring_guessed(tmp_path):
 import pytest,json
 from measurements import geojson
 from geodesy import Definition
 from errors import ResolutionFailure
 p=tmp_path/'bad.geojson';p.write_text(json.dumps({'type':'FeatureCollection','crs':{'type':'name','properties':{'name':'EPSG:14326'}},'features':[{'type':'Feature','properties':{},'geometry':{'type':'Point','coordinates':[2,49]}}]}))
 with pytest.raises(ResolutionFailure,match='unsupported-legacy-geojson-crs'):geojson(p,'','geometry',Definition(wkt(4326)))

def test_working_context_binding_role_must_be_valid():
 import pytest
 from errors import ResolutionFailure
 s=stage();p=s.DefinePrim('/World/Invalid','Scope');p.AddAppliedSchema('GeospatialCRSBindingAPI');p.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,variability=Sdf.VariabilityUniform).Set(wkt(4979));bind(s,'/World/Invalid/Model')
 with pytest.raises(ResolutionFailure,match='invalid-binding-role'):Reader(s).coordinates('/World/Invalid/Model',[(0,0,0)],wkt(4978))

def test_model_retains_authored_static_bound_operation():
 from pyproj import CRS
 source=CRS.from_proj4('+proj=longlat +ellps=clrk66 +towgs84=100,200,300 +no_defs').to_3d()
 s=stage();bind(s,'/World/A',source.to_wkt())
 result=Reader(s).coordinates('/World/A',[(0,0,0),(1,0,0),(0,1,0)],wkt(4978))
 # Analytic ellipsoid equator + authored XYZ shift, not another reader.
 np.testing.assert_allclose(result['coordinates'],[(6378306.4,200,300),(6378306.4,201,300),(6378306.4,200,301)],atol=1e-7,rtol=0)
 source_points=Reader(s).inverse_model('/World/A',np.array(result['coordinates']),Reader(s).selected_output(wkt(4978)))
 np.testing.assert_allclose(source_points,[(0,0,0),(1,0,0),(0,1,0)],atol=1e-7,rtol=0)

def test_instance_result_retains_authored_id():
 from test_assembly import instance_scene
 s,inst,mesh=instance_scene()
 identity=Reader(s).point_instance(str(inst.GetPath()),0,str(mesh.GetPath()),[(0,0,0)],wkt(4978))['instance_identity']
 assert identity['index']==0 and identity['id']==1234 and identity['prototype_relative_path']=='Mesh'
