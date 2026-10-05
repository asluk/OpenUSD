# Remaining required contracts

Authority: the entire unpublished local candidate, SHA-256 `a5444966c41e3a067d7c4db5b2e9a300a08b17fcce377bd6fb24727b390e6904`, based on `39c8fb816a9113b14c8f64b020270724b8357312`. [proposal-source.txt](proposal-source.txt) is the sole proposal authority. These files record derivation and do not add normative choices. Proposed details remain under author review.

## G03: Physical coordinate context of project adjustments

Requirements 5, 6, 8, 9, 11, 15, 16, 19; questions 3.

Post-CRS order is decided. The controlling composed frame, adjustment axes/units/pivot and preservation across output changes are not. The complete xform stack must supply the intended adjustment; raw numeric reuse in another CRS is insufficient.

A 90-degree oriented model distinguishes a model-X adjustment from a grid-easting adjustment. The text identifies this precise choice rather than reopening placement order.

## G04: Remaining component conventions and scene result domain

Requirements 12, 13, 14, 16, 17, 18; questions 6, 9.

Geographic longitude/latitude/height and geocentric XYZ have proposed conventions. Canonical tuple order does not specify a Y-up or Z-up scene basis. Geographic coordinate queries are settled functional scope; using angular coordinates as a scene frame remains distinct.

Requirement 13 distinguishes coordinate components from scene axes. Returned query tuples use the same role order; unsupported component sets cannot be guessed.

## G06: Measurement-coordinate association

Requirements 2, 5, 6, 7, 12, 18, 19, 21, 27, 30; questions 11.

Subtree scope and measurement preservation are settled. The carrier identifying absolute coordinate properties or an external dataset domain is missing; neither API application nor float3 shape supplies that role. Coordinate-only data must not acquire a fake model anchor or receive crs:position twice.

Two bounded authored facts, multiple domains, retained format associations and the external-format/composed-binding authority conflict are stated. No new relation or generic measurement schema is invented.

## G07: Dependency declaration carrier and composition

Requirements 7, 19, 25, 26, 27; questions 12.

Coverage is already all placed content. The carrier, root/session interpretation, conservative assembly maintenance across composition/unloaded content, and export update rule are not specified. Traversal for detection is not the promised declaration.

Existing Core customLayerData is identified as a possible carrier, not selected as a normative key. Composition does not automatically aggregate it; no prototype layer flag is promoted.

Question 9 separately concerns geographic scene geometry, frames and bounds. Geographic coordinate queries already belong to initial scope. Coordinate epochs are roadmap, not a build failure.
