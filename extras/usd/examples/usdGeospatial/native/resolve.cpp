//
// Copyright 2026 NVIDIA CORPORATION & AFFILIATES
//
// Licensed under the terms set forth in the LICENSE.txt file available at
// https://openusd.org/license.
//
// JSON command-line adapter. Coordinate and USD semantics live in crs.cpp and
// placement.cpp; this request format is an implementation interface only.
#include "crs.h"
#include "placement.h"
#include "profiles.h"
#include <fstream>
#include <iostream>
#include <pxr/base/plug/registry.h>

using namespace usdGeospatialExample;

namespace {
JsonValue ExecuteRequest(const JsonValue& request)
{
    if (HasField(request, "publishStage") || HasField(request, "profilesStage")) {
        return ExecuteProfilesRequest(request);
    }

    CoordinateEngine engine;
    auto output = engine.ParseWkt(GetField(request, "output").GetString());
    JsonArray results;
    JsonObject report;
    if (HasField(request, "coordinateSource")) {
        const bool fallback = HasField(request, "modelFallback") &&
                              GetField(request, "modelFallback").GetBool();
        CrsInfo source(
            engine, engine.ParseWkt(GetField(request, "coordinateSource").GetString()),
            fallback);
        for (const auto& value : GetField(request, "points").GetJsArray()) {
            results.push_back(
                PointToJson(engine.Convert(ReadPoint(value), source.crs, output)));
        }
        report["sourceHeight"] = source.HeightReport();
    }
    else {
        auto stage = UsdStage::Open(GetField(request, "stage").GetString());
        Require(bool(stage), "cannot open stage");
        auto prim =
            stage->GetPrimAtPath(SdfPath(GetField(request, "prim").GetString()));
        Require(bool(prim), "missing prim");
        const UsdTimeCode time =
            HasField(request, "time")
                ? UsdTimeCode(ReadNumber(GetField(request, "time")))
                : UsdTimeCode::Default();
        PlacementEvaluator evaluator(engine);
        UsdPrim sourceContext = prim;
        if (HasField(request, "instance")) {
            auto instancer = stage->GetPrimAtPath(
                SdfPath(GetField(request, "instancer").GetString()));
            std::vector<Point3d> points;
            for (const auto& value : GetField(request, "points").GetJsArray()) {
                points.push_back(ReadPoint(value));
            }
            for (const auto& point : evaluator.ResolveInstance(
                     instancer, GetField(request, "instance").GetInt(), prim, points,
                     output, time)) {
                results.push_back(PointToJson(point));
            }
            sourceContext = FindControllingBinding(instancer);
        }
        else {
            for (const auto& value : GetField(request, "points").GetJsArray()) {
                results.push_back(PointToJson(
                    evaluator.ResolvePoint(prim, ReadPoint(value), output, time)));
            }
        }
        while (sourceContext && !sourceContext.IsPseudoRoot() &&
               !HasDirectBinding(sourceContext) &&
               sourceContext.GetTypeName() != TfToken("CoordinateReferenceSystem")) {
            sourceContext = sourceContext.GetParent();
        }
        Require(sourceContext && !sourceContext.IsPseudoRoot(),
                "source context unavailable");
        CrsInfo source(engine, engine.ParseWkt(ReadWkt(sourceContext, engine)),
                       HasDirectBinding(sourceContext));
        report["sourceHeight"] = source.HeightReport();
    }
    report["success"] = JsonValue(true);
    report["points"] = JsonValue(results);
    report["operations"] = JsonValue(engine.operations);
    report["warnings"] = JsonValue(engine.diagnostics);
    report["PROJ"] = JsonValue(proj_info().version);
    return JsonValue(report);
}
} // namespace

int main(int argc, char** argv)
{
    try {
        Require(argc == 4, "resolve request.json result.json schema-directory");
        PlugRegistry::GetInstance().RegisterPlugins(argv[3]);
        std::ifstream input(argv[1]);
        JsonValue request = JsParseStream(input);
        Require(request.IsObject(), "invalid request");
        const JsonValue report = ExecuteRequest(request);
        std::ofstream output(argv[2]);
        JsWriteToStream(report, output);
        return 0;
    }
    catch (const std::exception& error) {
        if (argc > 2) {
            std::ofstream output(argv[2]);
            JsWriteToStream(JsonValue(JsonObject{{"success", JsonValue(false)},
                                                 {"error", JsonValue(error.what())}}),
                            output);
        }
        std::cerr << error.what() << "\n";
        return 1;
    }
}
