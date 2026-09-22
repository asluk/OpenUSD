"""Generate measured scientific figures for the README and derived slides."""
import ast
import shutil
from matplotlib.transforms import Affine2D
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
    demos=run/'demonstrations'
    for name,expected in report['demonstration_files'].items():
        if sha(demos/name)!=expected:
            raise ValueError('Demonstration changed since execution: '+name)
    railway=json.loads((demos/'railway.json').read_text(encoding='utf-8'))
    all_points=np.vstack([c['points'] for c in railway['curves']])
    origin=np.floor(all_points[:,:2].min(axis=0)/1000)*1000
    fig,ax=plt.subplots(figsize=(8.8,5.4),layout='constrained')
    for tile in railway['tiles']:
        points=np.array(tile['points'])[:,:2]-origin
        number=tile['path'].split('MapGeo')[1].split('/')[0]
        bitmap=plt.imread(dataset_root/'railway'/('quadnode-'+number+'.png'))
        x,y=points[3]-points[0],points[1]-points[0]
        transform=Affine2D.from_values(x[0],x[1],y[0],y[1],*points[0])
        ax.imshow(bitmap,extent=(0,1,0,1),origin='upper',transform=transform+ax.transData,zorder=0,alpha=.9)
    for curve in railway['curves']:
        points=np.array(curve['points'])[:,:2]-origin
        ax.plot(points[:,0],points[:,1],color='#DC5020',lw=1.1)
    extent=np.vstack([np.array(t['points'])[:,:2]-origin for t in railway['tiles']])
    lo,hi=extent.min(axis=0),extent.max(axis=0)
    ax.set(xlim=(lo[0]-80,hi[0]+80),ylim=(lo[1]-80,hi[1]+80),aspect='equal',
           xlabel=f'UTM easting minus {origin[0]:,.0f} (m)',ylabel=f'UTM northing minus {origin[1]:,.0f} (m)')
    residual=max(railway['provider_curve_residuals_m'])*100
    tangent=max(railway['cartesian_tangent_residuals_m'])*1e6
    ax.set_title(f'Offset-basis comparison: {residual:.2f} cm versus {tangent:.1f} µm maximum mismatch',fontsize=12)
    ax.text(.99,.015,'© OpenStreetMap contributors · openstreetmap.org/copyright',transform=ax.transAxes,
            ha='right',fontsize=8,bbox={'facecolor':'white','alpha':.9,'edgecolor':'none'})
    fig.savefig(output/'railway.png',dpi=180)
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

    field=json.loads((demos/'field.json').read_text(encoding='utf-8'))
    points=np.array(field['ecef'])/1000
    fig=plt.figure(figsize=(8.8,5.4),layout='constrained')
    ax=fig.add_subplot(111,projection='3d')
    scatter=ax.scatter(*points.T,c=field['values'],s=13,cmap='viridis',depthshade=True)
    ax.set(xlabel='X (km)',ylabel='Y (km)',zlabel='Z (km)',title='Resolved ECEF sample positions')
    ax.set_xticks([-6000,0,6000])
    ax.set_yticks([-6000,0,6000])
    ax.set_zticks([-6000,0,6000])
    ax.set_box_aspect((1,1,1))
    ax.view_init(elev=22,azim=-45)
    fig.colorbar(scatter,ax=ax,label='Raw value; units unverified',shrink=.7,pad=.13)
    fig.savefig(output/'field.png',dpi=180)
    plt.close(fig)
    shutil.copyfile(demos/'storm-site.png',output/'site.png')
    case=next(t for t in report['tests'] if t['name']=='test_complete_W06_extent_sweep_and_precision')
    pairs=np.array(ast.literal_eval(case['properties']['footprint_vs_vertex_displacement_m']))
    fig,ax=plt.subplots(figsize=(8.8,5.4),layout='constrained')
    ax.loglog(pairs[:,0],np.maximum(pairs[:,1],1e-10),'o-',color='#256C89',lw=3,ms=9)
    ax.axhline(.01,color='#CA6C30',ls='--',label='Illustrative 1 cm budget')
    ax.set(xlabel='Cube side length (m)',ylabel='Maximum vertex displacement (m)')
    ax.grid(True,which='major',alpha=.2)
    ax.annotate(f'{pairs[-1,1]:.2f} m at 20 km',(pairs[-1,0],pairs[-1,1]),xytext=(-190,-10),textcoords='offset points')
    ax.legend(loc='upper left')
    fig.savefig(output/'extent.png',dpi=180)
    plt.close(fig)
    write_json(output / "manifest.json", {"evidence_key": evidence_key(report),
               "dataset_catalog_sha256": report["dataset_inventory"]["catalog_sha256"],
               "files": {name: sha(output / name) for name in ("railway.png", "interpolation.png", "field.png", "site.png", "extent.png")}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "docs" / "figures")
    args = parser.parse_args()
    build(args.run, args.dataset_root, args.output)
