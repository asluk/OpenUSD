# Source contract and reverse audit

Authority: proposal commit `4120379fa12473b54a8f8e11999a1cefa5443614`,
README blob `2386f16283df435ccb4304a3972d51e26d4be311`.
The private authority snapshot is byte-frozen; this run does not edit it.

This is a new derivation on stock OpenUSD, by the same agent that performed
earlier runs. Only original datasets, installed dependencies and a neutral Storm
recorder were reused. No previous geospatial reader, fixture generator or
generated expected answers were read or copied for this implementation.

The following table traces required meaning to the source model and observable
evidence. A row is traceability, not a claim of exhaustive conformance.

| Requirements | Authored facts and specified runtime meaning | Evidence |
|---|---|---|
| 1,2 | Whole uniform WKT is self-contained authored authority; queries do not create properties | Original full WKT controls; schema field inventory; unchanged source snapshots |
| 3 | Frame reference epoch may occur in WKT; coordinate epochs/epoch operations remain deferred | Dynamic CRS parse; wrapper and rate-bearing operation rejection |
| 4 | Calibration remains a derived CRS, including vertical conversion | Original Westminster site WKT and five provider controls |
| 5,6 | Direct schema application establishes binding; ordinary descendants inherit until next direct binding | Nested independent anchors; point-instancer occurrences |
| 7 | Interpret composed opinions; do not infer coordinate role from reference provenance | Inherits, references, layer offsets, value clips, native instance proxies |
| 8 | Source remains unchanged; anchor adjustment has fixed working context independent of requested output | Cross-output physical position comparison; adjusted measurement locations |
| 9,10 | Physical HPR and local metric geometry use geodetic ENU; full point map retains conversions | Finite model points and original Eiffel vertices through both readers |
| 11 | Independent positions exclude ancestor ordinary stacks; resets retain intrinsic placement | Nested direct binding and descendant reset counterexamples |
| 12,13 | Semantic coordinate order, declared units/height; no angular length | Geographic/ECEF controls, US survey feet, EGM2008 fallback and computed height reports |
| 14,15 | Scene axis/unit mapping fixed; writer authors asset conformance separately from placement | Explicit original tower cm/Y-up corrective; Y-up/centimetre scene query |
| 16 | Consumer output defines query; no invented output context | Cartesian/geographic query comparisons; default context read |
| 17,18 | Shared point placement for analytics/ordinary geometry; relative coordinate queries retain declared meaning | Both reader bakes; actual Storm/Omniverse consumers; nonvisual arrays |
| 19 | Source untouched; explicit bake represents effects once and records actual Cartesian context/time keys | Fresh reread of original Eiffel bake; source layer snapshots |
| 20 | Source position interpolation precedes conversion; composed HPR samples become quaternions before interpolation | Surface equatorial midpoint; shortest arc, held and ambiguous half-turn cases |
| 21 | Invalid input/resource/domain/epoch requests fail visibly; no substitute coordinate | Negative cases, isolated missing-EGM grid process, non-finite and invalid-role checks |
| 22 | Full Cartesian/geocentric charts retain global curvature | Global climate samples; geographic-output associated geocentric chart |
| 23 | Separate double origin and float local points retain detail | Fresh ordinary bake rounding/readback distances at ECEF magnitudes |
| 24 | Finite vertices/polygons do not certify nonlinear continuous domains | Explicit finite coverage reports; continuous-domain requests visibly unsupported |
| 25 | Geospatial inputs additive; ordinary bakes readable without geospatial evaluator | Ordinary source xform interpretation; actual consumer stage/renderer |
| 26,27 | Conservative Profiles summary above payloads, validated at publication | Actual native ClaimsAPI read with zero payloads loaded; stale-summary rejection |
| 28,29 | Actual operation and attributed accuracy separate from comparison/approximation error | Realized pipelines and resource hashes; predeclared 2 mm control/comparison distance |
| 30 | Native coordinate dimensions align values, indices and observation times | CF dimension permutation, two raster sample conventions, original railway and climate |
| 31 | Exact lexical normalization preserves decimal/text information; semantic equality is separate | Idempotence, long decimals, quote preservation, unequal text with equivalent CRS |

## Implementation findings, corrected against existing text

These are implementation defects, not reasons to invent new proposal fields:

- An early native request passed a zero time ordinate to PROJ. The proposal
  explicitly excludes coordinate-epoch operations. Unknown time is now passed
  as unavailable and rate-bearing/epoch-dependent operations reject visibly.
- A prototype Profiles author wrote string dictionaries resembling ClaimsAPI
  data. The existing native ClaimsAPI instead requires its native token types.
  Publication now uses that API and is read back through it with payloads
  unloaded. The proposal's `customData.profilesInfo` location was verified
  against actual upstream source; a stale header description alone was not used.
- A first CF adapter required a dimension coordinate variable for every named
  dimension. The specified auxiliary-coordinate association also covers such
  dimensions; the corrected adapter aligns by declared dimension names/order.
- A native unbound point-instance result queried the prototype's storage parents
  for its report. Occurrence context now supplies that report. Bound placement
  never adds a second instancer origin.
- A model with identity ordinary adjustment need not request a conversion into
  the enclosing working chart. Chart setup is now lazy, preserving the specified
  ability to avoid an unnecessary intermediate operation.
- A first sampled export kept one float frame while the model moved hundreds
  of kilometres. Its millimetre detail check failed. Each exported sample now
  keeps local geometry small and records motion in ordinary double-precision
  transforms; the existing precision/sampling rules require this repair.
- Requiring a clean native process exit exposed a cache-lifetime error after
  large requests had written their coordinates. Cached models now belong to
  the engine and are destroyed before its PROJ context. A written result alone
  no longer counts as a successful execution.

## Limits that are not missing model definitions

The prototype's finite-point success does not certify continuous curves,
subdivision surfaces or the nonlinear image of an original face. Unsupported
certification is reported visibly. General custom GeoTIFF key decoding, complete
indexed/animated primvar export coverage, complete inverse-domain certification and exhaustive
variant/publication maintenance are implementation coverage items, not added
USD fields or evidence that the proposal has no meaning for them. Their current
coverage must remain visible in the README and deck.

Profiles identity stewardship and standard approval remain review questions.
This run registers proposed identities locally and does not claim their adoption.
Provider coordinate tables are useful external references, but their author
generated them with PROJ: they are not an independent geodetic engine oracle.
