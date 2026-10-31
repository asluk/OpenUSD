#
# Copyright 2026 NVIDIA CORPORATION & AFFILIATES
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
"""Shared input validation and locally proposed Profiles identities.

This implementation's callable interfaces are not proposed USD standard APIs.
The tested authority and provenance are recorded in audit/authority.json.
"""

from pathlib import Path
import numpy as np
from pxr import Plug

ROOT = Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT / "schema"))
CAPABILITY = "usd.geospatial.crsResolution.v1"
PROFILE = "usd.geospatial.publication.v1"


class Failure(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise Failure(message)


def finite(x):
    a = np.asarray(x, dtype=float)
    require(np.isfinite(a).all(), "non-finite coordinate or placement")
    return a
