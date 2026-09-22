// Native Hydra consumer of the shared, read-only resolved-scene contract.
// This adapter does not author USD or select a coordinate operation.
#include "pxr/pxr.h"
#include "pxr/base/js/json.h"
#include "pxr/base/js/value.h"
#include "pxr/base/gf/matrix4d.h"
#include "pxr/base/gf/vec3f.h"
#include "pxr/base/vt/array.h"
#include "pxr/imaging/hd/filteringSceneIndex.h"
#include "pxr/imaging/hd/retainedSceneIndex.h"
#include "pxr/imaging/hd/retainedDataSource.h"
#include "pxr/imaging/hd/overlayContainerDataSource.h"
#include "pxr/imaging/hd/xformSchema.h"
#include "pxr/imaging/hd/primvarsSchema.h"
#include "pxr/imaging/hd/primvarSchema.h"
#include "pxr/imaging/hd/sceneIndexObserver.h"
#include "pxr/imaging/hd/meshSchema.h"
#include "pxr/imaging/hd/meshTopologySchema.h"
#include "pxr/imaging/hd/basisCurvesSchema.h"
#include "pxr/imaging/hd/basisCurvesTopologySchema.h"
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>

PXR_NAMESPACE_USING_DIRECTIVE

#include "stormRender.h"

static double Number(const JsValue &v) {
    if (v.IsReal()) return v.GetReal();
    if (v.IsInt()) return static_cast<double>(v.GetInt());
    throw std::runtime_error("Expected finite numeric snapshot component");
}
static GfMatrix4d Matrix(const JsValue &value) {
    GfMatrix4d result(1);
    const auto &rows = value.GetJsArray();
    if (rows.size()!=4) throw std::runtime_error("Bad matrix");
    for (size_t i=0;i<4;++i) {
        const auto &row=rows[i].GetJsArray();
        if(row.size()!=4) throw std::runtime_error("Bad matrix row");
        for(size_t j=0;j<4;++j) result[i][j]=Number(row[j]);
    }
    return result;
}
static VtVec3fArray Points(const JsValue &value) {
    VtVec3fArray result;
    for(const auto &item:value.GetJsArray()) {
        const auto &p=item.GetJsArray();
        if(p.size()!=3) throw std::runtime_error("Bad point");
        result.push_back(GfVec3f(Number(p[0]),Number(p[1]),Number(p[2])));
    }
    return result;
}
static JsValue JsonMatrix(const GfMatrix4d &matrix) {
    JsArray rows;
    for(int i=0;i<4;++i) { JsArray row; for(int j=0;j<4;++j) row.emplace_back(matrix[i][j]); rows.emplace_back(row); }
    return JsValue(rows);
}
static HdContainerDataSourceHandle Data(const GfMatrix4d &matrix, const VtVec3fArray &points) {
    const TfToken xform("xform"), primvars("primvars"), pointName("points");
    auto xf=HdXformSchema::Builder()
        .SetMatrix(HdRetainedTypedSampledDataSource<GfMatrix4d>::New(matrix))
        .SetResetXformStack(HdRetainedTypedSampledDataSource<bool>::New(true)).Build();
    auto point=HdPrimvarSchema::Builder()
        .SetPrimvarValue(HdRetainedTypedSampledDataSource<VtVec3fArray>::New(points))
        .SetInterpolation(HdRetainedTypedSampledDataSource<TfToken>::New(TfToken("vertex")))
        .SetRole(HdRetainedTypedSampledDataSource<TfToken>::New(TfToken("point"))).Build();
    auto color=HdPrimvarSchema::Builder()
        .SetPrimvarValue(HdRetainedTypedSampledDataSource<VtVec3fArray>::New(VtVec3fArray{GfVec3f(.18f,.75f,.9f)}))
        .SetInterpolation(HdRetainedTypedSampledDataSource<TfToken>::New(TfToken("constant")))
        .SetRole(HdRetainedTypedSampledDataSource<TfToken>::New(TfToken("color"))).Build();
    auto widths=HdPrimvarSchema::Builder()
        .SetPrimvarValue(HdRetainedTypedSampledDataSource<VtFloatArray>::New(VtFloatArray{1.5f}))
        .SetInterpolation(HdRetainedTypedSampledDataSource<TfToken>::New(TfToken("constant"))).Build();
    auto pv=HdRetainedContainerDataSource::New(pointName,point,TfToken("displayColor"),color,TfToken("widths"),widths);
    return HdRetainedContainerDataSource::New(xform,xf,primvars,pv);
}

