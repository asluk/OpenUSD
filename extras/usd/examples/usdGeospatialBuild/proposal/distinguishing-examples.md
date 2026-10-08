# Derived excerpt: no additional authority

Source SHA-256: 28768109389139a56d5c8e5f473446bfa46dd1ab46a48924165b97fb92cb7ae9

## Appendix C: Distinguishing examples

These cases illustrate the proposed contracts; they add no normative fields.

| Case | Distinguishing result |
|---|---|
| Same physical tower re-expressed in geographic, CC49 and Lambert-93 coordinates | Geodetic model attitude and local lengths stay physical; output grid convergence and scale come from resolution, not stored output properties. |
| Tower attitude turns 90 degrees, then a descendant translates along working-grid X | The descendant translation follows the model's turned X, while an anchor adjustment follows working-grid X; interpreting both as raw working offsets loses local conformance. |
| Two independent origins, one at 100 and its directly bound child at 20 | Relative output-coordinate difference is 80; the child does not accumulate 100 or return a reference-model-local offset. |
| Project-adjusted satellite imagery | Original pixel values, indices and native coordinates remain unchanged; queries and visualization include the same working-frame adjustment even for another output CRS. |
| Global climate domain | Measurement times remain attached to the same samples; geographic coordinate queries and geocentric scene visualization use the same locations without a global flattened surface. |
| Independently bound point-instancer prototype | Each instance retains the prototype's source georeference and applies its per-instance adjustment once; the instancer does not add a second absolute anchor. |
| Linear mesh exported after a nonlinear map | Vertex and exported-polygon bounds alone do not certify the continuous image of the original face; a requested continuous guarantee needs separate evidence. |
| Scene with an unloaded geospatial payload | The published interface retains the conservative hard Profiles claim; a consumer need not load the payload to detect dependency. |
