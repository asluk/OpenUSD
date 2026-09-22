"""Evidence inventory. Partner data stays outside Git and is never executed."""
import hashlib
import zipfile
from pathlib import Path


def inspect_aeco(archive, output_dir):
    archive = Path(archive).resolve()
    required = ["README.md", "site.usda", "crs_library.usda", "La_tour_Eiffel.usdz"]
    manifest = {"path": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "origin": "Sébastien Vielliard, AECO example received 2026-09-16",
                "redistribution": "not established; kept local",
                "role": "partner-authored stock-USD baseline; not an approved scene-resolution fixture"}
    with zipfile.ZipFile(archive) as z:
        members = {i.filename: i for i in z.infolist()}
        manifest["members"] = [{"name": i.filename, "bytes": i.file_size} for i in z.infolist()]
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        # Fixed allow-list; no archive-controlled paths, scripts, or extraction tools.
        for name in required:
            key = "aeco_site_example/" + name
            if key not in members or members[key].file_size > 32 * 1024 * 1024:
                raise ValueError(f"Missing or oversized AECO fixture: {key}")
            (output_dir / name).write_bytes(z.read(key))
    manifest["scene"] = str(output_dir / "site.usda")
    return manifest
