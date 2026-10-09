# Proposal assessment delivery

The README, review body and slides assess the complete pinned proposal for readers
who may be unfamiliar with geospatial concepts and OpenUSD. Use the October 6
assessment that Tam praised as the explanation and visual baseline. Its evidence
is historical and must not replace the current pinned execution.

Start with the problem and the authored inputs. Explain what each example asks,
the proposed behavior, its observed result, what that establishes about the
proposal and its limits. Explain shape versus Earth location before CRS math.
Define geospatial attitude separately from ordinary USD adjustments. Show actual
working renders and analytics alongside the assessment.

Keep proposed definitions, group adoption, implementation failures, verification
coverage and deferred scope distinct. A prototype shortcut adds no normative
authority. Test totals and reader agreement cannot substitute for completeness
or independent geodetic evidence. Name shared libraries and the actual consumer
output. Omniverse reuses Python placement with stage geometry writeback. Hydra
consumes an ordinary USD bake. There are two placement readers.

Run history and comparisons belong in supporting records. Reject a delivery whose
main narrative is what changed, what was repaired or which run passed more tests.
Each explanation must remain understandable without a prior deck or email.
Specify the inputs and interpretation of each chart, including negative controls,
units and any display-only offsets. Label conceptual illustrations, synthetic
data and recorded native output visibly.

The active derivation is `revised_leans_delivery.py` for frozen evidence and
`standalone_delivery.py` for one shared human narrative. It produces README.md,
REVIEW.md and the slide story. `revised_leans_slides.mjs` renders that story,
checking the README hash first. Slide claims must come from the README and its
linked evidence. Do not maintain a second technical narrative in the slide code.

Review the README for comprehension and coherence, then inspect every final PDF
page against the source and the praised baseline. Literal source binding and
structural checks are necessary but cannot certify reader comprehension. Check
that illustrations do not stand in for numerical proof, limitations remain
visible, and the introduction still explains the complete proposal. Delivery-only
edits do not rerun or rewrite an immutable execution receipt. Keep source and
input hashes verified, and replace current README/story/deck/manifest together.

The existing executed BUILD_LOOP.md is a frozen record and names the older
delivery entry point. Before the next execution, update that active entry point
to these generators and freeze the new plan with that run. Do not rewrite the
previous execution's source or receipt.
