from pathlib import Path
import json
p=Path(__file__).parent
lines=(p/'plugInfo.json').read_text().splitlines()
obj=json.loads('\n'.join(x for x in lines if not x.lstrip().startswith('#')))
plugin=obj['Plugins'][0]
plugin.update(Type='resource',Root='.',ResourcePath='.')
plugin.pop('LibraryPath',None)
cap='usd.geospatial.crsResolution.v1';profile='usd.geospatial.publication.v1'
plugin['Info']['Profiles']={'Capabilities':{cap:{'name':'Geospatial CRS resolution v1','predecessors':['usd'],'docstring':'Proposed geospatial resolution capability; local test registration.'},profile:{'name':'Geospatial publication v1','predecessors':['usd'],'isProfile':True,'docstring':'Proposed declaration coverage contract; local test registration.'}}}
for name in ('GeoFreshGeospatialCRSBindingAPI','GeoFreshGeospatialDataSource'):
    plugin['Info']['Types'][name]['impliesCapabilities']=[cap]
(p/'plugInfo.json').write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
