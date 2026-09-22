"""Scene coordinate operations and independent numerical implementation.

Policies here are explicitly experimental, never silent scene defaults. PROJ
parses full definitions in both adapters; only ProjOperations executes PROJ
transformations. KarneyOperations uses PyGeodesy for all coordinate arithmetic.
"""
import math
from functools import lru_cache
from pyproj import CRS, network
from pyproj.crs import GeographicCRS
from pyproj.transformer import TransformerGroup

from geobuild.engine import Conversion, TransformError


@lru_cache(maxsize=256)
def parse(wkt):
    try:
        value = CRS.from_wkt(wkt)
    except Exception as exc:
        raise TransformError("Unreadable complete WKT definition") from exc
    if len(value.axis_info) != 3:
        raise TransformError("Three coordinate axes and an explicit vertical reference are required by this experiment")
    return value


def batch(points):
    try:
        values = tuple(tuple(float(v) for v in p) for p in points)
    except (ValueError, TypeError, OverflowError) as exc:
        raise TransformError("Coordinates must be finite triples") from exc
    if not values or any(len(p) != 3 or not all(map(math.isfinite, p)) for p in values):
        raise TransformError("Coordinates must be a nonempty batch of finite triples")
    return values


def dynamic(crs):
    def walk(value):
        if isinstance(value, dict):
            return str(value.get("type", "")).startswith("Dynamic") or any(walk(v) for v in value.values())
        return isinstance(value, list) and any(walk(v) for v in value)
    return walk(crs.to_json_dict())


def input_domain(crs, values):
    angular = crs.axis_info[0].unit_conversion_factor * 180 / math.pi if crs.is_geographic else 1
    if crs.is_geographic and any(not (-180 <= p[0]*angular <= 180 and -90 <= p[1]*angular <= 90) for p in values):
        raise TransformError("Geographic coordinate outside its domain; no partial placement")
    if crs.is_geocentric and any(p == (0, 0, 0) for p in values):
        raise TransformError("Geocentric origin has no unique geographic frame")


class ProjOperations:
    """Best locally available operation, no ballpark or downloaded resources."""
    name = "PROJ"

    def __init__(self, require_unique=False):
        self._cache = {}
        self.require_unique = require_unique

    def _operation(self, source, target):
        key = source.srs, target.srs
        if key not in self._cache:
            enabled = network.is_network_enabled()
            try:
                network.set_network_enabled(False)
                group = TransformerGroup(source, target, always_xy=True, allow_ballpark=False)
            finally:
                network.set_network_enabled(enabled)
            if not group.best_available or not group.transformers:
                grids = sorted({g.short_name for op in group.unavailable_operations for g in op.grids if not g.available})
                raise TransformError("Best operation unavailable; missing resources: " + ", ".join(grids))
            if self.require_unique and len(group.transformers) != 1:
                raise TransformError("Operation choice is ambiguous under require-unique policy")
            self._cache[key] = group.transformers[0], len(group.transformers)
        return self._cache[key]

    def convert(self, source_wkt, target_wkt, points, epoch=None):
        source, target = parse(source_wkt), parse(target_wkt)
        values = batch(points)
        input_domain(source, values)
        if (dynamic(source) or dynamic(target)) and epoch is None:
            raise TransformError("Dynamic CRS requires a coordinate epoch; animation time is not that epoch")
        if epoch is not None and not math.isfinite(float(epoch)):
            raise TransformError("Coordinate epoch must be finite")
        if source == target:
            return Conversion(values, {"engine": self.name, "operation": "identity in the complete source CRS",
                "accuracy_metres": 0.0, "coordinate_epoch": epoch, "network": False})
        operation, choices = self._operation(source, target)
        try:
            columns = list(zip(*values))
            if epoch is not None:
                columns.append([float(epoch)] * len(values))
            transformed = operation.transform(*columns, errcheck=True)
            output = tuple(tuple(p) for p in zip(*transformed[:3]))
        except Exception as exc:
            raise TransformError("Operation failed; entire result rejected: " + str(exc)) from exc
        if len(output) != len(values) or any(not all(map(math.isfinite, p)) for p in output):
            raise TransformError("Partial or non-finite result rejected")
        # CRS/operation area checks use the input's own datum; no WGS84 assumption.
        area = operation.area_of_use
        if area and source.geodetic_crs:
            try:
                horizontal = source.sub_crs_list[0] if source.is_compound else source
                geodetic = GeographicCRS(datum=horizontal.geodetic_crs.datum)
                columns = list(zip(*values))
                if not horizontal.is_geocentric:
                    columns = columns[:2]
                    horizontal = horizontal.to_2d()
                geographic = tuple(zip(*self._operation(horizontal, geodetic)[0].transform(*columns, errcheck=True)))
                for lon, lat, *_ in geographic:
                    longitude_ok = area.west <= lon <= area.east if area.west <= area.east else lon >= area.west or lon <= area.east
                    if not longitude_ok or not area.south <= lat <= area.north:
                        raise TransformError("Point outside the selected operation's area of use")
            except TransformError:
                raise
            except Exception as exc:
                raise TransformError("Operation domain could not be established") from exc
        import pyproj
        return Conversion(output, {"engine": self.name, "version": pyproj.proj_version_str,
            "operation": operation.description, "pipeline": operation.definition,
            "accuracy_metres": None if operation.accuracy < 0 else operation.accuracy,
            "coordinate_epoch": epoch, "network": False, "candidate_operations": choices,
            "selection_policy": "require_unique" if self.require_unique else "best_available_no_ballpark"})


