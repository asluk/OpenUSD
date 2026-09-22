# Build and deliver a complete geospatial experiment

Every ordinary run follows functional requirements → proposed runtime behavior →
explicit candidate choices → implementation → complete demonstrations/tests →
README → PR summary/slides → delivery verification. A passing component suite
alone does not complete this process.

## Inputs and re-derivation

The portable default input is `inputs/requirements.json`. `--proposal-repo` reads
committed Terms, requirements, open questions and explicit accepted decision
paragraphs from a clean proposal checkout. Old runtime/schema/converter code is
excluded; raw datasets and workflows remain authorized fixture scope.

`proposal/runtime-behavior.md` is the canonical proposed normative description.
`proposal/runtime-experiments.md` supplies executable, unaccepted alternatives;
`proposal/runtime-open-decisions.md` records the actual design questions.
`derivation.json` traces all requirements and pins reviewed prose and input hashes.
Changed requirements or prose require semantic re-derivation, not a hash-only update.

When a genuine ambiguity remains, implement labeled alternatives where feasible,
test consequences and counterexamples, and finish independent work. Do not classify
unfinished implementation, demonstrations, tests or documentation as a design stop.
Dataset assumptions remain explicit, and missing certified controls never become
invented accuracy claims.

## Complete run

Use Python 3.12 with the pinned requirements, dataset and delivery packages:

```sh
python -m pip install -r requirements.txt -r requirements-datasets.txt -r requirements-delivery.txt
```

Configure these environment variables for the machine:

| Variable | Purpose |
|---|---|
| `GEO_USD_SDK` | Stock OpenUSD SDK containing `pxrConfig.cmake`, headers and imaging libraries |
| `GEO_CMAKE` | CMake executable, or use CMake on PATH |
| `GEO_NINJA` | Optional Ninja executable |
| `GEO_VCVARS` | Optional Windows compiler-environment batch file |
| `GEO_HYDRA_LIBRARY_PATH` | Additional runtime DLL/library directories needed by the chosen SDK |
| `GEO_KIT_EXECUTABLE` | Installed Kit with omni.usd, USDRT and the bundled NumPy extension |

The native target uses stock imaging libraries only. It is freshly compiled inside
each complete run. The report hashes the binary and source; native module and Kit
extension audits reject retired geospatial implementations. Storm uses an invisible
Windows OpenGL context in this build. Other platforms require a working native
context integration before claiming the same complete rendering scope.

Populate an external cache with `datasets.py` and supply the locally authorized
original GeoJSON, scalar field and partner attachment. Raw data and partner scripts
are never committed or executed. Then run:

```sh
python run.py --output /external/new-run --dataset-root /external/cache --aeco-zip /external/attachment.zip
```

Use a new output directory each time. The runner executes all eight workflow
families, both position carriers, native and point instances, composition and edit
propagation, export/re-resolution, extent/precision, negative cases, independent
coordinate arithmetic, native Hydra/Storm and actual Kit/Fabric readback. It records
all versions, metrics, dataset hashes and private demonstration artifacts.

Exit 0 means `COMPLETE_WITH_OPEN_DESIGN_QUESTIONS`: all conditional workflows pass,
no checks skip, and the native target was built in that run. This does not approve
the design or certify survey accuracy. Exit 1 reports failures or incomplete scope.
Exit 2 is reserved for stale derivation or explicitly partial diagnostics.
`--components-only` is available for targeted investigation; it cannot be delivered
as a complete run. Missing private inputs must remain visible instead of being
quietly replaced or omitted from a delivery claim.

## README, review summary and slides

After inspecting the evidence, author the README around actual workflows,
mechanisms, results and design decisions. Keep qualifications beside the claims.
The previous implementation's narrative is not a template to copy. Include all
completed work; no in-scope build activity belongs in a “next demonstration” section.

Commit implementation, contracts, tests and delivery code before the final run.
Then execute a fresh complete run and prepare its immutable checkpoint:

```sh
python run.py --output /external/final-run --dataset-root /external/cache --aeco-zip /external/attachment.zip --deliver --checkpoint-id complete-run-id
```

`figures.py` uses the freshly executed demonstration files and verifies their
hashes. The site image is a direct Storm render. The railway tile visualization
labels its affine display approximation. Figure hashes bind all images to the run.
Preparation refreshes only marked measured blocks in the authored README, preserves
an immutable `runs/<id>` record, and derives `docs/PR_BODY.md` and `docs/slides.json`.
It also preserves the exact normative prose, candidate contract and open questions.

`build_deck.mjs` builds editable slides from that README-derived content using the
artifact-tool presentation library. Each slide records the README hash in its
notes. Follow the presentation skill's operation-start, finalization and visual
inspection procedure, export to a new PPTX filename and render the PDF. Inspect
every slide for layout, legibility and agreement with the README. Then seal:

```sh
python deliver.py seal-slides --pptx /external/new-deck.pptx --pdf /external/new-deck.pdf
python deliver.py verify
```

Source, report, figures, README, PR body or slide drift fails verification. A changed
source requires another complete run. Later changes to slide layout alone require
regeneration, visual inspection and resealing; do not rerun unrelated numerical
tests solely for slide formatting.

## Publish the standing fork draft

The separately invoked publish command requires the verified package and a clean
implementation revision in its run record. It commits derived delivery artifacts,
pushes the owner's delivery branch and updates the existing draft against the
owner's `dev` branch. It never pushes the upstream repository.

```sh
python deliver.py publish
```

Verify remote head and PR body against local results after publication. The README,
review summary and deck must describe the final implementation, not conversational
history. Do not cite other issues or pull requests at this phase. Public guards scan
text, native source, PPTX relationships and PDF text for backlinks, private paths,
communication URLs and raw dataset artifacts. Keep original attachments and
machine configuration outside Git.

Subsequent changes to functional requirements repeat this entire loop. The only
remaining review items in a delivered run are actual design choices, input
interpretation and externally supplied controls—not deferred coding or delivery work.
