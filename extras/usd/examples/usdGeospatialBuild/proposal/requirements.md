# Derived excerpt: no additional authority

Source SHA-256: 28768109389139a56d5c8e5f473446bfa46dd1ab46a48924165b97fb92cb7ae9

### Functional requirements

<!--
Editing note for this section, for people and for agents alike.

Requirement numbers are identifiers, frozen at the review baseline of the pull
request that introduced this section. Other documents, comments and test
fixtures cite them.

- Do not renumber, and do not insert a requirement between two existing numbers.
- A new requirement takes the next unused number and is placed under
  the group heading it belongs to, even where that breaks the numeric sequence
  within that group.
- A withdrawn requirement keeps its number and its title; its sentence is
  replaced by "Withdrawn." and one line saying why.
- When citing a requirement anywhere outside this file, give number and title
  together: "requirement 21, Never placed by a guess".
- Each requirement is one sentence. The italic text after it is a case from
  practice and carries no requirement of its own. Requirements state observable
  outcomes; any required encoding constraint must be explicit and reviewed.
- Do not decide an open question in Terms or in a requirement. The table at the
  end of this section names the requirements each open question is decided
  against; the decision is made there, not here.

Existing identifiers remain unchanged through merge and the follow-up review.
-->

What a solution has to do, including the explicitly proposed WKT encoding
constraints in requirements 2 and 31.
These are what an implementation is checked against,
and the terms on which a design change is argued:
it either serves one of these or it does not.
The questions the discussion has left open are decided the same way;
the table at the end of this section names the requirements each one is decided against.

Each requirement is one sentence.
The italic text that follows it is rationale or a case from practice,
and carries no requirement of its own.

These requirements constrain the geospatial data model and normative runtime
behavior, including resolved queries; they do not prescribe callable APIs or
an implementation architecture. Retained design sketches and prototype code
later in this document do not settle the open questions or establish that
the model is complete. An applied API schema is a USD data-model category,
distinct from a callable programming interface.

#### Initial scope and roadmap

The initial scope retains georeferencing, multi-CRS assembly, CRS-aware model
placement and non-visual measurement workflows, using CRS-only WKT as the
authored authority for each CRS definition. The Colorado
site-grid/State Plane + NAVD88 and France CC49/Lambert-93 examples illustrate
site calibration and assembly. They impose no limit on geographic extent or
dataset size; the city and global analytical cases under requirement 30 remain
part of the functional requirements.

The scene supplies the source CRS definitions and coordinate/placement data;
the consumer selects the output CRS under requirement 16. The transformation
engine chooses applicable geodetic operations and manages their resources,
including datum or height grids, while respecting the authored CRS definitions.
A non-epoch transformation is not excluded merely because it needs a grid or
an operation database. An engine unable to perform the requested transformation
reports failure under requirement 21; its operation choice and accuracy are
observable under requirement 28. This does not require every engine to support
every CRS or prescribe its algorithms, catalog or resource distribution.

Coordinate-epoch representation, interpretation and epoch-dependent resolution
are deferred to roadmap question 15. CRS frame-reference-epoch information,
measurement/observation times and USD time-sampled content retain their distinct
meanings; none supplies an unrecorded coordinate epoch. Epoch-dependent requests
are unsupported in the initial scope, even if an engine could compute them;
silently dropping epoch information or selecting a default epoch does not meet
requirement 21.

Scene-authored selection or pinning of a coordinate operation, model or resource
is separate roadmap work; the initial scope does not introduce USD properties
for it. Engine-selected resources and authored CRS information are not the same
authority. Initial model choices must preserve a path to these controls and to
coordinate epochs. Retained epoch sketches describe roadmap candidates, not
initial conformance obligations. The placement fields and WKT string
normalization profile below are concrete proposals under review, rather than
missing definitions. The complete proposed frame, coordinate-role and declaration contracts are
identified in the question table; proposing a definition and agreeing to it
are distinct steps.

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
   A complete CRS definition used in many places
   is authored once and referred to, describes no object-specific placement,
   orientation or scale, and has its authored WKT as the sole authored authority
   for the information that WKT determines.

   *The unit of sharing is a complete WKT value within a layer stack.
   Its embedded components do not compose independently: a WKT override replaces
   the complete value and can mask a later correction in a weaker layer.
   Extracting information for a query or cache does not create another authored
   authority, and normalization cannot infer which separate definitions were
   intended to change together.
   A site calibration and an asset placement can involve the same arithmetic —
   an origin, a rotation, a scale — so their roles must remain distinguishable.
   A calibration defines the shared coordinate system; a placement puts a
   particular object in it.*