class KarneyOperations:
    """Independent static same-datum geographic, ECEF and transverse-Mercator math.

    Unsupported cross-datum/grid operations fail explicitly. No PROJ transformer
    is called; WKT parameter parsing is shared, coordinate arithmetic is not.
    """
    name = "PyGeodesy-Karney"

    @staticmethod
    @lru_cache(maxsize=128)
    def _math(wkt):
        from pygeodesy import EcefKarney, ExactTransverseMercator, Ellipsoid
        crs = parse(wkt)
        e = crs.ellipsoid
        ellipsoid = Ellipsoid(e.semi_major_metre, f=1 / e.inverse_flattening)
        ecef = EcefKarney(ellipsoid)
        projection = None
        offsets = (0.0, 0.0)
        if crs.is_projected:
            operation = crs.coordinate_operation
            if not operation or operation.method_name != "Transverse Mercator":
                raise TransformError("Independent engine has no implementation of this projection")
            params = {p.name: p.value * p.unit_conversion_factor *
                      (180 / math.pi if 'origin' in p.name and 'Scale' not in p.name else 1)
                      for p in operation.params}
            projection = ExactTransverseMercator(datum=ellipsoid,
                lon0=params['Longitude of natural origin'], k0=params['Scale factor at natural origin'], raiser=True)
            lat0 = params['Latitude of natural origin']
            y0 = projection.forward(lat0, params['Longitude of natural origin']).northing
            offsets = params['False easting'], params['False northing'] - y0
        elif not (crs.is_geographic or crs.is_geocentric):
            raise TransformError("Independent engine supports geographic, geocentric and transverse Mercator")
        return crs, ecef, projection, offsets

    def convert(self, source_wkt, target_wkt, points, epoch=None):
        source, secef, sp, so = self._math(source_wkt)
        target, tecef, tp, to = self._math(target_wkt)
        values = batch(points)
        input_domain(source, values)
        if dynamic(source) or dynamic(target) or source.datum != target.datum:
            raise TransformError("Independent engine requires one static datum; no invented datum or epoch transform")
        output = []
        try:
            for x, y, z in values:
                if source.is_geocentric:
                    point = secef.reverse(*(v * a.unit_conversion_factor for v, a in zip((x,y,z), source.axis_info)))
                    lon, lat, height = point.lon, point.lat, point.height
                elif sp:
                    factor = source.axis_info[0].unit_conversion_factor
                    point = sp.reverse(x * factor - so[0], y * factor - so[1])
                    lon, lat, height = point.lon, point.lat, z * source.axis_info[2].unit_conversion_factor
                else:
                    angular = source.axis_info[0].unit_conversion_factor * 180 / math.pi
                    lon, lat, height = x * angular, y * angular, z * source.axis_info[2].unit_conversion_factor
                if target.is_geocentric:
                    point = tecef.forward(lat, lon, height)
                    result = tuple(v / a.unit_conversion_factor for v, a in zip((point.x,point.y,point.z), target.axis_info))
                elif tp:
                    point = tp.forward(lat, lon)
                    factor = target.axis_info[0].unit_conversion_factor
                    result = ((point.easting + to[0]) / factor, (point.northing + to[1]) / factor,
                              height / target.axis_info[2].unit_conversion_factor)
                else:
                    angular = target.axis_info[0].unit_conversion_factor * 180 / math.pi
                    result = lon / angular, lat / angular, height / target.axis_info[2].unit_conversion_factor
                if not all(map(math.isfinite, result)):
                    raise TransformError("Independent operation returned non-finite coordinates")
                output.append(result)
        except TransformError:
            raise
        except Exception as exc:
            raise TransformError("Independent operation failed; no partial placement") from exc
        import pygeodesy
        return Conversion(tuple(output), {"engine": self.name, "version": pygeodesy.__version__,
            "operation": "Karney geocentric / exact transverse Mercator; static same-datum",
            "accuracy_metres": None, "coordinate_epoch": epoch, "coordinate_math_uses_proj": False})
