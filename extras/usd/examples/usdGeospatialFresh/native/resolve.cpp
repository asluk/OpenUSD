// New native implementation derived from authority/proposal.md, 2026-10-15.
// Uses USD Core value resolution and PROJ C directly. No Python placement call.
#include <pxr/pxr.h>
#include <pxr/base/plug/registry.h>
#include <pxr/base/js/json.h>
#include <pxr/base/gf/matrix4d.h>
#include <pxr/base/gf/quatd.h>
#include <pxr/base/gf/rotation.h>
#include <pxr/base/vt/dictionary.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usd/primRange.h>
#include <pxr/usd/usdGeom/xformable.h>
#include <pxr/usd/usdGeom/xformCache.h>
#include <pxr/usd/usdGeom/metrics.h>
#include <pxr/usd/usdGeom/mesh.h>
#include <pxr/usd/usdGeom/xform.h>
#include <pxr/usd/usdGeom/pointInstancer.h>
#include <pxr/usd/usdShade/materialBindingAPI.h>
#include <pxr/usd/sdf/assetPath.h>
#include <pxr/usd/sdf/copyUtils.h>
#include <proj.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <filesystem>
#include <iostream>
#include <map>
#include <memory>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>
PXR_NAMESPACE_USING_DIRECTIVE
using V=GfVec3d;using M=GfMatrix4d;using Q=GfQuatd;
const double PI=3.14159265358979323846;
void check(bool b,const std::string&s){if(!b)throw std::runtime_error(s);}
std::string readFile(const std::string&p){std::ifstream f(p,std::ios::binary);check(bool(f),"Cannot open "+p);return {std::istreambuf_iterator<char>(f),{}};}
double number(const JsValue&v){return v.IsInt()?double(v.GetInt64()):v.GetReal();}
V vector3(const JsValue&v){auto a=v.GetJsArray();check(a.size()==3,"Expected three components");return V(number(a[0]),number(a[1]),number(a[2]));}
JsValue jsonV(const V&v){return JsValue(JsArray{JsValue(v[0]),JsValue(v[1]),JsValue(v[2])});}
void finite(const V&v){for(int i=0;i<3;++i)check(std::isfinite(v[i]),"Non-finite coordinate or angle");}
std::string lower(std::string s){std::transform(s.begin(),s.end(),s.begin(),[](unsigned char c){return char(std::tolower(c));});return s;}
std::string upper(std::string s){std::transform(s.begin(),s.end(),s.begin(),[](unsigned char c){return char(std::toupper(c));});return s;}

