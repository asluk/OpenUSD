//
// testCrsEngine.cpp -- standalone parity check of GeoCrsEngine vs the Python
// reference runtime / closed-form WGS84 geodesy.
//
// Reads a JSON-ish line file of test cases (produced by the python oracle):
//   each line: <srcWkt-as-authority-or-file-token>\t x \t y \t z \t gtX \t gtY \t gtZ
// where (gtX,gtY,gtZ) is closed-form-geodesy ECEF of the authored point.
// For each case we (a) reproject src->ECEF and compare to GT, and (b) build the
// ENU->ECEF frame and confirm M.Transform(0,0,0) == the same ECEF (the anchor
// origin), to sub-mm. Exits non-zero if any case exceeds tolerance.
//
#include "crsEngine.h"

#include <pxr/pxr.h>
#include <pxr/base/gf/vec3d.h>
#include <pxr/base/gf/matrix4d.h>

#include <cstdio>
#include <cmath>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

PXR_NAMESPACE_USING_DIRECTIVE

int main(int argc, char** argv)
{
    if (argc < 2) {
        std::fprintf(stderr, "usage: %s <cases.tsv> [tol_mm]\n", argv[0]);
        return 2;
    }
    const double tol_mm = (argc >= 3) ? std::atof(argv[2]) : 5.0;
    std::ifstream in(argv[1]);
    if (!in) { std::fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }

    GeoCrsEngine& eng = GeoCrsEngine::GetDefault();

    std::string line;
    int n = 0, fail = 0;
    double worst_reproj_mm = 0.0, worst_frame_mm = 0.0;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#') continue;
        // fields are tab-separated; the WKT itself may contain spaces but no tabs
        std::vector<std::string> f;
        std::stringstream ss(line);
        std::string tok;
        while (std::getline(ss, tok, '\t')) f.push_back(tok);
        if (f.size() < 8) continue;
        const std::string& name = f[0];
        const std::string& srcWkt = f[1];
        double x = std::stod(f[2]), y = std::stod(f[3]), z = std::stod(f[4]);
        GfVec3d gt(std::stod(f[5]), std::stod(f[6]), std::stod(f[7]));

        GfVec3d ecef = eng.Reproject(srcWkt, "EPSG:4978", x, y, z);
        double d_reproj_mm = (ecef - gt).GetLength() * 1e3;

        GfMatrix4d M = eng.LocalFrameToEcef(srcWkt, x, y, z);
        GfVec3d origin = M.Transform(GfVec3d(0,0,0));
        double d_frame_mm = (origin - gt).GetLength() * 1e3;

        worst_reproj_mm = std::max(worst_reproj_mm, d_reproj_mm);
        worst_frame_mm  = std::max(worst_frame_mm, d_frame_mm);
        bool ok = (d_reproj_mm < tol_mm) && (d_frame_mm < tol_mm);
        if (!ok) {
            ++fail;
            std::printf("FAIL %-44s reproj=%.4f mm  frameOrigin=%.4f mm\n",
                        name.c_str(), d_reproj_mm, d_frame_mm);
        } else {
            std::printf("ok   %-44s reproj=%.4f mm  frameOrigin=%.4f mm\n",
                        name.c_str(), d_reproj_mm, d_frame_mm);
        }
        ++n;
    }
    std::printf("----\n%d cases, %d fail; worst reproj=%.4f mm worst frameOrigin=%.4f mm (tol %.1f mm)\n",
                n, fail, worst_reproj_mm, worst_frame_mm, tol_mm);
    return fail ? 1 : 0;
}
