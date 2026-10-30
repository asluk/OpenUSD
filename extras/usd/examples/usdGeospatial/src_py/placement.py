#
# Copyright 2026 NVIDIA CORPORATION & AFFILIATES
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
"""Composed CRS binding, physical orientation and ordered model placement.

ModelMap.forward applies descendant USD transforms in model space, then
stage conformance, physical orientation and CRS placement. The anchor's
ordinary adjustment follows in the fixed working chart. A descendant reset
suppresses that ordinary adjustment without discarding georeferencing.
"""

import bisect
import math
import warnings
import numpy as np
from pxr import Usd, UsdGeom, Sdf
from common import Failure, require, finite
from crs import as_crs, normalize_wkt, model_crs, geodetic, geocentric
from math_util import stage_basis, enu_basis, pose, rotation, apply_matrix


def value(attr, time_code, typ, required=True):
    require(
        bool(attr) and attr.GetTypeName() == typ,
        "missing or wrongly typed " + str(attr.GetName()),
    )
    v = attr.Get(time_code)
    require(
        v is not None or not required, "blocked or unavailable " + str(attr.GetName())
    )
    return v


def attitude(prim, time_code):
    a = prim.GetAttribute("crs:orientation")
    if not a or not a.HasAuthoredValueOpinion():
        return np.eye(3)
    require(a.GetTypeName() == Sdf.ValueTypeNames.Double3, "wrongly typed orientation")

    def at(t):
        v = value(a, t, Sdf.ValueTypeNames.Double3)
        return pose(v)

    samples = a.GetTimeSamples()
    if time_code.IsDefault() or not samples:
        return rotation(at(time_code))
    t = time_code.GetValue()
    i = bisect.bisect_right(samples, t)
    if i == 0:
        return rotation(at(samples[0]))
    if (
        i == len(samples)
        or samples[i - 1] == t
        or prim.GetStage().GetInterpolationType() == Usd.InterpolationTypeHeld
    ):
        return rotation(at(samples[i - 1]))
    qa, qb = at(samples[i - 1]), at(samples[i])
    dot = float(np.dot(qa, qb))
    require(
        abs(dot) > 1e-12,
        "ambiguous 180-degree orientation arc; rotational uncertainty 2e-12 radians",
    )
    if dot < 0:
        qb = -qb
        dot = -dot
    f = (t - samples[i - 1]) / (samples[i] - samples[i - 1])
    if dot > 1 - 1e-12:
        q = (1 - f) * qa + f * qb
    else:
        theta = math.acos(min(1, dot))
        q = (math.sin((1 - f) * theta) * qa + math.sin(f * theta) * qb) / math.sin(
            theta
        )
    return rotation(q)


def direct(p):
    return "GeospatialCRSBindingAPI" in p.GetAppliedSchemas()


def controlling(p):
    while p and not p.IsPseudoRoot():
        if direct(p):
            return p
        p = p.GetParent()
    raise Failure("content outside a CRS binding")


def uniform(prim, name, typ):
    a = prim.GetAttribute(name)
    require(
        a and a.GetVariability() == Sdf.VariabilityUniform and a.GetTypeName() == typ,
        "invalid uniform field " + name,
    )
    require(not a.GetTimeSamples(), "active samples on uniform " + name)
    return value(a, Usd.TimeCode.Default(), typ)


def definition(p, model=True):
    w = str(uniform(p, "crs:wkt", Sdf.ValueTypeNames.Token))
    if normalize_wkt(w) != w:
        warnings.warn("non-normal WKT spelling", stacklevel=2)
    return model_crs(w)[0] if model else as_crs(w)


def check_roles(p):
    for ancestor in [p]:
        authored = [
            n
            for n in ("crs:position", "crs:orientation")
            if ancestor.GetAttribute(n)
            and ancestor.GetAttribute(n).HasAuthoredValueOpinion()
        ]
        require(
            not authored
            or (direct(ancestor) and ancestor.GetTypeName() != "GeospatialDataSource"),
            "placement fields in an invalid role on " + str(p.GetPath()),
        )


