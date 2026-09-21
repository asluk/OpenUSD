import json
import os
from pathlib import Path
from urllib.parse import quote

import pytest

from geobuild.delivery import prepare, public_report, scan_text, sha, slide_content, verify, write_json
from geobuild.source import load_snapshot


def test_public_guard_rejects_backlinks_and_private_paths():
    url = "https://github.com/" + "PixarAnimationStudios/OpenUSD/" + "pull/" + str(123)
    for value in (url, quote(url, safe=""), "OpenUSD-proposals" + chr(35) + str(7),
                  "PR " + str(9), "C:" + chr(92) + "Users" + chr(92) + "someone" + chr(92) + "file"):
        with pytest.raises(ValueError, match="Public delivery guard"):
            scan_text(value)


def test_public_guard_allows_pinned_source_files_and_requirements():
    scan_text("https://github.com/asluk/OpenUSD-proposals/blob/" + "a" * 40 + "/proposals/geospatial/README.md")
    scan_text("Requirement 7, Composition agnostic; open question 2, position carrier")


@pytest.fixture
def delivery_case(tmp_path):
    root, run = tmp_path / "package", tmp_path / "run"
    root.mkdir()
    run.mkdir()
    (root / "run.py").write_text("# Minimal source fixture\n")
    source = json.loads(Path(os.environ["GEO_SOURCE_JSON"]).read_text(encoding="utf-8"))
    report = {
        "started_utc": "2026-09-21T22:00:00Z", "proposal_commit": source["commit"],
        "allowed_sha256": source["allowed_sha256"], "derivation_current": True,
        "approval": "draft", "status": "NEEDS_DECISIONS_AND_EVIDENCE", "test_exit_code": 0,
        "implementation": {"revision": "a" * 40, "source_dirty": False}, "stop_count": 7,
        "environment": {"python": "3.12", "platform": "test", "packages": {}, "executable": "private executable"},
        "source_files": {"run.py": sha(root / "run.py")}, "dataset": None,
        "tests": [
            {"name": "test_engine_analytic_global_points_and_provenance", "status": "passed",
             "properties": {"max_residual_m": "0", "max_coordinate_magnitude_m": "6378147"}},
            {"name": "test_native_sample_midpoint_before_conversion", "status": "passed",
             "properties": {"wrong_order_chord_depth_m": "971.4211583"}},
        ],
    }
    write_json(run / "source.json", source)
    write_json(run / "report.json", report)
    for name in ("RUNTIME.md", "FIXTURES.md", "STOPS.md", "AGENT-BRIEF.md"):
        (run / name).write_text("# Public fixture\n")
    return root, run, report


def test_delivery_readme_is_the_source_for_summaries(delivery_case):
    root, run, _ = delivery_case
    prepare(run, root, "run-001")
    manifest = verify(root, require_slides=False)
    assert manifest["checkpoint"] == "run-001"
    readme = (root / "README.md").read_text(encoding="utf-8")
    slides = json.loads((root / "docs" / "slides.json").read_text(encoding="utf-8"))
    assert slides == slide_content(readme)
    assert len(slides["slides"]) == 8
    assert slides["slides"][4]["chart"]["values"] == [0, 971.421]
    (root / "docs" / "PR_BODY.md").write_text("An independently edited summary\n")
    with pytest.raises(ValueError, match="PR body drifted"):
        verify(root, require_slides=False)


def test_delivery_checkpoints_are_immutable(delivery_case):
    root, run, _ = delivery_case
    prepare(run, root, "run-001")
    with pytest.raises(ValueError, match="already exists"):
        prepare(run, root, "run-001")


def test_delivery_rejects_changed_source(delivery_case):
    root, run, _ = delivery_case
    (root / "run.py").write_text("# Source changed after tests\n")
    with pytest.raises(ValueError, match="Build source changed"):
        prepare(run, root, "run-001")


@pytest.mark.parametrize("status", ["TEST_FAILURE", "DERIVATION_STALE"])
def test_delivery_rejects_failed_or_stale_runs(delivery_case, status):
    root, run, report = delivery_case
    report["status"] = status
    write_json(run / "report.json", report)
    with pytest.raises(ValueError, match="current derivation"):
        prepare(run, root, "run-001")


def test_public_report_omits_local_access_information(delivery_case):
    _, _, report = delivery_case
    report["dataset"] = {"path": "private path", "scene": "private scene", "sha256": "a" * 64,
                         "origin": "partner fixture", "redistribution": "local only", "role": "baseline"}
    clean = public_report(report)
    assert "executable" not in clean["environment"]
    assert "path" not in clean["dataset"] and "scene" not in clean["dataset"]


def test_portable_input_rejects_changed_text(delivery_case):
    root, run, _ = delivery_case
    prepare(run, root, "run-001")
    source_path = root / "inputs" / "requirements.json"
    loaded = load_snapshot(source_path)
    assert len(loaded["requirements"]) >= 29
    loaded["allowed_text"] += "Changed text\n"
    write_json(source_path, loaded)
    with pytest.raises(ValueError, match="hash"):
        load_snapshot(source_path)
