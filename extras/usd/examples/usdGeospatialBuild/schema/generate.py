"""Generate codeless schema packaging with stock usdGenSchema."""
import argparse,runpy,sys,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--generator',required=True);p.add_argument('--base-schema',required=True);a=p.parse_args();root=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='usd-geospatial-schema-') as d:
    source=Path(d)/'schema.usda';source.write_text((root/'schema.usda').read_text().replace('@usd/schema.usda@','@'+Path(a.base_schema).resolve().as_posix()+'@'))
    templates=Path(a.base_schema).resolve().parent.parent/'codegenTemplates'
    sys.argv=[a.generator,str(source),str(root/'generated'),'--templates',str(templates)]
    try:runpy.run_path(a.generator,run_name='__main__')
    except SystemExit as e:
        if e.code not in (0,None):raise
    p=root/'generated/plugInfo.json';p.write_text(p.read_text().replace('@PLUG_INFO_ROOT@','.').replace('@PLUG_INFO_RESOURCE_PATH@','.').replace('@PLUG_INFO_LIBRARY_PATH@',''))
