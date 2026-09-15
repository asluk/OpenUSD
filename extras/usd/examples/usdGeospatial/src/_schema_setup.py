"""
_schema_setup.py -- register the codeless usdGeospatial schema at import time.

Importing this makes `CoordinateReferenceSystem` (typed) and `BindingAPI`
(single-apply) available, so crs:* properties authored with custom=False are
recognised as schema-defined. Self-contained equivalent of setting
PXR_PLUGINPATH_NAME to the resources dir before launch.
"""
import os
from pxr import Plug

# .../pxr/usd/usdGeospatial holds plugInfo.json; resources/ holds generatedSchema.usda
_HERE = os.path.dirname(os.path.abspath(__file__))
# src -> usdGeospatial -> examples -> usd -> extras -> <repo root>
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
_SCHEMA_LIB = os.path.join(_REPO_ROOT, "pxr", "usd", "usdGeospatial")


def register():
    pi = os.path.join(_SCHEMA_LIB, "plugInfo.json")
    if os.path.isfile(pi):
        Plug.Registry().RegisterPlugins(_SCHEMA_LIB)
    return _SCHEMA_LIB


register()
