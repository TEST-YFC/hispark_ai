/**
 * Copyright (c) 2025-2025 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#if defined(PROCESSOR_TYPE_NANO)
#include "std_def.h"
#endif
#include "acl_rt.h"
#include "acl.h"
#include "ai.h"

OH_AI_Status error_code = OH_AI_STATUS_SUCCESS;
int32_t g_device_id = 0;
bool g_is_env_inited = false;

OH_AI_Status OH_AI_InitFromFile(char* config_file_path)
{
    if (g_is_env_inited) {
        return OH_AI_STATUS_FAILED;
    }

    aclError ret;
    ret = aclInit(config_file_path);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return OH_AI_STATUS_FAILED;
    }

    ret = aclrtSetDevice(g_device_id);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        aclFinalize();
        return OH_AI_STATUS_FAILED;
    }

    g_is_env_inited = true;
    return OH_AI_STATUS_SUCCESS;
}

OH_AI_Status OH_AI_Deinit(void)
{
    if (!g_is_env_inited) {
        return OH_AI_STATUS_FAILED;
    }

    aclError ret;
    ret = aclrtResetDevice(g_device_id);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return OH_AI_STATUS_FAILED;
    }

    ret = aclFinalize();
    if (ret != ACL_SUCCESS) {
        return OH_AI_STATUS_FAILED;
    }

    g_is_env_inited = false;
    return OH_AI_STATUS_SUCCESS;
}

int32_t OH_AI_GetErrorCode(void)
{
    return (int32_t)error_code;
}