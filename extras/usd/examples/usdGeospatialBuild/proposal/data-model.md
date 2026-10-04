# Derivation from the shared geospatial proposal

Authority: full proposal snapshot at `39c8fb816a9113b14c8f64b020270724b8357312`, retained verbatim in [proposal-source.txt](proposal-source.txt). This derivation records defined behavior and missing contracts. It is not an alternative specification.

## Defined authored representation

`GeospatialCRS` is the typed schema class; its declared prim type name is `CoordinateReferenceSystem`. It defines one `uniform token crs:wkt`. The complete WKT token owns facts represented within it. This run neither splits those facts into USD properties nor rewrites the WKT.

`GeospatialCRSBindingAPI` applies to `UsdGeomXformable` prims. A reference to a CRS definition contributes composed `crs:wkt` at the bound prim. The applied schema identifies a direct binding; an unmarked vector or WKT property does not establish one. Descendants use the nearest direct binding in the composed ancestry. Independent descendants can establish a different source CRS. Equivalent composed data has equivalent meaning, regardless of the arcs used to obtain it.

CRS position, orientation and scale are separate from ordinary xformOps. Their exact property definitions are absent. This derivation defines no replacement properties, private relationship binding or placement defaults. A direct binding establishes a model-placement boundary, but discovery alone does not compute its placement.

## Representation still required

The shared text must specify placement fields and component conventions (questions 2 and 6), measurement-coordinate association (11), dependency declaration and composition (12), and the export sampling record (14). The exact WKT string normal form (10) also remains unspecified. The existing 3D scope and two-axis examples must be reconciled.

An implementation must not author `geo:coordinateEpoch`, `geo:positionOnly`, an inferred coordinate-property association or a private already-resolved flag to fill these gaps. Internal caches and transient result objects do not become authored scene facts.
