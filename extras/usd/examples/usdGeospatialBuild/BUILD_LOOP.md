# Build, verify and deliver a geospatial checkpoint

The implementation, tests and delivery code in this directory form one experiment.
The README is the public explanation of the latest checkpoint. This procedure is
the operator's guide. Generated runs and partner attachments stay outside the checkout.

## Input and runtime derivation

The default input is `inputs/requirements.json`, a self-contained snapshot of the
Terms and functional requirements, including the numbered open questions. The
snapshot preserves the source revision and allowed-text hash. The reader verifies
the hash and re-extracts the requirements instead of trusting cached JSON fields.

To use a newer input, pass `--proposal-repo` with a clean checkout. The runner
reads committed text only. If the allowed text changes, the existing derivation
becomes stale and its tests do not count as current evidence. Re-derive the contract
and update `derivation.json`; do not change only the hash.

The supplied schema direction and experimental implementation policies are explicit
in `derivation.json`. Historical prototype implementations are excluded from the
derivation inputs. Requirements and questions retain their identifiers and titles.

## Run and test

Use Python 3.12 and the pinned packages in `requirements.txt`. Tests use stock USD
and PROJ without the old geospatial plugin or a renderer. Record implementation
changes in a commit before a delivery run so the evidence identifies the exact code.

```sh
python -m pip install -r requirements.txt
python run.py --output /absolute/path/outside-checkout/run-001
```

Use a fresh output directory for every run. `--aeco-zip` optionally supplies the
existing AECO example. Its two tests skip when it is absent; no attachment scripts
execute. The importer reads four explicitly named files and records provenance.
The public checkpoint contains the supplemental results and hash, not the attachment.

Exit 1 means an execution/test failure. Exit 2 means the cycle completed with
design/evidence gaps or a stale derivation. The current implementation has no
full-conformance success path. Its numeric probes and binding tests do not establish
complete scene placement, an independent second engine or OV implementation agreement.

## Prepare delivery

Delivery is a phase of the run:

```sh
python run.py --output /absolute/path/outside-checkout/run-002 --deliver --checkpoint-id 20260921-first
```

Or prepare from a completed run whose source is still unchanged:

```sh
python deliver.py prepare --run /absolute/path/outside-checkout/run-002 --checkpoint-id 20260921-first
```

Preparation requires a current derivation and a successful test invocation. It
checks every source hash, preserves an immutable `runs/<id>` record, updates the
canonical README and derives `docs/PR_BODY.md` and `docs/slides.json` from that README.
The public report omits machine paths and private access information. A changed
README, edited PR summary, stale slides or modified evidence fails verification.

Do not cite issues or pull requests in delivered text, source comments, commit
messages or slides during this phase. Refer to the bundled requirements or a
commit-pinned source file. The publication guard checks text, PPTX XML/relationships
and extracted PDF text, including encoded URLs. It also rejects private machine
paths, communication links and unapproved dataset files.

## Slides from the README

`build_deck.mjs` consumes only `docs/slides.json`. Slide titles and claims come from
README sections, and every slide's notes record the README hash. The sampled-path
chart is an editable native chart using the README's measured values.

The authoring environment needs Node.js and `@oai/artifact-tool` 2.8.59. Use the
provided runtime where available, or the declared package dependency. An explicit
`ARTIFACT_TOOL_MODULE` path can select the runtime's module without changing it.

```sh
node build_deck.mjs . /absolute/path/outside-checkout/deck-build
```

This writes a candidate PPTX and rendered slide previews. Validate the deck package
and layout, render and inspect every slide, then export the validated PPTX to PDF.
The current checkpoint uses PowerPoint's PDF export. Preserve the candidate and
validation records outside the checkout. No slide content is edited independently.

After verification, attach the final artifacts to the prepared checkpoint:

```sh
python -m pip install -r requirements-delivery.txt
python deliver.py seal-slides --pptx /path/to/validated.pptx --pdf /path/to/validated.pdf
python deliver.py verify
```

The seal checks slide counts, README provenance and artifact hashes. Visual review
remains an explicit part of delivery; a hash check cannot establish layout quality.

## Publish to the standing draft

```sh
python deliver.py publish
```

The publisher verifies the package, checks that `origin` is `asluk/OpenUSD`, checks
the delivery branch and refuses unrelated working-tree changes. It commits the
checkpoint, pushes that branch and creates or updates one draft review against the
fork's `dev` branch. The README-derived body is supplied through a file. The returned
receipt identifies the published revision and review URL.

Publishing is explicit. An ordinary build or preparation does not push, update a
review, send messages or modify the source proposal. The publisher does not target
the upstream repository and never marks a draft ready or merges it.

## Next increments

The runtime contract and build stops identify the next useful decisions. Position
storage and boundary rules unlock anchor decoding; native/project CRS semantics
unlock imported-asset placement. Unit/up-axis and output decisions, practitioner
controls and distance/extent criteria then support full placement, explicit export,
validation and independent OpenUSD/OV implementations.
