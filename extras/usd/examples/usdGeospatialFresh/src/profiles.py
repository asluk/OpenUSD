"""Profiles discovery reads claims only; publisher audit performs coverage work."""
import itertools
from scene import direct
from pxr import Usd,UsdProfiles,Vt
from errors import ResolutionFailure

CAPABILITY='usd.geospatial.crsResolution.v1'
PUBLICATION='usd.geospatial.publication.v1'

def declare(prim,required,complete=True):
    api=UsdProfiles.ClaimsAPI.Apply(prim)
    info={'capabilityUsages':{CAPABILITY:'hard'} if required else {}}
    api.SetProfilesInfo(info)
    if complete:api.SetProfileCompatible(PUBLICATION)

def discover(stage,entrypoint=None):
    root=stage.GetPrimAtPath(entrypoint) if entrypoint else stage.GetDefaultPrim()
    if not root:raise ResolutionFailure('missing-publication-entrypoint','No default/reference entrypoint')
    api=UsdProfiles.ClaimsAPI(root)
    info=api.GetProfilesInfo() if api else {}
    usages=info.get('capabilityUsages')
    hard=isinstance(usages,dict) and usages.get(CAPABILITY)=='hard'
    compatibility=info.get('profileCompatibility',{})
    complete=(isinstance(usages,dict) and isinstance(compatibility,dict) and isinstance(compatibility.get(PUBLICATION),Vt.TokenArray) and len(compatibility[PUBLICATION])==0 and (CAPABILITY not in usages or hard))
    state='required' if hard else ('known-none' if complete else 'unknown')
    return {'state':state,'hard_dependency':hard or state=='unknown','qualified_complete':complete,'payloads_loaded':sorted(str(p) for p in stage.GetLoadSet()),'entrypoint':str(root.GetPath()),'authored_info':info}

def publisher_audit(path):
    stage=Usd.Stage.Open(str(path),Usd.Stage.LoadAll)
    if not stage:raise ResolutionFailure('unavailable-publication',str(path))
    checks=[];required=False
    # The tested publications have finite retained alternatives. Enumerate
    # combinations rather than treating the selected alternative as coverage.
    sets=[]
    for prim in stage.TraverseAll():
        for name in prim.GetVariantSets().GetNames():
            choices=prim.GetVariantSet(name).GetVariantNames()
            sets.append((str(prim.GetPath()),name,choices))
    for choices in itertools.product(*(s[2] for s in sets)) if sets else [()]:
        with Usd.EditContext(stage,stage.GetSessionLayer()):
            for (prim_path,name,_),choice in zip(sets,choices):
                stage.GetPrimAtPath(prim_path).GetVariantSet(name).SetVariantSelection(choice)
        stage.Load()
        needed=any(direct(p) or p.GetTypeName()=='GeospatialDataSource' for p in stage.TraverseAll())
        required=required or needed
        checks.append({'variants':list(choices),'requires_geospatial':needed})
    claim=discover(stage)
    valid=not(required and claim['state']=='known-none')
    return {'valid':valid,'retained_requires_geospatial':required,'declaration':claim,'alternatives_checked':checks,'failure':None if valid else 'stale-known-none-publication'}
