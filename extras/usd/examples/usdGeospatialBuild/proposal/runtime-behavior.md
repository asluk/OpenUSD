# Derivation from the shared geospatial proposal

Authority: full proposal snapshot at `39c8fb816a9113b14c8f64b020270724b8357312`, retained verbatim in [proposal-source.txt](proposal-source.txt). This derivation records defined behavior and missing contracts. It is not an alternative specification.

## Behavior independently derivable now

Read composed scene data. For a queried existing prim, walk its composed ancestry to the nearest prim bearing `GeospatialCRSBindingAPI`. Read the composed `crs:wkt` there. A direct binding with absent or unusable WKT fails visibly; it does not fall back to a farther ancestor and invent a different source. A query for content absent from an unloaded payload cannot claim to know that content's CRS. Binding on an available enclosing prim remains discoverable.

The WKT property is uniform and token-valued. Empty or missing definitions cannot supply a usable CRS. This partial discovery check does not certify WKT syntax, its unprescribed normal form or transformation support. It returns the source definition exactly as authored.

Queries leave used source layers unchanged. Adding CRS association does not rewrite ordinary xformOps, resetXformStack, metersPerUnit or upAxis. These are ordinary scene data. Discovery is not a traversal-free dependency declaration.

## Defined resolution obligations, blocked in this derivation

The consumer chooses the output CRS. Without a selection, the proposal's default uses the binding on composed defaultPrim. Preserve independently authored source CRS facts and project-adjusted physical placement. Separate CRS placement resolves before ordinary USD transforms. At an independent binding boundary, ancestor ordinary transforms do not accumulate as its absolute source placement, and source data remains unchanged. Writers or assemblers author unit/up-axis correctives.

Source positions interpolate before CRS conversion. All consumers share resolved placement. Geographic coordinate queries are allowed; geographic scene frames, geometry and bounds remain distinct. Engines select applicable operations and manage required resources, expose failure and identify the operation and its attributed accuracy. Operation accuracy, numerical agreement and placement approximation are different claims.

Those outcomes are defined, but the absent placement fields, component conventions and adjustment coordinate frame prevent a complete input-to-result contract. Measurement association, declaration and export sampling require authored definitions too. No finite-difference frame algorithm, affine transform or private field choice fills them. The current runner executes discovery controls only and stops projection, geometry placement and exports.
