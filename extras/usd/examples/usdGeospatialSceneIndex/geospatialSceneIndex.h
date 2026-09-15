//
// geospatialSceneIndex.h -- an illustrative Hydra scene index for the geospatial schema.
//
// A filtering scene index that performs geospatial resolution at render time:
// for any prim that resolves to a geospatial anchor (via crs:binding/crs:position),
// it OVERRIDES the prim's xform matrix locator with the inject-don't-bake ENU->ECEF
// transform computed by GeoResolver (the same code proven at sub-mm parity against
// the Python reference runtime). Children are dirtied on anchor change.
//
// Design (ported from NVIDIA omniGeoSceneIndex, updated to current Hydra +
// retargeted from the OmniWGS84* API schemas to our crs:binding/crs:position):
//   * HdSingleInputFilteringSceneIndexBase, lazy per-prim wrapping.
//   * The xform override is supplied via an overlay container data source that
//     intercepts the HdXformSchema matrix locator.
//   * GeoResolver needs the UsdStage for binding/collection resolution; it is
//     provided at construction (via inputArgs "stage" data source) since this is
//     a stage-backed scene index, mirroring how UsdImagingStageSceneIndex carries
//     stage context.
//
#ifndef USDGEOSPATIAL_SCENE_INDEX_H
#define USDGEOSPATIAL_SCENE_INDEX_H

#include <pxr/pxr.h>
#include <pxr/usd/sdf/pathTable.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/imaging/hd/filteringSceneIndex.h>

#include "api.h"

#include <memory>

PXR_NAMESPACE_OPEN_SCOPE

class GeoResolver;

TF_DECLARE_REF_PTRS(UsdGeospatialSceneIndex);

class UsdGeospatialSceneIndex : public HdSingleInputFilteringSceneIndexBase
{
public:
    USDGEOSPATIAL_SI_API
    static UsdGeospatialSceneIndexRefPtr New(
        const HdSceneIndexBaseRefPtr& inputSceneIndex,
        const HdContainerDataSourceHandle& inputArgs = nullptr);

    USDGEOSPATIAL_SI_API ~UsdGeospatialSceneIndex() override;

    USDGEOSPATIAL_SI_API
    HdSceneIndexPrim GetPrim(const SdfPath& primPath) const override;

    USDGEOSPATIAL_SI_API
    SdfPathVector GetChildPrimPaths(const SdfPath& primPath) const override;

    /// Provide the source UsdStage used for binding resolution (call once after
    /// construction when not supplied via inputArgs).
    USDGEOSPATIAL_SI_API
    void SetStage(const UsdStagePtr& stage);

protected:
    UsdGeospatialSceneIndex(const HdSceneIndexBaseRefPtr& inputSceneIndex,
                            const HdContainerDataSourceHandle& inputArgs);

    void _PrimsAdded(const HdSceneIndexBase& sender,
        const HdSceneIndexObserver::AddedPrimEntries& entries) override;
    void _PrimsRemoved(const HdSceneIndexBase& sender,
        const HdSceneIndexObserver::RemovedPrimEntries& entries) override;
    void _PrimsDirtied(const HdSceneIndexBase& sender,
        const HdSceneIndexObserver::DirtiedPrimEntries& entries) override;

private:
    UsdStagePtr _stage;
    std::shared_ptr<GeoResolver> _resolver;
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif
