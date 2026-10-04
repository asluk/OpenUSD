# Geospatial: defined CRS binding, blocked placement

The current shared proposal still needs exact authored definitions before a full placement build can follow it without guessing. This run stops dependent placement and executes the defined CRS discovery and composition behavior in three independent readers.

The editorial revision closes obsolete interface and transform-authoring contradictions. The remaining audit identifies eight narrower missing contracts and one existing 3D-versus-2D example inconsistency. It does not reopen agreed functional outcomes or treat internal implementation methods as standardized data.

Fresh evidence: 15 tests passed. Each reader passed 12 cases and 19 queries, giving 57 reader/query checks. Source layers and fixture bytes remained unchanged. This run executed zero projection or placement jobs and produced no resolved export.

[Editable slides](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/delivery/geospatial-build.pptx) · [PDF](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/delivery/geospatial-build.pdf) · [Receipt](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/delivery/run-report.json) · [Proposal audit](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/QUALITY_REVIEW.md) · [Build loop](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/BUILD_LOOP.md)


## What is already settled

| Authored fact or outcome | Existing answer |
|---|---|
| CRS authority | Complete WKT is authoritative. The typed definition stores uniform token crs:wkt. |
| Binding and composition | Applied binding uses a CRS reference. Nearest direct binding defines composed subtree scope. |
| Placement order | Separate CRS position, orientation and scale resolve before ordinary USD transforms. |
| Source and output | Preserve source facts and adjusted physical placement. The consumer selects the output CRS. |
| Stage conventions | Writers or assemblers author unit/up-axis correctives. Readers honor ordinary USD data. |

Geographic source positions and geographic coordinate queries are supported. Site calibration lives in a derived CRS definition. Engines select applicable operations, manage resources and report operation accuracy or visible failure. Explicit export preserves values, associations and sampling meaning. Coordinate epochs remain roadmap work.

## Missing authored representation

| Audit category | Exact contract still required |
|---|---|
| G02: placement fields | Names, types, defaults/requiredness, applicability, orientation/scale bases and mutual order. |
| G05: WKT string normalization | A prescribed serialized normal form that preserves the represented information. |
| G06: measurement coordinates | An authored association identifying source coordinates, including external assets. |
| G07: dependency declaration | A carrier and composition rule readable without traversal, including unloaded content. |
| G09: export sampling | A record distinguishing exported-sample interpolation from original-source resolution. |
| G10: existing inconsistency | Reconcile the 3D scope statement with two-axis WKT examples without silently broadening scope. |

Questions 2, 10, 11, 12 and 14 retain the specific representation work. The dimensionality inconsistency is existing proposal text, not a new restriction invented by this run. The fixtures use complete 3D definitions copied unchanged from the proposal.

## Missing observable definitions

| Audit category | Agreed outcome and narrower missing meaning |
|---|---|
| G03: project adjustments | Post-placement adjustments preserve physical placement. Their authored coordinate frame remains undefined. |
| G04: components and scene domain | E/N/up and geographic queries are settled. Other component mappings and geographic scene frames/bounds remain open. |
| G08: extent and agreement | State the approximation domain, how the claim is satisfied and how comparable operations are measured. |

Operation accuracy, numerical agreement and approximation over an extent are different claims. A full placement-chain accuracy estimate is not a requirement-28 obligation. Internal differentiation, caching or adapter design is implementation freedom. Missing consumer tests are verification work, not new design questions.

## Verification

| Control group | Cases | Queries per reader |
|---|---:|---:|
| References and referenced assembly | 2 | 6 |
| Stronger layer, variant and inherits | 3 | 4 |
| Equivalent composed data | 1 | 2 |
| Unloaded payload | 1 | 2 |
| Missing, broken or invalid definitions | 5 | 5 |
| Total | 12 | 19 |

Headless OpenUSD, independently written native C++ OpenUSD and a live OV stage each match authored expectations. The readers do not import one another's discovery function. Native discovery does not exercise Hydra placement. Live OV discovery does not ingest resolved geometry. The 15 tests also check the readiness gate, fixture field ownership and the previous resolver's incompatibility.

Partial checks reject absent binding, a broken nearest binding, wrong WKT type or variability and an empty definition. A broken nearest binding cannot fall back to an enclosing CRS. Available enclosing scope remains readable with a payload unloaded; content absent from that payload fails. These checks do not certify WKT normalization, the dependency declaration or whole-asset conformance.

Executed source: `d1746ce725999e2a472df6c6dee13a804ff732e2`. Current receipt, fixtures and editable slides accompany the README. No placement or geodetic accuracy claim is made.
