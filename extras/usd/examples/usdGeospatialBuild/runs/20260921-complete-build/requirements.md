## Terms
The background above covers the geodesy.
This section fixes the words this proposal uses for its own constructs,
and separates several that mean different things
to the industries this proposal serves.

### Terms this proposal defines

**CRS binding.**
A statement that the coordinates of a prim,
and of its subtree down to the next binding,
are expressed in a named CRS.

**Anchor.**
The prim at which CRS coordinates enter a scene:
its own location is a position in the CRS bound to it.
Content beneath an anchor, up to but excluding any nested anchor,
is positioned relative to it by offsets in ordinary scene units,
with no CRS coordinates of its own.
What constrains the CRS an anchor may be bound to is a design question,
not part of the term.

**Position and offset.**
A *position* is a coordinate in a CRS; an *offset* is a distance
from another prim, in scene units.
An anchor's location is a position. Content beneath it is offsets,
up to but excluding any nested anchor.

**Resolution.**
The computation that takes a composed stage and produces
where each prim is in one output CRS.
Resolution is work a runtime does.

**Target CRS.**
The CRS a resolution produces its output in.
How it is chosen is not part of the term.

**Placement.**
Where an instance sits and how it is oriented within a CRS,
recorded on or below an anchor.
Placement is survey data: it differs from instance to instance,
and it is the record of a real-world decision about a real-world object.

**Conformance.**
A correction for the authoring conventions of a source asset —
its up axis, its units, the orientation it was modelled in.
Conformance is not survey data.
It is identical for every instance of that asset,
and separating it from placement is what keeps the asset reusable.

### Terms that collide

**Base.**
Three different things are called *base* by the industries this proposal serves,
and this proposal uses none of them unqualified.

- A **project's base CRS**, in GIS practice,
  is the CRS a project works in and brings its data into.
  This proposal calls that the **Target CRS**.
- **`BASEGEOGCRS`**, in WKT 2,
  is the geographic CRS a projected or derived CRS is built *from*.
  It sits underneath a CRS definition, not above a project.
- A **project base point**, in surveying practice,
  is a point on the ground, not a CRS.

**Local.**
Two established and incompatible uses.

- In AECO, a **local CRS** is a project or construction grid:
  a flat Cartesian grid agreed for a site,
  with its own origin and its axes along the construction drawings.
  Its relationship to ground distances can include scale distortion.
  This proposal says **project grid**.
- In GIS, **local** often means a topocentric CRS such as
  east-north-up (ENU), whose horizontal axes define a tangent plane.
  Its vertical component retains departure from that plane;
  flattening the surface onto the plane discards that departure.
  This proposal says **topocentric CRS**.

A topocentric CRS and a surface flattened onto its tangent plane
are different representations.

**Localization.**
In ISO/TS 15143-4 and in construction machine control,
the operation of relating a site's working coordinates to a geodetic CRS.
Whether this proposal needs a construct of its own for it
is a design question, decided against requirements 2 and 4.

**Reference epoch and coordinate epoch.**
A dynamic datum's reference epoch is the date to which its defining
parameters refer; a coordinate epoch is the date at which a coordinate
set's positions apply.
Neither is the time sample used to animate content in a scene.

### Functional requirements
<!--
Editing note for this section, for people and for agents alike.

Requirement numbers are identifiers, frozen at the review baseline of the pull
request that introduced this section. Other documents, comments and test
fixtures cite them.

- Do not renumber, and do not insert a requirement between two existing numbers.
- A new requirement takes the next unused number (30 onward) and is placed under
  the group heading it belongs to, even where that breaks the numeric sequence
  within that group.
- A withdrawn requirement keeps its number and its title; its sentence is
  replaced by "Withdrawn." and one line saying why.
- When citing a requirement anywhere outside this file, give number and title
  together: "requirement 21, Never placed by a guess".
- Each requirement is one sentence. The italic text after it is a case from
  practice and carries no requirement of its own. No mechanism belongs in a
  requirement.
- Do not decide an open question in Terms or in a requirement. The table at the
  end of this section names the requirements each open question is decided
  against; the decision is made there, not here.

Renumbering happens once, at merge, with a published old-to-new mapping.
-->

What a solution has to do, stated without reference to any mechanism.
These are what an implementation is checked against,
and the terms on which a design change is argued:
it either serves one of these or it does not.
The questions the discussion has left open are decided the same way;
the table at the end of this section names the requirements each one is decided against.

Each requirement is one sentence.
The italic text that follows it is rationale or a case from practice,
and carries no requirement of its own.

