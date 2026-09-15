#!/usr/bin/env python3
"""
fig_runtime_parity.py -- VISUAL parity proof: the same scene rendered through
TWO viable runtime implementations of the same codeless schema:

   (A) Python reference runtime   -- resolve_runtime.py (oracle / behavior spec)
   (B) C++ Hydra scene index      -- usdGeospatialSceneIndex (compiled, illustrative runtime)

Both consume the SAME authored stage (out/railway_georef.usda: real NVIDIA
Deutsche Bahn rails on geospatial tiles, in our crs:binding/crs:position schema).
Both produce a "rails on tiles" picture; the figure draws them side-by-side and
reports the worst per-vertex disagreement (sub-mm).

Inputs:
   /tmp/hydra_railway_xforms.tsv   (one row per prim:
                                    primPath \t 16 doubles row-major xform)
   produced by  ../usdGeospatialSceneIndex/dumpHydraXforms

Output: docs/runtime_parity.png
"""
import os, sys, tempfile, argparse
import numpy as np
try:                                    # matplotlib/PIL are only needed to DRAW the
    import matplotlib.pyplot as plt     # figure; --check mode (the ctest parity gate)
    from PIL import Image               # is numpy-only, so it runs on a headless box
except Exception:                       # without a plotting stack installed.
    plt = None
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
import _schema_setup        # noqa
import resolve_runtime as rr
from pxr import Usd, Gf
from pyproj import CRS
ECEF = CRS.from_epsg(4978)

# STAGE/OUT/TOL honor an env override so the parity ctest driver
# (../usdGeospatialSceneIndex/run_runtime_parity.py) can point at a scene it
# generated in a work dir and a throwaway figure path -- without touching the
# committed docs/ figure -- and set the gate threshold explicitly.
STAGE = os.environ.get("GEO_RAILWAY_STAGE", os.path.join(HERE, "out", "railway_georef.usda"))
# Portable: honor GEO_HYDRA_TSV (set by render_figures.py), else the system temp
# dir -- not a hardcoded /tmp (so this works on Windows/macOS too).
HYDRA_TSV = os.environ.get(
    "GEO_HYDRA_TSV", os.path.join(tempfile.gettempdir(), "hydra_railway_xforms.tsv"))
OUT = os.environ.get("GEO_RUNTIME_PARITY_OUT", os.path.join(HERE, "docs", "runtime_parity.png"))
# The gate: worst per-vertex Python-vs-Hydra disagreement must stay under this (mm).
# Wired as ctest testUsdGeospatialRuntimeParity; the process exits non-zero above it.
TOL_MM = float(os.environ.get("GEO_PARITY_TOL_MM", "1.0"))
TEXDIR = os.path.join(HERE, "data", "thirdparty")


def load_hydra_xforms(path):
    M = {}
    with open(path) as f:
        for line in f:
            t = line.rstrip("\n").split("\t")
            if len(t) != 17:
                continue
            primpath = t[0]
            vals = [float(v) for v in t[1:17]]
            # row-major Gf row-vector layout: [m00..m03, m10..m13, ...]
            mat = Gf.Matrix4d(*vals)
            M[primpath] = mat
    return M


def shared_enu_basis(stage):
    """Centroid-of-georef ENU frame (matches render_figures._railway_local_geometry)."""
    georef = [p for p in stage.Traverse() if p.GetAttribute("crs:position")]
    lons = np.array([p.GetAttribute("crs:position").Get()[0] for p in georef])
    lats = np.array([p.GetAttribute("crs:position").Get()[1] for p in georef])
    lon0, lat0 = float(lons.mean()), float(lats.mean())
    a = 6378137.0; f = 1/298.257223563; e2 = f*(2-f)
    lm = np.radians(lon0); ph = np.radians(lat0)
    N = a / np.sqrt(1 - e2 * np.sin(ph) ** 2)
    o = np.array([(N) * np.cos(ph) * np.cos(lm),
                  (N) * np.cos(ph) * np.sin(lm),
                  (N * (1 - e2)) * np.sin(ph)])
    east = np.array([-np.sin(lm), np.cos(lm), 0.0])
    north = np.array([-np.sin(ph)*np.cos(lm), -np.sin(ph)*np.sin(lm), np.cos(ph)])
    return o, east, north, lon0, lat0


