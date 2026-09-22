# Decisions supported by the completed experimental run

The companion `runtime-behavior.md` is proposed normative prose. This document
records gaps and implementation questions; these are not additional accepted rules.
The behavior draft currently traces all 29 functional requirements, but that
coverage does not make it a complete contract or establish conformance.

| Decision | Rules still needed | What it enables |
|---|---|---|
| S01 | Position carrier, position/offset boundary, permitted geographic recording and native interpolation details | Decode authored positions and evaluate time samples |
| S02 | Preserve native coordinates while expressing project placement; define how native and project CRSs interact | Place imported railway and site assets |
| S03 | Unit/up-axis reconciliation, offset basis and scale, approximation bound and applicable extent | Place and orient complete geometry with a stated error budget |
| S04 | Output-CRS selection precedence and permitted geographic outputs | One resolved representation and consistent queries |
| S05 | Dependency declaration, explicit export and subsequent resolution/invalidation | Safe consumption of original and exported scenes |
| S06 | Operation selection, practitioner controls, resources and engine evidence | Real datum/grid/epoch cases and independent-engine comparison |
| S07 | Full binding rules, including empty targets, strength and supported relationship forms | Unambiguous CRS scope across composed scenes |

The choices in `runtime-experiments.md` are now executable. The run includes a
non-Hydra resolver, native Hydra/Storm, real Kit/Fabric, independent Karney
coordinate arithmetic and all eight conditional workflow families. The table
records decisions awaiting approval, not implementation work deferred by this run.

The two position carriers sample and export consistently. The ancestor-after-position
alternative produces a constructed 1,000 m violation. The site-grid calibration
changes the meaning of ordinary offsets compared with Lambert-93. A 20 km footprint
exhibits about 40 m affine-versus-pointwise vertex displacement. These are evidence
for selecting rules, not implicit acceptance of a candidate.

R24's domain remains consequential: a maximum over authored vertices is a finite-set
bound, not a proof over every point of a curved patch. Both placement alternatives
execute; review must choose whether vertices, edges or a continuous surface are the
intended set, and what budget applies.

The original railway GeoJSON also needs its vertical reference and epoch clarified
for survey-accuracy acceptance. Its source identity and coordinate preservation can
be tested independently of those unresolved interpretation questions.
