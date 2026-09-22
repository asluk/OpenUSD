# Runtime coordinate resolution

Draft proposed text derived from the functional requirements. This describes the
behavior expected of implementations; it is not an approval claim or a report of
implemented functionality. The companion open-decisions document identifies the
rules still needed before this is a complete implementable contract. No current
experimental property name, projection engine or rendering integration is prescribed.

## CRS definitions and coordinate metadata

Resolution obtains a complete CRS definition from the scene. An external registry
identifier alone is insufficient. A CRS used in multiple places is defined once
and referenced. Its shared definition describes a coordinate system,
including a site's calibrated grid where applicable, independently of the placement,
orientation or dimensions of an object that uses it. Content in a project grid
needs no additional construct that content in a national grid does not need.

A datum's realization and reference epoch are distinct from the coordinate epoch of
a coordinate set. An animation sample time does not supply either epoch. When a
realization or epoch is absent, resolution does not assume one.

## Composed declarations and scope

Resolution reads the composed stage, after USD composition and value resolution.
It interprets CRS declarations and their scope under the AOUSD USD Core
[Specification v1.0.1](https://github.com/aousd/specifications-public/blob/main/core/1.0.1/core_spec.md)'s
composition and value-resolution rules. Equivalent composed declarations and coordinate
values have equivalent geospatial meaning, regardless of the layers or composition
arcs through which they were introduced.

A CRS declaration governs the content in its subtree; content within that subtree
can declare another CRS. The CRS governing an authored position is discoverable
from the scene. Bringing content into a project working in another CRS preserves
the imported content's authored coordinate values and native CRS.

## Positions, offsets and asset conventions

The authored scene distinguishes an absolute position in a CRS from an offset
relative to its parent. Nothing above an absolute position adds to that position.
Content beneath it is placed through offsets along the axes and at the scale its
CRS defines there, until another absolute position establishes a new placement.
The axes and scale can be determined from the authored scene without resolving it.

Resolution keeps coordinate units and height reference surfaces explicit. It never
interprets an angular component as an ordinary scene distance. The proposal's axis
mapping applies consistently across CRSs and implementations; a CRS definition's
own axis order does not override it. Where the components are easting, northing and
up, scene X, Y and Z carry those components in a right-handed mapping.

CRS binding does not change the authored scene's units or up axis. Conversion
between scene conventions and the CRS follows one defined rule. Placement of an
instance is recorded separately from corrections that adapt its source asset's units,
orientation or other conventions. Ordinary edits to offsets remain ordinary scene
authoring operations.

## Shared resolved results and coordinate queries

One resolution evaluates content expressed in potentially many source CRSs into
one output CRS. A scene can name an expected output CRS, and a consumer can request
one. Resolution uses the selected output consistently; it does not hard-code a
particular world CRS as the only valid output.

World positions, bounds, instances, physics and rendering consume the same resolved
placement. Obtaining that placement does not require a renderer. A resolved position
can also be reported in a CRS named by the scene or consumer, and the
placement of one prim relative to another can be queried in the output CRS.

## Time evaluation and authored-scene preservation

Resolution reads the authored scene without writing into it. Coordinates, CRS
definitions and bindings retain their authored values. Computed placement state is
separate from authored scene state.

For a position sampled over time, interpolation evaluates the recorded values in
their recorded CRS before coordinate conversion. Interpolating already converted
endpoints does not replace that evaluation. Reporting or resolving the result in
another CRS preserves the path established by the recorded values.

Writing out resolved results is a separate, explicit operation. Its output records
the CRS used and, for varying content, how time was sampled. Dependency information
on that output reflects what is still required to interpret its placement.

## Failures and operation provenance

An unavailable engine, unreadable or unsupported definition, missing operation
resource, or coordinate outside an operation's domain does not produce substitute
placement. If a transformation is only partly computable, it fails; its partial
output is not reported as valid placement.

Validation reports problems detectable from the authored scene. The transformation
engine reports failures that only coordinate resolution can discover. Failure
preserves the source data and identifies the condition that prevents resolution.

A resolved result can identify the coordinate operation that produced it and the
accuracy attributed to that operation. An unavailable accuracy estimate remains
unknown. Measured numerical disagreement is reported separately from an engine's
accuracy estimate.

## Project scale, local detail and placement extent

Resolution supports site, regional and global projects without requiring their
geometry to be approximated by one tangent plane. Changing an asset's geospatial
placement does not reduce the precision of its authored asset-relative geometry.

When one position places an extended piece of content, the result states both the
distance bound relative to placing its points individually and the extent over
which that bound holds. A placement approximation does not silently claim validity
outside its stated extent.

## Dependency discovery and authored-data validation

Geospatial information remains additive for a consumer that does not interpret it:
that consumer reads the same ordinary scene content it would read without the
geospatial information. This alone does not establish correct geospatial placement.

A scene whose correct placement requires CRS resolution declares that dependency
without requiring a traversal to discover it. The declaration covers every piece
of content whose placement depends on resolution.

Before resolution, validation can inspect the authored conditions the proposal
makes checkable, including nested positions, missing CRS definitions, content
outside CRS scope, and missing or stale dependency declarations. It does not
manufacture geodetic correctness for plausible but unverified source coordinates.

## Agreement between implementations

Independent implementations follow this behavior description rather than treating
one implementation's output as the specification or consulting its authors for
missing rules. Implementations using different transformation engines place the
same scene in the same place and report their agreement as a distance in the output CRS's
units at a stated coordinate magnitude. Their operation provenance accompanies
that comparison so differing operations are distinguishable from numerical drift.

Agreement between consumers or implementations demonstrates consistency.
Correctness evidence uses independently established controls or analytic reference
values, with their applicability and uncertainty stated.
