# Draft proposal feedback — local, not posted

These are build stops and suggested requests for wording/decisions, not accepted decisions.

## S01: Decoding a composed prim into an absolute position and its offset descendants

R5 — A discoverable CRS; R6 — Declared for a subtree, not a prim; R8 — Brought-in data keeps its coordinates and its CRS; R9 — Positions, and offsets from them; R11 — Position or offset, and the scene says which; R12 — No angle read as a length; R19 — Resolution leaves the scene as authored; R20 — Positions between recorded moments; R27 — Checkable before use

Needed: An authored carrier and boundary rule, including sampled values, nested anchors and supported CRS coordinate units.

Would otherwise invent: Treating every binding or every translate as a position, or banning geographic recording before open question 1, geographic authored positions, is decided.

Proposed feedback: Decision needed on open question 2, the position carrier, together with open question 5, the position/offset boundary: name the composed property/opinion that identifies a position and how its value and samples are read. Evaluate open question 1, geographic authored positions, against requirement 8, Brought-in data keeps its coordinates and its CRS, and requirement 20, Positions between recorded moments. Keep the boundary runtime-derived and avoid introducing an authored reset as a side effect.

Follow-up: Tamrat and reviewers; geographic workflows from Devin

Open question 1: May a position be recorded in a geographic CRS, or only in one with length axes?
Open question 2: How does the scene mark a position: by the binding on the prim, by a marked transform, or by a typed attribute of its own?
Open question 5: Does the scene record where CRS coordinates give way to scene offsets, or does the binding determine it?

## S02: Importing an asset with a native CRS into a differently georeferenced project

R2 — Defined once, and describing no object; R3 — Datum, realization and epoch; R4 — A site's own grid is a CRS like any other; R5 — A discoverable CRS; R6 — Declared for a subtree, not a prim; R8 — Brought-in data keeps its coordinates and its CRS; R11 — Position or offset, and the scene says which

Needed: The distinction between source CRS identity and placement CRS, plus whether and where project placement acts after conversion without violating the absolute-position rule.

Would otherwise invent: Replacing the source binding or applying an ancestor transform after an absolute position contrary to requirement 11, Position or offset, and the scene says which.

Proposed feedback: For open question 3, the asset's native CRS, specify both declarations and walk one asset-native → project-CRS → placed-instance example. State which authored values remain unchanged and how the result satisfies requirement 11, Position or offset, and the scene says which. For open question 7, localization, identify any information the CRS definition cannot already carry before adding a construct.

Follow-up: Devin starts the native-CRS discussion; Tamrat and Sébastien review

Open question 3: Where is an asset's own native CRS recorded?
Open question 7: Does localization need a construct of its own?

## S03: Turning a CRS position and child offsets into a placed basis

R9 — Positions, and offsets from them; R10 — Offsets along the axes of their position; R12 — No angle read as a length; R13 — One axis mapping; R14 — Scene conventions stay the scene's; R15 — Placement separate from conformance; R22 — A CRS suited to the project's size; R23 — Detail that does not depend on location; R24 — Extent under one position is bounded and stated

Needed: Unit/up-axis correction ownership, axes and scale away from the anchor, numerical error bound and supported extent.

Would otherwise invent: A basis algorithm, automatic asset-metadata correction, or a universal extent/tolerance chosen by NVIDIA.

Proposed feedback: For open question 4, up-axis and unit correction, record the author/reader decision with a metre-stage / survey-foot-CRS example. Open question 6, axis mapping, already has an easting/northing/up rule in requirement 13, One axis mapping; record the decision and remaining component cases explicitly. For requirement 24, Extent under one position is bounded and stated, require each supported placement mode to state its measured distance bound and extent; request practitioner acceptance cases before choosing values.

Follow-up: Sébastien calibration/control points; Tamrat scene conventions; reviewers approve bounds

