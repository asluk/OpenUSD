"""Explain the recorded tower placement with actual geometry and bake comparisons."""
import hashlib
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pxr import Usd, UsdGeom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src_py'))
from reader import Engine, ModelMap, apply_matrix

authored = ROOT / 'inputs/authored'
figure_dir = ROOT / 'evidence/figures'
figure_dir.mkdir(exist_ok=True)
source_path = authored / 'tower.usda'
source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
source = Usd.Stage.Open(str(source_path))
anchor = source.GetPrimAtPath('/World/Tower')
mapping = ModelMap(anchor, Usd.TimeCode.Default(), Engine())
working = mapping.working
assert not working.is_geographic and working.axis_info[0].unit_conversion_factor == 1
origin_before = mapping.forward([[0, 0, 0]], working, reset=True)[0]
origin_after = mapping.forward([[0, 0, 0]], working)[0]

def ordinary_meshes(path):
    stage = Usd.Stage.Open(str(path))
    cache = UsdGeom.XformCache()
    report = {}
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), dtype=float)
            report[str(prim.GetPath())] = apply_matrix(points, cache.GetLocalToWorldTransform(prim))
    return report

python_bake = ordinary_meshes(authored / 'tower-python-bake.usda')
native_bake = ordinary_meshes(authored / 'tower-native-bake.usda')
assert python_bake.keys() == native_bake.keys()
python_world = np.concatenate([python_bake[key] for key in sorted(python_bake)])
native_world = np.concatenate([native_bake[key] for key in sorted(native_bake)])
differences = np.linalg.norm(python_world - native_world, axis=1)
assert len(differences) == 163416
recorded = json.loads((ROOT / 'evidence/full-data.json').read_text('utf-8'))
assert abs(differences.max() - recorded['all_meshes_reader_agreement_m']) < 1e-10

cache = UsdGeom.XformCache()
local_parts, before_parts = [], []
mesh_records = sorted(recorded['native_bake']['meshes'], key=lambda item: item['export'])
assert [item['export'] for item in mesh_records] == sorted(native_bake)
for item in mesh_records:
    prim = source.GetPrimAtPath(item['source'])
    points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), dtype=float)
    relative, reset = cache.ComputeRelativeTransform(prim, anchor)
    assert not reset and len(points) == item['vertices']
    local_parts.append(apply_matrix(points, relative))
    # Skip only the anchor's ordinary adjustment to expose the preceding phase.
    before_parts.append(mapping.forward(points, working, relative, reset=True))
local = np.concatenate(local_parts)
before = np.concatenate(before_parts) - origin_before
after = mapping.e.convert(native_world, mapping.ecef, working) - origin_before
adjusted = mapping.unchart(apply_matrix(mapping.chart(before + origin_before), mapping.A)) - origin_before
adjustment_error = float(np.linalg.norm(adjusted - after, axis=1).max())
assert adjustment_error < .001, 'Before/after geometry does not match the authored adjustment'
offset = origin_after - origin_before
translation = np.asarray(anchor.GetAttribute('xformOp:translate:project').Get())
assert np.allclose(offset, translation, atol=1e-7)
assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash

ink, muted, blue, teal = '#213f4c', '#536b75', '#5b7fa5', '#007b83'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 15,
                     'text.color': ink, 'axes.labelcolor': ink,
                     'xtick.color': muted, 'ytick.color': muted,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': 'white', 'savefig.facecolor': 'white'})
fig = plt.figure(figsize=(16, 6.7))
fig.text(.035, .94, 'From authored location to a checked placement', size=24, weight='bold')
fig.text(.035, .865, '1  Author the placement', size=18, weight='bold')
fig.text(.325, .865, '2  See the adjustment in metres', size=18, weight='bold')
fig.text(.735, .865, '3  Compare the two results', size=18, weight='bold')

position = np.asarray(anchor.GetAttribute('crs:position').Get())
orientation = np.asarray(anchor.GetAttribute('crs:orientation').Get())
scale = np.asarray(anchor.GetAttribute('xformOp:scale:project').Get())
rotate = float(anchor.GetAttribute('xformOp:rotateZ:project').Get())
fig.text(.035, .815, f'{mapping.source.name} geographic 3D', size=14, color=muted)
fig.text(.035, .765, f'{position[0]:.4f}° E   {position[1]:.4f}° N', size=17)
fig.text(.035, .715, f'Ellipsoidal height {position[2]:g} m', size=16)
fig.text(.035, .665, f'Heading {orientation[0]:g}° from true north', size=16)
asset_ax = fig.add_axes([.055, .185, .19, .445])
asset_ax.scatter(local[:, 0], local[:, 2], s=.03, color=ink, alpha=.3, rasterized=True)
asset_ax.set_aspect('equal')
asset_ax.set_axis_off()
height = np.ptp(local[:, 2])
asset_ax.text(.5, -.04, f'{height:.0f} m model after asset conformance',
              transform=asset_ax.transAxes, ha='center', size=13, color=muted)

