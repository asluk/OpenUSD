#include "placement.h"
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
PXR_NAMESPACE_USING_DIRECTIVE
JsValue J(const GfVec3d& p){return JsValue(JsArray{JsValue(p[0]),JsValue(p[1]),JsValue(p[2])});}
GfVec3d V(const JsValue& v){auto a=v.GetJsArray();return {a[0].GetReal(),a[1].GetReal(),a[2].GetReal()};}
GfMatrix4d Matrix(const JsValue& v){GfMatrix4d m;auto a=v.GetJsArray();for(int i=0;i<4;i++)for(int j=0;j<4;j++)m[i][j]=a[i].GetJsArray()[j].GetReal();return m;}
JsValue J(const GfMatrix4d& m){JsArray a;for(int i=0;i<4;i++){JsArray row;for(int j=0;j<4;j++)row.push_back(JsValue(m[i][j]));a.push_back(JsValue(row));}return JsValue(a);}
int main(int argc,char **argv){
try{
 if(argc!=3)throw std::runtime_error("Usage: candidateNative job.json output.json");
 std::ifstream input(argv[1]);auto job=JsParseStream(input).GetJsObject();if(job.count("plugin_directory"))PlugRegistry::GetInstance().RegisterPlugins(job.at("plugin_directory").GetString());if(job.count("schema_directory"))PlugRegistry::GetInstance().RegisterPlugins(job.at("schema_directory").GetString());auto s=UsdStage::Open(job.at("stage").GetString());if(!s)throw std::runtime_error("Cannot open source USD stage");
 double t=job.count("time")?job.at("time").GetReal():std::numeric_limits<double>::quiet_NaN();auto tc=std::isnan(t)?UsdTimeCode::Default():UsdTimeCode(t);
 const std::string requestedOutput=job.count("output_wkt")?job.at("output_wkt").GetString():std::string();
 Configure(s,requestedOutput,t,GfVec3d(0),job.at("resources").GetString());
 JsObject result,measures,geometry,frames,pointInstances,operations,bounds;std::vector<GfVec3d> all;
 std::string snapshot;s->GetRootLayer()->ExportToString(&snapshot);
 for(auto p:UsdPrimRange::Stage(s,UsdTraverseInstanceProxies())){
  auto coordinates=p.GetRelationship(TfToken("crs:coordinateProperties"));SdfPathVector props;
  if(coordinates&&coordinates.GetTargets(&props))for(auto path:props){VtVec3dArray a;if(!s->GetAttributeAtPath(path).Get(&a,tc))throw std::runtime_error("Invalid coordinate property");JsArray b;for(auto q:a)b.push_back(J(CandidateCoordinate(p,q)));measures[path.GetString()]=JsValue(b);operations[path.GetString()]=JsValue(JsObject{{"description",JsValue(CandidateOperation())},{"accuracy",JsValue(CandidateAccuracy())}});}
  if(p.GetAttribute(TfToken("crs:position")).HasAuthoredValueOpinion()){auto m=CandidateFrame(p);JsArray a;for(int i=0;i<4;i++){JsArray row;for(int j=0;j<4;j++)row.push_back(JsValue(m[i][j]));a.push_back(JsValue(row));}frames[p.GetPath().GetString()]=JsValue(a);operations[p.GetPath().GetString()]=JsValue(JsObject{{"description",JsValue(CandidateOperation())},{"accuracy",JsValue(CandidateAccuracy())}});}
  if(p.IsA<UsdGeomPointInstancer>()){
   auto root=p;GfMatrix4d local(1);while(root&&!root.IsPseudoRoot()&&!root.GetAttribute(TfToken("crs:position")).HasAuthoredValueOpinion()){UsdGeomXformable x(root);if(x){GfMatrix4d m;bool reset;x.GetLocalTransformation(&m,&reset,tc);local=local*m;}root=root.GetParent();}
   VtMatrix4dArray transforms;if(!UsdGeomPointInstancer(p).ComputeInstanceTransformsAtTime(&transforms,tc,tc))throw std::runtime_error("Point instance transform evaluation failed");JsArray a;auto frame=CandidateFrame(root);for(auto m:transforms)a.push_back(J((m*local*frame).Transform(GfVec3d(0))));pointInstances[p.GetPath().GetString()]=JsValue(a);
  }
  VtVec3fArray points;if(p.GetAttribute(TfToken("points")).Get(&points,tc)){
   auto root=p;while(root&&!root.IsPseudoRoot()&&!root.GetAttribute(TfToken("crs:position")).HasAuthoredValueOpinion())root=root.GetParent();if(!root||root.IsPseudoRoot())continue;
   GfMatrix4d local(1);auto q=p;while(q&&q!=root){UsdGeomXformable x(q);if(x){GfMatrix4d m;bool reset;x.GetLocalTransformation(&m,&reset,tc);local=local*m;if(reset)break;}q=q.GetParent();}
   auto m=CandidateFrame(root);JsArray b;for(auto point:points){auto v=m.Transform(local.Transform(GfVec3d(point)));all.push_back(v);b.push_back(J(v));}geometry[p.GetPath().GetString()]=JsValue(b);
   VtVec3fArray extent;if(UsdGeomBoundable(p)&&UsdGeomBoundable::ComputeExtentFromPlugins(UsdGeomBoundable(p),tc,&extent)&&extent.size()==2){auto range=GfBBox3d(GfRange3d(GfVec3d(extent[0]),GfVec3d(extent[1])),local*m).ComputeAlignedRange();bounds[p.GetPath().GetString()]=JsValue(JsArray{J(range.GetMin()),J(range.GetMax())});}
  }
 }
 result["measurements"]=JsValue(measures);result["geometry"]=JsValue(geometry);result["frames"]=JsValue(frames);result["operation"]=JsValue(CandidateOperation());
 result["point_instances"]=JsValue(pointInstances);
 result["bounds"]=JsValue(bounds);
 JsObject relativeFrames;for(auto one=frames.begin();one!=frames.end();++one){auto other=one;for(++other;other!=frames.end();++other)relativeFrames[one->first+" relative to "+other->first]=J(Matrix(one->second)*Matrix(other->second).GetInverse());}result["relative_frames"]=JsValue(relativeFrames);
 result["operations"]=JsValue(operations);result["proj_version"]=JsValue(CandidateProjVersion());
 if(job.count("render")&&!all.empty()){
  PlugRegistry::GetInstance().RegisterPlugins(job.at("plugin_directory").GetString());
  auto registered=PlugRegistry::GetInstance().GetPluginWithName("candidatePlacement");if(!registered)throw std::runtime_error("Candidate placement metadata was not registered");
  std::cerr<<"Candidate metadata: "<<registered->GetPath()<<"\n";
  GfVec3d origin=job.count("render_origin")?V(job.at("render_origin")):all[0];Configure(s,requestedOutput,t,origin,job.at("resources").GetString());
  auto imaging=UsdImagingSceneIndex::New(HdRetainedContainerDataSource::New(),[](const HdSceneIndexBaseRefPtr& input){return CandidateSceneIndex(input);});imaging->SetStage(s);imaging->SetTime(tc);imaging->ApplyPendingUpdates();
  JsObject hydraPrims;
  int nativeInstanceReadback=0,pointInstanceReadback=0;
  for(auto path:HdSceneIndexPrimView(imaging)){auto prim=imaging->GetPrim(path);if(prim.primType!=TfToken("mesh")&&prim.primType!=TfToken("instancer"))continue;auto a=HdXformSchema::GetFromParent(prim.dataSource).GetMatrix();auto m=a?a->GetTypedValue(0):GfMatrix4d(1);JsObject entry{{"type",JsValue(prim.primType.GetString())},{"origin",J(m.ExtractTranslation())}};
   if(prim.primType==TfToken("instancer")){
    auto pv=HdPrimvarsSchema::GetFromParent(prim.dataSource);auto inst=pv.GetPrimvar(HdInstancerTokens->instanceTransforms).GetPrimvarValue();auto locations=HdInstancerTopologySchema::GetFromParent(prim.dataSource).GetInstanceLocations();
    if(inst&&locations){auto value=inst->GetValue(0);auto paths=locations->GetTypedValue(0);if(value.IsHolding<VtMatrix4dArray>()){auto matrices=value.Get<VtMatrix4dArray>();if(matrices.size()!=paths.size())throw std::runtime_error("Hydra native instance association mismatch");JsArray origins;for(size_t i=0;i<matrices.size();i++){auto p=s->GetPrimAtPath(paths[i]);auto root=p;GfMatrix4d local(1);while(root&&!root.IsPseudoRoot()&&!root.GetAttribute(TfToken("crs:position")).HasAuthoredValueOpinion()){UsdGeomXformable x(root);if(x){GfMatrix4d q;bool reset;x.GetLocalTransformation(&q,&reset,tc);local=local*q;}root=root.GetParent();}auto expected=CandidateRenderCoordinate((local*CandidateFrame(root)).Transform(GfVec3d(0)));auto actual=(matrices[i]*m).Transform(GfVec3d(0));if((expected-actual).GetLength()>1e-6)throw std::runtime_error("Hydra native-instance placement readback mismatch");origins.push_back(J(actual));nativeInstanceReadback++;}entry["instance_origins"]=JsValue(origins);}}
    auto translations=pv.GetPrimvar(HdInstancerTokens->instanceTranslations).GetPrimvarValue();auto source=s->GetPrimAtPath(path);
    if(translations&&source&&source.IsA<UsdGeomPointInstancer>()){auto value=translations->GetValue(0);if(value.IsHolding<VtVec3fArray>()){auto rows=value.Get<VtVec3fArray>();auto expected=pointInstances[path.GetString()].GetJsArray();if(rows.size()!=expected.size())throw std::runtime_error("Hydra point-instance association mismatch");for(size_t i=0;i<rows.size();i++){auto actual=m.Transform(GfVec3d(rows[i]));if((actual-CandidateRenderCoordinate(V(expected[i]))).GetLength()>1e-6)throw std::runtime_error("Hydra point-instance placement readback mismatch");pointInstanceReadback++;}}}
   }hydraPrims[path.GetString()]=JsValue(entry);
  }
  result["hydra_prims"]=JsValue(hydraPrims);
  result["hydra_instance_readback"]=JsValue(JsObject{{"native_instances",JsValue(nativeInstanceReadback)},{"point_instances",JsValue(pointInstanceReadback)}});
  JsObject geometryReadback;
  for(auto p:UsdPrimRange::Stage(s,UsdTraverseInstanceProxies())){VtVec3fArray points;if(!p.GetAttribute(TfToken("points")).Get(&points,tc))continue;auto prim=imaging->GetPrim(p.GetPath());auto matrix=HdXformSchema::GetFromParent(prim.dataSource).GetMatrix();if((prim.primType!=HdPrimTypeTokens->mesh&&prim.primType!=HdPrimTypeTokens->basisCurves)||!matrix||!geometry.count(p.GetPath().GetString()))continue;auto m=matrix->GetTypedValue(0);auto expected=geometry[p.GetPath().GetString()].GetJsArray();double error=0;for(size_t i=0;i<points.size();i++)error=std::max(error,(m.Transform(GfVec3d(points[i]))-CandidateRenderCoordinate(V(expected[i]))).GetLength());if(error>1e-6)throw std::runtime_error("Hydra consumed geometry placement differs from native query");geometryReadback[p.GetPath().GetString()]=JsValue(JsObject{{"vertices",JsValue(int(points.size()))},{"max_render_unit_error",JsValue(error)}});}
  result["hydra_geometry_readback"]=JsValue(geometryReadback);
  JsObject boundsReadback;
  for(auto p:UsdPrimRange::Stage(s,UsdTraverseInstanceProxies())){auto key=p.GetPath().GetString();if(!bounds.count(key))continue;auto prim=imaging->GetPrim(p.GetPath());auto matrix=HdXformSchema::GetFromParent(prim.dataSource).GetMatrix();auto extent=HdExtentSchema::GetFromParent(prim.dataSource);if(!matrix||!extent.GetMin()||!extent.GetMax())continue;
   auto actual=GfBBox3d(GfRange3d(extent.GetMin()->GetTypedValue(0),extent.GetMax()->GetTypedValue(0)),matrix->GetTypedValue(0)).ComputeAlignedRange();auto bb=bounds[key].GetJsArray();auto first=CandidateRenderCoordinate(V(bb[0])),second=CandidateRenderCoordinate(V(bb[1]));GfRange3d expected;expected.UnionWith(first);expected.UnionWith(second);double error=std::max((actual.GetMin()-expected.GetMin()).GetLength(),(actual.GetMax()-expected.GetMax()).GetLength());if(error>1e-6)throw std::runtime_error("Hydra consumed extent differs from affine query bound");boundsReadback[key]=JsValue(JsObject{{"max_render_unit_error",JsValue(error)}});
  }result["hydra_bounds_readback"]=JsValue(boundsReadback);
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
  result["filter_reads"]=JsValue(int(CandidateFilterReads()));if(!CandidateFilterReads())throw std::runtime_error("Storm did not consume the candidate scene index");
  result["render_origin"]=J(origin);result["renderer"]=JsValue("HdStormRendererPlugin");
  // Exercise the actual scene-index observer chain, not just a second standalone query.
  for(auto p:s->Traverse())if(p.GetAttribute(TfToken("crs:position")).HasAuthoredValueOpinion()){
   auto a=p.GetAttribute(TfToken("crs:position"));GfVec3d old;a.Get(&old,tc);auto beforeFrame=CandidateFrame(p);auto beforeReads=CandidateFilterReads();
   a.Set(old+GfVec3d(10,0,0),tc);for(int i=0;i<3;i++)draw();auto afterFrame=CandidateFrame(p);
   if(beforeFrame==afterFrame||CandidateFilterReads()<=beforeReads)throw std::runtime_error("Hydra edit did not invalidate placed scene data");
   result["live_edit"]=JsValue(JsObject{{"path",JsValue(p.GetPath().GetString())},{"filter_requeried",JsValue(true)},{"before_origin",J(beforeFrame.ExtractTranslation())},{"after_origin",J(afterFrame.ExtractTranslation())}});
   s->GetRootLayer()->ImportFromString(snapshot);for(int i=0;i<3;i++)draw();break;
  }
 }
 JsArray plugins;for(auto p:PlugRegistry::GetInstance().GetAllPlugins())if(p->IsLoaded())plugins.push_back(JsValue(p->GetName()));result["loaded_plugins"]=JsValue(plugins);
 std::string after;s->GetRootLayer()->ExportToString(&after);result["source_unchanged"]=JsValue(snapshot==after);
 std::ofstream output(argv[2]);JsWriteToStream(JsValue(result),output);std::cout<<"Native query and rendering complete\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
