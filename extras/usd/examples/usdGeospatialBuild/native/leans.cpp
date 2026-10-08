// Independent USD/C++ pointwise reader of the exact pinned proposal candidate.
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
#include <proj_experimental.h>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <cmath>
#include <sstream>
#include <stdexcept>
#include <algorithm>
#include <limits>
#include <functional>
#include <set>
#include "pxr/usd/usdGeom/mesh.h"
PXR_NAMESPACE_USING_DIRECTIVE
namespace {
PJ_CONTEXT* ctx=nullptr;UsdStageRefPtr stage;UsdTimeCode timeCode;std::string output;double unit;bool yUp;
JsArray operations;std::set<std::string> recordedOperations;
bool Bound(const UsdPrim& p){SdfTokenListOp schemas;if(!p.GetMetadata(TfToken("apiSchemas"),&schemas))return false;auto names=schemas.GetAppliedItems();return std::find(names.begin(),names.end(),TfToken("GeospatialCRSBindingAPI"))!=names.end();}
UsdPrim Owner(UsdPrim p){while(p&&!p.IsPseudoRoot()){if(Bound(p)||p.GetTypeName()==TfToken("CoordinateReferenceSystem"))return p;for(auto name:{"crs:position","crs:orientation"}){auto a=p.GetAttribute(TfToken(name));if(a&&!a.GetPropertyStack(timeCode).empty())throw std::runtime_error(std::string("Invalid placement field on inherited-only descendant: ")+name);}p=p.GetParent();}throw std::runtime_error("No CRS binding");}
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
  if(recordedOperations.insert(pipeline).second){double accuracy=proj_coordoperation_get_accuracy(ctx,actual);operations.push_back(JsValue(JsObject{{"definition",JsValue(pipeline)},{"description",JsValue(info.description?info.description:"unknown")},{"accuracy_metres",accuracy<0?JsValue():JsValue(accuracy)}}));}
  if(used)proj_destroy(used);GfVec3d result(v.xyz.x,v.xyz.y,v.xyz.z);if(d.geographic){result[0]/=d.units[0]*180/3.141592653589793;result[1]/=d.units[1]*180/3.141592653589793;}return result;
 }
};
std::map<std::pair<std::string,std::string>,std::unique_ptr<Operation>> ops;
GfVec3d Convert(const std::string& s,const std::string& d,const GfVec3d& p){auto& o=ops[{s,d}];if(!o)o=std::make_unique<Operation>(s,d);return o->Run(p);}
GfVec3d ToBasis(GfVec3d p){return yUp?GfVec3d(p[0],-p[2],p[1]):p;}
GfVec3d ToStage(GfVec3d p){return yUp?GfVec3d(p[0],p[2],-p[1]):p;}
GfVec3d Ecef(Definition& d,GfVec3d p){if(d.requiresVertical)throw std::runtime_error("Explicit ellipsoidal vertical chart conversion unsupported in this adapter");double lo=p[0]*d.units[0],la=p[1]*d.units[1],h=p[2]*d.units[2],e2=1-d.b*d.b/(d.a*d.a),n=d.a/sqrt(1-e2*sin(la)*sin(la));return {(n+h)*cos(la)*cos(lo),(n+h)*cos(la)*sin(lo),(n*(1-e2)+h)*sin(la)};}
GfMatrix3d Enu(Definition& d,GfVec3d p){double lo=p[0]*d.units[0],la=p[1]*d.units[1];return GfMatrix3d(-sin(lo),cos(lo),0,-sin(la)*cos(lo),-sin(la)*sin(lo),cos(la),cos(la)*cos(lo),cos(la)*sin(lo),sin(la));}
GfVec3d InverseEcef(Definition& d,GfVec3d p){double e2=1-d.b*d.b/(d.a*d.a),r=hypot(p[0],p[1]),la=atan2(p[2],r*(1-e2)),n=0;for(int i=0;i<20;i++){n=d.a/sqrt(1-e2*sin(la)*sin(la));la=atan2(p[2]+e2*n*sin(la),r);}double h=std::abs(cos(la))>1e-8?r/cos(la)-n:std::abs(p[2])-d.b;return {atan2(p[1],p[0])/d.units[0],la/d.units[1],h/d.units[2]};}
std::map<std::string,std::string> geographics,geocentrics;
std::string Geographic(const std::string& w){
 auto& cached=geographics[w];if(!cached.empty())return cached;
 auto obj=Def(w).object;PJ* horizontal=nullptr;
 if(proj_get_type(obj)==PJ_TYPE_COMPOUND_CRS){horizontal=proj_crs_get_sub_crs(ctx,obj,0);obj=horizontal;}
 auto g=proj_crs_get_geodetic_crs(ctx,obj);if(horizontal)proj_destroy(horizontal);if(!g)throw std::runtime_error("No geodetic relationship");
 if(proj_get_type(g)==PJ_TYPE_GEOCENTRIC_CRS){
  auto data=JsParseString(proj_as_projjson(ctx,g,nullptr)).GetJsObject();data.erase("id");data["type"]=JsValue("GeographicCRS");
  data["coordinate_system"]=JsParseString(R"({"subtype":"ellipsoidal","axis":[{"name":"Geodetic longitude","abbreviation":"Lon","direction":"east","unit":"degree"},{"name":"Geodetic latitude","abbreviation":"Lat","direction":"north","unit":"degree"},{"name":"Ellipsoidal height","abbreviation":"h","direction":"up","unit":"metre"}]})");
  std::ostringstream text;JsWriteToStream(JsValue(data),text);proj_destroy(g);g=proj_create(ctx,text.str().c_str());
 }else{auto promoted=proj_crs_promote_to_3D(ctx,nullptr,g);proj_destroy(g);g=promoted;}
 if(!g)throw std::runtime_error("Geographic 3D representation unavailable");cached=proj_as_wkt(ctx,g,PJ_WKT2_2019,nullptr);proj_destroy(g);return cached;
}
std::string Geocentric(const std::string& w){
 auto& cached=geocentrics[w];if(!cached.empty())return cached;
 auto& g=Def(Geographic(w));auto data=JsParseString(proj_as_projjson(ctx,g.object,nullptr)).GetJsObject();data.erase("id");data["type"]=JsValue("GeodeticCRS");
 data["coordinate_system"]=JsParseString(R"({"subtype":"Cartesian","axis":[{"name":"Geocentric X","abbreviation":"X","direction":"geocentricX","unit":"metre"},{"name":"Geocentric Y","abbreviation":"Y","direction":"geocentricY","unit":"metre"},{"name":"Geocentric Z","abbreviation":"Z","direction":"geocentricZ","unit":"metre"}]})");
 std::ostringstream text;JsWriteToStream(JsValue(data),text);auto c=proj_create(ctx,text.str().c_str());if(!c)throw std::runtime_error("Geocentric scene chart unavailable");cached=proj_as_wkt(ctx,c,PJ_WKT2_2019,nullptr);proj_destroy(c);return cached;
}
GfVec3d Source(const std::string& w,GfVec3d p,GfVec3d metric){
 if(Def(w).dimensions!=3)throw std::runtime_error("Complete 3D model CRS required");auto gw=Geographic(w);auto& g=Def(gw);auto o=Convert(w,gw,p);
 return Convert(gw,w,InverseEcef(g,Ecef(g,o)+metric*Enu(g,o)));
}
std::string Working(UsdPrim anchor,const std::string& source){auto p=anchor.GetParent();while(p&&!p.IsPseudoRoot()&&!Bound(p))p=p.GetParent();return p&&!p.IsPseudoRoot()?Wkt(p):source;}
GfVec3d Chart(const std::string& work,GfVec3d p,GfVec3d origin){
 auto& w=Def(work);if(w.geographic){auto gw=Geographic(work);auto& g=Def(gw);auto o=Convert(work,gw,origin);return ToStage((Ecef(g,Convert(work,gw,p))-Ecef(g,o))*Enu(g,o).GetTranspose())/unit;}
 return ToStage(GfVec3d((p[0]-origin[0])*w.units[0],(p[1]-origin[1])*w.units[1],(p[2]-origin[2])*w.units[2]))/unit;
}
GfVec3d Unchart(const std::string& work,GfVec3d p,GfVec3d origin){auto& w=Def(work);auto v=ToBasis(p)*unit;
 if(w.geographic){auto gw=Geographic(work);auto& g=Def(gw);auto o=Convert(work,gw,origin);return Convert(gw,work,InverseEcef(g,Ecef(g,o)+v*Enu(g,o)));}
 return {v[0]/w.units[0]+origin[0],v[1]/w.units[1]+origin[1],v[2]/w.units[2]+origin[2]};
}
void Field(UsdPrim p,const char* name,SdfValueTypeName type){auto attr=p.GetAttribute(TfToken(name));if(!attr)return;auto stack=attr.GetPropertyStack(timeCode);if(!stack.empty()&&(stack[0]->GetTypeName()!=type||stack[0]->GetVariability()!=SdfVariabilityVarying))throw std::runtime_error("Invalid authored placement field declaration");if(attr.GetResolveInfo(timeCode).ValueIsBlocked())throw std::runtime_error("Blocked placement field unavailable");}
GfVec3d Position(UsdPrim p){Field(p,"crs:position",SdfValueTypeNames->Double3);GfVec3d v;if(!p.GetAttribute(TfToken("crs:position")).Get(&v,timeCode)||!std::isfinite(v[0])||!std::isfinite(v[1])||!std::isfinite(v[2]))throw std::runtime_error("Missing/nonfinite position");return v;}
GfQuatd HprSample(const UsdAttribute& a,UsdTimeCode t){
 GfVec3d hpr;if(!a.Get(&hpr,t))throw std::runtime_error("Unavailable orientation");
 for(int i=0;i<3;i++)if(!std::isfinite(hpr[i]))throw std::runtime_error("Nonfinite orientation");
 double h=hpr[0]/360*3.141592653589793,p=hpr[1]/360*3.141592653589793,r=hpr[2]/360*3.141592653589793;
 auto qh=GfQuatd(cos(h),GfVec3d(0,0,-sin(h)));auto qp=GfQuatd(cos(p),GfVec3d(sin(p),0,0));auto qr=GfQuatd(cos(r),GfVec3d(0,sin(r),0));
 return (qh*qp*qr).GetNormalized();
}
GfQuatd Orientation(UsdPrim p){
 Field(p,"crs:orientation",SdfValueTypeNames->Double3);auto a=p.GetAttribute(TfToken("crs:orientation"));
 if(a&&a.GetResolveInfo(timeCode).ValueIsBlocked())throw std::runtime_error("Unavailable orientation");
 if(!a||!a.HasAuthoredValueOpinion())return GfQuatd(1);
 if(timeCode.IsDefault())return HprSample(a,timeCode);
 double lower=0,upper=0;bool has=false;
 if(!a.GetBracketingTimeSamples(timeCode.GetValue(),&lower,&upper,&has))throw std::runtime_error("Unavailable orientation samples");
 if(!has)return HprSample(a,timeCode);
 auto first=HprSample(a,UsdTimeCode(lower));
 if(lower==upper||stage->GetInterpolationType()==UsdInterpolationTypeHeld)return first;
 auto second=HprSample(a,UsdTimeCode(upper));
 double dot=first.GetReal()*second.GetReal()+GfDot(first.GetImaginary(),second.GetImaginary());
 if(dot<0)second=GfQuatd(-second.GetReal(),-second.GetImaginary());
 return GfSlerp((timeCode.GetValue()-lower)/(upper-lower),first,second).GetNormalized();
}
std::map<std::string,std::function<GfVec3d(GfVec3d)>> preparedMaps;
GfVec3d Full(UsdPrim prim,GfVec3d point,const GfMatrix4d* instance=nullptr){
 std::ostringstream identity;identity.precision(17);identity<<prim.GetPath().GetString();if(instance)identity<<*instance;auto key=identity.str();auto found=preparedMaps.find(key);if(found!=preparedMaps.end())return found->second(point);
 auto anchor=Owner(prim);auto source=Wkt(anchor);auto& d=Def(source);GfMatrix4d D(1);bool reset=false;auto p=prim;
 while(p&&p!=anchor){UsdGeomXformable x(p);if(x){GfMatrix4d m;bool r;x.GetLocalTransformation(&m,&r,timeCode);D=D*m;if(r){reset=true;break;}}p=p.GetParent();}
 if(!Bound(anchor)){
  if(d.geographic)throw std::runtime_error("Baked ordinary geometry needs Cartesian context");auto units=d.units;
  preparedMaps[key]=[=](GfVec3d x){auto v=ToBasis(D.Transform(x))*unit;return Convert(source,output,{v[0]/units[0],v[1]/units[1],v[2]/units[2]});};return preparedMaps[key](point);
 }
 if(anchor.GetTypeName()==TfToken("GeospatialDataSource"))throw std::runtime_error("Data source is not a model anchor");
 auto old=anchor.GetAttribute(TfToken("crs:scale"));if(old&&old.HasAuthoredValueOpinion())throw std::runtime_error("Undocumented crs:scale is not an input");
 auto rotation=Orientation(anchor);
 auto origin=Position(anchor);auto work=Working(anchor,source);Def(work);if(d.dimensions!=3)throw std::runtime_error("Complete 3D model CRS required");
 auto gw=Geographic(source);auto go=Convert(source,gw,origin);auto base=Ecef(Def(gw),go);auto axes=Enu(Def(gw),go);auto R=GfMatrix3d(rotation);
 GfMatrix4d A(1);bool ignored;if(!reset)UsdGeomXformable(anchor).GetLocalTransformation(&A,&ignored,timeCode);if(instance)A=A*(*instance);
 auto o=A==GfMatrix4d(1)?GfVec3d(0):Convert(source,work,origin);
 preparedMaps[key]=[=](GfVec3d x){auto metric=ToBasis(D.Transform(x))*unit*R;auto xyz=Convert(gw,source,InverseEcef(Def(gw),base+metric*axes));
  if(A==GfMatrix4d(1))return Convert(source,output,xyz);auto c=Chart(work,Convert(source,work,xyz),o);return Convert(work,output,Unchart(work,A.Transform(c),o));};
 return preparedMaps[key](point);
}

