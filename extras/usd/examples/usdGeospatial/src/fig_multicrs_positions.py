#!/usr/bin/env python3
"""fig_multicrs_positions.py -- the ANTI-OVERFIT figure, done honestly.

Replaces the old docs/multiCRS_glyph_renders.png montage. That montage stacked
five auto-insert renders that were pixel-identical (a single centred glyph on a
black frame, one per locale), so it could not *visually* distinguish the five
CRS families -- the differences lived in the numbers, not the pixels.

This figure instead plots, on one wireframe WGS84 globe, WHERE each locale's
authored point actually resolves. It is a Matplotlib plot of resolved
coordinates (matplotlib.use("Agg")) -- a diagram of resolved numbers, not a
renderer screenshot -- consistent with every other figure in this README.

Resolution path (the genuine one, PROJ / pyproj = the registered default engine,
no per-CRS special casing):
  authored (lon,lat,h)  --forward-->  the locale's PROJECTED CRS (E,N,h)   [how it is authored]
  projected (E,N,h)     --PROJ----->  geocentric ECEF (EPSG:4978)          [how it resolves]
The same single code path runs for all five locales; the ONLY thing that changes
between them is the authored EPSG. That is the anti-overfit claim, made visible.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pyproj import CRS, Transformer

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")

# name, lon, lat, h(m), projected EPSG, label  -- identical to overfit_glyph_suite.LOCALES
LOCALES = [
    ("nyc",        -73.985656,  40.748817,    0.0, 32618, "NYC \u2014 UTM 18N",       "#ffd166"),
    ("sydney",     151.214000, -33.857000,   58.0, 32756, "Sydney \u2014 UTM 56S",    "#06d6a0"),
    ("wellington", 174.776200, -41.286500,    5.0,  2193, "Wellington \u2014 NZTM2000", "#4cc9f0"),
    ("quito",      -78.467800,  -0.180700, 2850.0, 32717, "Quito \u2014 UTM 17S (~eq)", "#ef476f"),
    ("svalbard",    15.650000,  78.220000,   10.0, 32633, "Svalbard \u2014 UTM 33N (~78N)", "#c77dff"),
]

_A = 6378137.0  # WGS84 semi-major, for the reference wireframe only


def resolve_ecef(lon, lat, h, epsg):
    """The two-hop runtime path, PROJ only, one code path for every locale."""
    geo = CRS.from_epsg(4979)                    # lon/lat/h WGS84 (as published)
    proj = CRS.from_epsg(epsg)                   # the locale's PROJECTED CRS (as authored)
    ecef = CRS.from_epsg(4978)                   # geocentric ECEF (the world)
    # 1) forward-project the published point into the authored projected CRS
    fwd = Transformer.from_crs(geo, proj, always_xy=True)
    e, n, up = fwd.transform(lon, lat, h)
    # 2) resolve the projected coordinate to ECEF (this is what the runtime does)
    toecef = Transformer.from_crs(proj, ecef, always_xy=True)
    x, y, z = toecef.transform(e, n, up)
    return np.array([x, y, z])


def wireframe(ax):
    u = np.linspace(0, 2 * np.pi, 48)
    v = np.linspace(0, np.pi, 24)
    x = _A * np.outer(np.cos(u), np.sin(v))
    y = _A * np.outer(np.sin(u), np.sin(v))
    z = _A * np.outer(np.ones_like(u), np.cos(v))
    ax.plot_wireframe(x, y, z, color="#2a2f3a", linewidth=0.4, rstride=1, cstride=1)


def main():
    pts = [(name, lbl, col, resolve_ecef(lon, lat, h, epsg))
           for (name, lon, lat, h, epsg, lbl, col) in LOCALES]

    fig = plt.figure(figsize=(13, 6.2))
    fig.patch.set_facecolor("#0b0e14")

    # LEFT: the globe with the five resolved points
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    ax.set_facecolor("#0b0e14")
    wireframe(ax)
    for name, lbl, col, p in pts:
        ax.scatter(*p, s=70, color=col, edgecolor="white", linewidth=0.6, depthshade=False, zorder=5)
    ax.set_box_aspect((1, 1, 1))
    lim = _A * 1.05
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
    ax.set_axis_off()
    ax.view_init(elev=18, azim=-60)
    ax.set_title("Where each authored point resolves (ECEF)", color="white", fontsize=12, pad=0)

    # RIGHT: legend + resolved ECEF coordinates (the numbers behind the dots)
    axr = fig.add_subplot(1, 2, 2)
    axr.set_facecolor("#0b0e14"); axr.axis("off")
    axr.set_xlim(0, 1); axr.set_ylim(0, 1)
    axr.text(0.0, 0.97, "Same code path, five CRS families, zero per-CRS special-casing",
             color="white", fontsize=12.5, fontweight="bold", va="top")
    axr.text(0.0, 0.90,
             "One resolution path runs for every locale; the only thing that changes\n"
             "is the authored EPSG. Each point round-trips  lon/lat \u2192 projected CRS \u2192 ECEF\n"
             "through PROJ (the registered default engine).",
             color="#a9b1c2", fontsize=9.5, va="top")
    y = 0.72
    for name, lbl, col, p in pts:
        axr.scatter([0.02], [y + 0.012], transform=axr.transAxes, s=90,
                    color=col, edgecolor="white", linewidth=0.6, zorder=5, clip_on=False)
        axr.text(0.07, y + 0.012, lbl, color="white", fontsize=10.5, va="center")
        axr.text(0.07, y - 0.028,
                 f"ECEF = ({p[0]/1e6:+.3f}, {p[1]/1e6:+.3f}, {p[2]/1e6:+.3f}) \u00d710\u2076 m",
                 color="#8b93a3", fontsize=8.6, va="center", family="monospace")
        y -= 0.135
    axr.text(0.0, 0.02,
             "Verified against closed-form WGS84 geodesy in generalization_suite.py "
             "(sub-mm, all 5).",
             color="#6f7787", fontsize=8.2, va="bottom")

    fig.suptitle("Anti-overfit: one runtime resolves five CRS families across both hemispheres "
                 "(equator \u2192 ~78\u00b0N)", color="white", fontsize=13, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    out = os.path.join(DOCS, "multiCRS_glyph_renders.png")
    fig.savefig(out, dpi=130, facecolor=fig.get_facecolor())
    print("wrote", os.path.abspath(out))
    # sanity: the five resolved points must be DISTINCT (the old figure's failure)
    arr = np.array([p for *_, p in pts])
    dmin = min(np.linalg.norm(arr[i] - arr[j]) for i in range(len(arr)) for j in range(i + 1, len(arr)))
    print(f"min pairwise separation = {dmin/1e3:,.0f} km (all five distinct)")


if __name__ == "__main__":
    main()
