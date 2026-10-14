# Reproduce the frozen candidate

This is a tested Windows environment, not a claim of portable binary packaging. Run commands from this directory. The example does not fetch resources or enable network transformations.

Dependencies: Python with USD 26.8 bindings including UsdProfiles, pyproj 3.8, NumPy, pytest, rasterio and netCDF4; native USD 26.11 SDK; TIFF-enabled PROJ; MSVC/NMake and CMake. The native reader requires the SDK Python 3.10 library/DLL. `native/build.cmd` records the execution machine's paths. For another environment, invoke CMake with explicit USD_ROOT, PROJ_ROOT and PYTHON_ROOT, then build `native-build` with a compatible toolchain.

The recorded workflow harness expects two sibling directories beside this example: `geospatial-proj-tiff` (native PROJ installation) and `geospatial-model-resources` (the grids in resource-manifest.json). Supply those explicitly as local directories or junctions. Its recorded SDK paths also need adaptation on another machine. That configuration affects dependency locations, not geospatial scene meaning. Do not load another PROJ DLL ahead of the TIFF-enabled build.

```powershell
python tests/fixtures.py
python tests/make_workflows.py
python -m pytest tests -q
python tests/run_workflows.py
python tests/native_controls.py
python tests/native_guard_checks.py
python tests/focused_native_checks.py
python tests/compound_probe.py
python tests/sharing_checks.py
```

The copied compact receipts retain the original execution paths for provenance. New fixtures and outputs are generated in the current directory. The exact authority document is held outside this package to avoid unsolicited cross-repository backlinks; generation-record.json identifies its commit and document hash.

The supplemental final_checks.py verifies the bake and original hashes, then checks the original freeze manifest. Additional neutral check files packaged after the freeze are not new generation inputs. delivery/ documents the executed consumer bridges. README.md and the deck are the assessment, not an implementation specification.