**The CRS itself**

1. **Self-contained definitions.**
   A CRS carried in a scene can be read from the scene alone,
   without a lookup against an external registry.

   *A 2D State Plane zone has a registry code; the compound of that zone,
   its current realization and its vertical datum often has none,
   so an identifier alone cannot name the system the data is actually in,
   and a code that does exist can be missing or differently versioned
   when the scene is next opened.
   This is about the definition. The operation that transforms between
   two CRSs may need resources no scene carries, such as a datum grid;
   requirement 21 says what happens then.*

2. **Defined once, and describing no object.**
   A CRS used in many places is defined once and referred to,
   and its definition says nothing about where any particular object sits,
   which way it faces or how large it is.

   *Once means once within a layer stack, not once for all of USD.
   Restating a definition makes the copies that have drifted
   indistinguishable from the ones that were meant to differ.
   A site calibration and an asset placement are the same arithmetic —
   an origin, a rotation, a scale — so only which of the two a number is
   tells a reader where to change it.
   The test: if the number is needed to read a position in the CRS,
   it belongs to the CRS; if it only puts one object somewhere, it is placement.*

3. **Datum, realization and epoch.**
   The scene can identify the datum realization and its reference epoch,
   and separately the coordinate epoch of a coordinate set,
   wherever applicable, and where none is recorded none is assumed.

   *A national datum such as NAD83(2011) carries its epoch in its definition.
   A global one such as ITRF or WGS 84 does not: its coordinates move
   with the plates, and without a coordinate epoch they are good
   to about 2 m, however precise the survey was.
   The two dates are different quantities: at 2 cm per year,
   coordinates ten years apart differ by 20 cm,
   and the datum's reference epoch alone does not date them.*

4. **A site's own grid is a CRS like any other.**
   A project grid — its origin, orientation and scale relative to a geodetic
   CRS, agreed once for a site — can be the CRS its content is expressed in,
   and content in it needs nothing that content in a national grid does not.

   *Construction works in a ground system: an origin on the site,
   axes along the construction drawings rather than grid north,
   and a scale of one, so a metre in the field is a metre in the system.
   Such a grid typically reads (1000, 1000) at its origin
   so that no coordinate on site is negative.
   Those are properties of the site, shared by every discipline on it.
   Placing that system in the world takes an affine adjustment
   horizontally and an inclined plane vertically; carrying that relation
   with the grid's definition is what lets a reader tell
   grid distances from ground distances.*

**Attaching it to content**

5. **A discoverable CRS.**
   The CRS in which any authored position is expressed
   can be determined from the scene alone.

   *An easting of 481,948 with a northing of 3,767,521
   in metres is valid in all sixty WGS 84 northern UTM zones
   and names a different place on the Earth in each.
   Coordinates whose CRS must be supplied out of band
   are not approximately located. They are not located at all.*

6. **Declared for a subtree, not a prim.**
   A CRS declared once applies to the content beneath it,
   and part of that content can declare a different one.

   *Assembling georeferenced data nests it: an asset in its own CRS,
   inside a dataset in another, inside a scene in a third.
   Each keeps its own native CRS, shared by its descendants
   and different from what is around it.
   Repeating the declaration for every descendant risks a missed update
   among coordinates intended to share the same CRS.*

