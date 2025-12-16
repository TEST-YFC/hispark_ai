set(COMPONENT_NAME "npu_samples")

set(PUBLIC_HEADER_LIST
    ${CMAKE_CURRENT_SOURCE_DIR}
    "${ROOT_DIR}/include/middleware/services/ai/npu/acl"
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

add_subdirectory_if_exist(src)
set(SOURCES "${SOURCES_LIST}")


set(PUBLIC_HEADER "${PUBLIC_HEADER_LIST}" PARENT_SCOPE)
build_component()
