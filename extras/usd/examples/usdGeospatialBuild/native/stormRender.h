// Stock Storm consumes the new scene index directly; no USD export intermediary.
#include "pxr/imaging/garch/glApi.h"
#include "pxr/imaging/hd/engine.h"
#include "pxr/imaging/hd/renderBuffer.h"
#include "pxr/imaging/hdSt/renderDelegate.h"
#include "pxr/imaging/hdx/taskController.h"
#include "pxr/imaging/hdx/renderTask.h"
#include "pxr/imaging/hgi/hgi.h"
#include "pxr/imaging/hgi/tokens.h"
#include "pxr/imaging/hio/image.h"
#include "pxr/imaging/glf/simpleLight.h"
#include "pxr/base/gf/frustum.h"
#include "pxr/base/gf/range3d.h"
#include <memory>
#ifdef _WIN32
#include <windows.h>
#include <tlhelp32.h>
#endif

static JsArray LoadedModules() {
    JsArray result;
#ifdef _WIN32
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE,GetCurrentProcessId());
    MODULEENTRY32 entry{}; entry.dwSize=sizeof(entry);
    if(Module32First(snapshot,&entry)) do { result.emplace_back(std::string(entry.szModule)); } while(Module32Next(snapshot,&entry));
    CloseHandle(snapshot);
#endif
    return result;
}

static JsObject RenderStorm(const HdSceneIndexBaseRefPtr &scene,const char *filename) {
#ifdef _WIN32
    // Invisible window provides a WGL context; no interactive window is shown.
    WNDCLASSA wc{}; wc.style=CS_OWNDC; wc.lpfnWndProc=DefWindowProcA;
    wc.hInstance=GetModuleHandle(nullptr); wc.lpszClassName="GeobuildOffscreen";
    RegisterClassA(&wc);
    HWND window=CreateWindowA(wc.lpszClassName,"",WS_POPUP,0,0,16,16,nullptr,nullptr,wc.hInstance,nullptr);
    HDC dc=GetDC(window);
    PIXELFORMATDESCRIPTOR pfd{}; pfd.nSize=sizeof(pfd); pfd.nVersion=1;
    pfd.dwFlags=PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL|PFD_DOUBLEBUFFER;
    pfd.iPixelType=PFD_TYPE_RGBA; pfd.cColorBits=32; pfd.cDepthBits=24;
    SetPixelFormat(dc,ChoosePixelFormat(dc,&pfd),&pfd);
    HGLRC context=wglCreateContext(dc);
    if(!context || !wglMakeCurrent(dc,context)) throw std::runtime_error("Could not create offscreen OpenGL context");
    GarchGLApiLoad();
    JsObject result;
    {
        auto hgi=Hgi::CreatePlatformDefaultHgi();
        HdDriver driver{HgiTokens->renderDriver,VtValue(hgi.get())};
        HdStRenderDelegate delegate;
        std::unique_ptr<HdRenderIndex> index(HdRenderIndex::New(&delegate,{&driver}));
        index->InsertSceneIndex(scene,SdfPath::AbsoluteRootPath());
        HdxTaskController controller(index.get(),SdfPath("/RenderController"));
        controller.SetEnablePresentation(false);
        controller.SetEnableSelection(false);
        controller.SetEnableShadows(false);
        controller.SetRenderOutputs({HdAovTokens->color});
        auto descriptor=controller.GetRenderOutputSettings(HdAovTokens->color);
        descriptor.format=HdFormatFloat32Vec4;
        descriptor.clearValue=VtValue(GfVec4f(.035f,.05f,.075f,1.f));
        controller.SetRenderOutputSettings(HdAovTokens->color,descriptor);
        controller.SetRenderViewport(GfVec4d(0,0,1280,720));
        controller.SetRenderBufferSize(GfVec2i(1280,720));
        controller.SetCollection(HdRprimCollection(HdTokens->geometry,HdReprSelector(HdReprTokens->smoothHull)));
        HdxRenderTaskParams params;
        params.enableLighting=true;
        params.cullStyle=HdCullStyleNothing;
        controller.SetRenderParams(params);
        GfRange3d bounds;
        SdfPathVector paths{SdfPath::AbsoluteRootPath()};
        for(size_t i=0;i<paths.size();++i) {
            auto children=scene->GetChildPrimPaths(paths[i]); paths.insert(paths.end(),children.begin(),children.end());
            const auto prim=scene->GetPrim(paths[i]);
            auto pv=HdPrimvarsSchema::GetFromParent(prim.dataSource).GetPrimvar(TfToken("points")).GetPrimvarValue();
            auto xf=HdXformSchema::GetFromParent(prim.dataSource).GetMatrix();
            if(pv && xf) {
                const auto values=pv->GetValue(0).Get<VtVec3fArray>();
                for(const auto &p:values) bounds.UnionWith(xf->GetTypedValue(0).Transform(GfVec3d(p)));
            }
        }
        if(bounds.IsEmpty()) throw std::runtime_error("Cannot render empty geometry");
        double radius=bounds.GetSize().GetLength()*.58;
        radius=std::max(radius,1.0);
        GfFrustum camera;
        camera.SetOrthographic(-radius*1280/720,radius*1280/720,-radius,radius,.01,radius*20+std::max(bounds.GetSize()[2],1.0));
        GfMatrix4d view;
        view.SetLookAt(bounds.GetMidpoint()+GfVec3d(1,-1,1)*radius*4,bounds.GetMidpoint(),GfVec3d(0,0,1));
        camera.SetPositionAndRotationFromMatrix(view.GetInverse());
        controller.SetFreeCameraMatrices(camera.ComputeViewMatrix(),camera.ComputeProjectionMatrix());
        auto lighting=GlfSimpleLightingContext::New();
        GlfSimpleLight light;
        light.SetPosition(GfVec4f(1,-1,2,0));
        light.SetDiffuse(GfVec4f(1,1,1,1));
        light.SetAmbient(GfVec4f(.2f,.2f,.2f,1));
        lighting->SetLights(GlfSimpleLightVector{light});
        controller.SetLightingState(lighting);
        HdEngine engine;
        for(int i=0;i<12;++i) { auto tasks=controller.GetRenderingTasks(); engine.Execute(index.get(),&tasks); }
        auto buffer=controller.GetRenderOutput(HdAovTokens->color);
        if(!buffer) throw std::runtime_error("Storm returned no color buffer");
        buffer->Resolve();
        void *pixels=buffer->Map();
        if(!pixels) throw std::runtime_error("Storm color buffer is not readable");
        HioImage::StorageSpec storage;
        storage.width=buffer->GetWidth(); storage.height=buffer->GetHeight();
        storage.format=HioFormatFloat32Vec4; storage.flipped=true; storage.data=pixels;
        // Request RGBA32F explicitly below; never infer format from a raw pointer.
        if(buffer->GetFormat()!=HdFormatFloat32Vec4) throw std::runtime_error("Unexpected Storm buffer format");
        auto image=HioImage::OpenForWriting(filename);
        if(!image || !image->Write(storage)) throw std::runtime_error("Could not write Storm image");
        buffer->Unmap();
        result={{"renderer",JsValue("Storm")},{"scene_index_direct",JsValue(true)},
                {"width",JsValue(storage.width)},{"height",JsValue(storage.height)}};
    }
    wglMakeCurrent(nullptr,nullptr); wglDeleteContext(context); ReleaseDC(window,dc); DestroyWindow(window);
    return result;
#else
    throw std::runtime_error("This build needs an offscreen context implementation for its platform");
#endif
}