static HdContainerDataSourceHandle Topology(const JsObject &item) {
    auto ints=[&](const char *name) { VtIntArray a; auto i=item.find(name);
        if(i!=item.end()) for(const auto &v:i->second.GetJsArray()) a.push_back(static_cast<int>(Number(v)));
        return HdRetainedTypedSampledDataSource<VtIntArray>::New(a); };
    auto token=[](const char *name) { return HdRetainedTypedSampledDataSource<TfToken>::New(TfToken(name)); };
    const auto type=item.at("type").GetString();
    if(type=="Mesh") {
        auto topology=HdMeshTopologySchema::Builder().SetFaceVertexCounts(ints("counts"))
            .SetFaceVertexIndices(ints("indices")).SetOrientation(token("rightHanded")).Build();
        auto mesh=HdMeshSchema::Builder().SetTopology(topology).SetSubdivisionScheme(token("none"))
            .SetDoubleSided(HdRetainedTypedSampledDataSource<bool>::New(true)).Build();
        return HdRetainedContainerDataSource::New(TfToken("mesh"),mesh);
    }
    if(type=="BasisCurves") {
        auto topology=HdBasisCurvesTopologySchema::Builder().SetCurveVertexCounts(ints("counts"))
            .SetBasis(token("bezier")).SetType(token("linear")).SetWrap(token("nonperiodic")).Build();
        return HdRetainedContainerDataSource::New(TfToken("basisCurves"),HdBasisCurvesSchema::Builder().SetTopology(topology).Build());
    }
    return HdRetainedContainerDataSource::New();
}

class GeobuildSceneIndex final: public HdSingleInputFilteringSceneIndexBase {
public:
    static TfRefPtr<GeobuildSceneIndex> New(const HdSceneIndexBaseRefPtr &input) {
        return TfCreateRefPtr(new GeobuildSceneIndex(input));
    }
    void Replace(const JsObject &prims) {
        std::map<SdfPath,HdContainerDataSourceHandle> next;
        HdSceneIndexObserver::DirtiedPrimEntries changed;
        for(const auto &entry:prims) {
            const auto &p=entry.second.GetJsObject();
            SdfPath path(entry.first);
            next[path]=HdOverlayContainerDataSource::New(Data(Matrix(p.at("matrix")),Points(p.at("points"))),Topology(p));
            changed.push_back({path,HdDataSourceLocatorSet{HdDataSourceLocator()}});
        }
        _resolved.swap(next);
        _SendPrimsDirtied(changed);
    }
    HdSceneIndexPrim GetPrim(const SdfPath &path) const override {
        auto prim=_GetInputSceneIndex()->GetPrim(path);
        const auto found=_resolved.find(path);
        if(found!=_resolved.end()) prim.dataSource=HdOverlayContainerDataSource::New(found->second,prim.dataSource);
        return prim;
    }
    SdfPathVector GetChildPrimPaths(const SdfPath &path) const override {
        return _GetInputSceneIndex()->GetChildPrimPaths(path);
    }
protected:
    explicit GeobuildSceneIndex(const HdSceneIndexBaseRefPtr &input):HdSingleInputFilteringSceneIndexBase(input) {}
    void _PrimsAdded(const HdSceneIndexBase &,const HdSceneIndexObserver::AddedPrimEntries &e) override { _SendPrimsAdded(e); }
    void _PrimsRemoved(const HdSceneIndexBase &,const HdSceneIndexObserver::RemovedPrimEntries &e) override {
        for(const auto &removed:e) for(auto i=_resolved.begin();i!=_resolved.end();) {
            if(i->first.HasPrefix(removed.primPath)) i=_resolved.erase(i); else ++i;
        }
        _SendPrimsRemoved(e);
    }
    void _PrimsDirtied(const HdSceneIndexBase &,const HdSceneIndexObserver::DirtiedPrimEntries &e) override { _SendPrimsDirtied(e); }
private:
    std::map<SdfPath,HdContainerDataSourceHandle> _resolved;
};

