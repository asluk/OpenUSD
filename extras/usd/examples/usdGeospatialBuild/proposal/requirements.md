# Derivation from the shared geospatial proposal

Authority: full proposal snapshot at `39c8fb816a9113b14c8f64b020270724b8357312`, retained verbatim in [proposal-source.txt](proposal-source.txt). This derivation records defined behavior and missing contracts. It is not an alternative specification.

## Functional requirements

1. **Self-contained definitions**
A CRS carried in a scene can be read from the scene alone, without a lookup against an external registry.

Source: proposal-source.txt:570.

2. **Defined once, and describing no object**
A complete CRS definition used in many places is authored once and referred to, describes no object-specific placement, orientation or scale, and has its authored WKT as the sole authored authority for the information that WKT determines.

Source: proposal-source.txt:583.

3. **Datum, realization and epoch**
The scene can identify the datum realization and any frame reference epoch defined by its CRS, without inferring a coordinate epoch for the coordinates.

Source: proposal-source.txt:600.

4. **A site's own grid is a CRS like any other**
A project grid — its origin, orientation and scale relative to a geodetic or projected CRS, and, where applicable, its heights relative to a vertical CRS, agreed once for a site — can be the CRS its content is expressed in, and content in it needs nothing that content in a national grid does not.

Source: proposal-source.txt:612.

5. **A discoverable CRS**
The CRS in which any authored position is expressed can be determined from the scene alone.

Source: proposal-source.txt:656.

6. **Declared for a subtree, not a prim**
A CRS declared once applies to the content beneath it, and part of that content can declare a different one.

Source: proposal-source.txt:666.

7. **Composition agnostic**
CRS declarations and their scope are interpreted on the composed stage, following the composition and value-resolution rules of the [AOUSD USD Core Specification v1.0.1](https://github.com/aousd/specifications-public/blob/main/core/1.0.1/core_spec.md).

Source: proposal-source.txt:677.

8. **Brought-in data keeps its coordinates and its CRS**
Data authored in one CRS can be brought into a project working in another, and given project-specific placement, with its authored coordinate values and CRS unchanged and that placement preserved in any supported requested output CRS.

Source: proposal-source.txt:687.

9. **Positions, and offsets from them**
Content is placed by a position, orientation and scale with defined meaning in a named CRS, and the content beneath that placement is authored and moved as ordinary scene offsets in scene distances by someone who need know no geodesy.

Source: proposal-source.txt:713.

10. **Offsets along the axes of their position**
Offsets beneath a CRS placement have an orientation and scale discoverable from its authored placement and CRS without resolving into another CRS, and resolution accounts for changes in local axes and scale as well as position.

Source: proposal-source.txt:731.

11. **Position or offset, and the scene says which**
Whether an authored location is a position in a CRS or an offset from its parent can be read from the scene, and a CRS position does not accumulate ancestor xformOps.

Source: proposal-source.txt:750.

12. **No angle read as a length**
Every coordinate's unit, and the surface its height is measured from, are unambiguous, and no reading of the scene takes an angular coordinate as a scene distance.

Source: proposal-source.txt:767.

13. **One axis mapping**
Which scene axis carries which CRS component is fixed by this proposal, the same for every CRS and every implementation, and never taken from the axis order a CRS declares: where a CRS has easting, northing and up, X carries easting, Y northing, Z up, right-handed.

Source: proposal-source.txt:781.

14. **Scene conventions stay the scene's**
A CRS binding changes neither the scene's units nor its up axis, and where a CRS's units or axes differ from the scene's, the relation between the two is defined by this proposal once, not by each implementation.

Source: proposal-source.txt:794.

15. **Placement separate from conformance**
Where an instance sits is recorded separately from the corrections that adapt its source asset's conventions.

Source: proposal-source.txt:807.

16. **One CRS out**
Content expressed in any number of CRSs resolves into one output CRS selected by the consumer, with the scene able to name a default for consumers that make no selection.

Source: proposal-source.txt:819.

17. **The same answer for every consumer**
A world position, a bound, an instance, a physics body and a rendered image all come from the same resolution, and none of them needs a renderer.

Source: proposal-source.txt:839.

18. **Coordinates back out**
Any resolved position can be reported as coordinates in any CRS the scene or the consumer names, and the placement of one prim relative to another can be asked for in the output CRS.

Source: proposal-source.txt:852.

19. **Resolution leaves the scene as authored**
Resolving a scene writes nothing into it — authored coordinates, placement values, CRS definitions and bindings are unchanged — and writing a resolved result out is a separate, explicit act that records the CRS it was written in and, for content that varies over time, how it was sampled.

Source: proposal-source.txt:867.

20. **Positions between recorded moments**
A position recorded as samples over time is interpolated on the recorded values, in the CRS they were recorded in, and converting the result to another CRS does not change the path.

Source: proposal-source.txt:886.

21. **Never placed by a guess**
A requested transformation outside the supported scope or one that cannot be computed — no engine, a definition that cannot be read or is unsupported, a missing grid, a point outside the transformation's domain of validity, a requested change of coordinate epoch that the operation does not model — never places content by a substitute, a result that could only be partly computed is a failure and not a partial placement, and the failure surfaces where it can be known: in validation for what the authored scene reveals, from the engine for what only resolution can discover.

Source: proposal-source.txt:903.

22. **A CRS suited to the project's size**
The scheme supports site, regional and global projects without requiring their geometry to be approximated by a single tangent plane.

Source: proposal-source.txt:952.

23. **Detail that does not depend on location**
Changing only an asset's geospatial placement does not reduce the precision of its asset-relative geometry as authored.

Source: proposal-source.txt:965.

24. **Extent under one position is bounded and stated**
Content beneath one position is placed to within a stated distance of where placing each of its points would put it, and the extent over which that holds is stated.

Source: proposal-source.txt:974.

25. **Additive for consumers that ignore it**
A consumer that does not interpret the geospatial information reads the same scene it would have read without it.

Source: proposal-source.txt:989.

26. **Declares its dependency**
A scene whose correct placement depends on resolving CRSs says so, in a way a consumer can read without traversing the scene, and the declaration covers every piece of placed content in it.

Source: proposal-source.txt:999.

27. **Checkable before use**
What the scene itself establishes — a position nested beneath another position, a binding to no definition, content outside any CRS, a dependency declaration missing or left behind by a written-out result — can be detected in the authored scene without resolving it.

Source: proposal-source.txt:1010.

28. **A result says what produced it**
A resolved result can name the coordinate operation that produced it and the accuracy attributed to it.

Source: proposal-source.txt:1025.

29. **Implementable from the text alone**
Two implementations built from this proposal without consulting its authors give the same coordinate interpretation and, using equivalent coordinate operations, place the same scene within a stated agreement distance in the output CRS's units at a stated coordinate magnitude.

Source: proposal-source.txt:1043.

30. **Measurements remain usable as data**
Georeferenced measurements remain accessible to consumers together with their associated positions and times, without requiring renderable geometry or a visualization, and coordinate resolution preserves those associations and measurement values.

Source: proposal-source.txt:935.

31. **Same definition, same meaning**
CRS definitions are authored in the proposal's prescribed WKT normal form, so OGC-permitted syntactic variants of the same definition normalize to identical text without losing represented information or changing coordinate interpretation or resolved coordinate results.

Source: proposal-source.txt:636.

## Scope

Coordinate epochs remain roadmap work. Frame reference epochs belong to the CRS definition. Engine-managed non-epoch transformation resources remain supported where an operation can succeed. Colorado and France examples illustrate initial value without restricting city-scale or global measurement workflows. No requirement is added or removed by this derivation.
