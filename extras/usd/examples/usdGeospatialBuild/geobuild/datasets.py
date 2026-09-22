"""Data-only intake and workflow evidence. No legacy runtime imports or scripts."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "dataset-catalog.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_catalog(path=CATALOG):
    catalog = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = [d["id"] for d in catalog["datasets"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate dataset identifier")
    for workflow in catalog["workflows"]:
        if not set(workflow["datasets"]) <= set(ids):
            raise ValueError("Unknown workflow dataset")
    return catalog


def cache_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if path == root or root not in path.parents:
        raise ValueError("Dataset path escapes cache")
    return path


def check_cache_root(root):
    root = Path(root).resolve()
    repo = next((p for p in ROOT.parents if (p / ".git").exists()), ROOT)
    if root == repo or repo in root.parents:
        raise ValueError("Dataset cache must be outside the source repository")
    return root


def inspect_inventory(root=None, catalog=None, aeco=False):
    catalog = catalog or load_catalog()
    inventory = {"catalog_sha256": sha(CATALOG), "datasets": []}
    for item in catalog["datasets"]:
        files = []
        for expected in item["files"]:
            path = cache_path(root, expected["path"]) if root else None
            present = bool(path and path.is_file())
            if present and (path.stat().st_size != expected["bytes"] or sha(path) != expected["sha256"]):
                raise ValueError("Dataset differs from pinned input: " + expected["path"])
            files.append({"path": expected["path"], "sha256": expected["sha256"], "present": present,
                          "local_path": str(path) if present else None})
        if files:
            count = sum(f["present"] for f in files)
            status = "available" if count == len(files) else "missing" if count == 0 else "incomplete"
        else:
            status = item.get("availability", "available")
        if item["id"] == "aeco":
            status = "available" if aeco else "missing"
        inventory["datasets"].append({"id": item["id"], "label": item["label"], "status": status,
                                      "kind": item["kind"], "provenance": item["provenance"], "files": files})
    return inventory


def public_inventory(inventory):
    return {"catalog_sha256": inventory["catalog_sha256"], "datasets": [
        {**{k: v for k, v in item.items() if k != "files"},
         "files": [{k: f[k] for k in ("path", "sha256", "present")} for f in item["files"]]}
        for item in inventory["datasets"]]}


def fetch_public(root):
    root = check_cache_root(root)
    for item in load_catalog()["datasets"]:
        for entry in item["files"]:
            if "url" not in entry:
                continue
            path = cache_path(root, entry["path"])
            if path.exists():
                if sha(path) != entry["sha256"]:
                    raise ValueError("Existing cache differs: " + entry["path"])
                continue
            data = urllib.request.urlopen(entry["url"], timeout=60).read(entry["bytes"] + 1)
            if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError("Download differs from pinned input: " + entry["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return public_inventory(inspect_inventory(root))


def import_local(root, dataset, source):
    root = check_cache_root(root)
    item = next((d for d in load_catalog()["datasets"] if d["id"] == dataset), None)
    if not item or len(item["files"]) != 1 or "url" in item["files"][0]:
        raise ValueError("Choose a single-file local dataset")
    entry = item["files"][0]
    source = Path(source).resolve()
    if source.stat().st_size != entry["bytes"] or sha(source) != entry["sha256"]:
        raise ValueError("Local input differs from the catalog; review provenance before updating it")
    target = cache_path(root, entry["path"])
    if target.exists() and sha(target) != entry["sha256"]:
        raise ValueError("Existing cache differs")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source != target:
        shutil.copyfile(source, target)
    return public_inventory(inspect_inventory(root))


def read_geojson(path):
    """Read the supplied source as data; preserve rings and feature identity."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("type") != "FeatureCollection" or not isinstance(doc.get("features"), list):
        raise ValueError("Expected a GeoJSON FeatureCollection")
    features = []
    ids = set()
    for feature in doc["features"]:
        identity = feature.get("properties", {}).get("object_id")
        if not isinstance(identity, str) or not identity or identity in ids:
            raise ValueError("Missing or duplicate railway object_id")
        ids.add(identity)
        geometry = feature.get("geometry") or {}
        kind, coordinates = geometry.get("type"), geometry.get("coordinates")
        if kind == "LineString":
            parts = [coordinates]
        elif kind == "Polygon":
            parts = coordinates
        elif kind == "MultiPolygon":
            parts = [ring for polygon in coordinates for ring in polygon]
        else:
            raise ValueError("Unsupported railway geometry")
        if not parts or any(not part for part in parts):
            raise ValueError("Empty railway geometry")
        points = [tuple(point) for part in parts for point in part]
        if any(len(p) != 3 or any(not isinstance(v, (float, int)) or not math.isfinite(v) for v in p)
               or not -180 <= p[0] <= 180 or not -90 <= p[1] <= 90 for p in points):
            raise ValueError("Invalid railway longitude/latitude/third ordinate")
        features.append({"id": identity, "geometry": kind, "parts": parts, "points": points,
                         "polygon_ring_counts": [len(p) for p in coordinates] if kind == 'MultiPolygon' else [len(parts)] if kind == 'Polygon' else [],
                         "properties": feature["properties"]})
    return {"crs": doc.get("crs"), "features": features,
            "geometry_counts": dict(Counter(f["geometry"] for f in features))}


