//
// geospatialAPISchemaAdapter.h -- a KEYLESS UsdImaging API-schema adapter that
// surfaces the codeless usdGeospatial schema's custom crs:* properties into the
// Hydra scene as data sources on each prim.
//
// WHY KEYLESS: the usdGeospatial schema is CODELESS -- crs:binding / crs:position
// are authored as plain custom USD relationship/attribute, and CoordinateReference
// System.crs:wkt is a plain custom attr. There is NO applied API schema type to key
// an adapter off. UsdImaging supports a "keyless" API-schema adapter (registered
// with an EMPTY apiSchemaName) that runs GetImagingSubprimData for EVERY prim; we
// use that to detect crs:* properties and emit a "geospatial" container data source.
//
// This is the missing piece the probe (probeHydra.cpp) diagnosed: without it the
// crs:* data never enters the Hydra stream, so a downstream scene-index filter
// cannot see it. With it, UsdGeospatialSceneIndex can resolve purely from Hydra
// data sources -- no UsdStage handle required -- which is what makes AUTO-INSERTION
// in usdview / UsdImagingGLEngine actually work.
//
// Contract of the emitted "geospatial" container (see geospatialSchema tokens):
//   geospatial/position       double3  (crs:position; axis order lon/E, lat/N, h)
//   geospatial/binding        path[]   (crs:binding relationship targets)
//   geospatial/bindingStronger bool    (bindCRSAs == strongerThanDescendants)
//   geospatial/wkt            string   (crs:wkt; present on CoordinateReferenceSystem prims)
//   geospatial/epoch          double   (crs:epoch; present on CRS prims, 0 if unset)
//
#ifndef USDGEOSPATIAL_API_SCHEMA_ADAPTER_H
#define USDGEOSPATIAL_API_SCHEMA_ADAPTER_H

#include <pxr/pxr.h>
#include <pxr/usdImaging/usdImaging/apiSchemaAdapter.h>

#include "api.h"

PXR_NAMESPACE_OPEN_SCOPE

/// Keyless API-schema adapter: emits the "geospatial" data source for any prim
/// carrying crs:* properties.
class UsdGeospatialAPISchemaAdapter : public UsdImagingAPISchemaAdapter
{
public:
    using BaseAdapter = UsdImagingAPISchemaAdapter;

    USDGEOSPATIAL_SI_API
    HdContainerDataSourceHandle GetImagingSubprimData(
        UsdPrim const& prim,
        TfToken const& subprim,
        TfToken const& appliedInstanceName,
        const UsdImagingDataSourceStageGlobals& stageGlobals) override;

    USDGEOSPATIAL_SI_API
    HdDataSourceLocatorSet InvalidateImagingSubprim(
        UsdPrim const& prim,
        TfToken const& subprim,
        TfToken const& appliedInstanceName,
        TfTokenVector const& properties,
        UsdImagingPropertyInvalidationType invalidationType) override;
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif
