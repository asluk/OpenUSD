# Contract audit before generation

Authority: proposal commit 9f15b1b46224fcd3b22f1a0d5ebf352965cf2d97,
SHA-256 7b7784019d125bf27523929501b72d134810f996a87e764ea0e82db3da120256.
Read all 2,847 lines. This audit does not add normative authority.

The author supplies a complete WKT definition, a model position and physical
heading/pitch/roll, or an external-data association. Ordinary UsdGeom inputs
retain their roles. The proposed contract supplies observable meaning for the
following initial-scope requirements. Proposed wording is implementable even
where adoption remains under review.

| Requirements | Authoritative facts and behavior | Predeclared distinguishing control |
|---|---|---|
| 1–4, 31 | WKT is atomic authority; lexical normalization preserves all represented information; derived CRS conversions retained | Exact decimal and quoted-content preservation, fixed point, malformed WKT rejection, derived site CRS round trip |
| 5–8 | Composed applied schema marks direct binding, nearest enclosing binding fixes working CRS, unavailable direct definition fails | Reference/inherit/sublayer equivalent composed inputs; independent child does not accumulate parent origin; unloaded binding disappears but dependency claim remains |
| 9–13 | double3 position and physical orientation, finite local ENU map, semantic tuple units/order | Equator origin analytic ECEF; heading 90 turns forward east; latitude-first WKT receives lon/lat semantic tuple; 2D never gains height |
| 14–16 | Writer conformance; anchor adjustment in fixed working chart; descendants local; output selection preserves placement | Metre/centimetre and Y/Z equivalent conformed fixtures; parent ordinary transforms excluded; reset removes ordinary contributions only; output change retains adjustment |
| 17–19 | Shared point map, inverse/relative queries and explicit derived bake; source immutable | Two separately authored readers, original survey coordinates as independent oracle, ordinary USD world points match resolved points; double origin applied once after reassembly |
| 20 | Core source-position interpolation; endpoint pose conversion then shortest-arc quaternion slerp | ±1 degree equatorial midpoint is on surface; 0/360 no winding; 180 interior fails, exact/held succeeds; sample offset and blocked inputs |
| 21 | Invalid bindings, dimensions, operations, resources and nonfinite values fail | Missing grid, unsupported axis/epoch wrapper, wrong type/uniform samples, invalid placement role and partial batch controls |
| 22–24 | Point map supports project to global coordinates; finite points distinct from continuous certificates | France/Colorado controls, railway and global samples; origin-separated millimetre local detail; continuous bound request explicitly unsupported without certificate |
| 25–27 | Additive unaware interpretation, Profiles existing carrier, publication completeness/coverage validation | Required/known-none/unknown read above unloaded payloads; stale stronger usage override rejected by publisher; read performs no traversal |
| 28–29 | Operation, accuracy, spatial coverage and comparable-operation identity reported separately | Record full actual pipelines and grid hashes, Euclidean metre residuals and output magnitudes; no independent-engine claim from Python/C++ agreement |
| 30 | CF/GeoTIFF/GeoJSON native dimensional association, unchanged measurement values/indices/time | CF named-dimension permutation with nonconstant values/masks/time; GeoTIFF pixel-centre semantics; original railway feature indices; native metadata conflict rejects |

## Boundaries to preserve

- No coordinate epochs, motion models, automatic vertical default, `crs:scale`,
  computed source attributes or unrecorded export flags.
- Derivatives/normals require the full map. Point-instancer independent prototype
  adjustments use finite conjugation in the instancer datum's geocentric chart.
- Unsupported continuous-domain certification is an implementation limit, not
  permission to label sampled bounds certified or a gap in the contract.
- The original climate container lacks CF role/unit/grid-mapping declarations
  and height. Preserve it. Use a labeled derived CF example with explicitly
  declared synthetic height and temporal samples for the 3D association proof.
- Two implementations may share USD, PROJ, native format decoders and original
  inputs. Their geospatial readers/evaluators must be newly authored separately.
  Shared PROJ is not an independent geodetic oracle.

## Generation and delivery sequence

1. Generate Python reader, codeless schema and independent expectations/fixtures.
2. Generate native USD/PROJ reader independently against the same text.
3. Execute numerical, invalid-authoring, composition, sampling, association,
   instance, precision, export and publisher controls. Repair this candidate only
   against the pinned text. A normative change requires another fresh generation.
4. Freeze source hashes before comparing historical evidence or inspecting
   neutral rendering/integration tools. Execute actual consumer sinks.
5. Reverse-audit all authored fields and implementation choices. Classify contract
   gaps, implementation defects, unverified coverage and adoption separately.
6. Derive a standalone human README and editable deck/PDF from measured evidence,
   with actual output images and USD Profiles in the main narrative. No push.
