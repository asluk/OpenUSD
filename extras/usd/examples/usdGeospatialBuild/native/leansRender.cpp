#include "pxr/base/js/json.h"
#include "pxr/base/plug/registry.h"
#include "pxr/base/plug/plugin.h"
#include "pxr/base/gf/camera.h"
#include "pxr/base/gf/vec2d.h"
#include "pxr/base/gf/bbox3d.h"
#include "pxr/imaging/glf/testGLContext.h"
#include "pxr/imaging/glf/glContext.h"
#include "pxr/imaging/hgi/hgi.h"
#include "pxr/imaging/hgi/tokens.h"
#include "pxr/imaging/hgi/texture.h"
#include "pxr/imaging/hgi/blitCmds.h"
#include "pxr/imaging/hgi/blitCmdsOps.h"
#include "pxr/imaging/hio/image.h"
#include "pxr/imaging/hdx/types.h"
#include "pxr/usdImaging/usdImagingGL/engine.h"
#include "pxr/usd/usdGeom/xformable.h"
#include "pxr/usd/usdGeom/metrics.h"
#include "pxr/usd/usdGeom/pointInstancer.h"
#include "pxr/usd/usdGeom/boundable.h"
#include "pxr/usd/usd/primRange.h"
#include "pxr/usdImaging/usdImaging/sceneIndex.h"
#include "pxr/imaging/hd/sceneIndexPrimView.h"
#include "pxr/imaging/hd/retainedDataSource.h"
#include "pxr/imaging/hd/xformSchema.h"
#include "pxr/imaging/hd/extentSchema.h"
#include "pxr/imaging/hd/primvarsSchema.h"
#include "pxr/imaging/hd/primvarSchema.h"
#include "pxr/imaging/hd/instancerTopologySchema.h"
#include "pxr/imaging/hd/tokens.h"
#include "pxr/imaging/hd/renderIndex.h"
#include "pxr/imaging/hd/renderBuffer.h"
#include "pxr/imaging/hd/engine.h"
#include "pxr/imaging/hd/rendererPluginRegistry.h"
#include "pxr/imaging/hd/pluginRenderDelegateUniqueHandle.h"
#include "pxr/imaging/hdx/taskController.h"
#include "pxr/imaging/hdx/selectionTracker.h"
#include "pxr/imaging/hdx/tokens.h"
#include "pxr/imaging/glf/simpleLightingContext.h"
#include <fstream>
#include <iostream>
#include <limits>
#include <windows.h>
#include "pxr/imaging/garch/glApi.h"
#include "pxr/usd/usd/stage.h"
#include "pxr/usd/usdGeom/xformCache.h"
PXR_NAMESPACE_USING_DIRECTIVE
int main(int argc,char** argv){try{
 if(argc!=3)throw std::runtime_error("Usage: leansRender job.json result.json");
 std::ifstream input(argv[1]);auto job=JsParseStream(input).GetJsObject();auto s=UsdStage::Open(job.at("stage").GetString());if(!s)throw std::runtime_error("No resolved stage");auto tc=UsdTimeCode(job.at("time").GetReal());
 auto V=[](const JsValue& x){auto a=x.GetJsArray();return GfVec3d(a[0].GetReal(),a[1].GetReal(),a[2].GetReal());};
 auto imaging=UsdImagingSceneIndex::New(HdRetainedContainerDataSource::New(),[](const HdSceneIndexBaseRefPtr& input){return input;});imaging->SetStage(s);imaging->SetTime(tc);imaging->ApplyPendingUpdates();
 UsdGeomXformCache cache(tc);JsObject consumed;size_t total=0;
 for(auto p:s->Traverse()){VtVec3fArray points;if(!p.GetAttribute(TfToken("points")).Get(&points,tc))continue;auto prim=imaging->GetPrim(p.GetPath());auto pv=HdPrimvarsSchema::GetFromParent(prim.dataSource).GetPrimvar(HdTokens->points).GetPrimvarValue();auto matrix=HdXformSchema::GetFromParent(prim.dataSource).GetMatrix();if(!pv||!matrix)throw std::runtime_error("Hydra did not expose resolved geometry");auto value=pv->GetValue(0);if(!value.IsHolding<VtVec3fArray>())throw std::runtime_error("Hydra points type mismatch");auto actual=value.Get<VtVec3fArray>();if(actual.size()!=points.size())throw std::runtime_error("Hydra geometry count mismatch");double error=0;auto m=matrix->GetTypedValue(0);auto expected=cache.GetLocalToWorldTransform(p);for(size_t i=0;i<points.size();i++)error=std::max(error,(m.Transform(GfVec3d(actual[i]))-expected.Transform(GfVec3d(points[i]))).GetLength());if(error>1e-8)throw std::runtime_error("Hydra data-source readback mismatch");consumed[p.GetPath().GetString()]=JsValue(JsObject{{"vertices",JsValue(int(points.size()))},{"max_stage_unit_error",JsValue(error)}});total+=points.size();}
 if(!total)throw std::runtime_error("No geometry reached Hydra");JsObject result;
  WNDCLASSA wc{};wc.style=CS_OWNDC;wc.lpfnWndProc=DefWindowProcA;wc.hInstance=GetModuleHandle(nullptr);wc.lpszClassName="CandidateHiddenGL";RegisterClassA(&wc);
  HWND window=CreateWindowA(wc.lpszClassName,"",WS_POPUP,0,0,1280,720,nullptr,nullptr,wc.hInstance,nullptr);HDC dc=GetDC(window);
  PIXELFORMATDESCRIPTOR pfd{};pfd.nSize=sizeof(pfd);pfd.nVersion=1;pfd.dwFlags=PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL|PFD_DOUBLEBUFFER;pfd.iPixelType=PFD_TYPE_RGBA;pfd.cColorBits=32;pfd.cDepthBits=24;SetPixelFormat(dc,ChoosePixelFormat(dc,&pfd),&pfd);HGLRC context=wglCreateContext(dc);wglMakeCurrent(dc,context);GarchGLApiLoad();
  auto hgi=Hgi::CreatePlatformDefaultHgi();HdDriver driver{HgiTokens->renderDriver,VtValue(hgi.get())};
  auto delegate=HdRendererPluginRegistry::GetInstance().CreateRenderDelegate(TfToken("HdStormRendererPlugin"));
  std::unique_ptr<HdRenderIndex> renderIndex(HdRenderIndex::New(delegate.Get(),{&driver}));renderIndex->InsertSceneIndex(imaging,SdfPath::AbsoluteRootPath());
  HdxTaskController controller(renderIndex.get(),SdfPath("/RenderTasks"));HdEngine engine;engine.SetTaskContextData(HdxTokens->selectionState,VtValue(std::make_shared<HdxSelectionTracker>()));
  controller.SetEnableSelection(false);controller.SetCollection(HdRprimCollection(TfToken("geometry"),HdReprSelector(TfToken("smoothHull"))));controller.SetRenderViewport(GfVec4d(0,0,1280,720));controller.SetRenderOutputs({TfToken("color")});
  auto aov=controller.GetRenderOutputSettings(TfToken("color"));aov.clearValue=VtValue(GfVec4f(.91f,.94f,.96f,1));controller.SetRenderOutputSettings(TfToken("color"),aov);
  GfCamera camera;camera.SetPerspectiveFromAspectRatioAndFieldOfView(1280./720,45,GfCamera::FOVHorizontal);
  auto eye=job.count("camera_eye")?V(job.at("camera_eye")):GfVec3d(600,-800,450);auto aim=job.count("camera_aim")?V(job.at("camera_aim")):GfVec3d(0,0,130);
  GfMatrix4d view;view.SetLookAt(eye,aim,GfVec3d(0,0,1));camera.SetTransform(view.GetInverse());camera.SetClippingRange(GfRange1f(.1f,50000.f));controller.SetFreeCameraMatrices(view,camera.GetFrustum().ComputeProjectionMatrix());
  GlfSimpleLight light;light.SetPosition(GfVec4f(.4f,-.8f,1.f,0));light.SetAmbient(GfVec4f(.25f,.25f,.25f,1));light.SetDiffuse(GfVec4f(.8f,.8f,.8f,1));auto lighting=GlfSimpleLightingContext::New();lighting->SetLights({light});lighting->SetMaterial(GlfSimpleMaterial());lighting->SetSceneAmbient(GfVec4f(.2f,.2f,.2f,1));controller.SetLightingState(lighting);
  HdxRenderTaskParams params;params.enableLighting=true;params.enableSceneLights=false;params.cullStyle=HdCullStyleNothing;controller.SetRenderParams(params);
  auto draw=[&](){imaging->ApplyPendingUpdates();auto tasks=controller.GetRenderingTasks();engine.Execute(renderIndex.get(),&tasks);};
  for(int i=0;i<12;i++)draw();
  auto buffer=controller.GetRenderOutput(TfToken("color"));if(!buffer)throw std::runtime_error("No Storm color AOV");auto resource=buffer->GetResource(false);auto tex=resource.Get<HgiTextureHandle>();if(!tex)throw std::runtime_error("No Storm texture");auto desc=tex->GetDescriptor();size_t bytes=desc.dimensions[0]*desc.dimensions[1]*HgiGetDataSizeOfFormat(desc.format);std::vector<unsigned char> pixels(bytes);
  auto blit=hgi->CreateBlitCmds();HgiTextureGpuToCpuOp copy;copy.gpuSourceTexture=tex;copy.cpuDestinationBuffer=pixels.data();copy.destinationBufferByteSize=bytes;blit->CopyTextureGpuToCpu(copy);hgi->SubmitCmds(blit.get(),HgiSubmitWaitTypeWaitUntilCompleted);
  HioImage::StorageSpec spec;spec.width=desc.dimensions[0];spec.height=desc.dimensions[1];spec.depth=1;spec.flipped=true;spec.data=pixels.data();spec.format=HdxGetHioFormat(desc.format);
  auto image=HioImage::OpenForWriting(job.at("render").GetString());if(!image||!image->Write(spec))throw std::runtime_error("Cannot save Storm AOV");

 result["renderer"]=JsValue("HdStormRendererPlugin");result["geometry_readback"]=JsValue(consumed);result["vertices"]=JsValue(int(total));result["integration"]=JsValue("Hydra consumes ordinary USD resolved export; no live CRS scene-index filter");std::ofstream output(argv[2]);JsWriteToStream(JsValue(result),output);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
