// probeHydra.cpp -- dump the Hydra container data source keys for a prim to see
// whether custom crs:* attributes/relationships survive into the Hydra stream.
#include <pxr/pxr.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usdImaging/usdImaging/stageSceneIndex.h>
#include <pxr/imaging/hd/sceneIndex.h>
#include <pxr/imaging/hd/dataSource.h>
#include <cstdio>
#include <string>

PXR_NAMESPACE_USING_DIRECTIVE

static void dumpContainer(const HdContainerDataSourceHandle& c, const std::string& indent, int depth) {
    if (!c || depth > 3) return;
    for (const TfToken& name : c->GetNames()) {
        HdDataSourceBaseHandle child = c->Get(name);
        const char* kind = "?";
        if (HdContainerDataSource::Cast(child)) kind = "container";
        else if (HdSampledDataSource::Cast(child)) kind = "sampled";
        std::printf("%s%s [%s]\n", indent.c_str(), name.GetText(), kind);
        if (auto cc = HdContainerDataSource::Cast(child)) {
            dumpContainer(cc, indent + "  ", depth + 1);
        }
    }
}

int main(int argc, char** argv) {
    if (argc < 3) { std::fprintf(stderr, "usage: %s stage.usda /Prim/Path\n", argv[0]); return 2; }
    UsdStageRefPtr stage = UsdStage::Open(argv[1]);
    if (!stage) { std::fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }
    auto si = UsdImagingStageSceneIndex::New();
    si->SetStage(stage);
    si->SetTime(UsdTimeCode::Default());
    si->ApplyPendingUpdates();

    SdfPath p(argv[2]);
    HdSceneIndexPrim prim = si->GetPrim(p);
    std::printf("primType=%s dataSource=%p\n", prim.primType.GetText(), (void*)prim.dataSource.get());
    if (prim.dataSource) dumpContainer(prim.dataSource, "  ", 0);
    return 0;
}
