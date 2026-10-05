# Functional requirements

Authority: the entire unpublished local candidate, SHA-256 `a5444966c41e3a067d7c4db5b2e9a300a08b17fcce377bd6fb24727b390e6904`, based on `39c8fb816a9113b14c8f64b020270724b8357312`. [proposal-source.txt](proposal-source.txt) is the sole proposal authority. These files record derivation and do not add normative choices. Proposed details remain under author review.

## R1: Self-contained definitions

Source line 588.

A CRS carried in a scene can be read from the scene alone, without a lookup against an external registry.

Dependent open contracts: none identified for this statement.

## R2: Defined once, and describing no object

Source line 601.

A complete CRS definition used in many places is authored once and referred to, describes no object-specific placement, orientation or scale, and has its authored WKT as the sole authored authority for the information that WKT determines.

Dependent open contracts: G06.

## R3: Datum, realization and epoch

Source line 618.

The scene can identify the datum realization and any frame reference epoch defined by its CRS, without inferring a coordinate epoch for the coordinates.

Dependent open contracts: none identified for this statement.

## R4: A site's own grid is a CRS like any other

Source line 630.

A project grid — its origin, orientation and scale relative to a geodetic or projected CRS, and, where applicable, its heights relative to a vertical CRS, agreed once for a site — can be the CRS its content is expressed in, and content in it needs nothing that content in a national grid does not.

Dependent open contracts: none identified for this statement.

## R5: A discoverable CRS

Source line 676.

The CRS in which any authored position is expressed can be determined from the scene alone.

Dependent open contracts: G03, G06.

## R6: Declared for a subtree, not a prim

Source line 686.

A CRS declared once applies to the content beneath it, and part of that content can declare a different one.

Dependent open contracts: G03, G06.

## R7: Composition agnostic

Source line 697.

