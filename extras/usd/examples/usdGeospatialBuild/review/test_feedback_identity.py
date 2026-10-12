"""Fixed identity controls from the proposal's publication contract.

The v2 metadata below is a distinguishing counterexample, not a future model.
"""
from pathlib import Path
import json,subprocess,sys
from pxr import Plug,UsdProfiles,Usd,Vt
from candidate.fixtures import claim
from candidate.runtime import dependency

ROOT=Path(__file__).resolve().parents[1]
V1='usd.geospatial.crsResolution.v1'
PROFILE='usd.geospatial.publication.v1'

def test_schema_implications_and_registered_profile_match_pinned_identity():
    Plug.Registry().RegisterPlugins(str(ROOT/'schema/generated/plugInfo.json'))
    for name in ['GeospatialCRSBindingAPI','GeospatialDataSource']:
        schema=Usd.SchemaRegistry.GetTypeFromName(name)
        assert V1 in UsdProfiles.ProfileRegistry.GetSchemaImpliedCapabilities(schema)
    assert UsdProfiles.ProfileRegistry.IsProfile(PROFILE)

def test_new_identity_does_not_reinterpret_existing_requirement(tmp_path):
    Plug.Registry().RegisterPlugins(str(ROOT/'schema/generated/plugInfo.json'))
    node='usd.geospatial.crsResolution.v2'
    plugin={'Plugins':[{'Name':'FixedIdentityCounterexample','Type':'resource','Root':'.','ResourcePath':'.','Info':{'Profiles':{'Capabilities':{node:{'name':'Future identity counterexample','docstring':'No future scene semantics are defined by this test.','predecessors':['usd']}}}}}]}
    (tmp_path/'plugInfo.json').write_text(json.dumps(plugin),encoding='utf-8')
    # Profiles discovers registrations at startup. Use a fresh reader with both
    # resources present before its first registry query.
    code="from pxr import Plug,UsdProfiles; import sys,json; [Plug.Registry().RegisterPlugins(p) for p in sys.argv[1:3]]; print(json.dumps([str(UsdProfiles.ProfileRegistry.ResolveCapability(p)) for p in sys.argv[3:]]))"
    actual=json.loads(subprocess.check_output([sys.executable,'-c',code,str(ROOT/'schema/generated/plugInfo.json'),str(tmp_path/'plugInfo.json'),V1,node],text=True))
    assert actual==[V1,node]
    stage=Usd.Stage.CreateInMemory();root=stage.DefinePrim('/Asset','Scope');stage.SetDefaultPrim(root);claim(stage)
    before=root.GetCustomData()
    assert dependency(stage)['capability']==V1
    assert dependency(stage)['usage']=='hard'
    assert root.GetCustomData()==before

def test_unqualified_version_does_not_certify_complete_empty(tmp_path):
    stage=Usd.Stage.CreateInMemory();root=stage.DefinePrim('/Asset','Scope');stage.SetDefaultPrim(root);claim(stage,required=False)
    info=root.GetCustomData();info['profilesInfo']['profileCompatibility']={'usd.geospatial.publication.v2':Vt.TokenArray()}
    root.SetCustomData(info)
    result=dependency(stage)
    assert result['coverage']=='unknown' and result['usage']=='hard'
    assert not result['known_none']
