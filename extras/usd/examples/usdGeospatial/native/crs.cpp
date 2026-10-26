#include "crs.h"
#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <iomanip>
#include <proj_experimental.h>
#include <regex>
#include <sstream>
namespace usdGeospatialExample {
std::string NormalizeDecimal(std::string s)
{
    bool neg = s[0] == '-';
    if (s[0] == '+' || neg) {
        s.erase(0, 1);
    }
    int exp = 0;
    auto e = s.find_first_of("eE");
    if (e != s.npos) {
        exp = std::stoi(s.substr(e + 1));
        s = s.substr(0, e);
    }
    auto dot = s.find('.');
    int digits = int(dot == s.npos ? s.size() : dot) + exp;
    if (dot != s.npos) {
        s.erase(dot, 1);
    }
    if (digits <= 0) {
        s = "0." + std::string(-digits, '0') + s;
    }
    else if (digits >= int(s.size())) {
        s += std::string(digits - int(s.size()), '0');
    }
    else {
        s.insert(digits, ".");
    }
    while (s.size() > 1 && s[0] == '0' && s[1] != '.') {
        s.erase(0, 1);
    }
    if (s.find('.') != s.npos) {
        while (s.back() == '0') {
            s.pop_back();
        }
        if (s.back() == '.') {
            s.pop_back();
        }
    }
    return s == "0" ? s : neg ? "-" + s : s;
}
std::string NormalizeWkt(const std::string& s)
{
    static const std::regex token(
        R"wkt(\s+|"(?:[^"]|"")*"|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[A-Za-z_][A-Za-z_0-9]*|[\[\](),])wkt");
    static const std::map<std::string, std::string> enums = {
        {"cartesian", "Cartesian"},
        {"ellipsoidal", "ellipsoidal"},
        {"vertical", "vertical"},
        {"spherical", "spherical"},
        {"parametric", "parametric"},
        {"temporal", "temporal"},
        {"east", "east"},
        {"north", "north"},
        {"up", "up"},
        {"geocentricx", "geocentricX"},
        {"geocentricy", "geocentricY"},
        {"geocentricz", "geocentricZ"}};
    std::string out;
    size_t end = 0;
    for (std::sregex_iterator i(s.begin(), s.end(), token), last; i != last; ++i) {
        Require(size_t(i->position()) == end, "invalid WKT lexical character");
        auto t = i->str();
        end = i->position() + t.size();
        if (isspace((unsigned char)t[0])) {
            continue;
        }
        if (t[0] == '"') {
            out += t;
        }
        else if (t == "(" || t == "[") {
            out += '[';
        }
        else if (t == ")" || t == "]") {
            out += ']';
        }
        else if (t == ",") {
            out += t;
        }
        else if (isdigit((unsigned char)t[0]) || t[0] == '+' || t[0] == '-' ||
                 t[0] == '.') {
            out += NormalizeDecimal(t);
        }
        else {
            std::string lower = t;
            std::transform(lower.begin(), lower.end(), lower.begin(),
                           [](unsigned char c) { return char(tolower(c)); });
            auto e = enums.find(lower);
            if (e != enums.end()) {
                out += e->second;
            }
            else {
                std::transform(t.begin(), t.end(), t.begin(),
                               [](unsigned char c) { return char(toupper(c)); });
                out += t;
            }
        }
    }
    Require(end == s.size(), "invalid WKT trailing text");
    return out;
}

CoordinateEngine::CoordinateEngine()
{
    proj_context_set_enable_network(context, 0);
    if (auto r = getenv("GEOSPATIAL_RESOURCE_DIR")) {
        std::vector<std::string> a = {r};
        if (auto d = getenv("PROJ_DATA")) {
            a.push_back(d);
        }
        std::vector<const char*> b;
        for (auto& x : a) {
            b.push_back(x.c_str());
        }
        proj_context_set_search_paths(context, int(b.size()), b.data());
    }
}

CoordinateEngine::~CoordinateEngine()
{

    operationCache.clear();
    proj_context_destroy(context);
}

ProjHandle CoordinateEngine::ParseWkt(const std::string& text)
{
    Require(!text.empty(), "missing WKT");
    Require(text.find("COORDINATEMETADATA") == std::string::npos,
            "coordinate epochs deferred");
    auto parsed = std::make_shared<ProjObject>(proj_create(context, text.c_str()));
    Require(parsed->handle, "invalid or unsupported WKT");
    return parsed;
}

std::string CoordinateEngine::SerializeWkt(ProjHandle crs)
{
    auto text = proj_as_wkt(context, crs->handle, PJ_WKT2_2019, nullptr);
    Require(text, "cannot serialize CRS");
    return text;
}

JsonValue CoordinateEngine::DescribeCrs(ProjHandle crs)
{
    auto text = proj_as_projjson(context, crs->handle, nullptr);
    Require(text, "cannot inspect CRS");
    return JsParseString(text);
}

ProjHandle CoordinateEngine::WithCoordinateSystem(ProjHandle source, bool useGeocentric)
{
    ProjHandle geodetic = std::make_shared<ProjObject>(
        proj_crs_get_geodetic_crs(context, source->handle));
    Require(geodetic->handle, "CRS has no geodetic relation");
    JsonObject description = DescribeCrs(geodetic).GetJsObject();
    description.erase("id");
    description["type"] = JsonValue(useGeocentric ? "GeodeticCRS" : "GeographicCRS");
    JsonArray axes;
    if (useGeocentric) {
        for (auto component : {"X", "Y", "Z"}) {
            axes.push_back(JsonValue(JsonObject{
                {"name", JsonValue(std::string("Geocentric ") + component)},
                {"abbreviation", JsonValue(component)},
                {"direction", JsonValue(std::string("geocentric") + component)},
                {"unit", JsonValue("metre")}}));
        }
    }
    else {
        axes = {JsonValue(JsonObject{{"name", JsonValue("Latitude")},
                                     {"abbreviation", JsonValue("Lat")},
                                     {"direction", JsonValue("north")},
                                     {"unit", JsonValue("degree")}}),
                JsonValue(JsonObject{{"name", JsonValue("Longitude")},
                                     {"abbreviation", JsonValue("Lon")},
                                     {"direction", JsonValue("east")},
                                     {"unit", JsonValue("degree")}}),
                JsonValue(JsonObject{{"name", JsonValue("Height")},
                                     {"abbreviation", JsonValue("h")},
                                     {"direction", JsonValue("up")},
                                     {"unit", JsonValue("metre")}})};
    }
    description["coordinate_system"] = JsonValue(
        JsonObject{{"subtype", JsonValue(useGeocentric ? "Cartesian" : "ellipsoidal")},
                   {"axis", JsonValue(axes)}});
    return ParseWkt(JsWriteToString(JsonValue(description)));
}

Point3d CoordinateEngine::Convert(Point3d point, ProjHandle source, ProjHandle output)
{
    RequireFinite(point);
    auto key = std::make_pair(source->handle, output->handle);
    if (!operationCache.count(key)) {
        const char* options[] = {"ALLOW_BALLPARK=NO", "ONLY_BEST=YES", nullptr};
        ProjObject raw(proj_create_crs_to_crs_from_pj(
            context, source->handle, output->handle, nullptr, options));
        Require(raw.handle, "required operation unavailable");
        operationCache[key] = std::make_shared<ProjObject>(
            proj_normalize_for_visualization(context, raw.handle));
        Require(operationCache[key]->handle, "axis adaptation failed");
    }
    auto operation = operationCache[key]->handle;
    proj_errno_reset(operation);
    auto transformed = proj_trans(operation, PJ_FWD,
                                  proj_coord(point[0], point[1], point[2], HUGE_VAL));
    Require(!proj_errno(operation), "coordinate operation or required grid failed");
    Point3d result(transformed.xyz.x, transformed.xyz.y, transformed.xyz.z);
    RequireFinite(result);
    ProjObject lastUsed(proj_trans_get_last_used_operation(operation));
    PJ* realized = lastUsed.handle ? lastUsed.handle : operation;
    const char* pipeline = proj_as_proj_string(context, realized, PJ_PROJ_5, nullptr);
    double accuracy = proj_coordoperation_get_accuracy(context, realized);
    static const std::regex timeOperation(
        R"((?:^|\s)\+?(?:proj=(?:deformation|defmodel|velocitygrid)|d(?:x|y|z|rx|ry|rz|s)=))");
    Require(!pipeline || !std::regex_search(pipeline, timeOperation),
            "coordinate-epoch-dependent operation outside initial scope");
    JsonValue report(
        JsonObject{{"pipeline", JsonValue(pipeline ? pipeline : "")},
                   {"description",
                    JsonValue(proj_get_name(realized) ? proj_get_name(realized) : "")},
                   {"accuracy_m", accuracy < 0 ? JsonValue() : JsonValue(accuracy)}});
    if (seenOperations.insert(JsWriteToString(report)).second) {
        operations.push_back(report);
    }
    return result;
}

CrsInfo::CrsInfo(CoordinateEngine& engine, ProjHandle p, bool model)
    : engine(engine), crs(p)
{
    ReadAxes();
    if (model && unitNames.size() == 2) {
        assumedHeight = true;
        engine.diagnostics.push_back(JsonValue(
            "missing vertical reference: assuming EGM2008 height (EPSG:3855)"));
        double u = isGeographic ? 1 : componentUnits[0];
        std::string un = isGeographic ? "metre" : unitNames[0];
        std::ostringstream v;
        v << std::setprecision(17) << "COMPOUNDCRS[\"Horizontal with assumed EGM2008\","
          << engine.SerializeWkt(crs)
          << ",VERTCRS[\"EGM2008 height\",VDATUM[\"EGM2008 "
             "geoid\"],CS[vertical,1],AXIS[\"Gravity-related "
             "height\",up,LENGTHUNIT[\""
          << un << "\"," << u << "]]]]";
        crs = engine.ParseWkt(v.str());
        ReadAxes();
    }
    Require(!model || unitNames.size() == 3, "model requires complete 3D CRS");
}

void CrsInfo::ReadAxes()
{
    unitNames.clear();
    ProjObject cs(proj_crs_get_coordinate_system(engine.context, crs->handle));
    if (!cs.handle) {
        ProjObject h(proj_crs_get_sub_crs(engine.context, crs->handle, 0));
        Require(h.handle, "CRS has no coordinate system");
        ProjObject s(proj_crs_get_coordinate_system(engine.context, h.handle));
        Require(s.handle, "horizontal system unavailable");
        cs.handle = s.handle;
        s.handle = nullptr;
    }
    auto ty = proj_get_type(crs->handle);
    isGeographic = ty == PJ_TYPE_GEOGRAPHIC_2D_CRS || ty == PJ_TYPE_GEOGRAPHIC_3D_CRS;
    isGeocentric = ty == PJ_TYPE_GEOCENTRIC_CRS;
    int count = proj_cs_get_axis_count(engine.context, cs.handle);
    for (int i = 0; i < count; i++) {
        const char *direction = nullptr, *unit = nullptr;
        double factor = 1;
        proj_cs_get_axis_info(engine.context, cs.handle, i, nullptr, nullptr,
                              &direction, &factor, &unit, nullptr, nullptr);
        std::string d = direction ? direction : "";
        Require(d == "east" || d == "north" || d == "up" || d == "geocentricX" ||
                    d == "geocentricY" || d == "geocentricZ",
                "unsupported component directions");
        int slot = d == "east" || d == "geocentricX"    ? 0
                   : d == "north" || d == "geocentricY" ? 1
                                                        : 2;
        componentUnits[slot] = factor;
        unitNames.push_back(unit ? unit : "");
    }
    if (ty == PJ_TYPE_COMPOUND_CRS) {
        ProjObject h(proj_crs_get_sub_crs(engine.context, crs->handle, 0));
        auto ht = proj_get_type(h.handle);
        isGeographic =
            ht == PJ_TYPE_GEOGRAPHIC_2D_CRS || ht == PJ_TYPE_GEOGRAPHIC_3D_CRS;
        ProjObject v(proj_crs_get_sub_crs(engine.context, crs->handle, 1));
        ProjObject vc(proj_crs_get_coordinate_system(engine.context, v.handle));
        const char* unit = nullptr;
        double f = 1;
        proj_cs_get_axis_info(engine.context, vc.handle, 0, nullptr, nullptr, nullptr,
                              &f, &unit, nullptr, nullptr);
        componentUnits[2] = f;
        unitNames.push_back(unit ? unit : "");
    }
}

JsonValue CrsInfo::HeightReport()
{
    std::string kind, ref, unit;
    JsonValue reference;
    if (isGeocentric || unitNames.size() < 3) {
        kind = "none";
    }
    else if (proj_get_type(crs->handle) == PJ_TYPE_COMPOUND_CRS) {
        kind = "gravityRelated";
        ProjObject v(proj_crs_get_sub_crs(engine.context, crs->handle, 1));
        const char *auth = proj_get_id_auth_name(v.handle, 0),
                   *code = proj_get_id_code(v.handle, 0);
        reference = JsonValue(assumedHeight  ? "EPSG:3855"
                              : auth && code ? std::string(auth) + ":" + code
                                             : proj_get_name(v.handle));
        unit = unitNames.back();
    }
    else {
        kind = "ellipsoidal";
        ProjObject ell(proj_get_ellipsoid(engine.context, crs->handle));
        ProjObject dat(proj_crs_get_datum_forced(engine.context, crs->handle));
        reference = JsonValue(JsonObject{
            {"ellipsoid", JsonValue(ell.handle ? proj_get_name(ell.handle) : "")},
            {"datum", JsonValue(dat.handle ? proj_get_name(dat.handle) : "")}});
        unit = unitNames.back();
    }
    return JsonValue(JsonObject{
        {"heightModel", JsonValue(kind)},
        {"heightReference", reference},
        {"heightUnit", unit.empty() ? JsonValue() : JsonValue(unit)},
        {"heightReferenceSource", JsonValue(assumedHeight ? "assumed" : "declared")}});
}

} // namespace usdGeospatialExample
