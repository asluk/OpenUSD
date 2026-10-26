"""WKT interpretation, height reporting and offline PROJ operations.

Proposal: WKT authority and normalization; coordinate components and height;
realized operations, resource failures and accuracy. See audit/source-contract.md.
Reports are computed results, not authored USD properties.
"""

import os
import re
import warnings
from decimal import Decimal
import numpy as np
from pyproj import CRS, datadir
from pyproj.crs import CompoundCRS
from pyproj.transformer import TransformerGroup
from common import Failure, require, finite

if os.getenv("GEOSPATIAL_RESOURCE_DIR"):
    datadir.append_data_dir(os.environ["GEOSPATIAL_RESOURCE_DIR"])

# Lexical normalization preserves quoted bytes, node order and exact decimals.
_tokens = re.compile(
    r'\s+|"(?:[^"]|"")*"|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[A-Za-z_][A-Za-z_0-9]*|[\[\](),]'
)
_enum = {
    v.lower(): v
    for v in (
        "Cartesian",
        "ellipsoidal",
        "spherical",
        "vertical",
        "parametric",
        "temporal",
        "affine",
        "ordinal",
        "east",
        "west",
        "north",
        "south",
        "up",
        "down",
        "future",
        "past",
        "clockwise",
        "counterClockwise",
        "geocentricX",
        "geocentricY",
        "geocentricZ",
        "columnPositive",
        "columnNegative",
        "rowPositive",
        "rowNegative",
        "displayRight",
        "displayLeft",
        "displayUp",
        "displayDown",
        "forward",
        "aft",
        "port",
        "starboard",
        "towards",
        "awayFrom",
        "unspecified",
        "northNorthEast",
        "northEast",
        "eastNorthEast",
        "eastSouthEast",
        "southEast",
        "southSouthEast",
        "southSouthWest",
        "southWest",
        "westSouthWest",
        "westNorthWest",
        "northWest",
        "northNorthWest",
    )
}


def normalize_wkt(text):
    out = []
    end = 0
    for m in _tokens.finditer(text):
        require(m.start() == end, "invalid WKT lexical character")
        end = m.end()
        t = m.group()
        if t.isspace():
            continue
        if t[0] == '"':
            out.append(t)
        elif t in "[(":
            out.append("[")
        elif t in "])":
            out.append("]")
        elif t == ",":
            out.append(t)
        elif t[0].isdigit() or t[0] in "+-.":
            d = Decimal(t)
            n = format(d, "f")
            if "." in n:
                n = n.rstrip("0").rstrip(".")
            out.append("0" if d == 0 else n)
        else:
            out.append(_enum.get(t.lower(), t.upper()))
    require(end == len(text), "invalid WKT trailing text")
    return "".join(out)


def as_crs(value):
    if isinstance(value, CRS):
        return value
    require(isinstance(value, str) and value.strip(), "missing WKT")
    require(
        not value.lstrip().upper().startswith("COORDINATEMETADATA"),
        "coordinate epochs are deferred",
    )
    try:
        c = CRS.from_wkt(value)
    except Exception as e:
        raise Failure("invalid or unsupported WKT: " + str(e)) from e
    dirs = [a.direction.lower() for a in c.axis_info]
    require(
        all(
            d in ("east", "north", "up", "geocentricx", "geocentricy", "geocentricz")
            for d in dirs
        ),
        "unsupported component directions",
    )
    require(c.geodetic_crs is not None, "CRS has no computable geodetic relation")
    return c


def geodetic(c):
    c = as_crs(c).geodetic_crs
    j = c.to_json_dict()
    j["type"] = "GeographicCRS"
    j.pop("id", None)
    j["coordinate_system"] = {
        "subtype": "ellipsoidal",
        "axis": [
            {
                "name": "Geodetic latitude",
                "abbreviation": "Lat",
                "direction": "north",
                "unit": "degree",
            },
            {
                "name": "Geodetic longitude",
                "abbreviation": "Lon",
                "direction": "east",
                "unit": "degree",
            },
            {
                "name": "Ellipsoidal height",
                "abbreviation": "h",
                "direction": "up",
                "unit": "metre",
            },
        ],
    }
    return CRS.from_json_dict(j)


