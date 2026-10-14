from pathlib import Path
import json,re,hashlib,datetime
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
BASE=Path('C:/Users/aluk/Documents/Codex/2026-09-21/have');ROOT=BASE/'work/geospatial-fresh-20261014';OUT=BASE/'outputs/geospatial-fresh-build-20261014';OUT.mkdir(exist_ok=True)
def read(name):return json.loads((ROOT/'evidence'/name).read_text())
plt.rcParams.update({'font.family':'Arial','font.size':13,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#203744','text.color':'#203744','axes.titleweight':'bold','figure.facecolor':'white','axes.facecolor':'white'})
def save(fig,name):fig.savefig(OUT/name,dpi=180,bbox_inches='tight',facecolor='white');plt.close(fig)
rail=np.load(ROOT/'evidence/railway-resolved.npz',allow_pickle=True);p=rail['coordinates'];idx=rail['indices'];groups={}
for position,key in zip(p,idx):groups.setdefault(tuple(key[:-1]),[]).append(position)
origin=p.min(axis=0);fig,ax=plt.subplots(figsize=(8.2,5.2));ax.add_collection(LineCollection([(np.array(g)-origin)/1000 for g in groups.values() if len(g)>1],colors='#007f8b',linewidths=1.4));ax.autoscale();ax.set_aspect('equal');ax.set_xlabel('East from plotted origin (km)');ax.set_ylabel('North from plotted origin (km)');ax.set_title('Railway • resolved into Lambert-93',loc='left',pad=18);ax.grid(alpha=.12);save(fig,'railway-map.png')
city=np.load(ROOT/'evidence/city-resolved.npz');c=city['coordinates'];v=np.ma.array(city['values'].reshape(48,64),mask=city['mask'].reshape(48,64));fig,ax=plt.subplots(figsize=(8.2,5.2));im=ax.imshow(v,cmap='magma',extent=[np.nanmin(c[:,0]),np.nanmax(c[:,0]),np.nanmin(c[:,1]),np.nanmax(c[:,1])],origin='upper',interpolation='nearest');ax.set_title('Synthetic city heat field',loc='left',pad=18);ax.set_xlabel('Lambert-93 easting (m)');ax.set_ylabel('Lambert-93 northing (m)');ax.ticklabel_format(style='plain',useOffset=False);fig.colorbar(im,ax=ax,label='Temperature (°C)',shrink=.83);save(fig,'city-heatmap.png')
climate=np.load(ROOT/'evidence/climate-resolved.npz');values=np.ma.array(climate['values'].reshape(2,7,11),mask=climate['mask'].reshape(2,7,11));y,x=np.indices((7,11));lon=-150+x*30+y*.1;lat=-60+y*20+x*.05
fig,axes=plt.subplots(1,2,figsize=(11.2,4.2),sharey=True)
for t,ax in enumerate(axes):
 im=ax.scatter(lon,lat,c=values[t],cmap='plasma',vmin=270,vmax=287,s=105,marker='s');ax.set_xlim(-165,165);ax.set_ylim(-72,72);ax.set_title(['Observation 00:00','Observation 06:00'][t],loc='left');ax.set_xlabel('Declared longitude (°)');ax.grid(alpha=.12)
axes[0].set_ylabel('Declared latitude (°)');fig.subplots_adjust(right=.88,wspace=.15);fig.colorbar(im,cax=fig.add_axes([.91,.15,.02,.66]),label='Temperature (K)');save(fig,'climate-samples.png')
survey=np.load(ROOT/'evidence/survey-resolved.npz');c=survey['coordinates'];center=c.mean(axis=0);lon=np.arctan2(center[1],center[0]);lat=np.arctan2(center[2],np.hypot(center[0],center[1]));basis=np.array([[-np.sin(lon),-np.sin(lat)*np.cos(lon),np.cos(lat)*np.cos(lon)],[np.cos(lon),-np.sin(lat)*np.sin(lon),np.cos(lat)*np.sin(lon)],[0,np.cos(lat),np.sin(lat)]]);view=(c-center)@basis;starts=survey['starts'];segments=[view[a:b,:2] for a,b in zip(starts[:-1],starts[1:])];height=[view[a:b,2].mean() for a,b in zip(starts[:-1],starts[1:])];fig,ax=plt.subplots(figsize=(8.2,5.2));lines=LineCollection(segments,cmap='viridis',linewidths=1);lines.set_array(np.array(height));ax.add_collection(lines);ax.autoscale();ax.set_aspect('equal');ax.set_title('Colorado survey • absolute points resolved',loc='left',pad=18);ax.set_xlabel('Local view east (m)');ax.set_ylabel('Local view north (m)');ax.grid(alpha=.12);fig.colorbar(lines,ax=ax,label='View height relative to centre (m)',shrink=.83);save(fig,'colorado-survey.png')
provider=read('provider-controls.json');partner=read('provider-reader-comparison.json');tower=read('tower.json');profiles=read('profiles.json');measurements=read('measurements.json');immutability=read('immutability.json');ov=read('ov-writeback.json');export=read('fresh-export-checks.json');registration=read('profiles-generic-query.json')
suites=ET.parse(ROOT/'evidence/control-tests-final.xml').getroot().findall('testsuite');python_count=sum(int(x.attrib['tests'])-int(x.attrib.get('failures',0))-int(x.attrib.get('errors',0))-int(x.attrib.get('skipped',0)) for x in suites)
native_count=len(read('native-controls.json'))+read('native-guards.json')['checks']+read('focused-native-checks.json')['checks']+int(read('compound-geographic.json')['passed'])
assert all(x['passed'] for x in read('native-controls.json')) and read('native-guards.json')['passed'] and read('focused-native-checks.json')['passed']
provider_max=max(c['max_provider_error_m'] for c in provider if c['kind']=='provider-control');tower_max=max(m['max_reader_difference_m'] for m in tower['meshes']);rounding=max(c['float32_write_error_m'] for c in tower['bake']['controls'])
audit={'proposal_commit':'e51919927ced49b9c68bcd86160be468121f633d','candidate_generation':5,'assessment':'Fresh derivation supports the tested data model and normative placement contracts without new source fields or proposal changes. This is bounded evidence, not full conformance.','new_scene_meaning_gaps_found':[], 'clarification':{'topic':'USD Profiles integration','classification':'Registration/integration detail, not an unresolved placement rule','finding':'The publishing profile predecessor graph is unspecified. Labeled graphs change generic IsCompatibleWith results; empty qualified capability usage remains known-none under the proposal, even when this SDK generic query returns NoPath.','recommendation':'State that discovery reads qualified composed usage metadata, not generic compatibility status; supply the predecessor graph with registration and keep namespace review explicit.'},'prototype_limits':['General nonlinear derivative/vector/normal transport is not certified; unsupported requests fail.','Continuous surface/time bounds are not certified by finite vertices or samples.','Occurrence exporter refuses authored instance normals; material-graph closure is not claimed.','Full native-format coverage, conditional/nested variant publisher enumeration and formal ISO WKT grammar conformance are not established.','Native format decoder and PROJ are shared dependencies; the placement readers are independently written in Python and C++.'],'resolved_implementation_findings':['OGC-preferred WKT aliases initially chosen incorrectly; fixed from referenced productions.','Native grid-backed operations loaded an incompatible SDK PROJ library; pinned the TIFF-capable loader path.','Stale PROJ errors from probing missing alternate grids were mistaken for actual operation failures; reset immediately before transform.','Exporter retained unrequested point samples; clear and author only selected samples.','Native tuples could fill missing height with zero; enforce domain dimensions.','Malformed or soft geospatial usage could qualify as known-none; retain conservative unknown.'],'data_intake_findings':['Original climate file lacks CF role/unit/grid mapping metadata; reject it.','Original railway third coordinate lacks established vertical reference; horizontal derivative explicitly drops it, original preserved.','Eiffel asset cm metadata conflicts with producer-known metre geometry; explicit ordinary writer conformance is labeled.'],'evidence':{'python_contract_controls':72,'native_controls':15,'provider_coordinate_comparisons':187,'max_provider_error_m':provider_max,'max_dense_reader_difference_m':tower_max,'tower_vertices':tower['vertices'],'float32_write_error_m':rounding,'profiles_payloads_loaded':0,'originals_preserved':immutability['original_datasets_preserved'],'source_drift':immutability['candidate_source_drift'],'fresh_export_aware_unaware_difference_m':0.0,'storm':'Actual native HdStormRendererPlugin render of an ordinary C++-resolved viewing copy','omniverse':'Actual stage writeback/readback of fresh Python output through an external bridge; no Fabric/ovstage resolver'}}
audit['candidate_generation']=json.loads((ROOT/'generation-record.json').read_text())['candidate_generation'];audit['evidence']['python_contract_controls']=python_count;audit['evidence']['native_controls']=native_count;audit['resolved_implementation_findings']+=['Native compound geographic/vertical CRS was classified as Cartesian; inspect its horizontal coordinate system before applying the specified working chart. Regression now agrees within 5 nanometres.','Time-dependent operations escaped Python deferral because PROJ emitted bare parameter names; parse both string forms and reject missing-epoch operations.','Legacy GeoJSON CRS identifiers were substring-matched; require recognized complete spellings.']
audit['resolved_implementation_findings'] += ['Enclosing working binding role was not validated; reject non-Xformable bindings.', 'A model path shortcut through associated geocentric CRS bypassed an authored BOUNDCRS operation; route through the complete source CRS and test an analytic static shift.', 'Instance query receipts omitted authored IDs; retain ID/index and full prototype context.']
(OUT/'proposal-quality.json').write_text(json.dumps(audit,indent=2));(ROOT/'evidence/proposal-quality.json').write_text(json.dumps(audit,indent=2))
rows='\n'.join(f"| {c['region']} {c['source']} | {c['points']} | {c['max_provider_error_m']*1000:.3f} mm | {n['max_reader_difference_m']:.1g} m |" for c,n in zip([c for c in provider if c['kind']=='provider-control'],partner))
text=f'''# Geospatial in USD: proposal quality and demonstrated behavior

The proposal can now drive a fresh implementation of the tested placement, measurement and dependency-discovery contracts. The new Python and C++ placement readers resolve the same original provider data and dense Eiffel geometry without adding source properties or changing the proposal. This is stronger evidence of derivability than repairing an existing prototype. It is not proof of complete conformance or independent geodetic accuracy.

**Assessment:** no new scene-meaning gap was found in the exercised paths. One Profiles integration clarification remains useful: dependency discovery and a generic compatibility query answer different questions. Registration still needs its explicit graph and agreed identities. Prototype coverage limits remain visible below.

Authority: proposal commit `e51919927ced49b9c68bcd86160be468121f633d`; SHA-256 `276ae17d60e9b4801947525528c98cfac58b25a7e6ac5999dc01ddb60a2e83b9`. The proposal was unchanged during this run. This assessment and the deck derive from the same evidence.

## A USD model gains a location, without changing what its points mean

The mesh describes shape in ordinary local lengths. WKT describes how to interpret an Earth location. A direct binding associates that definition with a model; `crs:position` records its absolute origin and `crs:orientation` records physical heading, pitch and roll against local geodetic east/north/up. Intentional scale and pivots remain ordinary xformOps. Computed positions, convergence, scale and bounds are results, not additional source USD properties.

![Actual native Storm render of the C++-resolved Eiffel bake, with illustrative ground](tower-storm-final.png)

This is the original 163,416-vertex Eiffel asset. The location, 30° heading and 35 m east / 15 m north ordinary adjustment are explicit illustrative author inputs. The asset’s incorrect cm metadata receives a documented ordinary writer correction. Ground, sky, material override and viewing camera are presentation context, not a surveyed Paris dataset or placement proof. Geometry comes from the native C++ evaluation; Storm consumes ordinary USD.

## The order of operations is part of the contract

1. Evaluate composed source position and orientation at the requested USD time. Position follows Core interpolation; orientation interpolates endpoint physical poses on the shorter arc. An ambiguous half-turn needs an intermediate authored pose.
2. Apply ordinary descendant transforms to the local detail; convert stage lengths and up axis to metric model ENU.
3. Orient and place that detail in the source datum. Preserve the complete WKT’s projection, calibration, units and height reference.
4. Apply the directly bound anchor’s ordinary xformOps in its fixed working chart, after intrinsic placement. A direct child binding is an absolute anchor; ancestor ordinary transforms do not add another placement.
5. Express the result in the requested CRS. Geographic coordinate queries return angles/height; ordinary scene geometry uses the associated Cartesian chart and a recorded numeric origin where needed.

Reference/inherit CRS sharing, nested bindings, descendant reset stacks, layer time offsets, value clips, geographic scene charts and transported independently bound instances all have executed controls. An identity instance needs no invented instancer anchor. Nonidentity transport requires its specified context and inverse.

## WKT string identity and shared placement

Normalization removes spelling differences such as spacing, preferred keyword aliases and decimal formatting without deleting CRS content. Quoted names, axes, units and authored operations remain meaningful input. Equal normalized tokens establish text identity; different normalized text can still describe equivalent CRSs. Resolver equivalence and exact-token matching answer separate questions. An analytic static-shift control confirms that the complete authored WKT operation survives model placement.

A CRS definition shared through reference and one shared through inherit produce the same composed interpretation in both readers. A directly bound child keeps its own absolute placement; a parent’s 1,000 m ordinary translation does not add to it. For a repeated independently georeferenced prototype at the equator, the specified instancer frame carries a 10 m east offset exactly once. Storage ancestors do not move the occurrence. An identity occurrence keeps placement without requiring a fabricated frame; a nonidentity adjustment without its required frame fails. Results retain standard instance ID/index and prototype-relative context.

These are finite, executed distinctions, not a claim that every inverse or every instance normal is implemented. The library, nested-binding and point-instancer controls separate composition meaning from implementation convenience.

## USD Profiles: authors declare, publishers maintain, consumers discover

Profiles makes the geospatial dependency visible before a consumer loads content. It uses existing `ClaimsAPI` metadata, not a new geospatial property.

| Role | Action | Executed evidence |
|---|---|---|
| Author | Bind a model or native measurement; its schema implies the proposed capability. | Fresh codeless schema registration and composed bindings. |
| Publisher | Record the conservative union for retained content and variants, outside payloads. | Required, qualified known-none, unknown and deliberately stale publications. |
| Consumer | Read the qualified summary without scene traversal or payload loading. | Python and C++ report the same states with **zero loaded payloads**. |

Illustrative composed metadata on a publication’s default prim:

```usda
dictionary profilesInfo = {{
    dictionary capabilityUsages = {{
        string "usd.geospatial.crsResolution.v1" = "hard"
    }}
    dictionary profileCompatibility = {{
        token[] "usd.geospatial.publication.v1" = []
    }}
}}
```

These are proposed identities. A qualified, explicitly recorded usage dictionary without the geospatial entry is known-none. Missing qualification is unknown and retains a conservative dependency. A stale known-none claim hiding a retained bound variant is rejected by the publisher audit. Discovery reads the claim; it does not prove its truth. A bare CRS library is known-none; a complete ordinary geometry bake can be known-none; a retained native measurement still requires resolution.

The local registration uses a publishing-profile graph rooted at `usd`. A labeled alternative rooted at the geospatial capability changes the generic `IsCompatibleWith` result. In this SDK, an empty usage dictionary yields `NoPath` even with the completeness claim. Neither result changes the proposal’s explicitly defined discovery semantics. **Clarify the distinction and supply the final registration graph; do not add fake usages or change scene meaning to make the generic query pass.** Namespace stewardship and approval remain adoption work. See [Profiles documentation](https://openusd.org/release/user_guides/schemas/UsdProfiles/overview.html).

## Independent provider controls, separate from reader agreement

Expected coordinates come from the providers’ paired CSVs, matched by point ID. Python was not used as the expected answer. France projected/height, geographic and geocentric data and Colorado projection/site calibration retain their complete WKT operations. Local RAF20 and GEOID18 resources are used with network access disabled.

| Provider source | Points | Largest error against provider | Python–C++ difference |
|---|---:|---:|---:|
{rows}

The largest provider error is **{provider_max*1000:.3f} mm**, below the stated 2 mm test tolerance. Provider coordinates are rounded; these errors do not certify survey accuracy. Operation-attributed accuracy is 1 cm for the tested France height pipelines, 1.5 cm for the tested Colorado pipelines and unknown for the tested geographic/geocentric operation. Agreement and attributed accuracy are different quantities.

![Colorado absolute survey coordinates after resolution](colorado-survey.png)

The original LandXML supplies 14,359 absolute vertices in 710 parts, with north/east/height and US survey feet. A fresh producer importer maps those roles explicitly and resolves them without treating them as model offsets. The two readers agree exactly in the recorded output. LandXML is a producer import demonstration, not a fourth `data:format` in the schema. The local view is only a plotting convention.

## Native measurements keep values attached to the right locations

USD identifies a native asset, format, field and coordinate domain. The decoder uses explicit metadata roles and named dimensions; resolution changes the returned locations, not the values, masks or observation times.

![Original railway’s explicit horizontal derivative resolved to Lambert-93](railway-map.png)

The railway’s 15,822 coordinates are resolved horizontally. The original third components lack a confirmed height reference, so no 3D claim is made. The original file remains intact; the horizontal derivative is labeled.

![CF observations with values, masks and times retained](climate-samples.png)

The synthetic CF example has 154 samples, one masked, deliberately permuted coordinate dimensions and two observation times. All 153 valid samples agree between placement readers. The supplied original climate file lacks the role/unit/grid-mapping metadata needed for this association and is correctly rejected. Observation times are not coordinate epochs.

![Synthetic city GeoTIFF heat field](city-heatmap.png)

The GeoTIFF example retains all 3,072 cells and 24 masks; its 3,048 valid sample locations agree. Pixel centres and 2D height absence have separate controls. The native readers share this newly written format decoder; they do not share placement evaluation. These plots are analytics presentations, not Hydra or Omniverse renders.

## Two placement readers; explicit integration paths

| Path | What actually ran | Limit of the claim |
|---|---|---|
| Python reader | New composed-USD evaluator with PROJ. | Shared PROJ and native-format decoder. |
| Native C++ reader | New native USD-stage evaluator with independently written placement math and PROJ calls. | Common geodetic engine; not an independent geodetic oracle. |
| Omniverse stage writeback | External fresh Python results bridged into an Omniverse stage, then read back for all 163,416 vertices. | Integration, not a third placement engine or Fabric/ovstage resolver. |
| Native Hydra/Storm | `HdStormRendererPlugin` rendered a viewing copy of the C++ ordinary USD bake. | No geospatial Hydra filter was implemented. |

Dense Eiffel reader differences are at most **{tower_max:.2g} m**. The float32 write/readback error is at most **{rounding*1000:.3f} mm**, reported separately. Fresh C++ and Python readers and an ordinary USD reader recover the same selected baked vertices; the double origin appears once. An explicit bake contains the actual Cartesian CRS definition and ordinary geometry/transforms in a derived copy. It is not a private “already resolved” flag.

## What the proposal audit found

**{python_count} Python controls and {native_count} native controls pass**, alongside provider, sharing, dense-geometry and fresh-export checks. The post-implementation audit caught and repaired incorrect preferred WKT aliases, a native library collision, stale operation errors, unrequested export samples, short 3D tuples and malformed Profiles qualifications. Their remedies came from existing normative text and primary library/specification references. No new source schema fields or model decisions were inserted to excuse the implementation.

WKT normalization uses the referenced OGC-preferred keywords, exact lexical decimal rewriting and quoted-content preservation. Text identity remains separate from CRS equivalence. Readers warn about supported valid non-normal WKT; they leave source layers unchanged. See [OGC WKT2](https://docs.ogc.org/is/18-010r11/18-010r11.pdf).

The required implementation choices are recorded: codeless plugin registration, PROJ operation factory and local resource search, interval arithmetic for the ambiguous orientation test, finite-point evaluation, and ordinary exporter hierarchy. Those choose algorithms or integration; they do not choose new source meaning. The publishing-profile graph is explicitly labeled as a local registration choice pending clarification.

**Limits:** nonlinear derivatives, general vector/normal transport and continuous surface/time bounds are not certified; their unsupported paths fail visibly. The occurrence exporter refuses authored instance normals and does not claim arbitrary material-graph closure. Complete native-format coverage, nested conditional-variant enumeration and formal ISO grammar validation are not demonstrated. Successful sample queries do not close those implementation/coverage limits. Coordinate-epoch wrappers remain deferred and are negative controls, preserving a path to later support.

## Reproducibility and delivery

The geospatial source, schemas, adapters and fixture writers were newly authored from the pinned proposal. Original data and generic libraries/tooling were reused. No previous geospatial implementation source or output was consulted before the first candidate freeze. Corrective generations have retained provenance receipts. Previous delivery collateral was inspected only after freezing, to match its human clarity.

All original dataset hashes and the proposal hash remain unchanged. The final candidate hash audit reports no source drift. This is one agent’s fresh derivation, not a blinded separate-implementer study. Earlier runs were incremental and are not relabeled as fresh.

Evidence is in `evidence/`; source-to-contract trace is in `authority/derivation.md`; generation inputs and hashes are in `generation-record.json`. Build the native reader with `native/build.cmd`, generate fixtures with `tests/fixtures.py` and `tests/make_workflows.py`, run the contract controls, then `tests/run_workflows.py` and `tests/native_controls.py`. The recorded Windows environment uses the generic USD SDK, the TIFF-enabled PROJ library and offline resources identified in the manifest. The deck is derived from this README and the same numerical receipts. It is a local deliverable; nothing was pushed or posted.

Eiffel asset credit: original Sketchfab asset and its embedded CC BY 4.0 attribution are retained. Partner dataset license: `data/LICENSE-partner.txt`.
'''
text=text.replace('short 3D tuples and malformed Profiles qualifications','short 3D tuples, compound geographic chart classification, epoch-boundary leakage, native CRS identification, malformed Profiles qualifications, bypassed authored WKT operations and missing instance identity')
(OUT/'README.md').write_text(text,encoding='utf-8');(OUT/'profiles-clarification-draft.md').write_text('''Proposed editorial clarification for the Profiles section:

“Dependency discovery reads the composed completeness qualification and capability usages. A registry path or generic compatibility-query status alone establishes neither known-none nor the truth of coverage. The contribution must supply the registered publishing-profile predecessor graph, without changing these declaration semantics.”

This clarifies the existing raw-metadata contract. Selecting and approving the final registration graph and identities remains explicit adoption work; the current local plugin graph is a labeled integration choice.
''',encoding='utf-8')
print(json.dumps(audit['evidence'],indent=2))
