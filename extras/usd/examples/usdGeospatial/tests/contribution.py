#
# Copyright 2026 NVIDIA CORPORATION & AFFILIATES
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
"""Check source notices and original-byte integrity; this is not legal approval."""

import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = {"native", "src_py", "schema", "tests", "delivery"}
SUFFIXES = {".py", ".cpp", ".h", ".mjs", ".cmd", ".usda"}


def source_names():
    """Use the deliverable inventory, excluding ignored build products."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "."],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(
        name
        for name in set(result.stdout.splitlines())
        if name.split("/", 1)[0] in FOLDERS
        and (Path(name).suffix in SUFFIXES or Path(name).name == "CMakeLists.txt")
        and (ROOT / name).is_file()
    )


def source_has_notice(text):
    """Require a copyright notice and the upstream license reference."""
    header = text[:1800]
    return bool(re.search(r"copyright\s+\d{4}", header, re.I)) and (
        "Licensed under the terms set forth in the LICENSE.txt file" in header
        and "https://openusd.org/license" in header
    )


def check():
    names = source_names()
    missing = [
        name
        for name in names
        if not source_has_notice((ROOT / name).read_text(encoding="utf-8"))
    ]
    assert not missing, "Missing source notice: " + ", ".join(missing)
    original = json.loads((ROOT / "audit/original-inputs.json").read_text())
    changed = [
        row["path"]
        for row in original
        if hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest()
        != row["sha256"]
    ]
    assert not changed, "Original dataset bytes changed: " + ", ".join(changed)
    report = {
        "pass": True,
        "source_files_checked": len(names),
        "original_files_byte_preserved": len(original),
        "scope": "Source notices and byte integrity; dataset permissions and legal approval require separate evidence",
        "files": names,
        "noncomment_formats": "JSON plugin/configuration files are covered by the repository license; third-party input terms are separate",
    }
    destination = ROOT / "evidence/contribution.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(check()))