7. **Composition agnostic**
   CRS declarations and their scope are interpreted on the composed stage,
   following the composition and value-resolution rules of the
   [AOUSD USD Core Specification v1.0.1](https://github.com/aousd/specifications-public/blob/main/core/1.0.1/core_spec.md).

   *Equivalent composed stage data has the same geospatial interpretation,
   regardless of the layers or composition arcs used to produce it.
   Core defines how opinions compose and resolve; this proposal defines
   the CRS interpretation and scope applied to that result.*

8. **Brought-in data keeps its coordinates and its CRS.**
   Data authored in one CRS can be brought into a project working in another,
   and placed there, with its coordinate values and its CRS unchanged.

   *This is the hierarchy a GIS runs on: each asset's own CRS,
   the project's CRS, and the placement of the asset in it.
   A reprojected copy made on import is a second dataset to maintain;
   replacing the original with it loses the native representation.*

**Saying where content is**

9. **Positions, and offsets from them.**
   Content is placed and oriented by a position in a named CRS,
   and the content beneath that position by offsets in scene distances,
   authored and moved as ordinary scene content
   by someone who need know no geodesy.

   *A simulation team georeferences a road scene once, at its origin,
   and dresses it by moving props with the ordinary widget in ordinary
   units; no prop carries a coordinate, and nobody dressing the scene
   touches geodesy. A door is offset from its building's origin the same way.
   The position is where those distances meet the Earth, and what is up
   there is up for all of them: converting the position alone and leaving
   the orientation as authored lays a building on its side at mid-latitudes.
   Place a tower on a site and not one byte of the tower changes;
   move the position and everything beneath it moves with it.*

10. **Offsets along the axes of their position.**
    An offset beneath a position is measured along the axes, and at the
    scale, that position's CRS defines there, and both can be determined
    from the scene without resolving it.

    *A grid's axes differ from true east and north by the grid's convergence
    and scale at that point. Reading grid offsets as east and north
    misplaces content by an amount that grows with the distance
    from the position to the geometry.
    An editing tool asked to move something one metre east
    needs those axes without resolving the whole scene.*

11. **Position or offset, and the scene says which.**
    Whether an authored location is a position in a CRS or an offset
    from its parent can be read from the scene,
    and a position is absolute: nothing above it adds to it.

    *Two positions in one chain are two absolute statements,
    not a base and an offset.
    Authoring a building corner as an independent position,
    where an offset from the building was meant,
    misplaces it by the whole distance between the two positions.
    That is the most common way to misplace a georeferenced scene,
    and it is only detectable if the scene distinguishes the two.*

12. **No angle read as a length.**
    Every coordinate's unit, and the surface its height is measured from,
    are unambiguous, and no reading of the scene takes
    an angular coordinate as a scene distance.

    *A latitude of 48.8584 read as 48 metres passes a numeric plausibility
    check, and so does a height whose reference surface was never stated:
    ellipsoidal and gravity-related heights differ by tens of metres
    over most of the Earth. This requirement is met either by constraining what may be
    recorded as a position, or by carrying enough about each position
    that no reader can mistake its unit; which is a design question
    this section leaves open.*

13. **One axis mapping.**
    Which scene axis carries which CRS component is fixed by this proposal,
    the same for every CRS and every implementation,
    and never taken from the axis order a CRS declares:
    where a CRS has easting, northing and up,
    X carries easting, Y northing, Z up, right-handed.

    *EPSG:3006, a horizontal CRS, declares northing before easting.
    Following that order as X and Y would transpose the scene,
    and a transposed pair is usually still a valid coordinate,
    so inspection does not catch it.
    Left to implementations, each would pick its own.*

14. **Scene conventions stay the scene's.**
    A CRS binding changes neither the scene's units nor its up axis,
    and where a CRS's units or axes differ from the scene's,
    the relation between the two is defined by this proposal once,
    not by each implementation.

    *A State Plane CRS is in US survey feet under a scene declared in metres;
    a Y-up asset from a graphics pipeline sits in a Z-up survey.
    Each is a fixed relation, and an implementation that guessed it
    would place content at a scale or on its side.
    Whose job the correction is — recorded at authoring time,
    as OpenUSD's own guidance for the up axis has it today,
    or applied by the reader — is left open here.*

15. **Placement separate from conformance.**
    Where an instance sits is recorded separately
    from the corrections that adapt its source asset's conventions.

    *Place the same tower fifty times across a site
    and there are fifty survey records, all different,
    and one rotation correcting the asset's up axis, the same every time.
    Recording them together copies that rotation into fifty survey records,
    where it is indistinguishable from something a surveyor measured.*

**Resolving a scene**

16. **One CRS out.**
    Content expressed in any number of CRSs resolves, in one pass, into one CRS;
    a consumer can obtain the result in a CRS of its choosing,
    and a scene can name the CRS it expects to be resolved into.

    *Data aggregated from several CRSs is useful to a runtime only once
    it is normalized into one; which one can differ from one resolve
    to the next, but there is one.
    A pipeline crosses UTM zones 11N and 12N.
    Read in zone 11N without conversion, the 12N half lands
    away from the endpoints it shares on the ground.
    A GIS host has a project CRS of its own and wants a scene
    authored elsewhere in it, without editing the scene;
    a viewer with no opinion needs the scene to say what it expects.
    Whether the consumer's choice is the CRS the scene resolves into,
    or a conversion applied after the scene resolves into the CRS it names,
    is a design question the table below sends to requirements 16, 17, 21 and 23.*

17. **The same answer for every consumer.**
    A world position, a bound, an instance, a physics body and a rendered
    image all come from the same resolution, and none of them needs a renderer.

    *The projection is just the projection: whether its result feeds
    a renderer or an analytics engine does not change it.
    "Does this work without a renderer" is the first question
    a GIS or AECO pipeline asks.
    A building that renders in the right place while a spatial query
    still answers from its unconverted coordinates is two scenes, not one.*

18. **Coordinates back out.**
    Any resolved position can be reported as coordinates in any CRS
    the scene or the consumer names, and the placement of one prim
    relative to another can be asked for in the output CRS.

    *A GIS wants a surveyed corner back as latitude, longitude and height
    whether or not anything in the scene is expressed that way.
    A picking tool asking where two independently placed objects sit
    relative to each other gets the wrong answer by walking the authored
    hierarchy across a position: with one prim at 100 and an independently
    placed child at 20, the hierarchy says 120 and the resolved scene says 20.*

19. **Resolution leaves the scene as authored.**
    Resolving a scene writes nothing into it —
    authored coordinates, CRS definitions and bindings are unchanged —
    and writing a resolved result out is a separate, explicit act
    that records the CRS it was written in and,
    for content that varies over time, how it was sampled.

    *Whatever the runtime does — the conversion, or disregarding the
    transforms above a position — requires writing nothing into the scene.
    Once a placement has been baked into a matrix,
    the intent behind it has collapsed and nothing is left to check against.
    A written-out result that records its CRS resolves again
    to the same place, and a re-resolve does not transform it twice.
    Matrices baked at sampled times and interpolated afterwards
    are not the operation requirement 20 describes,
    and nothing downstream can tell the two apart from the matrices alone.*

20. **Positions between recorded moments.**
    A position recorded as samples over time is interpolated on the recorded
    values, in the CRS they were recorded in,
    and converting the result to another CRS does not change the path.

    *Take samples on the WGS 84 equator, a degree of longitude
    either side of the prime meridian, both at zero ellipsoidal height.
    Interpolated in the recording CRS, the midpoint is on the surface.
    Converted to Earth-centered, Earth-fixed coordinates first
    and interpolated there, the midpoint is about 971 m inside the ellipsoid.
    Telemetry from GPS, AIS or ADS-B arrives as latitude, longitude and
    altitude over time; whether such samples may be recorded as they arrive
    is part of what this section leaves open, and this requirement is
    what that answer costs or keeps.*

21. **Never placed by a guess.**
    A transformation that cannot be computed — no engine, a definition
    that cannot be read or is unsupported, a missing grid,
    a point outside the transformation's domain of validity —
    never places content by a substitute, a result that could only be
    partly computed is a failure and not a partial placement,
    and the failure surfaces where it can be known: in validation
    for what the authored scene reveals, from the engine for what
    only resolution can discover.

    *A substituted matrix is indistinguishable from a computed one.
    A quiet fallback turns a missing grid file into content
    confidently in the wrong place by hundreds of metres.
    For a conversion that shifts by 1,000 m, a two-point batch
    whose second point falls outside the operation's domain and is left in place
    returns a plausible number 1,000 m from the intended one,
    in an array the caller has been told succeeded.
    The definitions and bindings survive the failure,
    so the scene is recoverable in a tool that has what was missing.
    A malformed definition or a binding to nothing is visible when the
    scene is authored; whether a grid covers the point, or an engine
    is present at all, is not, and no authoring API can promise to say so.*

**Staying usable at real sizes**

22. **A CRS suited to the project's size.**
    The scheme supports site, regional and global projects
    without requiring their geometry to be approximated
    by a single tangent plane.

    *Flattening a curved surface onto a tangent plane discards
    its vertical departure: using a spherical radius of 6,371 km,
    the small-distance approximation gives about 8 cm at 1 km
    and about 785 m at 100 km.
    A full 3D topocentric CRS retains that vertical component.
    A construction grid can also have ground-to-grid distortion;
    choosing it does not guarantee undistorted ground distances.*

23. **Detail that does not depend on location.**
    Changing only an asset's geospatial placement does not reduce
    the precision of its asset-relative geometry as authored.

    *At a UTM easting of 481,948 m, adjacent float32 values
    are 3.125 cm apart, so millimetre detail cannot be reliably
    distinguished in an absolute float32 coordinate at that magnitude.
    The same detail can be represented as an asset-relative offset.*

24. **Extent under one position is bounded and stated.**
    Content beneath one position is placed to within a stated distance
    of where placing each of its points would put it,
    and the extent over which that holds is stated.

    *A map is curved and a placement about one point is flat,
    and the difference grows with the square of the distance from the position:
    for a UTM position resolved into geocentric coordinates,
    a point 1 km along the grid lands about 8 cm from where
    converting it directly would put it.
    A stated tolerance implies a maximum extent under one position,
    and content larger than that is split across several.*

**Living alongside everything else**

25. **Additive for consumers that ignore it.**
    A consumer that does not interpret the geospatial information
    reads the same scene it would have read without it.

    *Such a consumer does not get a correctly placed scene.
    It reads the authored coordinates as they stand,
    which for a projected CRS puts content
    hundreds of kilometres from the origin.
    What this requires is only that adding the CRS information
    changed nothing for it.*

26. **Declares its dependency.**
    A scene whose correct placement depends on resolving CRSs says so,
    in a way a consumer can read without traversing the scene,
    and the declaration covers every piece of placed content in it.

    *To a consumer that ignores it, a scene of bare offsets
    near the centre of the planet is indistinguishable from a correct one.
    What the consumer does with the declaration — refuse, defer, warn —
    is its own call. The dependency is a property of the data,
    so an author who omits the declaration has a defect a tool can find.*

27. **Checkable before use.**
    What the scene itself establishes — a position nested beneath another
    position, a binding to no definition, content outside any CRS,
    a dependency declaration missing or left behind by a written-out result —
    can be detected in the authored scene without resolving it.

    *A description that nothing validates against is violated at render time.
    Because resolution writes nothing into the scene,
    the CRS intent is still present as data, and can be checked.
    What the scene does not record cannot be checked from it:
    plausible offsets authored along the wrong axes
    are caught by comparing against survey control, not by inspection.*

28. **A result says what produced it.**
    A resolved result can name the coordinate operation that produced it
    and the accuracy attributed to it.

    *Two datum operations between the same pair of CRSs
    can legitimately place the same point metres apart.
    A stated agreement between two implementations means nothing
    until an adopter can tell an operation choice from numerical drift,
    and a lower-accuracy operation quietly substituted for an unavailable one,
    reporting success, is a failure hidden inside a result.*

29. **Implementable from the text alone.**
    Two implementations built from this proposal without consulting
    its authors, using different transformation engines,
    place the same scene in the same place,
    and each states how closely it agrees, as a distance
    in the output CRS's units at a stated coordinate magnitude.

    *Exact agreement is not achievable: engines differ in grid handling
    and in floating-point operation order, and two engines can differ
    by metres because they have different datum operations available,
    neither in error. A count of matching digits is not comparable
    across CRS families; a distance at a magnitude is.
    The survey control this data derives from is generally good to
    centimetres, so agreement at the millimetre scale sits below the source.*

**What the open questions are decided against**

<!--
Editing note for this table, for people and for agents alike.

Open question numbers are identifiers, frozen at the review baseline of the
pull request that introduced this section, and "open question N" anywhere
outside this file means this table, not the older list under Design
considerations.

- Do not renumber or reorder. A new open question takes the next unused number
  at the bottom of the table.
- A decided question keeps its number and its line; the "Decided against"
  column gains "Decided:" and a pointer to where the decision paragraph lives.
  Do not delete it.
- A decision is recorded in that paragraph and in the design or runtime text it
  changes. It is not recorded by rewording a requirement or a Term.
- When citing an open question anywhere outside this file, give number and a
  short name together: "open question 3, the asset's native CRS".
-->

An answer to any of these is argued as whether it meets the requirements named.

| # | Question | Decided against |
|--:|---|---|
| 1 | May a position be recorded in a geographic CRS, or only in one with length axes? | 5, 8, 12, 20, 22 |
| 2 | How does the scene mark a position: by the binding on the prim, by a marked transform, or by a typed attribute of its own? | 9, 11, 12, 20 |
| 3 | Where is an asset's own native CRS recorded? | 5, 6, 8 |
| 4 | Whose job is the up-axis and unit correction, the writer's or the reader's? | 14, 15 |
| 5 | Does the scene record where CRS coordinates give way to scene offsets, or does the binding determine it? | 11, 19, 27 |
| 6 | Which scene axis carries which CRS component? | 13 |
| 7 | Does localization need a construct of its own? | 2, 4 |
| 8 | Is the consumer's chosen CRS the one the scene resolves into, or a conversion of a result resolved into the CRS the scene names? | 16, 17, 21, 23 |
| 9 | Can a scene resolve into a geographic CRS? | 16, 18, 22 |

Open question 1 asks whether authored positions, including time samples,
can retain geographic coordinates. A geographic origin in a CRS definition
does not settle that question. Reporting resolved positions in geographic
coordinates is covered by requirement 18, Coordinates back out;
a geographic Target CRS is open question 9.
Open questions 1 and 2 both have to satisfy requirement 20,
Positions between recorded moments.