CRS declarations and their scope are interpreted on the composed stage, following the composition and value-resolution rules of the [AOUSD USD Core Specification v1.0.1](https://github.com/aousd/specifications-public/blob/main/core/1.0.1/core_spec.md).

Dependent open contracts: G06, G07.

## R8: Brought-in data keeps its coordinates and its CRS

Source line 707.

Data authored in one CRS can be brought into a project working in another, and given project-specific placement, with its authored coordinate values and CRS unchanged and that placement preserved in any supported requested output CRS.

Dependent open contracts: G03.

## R9: Positions, and offsets from them

Source line 733.

Content is placed by a position, orientation and scale with defined meaning in a named CRS, and the content beneath that placement is authored and moved as ordinary scene offsets in scene distances by someone who need know no geodesy.

Dependent open contracts: G03.

## R10: Offsets along the axes of their position

Source line 751.

Offsets beneath a CRS placement have an orientation and scale discoverable from its authored placement and CRS without resolving into another CRS, and resolution accounts for changes in local axes and scale as well as position.

Dependent open contracts: none identified for this statement.

## R11: Position or offset, and the scene says which

Source line 770.

Whether an authored location is a position in a CRS or an offset from its parent can be read from the scene, and a CRS position does not accumulate ancestor xformOps.

Dependent open contracts: G03.

## R12: No angle read as a length

Source line 787.

Every coordinate's unit, and the surface its height is measured from, are unambiguous, and no reading of the scene takes an angular coordinate as a scene distance.

Dependent open contracts: G04, G06.

## R13: One axis mapping

Source line 801.

The semantic component order of a CRS position is fixed by this proposal rather than by the CRS's declared storage order, with easting, northing and up occupying the first, second and third components respectively, and its representation in a scene frame follows the common convention specified under requirement 14.

Dependent open contracts: G04.

## R14: Scene conventions stay the scene's

Source line 818.

A CRS binding changes neither the scene's units nor its up axis, and where a CRS's units or axes differ from the scene's, the relation between the two is defined by this proposal once, not by each implementation.

Dependent open contracts: G04.

## R15: Placement separate from conformance

Source line 831.

Where an instance sits is recorded separately from the corrections that adapt its source asset's conventions.

Dependent open contracts: G03.

## R16: One CRS out

Source line 843.

Content expressed in any number of CRSs resolves into one output CRS selected by the consumer, with the scene able to name a default for consumers that make no selection.

Dependent open contracts: G03, G04.

## R17: The same answer for every consumer

Source line 863.

A world position, a bound, an instance, a physics body and a rendered image all come from the same resolution, and none of them needs a renderer.

Dependent open contracts: G04.

## R18: Coordinates back out

Source line 876.

Any resolved position can be reported as coordinates in any CRS the scene or the consumer names, and the placement of one prim relative to another can be asked for in the output CRS.

Dependent open contracts: G04, G06.

## R19: Resolution leaves the scene as authored

Source line 891.

Resolving a scene writes nothing into it — authored coordinates, placement values, CRS definitions and bindings are unchanged — and writing a resolved result out is a separate, explicit act that records the CRS it was written in and, for content that varies over time, how it was sampled.

Dependent open contracts: G03, G06, G07.

## R20: Positions between recorded moments

Source line 910.

A position recorded as samples over time is interpolated on the recorded values, in the CRS they were recorded in, and converting the result to another CRS does not change the path.

Dependent open contracts: none identified for this statement.

## R21: Never placed by a guess

Source line 927.

A requested transformation outside the supported scope or one that cannot be computed — no engine, a definition that cannot be read or is unsupported, a missing grid, a point outside the transformation's domain of validity, a requested change of coordinate epoch that the operation does not model — never places content by a substitute, a result that could only be partly computed is a failure and not a partial placement, and the failure surfaces where it can be known: in validation for what the authored scene reveals, from the engine for what only resolution can discover.

Dependent open contracts: G06.

## R22: A CRS suited to the project's size

Source line 976.

The scheme supports site, regional and global projects without requiring their geometry to be approximated by a single tangent plane.

Dependent open contracts: none identified for this statement.

## R23: Detail that does not depend on location

Source line 989.

Changing only an asset's geospatial placement does not reduce the precision of its asset-relative geometry as authored.

Dependent open contracts: none identified for this statement.

## R24: Extent under one position is bounded and stated

Source line 998.

Content beneath one position is placed to within a stated distance of where placing each of its points would put it, and the extent over which that holds is stated.

Dependent open contracts: none identified for this statement.

## R25: Additive for consumers that ignore it

Source line 1013.

A consumer that does not interpret the geospatial information reads the same scene it would have read without it.

Dependent open contracts: G07.

## R26: Declares its dependency

Source line 1023.

A scene whose correct placement depends on resolving CRSs says so, in a way a consumer can read without traversing the scene, and the declaration covers every piece of placed content in it.

Dependent open contracts: G07.

## R27: Checkable before use

Source line 1034.

What the scene itself establishes — a position nested beneath another position, a binding to no definition, content outside any CRS, a dependency declaration missing or left behind by a written-out result — can be detected in the authored scene without resolving it.

Dependent open contracts: G06, G07.

## R28: A result says what produced it

Source line 1049.

A resolved result can name the coordinate operation that produced it and the accuracy attributed to it.

Dependent open contracts: none identified for this statement.

## R29: Implementable from the text alone

Source line 1067.

Two implementations built from this proposal without consulting its authors give the same coordinate interpretation and, using equivalent coordinate operations, place the same scene within a stated agreement distance using a specified distance measure and units at stated output coordinate magnitudes.

Dependent open contracts: none identified for this statement.

## R30: Measurements remain usable as data

Source line 959.

Georeferenced measurements remain accessible to consumers together with their associated positions and times, without requiring renderable geometry or a visualization, and coordinate resolution preserves those associations and measurement values.

Dependent open contracts: G06.

## R31: Same definition, same meaning

Source line 654.

CRS definitions use the proposal's prescribed WKT string normal form, whose specified lexical variants normalize to identical text without loss of represented information or changed coordinate interpretation, while comparisons distinguish serialized-definition identity from CRS equivalence and do not infer different CRS meaning or a necessary transformation solely from different normalized text.

Dependent open contracts: none identified for this statement.