3. **Datum, realization and epoch.**
   The scene can identify the datum realization and any frame reference epoch
   defined by its CRS, without inferring a coordinate epoch for the coordinates.

   *A dynamic reference frame's reference epoch and the coordinate epoch
   of a set expressed in that frame are different quantities.
   An ITRF2020 definition carries a frame reference epoch of 2015; that describes
   the frame, not the epoch of every coordinate set expressed in it.
   An observation timestamp or a USD time code does not by itself establish
   the coordinate epoch either. Representation and interpretation of coordinate
   epochs are roadmap work under question 15, outside the initial scope.*

4. **A site's own grid is a CRS like any other.**
   A project grid — its origin, orientation and scale relative to a geodetic or
   projected CRS, and, where applicable, its heights relative to a vertical CRS,
   agreed once for a site — can be the CRS its content is expressed in,
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
   grid distances from ground distances.
   This is site calibration, sometimes called localization: a derived CRS
   carries its base CRS and the conversion defining the site's grid.
   An engineering CRS with no known relation to an Earth-referenced system
   does not establish an Earth location. Site calibration defines a shared
   coordinate system, not the placement of an individual model.*

<!-- Start a separate list so the new identifier renders as 31. -->

31. **Same definition, same meaning.**
    CRS definitions use the proposal's prescribed WKT string normal form, whose
    specified lexical variants normalize to identical text without loss of
    represented information or changed coordinate interpretation, while
    comparisons distinguish serialized-definition identity from CRS equivalence
    and do not infer different CRS meaning or a necessary transformation solely
    from different normalized text.

    *One writer produces compact WKT and another adds indentation and line breaks;
    OGC WKT also permits keyword case and delimiter variants under its syntax rules.
    These differences need not imply different coordinate definitions.
    A prescribed normal form makes identical serialized definitions comparable,
    while requiring valid WKT from other tools to be normalized before conforming
    authoring. That is an additional interchange constraint, not a restriction OGC
    already imposes. The proposed profile is under review in question 10.
    Changing an axis order, unit or datum can change the meaning;
    normalization cannot erase those differences, or discard names and remarks
    merely to make text equal. Identical text does not establish that a requested
    coordinate operation can be omitted.*

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
   and given project-specific placement, with its authored coordinate values
   and CRS unchanged and that placement preserved in any supported requested
   output CRS.

   *This is the hierarchy a GIS runs on: each asset's own CRS,
   the project's CRS, and the placement of the asset in it.
   A reprojected copy made on import is a second dataset to maintain;
   replacing the original with it loses the native representation.
   In a GIS workflow, native coordinates are converted on demand into the
   project's CRS, then project-specific rotation, scale and translation
   adjust their placement in that CRS.
   The native CRS interprets the coordinates still authored on the asset;
   preserving it is not a requirement to track earlier CRSs or conversions.
   CRS conversion establishes a placement with known coordinate meaning;
   an intentional project adjustment then acts on that placement, separately
   from the rotation or scale required by the conversion itself.
   These instance-specific adjustments are separate from corrections
   to the source asset's conventions, as required by requirement 15.
   If an imagery dataset is shifted to align with survey control in a project,
   asking for its locations in another supported CRS retains that adjusted
   placement; it does not return the unadjusted locations.*

**Saying where content is**

