"""Verify executed evidence and README-derived collateral before publication."""
from pathlib import Path
import argparse, hashlib, json, re, zipfile

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--presentation-validation',required=True)
    p.add_argument('--visual-review-complete',action='store_true');a=p.parse_args()
    assert a.visual_review_complete,'Inspect every final slide and PDF page before declaring review complete'
    report=json.loads((ROOT/'delivery/run-report.json').read_text())
    story=json.loads((ROOT/'delivery/story.json').read_text())
    validation=json.loads(Path(a.presentation_validation).read_text())
    digest=sha(ROOT/'README.md');assert digest==story['readme_sha256']
    for name,h in report['source_files'].items():assert sha(ROOT/name)==h,name
    for name,h in report['delivery_files'].items():assert sha(ROOT/'delivery'/name)==h,name
    assert validation['packageIntegrity']['exitCode']==0 and validation['presentationLayout']['exitCode']==0
    assert validation['finalSha256']==sha(ROOT/'delivery/geospatial-build.pptx')
    total=len(story['slides'])
    with zipfile.ZipFile(ROOT/'delivery/geospatial-build.pptx') as z:
        assert sum(bool(re.fullmatch(r'ppt/slides/slide\d+\.xml',n)) for n in z.namelist())==total
        assert all(digest in z.read(f'ppt/notesSlides/notesSlide{i}.xml').decode() for i in range(1,total+1))
        assert all('<a:tbl>' in z.read(f'ppt/slides/slide{i}.xml').decode() for i in [5,9])
        texts=[z.read(n).decode() for n in z.namelist() if n.endswith('.xml')]
    for root in [ROOT/'delivery',ROOT/'proposal']:
        texts.extend(q.read_text(encoding='utf8') for q in root.rglob('*') if q.is_file() and q.suffix in ['.json','.md','.usda','.geojson'])
    texts.append((ROOT/'README.md').read_text(encoding='utf8'))
    for text in texts:
        assert not re.search(r'https?://github\.com/(?:PixarAnimationStudios|Tamrat-B)/(?:OpenUSD|OpenUSD-proposals)/(?:pull|issues)/',text)
        assert not re.search(r'[A-Z]:[\\/]+Users[\\/]+',text)
    result={'readme_sha256':digest,'run_report_sha256':sha(ROOT/'delivery/run-report.json'),
            'executed_source_commit':report['source_commit'],
            'pptx_sha256':sha(ROOT/'delivery/geospatial-build.pptx'),
            'pdf_sha256':sha(ROOT/'delivery/geospatial-build.pdf'),
            'story_sha256':sha(ROOT/'delivery/story.json'),
            'pr_body_sha256':sha(ROOT/'delivery/pr-body.md'),
            'slides':total,'editable_native_table_slides':[5,9],
            'structure_and_layout':'pass','visual_review':'Author declares all final slides and PDF pages inspected',
            'claim_boundary':'Candidate choices require review; runtime agreement shares PROJ; finite samples do not certify a continuous bound'}
    (ROOT/'delivery/collateral-manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print('Executed evidence and derived collateral verified')

if __name__=='__main__':main()
