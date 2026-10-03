# Decisions exercised rather than assumed approved

| Question | Executed candidate/alternative | Group decision still needed |
|---|---|---|
| Q2 placement attributes | `double3` position, `quatd` orientation, `double3` scale; fields and defaults are frozen before code | Exact standard fields/types/conventions |
| Q3 project adjustments | Working-context transport; compare unchanged numbers in output axes with a physical-placement counterexample | Authored adjustment context and detailed composition |
| Q6 axes | ENU projected; longitude/latitude/height geographic; geocentric XYZ | Geographic/geocentric tuple/frame conventions |
| Q9 geographic scenes | Geographic coordinate queries; do not claim geographic mesh/bounds rendering | Angular scene frame/bounds semantics |
| Q10 normalization | Preserving lexical canonicalization; compare changed axes/units/datum and different metadata | Adopted normalization/equality profile |
| Q11 association | Property-target relationship for coordinate arrays; measurements/times retained | Standard association with existing dataset schemas/adapters |
| Q12 declaration | Writer-maintained root customLayerData declaration; test unloaded/stale cases | Composed declaration representation/coverage contract |
| Q13 results/extent | Operations disclosed; double-coordinate agreement and sampled affine error measured | Certified general extent/approximation and comparison contract |
| Q14 export | New standard-data asset with output CRS and explicit sampled-time metadata | Sampling record representation/interpolation contract |
| Q15 epochs | Wrappers, authored/requested coordinate epochs fail explicitly; frame epochs retained | Future authoritative association and time-dependent model contract |

Q1 geographic source placement, Q4 writer conformance, Q5 direct-binding boundary,
Q7 site calibration through CRS definitions and Q8 selected output meaning are
retained answers. Requirement 30 and Devin's city/global functional use cases are
already confirmed. Runtime API signatures are not open standards questions.
