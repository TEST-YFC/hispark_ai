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
#include "ai_mcu.h"
#include "ai.h"
#include "env.h"
#include "model_state.h"

#ifdef __cplusplus
#if __cplusplus
extern "C" {
#endif
#endif

static MSContextHandle g_singleton_context = NULL;

OH_AI_ContextHandle OH_AI_ContextCreate(void)
{
    if (!g_is_env_inited || g_singleton_context != NULL) {
        return NULL;
    }
    MSContextHandle ctx = MSContextCreate();
    if (ctx != NULL) {
        g_singleton_context = ctx;
    }
    return (OH_AI_ContextHandle)ctx;
}

void OH_AI_ContextDestroy(OH_AI_ContextHandle *context)
{
    if (context == NULL || *context == NULL || g_singleton_context != (MSContextHandle)*context ||
        ModelState_HasUnreleasedModel()) {
        return;
    }

    MSContextDestroy((MSContextHandle*)context);
    g_singleton_context = NULL;
}

#ifdef __cplusplus
#if __cplusplus
}
#endif
#endif