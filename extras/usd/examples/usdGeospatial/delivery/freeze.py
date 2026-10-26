"""Freeze final evidence, input/schema inventory and reproducibility provenance."""

import json, hashlib, platform
from pathlib import Path
import pyproj
from pxr import Usd
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from reviewability import check as check_reviewability

check_reviewability()

root = Path(__file__).resolve().parents[1]
audit = root / "audit"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


checks = json.loads((root / "evidence/checks.json").read_text(encoding="utf-8"))
assert len(checks) == 19 and all(x["pass"] for x in checks)
original = json.loads((audit / "original-inputs.json").read_text(encoding="utf-8"))
assert len(original) == 23
assert all(sha(root / x["path"]) == x["sha256"] for x in original)
allowed = {
    "crs:wkt",
    "crs:position",
    "crs:orientation",
    "data:asset",
    "data:format",
    "data:field",
    "data:coordinateDomain",
}
fields = set()
for file in (root / "inputs/authored").glob("*.usda"):
    if file.name == "tower-storm-view.usda":
        continue
    s = Usd.Stage.Open(str(file))
    for p in s.TraverseAll():
        for a in p.GetAttributes():
            if a.GetName().startswith(("crs:", "data:")):
                fields.add(a.GetName())
assert fields <= allowed, fields - allowed
authority = {
    "proposal_commit": "4120379fa12473b54a8f8e11999a1cefa5443614",
    "proposal_blob": "2386f16283df435ccb4304a3972d51e26d4be311",
    "proposal_sha256": "035c4bb5312862567176045e18d3f9d4b0da145b51db8275e457b73318b28b42",
    "stock_upstream_base": "5bc38c9d8799d16ce20ade219a464beaeae548cc",
    "implementation_origin": "New Python/C++ readers, schemas, fixtures and tests derived from frozen proposal. Previous geospatial implementations/fixture logic/generated expectations did not seed this run.",
    "reused": "Original input bytes; installed neutral SDK/build libraries; neutral Storm frame recorder.",
    "independence_limit": "Same agent and PROJ family; provider control tables were generated with PROJ.",
    "Python": platform.python_version(),
    "Python_USD": list(Usd.GetVersion()),
    "Python_PROJ": pyproj.proj_version_str,
    "native_USD": "26.11",
    "native_PROJ": "9.4.1",
    "contract_groups": 19,
    "passed": 19,
    "failed": 0,
    "original_files_byte_preserved": 23,
    "authored_geospatial_fields": sorted(fields),
    "undocumented_geospatial_fields": [],
    "acceptance": "2 mm for comparable control/reader coordinates; 1 mm for bake local detail, fixed before execution",
    "publication": "Build record; continuing delivery is described in audit/companion.json",
}
(audit / "authority.json").write_text(json.dumps(authority, indent=2))
resource_root = Path(
    "C:/Users/aluk/Documents/Codex/2026-09-21/have/work/geospatial-model-resources"
)
resources = [
    {
        "name": p.name,
        "bytes": p.stat().st_size,
        "sha256": sha(p),
        "source": "https://cdn.proj.org/" + p.name,
        "role": "Engine-selected transformation resource; not a new authored USD field",
    }
    for p in sorted(resource_root.glob("*.tif"))
]
(audit / "resources.json").write_text(json.dumps(resources, indent=2))
files = []
for folder in ("src_py", "native", "schema", "tests", "delivery"):
    for p in (root / folder).iterdir():
        if p.is_file() and p.suffix in (
            ".py",
            ".cpp",
            ".h",
            ".mjs",
            ".cmd",
            ".json",
            ".usda",
            ".txt",
        ):
            files.append({"path": p.relative_to(root).as_posix(), "sha256": sha(p)})
(audit / "source-files.json").write_text(json.dumps(files, indent=2))
artifacts = [
    root / "README.md",
    *sorted((root / "delivery/output").glob("Geospatial-USD-proposal-assessment.*")),
]
(audit / "delivery.json").write_text(
    json.dumps(
        [
            {
                "path": p.relative_to(root).as_posix(),
                "bytes": p.stat().st_size,
                "sha256": sha(p),
            }
            for p in artifacts
        ],
        indent=2,
    )
)
print(
    json.dumps(
        {
            "groups_passed": len(checks),
            "original_files": len(original),
            "fields": sorted(fields),
            "artifacts": len(artifacts),
        }
    )
)
