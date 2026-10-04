# Proposal-derived build loop

1. Pin the complete shared proposal and normative references. Keep its Git blob, commit and SHA-256. Read background, design, decisions and examples along with every functional requirement.
2. Derive the authored data model and observable runtime behavior. Cite the existing answer first. Identify the smallest missing authored fact or observable meaning, distinguishing design gaps, conflicting text, implementation freedom and unfinished verification.
3. Gate dependent work before implementation. Missing placement fields, coordinate conventions or other required contracts stop that portion. Do not replace the proposal with an experimental model, infer fields from fixtures or stash an implementation workaround in normative prose.
4. Execute independently defined controls. Freeze the derived source before execution. Independently read authored fixtures in headless OpenUSD, native OpenUSD and a live OV stage where relevant. Compare each with an authority-derived expected result, not merely with each other. Record source preservation and expected failures.
5. Audit after implementation. Trace every authored geospatial field and observable interpretation back to the proposal. Check the reverse trace for required results absent from tests. Internal implementation choices must not invent scene facts or normalize unspecified syntax.
6. Deliver the actual run. Derive the README from the receipt, then derive the review body and editable slides from the README. Lead with proposal quality, exact stopped portions and the evidence actually executed. Replace current delivery artifacts together and retain historical evidence in Git history. Publish to the existing fork draft when authorized.

The current default run completes the discovery controls and delivers a specification-stopped receipt with exit code 2. It executes zero placement/projection/Hydra jobs and produces no resolved export. Test or consumer failures are execution failures, not a successful stopped receipt.

The previous full placement experiment is reproducible from its historical source commit. Its private relationship binding and placement fields do not supply the current proposal's missing contracts. The current runner does not allow an experiment flag to bypass readiness with that obsolete candidate.
