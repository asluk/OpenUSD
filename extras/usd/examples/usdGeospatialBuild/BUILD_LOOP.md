# Derive and test geospatial behavior from the proposal

This is a fresh build brief on stock OpenUSD. No previous geospatial model,
runtime, test implementation, generated schema, runner, expected-output file,
README narrative or slide deck is inherited. `inputs.json` pins the starting
proposal and OpenUSD revisions. The historical experiment remains recoverable
on its separate branch and is not a derivation input.

**Current phase: complete derivation, execution and delivery authorized October 2.**
The committed input pin and pre-implementation candidate are the run authority.
See PLAN.md for the full execution and reporting criteria.

## What the run must establish

Produce a coherent proposal that preserves the required geospatial meaning,
maps necessary information onto appropriate USD representations, specifies the
observable runtime behavior and can be implemented from the text alone.
The original datasets and partner examples exercise that meaning; they do not
determine the schema. Passing tests against a self-invented contract is insufficient.

The Git starting point records text, not acceptance of every design choice in it.
First separate retained requirements, obsolete prototype material to remove, and
genuine open design questions, using the user's current direction and recorded
decisions. Do not wait for a remote removal commit to honor that direction locally.
Remove callable APIs, implementation/plugin prescriptions and automatic transform
reset side effects from the proposal. Do not convert removed code into normative
rules or count its removal as a need for new schema fields.

Assess the remaining data-model candidates against the requirements, OGC concepts
and existing USD semantics. Do not inherit them merely because they were in the
baseline, and do not import the withdrawn replacement model to fix them.

The proposal specifies data models and normative runtime behaviors, including
resolved-query meaning, sufficient context, evaluation, results and failures.
Programming-language APIs and library/plugin interfaces are derived implementation
choices outside the proposal. An applied API schema is an authored USD schema
category, not a mandate for a callable interface. A gap in query semantics is a
specification gap; a missing function signature is not.

## Inputs and authority

- Terms, numbered functional requirements, their rationale and the numbered open
  questions in the pinned proposal; explicit recorded decisions when available.
- The remaining design sections as candidates to examine after removing obsolete
  prototype material, not permission to override functional intent or current
user direction. Separate cleanup, factual corrections, proposed design choices
  and missing requirements. Preserve functional requirement/question identities.
- OGC's coordinate reference and coordinate-metadata model, including the
  proposal's existing COORDINATEMETADATA approach, and AOUSD Core composition.
  Use primary sources and state any ambiguity rather than inventing geodesy.
- Existing USD data/schema/transform semantics, with stock USD examples to test
  representation choices. WKT content, coordinate association and transforms
  must each have a justified representation.
- Original railway GeoJSON and provider data, site/tower data, measurement inputs,
  and supplied Colorado/France calibration and epoch samples with their source
  metadata, stated assumptions and original bytes. Retain the authorized city,
  global, placement, composition, instancing, editing and export workflow scope.

Keep local paths and private attachments outside public delivery. Rebuild dataset
adapters, synthetic fixtures and expectations from the source information. Do not
carry forward old fixture flags, assumed epochs, per-record geometry, private
export markers or old comparison results as authority. Historical defect reports
may challenge an independently derived candidate afterwards; they cannot provide
missing semantics or make their previous solutions mandatory.

## Derivation and gap resolution

1. Establish the necessary facts and authored intent: identity, ownership, scope,
   units, temporal meaning, reuse and dependencies. Separate consumer requests
   and derived results from source data. Examine the requirements together for
   incompatible readings; a complete list of properties is not a coherent model.
2. Map those facts to existing OGC/USD concepts. Before adding a property, show
   the information that would otherwise be lost and a concrete counterexample
   demonstrating that existing representations are insufficient. Minimize
   duplication without hiding meaning. Do not force every kind of coordinate
   data through an oriented modelling-frame abstraction.
3. Derive the proposed normative runtime description in the proposal: composed
   scope, positions/offsets/project placement, units/axes, epochs and time,
   operations, result capabilities, precision/bounds, failures, edits and export.
   Define the observable meaning; internal implementation algorithms remain free
   where that meaning is preserved.
