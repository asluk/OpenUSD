# Geospatial proposal candidate and executed evidence

The proposal now contains a **complete proposed answer for every known retained-scope contract gap** from the audit. It remains a review candidate: input-only model attitude, descendant-transform meaning, native-data association, independently bound prototypes, geographic scene charts, Profiles, export representation and WKT string normalization require author alignment. No computed projection result becomes a source USD property. Passing this run does not establish group agreement or whole-proposal conformance.

The full local loop passed **64 regressions and 61 distinguishing controls**, compared 213,231 coordinate results per Python/C++ path, verified 35 OV-hosted jobs, rendered two native Hydra/Storm exports and reread 11 exports. The maximum measured Python/C++ coordinate difference was 3.39e-08 m. Original source inputs and frozen executed files remained unchanged.

[Editable slides](delivery/geospatial-build.pptx) Â· [PDF](delivery/geospatial-build.pdf) Â· [Receipt](delivery/run-report.json) Â· [Proposal audit](proposal-quality.json) Â· [Whole proposal](proposal/proposal-source.txt) Â· [Build loop](BUILD_LOOP.md)

## Proposal quality and review choices

The sole normative candidate is the whole proposal, SHA-256 `1727a552053cfdcdf202e2c84ad1209d1a898fe2eab2e322d51e9c7b4ad7c7c0`, with the exact local diff retained beside it. Requirement traceability now uses the actual 31 functional requirements and their exact normative clauses. Derived notes, fixtures and adapter code add no authority. The pre-implementation gate distinguishes missing meanings from complete choices awaiting review; the post-implementation gate checks both authored fields and observable results in reverse.

| Subject | Proposed answer |
|---|---|
| Inputs / Q2, Q6 | Position plus physical geodetic-attitude quaternion. Projection scale/convergence are computed; intentional scale uses xformOps. |
| Transform order / Q3 | Anchor xformOps adjust the resolved placement in a fixed working chart. Descendants retain model-local USD meaning. |
| Absolute data / Q11 | Xformable carrier selects native asset, format, field and coordinate domain; values, masks and observation times stay paired. |
| Instances and geographic output | Bound prototypes retain their own anchor; geographic tuples have an associated geocentric Cartesian scene chart. |
| Profiles, export and WKT | Whole-scene hard dependency claim; nonbinding Cartesian context for baked geometry; lexical WKT normal form distinct from semantic CRS equality. |

The authored model inputs are `double3 crs:position` and `quatd crs:orientation`. Their scope, defaults, units, ordering, quaternion validity and time behavior are defined. `crs:scale`, coordinate epoch, heading/pitch/roll outputs, convergence and computed projection-scale properties are not authored inputs. The proposed external schema uses `data:asset`, `data:format`, `data:field` and `data:coordinateDomain`; this is an explicit new schema candidate, not a claim that existing fields already covered association. WKT retains CRS authority. Ordinary scaling and pivots remain xformOps.

Coordinate epochs and scene-authored operation/resource controls remain deferred without foreclosing later support. Larger-scale geographic workflows remain represented. Nothing in these choices is justified by a fixture name or an adapter limitation.

## Ordered math and the descendant choice

The intrinsic map converts model-local stage coordinates through geospatial attitude and the source datum's ENU/ECEF relationship. The anchor's ordinary stack adjusts the resolved point in its fixed working chart, then the adjusted physical point is expressed in the requested output CRS. The nearest strictly enclosing direct CRS binding selects that working context; the source CRS is its fallback. Output selection never reinterprets raw adjustment values.

Descendant xformOps, including authored asset conformance, define the model-local point supplied to placement. This is a **proposed clarification** of the call's broad post-placement wording, not an assertion that descendant semantics were already settled. The tested all-working-axis counterfactual differs by **4.222137 m** in the distinguishing rotated-child case. Both exact coordinates are retained in [the comparison](delivery/transform-order-comparison.json). This review choice is visible rather than hidden behind an implementation order.

An anchor +10 translation moves along site easting; the oriented child +3 local-X offset follows model axes. A descendant reset removes ordinary ancestors and retains intrinsic placement. Independent direct bindings exclude ancestor xformOps without ignoring the enclosing CRS's role. Per-instance transforms are applied once; bound prototypes retain their own absolute source placement. A separate prototype-child reset control excludes a +100 prototype transform and retains the explicitly selected instance transform.

## Eiffel geometry and shading

![Native Storm Eiffel rendering](delivery/renders/tower.png)

The native C++ path resolves **163,440 vertices**, including the illustrative context markers and plane. **163,416 authored vertex normals** are transported through the full-map Jacobian, compared between readers, retained in the output and reread. The export's ordinary points and double transforms reach Hydra data sources and native Storm color output. The plane and markers are illustrative, not surveyed Paris context. This is a resolved-export rendering path; no live geospatial Hydra filter or OV render is claimed.

## Colorado site calibration

![Native Storm survey rendering](delivery/renders/terrain.png)

The original LandXML survey contributes **14,359 breakline vertices**. WKT carries the calibrated site relationship and US survey foot units. Stage conventions remain separate. No terrain surface was fabricated. Fresh readers verify placement; polygonal bounds describe returned vertices and straight faces, not the continuous nonlinear image of an original surface.

## Native measurements and larger-scale workflows

