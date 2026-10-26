"""Native-format associations derived from the external measurement contract.

Adapters preserve sample identity; no visualization is required for access.
"""

import json, re
from pathlib import Path
import numpy as np
from pxr import UsdGeom, Sdf, Usd
from pyproj import CRS
from crs import Engine, geocentric
from common import Failure, finite, require
from math_util import apply_matrix, stage_basis
from placement import definition, direct, uniform


def equivalent(a, b):
    # Explicit criterion: PROJ semantic equivalence after native format axis mapping.
    return a.equals(b, ignore_axis_order=True)


def cf(path, field, domain, wkt):
    import netCDF4

    with netCDF4.Dataset(path) as ds:
        require(
            field in ds.variables and domain in ds.variables,
            "missing CF field or mapping",
        )
        v = ds[field]
        gm = ds[domain]
        text = getattr(v, "grid_mapping", "")
        if ":" in text:
            pairs = re.findall(r"(\w+)\s*:\s*([^:]+?)(?=\s+\w+\s*:|$)", text)
            groups = {k: x.split() for k, x in pairs}
            require(domain in groups, "selected CF domain not associated with field")
            names = groups[domain]
        else:
            require(text == domain, "CF mapping association mismatch")
            names = [d for d in v.dimensions if d in ds.variables] + getattr(
                v, "coordinates", ""
            ).split()
        names = list(dict.fromkeys(names))
        coords = {}
        units = {}
        times = {}
        shape = v.shape
        dims = v.dimensions
        for name in names:
            require(name in ds.variables, "missing CF coordinate " + name)
            c = ds[name]
            role = getattr(c, "standard_name", "")
            unit = getattr(c, "units", "")
            if role == "time" or " since " in unit:
                times[name] = {
                    "values": np.ma.filled(c[:], np.nan).tolist(),
                    "units": unit,
                    "dimensions": c.dimensions,
                }
                continue
            if role == "height":
                raise Failure(
                    "surface-relative CF height is not an absolute ellipsoidal/geoid height"
                )
            if role == "height_above_reference_ellipsoid":
                require(
                    not any(x.is_vertical for x in wkt.sub_crs_list),
                    "CF ellipsoidal height conflicts with declared vertical CRS",
                )
            if role == "altitude":
                require(
                    any(x.is_vertical for x in wkt.sub_crs_list),
                    "CF geoid altitude conflicts with ellipsoidal height",
                )
            role = {
                "longitude": "X",
                "latitude": "Y",
                "projection_x_coordinate": "X",
                "projection_y_coordinate": "Y",
                "height_above_reference_ellipsoid": "Z",
                "altitude": "Z",
            }.get(role)
            if not role:
                continue
            require(role not in coords, "ambiguous CF coordinate role")
            require(
                all(d in dims for d in c.dimensions),
                "coordinate dimensions not in sample domain",
            )
            order = sorted(
                range(len(c.dimensions)), key=lambda i: dims.index(c.dimensions[i])
            )
            a = np.ma.filled(c[:], np.nan)
            a = np.transpose(a, order) if order else a
            resh = [1] * len(dims)
            for i in order:
                resh[dims.index(c.dimensions[i])] = len(ds.dimensions[c.dimensions[i]])
            coords[role] = np.broadcast_to(a.reshape(resh), shape).reshape(-1)
            units[role] = unit
        require("X" in coords and "Y" in coords, "missing CF horizontal coordinates")
        declared = CRS.from_wkt(getattr(gm, "crs_wkt", getattr(gm, "spatial_ref", "")))
        require(equivalent(declared, wkt), "conflicting CF and USD CRS")
        require(
            hasattr(gm, "grid_mapping_name"),
            "incomplete CF grid mapping; WKT supplements native mapping metadata",
        )
        expected_cf = declared.to_cf()
        require(
            expected_cf.get("grid_mapping_name") == gm.grid_mapping_name,
            "CF mapping name conflicts with WKT",
        )
        for key in gm.ncattrs():
            if (
                key in ("crs_wkt", "spatial_ref", "grid_mapping_name")
                or key not in expected_cf
            ):
                continue
            actual = getattr(gm, key)
            expected = expected_cf[key]
            require(
                (
                    np.allclose(actual, expected, rtol=1e-12, atol=1e-12)
                    if isinstance(expected, (float, int, list, tuple, np.ndarray))
                    else actual == expected
                ),
                "CF parameter conflicts with WKT: " + key,
            )
        require(
            not wkt.is_geographic
            or (
                units["X"] in ("degrees_east", "degree_east")
                and units["Y"] in ("degrees_north", "degree_north")
            ),
            "CF angular units conflict",
        )
        length_units = {
            "m": 1,
            "metre": 1,
            "meter": 1,
            "ft": 0.3048,
            "foot": 0.3048,
            "US_survey_foot": 1200 / 3937,
        }
        for key, i in [("X", 0), ("Y", 1), ("Z", 2)]:
            if key not in coords or (wkt.is_geographic and key != "Z"):
                continue
            require(units[key] in length_units, "unsupported CF length unit")
            target = wkt.axis_info[i].unit_conversion_factor
            coords[key] = coords[key] * length_units[units[key]] / target
        if "Z" in coords:
            require(
                len(wkt.axis_info) == 3, "CF height conflicts with WKT dimensionality"
            )
        else:
            require(
                len(wkt.axis_info) == 2, "missing CF height for three-component CRS"
            )
        values = np.ma.array(v[:])
        mask = np.ma.getmaskarray(values).reshape(-1)
        points = np.array([coords[k] for k in ("X", "Y", "Z") if k in coords]).T
        finite(points)
        return {
            "coordinates": points,
            "values": values.filled(np.nan).reshape(-1),
            "mask": mask,
            "indices": list(np.ndindex(shape)),
            "dimensions": list(dims),
            "times": times,
            "native": "CF",
            "coordinateUnits": units,
        }