GfVec3d Measurement(UsdPrim p,const std::string& source,GfVec3d point){
 auto work=Working(p,source);auto& w=Def(work);GfMatrix4d A(1);bool reset;UsdGeomXformable(p).GetLocalTransformation(&A,&reset,timeCode);
 if(A==GfMatrix4d(1))return Convert(source,output,point);auto v=Convert(source,work,point);
 if(w.dimensions==2){
  if(w.geographic)throw std::runtime_error("Geographic adjustment requires height");
  auto zero=ToBasis(A.Transform(GfVec3d(0)));auto east=ToBasis(A.Transform(ToStage({1,0,0})))-zero;auto north=ToBasis(A.Transform(ToStage({0,1,0})))-zero;auto up=ToBasis(A.Transform(ToStage({0,0,1})))-zero;
  if(std::abs(zero[2])+std::abs(east[2])+std::abs(north[2])+std::abs(up[0])+std::abs(up[1])>1e-14)throw std::runtime_error("Nonplanar adjustment requires height");
  auto c=ToStage({v[0]*w.units[0]/unit,v[1]*w.units[1]/unit,0});auto r=ToBasis(A.Transform(c))*unit;
  return Convert(work,output,{r[0]/w.units[0],r[1]/w.units[1],0});
 }
 return Convert(work,output,Unchart(work,A.Transform(Chart(work,v,GfVec3d(0))),GfVec3d(0)));
}
GfVec3d Vec(const JsValue& v){auto a=v.GetJsArray();return {a[0].GetReal(),a[1].GetReal(),a.size()==3?a[2].GetReal():0};}
JsValue Json(const GfVec3d& p,int dim=3){JsArray a;for(int i=0;i<dim;i++)a.push_back(JsValue(p[i]));return JsValue(a);}
JsObject geometryNormals;
void RecordNormals(UsdPrim mesh,const std::string& path,std::function<GfVec3d(GfVec3d)> map){
 VtVec3fArray normals,points;auto attr=mesh.GetAttribute(TfToken("normals"));if(!attr||!attr.HasAuthoredValueOpinion()||!attr.Get(&normals,timeCode))return;
 mesh.GetAttribute(TfToken("points")).Get(&points,timeCode);UsdGeomMesh m(mesh);auto interpolation=m?m.GetNormalsInterpolation():TfToken("vertex");std::vector<GfVec3d> positions;
 if((interpolation==TfToken("vertex")||interpolation==TfToken("varying"))&&normals.size()==points.size()){for(auto v:points)positions.push_back(GfVec3d(v));}
 else if(interpolation==TfToken("faceVarying")){VtIntArray indices;m.GetFaceVertexIndicesAttr().Get(&indices,timeCode);for(auto i:indices)positions.push_back(GfVec3d(points[i]));}
 else if(interpolation==TfToken("uniform")){VtIntArray indices,counts;m.GetFaceVertexIndicesAttr().Get(&indices,timeCode);m.GetFaceVertexCountsAttr().Get(&counts,timeCode);size_t offset=0;for(auto count:counts){GfVec3d center(0);for(int j=0;j<count;j++)center+=GfVec3d(points[indices[offset++]]);positions.push_back(center/double(count));}}
 else if(interpolation==TfToken("constant")&&normals.size()==1){auto n=normals[0];normals=VtVec3fArray(points.size(),n);for(auto v:points)positions.push_back(GfVec3d(v));interpolation=TfToken("vertex");}
 else throw std::runtime_error("Invalid normal interpolation domain");
 if(normals.size()!=positions.size())throw std::runtime_error("Normal association mismatch");JsArray values;auto chart=Def(output).geographic?Geocentric(output):output;auto& d=Def(chart);
 for(size_t j=0;j<normals.size();j++){GfMatrix3d J(0);for(int i=0;i<3;i++){GfVec3d step(0);step[i]=.5;auto a=map(positions[j]+step),b=map(positions[j]-step);if(chart!=output){a=Convert(output,chart,a);b=Convert(output,chart,b);}auto v=a-b;v=ToStage({v[0]*d.units[0],v[1]*d.units[1],v[2]*d.units[2]})/unit;for(int k=0;k<3;k++)J[i][k]=v[k];}
  if(std::abs(J.GetDeterminant())<1e-15)throw std::runtime_error("Singular normal transport");auto n=GfVec3d(normals[j])*J.GetInverse().GetTranspose();if(n.GetLength()==0)throw std::runtime_error("Zero normal");n.Normalize();values.push_back(Json(n));}
 geometryNormals[path]=JsValue(JsObject{{"values",JsValue(values)},{"interpolation",JsValue(interpolation.GetString())}});
}
JsValue Frame(UsdPrim p){
 if(Def(output).dimensions!=3)throw std::runtime_error("3D Cartesian frame requires height");auto chart=Def(output).geographic?Geocentric(output):output;auto eval=[&](GfVec3d v){return Convert(output,chart,Full(p,v));};
 JsArray rows;double residual=0;GfMatrix3d matrix(0);
 for(int i=0;i<3;i++){GfVec3d a(0),b(0);a[i]=1;b[i]=.5;auto coarse=(eval(a)-eval(-a))/2.;auto fine=eval(b)-eval(-b);auto v=(4*fine-coarse)/3.;for(int k=0;k<3;k++){matrix[i][k]=v[k];residual=std::max(residual,std::abs(fine[k]-coarse[k]));}rows.push_back(Json(v));}
 return JsValue(JsObject{{"origin",Json(Full(p,GfVec3d(0)))},{"jacobian",JsValue(rows)},{"chart",JsValue(Def(output).geographic?"associated geocentric Cartesian":"output CRS ordered Cartesian components")},{"units",JsValue("declared output component units per stage unit")},{"method",JsValue("Richardson-refined central differences at 1 and 0.5 stage units")},{"convergence_residual",JsValue(residual)},{"extent_certificate",JsValue(false)},{"inverse_available",JsValue(matrix.GetDeterminant()!=0)}});
}
}
int main(int argc,char** argv){try{
 if(argc!=3)throw std::runtime_error("Usage: leansNative job.json result.json");std::ifstream f(argv[1]);auto job=JsParseStream(f).GetJsObject();
 ctx=proj_context_create();std::vector<std::string> paths;std::istringstream ss(job.at("resources").GetString());std::string part;while(std::getline(ss,part,';'))paths.push_back(part);std::vector<const char*> dirs;for(auto& v:paths)dirs.push_back(v.c_str());proj_context_set_search_paths(ctx,int(dirs.size()),dirs.data());proj_context_set_enable_network(ctx,0);
 if(job.count("schema_directory"))PlugRegistry::GetInstance().RegisterPlugins(job.at("schema_directory").GetString());stage=UsdStage::Open(job.at("stage").GetString());if(!stage)throw std::runtime_error("Stage unavailable");stage->SetInterpolationType(job.at("interpolation").GetString()=="held"?UsdInterpolationTypeHeld:UsdInterpolationTypeLinear);timeCode=UsdTimeCode(job.at("time").GetReal());unit=UsdGeomGetStageMetersPerUnit(stage);yUp=UsdGeomGetStageUpAxis(stage)==TfToken("Y");output=job.at("output_wkt").GetString();if(output.empty())output=Wkt(stage->GetDefaultPrim());
 std::string before;stage->GetRootLayer()->ExportToString(&before);JsArray queries;JsObject geometry,geometrySources,result;
 for(auto q:job.at("queries").GetJsArray()){auto query=q.GetJsObject();auto p=stage->GetPrimAtPath(SdfPath(query.at("prim").GetString()));JsArray values;for(auto v:query.at("points").GetJsArray())values.push_back(Json(Full(p,Vec(v))));queries.push_back(JsValue(JsObject{{"prim",query.at("prim")},{"coordinates",JsValue(values)}}));}
 if(job.count("frames")){JsObject frames;for(auto path:job.at("frames").GetJsArray())frames[path.GetString()]=Frame(stage->GetPrimAtPath(SdfPath(path.GetString())));result["frames"]=JsValue(frames);}
 if(job.count("relative")){auto r=job.at("relative").GetJsObject();auto a=stage->GetPrimAtPath(SdfPath(r.at("from").GetString())),b=stage->GetPrimAtPath(SdfPath(r.at("to").GetString()));result["relative_position"]=JsValue(JsArray{Json(Full(a,GfVec3d(0))-Full(b,GfVec3d(0)))});}
 if(job.count("geometry")&&job.at("geometry").GetBool()){
  SdfPathVector prototypeRoots;for(auto p:stage->Traverse())if(p.IsA<UsdGeomPointInstancer>()){SdfPathVector paths;UsdGeomPointInstancer(p).GetPrototypesRel().GetTargets(&paths);prototypeRoots.insert(prototypeRoots.end(),paths.begin(),paths.end());}
  for(auto p:UsdPrimRange::Stage(stage,UsdTraverseInstanceProxies())){bool prototype=false;for(auto path:prototypeRoots)if(p.GetPath().HasPrefix(path))prototype=true;if(prototype)continue;VtVec3fArray points;if(!p.GetAttribute(TfToken("points")).Get(&points,timeCode))continue;try{Owner(p);}catch(const std::runtime_error& e){if(std::string(e.what())=="No CRS binding")continue;throw;}JsArray values;for(auto v:points)values.push_back(Json(Full(p,GfVec3d(v))));geometry[p.GetPath().GetString()]=JsValue(values);geometrySources[p.GetPath().GetString()]=JsValue(p.GetPath().GetString());RecordNormals(p,p.GetPath().GetString(),[&](GfVec3d v){return Full(p,v);});}
  for(auto p:stage->Traverse())if(p.IsA<UsdGeomPointInstancer>()){
   UsdGeomPointInstancer inst(p);SdfPathVector prototypes;inst.GetPrototypesRel().GetTargets(&prototypes);VtIntArray indices;inst.GetProtoIndicesAttr().Get(&indices,timeCode);VtMatrix4dArray transforms;if(!inst.ComputeInstanceTransformsAtTime(&transforms,timeCode,timeCode,UsdGeomPointInstancer::ExcludeProtoXform,UsdGeomPointInstancer::IgnoreMask))throw std::runtime_error("Point instance transforms unavailable");auto mask=inst.ComputeMaskAtTime(timeCode);
   for(size_t i=0;i<transforms.size();i++){if(!mask.empty()&&!mask[i])continue;auto proto=stage->GetPrimAtPath(prototypes.at(indices[i]));for(auto mesh:UsdPrimRange(proto)){
    VtVec3fArray points;if(!mesh.GetAttribute(TfToken("points")).Get(&points,timeCode))continue;GfMatrix4d local(1);bool localReset=false;auto q=mesh;while(q&&q!=proto){UsdGeomXformable x(q);if(x){GfMatrix4d m;bool reset;x.GetLocalTransformation(&m,&reset,timeCode);local=local*m;if(reset){localReset=true;break;}}q=q.GetParent();}
    UsdPrim owner;try{owner=Owner(mesh);}catch(const std::runtime_error& e){if(std::string(e.what())!="No CRS binding")throw;}bool independent=owner&&owner.GetPath().HasPrefix(proto.GetPath());GfMatrix4d protoLocal(1);bool protoReset;if(!localReset)UsdGeomXformable(proto).GetLocalTransformation(&protoLocal,&protoReset,timeCode);
    auto matrix=local*protoLocal*transforms[i];JsArray values;for(auto v:points)values.push_back(Json(independent?Full(mesh,GfVec3d(v),&transforms[i]):Full(p,matrix.Transform(GfVec3d(v)))));
    auto relative=mesh.GetPath().MakeRelativePath(proto.GetPath()).GetString();if(relative==".")relative="Root";std::string path=p.GetPath().GetString()+"/_ResolvedInstance"+std::to_string(i)+"/"+relative;if(geometry.count(path))throw std::runtime_error("Runtime instance output identity collision");geometry[path]=JsValue(values);geometrySources[path]=JsValue(mesh.GetPath().GetString());RecordNormals(mesh,path,[&](GfVec3d v){return independent?Full(mesh,v,&transforms[i]):Full(p,matrix.Transform(v));});
   }}
  }
 }
 if(job.count("dataset_coordinates")){auto p=stage->GetPrimAtPath(SdfPath(job.at("dataset").GetString()));if(p.GetTypeName()!=TfToken("GeospatialDataSource"))throw std::runtime_error("No dataset role");auto source=Wkt(p);JsArray coords;for(auto v:job.at("dataset_coordinates").GetJsArray()){if(int(v.GetJsArray().size())!=Def(source).dimensions)throw std::runtime_error("Missing sample component");coords.push_back(Json(Measurement(p,source,Vec(v)),Def(output).dimensions));}result["dataset_coordinates"]=JsValue(coords);}
 if(!geometry.empty()){GfVec3d low(std::numeric_limits<double>::max()),high(-std::numeric_limits<double>::max());for(auto& kv:geometry)for(auto v:kv.second.GetJsArray()){auto xyz=Vec(v);if(Def(output).geographic)xyz=Convert(output,Geocentric(output),xyz);for(int i=0;i<3;i++){low[i]=std::min(low[i],xyz[i]);high[i]=std::max(high[i],xyz[i]);}}result["polygonal_bounds"]=JsValue(JsObject{{"min",Json(low)},{"max",Json(high)},{"chart_wkt",JsValue(Def(output).geographic?Geocentric(output):output)},{"domain",JsValue("resolved vertices and straight polygonal faces; no continuous source-face certificate")}});}
 std::string after;stage->GetRootLayer()->ExportToString(&after);result["queries"]=JsValue(queries);result["geometry"]=JsValue(geometry);result["geometry_sources"]=JsValue(geometrySources);result["geometry_normals"]=JsValue(geometryNormals);result["operations"]=JsValue(operations);result["source_unchanged"]=JsValue(before==after);result["engine_version"]=JsValue(proj_info().version);
 std::ofstream out(argv[2]);JsWriteToStream(JsValue(result),out);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
