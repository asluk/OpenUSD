# Implementation and authority audit

The exact local candidate is the only proposal authority. All 31 requirements are reviewed, and only four missing contracts stop dependent derivation.

Current fixtures author only crs:wkt, crs:position, crs:orientation and crs:scale. Reference binding and composed apiSchemas follow the candidate. No crs:coordinateEpoch, crs:binding relationship, crs:coordinateProperties role carrier or customLayerData geospatial flag is accepted as an authority. Source layers are compared before and after each consumer.

Each USD reader independently reads composition and placement fields. Projection readers share PROJ, so agreement is not independent geodetic-engine certification. Lexical expectations are hand-specified and preserve exact numeric text rather than using an engine writer as a golden file. Provider CSV controls are explicitly rounding/intake references.

Model-axis frames, project-adjustment frames, measurement associations and dependency declarations are not guessed. Direct origin queries explicitly exclude ordinary adjustments and geometry. Old full placement/render/export evidence is historical and is not reused in this run. Numerical tolerances are prescribed in case definitions before execution. Sampling, continuous extent, geographic-distance comparison and complete validators have no passing claim from these partial controls.

Postimplementation audit checks reverse coverage too: remaining untested required results retain requirements_build_complete=false even when controls pass. The receipt must separate tests passed, semantics missing, implementation limits and partner adoption.
