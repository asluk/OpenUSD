#
# Copyright 2026 NVIDIA CORPORATION & AFFILIATES
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
"""Stage units/axes, physical heading-pitch-roll and point matrix helpers.

NumPy uses column-vector bases here. apply_matrix accepts USD row-vector
matrices; transposes at those boundaries are deliberate.
"""

import math
import numpy as np
from pxr import UsdGeom
from common import require, finite


def stage_basis(stage):
    # Columns here map vectors; equivalent to the proposal's Core row-vector mapping.
    m = UsdGeom.GetStageMetersPerUnit(stage)
    require(math.isfinite(m) and m > 0, "invalid stage length unit")
    return (
        np.eye(3)
        if UsdGeom.GetStageUpAxis(stage) == "Z"
        else np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    ) * m


def enu_basis(lon, lat):
    l, b = np.radians([lon, lat])
    sl, cl, sb, cb = np.sin(l), np.cos(l), np.sin(b), np.cos(b)
    return np.array([[-sl, -sb * cl, cb * cl], [cl, -sb * sl, cb * sl], [0, cb, sb]])


def qmul(a, b):
    return np.r_[
        a[0] * b[0] - np.dot(a[1:], b[1:]),
        a[0] * b[1:] + b[0] * a[1:] + np.cross(a[1:], b[1:]),
    ]


def pose(hpr):
    h, p, r = np.radians(finite(hpr)) / 2
    return qmul(
        qmul(
            np.array([math.cos(h), 0, 0, -math.sin(h)]),
            np.array([math.cos(p), math.sin(p), 0, 0]),
        ),
        np.array([math.cos(r), 0, math.sin(r), 0]),
    )


def rotation(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def apply_matrix(points, m):
    p = np.atleast_2d(finite(points))
    h = np.c_[p, np.ones(len(p))] @ np.asarray(m)
    require(np.all(np.abs(h[:, 3]) > 1e-15), "unavailable projective point")
    return finite(h[:, :3] / h[:, 3, None])
