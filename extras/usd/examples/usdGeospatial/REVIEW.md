# Geospatial support for USD

This draft assesses **whether the [geospatial proposal](https://github.com/Tamrat-B/OpenUSD-proposals/blob/geospatial-crs-proposal/proposals/geospatial_coordinate_reference_systems/README.md)
is clear and complete enough for an agent to implement as written**.

An agent built new Python and C++ implementations from the proposal, then
tested them with real models and datasets. The code, tests and visual examples
provide evidence about the proposal's quality. Any required behavior that
still needs an invented rule is a proposal gap to resolve.

**Current finding:** all 19 test groups pass. No new blocking proposal gaps
were found in the tested workflows, and implementation bugs could be corrected
using the existing text. The tested proposal revision is `4120379`; the link
above follows the live branch. The README records the coverage limits.

The [review map](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-companion/extras/usd/examples/usdGeospatial/REVIEWING.md)
provides a path through the files:

- **Placement:** [Python](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-companion/extras/usd/examples/usdGeospatial/src_py/placement.py) and [C++](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-companion/extras/usd/examples/usdGeospatial/native/placement.cpp), with separate CRS-operation and query modules.
- **Inputs:** [codeless schema](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-companion/extras/usd/examples/usdGeospatial/schema/generatedSchema.usda).
- **Verification:** [contract cases](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-companion/extras/usd/examples/usdGeospatial/tests/run.py) and [reproduction commands](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-companion/extras/usd/examples/usdGeospatial/REPRODUCE.md).

Generated fixtures, reports and deck outputs start collapsed in the diff.
Their generators, reader source and tests remain visible for review.

Examples make that assessment concrete:

- Place the Eiffel Tower and a railway using their coordinate systems, and
  align survey data with a calibrated construction site.
- Query measurement locations and show illustrative global climate data as a
  globe or heatmap.
- Produce ordinary USD geometry for Hydra and Omniverse. Use Profiles to tell
  a consumer that a scene needs geospatial support before loading its contents.

![Authored tower location, before/after ordinary USD adjustment, and measured agreement between the two implementations](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-companion/extras/usd/examples/usdGeospatial/evidence/figures/tower-placement.png?raw=1)

*Illustrative placement: authored georeferencing, then ordinary USD adjustments.
The comparison uses all 163,416 vertices from the actual ordinary USD outputs.
Tower geometry: [SDC PERFORMANCE](https://sketchfab.com/Lambo_SC04),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), with size and placement modified.*

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
