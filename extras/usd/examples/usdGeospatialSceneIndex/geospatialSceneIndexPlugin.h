//
// geospatialSceneIndexPlugin.h / .cpp -- HdSceneIndexPlugin registration.
//
#ifndef USDGEOSPATIAL_SCENE_INDEX_PLUGIN_H
#define USDGEOSPATIAL_SCENE_INDEX_PLUGIN_H

#include <pxr/pxr.h>
#include <pxr/imaging/hd/sceneIndexPlugin.h>

#include "api.h"

PXR_NAMESPACE_OPEN_SCOPE

/// Registers UsdGeospatialSceneIndex with the Hydra scene-index plugin registry,
/// for all renderers, inserted early. Mirrors hdParticleField's plugInfo-based
/// registration pattern, but registers an HdSceneIndexPlugin (a FILTER that
/// rewrites xforms) rather than an HdRendererPlugin.
class UsdGeospatialSceneIndexPlugin : public HdSceneIndexPlugin
{
public:
    UsdGeospatialSceneIndexPlugin();

protected:
    HdSceneIndexBaseRefPtr _AppendSceneIndex(
        const HdSceneIndexBaseRefPtr& inputScene,
        const HdContainerDataSourceHandle& inputArgs) override;
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif
