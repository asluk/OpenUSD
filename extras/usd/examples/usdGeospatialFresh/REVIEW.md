# Geospatial in USD: placement and analysis examples

This draft puts the [proposed geospatial support for USD](https://github.com/Tamrat-B/OpenUSD-proposals/blob/4120379fa12473b54a8f8e11999a1cefa5443614/proposals/geospatial_coordinate_reference_systems/README.md)
to work on real models and datasets. The same location information supports
both visualization and analysis:

- Place the Eiffel Tower and a railway using their coordinate systems, and
  align survey data with a calibrated construction site.
- Query measurement locations and show illustrative global climate data as a
  globe or heatmap.
- Produce ordinary USD geometry for Hydra and Omniverse. Use Profiles to tell
  a consumer that a scene needs geospatial support before loading its contents.

![Eiffel Tower geometry rendered in Hydra after geospatial placement](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-fresh-20261023/extras/usd/examples/usdGeospatialFresh/evidence/tower-storm.png?raw=1)

*The tower's placement and scale are illustrative; the ground is a presentation grid.*

Start with the [illustrated README](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-fresh-20261023/extras/usd/examples/usdGeospatialFresh/README.md)
or [slide deck](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-fresh-20261023/extras/usd/examples/usdGeospatialFresh/delivery/output/Geospatial-USD-proposal-assessment.pdf).

The Python and C++ implementations were built anew from the proposal. All 19
test groups pass, and the tested workflows needed no additional proposal rules
or scene properties. Both implementations and the reference coordinates use
PROJ, so these checks do not independently verify the geodetic calculations.
The README explains the remaining coverage limits.

**Please review the proposal first.** This companion helps make its behavior
and remaining questions concrete. Detailed implementation code review comes
after agreement on the proposal; this draft is not requesting merge.
