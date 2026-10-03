# Controls reasoned before implementation

These examples select observable semantics; they are not generated expectations.

1. In one Cartesian metre CRS, an anchor (1000,2000,30), 90-degree Z
   orientation and scale (2,1,1) maps local (3,4,5) to (996,2006,35).
   A post translation (7,8,9) produces (1003,2014,44). A parent ordinary
   translation (100000,0,0) is excluded at the direct binding. A child
   translation (1,0,0) acts in the rotated/scaled model frame.
2. Feet are CRS coordinate units, not geometry units. A source metre asset
   remains one metre long in a US-survey-foot output; its coordinate delta is
   3937/1200 feet. Its rendered delta is one metre in a metre stage.
3. Longitude 2, latitude 49, height 80 is never a mesh point in degrees.
   A local one-metre east displacement has longitude change roughly
   1/(ellipsoid prime-vertical radius * cos(latitude)); use full ellipsoid
   Cartesian conversion as an independently written numerical control.
4. A Cartesian adjustment transported between two differently rotated projected
   systems retains physical placement. Reusing unchanged output-axis numbers
   does not. Compare both candidates after conversion back to one common CRS.
5. A sampled source position (1000,2000,30) at time 0 and (1010,2000,30)
   at time 10 is (1005,2000,30) at time 5 before nonlinear conversion.
6. Whitespace outside WKT quotes and decimal spelling differences normalize
   identically. Whitespace inside a name/remark, changed axes/units/datum and
   a coordinate-metadata wrapper do not disappear.
7. Exported placement is read by a fresh reader without any private resolved
   flag. Applying a post translation a second time is a test failure.
8. Measurement values [10,20] remain paired with their original coordinate
   indices and recorded observation times, including when coordinates move.
9. An unloaded payload's dependency is declared by the assembler. Traversing
   the loaded stage cannot prove absence of a dependency in that payload.
10. Vertex or grid-sample agreement does not certify a surface-wide error bound.
    This remains an explicit result-contract finding rather than a passing test.
11. In a Y-up metre stage, local (0,1,0) means one metre up, and a post
    translation (0,2,0) adds two metres up. Source/output geographic axes do
    not make that ordinary Y displacement a northing or latitude displacement.
    The writer still owns any referenced asset's conformance to the stage.
12. Square-bracket and parenthesis WKT delimiters outside quotes normalize to
    identical text. Parentheses or brackets inside a quoted name remain intact.
13. A broken enclosing binding fails a project adjustment even when the model's
    own source binding is valid. Absence of an enclosing binding permits source
    context; a malformed binding does not.
14. Measurement roles and values with names such as samples:locations and
    observations:temperature resolve and export without a data: prefix. A role
    in an inherited CRS scope receives the same authored checks as a direct one.
15. An explicit output wins over the defaultPrim's CRS. Without an explicit
    output, the composed defaultPrim binding supplies the default or fails visibly.
16. Leaf bounds in a length output include the primitive's ordinary local extent
    and use its resolved placement. An independently bound child does not add
    its parent's position when queried relative to another resolved frame.
