"""New authored fixtures and expectations, from the pinned contract and originals."""
import csv,json,sys,math
from pathlib import Path
import numpy as np
from pyproj import CRS
from pxr import Usd,UsdGeom,Sdf,Gf,Vt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src_py'))
from reader import normalize_wkt,publish_claim
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'inputs/authored';F.mkdir(exist_ok=True)
O=ROOT/'inputs/original'

def stage(name):
    s=Usd.Stage.CreateNew(str(F/name));UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.SetStageUpAxis(s,'Z');s.SetTimeCodesPerSecond(24);return s

def wkt(code):return normalize_wkt(CRS.from_epsg(code).to_wkt())

def bind(s,path,w,position=None,orientation=None,typ='Xform'):
    p=s.DefinePrim(path,typ);p.AddAppliedSchema('GeospatialCRSBindingAPI')
    p.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=False,variability=Sdf.VariabilityUniform).Set(w)
    if position is not None:p.GetAttribute('crs:position').Set(Gf.Vec3d(*position))
    if orientation is not None:p.GetAttribute('crs:orientation').Set(Gf.Vec3d(*orientation))
    return p

def main():
    g=wkt(4979);ecef=wkt(4978);(F/'geographic.wkt').write_text(g);(F/'ecef.wkt').write_text(ecef)
    s=stage('controls.usda');world=bind(s,'/World',g,(0,0,0));s.SetDefaultPrim(world)
    # An ancestor's 10000m adjustment must never leak through an independent binding.
    UsdGeom.Xformable(world).AddTranslateOp().Set((10000,0,0))
    m=bind(s,'/World/Model',g,(0,0,0));
    a=bind(s,'/World/Heading',g,(0,0,0),(90,0,0))
    child=UsdGeom.Xform.Define(s,'/World/Heading/Child');child.AddTranslateOp().Set((0,10,0))
    adjustment=bind(s,'/World/Adjusted',g,(0,0,0));UsdGeom.Xformable(adjustment).AddTranslateOp().Set((10,0,0))
    reset=UsdGeom.Xform.Define(s,'/World/Adjusted/Reset');reset.SetResetXformStack(True);reset.AddTranslateOp().Set((0,20,0))
    own=bind(s,'/World/Independent',ecef,(6378237,0,0));boundchild=bind(s,'/World/Independent/Child',ecef,(6378157,0,0))
    moving=bind(s,'/World/Moving',g)
    moving.GetAttribute('crs:position').Set((-1,0,0),0);moving.GetAttribute('crs:position').Set((1,0,0),10)
    turn=bind(s,'/World/Turn',g,(0,0,0));turn.GetAttribute('crs:orientation').Set((0,0,0),0);turn.GetAttribute('crs:orientation').Set((180,0,0),10)
    wrap=bind(s,'/World/Wrap',g,(0,0,0));wrap.GetAttribute('crs:orientation').Set((0,0,0),0);wrap.GetAttribute('crs:orientation').Set((360,0,0),10)
    bad=bind(s,'/World/Broken',g,(0,0,0));bad.GetAttribute('crs:wkt').Block()
    badrole=UsdGeom.Xform.Define(s,'/World/Model/BadRole').GetPrim();badrole.CreateAttribute('crs:position',Sdf.ValueTypeNames.Double3).Set((1,2,3))
    badtype=UsdGeom.Xform.Define(s,'/World/WrongType').GetPrim();badtype.CreateAttribute('crs:position',Sdf.ValueTypeNames.Float3).Set((0,0,0));badtype.AddAppliedSchema('GeospatialCRSBindingAPI');badtype.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=False,variability=Sdf.VariabilityUniform).Set(g)
    nonfinite=bind(s,'/World/Nonfinite',g,(0,0,float('nan')))
    twod=bind(s,'/World/TwoD',wkt(4326),(0,0,0))
    blocked=bind(s,'/World/Blocked',g,(0,0,0));blocked.GetAttribute('crs:orientation').Block()
    pole=bind(s,'/World/Pole',ecef,(0,0,6356752.314245))
    singular=bind(s,'/World/Singular',g,(0,0,0));UsdGeom.Xformable(singular).AddScaleOp().Set((0,1,1))
    mesh=UsdGeom.Mesh.Define(s,'/World/Heading/Triangle');mesh.CreatePointsAttr([(0,0,0),(10,0,0),(0,0,10)]);mesh.CreateFaceVertexCountsAttr([3]);mesh.CreateFaceVertexIndicesAttr([0,1,2]);mesh.GetPrim().CreateAttribute('purposeNote',Sdf.ValueTypeNames.String).Set('Unrelated property retained')
    inst=UsdGeom.PointInstancer.Define(s,'/World/Instances');inst.GetPrim().AddAppliedSchema('GeospatialCRSBindingAPI');inst.GetPrim().CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=False,variability=Sdf.VariabilityUniform).Set(g);inst.GetPrim().GetAttribute('crs:position').Set((0,0,0))
    proto=bind(s,'/Storage/Prototype',g,(.0001,0,0));inst.CreatePrototypesRel().SetTargets([proto.GetPath()]);inst.CreateProtoIndicesAttr([0,0]);inst.CreatePositionsAttr([(0,0,0),(10,0,0)]);inst.CreateIdsAttr([41,42])
    publish_claim(world,True);s.GetRootLayer().Save()
    # Original survey table expected values are independent of either implementation.
    s=stage('survey.usda');root=UsdGeom.Xform.Define(s,'/Survey').GetPrim();s.SetDefaultPrim(root)
    cases=[]
    for locale,source_name,target_name,coords_name,target_coords_name,semantic in [
      ('France','04_RGF93v2b_Geographic3D_WKT2.txt','03_RGF93v2b_Geocentric_WKT2.txt','04_RGF93v2b_Geographic3D_Coordinates.csv','03_RGF93v2b_Geocentric_Coordinates.csv',[1,0,2]),
      ('France','01_RGF93v2b_CC49_IGN69_WKT2.txt','02_RGF93v2b_Lambert93_IGN69_WKT2.txt','01_RGF93v2b_CC49_IGN69_Coordinates.csv','02_RGF93v2b_Lambert93_IGN69_Coordinates.csv',[0,1,2]),
      ('Colorado','02_NAD83-2011_ColoradoCentral_NAVD88_WKT2.txt','03_Westminster_Site_Calibration_WKT2.txt','02_NAD83-2011_ColoradoCentral_NAVD88_Coordinates.csv','03_Westminster_Site_Calibration_Coordinates.csv',[0,1,2])]:
        src=(O/locale/source_name).read_text(encoding='utf-8-sig');dst=(O/locale/target_name).read_text(encoding='utf-8-sig')
        source_rows=list(csv.reader((O/locale/coords_name).open(encoding='utf-8-sig')))[1:];targets={r[0]:r for r in list(csv.reader((O/locale/target_coords_name).open(encoding='utf-8-sig')))[1:]}
        item={'name':locale+'_'+source_name[:2],'source_wkt':src,'output_wkt':dst,'rows':[],'tolerance_m':.002}
        for r in source_rows:
            numbers=[float(x) for x in r[1:4]];point=[numbers[i] for i in semantic];expected=[float(x) for x in targets[r[0]][1:4]]
            item['rows'].append({'id':r[0],'source':point,'expected':expected})
        cases.append(item)
    (F/'survey-expectations.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
    for i,c in enumerate(cases):
        bind(s,f'/Survey/Case{i}',normalize_wkt(c['source_wkt']),c['rows'][0]['source'])
    s.GetRootLayer().Save()
    # Labeled native samples: deliberately permuted coordinate storage dimensions.
    import netCDF4
    with netCDF4.Dataset(F/'permuted.cf.nc','w') as n:
        n.Conventions='CF-1.12';n.createDimension('row',2);n.createDimension('col',3);n.createDimension('time',2)
        cr=n.createVariable('crs','i4');cr.grid_mapping_name='latitude_longitude';cr.crs_wkt=g
        lon=n.createVariable('longitude','f8',('col','row'));lon.standard_name='longitude';lon.units='degrees_east';lon[:]=np.array([[0,.1],[1,1.1],[2,2.1]])
        lat=n.createVariable('latitude','f8',('row',));lat.standard_name='latitude';lat.units='degrees_north';lat[:]=[0,1]
        ht=n.createVariable('height','f8',());ht.standard_name='height_above_reference_ellipsoid';ht.units='m';ht.assignValue(10)
        t=n.createVariable('time','f8',('time',));t.standard_name='time';t.units='hours since 2026-10-15 00:00:00';t[:]=[0,6]
        v=n.createVariable('measurement','f8',('time','row','col'),fill_value=-9999);v.grid_mapping='crs';v.coordinates='longitude latitude height time';v[:]=np.arange(12).reshape(2,2,3);v[1,1,2]=-9999
    # Climate original is unchanged. Additional declarations/height/time are explicit
    # illustrative author input, never inferred by a reader from names or values.
    with netCDF4.Dataset(O/'gfs_t2m.nc') as original,netCDF4.Dataset(F/'climate.cf.nc','w') as n:
        n.Conventions='CF-1.12';n.comment='Illustrative derived copy. Added metadata, explicit synthetic ellipsoid height 0, and synthetic second time +1 K.'
        n.createDimension('lat',37);n.createDimension('lon',72);n.createDimension('time',2)
        cr=n.createVariable('crs','i4');cr.grid_mapping_name='latitude_longitude';cr.crs_wkt=g
        for name,role,unit in [('lon','longitude','degrees_east'),('lat','latitude','degrees_north')]:
            a=n.createVariable(name,'f8',(name,));a.standard_name=role;a.units=unit;a[:]=original[name][:]
        h=n.createVariable('height','f8',());h.standard_name='height_above_reference_ellipsoid';h.units='m';h.assignValue(0)
        t=n.createVariable('time','f8',('time',));t.standard_name='time';t.units='hours since 2026-10-15 00:00:00';t[:]=[0,6]
        v=n.createVariable('t2m','f4',('time','lat','lon'));v.coordinates='lat lon height time';v.grid_mapping='crs';v.units='K';v[0]=original['t2m'][:];v[1]=original['t2m'][:]+1
    import rasterio
    from rasterio.transform import from_origin
    with rasterio.open(F/'samples.tif','w',driver='GTiff',width=3,height=2,count=1,dtype='float32',crs=CRS.from_epsg(32631),transform=from_origin(500000,5400000,10,10)) as r:r.write(np.arange(6,dtype=np.float32).reshape(2,3),1)
    s=stage('measurements.usda');root=UsdGeom.Xform.Define(s,'/Data').GetPrim();s.SetDefaultPrim(root)
    for name,asset,fmt,field,domain,cr in [('Permutation','permuted.cf.nc','CF','measurement','crs',g),('Climate','climate.cf.nc','CF','t2m','crs',g),('Railway','../original/railway.geojson','GeoJSON','','geometry',g),('Raster','samples.tif','GeoTIFF','1','0',wkt(32631))]:
        p=bind(s,'/Data/'+name,cr,typ='GeospatialDataSource')
        for key,typ,val in [('asset',Sdf.ValueTypeNames.Asset,Sdf.AssetPath(asset)),('format',Sdf.ValueTypeNames.Token,fmt),('field',Sdf.ValueTypeNames.String,field),('coordinateDomain',Sdf.ValueTypeNames.String,domain)]:
            p.CreateAttribute('data:'+key,typ,custom=False,variability=Sdf.VariabilityUniform).Set(val)
    publish_claim(root,True);s.GetRootLayer().Save()
    expectations={'equator_ecef':[6378137,0,0],'heading90_forward10_ecef':[6378137,10,0],
      'source_interpolated_midpoint':[6378137,0,0],'export_endpoints_chord_deficit_m':6378137*(1-math.cos(math.pi/180)),
      'independent_origin_difference_m':80,'permuted_index_0_1_2':{'coordinates':[2.1,1,10],'value':5},
      'raster_first_center':[500005,5399995],'agreement_m':.0001,'survey_tolerance_m':.002}
    (F/'expected-before-execution.json').write_text(json.dumps(expectations,indent=2),encoding='utf-8')
    print('Fresh fixtures and independent expectations written')
if __name__=='__main__':main()