def to_en(world_xyz, o, east, north):
    v = np.array(world_xyz) - o
    return np.array([v @ east, v @ north])


def collect_tiles_rails(stage, get_xform):
    """get_xform(prim) -> Gf.Matrix4d that takes the prim's local geometry to
    world (ECEF). Returns (tiles, rails)."""
    o, east, north, lon0, lat0 = shared_enu_basis(stage)
    tiles = []
    for t in stage.Traverse():
        if not (t.GetName().startswith("MapGeo") and t.GetAttribute("crs:position")):
            continue
        M = get_xform(t)
        if M is None:
            continue
        for c in t.GetChildren():
            if c.GetTypeName() == "Mesh" and c.GetAttribute("points"):
                pts = c.GetAttribute("points").Get()
                if not pts:
                    continue
                corners = np.array([to_en(M.Transform(Gf.Vec3d(*p)), o, east, north)
                                    for p in pts])
                stp = c.GetAttribute("primvars:st")
                uvs = (np.array([list(uv) for uv in stp.Get()])
                       if stp and stp.Get() else None)
                tiles.append({"name": t.GetName(), "corners": corners, "uvs": uvs})
    rails = []
    rail_world = []     # raw ECEF points for parity stats
    for r in stage.Traverse():
        if not (r.GetName().startswith("CurveXform") and r.GetAttribute("crs:position")):
            continue
        M = get_xform(r)
        if M is None:
            continue
        for c in r.GetChildren():
            if c.GetTypeName() == "BasisCurves" and c.GetAttribute("points"):
                pts = c.GetAttribute("points").Get()
                if not pts:
                    continue
                w = np.array([list(M.Transform(Gf.Vec3d(*p))) for p in pts])
                rail_world.append(w)
                rails.append(np.array([to_en(p, o, east, north) for p in w]))
    # tile texture lookup
    for tl in tiles:
        idx = tl["name"].replace("MapGeo", "")
        cand = os.path.join(TEXDIR, f"quadnode-{idx}.png")
        tl["tex"] = cand if os.path.exists(cand) else None
    return tiles, rails, rail_world, (lon0, lat0)


def _draw_uv_textured_quad(ax, img, corners_en, uvs, **imshow_kw):
    """Place image pixel (s,t) at the world-EN corner carrying that st (honors
    the asset's UsdUVTexture/st mapping for any quad orientation), via an affine
    UV->EN transform; bbox fallback only if UVs are missing."""
    import matplotlib.transforms as mtransforms
    if uvs is None or corners_en is None or len(corners_en) < 4:
        c = corners_en
        ax.imshow(img, extent=[c[:, 0].min(), c[:, 0].max(),
                               c[:, 1].min(), c[:, 1].max()],
                  origin="upper", **imshow_kw)
        return
    S = np.column_stack([uvs[:, 0], uvs[:, 1], np.ones(len(uvs))])
    A, *_ = np.linalg.lstsq(S, np.asarray(corners_en), rcond=None)  # (3,2)
    # origin="upper": image row 0 (picture top) -> t=1, bottom row -> t=0, per st.
    # (origin="lower" flips the texture N/S -- the mirrored-tile bug.)
    im = ax.imshow(img, extent=[0, 1, 0, 1], origin="upper", **imshow_kw)
    aff = mtransforms.Affine2D(matrix=np.array([
        [A[0, 0], A[1, 0], A[2, 0]],
        [A[0, 1], A[1, 1], A[2, 1]],
        [0.0,     0.0,     1.0],
    ]))
    im.set_transform(aff + ax.transData)


