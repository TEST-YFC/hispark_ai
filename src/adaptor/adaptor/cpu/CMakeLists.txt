set(COMPONENT_NAME "ai_adaptor_cpu")

if(EXISTS "${ROOT_DIR}/middleware/utils/ai_mcu/micro_gen")
    file(REMOVE_RECURSE "${CMAKE_CURRENT_SOURCE_DIR}/build_lib")
    add_subdirectory("${ROOT_DIR}/middleware/utils/ai_mcu/micro_gen" "${ROOT_DIR}/middleware/utils/ai_mcu/build_lib")
    set(LIBS
        "${ROOT_DIR}/middleware/utils/ai_mcu/build_lib/libmicro_runtime.a"
        "${ROOT_DIR}/middleware/utils/ai_mcu/build_lib/src/libnet.a"
    )
elseif(EXISTS "${ROOT_DIR}/middleware/utils/ai_mcu/lib")
    set(LIBS
        "${ROOT_DIR}/middleware/utils/ai_mcu/lib/libmicro_runtime.a"
        "${ROOT_DIR}/middleware/utils/ai_mcu/lib/libnet.a"
    )
endif()

if(EXISTS "${ROOT_DIR}/middleware/utils/ai_mcu/micro_gen" OR EXISTS "${ROOT_DIR}/middleware/utils/ai_mcu/lib")
    set(SOURCES
        ${CMAKE_CURRENT_SOURCE_DIR}/env.c
        ${CMAKE_CURRENT_SOURCE_DIR}/context.c
        ${CMAKE_CURRENT_SOURCE_DIR}/model.c
        ${CMAKE_CURRENT_SOURCE_DIR}/tensor.c
        ${CMAKE_CURRENT_SOURCE_DIR}/model_state.c
        ${CMAKE_CURRENT_SOURCE_DIR}/dump/dump.c
        ${CMAKE_CURRENT_SOURCE_DIR}/load/load.c
        ${CMAKE_CURRENT_SOURCE_DIR}/infer/infer.c
    )
    set(PUBLIC_HEADER
        ${CMAKE_CURRENT_SOURCE_DIR}
        "${ROOT_DIR}/middleware/utils/ai_mcu/include"
        "${ROOT_DIR}/middleware/utils/ai_mcu/adaptor/cpu/include"
        "${ROOT_DIR}/include/middleware/utils"
    )
endif()

# use this when you want to add ccflags like -include xxx
set(COMPONENT_PUBLIC_CCFLAGS
)

set(COMPONENT_CCFLAGS
)

set(WHOLE_LINK
    true
)

set(MAIN_COMPONENT
    false
)

build_component()
install_sdk(${CMAKE_CURRENT_SOURCE_DIR} "*.h")