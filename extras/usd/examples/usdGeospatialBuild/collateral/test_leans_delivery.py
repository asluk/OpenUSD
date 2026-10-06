"""Negative controls for the integration overclaims caught in earlier delivery."""
import json
from pathlib import Path
import pytest
from verify_leans_delivery import validate_claims
ROOT=Path(__file__).resolve().parents[1]
def receipt():return json.loads((ROOT/'delivery/run-report.json').read_text(encoding='utf-8'))
def claims():return json.loads((ROOT/'delivery/integration-evidence.json').read_text(encoding='utf-8'))['claims']
def test_actual_consumer_claims_have_evidence():validate_claims(claims(),receipt())
@pytest.mark.parametrize('bad',['ov_rendering','hydra_live_crs_filter','physics_integration','whole_proposal_conformance','independent_geodetic_validation','continuous_nonlinear_extent_certificate'])
def test_unsupported_capability_claim_is_rejected(bad):
    c=claims();c[bad]=True
    with pytest.raises(AssertionError):validate_claims(c,receipt())
def test_ov_host_is_not_a_third_placement_implementation():
    c=claims();c['usd_placement_implementations']=3
    with pytest.raises(AssertionError):validate_claims(c,receipt())
def test_query_counts_do_not_prove_geometry_sink():
    r=receipt();r['ov']['geometry_vertices']=0
    with pytest.raises(AssertionError):validate_claims(claims(),r)
def test_renderer_name_without_hydra_readback_is_insufficient():
    r=receipt();r['hydra'][0]['geometry_readback']={}
    with pytest.raises(AssertionError):validate_claims(claims(),r)
