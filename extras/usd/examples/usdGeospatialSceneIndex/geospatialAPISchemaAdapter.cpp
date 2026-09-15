//
// geospatialAPISchemaAdapter.cpp -- implementation of the keyless API-schema
// adapter that lifts crs:* properties into the Hydra "geospatial" data source.
//
#include "geospatialAPISchemaAdapter.h"
#include "geospatialSchema.h"

#include <pxr/base/tf/staticTokens.h>
#include <pxr/base/tf/stringUtils.h>
#include <pxr/base/vt/array.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/attribute.h>
#include <pxr/usd/usd/relationship.h>
#include <pxr/imaging/hd/retainedDataSource.h>
#include <pxr/usdImaging/usdImaging/dataSourceAttribute.h>
#include <pxr/base/tf/type.h>

PXR_NAMESPACE_OPEN_SCOPE

// Register the keyless API-schema adapter's TfType so the UsdImaging adapter
// registry can discover + construct it (keyed by the EMPTY apiSchemaName in
// plugInfo.json -> runs for every prim).
TF_REGISTRY_FUNCTION(TfType)
{
    using Adapter = UsdGeospatialAPISchemaAdapter;
    TfType t = TfType::Define<Adapter, TfType::Bases<Adapter::BaseAdapter>>();
    t.SetFactory<UsdImagingAPISchemaAdapterFactory<Adapter>>();
}

namespace {
const TfToken kCrsWkt("crs:wkt");
const TfToken kCrsBinding("crs:binding");
const TfToken kCrsPosition("crs:position");
const TfToken kCrsEpoch("crs:epoch");
const TfToken kBindStrengthKey("bindCRSAs");
const TfToken kStronger("strongerThanDescendants");
}

HdContainerDataSourceHandle
UsdGeospatialAPISchemaAdapter::GetImagingSubprimData(
    UsdPrim const& prim,
    TfToken const& subprim,
    TfToken const& appliedInstanceName,
    const UsdImagingDataSourceStageGlobals& stageGlobals)
{
    // Only the primary prim (no subprim / no multi-apply instance).
    if (!subprim.IsEmpty() || !appliedInstanceName.IsEmpty()) {
        return nullptr;
    }

    // Detect the codeless crs:* properties directly off the USD prim. This is
    // the whole point: we read the custom attrs/rels here (where we DO have the
    // UsdPrim) and re-express them as Hydra data sources.
    UsdAttribute posAttr = prim.GetAttribute(kCrsPosition);
    UsdRelationship bindingRel = prim.GetRelationship(kCrsBinding);
    UsdAttribute wktAttr = prim.GetAttribute(kCrsWkt);
    UsdAttribute epochAttr = prim.GetAttribute(kCrsEpoch);

    const bool hasPos = posAttr && posAttr.HasAuthoredValue();
    bool hasBinding = false;
    SdfPathVector bindingTargets;
    if (bindingRel) {
        bindingRel.GetTargets(&bindingTargets);
        hasBinding = !bindingTargets.empty();
    }
    const bool hasWkt = wktAttr && wktAttr.HasAuthoredValue();

    // Nothing geospatial on this prim -> no contribution (keeps the keyless
    // adapter cheap for the vast majority of prims).
    if (!hasPos && !hasBinding && !hasWkt) {
        return nullptr;
    }

    std::vector<TfToken> names;
    std::vector<HdDataSourceBaseHandle> values;

    if (hasPos) {
        names.push_back(UsdGeospatialSchemaTokens->position);
        values.push_back(
            UsdImagingDataSourceAttribute<GfVec3d>::New(posAttr, stageGlobals));
    }
    if (hasBinding) {
        VtArray<SdfPath> paths(bindingTargets.begin(), bindingTargets.end());
        names.push_back(UsdGeospatialSchemaTokens->binding);
        values.push_back(
            HdRetainedTypedSampledDataSource<VtArray<SdfPath>>::New(paths));

        // strength metadata on the relationship (bindCRSAs).
        bool stronger = false;
        VtValue sv;
        if (bindingRel.GetMetadata(kBindStrengthKey, &sv) &&
            sv.IsHolding<TfToken>()) {
            stronger = (sv.Get<TfToken>() == kStronger);
        }
        names.push_back(UsdGeospatialSchemaTokens->bindingStronger);
        values.push_back(
            HdRetainedTypedSampledDataSource<bool>::New(stronger));
    }
    if (hasWkt) {
        // crs:wkt is a uniform token; expose as string for the engine.
        TfToken wkt;
        wktAttr.Get(&wkt);
        names.push_back(UsdGeospatialSchemaTokens->wkt);
        values.push_back(
            HdRetainedTypedSampledDataSource<std::string>::New(wkt.GetString()));

        double epoch = 0.0;
        if (epochAttr) epochAttr.Get(&epoch);
        names.push_back(UsdGeospatialSchemaTokens->epoch);
        values.push_back(
            HdRetainedTypedSampledDataSource<double>::New(epoch));
    }

    HdContainerDataSourceHandle geo =
        HdRetainedContainerDataSource::New(
            names.size(), names.data(), values.data());

    return HdRetainedContainerDataSource::New(
        UsdGeospatialSchemaTokens->geospatial, geo);
}

HdDataSourceLocatorSet
UsdGeospatialAPISchemaAdapter::InvalidateImagingSubprim(
    UsdPrim const& prim,
    TfToken const& subprim,
    TfToken const& appliedInstanceName,
    TfTokenVector const& properties,
    UsdImagingPropertyInvalidationType invalidationType)
{
    if (!subprim.IsEmpty() || !appliedInstanceName.IsEmpty()) {
        return HdDataSourceLocatorSet();
    }
    for (const TfToken& p : properties) {
        if (TfStringStartsWith(p.GetString(), "crs:")) {
            return UsdGeospatialSchemaGetDefaultLocator();
        }
    }
    return HdDataSourceLocatorSet();
}

PXR_NAMESPACE_CLOSE_SCOPE
