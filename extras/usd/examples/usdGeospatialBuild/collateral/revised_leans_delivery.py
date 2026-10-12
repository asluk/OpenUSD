from pathlib import Path
import json,hashlib,shutil,sys,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
W=Path('C:/Users/aluk/Documents/Codex/2026-09-21/have')
P=Path(__file__).resolve().parents[1]
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,default=W/'work/geospatial-feedback-run-20261012-v1');parser.add_argument('--assessment-dir',type=Path,default=W/'outputs/geospatial-feedback-build-20261012');args=parser.parse_args()
N=args.run.resolve();O=args.assessment_dir.resolve()
D=P/'delivery/feedback-20261012'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def table(h,rows):return '\n'.join(['| '+' | '.join(h)+' |','|'+'|'.join('---' for x in h)+'|',*['| '+' | '.join(str(x) for x in row)+' |' for row in rows]])
r=load(N/'delivery/run-report.json');c=load(O/'run-comparison.json');a=load(W/'outputs/geospatial-independent-audit-feedback-20261012/diagnostic-results.json');sc=load(O/'scope-audit/results.json');cl=load(O/'closure-audit/focused-counterexamples.json')
assert all(sha(P/f)==h for f,h in r['source_files'].items())
assert a['source_freeze_verified'] and a['native_binary_matches_completed_run'] and sc['source_freeze_verified']
assert not c['numeric_regressions'] and cl['checks_failed']==0
D.mkdir(parents=True,exist_ok=True)
py=load(N/'python-results.json');cpp=load(N/'native-results.json');diag={x['name']:x for x in a['cases']}
normal=diag['actual_projected_normal_sampling']['maximum_direction_difference_degrees']
count=sum(x['native_vs_python']['coordinate_count'] for x in r['metrics']);maximum=max(x['native_vs_python']['max_distance_metres'] for x in r['metrics'])

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
limits=[
 ['Normal transport',f'Confirmed prototype defect: one large projected face differs by {normal:.2f} degrees across its domain. Centroid sampling has no justified domain/error bound. The source already requires a faithful derivative or covered approximation.'],
 ['Near-half-turn numerics','The proposed failure rule is clear. The prototype\'s 64-epsilon guard lacks a demonstrated rotational uncertainty bound and a quantified native diagnostic.'],
 ['WKT quoted text','Confirmed shared prototype defect: a valid CRS name containing COORDINATEMETADATA is mistaken for a deferred epoch wrapper. Capability detection must use WKT structure, not quoted text.'],
 ['Publisher coverage','Retained-variant and unloaded-payload controls pass, including detection of a stale empty claim. This is not a production validator for every composition or variant combination.'],
 ['Consumer coverage','Python and C++ share PROJ and external-data decoding. Omniverse reuses Python. General material/primvar baking, physics and nonlinear continuous space/time certificates remain unverified or visibly unsupported.']]
review_choices=[
 ['Instance authoring','Review finite transport in the instancer frame, including the inverse requirement. It preserves Core input meaning.'],
 ['Geographic adjustments','Review the explicit Cartesian project context for absolute-domain adjustments. Geographic and global analytical access remain in scope.'],
 ['Publication contract','Review the fixed v1 identities and approval ownership. Coverage and publisher maintenance have agreement. Registration and group adoption remain pending.'],
 ['Orientation and comparison','Review the intermediate-pose policy and physical 3D versus horizontal surface metrics. The HPR tuple is agreed; detailed interpolation and WKT string normalization remain proposed.']]
metrics=[['Contract tests',str(r['tests']['regressions_passed'])+' passed'],['Existing distinguishing controls',str(r['tests']['distinguishing_controls_passed'])+' passed'],['Coordinates per Python/C++ comparison path',f'{count:,}'],['Maximum Python/C++ physical difference',f'{maximum:.3g} m'],['Ordinary geometry/data exports',str(len(r['exports']))],['Native Hydra/Storm images',str(len(r['hydra']))],['Omniverse geometry writeback',f"{r['ov']['geometry_vertices']:,} vertices and {r['ov']['edit_checks']} edit/recovery checks"],['Prior output comparisons',f"{len(c['numeric_case_comparisons'])}, with no unexpected regression"],['Prior focused conformance controls',f"{cl['checks_passed']} passed"]]

for src,dst in [(O/'run-comparison.json','run-comparison.json'),(W/'outputs/geospatial-independent-audit-feedback-20261012/diagnostic-results.json','audit-diagnostics.json'),(O/'scope-audit/results.json','scope-audit.json'),(O/'closure-audit/focused-counterexamples.json','closure-audit.json'),(O/'quoted-keyword-audit/results.json','quoted-keyword-audit.json')]:
 shutil.copy2(src,D/dst)
facts=dict(proposal_sha256=r['inputs']['proposal']['sha256'],receipt_sha256=sha(N/'delivery/run-report.json'),proposal_revision=r['inputs']['proposal']['revision'],source_commit=r['source_commit'],limits=limits,review_choices=review_choices,metrics=metrics,examples=examples,instance_displacements=instance_displacements,bake_x=bake_x,physical_km=physical/1000,surface_km=surface/1000,normal_difference_degrees=normal,coordinate_count=count,maximum_difference_metres=maximum)
# Regenerate the railway image from this run's native indices and resolved coordinates.
rail=py['railway'];rc=np.asarray(rail['dataset_coordinates'],float);offset=rc.min(axis=0);fig,ax=plt.subplots(figsize=(10.5,5.4),layout='constrained');groups={}
for point,index in zip(rc,rail['association']['indices']):groups.setdefault(tuple(index[:-1]),[]).append(point)
assert len(groups)==2386 and sum(len(v) for v in groups.values())==15822
for group in groups.values():
 part=np.asarray(group)-offset;ax.plot(part[:,0],part[:,1],color='#157C87',linewidth=.8,alpha=.8)
ax.set(xlabel='Map east offset (m)',ylabel='Map north offset (m)',title='Horizontal railway coordinates in UTM 32');ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.12);fig.savefig(D/'railway.png',dpi=180);plt.close(fig)
from standalone_delivery import publish
publish(P,facts,N,O)