def read_field(path):
    """Pinned HDF5 sample, retaining unknown scientific metadata as unknown."""
    import h5py
    with h5py.File(path, "r") as file:
        lat, lon, values = (file[name][...] for name in ("lat", "lon", "t2m"))
    if lat.ndim != 1 or lon.ndim != 1 or values.shape != (len(lat), len(lon)):
        raise ValueError("Unexpected scalar-field axes or shape")
    points, scalar = [], []
    for row, latitude in enumerate(lat):
        for col, longitude in enumerate(lon):
            # Explicit diagnostic interpretation, never a runtime default.
            x = (float(longitude) + 180) % 360 - 180
            y, value = float(latitude), float(values[row, col])
            if not -90 <= y <= 90 or not all(map(math.isfinite, (x, y, value))):
                raise ValueError("Invalid scalar-field sample")
            points.append((x, y, 0.0))
            scalar.append(value)
    return {"shape": tuple(values.shape), "points": points, "values": scalar}


def workflow_evidence(catalog, report):
    result = []
    datasets = {d["id"]: d for d in report["dataset_inventory"]["datasets"]}
    for workflow in catalog["workflows"]:
        tests = [t for t in report["tests"] if any(t["name"].startswith(p) for p in workflow["tests"])]
        states = {t["status"] for t in tests}
        if not report["derivation_current"]:
            status = "STALE"
        elif "failed" in states:
            status = "CHECK_FAILED"
        elif "passed" in states:
            status = "COMPONENT_EVIDENCE_ONLY"
        elif "skipped" in states:
            status = "NOT_EXERCISED"
        else:
            status = "AWAITING_IMPLEMENTATION"
        full=[t for t in tests if t['name'].startswith('test_complete_'+workflow['id']+'_')]
        validated=bool(full) and all(t['status']=='passed' for t in full) and report['derivation_current']
        if validated:
            status='CONDITIONAL_WORKFLOW_PASSED'
        result.append({**workflow, "status": status, "full_workflow_validated": validated,
                       "dataset_status": {i: datasets[i]["status"] for i in workflow["datasets"]},
                       "checks": [{"name": t["name"], "status": t["status"]} for t in tests]})
    return result


def render_workflows(source, report):
    titles = {r["number"]: r["title"] for r in source["requirements"]}
    lines = ["# Datasets and workflow evidence", "",
             "Source data and workflows are reused; current requirements determine behavior and acceptance.",
             "A conditional workflow passes only when its full demonstration runs; policy choices and data interpretation remain explicit.", "", "## Data available in this run", ""]
    for item in report["dataset_inventory"]["datasets"]:
        lines += [f"- **{item['label']}**: {item['status']}. {item['provenance']}"]
    for workflow in report["workflows"]:
        lines += ["", f"## {workflow['id']}: {workflow['title']}", "", workflow["question"], "",
                  "Requirements: " + "; ".join(f"R{n}, {titles[n]}" for n in workflow["requirements"]), "",
                  "Demonstration: " + workflow["demonstration"], "", "Reference: " + workflow["oracle"], "",
                  "This run: **" + workflow["status"] + "**. " +
                  (", ".join(t["name"] + ": " + t["status"] for t in workflow["checks"]) or "No runnable check yet."), "",
                  "Open design/interpretation questions: " + workflow["remaining"], "", "Dependent decisions: " + ", ".join(workflow["stops"])]
    return "\n".join(lines) + "\n"
