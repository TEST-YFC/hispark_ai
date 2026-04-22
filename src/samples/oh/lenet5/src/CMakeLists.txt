if ("${CHIP_VERSION}" STREQUAL "")
    set(COMPONENT_NAME "npu_samples")

    set(PUBLIC_HEADER_LIST
        ${CMAKE_CURRENT_SOURCE_DIR}
        "${ROOT_DIR}/include/middleware/services/ai/acl"
        "${ROOT_DIR}/include/middleware/utils"
        "${ROOT_DIR}/middleware/utils"
        "${ROOT_DIR}/tools/bin/compiler/linx/linx_170/linx-llvm-binary-debug/linx-llvm-binary-release-musl/lib/clang/12.0.1/include"
        "${ROOT_DIR}/application/samples/ai/npu/src"
    )

    set(SOURCES_LIST
        ${CMAKE_CURRENT_SOURCE_DIR}/ai_deploy_main_npu.c
    )

    set(LIBS
        PARENT_SCOPE
    )

    set(PRIVATE_DEFINES CHIP_VERSION=3322)

    add_subdirectory_if_exist(src)
    set(SOURCES "${SOURCES_LIST}")

    set(PUBLIC_HEADER "${PUBLIC_HEADER_LIST}" PARENT_SCOPE)
    build_component()
elseif ("${CHIP_VERSION}" STREQUAL "1156")
    project(lenet1156 LANGUAGES C)

    set(CMAKE_C_COMPILER ${COMPILER_PATH}/bin/arm-linux-musleabi-gcc)
    set(CMAKE_CXX_COMPILER ${COMPILER_PATH}/bin/arm-linux-musleabi-g++)

    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} \
        -Wno-strict-prototypes \
        -std=c99 \
        -fPIC \
        -mcpu=cortex-a55 \
        -mfloat-abi=soft \
    ")

    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} \
        -fPIC \
        -mcpu=cortex-a55 \
        -mfloat-abi=soft \
    ")

    set(COMPILER_LIB_DIR "${COMPILER_PATH}/lib")

    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} \
        -Wl,-rpath-link=${LIB_PATH} \
        -Wl,-rpath=${LIB_PATH} \
        -Wl,-rpath-link=${COMPILER_LIB_DIR} \
        -Wl,-rpath=${COMPILER_LIB_DIR} \
        -L${LIB_PATH} \
        -L${COMPILER_LIB_DIR} \
        -Wl,--warn-unresolved-symbols \
    ")

    set(SOURCES
        ${CMAKE_CURRENT_SOURCE_DIR}/ai_deploy_main_npu.c
    )

    include_directories(
        ${ADAPTOR_PATH}/include
    )

    add_executable(${PROJECT_NAME} ${SOURCES})

    target_compile_definitions(${PROJECT_NAME} PRIVATE CHIP_VERSION=1156)

    add_compile_definitions(_POSIX_C_SOURCE=200809L)

    target_link_libraries(${PROJECT_NAME}
        ${ADAPTOR_SO_PATH}
        -lstdc++
        -lpthread
        -lm
    )
endif()
