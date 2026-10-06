"""Verify provenance, inspected presentation and current delivery together."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,zipfile
import xml.etree.ElementTree as ET
from integration_evidence import verify_current_delivery, verify_executed_source
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
    process_changes=verify_executed_source(ROOT,report,collateral_only=bool(story.get('post_execution_process_documents')))
    assert process_changes==story.get('post_execution_process_documents',{}),'Process documents changed after derivation'
    validation=json.loads(Path(args.validation).read_text())
    assert validation['finalSha256']==sha(args.deck)
    assert validation['packageIntegrity']['status']=='pass' and validation['presentationLayout']['finding_count']==0
    assert validation['nativeChartValidation']['passed'] and validation['chartDataPackaging']['portable_chart_validation_passed']
    ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','c':'http://schemas.openxmlformats.org/drawingml/2006/chart'};tables=[];charts=[];deck_text=[]
    with zipfile.ZipFile(args.deck) as package:
        slides=sorted(name for name in package.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',name))
        assert len(slides)==len(story['slides'])==9
        for number in range(1,len(slides)+1):
            node=ET.fromstring(package.read(f'ppt/slides/slide{number}.xml'))
            if node.findall('.//a:tbl',ns):tables.append(number)
            if node.findall('.//c:chart',ns):charts.append(number)
            notes=package.read(f'ppt/notesSlides/notesSlide{number}.xml').decode()
            assert story['readme_sha256'] in notes and report['source_commit'] in notes
            assert story['integration_evidence_sha256'] in notes
        for name in package.namelist():
            if re.fullmatch(r'ppt/(?:slides/slide\d+|notesSlides/notesSlide\d+|charts/chart\d+)\.xml',name):
                node=ET.fromstring(package.read(name))
                deck_text.extend(node.itertext())
    integration=verify_current_delivery(ROOT,' '.join(deck_text))
    assert tables==[2,3,5] and charts==[6,7,8]
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
              'slides':9,'editable_native_table_slides':tables,'editable_native_chart_slides':charts,'proposal_ready':False,'requirements_build_complete':False,
              'tests':report['tests'],'cases_per_reader':len(report['scope_controls']),
              'queries_per_reader':report['scope_queries_per_reader'],'reader_query_checks':report['scope_queries_per_reader']*3,
              'full_placement_jobs':0,'resolved_scene_exports':0,
              'structure_and_layout':'pass','application_verification':'PowerPoint opened the final deck and exported all nine slides and the PDF.',
              'visual_review':'Every PowerPoint slide and exported PDF page inspected individually. Native coordinate charts, tables, diagrams and text are editable.',
              'collateral_revision':'Integration labels corrected from inspected call paths, using the same immutable execution. No new runtime execution.',
              'integration_evidence_sha256':sha(delivery/'integration-evidence.json'),
              'integration_claims':story['integration_claims'],'post_execution_process_documents':process_changes,
              'claim_boundary':'OpenUSD Python and C++ query results plus OpenUSD Python queries hosted in Omniverse. Shared PROJ. No full model geometry, OV geometry writeback, rendering or resolved-scene export in this run.',
              'delivered_files':{path.relative_to(delivery).as_posix():sha(path) for path in sorted(delivery.rglob('*')) if path.is_file() and path.name!='collateral-manifest.json'}}
    (delivery/'collateral-manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
    print(json.dumps({'source_provenance_verified':True,'native_tables':tables,'reader_checks':manifest['reader_query_checks'],'manifest_sha256':sha(delivery/'collateral-manifest.json')}))
if __name__=='__main__':main()
