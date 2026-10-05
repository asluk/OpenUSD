"""Semantic controls for defined contracts and the proposal-readiness boundary."""
from pathlib import Path
import hashlib
import json
import pytest
from pxr import Usd, UsdGeom
from review.fixtures import build
from review.scope import queries
from review.placement_values import queries as placement_queries
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
            assert names <= {'crs:wkt', 'crs:position', 'crs:orientation', 'crs:scale'}
        assert not stage.GetRootLayer().customLayerData


def test_readiness_tracks_full_local_candidate_and_derivation():
    inputs = json.loads((ROOT/'inputs.json').read_text())
    assert hashlib.sha256((ROOT/'proposal/proposal-source.txt').read_bytes()).hexdigest() == inputs['proposal']['sha256']
    for name, expected in inputs['derivation'].items():
        assert hashlib.sha256((ROOT/'proposal'/name).read_bytes()).hexdigest() == expected
    with pytest.raises(ProposalNotReady, match='Dependent implementation stopped'):
        require_derivable_proposal(ROOT)
    result = assessment(ROOT)
    assert 'G01' not in result['open_semantic_gap_ids']
    assert set(result['open_semantic_gap_ids']) == {'G03', 'G04', 'G06', 'G07'}
    assert result['proposal_ready'] is False


def test_retained_experiment_is_not_a_shared_proposal_implementation(jobs):
    from geobuild.model import binding, GeoError
    stage = Usd.Stage.Open(next(x for x in jobs if x['name'] == 'references')['stage'])
    assert queries(stage, ['/World/Data'])['queries'][0]['success']
    with pytest.raises(GeoError, match='no CRS binding'):
        binding(stage.GetPrimAtPath('/World/Data'))


@pytest.mark.parametrize('name', ['placement-defaults', 'placement-linear', 'placement-held',
    'geographic-no-unwrapping', 'same-crs-independent-anchor', 'position-missing',
    'orientation-blocked', 'position-wrong-type', 'position-wrong-variability',
    'nonfinite-scale', 'zero-quaternion', 'singular-source-scale'])
def test_candidate_source_placement_records(name, jobs):
    from review.runner import assert_results
    job = next(x for x in jobs if x['name'] == name)
    stage = Usd.Stage.Open(job['stage'])
    result = placement_queries(stage, job['queries'], job['time'], job['interpolation'])
    assert_results(result['queries'], job['expected'])
    assert result['source_unchanged']


@pytest.mark.parametrize('name', ['origins-France_01-to-France_02', 'origins-France_02-to-France_01',
    'origins-Colorado_02-to-Colorado_03', 'origins-Colorado_03-to-Colorado_02',
    'origin-source-interpolation-0', 'origin-source-interpolation-5', 'origin-source-interpolation-10',
    'origin-adjustment-stops', 'origin-invalid-latitude'])
def test_direct_origin_coordinate_controls(name, jobs):
    from review.origin_queries import queries as origin_queries
    from review.runner import check_job
    job=next(row for row in jobs if row['name']==name)
    stage=Usd.Stage.Open(job['stage'])
    result=origin_queries(stage,job['queries'],job['output_wkt'],job['time'],job['interpolation'])
    check_job(result,job)
    assert result['source_unchanged']
