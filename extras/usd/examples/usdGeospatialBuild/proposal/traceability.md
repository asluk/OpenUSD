# Requirement traceability

Authority: the entire unpublished local candidate, SHA-256 `a5444966c41e3a067d7c4db5b2e9a300a08b17fcce377bd6fb24727b390e6904`, based on `39c8fb816a9113b14c8f64b020270724b8357312`. [proposal-source.txt](proposal-source.txt) is the sole proposal authority. These files record derivation and do not add normative choices. Proposed details remain under author review.

| Requirement | Source line | Dependent open contracts |
|---|---:|---|
| R1 Self-contained definitions | 588 | None identified |
| R2 Defined once, and describing no object | 601 | G06 |
| R3 Datum, realization and epoch | 618 | None identified |
| R4 A site's own grid is a CRS like any other | 630 | None identified |
| R5 A discoverable CRS | 676 | G03, G06 |
| R6 Declared for a subtree, not a prim | 686 | G03, G06 |
| R7 Composition agnostic | 697 | G06, G07 |
| R8 Brought-in data keeps its coordinates and its CRS | 707 | G03 |
| R9 Positions, and offsets from them | 733 | G03 |
| R10 Offsets along the axes of their position | 751 | None identified |
| R11 Position or offset, and the scene says which | 770 | G03 |
| R12 No angle read as a length | 787 | G04, G06 |
| R13 One axis mapping | 801 | G04 |
| R14 Scene conventions stay the scene's | 818 | G04 |
| R15 Placement separate from conformance | 831 | G03 |
| R16 One CRS out | 843 | G03, G04 |
| R17 The same answer for every consumer | 863 | G04 |
| R18 Coordinates back out | 876 | G04, G06 |
| R19 Resolution leaves the scene as authored | 891 | G03, G06, G07 |
| R20 Positions between recorded moments | 910 | None identified |
| R21 Never placed by a guess | 927 | G06 |
| R22 A CRS suited to the project's size | 976 | None identified |
| R23 Detail that does not depend on location | 989 | None identified |
| R24 Extent under one position is bounded and stated | 998 | None identified |
| R25 Additive for consumers that ignore it | 1013 | G07 |
| R26 Declares its dependency | 1023 | G07 |
| R27 Checkable before use | 1034 | G06, G07 |
| R28 A result says what produced it | 1049 | None identified |
| R29 Implementable from the text alone | 1067 | None identified |
| R30 Measurements remain usable as data | 959 | G06 |
| R31 Same definition, same meaning | 654 | None identified |

Partial evidence does not certify a complete requirement. Every fresh control and its result is recorded in delivery/run-report.json. Ordinary transforms are post-placement, writer convention repairs remain ordinary USD authoring, and independent source scope remains composed-data based.
