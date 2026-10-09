# USD geospatial proposal assessment

USD holds a model's shape. A coordinate reference system (CRS) explains a position on Earth.

The revised local proposal addresses the seven red-team concerns without changing the 31 functional requirements or adding geospatial attributes. Fresh tests support its instance and bake semantics, make unsupported requests explicit, and preserve the existing workflows. No additional undefined rule was found in the inspected paths. This is a scoped finding, not proof of exhaustive completeness.

The model records inputs only: WKT, geographic/model placement and external-data
associations. Resolved positions and frames remain transient. The full local draft
is the execution authority. The terms/requirements baseline cannot substitute for
its data model and normative runtime rules.

## What the red-team review changed

| Workflow | Proposed rule | Fresh evidence |
|---|---|---|
| Repeated models | Each instance offset keeps its instancer-local meaning, including independently georeferenced prototypes. | Coincident bound/unbound models agree for translation, rotation and scale. Singular required inverses fail. |
| Reusing a bake | The retained Cartesian context follows ordinary USD parent transforms until an authored reset. | A +100 m parent and an explicit reset agree with ordinary UsdGeom in both readers. |
| Rotation over time | A half-turn needs an authored intermediate pose for interior-time resolution. | Equivalent +180/-180 endpoints both fail on ambiguity. Exact and held samples remain defined. |
| Geographic measurements | A nonidentity ordinary adjustment requires an explicitly enclosing Cartesian project frame. | Geographic coordinates remain available. Missing context fails and supplied context produces the expected +1 m adjustment. |
| Physical 3D distance | Use the datum's associated Earth-centred Cartesian coordinates. Report surface distance separately. | At 400 km ellipsoidal height, the control distinguishes 118.299 km physical separation from 111.319 km surface distance. |
| Dependency summaries | Existing Profiles metadata distinguishes complete-empty, positive and unknown coverage. | Both readers distinguish the cases. Separate publisher controls detect a stale complete-empty retained-variant summary. |
| Sampled bakes | A between-sample preservation claim identifies the reader interpolation setting and its covered bound. | The existing source-first trajectory control remains stable. No general continuous trajectory certificate is claimed. |

These restrictions remain local leans for group review. The geographic adjustment
restriction affects an adjustment convention, not global data or larger-scale
analytical workflows. Coordinate epochs and scene-authored transformation-resource
controls remain deferred, with future extension paths preserved.

## Concrete reuse checks

A USD point instancer stores positions in its local model frame. With a shared
origin at longitude/latitude zero, [10, 0, 0] moves both prototypes ten metres east.
Both fresh readers recover Earth-centred displacement [0, 10, 0]. The older
candidate gave the independently bound prototype an upward displacement. The
new rule specifies full finite frame transport. A required unavailable inverse fails.

![Recorded instance displacement control](delivery/revised-leans-20261008/instance-offset.png)

A resolved ordinary USD bake retains its Cartesian context when referenced.
An ordinary +100 m parent affects both queries and ordinary viewers. An authored
reset at an Xformable boundary suppresses that parent. A typed CRS definition
alone does not reset transforms.

| Assembly intent | Ordinary USD X (m) | Fresh Python/C++ X (m) |
|---|---|---|
| Inherit +100 m parent | 6,378,237 | 6,378,237 |
| Authored ordinary reset | 6,378,137 | 6,378,137 |

These synthetic controls assess semantics. They do not establish surveyed locations.
Stable entrypoints and metadata above payloads follow the
[NVIDIA asset-structuring guidance](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html)
without prescribing a fixed hierarchy or redefining Core composition.

## Working workflows in this run

| Path or check | Fresh evidence |
|---|---|
| Contract tests | 113 passed |
| Existing distinguishing controls | 65 passed |
| Coordinates per Python/C++ comparison path | 213,243 |
| Maximum Python/C++ physical difference | 3.39e-08 m |
| Ordinary geometry/data exports | 11 |
| Native Hydra/Storm images | 2 |
| Omniverse geometry writeback | 177,872 vertices and 48 edit/recovery checks |
| Prior output comparisons | 117, with no unexpected regression |
| Prior focused conformance controls | 14 passed |

![Native Storm image of the resolved Eiffel model](delivery/revised-leans-20261008/tower.png)

![Native Storm image of resolved terrain](delivery/revised-leans-20261008/terrain.png)

These fresh native Hydra/Storm images read ordinary USD geometry baked from C++
results. They demonstrate the visualization path. They do not establish surveyed
placement, surface-normal accuracy, a geospatial Hydra filter or Omniverse rendering.
Python and C++ share PROJ and external-format decoding. Omniverse stage geometry
writeback reuses Python and verifies readback and edit/failure/recovery. It is not
a third placement implementation.