4. For every gap, record the conflicting interpretations, affected requirements,
   minimal justified correction or labeled alternatives, implications and a
   counterexample that would distinguish a correct implementation from a shortcut.
   Implement feasible alternatives where group decisions remain open. Do not
   invent an accepted decision or treat unfinished implementation as a question
   for the group.

Freeze the justified model/runtime candidate before deriving its implementation.
If implementation exposes another gap, record it and return to the semantic
argument. Keep proposal changes separately reviewable from implementation fixes.
The fact that code already behaves a certain way never justifies a specification
change. A revised candidate invalidates affected derivations and evidence.

## Proposal readiness before implementation

Review the connected decisions in dependency order: coordinate ownership,
definition identity/normalization and binding; placement and coordinate frames;
resolved results over space/time and export; dependency declaration and
conformance. Candidate answers about absolute placement or Cartesian anchors do
not close their gaps until their representation and evaluation compose with the
rest of the model. Supporting geographic measurements does not by itself decide
the representation of geographic modelling anchors.

Begin with an inventory of all in-scope CRS-related metadata, using the required
CRS families, workflows and referenced standards. Solving coordinate epoch alone
does not complete this inventory. Distinguish CRS-defining information and common
WKT attributes from coordinate-set metadata, operation/resource information,
dataset metadata, consumer requests and resolved-result evidence. For each, state
ownership, authoritative encoding, scope/composition, absence/conflicts, and what
interprets or preserves it through resolution, validation, normalization and
export. Existing WKT representations must be evaluated before creating separate
USD attributes; justify and reconcile any duplicated or factored representation.
Metadata is not automatically an inert annotation or a new generic property bag.
The inventory is not a plan to mirror WKT elements into USD properties. Retain WKT
as the authored authority for information it already represents, and evaluate
association/scope around complete WKT objects first, including COORDINATEMETADATA.
Specify the accepted WKT object forms for each carrier. Conceptually different
owners do not alone justify splitting an existing encoding into new properties;
parsed values/caches remain derived state. Demonstrate a functional limitation or
an explicit reviewed tradeoff before choosing a factored authored representation.
The local expansion of requirement 2, Defined once, and describing no object,
makes authored WKT the sole authored authority for information it determines.
New independently editable copies are not a conforming shortcut. Check accepted
WKT object forms and their coordinate associations, including shared contexts,
different coordinate epochs for one underlying CRS, and native measurement data
alongside Cartesian geometry. Expose conflicts with definition reuse explicitly;
do not silently relax a requirement or add fields to make a sample pass.

Whole authored WKT and independent USD composition of its internal elements
cannot both be promised. Assess the chosen boundary using written controls before
implementation: two complete contexts with identical embedded CRS and different
epochs can drift; a stronger whole-value epoch edit can mask a later weaker CRS
correction; and both cases may pass local WKT validation. Distinguish correcting
metadata from propagating coordinates, complete-context identity from embedded-CRS
comparison, and consistency guaranteed by the scene from author intent a validator
cannot infer. Normalization, token equality and authoring tools do not restore
component composition. State the real sharing/editing limits in the proposal;
do not conceal them in an appendix or invent a synchronization field to pass a
test. Carry these controls into later implementation evidence and reverse audit,
including metadata-only differences and many distinct epochs where required.

For each decision, record the functional requirement and evidence of agreement,
necessary facts and owners, justified authored representation, normative runtime
rule, a written distinguishing example with independently reasoned expectations,
and any remaining alternatives. Specify types, units, variability, absence,
defaults, inheritance/composition and invalid-data behavior where applicable.
Keep authored information, consumer requests, resolved results and internal
implementation state distinct. Choosing a field name or copying an old prototype
is not a derivation.

