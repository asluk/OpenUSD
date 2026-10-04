"""Verify receipt-bound delivery and record the reviewed presentation hashes."""
from pathlib import Path
import argparse, hashlib, json, re, shutil, subprocess, zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PREFIX='extras/usd/examples/usdGeospatialBuild/'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    for name in ['deck','pdf','validation']:
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    delivery=ROOT/'delivery'
    report=json.loads((delivery/'run-report.json').read_text())
    story=json.loads((delivery/'story.json').read_text())
    assert story['readme_sha256']==sha(ROOT/'README.md')
    assert story['run_receipt_sha256']==sha(delivery/'run-report.json')
    for name,expected in report['source_files'].items():
        assert sha(ROOT/name)==expected,'Source changed after execution: '+name
        # Git may normalize line endings. Verify that the frozen commit contains
        # the same text, while the receipt retains exact execution byte hashes.
        frozen=subprocess.check_output(['git','-C',str(ROOT),'show',report['source_commit']+':'+PREFIX+name])
        assert frozen.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),name
    validated=json.loads(Path(args.validation).read_text())
    assert validated['finalSha256']==sha(args.deck)
    assert validated['packageIntegrity']['status']=='pass'
    assert validated['presentationLayout']['exitCode']==0 and validated['presentationLayout']['finding_count']==0
    ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
    native=[]
    with zipfile.ZipFile(args.deck) as package:
        for number in range(1,8):
            node=ET.fromstring(package.read(f'ppt/slides/slide{number}.xml'))
            if node.findall('.//a:tbl',ns): native.append(number)
    assert native==[2,3,4,5,6]
    for file in [ROOT/'README.md',delivery/'pr-body.md',delivery/'story.json',ROOT/'QUALITY_REVIEW.md']:
        content=file.read_text(encoding='utf-8')
        assert not re.search(r'https://github.com/(?:PixarAnimationStudios/OpenUSD|[^/]+/OpenUSD-proposals)/(?:pull|issues)/\d+',content)
        assert not re.search(r'(?:C:|/Users/aluk|Documents/Codex)',content)
    shutil.copy2(args.deck,delivery/'geospatial-build.pptx')
    shutil.copy2(args.pdf,delivery/'geospatial-build.pdf')
    manifest={'readme_sha256':sha(ROOT/'README.md'),'run_report_sha256':sha(delivery/'run-report.json'),
      'proposal_source_commit':report['inputs']['proposal']['commit'],
      'executed_source_commit':report['source_commit'],
      'pptx_sha256':sha(delivery/'geospatial-build.pptx'),'pdf_sha256':sha(delivery/'geospatial-build.pdf'),
      'story_sha256':sha(delivery/'story.json'),'pr_body_sha256':sha(delivery/'pr-body.md'),
      'slides':7,'editable_native_table_slides':native,
      'proposal_ready':False,'requirements_build_complete':False,
      'tests':report['tests'],'scope_cases':len(report['scope_controls']),
      'scope_queries_per_reader':report['scope_queries_per_reader'],
      'placement_runtime_jobs':0,'exports':0,
      'structure_and_layout':'pass',
      'layout_warning_review':'The conservative native-table height estimate flags slide 3. Actual PowerPoint and PDF renders show the complete table with a clear gap before the following text.',
      'application_verification':'PowerPoint opened the final deck and exported all seven slides and the PDF.',
      'visual_review':'All slides inspected individually. Corrected one expanded-table overlap. Unchanged slides verified pixel-identical after correction. All PDF pages inspected.',
      'claim_boundary':'Defined CRS discovery only. Missing shared contracts stop placement. No Hydra/OV geometry, projection, export or geodetic accuracy claim.',
      'delivered_files':{p.relative_to(delivery).as_posix():sha(p) for p in sorted(delivery.rglob('*')) if p.is_file() and p.name!='collateral-manifest.json'}}
    (delivery/'collateral-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'proposal_ready':False,'source_provenance_verified':True,'native_table_slides':native,'manifest':sha(delivery/'collateral-manifest.json')},indent=2))

if __name__=='__main__': main()
