"""Derive the current README from its receipt, then derive the body and slides."""
from pathlib import Path
import argparse, hashlib, json, re, shutil

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-directory',required=True)
    run=Path(parser.parse_args().run_directory)
    receipt=run/'delivery/run-report.json'
    report=json.loads(receipt.read_text())
    assert not report['completion']['proposal_ready'] and report['completion']['placement_execution_stopped']
    assert not report['completion']['experimental_execution_authorized'] and report['tests']['failed']==0
    assert report['placement_runtime_jobs']==report['hydra_placement_jobs']==report['ov_placement_jobs']==0
    assert not report['exports']
    for name,expected in report['source_files'].items():
        assert sha(ROOT/name)==expected,'Executed source changed: '+name
    destination=ROOT/'delivery'
    destination.mkdir(exist_ok=True)
    allowed={p.name for p in (run/'delivery').iterdir()}|{'scope-fixtures','story.json','pr-body.md'}
    assert {p.name for p in destination.iterdir()} <= allowed, 'Unexpected files in generated delivery'
    for file in (run/'delivery').iterdir():
        shutil.copy2(file,destination/file.name)
    shutil.copytree(run/'scope-fixtures',destination/'scope-fixtures',dirs_exist_ok=True)
    rows=report['scope_controls']; queries=report['scope_queries_per_reader']
    assert queries==sum(x['queries'] for x in rows)
    checks=queries*len(report['discovery_readers'])
    proposal=report['inputs']['proposal']['commit']
    text=f'''# Geospatial: defined CRS binding, blocked placement

The current shared proposal still needs exact authored definitions before a full placement build can follow it without guessing. This run stops dependent placement and executes the defined CRS discovery and composition behavior in three independent readers.

The editorial revision closes obsolete interface and transform-authoring contradictions. The remaining audit identifies eight narrower missing contracts and one existing 3D-versus-2D example inconsistency. It does not reopen agreed functional outcomes or treat internal implementation methods as standardized data.

Fresh evidence: {report['tests']['passed']} tests passed. Each reader passed {len(rows)} cases and {queries} queries, giving {checks} reader/query checks. Source layers and fixture bytes remained unchanged. This run executed zero projection or placement jobs and produced no resolved export.

[Editable slides](delivery/geospatial-build.pptx) · [PDF](delivery/geospatial-build.pdf) · [Receipt](delivery/run-report.json) · [Proposal audit](QUALITY_REVIEW.md) · [Build loop](BUILD_LOOP.md)

## What is already settled

| Authored fact or outcome | Existing answer |
|---|---|
| CRS authority | Complete WKT is authoritative. The typed definition stores uniform token crs:wkt. |
| Binding and composition | Applied binding uses a CRS reference. Nearest direct binding defines composed subtree scope. |
| Placement order | Separate CRS position, orientation and scale resolve before ordinary USD transforms. |
| Source and output | Preserve source facts and adjusted physical placement. The consumer selects the output CRS. |
| Stage conventions | Writers or assemblers author unit/up-axis correctives. Readers honor ordinary USD data. |

Geographic source positions and geographic coordinate queries are supported. Site calibration lives in a derived CRS definition. Engines select applicable operations, manage resources and report operation accuracy or visible failure. Explicit export preserves values, associations and sampling meaning. Coordinate epochs remain roadmap work.

## Missing authored representation

| Audit category | Exact contract still required |
|---|---|
| G02: placement fields | Names, types, defaults/requiredness, applicability, orientation/scale bases and mutual order. |
| G05: WKT string normalization | A prescribed serialized normal form that preserves the represented information. |
| G06: measurement coordinates | An authored association identifying source coordinates, including external assets. |
| G07: dependency declaration | A carrier and composition rule readable without traversal, including unloaded content. |
| G09: export sampling | A record distinguishing exported-sample interpolation from original-source resolution. |
| G10: existing inconsistency | Reconcile the 3D scope statement with two-axis WKT examples without silently broadening scope. |

Questions 2, 10, 11, 12 and 14 retain the specific representation work. The dimensionality inconsistency is existing proposal text, not a new restriction invented by this run. The fixtures use complete 3D definitions copied unchanged from the proposal.

## Missing observable definitions

| Audit category | Agreed outcome and narrower missing meaning |
|---|---|
| G03: project adjustments | Post-placement adjustments preserve physical placement. Their authored coordinate frame remains undefined. |
| G04: components and scene domain | E/N/up and geographic queries are settled. Other component mappings and geographic scene frames/bounds remain open. |
| G08: extent and agreement | State the approximation domain, how the claim is satisfied and how comparable operations are measured. |

Operation accuracy, numerical agreement and approximation over an extent are different claims. A full placement-chain accuracy estimate is not a requirement-28 obligation. Internal differentiation, caching or adapter design is implementation freedom. Missing consumer tests are verification work, not new design questions.

## A concrete composition result

| Queried prim | Nearest direct binding | Returned definition |
|---|---|---|
| /World/Data | /World | Geocentric ITRF2020 |
| /World/Independent/Data | /World/Independent | NAD83 grid with NAVD88 height |
| /World/Unmarked | /World | Geocentric ITRF2020 |
| /Assembly/Independent/Data | /Assembly/Independent | NAD83 grid with NAVD88 height |

The independent descendant keeps its own source CRS when the scene is referenced into an assembly. An unmarked WKT property does not establish a new binding. A stronger layer can override the enclosing composed definition without changing the independent child. Equivalent composed data keeps this interpretation after ordinary flattening. This is CRS discovery, not computed geospatial placement or resolved export.

## What this run executed

| Control group | Cases | Queries per reader |
|---|---:|---:|
| References and referenced assembly | 2 | 6 |
| Stronger layer, variant and inherits | 3 | 4 |
| Equivalent composed data | 1 | 2 |
| Unloaded payload | 1 | 2 |
| Missing, broken or invalid definitions | 5 | 5 |
| Total | {len(rows)} | {queries} |

Headless OpenUSD, independently written native C++ OpenUSD and a live OV stage each match authored expectations. The readers do not import one another's discovery function. Native discovery does not exercise Hydra placement. Live OV discovery does not ingest resolved geometry. The {report['tests']['passed']} tests also check the readiness gate, fixture field ownership and the previous resolver's incompatibility.

Partial checks reject absent binding, a broken nearest binding, wrong WKT type or variability and an empty definition. A broken nearest binding cannot fall back to an enclosing CRS. Available enclosing scope remains readable with a payload unloaded; content absent from that payload fails. These checks do not certify WKT normalization, the dependency declaration or whole-asset conformance.

## Why earlier passing tests were insufficient

The earlier freeze pinned private experimental answers, then tested code against those answers. A requirements-only intake excluded contradictory design text. Execution results became the headline despite known specification dependencies.

The prior relationship-based placement reader fails a reference-binding fixture from the shared proposal. This run exposes that mismatch and excludes the old placement candidate. Passing tests cannot substitute a private model for the shared data contract.

The default gate now stops dependent execution. It still finishes independently specified checks and delivers their receipt. No previous render, projected coordinate, export or test count is presented as evidence from this run. The remaining blockers are the named proposal contracts, not deferred mechanical work.

## Reproducing this run

The authoritative full proposal is `{proposal}`. Its verbatim Git blob is [proposal-source.txt](proposal/proposal-source.txt), SHA-256 `{report['inputs']['proposal']['sha256']}`. All 31 requirements have source-line traces. The executed source commit is `{report['source_commit']}`. Six derived documents and executed source files are hashed in the receipt.

Run `run.py --output <fresh-directory> --usd-sdk <native-USD-install> --native-python <linked-Python-DLL-directory> --native-build <configured-build> --ov-sdk <OV-install> --cmake <cmake>`. Use the native compiler environment. A successful specification-stopped run writes its receipt and returns exit code 2; test or runtime failures produce no successful receipt. `--experiment-with-open-specifications` cannot bypass this gate using the obsolete candidate.

The current delivery contains the exact source fixtures, independently returned definitions and execution receipt. Historical full experiments remain in Git history, including source `53d6f96ae7820c228438cd4523ff995f4148e244`. The current build does not relabel them as proposal conformance.
'''
    assert not re.search(r'https://github.com/[^\s)]+/(?:pull|issues)/\d+',text)
    (ROOT/'README.md').write_text(text,encoding='utf-8',newline='\n')
    canonical=(ROOT/'README.md').read_text()
    sections={}
    for section in canonical.split('\n## ')[1:]:
        heading,body=section.split('\n',1); sections[heading]=body.strip()
    headings=['What is already settled','Missing authored representation','Missing observable definitions',
              'A concrete composition result','What this run executed','Why earlier passing tests were insufficient']
    def content(section):
        parts=sections[section].split('\n\n')
        table=next((p for p in parts if p.startswith('|')),None)
        values=[] if not table else [[c.strip() for c in row.strip('|').split('|')] for row in table.splitlines() if not re.match(r'^\|[-|: ]+\|$',row)]
        return {'title':section,'values':values,'paragraphs':[p for p in parts if not p.startswith('|')],'readme_section':section}
    intro=[p for p in canonical.split('\n## ',1)[0].split('\n\n')[1:] if not p.startswith('[Editable')]
    story={'title':canonical.splitlines()[0][2:],'readme_sha256':sha(ROOT/'README.md'),
      'run_receipt_sha256':sha(receipt),'executed_source_commit':report['source_commit'],
      'slides':[{'title':canonical.splitlines()[0][2:],'values':[],'paragraphs':intro,'readme_section':'Opening'}]+[content(h) for h in headings]}
    (destination/'story.json').write_text(json.dumps(story,indent=2)+'\n')
    body=canonical.split('\n## What is already settled')[0]+'\n\n'+'\n\n'.join('## '+h+'\n\n'+sections[h] for h in headings[:3])
    body+='\n\n## Verification\n\n'+sections['What this run executed']+'\n\nExecuted source: `'+report['source_commit']+'`. Current receipt, fixtures and editable slides accompany the README. No placement or geodetic accuracy claim is made.\n'
    base='https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/'
    for local in ['delivery/geospatial-build.pptx','delivery/geospatial-build.pdf','delivery/run-report.json','QUALITY_REVIEW.md','BUILD_LOOP.md']:
        body=body.replace('('+local+')','('+base+local+')')
    (destination/'pr-body.md').write_text(body,encoding='utf-8',newline='\n')
    print(json.dumps({'readme_sha256':story['readme_sha256'],'slides':len(story['slides']),'scope_checks':checks},indent=2))

if __name__=='__main__':
    main()
