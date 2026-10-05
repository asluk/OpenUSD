The revised local geospatial proposal gives concrete placement and WKT string-normalization contracts. Four missing contracts still stop full model-placement derivation: project-adjustment frame, stage/basis mapping, measurement-coordinate association and dependency declaration. Candidate details remain under author review.

Fresh evidence: 64 tests and 504 reader/query checks passed across headless OpenUSD, native OpenUSD and a live OV stage. Readers preserve source data and agree on France, Colorado and analytic ECEF anchor-origin conversions. The source-first interpolation example exposes a 971.421 m error from interpolating only converted endpoints. Readers share PROJ, so this is no independent geodetic-engine certification.

Full model geometry, Hydra placement and resolved-scene export remain stopped. The README leads with proposal quality and separates proposed contracts, observed evidence and unresolved semantics.

[README](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/README.md) · [Editable slides](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/delivery/geospatial-build.pptx) · [PDF](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/delivery/geospatial-build.pdf) · [Receipt](https://github.com/asluk/OpenUSD/blob/aluk/geospatial-build-loop/extras/usd/examples/usdGeospatialBuild/delivery/run-report.json)

Candidate SHA-256: `a5444966c41e3a067d7c4db5b2e9a300a08b17fcce377bd6fb24727b390e6904`. Executed source: `6d8323764ad44953887cac9781375b7c7176e928`. Proposal publication and group communications remain separate from fork delivery.
