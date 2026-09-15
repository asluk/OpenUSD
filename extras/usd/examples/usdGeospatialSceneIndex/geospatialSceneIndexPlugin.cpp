#include <pxr/imaging/hd/sceneIndexPluginRegistry.h>

#include "geospatialSceneIndexPlugin.h"
#include "geospatialSceneIndex.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DEFINE_PRIVATE_TOKENS(
    _tokens,
    ((sceneIndexPluginName, "UsdGeospatialSceneIndexPlugin"))
);

TF_REGISTRY_FUNCTION(TfType)
{
    HdSceneIndexPluginRegistry::Define<UsdGeospatialSceneIndexPlugin>();
}

TF_REGISTRY_FUNCTION(HdSceneIndexPlugin)
{
    const HdSceneIndexPluginRegistry::InsertionPhase insertionPhase = 1;
    // Register for all renderers, inserted early (geospatial resolution should
    // happen before downstream xform-dependent indices).
    HdSceneIndexPluginRegistry::GetInstance().RegisterSceneIndexForRenderer(
        "",
        _tokens->sceneIndexPluginName,
        nullptr,
        insertionPhase,
        HdSceneIndexPluginRegistry::InsertionOrderAtStart);
}

UsdGeospatialSceneIndexPlugin::UsdGeospatialSceneIndexPlugin() = default;

HdSceneIndexBaseRefPtr UsdGeospatialSceneIndexPlugin::_AppendSceneIndex(
    const HdSceneIndexBaseRefPtr& inputScene,
    const HdContainerDataSourceHandle& inputArgs)
{
    // NOTE: in a renderer pipeline the source UsdStage is supplied to the new
    // scene index out-of-band (the scene index resolves crs:binding against the
    // stage). See UsdGeospatialSceneIndex::SetStage; the parity harness wires it
    // explicitly. WKT remains opaque to USD; only GeoCrsEngine (PROJ) reads it.
    return UsdGeospatialSceneIndex::New(inputScene, inputArgs);
}

PXR_NAMESPACE_CLOSE_SCOPE
