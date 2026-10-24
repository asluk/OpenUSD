# Geospatial proposal evidence: fresh readers and working workflows

**Draft companion for proposal review.** Please review the proposal's
requirements, authored data model and normative runtime behavior first.
Implementation code review and upstream integration follow agreement on that
contract. This draft does not request merge or acceptance of these readers as a
production implementation.

The experiment asks whether an implementer can derive the tested behavior from
the [frozen proposal text](https://github.com/Tamrat-B/OpenUSD-proposals/blob/4120379fa12473b54a8f8e11999a1cefa5443614/proposals/geospatial_coordinate_reference_systems/README.md).
New Python and native C++ readers were generated from that revision, rather
than patched from the previous geospatial implementations. Their callable
interfaces are implementation details, not proposed standard APIs.

Start with the [standalone README](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-fresh-20261023/extras/usd/examples/usdGeospatialFresh/README.md)
and [12-slide assessment PDF](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-fresh-20261023/extras/usd/examples/usdGeospatialFresh/delivery/output/Geospatial-USD-proposal-assessment.pdf).
The README is the narrative source for the assessment and this description.

- All 19 contract groups pass. The run found implementation defects that could
  be corrected against existing proposal rules, with no new blocking
  specification gap in the exercised workflows or undocumented source fields.
- Original France, Colorado, Eiffel, railway, calibrated-site and measurement
  examples exercise placement and nonvisual queries. Native Hydra/Storm and an
  Omniverse stage consume ordinary geometry produced by the two readers.
- Height fallback and computed source-height reporting are exercised, including
  warning and missing-grid failure. Native Profiles reads the dependency
  declaration with zero payloads loaded; slide 10 explains its adoption role.

The [reverse audit](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-fresh-20261023/extras/usd/examples/usdGeospatialFresh/audit/source-contract.md)
separates proposal meaning, implementation defects, deferred capabilities and
unverified coverage. Feedback exposing a missing or contradictory proposal rule
is useful now. Successful finite-point tests are not exhaustive conformance or
continuous-domain certification. The same agent wrote both readers, and both
readers and the provider tables use PROJ; this is not independent geodetic
validation.

The diff adds only the isolated example package to its recorded stock OpenUSD
base, `5bc38c9`. It does not modify core USD libraries. Reproduction instructions,
input provenance, coverage limits and editable slides are linked from the README.
