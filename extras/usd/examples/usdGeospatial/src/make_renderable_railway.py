#!/usr/bin/env python3
"""
make_renderable_railway.py -- take the converted crs: georef railway scene
(out/railway_georef.usda, produced by convert_omni_geospatial.py) and produce a
RENDER-READY version WITHOUT touching any geospatial semantics.

Why this is needed
------------------
convert_omni_geospatial.py copies attributes with `if attr.Get() is None: continue`,
which silently DROPS every shader connection / output attr (they carry no authored
value), gutting the UsdPreviewSurface graph:
  - UsdUVTexture shaders lose `outputs:rgb` and `inputs:st.connect`
  - UsdPreviewSurface ("pbrMat1") loses `diffuseColor.connect` + `outputs:surface`
  - PrimvarReader_float2 loses `varname.connect` + `outputs:result`
  - Material prims lose `outputs:surface.connect`
  - the tile Mesh ("plane1") loses its `rel material:binding`
Additionally the texture asset paths are BARE filenames (@quadnode-0.png@) that do
NOT resolve relative to out/ (the PNGs live in data/thirdparty/), so tiles fall
back to the green fallback color (0,1,0,1).

This script REPAIRS the material graph and RESOLVES the texture paths, and gives
the rail BasisCurves a visible constant displayColor so they read on the tiles.
It does NOT bake any transform and does NOT touch crs:binding / crs:position /
crs:wkt -- georeferencing still comes entirely from the auto-inserted scene index.

Usage: make_renderable_railway.py <in_georef.usda> <out_renderable.usda> [tex_dir]
"""
import os
import sys
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf, Vt


def repair_material(stage, mat_path, tex_abspath):
    """Rebuild the full UsdPreviewSurface graph for one tile material."""
    mat = UsdShade.Material.Get(stage, mat_path)
    if not mat:
        return False

    st_name = "st"
    # ensure stPrimvarName input exists
    mat.CreateInput("frame:stPrimvarName", Sdf.ValueTypeNames.String).Set(st_name)

    # PrimvarReader
    reader = UsdShade.Shader.Get(stage, mat_path + "/PrimvarSt")
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.String).ConnectToSource(
        mat.GetInput("frame:stPrimvarName"))
    reader_out = reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    # UVTexture
    tex = UsdShade.Shader.Get(stage, mat_path + "/baseColorTex0")
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(tex_abspath)
    tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(reader_out)
    # keep a fallback so a missing texture is obvious (not black)
    tex.CreateInput("fallback", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(0.5, 0.5, 0.5, 1))
    tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
    tex_rgb = tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    # PreviewSurface
    pbr = UsdShade.Shader.Get(stage, mat_path + "/pbrMat1")
    pbr.CreateIdAttr("UsdPreviewSurface")
    pbr.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_rgb)
    # Drive emissive from the SAME texture so the map tiles read at full
    # brightness like the matplotlib plot, independent of scene lighting
    # (Storm under llvmpipe with a single distant light otherwise renders the
    # up-facing tiles very dark). This is a presentation choice for the ground
    # imagery -- it does not affect geometry or georeferencing.
    pbr.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_rgb)
    pbr.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(1.0)
    pbr.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    pbr.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    pbr.CreateInput("useSpecularWorkflow", Sdf.ValueTypeNames.Int).Set(0)
    surf = pbr.CreateOutput("surface", Sdf.ValueTypeNames.Token)

    mat.CreateSurfaceOutput().ConnectToSource(surf)
    return True


def main():
    src, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    tex_dir = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else \
        os.path.abspath(os.path.join(os.path.dirname(src), "..", "data", "thirdparty"))

    # Work on a flattened copy so we can edit prims directly and keep one self
    # contained render layer (still no transform baking; crs: attrs are copied
    # verbatim as authored on the georef prims).
    in_stage = Usd.Stage.Open(src)
    flat = in_stage.Flatten()
    stage = Usd.Stage.Open(flat)

    # 1) repair each tile material + point its texture at a resolvable abs path
    tile_mats = {
        "/mat0": os.path.join(tex_dir, "quadnode-0.png"),
        "/mat1": os.path.join(tex_dir, "quadnode-1.png"),
        "/mat4": os.path.join(tex_dir, "quadnode-4.png"),
    }
    fixed = []
    for mp, tex in tile_mats.items():
        if not os.path.exists(tex):
            print(f"[warn] texture missing: {tex}")
        if repair_material(stage, mp, tex):
            fixed.append(mp)

    # 2) re-bind each tile Mesh (plane1) to its material
    bind_map = {
        "/RootGeoReference/MapGeo0/plane1": "/mat0",
        "/RootGeoReference/MapGeo1/plane1": "/mat1",
        "/RootGeoReference/MapGeo4/plane1": "/mat4",
    }
    bound = []
    for mesh_path, mat_path in bind_map.items():
        prim = stage.GetPrimAtPath(mesh_path)
        if not prim:
            print(f"[warn] tile mesh not found: {mesh_path}")
            continue
        UsdShade.MaterialBindingAPI.Apply(prim)
        UsdShade.MaterialBindingAPI(prim).Bind(
            UsdShade.Material.Get(stage, mat_path))
        # tiles are authored single-sided with winding that backface-culls from
        # a top-down view -> make them double-sided so the map imagery always
        # shows. Also (re)assert vertex interpolation on the st primvar (the
        # convert step dropped the interpolation qualifier).
        mesh = UsdGeom.Mesh(prim)
        mesh.CreateDoubleSidedAttr(True)
        pv = UsdGeom.PrimvarsAPI(prim).GetPrimvar("st")
        if pv:
            pv.SetInterpolation(UsdGeom.Tokens.vertex)
        bound.append(mesh_path)

    # 3) rails: bind a bright unlit (emissive) material AND set a constant
    #    displayColor fallback so the BasisCurves read strongly (red) on top of
    #    the bright map tiles regardless of lighting.
    rail_mat = UsdShade.Material.Define(stage, "/RailMat")
    rshader = UsdShade.Shader.Define(stage, "/RailMat/surf")
    rshader.CreateIdAttr("UsdPreviewSurface")
    rshader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.95, 0.08, 0.08))
    rshader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.9, 0.05, 0.05))
    rshader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    rsurf = rshader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    rail_mat.CreateSurfaceOutput().ConnectToSource(rsurf)

    n_curves = 0
    rail_color = Vt.Vec3fArray([Gf.Vec3f(0.95, 0.1, 0.1)])
    for prim in stage.Traverse():
        if prim.GetTypeName() == "BasisCurves":
            curves = UsdGeom.BasisCurves(prim)
            dc = curves.CreateDisplayColorPrimvar(UsdGeom.Tokens.constant)
            dc.Set(rail_color)
            UsdShade.MaterialBindingAPI.Apply(prim)
            UsdShade.MaterialBindingAPI(prim).Bind(rail_mat)
            # widen the curves so they are visible from the top-down framing
            # distance (~2 km); rails are drawn as ~8 m ribbons.
            curves.CreateWidthsAttr([25.0])
            curves.SetWidthsInterpolation(UsdGeom.Tokens.constant)
            n_curves += 1

    stage.GetRootLayer().Export(out)
    print(f"[renderable] {src} -> {out}")
    print(f"[renderable]   materials repaired: {fixed}")
    print(f"[renderable]   tiles rebound:      {bound}")
    print(f"[renderable]   texture dir:        {tex_dir}")
    print(f"[renderable]   rail curves colored: {n_curves}")


if __name__ == "__main__":
    main()
