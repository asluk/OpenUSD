#!/usr/bin/env python3
"""
test_binding_semantics.py -- proves crs:binding has real MaterialBindingAPI-style
strength + purpose semantics (review fix F.1), not just a bare relationship.

Hierarchy:
  /World/CRS/{GeoA, GeoB, GeoC}   three distinct CRS prims (used as identity markers)
  /World/Region            crs:binding -> GeoA  (all-purpose; default weaker)
    /World/Region/Sub      crs:binding -> GeoB  (nearer binding)
      /World/Region/Sub/Pt           crs:position only (no own binding)
  /World/Strong            crs:binding -> GeoA  bindCRSAs=strongerThanDescendants
    /World/Strong/Sub      crs:binding -> GeoB  (nearer but should LOSE)
      /World/Strong/Sub/Pt           crs:position only
  /World/Purp              crs:binding -> GeoA, crs:binding:render -> GeoC
    /World/Purp/Pt                   crs:position only

Assertions (we check WHICH CRS prim is selected, by path):
  S1 default weaker-than-descendants: Pt under Region/Sub resolves to GeoB (nearest).
  S2 strongerThanDescendants ancestor: Pt under Strong/Sub resolves to GeoA (ancestor
     overrides the nearer GeoB) -> proves strength metadata is honoured.
  S3 purpose: resolving Purp/Pt with purpose='render' selects GeoC (the
     crs:binding:render), while all-purpose selects GeoA.
  S4 purpose fallback: resolving Purp/Pt with purpose='edit' (no such binding)
     falls back to the all-purpose GeoA.
Each assertion would FAIL if the resolver ignored strength/purpose (teeth).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _schema_setup  # noqa
from pyproj import CRS
from pxr import Usd, UsdGeom, Sdf, Gf
import resolve_runtime as rr

GEO = CRS.from_epsg(4979)


def mkcrs(stage, path):
    p = stage.DefinePrim(path, "CoordinateReferenceSystem")
    p.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                      Sdf.VariabilityUniform).Set(GEO.to_wkt(version="WKT2_2019"))
    p.CreateAttribute("crs:displayName", Sdf.ValueTypeNames.String, False).Set(path)
    return p


def bind(prim, crs_prim, purpose="", strength=None):
    name = "crs:binding" + (f":{purpose}" if purpose else "")
    rel = prim.CreateRelationship(name, False)
    rel.SetTargets([crs_prim.GetPath()])
    if strength:
        rel.SetMetadata("bindCRSAs", strength)
    return rel


def pos(prim):
    prim.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False) \
        .Set(Gf.Vec3d(-117.0, 34.0, 0.0))
    return prim


def main(out="out/_test_binding.usda"):
    stage = Usd.Stage.CreateNew(out)
    w = UsdGeom.Xform.Define(stage, "/World"); stage.SetDefaultPrim(w.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/CRS")
    A = mkcrs(stage, "/World/CRS/GeoA")
    B = mkcrs(stage, "/World/CRS/GeoB")
    C = mkcrs(stage, "/World/CRS/GeoC")

    # S1: default weaker -> nearest wins
    region = UsdGeom.Xform.Define(stage, "/World/Region").GetPrim(); bind(region, A)
    sub = UsdGeom.Xform.Define(stage, "/World/Region/Sub").GetPrim(); bind(sub, B)
    pt1 = UsdGeom.Xform.Define(stage, "/World/Region/Sub/Pt").GetPrim(); pos(pt1)

    # S2: stronger ancestor overrides nearer descendant
    strong = UsdGeom.Xform.Define(stage, "/World/Strong").GetPrim()
    bind(strong, A, strength="strongerThanDescendants")
    s_sub = UsdGeom.Xform.Define(stage, "/World/Strong/Sub").GetPrim(); bind(s_sub, B)
    pt2 = UsdGeom.Xform.Define(stage, "/World/Strong/Sub/Pt").GetPrim(); pos(pt2)

    # S3/S4: purpose
    purp = UsdGeom.Xform.Define(stage, "/World/Purp").GetPrim()
    bind(purp, A); bind(purp, C, purpose="render")
    pt3 = UsdGeom.Xform.Define(stage, "/World/Purp/Pt").GetPrim(); pos(pt3)

    # S5/S6/S7: collection-based binding.
    # /World/Coll has a collection 'sites' including only In1/In2 (not Out).
    # A collection binding crs:binding:collection:sites -> (collPath, GeoC).
    coll_root = UsdGeom.Xform.Define(stage, "/World/Coll").GetPrim()
    coll = Usd.CollectionAPI.Apply(coll_root, "sites")
    in1 = UsdGeom.Xform.Define(stage, "/World/Coll/In1").GetPrim(); pos(in1)
    in2 = UsdGeom.Xform.Define(stage, "/World/Coll/In2").GetPrim(); pos(in2)
    outp = UsdGeom.Xform.Define(stage, "/World/Coll/Out").GetPrim(); pos(outp)
    coll.CreateIncludesRel().SetTargets([in1.GetPath(), in2.GetPath()])
    crel = coll_root.CreateRelationship("crs:binding:collection:sites", False)
    crel.SetTargets([coll.GetCollectionPath(), C.GetPath()])

    # S7 (rule [4]): collection vs direct on the SAME prim. Put BOTH a direct
    # binding (GeoB) and a collection binding (GeoA, including this prim) on the
    # same prim Same; the collection must win over the direct binding.
    same = UsdGeom.Xform.Define(stage, "/World/Same").GetPrim(); pos(same)
    same_coll = Usd.CollectionAPI.Apply(same, "self")
    same_coll.CreateIncludesRel().SetTargets([same.GetPath()])
    bind(same, B)  # direct -> GeoB
    screl = same.CreateRelationship("crs:binding:collection:self", False)
    screl.SetTargets([same_coll.GetCollectionPath(), A.GetPath()])  # collection -> GeoA

    stage.GetRootLayer().Save()

    def sel(prim, purpose=""):
        _, crs_path, bound, strength = rr.crs_of_prim(prim, purpose)
        return str(crs_path), str(bound), strength

    s1 = sel(pt1)
    s2 = sel(pt2)
    s3 = sel(pt3, "render")
    s4 = sel(pt3, "edit")
    s3all = sel(pt3, "")
    s5 = sel(in2)          # collection member, no direct binding -> GeoC
    s6 = sel(outp)         # NOT a member -> no binding (None)
    s7 = sel(same)         # same prim: direct GeoB + collection GeoA -> GeoA wins (rule [4])

    print(f"[author] {out}")
    print(f"S1 Region/Sub/Pt (default weaker)        -> {s1[0]}  (want GeoB)")
    print(f"S2 Strong/Sub/Pt (ancestor stronger)     -> {s2[0]}  (want GeoA, via {s2[1]} {s2[2]})")
    print(f"S3 Purp/Pt purpose=render                -> {s3[0]}  (want GeoC)")
    print(f"S4 Purp/Pt purpose=edit (no binding)     -> {s4[0]}  (want GeoA fallback)")
    print(f"   Purp/Pt all-purpose                   -> {s3all[0]} (want GeoA)")
    print(f"S5 Coll/In2 (collection member)          -> {s5[0]}  (want GeoC)")
    print(f"S6 Coll/Out (NOT a member)               -> {s6[0]}  (want None)")
    print(f"S7 Same (direct GeoB + coll GeoA, same prim) -> {s7[0]}  (want GeoA; collection beats direct, rule [4])")

    p1 = s1[0].endswith("GeoB")
    p2 = s2[0].endswith("GeoA") and s2[2] == "strongerThanDescendants"
    p3 = s3[0].endswith("GeoC")
    p4 = s4[0].endswith("GeoA") and s3all[0].endswith("GeoA")
    p5 = s5[0].endswith("GeoC")
    p6 = s6[0] == "None"
    p7 = s7[0].endswith("GeoA")
    ok = all([p1, p2, p3, p4, p5, p6, p7])
    print()
    print(f"[check] S1 nearest-wins (weaker default):        {p1}")
    print(f"[check] S2 strongerThanDescendants honoured:     {p2}")
    print(f"[check] S3 purpose-specific binding selected:    {p3}")
    print(f"[check] S4 purpose fallback to all-purpose:      {p4}")
    print(f"[check] S5 collection member resolves CRS:       {p5}")
    print(f"[check] S6 non-member gets NO binding:           {p6}")
    print(f"[check] S7 collection beats direct at same prim (rule [4]):  {p7}")
    print("\nRESULT:", "BINDING STRENGTH+PURPOSE+COLLECTION SEMANTICS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or [])))
