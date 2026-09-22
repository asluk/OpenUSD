# Runtime behavior and workflow evidence

### Geospatial scenes with shared placement

- A railway, a site asset and a scalar field should retain their source coordinates while participating in one scene.
- Rendering, world-position queries, bounds and physics need the same resolved placement.

### Railway source and scene identity

- 1,473 source features match USD object identities and first-coordinate anchors.
- 186 railway curves retain 3,526 vertices by count; interior placement is still unchecked.
- These checks establish what survived conversion; they do not establish resolved rails-on-map placement.

### Two runtime targets

- Non-Hydra: a renderer-independent scene resolver for placements, coordinate queries and bounds. Not built.
- Hydra: a scene-index adapter consuming the same resolved placement and propagating changes. Not built.
- Consumer consistency is distinct from R29, Implementable from the text alone, which requires different transformation engines.

### Next complete demonstration

- Import the railway and a site asset, resolve them into one project CRS, and verify placement against independent controls.
- Relocate an asset, scrub time and compose another layer; compare non-Hydra queries with Hydra results after each change.
- State placement error and valid extent, preserve source data, and fail visibly when a required operation cannot run.

### Review requests

- Review the proposed runtime prose against the functional requirements and close the carrier, placement and scope decisions.
- Supply source CRS/epoch/vertical metadata, expected control points and a distance-and-extent acceptance criterion.
- Use the next railway/site demonstration to review both consumer paths and separate engine agreement from correctness.

### Run evidence

**51 passed, 0 failed, 0 skipped.** These are component and build-integrity checks, not full-workflow conformance.

Start with the [README](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/README.md), [proposed runtime behavior](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/proposal/runtime-behavior.md), and [slides](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/docs/checkpoint.pdf).
