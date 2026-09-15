//
// geoResolver.cpp -- C++ port of resolve_runtime.py (stage-level resolution).
//
#include "geoResolver.h"
#include "crsEngine.h"
#include "geospatialSchema.h"

#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/relationship.h>
#include <pxr/usd/usd/attribute.h>
#include <pxr/usd/usd/collectionAPI.h>
#include <pxr/usd/usdGeom/xform.h>
#include <pxr/base/tf/stringUtils.h>
#include <pxr/imaging/hd/xformSchema.h>
#include <pxr/imaging/hd/dataSource.h>
#include <pxr/imaging/hd/dataSourceTypeDefs.h>

#include <algorithm>
#include <vector>

PXR_NAMESPACE_OPEN_SCOPE

namespace {
const TfToken kCrsWkt("crs:wkt");
const TfToken kCrsBinding("crs:binding");
const TfToken kCrsPosition("crs:position");
const TfToken kCrsEpoch("crs:epoch");
const TfToken kBindStrengthKey("bindCRSAs");
const TfToken kWeaker("weakerThanDescendants");
const TfToken kStronger("strongerThanDescendants");
const std::string kCollection("collection");
const TfToken kCrsType("CoordinateReferenceSystem");
}

GeoResolver::GeoResolver(const UsdStagePtr& stage)
    : _stage(stage), _engine(GeoCrsEngine::GetDefault())
{
}

UsdPrim GeoResolver::_CrsTargetOf(const UsdRelationship& rel) const
{
    SdfPathVector targets;
    rel.GetTargets(&targets);
    // prefer a target that is a CRS prim
    for (const SdfPath& t : targets) {
        UsdPrim pr = _stage->GetPrimAtPath(t.GetPrimPath());
        if (pr && pr.IsValid() && pr.GetTypeName() == kCrsType) {
            return pr;
        }
    }
    // fall back to last target's prim (MaterialBinding convention: CRS is 2nd)
    if (!targets.empty()) {
        return _stage->GetPrimAtPath(targets.back().GetPrimPath());
    }
    return UsdPrim();
}

// port of _binding_rel_for_purpose:
//   purpose collection > purpose direct > all-purpose collection > all-purpose direct
//   among collections, lexicographically-smallest binding name wins.
UsdRelationship GeoResolver::_BindingRelForPurpose(const UsdPrim& prim,
                                                   const std::string& purpose,
                                                   const UsdPrim& resolvingPrim) const
{
    const UsdPrim& target = resolvingPrim ? resolvingPrim : prim;

    auto direct = [&](const std::string& p) -> UsdRelationship {
        if (!p.empty()) {
            if (p == kCollection) return UsdRelationship();
            UsdRelationship r = prim.GetRelationship(TfToken(kCrsBinding.GetString() + ":" + p));
            SdfPathVector t;
            if (r && r.GetTargets(&t) && !t.empty()) return r;
        } else {
            UsdRelationship r = prim.GetRelationship(kCrsBinding);
            SdfPathVector t;
            if (r && r.GetTargets(&t) && !t.empty()) return r;
        }
        return UsdRelationship();
    };

    // gather collection bindings that include the resolving prim
    struct CollEntry { std::string purpose; std::string name; UsdRelationship rel; };
    std::vector<CollEntry> collPurpose, collAll;

    const std::string collPrefix = kCrsBinding.GetString() + ":" + kCollection + ":";
    for (const UsdRelationship& rel : prim.GetRelationships()) {
        const std::string name = rel.GetName().GetString();
        if (name.rfind(collPrefix, 0) != 0) continue;
        SdfPathVector tgts;
        if (!rel.GetTargets(&tgts) || tgts.empty()) continue;
        // rest = name after "crs:binding:collection:" -> [name] or [purpose, name]
        std::string rest = name.substr(collPrefix.size());
        std::vector<std::string> parts = TfStringSplit(rest, ":");
        std::string relPurpose = (parts.size() == 2) ? parts[0] : "";
        std::string bindingName = parts.empty() ? "" : parts.back();

        // find collection-path target and test membership
        SdfPath collPath;
        for (const SdfPath& t : tgts) {
            if (t.GetString().find("collection:") != std::string::npos) { collPath = t; break; }
        }
        if (collPath.IsEmpty()) continue;
        UsdCollectionAPI coll = UsdCollectionAPI::GetCollection(_stage, collPath);
        if (!coll) continue;
        UsdCollectionMembershipQuery q = coll.ComputeMembershipQuery();
        if (!q.IsPathIncluded(target.GetPath())) continue;

        if (!relPurpose.empty()) collPurpose.push_back({relPurpose, bindingName, rel});
        else collAll.push_back({"", bindingName, rel});
    }

    std::sort(collAll.begin(), collAll.end(),
              [](const CollEntry& a, const CollEntry& b){ return a.name < b.name; });
    std::sort(collPurpose.begin(), collPurpose.end(),
              [](const CollEntry& a, const CollEntry& b){
                  return a.purpose != b.purpose ? a.purpose < b.purpose : a.name < b.name; });

    if (!purpose.empty()) {
        for (const auto& e : collPurpose) if (e.purpose == purpose) return e.rel; // purpose collection
        UsdRelationship d = direct(purpose);
        if (d) return d;                                                          // purpose direct
    }
    if (!collAll.empty()) return collAll.front().rel;                             // all-purpose collection
    UsdRelationship d = direct("");
    if (d) return d;                                                              // all-purpose direct
    return UsdRelationship();
}

