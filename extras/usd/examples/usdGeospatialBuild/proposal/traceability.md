# Derivation from the shared geospatial proposal

Authority: full proposal snapshot at `39c8fb816a9113b14c8f64b020270724b8357312`, retained verbatim in [proposal-source.txt](proposal-source.txt). This derivation records defined behavior and missing contracts. It is not an alternative specification.

| Requirement | Defined contract reference | Current evidence or limitation | Remaining categories |
|---|---|---|---|
| 1. Self-contained definitions | proposal-source.txt:570 | CRS discovery/composition only | G05 |
| 2. Defined once, and describing no object | proposal-source.txt:583 | CRS discovery/composition only | G05, G06 |
| 3. Datum, realization and epoch | proposal-source.txt:600 | Dependent resolution not executed in this run | G05 |
| 4. A site's own grid is a CRS like any other | proposal-source.txt:612 | Dependent resolution not executed in this run | No new missing contract identified here |
| 5. A discoverable CRS | proposal-source.txt:656 | CRS discovery/composition only | G03, G06 |
| 6. Declared for a subtree, not a prim | proposal-source.txt:666 | CRS discovery/composition only | G03, G06 |
| 7. Composition agnostic | proposal-source.txt:677 | CRS discovery/composition only | G06, G07 |
| 8. Brought-in data keeps its coordinates and its CRS | proposal-source.txt:687 | CRS discovery/composition only | G03 |
| 9. Positions, and offsets from them | proposal-source.txt:713 | Dependent resolution not executed in this run | G02, G03 |
| 10. Offsets along the axes of their position | proposal-source.txt:731 | Dependent resolution not executed in this run | G02 |
| 11. Position or offset, and the scene says which | proposal-source.txt:750 | Dependent resolution not executed in this run | G02, G03 |
| 12. No angle read as a length | proposal-source.txt:767 | Dependent resolution not executed in this run | G02, G04, G06, G10 |
| 13. One axis mapping | proposal-source.txt:781 | Dependent resolution not executed in this run | G04 |
| 14. Scene conventions stay the scene's | proposal-source.txt:794 | CRS discovery/composition only | G02, G04 |
| 15. Placement separate from conformance | proposal-source.txt:807 | Dependent resolution not executed in this run | G02, G03 |
| 16. One CRS out | proposal-source.txt:819 | Dependent resolution not executed in this run | G03, G04 |
| 17. The same answer for every consumer | proposal-source.txt:839 | Dependent resolution not executed in this run | G04, G08 |
| 18. Coordinates back out | proposal-source.txt:852 | Dependent resolution not executed in this run | G04, G06, G08, G09 |
| 19. Resolution leaves the scene as authored | proposal-source.txt:867 | CRS discovery/composition only | G03, G06, G07, G09 |
| 20. Positions between recorded moments | proposal-source.txt:886 | Dependent resolution not executed in this run | G02, G09 |
| 21. Never placed by a guess | proposal-source.txt:903 | CRS discovery/composition only | G05, G06, G08, G10 |
| 22. A CRS suited to the project's size | proposal-source.txt:952 | Dependent resolution not executed in this run | G08, G10 |
| 23. Detail that does not depend on location | proposal-source.txt:965 | Dependent resolution not executed in this run | G08 |
| 24. Extent under one position is bounded and stated | proposal-source.txt:974 | Dependent resolution not executed in this run | G08 |
| 25. Additive for consumers that ignore it | proposal-source.txt:989 | CRS discovery/composition only | G07 |
| 26. Declares its dependency | proposal-source.txt:999 | Dependent resolution not executed in this run | G07 |
| 27. Checkable before use | proposal-source.txt:1010 | CRS discovery/composition only | G05, G06, G07, G09 |
| 28. A result says what produced it | proposal-source.txt:1025 | Dependent resolution not executed in this run | G05, G08 |
| 29. Implementable from the text alone | proposal-source.txt:1043 | Dependent resolution not executed in this run | G05, G08 |
| 30. Measurements remain usable as data | proposal-source.txt:935 | Dependent resolution not executed in this run | G06, G09, G10 |
| 31. Same definition, same meaning | proposal-source.txt:636 | Dependent resolution not executed in this run | G05 |

The discovery evidence supports only the listed portions of requirements. It does not claim that every requirement without a newly identified gap is fully verified. The exact source clauses, decided outcomes and narrow missing contracts are recorded in proposal-quality.json.
