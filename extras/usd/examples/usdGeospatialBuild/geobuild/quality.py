"""Validate exact requirement authority separately from executable coverage."""
import json,re,hashlib
from pathlib import Path
class ProposalNotReady(RuntimeError):pass
def assessment(root):
    root=Path(root);review=json.loads((root/'proposal-quality.json').read_text(encoding='utf8'))
    source=(root/'proposal/proposal-source.txt').read_text(encoding='utf8')
    assert hashlib.sha256(source.encode()).hexdigest()==review['source_sha256']
    functional=source[source.index('### Functional requirements'):source.index('**Illustrative geographic data workflows**')]
    actual={int(m[1]):m[2] for m in re.finditer(r'^(\d+)\. \*\*([^*]+)\*\*',functional,re.M)}
    assert actual=={r['id']:r['title'] for r in review['requirements']}
    assert sorted(actual)==list(range(1,32))
    lines=source.splitlines()
    for r in review['requirements']:
        assert lines[r['source_line']-1]==str(r['id'])+'. **'+r['title']+'**'
        assert r['clauses']
        for ref in r['clauses']:assert lines[ref['line']-1]==ref['clause']
    gaps=[g['id'] for g in review['semantic_gaps'] if g['status']!='closed']
    return {'proposal_ready':not gaps,'requirements_build_complete':not gaps and not review['verification_gaps'],
        'open_semantic_gap_ids':gaps,'verification_gaps':review['verification_gaps'],'pending_design_agreement':review['pending_design_agreement']}
def require_derivable_proposal(root,experiment=False):
    result=assessment(root)
    if not result['proposal_ready'] and not experiment:raise ProposalNotReady('Dependent implementation stopped: '+str(result['open_semantic_gap_ids']))
    result['experimental_execution_authorized']=bool(experiment)
    return result
