from pathlib import Path
import hashlib
import json
import zipfile

import pytest

from geobuild.fixtures import inspect_aeco
from geobuild.source import parse
from run import is_current


def test_source_extraction_excludes_legacy_runtime():
    # Frozen source captured by the loop; no source repository read by a test.
    import os
    source = os.environ.get("GEO_SOURCE_JSON")
    if not source:
        pytest.skip("Run through run.py for pinned source evidence.")
    snapshot = json.loads(Path(source).read_text(encoding="utf-8"))
    assert set(range(1, 30)).issubset({r["number"] for r in snapshot["requirements"]})
    assert len(snapshot["questions"]) >= 9
    assert "### Schema design" not in snapshot["allowed_text"]
    assert "## Runtime coordinate transformation" not in snapshot["allowed_text"]
    assert snapshot["allowed_sha256"] == hashlib.sha256(snapshot["allowed_text"].encode()).hexdigest()


def test_fixture_import_ignores_archive_paths_and_scripts(tmp_path):
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for name in ("README.md", "site.usda", "crs_library.usda", "La_tour_Eiffel.usdz"):
            z.writestr("aeco_site_example/" + name, "test")
        z.writestr("../escaped.py", "raise Exception('should never execute')")
        z.writestr("aeco_site_example/verify.py", "raise Exception('should never execute')")
    manifest = inspect_aeco(archive, tmp_path / "extracted")
    assert not (tmp_path / "escaped.py").exists()
    assert not (tmp_path / "extracted" / "verify.py").exists()
    assert len(list((tmp_path / "extracted").iterdir())) == 4
    assert manifest["sha256"]


def test_changed_requirement_invalidates_derivation():
    import os
    snapshot = json.loads(Path(os.environ["GEO_SOURCE_JSON"]).read_text(encoding="utf-8"))
    baseline = {"allowed_sha256": snapshot["allowed_sha256"]}
    assert is_current(snapshot, baseline)
    # Change an actual requirement without changing identifiers. Old evidence
    # must not remain current just because the requirement count stayed at 29.
    modified = snapshot["allowed_text"].replace("A CRS carried in a scene", "A complete CRS carried in a scene", 1)
    wrapper = modified.replace("### Functional requirements", "## Design overview\n\n### Functional requirements") + "\n### Schema design\n"
    changed = parse(wrapper)
    assert len(changed["requirements"]) == len(snapshot["requirements"])
    assert not is_current(changed, baseline)


def test_duplicate_frozen_identifier_is_rejected():
    import os
    snapshot = json.loads(Path(os.environ["GEO_SOURCE_JSON"]).read_text(encoding="utf-8"))
    modified = snapshot["allowed_text"].replace("2. **Defined once", "1. **Defined once", 1)
    wrapper = modified.replace("### Functional requirements", "## Design overview\n\n### Functional requirements") + "\n### Schema design\n"
    with pytest.raises(ValueError, match="Missing or duplicate"):
        parse(wrapper)


def test_changed_runtime_prose_invalidates_derivation(tmp_path):
    from geobuild.contract import load_contract
    root = Path(__file__).resolve().parents[1]
    derivation = json.loads((root / "derivation.json").read_text(encoding="utf-8"))
    original = load_contract(root, derivation)
    source = {"allowed_sha256": derivation["allowed_sha256"]}
    assert is_current(source, derivation, original)
    copy = tmp_path / derivation["runtime_document"]["path"]
    copy.parent.mkdir(parents=True)
    copy.write_text(original["text"].replace("Resolution reads the composed stage", "Resolution reads a source layer"), encoding="utf-8")
    assert not is_current(source, derivation, load_contract(tmp_path, derivation))
    copy.write_text(original["text"].replace("## Composed declarations and scope", "## Missing scope"), encoding="utf-8")
    with pytest.raises(ValueError, match="Missing traced"):
        load_contract(tmp_path, derivation)


def test_changed_source_cycle_stops_before_tests_and_rejects_dirty_input(tmp_path):
    import os
    import subprocess
    import sys
    from geobuild.source import PROPOSAL, snapshot
    current = json.loads(Path(os.environ["GEO_SOURCE_JSON"]).read_text(encoding="utf-8"))
    changed = current["allowed_text"].replace("A CRS carried in a scene", "A complete CRS carried in a scene", 1)
    changed = changed.replace("### Functional requirements", "## Design overview\n\n### Functional requirements") + "\n### Schema design\n"
    repo = tmp_path / "proposal"
    target = repo / PROPOSAL
    target.parent.mkdir(parents=True)
    target.write_text(changed, encoding="utf-8")
    def git(*args):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    git("init")
    git("add", PROPOSAL)
    git("-c", "user.name=Build-loop test", "-c", "user.email=build-loop@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-m", "Temporary test input")
    out = tmp_path / "stale-run"
    runner = Path(__file__).resolve().parents[1] / "run.py"
    process = subprocess.run([sys.executable, str(runner), "--proposal-repo", str(repo), "--output", str(out)],
                             capture_output=True, text=True, encoding="utf-8")
    assert process.returncode == 2, process.stdout + process.stderr
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "DERIVATION_STALE"
    assert report["tests"] == []
    assert not (out / "tests.xml").exists()
    assert "A complete CRS carried" in (out / "AGENT-BRIEF.md").read_text(encoding="utf-8")
    target.write_text(changed + "\nUncommitted change\n", encoding="utf-8")
    with pytest.raises(ValueError, match="uncommitted"):
        snapshot(repo)
