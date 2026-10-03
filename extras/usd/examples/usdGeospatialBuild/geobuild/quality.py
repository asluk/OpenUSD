"""Proposal readiness is independent of an experimental implementation's tests."""
import json
from pathlib import Path

class ProposalNotReady(RuntimeError):pass

def assessment(root):
    review=json.loads((Path(root)/'proposal-quality.json').read_text(encoding='utf8'))
    assert sorted(r['id'] for r in review['requirements'])==list(range(1,32)), 'Review must cover every functional requirement'
    gaps=[g['id'] for g in review['semantic_gaps'] if g['status']!='closed']
    verification=review['verification_gaps']
    ready=not gaps
    return {'proposal_ready':ready,'requirements_build_complete':ready and not verification,
            'open_semantic_gap_ids':gaps,'verification_gaps':verification}

def require_derivable_proposal(root,experiment=False):
    result=assessment(root)
    if not result['proposal_ready'] and not experiment:
        raise ProposalNotReady('Dependent implementation stopped: proposal is unspecified or conflicting ('+', '.join(result['open_semantic_gap_ids'])+'). An explicitly labeled experiment cannot certify proposal conformance.')
    result['experimental_execution_authorized']=bool(experiment)
    return result