9. **Positions, and offsets from them.**
   Content is placed by a position, orientation and scale with defined meaning
   in a named CRS, and the content beneath that placement is authored and moved
   as ordinary scene offsets in scene distances by someone who need know no geodesy.

   *A simulation team georeferences a road scene once, at its origin,
   and dresses it by moving props with the ordinary widget in ordinary
   units; no prop carries a coordinate, and nobody dressing the scene
   touches geodesy. A door is offset from its building's origin the same way.
   The position is where those distances meet the Earth, and what is up
   there is up for all of them: converting the position alone and leaving
   the orientation as authored lays a building on its side at mid-latitudes.
   A scan records ground distances, while a projected grid may have a
   different distance scale and grid north; converting the model's origin
   alone does not align its geometry with survey control.
   Place a tower on a site and not one byte of the tower changes;
   move the position and everything beneath it moves with it.*

10. **Offsets along the axes of their position.**
    Offsets beneath a CRS placement have an orientation and scale discoverable
    from its authored placement and CRS without resolving into another CRS,
    and resolution accounts for changes in local axes and scale as well as position.

    *A grid's axes differ from true east and north by the grid's convergence
    and scale at that point. Reading grid offsets as east and north
    misplaces content by an amount that grows with the distance
    from the position to the geometry.
    An editing tool asked to move something one metre east
    needs those axes without resolving the whole scene.
    The source placement's meaning is discoverable from the authored scene;
    orientation and scale in another output CRS are derived by resolution.
    Bringing independently CRS-bound survey content into the calibrated site's
    output context must account for the local rotation and scale between those
    CRSs as well as converting its position. This does not establish that one
    local affine approximation suffices over an arbitrary extent; the result
    and approximation guarantees remain question 13.*

11. **Position or offset, and the scene says which.**
    Whether an authored location is a position in a CRS or an offset from its
    parent can be read from the scene, and a CRS position does not accumulate
    ancestor xformOps.

    *Two positions in one chain are two absolute statements,
    not a base and an offset.
    Authoring a building corner as an independent position,
    where an offset from the building was meant,
    misplaces it by the whole distance between the two positions.
    That is the most common way to misplace a georeferenced scene,
    and it is only detectable if the scene distinguishes the two.
    Excluding ancestor xformOps does not discard enclosing CRS context or
    prohibit intentional project placement under requirement 8; the
    coordinate context of the anchor's project adjustment is defined under
    question 3; its ordinary stack applies after CRS placement and resolution.*

12. **No angle read as a length.**
    Every coordinate's unit, and the surface its height is measured from,
    are unambiguous, and no reading of the scene takes
    an angular coordinate as a scene distance.

    *A latitude of 48.8584 read as 48 metres passes a numeric plausibility
    check, and so does a height whose reference surface was never stated:
    ellipsoidal and gravity-related heights differ by tens of metres
    over most of the Earth. Geographic source positions are permitted under
    the decision on question 1, but their angular components are not ordinary
    length-valued translates. The distinct placement properties proposed under
    question 2 preserve this distinction, including for consumers that ignore
    geospatial information.*

13. **One axis mapping.**
    The semantic component order is specified once for each supported CRS
    coordinate system independently of its declared storage order, with
    easting/northing/up in that order where those components apply, and its scene
    representation follows the common convention under requirement 14.

    *EPSG:3006 declares northing before easting. Reading its storage order as
    scene X/Y transposes plausible coordinates. Geographic and geocentric
    positions likewise need explicit semantic tuples; their components are not
    automatically easting/northing/up. Coordinate tuples and their representation
    in stage axes remain distinct.*

14. **Scene conventions stay the scene's.**
    A CRS binding changes neither the scene's units nor its up axis,
    and where a CRS's units or axes differ from the scene's,
    the relation between the two is defined by this proposal once,
    not by each implementation.

    *A State Plane CRS is in US survey feet under a scene declared in metres;
    a Y-up asset from a graphics pipeline sits in a Z-up survey.
    Each is a fixed relation, and an implementation that guessed it
    would place content at a scale or on its side.
    The decision on question 4 assigns authoring of unit and up-axis
    correctives to the writer or assembler, following UsdGeom.*

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
    Content expressed in any number of CRSs resolves into one output CRS
    selected by the consumer, with the scene able to name a default for
    consumers that make no selection.

    *Data aggregated from several CRSs is useful to a runtime only once
    it is normalized into one; which one can differ from one resolve
    to the next, but there is one.
    A pipeline crosses UTM zones 11N and 12N.
    Read in zone 11N without conversion, the 12N half lands
    away from the endpoints it shares on the ground.
    A GIS host has a project CRS of its own and wants a scene
    authored elsewhere in it, without editing the scene;
    a viewer with no opinion needs the scene to say what it expects.
    The consumer's choice determines the output under the decision on question
    8; it is not a conversion of a mandatory project-CRS result.
    This does not prescribe the engine's internal computational path.
    Authored project-specific placement must still be preserved under
    requirement 8; the adjustment's coordinate context is proposed under question 3.*

