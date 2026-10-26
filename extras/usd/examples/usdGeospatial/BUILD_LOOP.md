# Build-loop contract

The companion is a continuing OpenUSD contribution candidate, with a stable
`aluk/geospatial-companion` branch and `extras/usd/examples/usdGeospatial`
package. Its immediate review purpose is to assess the proposal's readiness
for implementation. Proposal alignment is followed by implementation review
and normal upstream integration; supporting proposal review does not remove
the implementation's path to merge.

Freeze the complete proposal commit/blob and SHA256 before deriving any source.
Read its terms, requirements, fields and normative runtime together. Record the
source contract, distinguishing an absent meaning from a pending review decision.

Generate both full placement readers, codeless schemas, fixture authoring and
acceptance cases in a stock upstream checkout. Previous geospatial source,
fixture logic and generated expectations may not seed the run. Original datasets
and neutral build/render infrastructure may be reused with provenance. Record
that two implementations from the same agent and geodetic engine family do not
constitute independent-author or independent-engine certification.

Before execution, fix coordinate definitions, time/interpolation, ordinary
adjustments, compared operations, physical distance measure and acceptance
distance. Do not choose a tolerance after observing residuals. Source examples
must state every introduced metadata fact, synthetic observation and format
adaptation; a plausible file name or coordinate magnitude is not evidence.

Run original datasets and counterexamples across composition, samples, physical
orientation, Cartesian/geographic charts, ordinary stack ordering, resets,
native/point instances, dimensional associations, Profiles and failures. Use
actual existing APIs to verify native-format and Profiles compatibility: a
lookalike dictionary is insufficient. Compare outputs before rendering. Explicit
bakes must preserve detail during large motion as well as at static origins,
retain unrelated meaning and be reread by a fresh aware and ordinary consumer.

Audit after implementation, before claiming success. Map each implemented
choice back to the frozen model/runtime, especially default time, height/epoch,
implicit intermediate operations, enum/axis adaptation and precision. A code
defect is repaired against existing text. Missing required meaning stops its
dependent portion and yields a concrete proposal issue; do not hide a hack in a
new source field or amend the proposal solely to bless an implementation choice.
Changes to normative authority require fresh generation from that new authority.

Complete local delivery: standalone README leading with proposal quality and
its practical limits; working visuals and explicit Profiles author/publisher/
consumer story; deck and PR description derived from that README. Render and
inspect every slide and the README. Keep continuous-domain certification distinct
from finite vertices; unsupported requests fail visibly. Do not inflate test
counts into a claim of exhaustive conformance.

Require both the expected result and a clean reader process exit. A result file
written before a shutdown crash is not a successful run. For application sinks,
also require the actual consumption/readback result rather than exit status alone.

Checkpoint phases for recovery. Freeze source/input/resource hashes, results and
scope; commit locally. Push, post and send only within the user's authorization.
Preserve any frozen OSRB review snapshot. Public collateral must not backlink
other upstream issues or pull requests.

## Deliver to the continuing companion

Generate each implementation on its own run branch from the recorded stock
OpenUSD base. Use the stable package name from the start. A fresh generation
must not read or patch the previous companion's readers, fixture logic or
generated expected answers. Reuse of original data and neutral infrastructure
follows the provenance rules above.

Preserve each delivered run under an immutable run reference, together with
its proposal revision, tested commit, resource/input hashes, results, README
and deck. Also preserve the current companion tip before replacing it. An
incomplete or failing run stays on its run branch with its findings; it does
not replace the currently delivered evidence. Never move a frozen OSRB review
reference as part of delivery.

After the run and its proposal-quality audit are complete, update the existing
companion branch to the selected run commit. Independent derivations may have
different history, so use a force-push with an explicit lease on the remote
tip that was inspected. Stop if the lease fails; inspect and preserve the new
remote work before retrying. Do not merge an old implementation into the new
run to make the branch update fast-forward.

Keep the existing companion PR open. Update its body from that run's README,
and verify that the body, deck, recorded proposal revision, results and branch
head describe the same run. Public links use the stable branch and package;
immutable references identify particular evidence snapshots. Run IDs belong
in provenance, not in the package, plugin or continuing PR branch name.

If the stock OpenUSD base changes, recheck compatibility and distinguish those
checks from the original fresh derivation. Do not silently relabel old results
as tests against a new base. Keep the diff scoped for upstream review and keep
experimental details and coverage limits explicit.