class Observer final: public HdSceneIndexObserver {
public:
    JsArray added,removed,dirtied;
    void PrimsAdded(const HdSceneIndexBase &,const AddedPrimEntries &e) override { for(const auto &x:e) added.emplace_back(x.primPath.GetString()); }
    void PrimsRemoved(const HdSceneIndexBase &,const RemovedPrimEntries &e) override { for(const auto &x:e) removed.emplace_back(x.primPath.GetString()); }
    void PrimsDirtied(const HdSceneIndexBase &,const DirtiedPrimEntries &e) override { for(const auto &x:e) dirtied.emplace_back(x.primPath.GetString()); }
    void PrimsRenamed(const HdSceneIndexBase &sender,const RenamedPrimEntries &e) override { ConvertPrimsRenamedToRemovedAndAdded(sender,e,this); }
    void Reset() { added.clear(); removed.clear(); dirtied.clear(); }
};

int main(int argc,char **argv) {
    try {
        if(argc!=3 && argc!=4) throw std::runtime_error("Usage: geobuildHydra input.json output.json [storm.png]");
        std::ifstream stream(argv[1]);
        std::ostringstream text; text<<stream.rdbuf();
        JsParseError error;
        JsValue document=JsParseString(text.str(),&error);
        if(!document.IsObject()) throw std::runtime_error("Unreadable snapshot JSON: "+error.reason);
        auto input=HdRetainedSceneIndex::New();
        auto resolved=GeobuildSceneIndex::New(input);
        Observer observer;
        resolved->AddObserver(HdSceneIndexObserverPtr(&observer));
        std::set<std::string> previous;
        JsArray results;
        for(const auto &frame:document.GetJsObject().at("frames").GetJsArray()) {
            observer.Reset();
            const auto &prims=frame.GetJsObject().at("prims").GetJsObject();
            std::set<std::string> paths;
            HdRetainedSceneIndex::AddedPrimEntries added;
            for(const auto &entry:prims) {
                paths.insert(entry.first);
                {
                    auto points=Points(entry.second.GetJsObject().at("points"));
                    std::string type=entry.second.GetJsObject().at("type").GetString();
                    type=type=="Mesh"?"mesh":type=="BasisCurves"?"basisCurves":type=="Points"?"points":"";
                    added.push_back({SdfPath(entry.first),TfToken(type),HdOverlayContainerDataSource::New(Data(GfMatrix4d(1),points),Topology(entry.second.GetJsObject()))});
                }
            }
            input->AddPrims(added);
            HdSceneIndexObserver::RemovedPrimEntries removed;
            for(const auto &path:previous) if(!paths.count(path)) removed.push_back({SdfPath(path)});
            input->RemovePrims(removed);
            resolved->Replace(prims);
            JsObject output;
            bool inputUnchanged=true;
            for(const auto &entry:prims) {
                const SdfPath path(entry.first);
                const auto prim=resolved->GetPrim(path);
                const auto matrix=HdXformSchema::GetFromParent(prim.dataSource).GetMatrix()->GetTypedValue(0);
                const auto points=HdPrimvarsSchema::GetFromParent(prim.dataSource).GetPrimvar(TfToken("points")).GetPrimvarValue()->GetValue(0).Get<VtVec3fArray>();
                JsArray transformed;
                for(const auto &point:points) {
                    const auto p=matrix.Transform(GfVec3d(point));
                    transformed.emplace_back(JsArray{JsValue(p[0]),JsValue(p[1]),JsValue(p[2])});
                }
                inputUnchanged=inputUnchanged && HdXformSchema::GetFromParent(input->GetPrim(path).dataSource).GetMatrix()->GetTypedValue(0)==GfMatrix4d(1);
                output[entry.first]=JsValue(JsObject{{"matrix",JsonMatrix(matrix)},{"world_points",JsValue(transformed)}});
            }
            results.emplace_back(JsObject{{"prims",JsValue(output)},{"added",JsValue(observer.added)},
                {"removed",JsValue(observer.removed)},{"dirtied",JsValue(observer.dirtied)},
                {"input_unchanged",JsValue(inputUnchanged)}});
            previous=paths;
        }
        resolved->RemoveObserver(HdSceneIndexObserverPtr(&observer));
        JsObject rendering;
        if(argc==4) rendering=RenderStorm(resolved,argv[3]);
        std::ofstream out(argv[2]);
        out<<JsWriteToString(JsValue(JsObject{{"usd_version",JsValue(PXR_VERSION)},
            {"native_scene_index",JsValue(true)},{"frames",JsValue(results)},
            {"rendering",JsValue(rendering)},{"loaded_modules",JsValue(LoadedModules())}}));
        return 0;
    } catch(const std::exception &e) { std::cerr<<e.what()<<std::endl; return 1; }
}