17. **The same answer for every consumer.**
    World positions, bounds, instances, physics bodies and rendered images use
    the same resolution without requiring a renderer, and a derived ordinary
    USD copy that preserves resolved placement over stated spatial and time
    coverage must be available for viewers performing no geospatial computation.

    *A building that renders in the right place while a spatial query uses its
    unconverted coordinates is two scenes, not one. The same applies to image
    and grid samples. The source remains an input-only scene; library-free
    viewers use an explicit bake into ordinary geometry and transforms instead
    of computed properties stored beside the source inputs. Such a bake must
    retain local detail at geospatial magnitudes under requirement 23 and state
    its approximation coverage under requirement 24; an affine matrix alone is
    insufficient when the conversion is nonlinear over that coverage.*

18. **Coordinates back out.**
    Any resolved position can be reported as coordinates in any CRS
    the scene or the consumer names, and the placement of one prim
    relative to another can be asked for in the output CRS.

    *A GIS wants a surveyed corner back as latitude, longitude and height
    whether or not anything in the scene is expressed that way.
    An analytical product similarly needs its sample locations in the
    receiving GIS's CRS, with the measurements and times associated
    with the same samples.
    A picking tool asking where two independently placed objects sit
    relative to each other gets the wrong answer by walking the authored
    hierarchy across a position: with one prim at 100 and an independently
    placed child at 20, the hierarchy says 120 and the resolved scene says 20.*

19. **Resolution leaves the scene as authored.**
    Resolving a scene writes nothing into it —
    authored coordinates, placement values, CRS definitions and bindings are unchanged —
    and writing a resolved result out is a separate, explicit act
    that records the CRS it was written in and,
    for content that varies over time, how it was sampled.

    *Whatever the runtime does — the conversion, or disregarding the
    transforms above a position — requires writing nothing into the scene.
    Choosing another output CRS recomputes resolved position, orientation and
    scale; it does not replace the source placement with those derived values.
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
    altitude over time; the decision on question 1 permits geographic source
    positions, whose placement encoding is proposed under question 2.
    A climate grid can instead have fixed positions and changing measurements:
    a new measurement time does not by itself move a sample, and this
    requirement does not define interpolation or resampling of its values.*

21. **Never placed by a guess.**
    A requested transformation outside the supported scope or one that
    cannot be computed — no engine, a definition
    that cannot be read or is unsupported, a missing grid,
    a point outside the transformation's domain of validity,
    invalid placement data or a non-finite result, including on a geographic
    path, a requested coordinate-epoch operation outside scope —
    never places content by a substitute, a result that could only be
    partly computed is a failure and not a partial placement,
    and the failure surfaces where it can be known: in validation
    for what the authored scene reveals, from the engine for what
    only resolution can discover.

    *Coordinate-epoch support is outside the initial scope even when an
    installed engine has a motion model. Grid use for a supported non-epoch
    operation is an engine responsibility, not by itself an excluded capability.
    A substituted matrix is indistinguishable from a computed one.
    A quiet fallback turns a missing grid file into content
    confidently in the wrong place by hundreds of metres.
    For a conversion that shifts by 1,000 m, a two-point batch
    whose second point falls outside the operation's domain and is left in place
    returns a plausible number 1,000 m from the intended one,
    in an array the caller has been told succeeded.
    An operation that ignores a requested coordinate-epoch change can likewise
    return plausible coordinates while failing to perform the requested operation.
    The definitions and bindings survive the failure,
    so the scene is recoverable in a tool that has what was missing.
    A malformed definition, an invalidly authored placement field or a
    binding to nothing is visible in the authored scene. Such a field cannot be
    silently ignored to produce a successful placement. Grid coverage and engine
    availability are resolution checks; a non-finite engine result is a failure,
    whether or not the engine raises an exception.*

