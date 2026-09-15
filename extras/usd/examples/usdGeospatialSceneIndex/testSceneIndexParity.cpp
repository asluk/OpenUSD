//
// testSceneIndexParity.cpp -- run the parity datasets THROUGH the Hydra scene
// index and assert the xform pulled via Hydra data sources matches the oracle.
//
// Pipeline: UsdStage -> UsdImagingStageSceneIndex -> UsdGeospatialSceneIndex.
// For each oracle row we GetPrim(primPath) on the filtered scene index, pull
// the HdXformSchema matrix (the value a renderer would consume), and compare its
// translation (origin) to the closed-form GT and the Python runtime output.
//
// This proves the geospatial resolution happens IN HYDRA at render-pull time
// (not just in a standalone resolver): the picture a renderer gets is correct.
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
            p.geoSi = UsdGeospatialSceneIndex::New(p.usdSi);
            p.geoSi->SetStage(p.stage);
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
    std::printf("----\n[HYDRA] %d rows, %d fail; worst vsGT=%.5f mm, worst vsPython=%.5f mm (tol %.1f mm)\n",
                n, fail, worst_gt, worst_py, tol_mm);
    return fail ? 1 : 0;
}
