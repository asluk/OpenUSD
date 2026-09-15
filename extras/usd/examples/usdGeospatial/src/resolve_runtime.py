#!/usr/bin/env python3
"""
resolve_runtime.py  --  RUNTIME geospatial transform resolution.

This is the deliberately-separate runtime layer (mirrors the omniGeoSceneIndex
PoC and the hdParticleField separation): it READS the CRS-neutral authored scene
and COMPUTES the world transform for each georeferenced prim, WITHOUT modifying
the authored Xformable and WITHOUT relying on a baked resetXformStack.

Resolution rule (the "coexist" answer to the stall question):
  1. Read the prim's `crs:binding` relationship -> source CRS prim -> WKT2
     (inherited from nearest bound ancestor, like material binding).
  2. Determine the Target CRS. Priority:
       (a) explicit --target-epsg if the user overrides it, else
       (b) the CRS bound to the composed defaultPrim (a stage-level render CRS),
           else
       (c) the WGS84 ECEF fallback (EPSG:4978), the cartesian render frame.
  3. Reproject the prim's absolute `crs:position` from source CRS -> target CRS
     via PROJ. The resulting cartesian point is the prim's GEOREFERENCED world
     position in the target frame.
  4. Compose ancestor Cartesian xformOps ON TOP of the georeferenced position,
     non-destructively and at runtime. Concretely:
        world = (ancestor_local_to_world_rotation_and_scale) * (georef_position)
                + (ancestor_local_to_world_translation)
     i.e. the georeferenced position is treated as the prim's local origin in
     the target frame, and any ancestor transform (a rig offset, a tile-local
     rotation, an instancing parent) is applied as an additional Cartesian
     transform in that frame. The prim's OWN xform stack is intentionally
     identity (the authored scene is CRS-neutral); only true ANCESTOR transforms
     compose. This is the same precedence the omniGeoSceneIndex PoC used: the
     geospatial binding establishes the world anchor, Cartesian transforms layer
     relative to it.

AXIS-ORDER CONTRACT (see docs/axis-order.md): `crs:position` is ALWAYS authored
as (longitude/easting, latitude/northing, height) -- i.e. X,Y,Z / east-north-up
ordering -- REGARDLESS of the bound CRS authority's declared axis order. All
reprojection therefore uses PROJ `always_xy=True`. A consumer MUST NOT read
`crs:position[0]` as latitude even when the bound CRS's WKT declares lat-first.

Nothing here is written back into the authored scene unless --bake is passed
(which exists only to produce a renderable artifact for visual evidence; the
canonical authored scene stays neutral).
"""
import argparse, numpy as np
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _schema_setup  # noqa
import crs_engine as ce
from pyproj import CRS, Transformer
from pxr import Usd, UsdGeom, Sdf, Gf

CRS_WKT_ATTR = "crs:wkt"
CRS_BINDING_REL = "crs:binding"
CRS_POSITION_ATTR = "crs:position"
BIND_STRENGTH_KEY = "bindCRSAs"          # metadata on the binding relationship
WEAKER = "weakerThanDescendants"          # default
STRONGER = "strongerThanDescendants"
COLLECTION = "collection"


def _crs_target_of(rel, stage):
    """Return the CoordinateReferenceSystem target of a binding relationship.
    Direct bindings have one target (the CRS prim). Collection bindings have two
    (a collection path + the CRS prim); pick the one that is a CRS prim."""
    for t in rel.GetTargets():
        pr = stage.GetPrimAtPath(t)
        if pr and pr.IsValid() and pr.GetTypeName() == "CoordinateReferenceSystem":
            return pr
    # fall back to last target (MaterialBindingAPI convention: CRS is 2nd)
    tgts = rel.GetTargets()
    return stage.GetPrimAtPath(tgts[-1]) if tgts else None


def _collection_path_of(rel, stage):
    """Return the collection-path target of a collection binding relationship."""
    for t in rel.GetTargets():
        pr = stage.GetPrimAtPath(t.GetPrimPath())
        # a collection path looks like </Prim.collection:Name>
        if "collection:" in t.pathString:
            return t
    return None