<!-- Start a separate list so the new identifier renders as 30. -->

30. **Measurements remain usable as data.**
    Georeferenced measurements remain accessible to consumers together with
    their associated positions and times, without requiring renderable geometry
    or a visualization, and coordinate resolution preserves measurement values
    and their associations using explicitly declared coordinate domains and
    dimension ordering rather than incidental array storage order.

    *An image, terrain model or climate grid carries values that a consumer
    can analyze to identify features or trends, not just colors to display.
    Adding or removing a visualization leaves those values and their
    associations intact.
    Derived products can be returned to a GIS with their coordinates,
    values and times still matched.
    Coordinate arrays can declare a different dimension order from the
    measurement variable; matching their flattened indices independently can
    attach a plausible location to the wrong measurement. Dimension declarations
    in the native format can supply that order: this does not require duplicated
    USD metadata. This requires access and preservation, not an analysis
    algorithm, storage format or interpolation of measurement values.*

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
    It reads ordinary local geometry and xformOps with their existing meaning;
    it does not apply the separate CRS placement attributes.
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
    an invalid placement field, or a dependency declaration missing or
    left behind by a written-out result —
    can be detected in the authored scene without computing CRS transformations.

    *A description that nothing validates against is violated at render time.
    Because resolution writes nothing into the scene,
    the CRS intent is still present as data, and can be checked.
    Detecting nested positions does not by itself make nesting invalid:
    question 5 permits direct bindings that establish independent anchors.
    What the scene does not record cannot be checked from it:
    plausible offsets authored along the wrong axes
    are caught by comparing against survey control, not by inspection.*

28. **A result says what produced it.**
    A resolved result can name the coordinate operation that produced it
    and the accuracy attributed to it.

    *Two datum operations between the same pair of CRSs
    can legitimately place the same point metres apart.
    Choosing an operation and managing its grids belongs to the engine;
    identifying that choice and its attributed accuracy belongs to the
    resolved result. Neither requires duplicating the CRS definition or
    authoring the engine's catalog and grid-management policy in USD.
    Operation-attributed accuracy, placement-approximation distance under
    requirement 24 and implementation agreement under requirement 29 are
    distinct quantities.
    A stated agreement between two implementations means nothing
    until an adopter can tell an operation choice from numerical drift,
    and a lower-accuracy operation quietly substituted for an unavailable one,
    reporting success, is a failure hidden inside a result.*

29. **Implementable from the text alone.**
    Two implementations built from this proposal without consulting its authors
    give the same coordinate interpretation and, using equivalent coordinate
    operations, place the same scene within a stated agreement distance using
    a specified distance measure and units at stated output coordinate magnitudes.

    *Exact agreement is not achievable: engines differ in grid handling
    and in floating-point operation order, and two engines can differ
    by metres because they have different datum operations available,
    neither in error. Different operation choices are reported under requirement
    28, rather than hidden inside a promise of identical engine results.
    What makes operations comparable and how agreement is measured remain
    question 13. A count of matching digits is not comparable
    across CRS families; a distance at a magnitude is.
    The survey control this data derives from is generally good to
    centimetres, so agreement at the millimetre scale sits below the source.*

**Illustrative geographic data workflows**

Geographic datasets can supply measurements for analysis as well as optional
visualizations, with derived products returned to a GIS:

- A city-scale satellite image has samples of longitude, latitude, height
  and measurement. A consumer identifies features from the measurement
  values and obtains their locations in a suitable project CRS;
  topocentric/ENU coordinates are one candidate.
- A global climate grid has samples of longitude, latitude, height,
  measurement and time. A consumer identifies trends while retaining the
  association between the measurements, sample locations and recorded times;
  ECEF is one candidate output for the global extent. Positions can stay
  fixed while measurements change.

