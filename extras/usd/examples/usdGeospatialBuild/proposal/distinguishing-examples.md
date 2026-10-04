# Derivation from the shared geospatial proposal

Authority: full proposal snapshot at `39c8fb816a9113b14c8f64b020270724b8357312`, retained verbatim in [proposal-source.txt](proposal-source.txt). This derivation records defined behavior and missing contracts. It is not an alternative specification.

## Executed controls

Two complete 3D WKT definitions are copied verbatim from Appendix A: dynamic geocentric ITRF2020 and compound NAD83 California zone 5 with NAVD88 height. They exercise definition identity and scope, without normalizing or transforming either definition.

References establish an enclosing binding and a distinct independent descendant. A referenced assembly remaps prim paths but keeps their source definitions. A stronger layer overrides one composed WKT. Selected variants and class inheritance produce the same scoped facts. Ordinary composition flattening preserves the binding interpretation; it is not resolved geospatial export. An enclosing available binding remains discoverable with its payload unloaded, while absent payload content fails.

Negative controls reject no binding, a broken nearest binding, a string-valued WKT property, varying WKT and an empty definition. An unmarked WKT property does not create a new coordinate domain. The retained relationship-based resolver fails a shared-reference-binding fixture, exposing a real compatibility difference.

## Dependent examples awaiting a complete contract

Colorado design/control separation, France non-epoch height conversions, Eiffel Tower placement, railway geometry, independently georeferenced project adjustments and city/global measurements remain useful full-loop workflows. The current run assigns them no invented placement properties or expected projected vectors. Their prior experimental results are historical, not current proposal-conformance evidence.
