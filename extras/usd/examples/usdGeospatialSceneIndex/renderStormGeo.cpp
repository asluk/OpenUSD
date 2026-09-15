// renderStormGeo.cpp -- REAL Hydra Storm render of the usdGeospatial scene with
// the UsdGeospatialSceneIndex inserted in the Hydra chain (Deliverable 2:
// by-hand chain, SetStage called explicitly), rendered offscreen to a PNG.
//
// Chain:  UsdStage
//           -> UsdImagingStageSceneIndex (SetStage)
//           -> [optional] UsdGeospatialSceneIndex (SetStage)   <-- toggled by --si
//           -> HdRenderIndex (HdStorm) via InsertSceneIndex
//         + HdxTaskController render tasks, HdxFreeCameraSceneDelegate camera,
//           color AOV read back to a PNG via HioImage.
//
// Usage: renderStormGeo <stage.usda> <out.png> [--si|--nosi] [W H]
//
// Proof design: run twice on the SAME stage.
//   --si   : geospatial xform override active -> gprims at ECEF world position.
//   --nosi : no override -> gprims sit at their authored local origin.
// The camera is framed identically (on the SI-resolved world centroid) so the
// two images visibly differ: with SI the railway is in frame; without SI it is
// absent (geometry is ~6.3e6 m away at the raw local origin).

#include "geospatialSceneIndex.h"
#include "geoResolver.h"

#include <pxr/pxr.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usd/primRange.h>
#include <pxr/usdImaging/usdImaging/stageSceneIndex.h>

#include <pxr/imaging/hd/engine.h>
#include <pxr/imaging/hd/renderIndex.h>
#include <pxr/imaging/hd/rendererPluginRegistry.h>
#include <pxr/imaging/hd/pluginRenderDelegateUniqueHandle.h>
#include <pxr/imaging/hd/renderBuffer.h>
#include <pxr/imaging/hd/rprimCollection.h>
#include <pxr/imaging/hd/xformSchema.h>
#include <pxr/imaging/hd/sceneIndex.h>
#include <pxr/imaging/hd/tokens.h>

#include <pxr/imaging/hdx/taskController.h>
#include <pxr/imaging/hdx/freeCameraSceneDelegate.h>
#include <pxr/imaging/hdx/tokens.h>
#include <pxr/imaging/hdx/renderTask.h>
#include <pxr/imaging/hdx/renderSetupTask.h>

#include <pxr/imaging/hgi/hgi.h>
#include <pxr/imaging/hgi/tokens.h>
#include <pxr/imaging/hd/driver.h>

#include <pxr/imaging/glf/testGLContext.h>
#include <pxr/imaging/glf/glContext.h>
#include <pxr/imaging/glf/contextCaps.h>
#include <pxr/imaging/glf/simpleLightingContext.h>
#include <pxr/imaging/glf/simpleLight.h>

#include <pxr/imaging/hio/image.h>
#include <pxr/imaging/hio/types.h>

#include <pxr/base/gf/matrix4d.h>
#include <pxr/base/gf/vec3d.h>
#include <pxr/base/gf/vec4d.h>
#include <pxr/base/gf/camera.h>
#include <pxr/base/gf/frustum.h>
#include <pxr/base/gf/range3d.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

// --- offscreen GL context provided via Glf (registered so Storm/HgiGL share it) ---
#include <X11/Xlib.h>
#include <unistd.h>

PXR_NAMESPACE_USING_DIRECTIVE
// Pull the xform translation of a prim from the terminal scene index.
static bool GetSiOrigin(const HdSceneIndexBaseRefPtr& si, const SdfPath& p, GfVec3d* out) {
    HdSceneIndexPrim prim = si->GetPrim(p);
    HdXformSchema xs = HdXformSchema::GetFromParent(prim.dataSource);
    if (!xs.IsDefined() || !xs.GetMatrix()) return false;
    GfMatrix4d m = xs.GetMatrix()->GetTypedValue(0.0f);
    *out = m.Transform(GfVec3d(0,0,0));
    return true;
}

