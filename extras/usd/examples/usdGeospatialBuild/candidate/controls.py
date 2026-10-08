"""Distinguishing controls and expected results, never implementation-derived oracles."""
import math,json
import numpy as np
from pathlib import Path
from pxr import Usd,UsdGeom,Gf,Sdf,UsdProfiles
from pyproj import CRS,Transformer
from .runtime import Runtime,ContractError,definition,dependency
from .datasets import read_source

def verify(jobs,results,targets,directory):
    checks=[]
    def yes(name,condition):
        if not condition:raise AssertionError(name)
        checks.append({'name':name,'passed':True})
    def fails(name,fn):
        try:fn()
        except ContractError as e:checks.append({'name':name,'passed':True,'visible_error':str(e)});return
        raise AssertionError('Expected visible failure: '+name)
    byname={j['name']:j for j in jobs}
    for j in jobs:
        if j.get('expected') is not None:
            actual=np.array(results[j['name']]['queries'][0]['coordinates'])
            yes(j['name']+' analytic expected',np.max(np.linalg.norm(actual-j['expected'],axis=1))<1e-8)
        if j['name'].startswith('basis-'):
            yes(j['name']+' local frame derivative matches the independent affine matrix',np.max(abs(np.array(results[j['name']]['frames']['/World/Model']['jacobian'])-(np.array(j['expected'])-[6378137,0,0])))<1e-8)
    grid=results['working-adjustment']['queries'];ecef=results['working-adjustment-ecef']['queries']
    # Separate direct engine control with known coordinates, never the candidate's placement implementation.
    source=[2.2945,48.8584,35];tr=Transformer.from_crs(CRS.from_wkt(targets['geo3']),CRS.from_wkt(targets['utm31']),always_xy=True,allow_ballpark=False,only_best=True)
    origin=np.array(tr.transform(*source));actual=np.array(grid[0]['coordinates'][0]);yes('anchor +10 means site easting after 90 degree orientation',np.linalg.norm(actual-(origin+[10,0,0]))<1e-7)
    yes('parent ordinary +100000 excluded',abs(actual[0]-origin[0]-10)<1e-7)
    to_grid=Transformer.from_crs(CRS.from_wkt(targets['ecef3']),CRS.from_wkt(targets['utm31']),always_xy=True,allow_ballpark=False,only_best=True)
    for i in range(3):
        a=np.array(grid[i]['coordinates']);b=np.array(ecef[i]['coordinates']);back=np.stack(to_grid.transform(*b.T),axis=-1)
        yes('physical placement survives output change '+str(i),np.max(np.linalg.norm(a-back,axis=1))<.001)
    child=np.array(grid[1]['coordinates'][0]);reset=np.array(grid[2]['coordinates'][0])
    yes('descendant reset removes anchor adjustment and retains CRS placement',np.linalg.norm((child-reset)-[10,0,0])<1e-7)
    # Quarter-turn makes a child local X displacement northward, distinguishing it from anchor site-easting adjustment.
    yes('descendant offset retains oriented model axes',abs(child[1]-origin[1])>2.9 and abs(child[0]-origin[0]-10)<.1)
    s=Usd.Stage.Open(byname['basis-Z-1']['stage']);r=Runtime(s,targets['ecef3']);p=s.GetPrimAtPath('/World/Model');before=r.snapshot()
    with Usd.EditContext(s,s.GetSessionLayer()):p.GetAttribute('crs:position').Block()
    fails('blocked position has no zero fallback',lambda:r.placement(p,[[0,0,0]]));s.GetSessionLayer().ImportFromString(before[s.GetSessionLayer().identifier])
    with Usd.EditContext(s,s.GetSessionLayer()):p.GetAttribute('crs:orientation').Set((float('nan'),0,0))
    fails('nonfinite authored heading rejected',lambda:r.placement(p,[[0,0,0]]));s.GetSessionLayer().ImportFromString(before[s.GetSessionLayer().identifier])
    with Usd.EditContext(s,s.GetSessionLayer()):UsdGeom.Xformable(p).AddScaleOp(opSuffix='singular').Set((0,1,1))
    yes('singular scale permits forward point',np.isfinite(r.placement(p,[[1,0,0]])).all())
    s.GetSessionLayer().ImportFromString(before[s.GetSessionLayer().identifier])
    yes('authored layers preserved through negative controls',before==r.snapshot())
    yes('same Cartesian CRS has an analytically affine map over the stated extent',r.approximation_bound(p,[[-1000,-1000,-1000],[1000,1000,1000]])['affine_approximation_error_metres']==0)
    nonlinear=Usd.Stage.Open(byname['working-adjustment']['stage']);nr=Runtime(nonlinear,targets['ecef3'])
    fails('finite samples cannot certify a continuous nonlinear extent',lambda:nr.approximation_bound(nonlinear.GetPrimAtPath('/World/Asset'),[[-1000,-1000,0],[1000,1000,100]]))
    with Usd.EditContext(nonlinear,nonlinear.GetSessionLayer()):
        UsdGeom.Xformable(nonlinear.GetPrimAtPath('/World/Asset')).ClearXformOpOrder()
        nonlinear.GetPrimAtPath('/World').GetAttribute('crs:wkt').Set('GEODCRS[broken]')
    fails('invalid nearest enclosing binding is not bypassed for an identity adjustment',lambda:nr.placement(nonlinear.GetPrimAtPath('/World/Asset'),[[0,0,0]]))
    fails('invalid nearest enclosing binding also rejects inverse requests',lambda:nr.inverse_placement(nonlinear.GetPrimAtPath('/World/Asset'),[[6378137,0,0]]))
    climate=Usd.Stage.Open(byname['climate']['stage']);p=climate.GetPrimAtPath('/World/Data');record=read_source(p)
    yes('global domain has original 2664 values',len(record['values'])==2664)
    yes('global domain stays 2D with no observation time invented',record['coordinates'].shape==(2664,2) and not record['times'])
    yes('unknown original physical units remain unknown',record['measurement_units'] is None)
    fails('geographic coordinate support does not invent a scene frame',lambda:Runtime(climate,targets['geo2']).frame(p))
    fails('missing height fails 3D request',lambda:Runtime(climate,targets['ecef3']).convert(record['crs'],CRS.from_wkt(targets['ecef3']),record['coordinates']))
    original={l.identifier:l.ExportToString() for l in climate.GetUsedLayers()}
    with Usd.EditContext(climate,climate.GetSessionLayer()):p.GetAttribute('crs:wkt').Set(targets['utm32_2'])
    fails('external and composed CRS conflict fails',lambda:read_source(p));climate.GetSessionLayer().ImportFromString(original[climate.GetSessionLayer().identifier])
    with Usd.EditContext(climate,climate.GetSessionLayer()):p.CreateAttribute('crs:position',Sdf.ValueTypeNames.Double3).Set((100,200,300))
    fails('absolute samples never receive model anchor twice',lambda:read_source(p));climate.GetSessionLayer().ImportFromString(original[climate.GetSessionLayer().identifier])
    yes('railway preserves all 15822 horizontal vertices',len(results['railway']['dataset_coordinates'])==15822)
    yes('GeoTIFF PixelIsPoint and PixelIsArea resolve declared sample centers',np.max(abs(np.array(results['city']['dataset_coordinates'])-results['city-point']['dataset_coordinates']))<1e-10)
    mg,mp=results['multi-geographic'],results['multi-projected']
    yes('one external container retains separate selected coordinate domains',np.max(abs(np.array(mg['dataset_coordinates'])-mp['dataset_coordinates']))<1e-10 and mg['association']['domain']!=mp['association']['domain'])
    yes('CF measurement values and missing masks remain paired across domains',mg['measurement_sha256']==mp['measurement_sha256'] and mg['association']['mask']==mp['association']['mask'] and sum(mg['association']['mask'])==1)
    yes('CF observation times remain native metadata independent of USD time',mg['association']['times']['time']['values']==[0,3600] and mg['association']['times']['time']['units']=='seconds since 2026-10-05 00:00:00')
    yes('relative position uses output CRS rather than target model frame',np.max(abs(np.array(results['relative-position']['relative_position'])-[[0,-10,0]]))<1e-8)
    full=results['instances']['geometry'];masked=results['instances-masked']['geometry']
    for name in ['tower','terrain','composition','instances']:
        vertices=np.concatenate([np.array(v) for v in results[name]['geometry'].values()]);box=results[name]['polygonal_bounds']
        yes(name+' polygonal bounds enclose every resolved vertex',np.all(vertices>=box['min']) and np.all(vertices<=box['max']))
    yes('point instancers resolve every retained prototype copy',sum('/_ResolvedInstance' in p for p in full)==3)
    yes('invisible instance ID suppresses its geometry without reindexing survivors',sum('/_ResolvedInstance' in p for p in masked)==2 and not any('/_ResolvedInstance1/' in p for p in masked) and any('/_ResolvedInstance2/' in p for p in masked))
    # Composed carrier alone is readable with an unloaded payload, outside subtree content included by publisher.
    from .fixtures import claim
    payload=Usd.Stage.CreateNew(str(directory/'dependency-payload.usda'));payload.DefinePrim('/Payload','Xform');payload.GetRootLayer().Save()
    scene=Usd.Stage.CreateNew(str(directory/'dependency-assembly.usda'));root=scene.DefinePrim('/Interface','Xform');scene.SetDefaultPrim(root);claim(scene);scene.DefinePrim('/Outside','Xform').GetPayloads().AddPayload('./dependency-payload.usda','/Payload');scene.GetRootLayer().Save()
    unloaded=Usd.Stage.Open(str(directory/'dependency-assembly.usda'),load=Usd.Stage.LoadNone)
    yes('Profiles summary readable with outside unloaded payload',dependency(unloaded)['usage']=='hard' and not unloaded.GetPrimAtPath('/Outside').IsLoaded())
    # Authored unknown dependency conservatively retains hard; ordinary Core composition still permits a bad override, detected here.
    with Usd.EditContext(unloaded,unloaded.GetSessionLayer()):unloaded.GetDefaultPrim().SetCustomData({'profilesInfo':{'capabilityUsages':{'usd.geospatial.crsResolution':'soft'}}})
    fails('stronger layer cannot silently weaken required summary',lambda:dependency(unloaded))
    # Newly defined outcomes, checked against explicit geometry/metadata facts.
    shifted=np.array(results['city-adjusted-grid']['dataset_coordinates'])
    yes('adjusted imagery keeps native measurements',results['city-adjusted']['measurement_sha256']==results['city']['measurement_sha256'])
    yes('adjusted imagery keeps native coordinate bytes',results['city-adjusted']['source_coordinates_sha256']==results['city']['source_coordinates_sha256'])
    yes('adjusted imagery adds 25m east and 10m south in project axes',np.linalg.norm(shifted[0]-[500030,5499985])<1e-7)
    reset_geometry=results['prototype-reset']['geometry'];yes('prototype-child reset excludes the +100 prototype offset',np.linalg.norm(np.asarray(next(iter(reset_geometry.values())))[0]-[6378137,11,0])<1e-8)
    g=results['geographic-scene'];yes('geographic scene frame names Cartesian chart',g['frames']['/World/Model']['chart']=='associated geocentric Cartesian')
    yes('geographic bounds use the associated Cartesian scene chart',CRS.from_wkt(g['polygonal_bounds']['chart_wkt']).is_geocentric and g['polygonal_bounds']['min'][0]>6e6)
    independent=results['instances-independent-prototype']['geometry']
    yes('independently CRS-bound prototypes no longer fail',sum('/_ResolvedInstance' in key for key in independent)==2)
    # Conformance counterexample: D is model-local while A is a working adjustment.
    s=Usd.Stage.Open(byname['working-adjustment']['stage']);r=Runtime(s,targets['utm31']);child=s.GetPrimAtPath('/World/Asset/Child')
    local=r.placement(child,[[0,0,0]])[0];world=r.placement(child,[[0,0,0]],descendants_in_working=True)[0]
    yes('model-local versus raw working-child alternatives are distinguishable',np.linalg.norm(local-world)>4)
    from pathlib import Path
    (Path(directory).parent/'transform-order-comparison.json').write_text(json.dumps({'candidate':'model-local descendant','alternative':'raw working-axis descendant','candidate_coordinates':local.tolist(),'alternative_coordinates':world.tolist(),'difference_metres':float(np.linalg.norm(local-world)),'normative_authority':'Evaluation, requirements 9 and 15; alternative is not an adopted contract'},indent=2))
    glob=results['global-3d'];geo=results['global-3d-geographic']
    yes('synthetic global 3D keeps all positions and both observation times',len(glob['dataset_coordinates'])==154 and geo['association']['times']['time']['values']==[0,3600])
    yes('synthetic global height is explicit rather than inferred',all(abs(c[2]-100)<1e-8 for c in geo['dataset_coordinates']))
    yes('global geographic/ECEF outputs retain the same measurement values',glob['measurement_sha256']==geo['measurement_sha256'])
    # Normal transport has an independently known direction at the equator.
    s=Usd.Stage.Open(byname['basis-Z-1']['stage']);r=Runtime(s,targets['ecef3']);p=s.GetPrimAtPath('/World/Model')
    n=r.normal(p,[[0,0,0]],[[1,0,0]])[0]
    yes('normal follows geodetic attitude and output Cartesian axes',np.linalg.norm(n-[0,0,1])<1e-8)
    with Usd.EditContext(s,s.GetSessionLayer()):UsdGeom.Xformable(p).AddScaleOp(opSuffix='singular').Set((0,1,1))
    fails('singular normal map rejected',lambda:r.normal(p,[[0,0,0]],[[1,0,0]]))
    return checks