Both cases need explicit coordinate units and height references, access to
the measurements independently of a visualization, and coordinates back
out in a named CRS. They illustrate requirements 8, 12, 17, 18, 19, 22 and 30
and support the geographic-source intent recorded in the decision on question 1;
the candidate outputs do not decide how native geographic positions are recorded
or whether the Target CRS may be geographic.

**Functional decisions and remaining questions**

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
Decisions on questions 1 and 5 make existing design intent explicit; geographic
source placement was also illustrated in the October 2 discussion. Decisions on
questions 7 and 8 record that discussion. Their rows remain for traceability
rather than reopening those answers. Questions 2, 3, 11, 13 and 14 separate existing
requirements or agreed behavior from the specific choices still to be made.
The proposal remains subject to author review.

| # | Question | Requirements and status |
|--:|---|---|
| 1 | May a model-placement position be recorded in a geographic CRS, or only in one with length axes? | 5, 8, 12, 17, 18, 19, 20, 22, 30; Decided: [geographic source positions](#decision-on-question-1-geographic-source-positions); encoding remains question 2 |
| 2 | What field definitions and conventions record source position and physical model attitude, with computed projection effects kept out of the source schema? | 9, 10, 11, 12, 20; Input-only meaning agreed; [position and attitude candidate](#crs-association-and-model-placement); quaternion versus one heading/pitch/roll tuple remains open, with no `crs:scale` |
| 3 | What coordinate context applies to project adjustments expressed as ordinary USD transforms when the consumer changes the requested output CRS? | 5, 6, 8, 9, 11, 15, 16, 19; Anchor project adjustments and descendant model-local transforms agreed; [complete chart, reset and instance contract](#evaluation) remains a review candidate |
| 4 | Whose job is the up-axis and unit correction, the writer's or the reader's? | 14, 15; Decided: [writer or assembler](#decision-on-question-4-authored-unit-and-up-axis-conformance) |
| 5 | Does the scene record where CRS coordinates give way to scene offsets, or does the binding determine it? | 11, 19, 27; Decided: [direct binding establishes the anchor](#decision-on-question-5-the-position-and-offset-boundary) |
| 6 | What component order and scene-frame representation apply to the supported CRS coordinate systems? | 12, 13, 14; [Component profile and stage mapping](#position-components) supported in feedback; geodetic attitude differs from grid axes; south-oriented axes are a known extension |
| 7 | Does site calibration (localization) need a construct of its own? | 2, 4; Decided: [CRS definition and binding](#decision-on-question-7-site-calibration) |
| 8 | Is the consumer's chosen CRS the one the scene resolves into, or a conversion of a result resolved into the CRS the scene names? | 16, 17, 21, 23; Decided: [consumer-selected output context](#decision-on-question-8-consumer-selected-output-context) |
| 9 | May a geographic CRS be the resolved scene context for geometry, frames and bounds? | 12, 16, 17, 18, 22; Proposed [geographic tuples with associated geocentric scene chart](#queries-scene-charts-and-instances); angular Euclidean scene frames are unsupported |
| 10 | What WKT string normalization profile preserves the represented information, and what comparisons can its normal form establish? | 1, 2, 3, 21, 27, 28, 29, 31; [Proposed lexical profile and comparison contract](#wkt-string-normalization) are under review |
| 11 | How are a measurement dataset's source coordinate properties associated with its CRS, separately from model-placement properties and ordinary geometry offsets? | 2, 5, 6, 7, 8, 12, 18, 19, 21, 27, 30; Proposed [external association and adjustment](#external-measurement-association), retaining native values; epochs remain question 15 |
| 12 | What authored declaration exposes the composed scene's CRS dependency without traversal, including referenced or unloaded content and explicit export? | 7, 19, 25, 26, 27; Proposed [Profiles carrier and conservative maintenance](#dependency-declaration-with-profiles), including unloaded content and export |
| 13 | How is placement-approximation error established for resolved frames, geometry and bounds, and how is cross-engine agreement measured for comparable operations? | 17, 18, 21, 22, 23, 24, 28, 29; Engine responsibility decided; proposed [extent and comparison rules](#extent-and-result-comparison) distinguish pointwise, polygonal and continuous guarantees |
| 14 | How does a time-sampled export record its sampling so a reader can distinguish it from resolution of the original authored samples? | 18, 19, 20, 27, 30; Export preservation decided; proposed [Cartesian representation and existing sampling fields](#explicit-export-and-sampling) |
| 15 | How should a future extension represent and associate coordinate epochs, and what must it specify for epoch-dependent resolution? | 2, 3, 5, 7, 19, 21, 27, 28, 30; Roadmap: [coordinate epochs](#roadmap-question-15-coordinate-epochs), outside the initial scope |

The table separates recorded direction from complete proposed definitions.
Runtime rules have one authoritative location in the detailed design and
[evaluation](#evaluation). Dataset descriptions and distinguishing counterexamples
are informative in [Appendix C](#appendix-c-distinguishing-examples). Pending
review is not missing behavior, and implementation coverage is not group adoption.

#### Decision on question 1: geographic source positions

A model-placement position may be expressed in a geographic CRS, including as
samples over time. This makes explicit the geographic CRS support listed in
the background and the latitude/longitude/height anchor illustrated on October
2. Angular position components are distinct
from the model's ordinary length-valued transforms and offsets. The placement
encoding and component mapping are proposed below for review under questions
2 and 6. Source-space interpolation follows requirement 20. Allowing a geographic source position does
not decide whether geographic coordinates provide the scene context for resolved
geometry, oriented frames or bounds under question 9.

#### Decision on question 2: CRS placement attributes

Source position and physical model attitude are authored inputs distinct from
ordinary USD transforms. Projection convergence, scale and resolved orientation
are runtime results, not additional source properties; no `crs:scale` is proposed.
Intentional object scaling uses ordinary USD xformOps. This input-only meaning
has author support. The candidate below stores attitude as `quatd` with a
normative heading/pitch/roll presentation. The alternative under discussion
stores one heading/pitch/roll tuple. Its exact field definition and sample
evaluation would need an explicit contract before replacing the candidate;
converting angles to a quaternion does not by itself make Core interpolate a
`double3` as an orientation. The stored type remains an alignment question.

#### Decision on question 5: the position and offset boundary

A direct CRS binding on model content establishes an anchor on the composed prim.
Its placement is expressed in that CRS; descendants inherit the coordinate
context while using ordinary scene offsets, until another direct binding
establishes a new anchor. An inherited CRS does not make each child translation
a new absolute CRS position. This is the boundary already defined by the Anchor and Position
and offset terms and binding inheritance; no second
boundary declaration is required. The placement table defines authored position and attitude. Question 3 specifies the
coordinate context of project adjustments, which use ordinary USD transforms
after CRS placement and resolution.

#### Decision on question 11: coordinate domains and property roles

Composed subtree scope and independent source CRSs are already established by
requirements 6 and 7. Model vertices are local offsets, not absolute coordinates.
The proposed [external measurement association](#external-measurement-association)
identifies a dataset, selected field and coordinate domain without introducing
a general measurement-storage schema. Its Xformable carrier preserves native
values and permits the project adjustments already required by requirement 8.
The association, dimensionality and consistency rules are proposed for review.

#### Decision on question 14: explicit export

Requirements 19 and 30 already specify the export obligations: an explicit
resolved export records its output CRS and, for time-varying content, how it was
sampled, while preserving measurement values and their position/time associations.
The output is authored data in that recorded CRS; rereading it must not repeat
the original source-to-output placement conversion or depend on a private
"already resolved" flag. Ordinary composition flattening alone does not perform
this export. The placement and measurement-coordinate encodings follow questions
2 and 11, and dependency-declaration maintenance follows question 12. The follow-up also specifies an explicit export origin to preserve
precision, the extent/error obligations and what the sampling record establishes. The
[proposed export rules](#explicit-export-and-sampling) use existing sample keys
and `timeCodesPerSecond` to record the actual exported schedule, and distinguish
it from a guarantee about the original between-sample trajectory. They do not
introduce an authored interpolation-mode field absent from USD Core.

#### Decision on question 4: authored unit and up-axis conformance

The writer or scene assembler authors the correctives needed to bring model
content into the destination stage's units and up axis, following UsdGeom.
Correctives may be authored at the assembly boundary without rewriting the
source asset. Readers honor those authored transforms; geospatial resolution
does not automatically repair asset unit or up-axis mismatches. This conformance
is separate from instance placement under requirement 15 and from interpreting
the units declared by a CRS or performing a requested coordinate conversion.

#### Decision on question 3: working context and placement order

An independently bound dataset retains its source CRS and coordinates. Author
feedback supports the enclosing-binding/fallback working context, model-origin
pivot, and the distinction between the anchor's post-placement project
adjustments and descendants' ordinary model-local transforms. Descendant
offsets must remain reusable when an asset is referenced into another project.
Changing the requested output CRS preserves the adjusted physical placement,
rather than reusing raw adjustment numbers in different output axes. The exact
chart, complete stack, reset and instance conventions remain the follow-up
candidate in [evaluation](#evaluation).

#### Decision on question 7: site calibration

Site calibration, also called localization, relates a site's local grid to a
known Earth-referenced base CRS. A derived CRS records the base and the supported
conversion defining that grid, including horizontal and vertical calibration
where applicable. The shared CRS definition and its binding carry this meaning
under requirements 2 and 4; no separate USD localization construct is needed.
An unlocated engineering CRS alone does not supply this relationship. Individual
asset placement remains separate under requirements 8 and 15. This answers the
functional question discussed on October 2; it does not require an engine to
support every calibration method or remove requirement 21's resource checks.

#### Decision on question 8: consumer-selected output context

The consumer's requested CRS is the resolved output context; an
enclosing project binding does not require first producing a result in its CRS.
This defines the output's meaning, not an engine's internal computational path.
Authored project-specific placement must still be preserved under requirement 8;
its adjustment coordinate context is proposed under question 3. The October 2 discussion
confirmed this as the intended behavior rather than a new output mode to design.
Question 9 proposes the associated Cartesian scene chart for geographic output.

#### Decision on question 13: operation and resource responsibility

The transformation engine selects applicable geodetic operations between the
authored source and selected output CRSs and manages the required grids or other
resources. The initial USD model need not mirror its operation catalog, download
policy or grid interpolation algorithms. CRS definitions remain self-contained
under requirement 1 and authoritative under requirement 2; that does not make
computing every transformation independent of external resources.

This records the responsibility agreed on October 2, not a guarantee that every
engine can perform every request or produces identical results from different
valid operations. Requirements 17, 21 and 28 already require shared placement for
visual and non-visual consumers, detectable failure without a substituted or
partial placement, and operation/accuracy reporting. Those behaviors are not
additional open decisions. Question 13 retains the method for establishing the
approximation distance and valid extent under requirement 24, and the agreement
measure for comparable operations under requirement 29; operation accuracy alone
does not measure placement approximation or supply a requested tolerance.
Comparison must distinguish different valid operations from numerical drift and
specify a distance measure for geographic coordinate outputs. Scene-authored
operation/resource controls and coordinate epochs remain roadmap work.

#### Roadmap question 15: coordinate epochs

Coordinate-epoch representation, interpretation and epoch-dependent resolution
are outside the initial scope, not foreclosed by it. A future extension
must answer two distinct parts:

- What is the authoritative epoch representation, which coordinate values does
  it describe, and how does the association behave through composition, reuse
  and export?
- What operation/motion-model information, resources and applicability are
  needed for a requested epoch-dependent result, and what must failure and
  result reporting establish?

COORDINATEMETADATA is an existing OGC representation to evaluate in that work,
not a requirement to introduce a separate USD epoch property. If distinct
metadata values embed the same CRS, complete-WKT sharing can repeat that CRS and
an epoch-only override can mask a later CRS correction in a weaker layer. The
future model must expose that tradeoff and respect the authored-authority rule
in requirement 2. It must keep coordinate epochs distinct from frame reference
epochs, observation times and USD time codes. The initial model must preserve a
path to adding this support; no future carrier or model is chosen here.
