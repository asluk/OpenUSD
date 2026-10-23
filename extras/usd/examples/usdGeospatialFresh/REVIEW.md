# Fresh geospatial readers and proposal assessment

Geospatial input definitions need to produce the same placement for coordinate
queries, nonvisual analysis and ordinary USD consumers. This example derives new
Python and native C++ readers from a frozen proposal and checks its model/runtime
contracts without introducing undocumented geospatial source fields.

The [README](README.md) and its derived assessment deck lead with proposal
quality, then show working original-data evidence and its practical limits.
They explicitly describe Profiles publication and consumer behavior.

Validation: 19 contract groups pass; 123 provider comparison rows are within
the predeclared 2 mm distance. The two reader bakes of all 163,416 Eiffel
vertices differ by at most 0.016 mm. Original railway, Westminster and climate
workflows retain coordinate/value associations. Native Storm rendering and
actual Omniverse stage readback verify ordinary consumer use.

These are not independent geodetic engines: both readers use PROJ, and the
provider reference tables also derive from PROJ. Unsupported certification and
export coverage are explicit in the README. The run found implementation
defects that existing proposal rules were sufficient to repair; it found no
new blocking specification gap in the exercised contracts.
