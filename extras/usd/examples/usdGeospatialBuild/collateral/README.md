# Current delivery derivation

`derive_leans_delivery.py --run <fresh-run-directory>` verifies frozen source, derives the README and review body, packages portable evidence, and prepares slide data. `leans_slides.mjs` builds the editable deck from that README and the recorded results. `verify_leans_delivery.py` checks source/evidence claims, hashes, editable elements and final artifact provenance after every slide and PDF page has been inspected.

Python/C++ placement, OV runtime geometry writeback and native Hydra resolved-export rendering are distinct paths. Shared PROJ, shared external decoding and OV's reused Python algorithm remain explicit. No output claim follows from an application name. No upstream issue/PR links enter delivery.

Earlier query-only generators and audit helpers remain historical code and are not used by the current generator. The current receipt replaces stale evidence; historical delivery lives in Git history.

## Native build prerequisite

The runner rebuilds an already configured native build directory; it does not configure an empty one. From this example directory, use a Windows C++ developer shell, a matching OpenUSD SDK/Python ABI, CMake and Ninja. Set the following paths to installed dependencies, then configure:

```powershell
$taskUsdSdk = 'C:/path/to/OpenUSD/inst'
$taskProj = 'C:/path/to/TIFF-enabled-PROJ'
$taskNativePython = 'C:/path/to/OpenUSD-matching-Python'
$taskNativeBuild = 'C:/path/to/native-build'
cmake -S native -B $taskNativeBuild -G Ninja -DCMAKE_BUILD_TYPE=Release "-Dpxr_DIR=$taskUsdSdk" "-DUSD_SDK=$taskUsdSdk" "-DPython3_ROOT_DIR=$taskNativePython" "-DCMAKE_PREFIX_PATH=$taskUsdSdk;$taskProj"
```

Pass that directory as `run.py --native-build`, with the same SDK, PROJ and Python paths. `run.py --help` lists the other required host, grid/resource, Python-dependency and fresh-output arguments. The native runtime must load the TIFF-enabled PROJ DLL before any SDK copy without TIFF support. The execution receipt records the actual library/database/grid hashes and versions; substituting dependencies requires a new run. The delivered evidence is a record of the installed Windows environment, not a claim of a dependency-free or cross-platform build.
