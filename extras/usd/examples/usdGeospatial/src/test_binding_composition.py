#!/usr/bin/env python3
"""
test_binding_composition.py -- proves crs:binding resolution respects USD
composition: cross-layer (sublayer) overrides and relationship list-editing
(prepend/append/delete) on binding targets. Closes the self-audit gap "no
cross-layer / list-edited binding coverage."

The resolver reads composed relationship targets (UsdRelationship.GetTargets()
returns the composed, list-edited result), so these should Just Work -- this test
makes that guarantee explicit and regression-proof.

Cases:
  L1 sublayer override: a weak sublayer binds Site->GeoA; a stronger sublayer
     re-binds Site->GeoB. Composed target must be GeoB (stronger layer wins).
  L2 list-edit prepend: base binds ->GeoA; an over prepends ->GeoB. With a
     single-target binding the prepended (stronger) target GeoB is what
     GetTargets()[0] yields; resolver must use GeoB.
  L3 list-edit delete: base binds ->GeoA; an over deletes that target and adds
     ->GeoC. Composed targets must be [GeoC] (GeoA removed), resolver uses GeoC.
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


def sel_path(prim):
    _, crs_path, _, _ = rr.crs_of_prim(prim)
    return str(crs_path) if crs_path else "None"


def case_sublayer_override(tmpdir):
    """L1: stronger sublayer re-binds to GeoB over weaker sublayer's GeoA."""
    weak = Sdf.Layer.CreateNew(os.path.join(tmpdir, "weak.usda"))
    strong = Sdf.Layer.CreateNew(os.path.join(tmpdir, "strong.usda"))
    root = Sdf.Layer.CreateNew(os.path.join(tmpdir, "root_L1.usda"))
    # root sublayers: strong first (strongest), then weak
    root.subLayerPaths.append(strong.identifier)
    root.subLayerPaths.append(weak.identifier)
    stage = Usd.Stage.Open(root)
    UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
    UsdGeom.Scope.Define(stage, "/World/CRS")
    a = mkcrs(stage, "/World/CRS/GeoA")
    b = mkcrs(stage, "/World/CRS/GeoB")
    site = UsdGeom.Xform.Define(stage, "/World/Site").GetPrim()
    site.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False).Set(Gf.Vec3d(-117, 34, 0))
    # author the weak binding -> GeoA in the weak layer
    with Usd.EditContext(stage, weak):
        site.CreateRelationship("crs:binding", False).SetTargets([a.GetPath()])
    # author the strong binding -> GeoB in the strong layer
    with Usd.EditContext(stage, strong):
        site.CreateRelationship("crs:binding", False).SetTargets([b.GetPath()])
    got = sel_path(site)
    return got.endswith("GeoB"), got


def case_list_prepend(tmpdir):
    """L2: over prepends a stronger target GeoB before base GeoA."""
    base = Sdf.Layer.CreateNew(os.path.join(tmpdir, "base_L2.usda"))
    over = Sdf.Layer.CreateNew(os.path.join(tmpdir, "over_L2.usda"))
    root = Sdf.Layer.CreateNew(os.path.join(tmpdir, "root_L2.usda"))
    root.subLayerPaths.append(over.identifier)   # stronger
    root.subLayerPaths.append(base.identifier)
    stage = Usd.Stage.Open(root)
    UsdGeom.Xform.Define(stage, "/World"); stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
    UsdGeom.Scope.Define(stage, "/World/CRS")
    a = mkcrs(stage, "/World/CRS/GeoA")
    b = mkcrs(stage, "/World/CRS/GeoB")
    site = UsdGeom.Xform.Define(stage, "/World/Site").GetPrim()
    site.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False).Set(Gf.Vec3d(-117, 34, 0))
    with Usd.EditContext(stage, base):
        site.CreateRelationship("crs:binding", False).SetTargets([a.GetPath()])
    with Usd.EditContext(stage, over):
        rel = site.CreateRelationship("crs:binding", False)
        rel.GetForwardedTargets()  # touch
        # prepend GeoB -> becomes the strongest/first composed target
        rel.AddTarget(b.GetPath(), Usd.ListPositionFrontOfPrependList)
    targets = [str(t) for t in site.GetRelationship("crs:binding").GetTargets()]
    got = sel_path(site)
    return got.endswith("GeoB"), f"{got} targets={targets}"


def case_list_delete(tmpdir):
    """L3: over deletes base target GeoA and adds GeoC."""
    base = Sdf.Layer.CreateNew(os.path.join(tmpdir, "base_L3.usda"))
    over = Sdf.Layer.CreateNew(os.path.join(tmpdir, "over_L3.usda"))
    root = Sdf.Layer.CreateNew(os.path.join(tmpdir, "root_L3.usda"))
    root.subLayerPaths.append(over.identifier)
    root.subLayerPaths.append(base.identifier)
    stage = Usd.Stage.Open(root)
    UsdGeom.Xform.Define(stage, "/World"); stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
    UsdGeom.Scope.Define(stage, "/World/CRS")
    a = mkcrs(stage, "/World/CRS/GeoA")
    c = mkcrs(stage, "/World/CRS/GeoC")
    site = UsdGeom.Xform.Define(stage, "/World/Site").GetPrim()
    site.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False).Set(Gf.Vec3d(-117, 34, 0))
    with Usd.EditContext(stage, base):
        site.CreateRelationship("crs:binding", False).SetTargets([a.GetPath()])
    with Usd.EditContext(stage, over):
        rel = site.CreateRelationship("crs:binding", False)
        rel.RemoveTarget(a.GetPath())
        rel.AddTarget(c.GetPath())
    targets = [str(t) for t in site.GetRelationship("crs:binding").GetTargets()]
    got = sel_path(site)
    return (got.endswith("GeoC") and not any("GeoA" in t for t in targets)), f"{got} targets={targets}"


def main(_=None):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="crs_comp_")
    l1, i1 = case_sublayer_override(tmp)
    l2, i2 = case_list_prepend(tmp)
    l3, i3 = case_list_delete(tmp)
    print(f"L1 sublayer override (want GeoB):  {i1}")
    print(f"L2 list-edit prepend (want GeoB):  {i2}")
    print(f"L3 list-edit delete  (want GeoC):  {i3}")
    print()
    print(f"[check] L1 stronger sublayer wins:        {l1}")
    print(f"[check] L2 prepended target is strongest: {l2}")
    print(f"[check] L3 deleted target removed:        {l3}")
    ok = l1 and l2 and l3
    print("\nRESULT:", "BINDING COMPOSITION (cross-layer + list-edit) ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or [])))