bool GeoResolver::_RelIsStronger(const UsdRelationship& rel) const
{
    if (!rel) return false;
    VtValue v;
    if (rel.GetMetadata(kBindStrengthKey, &v) && v.IsHolding<TfToken>()) {
        return v.Get<TfToken>() == kStronger;
    }
    return false;  // default weakerThanDescendants
}

double GeoResolver::_CrsEpoch(const SdfPath& crsPrimPath) const
{
    UsdPrim cp = _stage->GetPrimAtPath(crsPrimPath);
    if (!cp || !cp.IsValid()) return -1.0;
    UsdAttribute a = cp.GetAttribute(kCrsEpoch);
    double v = 0.0;
    if (a && a.Get(&v) && v != 0.0) return v;
    return -1.0;
}

// port of crs_of_prim: walk up collecting bindings; nearest wins unless an
// ancestor is strongerThanDescendants.
bool GeoResolver::ResolveBinding(const UsdPrim& prim, std::string* srcWkt,
                                 SdfPath* crsPrimPath, SdfPath* boundPrimPath,
                                 const std::string& purpose) const
{
    struct ChainEntry { SdfPath path; UsdRelationship rel; bool stronger; };
    std::vector<ChainEntry> chain;  // nearest-first
    UsdPrim p = prim;
    while (p && p.IsValid()) {
        UsdRelationship rel = _BindingRelForPurpose(p, purpose, prim);
        if (rel) chain.push_back({p.GetPath(), rel, _RelIsStronger(rel)});
        p = p.GetParent();
    }
    if (chain.empty()) return false;

    ChainEntry chosen = chain.front();         // nearest (default weaker)
    for (size_t i = 1; i < chain.size(); ++i)  // ancestors, increasingly far
        if (chain[i].stronger) chosen = chain[i];

    UsdPrim crsPrim = _CrsTargetOf(chosen.rel);
    if (!crsPrim || !crsPrim.IsValid()) return false;
    UsdAttribute wktAttr = crsPrim.GetAttribute(kCrsWkt);
    TfToken wkt;
    if (!wktAttr || !wktAttr.Get(&wkt) || wkt.IsEmpty()) {
        TF_WARN("crs:binding on %s targets %s which has no crs:wkt; skipping.",
                chosen.path.GetText(), crsPrim.GetPath().GetText());
        return false;
    }
    if (srcWkt) *srcWkt = wkt.GetString();
    if (crsPrimPath) *crsPrimPath = crsPrim.GetPath();
    if (boundPrimPath) *boundPrimPath = chosen.path;
    return true;
}

UsdPrim GeoResolver::NearestAnchor(const UsdPrim& prim, const std::string& purpose) const
{
    UsdPrim p = prim;
    while (p && p.IsValid()) {
        if (p.GetAttribute(kCrsPosition)) {
            std::string wkt;
            if (ResolveBinding(p, &wkt, nullptr, nullptr, purpose)) return p;
        }
        p = p.GetParent();
    }
    return UsdPrim();
}

bool GeoResolver::AnchorFrame(const UsdPrim& prim, GfMatrix4d* frame,
                             const std::string& purpose) const
{
    std::string srcWkt; SdfPath crsPath;
    if (!ResolveBinding(prim, &srcWkt, &crsPath, nullptr, purpose)) return false;
    UsdAttribute posA = prim.GetAttribute(kCrsPosition);
    GfVec3d pos;
    if (!posA || !posA.Get(&pos)) return false;
    double epoch = _CrsEpoch(crsPath);
    *frame = _engine.LocalFrameToEcef(srcWkt, pos[0], pos[1], pos[2], epoch);
    return true;
}

