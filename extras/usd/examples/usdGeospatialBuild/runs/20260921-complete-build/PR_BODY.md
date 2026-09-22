# Runtime behavior and workflow evidence

### Geospatial scenes with shared placement

- Place railway data, a calibrated site and a removable scalar overlay while retaining their source data.
- Headless queries, native Hydra/Storm and Omniverse Fabric consume the same evaluated placement.
- Execute every workflow and test alternative rules; use the failures and discrepancies to improve the design.

### Railway source and scene identity

- 1,473 source features resolve with all 15,822 vertices, object identities and polygon rings checked.
- Across 186 curves, offset-basis choice changes maximum mismatch from 16.71 cm to 41.7 micrometres.
- Three map tiles share the output frame. Height interpretation is explicit; survey metadata remains unknown.

### Two runtime targets

- Non-Hydra: read-only scene resolution, coordinate and relative-placement queries, bounds, edits and export.
- Hydra: a compiled scene index with geometry, topology and change notices, rendered directly by Storm.
- Omniverse Fabric is an additional real consumer; independent Karney arithmetic checks geodetic consistency.

### Design choices exercised by the complete run

- Affine and pointwise placement are both implemented; extent sweeps reveal where one matrix loses fidelity.
- Applying an ancestor transform after an absolute position produces a tested 1,000 m violation.
- Missing grids or coordinate epochs fail observably; animation time never supplies a coordinate epoch.

### Review requests

- Approve the drafted functional requirements and select among the executed runtime alternatives.
- Clarify the extent/bound domain, unit and offset basis, project placement and dependency/target rules.
- Supply certified vertical/epoch metadata and control points where accuracy claims are required.

### Run evidence

**75 passed, 0 failed, 0 skipped.** All eight conditional workflow families execute; design approval and survey accuracy are not inferred.

Start with the [README](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/README.md), [proposed runtime behavior](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/proposal/runtime-behavior.md), and [slides](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/docs/checkpoint.pdf).
