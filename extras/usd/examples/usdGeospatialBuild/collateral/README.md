# Current delivery derivation

The README and slides assess the proposal for readers who may know neither geospatial concepts nor OpenUSD. Explain the problem before naming schema fields. Each demonstration must identify the proposed rule and independently expected result, the recorded observation, what that observation establishes about the proposal, and its limits. A beautiful image or a passing test count alone supplies no completeness claim.

`derive_contract_delivery.py --run <executed-run-directory>` verifies the frozen source and packages recorded evidence. `human_delivery.py` binds `delivery-assessment.json` to the exact proposal, immutable receipt and `delivery/independent-audit.json`, then generates the README and story. Changed evidence requires reassessing the explanations; historical successes cannot hide later failures. `contract_slides.mjs` derives the editable deck from that README/story. `verify_contract_delivery.py` checks claims, assessment coverage, hashes, native elements and the final inspection record.

The assessment distinguishes proposed definitions awaiting agreement, genuinely missing or conflicting meanings, implementation failures, unverified coverage and deferred capabilities. Source data remains authoritative. Do not promote a prototype shortcut into the proposal to improve a delivery status.

Images state whether they illustrate proposed behavior, plot synthetic data or show recorded consumer output. Captions explain the visible change and its connection to proposal quality. The main explanation uses plain language and a small number of readable comparisons; supporting sections carry precise fields, coordinates, counts and provenance. Speaker notes bind each case to its functional requirements, proposal clause and evidence hashes.

Before delivery, inspect the rendered README and every final slide: can the reader understand the problem, the depicted change, the expected behavior and the implication without specialist vocabulary? Verify legibility and layout as well as factual accuracy. Record who performed that inspection and bind it to the final artifacts. An agent's inspection is not evidence of a user comprehension test. Automated structural checks are necessary safeguards, not a proof of readability.

Python/C++ placement, Omniverse stage geometry integration and native Hydra rendering of ordinary USD bakes are distinct paths. Shared PROJ, shared external decoding and Omniverse's reused Python algorithm remain explicit. No output claim follows from an application name. No upstream issue/PR links enter delivery.

Earlier generators remain historical code and are excluded from the active delivery path. Current artifacts are replaced together; history retains prior evidence.

## Native build prerequisite

The runner rebuilds an already configured native build directory; it does not configure an empty one. Use a Windows C++ developer shell, a matching OpenUSD SDK/Python ABI, CMake and Ninja. Set installed dependency paths, then configure:

```powershell
$taskUsdSdk = 'C:/path/to/OpenUSD/inst'
$taskProj = 'C:/path/to/TIFF-enabled-PROJ'
$taskNativePython = 'C:/path/to/OpenUSD-matching-Python'
$taskNativeBuild = 'C:/path/to/native-build'
cmake -S native -B $taskNativeBuild -G Ninja -DCMAKE_BUILD_TYPE=Release "-Dpxr_DIR=$taskUsdSdk" "-DUSD_SDK=$taskUsdSdk" "-DPython3_ROOT_DIR=$taskNativePython" "-DCMAKE_PREFIX_PATH=$taskUsdSdk;$taskProj"
```

Pass that directory as `run.py --native-build`, with the same SDK, PROJ and Python paths. `run.py --help` lists the remaining host, resource, dependency and fresh-output arguments. Load the TIFF-enabled PROJ DLL before an SDK copy without TIFF support. The execution receipt records actual library/database/grid hashes and versions; substituting dependencies requires a new run. The evidence records the installed Windows environment, not a dependency-free or cross-platform build.
