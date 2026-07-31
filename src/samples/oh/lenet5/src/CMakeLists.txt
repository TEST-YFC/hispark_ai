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
elseif ("${CHIP_VERSION}" STREQUAL "1155")
    cmake_minimum_required(VERSION 3.14.1)
    project(ai_sample_mcu C CXX)

    set(CMAKE_C_COMPILER ${COMPILER_PATH}/bin/arm-linux-musleabi-gcc)
    set(CMAKE_CXX_COMPILER ${COMPILER_PATH}/bin/arm-linux-musleabi-g++)
    set(CMAKE_STRIP ${COMPILER_PATH}/bin/arm-linux-musleabi-strip)

    set(link_lib_list
        stdc++
    )

    link_directories(
        ${link_so_dir}
        ${cann_so_dir}
        ${link_secure_dir}
    )

    set(src_list
        ${CMAKE_CURRENT_SOURCE_DIR}/ai_deploy_main_arm.c
        ${ADAPTOR_PATH}/adaptor/cpu/micro_gen/src/context.c
        ${ADAPTOR_PATH}/adaptor/cpu/micro_gen/src/model.c
        ${ADAPTOR_PATH}/adaptor/cpu/micro_gen/src/model0/model0.c
        ${ADAPTOR_PATH}/adaptor/cpu/micro_gen/src/model0/net0.c
        ${ADAPTOR_PATH}/adaptor/cpu/micro_gen/src/model0/weight0.c
        ${ADAPTOR_PATH}/adaptor/cpu/micro_gen/src/allocator.c
        ${ADAPTOR_PATH}/adaptor/cpu/micro_gen/src/tensor.c

        ${ADAPTOR_PATH}/adaptor/cpu/tensor.c
        ${ADAPTOR_PATH}/adaptor/cpu/context.c
        ${ADAPTOR_PATH}/adaptor/cpu/env.c
        ${ADAPTOR_PATH}/adaptor/cpu/model_state.c
        ${ADAPTOR_PATH}/adaptor/cpu/model.c
    )

    add_executable(ai_sample_mcu
        ${src_list}
    )

    target_include_directories(ai_sample_mcu
                            PRIVATE
                            ${MSLITE_PATH}/runtime/
                            ${MSLITE_PATH}/runtime/include/
                            ${MSLITE_PATH}/tools/codegen/include/
                            ${ADAPTOR_PATH}/adaptor/cpu/micro_gen/src/model0/
                            ${ADAPTOR_PATH}/adaptor/cpu/micro_gen/include/
                            ${ADAPTOR_PATH}/adaptor/cpu/micro_gen/
                            ${ADAPTOR_PATH}/adaptor/cpu/include
                            ${ADAPTOR_PATH}/include
    )

    target_link_libraries(ai_sample_mcu PRIVATE
        ${link_option}
        ${link_lib_list}
    )

    target_link_libraries(ai_sample_mcu PRIVATE ${MSLITE_PATH}/tools/codegen/lib/arm/libnnacl.a)
    target_link_libraries(ai_sample_mcu PRIVATE ${MSLITE_PATH}/tools/codegen/lib/arm/libwrapper.a)

    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,-rpath-link=${link_so_dir}")

    target_compile_options(
        ai_sample_mcu
        PRIVATE
        ${compiler_config}
    )

    add_custom_command(TARGET ai_sample_mcu POST_BUILD
        COMMAND ${CMAKE_STRIP} ai_sample_mcu
    )
endif()
