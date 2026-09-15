//
// geospatialSchema.h -- token names + locator for the "geospatial" Hydra data
// source emitted by UsdGeospatialAPISchemaAdapter and consumed by
// UsdGeospatialSceneIndex / GeoResolver. Keeps the data-stream contract in one
// place (mirrors how HdXformSchema centralizes the xform locator/tokens).
//
#ifndef USDGEOSPATIAL_SCHEMA_H
#define USDGEOSPATIAL_SCHEMA_H

#include <pxr/pxr.h>
#include <pxr/base/tf/staticTokens.h>
#include <pxr/imaging/hd/dataSourceLocator.h>

PXR_NAMESPACE_OPEN_SCOPE

#define USDGEOSPATIAL_SCHEMA_TOKENS \
    (geospatial)                    \
    (position)                      \
    (binding)                       \
    (bindingStronger)               \
    (wkt)                           \
    (epoch)

TF_DECLARE_PUBLIC_TOKENS(UsdGeospatialSchemaTokens, USDGEOSPATIAL_SCHEMA_TOKENS);

/// The container locator for the geospatial data source ("geospatial").
inline const HdDataSourceLocator& UsdGeospatialSchemaGetDefaultLocator()
{
    static const HdDataSourceLocator loc(UsdGeospatialSchemaTokens->geospatial);
    return loc;
}

PXR_NAMESPACE_CLOSE_SCOPE

#endif