Open question 4: Whose job is the up-axis and unit correction, the writer's or the reader's?
Open question 6: Which scene axis carries which CRS component?

## S04: Choosing a scene resolution target and publishing a shared result

R16 — One CRS out; R17 — The same answer for every consumer; R18 — Coordinates back out; R21 — Never placed by a guess; R22 — A CRS suited to the project's size; R23 — Detail that does not depend on location

Needed: Consumer-vs-scene target behavior and the supported output coordinate domain.

Would otherwise invent: defaultPrim precedence, mandatory ECEF, a second conversion step, or permission/prohibition for geographic scene resolution.

Proposed feedback: Decide open question 8, consumer target versus conversion, and open question 9, geographic Target CRS, with one multi-CRS scene and named consumer output. Keep geographic coordinate reporting under requirement 18, Coordinates back out, distinct from scene resolution.

Follow-up: Tamrat and reviewers; Devin regional/global cases

Open question 8: Is the consumer's chosen CRS the one the scene resolves into, or a conversion of a result resolved into the CRS the scene names?
Open question 9: Can a scene resolve into a geographic CRS?

## S05: Preflight validation and explicit export/re-resolution

R19 — Resolution leaves the scene as authored; R25 — Additive for consumers that ignore it; R26 — Declares its dependency; R27 — Checkable before use

Needed: A non-traversal dependency signal, what content it covers, and export CRS/sampling representation with a re-resolution rule.

Would otherwise invent: New stage metadata/profile schema or removing bindings on export without a specified dependency rule.

Proposed feedback: Add a design paragraph against requirement 19, Resolution leaves the scene as authored; requirement 26, Declares its dependency; and requirement 27, Checkable before use, naming the dependency declaration and showing both unresolved and exported scenes. Include the mixed-content case and show that the exported result is not transformed twice. Profiles remain a later integration option, not a prerequisite invented by this build.

Follow-up: NVIDIA proposes concrete text after the carrier/target decisions


## S06: Claiming practitioner coverage or independent implementation agreement

R3 — Datum, realization and epoch; R4 — A site's own grid is a CRS like any other; R8 — Brought-in data keeps its coordinates and its CRS; R14 — Scene conventions stay the scene's; R16 — One CRS out; R21 — Never placed by a guess; R22 — A CRS suited to the project's size; R23 — Detail that does not depend on location; R24 — Extent under one position is bounded and stated; R28 — A result says what produced it; R29 — Implementable from the text alone

Needed: Licensed control data and expected output, operation/epoch/grid availability, accepted distance/extent criteria, and a second engine plus independent OV implementation.

Would otherwise invent: Survey truth from this implementation, a second PROJ wrapper as an independent engine, or successful unit tests as full conformance.

Proposed feedback: Keep these as evidence gaps rather than new requirements. Attach dataset provenance, expected output, CRS/epoch, operation, units, coordinate magnitude and acceptance tolerance to each fixture. Compare numerical residuals only after distinguishing operation selection differences.

Follow-up: Sébastien additional calibration; Tamrat Redlands/source WKT; Devin facility → city → region → world; NVIDIA second-engine/OV integration


## S07: Generalizing the relationship inspector into a binding schema implementation

R5 — A discoverable CRS; R6 — Declared for a subtree, not a prim; R7 — Composition agnostic; R21 — Never placed by a guess; R27 — Checkable before use

Needed: Accepted schema spelling and rules for empty, blocked, multiple, forwarded and dangling relationships, collections/instances and override precedence.

Would otherwise invent: Material-binding behavior wholesale or a quiet ancestor fallback when a nearer binding is broken.

Proposed feedback: Record the agreed hierarchical relationship design in the proposal. Describe supported cardinality, unbinding/blocked opinions and invalid targets on composed prims. Core supplies composition and relationship forwarding; the geospatial design must supply its own scope and validity rules.

Follow-up: NVIDIA drafts; Tamrat/schema reviewers decide
