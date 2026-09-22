"""Generate measured scientific figures for the README and derived slides."""
import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pxr import Usd

from geobuild.datasets import inspect_inventory, read_geojson, read_field
from geobuild.delivery import sha, write_json, metric
from geobuild.narrative import evidence_key

HERE = Path(__file__).resolve().parent


def build(run, dataset_root, output):
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    inventory = inspect_inventory(dataset_root)
    for identifier in ("railway", "railway-geojson", "scalar-field"):
        now = next(d for d in inventory["datasets"] if d["id"] == identifier)
        then = next(d for d in report["dataset_inventory"]["datasets"] if d["id"] == identifier)
        if now["status"] != "available" or now["files"] != then["files"]:
            raise ValueError("Figure dataset differs from tested input: " + identifier)
    if report["test_exit_code"] != 0 or not report["derivation_current"]:
        raise ValueError("Figures require passing current evidence")
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.labelcolor": "#152A36", "text.color": "#152A36"})
    geojson = read_geojson(dataset_root / "railway-source" / "1kmE4334N3375.geojson")
    stage = Usd.Stage.Open(str(dataset_root / "railway" / "deutschebahn-rails.usda"))
    anchors = {p.GetAttribute("ObjectId").Get(): tuple(p.GetAttribute("omni:geospatial:wgs84:local:position").Get())
               for p in stage.Traverse() if p.GetAttribute("ObjectId")}
    fig, ax = plt.subplots(figsize=(8.8, 5.4), layout="constrained")
    first = True
    for f in geojson["features"]:
        if f["geometry"] != "LineString":
            continue
        points = np.array(f["points"])
        ax.plot(points[:, 0], points[:, 1], color="#256C89", lw=1.1,
                label="Original GeoJSON curves" if first else None)
        lat, lon, third = anchors[f["id"]]
        ax.plot(lon, lat, ".", color="#CA6C30", ms=4, label="USD first-coordinate anchors" if first else None)
        first = False
    ax.set(xlabel="Longitude (degrees)", ylabel="Latitude (degrees)")
    ax.ticklabel_format(useOffset=False)
    ax.legend(loc="best", fontsize=10)
    fig.savefig(output / "railway.png", dpi=180)
    plt.close(fig)

    radius = 6378137.0
    angle = np.linspace(-1, 1, 400) * math.pi / 180
    expected_depth = radius * (1 - math.cos(math.pi / 180))
    observed = metric(report, "test_native_sample_midpoint_before_conversion", "wrong_order_chord_depth_m")
    if observed is None or abs(observed - expected_depth) > 1e-6:
        raise ValueError("Interpolation figure differs from tested observation")
    fig, ax = plt.subplots(figsize=(8.8, 5.4), layout="constrained")
    ax.plot(radius * np.sin(angle) / 1000, radius * np.cos(angle) - radius, color="#256C89", lw=3,
            label="Interpolate longitude, then convert")
    ax.plot([-radius * math.sin(math.pi / 180) / 1000, radius * math.sin(math.pi / 180) / 1000],
            [-expected_depth] * 2, color="#CA6C30", lw=3, label="Convert endpoints, then interpolate")
    ax.scatter([0, 0], [0, -expected_depth], color=["#256C89", "#CA6C30"], s=50)
    ax.annotate(f"{observed:,.3f} m", (0, -expected_depth / 2), xytext=(10, -expected_depth / 2), fontsize=16)
    ax.plot([0, 0], [0, -expected_depth], color="#152A36", linestyle=":")
    ax.set(xlabel="ECEF Y / east (km)", ylabel="ECEF X minus equatorial radius (m)", ylim=(-1250, 220))
    ax.legend(loc="lower center", fontsize=10)
    fig.savefig(output / "interpolation.png", dpi=180)
    plt.close(fig)

    field = read_field(dataset_root / "scalar-field" / "gfs_t2m.nc")
    values = np.array(field["values"]).reshape(field["shape"])
    points = np.array(field["points"]).reshape((*field["shape"], 3))
    order = np.argsort(points[0, :, 0])
    points, values = points[:, order, :], values[:, order]
    fig, ax = plt.subplots(figsize=(8.8, 5.4), layout="constrained")
    plot = ax.pcolormesh(points[:, :, 0], points[:, :, 1], values, shading="nearest", cmap="viridis")
    fig.colorbar(plot, ax=ax, label="Raw value (units unverified)", shrink=.85)
    ax.set(xlabel="Source longitude values", ylabel="Source latitude values")
    fig.savefig(output / "field.png", dpi=180)
    plt.close(fig)
    write_json(output / "manifest.json", {"evidence_key": evidence_key(report),
               "dataset_catalog_sha256": report["dataset_inventory"]["catalog_sha256"],
               "files": {name: sha(output / name) for name in ("railway.png", "interpolation.png", "field.png")}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "docs" / "figures")
    args = parser.parse_args()
    build(args.run, args.dataset_root, args.output)
