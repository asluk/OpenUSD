//
// testGeoResolver.cpp -- parity of the C++ GeoResolver (stage-level) against the
// Python reference runtime AND closed-form geodesy.
//
// Reads out/parity/oracle.tsv (from dump_oracle.py). For each row:
//   * open the stage, get the prim
//   * translation rows: ResolveWorldTranslation -> compare vs GT and vs python
//   * frame rows: AnchorFrame -> compare M.Transform(0,0,0) vs GT, and the full
//     resolved frame's origin vs python
// Reports worst error in mm; exits nonzero if any exceeds tolerance.
//
#include "geoResolver.h"
#include "crsEngine.h"

#include <pxr/pxr.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/base/gf/vec3d.h>
#include <pxr/base/gf/matrix4d.h>

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

int main(int argc, char** argv)
{
    if (argc < 2) { std::fprintf(stderr, "usage: %s oracle.tsv [tol_mm]\n", argv[0]); return 2; }
    const double tol_mm = (argc >= 3) ? std::atof(argv[2]) : 5.0;

    std::ifstream in(argv[1]);
    if (!in) { std::fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }

    // cache opened stages + their resolver
    std::unordered_map<std::string, UsdStageRefPtr> stages;
    std::unordered_map<std::string, GeoResolver*> resolvers;

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

        if (!stages.count(stagePath)) {
            UsdStageRefPtr s = UsdStage::Open(stagePath);
            if (!s) { std::fprintf(stderr, "FAIL open stage %s\n", stagePath.c_str()); ++fail; continue; }
            stages[stagePath] = s;
            resolvers[stagePath] = new GeoResolver(s);
        }
        GeoResolver* R = resolvers[stagePath];
        UsdPrim prim = stages[stagePath]->GetPrimAtPath(SdfPath(primPath));
        if (!prim) { std::fprintf(stderr, "FAIL get prim %s\n", primPath.c_str()); ++fail; continue; }

        GfVec3d origin;
        bool ok_resolve;
        if (kind == "frame") {
            GfMatrix4d M;
            ok_resolve = R->AnchorFrame(prim, &M);
            origin = M.Transform(GfVec3d(0,0,0));
        } else {
            ok_resolve = R->ResolveWorldTranslation(prim, &origin);
        }
        if (!ok_resolve) {
            std::printf("FAIL %-40s %-12s (no resolution)\n", primPath.c_str(), kind.c_str());
            ++fail; ++n; continue;
        }
        double d_gt = (origin - gt).GetLength() * 1e3;
        double d_py = (origin - py).GetLength() * 1e3;
        worst_gt = std::max(worst_gt, d_gt);
        worst_py = std::max(worst_py, d_py);
        bool ok = d_gt < tol_mm && d_py < tol_mm;
        if (!ok) ++fail;
        std::printf("%-4s %-40s %-12s  vsGT=%.5f mm  vsPython=%.5f mm\n",
                    ok?"ok":"FAIL", primPath.c_str(), kind.c_str(), d_gt, d_py);
        ++n;
    }
    std::printf("----\n%d rows, %d fail; worst vsGT=%.5f mm, worst vsPython=%.5f mm (tol %.1f mm)\n",
                n, fail, worst_gt, worst_py, tol_mm);
    return fail ? 1 : 0;
}
