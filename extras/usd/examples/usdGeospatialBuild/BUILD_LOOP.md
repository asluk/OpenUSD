# Requirements → model → behavior → implementation → evidence → delivery

The numbered requirements and explicit decisions are inputs. An older
implementation, test expectation or slide cannot fill a specification gap.
`inputs.json` pins the proposal, stock source base, composition reference and
six frozen candidate documents. The experiment is an implementable candidate;
its fields and conventions are not represented as group-approved standard text.

## Run in dependency order

1. Pin requirements, decisions and original data. Separate retained intent from
   obsolete callable interfaces or helpers that author transform resets.
2. Inventory authoritative information, owners, scope, units, time and reuse.
   Justify every authored representation against an actual requirement and
   existing OGC/USD semantics. WKT remains authoritative for facts it expresses.
3. Specify the complete candidate in `proposal/data-model.md` and
   `proposal/runtime-behavior.md`. Describe absence, defaults, composition,
   result domains, failures and export. Write distinguishing examples before
   code. Label complete alternatives where group choices remain open.
4. Freeze and hash the candidate. Derive fresh headless OpenUSD, native Hydra
   and live OV implementations independently from it. Share projection-engine
   dependencies openly; never count shared-engine parity as geodetic truth.
5. Execute authored-content validators, semantic controls and all retained
   datasets through the implementations. Check real consumer ingestion and
   scene-index transforms, not only successful registration or call counts.
6. Reverse-audit implementation choices against the model, and the model
   against requirements and data ownership. Challenge hidden fixture defaults,
   lost metadata, private export flags, stale results and unsupported evidence
   claims. Fix code defects. A new semantic decision requires a fresh frozen
   candidate and invalidates affected results; code behavior alone cannot
   justify it.
7. Commit source and run again from that source into a fresh output directory.
   Record hashes, actual operations/resources, metrics, failures, versions and
   conditional assumptions. Generate README from the receipt, then derive the
   review body and editable slides from README. Render and inspect the slides.
8. Deliver the same source/evidence/collateral to the authorized standing draft.
   Verify the remote tree, receipt and collateral. Keep planning as current state,
   with history in Git and immutable run records rather than appended logs.

## Required execution coverage

- Original railway GeoJSON; Eiffel/model placement and explicit writer
  conformance; original Colorado terrain and partner Colorado/France controls.
- City imagery and global measurements as data, with source coordinates,
  values, indices and recorded times kept associated. Synthetic and conditional
  inputs must be labeled beside each result.
- Full oriented/scaled frames and ordinary post transforms; independent
  bindings, references, stronger opinions, variants, source interpolation,
  stage units/up-axis, native instances and point instances.
- Multiple output selections, live source edits, failure and recovery,
  declarations with unloaded payloads, explicit export and fresh re-resolution.
- Operation/resource failures, invalid batches, coordinate-epoch deferral,
  source preservation, float quantization, derivative-probe checks and finite
  extent comparisons. Finite samples never establish a continuous bound.
- Actual Storm rendering from the native scene index, direct rendered-transform
  readback, live OV geometry/result readback and stock `usdchecker` discovery.
  Scientific plots remain labeled headless query visualizations.

Coordinate epochs are deferred in full; reference epochs inside CRS WKT are
retained. Supported ordinary datum and height operations may use engine-selected
grids. Missing required resources fail visibly. Large extent is exercised,
not excluded merely because it exceeds the construction examples.

## Reproduce this package

Create a Python environment with `usd-core`, `pyproj`, `numpy`, `pytest`, `h5py`
and `matplotlib`. Register the codeless schema under `schema/generated` and the
Python validator under `geospatialValidation`. Generate the schema with the
stock generator using `schema/generate.py`; generated files accompany this run.
Original supplied data and newly authored demonstration stages accompany it.
`intake.py` documents source-to-stage authoring; private ZIPs are not required
when using the included stages and datasets.

Build `native/` with CMake against the recorded OpenUSD imaging SDK and a PROJ
runtime with TIFF support. Include the Python DLL directory linked by that USD
SDK on Windows. PROJ must have its database and the specified height grids;
`delivery/resources.json` records the resource URLs and hashes. Disable network
fallbacks during evidence collection. The native filter enters the USD imaging
chain before instance propagation/flattening through the application callback.
Stock Hydra and Storm consume that same chain.

Run `run.py --help` for dependency paths. On Windows, start it from a Visual
Studio developer command environment so the native rebuild has its compiler,
headers and libraries. Pass an output directory outside the source tree and
use a new directory for every completed run. The runner executes tests, native
negative cases, stock usdchecker, all three runtimes, exports and analytics.
It writes the complete receipt and delivery outputs, and rejects altered
candidate hashes. The runner's native request context is replaced per job;
source-change propagation is also exercised within the native rendering chain.

## Reporting rules

Execution success, candidate completeness, independent evidence and group
approval are distinct. Every selected demonstration and delivery step is
executed. Remaining work listed in results must be a genuine design decision,
not missing in-scope build work. R24's certified continuous-bound contract is
still a finding even when every test passes.

Public delivery excludes private correspondence, machine paths, attachment ZIPs
and issue/PR backlinks to upstream OpenUSD or proposal repositories. Dataset
permissions and original metadata travel with their evidence. Slide language
explains geospatial/OpenUSD behavior without platform implementation jargon.
No external communication is implied by a successful run.
