// testHydraAutoParity.cpp -- STAGE-FREE parity: prove the auto-insertion data
// path works. The scene index is given NO stage (SetStage is never called), so
// it MUST resolve crs:* purely from the Hydra data sources surfaced by the
// keyless UsdGeospatialAPISchemaAdapter (loaded via PXR_PLUGINPATH_NAME).
//
// This is the numeric twin of the usdview screenshot: same auto-insert data
// flow (adapter -> geospatial DS -> SI hydra path), asserted to the oracle.
//
// Pipeline: UsdStage -> UsdImagingStageSceneIndex -> UsdGeospatialSceneIndex(NO stage).
//
#include "geospatialSceneIndex.h"

#include <pxr/pxr.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usdImaging/usdImaging/stageSceneIndex.h>
#include <pxr/imaging/hd/xformSchema.h>
#include <pxr/imaging/hd/sceneIndex.h>
#include <pxr/base/gf/matrix4d.h>
#include <pxr/base/gf/vec3d.h>

#include <cstdio>
#include <cmath>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <unordered_map>

PXR_NAMESPACE_USING_DIRECTIVE

static std::vector<std::string> split_tabs(const std::string& line) {
    std::vector<std::string> f; std::stringstream ss(line); std::string t;
    while (std::getline(ss, t, '\t')) f.push_back(t);
    return f;
}

struct Pipeline {
    UsdStageRefPtr stage;
    UsdImagingStageSceneIndexRefPtr usdSi;
    UsdGeospatialSceneIndexRefPtr geoSi;
};

int main(int argc, char** argv)
{
    if (argc < 2) { std::fprintf(stderr, "usage: %s oracle.tsv [tol_mm]\n", argv[0]); return 2; }
    const double tol_mm = (argc >= 3) ? std::atof(argv[2]) : 5.0;

    std::ifstream in(argv[1]);
    if (!in) { std::fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }

    std::unordered_map<std::string, Pipeline> pipes;
    std::string line;
    int n=0, fail=0;
    double worst_gt=0.0, worst_py=0.0;
    while (std::getline(in, line)) {
        if (line.empty() || line[0]=='#') continue;
        auto f = split_tabs(line);
        if (f.size() < 9) continue;
        const std::string& stagePath = f[0];
        const std::string& primPath = f[1];
        const std::string& kind = f[2];
        GfVec3d gt(std::stod(f[3]), std::stod(f[4]), std::stod(f[5]));
        GfVec3d py(std::stod(f[6]), std::stod(f[7]), std::stod(f[8]));

        if (!pipes.count(stagePath)) {
            Pipeline p;
            p.stage = UsdStage::Open(stagePath);
            if (!p.stage) { std::fprintf(stderr,"FAIL open %s\n",stagePath.c_str()); ++fail; continue; }
            p.usdSi = UsdImagingStageSceneIndex::New();
            p.usdSi->SetStage(p.stage);
            p.usdSi->SetTime(UsdTimeCode::Default());
            p.usdSi->ApplyPendingUpdates();
            // NOTE: NO SetStage on geoSi -- hydra-data-source path only.
            p.geoSi = UsdGeospatialSceneIndex::New(p.usdSi);
            pipes[stagePath] = p;
        }
        Pipeline& P = pipes[stagePath];

        HdSceneIndexPrim siPrim = P.geoSi->GetPrim(SdfPath(primPath));
        HdXformSchema xs = HdXformSchema::GetFromParent(siPrim.dataSource);
        if (!xs.IsDefined() || !xs.GetMatrix()) {
            std::printf("FAIL %-40s %-12s (no xform from Hydra)\n", primPath.c_str(), kind.c_str());
            ++fail; ++n; continue;
        }
        GfMatrix4d M = xs.GetMatrix()->GetTypedValue(0.0f);
        GfVec3d origin = M.Transform(GfVec3d(0,0,0));

        double d_gt = (origin - gt).GetLength()*1e3;
        double d_py = (origin - py).GetLength()*1e3;
        worst_gt = std::max(worst_gt, d_gt);
        worst_py = std::max(worst_py, d_py);
        bool ok = d_gt < tol_mm && d_py < tol_mm;
        if (!ok) ++fail;
        std::printf("%-4s %-40s %-12s  vsGT=%.5f mm  vsPython=%.5f mm\n",
                    ok?"ok":"FAIL", primPath.c_str(), kind.c_str(), d_gt, d_py);
        ++n;
    }
    std::printf("----\n[HYDRA-AUTO] %d rows, %d fail; worst vsGT=%.5f mm, worst vsPython=%.5f mm (tol %.1f mm)\n",
                n, fail, worst_gt, worst_py, tol_mm);
    return fail ? 1 : 0;
}
