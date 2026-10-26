# Review the geospatial companion

The proposal defines the inputs and observable behavior. This package tests
whether those rules can be implemented and remains a candidate OpenUSD
contribution. Proposal review comes first; readable, reviewable code is required
for this evidence to be credible too.

## Follow the implementation

Read these responsibilities in order. The Python and C++ placement readers are
separate implementations; neither calls the other for placement. The Python
publication helper uses the existing native Profiles API because the recorded
Python USD build lacks those bindings.

| Responsibility | Python | C++ / schema |
|---|---|---|
| Authored input fields and schema identities | — | [generatedSchema.usda](schema/generatedSchema.usda), [plugInfo.json](schema/plugInfo.json) |
| WKT normalization, height reference and offline PROJ operations | [crs.py](src_py/crs.py) | [crs.cpp](native/crs.cpp), [declarations](native/crs.h) |
| Composed binding, physical orientation and ordered point map | [placement.py](src_py/placement.py): `ModelMap.forward` | [placement.cpp](native/placement.cpp): `ModelPlacement::Forward` |
| Queries and point-instancer occurrences | [reader.py](src_py/reader.py): `Reader.points`, `instance_points` | [placement.cpp](native/placement.cpp): `PlacementEvaluator`; [resolve.cpp](native/resolve.cpp) is only the JSON command-line adapter |
| Native measurement associations | [domains.py](src_py/domains.py): CF, GeoJSON, GeoTIFF | The C++ coordinate query receives associated coordinates; it does not independently decode these formats |
| Explicit ordinary-USD bake | [bake.py](src_py/bake.py) | The same bake driver can use either placement reader; it is not an independent C++ exporter |
| Profiles authoring, summary read and publication validation | [profiles.py](src_py/profiles.py) | [profiles.cpp](native/profiles.cpp) uses native `ClaimsAPI` |

[math_util.py](src_py/math_util.py) contains basis/quaternion helpers.
[common.py](src_py/common.py) and [common.h](native/common.h) contain validation
and small support types. Interfaces in these files are example interfaces,
not proposed standard USD APIs.

For the most important ordering check, follow a point through `forward`:
descendant USD transform → stage units/axes → physical ENU orientation → CRS
placement → anchor adjustment in the fixed working chart → requested output.
The comments identify the matrix conventions and reset behavior. The
[requirement trace](audit/source-contract.md) connects these meanings to tests.

## Read the tests, then inspect their inputs and results

[tests/run.py](tests/run.py) lists the 19 contract groups at its `run` entry point.
Named cases cover provider controls, transform order and resets, composition,
interpolation, instances, native associations, precision, Profiles and visible
failures. [tests/fixtures.py](tests/fixtures.py) authors the small counterexamples.
[REPRODUCE.md](REPRODUCE.md) records build and execution commands and dependencies.

| Supporting files | What to review there |
|---|---|
| `inputs/original/` | Supplied data, companion WKT, provenance and licenses; original bytes are preserved |
| `inputs/authored/` | Generated examples and ordinary bakes; inspect relevant examples alongside their fixture generator |
| `evidence/` | Generated numerical reports, figures and consumer readbacks; [checks.json](evidence/checks.json) and [full-data.json](evidence/full-data.json) are the entry points |
| `audit/` | Tested proposal revision, original/resource hashes, source inventory and coverage limitations |
| `delivery/` | Evidence/figure generation, actual consumer checks and the README-derived deck |

Generated results, authored fixtures and deck outputs are marked as generated
in [.gitattributes](.gitattributes), so GitHub can collapse their diffs. They are
still present and expandable. Supplied original data is identified separately
as vendored data. Schema resources, readers, fixture generators and tests remain
ordinary source files in review.

## Delivery quality gate

Run `python tests/reviewability.py` before freezing a delivery. It checks the
file inventory, review links, stable schema/plugin identities, explicit Python
imports, statement layout and generated-file attributes. Its report is
[evidence/reviewability.json](evidence/reviewability.json).

Those checks cannot establish that code is understandable. Delivery also
requires reading the final PR diff in the order above: names must identify
coordinate frames and roles, numerical steps must be explainable, and the PR
body must lead a reviewer to the actual implementation and its limits. A failed
readability review stops delivery even if every numerical test passes.