![Synthetic global 3D measurements](delivery/plots/global-3d.png)

The synthetic global CF domain has **154 samples over two observation times**, explicit **100 m ellipsoidal height** and illustrative temperature units in kelvin. Both readers resolve it into geographic and ECEF coordinates without changing values or treating observation time as a coordinate epoch. A fresh CF export preserves values, masks, coordinates, height and observation-time metadata.

The original global scalar grid retains **2,664 values** and its explicitly horizontal association. Missing physical units, height and observation times remain missing. Unsupported 3D requests fail visibly. Synthetic imagery adjustment retains native pixel values and coordinate bytes while adding +25 m east and -10 m north in the project frame. CF controls select distinct geographic/projected coordinate domains and retain missing masks and native times.

![Railway horizontal resolution](delivery/plots/railway.png)

The original railway retains **15,822 horizontal vertices** across 2,386 parts. An explicit horizontal illustrative copy resolves to UTM 32. Its original third components remain untouched and uninterpreted; no height reference is guessed. Plot origins serve display only.

## Same partner data in both placements

**France_01: CC49 to Lambert-93 (m).**

| Component | Source | USD Python | USD C++ | OV-hosted Python |
|---|---|---|---|---|
| Easting | 1661099.03900000 | 661101.10941715 | 661101.10941715 | 661101.10941715 |
| Northing | 8180053.11700000 | 6857834.25653567 | 6857834.25653567 | 6857834.25653567 |
| Height | 37.29800000 | 37.29800000 | 37.29800000 | 37.29800000 |

**Colorado_02: State Plane to Westminster site grid (ftUS).**

| Component | Source | USD Python | USD C++ | OV-hosted Python |
|---|---|---|---|---|
| Easting | 3108002.11220000 | 3108871.45010067 | 3108871.45010067 | 3108871.45010067 |
| Northing | 1752265.06660000 | 1206317.46940319 | 1206317.46940311 | 1206317.46940319 |
| Height | 5482.94240000 | 5484.67794933 | 5484.67794927 | 5484.67794933 |

All coordinate-conversion paths use PROJ. Independent placement arithmetic is verified, but engine-independent geodetic validation and survey accuracy are not established by these comparisons. Operation-pipeline comparability is reported separately from numerical agreement.

## Geographic scene charts and exports

Geographic coordinate tuples remain angular/height tuples. Scene geometry, derivatives and polygonal bounds use the associated geocentric Cartesian CRS of the same datum. An explicit control rejects angular scene bounds; fresh Python and C++ readers verify the exported geographic workflow's Cartesian geometry context.

The 11 exports cover Eiffel, survey, composition, ordinary instances, independently bound prototypes, geographic-scene geometry, four CF domains and a sampled geometry trajectory. Baked geometry has a typed, nonbinding Cartesian CRS context and ordinary geometry/transforms, without an active placement binding or private already-resolved flag. Fresh readers verify placement once. Original sample keys **0, 5, 10** and **48 time codes/second** are preserved. The source-first midpoint is 971.421 m from the converted-endpoint chord; no original-trajectory guarantee is claimed between exported samples.

## Consumer evidence and limits

| Path | Observed output |
|---|---|
| USD Python / C++ | Two independent placement readers; 213,231 comparable coordinate results each. Shared PROJ and dataset decoding. |
| Omniverse live stage | 177,864 geometry vertices read back from runtime buffers/world matrices; 36 edit, failure and recovery checks. Reuses Python placement; normal buffers also checked. |
| Hydra / Storm | C++-resolved ordinary exports reach points/transform sources and two native rendered images. |

Analytically affine geocentric placement has a zero mathematical approximation-error certificate at the evaluated time. General nonlinear continuous-domain and between-sample certificates remain unsupported by these adapters and fail visibly. Numerical frame derivatives and polygonal bounds are not certificates. General coordinate-bearing primvar transport, physics integration, independently implemented WKT normalization and a live geospatial Hydra filter have no complete evidence here. These are implementation/verification limits, not newly deferred model meanings.

The implementation audit corrected angular bounds, a native prototype reset, the relative-result frame and source-normal export. It also caught an independent Y-up test oracle that applied scale in the wrong mapped axis order. Native diagnostic logging now retains distinct realized pipelines rather than a repeated entry for every point. None of these repairs introduced a source property or changed the pinned proposal.

## Source credit

The Eiffel geometry is “( FREE ) La tour Eiffel” by [SDC PERFORMANCE](https://sketchfab.com/Lambo_SC04), [original model](https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674), licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The example reorients, places and renders that geometry with illustrative context. Partner-data credit and permission are retained in `data/README.md` and `data/LICENSE-partner.txt`.

## Reproduce and derive delivery

`run.py` requires a fresh run directory and the pinned USD, PROJ/resources and OV tools. It freezes source/inputs, compiles native targets, runs controls, verifies exports and actual consumers, then audits fields and preserved inputs. `collateral/derive_contract_delivery.py --run <directory>` verifies that freeze before deriving this README, portable evidence and story. `collateral/contract_slides.mjs` derives the deck from the README/story and immutable returns. `collateral/verify_contract_delivery.py` checks the actual artifacts and rejects unsupported integration claims. Prior generators remain historical and are excluded from the active delivery path.
