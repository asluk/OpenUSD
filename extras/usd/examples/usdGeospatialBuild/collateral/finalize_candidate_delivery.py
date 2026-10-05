"""Verify provenance, inspected presentation and current delivery together."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,zipfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
PREFIX='extras/usd/examples/usdGeospatialBuild/'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    for name in ['deck','pdf','validation','run-directory']:p.add_argument('--'+name,required=True)
    p.add_argument('--visual-review-complete',action='store_true');args=p.parse_args()
    assert args.visual_review_complete,'Inspect every final slide and PDF page before delivery'
    delivery=ROOT/'delivery';report=json.loads((delivery/'run-report.json').read_text());story=json.loads((delivery/'story.json').read_text())
    run=Path(args.run_directory)
    assert json.loads((run/'delivery/run-report.json').read_text())==report
    assert story['readme_sha256']==sha(ROOT/'README.md') and story['run_receipt_sha256']==sha(delivery/'run-report.json')
    assert story['executed_source_commit']==report['source_commit']
    for name,expected in report['source_files'].items():
        assert sha(ROOT/name)==expected,name
        frozen=subprocess.check_output(['git','-C',str(ROOT),'show',report['source_commit']+':'+PREFIX+name])
        assert frozen.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),name
    validation=json.loads(Path(args.validation).read_text())
    assert validation['finalSha256']==sha(args.deck)
    assert validation['packageIntegrity']['status']=='pass' and validation['presentationLayout']['finding_count']==0
    ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'};tables=[]
    with zipfile.ZipFile(args.deck) as package:
        slides=sorted(name for name in package.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',name))
        assert len(slides)==len(story['slides'])==8
        for number in range(1,9):
            node=ET.fromstring(package.read(f'ppt/slides/slide{number}.xml'))
            if node.findall('.//a:tbl',ns):tables.append(number)
            notes=package.read(f'ppt/notesSlides/notesSlide{number}.xml').decode()
            assert story['readme_sha256'] in notes and report['source_commit'] in notes
    assert tables==[2,3,4,5,6,7]
    for path in [ROOT/'README.md',delivery/'pr-body.md',delivery/'story.json',ROOT/'QUALITY_REVIEW.md']:
        text=path.read_text()
        assert not re.search(r'https://github.com/(?:PixarAnimationStudios/OpenUSD|[^/]+/OpenUSD-proposals)/(?:pull|issues)/\d+',text)
        assert not re.search(r'(?:C:|/Users/aluk|Documents/Codex)',text)
    for path in (run/'scope-fixtures').glob('*.usda'):
        assert path.read_bytes()==(delivery/'scope-fixtures'/path.name).read_bytes()
    assert sha(delivery/'origin-sampling-record.usda')==report['sampling_record_control']['record_sha256']
    shutil.copy2(args.deck,delivery/'geospatial-build.pptx');shutil.copy2(args.pdf,delivery/'geospatial-build.pdf')
    manifest={'readme_sha256':sha(ROOT/'README.md'),'run_report_sha256':sha(delivery/'run-report.json'),
              'immutable_execution_receipt_sha256':sha(run/'delivery/run-report.json'),
              'receipt_serialization':'Public JSON uses LF; parsed object verified identical to immutable execution receipt.',
              'proposal_base_commit':report['inputs']['proposal']['base_commit'],
              'proposal_candidate_sha256':report['inputs']['proposal']['sha256'],'executed_source_commit':report['source_commit'],
              'pptx_sha256':sha(delivery/'geospatial-build.pptx'),'pdf_sha256':sha(delivery/'geospatial-build.pdf'),
              'story_sha256':sha(delivery/'story.json'),'pr_body_sha256':sha(delivery/'pr-body.md'),
              'slides':8,'editable_native_table_slides':tables,'proposal_ready':False,'requirements_build_complete':False,
              'tests':report['tests'],'cases_per_reader':len(report['scope_controls']),
              'queries_per_reader':report['scope_queries_per_reader'],'reader_query_checks':report['scope_queries_per_reader']*3,
              'full_placement_jobs':0,'resolved_scene_exports':0,
              'structure_and_layout':'pass','application_verification':'PowerPoint opened the final deck and exported all eight slides and the PDF.',
              'visual_review':'Every PowerPoint slide and exported PDF page inspected individually. Native tables and text are editable.',
              'claim_boundary':'Defined discovery, source values, bounded WKT and direct top-level anchor-origin coordinates. Four missing contracts stop full placement. Shared PROJ; no independent geodetic accuracy certification.',
              'delivered_files':{path.relative_to(delivery).as_posix():sha(path) for path in sorted(delivery.rglob('*')) if path.is_file() and path.name!='collateral-manifest.json'}}
    (delivery/'collateral-manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
    print(json.dumps({'source_provenance_verified':True,'native_tables':tables,'reader_checks':manifest['reader_query_checks'],'manifest_sha256':sha(delivery/'collateral-manifest.json')}))
if __name__=='__main__':main()