def _prim_in_collection(prim, collection_path):
    """True if prim is a member of the UsdCollectionAPI at collection_path."""
    try:
        coll = Usd.CollectionAPI.GetCollection(prim.GetStage(), collection_path)
        q = coll.ComputeMembershipQuery()
        return q.IsPathIncluded(prim.GetPath())
    except Exception:
        return False


def _binding_rel_for_purpose(prim, purpose, resolving_prim=None):
    """Return (rel, is_collection) for the winning binding on `prim` applying to
    `resolving_prim`, for `purpose`, or (None, False).

    Per-prim precedence, faithful to UsdShadeMaterialBindingAPI rules [3]+[4]:
      purpose-specific collection  >  purpose-specific direct
      >  all-purpose collection     >  all-purpose direct
    Rule [4]: at a given prim, a collection-based binding (whose collection
    includes the resolving prim) is STRONGER than the direct binding. Rule [3]:
    a restricted-purpose binding is preferred over an all-purpose one.
    Among multiple matching collection bindings, rule [5]/[6]: the
    lexicographically-smallest binding NAME wins (we sort to be spec-faithful
    rather than relying on USD relationship iteration order).

    Relationship-name token grammar:
      crs:binding                              all-purpose direct
      crs:binding:<purpose>                    purpose direct
      crs:binding:collection:<name>            all-purpose collection
      crs:binding:collection:<purpose>:<name>  purpose collection
    """
    target = resolving_prim if resolving_prim is not None else prim
    stage = prim.GetStage()

    def direct(p):
        if p:
            r = prim.GetRelationship(f"{CRS_BINDING_REL}:{p}")
            if r and r.GetTargets() and p != COLLECTION:
                return r
        else:
            r = prim.GetRelationship(CRS_BINDING_REL)
            if r and r.GetTargets():
                return r
        return None

    # Gather collection bindings on this prim, split by purpose, that include
    # the resolving prim. Each entry: (binding_name, rel).
    coll_purpose, coll_all = [], []
    for rel in prim.GetRelationships():
        name = rel.GetName()
        if not name.startswith(f"{CRS_BINDING_REL}:{COLLECTION}:"):
            continue
        if not rel.GetTargets():
            continue
        rest = name.split(":")[3:]            # [name] or [purpose, name]
        rel_purpose = rest[0] if len(rest) == 2 else ""
        binding_name = rest[-1] if rest else ""
        cpath = _collection_path_of(rel, stage)
        if cpath is None or not _prim_in_collection(target, cpath):
            continue
        if rel_purpose:
            coll_purpose.append((rel_purpose, binding_name, rel))
        else:
            coll_all.append((binding_name, rel))

    # [5]/[6] lexicographic-smallest binding name wins among collections.
    coll_all.sort(key=lambda e: e[0])
    coll_purpose.sort(key=lambda e: (e[0], e[1]))

    # Precedence ladder (strongest first).
    if purpose:
        for rp, bn, rel in coll_purpose:
            if rp == purpose:
                return rel, True            # purpose collection (strongest)
        d = direct(purpose)
        if d is not None:
            return d, False                 # purpose direct
    if coll_all:
        return coll_all[0][1], True         # all-purpose collection
    d = direct("")
    if d is not None:
        return d, False                     # all-purpose direct
    return None, False


def _rel_strength(rel):
    s = rel.GetMetadata(BIND_STRENGTH_KEY) if rel else None
    return s if s in (WEAKER, STRONGER) else WEAKER


