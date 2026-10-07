"""Verify frozen consumer evidence and final artifacts before fork delivery."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,zipfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_claims(claims,receipt):
    if claims.get('usd_placement_implementations')!=2:raise AssertionError('OV reuses Python; there are two placement implementations')
    for name in ['ov_rendering','hydra_live_crs_filter','physics_integration','whole_proposal_conformance','independent_geodetic_validation']:
        if claims.get(name):raise AssertionError('Missing consumer/conformance evidence for '+name)
    if claims.get('ov_geometry_writeback') and not(receipt.get('ov',{}).get('geometry_vertices',0)>0 and receipt['ov']['edit_checks']>0):raise AssertionError('No OV geometry sink observation')
    if claims.get('hydra_resolved_export') and not(receipt.get('hydra') and all(h.get('renderer')=='HdStormRendererPlugin' and h.get('geometry_readback') for h in receipt['hydra'])):raise AssertionError('No Hydra points/transform/render observations')
    if claims.get('continuous_nonlinear_extent_certificate'):raise AssertionError('No continuous nonlinear certificate')

def main():
    p=argparse.ArgumentParser()
    for arg in ['deck','pdf','validation']:p.add_argument('--'+arg,required=True)
    p.add_argument('--grids',required=True)
    p.add_argument('--audience-review',required=True)
    p.add_argument('--visual-review-complete',action='store_true');a=p.parse_args();assert a.visual_review_complete
    d=ROOT/'delivery';report=json.loads((d/'run-report.json').read_text(encoding='utf-8'));story=json.loads((d/'story.json').read_text(encoding='utf-8'));integration=json.loads((d/'integration-evidence.json').read_text(encoding='utf-8'))
    validate_claims(integration['claims'],report)
    import sys
    sys.path.insert(0,str(ROOT))
    from collateral.portable_delivery import verify
    portable_proof=verify(ROOT,a.grids,validate_claims)
    for name,digest in report['source_files'].items():assert sha(ROOT/name)==digest,'Executed file changed: '+name
    assert story['readme_sha256']==sha(ROOT/'README.md') and story['run_receipt_sha256']==sha(d/'run-report.json')
    assert story['integration_evidence_sha256']==sha(d/'integration-evidence.json')
    from human_delivery import validate_narrative, verify_assessment_controls
    narrative_proof=verify_assessment_controls(ROOT,story)
    assert story['assessment_sha256']==sha(ROOT/'collateral/delivery-assessment.json')
    assert story['audit_sha256']==sha(d/'independent-audit.json')
    review=json.loads(Path(a.audience_review).read_text(encoding='utf-8'))
    assert review['readme_sha256']==sha(ROOT/'README.md') and review['pptx_sha256']==sha(a.deck) and review['pdf_sha256']==sha(a.pdf)
    assert review['inspection_performed_by']=='Codex agent' and review['user_comprehension_test_performed'] is False
    assert review['rendered_readme_inspected'] and len(review['slides'])==len(story['slides'])
    assert all(x['inspected'] and x['image_sha256'] for x in review['slides'])
    assert review['unresolved_layout_findings']==[]
    validation=json.loads(Path(a.validation).read_text(encoding='utf-8'));assert validation['finalSha256']==sha(a.deck)
    assert validation['packageIntegrity']['status']=='pass' and validation['presentationLayout']['finding_count']==0
    assert validation['nativeChartValidation']['passed'] and validation['chartDataPackaging']['portable_chart_validation_passed']
    ns={'x':'http://schemas.openxmlformats.org/drawingml/2006/main','c':'http://schemas.openxmlformats.org/drawingml/2006/chart'};tables=[];charts=[];texts=[]
    with zipfile.ZipFile(a.deck) as z:
        slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)];assert len(slides)==len(story['slides'])
        for n in range(1,len(slides)+1):
            node=ET.fromstring(z.read(f'ppt/slides/slide{n}.xml'));texts+=list(node.itertext())
            if node.findall('.//x:tbl',ns):tables.append(n)
            if node.findall('.//c:chart',ns):charts.append(n)
            note=z.read(f'ppt/notesSlides/notesSlide{n}.xml').decode();assert story['readme_sha256'] in note and story['proposal_sha256'] in note
            case=next((c for c in story['cases'] if c['id']==story['slides'][n-1].get('case')),None)
            if case:
                plain=''.join(ET.fromstring(note).itertext())
                for field in ['question','rule','expected','observed','implication','boundary']:assert case[field] in plain,(n,field)
            texts.append(note)
    assert tables==story['required_native_table_slides'] and charts==story['required_native_chart_slides']
    text=' '.join(texts)+'\n'+(ROOT/'README.md').read_text(encoding='utf-8')+'\n'+(d/'pr-body.md').read_text(encoding='utf-8')
    assert not re.search(r'https://github.com/(?:PixarAnimationStudios/OpenUSD|[^/]+/OpenUSD-proposals)/(?:pull|issues)/',text)
    assert report['readiness']['proposal_ready'] is True and report['readiness']['requirements_build_complete'] is False
    assert report['tests']['failed']==0 and len(report['expected_failures'])==1
    assert all(m['native_vs_python']['max_distance_metres']<=m['native_vs_python']['acceptance_metres'] for m in report['metrics'])
    shutil.copy2(a.deck,d/'geospatial-build.pptx');shutil.copy2(a.pdf,d/'geospatial-build.pdf')
    shutil.copy2(a.audience_review,d/'audience-review.json')
    manifest={'readme_sha256':sha(ROOT/'README.md'),'receipt_sha256':sha(d/'run-report.json'),'immutable_execution_receipt_sha256':story['immutable_receipt_sha256'],'proposal_sha256':story['proposal_sha256'],
        'source_parent_at_execution':report['source_commit'],'executed_file_hashes_verified':True,'pptx_sha256':sha(d/'geospatial-build.pptx'),'pdf_sha256':sha(d/'geospatial-build.pdf'),'story_sha256':sha(d/'story.json'),'pr_body_sha256':sha(d/'pr-body.md'),'slides':len(slides),'native_table_slides':tables,'native_chart_slides':charts,
        'tests':report['tests'],'coordinate_results_per_path':story['coordinate_count'],'integration_claims':integration['claims'],'proposal_ready':True,'requirements_build_complete':False,
        'visual_review':'Every final slide rendered by native PowerPoint and inspected individually by Codex; PDF exported from the same presentation. README rendered and inspected. This is not a user comprehension test.',
        'assessment_checks':narrative_proof,'audience_review_sha256':sha(d/'audience-review.json'),'later_audit_sha256':story['audit_sha256'],'delivery_refresh_without_runtime_repairs':True,
        'portable_delivery':'Local path prefixes relinked in public copies; immutable execution receipt SHA retained. Source input hashes remain in receipt.',
        'files':{f.relative_to(d).as_posix():sha(f) for f in sorted(d.rglob('*')) if f.is_file() and f.name!='collateral-manifest.json'}}
    (d/'collateral-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps({'validated':True,'slides':len(slides),'tables':tables,'charts':charts}))
if __name__=='__main__':main()
