# Fresh derivation record

The complete proposal at e519199 is the authority. The previous implementation
is excluded from generation inputs. Generic USD supplies composition, property
resolution and ordinary transforms. PROJ supplies geodetic operations, operation
selection and attributed accuracy. Those libraries are shared dependencies,
not evidence of independent geodetic truth.

| Derived contract | Proposal section | Independently specified distinguishing case |
|---|---|---|
| Seven input properties and schema roles | Authored properties; External measurement association | Wrong type, missing/block position, orientation fallback, forbidden inherited or measurement placement fields |
| WKT authority and lexical identity | WKT string normalization | Exact decimal rewrite and quoted text preservation; valid non-normal reader warning; epoch wrapper rejection |
| Absolute placement and child offsets | Evaluation | At WGS84 equator, east/north/up local offsets map to geocentric Y/Z/X respectively; nested direct anchor excludes ancestor translation |
| Heading/pitch/roll and interpolation | Geospatial model attitude; Evaluation | Heading 90 faces east; positive pitch raises forward; exact half-turn interior fails; source longitude midpoint stays on ellipsoid |
| Fixed working adjustment | Evaluation | A 10 m east adjustment retains physical placement in a second requested CRS; child movement follows model attitude |
| Semantic axes and unit mapping | Position components | Latitude-first WKT returns longitude/latitude; Y-up maps x/-z/y; feet map to metres |
| Coordinate queries and Cartesian scene results | Queries, scene charts and instances | Geographic coordinates remain angles, scene positions use ECEF; output origin appears only in representation |
| Independent instances | Queries, scene charts and instances | Identity instance keeps prototype placement; nonidentity offset uses instancer-local frame and requires valid inverse |
| External measurements | External measurement association | Coordinate dimensions deliberately permuted; values/masks/times stay paired; absent metadata fails |
| Profiles | Dependency declaration with Profiles | Hard, qualified known-none and unknown discovery without loading payload; stale empty claim fails publisher audit |
| Explicit bake | Explicit export and sampling | Recorded double origin once; aware/unaware readers include ordinary ancestors and resets; selected samples reread in a fresh process |
| Failure and precision | Observable outcomes; Extent and result comparison | Missing grids, invalid units/axes, non-finite coordinates and unsupported continuous-domain certificates report failure |

Implementation choices may select algorithms, data structures and supported
engine operations. They may not choose missing scene meaning. A missing required
meaning is recorded before dependent code and remains a proposal finding.

Initial intake finding: the supplied gfs_t2m.nc contains dimension names but no
CF coordinate-role/unit or grid-mapping metadata. It cannot serve as a conforming
CF association merely because its variables are called lat and lon. The run
must show that failure and use explicitly authored metadata in any derived
illustrative CF copy. The original dataset remains unchanged.
