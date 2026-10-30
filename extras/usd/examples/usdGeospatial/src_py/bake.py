#
# Copyright 2026 NVIDIA CORPORATION & AFFILIATES
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
"""Explicit ordinary-USD finite-vertex export; never modifies the source stage."""

from pathlib import Path
import json
import numpy as np
from pxr import Usd, UsdGeom, Sdf, Gf, Vt
from common import CAPABILITY, PROFILE, require
from reader import Reader
from crs import geocentric, normalize_wkt
from profiles import publish_claim
from math_util import stage_basis


def bake(stage, path, output, times=(None,), reader=None):
    reader = reader or Reader(stage)
    q = reader.output(output)
    chart = geocentric(q) if q.is_geographic else q
    meshes = [p for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)]
    require(bool(meshes), "no geometry to bake")
    require(
        not any(UsdGeom.Gprim(p) and not p.IsA(UsdGeom.Mesh) for p in stage.Traverse()),
        "non-mesh geometry export requires its consumed-domain evaluator",
    )
    require(
        not any(p.GetTypeName() == "GeospatialDataSource" for p in stage.Traverse()),
        "geometry-only bake cannot discard retained measurement domains",
    )
    require(
        not any(p.IsA(UsdGeom.PointInstancer) for p in stage.Traverse()),
        "point-instancer export requires explicit expansion",
    )
    # Preserve unrelated properties/materials on the flattened derived copy.
    out = Usd.Stage.CreateNew(str(path))
    source = stage.Flatten()
    UsdGeom.SetStageMetersPerUnit(out, UsdGeom.GetStageMetersPerUnit(stage))
    UsdGeom.SetStageUpAxis(out, UsdGeom.GetStageUpAxis(stage))
    out.SetTimeCodesPerSecond(stage.GetTimeCodesPerSecond())
    context = out.DefinePrim("/Resolved", "CoordinateReferenceSystem")
    out.SetDefaultPrim(context)
    context.CreateAttribute(
        "crs:wkt", Sdf.ValueTypeNames.Token, False, Sdf.VariabilityUniform
    ).Set(normalize_wkt(chart.to_wkt()))
    originprim = UsdGeom.Xform.Define(out, "/Resolved/Origin")
    points = {}
    reports = []
    first = None
    for p in meshes:
        for t in times:
            tc = Usd.TimeCode.Default() if t is None else t
            local = UsdGeom.Mesh(p).GetPointsAttr().Get(tc)
            xyz, _ = reader.scene_points(p, local, q, t)
            points[(str(p.GetPath()), t)] = xyz
            if first is None:
                first = xyz.mean(axis=0)
    originprim.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*first))
    roots = [p for p in stage.GetPseudoRoot().GetChildren()]
    for p in roots:
        Sdf.CopySpec(
            source,
            p.GetPath(),
            out.GetRootLayer(),
            Sdf.Path("/Resolved/Origin").AppendChild(p.GetName()),
        )

    # Fix flattened absolute relationship/connection targets after reparenting.
    def target(path):
        for r in roots:
            if path.HasPrefix(r.GetPath()):
                return path.ReplacePrefix(
                    r.GetPath(), Sdf.Path("/Resolved/Origin").AppendChild(r.GetName())
                )
        return path

    for p in out.TraverseAll():
        if p == context or p == originprim.GetPrim():
            continue
        ap = [x for x in p.GetAppliedSchemas() if x != "GeospatialCRSBindingAPI"]
        p.SetMetadata("apiSchemas", Sdf.TokenListOp.CreateExplicit(ap))
        # Remove superseded geospatial summaries, retaining unrelated capabilities.
        info = p.GetCustomDataByKey("profilesInfo")
        if info:
            usages = info.get("capabilityUsages", {})
            usages.pop(CAPABILITY, None)
            compat = info.get("profileCompatibility", {})
            compat.pop(PROFILE, None)
            p.ClearCustomDataByKey("profilesInfo")
            if usages or compat:
                p.SetCustomDataByKey(
                    "profilesInfo",
                    dict(capabilityUsages=usages, profileCompatibility=compat),
                )
        if p.GetTypeName() == "CoordinateReferenceSystem":
            p.SetTypeName("Xform")
        for prop in list(p.GetProperties()):
            n = prop.GetName()
            if n.startswith("crs:") or n == "xformOpOrder" or n.startswith("xformOp:"):
                p.RemoveProperty(n)
                continue
            if isinstance(prop, Usd.Relationship):
                prop.SetTargets([target(x) for x in prop.GetTargets()])
            elif isinstance(prop, Usd.Attribute):
                conn = prop.GetConnections()
                if conn:
                    prop.SetConnections([target(x) for x in conn])
    for p in meshes:
        dest = out.GetPrimAtPath(target(p.GetPath()))
        m = UsdGeom.Mesh(dest)
        translate = UsdGeom.Xformable(dest).AddTranslateOp(
            UsdGeom.XformOp.PrecisionDouble
        )
        maxerror = 0
        for t in times:
            xyz = points[(str(p.GetPath()), t)]
            center = xyz.mean(axis=0) - first
            translate.Set(Gf.Vec3d(*center), Usd.TimeCode.Default() if t is None else t)
            local = xyz - first - center
            rounded = local.astype(np.float32)
            maxerror = max(
                maxerror,
                float(np.max(np.linalg.norm(rounded.astype(float) - local, axis=1))),
            )
            m.GetPointsAttr().Set(
                Vt.Vec3fArray.FromNumpy(rounded),
                Usd.TimeCode.Default() if t is None else t,
            )
            normals = (
                UsdGeom.Mesh(p)
                .GetNormalsAttr()
                .Get(Usd.TimeCode.Default() if t is None else t)
            )
            if normals:
                original = UsdGeom.Mesh(p)
                sourcepoints = np.asarray(
                    original.GetPointsAttr().Get(
                        Usd.TimeCode.Default() if t is None else t
                    )
                )
                interpolation = original.GetNormalsInterpolation()
                if interpolation == "faceVarying":
                    locations = sourcepoints[
                        np.asarray(original.GetFaceVertexIndicesAttr().Get())
                    ]
                elif interpolation in ("vertex", "varying"):
                    locations = sourcepoints
                elif interpolation == "constant":
                    locations = sourcepoints.mean(axis=0, keepdims=True)
                elif interpolation == "uniform":
                    counts = original.GetFaceVertexCountsAttr().Get()
                    indices = original.GetFaceVertexIndicesAttr().Get()
                    offset = 0
                    locations = []
                    for count in counts:
                        locations.append(
                            sourcepoints[indices[offset : offset + count]].mean(axis=0)
                        )
                        offset += count
                else:
                    raise RuntimeError("unsupported normal interpolation")
                require(len(locations) == len(normals), "normal association mismatch")
                mapped = reader.vectors(p, locations, normals, "normal", q, t)
                m.GetNormalsAttr().Set(
                    Vt.Vec3fArray.FromNumpy(mapped.astype(np.float32)),
                    Usd.TimeCode.Default() if t is None else t,
                )
            # Role-bearing primvars follow their semantic role; arbitrary triples do not.
            for pv in UsdGeom.PrimvarsAPI(p).GetPrimvars():
                role = pv.GetTypeName().role
                if role not in ("Point", "Normal", "Vector"):
                    continue
                values = pv.ComputeFlattened(Usd.TimeCode.Default() if t is None else t)
                if values is None:
                    continue
                values = np.atleast_2d(np.asarray(values, dtype=float))
                target = UsdGeom.Primvar(dest.GetAttribute(pv.GetAttr().GetName()))
                if role == "Point":
                    mapped, _ = reader.scene_points(p, values, q, t)
                    mapped -= first + center
                else:
                    vertices = np.asarray(
                        UsdGeom.Mesh(p)
                        .GetPointsAttr()
                        .Get(Usd.TimeCode.Default() if t is None else t)
                    )
                    interpolation = pv.GetInterpolation()
                    if interpolation == "faceVarying":
                        locations = vertices[
                            np.asarray(UsdGeom.Mesh(p).GetFaceVertexIndicesAttr().Get())
                        ]
                    elif interpolation in ("vertex", "varying"):
                        locations = vertices
                    elif interpolation == "constant":
                        locations = vertices.mean(axis=0, keepdims=True)
                    elif interpolation == "uniform":
                        counts = UsdGeom.Mesh(p).GetFaceVertexCountsAttr().Get()
                        indices = UsdGeom.Mesh(p).GetFaceVertexIndicesAttr().Get()
                        offset = 0
                        locations = []
                        for count in counts:
                            locations.append(
                                vertices[indices[offset : offset + count]].mean(axis=0)
                            )
                            offset += count
                    else:
                        raise RuntimeError("unsupported primvar interpolation")
                    require(
                        len(locations) == len(values),
                        "semantic primvar association mismatch",
                    )
                    mapped = reader.vectors(p, locations, values, role.lower(), q, t)
                target.BlockIndices()
                a = target.GetAttr()
                is_double = (
                    "d" in str(a.GetTypeName()).lower()
                    or "double" in str(a.GetTypeName()).lower()
                )
                if a.GetTypeName().isArray:
                    a.Set(
                        (Vt.Vec3dArray if is_double else Vt.Vec3fArray).FromNumpy(
                            mapped.astype(np.float64 if is_double else np.float32)
                        ),
                        Usd.TimeCode.Default() if t is None else t,
                    )
                else:
                    a.Set(
                        Gf.Vec3d(*mapped[0]) if is_double else Gf.Vec3f(*mapped[0]),
                        Usd.TimeCode.Default() if t is None else t,
                    )
        reports.append(
            {
                "source": str(p.GetPath()),
                "export": str(dest.GetPath()),
                "vertices": len(xyz),
                "max_float_rounding_m": maxerror * UsdGeom.GetStageMetersPerUnit(stage),
            }
        )
    publish_claim(out, requires=False)
    out.GetRootLayer().Save()
    return out, {
        "coordinateCRS": q.to_wkt(),
        "sceneChart": chart.to_wkt(),
        "scope": "finite vertices and resulting straight polygonal export; no original continuous-surface certificate",
        "times": list(times),
        "readerInterpolation": "linear",
        "timeCodesPerSecond": out.GetTimeCodesPerSecond(),
        "origin_stage_units": first.tolist(),
        "meshes": reports,
    }