def draw_rails_on_tiles(ax, tiles, rails, title_top, title_sub):
    ax.set_title(f"{title_top}\n{title_sub}", fontsize=10.5, loc="left", pad=8)
    for tl in tiles:
        c = tl["corners"]
        if c is None:
            continue
        emin, emax = c[:, 0].min(), c[:, 0].max()
        nmin, nmax = c[:, 1].min(), c[:, 1].max()
        if tl["tex"]:
            img = np.asarray(Image.open(tl["tex"]).convert("RGB"))
            # Faithful UV-mapped draw (asset st convention), not a bbox stretch.
            _draw_uv_textured_quad(ax, img, c, tl.get("uvs"), zorder=1, alpha=0.95)
        else:
            ax.add_patch(plt.Rectangle((emin, nmin), emax - emin, nmax - nmin,
                         fc="#cdd6df", ec="#8a97a6", zorder=1))
        ax.add_patch(plt.Rectangle((emin, nmin), emax - emin, nmax - nmin,
                     fill=False, ec="#2c3e50", lw=1.0, zorder=3))
        ax.text(emin + 12, nmax - 12, tl["name"], fontsize=7.5, va="top",
                color="white", zorder=4,
                bbox=dict(facecolor="#2c3e50", alpha=0.7, edgecolor="none",
                          boxstyle="round,pad=0.18"))
    for r in rails:
        ax.plot(r[:, 0], r[:, 1], "-", color="#d62728", lw=0.55, zorder=5, alpha=0.95)
    ax.set_xlabel("East (m, local ENU)")
    ax.set_ylabel("North (m, local ENU)")
    ax.set_aspect("equal")
    ax.grid(alpha=0.25, zorder=0)


def measure(stage, hydra):
    """Per-vertex Python-vs-Hydra parity from the same authored stage. numpy-only
    (no matplotlib/PIL) so the parity gate runs on a headless box."""
    cache = {}

    def py_xform(prim):
        M, _ = rr.anchor_frame(prim, ECEF, cache)
        return M

    def hy_xform(prim):
        return hydra.get(str(prim.GetPath()))

    print("[fig_runtime_parity] resolving via Python reference runtime...")
    tiles_py, rails_py, rw_py, info = collect_tiles_rails(stage, py_xform)
    print(f"  python: {len(tiles_py)} tiles, {len(rails_py)} rails")
    print("[fig_runtime_parity] resolving via Hydra scene index...")
    tiles_hy, rails_hy, rw_hy, _ = collect_tiles_rails(stage, hy_xform)
    print(f"  hydra : {len(tiles_hy)} tiles, {len(rails_hy)} rails")

    # per-vertex parity (ECEF, not the projected ENU)
    n = min(len(rw_py), len(rw_hy))
    all_d = []
    for a, b in zip(rw_py[:n], rw_hy[:n]):
        if a.shape != b.shape:
            continue
        all_d.append(np.linalg.norm(a - b, axis=1) * 1e3)  # mm
    all_d = np.concatenate(all_d) if all_d else np.array([0.0])
    worst_mm = float(all_d.max())
    median_mm = float(np.median(all_d))
    print(f"  per-vertex disagreement: median={median_mm:.4f} mm  worst={worst_mm:.4f} mm  "
          f"({all_d.size} verts)")

    # also: tile-corner parity
    tile_max_mm = 0.0
    for ta, tb in zip(tiles_py, tiles_hy):
        d = np.linalg.norm(ta["corners"] - tb["corners"], axis=1) * 1e3
        if d.size:
            tile_max_mm = max(tile_max_mm, float(d.max()))

    return dict(tiles_py=tiles_py, rails_py=rails_py, tiles_hy=tiles_hy, rails_hy=rails_hy,
                all_d=all_d, worst_mm=worst_mm, median_mm=median_mm,
                tile_max_mm=tile_max_mm, info=info)


