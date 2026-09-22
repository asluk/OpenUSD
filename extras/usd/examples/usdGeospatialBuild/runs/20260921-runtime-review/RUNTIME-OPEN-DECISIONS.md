# Decisions needed to complete the runtime description

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

The current binding inspector's names and lookup policies are experiments, not
decisions on this table. The current WGS 84 reporting adapter is not a scene
resolver. The intended non-Hydra runtime and Hydra adapter are both still to be
built from the prose contract. Hydra/non-Hydra agreement and agreement across
independent coordinate engines are separate evidence requirements.

The original railway GeoJSON also needs its vertical reference and epoch clarified
for survey-accuracy acceptance. Its source identity and coordinate preservation can
be tested independently of those unresolved interpretation questions.