def geojson(path, field, domain, wkt):
    require(domain == "geometry", "unknown GeoJSON coordinate domain")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "crs" in data:
        legacy = data["crs"]
        name = (legacy.get("properties") or {}).get("name", "")
        try:
            horizontal = CRS.from_user_input(name)
        except Exception as e:
            raise Failure("unreadable legacy GeoJSON CRS") from e
        require(
            horizontal.equals(CRS.from_epsg(4326), ignore_axis_order=True),
            "legacy GeoJSON with another CRS is unsupported",
        )
        # The explicitly selected proposal profile supplies RFC 7946 semantics.
        # A compatible legacy horizontal label does not change those semantics.
    rows = []
    values = []
    indices = []

    def visit(obj, feature, branch, measurement):
        if obj["type"] == "GeometryCollection":
            for i, g in enumerate(obj["geometries"]):
                visit(g, feature, branch + [i], measurement)
            return

        def walk(x, idx):
            if x and isinstance(x[0], (float, int)):
                require(len(x) in (2, 3), "invalid GeoJSON position")
                rows.append(x)
                values.append(measurement)
                indices.append((feature, *branch, *idx))
            else:
                for i, y in enumerate(x):
                    walk(y, idx + [i])

        walk(obj["coordinates"], [])

    features = data.get("features", [data])
    for i, f in enumerate(features):
        if f["type"] == "Feature":
            props = f.get("properties") or {}
            require(not field or field in props, "missing feature property")
            if f["geometry"] is not None:
                visit(f["geometry"], i, [], props[field] if field else None)
        else:
            require(not field, "property requires feature")
            visit(f, i, [], None)
    require(
        bool(rows) and len({len(r) for r in rows}) == 1,
        "empty or mixed-dimensional GeoJSON domain",
    )
    dims = len(rows[0])
    native = CRS.from_epsg(4979 if dims == 3 else 4326)
    require(
        equivalent(native, wkt),
        "GeoJSON RFC coordinate/height semantics conflict with USD WKT",
    )
    return {
        "coordinates": finite(rows),
        "values": values,
        "indices": indices,
        "mask": [False] * len(rows),
        "times": {},
        "native": "GeoJSON",
    }


