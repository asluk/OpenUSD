# Observable runtime derivation

Authority: the entire unpublished local candidate, SHA-256 `a5444966c41e3a067d7c4db5b2e9a300a08b17fcce377bd6fb24727b390e6904`, based on `39c8fb816a9113b14c8f64b020270724b8357312`. [proposal-source.txt](proposal-source.txt) is the sole proposal authority. These files record derivation and do not add normative choices. Proposed details remain under author review.

Composed nearest direct binding supplies the source definition. Broken nearest definitions fail without falling through. Directness is composed data, not inspection of particular composition arcs.

### Source placement evaluation and transform order

Read the three placement fields from composed values. For sampled fields, use
Core value resolution in the source representation: `double3` interpolation for
position/scale and quaternion slerp for orientation when linear interpolation is
selected; held interpolation remains held. Interpolate before CRS conversion,
as requirement 20 already specifies. Do not invent longitude unwrapping or a
motion model. Animation time is not a coordinate epoch.

Resolve the complete position, orientation and scale into the requested output
context, including the change of local axes and distance scale. Converting only
the position and retaining the original orientation and scale is insufficient.
The three source fields do not require every resolved frame to be decomposable
into a quaternion and diagonal scale. A conversion can introduce shear or
nonlinear distortion; neither may be discarded merely to fit those source
field types. A local affine result is an approximation subject to the stated
extent and error contract, not a new authored source placement.
Only after that CRS computation apply ordinary USD transforms, retaining their
authored order, pivots and ordinary reset semantics. A direct binding excludes
ancestor ordinary transforms at the independent absolute placement boundary;
resolution does not author a reset or modify the source xformOps.

Changing the output CRS recomputes the result without replacing these source
placement values. Applying a requested CRS conversion is separate from applying
an intentional project adjustment. Question 3 still requires the exact working
coordinate context for those ordinary adjustments when output changes.
The proposed extent and result-comparison rules below address question 13;
they do not supply the missing frame definitions in questions 3 and 6.


### Observable outcomes and failures

Resolution leaves source layers unchanged. Unsupported requests, broken
bindings and failed or incomplete operations fail visibly. Operation reporting
must identify what was computed and distinguish engine estimates from the
placement/error guarantee required over the stated extent.

Explicit export is a separate act: it records the output CRS and time-sampling
meaning, preserves dataset values and associations, and can be resolved by a
fresh consumer without applying placement twice. The proposed sampling rules
are below; measurement-coordinate association remains question 11.

These obligations need a complete data model and normative runtime specification
before independent implementation can claim proposal conformance. A prototype's
choice of a projection engine or affine approximation does not fill that gap.


### Extent and result comparison

**Proposed clarification of question 13.** These are observable result
obligations; they prescribe neither callable interfaces nor an engine's
approximation algorithm.

Operation-attributed accuracy, model-placement approximation and agreement
between implementations are reported separately. An unknown operation accuracy
is unknown, not zero. Requirement 28 does not require a full propagation of
geodetic uncertainty through every scene transform.

An approximation claim names its spatial extent, evaluated time or time range,
distance measure and bound. Its reference is pointwise evaluation of the same
source placement, coordinate operation and ordinary-transform chain, not just
conversion of the placement origin. The claim must cover the content actually
consumed, including transformed geometry and bounds. A few representative
points do not establish a bound over an entire extent. An implementation may
refine an approximation or split the work; if it cannot establish the requested
bound for the requested extent, it reports that limitation instead of claiming
the bound. No universal tile size or private default tolerance follows from
this requirement.

Comparison cases fix the source and output definitions, sampled input values,
interpolation mode, ordinary adjustments, requested result and acceptance
distance before execution. They establish equivalent coordinate operations,
including the realized parameters and resource versions that affect results.
Different valid operations are reported as such, rather than classified as
floating-point disagreement. If equivalence cannot be established, comparability
is unestablished. Operation labels alone do not prove equivalence.

For Cartesian coordinate outputs, compare Euclidean distances after converting
each component's declared length unit to metres, and also report residual
components in the output's declared units and the coordinate magnitudes.
Mixing feet and metres in an unconverted norm is not a distance measure.

For geographic coordinate queries, propose reporting horizontal distance using
the existing [ellipsoidal inverse geodesic](https://proj.org/en/stable/geodesic.html)
on the output WKT's ellipsoid, height difference in metres in the same declared
vertical reference, and their Euclidean combination as the agreement distance.
Angular component residuals are reported separately; degrees and metres must
not be combined as Cartesian components. This is an explicit proposed comparison
convention, not an OGC-mandated error measure or a choice already agreed on the
call. It does not establish a geographic scene frame under question 9.
An acceptance distance is supplied by the request or documented comparison
case, not guessed after seeing the results or stored in an undocumented scene
attribute.


### Explicit export and sampling

**Proposed clarification of question 14 using existing USD fields.** A resolved
export is a new authored dataset in its recorded output CRS. It retains the
ordinary interpretation of its geometry, coordinates and measurements. Every
baked placement effect is represented once: an effect included in exported
coordinate or geometry values cannot also remain as an unapplied placement or
ordinary transform that a fresh reader will apply again. This changes the
exported copy, not the source stage, and requires no private "already resolved"
flag. Output bindings, coordinate associations and the dependency summary must
describe what the exported copy actually requires.

For sampled output, the authored `timeSamples` keys record the actual exported
sample schedule and the export authors the stage's existing `timeCodesPerSecond`
to record its time-code scale explicitly. Each exported sample equals the
requested resolved source result at that time, subject to the stated result
bound; export is not required to reuse only the source sample times.
Observation dates and measurement values
retain their own associations and are not inferred from USD time codes.

A reader evaluates the exported authored samples under Core value resolution
in their recorded output CRS. This differs from interpolating the original
source samples before CRS conversion: the equatorial example in requirement
20 produces a surface midpoint from source longitude samples, but a chord
midpoint from two exported ECEF endpoints. An exporter claiming to preserve
the original trajectory between samples must provide sufficient samples to
meet a stated bound over that time range. Recording two sample times alone
does not establish that claim.

Core defines held and linear stage interpolation, with linear as the default,
but how a reader selects that stage setting is implementation-defined. This
proposal adds no authored interpolation-mode field. Sampling-policy provenance
or a requirement to force a reader's interpolation setting would be a separate
model decision; the proposed record here establishes the actual sample times
and time-code scale, not an unrecorded sample-generation history.


## Executed boundary

Source-value reads use exact candidate types, defaults, blocks and Core interpolation. Direct anchor-origin queries have complete three-component CRS definitions and no ordinary adjustment or model offsets. They do not select a model-axis adapter, resolved frame approximation, measurement-coordinate carrier or dependency declaration. Nontrivial ordinary adjustment requests stop with the specified missing-frame diagnosis. Coordinate epochs are rejected. Network lookup is disabled.
