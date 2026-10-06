// Independent USD/C++ pointwise reader of the October 5 pinned local candidate.
#include "pxr/pxr.h"
#include "pxr/usd/usd/stage.h"
#include "pxr/usd/usd/primRange.h"
#include "pxr/usd/usdGeom/xformable.h"
#include "pxr/usd/usdGeom/metrics.h"
#include "pxr/usd/usdGeom/pointInstancer.h"
#include "pxr/base/js/json.h"
#include "pxr/base/gf/matrix3d.h"
#include "pxr/base/gf/quatd.h"
#include "pxr/base/vt/array.h"
#include "pxr/base/vt/dictionary.h"
#include "pxr/base/plug/registry.h"
#include "pxr/usd/sdf/listOp.h"
#include "pxr/usd/usd/resolveInfo.h"
#include <proj.h>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <cmath>
#include <sstream>
#include <stdexcept>
#include <algorithm>
#include <limits>
PXR_NAMESPACE_USING_DIRECTIVE
namespace {
PJ_CONTEXT* ctx=nullptr;UsdStageRefPtr stage;UsdTimeCode timeCode;std::string output;double unit;bool yUp;
JsArray operations;
bool Bound(const UsdPrim& p){SdfTokenListOp schemas;if(!p.GetMetadata(TfToken("apiSchemas"),&schemas))return false;auto names=schemas.GetAppliedItems();return std::find(names.begin(),names.end(),TfToken("GeospatialCRSBindingAPI"))!=names.end();}
UsdPrim Owner(UsdPrim p){while(p&&!p.IsPseudoRoot()){if(Bound(p))return p;p=p.GetParent();}throw std::runtime_error("No CRS binding");}
std::string Wkt(UsdPrim p){p=Owner(p);TfToken w;auto a=p.GetAttribute(TfToken("crs:wkt"));if(!a||a.GetTypeName()!=SdfValueTypeNames->Token||a.GetVariability()!=SdfVariabilityUniform||!a.Get(&w)||w.IsEmpty())throw std::runtime_error("Invalid nearest CRS binding");return w.GetString();}
struct Definition {
 PJ* object;bool geographic=false,requiresVertical=false;GfVec3d units{1};int dimensions=0;double a=0,b=0;
 Definition(const std::string& wkt){
  if(wkt.find("COORDINATEMETADATA")!=std::string::npos)throw std::runtime_error("Coordinate epochs deferred");
  object=proj_create(ctx,wkt.c_str());if(!object)throw std::runtime_error("Invalid WKT");auto type=proj_get_type(object);
  if(type==PJ_TYPE_BOUND_CRS)throw std::runtime_error("BOUNDCRS unsupported; no embedded operation dropped");
  geographic=type==PJ_TYPE_GEOGRAPHIC_2D_CRS||type==PJ_TYPE_GEOGRAPHIC_3D_CRS;
  auto horizontal=object;PJ* vertical=nullptr;
  if(type==PJ_TYPE_COMPOUND_CRS){horizontal=proj_crs_get_sub_crs(ctx,object,0);vertical=proj_crs_get_sub_crs(ctx,object,1);}
  auto horizontalType=proj_get_type(horizontal);if(horizontalType==PJ_TYPE_GEOGRAPHIC_2D_CRS||horizontalType==PJ_TYPE_GEOGRAPHIC_3D_CRS){geographic=true;requiresVertical=vertical!=nullptr;}
  auto cs=proj_crs_get_coordinate_system(ctx,horizontal);int count=cs?proj_cs_get_axis_count(ctx,cs):0;dimensions=count+(vertical?1:0);
  for(int i=0;i<count;i++){const char* direction=nullptr;double factor=1;proj_cs_get_axis_info(ctx,cs,i,nullptr,nullptr,&direction,&factor,nullptr,nullptr,nullptr);std::string d=direction?direction:"";int j=d=="east"||d=="geocentricX"?0:d=="north"||d=="geocentricY"?1:d=="up"||d=="geocentricZ"?2:-1;if(j<0)throw std::runtime_error("Unsupported component direction");units[j]=factor;}
  if(cs)proj_destroy(cs);if(vertical){cs=proj_crs_get_coordinate_system(ctx,vertical);const char* direction=nullptr;proj_cs_get_axis_info(ctx,cs,0,nullptr,nullptr,&direction,&units[2],nullptr,nullptr,nullptr);if(!direction||std::string(direction)!="up")throw std::runtime_error("Unsupported vertical direction");proj_destroy(cs);proj_destroy(vertical);proj_destroy(horizontal);}
  auto ell=proj_get_ellipsoid(ctx,object);if(ell){int computed;double inv;proj_ellipsoid_get_parameters(ctx,ell,&a,&b,&computed,&inv);proj_destroy(ell);}
 }
 ~Definition(){proj_destroy(object);}
};
std::map<std::string,std::unique_ptr<Definition>> defs;
Definition& Def(const std::string& w){auto& v=defs[w];if(!v)v=std::make_unique<Definition>(w);return *v;}
struct Operation {
 PJ* object;std::string src,dst;
 Operation(std::string s,std::string d):src(s),dst(d){const char* options[]={"ALLOW_BALLPARK=NO","ONLY_BEST=YES",nullptr};auto raw=proj_create_crs_to_crs_from_pj(ctx,Def(s).object,Def(d).object,nullptr,options);if(!raw)throw std::runtime_error("No coordinate operation");object=proj_normalize_for_visualization(ctx,raw);proj_destroy(raw);if(!object)throw std::runtime_error("Axis adaptation failed");}
 ~Operation(){proj_destroy(object);}
 GfVec3d Run(GfVec3d p){
  auto& s=Def(src);auto& d=Def(dst);if(s.dimensions!=d.dimensions)throw std::runtime_error("No implicit height or dimensional promotion");
  if(s.geographic){if(std::abs(p[1]*s.units[1])>1.5707963267948966+1e-14)throw std::runtime_error("Latitude outside domain");p[0]*=s.units[0]*180/3.141592653589793;p[1]*=s.units[1]*180/3.141592653589793;}
  proj_errno_reset(object);auto v=proj_trans(object,PJ_FWD,proj_coord(p[0],p[1],p[2],HUGE_VAL));if(proj_errno(object)||!std::isfinite(v.xyz.x)||!std::isfinite(v.xyz.y)||!std::isfinite(v.xyz.z))throw std::runtime_error("Coordinate operation failed; no substitute");
  auto used=proj_trans_get_last_used_operation(object);auto actual=used?used:object;auto info=proj_pj_info(actual);std::string pipeline=info.definition?info.definition:"";if(pipeline.find("t_epoch=")!=std::string::npos||pipeline.find("proj=deformation")!=std::string::npos)throw std::runtime_error("Epoch-dependent operation deferred");
  if(operations.empty()||operations.back().GetJsObject().at("definition").GetString()!=pipeline){double accuracy=proj_coordoperation_get_accuracy(ctx,actual);operations.push_back(JsValue(JsObject{{"definition",JsValue(pipeline)},{"description",JsValue(info.description?info.description:"unknown")},{"accuracy_metres",accuracy<0?JsValue():JsValue(accuracy)}}));}
  if(used)proj_destroy(used);GfVec3d result(v.xyz.x,v.xyz.y,v.xyz.z);if(d.geographic){result[0]/=d.units[0]*180/3.141592653589793;result[1]/=d.units[1]*180/3.141592653589793;}return result;
 }
};
std::map<std::pair<std::string,std::string>,std::unique_ptr<Operation>> ops;
GfVec3d Convert(const std::string& s,const std::string& d,const GfVec3d& p){auto& o=ops[{s,d}];if(!o)o=std::make_unique<Operation>(s,d);return o->Run(p);}
GfVec3d ToBasis(GfVec3d p){return yUp?GfVec3d(p[0],-p[2],p[1]):p;}
GfVec3d ToStage(GfVec3d p){return yUp?GfVec3d(p[0],p[2],-p[1]):p;}
GfVec3d Ecef(Definition& d,GfVec3d p){if(d.requiresVertical)throw std::runtime_error("Explicit ellipsoidal vertical chart conversion unsupported in this adapter");double lo=p[0]*d.units[0],la=p[1]*d.units[1],h=p[2]*d.units[2],e2=1-d.b*d.b/(d.a*d.a),n=d.a/sqrt(1-e2*sin(la)*sin(la));return {(n+h)*cos(la)*cos(lo),(n+h)*cos(la)*sin(lo),(n*(1-e2)+h)*sin(la)};}
GfMatrix3d Enu(Definition& d,GfVec3d p){double lo=p[0]*d.units[0],la=p[1]*d.units[1];if(std::abs(std::abs(la)-1.5707963267948966)<1e-14)throw std::runtime_error("ENU undefined at a pole");return GfMatrix3d(-sin(lo),cos(lo),0,-sin(la)*cos(lo),-sin(la)*sin(lo),cos(la),cos(la)*cos(lo),cos(la)*sin(lo),sin(la));}
GfVec3d InverseEcef(Definition& d,GfVec3d p){double e2=1-d.b*d.b/(d.a*d.a),r=hypot(p[0],p[1]),la=atan2(p[2],r*(1-e2)),n=0;for(int i=0;i<20;i++){n=d.a/sqrt(1-e2*sin(la)*sin(la));la=atan2(p[2]+e2*n*sin(la),r);}double h=std::abs(cos(la))>1e-8?r/cos(la)-n:std::abs(p[2])-d.b;return {atan2(p[1],p[0])/d.units[0],la/d.units[1],h/d.units[2]};}
GfVec3d Source(Definition& d,GfVec3d p,GfVec3d metric){if(d.dimensions!=3)throw std::runtime_error("Complete 3D model CRS required");if(!d.geographic)return {p[0]+metric[0]/d.units[0],p[1]+metric[1]/d.units[1],p[2]+metric[2]/d.units[2]};if(metric==GfVec3d(0))return p;return InverseEcef(d,Ecef(d,p)+metric*Enu(d,p));}
void Field(UsdPrim p,const char* name,SdfValueTypeName type){auto attr=p.GetAttribute(TfToken(name));if(!attr)return;auto stack=attr.GetPropertyStack(timeCode);if(!stack.empty()&&(stack[0]->GetTypeName()!=type||stack[0]->GetVariability()!=SdfVariabilityVarying))throw std::runtime_error("Invalid authored placement field declaration");if(attr.GetResolveInfo(timeCode).ValueIsBlocked())throw std::runtime_error("Blocked placement field unavailable");}
GfVec3d Position(UsdPrim p){Field(p,"crs:position",SdfValueTypeNames->Double3);GfVec3d v;if(!p.GetAttribute(TfToken("crs:position")).Get(&v,timeCode)||!std::isfinite(v[0])||!std::isfinite(v[1])||!std::isfinite(v[2]))throw std::runtime_error("Missing/nonfinite position");return v;}
GfVec3d Full(UsdPrim prim,GfVec3d point){
 auto anchor=Owner(prim);auto source=Wkt(anchor);auto& d=Def(source);GfMatrix4d D(1);bool reset=false;auto p=prim;
 while(p&&p!=anchor){UsdGeomXformable x(p);if(x){GfMatrix4d m;bool r;x.GetLocalTransformation(&m,&r,timeCode);D=D*m;if(r){reset=true;break;}}p=p.GetParent();}
 Field(anchor,"crs:scale",SdfValueTypeNames->Double3);Field(anchor,"crs:orientation",SdfValueTypeNames->Quatd);GfVec3d scale(1);GfQuatd rotation(1);auto a=anchor.GetAttribute(TfToken("crs:scale"));if(a&&a.HasAuthoredValueOpinion()&&!a.Get(&scale,timeCode))throw std::runtime_error("Unavailable scale");a=anchor.GetAttribute(TfToken("crs:orientation"));if(a&&a.HasAuthoredValueOpinion()&&!a.Get(&rotation,timeCode))throw std::runtime_error("Unavailable orientation");if(!std::isfinite(scale[0])||!std::isfinite(scale[1])||!std::isfinite(scale[2])||!std::isfinite(rotation.GetLength())||std::abs(rotation.GetLength()-1)>8*std::numeric_limits<double>::epsilon())throw std::runtime_error("Invalid scale or nonunit orientation");
 auto metric=ToBasis(D.Transform(point))*unit;metric=GfVec3d(metric[0]*scale[0],metric[1]*scale[1],metric[2]*scale[2])*GfMatrix3d(rotation);
 auto xyz=Source(d,Position(anchor),metric);GfMatrix4d A(1);bool ignored;if(!reset)UsdGeomXformable(anchor).GetLocalTransformation(&A,&ignored,timeCode);
 auto enclosing=anchor.GetParent();while(enclosing&&!enclosing.IsPseudoRoot()&&!Bound(enclosing))enclosing=enclosing.GetParent();if(enclosing&&!enclosing.IsPseudoRoot())Def(Wkt(enclosing));
 if(A==GfMatrix4d(1))return Convert(source,output,xyz);
 auto context=anchor.GetParent();while(context&&!context.IsPseudoRoot()&&!Bound(context))context=context.GetParent();if(!context||context.IsPseudoRoot())context=anchor;auto working=Wkt(context);auto& w=Def(working);auto v=Convert(source,working,xyz);GfVec3d chart,origin;
 if(w.geographic){origin=Position(context);chart=ToStage((Ecef(w,v)-Ecef(w,origin))*Enu(w,origin).GetTranspose())/unit;}
 else chart=ToStage(GfVec3d(v[0]*w.units[0],v[1]*w.units[1],v[2]*w.units[2]))/unit;
 auto adjusted=ToBasis(A.Transform(chart))*unit;
 if(w.geographic)v=InverseEcef(w,Ecef(w,origin)+adjusted*Enu(w,origin));else v={adjusted[0]/w.units[0],adjusted[1]/w.units[1],adjusted[2]/w.units[2]};
 return Convert(working,output,v);
}
GfVec3d Inverse(UsdPrim prim,GfVec3d coordinate){
 auto anchor=Owner(prim);auto source=Wkt(anchor);auto& d=Def(source);GfMatrix4d D(1);bool reset=false;auto p=prim;
 while(p&&p!=anchor){UsdGeomXformable x(p);if(x){GfMatrix4d m;bool r;x.GetLocalTransformation(&m,&r,timeCode);D=D*m;if(r){reset=true;break;}}p=p.GetParent();}
 Field(anchor,"crs:scale",SdfValueTypeNames->Double3);Field(anchor,"crs:orientation",SdfValueTypeNames->Quatd);GfVec3d scale(1);GfQuatd rotation(1);auto a=anchor.GetAttribute(TfToken("crs:scale"));if(a&&a.HasAuthoredValueOpinion()&&!a.Get(&scale,timeCode))throw std::runtime_error("Unavailable scale");a=anchor.GetAttribute(TfToken("crs:orientation"));if(a&&a.HasAuthoredValueOpinion()&&!a.Get(&rotation,timeCode))throw std::runtime_error("Unavailable orientation");if(!std::isfinite(scale[0])||!std::isfinite(scale[1])||!std::isfinite(scale[2])||!std::isfinite(rotation.GetLength())||std::abs(rotation.GetLength()-1)>8*std::numeric_limits<double>::epsilon())throw std::runtime_error("Invalid scale or nonunit orientation");
 GfMatrix4d A(1);bool ignored;if(!reset)UsdGeomXformable(anchor).GetLocalTransformation(&A,&ignored,timeCode);if(scale[0]==0||scale[1]==0||scale[2]==0||D.GetDeterminant()==0||A.GetDeterminant()==0)throw std::runtime_error("Singular placement has no inverse");GfVec3d v;
 auto enclosing=anchor.GetParent();while(enclosing&&!enclosing.IsPseudoRoot()&&!Bound(enclosing))enclosing=enclosing.GetParent();if(enclosing&&!enclosing.IsPseudoRoot())Def(Wkt(enclosing));
 if(A==GfMatrix4d(1))v=Convert(output,source,coordinate);
 else{auto context=anchor.GetParent();while(context&&!context.IsPseudoRoot()&&!Bound(context))context=context.GetParent();if(!context||context.IsPseudoRoot())context=anchor;auto working=Wkt(context);auto& w=Def(working);auto c=Convert(output,working,coordinate);GfVec3d chart,origin;
  if(w.geographic){origin=Position(context);chart=ToStage((Ecef(w,c)-Ecef(w,origin))*Enu(w,origin).GetTranspose())/unit;}else chart=ToStage(GfVec3d(c[0]*w.units[0],c[1]*w.units[1],c[2]*w.units[2]))/unit;
  auto adjusted=ToBasis(A.GetInverse().Transform(chart))*unit;if(w.geographic)c=InverseEcef(w,Ecef(w,origin)+adjusted*Enu(w,origin));else c={adjusted[0]/w.units[0],adjusted[1]/w.units[1],adjusted[2]/w.units[2]};v=Convert(working,source,c);
 }
 auto origin=Position(anchor);auto delta=d.geographic?(Ecef(d,v)-Ecef(d,origin))*Enu(d,origin).GetTranspose():GfVec3d((v[0]-origin[0])*d.units[0],(v[1]-origin[1])*d.units[1],(v[2]-origin[2])*d.units[2]);delta=delta*GfMatrix3d(rotation).GetTranspose();delta=GfVec3d(delta[0]/scale[0],delta[1]/scale[1],delta[2]/scale[2])/unit;
 return D.GetInverse().Transform(ToStage(delta));
}
GfVec3d Vec(const JsValue& v){auto a=v.GetJsArray();return {a[0].GetReal(),a[1].GetReal(),a.size()==3?a[2].GetReal():0};}
JsValue Json(const GfVec3d& p,int dim=3){JsArray a;for(int i=0;i<dim;i++)a.push_back(JsValue(p[i]));return JsValue(a);}
JsValue Frame(UsdPrim p){
 if(Def(output).geographic||Def(output).dimensions!=3)throw std::runtime_error("Geographic scene frames remain Q9; 3D Cartesian frame required");
 JsArray rows;double residual=0;GfMatrix3d matrix(0);
 for(int i=0;i<3;i++){GfVec3d a(0),b(0);a[i]=1;b[i]=.5;auto coarse=(Full(p,a)-Full(p,-a))/2.;auto fine=Full(p,b)-Full(p,-b);auto v=(4*fine-coarse)/3.;for(int k=0;k<3;k++){matrix[i][k]=v[k];residual=std::max(residual,std::abs(fine[k]-coarse[k]));}rows.push_back(Json(v));}
 return JsValue(JsObject{{"origin",Json(Full(p,GfVec3d(0)))},{"jacobian",JsValue(rows)},{"chart",JsValue("output CRS ordered Cartesian components")},{"units",JsValue("declared output component units per stage unit")},{"method",JsValue("Richardson-refined central differences at 1 and 0.5 stage units")},{"convergence_residual",JsValue(residual)},{"extent_certificate",JsValue(false)},{"inverse_available",JsValue(matrix.GetDeterminant()!=0)}});
}
}
int main(int argc,char** argv){try{
 if(argc!=3)throw std::runtime_error("Usage: leansNative job.json result.json");std::ifstream f(argv[1]);auto job=JsParseStream(f).GetJsObject();
 ctx=proj_context_create();std::vector<std::string> paths;std::istringstream ss(job.at("resources").GetString());std::string part;while(std::getline(ss,part,';'))paths.push_back(part);std::vector<const char*> dirs;for(auto& v:paths)dirs.push_back(v.c_str());proj_context_set_search_paths(ctx,int(dirs.size()),dirs.data());proj_context_set_enable_network(ctx,0);
 if(job.count("schema_directory"))PlugRegistry::GetInstance().RegisterPlugins(job.at("schema_directory").GetString());stage=UsdStage::Open(job.at("stage").GetString());if(!stage)throw std::runtime_error("Stage unavailable");stage->SetInterpolationType(job.at("interpolation").GetString()=="held"?UsdInterpolationTypeHeld:UsdInterpolationTypeLinear);timeCode=UsdTimeCode(job.at("time").GetReal());unit=UsdGeomGetStageMetersPerUnit(stage);yUp=UsdGeomGetStageUpAxis(stage)==TfToken("Y");output=job.at("output_wkt").GetString();if(output.empty())output=Wkt(stage->GetDefaultPrim());
 std::string before;stage->GetRootLayer()->ExportToString(&before);JsArray queries;JsObject geometry,geometrySources,result;
 for(auto q:job.at("queries").GetJsArray()){auto query=q.GetJsObject();auto p=stage->GetPrimAtPath(SdfPath(query.at("prim").GetString()));JsArray values;for(auto v:query.at("points").GetJsArray())values.push_back(Json(Full(p,Vec(v))));queries.push_back(JsValue(JsObject{{"prim",query.at("prim")},{"coordinates",JsValue(values)}}));}
 if(job.count("frames")){JsObject frames;for(auto path:job.at("frames").GetJsArray())frames[path.GetString()]=Frame(stage->GetPrimAtPath(SdfPath(path.GetString())));result["frames"]=JsValue(frames);}
 if(job.count("relative")){auto r=job.at("relative").GetJsObject();auto a=stage->GetPrimAtPath(SdfPath(r.at("from").GetString())),b=stage->GetPrimAtPath(SdfPath(r.at("to").GetString()));result["relative_position"]=JsValue(JsArray{Json(Inverse(b,Full(a,GfVec3d(0))))});}
 if(job.count("geometry")&&job.at("geometry").GetBool()){
  SdfPathVector prototypeRoots;for(auto p:stage->Traverse())if(p.IsA<UsdGeomPointInstancer>()){SdfPathVector paths;UsdGeomPointInstancer(p).GetPrototypesRel().GetTargets(&paths);prototypeRoots.insert(prototypeRoots.end(),paths.begin(),paths.end());}
  for(auto p:UsdPrimRange::Stage(stage,UsdTraverseInstanceProxies())){bool prototype=false;for(auto path:prototypeRoots)if(p.GetPath().HasPrefix(path))prototype=true;if(prototype)continue;VtVec3fArray points;if(!p.GetAttribute(TfToken("points")).Get(&points,timeCode))continue;try{Owner(p);}catch(...){continue;}JsArray values;for(auto v:points)values.push_back(Json(Full(p,GfVec3d(v))));geometry[p.GetPath().GetString()]=JsValue(values);geometrySources[p.GetPath().GetString()]=JsValue(p.GetPath().GetString());}
  for(auto p:stage->Traverse())if(p.IsA<UsdGeomPointInstancer>()){
   UsdGeomPointInstancer inst(p);SdfPathVector prototypes;inst.GetPrototypesRel().GetTargets(&prototypes);VtIntArray indices;inst.GetProtoIndicesAttr().Get(&indices,timeCode);VtMatrix4dArray transforms;if(!inst.ComputeInstanceTransformsAtTime(&transforms,timeCode,timeCode,UsdGeomPointInstancer::IncludeProtoXform,UsdGeomPointInstancer::IgnoreMask))throw std::runtime_error("Point instance transforms unavailable");auto mask=inst.ComputeMaskAtTime(timeCode);
   for(size_t i=0;i<transforms.size();i++){if(!mask.empty()&&!mask[i])continue;auto proto=stage->GetPrimAtPath(prototypes.at(indices[i]));for(auto mesh:UsdPrimRange(proto)){
    if(Bound(mesh))throw std::runtime_error("Independently CRS-bound point-instancer prototype is undefined");VtVec3fArray points;if(!mesh.GetAttribute(TfToken("points")).Get(&points,timeCode))continue;GfMatrix4d local(1);auto q=mesh;while(q&&q!=proto){UsdGeomXformable x(q);if(x){GfMatrix4d m;bool reset;x.GetLocalTransformation(&m,&reset,timeCode);local=local*m;if(reset)break;}q=q.GetParent();}
    auto matrix=local*transforms[i];JsArray values;for(auto v:points)values.push_back(Json(Full(p,matrix.Transform(GfVec3d(v)))));std::string path=p.GetPath().GetString()+"/_ResolvedInstance"+std::to_string(i)+"/"+mesh.GetName().GetString();if(geometry.count(path))throw std::runtime_error("Runtime instance output identity collision");geometry[path]=JsValue(values);geometrySources[path]=JsValue(mesh.GetPath().GetString());
   }}
  }
 }
 if(job.count("dataset_coordinates")){auto p=stage->GetPrimAtPath(SdfPath(job.at("dataset").GetString()));if(p.GetTypeName()!=TfToken("GeospatialDataSource"))throw std::runtime_error("No dataset role");auto source=Wkt(p);JsArray coords;for(auto v:job.at("dataset_coordinates").GetJsArray()){if(int(v.GetJsArray().size())!=Def(source).dimensions)throw std::runtime_error("Missing sample component");coords.push_back(Json(Convert(source,output,Vec(v)),Def(output).dimensions));}result["dataset_coordinates"]=JsValue(coords);}
 if(!geometry.empty()){GfVec3d low(std::numeric_limits<double>::max()),high(-std::numeric_limits<double>::max());for(auto& kv:geometry)for(auto v:kv.second.GetJsArray()){auto xyz=Vec(v);for(int i=0;i<3;i++){low[i]=std::min(low[i],xyz[i]);high[i]=std::max(high[i],xyz[i]);}}result["polygonal_bounds"]=JsValue(JsObject{{"min",Json(low)},{"max",Json(high)},{"domain",JsValue("resolved vertices and straight polygonal faces; no continuous source-face certificate")}});}
 std::string after;stage->GetRootLayer()->ExportToString(&after);result["queries"]=JsValue(queries);result["geometry"]=JsValue(geometry);result["geometry_sources"]=JsValue(geometrySources);result["operations"]=JsValue(operations);result["source_unchanged"]=JsValue(before==after);result["engine_version"]=JsValue(proj_info().version);
 std::ofstream out(argv[2]);JsWriteToStream(JsValue(result),out);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