def _draw_figure(R):
    """Render docs/runtime_parity.png (side-by-side runtimes + histogram) from a
    measure() result. matplotlib/PIL are only reached here, never in --check mode."""
    tiles_py, rails_py = R["tiles_py"], R["rails_py"]
    tiles_hy, rails_hy = R["tiles_hy"], R["rails_hy"]
    all_d = R["all_d"]
    worst_mm, median_mm, tile_max_mm, info = (
        R["worst_mm"], R["median_mm"], R["tile_max_mm"], R["info"])

    # ---------------- figure ----------------
    fig = plt.figure(figsize=(16.0, 9.6), constrained_layout=False)
    gs = fig.add_gridspec(2, 2, height_ratios=[3.0, 1.6], hspace=0.32, wspace=0.06,
                          left=0.05, right=0.985, top=0.92, bottom=0.07)
    fig.suptitle(
        "Two runtimes, one schema — the same authored stage rendered through "
        "the Python reference runtime and the compiled Hydra scene index",
        fontsize=13, fontweight="bold")

    axL = fig.add_subplot(gs[0, 0])
    axR = fig.add_subplot(gs[0, 1])
    sub = (f"NVIDIA Deutsche Bahn rails on geospatial tiles · "
           f"local ENU about ({info[1]:.3f}°N, {info[0]:.3f}°E)")
    draw_rails_on_tiles(
        axL, tiles_py, rails_py,
        "(A) Python reference runtime   resolve_runtime.py",
        sub + "  ·  every position resolved in pure Python")
    draw_rails_on_tiles(
        axR, tiles_hy, rails_hy,
        "(B) C++ Hydra scene index   usdGeospatialSceneIndex (compiled)",
        sub + "  ·  every position pulled via HdXformSchema, as a renderer would")

    # bottom panel: histogram of per-vertex disagreement
    axH = fig.add_subplot(gs[1, :])
    nbins = 60
    axH.hist(all_d, bins=nbins, color="#2e7d32", alpha=0.85, edgecolor="#1b5e20")
    axH.axvline(median_mm, color="#0d47a1", lw=1.2, ls="--", label=f"median {median_mm:.4f} mm")
    axH.axvline(worst_mm,  color="#b71c1c", lw=1.2, ls="--", label=f"worst  {worst_mm:.4f} mm")
    axH.set_xlabel("per-vertex world-space disagreement, Python vs Hydra (mm, ECEF)")
    axH.set_ylabel("vertex count")
    axH.set_title(f"Quantified agreement across {all_d.size:,} rail vertices + "
                  f"{sum(len(t['corners']) for t in tiles_py)} tile corners — "
                  "both runtimes resolve the same authored crs:binding/crs:position to the same world points",
                  fontsize=10, loc="left", pad=6)
    axH.legend(loc="upper right", fontsize=9)
    axH.grid(alpha=0.3)

    # disagreement banner
    ann = (f"per-vertex disagreement (ECEF):  median {median_mm:.4f} mm  ·  "
           f"worst {worst_mm:.4f} mm  ·  tile corners worst {tile_max_mm:.4f} mm  "
           f"(N={all_d.size:,} rail verts + {sum(len(t['corners']) for t in tiles_py)} tile corners)")
    fig.text(0.5, 0.012, ann, ha="center", va="bottom", fontsize=9.5,
             bbox=dict(boxstyle="round,pad=0.45", fc="#eaf6ea", ec="#2e7d32"))

    fig.savefig(OUT, dpi=150, facecolor="white")
    print(f"[fig_runtime_parity] -> {OUT}")


def main(check_only=False):
    if not os.path.exists(STAGE):
        sys.exit(f"missing stage {STAGE}; generate the railway scene first "
                 "(../usdGeospatialSceneIndex/run_runtime_parity.py does this)")
    stage = Usd.Stage.Open(STAGE)
    if not os.path.exists(HYDRA_TSV):
        sys.exit(f"missing {HYDRA_TSV}; build & run dumpHydraXforms first "
                 "(see ../usdGeospatialSceneIndex/run_parity.py)")
    hydra = load_hydra_xforms(HYDRA_TSV)
    R = measure(stage, hydra)
    if not check_only:
        if plt is None:
            print("[fig_runtime_parity] matplotlib/PIL unavailable; skipping figure "
                  "(the parity numbers above still gate)")
        else:
            _draw_figure(R)
    print(f"[fig_runtime_parity] worst per-vertex = {R['worst_mm']:.4f} mm  (tol {TOL_MM:g} mm)")
    if R["worst_mm"] > TOL_MM:
        sys.exit(f"PARITY FAIL (>{TOL_MM:g} mm)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Python-vs-Hydra runtime parity: figure (default) or gate (--check).")
    ap.add_argument("--check", action="store_true",
                    help="gate only: measure parity, exit non-zero if worst > tol; no figure "
                         "(used by ctest testUsdGeospatialRuntimeParity).")
    a = ap.parse_args()
    main(check_only=a.check)