def geocentric(c):
    j = geodetic(c).to_json_dict()
    j["type"] = "GeodeticCRS"
    j.pop("id", None)
    j["coordinate_system"] = {
        "subtype": "Cartesian",
        "axis": [
            {
                "name": "Geocentric " + a,
                "abbreviation": a,
                "direction": "geocentric" + a,
                "unit": "metre",
            }
            for a in "XYZ"
        ],
    }
    return CRS.from_json_dict(j)


def model_crs(wkt):
    c = as_crs(wkt)
    assumed = len(c.axis_info) == 2
    if assumed:
        unit = c.axis_info[0] if not c.is_geographic else None
        u = "metre" if unit is None else unit.unit_name
        factor = 1 if unit is None else unit.unit_conversion_factor
        vert = f'VERTCRS["EGM2008 height",VDATUM["EGM2008 geoid"],CS[vertical,1],AXIS["Gravity-related height",up,LENGTHUNIT["{u}",{factor:.17g}]]]'
        c = CompoundCRS(
            "Horizontal with assumed EGM2008 height", [c, CRS.from_wkt(vert)]
        )
        warnings.warn(
            "missing vertical reference: assuming EGM2008 height (EPSG:3855)",
            stacklevel=2,
        )
    require(
        len(c.axis_info) == 3, "model placement requires a complete three-component CRS"
    )
    return c, assumed


def height_report(wkt, model=True):
    original = as_crs(wkt)
    c, assumed = model_crs(wkt) if model else (original, False)
    vertical = next((s for s in c.sub_crs_list if s.is_vertical), None)
    if c.is_geocentric or len(c.axis_info) < 3:
        kind = "none"
        ref = None
        unit = None
    elif vertical:
        kind = "gravityRelated"
        ref = (
            "EPSG:3855"
            if assumed
            else (
                ":".join(vertical.to_authority())
                if vertical.to_authority()
                else vertical.name
            )
        )
        unit = vertical.axis_info[0].unit_name
    else:
        kind = "ellipsoidal"
        ref = {"ellipsoid": c.ellipsoid.name, "datum": c.datum.name}
        unit = c.axis_info[2].unit_name
    return dict(
        heightModel=kind,
        heightReference=ref,
        heightUnit=unit,
        heightReferenceSource="assumed" if assumed else "declared",
    )


class Engine:
    def __init__(self):
        self.cache = {}
        self.operations = []

    def convert(self, points, source, output):
        source = as_crs(source)
        output = as_crs(output)
        p = finite(points)
        one = p.ndim == 1
        p = np.atleast_2d(p)
        require(
            p.shape[1] in (2, 3), "coordinate domain must have two or three components"
        )
        key = (source.srs, output.srs)
        if key not in self.cache:
            with warnings.catch_warnings(record=True):
                group = TransformerGroup(
                    source, output, always_xy=True, allow_ballpark=False
                )
            require(
                bool(group.transformers) and group.best_available,
                "required coordinate operation or grid unavailable; no lower-accuracy substitute",
            )
            require(
                not re.search(
                    r"(?:^|\s)(?:proj=(?:deformation|defmodel|velocitygrid)|d(?:x|y|z|rx|ry|rz|s)=)",
                    group.transformers[0].definition,
                ),
                "coordinate-epoch-dependent operation outside initial scope",
            )
            self.cache[key] = group.transformers[0]
        t = self.cache[key]
        try:
            q = np.array(t.transform(*p.T, errcheck=True)).T
        except Exception as e:
            raise Failure("coordinate operation failed: " + str(e)) from e
        finite(q)
        try:
            op = t.get_last_used_operation()
        except Exception:
            op = t
        self.operations.append(
            dict(
                description=op.description,
                pipeline=op.definition,
                accuracy_m=None if op.accuracy < 0 else op.accuracy,
                source=source.name,
                output=output.name,
            )
        )
        return q[0] if one else q
