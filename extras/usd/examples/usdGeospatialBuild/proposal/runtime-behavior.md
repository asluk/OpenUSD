# Proposed normative runtime behavior for this candidate

The clauses below define the frozen experimental model in data-model.md. They
are normative for this experiment and proposed for later standards review; group
approval is recorded separately. Function signatures, caches, plugin factories,
projection-library selection and renderer integration are implementation choices.

1. Read authored information from the composed stage at the requested USD time.
   Evaluate ordinary USD value resolution and source-space placement sampling
   before CRS conversion. Equivalent composed data has identical interpretation.
2. Resolve a binding to one complete CRS-only WKT definition. Retain its declared
   information. Interpret position/measurement tuples by the candidate's fixed
   mapping, with CRS-derived component units and height reference. Do not infer
   an absolute CRS position from an unmarked mesh/vector or ordinary translate.
3. A direct model binding starts an absolute anchor. Ancestor xformOps do not
   accumulate across that boundary. Enclosing bindings may supply working
   context; they do not replace the source definition or source coordinates.
   Use position/orientation/scale together, not a converted origin alone.
4. Resolve intrinsic placement to the selected output CRS, including projection
   rotation/scale and any supported datum/height operation. Then apply ordinary
   USD transforms according to the declared candidate working-context rule.
   Preserve their physical placement meaning when the output selection changes.
   Descendant offset transforms follow ordinary USD composition relative to the
   resolved frame. Respect authored resets/inverses without authoring new ones.
5. Select applicable coordinate operations through the engine. No registry code
   replaces authored WKT. Allow engine-selected non-epoch grids; do not add USD
   grid/resource-selection properties. Expose operation identity and attributed
   accuracy. Never silently substitute a lower-accuracy/ballpark operation after
   a required resource or supported operation fails.
6. Produce the same placed geometry, coordinate queries and bounds for rendering
   and headless consumers of the same candidate. State the result coordinate
   frame/units. Scene-display adaptation is derived state, not source authoring.
   The tested affine leaf bounds and relative model-frame queries use the same
   resolved frames as geometry, as specified in data-model.md. They do not
   establish a nonlinear approximation guarantee or universal primitive coverage.
   A geographic coordinate query may return longitude/latitude/height without
   promising a Cartesian scene/bound interpretation for geographic outputs.
7. Keep measurement values, source coordinates, recorded observation times and
   their associations available independently of visualization. Transform only
   derived coordinates. Time-varying values on a fixed grid do not imply motion.
8. Preserve all source layer bytes and authored values during resolution. A
   source edit, binding/definition edit, output change or time change invalidates
   affected derived state. Results after an edit must reflect the new composed
   scene; instance results use each instance's composed placement.
9. Any invalid definition/binding, missing necessary placement/association,
   unsupported operation/output, missing required resource, nonfinite point,
   out-of-domain transformation or coordinate-epoch request is a visible failure.
   No unchanged, partially converted or fabricated placement is returned as
   success. Failure of a batch reports the affected input; no partial-success
   array is mislabeled as the complete successful batch.
10. Validate authored data without CRS conversion where possible: fields/types,
    bindings, WKT syntax/normal form, coordinate association in inherited as well
    as directly bound scopes, placement/binding consistency, declarations and
    finite values. Intentional nested independent bindings are permitted; a
    validator cannot infer that their author intended an ordinary offset instead.
    Existing dataset contracts govern measurement index/time/value coverage;
    the geospatial carrier and its adapter contract remain Q11. Runtime errors
    and independent controls are separate evidence. Registered USD validators
    must be discoverable by name/keyword in the stock validation registry.
11. Keep absolute positions in double precision and asset-relative geometry in
    its authored small-offset representation. Report actual float quantization,
    coordinate magnitude and finite extent. Compare full oriented/scaled
    placement with an origin-only control and exact per-point evaluation.
12. Export only by an explicit request to a new asset. Record output CRS and
    time-sampling meaning, preserve measurement associations and dependency
    declaration, and remove the need for a private history/skip-conversion flag.
    Fresh resolution in the exported CRS reproduces the placed result once.

## Evidence scope

The experiment must execute these clauses and feasible alternatives, identify
missing field/behavior contracts and report failed or conditional cases. It must
not claim conformance to unspecified general geographic scene output, certified
continuous-surface error bounds or future coordinate epochs. Those are design
questions; unfinished implementations or demonstrations are not such questions.

Headless queries, native Hydra and the OV runtime compute placement independently
from authored scenes. Sharing a projection engine is disclosed. Renderer and
analytics consumers within one runtime are not independent implementations.
Closed-form ellipsoid arithmetic and the partner CSVs provide different controls;
the partner coordinates were themselves computed with PROJ and therefore cannot
be represented as an independent geodetic-engine certification.
