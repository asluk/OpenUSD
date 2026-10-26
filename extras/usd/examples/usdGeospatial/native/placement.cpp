#include "placement.h"
#include <algorithm>
#include <pxr/base/gf/quatd.h>
#include <pxr/usd/usdGeom/metrics.h>
#include <pxr/usd/usdGeom/pointInstancer.h>
#include <pxr/usd/usdGeom/xformCache.h>
#include <pxr/usd/usdGeom/xformable.h>
namespace usdGeospatialExample {
bool HasDirectBinding(UsdPrim p)
{
    auto a = p.GetAppliedSchemas();
    return std::find(a.begin(), a.end(), TfToken("GeospatialCRSBindingAPI")) != a.end();
}
UsdPrim FindControllingBinding(UsdPrim p)
{
    while (p && !p.IsPseudoRoot()) {
        if (HasDirectBinding(p)) {
            return p;
        }
        p = p.GetParent();
    }
    throw std::runtime_error("content outside CRS binding");
}
template <class T>
T ReadAttribute(UsdPrim p, const char* n, UsdTimeCode t, const SdfValueTypeName& type)
{
    auto a = p.GetAttribute(TfToken(n));
    T v;
    Require(a && a.GetTypeName() == type && a.Get(&v, t),
            std::string("missing, blocked or wrongly typed ") + n);
    return v;
}
std::string ReadWkt(UsdPrim p, CoordinateEngine& engine)
{
    auto a = p.GetAttribute(TfToken("crs:wkt"));
    std::vector<double> s;
    a.GetTimeSamples(&s);
    Require(a && a.GetVariability() == SdfVariabilityUniform && s.empty(),
            "invalid uniform WKT value source");
    auto w = ReadAttribute<TfToken>(p, "crs:wkt", UsdTimeCode::Default(),
                                    SdfValueTypeNames->Token)
                 .GetString();
    if (NormalizeWkt(w) != w) {
        engine.diagnostics.push_back(JsonValue("non-normal WKT spelling"));
    }
    return w;
}
void ValidatePlacementRole(UsdPrim p)
{
    for (auto n : {"crs:position", "crs:orientation"}) {
        auto a = p.GetAttribute(TfToken(n));
        Require(!a || !a.HasAuthoredValueOpinion() ||
                    (HasDirectBinding(p) &&
                     p.GetTypeName() != TfToken("GeospatialDataSource")),
                "placement field in invalid role");
    }
}
Matrix4d GetLocalTransform(UsdPrim p, UsdTimeCode t)
{
    Matrix4d m(1);
    bool reset = false;
    UsdGeomXformable x(p);
    if (x) {
        Require(x.GetLocalTransformation(&m, &reset, t),
                "ordinary transform unavailable");
    }
    return m;
}
GfMatrix3d EnuToGeocentric(double lon, double lat)
{
    const double pi = acos(-1.);
    lon *= pi / 180;
    lat *= pi / 180;
    double sl = sin(lon), cl = cos(lon), sb = sin(lat), cb = cos(lat);
    return GfMatrix3d(-sl, cl, 0, -sb * cl, -sb * sl, cb, cb * cl, cb * sl, sb);
}
GfMatrix3d StageToEnu(UsdStageRefPtr s)
{
    double u = UsdGeomGetStageMetersPerUnit(s);
    Require(std::isfinite(u) && u > 0, "invalid stage unit");
    GfMatrix3d b = UsdGeomGetStageUpAxis(s) == TfToken("Z")
                       ? GfMatrix3d(1)
                       : GfMatrix3d(1, 0, 0, 0, 0, 1, 0, -1, 0);
    return b * u;
}
GfQuatd HeadingPitchRollQuaternion(Point3d a)
{
    RequireFinite(a);
    const double f = acos(-1.) / 360;
    GfQuatd h(cos(a[0] * f), Point3d(0, 0, -sin(a[0] * f))),
        p(cos(a[1] * f), Point3d(sin(a[1] * f), 0, 0)),
        r(cos(a[2] * f), Point3d(0, sin(a[2] * f), 0));
    return h * p * r;
}
GfMatrix3d ReadOrientation(UsdPrim p, UsdTimeCode t)
{
    auto a = p.GetAttribute(TfToken("crs:orientation"));
    if (!a || !a.HasAuthoredValueOpinion()) {
        return GfMatrix3d(1);
    }
    auto sampleOrientation = [&](UsdTimeCode q) {
        return HeadingPitchRollQuaternion(ReadAttribute<Point3d>(
            p, "crs:orientation", q, SdfValueTypeNames->Double3));
    };
    std::vector<double> s;
    a.GetTimeSamples(&s);
    GfQuatd q;
    if (t.IsDefault() || s.empty()) {
        q = sampleOrientation(t);
    }
    else {
        double x = t.GetValue();
        auto i = std::upper_bound(s.begin(), s.end(), x);
        if (i == s.begin()) {
            q = sampleOrientation(s.front());
        }
        else if (i == s.end() || *(i - 1) == x ||
                 p.GetStage()->GetInterpolationType() == UsdInterpolationTypeHeld) {
            q = sampleOrientation(*(i - 1));
        }
        else {
            auto u = sampleOrientation(*(i - 1)), v = sampleOrientation(*i);
            double d =
                u.GetReal() * v.GetReal() + GfDot(u.GetImaginary(), v.GetImaginary());
            Require(abs(d) > 1e-12, "ambiguous 180-degree orientation arc; rotational "
                                    "uncertainty 2e-12 radians");
            if (d < 0) {
                v = -v;
                d = -d;
            }
            double f = (x - *(i - 1)) / (*i - *(i - 1));
            if (d > 1 - 1e-12) {
                q = (u * (1 - f) + v * f).GetNormalized();
            }
            else {
                double theta = acos(std::min(1., d));
                q = (u * sin((1 - f) * theta) + v * sin(f * theta)) * (1 / sin(theta));
            }
        }
    }
    return GfMatrix3d(q);
}
Point3d MultiplyComponents(Point3d a, Point3d b)
{
    return Point3d(a[0] * b[0], a[1] * b[1], a[2] * b[2]);
}
Point3d DivideComponents(Point3d a, Point3d b)
{
    return Point3d(a[0] / b[0], a[1] / b[1], a[2] / b[2]);
}

ModelPlacement::ModelPlacement(CoordinateEngine& en, UsdPrim prim, UsdTimeCode time,
                               ProjHandle workingOverride)
    : engine(en), prim(prim), time(time),
      source(engine, engine.ParseWkt(ReadWkt(prim, engine)), true)
{
    ValidatePlacementRole(prim);
    Require(bool(UsdGeomXformable(prim)),
            "direct model binding requires Xformable content");
    Require(prim.GetTypeName() != TfToken("GeospatialDataSource"),
            "model query on measurement carrier");
    position =
        ReadAttribute<Point3d>(prim, "crs:position", time, SdfValueTypeNames->Double3);
    RequireFinite(position);
    Require(!source.isGeocentric || position[0] != 0 || position[1] != 0,
            "geocentric pole has no attitude meridian");
    sourceGeographic = engine.WithCoordinateSystem(source.crs, false);
    sourceGeocentric = engine.WithCoordinateSystem(source.crs, true);
    Point3d llh = engine.Convert(position, source.crs, sourceGeographic);
    originEcef = engine.Convert(llh, sourceGeographic, sourceGeocentric);
    enuToEcef = EnuToGeocentric(llh[0], llh[1]);
    orientation = ReadOrientation(prim, time);
    stageToEnu = StageToEnu(prim.GetStage());
    anchorAdjustment = GetLocalTransform(prim, time);
    auto par = prim.GetParent();
    while (par && !par.IsPseudoRoot() && !HasDirectBinding(par)) {
        par = par.GetParent();
    }
    ProjHandle W = workingOverride ? workingOverride
                   : par && HasDirectBinding(par)
                       ? engine.ParseWkt(ReadWkt(par, engine))
                       : source.crs;
    working = std::make_unique<CrsInfo>(engine, W, true);
}

void ModelPlacement::PrepareChart()
{
    if (chartReady) {
        return;
    }
    chartReady = true;
    workingOrigin = engine.Convert(originEcef, sourceGeocentric, working->crs);
    if (working->isGeographic) {
        workingGeographic = engine.WithCoordinateSystem(working->crs, false);
        workingGeocentric = engine.WithCoordinateSystem(working->crs, true);
        Point3d l = engine.Convert(workingOrigin, working->crs, workingGeographic);
        workingEnuToEcef = EnuToGeocentric(l[0], l[1]);
        workingOriginEcef =
            engine.Convert(workingOrigin, working->crs, workingGeocentric);
    }
}

Point3d ModelPlacement::ToChart(Point3d coordinate)
{
    PrepareChart();
    if (working->isGeographic) {
        return (engine.Convert(coordinate, working->crs, workingGeocentric) -
                workingOriginEcef) *
               workingEnuToEcef.GetInverse() * stageToEnu.GetInverse();
    }
    return MultiplyComponents(coordinate - workingOrigin, working->componentUnits) *
           stageToEnu.GetInverse();
}

Point3d ModelPlacement::FromChart(Point3d coordinate)
{
    PrepareChart();
    if (working->isGeographic) {
        return engine.Convert(workingOriginEcef +
                                  coordinate * stageToEnu * workingEnuToEcef,
                              workingGeocentric, working->crs);
    }
    return workingOrigin +
           DivideComponents(coordinate * stageToEnu, working->componentUnits);
}

Point3d ModelPlacement::Forward(Point3d point, ProjHandle output,
                                Matrix4d descendantTransform, bool reset)
{
    // Row vectors: descendant model-space transforms, stage axes/units,
    // physical ENU orientation, then placement at the authored CRS position.
    Point3d placedEcef = originEcef + descendantTransform.Transform(point) *
                                          stageToEnu * orientation * enuToEcef;
    if (reset || anchorAdjustment == Matrix4d(1)) {
        return engine.Convert(placedEcef, sourceGeocentric, output);
    }
    // Only the anchor's ordinary adjustment follows placement, in the fixed
    // working chart. Descendant reset suppresses it, not georeferencing.
    Point3d workingCoordinate =
        engine.Convert(placedEcef, sourceGeocentric, working->crs);
    return engine.Convert(
        FromChart(anchorAdjustment.Transform(ToChart(workingCoordinate))), working->crs,
        output);
}

Point3d ModelPlacement::Inverse(Point3d point, ProjHandle input,
                                Matrix4d descendantTransform, bool reset)
{
    Point3d workingCoordinate = engine.Convert(point, input, working->crs);
    if (!reset) {
        Require(abs(anchorAdjustment.GetDeterminant()) > 1e-15,
                "singular required inverse");
        workingCoordinate = FromChart(
            anchorAdjustment.GetInverse().Transform(ToChart(workingCoordinate)));
    }
    Require(abs(descendantTransform.GetDeterminant()) > 1e-15,
            "singular instancer inverse");
    Point3d modelPoint =
        (engine.Convert(workingCoordinate, working->crs, sourceGeocentric) -
         originEcef) *
        enuToEcef.GetInverse() * orientation.GetInverse() * stageToEnu.GetInverse();
    return descendantTransform.GetInverse().Transform(modelPoint);
}

Point3d PlacementEvaluator::ResolvePoint(UsdPrim prim, Point3d point, ProjHandle output,
                                         UsdTimeCode time)
{
    auto& engine = _engine;
    ValidatePlacementRole(prim);
    auto ancestor = prim;
    while (ancestor && !ancestor.IsPseudoRoot()) {
        if (HasDirectBinding(ancestor)) {
            break;
        }
        if (ancestor.GetTypeName() == TfToken("CoordinateReferenceSystem")) {
            CrsInfo context(engine, engine.ParseWkt(ReadWkt(ancestor, engine)), false);
            Require(!context.isGeographic, "angular ordinary geometry unsupported");
            Point3d world =
                UsdGeomXformCache(time).GetLocalToWorldTransform(prim).Transform(
                    point) *
                StageToEnu(prim.GetStage());
            return engine.Convert(DivideComponents(world, context.componentUnits),
                                  context.crs, output);
        }
        ancestor = ancestor.GetParent();
    }
    auto anchor = FindControllingBinding(prim);
    for (auto ancestor = prim; ancestor != anchor; ancestor = ancestor.GetParent()) {
        ValidatePlacementRole(ancestor);
    }
    auto key = anchor.GetPath().GetString();
    if (!_models.count(key)) {
        _models[key] = std::make_shared<ModelPlacement>(engine, anchor, time);
    }
    auto cached = _models[key];
    bool reset = false;
    Matrix4d descendantTransform =
        UsdGeomXformCache(time).ComputeRelativeTransform(prim, anchor, &reset);
    return cached->Forward(point, output, descendantTransform, reset);
}

std::vector<Point3d>
PlacementEvaluator::ResolveInstance(UsdPrim instancer, int index, UsdPrim prototypePrim,
                                    const std::vector<Point3d>& points,
                                    ProjHandle output, UsdTimeCode time)
{
    auto& engine = _engine;
    UsdGeomPointInstancer pointInstancer(instancer);
    VtMatrix4dArray transforms;
    Require(pointInstancer.ComputeInstanceTransformsAtTime(
                &transforms, time, time, UsdGeomPointInstancer::ExcludeProtoXform,
                UsdGeomPointInstancer::IgnoreMask),
            "instance transforms unavailable");
    auto mask = pointInstancer.ComputeMaskAtTime(time);
    Require(mask.empty() || mask.at(index), "masked instance");
    Matrix4d instanceTransform = transforms[index];
    auto anchor = FindControllingBinding(instancer);
    ModelPlacement instancerPlacement(engine, anchor, time);
    auto fixed = engine.WithCoordinateSystem(instancerPlacement.source.crs, true);
    bool instancerReset = false;
    Matrix4d instancerRelative = UsdGeomXformCache(time).ComputeRelativeTransform(
        instancer, anchor, &instancerReset);
    SdfPathVector targets;
    pointInstancer.GetPrototypesRel().GetTargets(&targets);
    VtIntArray indices;
    pointInstancer.GetProtoIndicesAttr().Get(&indices, time);
    auto root = instancer.GetStage()->GetPrimAtPath(targets.at(indices[index]));
    auto binding = prototypePrim;
    while (binding && binding.GetPath().HasPrefix(root.GetPath()) &&
           !HasDirectBinding(binding)) {
        if (binding == root) {
            binding = UsdPrim();
            break;
        }
        binding = binding.GetParent();
    }
    std::vector<Point3d> result;
    if (binding && HasDirectBinding(binding)) {
        // An independently placed prototype retains absolute placement. Apply
        // occurrence motion by conjugating it through the instancer's map.
        auto parent = binding.GetParent();
        while (parent && parent.GetPath().HasPrefix(root.GetPath()) &&
               !HasDirectBinding(parent)) {
            parent = parent.GetParent();
        }
        ProjHandle working = parent && parent.GetPath().HasPrefix(root.GetPath()) &&
                                     HasDirectBinding(parent)
                                 ? engine.ParseWkt(ReadWkt(parent, engine))
                                 : instancerPlacement.source.crs;
        ModelPlacement prototypePlacement(engine, binding, time, working);
        bool prototypeReset = false;
        Matrix4d prototypeRelative = UsdGeomXformCache(time).ComputeRelativeTransform(
            prototypePrim, binding, &prototypeReset);
        for (const auto& point : points) {
            Point3d placed = prototypePlacement.Forward(point, fixed, prototypeRelative,
                                                        prototypeReset);
            if (instanceTransform != Matrix4d(1)) {
                Require(abs(instancerRelative.GetDeterminant()) > 1e-15,
                        "singular instancer inverse");
                placed = instancerPlacement.Forward(
                    instanceTransform.Transform(instancerPlacement.Inverse(
                        placed, fixed, instancerRelative, instancerReset)),
                    fixed, instancerRelative, instancerReset);
            }
            result.push_back(engine.Convert(placed, fixed, output));
        }
    }
    else {
        bool prototypeReset = false;
        Matrix4d prototypeTransform = UsdGeomXformCache(time).ComputeRelativeTransform(
                                          prototypePrim, root, &prototypeReset) *
                                      GetLocalTransform(root, time) * instanceTransform;
        for (const auto& point : points) {
            result.push_back(
                instancerPlacement.Forward(prototypeTransform.Transform(point), output,
                                           instancerRelative, instancerReset));
        }
    }
    return result;
}

} // namespace usdGeospatialExample