def crs_of_prim(prim, purpose=""):
    """Resolve the CRS bound to `prim` for `purpose`, honouring MaterialBindingAPI-
    style strength + purpose semantics.

    Algorithm (mirrors UsdShade material resolution):
      * Walk from the prim up to the root collecting authored bindings (for the
        requested purpose, falling back to all-purpose at each level).
      * Default strength weakerThanDescendants: the NEAREST binding wins.
      * If an ANCESTOR binding is authored strongerThanDescendants, it overrides
        any closer (descendant) binding.
    Returns (CRS, crs_prim_path, bound_prim_path, strength) or (None,...).
    """
    chain = []  # nearest-first: [(prim_path, rel, strength)]
    p = prim
    while p and p.IsValid():
        rel, _is_coll = _binding_rel_for_purpose(p, purpose, resolving_prim=prim)
        if rel is not None:
            chain.append((p.GetPath(), rel, _rel_strength(rel)))
        p = p.GetParent()
    if not chain:
        return None, None, None, None
    # A strongerThanDescendants binding on an ancestor wins over nearer ones.
    chosen = chain[0]  # nearest (default weaker semantics)
    for entry in chain[1:]:  # ancestors, increasingly far
        if entry[2] == STRONGER:
            chosen = entry     # an ancestor declared itself stronger -> it wins
            # keep scanning: an even-higher stronger ancestor wins over this one
    bound_path, rel, strength = chosen
    crs_prim = _crs_target_of(rel, prim.GetStage())
    # D2 guard: a mis-authored binding (target is not a CRS prim, or has no
    # crs:wkt) must not crash the resolver with an opaque pyproj error.
    wkt = crs_prim.GetAttribute(CRS_WKT_ATTR).Get() if (
        crs_prim and crs_prim.IsValid() and crs_prim.GetAttribute(CRS_WKT_ATTR)) else None
    if not wkt:
        import sys as _sys
        print(f"[resolve] WARNING: crs:binding on {bound_path} targets "
              f"{crs_prim.GetPath() if crs_prim else '<none>'} which has no crs:wkt; "
              f"skipping this prim.", file=_sys.stderr)
        return None, None, None, None
    try:
        src = CRS.from_wkt(wkt)
    except Exception as e:
        import sys as _sys
        print(f"[resolve] WARNING: invalid crs:wkt on {crs_prim.GetPath()}: {e}; "
              f"skipping.", file=_sys.stderr)
        return None, None, None, None
    return src, crs_prim.GetPath(), bound_path, strength


def _crs_prim_epoch(stage, crs_prim_path):
    """Return the coordinate epoch (decimal year) authored on the CRS prim, or
    None if unspecified/zero."""
    cp = stage.GetPrimAtPath(crs_prim_path)
    if not cp or not cp.IsValid():
        return None
    a = cp.GetAttribute("crs:epoch")
    v = a.Get() if a else None
    return float(v) if v else None


_GRID_DIRS_REGISTERED = set()


def _register_grid_files(stage, crs_prim_path):
    """Read crs:gridFiles (asset[]) off the CRS prim, resolve each asset path, and
    add its containing directory to PROJ's grid search path so PROJ can find the
    transformation grids. Returns the list of resolved grid file paths.

    This is the plumbing for high-accuracy datum/geoid transforms that reference
    EXTERNAL grid assets rather than inlining everything in WKT. NOTE: applying a
    grid still requires the grid file to exist and PROJ to select an operation
    that uses it; this function makes the asset discoverable, it does not force a
    particular operation.
    """
    cp = stage.GetPrimAtPath(crs_prim_path)
    if not cp or not cp.IsValid():
        return []
    a = cp.GetAttribute("crs:gridFiles")
    vals = a.Get() if a else None
    if not vals:
        return []
    try:
        from pyproj.datadir import append_data_dir, get_data_dir
    except Exception:
        return []
    resolved = []
    for asset in vals:
        # Sdf.AssetPath -> resolved or authored path
        p = getattr(asset, "resolvedPath", "") or getattr(asset, "path", "") or str(asset)
        if not p:
            continue
        d = os.path.dirname(os.path.abspath(p))
        if d and d not in _GRID_DIRS_REGISTERED and os.path.isdir(d):
            append_data_dir(d)
            _GRID_DIRS_REGISTERED.add(d)
        resolved.append(p)
    return resolved


def target_crs_for_stage(stage, override_epsg=None):
    """Determine the Target/render CRS for the stage.
    Priority: explicit override -> CRS bound to the defaultPrim -> ECEF 4978.
    Returns (CRS, source_description)."""
    if override_epsg is not None:
        return CRS.from_epsg(override_epsg), f"--target-epsg={override_epsg}"
    dp = stage.GetDefaultPrim()
    if dp and dp.IsValid():
        crs, crs_path, _, _ = crs_of_prim(dp)
        if crs is not None:
            return crs, f"stage defaultPrim binding -> {crs_path}"
    return CRS.from_epsg(4978), "fallback EPSG:4978 (WGS84 ECEF)"


def make_transformer(src: CRS, dst: CRS):
    return Transformer.from_crs(src, dst, always_xy=True)


