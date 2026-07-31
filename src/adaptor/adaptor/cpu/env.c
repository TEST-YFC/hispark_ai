/**
 * Copyright (c) 2025-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
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
#include "std_def.h"
#include "ai_mcu.h"
#include "ai.h"

bool g_is_env_inited = false;
static OH_AI_Status errorCode = OH_AI_STATUS_SUCCESS;

OH_AI_Status OH_AI_Init(void* config_data, size_t data_size)
{
    UNUSED(config_data);
    UNUSED(data_size);
    if (g_is_env_inited) {
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
    g_is_env_inited = false;
    return OH_AI_STATUS_SUCCESS;
}

int32_t OH_AI_GetErrorCode(void)
{
    return (int32_t)errorCode;
}