class ModelMap:
    """Placement and its inverse for one composed binding at one USD time.

    Bases map model units and up-axis into physical ENU, then geocentric
    coordinates. The enclosing CRS supplies the fixed chart for the anchor's
    ordinary adjustment; requesting another output CRS does not move the model.
    """

    def __init__(self, prim, time_code, engine, working=None):
        self.prim = prim
        self.stage = prim.GetStage()
        self.time_code = time_code
        self.engine = engine
        require(
            bool(UsdGeom.Xformable(prim)),
            "direct model binding requires Xformable content",
        )
        self.source = definition(prim)
        self.source_geographic = geodetic(self.source)
        self.source_geocentric = geocentric(self.source)
        self.position = finite(
            value(
                prim.GetAttribute("crs:position"), time_code, Sdf.ValueTypeNames.Double3
            )
        )
        if self.source.is_geocentric:
            require(
                not (self.position[0] == 0 and self.position[1] == 0),
                "geocentric pole does not determine an attitude meridian",
            )
        longitude_latitude_height = self.engine.convert(
            self.position, self.source, self.source_geographic
        )
        self.origin_ecef = self.engine.convert(
            longitude_latitude_height, self.source_geographic, self.source_geocentric
        )
        self.enu_to_ecef = enu_basis(*longitude_latitude_height[:2])
        self.orientation_matrix = attitude(prim, time_code)
        self.stage_to_enu = stage_basis(self.stage)
        self.anchor_adjustment = np.asarray(
            UsdGeom.Xformable(prim).GetLocalTransformation(time_code)
        )
        if working is None:
            parent = prim.GetParent()
            while parent and not parent.IsPseudoRoot() and not direct(parent):
                parent = parent.GetParent()
            working = definition(parent) if parent and direct(parent) else self.source
        self.working = as_crs(working)
        self.working_origin = None

    def prepare_chart(self):
        if self.working_origin is not None:
            return
        self.working_origin = self.engine.convert(
            self.origin_ecef, self.source_geocentric, self.working
        )
        self.working_geographic = geodetic(self.working)
        self.working_geocentric = geocentric(self.working)
        if self.working.is_geographic:
            longitude_latitude_height = self.engine.convert(
                self.working_origin, self.working, self.working_geographic
            )
            self.working_enu_to_ecef = enu_basis(*longitude_latitude_height[:2])
            self.working_origin_ecef = self.engine.convert(
                self.working_origin, self.working, self.working_geocentric
            )
        else:
            self.working_units = np.array(
                [a.unit_conversion_factor for a in self.working.axis_info]
            )

    def chart(self, coordinates):
        self.prepare_chart()
        if self.working.is_geographic:
            return (
                (
                    self.engine.convert(
                        coordinates, self.working, self.working_geocentric
                    )
                    - self.working_origin_ecef
                )
                @ self.working_enu_to_ecef
                @ np.linalg.inv(self.stage_to_enu).T
            )
        return (
            (coordinates - self.working_origin)
            * self.working_units
            @ np.linalg.inv(self.stage_to_enu).T
        )

    def unchart(self, coordinates):
        self.prepare_chart()
        if self.working.is_geographic:
            return self.engine.convert(
                self.working_origin_ecef
                + (coordinates @ self.stage_to_enu.T) @ self.working_enu_to_ecef.T,
                self.working_geocentric,
                self.working,
            )
        return (
            self.working_origin
            + (coordinates @ self.stage_to_enu.T) / self.working_units
        )

    def forward(self, points, output, descendant_transform=None, reset=False):
        """Apply the proposal's ordered map without modifying the source stage."""
        # 1. Ordinary descendant transforms remain in model-local space.
        model_points = np.atleast_2d(finite(points))
        model_points = apply_matrix(
            model_points,
            np.eye(4) if descendant_transform is None else descendant_transform,
        )
        # 2. Conform stage axes/units, orient in physical ENU, then place at
        #    the authored position. This is a point map, not one global matrix.
        placed_ecef = (
            self.origin_ecef
            + (model_points @ self.stage_to_enu.T @ self.orientation_matrix.T)
            @ self.enu_to_ecef.T
        )
        if reset or np.array_equal(self.anchor_adjustment, np.eye(4)):
            return self.engine.convert(placed_ecef, self.source_geocentric, output)
        # 3. Apply the anchor's ordinary adjustment in its fixed working chart.
        working_coordinates = self.engine.convert(
            placed_ecef, self.source_geocentric, self.working
        )
        return self.engine.convert(
            self.unchart(
                apply_matrix(self.chart(working_coordinates), self.anchor_adjustment)
            ),
            self.working,
            output,
        )

    def inverse(self, points, input_crs, descendant_transform=None, reset=False):
        working_coordinates = self.engine.convert(points, input_crs, self.working)
        if not reset:
            require(
                abs(np.linalg.det(self.anchor_adjustment)) > 1e-15,
                "singular required inverse",
            )
            working_coordinates = self.unchart(
                apply_matrix(
                    self.chart(working_coordinates),
                    np.linalg.inv(self.anchor_adjustment),
                )
            )
        resolved_ecef = self.engine.convert(
            working_coordinates, self.working, self.source_geocentric
        )
        model_points = (
            (resolved_ecef - self.origin_ecef)
            @ self.enu_to_ecef
            @ self.orientation_matrix
            @ np.linalg.inv(self.stage_to_enu).T
        )
        if descendant_transform is not None:
            require(
                abs(np.linalg.det(np.asarray(descendant_transform))) > 1e-15,
                "singular instancer inverse",
            )
            model_points = apply_matrix(
                model_points, np.linalg.inv(np.asarray(descendant_transform))
            )
        return model_points
