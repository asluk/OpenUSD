"""Read a bounded subset of hierarchical CRS relationships on composed prims.

Property spellings are experimental implementation choices. This does NOT infer
which prim is an anchor or where its position is stored (open questions 2 and 5).
"""
from dataclasses import dataclass


class BindingError(ValueError):
    pass


@dataclass(frozen=True)
class Binding:
    declared_at: str
    definition: str
    wkt: str


def read_binding(stage, prim_path):
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        raise BindingError(f"No prim: {prim_path}")
    while prim and not prim.IsPseudoRoot():
        rel = prim.GetRelationship("crs:binding")
        if rel:
            targets = rel.GetForwardedTargets()
            if len(targets) != 1:
                raise BindingError("Empty or multiple targets need a specified policy; no ancestor fallback.")
            target = targets[0]
            definition = stage.GetPrimAtPath(target) if target.IsPrimPath() else None
            if not definition or definition.GetTypeName() != "GeospatialCRS":
                raise BindingError(f"Binding does not name a CRS definition: {target}")
            wkt = definition.GetAttribute("crs:wkt").Get()
            if not isinstance(wkt, str) or not wkt.strip():
                raise BindingError(f"Definition has no WKT: {target}")
            return Binding(str(prim.GetPath()), str(target), wkt)
        prim = prim.GetParent()
    raise BindingError(f"No CRS binding for {prim_path}")