Integrate the candidate into the proposal's data model, normative runtime and
conformance sections. Informative Appendix C supplies illustrative datasets and
workflows; it cannot be the only source of a normative requirement. Private notes
and generated downstream documents cannot supply missing behavior. Rewrite or
remove contradictory legacy examples, while preserving functional requirement and
question identifiers and explicitly recording any proposed change of intent.

Before pinning a candidate for implementation, account for all known in-scope
semantic gaps. Each is answered for that candidate or has separately complete,
labeled alternatives. A reader must be able to determine the meaning and expected
behavior/failure of the written examples from proposal text and referenced
standards. Required behavior cannot be omitted by labeling it unsupported. Check
both requirements-to-rules/examples coverage and authored-fields/observable-rules
back to justified needs. Preserve implementation freedom where observable
guarantees agree. Record group approval separately from candidate completeness.
This gate does not claim that implementation cannot reveal new defects.

## Implementation, evidence and reverse review

Derive the implementation and meaningful expected results independently from the
written candidate. Exercise all required behavior and the retained datasets,
including failures, composition, instances, units, epoch changes, animation,
queries, complete geometry, extent/precision, edits, export and re-import.

For requirement 31, Same definition, same meaning, include permitted WKT
representation variants with otherwise identical scene/request context, and
controls whose axes, units or datum actually differ. The evidence must distinguish
syntax validity, normalized-text identity, coordinate interpretation and resolved
results. Derive normalization from the specified profile, including consistent
output across implementations, idempotence, precision and metadata preservation.
A normalizer must not silently repair invalid input or erase meaningful changes
to make text match. Token identity or a normalization round trip alone cannot
establish all these properties. The current local candidate stores normalized WKT
in the authored token; validation checks syntax and equality with its prescribed
normalization without rewriting source values. Mandatory normalized storage is
an additional authored-data restriction whose interoperability tradeoff must be
reviewed explicitly; it is not a restriction required by OGC or by USD tokens.
These are future evidence obligations, not tests executed during proposal review.

Check both directions: every requirement/rule has appropriate evidence, and
every observable implementation choice follows a justified model/runtime rule.
Repeat the representation-necessity review after implementation, independently
of whether documentation and code agree. Specifically attempt these shortcuts:

- Fixture names, layout, sidecars or preparation code supply information absent
  from the authored model.
- Unsupported but valid in-scope content is rejected and counted as conformance.
- A finite vertex/sample comparison is presented as a bound over surfaces or time.
- Input preservation masks lost precision, meaning or associations in outputs.
- Hidden defaults, operation substitutions or cache dependencies change results.
- Export works only because the same implementation recognizes private state.
- Two consumers sharing one resolver are presented as independent implementations
  or independent geodetic evidence.
- A workaround is copied into proposal text so that a drift check passes.

Use independent analytic controls or partner expectations with their actual
assumptions. Agreement has to identify comparable operations/resources/epochs
and a meaningful error metric. Neither an unverified scientific assumption nor
an implementation's own expected output becomes ground truth.

The full program includes an OpenUSD implementation, an OV-library implementation
from the same text and a usdchecker-discoverable authored-content validator.
Headless and native Hydra consumer demonstrations remain required evidence;
they do not by themselves establish the second runtime or independent-engine
agreement. Account for all authorized scope explicitly. A snapshot transfer is
not end-to-end runtime integration.

## Delivery and status

After semantic closure of the exercised candidates, implementation review and
complete execution, author a README from the actual results, then derive the
review body and slide deck. Explain workflows, how the design represents them,
meaningful comparisons and genuine remaining group decisions. Slides address
geospatial/OpenUSD reviewers without platform-specific implementation jargon.

Keep execution success, coherent candidate semantics, independent evidence and
group approval distinct. A run is incomplete while required work is omitted or
a known semantic gap is hidden. Historical passing counts and artifacts are not
current evidence. Public delivery must contain no issue/PR backlinks to the
upstream OpenUSD or proposal repositories.

The complete run is authorized for delivery to the existing fork draft.
No external message or Outlook write is part of this run. Results and collateral
are newly derived and their completed state is recorded by the run report.