def geotiff(path, field, domain, wkt):
    # Pillow is the neutral TIFF container decoder; GeoTIFF tags define locations.
    from PIL import Image

    require(
        re.fullmatch(r"[1-9]\d*", field) and re.fullmatch(r"0|[1-9]\d*", domain),
        "invalid GeoTIFF band/IFD selector",
    )
    image = Image.open(path)
    image.seek(int(domain))
    tags = image.tag_v2
    keys = tags.get(34735)
    require(keys is not None, "missing GeoTIFF key directory")
    d = {keys[i]: keys[i + 3] for i in range(4, len(keys), 4) if keys[i + 1] == 0}
    code = d.get(3072, d.get(2048))
    require(
        code is not None and code != 32767, "custom GeoTIFF CRS decoding unsupported"
    )
    require(equivalent(CRS.from_epsg(code), wkt), "GeoTIFF and USD CRS conflict")
    a = np.asarray(image)
    a = a[:, :, int(field) - 1] if a.ndim == 3 else a if field == "1" else None
    require(a is not None, "band unavailable")
    h, width = a.shape
    offset = 0.5 if d.get(1025, 1) == 1 else 0.0
    x, y = np.meshgrid(np.arange(width) + offset, np.arange(h) + offset)
    if 34264 in tags:
        M = np.asarray(tags[34264]).reshape(4, 4)
        p = np.c_[x.ravel(), y.ravel(), np.zeros(h * width), np.ones(h * width)] @ M.T
        coords = p[:, :2]
    else:
        scale = tags.get(33550)
        tie = tags.get(33922)
        require(scale and tie, "missing raster-to-model mapping")
        coords = np.c_[
            tie[3] + (x.ravel() - tie[0]) * scale[0],
            tie[4] - (y.ravel() - tie[1]) * scale[1],
        ]
    require(len(wkt.axis_info) == 2, "raster has no associated height")
    nodata = tags.get(42113)
    mask = (
        np.zeros(h * width, dtype=bool)
        if nodata is None
        else a.ravel() == float(str(nodata).rstrip("\x00"))
    )
    return {
        "coordinates": finite(coords),
        "values": a.ravel(),
        "indices": list(np.ndindex(a.shape)),
        "mask": mask,
        "times": {},
        "native": "GeoTIFF",
    }


def read_domain(prim):
    require(
        prim.GetTypeName() == "GeospatialDataSource" and direct(prim),
        "not a directly bound data carrier",
    )
    for n in ("crs:position", "crs:orientation"):
        require(
            not prim.GetAttribute(n)
            or not prim.GetAttribute(n).HasAuthoredValueOpinion(),
            "placement on measurement carrier",
        )
    c = definition(prim, False)
    asset = uniform(prim, "data:asset", Sdf.ValueTypeNames.Asset)
    path = asset.resolvedPath
    require(bool(path), "unresolved dataset asset")
    fmt = str(uniform(prim, "data:format", Sdf.ValueTypeNames.Token))
    field = uniform(prim, "data:field", Sdf.ValueTypeNames.String)
    domain = uniform(prim, "data:coordinateDomain", Sdf.ValueTypeNames.String)
    require(fmt in ("CF", "GeoJSON", "GeoTIFF"), "unsupported association profile")
    return {"CF": cf, "GeoJSON": geojson, "GeoTIFF": geotiff}[fmt](
        path, field, domain, c
    )


def resolve_domain(prim, output, time=None):
    data = read_domain(prim)
    source = definition(prim, False)
    e = Engine()
    p = data["coordinates"]
    parent = prim.GetParent()
    while parent and not parent.IsPseudoRoot() and not direct(parent):
        parent = parent.GetParent()
    W = definition(parent, False) if parent and direct(parent) else source
    A = np.asarray(
        UsdGeom.Xformable(prim).GetLocalTransformation(
            Usd.TimeCode.Default() if time is None else time
        )
    )
    if not np.array_equal(A, np.eye(4)):
        require(
            not W.is_geographic,
            "geographic domain adjustment requires enclosing Cartesian working CRS",
        )
        require(
            p.shape[1] == 3
            or (
                np.allclose(A[[0, 1, 3], 2], [0, 0, 0])
                and np.allclose(A[2, [0, 1, 3]], [0, 0, 0])
            ),
            "non-planar adjustment on 2D domain",
        )
        w = e.convert(p, source, W)
        units = np.array([a.unit_conversion_factor for a in W.axis_info])
        B = stage_basis(prim.GetStage())
        xyz = np.zeros((len(w), 3))
        xyz[:, : w.shape[1]] = w * units
        adjusted = apply_matrix(xyz @ np.linalg.inv(B).T, A) @ B.T
        p = e.convert(adjusted[:, : w.shape[1]] / units, W, output)
    else:
        require(
            data["coordinates"].shape[1] == 3 or len(output.axis_info) == 2,
            "3D request needs height",
        )
        p = e.convert(p, source, output)
    return dict(data, resolved=p, operations=e.operations)
