"""Fresh conditional fixture authoring from raw data, never retired converters.

All source files remain external and unchanged. Explicit WGS84/ellipsoidal-height
interpretations below are test hypotheses, not recovered provider metadata.
"""
from pathlib import Path
import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom
from pyproj import CRS
from geobuild.datasets import read_geojson, read_field
from geobuild.operations import ProjOperations
from geobuild.runtime import definition, bind, position, declare

GEO = CRS.from_epsg(4979).to_wkt()
ECEF = CRS.from_epsg(4978).to_wkt()
UTM = CRS.from_epsg(32632).to_3d().to_wkt()


def new_stage(target=ECEF, source=GEO):
    stage=Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(stage,1)
    UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
    root=UsdGeom.Xform.Define(stage,'/World').GetPrim()
    stage.SetDefaultPrim(root)
    definition(stage,'/CRS/Native',source)
    declare(stage,target)
    return stage


def railway_original(path):
    data=read_geojson(path)
    stage=new_stage(UTM,UTM)
    engine=ProjOperations()
    expected={}
    for index,feature in enumerate(data['features']):
        # Explicit fixture preparation selects a projected native frame for local
        # modelling; the entire original geographic array is also retained.
        points=np.array(engine.convert(GEO,UTM,feature['points']).coordinates)
        parent=f'/World/Feature_{index}'
        anchor=UsdGeom.Xform.Define(stage,parent).GetPrim()
        bind(anchor,'/CRS/Native')
        position(anchor,points[0])
        anchor.CreateAttribute('source:objectId',Sdf.ValueTypeNames.String).Set(feature['id'])
        anchor.CreateAttribute('source:geometry',Sdf.ValueTypeNames.String).Set(feature['geometry'])
        anchor.CreateAttribute('source:polygonRingCounts',Sdf.ValueTypeNames.IntArray).Set(feature['polygon_ring_counts'])
        anchor.CreateAttribute('source:coordinates',Sdf.ValueTypeNames.Double3Array).Set([Gf.Vec3d(*p) for p in feature['points']])
        # Rings are boundaries, including holes; never fill a hole as a polygon.
        curve=UsdGeom.BasisCurves.Define(stage,parent+'/Boundary')
        curve.GetPointsAttr().Set([Gf.Vec3f(*p) for p in points-points[0]])
        curve.GetCurveVertexCountsAttr().Set([len(part) for part in feature['parts']])
        curve.GetTypeAttr().Set('linear')
        curve.GetWrapAttr().Set('nonperiodic')
        expected[parent+'/Boundary']=points
    return stage, expected, data


def railway_provider(path):
    source=Sdf.Layer.FindOrOpen(str(path))
    layer=Sdf.Layer.CreateAnonymous('railway-overlay.usda')
    layer.subLayerPaths=[source.identifier]
    stage=Usd.Stage.Open(layer)
    UsdGeom.SetStageMetersPerUnit(stage,1)
    UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
    definition(stage,'/CRS/Native',GEO)
    for prim in stage.Traverse():
        attr=prim.GetAttribute('omni:geospatial:wgs84:local:position')
        if attr:
            lat,lon,height=attr.Get()
            bind(prim,'/CRS/Native')
            position(prim,(lon,lat,height))
    declare(stage,UTM,roots=('/RootGeoReference',))
    return stage


def field_overlay(path):
    data=read_field(path)
    base=new_stage(ECEF,ECEF)
    engine=ProjOperations()
    coordinates=engine.convert(GEO,ECEF,data['points']).coordinates
    # Non-geometric base records; positions are explicit ECEF preparation to
    # avoid an undefined longitude-derived east direction at the poles.
    for index,(point,scalar,original) in enumerate(zip(coordinates,data['values'],data['points'])):
        prim=base.DefinePrim(f'/World/Sample_{index}','Scope')
        bind(prim,'/CRS/Native')
        position(prim,point)
        prim.CreateAttribute('field:rawValue',Sdf.ValueTypeNames.Double).Set(scalar)
        prim.CreateAttribute('field:sourceLonLatThird',Sdf.ValueTypeNames.Double3).Set(original)
    overlay=Sdf.Layer.CreateAnonymous('field-visualization.usda')
    overlay.subLayerPaths=[base.GetRootLayer().identifier]
    visual=Usd.Stage.Open(overlay)
    visual.GetRootLayer().customLayerData=base.GetRootLayer().customLayerData
    UsdGeom.SetStageMetersPerUnit(visual,1)
    UsdGeom.SetStageUpAxis(visual,UsdGeom.Tokens.z)
    for index in range(len(coordinates)):
        points=UsdGeom.Points.Define(visual,f'/World/Sample_{index}/Marker')
        points.GetPointsAttr().Set([(0,0,0)])
        points.GetWidthsAttr().Set([15000])
    return base,visual,coordinates,data


def aeco_site(folder):
    folder=Path(folder)
    library=Usd.Stage.Open(str(folder/'crs_library.usda'))
    crs={str(p.GetPath()):p.GetAttribute('crs:wkt').Get() for p in library.Traverse() if p.GetAttribute('crs:wkt')}
    if not crs:
        crs={str(p.GetPath()):a.Get().strip() for p in library.Traverse() for a in p.GetAttributes()
             if a.GetTypeName()==Sdf.ValueTypeNames.String and isinstance(a.Get(),str) and a.Get().strip().startswith(('COMPOUNDCRS[','PROJCRS[','GEODCRS[','DERIVEDPROJCRS['))}
    native=crs['/CRS/LocalSiteGrid']
    target=crs['/CRS/Lambert93_IGN69']
    stage=new_stage(target,native)
    definition(stage,'/CRS/Project',target)
    site=UsdGeom.Xform.Define(stage,'/World/Site').GetPrim()
    bind(site,'/CRS/Native')
    position(site,(1000,1000,33))
    tower=UsdGeom.Xform.Define(stage,'/World/Site/Tower')
    tower.AddTranslateOp().Set((37.125,51.89,.79))
    tower.AddRotateZOp().Set(45)
    geom=UsdGeom.Xform.Define(stage,'/World/Site/Tower/Geom')
    geom.GetPrim().GetReferences().AddReference(str(folder/'La_tour_Eiffel.usdz'))
    geom.AddRotateXOp().Set(90)
    # The asset measures 300 authoring units and declares centimetres. This
    # explicit provider-stated conformance uses metres, independently of placement.
    geom.AddScaleOp().Set((1,1,1))
    site.CreateRelationship('geo:projectBinding').SetTargets(['/CRS/Project'])
    site.CreateAttribute('geo:projectTransform',Sdf.ValueTypeNames.Matrix4d).Set(Gf.Matrix4d(1))
    return stage,site
