#
# Copyright 2026 NVIDIA CORPORATION & AFFILIATES
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
"""Check concrete reviewability prerequisites; human diff review is still required."""

import ast
from collections import Counter
import io
import json
from pathlib import Path
import re
import subprocess
import tokenize

from contribution import check as check_contribution

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FOLDERS = ("native", "src_py", "schema", "tests", "delivery")
SOURCE_SUFFIXES = {".cpp", ".h", ".py", ".mjs", ".cmd", ".txt", ".json", ".usda"}
REVIEW_DOCUMENTS = {
    "README.md",
    "REVIEW.md",
    "REVIEWING.md",
    "REPRODUCE.md",
    "BUILD_LOOP.md",
}


def inventory():
    """Include both tracked files and new deliverable files awaiting their commit."""
    command = [
        "git",
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "--",
        ".",
    ]
    result = subprocess.run(
        command, cwd=ROOT, check=True, capture_output=True, text=True
    )
    return sorted(
        name for name in set(result.stdout.splitlines()) if (ROOT / name).is_file()
    )


def category(path):
    if path in REVIEW_DOCUMENTS or path.startswith("."):
        return "review and build guidance"
    folder = path.split("/", 1)[0]
    if folder in ("native", "src_py", "schema"):
        return "implementation and schema"
    if folder == "tests":
        return "acceptance and fixture source"
    if path == "inputs/original/gfs_t2m.nc":
        return "retained synthetic test data"
    if path.startswith("inputs/original/"):
        return "original supplied data"
    if path.startswith("inputs/authored/"):
        return "generated examples and bakes"
    if folder == "evidence":
        return "generated evidence"
    if folder == "audit":
        return "provenance and requirement trace"
    if path.startswith("delivery/output/"):
        return "generated deck outputs"
    if folder == "delivery":
        return "delivery source"
    raise AssertionError("Unmapped deliverable: " + path)


def check():
    check_contribution()
    files = inventory()
    groups = {name: category(name) for name in files}
    sources = [
        ROOT / name
        for name in files
        if name.split("/", 1)[0] in SOURCE_FOLDERS
        and (ROOT / name).suffix in SOURCE_SUFFIXES
        and not name.startswith("delivery/output/")
    ]
    for path in sources:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"(?:usd)?geospatial[F]resh", text, re.I), path
        if path.suffix == ".py":
            tree = ast.parse(text, filename=str(path))
            assert not any(
                isinstance(node, ast.ImportFrom)
                and any(alias.name == "*" for alias in node.names)
                for node in ast.walk(tree)
            ), "Wildcard import: " + str(path)
            assert not any(
                token.type == tokenize.OP and token.string == ";"
                for token in tokenize.generate_tokens(io.StringIO(text).readline)
            ), "Compressed Python statements: " + str(path)
        if path.suffix in (".cpp", ".h"):
            assert all(
                len(line) <= 160 for line in text.splitlines()
            ), "Compressed C++ source: " + str(path)
            assert not re.search(
                r"using\s+[JOLVMP]\s*=", text
            ), "Opaque type alias: " + str(path)
    schema = (ROOT / "schema/generatedSchema.usda").read_text(encoding="utf-8")
    plugins = json.loads((ROOT / "schema/plugInfo.json").read_text(encoding="utf-8"))
    assert 'libraryName = "usdGeospatial"' in schema
    assert plugins["Plugins"][0]["Name"] == "usdGeospatial"
    guide = (ROOT / "REVIEWING.md").read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", guide):
        assert (
            target == "evidence/reviewability.json"
            or (ROOT / target.split("#")[0]).is_file()
        ), ("Broken review link: " + target)
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for pattern in ("evidence/**", "inputs/authored/**", "delivery/output/**"):
        assert pattern + " linguist-generated=true" in attributes
    assert "inputs/original/** linguist-vendored=true" in attributes
    for document in ("README.md", "REVIEW.md"):
        text = (ROOT / document).read_text(encoding="utf-8")
        assert "REVIEWING.md" in text, "Missing review entry point: " + document
        assert "/blob/geospatial-crs-proposal/" in text
        assert not re.search(r"/blob/[a-f0-9]{40}/proposals/", text)
    report = {
        "pass": True,
        "scope": "Review prerequisites, not an automated proof of readability or conformance",
        "source_files_checked": len(sources),
        "deliverable_files": len(files),
        "counts": dict(sorted(Counter(groups.values()).items())),
        "files": groups,
    }
    destination = ROOT / "evidence/reviewability.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "files"}))


if __name__ == "__main__":
    check()