def _wkt_of(crs):
    """WKT2 string for a pyproj CRS (the engine consumes WKT; USD never parses it)."""
    return crs.to_wkt(version="WKT2_2019")


def ancestor_local_to_world(prim, xform_cache=None):
    """Compute the composed local-to-world transform contributed by ANCESTORS
    only (excludes the prim's own xform, which is intentionally identity in the
    CRS-neutral scene). Returns a Gf.Matrix4d. Pass a shared UsdGeom.XformCache
    (`xform_cache`) to reuse ancestor computations across a full-stage resolve
    (D3: avoid rebuilding the cache per prim)."""
    parent = prim.GetParent()
    if not parent or not parent.IsValid():
        return Gf.Matrix4d(1.0)
    xc = xform_cache if xform_cache is not None else UsdGeom.XformCache()
    return xc.GetLocalToWorldTransform(parent)


def resolve_world_translation(prim, target_crs, cache, compose_ancestors=True, purpose="",
                              xform_cache=None):
    """Compute the world-space (target-CRS cartesian) position for a prim.

    world = ancestor_L2W . reproject(crs:position)
    where reproject maps the source-CRS (lon/E, lat/N, h) to the target frame.
    The georeferenced point is the prim's local origin; ancestor Cartesian
    transforms compose on top (rotation/scale applied to it, then translation).
    """
    src_crs, src_path, _, _ = crs_of_prim(prim, purpose)
    if src_crs is None:
        return None, None
    pos = prim.GetAttribute(CRS_POSITION_ATTR).Get()
    if pos is None:
        return None, src_path
    key = str(src_path)
    if key not in cache:
        _register_grid_files(prim.GetStage(), src_path)  # make grid assets discoverable
        # cache the (src_wkt, dst_wkt) pair the ENGINE will use -- pyproj is no
        # longer called directly here; the registered engine does the geodesy.
        cache[key] = (_wkt_of(src_crs), _wkt_of(target_crs))
    src_wkt, dst_wkt = cache[key]
    engine = ce.get_engine()
    # AXIS-ORDER CONTRACT: crs:position is (x=lon/E, y=lat/N, z=h) always.
    # DYNAMIC CRS: pass the coordinate epoch as the time coordinate when present.
    epoch = _crs_prim_epoch(prim.GetStage(), src_path)
    x, y, z = engine.reproject(src_wkt, dst_wkt, pos[0], pos[1], pos[2], epoch=epoch)
    georef = Gf.Vec3d(x, y, z)
    if not compose_ancestors:
        return georef, src_path
    # Compose ancestor Cartesian transform on top of the georeferenced anchor.
    a2w = ancestor_local_to_world(prim, xform_cache)
    world = a2w.Transform(georef)   # applies ancestor rot/scale + translation
    return world, src_path


# ===========================================================================
# ANCHOR INJECTION (the inject-don't-bake answer to the resetXformStack debate)
# ===========================================================================
# A georeferenced prim acts as an ANCHOR: its crs:position + bound CRS define a
# rigid local-frame -> ECEF transform (ORIENTATION + position; the ENU/topocentric
# basis at its footprint, or the projected-plane basis for a projected CRS). A
# NON-georef descendant authored in local metres (x=East, y=North, z=Up) is then
# placed by composing its authored local xform UNDER the injected anchor frame:
#
#     world_ecef = anchorFrame . localXform(descendant, relative to anchor)
#
# This is the case stock USD composition gets wrong (the anchor's georef lives in
# crs:position, which XformCache never reads, so the descendant renders at the
# origin). We inject the anchor frame into a COMPUTED representation at runtime;
# nothing is written back to the authored stage (injecting into a resolved .usda
# would just be baking at a different layer). The Python behavior here is the
# implementation-agnostic reference for a Hydra scene index / OpenExec / an OV
# runtime to each implement.

