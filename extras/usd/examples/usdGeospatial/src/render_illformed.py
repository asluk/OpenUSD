#!/usr/bin/env python3
"""
render_illformed.py -- visuals for the three guard-rail break/fix cases.

Produces one before/after figure per guard rail (see test_illformed_assets.py and
README "What breaks, and the fix"):

  docs/illformed_g1.png  anchor-vs-child ambiguity   (418.9 m off  -> 0.000 mm)
  docs/illformed_g2.png  wrong composition frame     (4.86 m off   -> 0.000 mm)
  docs/illformed_g3.png  no requires-CRS marker       (6,369 km off -> refuse)
  docs/illformed_gallery.png  the three stacked, for a single slide

Every plotted position is the ACTUAL number the shipped runtime / a naive consumer
produces, measured against independent closed-form pyproj geodesy -- the same
quantities test_illformed_assets.py prints. Nothing here is hand-drawn for effect.

House style follows render_figures.py (matplotlib Agg, dpi ~130).
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crs_engine as ce
from pxr import Usd, UsdGeom, Sdf, Gf
from pyproj import CRS, Transformer
import resolve_runtime as rr
import test_illformed_assets as ill   # reuse the exact scene builders + constants

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")

BAD_FC, BAD_EC = "#fde0dc", "#c0392b"
OK_FC, OK_EC = "#e3f0ff", "#2c6fbb"
TRUTH_C = "#2e7d32"
GRID = "#d9dde3"


def _enu_local(ecef_pts, origin_ecef, lon, lat):
    """Project ECEF points into a local ENU tangent plane at (lon,lat) so we can
    draw them in metres-from-truth on a flat panel. Returns (east, north) arrays."""
    lam, phi = np.radians(lon), np.radians(lat)
    e_hat = np.array([-np.sin(lam), np.cos(lam), 0.0])
    n_hat = np.array([-np.sin(phi) * np.cos(lam), -np.sin(phi) * np.sin(lam), np.cos(phi)])
    d = ecef_pts - origin_ecef
    return d @ e_hat, d @ n_hat


def _truth_lonlat():
    # the intended corner, in geographic, for the ENU projection origin
    e = ill.NY_UTM17[0] + ill.MOMA_OFFSET[0] + ill.CORNER_OFFSET[0]
    n = ill.NY_UTM17[1] + ill.MOMA_OFFSET[1] + ill.CORNER_OFFSET[1]
    h = ill.NY_UTM17[2] + ill.MOMA_OFFSET[2] + ill.CORNER_OFFSET[2]
    t = Transformer.from_crs(ill.UTM17N, CRS.from_epsg(4979), always_xy=True)
    lon, lat, _ = t.transform(e, n, h)
    gt_ecef = ill._ecef_of_utm17(e, n, h)
    return lon, lat, gt_ecef


# ---------------------------------------------------------------------------
def _localized_pair(broken_ecef, fixed_ecef):
    lon, lat, gt = _truth_lonlat()
    pts = np.vstack([broken_ecef, fixed_ecef, gt])
    e, n = _enu_local(pts, gt, lon, lat)
    # panel positions (ENU, for plotting only) + AUTHORITATIVE 3D ECEF errors
    # (the exact quantities test_illformed_assets.py measures vs pyproj geodesy),
    # so figure labels never drift from the test/prose numbers.
    err_b = float(np.linalg.norm(np.asarray(broken_ecef) - gt))
    err_f = float(np.linalg.norm(np.asarray(fixed_ecef) - gt))
    return (e[0], n[0]), (e[1], n[1]), (e[2], n[2]), err_b, err_f  # broken, fixed, truth, errs


def _scatter_panel(ax, title, target_en, obj_en, err_m, is_broken, note,
                   zoom=None):
    ax.set_title(title, fontsize=10, fontweight="bold",
                 color=BAD_EC if is_broken else OK_EC)
    ax.set_aspect("equal")
    ax.grid(True, color=GRID, lw=0.6)
    ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
    # truth
    ax.scatter([target_en[0]], [target_en[1]], marker="*", s=260,
               color=TRUTH_C, zorder=5, label="intended (geodesy truth)")
    # object
    c = BAD_EC if is_broken else OK_EC
    ax.scatter([obj_en[0]], [obj_en[1]], marker="s", s=90, color=c, zorder=6,
               label="where it lands")
    # error connector
    ax.annotate("", xy=obj_en, xytext=target_en,
                arrowprops=dict(arrowstyle="-", color=c, lw=1.4, ls="--"))
    mid = ((obj_en[0] + target_en[0]) / 2, (obj_en[1] + target_en[1]) / 2)
    if err_m >= 1000:
        etxt = f"{err_m/1000:,.0f} km off"
    elif err_m >= 1.0:
        etxt = f"{err_m:.1f} m off"
    else:
        etxt = f"{err_m*1000:.3f} mm"
    ax.text(mid[0], mid[1], etxt, fontsize=9, fontweight="bold", color=c,
            ha="center", va="bottom",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=c, lw=1))
    ax.set_xlabel("east of intended (m)", fontsize=7.5)
    ax.set_ylabel("north of intended (m)", fontsize=7.5)
    if zoom:
        ax.set_xlim(-zoom, zoom); ax.set_ylim(-zoom, zoom)
    ax.text(0.5, -0.22, note, transform=ax.transAxes, fontsize=7.5,
            ha="center", va="top", family="monospace", color="#333")
    ax.legend(loc="upper right", fontsize=6.5, framealpha=0.9)


# ---------------------------------------------------------------------------
# G1 -- anchor-vs-child ambiguity
def data_g1():
    stage = Usd.Stage.CreateInMemory()
    stage.SetMetadata("upAxis", "Z"); stage.SetMetadata("metersPerUnit", 1.0)
    ill._crs_scope(stage)
    ny = UsdGeom.Xform.Define(stage, "/World/NewYork")
    ill._bind(ny, "/World/CRS/UTM17N", ill.NY_UTM17)
    ill._translate(stage, "/World/NewYork/MoMa", ill.MOMA_OFFSET)
    corner = UsdGeom.Xform.Define(stage, "/World/NewYork/MoMa/Corner")
    ill._bind(corner, "/World/CRS/UTM17N", ill.NY_UTM17)  # its OWN position (== anchor)
    cp = stage.GetPrimAtPath("/World/NewYork/MoMa/Corner")
    wb, _ = rr.resolve_with_injection(cp, ill.ECEF, {}, xform_cache=UsdGeom.XformCache())
    broken = np.array(wb.Transform(Gf.Vec3d(0, 0, 0)))

    stage2 = Usd.Stage.CreateInMemory()
    stage2.SetMetadata("upAxis", "Z"); stage2.SetMetadata("metersPerUnit", 1.0)
    ill._crs_scope(stage2)
    ny2 = UsdGeom.Xform.Define(stage2, "/World/NewYork")
    ill._bind(ny2, "/World/CRS/UTM17N", ill.NY_UTM17)
    ill._translate(stage2, "/World/NewYork/MoMa", ill.MOMA_OFFSET)
    ill._translate(stage2, "/World/NewYork/MoMa/Corner", ill.CORNER_OFFSET)
    cp2 = stage2.GetPrimAtPath("/World/NewYork/MoMa/Corner")
    wf, _ = rr.resolve_with_injection(cp2, ill.ECEF, {}, xform_cache=UsdGeom.XformCache())
    fixed = np.array(wf.Transform(Gf.Vec3d(0, 0, 0)))
    return broken, fixed


def fig_g1(out):
    broken, fixed = data_g1()
    b_en, f_en, t_en, err_b, err_f = _localized_pair(broken, fixed)
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 5.4))
    fig.suptitle("G1  Anchor-vs-child ambiguity", fontsize=13, fontweight="bold")
    _scatter_panel(axL, "BROKEN: Corner owns its own crs:position", t_en, b_en, err_b,
                   True,
                   "Corner has rel crs:binding + crs:position\n"
                   "-> treated as its own anchor, ignores parent",
                   zoom=max(60, err_b * 1.4))
    _scatter_panel(axR, "FIXED: Corner is a plain Cartesian child", t_en, f_en, err_f,
                   False,
                   "double3 xformOp:translate = (50,100,30)\n"
                   "-> composes under MoMa's frame",
                   zoom=max(60, err_b * 1.4))
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    fig.savefig(out, dpi=130); plt.close(fig)
    print(f"[g1] {os.path.basename(out)}  broken {err_b:.1f} m  fixed {err_f*1000:.3f} mm")
    return err_b, err_f


# ---------------------------------------------------------------------------
# G2 -- wrong composition frame
def data_g2():
    eng = ce.get_engine()
    total = (ill.MOMA_OFFSET[0] + ill.CORNER_OFFSET[0],
             ill.MOMA_OFFSET[1] + ill.CORNER_OFFSET[1],
             ill.MOMA_OFFSET[2] + ill.CORNER_OFFSET[2])
    M = eng.local_frame_to_ecef(ill.WKT17, *ill.NY_UTM17)
    broken = np.array(M.Transform(Gf.Vec3d(*total)))
    X, Y, Z = eng.project_grid_offset_to_target(ill.WKT17, ill.ECEF.to_wkt(),
                                                ill.NY_UTM17, total)
    fixed = np.array([X, Y, Z])
    return broken, fixed


def fig_g2(out):
    broken, fixed = data_g2()
    b_en, f_en, t_en, err_b, err_f = _localized_pair(broken, fixed)
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 5.4))
    fig.suptitle("G2  Wrong composition frame (projected anchor)", fontsize=13,
                 fontweight="bold")
    _scatter_panel(axL, "BROKEN: grid offsets lifted through true-ENU", t_en, b_en,
                   err_b, True,
                   "UTM grid axes != true ENU (convergence +\n"
                   "point-scale) -> bent over the ~418 m lever",
                   zoom=max(8, err_b * 1.6))
    _scatter_panel(axR, "FIXED: compose in the grid plane + reproject", t_en, f_en,
                   err_f, False,
                   "grid add + reproject (CRS-implied frame)\n"
                   "-> matches closed-form geodesy",
                   zoom=max(8, err_b * 1.6))
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    fig.savefig(out, dpi=130); plt.close(fig)
    print(f"[g2] {os.path.basename(out)}  broken {err_b:.2f} m  fixed {err_f*1000:.3f} mm")
    return err_b, err_f


# ---------------------------------------------------------------------------
# G3 -- no requires-CRS marker (planet-scale; use a world map schematic)
def data_g3():
    stage = Usd.Stage.CreateInMemory()
    stage.SetMetadata("upAxis", "Z"); stage.SetMetadata("metersPerUnit", 1.0)
    ill._crs_scope(stage)
    ny = UsdGeom.Xform.Define(stage, "/World/NewYork")
    ill._bind(ny, "/World/CRS/UTM17N", ill.NY_UTM17)
    ill._translate(stage, "/World/NewYork/MoMa", ill.MOMA_OFFSET)
    ill._translate(stage, "/World/NewYork/MoMa/Corner", ill.CORNER_OFFSET)
    corner = stage.GetPrimAtPath("/World/NewYork/MoMa/Corner")
    naive = np.array(UsdGeom.XformCache().GetLocalToWorldTransform(corner)
                     .Transform(Gf.Vec3d(0, 0, 0)))
    _, _, gt = _truth_lonlat()
    off = float(np.linalg.norm(naive - gt))
    # geographic positions for the schematic
    geo = Transformer.from_crs(ill.ECEF, CRS.from_epsg(4979), always_xy=True)
    lon_t, lat_t, _ = geo.transform(*gt)
    lon_n, lat_n, _ = geo.transform(*naive)
    return off, (lon_t, lat_t), (lon_n, lat_n)


def fig_g3(out):
    off, truth_ll, naive_ll = data_g3()

    def world_panel(ax, title, show_naive, note, is_broken):
        ax.set_title(title, fontsize=10, fontweight="bold",
                     color=BAD_EC if is_broken else OK_EC)
        ax.set_xlim(-180, 180); ax.set_ylim(-90, 90); ax.set_aspect("equal")
        ax.grid(True, color=GRID, lw=0.5)
        ax.set_xticks([-180, -90, 0, 90, 180]); ax.set_yticks([-90, -45, 0, 45, 90])
        ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
        ax.scatter([truth_ll[0]], [truth_ll[1]], marker="*", s=240, color=TRUTH_C,
                   zorder=5, label="intended (New York)")
        if show_naive:
            ax.scatter([naive_ll[0]], [naive_ll[1]], marker="s", s=80, color=BAD_EC,
                       zorder=6, label="where it lands (near 0,0)")
            ax.annotate("", xy=naive_ll, xytext=truth_ll,
                        arrowprops=dict(arrowstyle="-", color=BAD_EC, lw=1.3, ls="--"))
            ax.text(-60, 20, f"{off/1000:,.0f} km off,\nsilently", fontsize=9,
                    fontweight="bold", color=BAD_EC,
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=BAD_EC))
        else:
            ax.text(0, 0, "consumer sees marker\n-> REFUSES / defers to resolver",
                    fontsize=8.5, fontweight="bold", color=OK_EC, ha="center",
                    bbox=dict(boxstyle="round,pad=0.3", fc="#eef6ff", ec=OK_EC))
        ax.set_xlabel("lon", fontsize=7.5); ax.set_ylabel("lat", fontsize=7.5)
        ax.text(0.5, -0.2, note, transform=ax.transAxes, fontsize=7.5, ha="center",
                va="top", family="monospace", color="#333")
        ax.legend(loc="lower left", fontsize=6.5, framealpha=0.9)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 5.0))
    fig.suptitle("G3  No requires-CRS marker -> silent misplacement", fontsize=13,
                 fontweight="bold")
    world_panel(axL, "BROKEN: unmarked scene, CRS-unaware consumer", True,
                "no marker; XformCache reads bare local offset\n"
                "unknown crs:* ignored -> 'wrong place' looks 'loaded'", True)
    world_panel(axR, "FIXED: customLayerData['crsResolutionRequired']", False,
                "conformant consumer detects marker and fails LOUD\n"
                "(with a resolver the same scene lands to 0 mm)", False)
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    fig.savefig(out, dpi=130); plt.close(fig)
    print(f"[g3] {os.path.basename(out)}  broken {off/1000:,.0f} km  fixed refuse")
    return off


def fig_gallery(out):
    """Stitch the three PNGs vertically for a single slide."""
    imgs = [plt.imread(os.path.join(DOCS, f"illformed_g{i}.png")) for i in (1, 2, 3)]
    fig, axes = plt.subplots(3, 1, figsize=(12, 15))
    for ax, im in zip(axes, imgs):
        ax.imshow(im); ax.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=110); plt.close(fig)
    print(f"[gallery] {os.path.basename(out)}")


def main():
    os.makedirs(DOCS, exist_ok=True)
    fig_g1(os.path.join(DOCS, "illformed_g1.png"))
    fig_g2(os.path.join(DOCS, "illformed_g2.png"))
    fig_g3(os.path.join(DOCS, "illformed_g3.png"))
    fig_gallery(os.path.join(DOCS, "illformed_gallery.png"))


if __name__ == "__main__":
    main()
