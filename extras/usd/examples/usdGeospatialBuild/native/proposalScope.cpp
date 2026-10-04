#include "pxr/base/js/json.h"
#include "pxr/usd/usd/stage.h"
#include "pxr/usd/usd/prim.h"
#include "pxr/usd/usd/attribute.h"
#include "pxr/usd/sdf/types.h"
#include "pxr/usd/sdf/listOp.h"
#include "pxr/usd/sdf/layer.h"
#include "pxr/usd/sdf/schema.h"
#include <algorithm>
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
            std::map<std::string, std::string> before;
            for (const auto& layer : stage->GetUsedLayers()) layer->ExportToString(&before[layer->GetIdentifier()]);
            JsArray queries;
            for (const auto& path : job.at("queries").GetJsArray()) {
                JsObject query{{"prim", path}};
                try {
                    auto found = Discover(stage->GetPrimAtPath(SdfPath(path.GetString())));
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
