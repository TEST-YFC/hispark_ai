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
#include "acl_rt.h"
#include "ai.h"
#include "env.h"
#include "context.h"

static ContextInfo *g_singleton_context = NULL;

OH_AI_ContextHandle OH_AI_ContextCreate(void)
{
    if (!g_is_env_inited || g_singleton_context != NULL) {
        return NULL;
    }

    ContextInfo *context_info = NULL;
    aclError ret = aclrtMalloc(&context_info, sizeof(ContextInfo), ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return NULL;
    }
    if (context_info == NULL) {
        return NULL;
    }

    aclrtContext context;
    ret = aclrtCreateContext(&context, g_device_id);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return NULL;
    }
    context_info->context = context;
    context_info->model_count = 0;
    g_singleton_context = context_info;

    return (OH_AI_ContextHandle)context_info;
}

void OH_AI_ContextDestroy(OH_AI_ContextHandle *context)
{
    if (context == NULL || *context == NULL) {
        return;
    }

    ContextInfo *context_info = (ContextInfo *)*context;
    if (context_info->model_count != 0 || g_singleton_context != context_info) {
        return;
    }

    aclError ret;
    ret = aclrtDestroyContext(context_info->context);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return;
    }

    aclrtFree(context_info);
    g_singleton_context = NULL;
    *context = NULL;
}