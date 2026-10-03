# Requirement to candidate trace

| ID | Source requirement | Candidate obligation |
|---|---|---|
| 1 | Self-contained definitions. | WKT identity |
| 2 | Defined once, and describing no object. | single WKT authority |
| 3 | Datum, realization and epoch. | retained WKT metadata |
| 4 | A site's own grid is a CRS like any other. | derived/compound calibration |
| 5 | A discoverable CRS. | source binding preservation |
| 6 | Declared for a subtree, not a prim. | nearest binding composition |
| 7 | Composition agnostic | measurement source association |
| 8 | Brought-in data keeps its coordinates and its CRS. | physical placement under output selection |
| 9 | Positions, and offsets from them. | placement versus post matrix |
| 10 | Offsets along the axes of their position. | orientation and scale |
| 11 | Position or offset, and the scene says which. | direct binding boundary |
| 12 | No angle read as a length. | explicit angle/length domains |
| 13 | One axis mapping. | fixed tuples |
| 14 | Scene conventions stay the scene's. | writer conformance |
| 15 | Placement separate from conformance. | separate conformance child |
| 16 | One CRS out. | requested result meaning |
| 17 | The same answer for every consumer. | common resolved frames |
| 18 | Coordinates back out. | position/query/measurement results |
| 19 | Resolution leaves the scene as authored. | source preservation and export |
| 20 | Positions between recorded moments. | source interpolation |
| 21 | Never placed by a guess. | whole-result failures |
| 22 | A CRS suited to the project's size. | city/global CRS extent |
| 23 | Detail that does not depend on location. | double anchor and local floats |
| 24 | Extent under one position is bounded and stated. | sampled finite-domain discrepancy; certified bounds unresolved |
| 25 | Additive for consumers that ignore it. | unaware-reader invariance |
| 26 | Declares its dependency. | writer dependency declaration |
| 27 | Checkable before use. | stock authored validator |
| 28 | A result says what produced it. | operation and accuracy result |
| 29 | Implementable from the text alone. | independent runtimes; shared PROJ disclosed |
| 30 | Measurements remain usable as data. | measurement values/times/index preservation |
| 31 | Same definition, same meaning. | lexical WKT normal form |

No implementation field may be justified solely by this table. Read the functional rationale and candidate necessity together. R24 is not claimed settled by sampled tests.
