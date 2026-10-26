# Geospatial support for USD

This draft assesses **whether the [geospatial proposal](https://github.com/Tamrat-B/OpenUSD-proposals/blob/4120379fa12473b54a8f8e11999a1cefa5443614/proposals/geospatial_coordinate_reference_systems/README.md)
is clear and complete enough for an agent to implement as written**.

An agent built new Python and C++ implementations from the proposal, then
tested them with real models and datasets. The code, tests and visual examples
provide evidence about the proposal's quality. Any required behavior that
still needs an invented rule is a proposal gap to resolve.

**Current finding:** all 19 test groups pass. No new blocking proposal gaps
were found in the tested workflows, and implementation bugs could be corrected
using the existing text. The README records the coverage limits.

Examples make that assessment concrete:

- Place the Eiffel Tower and a railway using their coordinate systems, and
  align survey data with a calibrated construction site.
- Query measurement locations and show illustrative global climate data as a
  globe or heatmap.
- Produce ordinary USD geometry for Hydra and Omniverse. Use Profiles to tell
  a consumer that a scene needs geospatial support before loading its contents.

![Eiffel Tower geometry rendered in Hydra after geospatial placement](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-companion/extras/usd/examples/usdGeospatial/evidence/tower-storm.png?raw=1)

*The tower's placement and scale are illustrative; the ground is a presentation grid.*

Start with the [illustrated README](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-companion/extras/usd/examples/usdGeospatial/README.md)
or [slide deck](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-companion/extras/usd/examples/usdGeospatial/delivery/output/Geospatial-USD-proposal-assessment.pdf).

Both implementations and the reference coordinates use PROJ, so these checks
do not independently verify the geodetic calculations or prove that every
possible workflow is specified completely.

**Please review the proposal first.** This companion helps make its behavior
and remaining questions concrete. The implementation remains a candidate for
OpenUSD; detailed code review follows alignment on the data model and behavior.
This PR continues across build runs, with its branch updated to the latest
delivered implementation and evidence.
