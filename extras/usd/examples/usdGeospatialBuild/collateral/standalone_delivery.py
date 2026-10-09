"""One human assessment supplies the README, review body and slide story.

Run history belongs to the linked execution records. This explanation assesses
the whole pinned proposal and labels illustrations separately from evidence.
"""
from pathlib import Path
import hashlib, json

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '|'+'|'.join('---' for _ in headers)+'|', *['| '+' | '.join(str(v).replace('\n',' ') for v in row)+' |' for row in rows]])

def publish(root, facts, run_dir, output=None):
    root, run_dir = Path(root), Path(run_dir)
    receipt_path = run_dir/'delivery/run-report.json'
    receipt = json.loads(receipt_path.read_text())
    assert sha(receipt_path) == facts['receipt_sha256']
    assert sha(root/'proposal/proposal-source.txt') == facts['proposal_sha256'] == receipt['inputs']['proposal']['sha256']
    assert all(sha(root/name) == digest for name,digest in receipt['source_files'].items()), 'Execution inputs changed'
    proposal = (root/'proposal/proposal-source.txt').read_text(encoding='utf-8').splitlines()
    D = root/'delivery/revised-leans-20261008'
    opening = "USD describes a 3D model's shape and size. Geospatial information says where it belongs on Earth, so models, surveys and measurements can work together."
    assessment = "Proposal quality means that another implementer can derive the inputs, evaluation order and observable outcomes without guessing. The full draft specifies those rules for the workflows shown here."
    summary = "Selected demonstrations support the proposed behavior. Detailed conventions still need group review, and three prototype limitations remain. This evidence does not establish exhaustive completeness or independent geodetic accuracy."
    status_rows = [
        ['Data model and runtime rules', 'The draft separates authored inputs from computed results and defines placement, adjustment, query and bake behavior.'],
        ['Group alignment', 'The detailed orientation, frame, WKT string normalization and publication conventions remain proposed.'],
        ['Prototype limitations', 'Lighting directions lack an error bound. Rotation uncertainty is unquantified. A quoted CRS name causes false rejection.'],
        ['Verification coverage', 'Selected workflows and distinguishing controls support the rules. Broader composition and continuous space/time coverage remain unverified.']]
    inputs = [
        ['Model geometry', 'Shape and local distances, with declared units and up direction. In USD: points, metersPerUnit and upAxis.'],
        ['Coordinate reference', 'A CRS binding refers to WKT, the standard text description of the location\'s axes, units and height meaning.'],
        ['Geographic origin', 'crs:position locates the model origin. The illustrative example uses longitude 2.2945°, latitude 48.8584° and ellipsoidal height 80 m.'],
        ['Physical orientation', 'crs:orientation records heading, pitch and roll in degrees: which way the model faces and tilts against local east, north and up.']]
    cases=[]
    def case(id,title,question,rule,expected,observed,meaning,limit,heading,reqs,image=None,kind='evidence'):
        lines=[i+1 for i,line in enumerate(proposal) if line==heading]
        assert len(lines)==1,(id,heading)
        c=dict(id=id,title=title,question=question,rule=rule,expected=expected,observed=observed,implication=meaning,boundary=limit,clause_heading=heading,clause_line=lines[0],requirement_ids=reqs,kind=kind)
        if image:
            path,role,alt=image
            assert (root/'delivery'/path).is_file(),path
            c['image']=dict(path=path,role=role,alt=alt)
        cases.append(c)
    case('inputs','A geographic location for a 3D model',
         "Can a reader distinguish the model's shape from its location on Earth?",
         'The source records model geometry separately from its absolute origin and physical attitude. WKT supplies the coordinate meaning. Ordinary USD operations express intentional scaling and pivots.',
         'A reader can place the model without treating longitude or latitude as a distance or adding computed results to the source schema.',
         'The source stores position and one heading/pitch/roll tuple. Readers compute the physical pose, coordinate results and projection effects without writing them back.',
         'Inputs-only authoring gives the reader one authority for each meaning. The detailed field and pose conventions remain proposed.',
         'The illustrated position is an example, not a surveyed Eiffel location. No crs:scale is proposed.',
         '#### Authored properties',[9,10,12,14,15],kind='explanation')
    case('coordinates','One physical place, different coordinates',
         'Does changing coordinate systems preserve physical placement?',
         'A CRS conversion expresses the same physical location in different coordinates. The reader derives map convergence and local scale from the authoritative WKT and position.',
         'The coordinate numbers and units can change while the tower stays at the same physical place.',
         'Longitude, latitude and height become map coordinates. The physical site stays the same, while grid north and local scale can differ.',
         'A new coordinate representation has a defined physical meaning. The France and Colorado numerical controls test conversion separately from this illustration.',
         'It explains the rule and does not verify surveyed Paris placement.',
         '### Source placement evaluation and transform order',[9,12,13,16,19],('figures/03-crs-resolved.png','informative illustration','Eiffel model remains at the same physical location as its coordinate representation changes'),kind='illustration')
    child=json.loads((root/'delivery/transform-order-comparison.json').read_text())['difference_metres']
    case('adjustments','Ordinary model adjustments after placement',
         "In which coordinates do an author's scale, rotation and translation operate?",
         "Child transforms define the model's local geometry. Geospatial position and attitude place that geometry. The directly bound model's own xformOps then adjust the placed result in a fixed project chart, before conversion to the requested output.",
         'Changing the requested output CRS preserves the same physical adjustment. Child offsets continue to follow the model axes.',
         'The illustration scales by 1.15, rotates 20° and moves 120 m east and 60 m south. It shows adjustments on the directly bound model.',
         'The draft distinguishes project adjustments from model-local child offsets. A numerical control separates those interpretations by '+f'{child:.3f} m.',
         'The chart and reset conventions remain proposed. Ordinary pivots follow the authored USD stack.',
         '#### Evaluation',[9,14,15,17,19],('figures/05-usd-translate.png','informative illustration','Eiffel model moves after ordinary scaling and rotation, with its previous position outlined'),kind='illustration')
    case('readers','The same rules in two placement readers',
         'Can separate implementations derive the same coordinates from the proposed inputs and rules?',
         'Both readers use the composed source inputs and declared output CRS. Results include declared units and meaningful physical comparison.',
         'Python and C++ resolve the same partner points within the recorded comparison tolerance.',
         f"The readers compare {facts['coordinate_count']:,} coordinate results. The maximum measured physical difference is {facts['maximum_difference_metres']:.3g} m.",
         'These cases support reproducible interpretation of the proposed behavior. Agreement alone cannot establish all rules or all input layouts.',
         'Both readers use PROJ and share native dataset decoding. Agreement does not establish independent geodetic validation.',
         '### Extent and result comparison',[4,13,16,17,18,28,29])
    case('bake','Ordinary USD geometry for rendering',
         'Can a renderer use the result without implementing geospatial evaluation?',
         'An explicit bake resolves georeferencing into ordinary geometry and xformOps in a derived copy. A Cartesian coordinate context preserves location without an active source placement binding.',
         'An ordinary USD renderer displays the derived copy. The source scene retains its authored inputs.',
         'Native Hydra/Storm renders the C++-resolved Eiffel bake. A double-precision origin keeps local geometry small.',
         'The visualization path uses ordinary USD geometry. Reassembly controls confirm that a parent translation and an authored reset keep their USD meaning.',
         'Ground context is illustrative. The image does not establish surveyed placement or surface-normal accuracy.',
         '### Explicit export and sampling',[17,19,23,25,29],('revised-leans-20261008/tower.png','recorded native render','Native Hydra Storm image of the resolved ordinary USD Eiffel bake'))
    case('measurements','Measurements stay paired with their locations',
         'Can a native measurement dataset remain usable without rewriting values or guessing coordinate meaning?',
         'The scene identifies the native asset, field and coordinate domain. Resolution preserves the pairing of values, locations, missing-data masks and observation times.',
         'A measurement stays the same whether its location is returned geographically or in Earth-centred Cartesian coordinates.',
         'The global field returns geographic and Earth-centred positions for 154 samples, preserving native values and two observation times.',
         'The same data model supports global analytics as well as rendering. Named-dimension controls check the value/location association separately.',
         'Synthetic temperatures in kelvin. Both readers share decoding, so their agreement alone cannot verify the association.',
         '### External measurement association',[8,12,18,19,21,30],('revised-leans-20261008/global-temperature.png','plot of recorded synthetic data','Synthetic global temperature values at their recorded geographic locations'))
    case('colorado',"A construction site's own survey grid",
         "Can a project's local survey grid participate as a defined CRS?",
         'The source WKT describes how a calibrated site grid relates to a broader CRS, including its units and height meaning.',
         'Partner survey lines resolve into the site grid without redefining the model units or up direction.',
         'The original LandXML survey breaklines resolve and reach an ordinary USD bake rendered by Storm.',
         "The partner case exercises a site's calibrated CRS. Its WKT-carried calibration participates in resolution.",
         'The survey-line image does not establish independent survey accuracy or a continuous terrain-surface certificate.',
         '#### Decision on question 7: site calibration',[4,14,15,17],('revised-leans-20261008/terrain.png','recorded native render','Native Storm render of Colorado survey breaklines in the calibrated site grid'))
    case('railway','Horizontal railway placement',
         'Can incomplete source metadata still support a useful, explicitly horizontal workflow?',
         'The reader resolves a declared horizontal association and preserves uninterpreted third components. It does not invent a height reference.',
         'The horizontal railway copy resolves into UTM 32 while the original GeoJSON remains unchanged.',
         'The horizontal copy resolves 15,822 vertices across 2,386 parts. The plot uses offsets only for display.',
         'The draft supports horizontal resolution without inventing a height reference. The original third components remain uninterpreted.',
         'Horizontal coordinates only. The original third components remain uninterpreted and supply no physical 3D distance.',
         '### External measurement association',[8,12,19,21],('plots/railway.png','plot of recorded resolved geometry','Resolved UTM 32 horizontal railway coordinates with display-only offsets'))
    # The existing recorded control remains unchanged in the immutable execution.
    rpy=json.loads((run_dir/'python-results.json').read_text())
    def origin(name): return rpy[name]['queries'][0]['coordinates'][0]
    start,mid,end=[origin(name) for name in ['time-source-t0','time-source','time-source-t10']]
    chord=sum(((a+b)/2-c)**2 for a,b,c in zip(start,end,mid))**0.5
    case('animation','Animation evaluation order',
         'Does the proposal define the result between authored moments?',
         'Interpolate the authored source position first, then convert coordinates. Physical orientation uses composed heading/pitch/roll samples and shortest-arc pose interpolation.',
         'The midpoint follows the source-defined path. An ambiguous half-turn requires an intermediate authored pose for interior-time evaluation.',
         f'Equatorial longitude changes from 0° to 2°. Interpolating converted endpoints misses the source-first midpoint by {chord:.3f} m.',
         'The order is testable. Sample keys alone cannot certify the original trajectory between samples.',
         'The bake preserves time codes 0, 5 and 10 at 48 time codes per second. Continuous trajectory coverage remains unverified.',
         '#### Evaluation',[20,29])
    placements=[
        ['Physical orientation', 'One heading/pitch/roll tuple describes physical attitude against local east, north and up. Projection effects stay computed.'],
        ['Project adjustments', "The directly bound model's own xformOps adjust its placed result in a fixed project chart, including ordinary pivots."],
        ['Child objects', 'Child transforms define model-local geometry. Their offsets follow model axes and the geospatial attitude.'],
        ['Repeated models', 'Each instance offset retains its instancer-local meaning. Independent prototype placement participates once. A required unavailable inverse fails.'],
        ['Geographic scene results', "Geographic queries retain longitude/latitude/height. Cartesian geometry and bounds use the datum's Earth-centred frame."]]
    data=[
        ['Native data associations', 'Declare the asset, field and coordinate domain. Preserve named dimensions and observation times.'],
        ['WKT string normalization', 'Normalize lexical spelling without losing represented information. Equal tokens establish serialized identity.'],
        ['Semantic CRS comparison', 'Different normalized texts can represent equivalent CRSs. Comparison names its criteria and domain.'],
        ['Dependency declaration', 'Existing Profiles metadata carries a proposed complete publication summary, including unloaded and retained variant content.'],
        ['Baked coordinate context', 'Retain a Cartesian CRS and double-precision origin without an active source placement binding. Ordinary USD controls subsequent transforms.']]
    evidence=[
        ['Python and C++ readers', f"{facts['coordinate_count']:,} coordinate results per reader. Maximum measured difference {facts['maximum_difference_metres']:.3g} m. Shared PROJ and decoding."],
        ['Omniverse stage geometry', f"Reuses Python placement. Readback covers {receipt['ov']['geometry_vertices']:,} vertices and {receipt['ov']['edit_checks']} edit, failure and recovery checks across {receipt['ov']['jobs']} jobs."],
        ['Hydra / Storm', 'Two selected ordinary USD bakes reach native rendering using C++-resolved placements.'],
        ['Recorded tests', f"{receipt['tests']['regressions_passed']} contract tests and {receipt['tests']['distinguishing_controls_passed']} distinguishing controls pass. Separate diagnostics expose the reported prototype limits."],
        ['Source preservation', f"Original inputs and {len(receipt['source_files'])} frozen execution files remain unchanged. The immutable receipt identifies exact executed content."],
        ['Bake readbacks', f"{len(receipt['exports'])} selected exports checked. No general material/primvar, physics or continuous trajectory conformance is claimed."]]
    limits=facts['limits']
    by={c['id']:c for c in cases}
    def render_case(c):
        t=f"### {c['title']}\n\n**Question.** {c['question']}\n\n**Proposed rule.** {c['rule']}\n\n"
        if c.get('image'):
            im=c['image'];t+=f"![{im['alt']}](delivery/{im['path']})\n\n*{im['role'].capitalize()}. {c['boundary']}*\n\n"
        t+=f"**Expected behavior.** {c['expected']}\n\n**Observed result.** {c['observed']}\n\n**What this says about the proposal.** {c['implication']}\n\n"
        if not c.get('image'): t+=f"**Limit.** {c['boundary']}\n\n"
        t+=f"Proposal basis: [{c['clause_heading'].lstrip('# ')}](proposal/proposal-source.txt#L{c['clause_line']}). Functional requirements {', '.join(map(str,c['requirement_ids']))}.\n\n"
        return t
    text='# Geospatial proposal assessment\n\n'+opening+'\n\n'+assessment+'\n\n'+summary+'\n\n'
    text+='[Slides](delivery/geospatial-build.pptx) · [PDF](delivery/geospatial-build.pdf) · [Proposal snapshot](proposal/proposal-source.txt) · [Build loop](BUILD_LOOP.md)\n\n'
    text+='## What the proposal covers\n\nThe initial scope combines local model placement, partner survey coordinates and native measurement domains. It retains geographic queries and global analytical use. Coordinate epochs and scene-authored transformation-resource controls are deferred while preserving a path to future support. Unsupported requests report their limits rather than inventing coordinate meaning.\n\n'
    text+='## Source inputs and computed placement\n\n'+render_case(by['inputs'])+table(['Source information','Plain meaning'],inputs)+'\n\n'
    text+='WKT remains authoritative for coordinate meaning. Placement inputs add model position and physical attitude. Resolved positions, frames, projection scale and convergence are query results, not properties of the source schema. Intentional scaling and pivots use ordinary xformOps.\n\n'
    text+='## Demonstrations and their meaning\n\n'
    for k in ['coordinates','adjustments','readers','bake','measurements']: text+=render_case(by[k])
    for e in facts['examples']:
        rows=[[label,*[f"{e[n][i]:,.6f}" for n in ['python','cpp']]] for i,label in enumerate(['Map east coordinate','Map north coordinate','Height'])]
        text+=f"### {e['label']} ({e['unit']})\n\n"+table(['Resolved component','Python reader','C++ reader'],rows)+'\n\n'
    text+='## Proposal quality and its limits\n\n'+table(['Review dimension','Assessment'],status_rows)+'\n\n'
    text+='No additional undefined model rule was confirmed in the inspected paths. That is a bounded finding. Passing results and matching readers cannot establish exhaustive completeness, group adoption or independent geodetic truth.\n\n'
    text+='### Implementation and verification limits\n\n'+table(['Topic','Finding'],limits)+'\n\n'
    text+='The three prototype issues must be assessed against the proposed rules. A shortcut does not become a valid rule because both readers use it. Publisher controls cover selected retained variants and unloaded payloads. A metadata read alone cannot establish the truth of a completeness claim.\n\n'
    text+='## Supporting workflows\n\n'
    for k in ['colorado','railway','animation']: text+=render_case(by[k])
    text+='### Repeated models retain instance-local offsets\n\nThe draft expands a repeated model at its occurrence, keeps the prototype\'s independent geographic placement once, and transports the ordinary instance effect through the instancer frame. A required unavailable inverse fails.\n\n'
    text+='![Recorded instance displacement control](delivery/revised-leans-20261008/instance-offset.png)\n\nIn the synthetic control, an instancer-local +X offset moves two initially coincident prototypes ten metres east, whether they inherit a georeference or carry their own. Both readers return Earth-centred displacement [0, 10, 0] m. Rotation and scale controls also distinguish the frame choices. These controls establish the selected semantics, not surveyed placement or all instancer combinations.\n\n'
    text+='### Physical separation and surface distance\n\n'+f"At an explicit 400 km ellipsoidal height, a one-degree equatorial separation is {facts['physical_km']:.3f} km in physical 3D and {facts['surface_km']:.3f} km along the ellipsoid surface. The draft names these as distinct metrics. A horizontal-only coordinate supplies neither an invented zero height nor a physical 3D separation.\n\n"
    text+='### Reusing a resolved bake\n\nA +100 m ordinary parent moves a baked point from X = 6,378,137 m to 6,378,237 m. An authored reset retains X = 6,378,137 m. Both readers match ordinary UsdGeom. A typed CRS definition alone does not reset the ordinary stack. Stable entrypoints and metadata above payloads follow the [NVIDIA asset-structuring guidance](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html) without prescribing a fixed scene hierarchy.\n\n'
    text+='## Detailed conventions for group review\n\nThese are proposed definitions in the full draft. The demonstrations provide evidence for evaluating them; they do not make them adopted by the group.\n\n'+table(['Placement topic','Proposed meaning'],placements)+'\n\n'+table(['Data or declaration topic','Proposed meaning'],data)+'\n\n'
    text+='An absolute geographic measurement domain needs an explicit enclosing Cartesian project context for a nonidentity ordinary adjustment. Unadjusted geographic and Earth-centred queries remain supported, including global domains. Orientation follows the unique shorter physical arc. An exact half-turn needs an authored intermediate pose for an interior-time query, while exact-sample and held queries remain defined.\n\n'
    text+='The proposed publication profile distinguishes complete-empty (known none), positive capability usage and unqualified/absent summaries (unknown, conservatively hard). Writers and assemblers maintain truthful coverage through retained variants and unloaded content. Profile registration and adoption remain pending.\n\n'
    text+='## Evidence and its limits\n\n'+table(['Path or check','Recorded evidence'],evidence)+'\n\n'
    text+='There are two placement readers. Omniverse reuses Python with a verified stage geometry sink. Hydra consumes a C++-resolved ordinary USD bake. This evidence establishes no third independent engine, Omniverse rendering, geospatial Hydra filter or physics integration. Polygonal vertex/face bounds do not certify the continuous image of a curved source surface or a trajectory between baked samples.\n\n'
    text+='## Authority and reproduction\n\nThe README and deck explain the same pinned proposal and immutable execution. Collateral adds no normative authority.\n\n'
    text+=f"Proposal commit: `{facts['proposal_revision']}`. Proposal SHA-256: `{facts['proposal_sha256']}`. Execution source: `{facts['source_commit']}`. Immutable receipt SHA-256: `{facts['receipt_sha256']}`.\n\n"
    text+='[Receipt](delivery/run-report.json) · [31 requirement mappings](proposal/traceability.md) · [Diagnostic results](delivery/revised-leans-20261008/audit-diagnostics.json) · [Scope and publisher controls](delivery/revised-leans-20261008/scope-audit.json) · [Quoted WKT control](delivery/revised-leans-20261008/quoted-keyword-audit.json) · [Focused conformance controls](delivery/revised-leans-20261008/closure-audit.json)\n\n'
    text+='<details>\n<summary>Run comparison and execution history</summary>\n\n[Recorded comparison](delivery/revised-leans-20261008/run-comparison.json) separates intended contract effects from regressions. Historical failure and repair records remain in the immutable execution directories. They are supporting evidence, not the structure of this assessment.\n\n</details>\n\n'
    text+='`collateral/revised_leans_delivery.py` extracts pinned evidence. `collateral/standalone_delivery.py` supplies this shared explanation and slide story. `collateral/revised_leans_slides.mjs` renders the story without adding presentation-only technical claims. The delivery review checks standalone meaning, evidence boundaries, literal source wording and every rendered slide.\n\n'
    text+='Eiffel mesh: [SDC PERFORMANCE, Free La Tour Eiffel](https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The diagrams use illustrative positions and ground context. Partner-data credit and permission remain in [data documentation](data/README.md) and [partner license](data/LICENSE-partner.txt).\n'
    (root/'README.md').write_text(text,encoding='utf-8',newline='\n')
    review='This proposal separates local model geometry from its Earth location and defines how readers place models, preserve native measurement associations and create ordinary USD bakes. The README and deck assess the same inputs, observable rules and recorded demonstrations.\n\nSelected partner and global workflows support the proposed interpretation. Detailed conventions need group review. Normal-domain accuracy, half-turn numerical uncertainty and quoted-WKT classification remain prototype limits; broader coverage and independent geodetic accuracy are not established.\n'
    (root/'REVIEW.md').write_text(review,encoding='utf-8',newline='\n')
    story=dict(facts,readme_sha256=sha(root/'README.md'),narrative_version=2,opening=opening,assessment=assessment,summary=summary,cases=cases,input_rows=inputs,status_rows=status_rows,placement_choice_rows=placements,data_choice_rows=data,evidence_rows=evidence,chord_error_metres=chord,child_difference_metres=child,main_slide_count=8,appendix_slide_count=6,required_native_table_slides=[2,5,8,12,13,14],required_native_chart_slides=[11])
    story['slides']=[dict(title='Geospatial proposal assessment',kind='assessment'),*[dict(title=by[k]['title'],case=k,kind=by[k]['kind']) for k in ['inputs','coordinates','adjustments','readers','bake','measurements']],dict(title='Proposal quality and its limits',kind='quality'),*[dict(title='Appendix: '+by[k]['title'],case=k,kind=by[k]['kind']) for k in ['colorado','railway','animation']],dict(title='Appendix: Placement conventions',kind='placement_choices'),dict(title='Appendix: Data and declaration conventions',kind='data_choices'),dict(title='Appendix: Evidence and its limits',kind='evidence')]
    for p in [root/'delivery/story.json',D/'story.json']:
        p.write_text(json.dumps(story,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    if output:
        output=Path(output);output.mkdir(exist_ok=True,parents=True)
        (output/'README.md').write_text(text,encoding='utf-8',newline='\n')
    print(json.dumps({'readme_sha256':story['readme_sha256'],'slides':14,'frozen_files_verified':len(receipt['source_files'])}))
    return story

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    facts=json.loads((args.root/'delivery/revised-leans-20261008/story.json').read_text())
    publish(args.root,facts,args.run,args.output)
