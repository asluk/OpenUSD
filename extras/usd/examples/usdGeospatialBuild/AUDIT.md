# Audit of the current derivation

The authoritative input is the full proposal snapshot, not the previous experiment. Every requirement has a source-line trace. Existing reference binding, nearest composed scope, post-placement ordinary transforms, source-space interpolation, writer conformance and export intent remain intact.

The newly executed discovery code reads only composed apiSchemas and crs:wkt. Its fixtures author only the existing WKT property, applied binding metadata, normal USD composition arcs and ordinary USD scene data. The readers add no CRS placement fields, duplicated WKT-derived metadata, coordinate epoch, coordinate-role guesses or private resolution flags. Unknown API registration is handled as explicit composed applied-schema metadata for these partial readers; no generated placement schema is registered.

The Python, native C++ and live OV readers implement discovery independently. Each is checked against authored scope expectations. Used layers are compared before and after reads, and fixture bytes are checked across consumer execution. Invalid nearest bindings fail rather than inheriting a farther source. The retained experimental relationship reader is deliberately checked as incompatible with the proposal format.

The default gate checks the source snapshot and derived documents. Missing placement, adjustment, measurement, declaration and export contracts stop dependent execution. The fixture set tests discovery without claiming full-asset validation or conformance to the missing declaration/normalization contracts. A binding-scope traversal cannot satisfy requirement 26's declaration without traversal.

Neither a native discovery executable nor a live OV stage read demonstrates resolved Hydra/OV geometry. No projection, placement frame, bound, render, physics result or resolved export is claimed in this run. Coordinate-operation accuracy, numerical agreement and approximation over an extent remain distinct. Source and receipt hashes make execution provenance reviewable; passing controls cannot close an unspecified contract.
