# Post-implementation audit

## Assessment

No new required authored fact or undefined runtime meaning was encountered in
the exercised workflows. The pinned proposal remained unchanged throughout
implementation. This conclusion is bounded by the coverage below. A complete
proposed contract, group approval and complete implementation conformance are
separate judgments.

## Reverse trace of the authored model

| Source data | Proposal authority | Audit result |
|---|---|---|
| `crs:wkt` | Detailed design, GeospatialCRS | Uniform token; complete WKT retained. Valid supported non-normal spelling warns. No source rewrite. |
| `crs:position`, `crs:orientation` | Authored properties and physical-attitude convention | Only model-placement inputs. Required position, identity attitude fallback, explicit blocks, types and finite values checked. |
| `data:asset`, `data:format`, `data:field`, `data:coordinateDomain` | External measurement association | Uniform association facts. Shared decoder transport identifies the resolved asset and selection; C++ verifies them before its own coordinate evaluation. |
| `ClaimsAPI`, `customData.profilesInfo` | Dependency declaration with Profiles | Existing carrier, local proposed capability/profile registration, conservative publisher-maintained completeness. Summary reads do not load/traverse. |
| Ordinary xformOps, mesh values/normals and bake context | Evaluation and explicit export | Ordinary USD inputs retain their specified roles. Derived output records Cartesian CRS and double origins; it carries no private resolved flag. |

There is no authored coordinate epoch, duplicate datum/unit metadata, `crs:scale`
or computed source geospatial property. `purposeNote` is a deliberately unrelated
fixture property for preservation testing. `resolvedOffset` is the name of an
ordinary double translate in the derived copy, not a proposed geospatial field.

## Reverse trace of behavior

Core value resolution supplies position opinions, composed sample times and
ordinary transforms. Selected attitude endpoints convert to poses before slerp.
The intrinsic ENU point map precedes the fixed working-chart anchor adjustment;
descendants remain local. Independent bindings exclude ancestor ordinary stacks.
Descendant resets remove ordinary contributions while preserving placement.
Independently bound point-instancer prototypes use finite instancer-frame
transport, including reset handling below their own binding.

Geographic queries retain angular/height tuples; scene geometry uses the associated
geocentric chart. No 2D sample acquires height. Required operations and grids must
work. Missing resources and epoch-dependent requests fail rather than using
ballpark substitution. Full realized pipelines, known/unknown accuracy and grid
hashes distinguish operation choices from reader agreement.

The output comparison controls fix the acceptance distance before execution.
Survey-table coordinates and analytic cases supply independent expectations.
Both readers use PROJ, so numerical agreement does not constitute an independent
geodetic-algorithm proof. Shared native-format decoding is identified explicitly.

## Defects caught and addressed within this fresh candidate

- The first fixture generator selected trailing diagnostic columns from some
  provider CSVs. It now selects the coordinate columns and matches point IDs.
- USD's built-in attribute type can mask a wrong authored spec type. Validation
  checks the contributing spec as well as the composed schema type.
- The native-format bridge initially did not verify its resolved asset identity.
  It now validates the authored asset and format/field/domain/CRS association.
- A native coordinate query initially returned a three-component container for
  a two-dimensional result. It now retains two-component arity and rejects a
  requested 3D scene chart without height.
- A recorded Cartesian bake imported below an unrelated project binding must
  retain its own context and the complete ordinary transform hierarchy. Readers
  now honor that typed context before searching for an outside inherited binding,
  as already required by the explicit-export section.
- Reset handling below an independently bound prototype needed to remove that
  anchor's ordinary adjustment. A distinguishing instance control now covers it.
- A single fixed origin for a long sampled trajectory could lose millimetre
  geometry detail. Both bakes use ordinary double per-model translations while
  retaining float local geometry.
- Ordinary bake normals and extents initially remained in source coordinates.
  Mesh normals now use full-map derivative transport and extents describe the
  output points. Referenced material definitions now live under the advertised
  bake entrypoint, with internal connections remapped by standard Sdf copying.
  A default-reference reassembly control checks the actual shader connection;
  keeping materials elsewhere in the layer would not preserve that import.
- Geometric primvars without implemented export transport now produce an explicit
  unsupported error rather than an incorrect successful copy.
- Visual review caught a plot connecting unrelated railway feature segments.
  The scientific visualization now follows retained feature/geometry indices.
- The derived CF authoring copy uses an upward length axis and authoritative WKT
  for the custom site vertical ordinate. It does not label that calibrated
  ordinate as a geoid altitude. This is native CF association metadata, not
  additional USD vertical authority.

All these repairs follow existing proposal text. None introduced a new schema
fact or promoted a private workaround into the proposal.

## Remaining implementation and verification limits

Continuous nonlinear face/curve/subdivision enclosures are unsupported and
reported as such. Finite points and bounds of a resulting polygonal bake do not
certify those domains. Geometric point/vector/normal primvar export is explicitly
unsupported; ordinary mesh normals have implemented transport. GeoTIFF decoding
supports IFD 0. CF decoding covers the declared unit/role subset and examples,
not every valid CF association. Global inverse uniqueness, all value-clip
combinations and every ordinary USD dependency/geometry interaction have not
been exhaustively verified. The native-format environment emits a NumPy ABI
warning despite the passing association controls.

These limits remain visible in the README and deck. They are not silently
deferred functional requirements, missing proposal conventions, or a claim of
complete initial-scope conformance. General support for all these contracts is
still implementation work. Group review of the detailed candidate and Profiles
identity stewardship remains adoption work.

## Generation provenance and comparison boundary

The core candidate was newly authored and frozen before historical evidence or
neutral rendering tools were inspected. Original datasets, general libraries and
the small neutral Storm recorder were reused. A prior view-generation script was
inspected after the freeze but rejected as a generation seed because it contained
old placement assumptions; this run authors its own ordinary viewing stage.
No prior geospatial reader, schema, fixture logic or test suite was copied,
translated or patched into this candidate. Subsequent fixes repair this newly
generated candidate against the same pinned authority.

The previous presentation was consulted for clarity and layout after generation.
Its results were not imported as current expectations. The proposal changes are
informative corrections, so this run establishes fresh derivability evidence;
different case counts do not support a blanket claim of greater coverage than
every previous prototype.
