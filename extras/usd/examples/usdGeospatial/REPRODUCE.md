# Reproduce this fresh derivation

Run the commands below from `extras/usd/examples/usdGeospatial`. The package
name stays fixed across runs; [audit/companion.json](audit/companion.json)
identifies the source derivation and subsequent packaging checks.

The native CMake inputs are configurable `USD_ROOT`, `PROJ_ROOT` and
`PYTHON_ROOT`; defaults describe the installed Windows infrastructure used here.
Use a C++17 MSVC developer shell, the unmodified OpenUSD SDK, a TIFF-enabled
PROJ build and Python with USD, pyproj, NumPy, netCDF4, Pillow and matplotlib.
These are implementation dependencies, not additions to the proposed USD model.

1. Set `GEOSPATIAL_RESOURCE_DIR` to a directory with the recorded PROJ grids.
   Keep networking disabled for the numerical runs. Use the same resource
   hashes recorded in `audit/resources.json` for comparable operations.
2. Build `native/CMakeLists.txt` with CMake; `native/build.cmd` selects the
   installed local toolchain. Put SDK/PROJ/Python DLL directories on `PATH`.
3. Run `python tests/fixtures.py`, then `python tests/run.py`. The fixture
   generator recreates only this package's derived examples. A fresh derivation
   of reader logic is a separate requirement; rerunning these commands alone
   does not independently derive a new implementation.
4. Run `python delivery/evidence.py` and `python delivery/plots.py` for complete
   original-data comparisons, ordinary bakes and scientific figures.
5. Run `native/build/record_storm.exe inputs/authored/tower-storm-view.usda
   evidence/tower-storm.png <SDK plugin directory>`. This neutral recorder
   consumes the native reader's ordinary geometry, with a stated display chart.
6. Execute `delivery/consume_ov.py` in an actual Omniverse application with
   `omni.usd` and `omni.kit.exec.core` enabled. For automation, use a bounded
   hidden subprocess and require a clean exit, the success marker and a fresh
   `evidence/omniverse.json`; application exit status alone is insufficient.
7. Run `delivery/plots.py`, then the local artifact-tool deck builder using its
   recorded Node runtime. The builder reads the README sections, tables and
   images; it does not carry a separate set of proposal claims. Validate the
   PowerPoint and inspect each rendered slide before producing the PDF.
8. Run `python tests/reviewability.py`, follow [REVIEWING.md](REVIEWING.md) through
   the final source diff, then run `python delivery/freeze.py`. Readability and
   PR navigation are required delivery checks; numerical success alone does not
   make a run ready to publish.

The assessment is for finite points, tested role-bearing primvars and resulting
ordinary polygonal geometry. It is not continuous curve/subdivision certification
or a complete importer/exporter for every valid native format. Such unsupported
requests must be reported, not silently replaced by a successful approximation.

Original dataset metadata and introduced example inputs are distinguished in
the README and fixture provenance. In particular, the original climate file is
not a complete CF association or a dated weather observation; the illustrative
wrapper explicitly authors missing unit/height/time facts. The LandXML client
supplies records plus companion WKT to a coordinate query, without claiming a
standard LandXML association profile.

Primary references used to verify format and publication behavior:

- [CF 1.12, coordinate systems and WKT](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.12/cf-conventions.pdf)
- [RFC 7946 GeoJSON](https://www.rfc-editor.org/rfc/rfc7946)
- [OpenUSD Profiles](https://openusd.org/release/user_guides/schemas/UsdProfiles/overview.html)
- [Official PROJ grid distribution](https://cdn.proj.org/)

No claim of upstream acceptance, approved capability identities, geodetic-engine
independence or expanded OSRB clearance follows from a successful run.
