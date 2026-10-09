from pathlib import Path
import json,hashlib,shutil,sys,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
W=Path('C:/Users/aluk/Documents/Codex/2026-09-21/have')
P=Path(__file__).resolve().parents[1]
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,default=W/'work/geospatial-revised-leans-run-20261008-v2');parser.add_argument('--assessment-dir',type=Path,default=W/'outputs/geospatial-revised-leans-20261008');args=parser.parse_args()
N=args.run.resolve();O=args.assessment_dir.resolve()
D=P/'delivery/revised-leans-20261008'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def table(h,rows):return '\n'.join(['| '+' | '.join(h)+' |','|'+'|'.join('---' for x in h)+'|',*['| '+' | '.join(str(x) for x in row)+' |' for row in rows]])
r=load(N/'delivery/run-report.json');c=load(O/'run-comparison.json');a=load(W/'outputs/geospatial-independent-audit-revised-leans-20261008/diagnostic-results.json');sc=load(O/'scope-audit/results.json');cl=load(O/'closure-audit/focused-counterexamples.json')
assert all(sha(P/f)==h for f,h in r['source_files'].items())
assert a['source_freeze_verified'] and a['native_binary_matches_completed_run'] and sc['source_freeze_verified']
assert not c['numeric_regressions'] and cl['checks_failed']==0
D.mkdir(parents=True,exist_ok=True)
py=load(N/'python-results.json');cpp=load(N/'native-results.json');diag={x['name']:x for x in a['cases']}
normal=diag['actual_projected_normal_sampling']['maximum_direction_difference_degrees']
count=sum(x['native_vs_python']['coordinate_count'] for x in r['metrics']);maximum=max(x['native_vs_python']['max_distance_metres'] for x in r['metrics'])
changes=[
 ['Repeated models','Each instance offset keeps its instancer-local meaning, including independently georeferenced prototypes.','Coincident bound/unbound models agree for translation, rotation and scale. Singular required inverses fail.'],
 ['Reusing a bake','The retained Cartesian context follows ordinary USD parent transforms until an authored reset.','A +100 m parent and an explicit reset agree with ordinary UsdGeom in both readers.'],
 ['Rotation over time','A half-turn needs an authored intermediate pose for interior-time resolution.','Equivalent +180/-180 endpoints both fail on ambiguity. Exact and held samples remain defined.'],
 ['Geographic measurements','A nonidentity ordinary adjustment requires an explicitly enclosing Cartesian project frame.','Geographic coordinates remain available. Missing context fails and supplied context produces the expected +1 m adjustment.'],
 ['Physical 3D distance','Use the datum\'s associated Earth-centred Cartesian coordinates. Report surface distance separately.','At 400 km ellipsoidal height, the control distinguishes 118.299 km physical separation from 111.319 km surface distance.'],
 ['Dependency summaries','Existing Profiles metadata distinguishes complete-empty, positive and unknown coverage.','Both readers distinguish the cases. Separate publisher controls detect a stale complete-empty retained-variant summary.'],
 ['Sampled bakes','A between-sample preservation claim identifies the reader interpolation setting and its covered bound.','The existing source-first trajectory control remains stable. No general continuous trajectory certificate is claimed.']]
def native_test(prefix):
 candidates=list((N/'pytest').glob(prefix+'*/adversarial.native.json'));assert candidates,prefix
 return [load(p) for p in sorted(candidates)]
instances=native_test('test_instancer_local_meaning_i')
translation=next(x for x in instances if abs(next(iter(x['geometry'].values()))[0][1]-10)<1e-7)
instance_displacements=[(np.array(v[0])-np.array([6378137,0,0])).tolist() for v in translation['geometry'].values()]
assert all(np.allclose(v,[0,10,0],atol=1e-7,rtol=0) for v in instance_displacements)
bakes=native_test('test_bake_reassembly_matches_o');bake_x=sorted(next(iter(x['geometry'].values()))[0][0] for x in bakes)
assert bake_x==[6378137.,6378237.]
physical=2*(6378137+400000)*math.sin(math.pi/360);surface=6378137*math.pi/180
examples=[]
for name,label,unit in [('France_01','France: CC49 to Lambert-93','m'),('Colorado_02','Colorado: State Plane to site grid','US survey ft')]:
 examples.append(dict(name=name,label=label,unit=unit,python=py[name]['queries'][0]['coordinates'][0],cpp=cpp[name]['queries'][0]['coordinates'][0]))
