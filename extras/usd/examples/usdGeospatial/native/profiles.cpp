#include "profiles.h"
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdProfiles/claimsAPI.h>
#include <pxr/usd/usdProfiles/profileRegistry.h>

namespace usdGeospatialExample {
JsonValue ExecuteProfilesRequest(const JsonValue& request)
{
    const bool publishing = HasField(request, "publishStage");
    const char* key = publishing ? "publishStage" : "profilesStage";
    auto stage = UsdStage::Open(GetField(request, key).GetString(), UsdStage::LoadNone);
    Require(bool(stage), "Profiles stage unavailable");
    auto prim = stage->GetDefaultPrim();
    auto claims = UsdProfilesClaimsAPI(prim);
    const TfToken capability("usd.geospatial.crsResolution.v1");
    const TfToken profile("usd.geospatial.publication.v1");

    if (publishing) {
        claims = UsdProfilesClaimsAPI::Apply(prim);
        auto usages = claims.GetCapabilityUsages();
        usages.erase(capability.GetString());
        if (GetField(request, "requires").GetBool()) {
            usages[capability.GetString()] = VtValue(TfToken("hard"));
        }
        claims.SetCapabilityUsages(usages);
        if (GetField(request, "complete").GetBool()) {
            claims.SetProfileCompatible(profile);
        }
        stage->GetRootLayer()->Save();
    }

    JsonArray profiles;
    for (const auto& compatible : claims.GetCompatibleProfiles()) {
        profiles.push_back(JsonValue(compatible.GetString()));
    }
    JsonArray implied;
    for (const auto& name : UsdProfileRegistry::GetSchemaImpliedCapabilities(
             TfType::FindByName("UsdGeospatialCRSBindingAPI"))) {
        implied.push_back(JsonValue(name.GetString()));
    }
    return JsonValue(JsonObject{
        {"bindingImpliedCapabilities", JsonValue(implied)},
        {"success", JsonValue(true)},
        {"hardUsage", JsonValue(claims.GetCapabilityUsage(capability).GetString())},
        {"profiles", JsonValue(profiles)},
        {"loadedPayloads", JsonValue(int(stage->GetLoadSet().size()))},
        {"ClaimsAPI", JsonValue(bool(claims))}});
}
} // namespace usdGeospatialExample
