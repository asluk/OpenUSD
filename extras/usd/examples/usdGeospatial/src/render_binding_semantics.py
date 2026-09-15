#!/usr/bin/env python3
"""
render_binding_semantics.py -- generate docs/binding_semantics.png, a data-driven
figure of crs:binding resolution semantics. The "winner" cells are computed by the
ACTUAL resolver (resolve_runtime.crs_of_prim) against a constructed stage, so the
figure can never drift from the implementation -- if the resolver changes, rerun
and the picture changes with it.

Panels:
  (1) Per-prim precedence ladder (UsdShadeMaterialBindingAPI parity), strongest->weakest:
      purpose-collection > purpose-direct > all-collection > all-direct. Rule [4]:
      at the SAME prim, a collection binding beats a direct binding.
  (2) Namespace strength: nearest binding wins by default (weakerThanDescendants);
      an ancestor marked strongerThanDescendants overrides closer descendants.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _schema_setup  # noqa
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pyproj import CRS
from pxr import Usd, UsdGeom, Sdf, Gf
import resolve_runtime as rr

GEO = CRS.from_epsg(4979)


def mkcrs(stage, path):
    p = stage.DefinePrim(path, "CoordinateReferenceSystem")
    p.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                      Sdf.VariabilityUniform).Set(GEO.to_wkt(version="WKT2_2019"))
    return p


def winner(prim, purpose=""):
    _, crs_path, bound, strength = rr.crs_of_prim(prim, purpose)
    return (crs_path.name if crs_path else "None"), strength


def build_precedence_stage():
    """One prim carrying ALL four binding kinds; resolver picks the winner.
    We then knock out the winner and re-resolve to reveal the next tier, giving
    the true ladder order straight from the implementation."""
    s = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(s, "/W"); s.SetDefaultPrim(s.GetPrimAtPath("/W"))
    UsdGeom.Scope.Define(s, "/W/CRS")
    Ad = mkcrs(s, "/W/CRS/AllDirect")
    Ac = mkcrs(s, "/W/CRS/AllColl")
    Pd = mkcrs(s, "/W/CRS/PurpDirect")
    Pc = mkcrs(s, "/W/CRS/PurpColl")
    p = UsdGeom.Xform.Define(s, "/W/Site").GetPrim()
    coll_all = Usd.CollectionAPI.Apply(p, "ca"); coll_all.CreateIncludesRel().SetTargets([p.GetPath()])
    coll_pur = Usd.CollectionAPI.Apply(p, "cp"); coll_pur.CreateIncludesRel().SetTargets([p.GetPath()])
    PURPOSE = "render"
    rels = {
        "all-direct":         ("crs:binding",                                 [Ad.GetPath()]),
        "all-collection":     ("crs:binding:collection:ca",                   [coll_all.GetCollectionPath(), Ac.GetPath()]),
        "purpose-direct":     (f"crs:binding:{PURPOSE}",                       [Pd.GetPath()]),
        "purpose-collection": (f"crs:binding:collection:{PURPOSE}:cp",         [coll_pur.GetCollectionPath(), Pc.GetPath()]),
    }
    for _, (name, tgts) in rels.items():
        p.CreateRelationship(name, False).SetTargets(tgts)
    # Reveal the ladder: resolve, record winner, delete that rel, repeat.
    crs_to_tier = {"PurpColl": "purpose-collection", "PurpDirect": "purpose-direct",
                   "AllColl": "all-collection", "AllDirect": "all-direct"}
    order = []
    for _ in range(4):
        w, _str = winner(p, PURPOSE)
        tier = crs_to_tier.get(w)
        order.append(tier)
        p.RemoveProperty(rels[tier][0])  # knock out current winner
    return order  # strongest -> weakest, as resolved


def build_strength_stage():
    s = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(s, "/W"); s.SetDefaultPrim(s.GetPrimAtPath("/W"))
    UsdGeom.Scope.Define(s, "/W/CRS")
    near = mkcrs(s, "/W/CRS/Near")
    far = mkcrs(s, "/W/CRS/Far")
    anc = UsdGeom.Xform.Define(s, "/W/Anc").GetPrim()
    mid = UsdGeom.Xform.Define(s, "/W/Anc/Mid").GetPrim()
    leaf = UsdGeom.Xform.Define(s, "/W/Anc/Mid/Leaf").GetPrim()
    leaf.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False).Set(Gf.Vec3d(-117, 34, 0))
    # default case: ancestor Far(weaker) + nearer Mid Near -> nearest wins
    anc.CreateRelationship("crs:binding", False).SetTargets([far.GetPath()])
    mid.CreateRelationship("crs:binding", False).SetTargets([near.GetPath()])
    default_w, _ = winner(leaf)
    # stronger case: mark ancestor strongerThanDescendants -> ancestor overrides
    anc.GetRelationship("crs:binding").SetMetadata("bindCRSAs", "strongerThanDescendants")
    strong_w, _ = winner(leaf)
    return default_w, strong_w


def main(out="docs/binding_semantics.png"):
    ladder = build_precedence_stage()
    default_w, strong_w = build_strength_stage()

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13, 6))
    fig.suptitle("crs:binding resolution \u2014 computed by resolve_runtime.crs_of_prim "
                 "(UsdShadeMaterialBindingAPI parity)", fontsize=12, fontweight="bold")

    # --- Panel 1: precedence ladder ---
    axL.set_title("(1) Per-prim precedence \u2014 strongest at top\n"
                  "rule [4]: collection beats direct at the same prim", fontsize=10)
    axL.set_xlim(0, 10); axL.set_ylim(0, 10); axL.axis("off")
    colors = ["#1b7837", "#5aae61", "#a6dba0", "#d9f0d3"]
    labels = {"purpose-collection": "purpose-specific COLLECTION",
              "purpose-direct": "purpose-specific direct",
              "all-collection": "all-purpose COLLECTION",
              "all-direct": "all-purpose direct"}
    for i, tier in enumerate(ladder):
        y = 8.2 - i * 2.0
        box = FancyBboxPatch((1, y), 8, 1.4, boxstyle="round,pad=0.1",
                             fc=colors[i], ec="black", lw=1.2)
        axL.add_patch(box)
        rank = ["STRONGEST", "", "", "weakest"][i]
        axL.text(5, y + 0.7, f"{i+1}.  {labels[tier]}", ha="center", va="center",
                 fontsize=11, fontweight="bold" if i == 0 else "normal")
        if rank:
            axL.text(9.4, y + 0.7, rank, ha="left", va="center", fontsize=8, style="italic")
        if i < 3:
            axL.annotate("", xy=(0.6, y), xytext=(0.6, y - 0.6),
                         arrowprops=dict(arrowstyle="->", color="gray"))
    axL.text(5, 0.4, "(order read back from the live resolver, not hand-authored)",
             ha="center", fontsize=8, color="gray", style="italic")

    # --- Panel 2: namespace strength ---
    axR.set_title("(2) Namespace strength\nnearest wins; strongerThanDescendants ancestor overrides",
                  fontsize=10)
    axR.set_xlim(0, 10); axR.set_ylim(0, 10); axR.axis("off")

    def chain(x0, title, anc_label, leaf_label, win_label, win_color):
        axR.text(x0 + 1.5, 9.3, title, ha="center", fontsize=10, fontweight="bold")
        nodes = [("/W/Anc\n" + anc_label, 7.2, anc_label.endswith("(Far)")),
                 ("/W/Anc/Mid\nbinding=Near", 5.0, False),
                 ("/W/Anc/Mid/Leaf\n(resolve here)", 2.8, False)]
        for txt, y, _ in nodes:
            axR.add_patch(FancyBboxPatch((x0, y), 3, 1.4, boxstyle="round,pad=0.08",
                                         fc="#eef", ec="black", lw=1))
            axR.text(x0 + 1.5, y + 0.7, txt, ha="center", va="center", fontsize=8)
        for ya, yb in [(7.2, 6.4), (5.0, 4.2)]:
            axR.annotate("", xy=(x0 + 1.5, yb), xytext=(x0 + 1.5, ya),
                         arrowprops=dict(arrowstyle="-", color="gray"))
        axR.add_patch(FancyBboxPatch((x0, 1.0), 3, 1.0, boxstyle="round,pad=0.08",
                                     fc=win_color, ec="black", lw=1.3))
        axR.text(x0 + 1.5, 1.5, f"\u2192 winner: {win_label}", ha="center", va="center",
                 fontsize=9, fontweight="bold")

    chain(0.4, "default (weaker)", "binding=Far", "binding=Near", default_w, "#a6dba0")
    chain(5.6, "ancestor strongerThanDescendants", "binding=Far\n[STRONGER]", "binding=Near",
          strong_w, "#fdae61")

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"[render] wrote {out}")
    print(f"[render] ladder (strong->weak): {ladder}")
    print(f"[render] strength: default winner={default_w} (want Near); "
          f"stronger-ancestor winner={strong_w} (want Far)")
    assert ladder == ["purpose-collection", "purpose-direct", "all-collection", "all-direct"], ladder
    assert default_w == "Near" and strong_w == "Far"
    print("[render] figure matches resolver semantics \u2713")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/binding_semantics.png")
    a = ap.parse_args()
    main(a.out)