for name in ['tower','terrain']:shutil.copy2(N/'renders'/(name+'.png'),D/(name+'.png'))
g=py['global-3d-geographic'];coords=np.array(g['dataset_coordinates']).reshape(2,7,11,3)[0];values=np.array(g['measurement_values']).reshape(2,7,11)[0]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':15,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(10.5,4.8),layout='constrained');im=ax.pcolormesh(coords[:,:,0],coords[:,:,1],values,cmap='viridis',shading='nearest');ax.set(xlabel='Longitude (degrees)',ylabel='Latitude (degrees)',title='First observation time');fig.colorbar(im,ax=ax,label='Synthetic temperature (K)');fig.savefig(D/'global-temperature.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(8,4.8),layout='constrained')
for z,v in enumerate(instance_displacements):ax.scatter(v[1],v[2],s=280 if z==0 else 100,marker='o' if z==0 else 'x',c='#147D87' if z==0 else '#B76C2D',label='Unbound prototype' if z==0 else 'Independent georeference',linewidths=2)
ax.scatter(0,0,s=70,c='#536C7B',label='Shared initial origin');ax.set(xlabel='East displacement (m)',ylabel='North displacement (m)',xlim=(-1,12),ylim=(-2,2));ax.grid(alpha=.15);ax.legend(loc='upper left',frameon=False);fig.savefig(D/'instance-offset.png',dpi=180);plt.close(fig)
summary='The revised local proposal addresses the seven red-team concerns without changing the 31 functional requirements or adding geospatial attributes. Fresh tests support its instance and bake semantics, make unsupported requests explicit, and preserve the existing workflows. No additional undefined rule was found in the inspected paths. This is a scoped finding, not proof of exhaustive completeness.'
limits=[
 ['Normal transport',f'Confirmed prototype defect: one large projected face differs by {normal:.2f} degrees across its domain. Centroid sampling has no justified domain/error bound. The source already requires a faithful derivative or covered approximation.'],
 ['Near-half-turn numerics','The proposed failure rule is clear. The prototype\'s 64-epsilon guard lacks a demonstrated rotational uncertainty bound and a quantified native diagnostic.'],
 ['WKT quoted text','Confirmed shared prototype defect: a valid CRS name containing COORDINATEMETADATA is mistaken for a deferred epoch wrapper. Capability detection must use WKT structure, not quoted text.'],
 ['Publisher coverage','Retained-variant and unloaded-payload controls pass, including detection of a stale empty claim. This is not a production validator for every composition or variant combination.'],
 ['Consumer coverage','Python and C++ share PROJ and external-data decoding. Omniverse reuses Python. General material/primvar baking, physics and nonlinear continuous space/time certificates remain unverified or visibly unsupported.']]
review_choices=[
 ['Instance authoring','Review finite transport in the instancer frame, including the inverse requirement. It preserves Core input meaning.'],
 ['Geographic adjustments','Review the explicit Cartesian project context for absolute-domain adjustments. Geographic and global analytical access remain in scope.'],
 ['Publication contract','Review the proposed publishing-profile identity and maintenance obligations in existing Profiles metadata. Registration and group adoption remain pending.'],
 ['Orientation and comparison','Review the intermediate-pose policy and physical 3D versus horizontal surface metrics. HPR and detailed WKT string normalization remain proposed.']]