### France: CC49 to Lambert-93

| Component (m) | Python | C++ |
|---|---|---|
| East | 661101.109417 | 661101.109417 |
| North | 6857834.256536 | 6857834.256536 |
| Height | 37.298000 | 37.298000 |

### Colorado: State Plane to site grid

| Component (US survey ft) | Python | C++ |
|---|---|---|
| East | 3108871.450101 | 3108871.450101 |
| North | 1206317.469403 | 1206317.469403 |
| Height | 5484.677949 | 5484.677949 |

## Analytical data beyond rendering

The synthetic global field retains 154 observations over two times, including
explicit height. Geographic and Earth-centred queries preserve values and native
array associations. A separate dimension-permutation control checks the shared
decoder against named dimensions. The original railway keeps its horizontal
workflow without inventing height semantics.

![Heatmap of newly recorded synthetic observations](delivery/revised-leans-20261008/global-temperature.png)

At 400 km ellipsoidal height, a one-degree equatorial separation measures
118.299 km in physical 3D, compared with
111.319 km along the ellipsoid surface. The draft names these
as distinct metrics and also reports angular components and height residuals.
A coordinate without height does not acquire an invented zero height.

## Implementation and verification limits

| Topic | Finding |
|---|---|
| Normal transport | Confirmed prototype defect: one large projected face differs by 1.24 degrees across its domain. Centroid sampling has no justified domain/error bound. The source already requires a faithful derivative or covered approximation. |
| Near-half-turn numerics | The proposed failure rule is clear. The prototype's 64-epsilon guard lacks a demonstrated rotational uncertainty bound and a quantified native diagnostic. |
| WKT quoted text | Confirmed shared prototype defect: a valid CRS name containing COORDINATEMETADATA is mistaken for a deferred epoch wrapper. Capability detection must use WKT structure, not quoted text. |
| Publisher coverage | Retained-variant and unloaded-payload controls pass, including detection of a stale empty claim. This is not a production validator for every composition or variant combination. |
| Consumer coverage | Python and C++ share PROJ and external-data decoding. Omniverse reuses Python. General material/primvar baking, physics and nonlinear continuous space/time certificates remain unverified or visibly unsupported. |

Six earlier defect counterexamples still pass after repair. Normal transport remains
the unresolved earlier defect. This run also found a native regex-stack failure on
longer WKT. The second execution uses a linear scanner and passes a 20,000-character
quoted-name regression. The failed first run remains preserved.

## Choices for group review

| Topic | Disposition |
|---|---|
| Instance authoring | Review finite transport in the instancer frame, including the inverse requirement. It preserves Core input meaning. |
| Geographic adjustments | Review the explicit Cartesian project context for absolute-domain adjustments. Geographic and global analytical access remain in scope. |
| Publication contract | Review the proposed publishing-profile identity and maintenance obligations in existing Profiles metadata. Registration and group adoption remain pending. |
| Orientation and comparison | Review the intermediate-pose policy and physical 3D versus horizontal surface metrics. HPR and detailed WKT string normalization remain proposed. |

The proposal states local outcomes and failures. Group review can accept or revise
them before treating the detailed model as adopted. The build loop now checks
semantics, publisher coverage and ordinary USD reuse beyond a field-name whitelist.

## Local review deck

[Slide deck](delivery/revised-leans-20261008/geospatial-build.pptx) and
[PDF](delivery/revised-leans-20261008/geospatial-build.pdf) present these same findings.

## Authority and evidence

Proposal commit: 7b5b34b7282305135f672663a3cffb0f94342ecc.

Execution source commit: adab61d5aa33097c3f5f5166b5f6c326399fc5a5.

Proposal SHA-256: 010d4c0243e7e6985284cccadb00fb7c6f7b0c5c50f22d81bb31ada960548d75.

Immutable execution receipt SHA-256: db39bc27bc04bf7f70bfaf2e5048b085798e3ef8b72e58fa54a367a51b7b6d91.


Full authority: [proposal source](proposal/proposal-source.txt).
[31 requirement mappings](proposal/traceability.md).
[Fresh comparison](delivery/revised-leans-20261008/run-comparison.json).
[Earlier defect diagnostics](delivery/revised-leans-20261008/audit-diagnostics.json).
[Scope and publisher controls](delivery/revised-leans-20261008/scope-audit.json).
[Quoted WKT keyword control](delivery/revised-leans-20261008/quoted-keyword-audit.json).
[Uniform, pole and normal-form controls](delivery/revised-leans-20261008/closure-audit.json).
This is local evidence. No remote or communication updates belong to this run.

Eiffel mesh: SDC PERFORMANCE,
[Free La Tour Eiffel](https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
