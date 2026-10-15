# Proposal-derived build loop

The implementation in this directory is an output of a fresh run. It is not a
source template for the next implementation.

1. Pin and read the complete proposal, including requirements, model, runtime
   rules, examples and normative references. Verify the Git blob and file hash.
2. Trace each initial-scope requirement from authored facts to observable behavior
   and an independently derivable expectation. Distinguish complete proposed
   conventions from group adoption. A missing necessary meaning stops that
   dependent implementation and triggers a concrete proposal repair.
3. Generate new schema, full readers, fixtures and tests in an isolated output
   directory. Original data and reviewed neutral tools may be reused. Previous
   geospatial source, fixture logic and expected results may not seed generation.
4. Execute original-data, composition, interpolation, chart/reset/instance,
   dimensional association, Profiles, failure, precision and explicit-bake
   controls. Run actual consumer sinks and distinguish placement readers from
   consumers of their outputs. A reader pair using PROJ is not an independent
   geodetic oracle.
5. Reverse-audit every authored field, implied behavior and result claim against
   the pinned text. Repair implementation defects against that authority. Never
   add a schema fact or normative rule merely to excuse a shortcut. A normative
   authority change requires a fresh regeneration. Report unsupported or
   unverified prototype coverage separately from model gaps and adoption.
6. Write a standalone human README that leads with proposal quality and explicit
   limits, then demonstrates working behavior with actual outputs. Give USD
   Profiles a concrete main-story example with author/publisher/consumer roles,
   coverage states and an unloaded-content proof. Derive the review body and
   editable deck/PDF from that README. Render and inspect the README and each
   slide. Dataset and visualization provenance are part of the evidence.
7. Freeze source/evidence hashes, verify source preservation and collateral
   consistency, package a reviewable local branch and commit it. Push, post or
   send only when authorized. Keep any OSRB review snapshot fixed independently
   of this evolving development candidate.

Checkpoint every phase and substantive finding so a crash or sleep does not
restart work or turn an incomplete run into a claimed success. Public companion
collateral must not backlink to other upstream issues or pull requests.
