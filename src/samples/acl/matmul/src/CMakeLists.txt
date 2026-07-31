set(COMPONENT_NAME "npu_samples")

set(PUBLIC_HEADER_LIST
    ${CMAKE_CURRENT_SOURCE_DIR}
    "${ROOT_DIR}/include/middleware/services/ai/acl"
    "${ROOT_DIR}/include/middleware/utils"
    "${ROOT_DIR}/middleware/utils"
    "${ROOT_DIR}/application/samples/ai/npu/src"
)

set(SOURCES_LIST
    ${CMAKE_CURRENT_SOURCE_DIR}/utils.c
    ${CMAKE_CURRENT_SOURCE_DIR}/demo.c
)

set(LIBS
    PARENT_SCOPE
)

set(PRIVATE_DEFINES CHIP_VERSION=3322)

set(COMPONENT_CCFLAGS
    -Wno-strict-prototypes
)

add_subdirectory_if_exist(src)
set(SOURCES "${SOURCES_LIST}")

set(PUBLIC_HEADER "${PUBLIC_HEADER_LIST}" PARENT_SCOPE)
build_component()