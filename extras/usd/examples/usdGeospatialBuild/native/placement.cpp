#include "placement.h"
#include "pxr/base/tf/registryManager.h"
#include "pxr/base/gf/matrix3d.h"
#include "pxr/usd/usdGeom/xformable.h"
#include "pxr/usd/usdGeom/metrics.h"
#include "pxr/usd/usd/primRange.h"
#include "pxr/usd/usd/notice.h"
#include "pxr/usdImaging/usdImaging/sceneIndexPlugin.h"
#include "pxr/imaging/hd/filteringSceneIndex.h"
#include "pxr/imaging/hd/xformSchema.h"
#include "pxr/imaging/hd/retainedDataSource.h"
#include "pxr/imaging/hd/overlayContainerDataSource.h"
#include <proj.h>
#include <cmath>
#include <stdexcept>
#include <sstream>
#include <map>
#include <memory>
#include <mutex>
PXR_NAMESPACE_USING_DIRECTIVE
namespace {
UsdStageRefPtr stage; std::string target,resources,lastOperation; double lastAccuracy=-1;UsdTimeCode timeCode;GfVec3d renderOrigin;size_t reads=0;
PJ_CONTEXT *ctx=nullptr;std::recursive_mutex guard;
struct Definition {
 PJ *object; bool geographic=false; GfVec3d units{1};double a=6378137,b=6356752.314245;
 Definition(const std::string& wkt){
  if(wkt.find("COORDINATEMETADATA")!=std::string::npos)throw std::runtime_error("Coordinate epochs deferred");
  object=proj_create(ctx,wkt.c_str());if(!object)throw std::runtime_error("Invalid CRS WKT");
  auto type=proj_get_type(object);auto coordinate=type==PJ_TYPE_BOUND_CRS?proj_get_source_crs(ctx,object):object;type=proj_get_type(coordinate);geographic=type==PJ_TYPE_GEOGRAPHIC_3D_CRS||type==PJ_TYPE_GEOGRAPHIC_2D_CRS;
  PJ *horizontal=coordinate,*vertical=nullptr;
  if(type==PJ_TYPE_COMPOUND_CRS){horizontal=proj_crs_get_sub_crs(ctx,coordinate,0);vertical=proj_crs_get_sub_crs(ctx,coordinate,1);}
  auto cs=proj_crs_get_coordinate_system(ctx,horizontal);int count=cs?proj_cs_get_axis_count(ctx,cs):0;
  if(count+(vertical?1:0)!=3)throw std::runtime_error("Complete three-axis CRS required");
  for(int i=0;i<count;i++){const char *direction;double factor;
   proj_cs_get_axis_info(ctx,cs,i,nullptr,nullptr,&direction,&factor,nullptr,nullptr,nullptr);
   std::string d=direction?direction:"";int j=d=="east"?0:d=="north"?1:i; if(j<3)units[j]=factor;
  }
  if(cs)proj_destroy(cs);
  if(vertical){cs=proj_crs_get_coordinate_system(ctx,vertical);proj_cs_get_axis_info(ctx,cs,0,nullptr,nullptr,nullptr,&units[2],nullptr,nullptr,nullptr);proj_destroy(cs);proj_destroy(vertical);proj_destroy(horizontal);}
  auto ell=proj_get_ellipsoid(ctx,coordinate); if(ell){int computed;double inv;proj_ellipsoid_get_parameters(ctx,ell,&a,&b,&computed,&inv);proj_destroy(ell);}if(coordinate!=object)proj_destroy(coordinate);
 }
 ~Definition(){proj_destroy(object);}
};
std::string Wkt(const UsdPrim &p,bool allowAbsent=false){
 auto q=p;while(q&&!q.IsPseudoRoot()){
  auto r=q.GetRelationship(TfToken("crs:binding"));SdfPathVector paths;
  if(r&&r.HasAuthoredTargets()){
   r.GetTargets(&paths);
   if(paths.size()!=1)throw std::runtime_error("Ambiguous binding");auto cp=stage->GetPrimAtPath(paths[0]);TfToken w;
   if(!cp||!cp.GetAttribute(TfToken("crs:wkt")).Get(&w))throw std::runtime_error("Broken CRS binding");return w.GetString();
  }q=q.GetParent();
 }if(allowAbsent)return {};throw std::runtime_error("No CRS binding/default output CRS");
}
struct Operation {
 PJ *op;bool geographic=false;double latitudeUnit=1;
 Operation(const std::string &src,const std::string &dst){
  Definition s(src),d(dst);geographic=s.geographic;latitudeUnit=s.units[1];const char *opts[]={"ALLOW_BALLPARK=NO","ONLY_BEST=YES",nullptr};
  auto raw=proj_create_crs_to_crs_from_pj(ctx,s.object,d.object,nullptr,opts);
  if(!raw)throw std::runtime_error("No supported coordinate operation");op=proj_normalize_for_visualization(ctx,raw);proj_destroy(raw);
  if(!op)throw std::runtime_error("Cannot normalize operation axes");
 }
 ~Operation(){proj_destroy(op);}
 GfVec3d Run(const GfVec3d& p){
  if(!std::isfinite(p[0])||!std::isfinite(p[1])||!std::isfinite(p[2])||(geographic&&abs(p[1]*latitudeUnit)>1.5707963267948966+1e-12))throw std::runtime_error("Coordinate outside domain; whole batch rejected");
  proj_errno_reset(op);auto v=proj_trans(op,PJ_FWD,proj_coord(p[0],p[1],p[2],HUGE_VAL));
  if(proj_errno(op)||!std::isfinite(v.xyz.x)||!std::isfinite(v.xyz.y)||!std::isfinite(v.xyz.z))throw std::runtime_error("Coordinate operation failed; whole batch rejected");
  auto used=proj_trans_get_last_used_operation(op);auto actual=used?used:op;auto info=proj_pj_info(actual);lastOperation=info.description?info.description:"unknown";lastAccuracy=proj_coordoperation_get_accuracy(ctx,actual);
  if(info.definition&&std::string(info.definition).find("t_epoch=")!=std::string::npos)throw std::runtime_error("Epoch dependent operation deferred");
  if(used)proj_destroy(used);return {v.xyz.x,v.xyz.y,v.xyz.z};
 }
};
std::map<std::string,std::unique_ptr<Operation>> coordinateOps;
GfVec3d SourceLocal(Definition& d,const GfVec3d& p,const GfVec3d& x){
 if(!d.geographic)return p+GfVec3d(x[0]/d.units[0],x[1]/d.units[1],x[2]/d.units[2]);
 double lo=p[0]*d.units[0],la=p[1]*d.units[1],h=p[2]*d.units[2];double sl=sin(lo),cl=cos(lo),sp=sin(la),cp=cos(la),e2=1-d.b*d.b/(d.a*d.a),n=d.a/sqrt(1-e2*sp*sp);
 GfVec3d v((n+h)*cp*cl,(n+h)*cp*sl,(n*(1-e2)+h)*sp);
 v+=GfVec3d(-sl,cl,0)*x[0]+GfVec3d(-sp*cl,-sp*sl,cp)*x[1]+GfVec3d(cp*cl,cp*sl,sp)*x[2];
 double l=atan2(v[1],v[0]),r=hypot(v[0],v[1]),f=atan2(v[2],r*(1-e2));
 for(int i=0;i<12;i++){n=d.a/sqrt(1-e2*sin(f)*sin(f));f=atan2(v[2]+e2*n*sin(f),r);}
 n=d.a/sqrt(1-e2*sin(f)*sin(f));h=abs(cos(f))>1e-8?r/cos(f)-n:abs(v[2])-d.b;
 return {l/d.units[0],f/d.units[1],h/d.units[2]};
}
GfVec3d Full(const UsdPrim& root,const GfVec3d& local){
 auto src=Wkt(root);Definition source(src);GfVec3d anchor,scale(1);GfQuatd quat(1);
 if(!root.GetAttribute(TfToken("crs:position")).Get(&anchor,timeCode))throw std::runtime_error("Missing placement");
 auto scaleAttr=root.GetAttribute(TfToken("crs:scale")),rotationAttr=root.GetAttribute(TfToken("crs:orientation"));
 if(scaleAttr&&scaleAttr.HasAuthoredValueOpinion()&&!scaleAttr.Get(&scale,timeCode))throw std::runtime_error("Invalid authored scale type");
 if(rotationAttr&&rotationAttr.HasAuthoredValueOpinion()&&!rotationAttr.Get(&quat,timeCode))throw std::runtime_error("Invalid authored orientation type");
 GfMatrix3d rot(quat);double unit=UsdGeomGetStageMetersPerUnit(stage);
 auto scaled=GfVec3d(local[0]*scale[0],local[1]*scale[1],local[2]*scale[2]);bool yUp=UsdGeomGetStageUpAxis(stage)==TfToken("Y");if(yUp)scaled={scaled[0],-scaled[2],scaled[1]};
 if(abs(quat.GetLength()-1)>1e-9||!std::isfinite(scale[0])||!std::isfinite(scale[1])||!std::isfinite(scale[2])||scale[0]==0||scale[1]==0||scale[2]==0)throw std::runtime_error("Invalid placement orientation/scale");
 auto sourcePoint=SourceLocal(source,anchor,(scaled*rot)*unit);
 Operation op(src,target);auto p=op.Run(sourcePoint);bool reset=false;GfMatrix4d post(1);UsdGeomXformable(root).GetLocalTransformation(&post,&reset,timeCode);
 if(post!=GfMatrix4d(1)){
  std::string working=Wkt(root.GetParent(),true);if(working.empty())working=src;Definition work(working);
  Operation to(target,working),from(working,target);auto w=to.Run(p);
  if(work.geographic){
   // Independent geographic post path: local ENU Cartesian chart about source anchor.
   Operation anchorOp(src,working);auto o=anchorOp.Run(anchor);double lo=o[0]*work.units[0],la=o[1]*work.units[1];
   auto ecef=[&](GfVec3d a){double l=a[0]*work.units[0],f=a[1]*work.units[1],h=a[2]*work.units[2],e2=1-work.b*work.b/(work.a*work.a),n=work.a/sqrt(1-e2*sin(f)*sin(f));return GfVec3d((n+h)*cos(f)*cos(l),(n+h)*cos(f)*sin(l),(n*(1-e2)+h)*sin(f));};
   auto delta=ecef(w)-ecef(o);GfVec3d east(-sin(lo),cos(lo),0),north(-sin(la)*cos(lo),-sin(la)*sin(lo),cos(la)),up(cos(la)*cos(lo),cos(la)*sin(lo),sin(la));
   GfVec3d enu(GfDot(delta,east),GfDot(delta,north),GfDot(delta,up));if(yUp)enu={enu[0],enu[2],-enu[1]};enu=post.Transform(enu/unit)*unit;if(yUp)enu={enu[0],-enu[2],enu[1]};w=SourceLocal(work,o,enu);
  }else{auto m=GfVec3d(w[0]*work.units[0],w[1]*work.units[1],w[2]*work.units[2])/unit;if(yUp)m={m[0],m[2],-m[1]};m=post.Transform(m)*unit;if(yUp)m={m[0],-m[2],m[1]};w={m[0]/work.units[0],m[1]/work.units[1],m[2]/work.units[2]};}
  p=from.Run(w);
 }return p;
}
}
void Configure(UsdStageRefPtr s,const std::string& dst,double t,const GfVec3d& origin,const std::string& dirs){coordinateOps.clear();stage=s;target=dst.empty()?Wkt(s->GetDefaultPrim()):dst;timeCode=std::isnan(t)?UsdTimeCode::Default():UsdTimeCode(t);renderOrigin=origin;resources=dirs;if(ctx)proj_context_destroy(ctx);ctx=proj_context_create();std::vector<std::string> parts;std::istringstream ss(dirs);std::string x;while(std::getline(ss,x,';'))parts.push_back(x);std::vector<const char*> paths;for(auto &p:parts)paths.push_back(p.c_str());proj_context_set_search_paths(ctx,int(paths.size()),paths.data());proj_context_set_enable_network(ctx,0);}
GfVec3d CandidateCoordinate(const UsdPrim& p,const GfVec3d& xyz){auto source=Wkt(p);auto &op=coordinateOps[source];if(!op)op=std::make_unique<Operation>(source,target);return op->Run(xyz);}
GfVec3d CandidateFullPoint(const UsdPrim& p,const GfVec3d& xyz){return Full(p,xyz);}
GfMatrix4d CandidateFrame(const UsdPrim& p){
 std::lock_guard<std::recursive_mutex> lock(guard);
 double unit=UsdGeomGetStageMetersPerUnit(stage);auto origin=Full(p,GfVec3d(0));GfMatrix4d m(1);for(int i=0;i<3;i++){GfVec3d e(0);e[i]=1/unit;auto d=(Full(p,e)-Full(p,-e))/(2/unit);for(int j=0;j<3;j++)m[i][j]=d[j];}m.SetTranslateOnly(origin);return m;
}
std::string CandidateOperation(){return lastOperation;}
double CandidateAccuracy(){return lastAccuracy;}
std::string CandidateProjVersion(){return proj_info().version;}
size_t CandidateFilterReads(){return reads;}
GfVec3d CandidateRenderCoordinate(const GfVec3d& q){std::lock_guard<std::recursive_mutex> lock(guard);Definition d(target);double u=UsdGeomGetStageMetersPerUnit(stage);GfVec3d v(q[0]*d.units[0]/u,q[1]*d.units[1]/u,q[2]*d.units[2]/u);v-=renderOrigin;return UsdGeomGetStageUpAxis(stage)==TfToken("Y")?GfVec3d(v[0],v[2],-v[1]):v;}
PXR_NAMESPACE_OPEN_SCOPE
class CandidateMatrix final:public HdTypedSampledDataSource<GfMatrix4d>{
public:
 HD_DECLARE_DATASOURCE(CandidateMatrix);
 VtValue GetValue(Time t)override{return VtValue(GetTypedValue(t));}
 GfMatrix4d GetTypedValue(Time)override{
  std::lock_guard<std::recursive_mutex> lock(guard);auto p=stage->GetPrimAtPath(_path);auto m=CandidateFrame(p);Definition out(target);if(out.geographic)throw std::runtime_error("Geographic rendering frame unsupported");
  double u=UsdGeomGetStageMetersPerUnit(stage);for(int i=0;i<4;i++)for(int j=0;j<3;j++)m[i][j]*=out.units[j]/u;m.SetTranslateOnly(m.ExtractTranslation()-renderOrigin);
  if(UsdGeomGetStageUpAxis(stage)==TfToken("Y")){GfMatrix4d perm(1);perm[1][1]=0;perm[1][2]=-1;perm[2][1]=1;perm[2][2]=0;m=m*perm;}++reads;return m;
 }
 bool GetContributingSampleTimesForInterval(Time,Time,std::vector<Time>*)override{return false;}
private:
 CandidateMatrix(const SdfPath& path):_path(path){}SdfPath _path;
};
class CandidatePlacementIndex final:public HdSingleInputFilteringSceneIndexBase{
public:
 ~CandidatePlacementIndex()override{TfNotice::Revoke(_notice);}
 static HdSceneIndexBaseRefPtr New(const HdSceneIndexBaseRefPtr& input){return TfCreateRefPtr(new CandidatePlacementIndex(input));}
 HdSceneIndexPrim GetPrim(const SdfPath& path)const override{
  std::lock_guard<std::recursive_mutex> lock(guard);
  auto v=_GetInputSceneIndex()->GetPrim(path);auto p=stage->GetPrimAtPath(path);
  if(p&&p.GetAttribute(TfToken("crs:position")).HasAuthoredValueOpinion()){
   try{auto m=CandidateFrame(p);Definition out(target);if(out.geographic)throw std::runtime_error("Geographic rendering frame unsupported");
    double u=UsdGeomGetStageMetersPerUnit(stage);for(int i=0;i<4;i++)for(int j=0;j<3;j++)m[i][j]*=out.units[j]/u;
    m.SetTranslateOnly(m.ExtractTranslation()-renderOrigin);
    if(UsdGeomGetStageUpAxis(stage)==TfToken("Y")){GfMatrix4d perm(1);perm[1][1]=0;perm[1][2]=-1;perm[2][1]=1;perm[2][2]=0;m=m*perm;}
    auto x=HdXformSchema::Builder().SetMatrix(CandidateMatrix::New(path)).SetResetXformStack(HdRetainedTypedSampledDataSource<bool>::New(true)).Build();
    v.dataSource=HdOverlayContainerDataSource::New(HdRetainedContainerDataSource::New(HdXformSchemaTokens->xform,x),v.dataSource);++reads;
   }catch(const std::exception& e){TF_RUNTIME_ERROR("Candidate placement failed: %s",e.what());v.dataSource=nullptr;v.primType=TfToken();}
  }return v;
 }
 SdfPathVector GetChildPrimPaths(const SdfPath& p)const override{return _GetInputSceneIndex()->GetChildPrimPaths(p);}
protected:
 TfNotice::Key _notice;
 CandidatePlacementIndex(const HdSceneIndexBaseRefPtr& p):HdSingleInputFilteringSceneIndexBase(p){_notice=TfNotice::Register(TfCreateWeakPtr(this),&CandidatePlacementIndex::_OnUsdChanged,stage);}
 void _OnUsdChanged(const UsdNotice::ObjectsChanged&,const UsdStageWeakPtr&){HdSceneIndexObserver::DirtiedPrimEntries all;for(auto p:stage->Traverse())if(p.GetAttribute(TfToken("crs:position")).HasAuthoredValueOpinion())all.push_back({p.GetPath(),HdDataSourceLocatorSet(HdXformSchema::GetDefaultLocator())});_SendPrimsDirtied(all);}
 void _PrimsAdded(const HdSceneIndexBase&,const HdSceneIndexObserver::AddedPrimEntries& e)override{_SendPrimsAdded(e);}
 void _PrimsRemoved(const HdSceneIndexBase&,const HdSceneIndexObserver::RemovedPrimEntries& e)override{_SendPrimsRemoved(e);}
 void _PrimsDirtied(const HdSceneIndexBase&,const HdSceneIndexObserver::DirtiedPrimEntries& e)override{
  auto all=e;for(auto p:stage->Traverse())if(p.GetAttribute(TfToken("crs:position")).HasAuthoredValueOpinion())all.push_back({p.GetPath(),HdDataSourceLocatorSet(HdXformSchema::GetDefaultLocator())});_SendPrimsDirtied(all);
 }
};
PXR_NAMESPACE_CLOSE_SCOPE
HdSceneIndexBaseRefPtr CandidateSceneIndex(const HdSceneIndexBaseRefPtr& input){return CandidatePlacementIndex::New(input);}
