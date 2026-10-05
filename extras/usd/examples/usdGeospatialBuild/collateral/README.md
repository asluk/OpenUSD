# Delivery is part of every complete run

The runtime receipt is an input to delivery, not the end of the loop. Repeat
these steps after every requirements/model change and fresh execution. Candidate
changes first require a new pre-implementation freeze and audit; passing old
outputs through this directory does not validate a new model.

1. Commit the frozen candidate and implementation before collecting final
   evidence. Execute `run.py` into a new directory outside the source checkout.
2. Run `python collateral/build_candidate_review.py --run-directory <completed-run>`.
   It verifies executed source hashes, copies the run's evidence and generates
   the canonical package README from that receipt.
3. Run `python collateral/derive.py`. The review body and slide story derive
   from README and records its SHA-256. Edit the canonical narrative generator
   when facts or explanations change; regenerate the derivatives together.
4. Use the installed Presentations skill with its bundled Node/Python runtime.
   Link `collateral/node_modules` to the bundled packages, set
   `RUNTIME_NODE_MODULES`, `RUNTIME_NODE` and `RUNTIME_BIN_DIR`, and run:

   ```text
   node collateral/candidate_slides.mjs <presentations-skill-directory>
        <runtime-python> <workspace-directory> <new-output-name.pptx>
   ```

   The builder creates editable text/tables, validates a private draft, writes
   a separate final PPTX and renders every final slide. Follow the skill's
   operation marker requirement before the first authoring operation. Inspect
   every slide and correct unintended overlap, clipping or misleading claims.
5. Export a PDF using PowerPoint on Windows:

   ```text
   powershell -File collateral/export_pdf.ps1
        -InputDeck <validated-pptx> -OutputPdf <new-pdf>
   ```

   Inspect all exported pages too. Copy the validated files to
   `delivery/geospatial-build.pptx` and `delivery/geospatial-build.pdf`.
6. Run `python collateral/verify.py --presentation-validation <validation-json>
   --visual-review-complete` after performing the visual review. It verifies
   receipt/source/data hashes, README lineage, editable tables, presentation
   structure and public-output boundaries, then writes collateral-manifest.json.
   Automated checks do not substitute for the declared visual review.
7. Commit source/evidence/collateral in meaningful batches. When publication is
   authorized, deliver the fresh tree to the existing fork draft with a normal
   fast-forward update, preserve the draft state, and use
   `gh pr edit --body-file delivery/pr-body.md`. Verify the remote commit/tree,
   README/receipt/deck hashes and PR body before reporting completion.

No completed run leaves a selected demonstration or delivery artifact as a
build next step. Design findings and experimental choices remain explicit;
successful execution is not approval of standard text. Public artifacts have
no private machine paths, correspondence or upstream issue/PR backlinks.