// Decimal text manipulation is exact. No double parse/format in normalization.
std::string decimal(std::string s){
 bool neg=false;if(s[0]=='+'||s[0]=='-'){neg=s[0]=='-';s.erase(0,1);}
 int exp=0;auto e=s.find_first_of("eE");if(e!=std::string::npos){exp=std::stoi(s.substr(e+1));s=s.substr(0,e);}
 auto p=s.find('.');int dot=p==std::string::npos?int(s.size()):int(p);if(p!=std::string::npos)s.erase(p,1);dot+=exp;
 check(std::abs(dot)<1000000,"Decimal expansion exceeds implementation limit");
 if(dot<=0)s="0."+std::string(-dot,'0')+s;
 else if(dot>=int(s.size()))s+=std::string(dot-int(s.size()),'0');else s.insert(dot,1,'.');
 auto q=s.find('.');std::string a=s.substr(0,q),b=q==std::string::npos?"":s.substr(q+1);
 auto nz=a.find_first_not_of('0');a=nz==std::string::npos?"0":a.substr(nz);while(!b.empty()&&b.back()=='0')b.pop_back();
 s=a+(b.empty()?"":"."+b);return neg&&s!="0"?"-"+s:s;
}
std::string normalize(const std::string&s){
 static const std::regex lex(R"(\s+|"(?:[^"]|"")*"|[A-Za-z_][A-Za-z_0-9]*|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?|[\[\](),])");
 static const std::map<std::string,std::string> aliases={{"VERTICALCRS","VERTCRS"},{"PRIMEMERIDIAN","PRIMEM"},{"GEODETICCRS","GEODCRS"},{"GEOGRAPHICCRS","GEOGCRS"},{"PROJECTEDCRS","PROJCRS"},{"GEODETICDATUM","DATUM"},{"TRF","DATUM"},{"VERTICALDATUM","VDATUM"},{"VRF","VDATUM"},{"SPHEROID","ELLIPSOID"},{"PROJECTION","METHOD"},{"ENGINEERINGCRS","ENGCRS"},{"ENGINEERINGDATUM","EDATUM"},{"TIMEDATUM","TDATUM"},{"TEMPORALQUANTITY","TIMEUNIT"},{"VELOCITYGRID","MODEL"}};
 std::vector<std::string> tok;size_t pos=0;for(auto i=std::sregex_iterator(s.begin(),s.end(),lex);i!=std::sregex_iterator();++i){check(size_t(i->position())==pos,"Invalid WKT character");pos+=i->length();auto t=i->str();if(!std::isspace((unsigned char)t[0]))tok.push_back(t);}check(pos==s.size(),"Invalid WKT character");
 std::string out;std::vector<std::string> stack;std::string last;
 for(size_t i=0;i<tok.size();++i){auto t=tok[i];if(t[0]=='"')out+=t;
 else if(std::isdigit((unsigned char)t[0])||t[0]=='+'||t[0]=='-'||t[0]=='.')out+=decimal(t);
 else if(t=="["||t=="("){stack.push_back(last);out+='[';}
 else if(t=="]"||t==")"){check(!stack.empty(),"Unbalanced WKT");stack.pop_back();out+=']';}
 else if(t==",")out+=',';
 else if(i+1<tok.size()&&(tok[i+1]=="["||tok[i+1]=="(")){auto key=upper(t);auto it=aliases.find(key);if(it!=aliases.end())key=it->second;if(key=="UNIT"){check(!stack.empty(),"Unit context missing");if(stack.back()=="PRIMEM")key="ANGLEUNIT";else if(stack.back()=="ELLIPSOID")key="LENGTHUNIT";else {auto cs=out.rfind("CS[ellipsoidal,");auto ca=out.rfind("CS[Cartesian,");key=cs!=std::string::npos&&(ca==std::string::npos||cs>ca)?"ANGLEUNIT":"LENGTHUNIT";}}out+=key;last=key;}
 else {auto tlo=lower(t);static const std::map<std::string,std::string> mixed={{"cartesian","Cartesian"},{"geocentricx","geocentricX"},{"geocentricy","geocentricY"},{"geocentricz","geocentricZ"},{"temporalcount","temporalCount"},{"temporaldatetime","temporalDateTime"},{"temporalmeasure","temporalMeasure"},{"northnortheast","northNorthEast"},{"northeast","northEast"},{"eastnortheast","eastNorthEast"},{"eastsoutheast","eastSouthEast"},{"southeast","southEast"},{"southsoutheast","southSouthEast"},{"southsouthwest","southSouthWest"},{"southwest","southWest"},{"westsouthwest","westSouthWest"},{"westnorthwest","westNorthWest"},{"northwest","northWest"},{"northnorthwest","northNorthWest"}};auto m=mixed.find(tlo);out+=m==mixed.end()?tlo:m->second;}}
 check(stack.empty(),"Unbalanced WKT");return out;
}

struct PjDelete{void operator()(PJ*p)const{proj_destroy(p);}};using Pj=std::shared_ptr<PJ>;
Pj own(PJ*p){check(p!=nullptr,"Unavailable CRS or operation");return Pj(p,PjDelete{});}
struct Def{
 Pj pj;std::string wkt;std::vector<int> order;std::vector<double> unit;bool geographic=false,geocentric=false;int dim=0;
};
struct Engine{
 PJ_CONTEXT*ctx=proj_context_create();std::map<std::string,Def>defs;std::map<std::string,Pj>ops;JsArray reports;
 Engine(){proj_context_set_enable_network(ctx,0);}
 ~Engine(){ops.clear();defs.clear();proj_context_destroy(ctx);}
 void axes(PJ*p,std::vector<std::string>&dirs,std::vector<double>&units){
   if(proj_get_type(p)==PJ_TYPE_COMPOUND_CRS){for(int i=0;i<2;++i){auto sub=own(proj_crs_get_sub_crs(ctx,p,i));axes(sub.get(),dirs,units);}return;}
   auto cs=own(proj_crs_get_coordinate_system(ctx,p));int n=proj_cs_get_axis_count(ctx,cs.get());for(int i=0;i<n;++i){const char*dir=nullptr;double u=0;check(proj_cs_get_axis_info(ctx,cs.get(),i,nullptr,nullptr,&dir,&u,nullptr,nullptr,nullptr),"Unknown CRS axis");dirs.push_back(lower(dir));units.push_back(u);}
 }
 Def make(Pj p){Def d;d.pj=p;const char*w=proj_as_wkt(ctx,p.get(),PJ_WKT2_2019,nullptr);check(w,"Cannot serialize CRS");d.wkt=w;
   auto type=proj_get_type(p.get());d.geographic=type==PJ_TYPE_GEOGRAPHIC_2D_CRS||type==PJ_TYPE_GEOGRAPHIC_3D_CRS;d.geocentric=type==PJ_TYPE_GEOCENTRIC_CRS;
   std::vector<std::string>dirs;std::vector<double>u;axes(p.get(),dirs,u);d.dim=int(dirs.size());check(d.dim==2||d.dim==3,"Unsupported coordinate dimensions");
   std::vector<std::string>meaning=d.geocentric?std::vector<std::string>{"geocentricx","geocentricy","geocentricz"}:std::vector<std::string>{"east","north"};if(!d.geocentric&&d.dim==3)meaning.push_back("up");
   for(auto&m:meaning){auto it=std::find(dirs.begin(),dirs.end(),m);check(it!=dirs.end(),"Unsupported CRS direction");int i=int(it-dirs.begin());d.order.push_back(i);d.unit.push_back(u[i]);}return d;
 }
 Def parse(const std::string&w){check(upper(w).find("COORDINATEMETADATA")==std::string::npos,"Coordinate epochs outside initial scope");check(std::regex_search(upper(w),std::regex(R"(^\s*(GEOGCRS|GEOGRAPHICCRS|GEODCRS|GEODETICCRS|PROJCRS|PROJECTEDCRS|COMPOUNDCRS|BOUNDCRS|DERIVEDPROJCRS)\s*[\[(])")),"Supported complete WKT2 required");auto it=defs.find(w);if(it!=defs.end())return it->second;auto d=make(own(proj_create_from_wkt(ctx,w.c_str(),nullptr,nullptr,nullptr)));d.wkt=w;try{if(normalize(w)!=w)std::cerr<<"Validation warning: non-normal WKT spelling\n";}catch(const std::exception&){std::cerr<<"Validation warning: WKT normalization check unavailable\n";}defs[w]=d;return d;}
 Pj horizontal(const Def&d){if(proj_get_type(d.pj.get())==PJ_TYPE_COMPOUND_CRS)return own(proj_crs_get_sub_crs(ctx,d.pj.get(),0));return d.pj;}
 Def geo(const Def&d){std::string key="@geographic/"+d.wkt;if(defs.count(key))return defs.at(key);auto h=horizontal(d);auto geod=own(proj_crs_get_geodetic_crs(ctx,h.get()));auto datum=own(proj_crs_get_datum_forced(ctx,geod.get()));auto cs=own(proj_create_ellipsoidal_3D_cs(ctx,PJ_ELLPS3D_LATITUDE_LONGITUDE_HEIGHT,"degree",PI/180,"metre",1));auto result=make(own(proj_create_geographic_crs_from_datum(ctx,"Source geographic 3D",datum.get(),cs.get())));defs[key]=result;return result;}
 Def gc(const Def&d){std::string key="@geocentric/"+d.wkt;if(defs.count(key))return defs.at(key);auto h=horizontal(d);auto geod=own(proj_crs_get_geodetic_crs(ctx,h.get()));auto datum=own(proj_crs_get_datum_forced(ctx,geod.get()));auto result=make(own(proj_create_geocentric_crs_from_datum(ctx,"Associated geocentric",datum.get(),"metre",1)));defs[key]=result;return result;}
 V transform(const Def&s,const Def&d,V v){finite(v);check(s.dim==d.dim,"Missing height cannot be invented");if(s.wkt==d.wkt)return v;
   std::string key=s.wkt+"\n"+d.wkt;auto it=ops.find(key);if(it==ops.end()){const char* options[]={"ALLOW_BALLPARK=NO","ONLY_BEST=YES",nullptr};it=ops.emplace(key,own(proj_create_crs_to_crs_from_pj(ctx,s.pj.get(),d.pj.get(),nullptr,options))).first;}
   double a[4]={0,0,0,HUGE_VAL};for(int j=0;j<s.dim;++j)a[s.order[j]]=v[j];auto p=it->second.get();proj_errno_reset(p);auto z=proj_trans(p,PJ_FWD,proj_coord(a[0],a[1],a[2],a[3]));check(proj_errno(p)==0,"Coordinate operation failed or required grid unavailable");V out(0);for(int j=0;j<d.dim;++j)out[j]=z.v[d.order[j]];finite(out);
   auto used=proj_trans_get_last_used_operation(p);PJ* actual=used?used:p;const char*ps=proj_as_proj_string(ctx,actual,PJ_PROJ_5,nullptr);std::string pipeline=ps?ps:"unavailable";
   double accuracy=proj_coordoperation_get_accuracy(ctx,actual);if(used)proj_destroy(used);
   check(!std::regex_search(pipeline,std::regex(R"(\+(dx|dy|dz|drx|dry|drz|ds|t_epoch|dt)=)")),"Epoch-dependent operation outside initial scope");
   bool found=false;for(auto&r:reports)if(r.GetJsObject().at("pipeline").GetString()==pipeline)found=true;
   if(!found){JsObject r{{"pipeline",JsValue(pipeline)},{"accuracy_m",accuracy<0?JsValue():JsValue(accuracy)}};reports.emplace_back(r);}return out;
 }
};

bool direct(const UsdPrim&p){auto a=p.GetAppliedSchemas();return std::find(a.begin(),a.end(),TfToken("GeospatialCRSBindingAPI"))!=a.end();}
UsdPrim nearest(UsdPrim p){while(p&&!p.IsPseudoRoot()){if(direct(p))return p;p=p.GetParent();}return UsdPrim();}
template<class T>T attr(const UsdPrim&p,const char*name,const SdfValueTypeName&type,UsdTimeCode t,bool uniform=false){auto a=p.GetAttribute(TfToken(name));check(bool(a),std::string("Missing ")+name);check(a.GetTypeName()==type,std::string("Wrong type for ")+name);auto stack=a.GetPropertyStack(t);check(stack.empty()||stack.front()->GetTypeName()==type,std::string("Wrong authored type for ")+name);check((stack.empty()||stack.front()->GetVariability()==(uniform?SdfVariabilityUniform:SdfVariabilityVarying))&&a.GetVariability()==(uniform?SdfVariabilityUniform:SdfVariabilityVarying),std::string("Wrong variability for ")+name);if(uniform){std::vector<double>ts;a.GetTimeSamples(&ts);check(ts.empty()&&a.GetVariability()==SdfVariabilityUniform,std::string("Invalid uniform property ")+name);t=UsdTimeCode::Default();}T v;check(a.Get(&v,t),std::string("Blocked/unavailable ")+name);return v;}
Q angles(V a){finite(a);double h=a[0]*PI/360,p=a[1]*PI/360,r=a[2]*PI/360;return Q(cos(h),V(0,0,-sin(h)))*Q(cos(p),V(sin(p),0,0))*Q(cos(r),V(0,sin(r),0));}
struct Reader{
 UsdStageRefPtr stage;UsdTimeCode time;Engine engine;Def output,scene;bool yup,held;double mpu;
 std::map<std::tuple<std::string,double,double,double>,GfMatrix3d> jacobians;
 Reader(UsdStageRefPtr s,const std::string&w,UsdTimeCode t):stage(s),time(t){mpu=UsdGeomGetStageMetersPerUnit(s);check(mpu>0&&std::isfinite(mpu),"Invalid stage unit");yup=UsdGeomGetStageUpAxis(s)==TfToken("Y");held=s->GetInterpolationType()==UsdInterpolationTypeHeld;
   if(w.empty()){auto p=s->GetDefaultPrim();check(bool(p)&&(direct(p)||p.GetTypeName()==TfToken("CoordinateReferenceSystem")),"Output context unspecified");output=crs(p);}else output=engine.parse(w);scene=output.geographic?engine.gc(output):output;}
 Def crs(const UsdPrim&p){return engine.parse(attr<TfToken>(p,"crs:wkt",SdfValueTypeNames->Token,time,true).GetString());}
 V enu(V p){return (yup?V(p[0],-p[2],p[1]):p)*mpu;}
 V stageVector(V p){p/=mpu;return yup?V(p[0],p[2],-p[1]):p;}
 M local(const UsdPrim&p){M m(1);bool reset=false;UsdGeomXformable x(p);if(x)check(x.GetLocalTransformation(&m,&reset,time),"Invalid ordinary transform");return m;}
 Q orientation(const UsdPrim&p){auto a=p.GetAttribute(TfToken("crs:orientation"));if(!a||!a.HasAuthoredValueOpinion())return Q(1);check(a.GetTypeName()==SdfValueTypeNames->Double3,"Wrong orientation type");auto stack=a.GetPropertyStack(time);check(stack.empty()||stack.front()->GetTypeName()==SdfValueTypeNames->Double3,"Wrong authored orientation type");std::vector<double>ts;a.GetTimeSamples(&ts);auto get=[&](UsdTimeCode t){V v;check(a.Get(&v,t),"Unavailable orientation sample");return angles(v);};
   if(time.IsDefault()||ts.empty())return get(time);double t=time.GetValue();auto i=std::lower_bound(ts.begin(),ts.end(),t);if(i==ts.begin())return get(UsdTimeCode(*i));if(i==ts.end())return get(UsdTimeCode(ts.back()));if(*i==t)return get(time);double hi=*i,lo=*(i-1);Q q0=get(UsdTimeCode(lo));if(held)return q0;Q q1=get(UsdTimeCode(hi));double dot=GfDot(q0,q1);check(std::abs(dot)>1e-12,"Ambiguous 180-degree orientation; dot uncertainty 1e-12");if(dot<0)q1=-q1;return GfSlerp((t-lo)/(hi-lo),q0,q1).GetNormalized();}
 struct Basis{Def gc;V origin,e,n,u;};
 Basis basis(const Def&s,V pos){check(s.dim==3,"Model placement requires complete 3D CRS");check(!(s.geocentric&&pos[0]==0&&pos[1]==0),"Geocentric pole lacks attitude meridian");auto g=engine.geo(s);auto c=engine.gc(s);V ll=engine.transform(s,g,pos);double l=ll[0]*g.unit[0],p=ll[1]*g.unit[1];check(std::abs(p)<=PI/2+1e-12,"Latitude outside domain");return {c,engine.transform(s,c,pos),V(-sin(l),cos(l),0),V(-sin(p)*cos(l),-sin(p)*sin(l),cos(p)),V(cos(p)*cos(l),cos(p)*sin(l),sin(p))};}
 V embed(const Basis&b,V v){return b.origin+b.e*v[0]+b.n*v[1]+b.u*v[2];}
 V tangent(const Basis&b,V p){V v=p-b.origin;return V(GfDot(v,b.e),GfDot(v,b.n),GfDot(v,b.u));}
 V adjust(const Def&w,V p,const M&a,const V*origin){if(a==M(1))return p;
   if(w.geographic){check(origin,"Geographic measurement adjustment needs explicit Cartesian context");auto b=basis(w,*origin);V q=engine.transform(w,b.gc,p);q=embed(b,enu(a.Transform(stageVector(tangent(b,q)))));return engine.transform(b.gc,w,q);}
   V zero=origin?*origin:V(0),v=p-zero;for(int i=0;i<w.dim;++i)v[i]*=w.unit[i];if(w.dim==2)v[2]=0;v=enu(a.Transform(stageVector(v)));if(w.dim==2)check(std::abs(v[2])<1e-12,"2D adjustment has out-of-plane coupling");for(int i=0;i<w.dim;++i)v[i]/=w.unit[i];return v+zero;}
 V intrinsic(const UsdPrim&a,V x,const Def&s,V pos){auto b=basis(s,pos);M rotate(1);rotate.SetRotate(orientation(a));return engine.transform(b.gc,s,embed(b,rotate.TransformDir(enu(x))));}
 V model(const UsdPrim&a,V x,const Def&q,UsdPrim occurrence=UsdPrim(),bool reset=false){check(a.GetTypeName()!=TfToken("GeospatialDataSource"),"Measurement carrier is not model");check(bool(UsdGeomXformable(a)),"Model binding requires Xformable prim");auto s=crs(a);V pos=attr<V>(a,"crs:position",SdfValueTypeNames->Double3,time);finite(pos);V p=intrinsic(a,x,s,pos);auto enclosing=occurrence?occurrence:nearest(a.GetParent());auto w=enclosing?crs(enclosing):s;if(reset)return engine.transform(s,q,p);V origin=engine.transform(s,w,pos);p=engine.transform(s,w,p);return engine.transform(w,q,adjust(w,p,local(a),&origin));}
 void roles(UsdPrim p,const UsdPrim&a){while(p&&!p.IsPseudoRoot()){if(p!=a||p.GetTypeName()==TfToken("GeospatialDataSource"))for(auto name:{"crs:position","crs:orientation"}){auto v=p.GetAttribute(TfToken(name));check(!(v&&v.HasAuthoredValueOpinion()),std::string("Invalid placement role ")+name);}if(p==a)break;p=p.GetParent();}}
 V points(const UsdPrim&p,V x,const Def&q){check(bool(p),"Missing prim");auto a=nearest(p);auto cursor=p;while(cursor&&!cursor.IsPseudoRoot()){if(direct(cursor))break;if(cursor.GetTypeName()==TfToken("CoordinateReferenceSystem")){a=UsdPrim();break;}cursor=cursor.GetParent();}if(!a){auto c=p;while(c&&!c.IsPseudoRoot()&&c.GetTypeName()!=TfToken("CoordinateReferenceSystem"))c=c.GetParent();check(bool(c)&&!c.IsPseudoRoot(),"No binding or bake context");auto d=crs(c);check(!d.geographic,"Angular ordinary geometry invalid");UsdGeomXformCache cache(time);V v=enu(cache.GetLocalToWorldTransform(p).Transform(x));for(int i=0;i<d.dim;++i)v[i]/=d.unit[i];return engine.transform(d,q,v);}
   roles(p,a);M d(1);auto cur=p;bool reset=false;while(cur!=a){d=d*local(cur);UsdGeomXformable xf(cur);if(xf&&xf.GetResetXformStack()){reset=true;break;}cur=cur.GetParent();}return model(a,d.Transform(x),q,UsdPrim(),reset);}
 V scenePoint(const UsdPrim&p,V x,V origin=V(0)){check(scene.dim==3,"Scene geometry needs a complete 3D chart");V v=points(p,x,scene)-origin;for(int i=0;i<3;++i)v[i]*=scene.unit[i];return stageVector(v);}
 GfMatrix3d derivative(const UsdPrim&p,V x,const Def&chart){GfMatrix3d j(0);double h=.01;for(int i=0;i<3;++i){V e(0);e[i]=h;V v=(points(p,x+e,chart)-points(p,x-e,chart))/(2*h);for(int k=0;k<3;++k)j[i][k]=v[k];}return j;}
 V vectorMap(const UsdPrim&p,V at,V value,bool normal){auto key=std::make_tuple(p.GetPath().GetString(),at[0],at[1],at[2]);GfMatrix3d j(0);auto found=jacobians.find(key);if(found!=jacobians.end())j=found->second;else {double h=.01;for(int i=0;i<3;++i){V e(0);e[i]=h;V v=(scenePoint(p,at+e)-scenePoint(p,at-e))/(2*h);for(int k=0;k<3;++k)j[i][k]=v[k];}jacobians[key]=j;}if(normal){check(std::abs(j.GetDeterminant())>1e-14,"Singular normal transport");V n=value*j.GetInverse().GetTranspose();check(n.GetLength()>0,"Unavailable normal");return n.GetNormalized();}return value*j;}
 V inverse(const UsdPrim&p,V target,const Def&chart){auto c=engine.gc(chart);V wanted=engine.transform(chart,c,target),x(0);for(int it=0;it<25;++it){V f=points(p,x,c),r=wanted-f;if(r.GetLength()<1e-5)return x;auto j=derivative(p,x,c);double det=j.GetDeterminant();check(std::abs(det)>1e-14,"Singular required inverse");x+=r*j.GetInverse();}throw std::runtime_error("Inverse tolerance not established");}
 V instance(const UsdPrim&i,int index,const UsdPrim&p,V x){UsdGeomPointInstancer inst(i);VtMatrix4dArray mats;check(inst.ComputeInstanceTransformsAtTime(&mats,time,time,UsdGeomPointInstancer::ExcludeProtoXform,UsdGeomPointInstancer::IgnoreMask),"Invalid instancer inputs");auto mask=inst.ComputeMaskAtTime(time);check(index>=0&&size_t(index)<mats.size(),"Invalid instance index");check(mask.empty()||mask[index],"Masked instance");VtIntArray indices;check(inst.GetProtoIndicesAttr().Get(&indices,time),"Missing prototypes");SdfPathVector paths;inst.GetPrototypesRel().GetTargets(&paths);auto root=stage->GetPrimAtPath(paths[indices[index]]);auto bound=nearest(p);M d(1);auto cur=p;
   if(!bound||!bound.GetPath().HasPrefix(root.GetPath())){while(true){d=d*local(cur);if(cur==root)break;cur=cur.GetParent();}return points(i,mats[index].Transform(d.Transform(x)),output);}
   bool reset=false;while(cur!=bound){d=d*local(cur);UsdGeomXformable xf(cur);if(xf&&xf.GetResetXformStack()){reset=true;break;}cur=cur.GetParent();}auto enclosing=nearest(bound.GetParent());if(bound==root||!enclosing||!enclosing.GetPath().HasPrefix(root.GetPath()))enclosing=nearest(i);
   V b=model(bound,d.Transform(x),output,enclosing,reset);if(mats[index]==M(1))return b;auto context=nearest(i);check(bool(context),"Instance transport lacks model context");auto c=engine.gc(crs(context));V localPoint=inverse(i,engine.transform(output,c,b),c);return engine.transform(c,output,points(i,mats[index].Transform(localPoint),c));}
 std::string summary(const UsdPrim&p){auto dict=p.GetCustomData();auto it=dict.find("profilesInfo");if(it==dict.end()||!it->second.IsHolding<VtDictionary>())return "unknown";auto info=it->second.UncheckedGet<VtDictionary>();auto usages=info.find("capabilityUsages");bool hasUsage=usages!=info.end()&&usages->second.IsHolding<VtDictionary>();if(hasUsage){auto u=usages->second.UncheckedGet<VtDictionary>();auto a=u.find("usd.geospatial.crsResolution.v1");if(a!=u.end()&&a->second.IsHolding<std::string>()&&a->second.UncheckedGet<std::string>()=="hard")return "required";}
   auto apis=p.GetAppliedSchemas();bool claims=std::find(apis.begin(),apis.end(),TfToken("ClaimsAPI"))!=apis.end();auto compat=info.find("profileCompatibility");if(claims&&hasUsage&&compat!=info.end()&&compat->second.IsHolding<VtDictionary>()){auto c=compat->second.UncheckedGet<VtDictionary>();auto a=c.find("usd.geospatial.publication.v1");if(a!=c.end()&&a->second.IsArrayValued()&&a->second.GetArraySize()==0)return "known-none";}return "unknown";}
};

JsObject bake(Reader&r,const JsObject&request){
 auto destination=request.at("destination").GetString();auto paths=request.at("meshes").GetJsArray();check(!paths.empty(),"Bake needs explicit consumed mesh set");check(r.scene.dim==3,"Bake requires Cartesian 3D context");
 auto out=UsdStage::CreateNew(destination);check(bool(out),"Cannot create derived bake");UsdGeomSetStageMetersPerUnit(out,r.mpu);UsdGeomSetStageUpAxis(out,r.yup?TfToken("Y"):TfToken("Z"));out->SetTimeCodesPerSecond(r.stage->GetTimeCodesPerSecond());
 auto context=out->DefinePrim(SdfPath("/Context"),TfToken("CoordinateReferenceSystem"));out->SetDefaultPrim(context);context.CreateAttribute(TfToken("crs:wkt"),SdfValueTypeNames->Token,false,SdfVariabilityUniform).Set(TfToken(normalize(r.scene.wkt)));
 auto first=r.stage->GetPrimAtPath(SdfPath(paths[0].GetString()));V origin=r.points(first,V(0),r.scene);V stageOrigin=origin;for(int k=0;k<3;++k)stageOrigin[k]*=r.scene.unit[k];stageOrigin=r.stageVector(stageOrigin);
 auto offset=UsdGeomXform::Define(out,SdfPath("/Context/Origin"));offset.AddTranslateOp(UsdGeomXformOp::PrecisionDouble).Set(stageOrigin);
 auto flat=r.stage->Flatten();int index=0;JsArray info;std::map<SdfPath,SdfPath> materials;
 for(auto&pv:paths){auto source=r.stage->GetPrimAtPath(SdfPath(pv.GetString()));UsdGeomMesh mesh(source);check(bool(mesh),"Bake consumes meshes");for(auto&a:source.GetAttributes()){auto role=a.GetTypeName().GetRole();if(a.GetName().GetString().find("primvars:")==0&&(role==TfToken("Point")||role==TfToken("Vector")||role==TfToken("Normal")))throw std::runtime_error("Semantic geometric primvar export unsupported in this prototype");}SdfPath targetPath("/Context/Origin/Mesh"+std::to_string(index++));out->DefinePrim(targetPath,TfToken("Mesh"));check(SdfCopySpec(flat,source.GetPath(),out->GetRootLayer(),targetPath),"Copy unrelated mesh semantics failed");auto target=out->GetPrimAtPath(targetPath);UsdGeomXformable(target).ClearXformOpOrder();for(auto n:{"crs:position","crs:orientation","crs:wkt"})target.RemoveProperty(TfToken(n));target.RemoveAppliedSchema(TfToken("GeospatialCRSBindingAPI"));
   auto material=UsdShadeMaterialBindingAPI(source).ComputeBoundMaterial();if(material){auto original=material.GetPath();if(!materials.count(original)){SdfPath destination("/Context/Materials/Material"+std::to_string(materials.size()));out->DefinePrim(SdfPath("/Context/Materials"),TfToken("Scope"));check(SdfCopySpec(flat,original,out->GetRootLayer(),destination),"Material dependency copy failed");materials[original]=destination;}UsdShadeMaterialBindingAPI::Apply(target).Bind(UsdShadeMaterial(out->GetPrimAtPath(materials[original])));}UsdGeomMesh result(target);result.GetPointsAttr().Clear();auto translate=UsdGeomXformable(target).AddTranslateOp(UsdGeomXformOp::PrecisionDouble,TfToken("resolvedOffset"));std::vector<UsdTimeCode> schedule;if(request.count("times")){for(auto&t:request.at("times").GetJsArray())schedule.emplace_back(number(t));}else schedule.push_back(r.time);int count=0;
   for(auto&t:schedule){Reader at(r.stage,r.output.wkt,t);V meshOrigin=at.points(source,V(0),at.scene);V delta=meshOrigin-origin;for(int k=0;k<3;++k)delta[k]*=at.scene.unit[k];translate.Set(at.stageVector(delta),t);VtVec3fArray points;check(mesh.GetPointsAttr().Get(&points,t),"Unavailable mesh points");VtVec3fArray baked;V low(HUGE_VAL),high(-HUGE_VAL);for(auto&p:points){V z=at.scenePoint(source,V(p),meshOrigin);for(int k=0;k<3;++k){low[k]=std::min(low[k],z[k]);high[k]=std::max(high[k],z[k]);}baked.push_back(GfVec3f(z));}result.GetPointsAttr().Set(baked,t);result.GetExtentAttr().Set(VtVec3fArray{GfVec3f(low),GfVec3f(high)},t);count=int(baked.size());
     VtVec3fArray normals;if(mesh.GetNormalsAttr().Get(&normals,t)&&!normals.empty()){VtIntArray counts,indices;mesh.GetFaceVertexCountsAttr().Get(&counts,t);mesh.GetFaceVertexIndicesAttr().Get(&indices,t);auto interpolation=mesh.GetNormalsInterpolation();VtVec3fArray transformed;int corner=0;for(int face=0;face<int(counts.size());++face)for(int k=0;k<counts[face];++k){int vertex=indices[corner];int ni=interpolation==TfToken("constant")?0:interpolation==TfToken("uniform")?face:interpolation==TfToken("faceVarying")?corner:vertex;check(ni<int(normals.size()),"Invalid normal interpolation");transformed.push_back(GfVec3f(at.vectorMap(source,V(points[vertex]),V(normals[ni]),true)));++corner;}result.GetNormalsAttr().Set(transformed,t);result.SetNormalsInterpolation(TfToken("faceVarying"));}
   }info.emplace_back(JsObject{{"source",JsValue(pv.GetString())},{"baked",JsValue(targetPath.GetString())},{"points",JsValue(count)}});
 }
 context.AddAppliedSchema(TfToken("ClaimsAPI"));VtDictionary compatibility{{"usd.geospatial.publication.v1",VtValue(VtStringArray())}};VtDictionary profiles{{"capabilityUsages",VtValue(VtDictionary())},{"profileCompatibility",VtValue(compatibility)}};context.SetCustomDataByKey(TfToken("profilesInfo"),VtValue(profiles));out->GetRootLayer()->Save();return {{"success",JsValue(true)},{"destination",JsValue(destination)},{"origin",jsonV(origin)},{"meshes",JsValue(info)},{"coverage",JsValue("finite points and resulting polygonal geometry only")}};
}

int main(int argc,char**argv){
 try{check(argc==4,"Usage: resolve REQUEST.json RESULT.json SCHEMA_DIR");PlugRegistry::GetInstance().RegisterPlugins(argv[3]);auto request=JsParseString(readFile(argv[1])).GetJsObject();auto stage=UsdStage::Open(request.at("stage").GetString(),request.count("load_none")&&request.at("load_none").GetBool()?UsdStage::LoadNone:UsdStage::LoadAll);check(bool(stage),"Cannot open USD stage");if(request.count("held")&&request.at("held").GetBool())stage->SetInterpolationType(UsdInterpolationTypeHeld);
 std::string w=request.count("output_wkt")?request.at("output_wkt").GetString():"";UsdTimeCode time=request.count("time")?UsdTimeCode(number(request.at("time"))):UsdTimeCode::Default();Reader r(stage,w,time);JsArray results;
 for(auto&value:request.at("queries").GetJsArray()){auto q=value.GetJsObject();JsObject result;try{auto p=stage->GetPrimAtPath(SdfPath(q.at("prim").GetString()));std::string kind=q.count("kind")?q.at("kind").GetString():"points";result["success"]=JsValue(true);
   if(kind=="bake")result=bake(r,q);
   else if(kind=="summary"){result["state"]=JsValue(r.summary(p));result["payload_loaded"]=JsValue(p.IsLoaded());}
   else if(kind=="continuous_bound")throw std::runtime_error("Continuous-domain bound unsupported without certificate");
   else if(kind=="normalize"){r.engine.parse(q.at("wkt").GetString());result["wkt"]=JsValue(normalize(q.at("wkt").GetString()));}
   else if(kind=="measurement"){
     check(p.GetTypeName()==TfToken("GeospatialDataSource")&&direct(p),"External domain needs directly bound carrier");r.roles(p,p);
     auto raw=JsParseString(readFile(q.at("decoded").GetString())).GetJsObject();auto asset=attr<SdfAssetPath>(p,"data:asset",SdfValueTypeNames->Asset,time,true);check(!asset.GetResolvedPath().empty(),"Dataset asset unavailable");check(lower(std::filesystem::weakly_canonical(asset.GetResolvedPath()).generic_string())==lower(std::filesystem::weakly_canonical(raw.at("asset").GetString()).generic_string()),"Decoder dataset asset association mismatch");
     for(auto key:{"format","field","domain"}){const char*name=std::string(key)=="domain"?"data:coordinateDomain":std::string(key)=="format"?"data:format":"data:field";std::string val=std::string(key)=="format"?attr<TfToken>(p,name,SdfValueTypeNames->Token,time,true).GetString():attr<std::string>(p,name,SdfValueTypeNames->String,time,true);check(raw.at(key).GetString()==val,"Native decoder association mismatch");}
     auto source=r.crs(p);auto decoded=r.engine.parse(raw.at("source_crs").GetString());check(proj_is_equivalent_to_with_ctx(r.engine.ctx,source.pj.get(),decoded.pj.get(),PJ_COMP_EQUIVALENT),"Decoder/WKT mismatch");auto parent=nearest(p.GetParent());auto work=parent?r.crs(parent):source;JsArray rows;
     for(auto&v:raw.at("samples").GetJsArray()){auto row=v.GetJsObject();auto nums=row.at("coordinates").GetJsArray();check(int(nums.size())==source.dim,"Native sample dimension mismatch");V x(0);for(int j=0;j<source.dim;++j)x[j]=number(nums[j]);x=r.engine.transform(source,work,x);x=r.adjust(work,x,r.local(p),nullptr);x=r.engine.transform(work,r.output,x);JsArray converted;for(int j=0;j<r.output.dim;++j)converted.emplace_back(x[j]);row["resolved_coordinates"]=JsValue(converted);rows.emplace_back(row);}result["samples"]=JsValue(rows);
   }
   else {JsArray points;for(auto&pv:q.at("points").GetJsArray()){V x(0),z;auto components=pv.GetJsArray();int expected=kind=="coordinate"?r.crs(p).dim:3;check(int(components.size())==expected,"Coordinate dimensionality mismatch");for(int j=0;j<expected;++j)x[j]=number(components[j]);if(kind=="normal"||kind=="vector")z=r.vectorMap(p,vector3(q.at("at")),x,kind=="normal");else if(kind=="coordinate")z=r.engine.transform(r.crs(p),r.output,x);else if(kind=="inverse")z=r.inverse(p,x,r.output);else if(kind=="instance")z=r.instance(stage->GetPrimAtPath(SdfPath(q.at("instancer").GetString())),q.at("index").GetInt(),p,x);else if(kind=="scene")z=r.scenePoint(p,x);else z=r.points(p,x,r.output);if(kind=="coordinate"&&r.output.dim==2)points.emplace_back(JsArray{JsValue(z[0]),JsValue(z[1])});else points.push_back(jsonV(z));}result["points"]=JsValue(points);}
 }catch(const std::exception&e){result=JsObject{{"success",JsValue(false)},{"error",JsValue(e.what())}};}results.emplace_back(result);}
 JsObject out{{"results",JsValue(results)},{"coordinate_crs",JsValue(r.output.wkt)},{"scene_chart",JsValue(r.scene.wkt)},{"operations",JsValue(r.engine.reports)},{"continuous_bound_certified",JsValue(false)}};std::ofstream file(argv[2]);JsWriteToStream(JsValue(out),file);return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
