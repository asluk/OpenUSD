"""Derive review body and slide content from the canonical README, not code."""
from pathlib import Path
import re, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'README.md').read_text(encoding='utf8')
digest=hashlib.sha256((ROOT/'README.md').read_bytes()).hexdigest()
parts=re.split(r'^## (.+)$',text,flags=re.M)
sections={parts[i]:parts[i+1].strip() for i in range(1,len(parts),2)}
def first(name):
    return sections[name].split('\n\n')[0]
slides=[]
def page(title,section,kind,images=None):
    slides.append({'title':title,'section':section,'summary':first(section),'content':sections[section],'kind':kind,'images':images or []})
page('Geospatial meaning that survives USD composition','Eiffel: see the placement and its coordinate context','hero',['tower-native.png','tower-plan.png'])
page('Numbers alone do not place an asset','The problem: numbers alone do not place an asset','problem')
page('CRS meaning first. Ordinary USD transforms after.','Three authored facts, followed by ordinary transforms','model')
page('Complete CRS definitions do real work','Colorado and France: complete CRS definitions do real work','partner',['terrain-native.png','colorado-terrain.png'])
page('The same authored data reaches three consumers','The same authored data reaches three consumers','comparison')
page('City analysis returns data, not just a picture','City analysis returns data, not just a picture','city',['city-analysis.png','railway-query.png'])
page('Global coverage with coordinates and values intact','Global measurements keep coordinates, values and time together','global',['global-ecef.png','climate-analysis.png'])
page('Composition and live edits reach real consumers','Composition, edits and explicit export survive real consumption','consumption',['instances-native.png'])
page('Precision is measured. Extent needs a contract.','Precision is measured; a continuous extent bound remains open','precision')
page('Executed evidence separates choices from gaps','Remaining decisions and the path forward','decisions')
(ROOT/'delivery/story.json').write_text(json.dumps({'readme_sha256':digest,'slides':slides},indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
intro=parts[0].split('\n\n')[1]
evidence=parts[0].split('\n\n')[2]
body=f'''{intro}

{evidence}

The experiment freezes its data model and runtime rules before deriving code. It includes actual native Hydra rendering and transform readback, a separate live OV consumer, stock USD validation, partner CRS controls, city/global analytic products, source-edit/failure recovery and fresh-reader exports. Candidate choices remain labeled; R24's certified continuous extent/error bound remains a design gap.

See the [README](extras/usd/examples/usdGeospatialBuild/README.md), [editable slides](extras/usd/examples/usdGeospatialBuild/delivery/geospatial-build.pptx), [PDF](extras/usd/examples/usdGeospatialBuild/delivery/geospatial-build.pdf) and [run receipt](extras/usd/examples/usdGeospatialBuild/delivery/run-report.json). Coordinate epochs remain fully deferred; CRS frame epochs and ordinary supported datum/height transformations are retained.

README source SHA-256: `{digest}`. The draft is an implementation experiment for review, not approved standard text.
'''
body=body.replace('(extras/usd/examples/', '(https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/')
(ROOT/'delivery/pr-body.md').write_text(body,encoding='utf8',newline='\n')
print('Derived',len(slides),'slides and PR body from README',digest)
