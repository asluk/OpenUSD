#include "pxr/base/js/json.h"
#include "pxr/usd/usd/stage.h"
#include "pxr/usd/usd/prim.h"
#include "pxr/usd/usd/attribute.h"
#include "pxr/usd/sdf/types.h"
#include "pxr/usd/sdf/listOp.h"
#include "pxr/usd/sdf/layer.h"
#include "pxr/usd/sdf/schema.h"
#include "pxr/usd/usdGeom/xformable.h"
#include "pxr/base/gf/vec3d.h"
#include "pxr/base/gf/quatd.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>

PXR_NAMESPACE_USING_DIRECTIVE

JsObject Discover(UsdPrim prim) {
    if (!prim) throw std::runtime_error("Prim is not available in the composed stage");
    for (auto current = prim; current && !current.IsPseudoRoot(); current = current.GetParent()) {
        SdfTokenListOp schemas;
        if (!current.GetMetadata(TfToken("apiSchemas"), &schemas)) continue;
        auto applied = schemas.GetAppliedItems();
        if (std::find(applied.begin(), applied.end(), TfToken("GeospatialCRSBindingAPI")) == applied.end()) continue;
        auto attribute = current.GetAttribute(TfToken("crs:wkt"));
        if (!attribute || !attribute.HasAuthoredValueOpinion())
            throw std::runtime_error("Nearest direct binding has no authored CRS definition");
        if (attribute.GetTypeName() != SdfValueTypeNames->Token)
            throw std::runtime_error("CRS definition must be a token");
        if (attribute.GetVariability() != SdfVariabilityUniform)
            throw std::runtime_error("CRS definition must be uniform");
        TfToken value;
        if (!attribute.Get(&value) || value.IsEmpty()) throw std::runtime_error("CRS definition is empty");
        return {{"binding_prim", JsValue(current.GetPath().GetString())}, {"wkt", JsValue(value.GetString())}};
    }
    throw std::runtime_error("No CRS binding in the composed ancestry");
}

JsValue Vector(const GfVec3d& value) {
    JsArray result;
    for (int index = 0; index != 3; ++index) result.emplace_back(value[index]);
    return JsValue(result);
}

JsObject ReadPlacement(UsdPrim prim, UsdTimeCode time) {
    auto result = Discover(prim);
    auto owner = prim.GetStage()->GetPrimAtPath(SdfPath(result.at("binding_prim").GetString()));
    if (!UsdGeomXformable(owner)) throw std::runtime_error("Model binding must be on Xformable");
    for (const auto& name : {"position", "orientation", "scale"}) {
        const bool rotation = std::string(name) == "orientation";
        auto attribute = owner.GetAttribute(TfToken(std::string("crs:") + name));
        auto requiredType = rotation ? SdfValueTypeNames->Quatd : SdfValueTypeNames->Double3;
        if (attribute && attribute.GetTypeName() != requiredType)
            throw std::runtime_error(std::string("Placement ") + name + " has wrong type");
        if (attribute && attribute.GetVariability() != SdfVariabilityVarying)
            throw std::runtime_error(std::string("Placement ") + name + " must be varying");
        GfVec3d vector(1.0);
        GfQuatd quaternion(1.0);
        bool authored = attribute && attribute.HasAuthoredValueOpinion();
        if (authored) {
            bool available = rotation ? attribute.Get(&quaternion, time) : attribute.Get(&vector, time);
            if (!available) throw std::runtime_error(std::string("Placement ") + name + " is unavailable");
        } else if (std::string(name) == "position") {
            throw std::runtime_error("Placement position is unavailable");
        }
        if (rotation) {
            auto imaginary = quaternion.GetImaginary();
            if (!std::isfinite(quaternion.GetReal()) || !std::isfinite(imaginary[0]) ||
                !std::isfinite(imaginary[1]) || !std::isfinite(imaginary[2]))
                throw std::runtime_error("Placement orientation is nonfinite");
            if (quaternion.GetReal() == 0 && imaginary == GfVec3d(0))
                throw std::runtime_error("Placement orientation is a zero quaternion");
            result[name] = JsValue(JsObject{{"real", JsValue(quaternion.GetReal())}, {"imaginary", Vector(imaginary)}});
        } else {
            for (int index = 0; index != 3; ++index)
                if (!std::isfinite(vector[index])) throw std::runtime_error(std::string("Placement ") + name + " is nonfinite");
            result[name] = Vector(vector);
        }
    }
    return result;
}

#include "originQuery.h"

int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::runtime_error("Usage: proposalScope jobs.json output.json");
        std::ifstream input(argv[1]);
        auto jobs = JsParseStream(input).GetJsArray();
        JsArray results;
        for (const auto& item : jobs) {
            auto job = item.GetJsObject();
            auto stage = UsdStage::Open(job.at("stage").GetString(),
                job.at("load_none").GetBool() ? UsdStage::LoadNone : UsdStage::LoadAll);
            if (!stage) throw std::runtime_error("Cannot open scope fixture");
            const bool origin = job.count("kind") && job.at("kind").GetString() == "origin_coordinates";
            const bool placement = job.count("kind") && (job.at("kind").GetString() == "placement_values" || origin);
            if (placement) stage->SetInterpolationType(job.at("interpolation").GetString() == "held" ? UsdInterpolationTypeHeld : UsdInterpolationTypeLinear);
            std::map<std::string, std::string> before;
            for (const auto& layer : stage->GetUsedLayers()) layer->ExportToString(&before[layer->GetIdentifier()]);
            JsArray queries;
            for (const auto& path : job.at("queries").GetJsArray()) {
                JsObject query{{"prim", path}};
                try {
                    auto prim = stage->GetPrimAtPath(SdfPath(path.GetString()));
                    auto found = origin ? OriginQuery(prim, UsdTimeCode(job.at("time").GetReal()), job.at("output_wkt").GetString()) :
                                 placement ? ReadPlacement(prim, UsdTimeCode(job.at("time").GetReal())) : Discover(prim);
                    query.insert(found.begin(), found.end());
                    query["success"] = JsValue(true);
                } catch (const std::exception& error) {
                    query["success"] = JsValue(false);
                    query["error"] = JsValue(error.what());
                }
                queries.emplace_back(query);
            }
            for (const auto& layer : stage->GetUsedLayers()) {
                std::string after;
                layer->ExportToString(&after);
                if (before.at(layer->GetIdentifier()) != after) throw std::runtime_error("Source layer changed");
            }
            results.emplace_back(JsObject{{"name", job.at("name")}, {"queries", JsValue(queries)}, {"source_unchanged", JsValue(true)}});
        }
        std::ofstream output(argv[2]);
        output << JsWriteToString(JsValue(results));
        std::cout << results.size() << " native USD scope cases completed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
