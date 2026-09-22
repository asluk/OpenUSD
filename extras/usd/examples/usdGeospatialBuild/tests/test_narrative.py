import json
from pathlib import Path

import pytest

from geobuild.delivery import sha, slide_content, pr_body
from geobuild.narrative import refresh, verify_figures, evidence_key


@pytest.fixture
def narrative_case():
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    source = json.loads((root / "inputs" / "requirements.json").read_text(encoding="utf-8"))
    metrics = [
        ("test_complete_W01_railway_all_vertices_tiles_and_topology", {"features_resolved":1473,"vertices_checked":15822,"provider_interior_max_discrepancy_m":.167,"cartesian_tangent_interior_max_discrepancy_m":.000042}),
        ("test_complete_W07_native_storm_and_omniverse_fabric", {"kit_fabric_max_residual_m":.00006}),
        ("test_complete_W03_same_place_across_frames_and_units", {"independent_scene_origin_residual_m":.000000003}),
        ("test_workflow_geojson_source_to_usd_identity_and_anchors", {"matched_feature_ids": 1473, "matched_linestring_vertices_by_count": 3526}),
        ("test_workflow_railway_source_inventory_and_anchor_reporting", {"curve_prims": 186}),
        ("test_workflow_field_coordinate_probe", {"samples": 2664}),
        ("test_native_sample_midpoint_before_conversion", {"wrong_order_chord_depth_m": 971.4211583}),
        ("test_engine_analytic_global_points_and_provenance", {"max_residual_m": 0}),
    ]
    report = {"tests": [{"name": n, "status": "passed", "properties": p} for n, p in metrics],
              "started_utc": "2026-09-21T22:00:00Z", "runtime_contract": {"sha256": "a" * 64},
              "implementation": {"revision": "b" * 40, "source_dirty": True}}
    return readme, source, report


def test_narrative_preserves_authored_argument_and_derives_summaries(narrative_case):
    readme, source, report = narrative_case
    addition = "A reviewer-authored qualification must survive regeneration.\n"
    readme += addition
    updated = refresh(readme, source, report, "fixture")
    assert addition in updated
    assert "1,473 source features" in updated and "971.421 m" in updated
    deck = slide_content(updated)
    assert len(deck["slides"]) == 8 and sum("image" in s for s in deck["slides"]) == 5
    assert not any("Not built." in line for s in deck["slides"] for line in s["lines"])
    body = pr_body(updated, "test-branch")
    assert "Non-Hydra" in body and "Hydra" in body and "Not built." not in body
    assert "Evidence is refreshed" not in updated
    # Repeated preparation changes measured blocks, never the authored narrative.
    assert refresh(updated, source, report, "fixture") == updated


def test_narrative_refuses_missing_workflow_evidence(narrative_case):
    readme, source, report = narrative_case
    report["tests"][0]["status"] = "skipped"
    with pytest.raises(ValueError, match="executed evidence"):
        refresh(readme, source, report, "fixture")


def test_figures_are_bound_to_run_and_bytes(tmp_path, narrative_case):
    _, _, report = narrative_case
    folder = tmp_path / "docs" / "figures"
    folder.mkdir(parents=True)
    names = ("railway.png", "interpolation.png", "field.png", "site.png", "extent.png")
    for name in names:
        (folder / name).write_bytes(b"synthetic hash fixture")
    manifest = {"evidence_key": evidence_key(report), "files": {n: sha(folder / n) for n in names}}
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    verify_figures(tmp_path, report)
    report["started_utc"] += "changed"
    with pytest.raises(ValueError, match="different run"):
        verify_figures(tmp_path, report)
    report["started_utc"] = report["started_utc"].removesuffix("changed")
    (folder / "railway.png").write_bytes(b"different figure")
    with pytest.raises(ValueError, match="changed after"):
        verify_figures(tmp_path, report)
