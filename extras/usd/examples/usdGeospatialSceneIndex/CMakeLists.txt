# usdGeospatialSceneIndex -- in-tree example plugin (pxr_plugin pattern).
#
# Mirrors extras/imaging/examples/hdParticleField/CMakeLists.txt, but builds an
# HdSceneIndexPlugin (a FILTER that rewrites xforms) plus a keyless UsdImaging
# API-schema adapter, and links PROJ (the CRS engine; WKT stays opaque to USD).
#
# Enabled via -DPXR_ENABLE_GEOSPATIAL_SUPPORT=ON (build_usd.py --usdGeospatial),
# which makes cmake/defaults/Packages.cmake run find_package(PROJ REQUIRED) and
# provide the PROJ::proj imported target used below.

set(PXR_PACKAGE usdGeospatialSceneIndex)

pxr_plugin(${PXR_PACKAGE}
    LIBRARIES
        tf
        gf
        sdf
        vt
        work
        plug
        usd
        usdGeom
        hd
        hf
        usdImaging
        PROJ::proj

    PUBLIC_CLASSES
        crsEngine
        geoResolver
        geospatialAPISchemaAdapter
        geospatialSceneIndex
        geospatialSceneIndexPlugin
        geospatialSchema

    PUBLIC_HEADERS
        api.h

    RESOURCE_FILES
        plugInfo.json

    DISABLE_PRECOMPILED_HEADERS
)

# api.h guards its export macro on USDGEOSPATIAL_SI_EXPORTS, but pxr_library
# defines the target-derived USDGEOSPATIALSCENEINDEX_EXPORTS. Define the name
# api.h actually checks so USDGEOSPATIAL_SI_API resolves to dllexport when the
# plugin is built (otherwise every marked symbol compiles as dllimport).
target_compile_definitions(${PXR_PACKAGE} PRIVATE USDGEOSPATIAL_SI_EXPORTS=1)

# -----------------------------------------------------------------------------
# Parity tests: the C++ CRS engine / stage resolver / Hydra scene index must
# agree with the Python reference runtime + closed-form geodesy to sub-mm. These
# compile the needed plugin sources directly (the plugin is a loadable MODULE,
# not a linkable library). Registered as ctest tests via a Python driver below.
if (PXR_BUILD_TESTS)
    pxr_build_test(testUsdGeospatialCrsEngine
        LIBRARIES
            arch tf gf vt work plug usd
            PROJ::proj
        CPPFILES
            testCrsEngine.cpp
            crsEngine.cpp
    )
    pxr_build_test(testUsdGeospatialResolver
        LIBRARIES
            arch tf gf vt work plug sdf usd usdGeom hd hf usdImaging
            PROJ::proj
        CPPFILES
            testGeoResolver.cpp
            geoResolver.cpp
            crsEngine.cpp
            geospatialSchema.cpp
    )
    pxr_build_test(testUsdGeospatialSceneIndex
        LIBRARIES
            arch tf gf vt work plug sdf usd usdGeom hd hf usdImaging
            PROJ::proj
        CPPFILES
            testSceneIndexParity.cpp
            geospatialSceneIndex.cpp
            geoResolver.cpp
            crsEngine.cpp
            geospatialSchema.cpp
    )
    # Stage-free auto-insertion proof: no SetStage; crs:* must be surfaced by the
    # keyless adapter from the LOADED plugin (PXR_PLUGINPATH_NAME). Headless twin
    # of the usdview screenshot.
    pxr_build_test(testUsdGeospatialHydraAuto
        LIBRARIES
            arch tf gf vt work plug sdf usd usdGeom hd hf usdImaging
            PROJ::proj
        CPPFILES
            testHydraAutoParity.cpp
            geospatialSceneIndex.cpp
            geoResolver.cpp
            crsEngine.cpp
            geospatialSchema.cpp
    )
    # dumpHydraXforms: the Hydra-resolved-xform dumper that feeds
    # ../usdGeospatial/fig_runtime_parity.py (the two-runtime parity figure).
    # Built here (via the test path) so that figure is reproducible cross-platform.
    pxr_build_test(dumpHydraXforms
        LIBRARIES
            arch tf gf vt work plug sdf usd usdGeom hd hf usdImaging
            PROJ::proj
        CPPFILES
            dumpHydraXforms.cpp
            geospatialSceneIndex.cpp
            geoResolver.cpp
            crsEngine.cpp
            geospatialSchema.cpp
    )
    # The test sources use USDGEOSPATIAL_SI_API too; define the export macro so
    # the compiled-in classes are consistent (matches build_standalone.sh).
    foreach(_geoTest testUsdGeospatialCrsEngine testUsdGeospatialResolver
                     testUsdGeospatialSceneIndex testUsdGeospatialHydraAuto
                     dumpHydraXforms)
        if (TARGET ${_geoTest})
            target_compile_definitions(${_geoTest} PRIVATE USDGEOSPATIAL_SI_EXPORTS=1)
        endif()
    endforeach()

    # One ctest that generates the Python oracle then runs all three C++ parity
    # tests against it (0.0 mm expected). run_parity.py is installed to
    # <inst>/tests; it locates the oracle generators in the source tree via
    # GEO_SRC_DIR and the compiled test exes via GEO_TEST_BIN.
    pxr_test_scripts(run_parity.py)
    pxr_register_test(testUsdGeospatialParity
        PYTHON
        COMMAND "${CMAKE_INSTALL_PREFIX}/tests/run_parity"
        ENV
            USD_INST=${CMAKE_INSTALL_PREFIX}
            GEO_TEST_BIN=${CMAKE_INSTALL_PREFIX}/tests
            GEO_SRC_DIR=${CMAKE_CURRENT_SOURCE_DIR}
        EXPECTED_RETURN_CODE 0
    )

    # The VISUAL two-runtime parity gate on the REAL railway stage: convert the
    # shipped asset, dump the compiled Hydra scene index's xforms, and self-assert
    # the Python-reference-vs-Hydra per-vertex disagreement stays sub-mm (fails the
    # build if it exceeds GEO_TOL_MM). Reuses the dumpHydraXforms exe built above.
    pxr_test_scripts(run_runtime_parity.py)
    pxr_register_test(testUsdGeospatialRuntimeParity
        PYTHON
        COMMAND "${CMAKE_INSTALL_PREFIX}/tests/run_runtime_parity"
        ENV
            USD_INST=${CMAKE_INSTALL_PREFIX}
            GEO_TEST_BIN=${CMAKE_INSTALL_PREFIX}/tests
            GEO_SRC_DIR=${CMAKE_CURRENT_SOURCE_DIR}
            GEO_TOL_MM=1.0
        EXPECTED_RETURN_CODE 0
    )
endif()