bool GeoResolver::ResolveWorldTranslation(const UsdPrim& prim, GfVec3d* world,
                                          const std::string& purpose) const
{
    std::string srcWkt; SdfPath crsPath;
    if (!ResolveBinding(prim, &srcWkt, &crsPath, nullptr, purpose)) return false;
    UsdAttribute posA = prim.GetAttribute(kCrsPosition);
    GfVec3d pos;
    if (!posA || !posA.Get(&pos)) return false;
    double epoch = _CrsEpoch(crsPath);
    GfVec3d georef = _engine.Reproject(srcWkt, "EPSG:4978", pos[0], pos[1], pos[2], epoch);

    // compose ancestor cartesian transform on top (port ancestor_local_to_world)
    UsdPrim parent = prim.GetParent();
    GfMatrix4d a2w(1.0);
    if (parent && parent.IsValid()) {
        std::lock_guard<std::mutex> lock(_xformCacheMutex);
        a2w = _xformCache.GetLocalToWorldTransform(parent);
    }
    *world = a2w.Transform(georef);
    return true;
}

// port of resolve_with_injection
bool GeoResolver::ResolveWithInjection(const UsdPrim& prim, GfMatrix4d* world,
                                       SdfPath* anchorPath,
                                       const std::string& purpose) const
{
    UsdPrim anchor = NearestAnchor(prim, purpose);
    if (!anchor || !anchor.IsValid()) return false;
    GfMatrix4d frame;
    if (!AnchorFrame(anchor, &frame, purpose)) return false;
    if (anchorPath) *anchorPath = anchor.GetPath();

    if (prim.GetPath() == anchor.GetPath()) {
        *world = frame;
        return true;
    }
    // local-to-anchor = desc_authored * anchor_authored^-1   (Gf row-vector)
    GfMatrix4d anchorAuthored, descAuthored;
    {
        std::lock_guard<std::mutex> lock(_xformCacheMutex);
        anchorAuthored = _xformCache.GetLocalToWorldTransform(anchor);
        descAuthored = _xformCache.GetLocalToWorldTransform(prim);
    }
    GfMatrix4d localToAnchor = descAuthored * anchorAuthored.GetInverse();
    *world = localToAnchor * frame;  // compose under the injected anchor frame
    return true;
}

// ===========================================================================
// HYDRA-DATA-SOURCE PATH (stage-free)
// ===========================================================================

bool GeoResolver::_ReadGeoDS(const HdSceneIndexBaseRefPtr& si,
                             const SdfPath& primPath,
                             bool* hasPos, GfVec3d* pos,
                             SdfPathVector* binding, bool* stronger) const
{
    if (!si) return false;
    HdSceneIndexPrim prim = si->GetPrim(primPath);
    if (!prim.dataSource) return false;
    HdContainerDataSourceHandle geo =
        HdContainerDataSource::Cast(
            prim.dataSource->Get(UsdGeospatialSchemaTokens->geospatial));
    if (!geo) return false;

    if (hasPos) *hasPos = false;
    if (auto pds = HdTypedSampledDataSource<GfVec3d>::Cast(
            geo->Get(UsdGeospatialSchemaTokens->position))) {
        if (pos) *pos = pds->GetTypedValue(0.0f);
        if (hasPos) *hasPos = true;
    }
    if (binding) binding->clear();
    if (auto bds = HdTypedSampledDataSource<VtArray<SdfPath>>::Cast(
            geo->Get(UsdGeospatialSchemaTokens->binding))) {
        VtArray<SdfPath> paths = bds->GetTypedValue(0.0f);
        if (binding) binding->assign(paths.begin(), paths.end());
    }
    if (stronger) {
        *stronger = false;
        if (auto sds = HdTypedSampledDataSource<bool>::Cast(
                geo->Get(UsdGeospatialSchemaTokens->bindingStronger))) {
            *stronger = sds->GetTypedValue(0.0f);
        }
    }
    return true;
}

