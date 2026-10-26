// Fresh translation of the frozen proposal, 23 October 2026.
// No previous geospatial C++ implementation or generated expectations used.
#include <pxr/pxr.h>
#include <pxr/base/js/json.h>
#include <pxr/base/plug/registry.h>
#include <pxr/base/gf/matrix3d.h>
#include <pxr/base/gf/matrix4d.h>
#include <pxr/base/gf/quatd.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdProfiles/claimsAPI.h>
#include <pxr/usd/usdProfiles/profileRegistry.h>
#include <pxr/usd/usd/primRange.h>
#include <pxr/usd/usdGeom/xformCache.h>
#include <pxr/usd/usdGeom/xformable.h>
#include <pxr/usd/usdGeom/metrics.h>
#include <pxr/usd/usdGeom/pointInstancer.h>
#include <proj.h>
#include <proj_experimental.h>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <cmath>
#include <algorithm>
#include <stdexcept>
#include <sstream>
#include <iomanip>
#include <regex>
#include <set>
PXR_NAMESPACE_USING_DIRECTIVE
using J=JsValue; using O=JsObject;using L=JsArray;using V=GfVec3d;using M=GfMatrix4d;
L diagnostics;
void need(bool b,const std::string&s){if(!b)throw std::runtime_error(s);}
double number(const J&j){return j.IsReal()?j.GetReal():double(j.GetInt64());}
const J& at(const J&j,const std::string&k){return j.GetJsObject().at(k);}
bool has(const J&j,const std::string&k){return j.IsObject()&&j.GetJsObject().count(k);}
V vec(const J&j){auto a=j.GetJsArray();need(a.size()==3,"three coordinates required");return V(number(a[0]),number(a[1]),number(a[2]));}
J json(V v){return J(L{J(v[0]),J(v[1]),J(v[2])});}
void finite(V v){for(int i=0;i<3;i++)need(std::isfinite(v[i]),"non-finite placement or coordinate");}
std::string decimal(std::string s){bool neg=s[0]=='-';if(s[0]=='+'||neg)s.erase(0,1);int exp=0;auto e=s.find_first_of("eE");if(e!=s.npos){exp=std::stoi(s.substr(e+1));s=s.substr(0,e);}auto dot=s.find('.');int digits=int(dot==s.npos?s.size():dot)+exp;if(dot!=s.npos)s.erase(dot,1);if(digits<=0)s="0."+std::string(-digits,'0')+s;else if(digits>=int(s.size()))s+=std::string(digits-int(s.size()),'0');else s.insert(digits,".");while(s.size()>1&&s[0]=='0'&&s[1]!='.')s.erase(0,1);if(s.find('.')!=s.npos){while(s.back()=='0')s.pop_back();if(s.back()=='.')s.pop_back();}return s=="0"?s:neg?"-"+s:s;}
std::string normal(const std::string&s){static const std::regex token(R"wkt(\s+|"(?:[^"]|"")*"|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[A-Za-z_][A-Za-z_0-9]*|[\[\](),])wkt");static const std::map<std::string,std::string> enums={{"cartesian","Cartesian"},{"ellipsoidal","ellipsoidal"},{"vertical","vertical"},{"spherical","spherical"},{"parametric","parametric"},{"temporal","temporal"},{"east","east"},{"north","north"},{"up","up"},{"geocentricx","geocentricX"},{"geocentricy","geocentricY"},{"geocentricz","geocentricZ"}};std::string out;size_t end=0;for(std::sregex_iterator i(s.begin(),s.end(),token),last;i!=last;++i){need(size_t(i->position())==end,"invalid WKT lexical character");auto t=i->str();end=i->position()+t.size();if(isspace((unsigned char)t[0]))continue;if(t[0]=='"')out+=t;else if(t=="("||t=="[")out+='[';else if(t==")"||t=="]")out+=']';else if(t==",")out+=t;else if(isdigit((unsigned char)t[0])||t[0]=='+'||t[0]=='-'||t[0]=='.')out+=decimal(t);else{std::string lower=t;std::transform(lower.begin(),lower.end(),lower.begin(),[](unsigned char c){return char(tolower(c));});auto e=enums.find(lower);if(e!=enums.end())out+=e->second;else{std::transform(t.begin(),t.end(),t.begin(),[](unsigned char c){return char(toupper(c));});out+=t;}}}need(end==s.size(),"invalid WKT trailing text");return out;}
struct P { PJ*p=nullptr;P(){}explicit P(PJ*q):p(q){}~P(){if(p)proj_destroy(p);}P(const P&)=delete;};
using Ptr=std::shared_ptr<P>;
struct Engine {
 PJ_CONTEXT*c=proj_context_create();std::map<std::pair<PJ*,PJ*>,Ptr> cache;std::map<std::string,std::shared_ptr<void>> models;L operations;std::set<std::string> seenOperations;
 Engine(){proj_context_set_enable_network(c,0);if(auto r=getenv("GEOSPATIAL_RESOURCE_DIR")){std::vector<std::string> a={r}; if(auto d=getenv("PROJ_DATA"))a.push_back(d);std::vector<const char*> b;for(auto&x:a)b.push_back(x.c_str());proj_context_set_search_paths(c,int(b.size()),b.data());}}
 ~Engine(){models.clear();cache.clear();proj_context_destroy(c);}
 Ptr parse(const std::string&s){need(!s.empty(),"missing WKT");need(s.find("COORDINATEMETADATA")==std::string::npos,"coordinate epochs deferred");auto p=std::make_shared<P>(proj_create(c,s.c_str()));need(p->p,"invalid or unsupported WKT");return p;}
 std::string wkt(Ptr p){auto s=proj_as_wkt(c,p->p,PJ_WKT2_2019,nullptr);need(s,"cannot serialize CRS");return s;}
 J object(Ptr p){auto s=proj_as_projjson(c,p->p,nullptr);need(s,"cannot inspect CRS");return JsParseString(s);}
 Ptr altered(Ptr p,bool cart){Ptr g=std::make_shared<P>(proj_crs_get_geodetic_crs(c,p->p));need(g->p,"CRS has no geodetic relation");O o=object(g).GetJsObject();o.erase("id");o["type"]=J(cart?"GeodeticCRS":"GeographicCRS");L axes;
   if(cart){for(auto a:{"X","Y","Z"})axes.push_back(J(O{{"name",J(std::string("Geocentric ")+a)},{"abbreviation",J(a)},{"direction",J(std::string("geocentric")+a)},{"unit",J("metre")}}));}
   else {axes={J(O{{"name",J("Latitude")},{"abbreviation",J("Lat")},{"direction",J("north")},{"unit",J("degree")}}),J(O{{"name",J("Longitude")},{"abbreviation",J("Lon")},{"direction",J("east")},{"unit",J("degree")}}),J(O{{"name",J("Height")},{"abbreviation",J("h")},{"direction",J("up")},{"unit",J("metre")}})};}
   o["coordinate_system"]=J(O{{"subtype",J(cart?"Cartesian":"ellipsoidal")},{"axis",J(axes)}});return parse(JsWriteToString(J(o)));}
 V convert(V p,Ptr a,Ptr b){finite(p);auto key=std::make_pair(a->p,b->p);if(!cache.count(key)){const char*opts[]={"ALLOW_BALLPARK=NO","ONLY_BEST=YES",nullptr};P raw(proj_create_crs_to_crs_from_pj(c,a->p,b->p,nullptr,opts));need(raw.p,"required operation unavailable");cache[key]=std::make_shared<P>(proj_normalize_for_visualization(c,raw.p));need(cache[key]->p,"axis adaptation failed");}
   auto op=cache[key]->p;proj_errno_reset(op);auto r=proj_trans(op,PJ_FWD,proj_coord(p[0],p[1],p[2],HUGE_VAL));need(!proj_errno(op),"coordinate operation or required grid failed");V out(r.xyz.x,r.xyz.y,r.xyz.z);finite(out);
   P used(proj_trans_get_last_used_operation(op));PJ*actual=used.p?used.p:op;const char*s=proj_as_proj_string(c,actual,PJ_PROJ_5,nullptr);double acc=proj_coordoperation_get_accuracy(c,actual);static const std::regex timeOperation(R"((?:^|\s)\+?(?:proj=(?:deformation|defmodel|velocitygrid)|d(?:x|y|z|rx|ry|rz|s)=))");need(!s||!std::regex_search(s,timeOperation),"coordinate-epoch-dependent operation outside initial scope");
   J report(O{{"pipeline",J(s?s:"")},{"description",J(proj_get_name(actual)?proj_get_name(actual):"")},{"accuracy_m",acc<0?J():J(acc)}});
   if(seenOperations.insert(JsWriteToString(report)).second)operations.push_back(report);
   return out;
 }
};
struct CRSInfo {
 Engine&e;Ptr crs;bool geographic=false,geocentric=false,assumed=false;V units{1,1,1};std::vector<std::string> names;
 CRSInfo(Engine&engine,Ptr p,bool model):e(engine),crs(p){read();if(model&&names.size()==2){assumed=true;diagnostics.push_back(J("missing vertical reference: assuming EGM2008 height (EPSG:3855)"));double u=geographic?1:units[0];std::string un=geographic?"metre":names[0];std::ostringstream v;v<<std::setprecision(17)<<"COMPOUNDCRS[\"Horizontal with assumed EGM2008\","<<e.wkt(crs)<<",VERTCRS[\"EGM2008 height\",VDATUM[\"EGM2008 geoid\"],CS[vertical,1],AXIS[\"Gravity-related height\",up,LENGTHUNIT[\""<<un<<"\","<<u<<"]]]]";crs=e.parse(v.str());read();}need(!model||names.size()==3,"model requires complete 3D CRS");}
 void read(){names.clear();P cs(proj_crs_get_coordinate_system(e.c,crs->p));
   if(!cs.p){P h(proj_crs_get_sub_crs(e.c,crs->p,0));need(h.p,"CRS has no coordinate system");P s(proj_crs_get_coordinate_system(e.c,h.p));need(s.p,"horizontal system unavailable");cs.p=s.p;s.p=nullptr;}
   auto ty=proj_get_type(crs->p);geographic=ty==PJ_TYPE_GEOGRAPHIC_2D_CRS||ty==PJ_TYPE_GEOGRAPHIC_3D_CRS;geocentric=ty==PJ_TYPE_GEOCENTRIC_CRS;
   int count=proj_cs_get_axis_count(e.c,cs.p);
   for(int i=0;i<count;i++){const char*direction=nullptr,*unit=nullptr;double factor=1;proj_cs_get_axis_info(e.c,cs.p,i,nullptr,nullptr,&direction,&factor,&unit,nullptr,nullptr);std::string d=direction?direction:"";need(d=="east"||d=="north"||d=="up"||d=="geocentricX"||d=="geocentricY"||d=="geocentricZ","unsupported component directions");int slot=d=="east"||d=="geocentricX"?0:d=="north"||d=="geocentricY"?1:2;units[slot]=factor;names.push_back(unit?unit:"");}
   if(ty==PJ_TYPE_COMPOUND_CRS){P h(proj_crs_get_sub_crs(e.c,crs->p,0));auto ht=proj_get_type(h.p);geographic=ht==PJ_TYPE_GEOGRAPHIC_2D_CRS||ht==PJ_TYPE_GEOGRAPHIC_3D_CRS;P v(proj_crs_get_sub_crs(e.c,crs->p,1));P vc(proj_crs_get_coordinate_system(e.c,v.p));const char*unit=nullptr;double f=1;proj_cs_get_axis_info(e.c,vc.p,0,nullptr,nullptr,nullptr,&f,&unit,nullptr,nullptr);units[2]=f;names.push_back(unit?unit:"");}
 }
 J height(){std::string kind,ref,unit;J reference;
   if(geocentric||names.size()<3){kind="none";}
   else if(proj_get_type(crs->p)==PJ_TYPE_COMPOUND_CRS){kind="gravityRelated";P v(proj_crs_get_sub_crs(e.c,crs->p,1));const char*auth=proj_get_id_auth_name(v.p,0),*code=proj_get_id_code(v.p,0);reference=J(assumed?"EPSG:3855":auth&&code?std::string(auth)+":"+code:proj_get_name(v.p));unit=names.back();}
   else{kind="ellipsoidal";P ell(proj_get_ellipsoid(e.c,crs->p));P dat(proj_crs_get_datum_forced(e.c,crs->p));reference=J(O{{"ellipsoid",J(ell.p?proj_get_name(ell.p):"")},{"datum",J(dat.p?proj_get_name(dat.p):"")}});unit=names.back();}
   return J(O{{"heightModel",J(kind)},{"heightReference",reference},{"heightUnit",unit.empty()?J():J(unit)},{"heightReferenceSource",J(assumed?"assumed":"declared")}});
 }
};
bool direct(UsdPrim p){auto a=p.GetAppliedSchemas();return std::find(a.begin(),a.end(),TfToken("GeospatialCRSBindingAPI"))!=a.end();}
UsdPrim bound(UsdPrim p){while(p&&!p.IsPseudoRoot()){if(direct(p))return p;p=p.GetParent();}throw std::runtime_error("content outside CRS binding");}
template<class T>T val(UsdPrim p,const char*n,UsdTimeCode t,const SdfValueTypeName&type){auto a=p.GetAttribute(TfToken(n));T v;need(a&&a.GetTypeName()==type&&a.Get(&v,t),std::string("missing, blocked or wrongly typed ")+n);return v;}
std::string wkt(UsdPrim p){auto a=p.GetAttribute(TfToken("crs:wkt"));std::vector<double>s;a.GetTimeSamples(&s);need(a&&a.GetVariability()==SdfVariabilityUniform&&s.empty(),"invalid uniform WKT value source");auto w=val<TfToken>(p,"crs:wkt",UsdTimeCode::Default(),SdfValueTypeNames->Token).GetString();if(normal(w)!=w)diagnostics.push_back(J("non-normal WKT spelling"));return w;}
void roles(UsdPrim p){for(auto n:{"crs:position","crs:orientation"}){auto a=p.GetAttribute(TfToken(n));need(!a||!a.HasAuthoredValueOpinion()||(direct(p)&&p.GetTypeName()!=TfToken("GeospatialDataSource")),"placement field in invalid role");}}
M local(UsdPrim p,UsdTimeCode t){M m(1);bool reset=false;UsdGeomXformable x(p);if(x)need(x.GetLocalTransformation(&m,&reset,t),"ordinary transform unavailable");return m;}
GfMatrix3d basis(double lon,double lat){const double pi=acos(-1.);lon*=pi/180;lat*=pi/180;double sl=sin(lon),cl=cos(lon),sb=sin(lat),cb=cos(lat);return GfMatrix3d(-sl,cl,0,-sb*cl,-sb*sl,cb,cb*cl,cb*sl,sb);}
GfMatrix3d axes(UsdStageRefPtr s){double u=UsdGeomGetStageMetersPerUnit(s);need(std::isfinite(u)&&u>0,"invalid stage unit");GfMatrix3d b=UsdGeomGetStageUpAxis(s)==TfToken("Z")?GfMatrix3d(1):GfMatrix3d(1,0,0,0,0,1,0,-1,0);return b*u;}
GfQuatd pose(V a){finite(a);const double f=acos(-1.)/360;GfQuatd h(cos(a[0]*f),V(0,0,-sin(a[0]*f))),p(cos(a[1]*f),V(sin(a[1]*f),0,0)),r(cos(a[2]*f),V(0,sin(a[2]*f),0));return h*p*r;}
GfMatrix3d attitude(UsdPrim p,UsdTimeCode t){auto a=p.GetAttribute(TfToken("crs:orientation"));if(!a||!a.HasAuthoredValueOpinion())return GfMatrix3d(1);auto at=[&](UsdTimeCode q){return pose(val<V>(p,"crs:orientation",q,SdfValueTypeNames->Double3));};std::vector<double>s;a.GetTimeSamples(&s);GfQuatd q;
 if(t.IsDefault()||s.empty())q=at(t);else{double x=t.GetValue();auto i=std::upper_bound(s.begin(),s.end(),x);if(i==s.begin())q=at(s.front());else if(i==s.end()||*(i-1)==x||p.GetStage()->GetInterpolationType()==UsdInterpolationTypeHeld)q=at(*(i-1));else{auto u=at(*(i-1)),v=at(*i);double d=u.GetReal()*v.GetReal()+GfDot(u.GetImaginary(),v.GetImaginary());need(abs(d)>1e-12,"ambiguous 180-degree orientation arc; rotational uncertainty 2e-12 radians");if(d<0){v=-v;d=-d;}double f=(x-*(i-1))/(*i-*(i-1));if(d>1-1e-12)q=(u*(1-f)+v*f).GetNormalized();else{double theta=acos(std::min(1.,d));q=(u*sin((1-f)*theta)+v*sin(f*theta))*(1/sin(theta));}}}
 return GfMatrix3d(q);
}
V multiply(V a,V b){return V(a[0]*b[0],a[1]*b[1],a[2]*b[2]);}V divide(V a,V b){return V(a[0]/b[0],a[1]/b[1],a[2]/b[2]);}
struct Model {
 Engine&e;UsdPrim p;UsdTimeCode t;CRSInfo source;std::unique_ptr<CRSInfo>work;Ptr geo,ecef,wgeo,wecef;V position,origin,worigin,weorigin;GfMatrix3d E,R,U,WE;M A;bool chartReady=false;
 Model(Engine&en,UsdPrim prim,UsdTimeCode time,Ptr overrideW=nullptr):e(en),p(prim),t(time),source(e,e.parse(wkt(p)),true){roles(p);need(bool(UsdGeomXformable(p)),"direct model binding requires Xformable content");need(p.GetTypeName()!=TfToken("GeospatialDataSource"),"model query on measurement carrier");position=val<V>(p,"crs:position",t,SdfValueTypeNames->Double3);finite(position);need(!source.geocentric||position[0]!=0||position[1]!=0,"geocentric pole has no attitude meridian");geo=e.altered(source.crs,false);ecef=e.altered(source.crs,true);V llh=e.convert(position,source.crs,geo);origin=e.convert(llh,geo,ecef);E=basis(llh[0],llh[1]);R=attitude(p,t);U=axes(p.GetStage());A=local(p,t);
  auto par=p.GetParent();while(par&&!par.IsPseudoRoot()&&!direct(par))par=par.GetParent();Ptr W=overrideW?overrideW:par&&direct(par)?e.parse(wkt(par)):source.crs;work=std::make_unique<CRSInfo>(e,W,true);} void prepare(){if(chartReady)return;chartReady=true;worigin=e.convert(origin,ecef,work->crs);if(work->geographic){wgeo=e.altered(work->crs,false);wecef=e.altered(work->crs,true);V l=e.convert(worigin,work->crs,wgeo);WE=basis(l[0],l[1]);weorigin=e.convert(worigin,work->crs,wecef);}}
 V chart(V p){prepare();if(work->geographic)return (e.convert(p,work->crs,wecef)-weorigin)*WE.GetInverse()*U.GetInverse();return multiply(p-worigin,work->units)*U.GetInverse();}
 V unchart(V p){prepare();if(work->geographic)return e.convert(weorigin+p*U*WE,wecef,work->crs);return worigin+divide(p*U,work->units);}
 V forward(V x,Ptr q,M D=M(1),bool reset=false){V b=origin+D.Transform(x)*U*R*E;if(reset||A==M(1))return e.convert(b,ecef,q);V w=e.convert(b,ecef,work->crs);return e.convert(unchart(A.Transform(chart(w))),work->crs,q);}
 V inverse(V x,Ptr q,M D=M(1),bool reset=false){V w=e.convert(x,q,work->crs);if(!reset){need(abs(A.GetDeterminant())>1e-15,"singular required inverse");w=unchart(A.GetInverse().Transform(chart(w)));}need(abs(D.GetDeterminant())>1e-15,"singular instancer inverse");V local=(e.convert(w,work->crs,ecef)-origin)*E.GetInverse()*R.GetInverse()*U.GetInverse();return D.GetInverse().Transform(local);}
};
V evaluate(Engine&e,UsdPrim p,V x,Ptr out,UsdTimeCode t){roles(p);auto q=p;while(q&&!q.IsPseudoRoot()){if(direct(q))break;if(q.GetTypeName()==TfToken("CoordinateReferenceSystem")){CRSInfo c(e,e.parse(wkt(q)),false);need(!c.geographic,"angular ordinary geometry unsupported");V world=UsdGeomXformCache(t).GetLocalToWorldTransform(p).Transform(x)*axes(p.GetStage());return e.convert(divide(world,c.units),c.crs,out);}q=q.GetParent();}
 auto anchor=bound(p);for(auto r=p;r!=anchor;r=r.GetParent())roles(r);auto key=anchor.GetPath().GetString();if(!e.models.count(key))e.models[key]=std::make_shared<Model>(e,anchor,t);auto cached=std::static_pointer_cast<Model>(e.models[key]);bool reset=false;M D=UsdGeomXformCache(t).ComputeRelativeTransform(p,anchor,&reset);return cached->forward(x,out,D,reset);}
int main(int argc,char**argv){try{need(argc==4,"resolve request.json result.json schema-directory");PlugRegistry::GetInstance().RegisterPlugins(argv[3]);std::ifstream f(argv[1]);J req=JsParseStream(f);need(req.IsObject(),"invalid request");Engine e;L result;O report; if(has(req,"publishStage")||has(req,"profilesStage")){auto stage=UsdStage::Open(at(req,has(req,"publishStage")?"publishStage":"profilesStage").GetString(),UsdStage::LoadNone);need(bool(stage),"Profiles stage unavailable");auto prim=stage->GetDefaultPrim();auto claims=UsdProfilesClaimsAPI(prim);if(has(req,"publishStage")){claims=UsdProfilesClaimsAPI::Apply(prim);auto usages=claims.GetCapabilityUsages();usages.erase("usd.geospatial.crsResolution.v1");if(at(req,"requires").GetBool())usages["usd.geospatial.crsResolution.v1"]=VtValue(TfToken("hard"));claims.SetCapabilityUsages(usages);if(at(req,"complete").GetBool())claims.SetProfileCompatible(TfToken("usd.geospatial.publication.v1"));stage->GetRootLayer()->Save();}auto profiles=claims.GetCompatibleProfiles();L names;for(auto p:profiles)names.push_back(J(p.GetString()));L implied;for(auto cap:UsdProfileRegistry::GetSchemaImpliedCapabilities(TfType::FindByName("UsdGeospatialCRSBindingAPI")))implied.push_back(J(cap.GetString()));O out{{"bindingImpliedCapabilities",J(implied)},{"success",J(true)},{"hardUsage",J(claims.GetCapabilityUsage(TfToken("usd.geospatial.crsResolution.v1")).GetString())},{"profiles",J(names)},{"loadedPayloads",J(int(stage->GetLoadSet().size()))},{"ClaimsAPI",J(bool(claims))}};std::ofstream dest(argv[2]);JsWriteToStream(J(out),dest);return 0;} Ptr output=e.parse(at(req,"output").GetString());
 if(has(req,"coordinateSource")){CRSInfo source(e,e.parse(at(req,"coordinateSource").GetString()),has(req,"modelFallback")&&at(req,"modelFallback").GetBool());for(auto&j:at(req,"points").GetJsArray())result.push_back(json(e.convert(vec(j),source.crs,output)));report["sourceHeight"]=source.height();}
 else {auto stage=UsdStage::Open(at(req,"stage").GetString());need(bool(stage),"cannot open stage");auto prim=stage->GetPrimAtPath(SdfPath(at(req,"prim").GetString()));need(bool(prim),"missing prim");UsdTimeCode time=has(req,"time")?UsdTimeCode(number(at(req,"time"))):UsdTimeCode::Default();auto points=at(req,"points").GetJsArray();
   if(has(req,"instance")){auto inst=stage->GetPrimAtPath(SdfPath(at(req,"instancer").GetString()));UsdGeomPointInstancer pi(inst);int index=at(req,"instance").GetInt();VtMatrix4dArray matrices;need(pi.ComputeInstanceTransformsAtTime(&matrices,time,time,UsdGeomPointInstancer::ExcludeProtoXform,UsdGeomPointInstancer::IgnoreMask),"instance transforms unavailable");auto mask=pi.ComputeMaskAtTime(time);need(mask.empty()||mask.at(index),"masked instance");M I=matrices[index];auto anchor=bound(inst);Model H(e,anchor,time);auto fixed=e.altered(H.source.crs,true);bool ir=false;M D=UsdGeomXformCache(time).ComputeRelativeTransform(inst,anchor,&ir);SdfPathVector targets;pi.GetPrototypesRel().GetTargets(&targets);VtIntArray indices;pi.GetProtoIndicesAttr().Get(&indices,time);auto root=stage->GetPrimAtPath(targets.at(indices[index]));auto b=prim;while(b&&b.GetPath().HasPrefix(root.GetPath())&&!direct(b)){if(b==root){b=UsdPrim();break;}b=b.GetParent();}
     if(b&&direct(b)){auto par=b.GetParent();while(par&&par.GetPath().HasPrefix(root.GetPath())&&!direct(par))par=par.GetParent();Ptr W=par&&par.GetPath().HasPrefix(root.GetPath())&&direct(par)?e.parse(wkt(par)):H.source.crs;Model B(e,b,time,W);bool br=false;M BD=UsdGeomXformCache(time).ComputeRelativeTransform(prim,b,&br);for(auto&j:points){V x=B.forward(vec(j),fixed,BD,br);if(I!=M(1)){need(abs(D.GetDeterminant())>1e-15,"singular instancer inverse");x=H.forward(I.Transform(H.inverse(x,fixed,D,ir)),fixed,D,ir);}result.push_back(json(e.convert(x,fixed,output)));}}
     else{bool r=false;M proto=UsdGeomXformCache(time).ComputeRelativeTransform(prim,root,&r)*local(root,time)*I;for(auto&j:points)result.push_back(json(H.forward(proto.Transform(vec(j)),output,D,ir)));}
   } else {for(auto&j:points)result.push_back(json(evaluate(e,prim,vec(j),output,time)));}
   auto a=has(req,"instance")?bound(stage->GetPrimAtPath(SdfPath(at(req,"instancer").GetString()))):prim;while(a&&!a.IsPseudoRoot()&&!direct(a)&&a.GetTypeName()!=TfToken("CoordinateReferenceSystem"))a=a.GetParent();need(a&&!a.IsPseudoRoot(),"source context unavailable");CRSInfo c(e,e.parse(wkt(a)),direct(a));report["sourceHeight"]=c.height();
 }
 report["success"]=J(true);report["points"]=J(result);report["operations"]=J(e.operations);report["warnings"]=J(diagnostics);report["PROJ"]=J(proj_info().version);std::ofstream dest(argv[2]);JsWriteToStream(J(report),dest);return 0;
 }catch(const std::exception&ex){O r{{"success",J(false)},{"error",J(ex.what())}};if(argc>2){std::ofstream d(argv[2]);JsWriteToStream(J(r),d);}std::cerr<<ex.what()<<"\n";return 1;}}
