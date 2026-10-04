"""Semantic controls for defined contracts and the proposal-readiness boundary."""
from pathlib import Path
import hashlib
import json
import pytest
from pxr import Usd, UsdGeom
from review.fixtures import build
from review.scope import queries
from geobuild.quality import assessment, require_derivable_proposal, ProposalNotReady

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def jobs(tmp_path_factory):
    return build(ROOT, tmp_path_factory.mktemp('shared-contracts'))


@pytest.mark.parametrize('name', ['references', 'referenced-assembly', 'stronger-layer', 'variant-selection',
    'class-inheritance', 'equivalent-composed-data', 'unloaded-payload', 'no-binding',
    'broken-nearest-binding', 'wrong-wkt-type', 'wrong-wkt-variability', 'empty-wkt'])
def test_authoritative_scope_controls(name, jobs):
    job = next(x for x in jobs if x['name'] == name)
    stage = Usd.Stage.Open(job['stage'], load=Usd.Stage.LoadNone if job['load_none'] else Usd.Stage.LoadAll)
    result = queries(stage, job['queries'])
    assert result['queries'] == job['expected']
    assert result['source_unchanged']
    assert UsdGeom.GetStageMetersPerUnit(stage) == .01
    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.y


def test_fixtures_do_not_supply_missing_geospatial_fields(jobs):
    for job in jobs:
        stage = Usd.Stage.Open(job['stage'])
        for prim in stage.Traverse():
            names = {x.GetName() for x in prim.GetProperties() if x.GetName().startswith('crs:')}
            assert names <= {'crs:wkt'}
        assert not stage.GetRootLayer().customLayerData


def test_readiness_tracks_full_published_source_and_derivation():
    inputs = json.loads((ROOT/'inputs.json').read_text())
    assert hashlib.sha256((ROOT/'proposal/proposal-source.txt').read_bytes()).hexdigest() == inputs['proposal']['sha256']
    for name, expected in inputs['derivation'].items():
        assert hashlib.sha256((ROOT/'proposal'/name).read_bytes()).hexdigest() == expected
    with pytest.raises(ProposalNotReady, match='Dependent implementation stopped'):
        require_derivable_proposal(ROOT)
    result = assessment(ROOT)
    assert 'G01' not in result['open_semantic_gap_ids']
    assert {'G02', 'G03', 'G05', 'G06'} <= set(result['open_semantic_gap_ids'])
    assert result['proposal_ready'] is False


def test_retained_experiment_is_not_a_shared_proposal_implementation(jobs):
    from geobuild.model import binding, GeoError
    stage = Usd.Stage.Open(next(x for x in jobs if x['name'] == 'references')['stage'])
    assert queries(stage, ['/World/Data'])['queries'][0]['success']
    with pytest.raises(GeoError, match='no CRS binding'):
        binding(stage.GetPrimAtPath('/World/Data'))
