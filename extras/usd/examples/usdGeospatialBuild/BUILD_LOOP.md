# Derive and test geospatial behavior from the proposal

This is a fresh build brief on stock OpenUSD. No previous geospatial model,
runtime, test implementation, generated schema, runner, expected-output file,
README narrative or slide deck is inherited. `inputs.json` pins the starting
proposal and OpenUSD revisions. The historical experiment remains recoverable
on its separate branch and is not a derivation input.

## What the run must establish

Produce a coherent proposal that preserves the required geospatial meaning,
maps necessary information onto appropriate USD representations, specifies the
observable runtime behavior and can be implemented from the text alone.
The original datasets and partner examples exercise that meaning; they do not
determine the schema. Passing tests against a self-invented contract is insufficient.

The starting proposal contains older design sketches as well as the functional
requirements. Retaining those sketches in the clean baseline does not settle
their conflicts or approve their field choices. Read and reconcile them explicitly
against the requirements, OGC concepts and existing USD semantics. Do not silently
inherit them, and do not import the withdrawn replacement model to fix them.

## Inputs and authority

- Terms, numbered functional requirements, their rationale and the numbered open
  questions in the pinned proposal; explicit recorded decisions when available.
- The starting design sections as candidate design to examine, not permission to
  override the functional intent. Separate factual corrections, proposed design
  choices and missing requirements. Preserve requirement/question identities.
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

## Implementation, evidence and reverse review

Derive the implementation and meaningful expected results independently from the
written candidate. Exercise all required behavior and the retained datasets,
including failures, composition, instances, units, epoch changes, animation,
queries, complete geometry, extent/precision, edits, export and re-import.

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

Current authorization is local work only. Nothing is pushed, posted, sent or
written to Outlook. The next complete build and delivery are to be newly derived;
this brief and its input pin are setup, not an executed run.