bool GeoResolver::_WktOfHydra(const HdSceneIndexBaseRefPtr& si,
                             const SdfPathVector& binding,
                             std::string* wkt, double* epoch) const
{
    if (!si) return false;
    // Prefer a target whose geospatial DS carries a wkt (the CRS prim).
    for (const SdfPath& t : binding) {
        HdSceneIndexPrim cp = si->GetPrim(t.GetPrimPath());
        if (!cp.dataSource) continue;
        HdContainerDataSourceHandle geo =
            HdContainerDataSource::Cast(
                cp.dataSource->Get(UsdGeospatialSchemaTokens->geospatial));
        if (!geo) continue;
        auto wds = HdTypedSampledDataSource<std::string>::Cast(
            geo->Get(UsdGeospatialSchemaTokens->wkt));
        if (!wds) continue;
        std::string w = wds->GetTypedValue(0.0f);
        if (w.empty()) continue;
        if (wkt) *wkt = w;
        if (epoch) {
            *epoch = -1.0;
            if (auto eds = HdTypedSampledDataSource<double>::Cast(
                    geo->Get(UsdGeospatialSchemaTokens->epoch))) {
                double e = eds->GetTypedValue(0.0f);
                if (e != 0.0) *epoch = e;
            }
        }
        return true;
    }
    return false;
}

SdfPath GeoResolver::NearestAnchorHydra(const HdSceneIndexBaseRefPtr& si,
                                        const SdfPath& primPath) const
{
    SdfPath p = primPath;
    while (!p.IsEmpty() && p != SdfPath::AbsoluteRootPath()) {
        bool hasPos = false; GfVec3d pos; SdfPathVector binding; bool stronger;
        if (_ReadGeoDS(si, p, &hasPos, &pos, &binding, &stronger) &&
            hasPos && !binding.empty()) {
            std::string wkt;
            if (_WktOfHydra(si, binding, &wkt, nullptr)) {
                return p;
            }
        }
        p = p.GetParentPath();
    }
    return SdfPath();
}

bool GeoResolver::_AnchorFrameHydra(const HdSceneIndexBaseRefPtr& si,
                                    const SdfPath& anchorPath,
                                    GfMatrix4d* frame) const
{
    bool hasPos = false; GfVec3d pos; SdfPathVector binding; bool stronger;
    if (!_ReadGeoDS(si, anchorPath, &hasPos, &pos, &binding, &stronger) ||
        !hasPos || binding.empty()) {
        return false;
    }
    std::string wkt; double epoch = -1.0;
    if (!_WktOfHydra(si, binding, &wkt, &epoch)) return false;
    *frame = _engine.LocalFrameToEcef(wkt, pos[0], pos[1], pos[2], epoch);
    return true;
}

// Compose the authored local-to-world from HdXformSchema matrices in `si`,
// walking to the root. Honors resetXformStack (stops composing ancestors).
GfMatrix4d GeoResolver::_AuthoredL2WHydra(const HdSceneIndexBaseRefPtr& si,
                                          const SdfPath& primPath) const
{
    GfMatrix4d acc(1.0);
    SdfPath p = primPath;
    while (!p.IsEmpty() && p != SdfPath::AbsoluteRootPath()) {
        HdSceneIndexPrim prim = si->GetPrim(p);
        HdXformSchema xs = HdXformSchema::GetFromParent(prim.dataSource);
        bool reset = false;
        if (xs.IsDefined()) {
            if (auto rds = xs.GetResetXformStack()) {
                reset = rds->GetTypedValue(0.0f);
            }
            if (auto mds = xs.GetMatrix()) {
                // Gf row-vector: local-to-world = local * parentLocalToWorld,
                // accumulated child-first.
                acc = acc * mds->GetTypedValue(0.0f);
            }
        }
        if (reset) break;  // reset means ignore ancestors above this prim
        p = p.GetParentPath();
    }
    return acc;
}

bool GeoResolver::ResolveWithInjectionHydra(const HdSceneIndexBaseRefPtr& si,
                                            const SdfPath& primPath,
                                            GfMatrix4d* world,
                                            SdfPath* anchorPath) const
{
    SdfPath anchor = NearestAnchorHydra(si, primPath);
    if (anchor.IsEmpty()) return false;
    GfMatrix4d frame;
    if (!_AnchorFrameHydra(si, anchor, &frame)) return false;
    if (anchorPath) *anchorPath = anchor;

    if (primPath == anchor) {
        *world = frame;
        return true;
    }
    // local-to-anchor = desc_authored * anchor_authored^-1 (Gf row-vector),
    // computed from Hydra xform matrices (mirrors the stage path).
    GfMatrix4d anchorAuthored = _AuthoredL2WHydra(si, anchor);
    GfMatrix4d descAuthored   = _AuthoredL2WHydra(si, primPath);
    GfMatrix4d localToAnchor = descAuthored * anchorAuthored.GetInverse();
    *world = localToAnchor * frame;
    return true;
}

PXR_NAMESPACE_CLOSE_SCOPE
