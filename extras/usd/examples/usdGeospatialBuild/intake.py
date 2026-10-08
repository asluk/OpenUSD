"""Original-data intake. No historical geospatial implementation or fixture imported."""
from pathlib import Path
import argparse,zipfile,json,hashlib,csv,io,shutil,xml.etree.ElementTree as ET
import numpy as np,h5py
from pxr import Usd,UsdGeom,Sdf,Gf,Vt
from pyproj import CRS
from geobuild.model import normalize_wkt
ROOT=Path(__file__).parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def attr(p,name,typ,value,uniform=False):
    a=p.CreateAttribute(name,typ,custom=True,variability=Sdf.VariabilityUniform if uniform else Sdf.VariabilityVarying)
    a.Set(value);return a
def base(path):
    s=Usd.Stage.CreateNew(str(path));UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.SetStageUpAxis(s,'Z')
    s.GetRootLayer().customLayerData={'geospatialResolutionRequired':True}
    UsdGeom.Scope.Define(s,'/CRS');return s
def define_crs(s,name,wkt):
    p=s.DefinePrim('/CRS/'+name,'CoordinateReferenceSystem')
    attr(p,'crs:wkt',Sdf.ValueTypeNames.Token,normalize_wkt(wkt),True);return p.GetPath()
def bind(p,path):
    p.ApplyAPI('GeospatialBindingAPI')
    p.CreateRelationship('crs:binding',custom=True).SetTargets([path])
def measurement(s,path,crspath,points,values=None):
    p=UsdGeom.Scope.Define(s,path).GetPrim();bind(p,crspath)
    a=attr(p,'data:coordinates',Sdf.ValueTypeNames.Double3Array,Vt.Vec3dArray([Gf.Vec3d(*r) for r in points]))
    p.CreateRelationship('crs:coordinateProperties',custom=True).SetTargets([a.GetPath()])
    if values is not None:attr(p,'data:values',Sdf.ValueTypeNames.DoubleArray,Vt.DoubleArray(values))
    return p
def model(s,path,crspath,position):
    p=UsdGeom.Xform.Define(s,path).GetPrim();bind(p,crspath)
    attr(p,'crs:position',Sdf.ValueTypeNames.Double3,Gf.Vec3d(*position))
    return p
def mesh(s,path,points,counts,indices):
    m=UsdGeom.Mesh.Define(s,path)
    m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*r) for r in points]))
    m.CreateFaceVertexCountsAttr(counts);m.CreateFaceVertexIndicesAttr(indices);m.CreateSubdivisionSchemeAttr('none')
    m.CreateDisplayColorAttr([Gf.Vec3f(.12,.48,.62)]);return m
