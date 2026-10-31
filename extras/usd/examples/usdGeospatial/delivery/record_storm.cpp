//
// Copyright 2026 NVIDIA CORPORATION & AFFILIATES
//
// Licensed under the terms set forth in the LICENSE.txt file available at
// https://openusd.org/license.
//
#define NOMINMAX
#include <iostream>
#include <pxr/base/plug/registry.h>
#include <pxr/imaging/garch/glApi.h>
#include <pxr/pxr.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdGeom/camera.h>
#include <pxr/usdImaging/usdAppUtils/frameRecorder.h>
#include <windows.h>
PXR_NAMESPACE_USING_DIRECTIVE
int main(int argc, char** argv)
{
    if (argc != 4) {
        std::cerr << "stage.usda output.png plugin-directory\n";
        return 2;
    }
    WNDCLASSA wc{};
    wc.style = CS_OWNDC;
    wc.lpfnWndProc = DefWindowProcA;
    wc.hInstance = GetModuleHandle(nullptr);
    wc.lpszClassName = "UsdGeospatialHiddenRecorder";
    RegisterClassA(&wc);
    HWND window = CreateWindowA(wc.lpszClassName, "", WS_POPUP, 0, 0, 8, 8, nullptr,
                                nullptr, wc.hInstance, nullptr);
    HDC dc = GetDC(window);
    PIXELFORMATDESCRIPTOR pfd{};
    pfd.nSize = sizeof(pfd);
    pfd.nVersion = 1;
    pfd.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    pfd.iPixelType = PFD_TYPE_RGBA;
    pfd.cColorBits = 32;
    pfd.cDepthBits = 24;
    int format = ChoosePixelFormat(dc, &pfd);
    if (!format || !SetPixelFormat(dc, format, &pfd)) {
        return 3;
    }
    HGLRC gl = wglCreateContext(dc);
    if (!gl || !wglMakeCurrent(dc, gl)) {
        return 4;
    }
    GarchGLApiLoad();
    PlugRegistry::GetInstance().RegisterPlugins(argv[3]);
    bool ok = false;
    {
        auto stage = UsdStage::Open(argv[1]);
        if (!stage) {
            return 5;
        }
        UsdAppUtilsFrameRecorder recorder(TfToken("HdStormRendererPlugin"), true);
        recorder.SetImageWidth(1500);
        recorder.SetColorCorrectionMode(TfToken("sRGB"));
        recorder.SetCameraLightEnabled(true);
        recorder.SetDomeLightVisibility(false);
        ok = recorder.Record(
            stage, UsdGeomCamera(stage->GetPrimAtPath(SdfPath("/View/Camera"))),
            UsdTimeCode::Default(), argv[2]);
        std::cout << "renderer=" << recorder.GetCurrentRendererId() << " success=" << ok
                  << "\n";
    }
    wglMakeCurrent(nullptr, nullptr);
    wglDeleteContext(gl);
    ReleaseDC(window, dc);
    DestroyWindow(window);
    return ok ? 0 : 6;
}
