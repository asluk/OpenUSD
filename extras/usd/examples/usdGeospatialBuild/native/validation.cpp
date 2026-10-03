// Authored-content validator loaded by the unmodified stock usdchecker.
#include "pxr/base/tf/registryManager.h"
#include "pxr/usd/usd/primRange.h"
#include "pxr/usd/usdGeom/xformable.h"
#include "pxr/usdValidation/usdValidation/registry.h"
#include "pxr/usdValidation/usdValidation/error.h"
#include "pxr/usdValidation/usdValidation/timeRange.h"
#include <proj.h>
#include <regex>
#include <cmath>
#include <stdexcept>
PXR_NAMESPACE_USING_DIRECTIVE
namespace {
std::string Number(std::string n){
 bool negative=n[0]=='-';if(n[0]=='-'||n[0]=='+')n.erase(0,1);
 auto e=n.find_first_of("eE");int exponent=e==std::string::npos?0:std::stoi(n.substr(e+1));if(e!=std::string::npos)n.resize(e);
 auto dot=n.find('.');int point=dot==std::string::npos?int(n.size()):int(dot);if(dot!=std::string::npos)n.erase(dot,1);point+=exponent;
 if(abs(point)>10000)throw std::runtime_error("WKT numeric exponent exceeds validator capacity");
 std::string s=point<=0?"0."+std::string(-point,'0')+n:point>=int(n.size())?n+std::string(point-n.size(),'0'):n.substr(0,point)+"."+n.substr(point);
 while(s.size()>1&&s[0]=='0'&&s[1]!='.')s.erase(0,1);
 if(s.find('.')!=std::string::npos){while(s.back()=='0')s.pop_back();if(s.back()=='.')s.pop_back();}
 bool zero=true;for(char c:s)if(c!='0'&&c!='.')zero=false;return zero?"0":(negative?"-":"")+s;
}
std::string Normal(const std::string& w){
 static const std::regex lex(R"LEX("(?:[^"\n]|"")*"|[A-Za-z_][A-Za-z_0-9]*|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?|[\[\](),]|\s+)LEX");
 std::string out;size_t end=0;
 for(std::sregex_iterator it(w.begin(),w.end(),lex),last;it!=last;++it){if(it->position()!=end)throw std::runtime_error("Unsupported WKT token");std::string s=it->str();end=it->position()+it->length();unsigned char c=s[0];if(isspace(c))continue;
  if(c=='"')out+=s;else if(isalpha(c)||c=='_'){for(char &x:s)x=char(toupper(static_cast<unsigned char>(x)));out+=s;}else if(s.size()==1&&std::string("[](),").find(c)!=std::string::npos)out+=s;else out+=Number(s);
 }if(end!=w.size())throw std::runtime_error("Invalid WKT suffix");return out;
}
void CheckWkt(const UsdAttribute& a){
 TfToken w;if(a.GetTypeName()!=SdfValueTypeNames->Token||a.GetVariability()!=SdfVariabilityUniform||!a.Get(&w))throw std::runtime_error("WKT requires a valued uniform token");
 auto text=w.GetString();if(Normal(text)!=text)throw std::runtime_error("WKT string is not normalized");if(text.rfind("COORDINATEMETADATA",0)==0)throw std::runtime_error("Coordinate epoch wrapper deferred");
 auto ctx=proj_context_create();proj_log_level(ctx,PJ_LOG_NONE);auto crs=proj_create(ctx,text.c_str());if(!crs){proj_context_destroy(ctx);throw std::runtime_error("Invalid CRS WKT");}
 int axes=0;auto type=proj_get_type(crs);if(type==PJ_TYPE_BOUND_CRS){auto coordinate=proj_get_source_crs(ctx,crs);proj_destroy(crs);crs=coordinate;type=proj_get_type(crs);}
 if(type==PJ_TYPE_COMPOUND_CRS){for(int i=0;i<2;i++){auto c=proj_crs_get_sub_crs(ctx,crs,i);auto cs=proj_crs_get_coordinate_system(ctx,c);axes+=cs?proj_cs_get_axis_count(ctx,cs):0;proj_destroy(cs);proj_destroy(c);}}
 else {auto cs=proj_crs_get_coordinate_system(ctx,crs);axes=cs?proj_cs_get_axis_count(ctx,cs):0;proj_destroy(cs);}
 proj_destroy(crs);proj_context_destroy(ctx);if(axes!=3)throw std::runtime_error("Complete three-axis CRS required");
}
std::vector<UsdTimeCode> Times(const UsdAttribute& a){std::vector<double> samples;a.GetTimeSamples(&samples);std::vector<UsdTimeCode> r{UsdTimeCode::Default()};for(double t:samples)r.emplace_back(t);return r;}
bool Finite(const GfVec3d& v){return std::isfinite(v[0])&&std::isfinite(v[1])&&std::isfinite(v[2]);}
UsdValidationErrorVector Check(const UsdStagePtr& s,const UsdValidationTimeRange&){
 UsdValidationErrorVector errors;bool dependent=false;
 auto error=[&](const SdfPath& p,const std::string& m){errors.emplace_back(TfToken("AuthoredModel"),UsdValidationErrorType::Error,UsdValidationErrorSites{UsdValidationErrorSite(s,p)},m);};
 for(auto p:UsdPrimRange::Stage(s,UsdTraverseInstanceProxies()))try{
  auto w=p.GetAttribute(TfToken("crs:wkt"));if(w)CheckWkt(w);
  auto b=p.GetRelationship(TfToken("crs:binding"));if(!b||!b.HasAuthoredTargets())continue;dependent=true;SdfPathVector paths;b.GetTargets(&paths);
  if(paths.size()!=1)throw std::runtime_error("Binding requires one target");auto target=s->GetPrimAtPath(paths[0]);if(!target)throw std::runtime_error("Broken CRS target");CheckWkt(target.GetAttribute(TfToken("crs:wkt")));
  auto roles=p.GetRelationship(TfToken("crs:coordinateProperties"));bool measurement=roles&&roles.HasAuthoredTargets();
  if(measurement){SdfPathVector a;roles.GetTargets(&a);if(a.empty())throw std::runtime_error("Empty coordinate association");for(auto path:a){auto v=s->GetAttributeAtPath(path);if(path.GetPrimPath()!=p.GetPath()||!v||v.GetTypeName()!=SdfValueTypeNames->Double3Array)throw std::runtime_error("Coordinate role must target on-prim double3[]");for(auto t:Times(v)){VtVec3dArray rows;if(v.Get(&rows,t))for(auto row:rows)if(!Finite(row))throw std::runtime_error("Nonfinite coordinate");}}}
  else if(UsdGeomXformable(p)){
   auto a=p.GetAttribute(TfToken("crs:position"));if(!a||!a.HasAuthoredValueOpinion()||a.GetTypeName()!=SdfValueTypeNames->Double3)throw std::runtime_error("Direct model binding requires double3 placement position");for(auto t:Times(a)){GfVec3d v;if(a.Get(&v,t)&&!Finite(v))throw std::runtime_error("Nonfinite position");}
   a=p.GetAttribute(TfToken("crs:orientation"));if(a){if(a.GetTypeName()!=SdfValueTypeNames->Quatd)throw std::runtime_error("Orientation must be quatd");for(auto t:Times(a)){GfQuatd q;if(a.Get(&q,t)&&(!std::isfinite(q.GetLength())||abs(q.GetLength()-1)>1e-9))throw std::runtime_error("Orientation must be a finite unit quaternion");}}
   a=p.GetAttribute(TfToken("crs:scale"));if(a){if(a.GetTypeName()!=SdfValueTypeNames->Double3)throw std::runtime_error("Scale must be double3");for(auto t:Times(a)){GfVec3d v;if(a.Get(&v,t)&&(!Finite(v)||v[0]==0||v[1]==0||v[2]==0))throw std::runtime_error("Invalid scale");}}
  }
 }catch(const std::exception& e){error(p.GetPath(),e.what());}
 if(dependent){auto d=s->GetRootLayer()->GetCustomLayerData();auto it=d.find("geospatialResolutionRequired");if(it==d.end()||!it->second.IsHolding<bool>()||!it->second.Get<bool>())error(SdfPath::AbsoluteRootPath(),"Missing complete-asset dependency declaration");}
 return errors;
}
}
TF_REGISTRY_FUNCTION(UsdValidationRegistry){UsdValidationRegistry::GetInstance().RegisterPluginValidator(TfToken("candidateValidation:AuthoredGeospatial"),UsdValidateStageTaskFn(Check));}
