"""Derive quality-first review body and slides from the canonical README."""
from pathlib import Path
import re,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'README.md').read_text(encoding='utf8');digest=hashlib.sha256((ROOT/'README.md').read_bytes()).hexdigest()
parts=re.split(r'^## (.+)$',text,flags=re.M);sections={parts[i]:parts[i+1].strip() for i in range(1,len(parts),2)}
slides=[{'title':'Geospatial proposal readiness','section':'Introduction','summary':parts[0].split('\n\n')[1],'content':parts[0],'kind':'readiness','images':[]}]
def page(title,section,kind,images=None,table_slice=None):
    slides.append({'title':title,'section':section,'summary':sections[section].split('\n\n')[0],'content':sections[section],'kind':kind,'images':images or [],'table_slice':table_slice})
page('The proposal still needs a shared contract','Contracts still missing from the proposal','gaps',table_slice=[0,5])
page('The remaining contracts span data and results','Contracts still missing from the proposal','gaps',table_slice=[5,10])
page('Why I did not stop during implementation','Why implementation did not stop','process')
page('Repairs remove shortcuts, not design decisions','Repairs and checks that did not require a new shared decision','repairs')
page('Placed measurements expose an unresolved dependency','A newly exposed dependency: placed measurement data','dependency')
page('A sampled error is not an extent guarantee','Extent and error remain a proposal gate','extent')
page('One authored dataset, three runtime results','The same authored data reaches three consumers','numeric')
page('Eiffel: see the model and its coordinate context','Eiffel: see the placement and its coordinate context','images',['tower-native.png','tower-plan.png'])
page('Complete CRS definitions support calibrated sites','Colorado and France: complete CRS definitions do real work','images',['terrain-native.png','colorado-terrain.png'])
page('City queries produce reusable analytic data','City analysis returns data, not just a picture','single',['city-analysis.png'])
page('Global data retains coordinates, values and time','Global measurements keep coordinates, values and time together','images',['global-ecef.png','climate-analysis.png'])
page('Real consumer edits and fresh-reader exports','Composition, edits and sampled export','single',['instances-native.png'])
page('Proposal closure governs the next derivation','What must be settled before proposal conformance','closure')
(ROOT/'delivery/story.json').write_text(json.dumps({'readme_sha256':digest,'native_table_slides':[2,3,7,8],'slides':slides},indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
intro=parts[0].split('\n\n')[1];execution=parts[0].split('\n\n')[3]
base='https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/'
body=f'''{intro}

{execution}

The review maps every requirement to evidence and remaining contracts. It also explains why the earlier implementation failed to stop: a frozen candidate was substituted for shared-proposal authority, known gaps did not block completion, and self-selected tests missed required coverage. The runner now stops by default on missing semantics; an explicitly labeled experimental run cannot certify proposal conformance.

Corrective evidence includes inherited-role validation, broken-binding failure, WKT string delimiter normalization, composed-default output, affine leaf bounds/relative frames and fresh exports preserving ordinary properties and standard instances. Adjusted absolute-coordinate measurement placement is stopped and flagged because its shared semantics are missing. Runtime agreement shares PROJ and finite samples do not establish the extent/error guarantee.

Read the [README]({base}README.md), [proposal quality review]({base}QUALITY_REVIEW.md), [editable slides]({base}delivery/geospatial-build.pptx), [PDF]({base}delivery/geospatial-build.pdf) and [run receipt]({base}delivery/run-report.json). The separate proposal cleanup remains an unpushed local review draft; this delivery does not update shared standard text. Coordinate epochs remain deferred, and larger-scale coordinate datasets remain initial-scope evidence.

README SHA-256: `{digest}`. This draft delivers audited experimental evidence; the proposal-readiness gate remains blocked.
'''
(ROOT/'delivery/pr-body.md').write_text(body,encoding='utf8',newline='\n');print('Derived',len(slides),'slides and PR body',digest)
