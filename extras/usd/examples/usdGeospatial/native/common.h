// Internal support for this example, not a proposed USD API.
#ifndef USD_GEOSPATIAL_EXAMPLE_COMMON_H
#define USD_GEOSPATIAL_EXAMPLE_COMMON_H
#include <cmath>
#include <pxr/base/gf/matrix4d.h>
#include <pxr/base/gf/vec3d.h>
#include <pxr/base/js/json.h>
#include <stdexcept>
#include <string>
#include <vector>
namespace usdGeospatialExample {
PXR_NAMESPACE_USING_DIRECTIVE
using JsonValue = JsValue;
using JsonObject = JsObject;
using JsonArray = JsArray;
using Point3d = GfVec3d;
using Matrix4d = GfMatrix4d;
inline void Require(bool condition, const std::string& message)
{
    if (!condition) {
        throw std::runtime_error(message);
    }
}
inline double ReadNumber(const JsonValue& value)
{
    return value.IsReal() ? value.GetReal() : double(value.GetInt64());
}
inline const JsonValue& GetField(const JsonValue& value, const std::string& key)
{
    return value.GetJsObject().at(key);
}
inline bool HasField(const JsonValue& value, const std::string& key)
{
    return value.IsObject() && value.GetJsObject().count(key);
}
inline Point3d ReadPoint(const JsonValue& value)
{
    auto a = value.GetJsArray();
    Require(a.size() == 3, "three coordinates required");
    return Point3d(ReadNumber(a[0]), ReadNumber(a[1]), ReadNumber(a[2]));
}
inline JsonValue PointToJson(Point3d point)
{
    return JsonValue(
        JsonArray{JsonValue(point[0]), JsonValue(point[1]), JsonValue(point[2])});
}
inline void RequireFinite(Point3d point)
{
    for (int i = 0; i < 3; i++) {
        Require(std::isfinite(point[i]), "non-finite placement or coordinate");
    }
}

} // namespace usdGeospatialExample
#endif
