#pragma once
#include "pxr/pxr.h"
#include "pxr/usd/usd/stage.h"
#include "pxr/base/gf/matrix4d.h"
#include "pxr/base/gf/vec3d.h"
#include "pxr/imaging/hd/sceneIndex.h"
#include <string>
#ifdef BUILD_PLACEMENT
#define GEO_API __declspec(dllexport)
#else
#define GEO_API __declspec(dllimport)
#endif
GEO_API void Configure(pxr::UsdStageRefPtr,const std::string&,double,const pxr::GfVec3d&,const std::string&);
GEO_API pxr::GfMatrix4d CandidateFrame(const pxr::UsdPrim&);
GEO_API pxr::GfVec3d CandidateCoordinate(const pxr::UsdPrim&,const pxr::GfVec3d&);
GEO_API pxr::GfVec3d CandidateFullPoint(const pxr::UsdPrim&,const pxr::GfVec3d&);
GEO_API std::string CandidateOperation();
GEO_API double CandidateAccuracy();
GEO_API std::string CandidateProjVersion();
GEO_API size_t CandidateFilterReads();
GEO_API pxr::HdSceneIndexBaseRefPtr CandidateSceneIndex(const pxr::HdSceneIndexBaseRefPtr&);
GEO_API pxr::GfVec3d CandidateRenderCoordinate(const pxr::GfVec3d&);
