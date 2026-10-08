"""Delivery controls for the reporting failure, separate from runtime tests."""
from copy import deepcopy
from pathlib import Path
import json
import shutil
import pytest
from integration_evidence import ROOT, collect, validate_claims, check_language

@pytest.fixture
def inspected(tmp_path):
    audit = json.loads((ROOT / 'collateral/query-path-audit.json').read_text())
    for name in [*audit['source_sha256'], 'collateral/query-path-audit.json', 'delivery/run-report.json', 'delivery/scope-results.json']:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    report = json.loads((tmp_path / 'delivery/run-report.json').read_text())
    results = json.loads((tmp_path / 'delivery/scope-results.json').read_text())
    return tmp_path, report, results

def test_actual_hosted_query_path_has_no_geometry_or_render_claim(inspected):
    root, report, results = inspected
    evidence = collect(root, report, results)
    ov = next(p for p in evidence['paths'] if p['result_key'] == 'live_ov')
    assert ov['usd_reader'] == 'omni.usd context.get_stage(), pxr.Usd.Stage'
    assert ov['output'] == 'JSON query results' and ov['queries'] == 168
    assert evidence['geodetic_engine_families'] == ['PROJ']
    assert not evidence['capabilities']['ov_geospatial_backend']
    assert not evidence['capabilities']['rendering']

@pytest.mark.parametrize('claim', ['full_model_placement', 'ov_geometry_writeback', 'ov_geospatial_backend', 'rendering', 'resolved_scene_export', 'independent_geodetic_engines'])
def test_rejects_fabricated_downstream_or_independence_claim(inspected, claim):
    evidence = collect(*inspected)
    with pytest.raises(ValueError, match='Claim exceeds'):
        validate_claims(evidence, {claim: True})

def test_changing_inspection_to_claim_geometry_does_not_supply_execution(inspected):
    root, report, results = inspected
    path = root / 'collateral/query-path-audit.json'
    audit = json.loads(path.read_text())
    audit['capabilities']['ov_geometry_writeback'] = True
    path.write_text(json.dumps(audit))
    with pytest.raises(ValueError, match='do not reach'):
        collect(root, report, results)

def test_shared_proj_cannot_be_declared_independent(inspected):
    root, report, results = inspected
    path = root / 'collateral/query-path-audit.json'
    audit = json.loads(path.read_text())
    audit['capabilities']['independent_geodetic_engines'] = True
    path.write_text(json.dumps(audit))
    with pytest.raises(ValueError, match='Shared conversion'):
        collect(root, report, results)

def test_stale_source_inspection_stops_delivery(inspected):
    root, report, results = inspected
    with (root / 'review/ov_scope_launch.py').open('a') as stream:
        stream.write('\n# changed consumer requires renewed inspection\n')
    with pytest.raises(ValueError, match='inspection is stale'):
        collect(root, report, results)

def test_missing_ov_execution_stops_claim(inspected):
    root, report, results = inspected
    results = deepcopy(results)
    results.pop('live_ov')
    with pytest.raises(ValueError, match='Missing executed query path'):
        collect(root, report, results)

@pytest.mark.parametrize('text', ['France: same origins in all three runtimes', 'Live OV'])
def test_previous_labels_fail_delivery(text):
    with pytest.raises(ValueError, match='Unsupported runtime label'):
        check_language(text)
