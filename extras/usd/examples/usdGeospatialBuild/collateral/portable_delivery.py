"""Read relocated exports and reject unsupported integration claims."""
from pathlib import Path
import copy,hashlib,json,subprocess
import numpy as np

def verify(root,grids,validate_claims):
    root=Path(root);d=root/'delivery'
    from candidate.runtime import Runtime
    from candidate.datasets import resolved
    from candidate.execution import coordinate_error
    from pxr import Usd,Plug
    from pyproj import datadir,network
    Plug.Registry().RegisterPlugins(str(root/'schema/generated/plugInfo.json'))
    datadir.append_data_dir(str(grids));network.set_network_enabled(False)
    report=json.loads((d/'run-report.json').read_text(encoding='utf-8'))
    integration=json.loads((d/'integration-evidence.json').read_text(encoding='utf-8'))
    native=json.loads((d/'native-results.json').read_text(encoding='utf-8'));py=json.loads((d/'python-results.json').read_text(encoding='utf-8'))
    controls=[]
    for key,value in [('usd_placement_implementations',3),('ov_rendering',True),('hydra_live_crs_filter',True),('physics_integration',True),('whole_proposal_conformance',True),('independent_geodetic_validation',True),('continuous_nonlinear_extent_certificate',True)]:
        bad=copy.deepcopy(integration['claims']);bad[key]=value
        try:validate_claims(bad,report)
        except AssertionError:controls.append({'false_claim':key,'rejected':True})
        else:raise AssertionError('Claim gate accepted '+key)
    byname={j['name']:j for j in json.loads((d/'jobs.json').read_text(encoding='utf-8'))};portable=[]
    for name in ['geographic-scene','instances-independent-prototype']:
        receipt=next(x for x in report['exports'] if x['path'].endswith('/'+name+'.usda'));job=byname[name]
        s=Usd.Stage.Open(str(d/'exports'/(name+'.usda')));r=Runtime(s,job['output_wkt'],job['time']);actual=r.geometry()
        for new,old in receipt['source_paths'].items():assert coordinate_error(actual[new],native[name]['geometry'][old],job['output_wkt'])<.001
        assert not s.GetDefaultPrim().HasAPI('GeospatialCRSBindingAPI')
        portable.append({'name':name,'portable_fresh_reader_verified':True})
    for name in ['climate','multi-geographic','multi-projected','global-3d-geographic']:
        job=byname[name];s=Usd.Stage.Open(str(d/'exports'/(name+'.usda')));r=Runtime(s,job['output_wkt'],job['time']);assoc,coords=resolved(s.GetDefaultPrim(),r)
        expected=np.asarray([np.nan if x is None else x for x in py[name]['measurement_values']]);assert np.array_equal(assoc['values'],expected,equal_nan=True)
        assert coordinate_error(coords,py[name]['dataset_coordinates'],job['output_wkt'])<.001
        portable.append({'name':name,'portable_fresh_reader_verified':True})
    repo=root.parents[3];git=['git','-c','safe.directory='+repo.as_posix(),'-C',str(repo)]
    commit=subprocess.check_output(git+['rev-parse','HEAD'],text=True).strip()
    for name,digest in report['source_files'].items():
        blob=subprocess.check_output(git+['show',commit+':extras/usd/examples/usdGeospatialBuild/'+name])
        assert hashlib.sha256(blob).hexdigest()==digest,(name,'Commit differs from executed source')
    proof={'executed_source_content_commit':commit,'commit_blobs_match_immutable_freeze':True,'source_file_count':len(report['source_files']),
           'rejected_false_claim_controls':controls,'portable_export_readbacks':portable,'remote_mutations':[]}
    (d/'local-delivery-verification.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n')
    return proof
