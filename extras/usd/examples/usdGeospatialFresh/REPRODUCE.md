# Reproducing the assessment

The proposal snapshot is pinned by commit, Git blob and SHA-256 in the authority
record. It remains outside the public companion package. The source-generation
record identifies original inputs and the small reused neutral recording tool.
This candidate contains newly authored readers, schema, fixtures and tests.

## Dependencies

Recorded environment: OpenUSD Python 26.8, native SDK 26.11, Python PROJ 9.8.1,
native PROJ 9.4.1 with SQLite/TIFF enabled, NumPy, pyproj, netCDF4, rasterio,
pytest and matplotlib. Native compilation uses MSVC and CMake. The Windows
SDK/Python/PROJ paths in `native/CMakeLists.txt`, `native/build.cmd` and the native
test runner describe this machine and can be supplied for another installation.
They are implementation infrastructure, not proposal requirements.

Provide the original datasets under `inputs/original` and verify them against
the original-data manifest. Offline `fr_ign_RAF20.tif` and
`us_noaa_g2018u0.tif` resources belong in the configured PROJ resource search
path. `GEOSPATIAL_RESOURCE_DIR` configures the Python resource directory. The
native runner's PROJ search path includes that resource directory and PROJ's
database directory. Network grid fetching is disabled in the recorded run.

## Execution

1. Generate the authored fixtures and independent expectations with
   `python tests/make_inputs.py`.
2. Configure/build the native reader using `native/build.cmd`, or CMake with
   `USD_ROOT` and `PROJ_ROOT` pointing at the installed SDKs. Set
   `GEOSPATIAL_PROJ_ROOT`, `GEOSPATIAL_USD_ROOT` and optionally
   `GEOSPATIAL_PYTHON_ROOT` for the native test runner's DLL/database locations.
3. Run `python -m pytest tests -q -p no:cacheprovider --junitxml=evidence/pytest.xml`.
4. Run `python delivery/landxml_workflow.py` and
   `python delivery/run_evidence.py` for original-data and full-geometry evidence.
5. Run `python delivery/plots.py` for the scientific plots. The Westminster plot
   uses the preserved site-grid coordinates, not an invented surface.
6. Execute `delivery/ov_consume.py` in an Omniverse application with `omni.usd`
   enabled. It writes the Python-derived geometry into the application's USD
   context stage, reads it back and reports distances. It performs no independent
   geospatial computation.
7. `python delivery/compact_bakes.py` creates lossless Crate copies for the
   delivered views and checks unchanged geometry and transforms. Build the
   neutral `record_storm` utility with CMake option
   `GEOSPATIAL_BUILD_STORM=ON`. It records the ordinary render stages with
   Hydra Storm. Ground, camera and display materials are presentation overrides.
8. Generate the deck from the README with `delivery/build_deck.mjs` in the Codex
   presentation runtime. This bundle needs the workspace-only
   `--import ./delivery/font_aliases.mjs` adapter for its missing standard-font
   aliases, using already-bundled metrics without changing installed packages.
   The actual deck fonts use the registered local Calibri/Consolas font files. The deck
   source, editable objects, rendered pages and PDF are checked together.

## What the evidence establishes

Survey expectations come from paired supplied CSVs matched by point ID, not
reader-to-reader agreement. Analytic controls independently establish ENU axes,
attitude, reset behavior, source interpolation and ordinary transform order.
Cross-reader comparisons fix definitions, source samples and operations first.
Selected pipelines and resource hashes accompany the results. Differences at
large coordinate magnitudes are distances in metres, not digit-count claims.

The native-format decoder is deliberately shared. Its output retains the asset,
selection, native indices, coordinate tuples, values, masks and observation
times. The native reader checks the authored asset/selection/CRS before its own
placement evaluation. This is shared format transport, not shared placement.

The climate and Westminster CF files are explicit derived authoring examples.
The climate demonstration file's observational provenance is unverified. Its
coordinate interpretation and temperature units are illustrative declarations.
The original climate file lacks required CF declarations and height. The new
copy declares synthetic height/time and a synthetic second temperature field.
The LandXML copy retains source breakline coordinates and indices while exposing
them through the proposed CF association. Original files remain byte-identical.

Runtime interfaces, cache policies, CLI request JSON and file names are local
implementation choices. The proposal prescribes none of these callable APIs.
`resolvedOffset` is an ordinary double translate in a derived bake, not a new
geospatial field or a private resolved-state marker.

Continuous-face certification, geometric primvar export and format combinations
outside the declared decoder subset remain explicit prototype limits. No claim
of full USD, CF or geospatial conformance follows from this run.
