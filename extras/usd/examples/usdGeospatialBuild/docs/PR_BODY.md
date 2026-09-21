A geospatial implementation needs an explicit runtime contract derived from functional requirements. This draft delivers the first runnable components and the evidence/decisions that determine the next increment.

- **35 tests passed, 0 failed, 0 skipped** in this delivered run.
- **29 functional requirements**, **9 numbered open questions** and **7 grouped build stops** are tracked.
- The requirements and runtime derivation remain drafts. Complete scene resolution and independent OpenUSD/OV agreement remain unimplemented.

Run record: [20260921-first](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/runs/20260921-first/report.json). Source input:
[bundled functional requirements](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/inputs/requirements.md), revision `eab823f46dad7c959019e5ce1851c8295c2a3701`.
Implementation revision: `2b4b9babf655f6004cb1b9646e3fb725a348579b`.
The [runtime derivation](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/docs/RUNTIME.md), [fixture matrix](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/docs/FIXTURES.md) and
[build stops](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/docs/STOPS.md) explain the scope of every result.

### What runs

- A read-only binding inspector reads composed USD relationships, nested overrides and forwarded targets.
- A PROJ adapter converts explicit WGS 84 geographic-3D and geocentric coordinates, with operation provenance and whole-batch failures.
- Input-change checks invalidate stale derivations before old tests can count as current evidence.
- Anchor decoding, placement matrices, scene-target selection, general datum/grid/epoch operations and OV integration remain pending.

### Review

Start with the [README](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/README.md). It is the source for this review guide and the [slide deck](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/docs/checkpoint.pdf).

The [runtime contract](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/docs/RUNTIME.md), [fixture matrix](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/docs/FIXTURES.md) and [build stops](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/docs/STOPS.md) connect the implementation to the requirements.

### Validation

- Maximum measured Cartesian residual: **0.000000000 m** at a coordinate magnitude of **6378147.000 m**.
- Expected coordinates come from WGS 84 ellipsoid equations calculated separately from PROJ.
- The analytic check uses a **0.000001 m** numerical tolerance. This is a component-test tolerance.
- PROJ reports this operation's accuracy as **unknown**. A measured residual does not replace the engine's accuracy estimate.

The README states the test scope, optional attachment checks, remaining decisions and reproduction commands. This checkpoint does not establish complete scene resolution or independent OpenUSD/OV agreement.