ax = fig.add_axes([.34, .29, .345, .44])
ax.set_facecolor('#f3f7f7')
ax.scatter(before[:, 0], before[:, 1], s=.045, color=blue, alpha=.2, rasterized=True)
ax.scatter(after[:, 0], after[:, 1], s=.045, color=teal, alpha=.2, rasterized=True)
ax.scatter([0], [0], marker='+', s=130, color=blue, linewidths=2)
ax.scatter([offset[0]], [offset[1]], marker='+', s=130, color=teal, linewidths=2)
ax.annotate('', xy=offset[:2], xytext=(0, 0),
            arrowprops={'arrowstyle': '->', 'lw': 2.3, 'color': ink})
ax.text(-72, 82, 'Before adjustment', size=14, color=blue, weight='bold')
ax.text(55, -137, 'After adjustment', size=14, color=teal, weight='bold')
ax.text(25, 27, f'+{offset[0]:.0f} m east\n{offset[1]:.0f} m north', size=14,
        bbox={'boxstyle': 'round,pad=.35', 'facecolor': 'white', 'edgecolor': '#d5dfe1'})
ax.set(xlim=(-100, 220), ylim=(-155, 110),
       xlabel='Project-grid easting from authored origin (m)',
       ylabel='Northing (m)')
ax.set_aspect('equal')
ax.set_xticks([-100, 0, 100, 200])
ax.set_yticks([-100, 0, 100])
ax.grid(color='#d6e2e4', zorder=0)
fig.text(.34, .765, 'Plan view of the actual tower vertices', size=14, color=muted)
fig.text(.345, .12, f'Ordinary USD: scale {scale[0]:g}×, rotate {rotate:g}°, then translate',
         size=14, color=ink)

maximum_mm = differences.max() * 1000
fig.text(.735, .775, f'{len(differences):,} vertices checked', size=17, weight='bold')
bound_mm = np.ceil(maximum_mm * 1000) / 1000
fig.text(.735, .685, f'≤ {bound_mm:.3f} mm', size=29, weight='bold', color=teal)
fig.text(.735, .63, 'largest Python / C++ difference', size=14, color=muted)
outputs = fig.add_axes([.735, .29, .24, .255])
outputs.set_axis_off()
for x, label in ((.23, 'Python'), (.77, 'C++')):
    outputs.text(x, .82, label, ha='center', va='center', size=17, color=ink,
                 bbox={'boxstyle':'round,pad=.55', 'facecolor':'#edf3f4', 'edgecolor':'#b7c9ce'})
    outputs.annotate('', xy=(.5, .28), xytext=(x, .59),
                     arrowprops={'arrowstyle':'->', 'lw':2, 'color':muted})
outputs.text(.5, .03, 'Compare every vertex', ha='center', size=15, color=ink)
fig.text(.735, .14, 'Ordinary USD outputs reach\nHydra and Omniverse consumers.', size=14)
fig.text(.035, .055, 'Illustrative placement, not surveyed Paris context. Both implementations use PROJ; agreement is not independent geodetic validation.',
         size=12.5, color=muted)
fig.text(.035, .02, 'Tower geometry: SDC PERFORMANCE, (FREE) La tour Eiffel, CC BY 4.0. Size and placement modified.',
         size=12.5, color=muted)
target = figure_dir / 'tower-placement.png'
fig.savefig(target, dpi=150)
plt.close(fig)
facts = {'source': 'inputs/authored/tower.usda', 'source_sha256': source_hash,
         'source_unchanged': True, 'authored_position': position.tolist(),
         'authored_orientation': orientation.tolist(),
         'ordinary_scale': scale.tolist(), 'ordinary_rotation_Z_degrees': rotate,
         'ordinary_translation': translation.tolist(), 'observed_origin_shift_m': offset.tolist(),
         'working_CRS': working.name, 'original_vertices': len(differences),
         'maximum_reader_bake_difference_m': float(differences.max()),
         'maximum_visual_adjustment_vs_native_bake_difference_m': adjustment_error,
         'display': 'All original vertices; local side view and before/after plan view. Differences measured in the common geocentric chart.',
         'scope': 'Interpretation of this illustrative placement, not an independent geodetic or surveyed-site check.'}
(ROOT / 'evidence/tower-placement.json').write_text(json.dumps(facts, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'figure': str(target), 'origin_shift_m': offset.tolist(), 'vertices': len(differences),
                  'maximum_difference_mm': maximum_mm, 'model_height_m': float(height)}))
