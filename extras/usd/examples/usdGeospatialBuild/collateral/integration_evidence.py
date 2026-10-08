"""Bind integration claims to inspected source and executed input-to-output paths.

This is a delivery audit, not proposal authority or a new runtime execution.
Changed consumer code requires a new source inspection and audit record.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'extras/usd/examples/usdGeospatialBuild/'
PROCESS_DOCUMENTS = {'BUILD_LOOP.md', 'AUDIT.md', 'PLAN.md'}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_executed_source(root, report, collateral_only=False):
    changes = {}
    for name, expected in report['source_files'].items():
        current = (root / name).read_bytes()
        frozen = subprocess.check_output(['git', '-C', str(root), 'show', report['source_commit'] + ':' + PREFIX + name])
        current_hash = hashlib.sha256(current).hexdigest()
        if current_hash != expected:
            if not collateral_only or name not in PROCESS_DOCUMENTS:
                raise ValueError('Executed source changed: ' + name)
            frozen_lf = frozen.replace(b'\r\n', b'\n')
            possible = {hashlib.sha256(frozen_lf).hexdigest(), hashlib.sha256(frozen_lf.replace(b'\n', b'\r\n')).hexdigest()}
            if expected not in possible:
                raise ValueError('Frozen process document does not match receipt: ' + name)
            changes[name] = {'executed_sha256': expected, 'current_sha256': current_hash}
        elif frozen.replace(b'\r\n', b'\n') != current.replace(b'\r\n', b'\n'):
            raise ValueError('Executed Git source mismatch: ' + name)
    return changes

def collect(root, report, results):
    audit_path = root / 'collateral/query-path-audit.json'
    audit = json.loads(audit_path.read_text(encoding='utf8'))
    if audit['source_commit'] != report['source_commit']:
        raise ValueError('Integration source inspection must be renewed for this executed revision')
    for name, expected in audit['source_sha256'].items():
        if report['source_files'].get(name) != expected or sha(root / name) != expected:
            raise ValueError('Integration source inspection is stale: ' + name)
    paths = []
    for audited in audit['paths']:
        rows = results.get(audited['result_key'])
        if not rows or len(rows) != len(report['scope_controls']):
            raise ValueError('Missing executed query path: ' + audited['result_key'])
        versions = set()
        for row, control in zip(rows, report['scope_controls']):
            if row['name'] != control['name'] or len(row['queries']) != control['queries'] or not row['source_unchanged']:
                raise ValueError('Query-path coverage does not match receipt')
            for query in row['queries']:
                if query.get('coordinates') is not None:
                    if query.get('engine') != audited['geodetic_engine_family']:
                        raise ValueError('Recorded conversion dependency disagrees with inspection')
                    versions.add(query['engine_version'])
        if not versions:
            raise ValueError('No executed origin conversion evidence')
        paths.append({**audited, 'cases': len(rows), 'queries': sum(len(r['queries']) for r in rows), 'engine_versions': sorted(versions)})
    capabilities = audit['capabilities']
    # This reviewed source has only query-to-JSON consumers. New downstream
    # capabilities require new audited call paths AND end-to-end execution.
    if any(capabilities[k] for k in ['full_model_placement', 'hydra_geometry', 'ov_geometry_writeback', 'ov_geospatial_backend', 'rendering', 'resolved_scene_export']):
        raise ValueError('The inspected query paths do not reach a geometry, rendering or scene-export sink')
    families = sorted({p['geodetic_engine_family'] for p in paths})
    if capabilities['independent_geodetic_engines'] and len(families) < 2:
        raise ValueError('Shared conversion dependencies cannot establish independent engines')
    return {
        'audit_schema': 1, 'source_commit': report['source_commit'],
        'source_inspection_sha256': sha(audit_path),
        'execution_receipt_sha256': sha(root / 'delivery/run-report.json'),
        'query_results_sha256': sha(root / 'delivery/scope-results.json'),
        'paths': paths, 'capabilities': capabilities,
        'geodetic_engine_families': families,
        'limitations': audit['limitations'], 'new_runtime_execution': False
    }

def validate_claims(evidence, claims):
    for claim, value in claims.items():
        if claim == 'query_paths':
            allowed = len(evidence['paths'])
        elif claim in evidence['capabilities']:
            allowed = evidence['capabilities'][claim]
        else:
            raise ValueError('Unreviewed integration claim: ' + claim)
        if value != allowed:
            raise ValueError('Claim exceeds inspected and executed evidence: ' + claim)

def check_language(text):
    # These labels previously conflated host, reader and backend. The source
    # audit remains necessary: a phrase check cannot establish semantic truth.
    for phrase in [r'\bthree runtimes\b', r'\beach runtime\b', r'\ball three runtimes\b', r'\bLive OV\b']:
        if re.search(phrase, text, flags=re.I):
            raise ValueError('Unsupported runtime label in current delivery: ' + phrase)

def verify_current_delivery(root=ROOT, deck_text=None):
    delivery = root / 'delivery'
    report = json.loads((delivery / 'run-report.json').read_text(encoding='utf8'))
    results = json.loads((delivery / 'scope-results.json').read_text(encoding='utf8'))
    actual = collect(root, report, results)
    saved = json.loads((delivery / 'integration-evidence.json').read_text(encoding='utf8'))
    if saved != actual:
        raise ValueError('Integration evidence is stale; derive delivery again')
    story = json.loads((delivery / 'story.json').read_text(encoding='utf8'))
    if story['integration_evidence_sha256'] != sha(delivery / 'integration-evidence.json'):
        raise ValueError('Slide story does not bind the current integration audit')
    validate_claims(actual, story['integration_claims'])
    for path in [root / 'README.md', delivery / 'pr-body.md', delivery / 'story.json']:
        check_language(path.read_text(encoding='utf8'))
    if deck_text is not None:
        check_language(deck_text)
        if 'USD in OV' not in deck_text or 'OpenUSD queries' not in deck_text:
            raise ValueError('Deck omits the OV-hosted OpenUSD integration boundary')
    return actual

if __name__ == '__main__':
    evidence = verify_current_delivery()
    print(json.dumps({'query_paths': len(evidence['paths']), 'geodetic_engines': evidence['geodetic_engine_families'], 'ov_geospatial_backend': evidence['capabilities']['ov_geospatial_backend'], 'rendering': evidence['capabilities']['rendering'], 'status': 'pass'}))