def main():
    a=argparse.ArgumentParser();a.add_argument('--workspace',required=True);args=a.parse_args();w=Path(args.workspace)
    data=ROOT/'data';scenes=ROOT/'scenes';data.mkdir(exist_ok=True);scenes.mkdir(exist_ok=True)
    manifest=[];targets={};partner={}
    z=zipfile.ZipFile(w/'AECO-CRS-Samples_2026-09-28.zip')
    for n in z.namelist():
        if n.lower().endswith(('.csv','_wkt2.txt')):
            p=data/Path(n).relative_to('AECO-CRS-Samples');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
            manifest.append({'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p),'licence':'Apache-2.0, partner sample permission','origin':'Partner coordinate samples; reference computations use PROJ 9.8.1'})
    for region in ['Colorado','France']:
        for f in sorted((data/region).glob('*.csv')):
            key=region+'_'+f.name.split('_')[0]
            wk=next(p for p in (data/region).iterdir() if p.name.endswith('_WKT2.txt') and p.name.startswith(f.name.split('_')[0]+'_'))
            text=wk.read_text(encoding='utf-8-sig')
            rows=list(csv.DictReader(io.StringIO(f.read_text(encoding='utf-8-sig'))))
            def col(pattern):return next(k for k in rows[0] if pattern in k)
            if 'Latitude (deg)' in rows[0]:names=['Longitude (deg)','Latitude (deg)',col('Ellipsoidal height')]
            elif 'X (m)' in rows[0]:names=['X (m)','Y (m)','Z (m)']
            else:names=[col('easting') if 'Site easting E (ftUS)' in rows[0] else col('Easting'),col('northing') if 'Site northing N (ftUS)' in rows[0] else col('Northing'),col('Site height') if 'Site height H (ftUS)' in rows[0] else col('height H')]
            pts=np.array([[float(r[k]) for k in names] for r in rows]);partner[key]={'wkt':text,'points':pts.tolist(),'ids':[r['Point ID'] for r in rows],'coordinate_columns':names}
            if 'COORDINATEMETADATA' in text:continue
            s=base(scenes/(key+'.usda'));c=define_crs(s,'Source',text);p=measurement(s,'/Controls',c,pts,np.arange(len(pts),dtype=float))
            attr(p,'data:ids',Sdf.ValueTypeNames.StringArray,[r['Point ID'] for r in rows])
            s.GetRootLayer().Save();targets[key]=normalize_wkt(text)
    (data/'partner-controls.json').write_text(json.dumps(partner,indent=2)+'\n')
    z=zipfile.ZipFile(w/'aeco_site_example.zip');tower=data/'tower.usdz';tower.write_bytes(z.read('aeco_site_example/La_tour_Eiffel.usdz'))
    ts=Usd.Stage.Open(str(tower));md=dict(ts.GetRootLayer().customLayerData)
    manifest.append({'path':'data/tower.usdz','sha256':digest(tower),'licence':md.get('copyright'),'attribution':md.get('author'),'url':md.get('url'),'origin':'Unmodified provider model; actual geometry metres, Y-up; erroneous asset metersPerUnit=0.01 retained'})
    france=partner['France_02']['wkt'];s=base(scenes/'tower.usda');c=define_crs(s,'Lambert93',france)
    p=model(s,'/Tower',c,[648237.125,6862251.890,33.79]);q=Gf.Rotation(Gf.Vec3d(0,0,1),45).GetQuat();attr(p,'crs:orientation',Sdf.ValueTypeNames.Quatd,q)
    cf=UsdGeom.Xform.Define(s,'/Tower/AssetConformance');cf.AddRotateXOp().Set(90)
    asset=UsdGeom.Xform.Define(s,'/Tower/AssetConformance/Asset').GetPrim();asset.GetReferences().AddReference('../data/tower.usdz')
    model(s,'/Ground',c,[648237.125,6862251.890,33.79]);floor=mesh(s,'/Ground/Plane',[[-400,-400,-.1],[400,-400,-.1],[400,400,-.1],[-400,400,-.1]],[4],[0,1,2,3]);floor.CreateDisplayColorAttr([(.63,.72,.67)])
    for i,offset in enumerate([(150,0,0),(0,150,0),(-150,0,0),(0,-150,0)]):
        p=model(s,f'/Control{i}',c,np.array([648237.125,6862251.890,33.79])+offset);m=mesh(s,f'/Control{i}/Marker',[[-4,-4,0],[4,-4,0],[4,4,0],[-4,4,0],[0,0,10]],[4,3,3,3,3],[0,1,2,3,0,1,4,1,2,4,2,3,4,3,0,4]);m.CreateDisplayColorAttr([(.8,.3,.15)])
    s.GetRootLayer().Save()
    landxml=zlib_read(w/'AECO-CRS-Samples_2026-09-28.zip','AECO-CRS-Samples/Colorado/Trimble Westminster Park and Ride LandXML.xml')
    original=data/'Colorado/Trimble Westminster Park and Ride LandXML.xml';original.write_bytes(landxml)
    manifest.append({'path':original.relative_to(ROOT).as_posix(),'sha256':digest(original),'licence':'Apache-2.0, partner sample permission','origin':'Original partner LandXML; N/E/H source order'})
    xml=ET.fromstring(landxml)
    def nodes(name):return [x for x in xml.iter() if x.tag.split('}')[-1]==name]
    pts={}
    for e in nodes('P'):
        if e.get('id'):
            n,east,h=map(float,e.text.split());pts[e.get('id')]=[east,n,h]
    faces=[e.text.split() for e in nodes('F')]
    used=sorted(set(k for f in faces for k in f));xyz=np.array([pts[k] for k in used]);lookup={k:i for i,k in enumerate(used)}
    # Provider LandXML N/E/H in US survey feet; actual complete site calibration WKT retained.
    if len(xyz):
        anchor=xyz.mean(axis=0);s=base(scenes/'terrain.usda');c=define_crs(s,'Site',partner['Colorado_03']['wkt']);model(s,'/Terrain',c,anchor)
        mesh(s,'/Terrain/Mesh',(xyz-anchor)*1200/3937,[len(f) for f in faces],[lookup[k] for f in faces for k in f]);s.GetRootLayer().Save()
    else:
        breaklines=[np.array(list(map(float,e.text.split()))).reshape(-1,3)[:,[1,0,2]] for e in nodes('PntList3D')]
        xyz=np.vstack(breaklines);anchor=xyz.mean(axis=0);s=base(scenes/'terrain.usda');c=define_crs(s,'Site',partner['Colorado_03']['wkt']);model(s,'/Terrain',c,anchor)
        curves=UsdGeom.BasisCurves.Define(s,'/Terrain/Breaklines');curves.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*r) for r in (xyz-anchor)*1200/3937]));curves.CreateCurveVertexCountsAttr([len(r) for r in breaklines]);curves.CreateTypeAttr('linear');curves.CreateWidthsAttr([.2]);curves.SetWidthsInterpolation('constant');curves.CreateDisplayColorAttr([(.14,.53,.67)]);s.GetRootLayer().Save()
    rail_src=w/'geospatial-datasets/railway-source/1kmE4334N3375.geojson';shutil.copyfile(rail_src,data/'railway.geojson');g=json.loads(rail_src.read_text())
    def lines(geom):
        typ=geom['type'];v=geom['coordinates']
        if typ=='LineString':return [v]
        if typ=='Polygon':return v
        if typ=='MultiPolygon':return [r for p in v for r in p]
        raise ValueError(typ)
    ll=[np.array(l,dtype=float) for f in g['features'] for l in lines(f['geometry'])];rr=np.vstack(ll)
    s=base(scenes/'railway.usda');c=define_crs(s,'Source',CRS.from_epsg(4979).to_wkt());measurement(s,'/RailCoordinates',c,rr)
    s.GetRootLayer().customLayerData={**s.GetRootLayer().customLayerData,'sourceHeightInterpretation':'GeoJSON third coordinate interpreted as WGS84 ellipsoidal height for this demonstration; source CRS label EPSG:4326 alone is incomplete for height. No survey-height accuracy claimed.'}
    s.GetRootLayer().Save();np.savez_compressed(data/'rail-topology.npz',counts=[len(l) for l in ll])
    manifest.append({'path':'data/railway.geojson','sha256':digest(data/'railway.geojson'),'origin':'Original user railway GeoJSON; all feature vertices preserved','source_crs':g.get('crs'),'height_interpretation':'Conditional WGS84 ellipsoidal height; no concealed zero-height promotion'})
    s=base(scenes/'city.usda');c=define_crs(s,'Source',CRS.from_epsg(4979).to_wkt())
    y,x=np.mgrid[0:64,0:64];xx=2.47+(x-32)*.000025;yy=48.82+(y-32)*.000025
    red=.2+.07*np.sin(x/4);nir=.4+.2*np.cos(y/8)*np.cos(x/7);ndvi=(nir-red)/(nir+red)
    p=measurement(s,'/Image',c,np.column_stack([xx.ravel(),yy.ravel(),np.full(x.size,80.)]),ndvi.ravel())
    attr(p,'data:red',Sdf.ValueTypeNames.DoubleArray,red.ravel().tolist());attr(p,'data:nir',Sdf.ValueTypeNames.DoubleArray,nir.ravel().tolist())
    attr(p,'data:observationTimes',Sdf.ValueTypeNames.DoubleArray,[0.]*x.size);p.SetCustomDataByKey('origin','Synthetic multispectral image; synthetic 80 m ellipsoidal sample height; NDVI demonstration, no real land-use claim');s.GetRootLayer().Save()
    nc=w/'geospatial-datasets/scalar-field/gfs_t2m.nc';shutil.copyfile(nc,data/'gfs_t2m.nc')
    with h5py.File(nc) as f:
        lo,la=np.meshgrid(f['lon'][:],f['lat'][:]);values=f['t2m'][:].astype(float).ravel();v=np.column_stack([((lo.ravel()+180)%360)-180,la.ravel(),np.zeros(lo.size)])
    s=base(scenes/'climate.usda');c=define_crs(s,'Source',CRS.from_epsg(4979).to_wkt());p=measurement(s,'/Climate',c,v,values)
    p.GetAttribute('data:values').Set(Vt.DoubleArray(values),0);p.GetAttribute('data:values').Set(Vt.DoubleArray(values+np.sin(np.deg2rad(la.ravel()))),10)
    attr(p,'data:observationTimes',Sdf.ValueTypeNames.DoubleArray,[0.,10.]);p.SetCustomDataByKey('origin','Original scalar field; second time explicitly synthetic perturbation. Surface positions assume zero ellipsoidal height; source file contains no height or units metadata. No forecast/trend accuracy claimed.');s.GetRootLayer().Save()
    manifest.append({'path':'data/gfs_t2m.nc','sha256':digest(data/'gfs_t2m.nc'),'origin':'Original scalar field supplied to prior workflow; values unchanged at time 0; time 10 synthetic'})
    s=base(scenes/'composition.usda');c=define_crs(s,'Source',CRS.from_epsg(32631).to_3d().to_wkt());parent=UsdGeom.Scope.Define(s,'/Project');bind(parent.GetPrim(),c)
    p=model(s,'/Project/Model',c,[1000,2000,30]);attr(p,'crs:orientation',Sdf.ValueTypeNames.Quatd,Gf.Rotation(Gf.Vec3d(0,0,1),90).GetQuat());attr(p,'crs:scale',Sdf.ValueTypeNames.Double3,Gf.Vec3d(2,1,1));UsdGeom.Xformable(p).AddTranslateOp().Set((7,8,9))
    p.GetAttribute('crs:position').Set(Gf.Vec3d(1000,2000,30),0);p.GetAttribute('crs:position').Set(Gf.Vec3d(1010,2000,30),10)
    child=UsdGeom.Xform.Define(s,'/Project/Model/Child');child.AddTranslateOp().Set((1,0,0));mesh(s,'/Project/Model/Child/Mesh',[[3,4,5],[0,0,0],[1,0,0]],[3],[0,1,2])
    p=model(s,'/Project/Model/Independent',c,[20,40,5]);mesh(s,'/Project/Model/Independent/Mesh',[[0,0,0],[1,0,0],[0,1,0]],[3],[0,1,2]);s.GetRootLayer().Save()
    # Native instances reference an ordinary asset, while each instance owns its CRS placement.
    asset_s=Usd.Stage.CreateNew(str(scenes/'instance-asset.usda'));asset_root=UsdGeom.Xform.Define(asset_s,'/Asset');m=mesh(asset_s,'/Asset/Geometry',[[0,0,0],[2,0,0],[0,3,0]],[3],[0,1,2]);asset_s.SetDefaultPrim(asset_root.GetPrim());asset_s.GetRootLayer().Save()
    s=base(scenes/'instances.usda');c=define_crs(s,'Source',CRS.from_epsg(32631).to_3d().to_wkt())
    for i in range(3):
        p=model(s,f'/Native{i}',c,[650000+10*i,6860000,40]);q=s.DefinePrim(f'/Native{i}/Asset');q.GetReferences().AddReference('instance-asset.usda');q.SetInstanceable(True)
    p=model(s,'/PointModels',c,[650000,6860040,40]);inst=UsdGeom.PointInstancer.Define(s,'/PointModels/Instances');proto=mesh(s,'/PointModels/Instances/Prototypes/One',[[0,0,0],[2,0,0],[0,3,0]],[3],[0,1,2]);inst.CreatePrototypesRel().SetTargets([proto.GetPath()]);inst.CreateProtoIndicesAttr([0,0,0]);inst.CreatePositionsAttr([(0,0,0),(10,0,0),(20,0,0)]);s.GetRootLayer().Save()
    (data/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    targets['ecef']=normalize_wkt(CRS.from_epsg(4978).to_wkt());targets['geographic']=normalize_wkt(CRS.from_epsg(4979).to_wkt());targets['utm31']=normalize_wkt(CRS.from_epsg(32631).to_3d().to_wkt());targets['utm32']=normalize_wkt(CRS.from_epsg(32632).to_3d().to_wkt());targets['utm13']=normalize_wkt(CRS.from_epsg(26913).to_3d().to_wkt())
    (ROOT/'targets.json').write_text(json.dumps(targets,indent=2)+'\n')
    print(json.dumps({'partner_sets':len(partner),'terrain_vertices':len(xyz),'terrain_faces':len(faces),'rail_vertices':len(rr),'rail_parts':len(ll),'city_samples':4096,'climate_samples':len(values),'source_assets':len(manifest)}))
def zlib_read(p,n):
    with zipfile.ZipFile(p) as z:return z.read(n)
if __name__=='__main__':main()
