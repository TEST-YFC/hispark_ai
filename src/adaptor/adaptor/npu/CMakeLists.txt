if ("${CHIP_VERSION}" STREQUAL "")
    set(COMPONENT_NAME "ai_adaptor_nano")

    set(SOURCES
        ${CMAKE_CURRENT_SOURCE_DIR}/env.c
        ${CMAKE_CURRENT_SOURCE_DIR}/context.c
        ${CMAKE_CURRENT_SOURCE_DIR}/model.c
        ${CMAKE_CURRENT_SOURCE_DIR}/tensor.c
    )

    set(PUBLIC_HEADER
        ${CMAKE_CURRENT_SOURCE_DIR}
        "${ROOT_DIR}/include/middleware/services/ai/acl"
        "${ROOT_DIR}/include/middleware/utils"
    )

    set(LIBS
        ${ROOT_DIR}/interim_binary/3322/libs/npu/3322-wstp-app/turing/libascendcl.a
    )

    set(PRIVATE_DEFINES PROCESSOR_TYPE_NANO)

    # use this when you want to add ccflags like -include xxx
    set(COMPONENT_PUBLIC_CCFLAGS)

    set(COMPONENT_CCFLAGS
        -Wno-strict-prototypes
    )

    set(WHOLE_LINK
        true
    )

    set(MAIN_COMPONENT
        false
    )

    build_component()
    # install_sdk(${CMAKE_CURRENT_SOURCE_DIR} "*.h")
elseif ("${CHIP_VERSION}" STREQUAL "1156")
    project(ai_adaptor_tiny LANGUAGES C)

    set(AI_ADAPTOR_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../")

    set(LIB_PATH "${AI_ADAPTOR_ROOT}/../ai_sample_test/lib" CACHE PATH "")

    set(CMAKE_C_COMPILER ${COMPILER_PATH}/bin/arm-linux-musleabi-gcc)
    set(CMAKE_CXX_COMPILER ${COMPILER_PATH}/bin/arm-linux-musleabi-g++)

    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wno-strict-prototypes -std=c99 -fPIC -mcpu=cortex-a55 -mfloat-abi=soft")
    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -fPIC -mcpu=cortex-a55 -mfloat-abi=soft")

    set(SOURCES
        ${CMAKE_CURRENT_SOURCE_DIR}/env.c
        ${CMAKE_CURRENT_SOURCE_DIR}/context.c
        ${CMAKE_CURRENT_SOURCE_DIR}/model.c
        ${CMAKE_CURRENT_SOURCE_DIR}/tensor.c
    )

    include_directories(
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${AI_ADAPTOR_ROOT}/include
        ${ACL_HEADER_PATH}
    )

    add_library(${PROJECT_NAME} SHARED ${SOURCES})

    target_compile_definitions(${PROJECT_NAME} PRIVATE PROCESSOR_TYPE_TINY)

    target_link_libraries(${PROJECT_NAME}
        ${LIB_PATH}/libascend_protobuf.so.3.13.0.0
        ${LIB_PATH}/libascend_dump.so
        ${LIB_PATH}/libascend_hal.so
        ${LIB_PATH}/libascend_watchdog.so
        ${LIB_PATH}/libascendalog.so
        ${LIB_PATH}/libascendcl_impl.so
        ${LIB_PATH}/libascendcl.so
        ${LIB_PATH}/libc_sec.so
        ${LIB_PATH}/libdavinci_executor.so
        ${LIB_PATH}/liberror_manager.so
        ${LIB_PATH}/libexe_graph.so
        ${LIB_PATH}/libge_common_base.so
        ${LIB_PATH}/libge_common.so
        ${LIB_PATH}/libge_executor.so
        ${LIB_PATH}/libgert.so
        ${LIB_PATH}/libgraph_base.so
        ${LIB_PATH}/libgraph.so
        ${LIB_PATH}/libhybrid_executor.so
        ${LIB_PATH}/liblowering.so
        ${LIB_PATH}/libmmpa.so
        ${LIB_PATH}/libmsprofiler.so
        ${LIB_PATH}/libplatform.so
        ${LIB_PATH}/libprofapi.so
        ${LIB_PATH}/libprofimpl.so
        ${LIB_PATH}/libqos_manager.so
        ${LIB_PATH}/libregister.so
        ${LIB_PATH}/libruntime_common.so
        ${LIB_PATH}/libruntime_v100.so
        ${LIB_PATH}/libruntime.so
        ${LIB_PATH}/libslog.so
    )
endif()