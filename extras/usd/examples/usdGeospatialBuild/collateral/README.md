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

## Decisions and evidence to explain

Plan this coverage before implementation. The next README and deck must explain
the whole proposal, not only attractive results or the newest changes. Combine
related cases when it improves the story; do not allocate a slide per requirement.

| Decision | Human question and distinguishing evidence |
|---|---|
| Profiles | Can a consumer detect required processing before loading heavy content? Show one assembly with its payload closed and an accessible declaration. Contrast complete-positive, qualified complete-empty and unknown coverage. Separately show a publisher catching a stale known-none claim after retaining georeferenced content. |
| Authored inputs and computed results | Which facts does an author provide, and what does a reader compute? Show WKT authority, position and physical attitude, with unchanged source geometry and no computed projection properties. |
| Transform order, units and axes | Does the same model retain its physical placement and ordinary USD meaning? Show CRS conversion, anchor adjustments and child-local movement, with a wrong-order or wrong-axis counterexample. |
| WKT identity | What does matching text establish? Show WKT string normalization separately from semantic CRS equivalence, preserving quoted content and exposing classification failures. |
| Native measurements | Do values, locations and observation times stay paired? Show named-dimension association, an independently checked permutation, and useful global analytics. |
| Composition and instances | Do imported and repeated models keep their intended placement? Show an independently bound prototype, instance-local offsets, and an explicitly unsupported inverse. |
| Ordinary USD bake | Can an unaware consumer use the derived copy? Show rendering and reassembly without double placement; distinguish sampled geometry from an unverified continuous space/time guarantee. |

Name **USD Profiles** directly in a main slide title and the corresponding
README section. Introduce it as the existing USD mechanism for declaring required
capabilities and profile conformance, then explain the proposed geospatial use.
Connect the benefit to adoption: tools can discover which processing is needed
before loading the content, and publishers supply an interoperable declaration.

Show the workflow in plain language: the author records a required capability;
the publisher qualifies and maintains coverage through references, variants,
edits and baking; the consumer reads the declaration with payloads closed.
Include one small authored metadata example using the proposal's actual carrier,
plus the resulting consumer interpretation and executed proof. Explain required,
known-none and unknown coverage before introducing their technical labels.

Keep the stale known-none publisher counterexample separate from discovery.
A summary read detects a declaration; it cannot prove its truth. Explain what a
consumer can determine when geospatial support is available or unavailable,
using the pinned contract and actual observations rather than inventing a loader
API. Include unloaded content, retained alternatives and identity controls.
State that geospatial v1 identities are proposed and local plugin registration
does not establish standards adoption or approval ownership.

Review whether a newcomer can identify USD Profiles, understand who authors and
maintains the declaration, and explain what the consumer learns without opening
the payload. A generic dependency table or a mention confined to notes does not
satisfy this delivery goal.

For each selected decision, reuse the question, rule, expected result, observation,
proposal implication and limit structure. Bind it to the new run's exact clause,
requirement and evidence. A failed or unexecuted check is a finding, not a reason
to omit the decision. The compact quality assessment must distinguish:

- Whether model facts and observable outcomes are fully specified for the case.
- What is agreed, proposed, conflicting or undefined.
- What independent counterexamples test, and what shared libraries cannot prove.
- Actual consumer reach, input preservation, failures and uncovered obligations.

Review this coverage semantically in both README and rendered slides. Merely
mentioning each topic or passing hash/count checks does not satisfy it. Retain
the praised deck's coherent explanation and visual clarity; revise the main
sequence to fit the story rather than append a collection of technical slides.

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

The working BUILD_LOOP.md names these active generators. Freeze the updated
plan with the next execution; these delivery directions are not new normative
proposal rules or executed evidence. Keep earlier execution source and receipts
immutable.
