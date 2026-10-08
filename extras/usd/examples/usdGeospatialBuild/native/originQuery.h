#pragma once
#include <proj.h>
#include <vector>
#include <string>
#include <cmath>
#include <stdexcept>
#include <memory>
#include <set>

// This adapter resolves only an absolute anchor origin. It selects no model
// frame, post-transform context, geometry approximation or private scene fact.
struct QueryDefinition {
    PJ* object = nullptr;
    bool geographic = false;
    double angular[2]{1, 1};
    QueryDefinition(PJ_CONTEXT* context, const std::string& wkt) {
        const char* options[]{"STRICT=YES", "UNSET_IDENTIFIERS_IF_INCOMPATIBLE_DEF=NO", nullptr};
        object = proj_create_from_wkt(context, wkt.c_str(), options, nullptr, nullptr);
        if (!object) throw std::runtime_error("Invalid or unsupported CRS definition");
        auto type = proj_get_type(object);
        PJ* horizontal = object;
        PJ* vertical = nullptr;
        if (type == PJ_TYPE_BOUND_CRS) throw std::runtime_error("Bound CRS origin-query profile not implemented; no embedded transform dropped");
        if (type == PJ_TYPE_COMPOUND_CRS) {
            horizontal = proj_crs_get_sub_crs(context, object, 0);
            vertical = proj_crs_get_sub_crs(context, object, 1);
            type = proj_get_type(horizontal);
        }
        geographic = type == PJ_TYPE_GEOGRAPHIC_3D_CRS || type == PJ_TYPE_GEOGRAPHIC_2D_CRS;
        auto system = proj_crs_get_coordinate_system(context, horizontal);
        int count = system ? proj_cs_get_axis_count(context, system) : 0;
        if (count + (vertical ? 1 : 0) != 3) throw std::runtime_error("Complete three-component coordinate definition required");
        bool east = false, north = false;
        std::set<std::string> roles;
        for (int index = 0; index != count; ++index) {
            const char* direction = nullptr;
            double factor = 0;
            if (!proj_cs_get_axis_info(context, system, index, nullptr, nullptr, &direction, &factor, nullptr, nullptr, nullptr))
                throw std::runtime_error("Axis interpretation unavailable");
            std::string role = direction ? direction : "";
            roles.insert(role);
            if (role == "east") { east = true; angular[0] = factor * 180. / std::acos(-1.); }
            else if (role == "north") { north = true; angular[1] = factor * 180. / std::acos(-1.); }
            else if (role != "up" && role != "geocentricX" && role != "geocentricY" && role != "geocentricZ")
                throw std::runtime_error("Unsupported coordinate component set");
        }
        if (vertical) {
            auto vSystem = proj_crs_get_coordinate_system(context, vertical);
            const char* direction = nullptr;
            bool valid = vSystem && proj_cs_get_axis_count(context, vSystem) == 1 &&
                proj_cs_get_axis_info(context, vSystem, 0, nullptr, nullptr, &direction, nullptr, nullptr, nullptr, nullptr) &&
                direction && std::string(direction) == "up";
            if (vSystem) proj_destroy(vSystem);
            if (!valid) throw std::runtime_error("Unsupported vertical component set");
            roles.insert("up");
        }
        if (roles != std::set<std::string>{"east", "north", "up"} &&
            roles != std::set<std::string>{"geocentricX", "geocentricY", "geocentricZ"})
            throw std::runtime_error("Unsupported coordinate component set");
        if (geographic && (!east || !north)) throw std::runtime_error("Unsupported geographic component set");
        if (system) proj_destroy(system);
        if (vertical) { proj_destroy(vertical); proj_destroy(horizontal); }
    }
    ~QueryDefinition() { if (object) proj_destroy(object); }
};

inline JsObject OriginQuery(UsdPrim prim, UsdTimeCode time, const std::string& outputWkt) {
    auto record = ReadPlacement(prim, time);
    if (record.at("binding_prim").GetString() != prim.GetPath().GetString() || !prim.GetParent().IsPseudoRoot())
        throw std::runtime_error("This origin adapter supports only direct top-level anchors; dependent frame request stopped");
    std::string selectedOutput = outputWkt;
    if (selectedOutput.empty()) {
        try { selectedOutput = Discover(prim.GetStage()->GetDefaultPrim()).at("wkt").GetString(); }
        catch (const std::exception&) { throw std::runtime_error("No usable output CRS on composed defaultPrim"); }
    }
    auto owner = prim.GetStage()->GetPrimAtPath(SdfPath(record.at("binding_prim").GetString()));
    bool reset = false;
    if (!UsdGeomXformable(owner).GetOrderedXformOps(&reset).empty())
        throw std::runtime_error("Ordinary-adjustment frame is unspecified; origin query stopped");
    std::unique_ptr<PJ_CONTEXT, decltype(&proj_context_destroy)> contextOwner(proj_context_create(), proj_context_destroy);
    auto context = contextOwner.get();
    proj_context_set_enable_network(context, 0);
    try {
        QueryDefinition source(context, record.at("wkt").GetString()), target(context, selectedOutput);
        const char* options[]{"ALLOW_BALLPARK=NO", "ONLY_BEST=YES", nullptr};
        auto raw = proj_create_crs_to_crs_from_pj(context, source.object, target.object, nullptr, options);
        if (!raw) throw std::runtime_error("Coordinate operation failed; no substitute");
        auto operation = proj_normalize_for_visualization(context, raw);
        proj_destroy(raw);
        if (!operation) throw std::runtime_error("Coordinate operation axes unavailable");
        auto input = record.at("position").GetJsArray();
        double x = input[0].GetReal(), y = input[1].GetReal(), z = input[2].GetReal();
        if (source.geographic) { x *= source.angular[0]; y *= source.angular[1]; }
        proj_errno_reset(operation);
        auto coordinate = proj_trans(operation, PJ_FWD, proj_coord(x, y, z, HUGE_VAL));
        if (proj_errno(operation) || !std::isfinite(coordinate.xyz.x) || !std::isfinite(coordinate.xyz.y) || !std::isfinite(coordinate.xyz.z)) {
            proj_destroy(operation);
            throw std::runtime_error("Coordinate operation failed; no substitute");
        }
        auto used = proj_trans_get_last_used_operation(operation);
        auto actual = used ? used : operation;
        auto info = proj_pj_info(actual);
        std::string definition = info.definition ? info.definition : "";
        double accuracy = proj_coordoperation_get_accuracy(context, actual);
        if (definition.find("t_epoch=") != std::string::npos || definition.find("proj=deformation") != std::string::npos) {
            if (used) proj_destroy(used);
            proj_destroy(operation);
            throw std::runtime_error("Epoch-dependent operations are deferred");
        }
        GfVec3d value(coordinate.xyz.x, coordinate.xyz.y, coordinate.xyz.z);
        if (target.geographic) { value[0] /= target.angular[0]; value[1] /= target.angular[1]; }
        JsObject result{{"coordinates", Vector(value)},
                        {"operation", JsValue(info.description ? info.description : "unknown")},
                        {"operation_definition", JsValue(definition)},
                        {"operation_accuracy_metres", accuracy >= 0 ? JsValue(accuracy) : JsValue()},
                        {"engine", JsValue("PROJ")},
                        {"engine_version", JsValue(proj_info().version)}};
        if (used) proj_destroy(used);
        proj_destroy(operation);
        // The definitions must be destroyed before their context is released.
        auto copy = result;
        return copy;
    } catch (...) {
        throw;
    }
}
