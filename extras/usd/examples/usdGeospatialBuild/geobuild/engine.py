"""First engine component: explicit WKT-to-WKT coordinate reporting.

This is not scene resolution. Geographic tuples use longitude, latitude, height
in this diagnostic API only; this does not decide geographic USD storage.
The initial supported operation is WGS 84 geographic 3D <-> geocentric. Other
operations fail explicitly until validity/resource policies have evidence.
"""
import math
from dataclasses import dataclass
from typing import Protocol


class TransformError(ValueError):
    pass


@dataclass(frozen=True)
class Conversion:
    coordinates: tuple
    provenance: dict


class CoordinateEngine(Protocol):
    def convert(self, source_wkt: str, target_wkt: str, points) -> Conversion: ...


class ProjEngine:
    def convert(self, source_wkt, target_wkt, points):
        try:
            import pyproj
            from pyproj import CRS, network
            from pyproj.transformer import TransformerGroup
        except ImportError as exc:
            raise TransformError("No PROJ engine is installed.") from exc
        try:
            source, target = CRS.from_wkt(source_wkt), CRS.from_wkt(target_wkt)
        except Exception as exc:
            raise TransformError("Unreadable WKT; an authority code alone is not a definition.") from exc
        # A deliberately bounded first increment: no unknown datum/grid/epoch policy.
        geo, ecef = CRS.from_epsg(4979), CRS.from_epsg(4978)
        if not ((source.equals(geo) and target.equals(ecef)) or
                (source.equals(ecef) and target.equals(geo))):
            raise TransformError("Unsupported operation in increment 1; no fallback or assumed height/epoch.")
        try:
            values = tuple(tuple(float(v) for v in p) for p in points)
        except (TypeError, ValueError, OverflowError) as exc:
            raise TransformError("Coordinates must be finite triples.") from exc
        if not values or any(len(p) != 3 or not all(map(math.isfinite, p)) for p in values):
            raise TransformError("Coordinates must be a nonempty batch of finite triples.")
        if source.is_geographic and any(not (-180 <= p[0] <= 180 and -90 <= p[1] <= 90) for p in values):
            raise TransformError("Geographic coordinate outside the supported domain; entire batch rejected.")
        if source.is_geocentric and any(p == (0, 0, 0) for p in values):
            raise TransformError("Geocentric origin has no unique geographic position.")
        # Local deterministic resources only; never download a grid in a test.
        was_network_enabled = network.is_network_enabled()
        try:
            network.set_network_enabled(False)
            group = TransformerGroup(source, target, always_xy=True, allow_ballpark=False)
            if not group.best_available or not group.transformers:
                raise TransformError("Best operation unavailable; no lower-accuracy substitute.")
            operation = group.transformers[0]
            # No streaming result is exposed: a single failed point rejects the batch.
            columns = operation.transform(*zip(*values), errcheck=True)
            output = tuple(tuple(p) for p in zip(*columns))
            if len(output) != len(values) or any(not all(map(math.isfinite, p)) for p in output):
                raise TransformError("Engine returned an incomplete or non-finite batch.")
            provenance = {"engine": "PROJ", "pyproj_version": pyproj.__version__,
                          "engine_version": pyproj.proj_version_str,
                          "operation": operation.description, "pipeline": operation.definition,
                          "accuracy_metres": None if operation.accuracy < 0 else operation.accuracy,
                          "accuracy_note": "Engine estimate, not measured numerical residual.",
                          "tuple_order": "longitude/latitude/height or geocentric X/Y/Z",
                          "network": False}
            return Conversion(output, provenance)
        except TransformError:
            raise
        except Exception as exc:
            raise TransformError(f"Engine rejected the entire batch: {exc}") from exc
        finally:
            network.set_network_enabled(was_network_enabled)
