from pathlib import Path
import sys,json
from pxr import UsdProfiles
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT/'src'))
from fixtures import stage,wkt
from profiles import declare,CAPABILITY
from run_workflows import native,dump
s=stage();declare(s.GetDefaultPrim(),False,True);a=UsdProfiles.ClaimsAPI(s.GetDefaultPrim());info=a.GetProfilesInfo();info['capabilityUsages'][CAPABILITY]='soft';a.SetProfilesInfo(info);p=ROOT/'fixtures/control-soft-profile.usda';s.GetRootLayer().Export(str(p))
jobs=[{'kind':'convert','source_wkt':wkt(4979),'output_wkt':wkt(4978),'points':[[2,49]]},{'kind':'model','stage':str(ROOT/'fixtures/france.usda'),'path':'/World/Model','points':[[0,0]],'output_wkt':wkt(4978)},{'kind':'profiles','stage':str(p)},{'kind':'convert','source_wkt':' '+wkt(4979)+' ','output_wkt':wkt(4978),'points':[[2,49,80]]}]
r=native(jobs,'native-guards');assert r[0].get('code')=='coordinate-dimension' and r[1].get('code')=='coordinate-dimension' and r[2].get('state')=='unknown' and 'non-normal-wkt-spelling' in r[3].get('warnings',[]),r
dump('native-guards.json',{'passed':True,'checks':4,'results':r});print('4 native guard controls passed.')