int main(int argc, char** argv)
{
    if (argc < 3) {
        std::fprintf(stderr, "usage: %s stage.usda out.png [--si|--nosi] [W H]\n", argv[0]);
        return 2;
    }
    setvbuf(stdout, nullptr, _IONBF, 0);
    std::string stagePath = argv[1];
    std::string outPng    = argv[2];
    bool useSI = true;
    int W = 1280, H = 960;
    for (int i=3; i<argc; ++i) {
        if (!strcmp(argv[i], "--si")) useSI = true;
        else if (!strcmp(argv[i], "--nosi")) useSI = false;
        else if (i+1 < argc) { W = atoi(argv[i]); H = atoi(argv[i+1]); ++i; }
    }

    std::printf("[render] stage=%s out=%s SI=%s %dx%d\n",
                stagePath.c_str(), outPng.c_str(), useSI?"ON":"OFF", W, H);

    // --- open stage ---
    UsdStageRefPtr stage = UsdStage::Open(stagePath);
    if (!stage) { std::fprintf(stderr,"cannot open stage\n"); return 1; }

    // --- create an offscreen GL context BEFORE Hgi, registered with Glf so
    // HgiGL/Storm share (not double-manage) it. This is the same setup the
    // hydra unit tests use for headless GL. ---
    GlfTestGLContext::RegisterGLContextCallbacks();
    GlfSharedGLContextScopeHolder sharedContext;
    GlfContextCaps::InitInstance();
    std::printf("[glx] Glf test GL context current (offscreen, llvmpipe)\n");

    // --- Hgi + Storm render delegate ---
    HgiUniquePtr hgi = Hgi::CreatePlatformDefaultHgi();
    HdDriver hgiDriver{HgiTokens->renderDriver, VtValue(hgi.get())};

    HdRendererPluginRegistry& reg = HdRendererPluginRegistry::GetInstance();
    TfToken pluginId("HdStormRendererPlugin");
    HdPluginRenderDelegateUniqueHandle renderDelegate =
        reg.CreateRenderDelegate(pluginId);
    if (!renderDelegate) { std::fprintf(stderr,"no Storm render delegate\n"); return 1; }

    HdRenderIndex* renderIndex =
        HdRenderIndex::New(renderDelegate.Get(), {&hgiDriver});
    if (!renderIndex) { std::fprintf(stderr,"no render index\n"); return 1; }

    // --- scene index chain ---
    UsdImagingStageSceneIndexRefPtr usdSi = UsdImagingStageSceneIndex::New();
    usdSi->SetStage(stage);
    usdSi->SetTime(UsdTimeCode::Default());
    usdSi->ApplyPendingUpdates();

    // ALWAYS build a geoSi for framing (need the resolved world centroid), but
    // only INSERT it into the render chain when useSI is true.
    UsdGeospatialSceneIndexRefPtr geoSi = UsdGeospatialSceneIndex::New(usdSi);
    geoSi->SetStage(stage);

    HdSceneIndexBaseRefPtr terminal = useSI
        ? HdSceneIndexBaseRefPtr(geoSi)
        : HdSceneIndexBaseRefPtr(usdSi);

    renderIndex->InsertSceneIndex(terminal, SdfPath::AbsoluteRootPath());

    // --- compute framing centroid/radius from the SI-resolved xforms ---
    // We frame on the geo-resolved (ECEF) positions so both runs use the SAME
    // camera; that is what makes the negative control meaningful.
    GfRange3d worldRange;
    int nAnchors = 0;
    for (UsdPrim p : stage->Traverse()) {
        // anchors carry crs:position; their SI xform is the ECEF frame
        if (!p.HasAttribute(TfToken("crs:position"))) continue;
        GfVec3d o;
        if (GetSiOrigin(geoSi, p.GetPath(), &o)) { worldRange.UnionWith(o); ++nAnchors; }
    }
    if (worldRange.IsEmpty()) {
        std::fprintf(stderr,"[render] WARN: no anchors found; framing on root\n");
        worldRange.UnionWith(GfVec3d(0,0,0));
    }
    GfVec3d center = worldRange.GetMidpoint();
    GfVec3d size   = worldRange.GetSize();
    double radius  = std::max(size.GetLength()*0.5, 1.0);
    std::printf("[render] anchors=%d worldCenter=(%.3f, %.3f, %.3f) radius=%.3f m\n",
                nAnchors, center[0], center[1], center[2], radius);

    // --- task controller (render tasks) ---
    std::printf("[render] creating task controller...\n");
    SdfPath controllerId("/taskController");
    HdxTaskController taskController(renderIndex, controllerId);

    // color AOV with a visible (non-black) clear color so "empty" is
    // distinguishable from "black geometry".
    taskController.SetRenderOutputs({HdAovTokens->color});
    taskController.SetRenderBufferSize(GfVec2i(W, H));
    taskController.SetRenderViewport(GfVec4d(0,0,W,H));
    {
        HdAovDescriptor colorDesc =
            taskController.GetRenderOutputSettings(HdAovTokens->color);
        colorDesc.clearValue = VtValue(GfVec4f(0.12f, 0.14f, 0.20f, 1.0f));
        taskController.SetRenderOutputSettings(HdAovTokens->color, colorDesc);
    }

    HdxRenderTaskParams rparams;
    rparams.enableLighting = true;
    rparams.enableSceneLights = true;
    taskController.SetRenderParams(rparams);
    taskController.SetEnableSelection(false);

    // --- camera framed on the world centroid, backed off along +Z-ish ---
    // Look from a point offset from center toward center. For ECEF the "up" is
    // roughly the center direction (away from earth center = normalize(center)).
    GfVec3d up = center.GetLength() > 1.0 ? center.GetNormalized() : GfVec3d(0,0,1);
    // eye: pull back along an oblique direction so curves are visible
    GfVec3d viewDir = GfVec3d(0.4, 0.4, 1.0).GetNormalized();
    double zoom = getenv("GEO_ZOOM") ? atof(getenv("GEO_ZOOM")) : 3.0;
    double dist = radius * zoom + 500.0;
    GfVec3d eye = center + viewDir * dist;

    GfFrustum frustum;
    frustum.SetPositionAndRotationFromMatrix(
        GfMatrix4d(1.0).SetLookAt(eye, center, up).GetInverse());
    frustum.SetPerspective(45.0, double(W)/double(H), dist*0.01, dist*10.0);
    GfMatrix4d view = frustum.ComputeViewMatrix();
    GfMatrix4d proj = frustum.ComputeProjectionMatrix();

    HdxFreeCameraSceneDelegate camDelegate(renderIndex, SdfPath("/freeCamera"));
    camDelegate.SetMatrices(view, proj);
    taskController.SetCameraPath(camDelegate.GetCameraId());

    // --- lighting: a simple headlight at the eye so unlit geometry is visible ---
    {
        GlfSimpleLight light;
        light.SetAmbient(GfVec4f(0.2f,0.2f,0.2f,1.0f));
        light.SetDiffuse(GfVec4f(1.0f,1.0f,1.0f,1.0f));
        light.SetPosition(GfVec4f((float)eye[0],(float)eye[1],(float)eye[2],1.0f));
        GlfSimpleLightingContextRefPtr lc = GlfSimpleLightingContext::New();
        GlfSimpleLightVector lights{light};
        lc->SetLights(lights);
        GlfSimpleMaterial mat;
        mat.SetAmbient(GfVec4f(0.2f,0.2f,0.2f,1.0f));
        mat.SetDiffuse(GfVec4f(0.8f,0.8f,0.8f,1.0f));
        lc->SetMaterial(mat);
        lc->SetSceneAmbient(GfVec4f(0.25f,0.25f,0.25f,1.0f));
        taskController.SetLightingState(lc);
    }

    // --- render ---
    std::printf("[render] executing tasks...\n");
    HdEngine engine;
    HdTaskSharedPtrVector tasks = taskController.GetRenderingTasks();

    // Multiple passes to allow Storm to converge/settle.
    for (int i=0; i<8; ++i) {
        std::printf("[render] pass %d\n", i);
        engine.Execute(renderIndex, &tasks);
        if (taskController.IsConverged()) { std::printf("[render] converged\n"); break; }
    }

    // --- read back color AOV ---
    HdRenderBuffer* colorBuffer = taskController.GetRenderOutput(HdAovTokens->color);
    if (!colorBuffer) { std::fprintf(stderr,"no color buffer\n"); return 1; }
    colorBuffer->Resolve();
    unsigned int bw = colorBuffer->GetWidth();
    unsigned int bh = colorBuffer->GetHeight();
    HdFormat fmt = colorBuffer->GetFormat();
    std::printf("[render] color buffer %ux%u fmt=%d\n", bw, bh, (int)fmt);

    void* data = colorBuffer->Map();
    if (!data) { std::fprintf(stderr,"cannot map color buffer\n"); return 1; }

    // Storm color AOV is typically HdFormatUNorm8Vec4 (RGBA8). Convert to RGBA8
    // for HioImage. Handle Float32Vec4 too.
    std::vector<uint8_t> rgba(bw*bh*4);
    size_t comps = HdGetComponentCount(fmt);
    HdFormat compFmt = HdGetComponentFormat(fmt);
    const uint8_t* src8 = static_cast<const uint8_t*>(data);
    const float*   srcf = static_cast<const float*>(data);
    const uint16_t* srch = static_cast<const uint16_t*>(data);
    auto half2float = [](uint16_t h)->float {
        uint32_t s=(h>>15)&1, e=(h>>10)&0x1F, m=h&0x3FF; uint32_t out;
        if (e==0) { if(m==0) out=s<<31; else { e=127-15+1; while(!(m&0x400)){m<<=1;--e;} m&=0x3FF; out=(s<<31)|(e<<23)|(m<<13);} }
        else if (e==31) out=(s<<31)|(0xFF<<23)|(m<<13);
        else out=(s<<31)|((e-15+127)<<23)|(m<<13);
        float f; memcpy(&f,&out,4); return f;
    };
    auto clamp01=[](float f){ return f<0?0.f:(f>1?1.f:f); };
    for (unsigned int i=0;i<bw*bh;++i) {
        for (int c=0;c<4;++c) {
            uint8_t v = 0;
            if (c < (int)comps) {
                if (compFmt == HdFormatUNorm8) {
                    v = src8[i*comps + c];
                } else if (compFmt == HdFormatFloat32) {
                    v = (uint8_t)(clamp01(srcf[i*comps + c])*255.0f + 0.5f);
                } else if (compFmt == HdFormatFloat16) {
                    v = (uint8_t)(clamp01(half2float(srch[i*comps + c]))*255.0f + 0.5f);
                }
            }
            if (c==3 && comps<4) v = 255; // opaque alpha
            rgba[i*4 + c] = v;
        }
    }
    colorBuffer->Unmap();

    // --- write PNG (flip vertically: GL origin bottom-left) ---
    std::vector<uint8_t> flipped(bw*bh*4);
    for (unsigned int y=0;y<bh;++y)
        memcpy(&flipped[(bh-1-y)*bw*4], &rgba[y*bw*4], bw*4);

    HioImageSharedPtr img = HioImage::OpenForWriting(outPng);
    if (!img) { std::fprintf(stderr,"cannot open %s for writing\n", outPng.c_str()); return 1; }
    HioImage::StorageSpec spec;
    spec.width  = bw;
    spec.height = bh;
    spec.format = HioFormatUNorm8Vec4;
    spec.flipped = false;
    spec.data = flipped.data();
    if (!img->Write(spec)) { std::fprintf(stderr,"write failed\n"); return 1; }

    std::printf("[render] wrote %s\n", outPng.c_str());
    std::fflush(stdout);

    // Avoid a teardown-order double-free between HdxTaskController /
    // HdRenderIndex / Hgi / GLX by exiting immediately after a successful write.
    _exit(0);

    // clean shutdown before Hgi dies
    return 0;
}