def anchor_frame(prim, target_crs, cache, purpose=""):
    """If `prim` is a georeferenced anchor, return its rigid local-frame -> target
    transform (Gf.Matrix4d, orientation+position) and the source CRS path; else
    (None, None). Only valid when target is ECEF (4978): the topocentric basis is
    defined for an ECEF target. For a planar/projected target, orientation is
    implicit and callers should use position-only composition instead."""
    src_crs, src_path, _, _ = crs_of_prim(prim, purpose)
    if src_crs is None:
        return None, None
    pos = prim.GetAttribute(CRS_POSITION_ATTR).Get()
    if pos is None:
        return None, src_path
    key = ("frame", str(src_path))
    if key not in cache:
        _register_grid_files(prim.GetStage(), src_path)
        cache[key] = _wkt_of(src_crs)
    src_wkt = cache[key]
    epoch = _crs_prim_epoch(prim.GetStage(), src_path)
    engine = ce.get_engine()
    M = engine.local_frame_to_ecef(src_wkt, pos[0], pos[1], pos[2], epoch=epoch)
    return M, src_path


def nearest_anchor(prim, purpose=""):
    """Walk ancestors (including self) to the nearest prim that is a georef anchor
    (has crs:position + a resolvable binding). Returns that prim or None."""
    p = prim
    while p and p.IsValid():
        if p.GetAttribute(CRS_POSITION_ATTR):
            src, _, _, _ = crs_of_prim(p, purpose)
            if src is not None:
                return p
        p = p.GetParent()
    return None


