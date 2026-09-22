"""Process boundary to the compiled native Hydra scene-index consumer."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import numpy as np


def consume(frames, executable=None, library_dirs=None, render=None):
    executable = executable or os.environ.get("GEO_HYDRA_EXECUTABLE")
    if not executable or not Path(executable).is_file():
        raise RuntimeError("Complete run requires the compiled geobuildHydra executable")
    env = dict(os.environ)
    env["PATH"] = (library_dirs or env.get("GEO_HYDRA_LIBRARY_PATH", "")) + os.pathsep + env.get("PATH", "")
    # The bridge does not load USD schemas or retired geospatial plugins.
    env.pop("PXR_PLUGINPATH_NAME", None)
    with tempfile.TemporaryDirectory(prefix="geobuild-hydra-") as folder:
        source, output = Path(folder) / "input.json", Path(folder) / "output.json"
        source.write_text(json.dumps({"frames": [f.snapshot() for f in frames]}, allow_nan=False), encoding="utf-8")
        command=[str(executable), str(source), str(output)]
        if render:
            command.append(str(Path(render).resolve()))
        completed = subprocess.run(command, env=env,
                                   capture_output=True, text=True, timeout=180)
        if completed.returncode:
            raise RuntimeError("Native Hydra consumer failed: " + completed.stderr[-2000:])
        result = json.loads(output.read_text(encoding="utf-8"))
    if any('geospatial' in name.lower() for name in result['loaded_modules']):
        raise AssertionError('A retired geospatial module was loaded')
    residual = 0.0
    for frame, native in zip(frames, result["frames"]):
        if not native["input_unchanged"] or set(native["prims"]) != set(frame.prims):
            raise AssertionError("Hydra changed upstream data or returned an incomplete scene")
        for path in frame.prims:
            actual = np.array(native["prims"][path]["world_points"]).reshape((-1, 3))
            expected = frame.world_points(path)
            if len(actual):
                residual = max(residual, float(np.linalg.norm(actual - expected, axis=1).max()))
    result["maximum_consumer_residual_output_units"] = residual
    return result