metrics=[['Contract tests',str(r['tests']['regressions_passed'])+' passed'],['Existing distinguishing controls',str(r['tests']['distinguishing_controls_passed'])+' passed'],['Coordinates per Python/C++ comparison path',f'{count:,}'],['Maximum Python/C++ physical difference',f'{maximum:.3g} m'],['Ordinary geometry/data exports',str(len(r['exports']))],['Native Hydra/Storm images',str(len(r['hydra']))],['Omniverse geometry writeback',f"{r['ov']['geometry_vertices']:,} vertices and {r['ov']['edit_checks']} edit/recovery checks"],['Prior output comparisons',f"{len(c['numeric_case_comparisons'])}, with no unexpected regression"],['Prior focused conformance controls',f"{cl['checks_passed']} passed"]]
readme='# USD geospatial proposal assessment\n\nUSD holds a model\'s shape. A coordinate reference system (CRS) explains a position on Earth.\n\n'+summary+'''

The model records inputs only: WKT, geographic/model placement and external-data
associations. Resolved positions and frames remain transient. The full local draft
is the execution authority. The terms/requirements baseline cannot substitute for
its data model and normative runtime rules.

## What the red-team review changed

'''+table(['Workflow','Proposed rule','Fresh evidence'],changes)+'''

These restrictions remain local leans for group review. The geographic adjustment
restriction affects an adjustment convention, not global data or larger-scale
analytical workflows. Coordinate epochs and scene-authored transformation-resource
controls remain deferred, with future extension paths preserved.

## Concrete reuse checks

A USD point instancer stores positions in its local model frame. With a shared
origin at longitude/latitude zero, [10, 0, 0] moves both prototypes ten metres east.
Both fresh readers recover Earth-centred displacement [0, 10, 0]. The older
candidate gave the independently bound prototype an upward displacement. The
new rule specifies full finite frame transport. A required unavailable inverse fails.

![Recorded instance displacement control](delivery/revised-leans-20261008/instance-offset.png)

A resolved ordinary USD bake retains its Cartesian context when referenced.
An ordinary +100 m parent affects both queries and ordinary viewers. An authored
reset at an Xformable boundary suppresses that parent. A typed CRS definition
alone does not reset transforms.

'''+table(['Assembly intent','Ordinary USD X (m)','Fresh Python/C++ X (m)'],[['Inherit +100 m parent','6,378,237','6,378,237'],['Authored ordinary reset','6,378,137','6,378,137']])+'''

These synthetic controls assess semantics. They do not establish surveyed locations.
Stable entrypoints and metadata above payloads follow the
[NVIDIA asset-structuring guidance](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html)
without prescribing a fixed hierarchy or redefining Core composition.

## Working workflows in this run

'''+table(['Path or check','Fresh evidence'],metrics)+'''

![Native Storm image of the resolved Eiffel model](delivery/revised-leans-20261008/tower.png)

![Native Storm image of resolved terrain](delivery/revised-leans-20261008/terrain.png)

These fresh native Hydra/Storm images read ordinary USD geometry baked from C++
results. They demonstrate the visualization path. They do not establish surveyed
placement, surface-normal accuracy, a geospatial Hydra filter or Omniverse rendering.
Python and C++ share PROJ and external-format decoding. Omniverse stage geometry
writeback reuses Python and verifies readback and edit/failure/recovery. It is not
a third placement implementation.

'''
for e in examples:readme+='### '+e['label']+'\n\n'+table(['Component ('+e['unit']+')','Python','C++'],[[label,f'{e["python"][i]:.6f}',f'{e["cpp"][i]:.6f}'] for i,label in enumerate(['East','North','Height'])])+'\n\n'
readme+='''## Analytical data beyond rendering

The synthetic global field retains 154 observations over two times, including
explicit height. Geographic and Earth-centred queries preserve values and native
array associations. A separate dimension-permutation control checks the shared
decoder against named dimensions. The original railway keeps its horizontal
workflow without inventing height semantics.

![Heatmap of newly recorded synthetic observations](delivery/revised-leans-20261008/global-temperature.png)

At 400 km ellipsoidal height, a one-degree equatorial separation measures
'''+f'{physical/1000:.3f} km'+''' in physical 3D, compared with
'''+f'{surface/1000:.3f} km'+''' along the ellipsoid surface. The draft names these
as distinct metrics and also reports angular components and height residuals.
A coordinate without height does not acquire an invented zero height.

## Implementation and verification limits

'''+table(['Topic','Finding'],limits)+'''

Six earlier defect counterexamples still pass after repair. Normal transport remains
the unresolved earlier defect. This run also found a native regex-stack failure on
longer WKT. The second execution uses a linear scanner and passes a 20,000-character
quoted-name regression. The failed first run remains preserved.

## Choices for group review

'''+table(['Topic','Disposition'],review_choices)+'''

The proposal states local outcomes and failures. Group review can accept or revise
them before treating the detailed model as adopted. The build loop now checks
semantics, publisher coverage and ordinary USD reuse beyond a field-name whitelist.

## Local review deck

[Slide deck](delivery/revised-leans-20261008/geospatial-build.pptx) and
[PDF](delivery/revised-leans-20261008/geospatial-build.pdf) present these same findings.

## Authority and evidence

'''+f"Proposal commit: {r['inputs']['proposal']['revision']}.\n\nExecution source commit: {r['source_commit']}.\n\nProposal SHA-256: {r['inputs']['proposal']['sha256']}.\n\nImmutable execution receipt SHA-256: {sha(N/'delivery/run-report.json')}.\n\n"+'''
Full authority: [proposal source](proposal/proposal-source.txt).
[31 requirement mappings](proposal/traceability.md).
[Fresh comparison](delivery/revised-leans-20261008/run-comparison.json).
[Earlier defect diagnostics](delivery/revised-leans-20261008/audit-diagnostics.json).
[Scope and publisher controls](delivery/revised-leans-20261008/scope-audit.json).
[Quoted WKT keyword control](delivery/revised-leans-20261008/quoted-keyword-audit.json).
[Uniform, pole and normal-form controls](delivery/revised-leans-20261008/closure-audit.json).
This is local evidence. No remote or communication updates belong to this run.

Eiffel mesh: SDC PERFORMANCE,
[Free La Tour Eiffel](https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
'''
(P/'README.md').write_text(readme,encoding='utf-8');(O/'README.md').write_text(readme,encoding='utf-8')
for src,dst in [(O/'run-comparison.json','run-comparison.json'),(W/'outputs/geospatial-independent-audit-revised-leans-20261008/diagnostic-results.json','audit-diagnostics.json'),(O/'scope-audit/results.json','scope-audit.json'),(O/'closure-audit/focused-counterexamples.json','closure-audit.json')]:shutil.copy2(src,D/dst)
shutil.copy2(O/'quoted-keyword-audit/results.json',D/'quoted-keyword-audit.json')
story=dict(readme_sha256=sha(P/'README.md'),proposal_sha256=r['inputs']['proposal']['sha256'],receipt_sha256=sha(N/'delivery/run-report.json'),proposal_revision=r['inputs']['proposal']['revision'],source_commit=r['source_commit'],summary=summary,changes=changes,limits=limits,review_choices=review_choices,metrics=metrics,examples=examples,instance_displacements=instance_displacements,bake_x=bake_x,physical_km=physical/1000,surface_km=surface/1000,normal_difference_degrees=normal,coordinate_count=count,maximum_difference_metres=maximum,slides=[
 dict(title='Geospatial proposal quality',paragraphs=[summary,'Local leans for group review. Authored input fields and the 31 functional requirements remain unchanged.']),
 dict(title='Instance offsets retain one meaning',image='instance-offset.png',paragraphs=['A local +X offset moves both coincident prototypes ten metres east, whether each has its own georeference or inherits one.','The draft specifies finite transport through the instancer frame. A required singular inverse fails.']),
 dict(title='Ordinary USD bake reassembly',table=[['Intent','Ordinary USD X (m)','Python / C++ X (m)'],['+100 m parent','6,378,237','6,378,237'],['Authored reset','6,378,137','6,378,137']],paragraphs=['A retained CRS identifies the Cartesian context. Ordinary USD determines transform inheritance and resets.']),
 dict(title='Geographic adjustment context',table=[['Request','Proposed outcome'],['Read geographic positions','Retain coordinates and native values'],['Adjust in an explicit Cartesian project frame','Apply the recorded ordinary adjustment'],['Adjust without a Cartesian project frame','Report unsupported adjustment']],paragraphs=['This limits one adjustment convention. Global data and analytical queries remain supported.']),
 dict(title='Physical 3D and surface distance',chart=True,paragraphs=['Two equatorial positions, one degree apart, both at 400 km ellipsoidal height.','The draft separates physical 3D separation from horizontal surface distance. Height remains explicit.']),
 dict(title='An authored rotation path',table=[['Authored poses','Resolved outcome'],['0 and +180 or -180 degrees','Ambiguous path fails'],['0, intermediate 90, then 180 degrees','Intermediate pose determines the path'],['Held reader or exact sample','Recorded pose remains defined']],paragraphs=['The source stores heading, pitch and roll. The reader computes a pose. The prototype uncertainty bound still needs evidence.']),
 dict(title='Dependency coverage with Profiles',table=[['Publisher declaration','Consumer interpretation'],['Complete summary, no retained use','Known none'],['Hard capability usage','Resolution dependency'],['Missing complete qualification','Unknown, conservatively hard']],paragraphs=['Existing Profiles metadata carries a proposed publishing profile. Publisher checks must cover retained variants and unloaded content. A metadata read alone cannot establish truth.']),
 dict(title='Working native visualization',images=['tower.png','terrain.png'],paragraphs=['Fresh native Hydra/Storm images of C++-resolved ordinary USD bakes.','They demonstrate the render path. Surface-normal accuracy remains a separate failed diagnostic.']),
 dict(title='Measurements retain native meaning',image='global-temperature.png',paragraphs=['The synthetic global field retains 154 observations over two times, with explicit height.','Geographic and Earth-centred results keep the same measurements. Named-dimension controls check the shared decoder.']),
 dict(title='Both readers resolve partner controls',examples=True,paragraphs=['Recorded components in the declared output units. Both placement readers share PROJ and external-data decoding.']),
 dict(title='Remaining prototype limits',table=[['Finding','Assessment'],['Surface lighting directions',f'{normal:.2f} degrees across one large projected face. Current sampling lacks an error bound.'],['Near-half-turn numerical guard','Correct failure, incomplete rotational uncertainty evidence'],['WKT quoted text','Both readers mistake a quoted name for a deferred epoch wrapper'],['Publication and consumer coverage','Selected controls pass. Broader composition and continuous coverage remains unverified']],paragraphs=['The proposal supplies rules for these outcomes. Passing prototype tests cannot establish exhaustive proposal quality.']),
 dict(title='Review choices and fresh evidence',table=[['Evidence','Result'],['Contract tests',str(r['tests']['regressions_passed'])+' passed'],['Coordinates compared per reader',f'{count:,}'],['Prior cases','No unexpected numerical regression'],['Omniverse writeback',f"{r['ov']['geometry_vertices']:,} vertices and {r['ov']['edit_checks']} edit checks"]],paragraphs=['Review instance transport, Cartesian adjustment context and the publishing-profile contract. HPR, the half-turn policy and comparison conventions remain proposed.'])])
save(D/'story.json',story);save(O/'assessment.json',dict(proposal_sha256=story['proposal_sha256'],receipt_sha256=story['receipt_sha256'],summary=summary,new_source_fields=[],unchanged_functional_requirement_count=31,limits=limits,review_choices=review_choices,source_frozen=True))
(P/'REVIEW.md').write_text('The local follow-up clarifies instance-local transforms, ordinary USD bake reuse and complete dependency summaries. It names geographic adjustment prerequisites, physical 3D comparison and ambiguous rotation outcomes. The 31 requirements and geospatial input fields remain unchanged.\n\nFresh controls support these leans. Existing workflows have no unexpected numerical regression. Normal-domain approximation, near-half-turn uncertainty and the quoted-WKT-keyword false rejection remain prototype limitations. The publishing-profile identity and detailed conventions require group review.\n',encoding='utf-8')
print(json.dumps({'readme_sha256':story['readme_sha256'],'slides':len(story['slides']),'coordinates':count,'max_error_m':maximum,'normal_difference_degrees':normal}))
