//
// dumpHydraXforms.cpp -- emit, for every prim on a stage, the world xform matrix
// resolved THROUGH the Hydra scene index (UsdStage -> UsdImagingStageSceneIndex
// -> UsdGeospatialSceneIndex), pulled via HdXformSchema exactly as a renderer
// consumes it. Output (one row per prim with an xform):
//   primPath \t m00 m01 ... m33   (16 doubles, row-major, Gf row-vector layout)
//
// Used to build the VISUAL parity figure: the Python figure resolves the railway
// tiles+rails with resolve_runtime; this gives the SAME geometry resolved by the
// compiled Hydra runtime, so we can draw both and show the picture is identical.
//
#include "geospatialSceneIndex.h"

#include <pxr/pxr.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usd/primRange.h>
#include <pxr/usdImaging/usdImaging/stageSceneIndex.h>
#include <pxr/imaging/hd/xformSchema.h>

#include <cstdio>

PXR_NAMESPACE_USING_DIRECTIVE

int main(int argc, char** argv)
{
    if (argc < 2) { std::fprintf(stderr, "usage: %s stage.usda\n", argv[0]); return 2; }
    auto stage = UsdStage::Open(argv[1]);
    if (!stage) { std::fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }

    auto usdSi = UsdImagingStageSceneIndex::New();
    usdSi->SetStage(stage);
    usdSi->SetTime(UsdTimeCode::Default());
    usdSi->ApplyPendingUpdates();

    auto geoSi = UsdGeospatialSceneIndex::New(usdSi);
    geoSi->SetStage(stage);

    for (const UsdPrim& prim : stage->Traverse()) {
        SdfPath path = prim.GetPath();
        HdSceneIndexPrim sip = geoSi->GetPrim(path);
        HdXformSchema xs = HdXformSchema::GetFromParent(sip.dataSource);
        if (!xs.IsDefined() || !xs.GetMatrix()) continue;
        GfMatrix4d M = xs.GetMatrix()->GetTypedValue(0.0f);
        std::printf("%s", path.GetText());
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j)
                std::printf("\t%.10g", M[i][j]);
        std::printf("\n");
    }
    return 0;
}
