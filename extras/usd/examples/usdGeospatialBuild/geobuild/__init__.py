"""Experimental geospatial implementation; no standard callable API claimed."""
from pathlib import Path
from pxr import Plug
Plug.Registry().RegisterPlugins((Path(__file__).resolve().parents[1]/'schema/generated/plugInfo.json').as_posix())
