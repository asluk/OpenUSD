"""Scientific figures from this run's actual datasets and freshly resolved results."""

import sys, json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from pyproj import CRS, Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src_py"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from pyproj import CRS, Transformer
from common import ROOT
from pxr import Usd
from domains import read_domain, resolve_domain
from domains import read_domain, resolve_domain
from run import native, near

E = ROOT / "evidence"
F = E / "figures"
F.mkdir(exist_ok=True)
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 13,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelcolor": "#233f4b",
        "text.color": "#233f4b",
        "xtick.color": "#54707a",
        "ytick.color": "#54707a",
        "figure.facecolor": "white",
        "axes.facecolor": "#f4f7f6",
        "savefig.facecolor": "white",
    }
)

rail = json.loads((E / "railway-points.json").read_text(encoding="utf-8"))
source = np.array(rail["source"])
tr = Transformer.from_crs(4979, 32632, always_xy=True)
x, y, z = tr.transform(*source.T)
p = np.c_[x, y]
base = p.min(axis=0)
p -= base
indices = rail["indices"]
keep = [
    i
    for i in range(len(p) - 1)
    if indices[i][:-1] == indices[i + 1][:-1]
    and indices[i + 1][-1] == indices[i][-1] + 1
]
fig, ax = plt.subplots(figsize=(11, 5.5))
segs = np.array([[p[i], p[i + 1]] for i in keep])
lc = LineCollection(
    segs, cmap="viridis", norm=Normalize(z.min(), z.max()), linewidth=1.5
)
lc.set_array(np.asarray(z)[keep])
ax.add_collection(lc)
ax.autoscale()
ax.set_aspect("equal")
ax.set_xlabel("Easting from view origin (m)")
ax.set_ylabel("Northing from view origin (m)")
ax.grid(color="white")
fig.colorbar(lc, ax=ax, label="Height under selected RFC 7946 profile (m)")
fig.tight_layout()
fig.savefig(F / "railway.png", dpi=190, bbox_inches="tight")
plt.close(fig)

data = np.load(E / "westminster.npz")
raw = data["source"]
points = raw[:, :2] * (1200 / 3937)
points -= points.min(axis=0)
parts = []
heights = []
offset = 0
for count in data["segment_lengths"]:
    q = points[offset : offset + count]
    parts.extend(np.stack([q[:-1], q[1:]], axis=1))
    heights.extend(raw[offset : offset + count - 1, 2] * (1200 / 3937))
    offset += count
fig, ax = plt.subplots(figsize=(7, 6))
lc = LineCollection(parts, cmap="viridis", linewidth=0.8)
lc.set_array(np.array(heights))
ax.add_collection(lc)
ax.autoscale()
ax.set_aspect("equal")
ax.set_xlabel("Site easting from view origin (m)")
ax.set_ylabel("Site northing from view origin (m)")
ax.grid(color="white")
fig.colorbar(lc, ax=ax, label="Provider site height (m)")
fig.tight_layout()
fig.savefig(F / "westminster.png", dpi=190, bbox_inches="tight")
plt.close(fig)

s = Usd.Stage.Open(str(ROOT / "inputs/authored/domains.usda"))
p = s.GetPrimAtPath("/World/Climate")
d = read_domain(p)
source = d["coordinates"]
q = CRS.from_epsg(4978)
py = resolve_domain(p, q)
n = native(
    {
        "coordinateSource": CRS.from_epsg(4979).to_wkt(),
        "output": q.to_wkt(),
        "points": source.tolist(),
    },
    "full-climate",
)
agreement = near(py["resolved"], n["points"])
(E / "climate-comparison.json").write_text(
    json.dumps(
        {
            "samples": len(source),
            "agreement_m": agreement,
            "values_preserved": True,
            "times": d["times"],
            "source": "Original values in explicitly illustrative CF wrapper. Added height, units and observation times are example inputs, not recovered source metadata.",
        },
        indent=2,
    )
)
values = np.array(d["values"])
xyz = py["resolved"][:2664]
v = values[:2664]
minimum, maximum = np.nanpercentile(v, [2, 98])
norm = Normalize(minimum, maximum)
fig = plt.figure(figsize=(12, 5.5))
ax = fig.add_subplot(121, projection="3d")
ax.scatter(
    xyz[:, 0],
    xyz[:, 1],
    xyz[:, 2],
    c=v,
    cmap="coolwarm",
    norm=norm,
    s=11,
    alpha=0.95,
    edgecolors="none",
)
ax.set_box_aspect((1, 1, 1))
ax.set_axis_off()
ax.view_init(22, -40)
ax.set_title("The same samples in a global Cartesian frame", fontsize=13)
ax2 = fig.add_subplot(122)
lon = source[:2664, 0].reshape(72, 37)[:, 0]
lat = source[:2664, 1].reshape(72, 37)[0]
lon = (lon + 180) % 360 - 180
order = np.argsort(lon)
matrix = v.reshape(72, 37)[order].T
im = ax2.pcolormesh(
    lon[order], lat, matrix, shading="nearest", cmap="coolwarm", norm=norm
)
ax2.set_xlabel("Longitude (degrees)")
ax2.set_ylabel("Latitude (degrees)")
ax2.set_title("Values stay paired with their coordinates", fontsize=13)
fig.colorbar(im, ax=ax2, label="Illustrative temperature unit (K)", shrink=0.8)
fig.tight_layout()
fig.savefig(F / "climate.png", dpi=190)
plt.close(fig)

# The source trajectory / two-sample bake distinction is an intentional counterexample.
angles = np.linspace(-1, 1, 101)
radius = 6378137
curve = np.c_[radius * np.cos(np.radians(angles)), radius * np.sin(np.radians(angles))]
chord = np.c_[
    np.full(101, radius * np.cos(np.radians(1))),
    np.linspace(curve[0, 1], curve[-1, 1], 101),
]
fig, ax = plt.subplots(figsize=(11, 4.3))
ax.plot(
    curve[:, 1] / 1000,
    curve[:, 0] - radius,
    color="#007d88",
    lw=3,
    label="Resolve interpolated source longitude",
)
ax.plot(
    chord[:, 1] / 1000,
    chord[:, 0] - radius,
    "--",
    color="#ad6335",
    lw=3,
    label="Interpolate two exported ECEF endpoints",
)
ax.set_xlabel("Position along equator (km)")
ax.set_ylabel("Radial offset at centre (m)")
ax.grid(color="white")
ax.legend(frameon=False, loc="lower left")
fig.tight_layout()
fig.savefig(F / "sampling.png", dpi=190)
plt.close(fig)
print(
    json.dumps(
        {
            "climate_samples": len(source),
            "climate_reader_agreement_m": agreement,
            "figures": len(list(F.glob("*.png"))),
        }
    )
)