def resolve_with_injection(prim, target_crs, cache, purpose="", xform_cache=None):
    """Resolve a prim's world transform under inject-don't-bake semantics.

    Returns (Gf.Matrix4d world_to_local? no -> local-to-world, anchor_path) or
    (None, None). Two cases:
      * The prim is ITSELF a georef anchor -> its world transform IS the injected
        anchor frame (orientation+position).
      * The prim is a NON-georef descendant of a georef anchor -> world is the
        anchor frame composed with the prim's authored local-to-anchor xform.
        The local-to-anchor xform is read from the AUTHORED stage (the subtree's
        ordinary Cartesian xformOps), relative to the anchor.
    A prim with neither (no anchor up the chain) returns (None, None) -- it has no
    georeferencing and stock USD composition already handles it.
    """
    anchor = nearest_anchor(prim, purpose)
    if anchor is None:
        return None, None
    frame, anchor_path = anchor_frame(anchor, target_crs, cache, purpose)
    if frame is None:
        return None, None
    if prim.GetPath() == anchor.GetPath():
        return frame, anchor.GetPath()
    xc = xform_cache if xform_cache is not None else UsdGeom.XformCache()
    # --- Projected-anchor path (compose IN-PLANE, do not lift through ENU) ---
    # When the anchor's CRS is a PROJECTED (grid) CRS, the child's authored local
    # offsets are grid-plane offsets in the anchor's units. Lifting them through
    # the anchor's true-ENU basis (the geographic path) introduces a
    # grid-convergence + point-scale error (~metres over a few hundred metres).
    # Instead: add the child's local offset to the anchor's grid position and
    # reproject that grid point straight to the target CRS. Matches closed-form
    # geodesy to 0 mm while keeping the AUTHORED scene neutral (the offset is
    # still read from ordinary Cartesian xformOps; nothing is baked).
    src_crs, src_path, _, _ = crs_of_prim(anchor, purpose)
    src_wkt = _wkt_of(src_crs) if src_crs is not None else None
    engine = ce.get_engine()
    if src_wkt is not None and engine.is_projected(src_wkt):
        anchor_pos = anchor.GetAttribute(CRS_POSITION_ATTR).Get()
        anchor_authored = xc.GetLocalToWorldTransform(anchor)
        desc_authored = xc.GetLocalToWorldTransform(prim)
        local_to_anchor = desc_authored * anchor_authored.GetInverse()
        # the child origin's grid offset composes in-plane and reprojects;
        # the child's own rotation/scale is preserved in the returned matrix.
        offset = local_to_anchor.Transform(Gf.Vec3d(0, 0, 0))
        epoch = _crs_prim_epoch(anchor.GetStage(), src_path)
        dst_wkt = _wkt_of(target_crs)
        X, Y, Z = engine.project_grid_offset_to_target(
            src_wkt, dst_wkt,
            (anchor_pos[0], anchor_pos[1], anchor_pos[2]),
            (offset[0], offset[1], offset[2]), epoch=epoch)
        world = Gf.Matrix4d(local_to_anchor)
        world.SetTranslateOnly(Gf.Vec3d(X, Y, Z))
        return world, anchor.GetPath()
    # --- Geographic/ECEF-anchor path (topocentric ENU lift, as before) ---
    # local-to-anchor: the descendant's transform expressed in the anchor's
    # local frame = (anchor_world_authored)^-1 . descendant_world_authored,
    # using the AUTHORED (Cartesian) stack only. The anchor's own authored xform
    # is intentionally identity in the neutral scene, so this is just the
    # descendant's local-to-world relative to the anchor.
    anchor_authored = xc.GetLocalToWorldTransform(anchor)
    desc_authored = xc.GetLocalToWorldTransform(prim)
    local_to_anchor = desc_authored * anchor_authored.GetInverse()
    world = local_to_anchor * frame      # compose under the injected anchor frame
    return world, anchor.GetPath()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="out/earth2_georef.usda")
    ap.add_argument("--target-epsg", type=int, default=None,
                    help="render/target CRS override; default: read from stage "
                         "defaultPrim binding, else EPSG:4978")
    ap.add_argument("--bake", default=None,
                    help="optional: write a resolved (cartesian) USD for rendering")
    ap.add_argument("--scale", type=float, default=1e-6,
                    help="scale ECEF metres -> scene units for renderable artifact")
    ap.add_argument("--limit", type=int, default=8, help="how many to print")
    ap.add_argument("--purpose", default="",
                    help="material-binding-style purpose; selects crs:binding:<purpose> "
                         "over the all-purpose crs:binding")
    args = ap.parse_args()

    stage = Usd.Stage.Open(args.inp)
    target_crs, target_src = target_crs_for_stage(stage, args.target_epsg)
    cache = {}
    xform_cache = UsdGeom.XformCache()   # D3: shared across the traverse

    resolved = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Xform):
            continue
        if not prim.GetAttribute(CRS_POSITION_ATTR):
            continue
        world, src = resolve_world_translation(prim, target_crs, cache,
                                               purpose=args.purpose,
                                               xform_cache=xform_cache)
        if world is not None:
            pos = prim.GetAttribute(CRS_POSITION_ATTR).Get()
            t2m = prim.GetAttribute("primvars:t2m").Get()
            resolved.append((prim.GetPath(), tuple(pos), tuple(world), t2m))

    print(f"[resolve] target CRS = {target_crs.name} (via {target_src})")
    print(f"[resolve] {len(resolved)} georeferenced prims resolved to world cartesian")
    print(f"[resolve] authored scene was NOT modified (no translate/reset baked)\n")
    for path, pos, world, t2m in resolved[:args.limit]:
        print(f"  {str(path):28s} lon/lat/h={pos[0]:7.2f},{pos[1]:6.2f},{pos[2]:4.0f}"
              f"  ->  ECEF=({world[0]:13.1f},{world[1]:13.1f},{world[2]:13.1f})  t2m={t2m:.1f}K")

    if args.bake:
        out = Usd.Stage.CreateNew(args.bake)
        UsdGeom.SetStageUpAxis(out, UsdGeom.Tokens.z)  # ECEF is z-up
        UsdGeom.SetStageMetersPerUnit(out, 1.0)
        w = UsdGeom.Xform.Define(out, "/World")
        out.SetDefaultPrim(w.GetPrim())
        pts_prim = UsdGeom.Points.Define(out, "/World/ResolvedPoints")
        positions, widths, colors = [], [], []
        tvals = np.array([r[3] for r in resolved], dtype=np.float64)
        tmin, tmax = float(tvals.min()), float(tvals.max())
        for _, _, world, t2m in resolved:
            positions.append(Gf.Vec3f(world[0]*args.scale, world[1]*args.scale, world[2]*args.scale))
            widths.append(0.15)
            f = (t2m - tmin) / (tmax - tmin + 1e-9)        # turbo-ish blue->red
            colors.append(Gf.Vec3f(float(f), float(0.25), float(1.0 - f)))
        pts_prim.CreatePointsAttr(positions)
        pts_prim.CreateWidthsAttr(widths)
        pts_prim.CreateDisplayColorAttr(colors)
        out.GetRootLayer().Save()
        print(f"\n[bake] wrote renderable resolved artifact -> {args.bake} "
              f"(ECEF*{args.scale}, z-up, {len(positions)} pts)")


if __name__ == "__main__":
    main()
