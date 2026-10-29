project(tiny_sample LANGUAGES C)

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
set(SECURE_LIB_DIR "${COMPILER_PATH}/target/usr/lib/a55_soft")

set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} \
    -Wl,-rpath-link=${LIB_PATH} \
    -Wl,-rpath=${LIB_PATH} \
    -Wl,-rpath-link=${COMPILER_LIB_DIR} \
    -Wl,-rpath=${COMPILER_LIB_DIR} \
    -Wl,-rpath-link=${SECURE_LIB_DIR} \
    -L${LIB_PATH} \
    -L${COMPILER_LIB_DIR} \
    -L${SECURE_LIB_DIR} \
    -Wl,--warn-unresolved-symbols \
")

set(SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/utils.c
    ${CMAKE_CURRENT_SOURCE_DIR}/demo.c
)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${ADAPTOR_PATH}/include
    ${ACL_HEADER_PATH}
)

add_executable(${PROJECT_NAME} ${SOURCES})

target_compile_definitions(${PROJECT_NAME} PRIVATE CHIP_VERSION=tiangong2)

add_compile_definitions(_POSIX_C_SOURCE=200809L)

target_link_libraries(${PROJECT_NAME}
    ${LIB_PATH}/libacl_rt.so
    ${LIB_PATH}/libacl_mdl.so
    ${SECURE_LIB_DIR}/libsecurec.so
    -lstdc++
    -lpthread
    -lm
)
