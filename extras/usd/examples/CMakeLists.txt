set(PXR_PREFIX examples)
set(PXR_INSTALL_SUBDIR share/usd/examples)

if (EMSCRIPTEN)
	add_subdirectory(wasmFetchResolver)
else()
	add_subdirectory(usdObj)
	add_subdirectory(usdDancingCubesExample)
	add_subdirectory(usdRecursivePayloadsExample)
	add_subdirectory(usdResolverExample)
	add_subdirectory(usdSchemaExamples)
	add_subdirectory(usdMakeFileVariantModelAsset)

	# The geospatial scene-index example is opt-in (needs PROJ) and links
	# usdImaging/hd, so it additionally requires USD imaging to be built.
	if (PXR_ENABLE_GEOSPATIAL_SUPPORT AND PXR_BUILD_USD_IMAGING)
		add_subdirectory(usdGeospatialSceneIndex)
	endif()
endif()
