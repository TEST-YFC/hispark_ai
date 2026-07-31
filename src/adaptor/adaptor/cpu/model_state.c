/**
 * Copyright (c) 2026-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
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
#include "model_state.h"

static ModelState    g_model_status[MAX_MODEL_NUM] = {MODEL_STATE_UNINIT};
static MSModelHandle g_model_handles[MAX_MODEL_NUM] = {NULL};

static inline bool IsValidStateTransition(ModelState curr, ModelState target)
{
    switch (curr) {
        case MODEL_STATE_UNINIT:
            return (target == MODEL_STATE_CREATED);
        case MODEL_STATE_CREATED:
            return (target == MODEL_STATE_BUILT || target == MODEL_STATE_UNINIT);
        case MODEL_STATE_BUILT:
            return (target == MODEL_STATE_UNINIT);
        default:
            return false;
    }
}

int ModelState_FindIndex(MSModelHandle handle)
{
    if (handle == NULL) {
        return INVALID_INDEX;
    }

    for (int i = 0; i < MAX_MODEL_NUM; i++) {
        if (g_model_handles[i] == handle) {
            return i;
        }
    }
    return INVALID_INDEX;
}

int ModelState_BindHandle(MSModelHandle handle)
{
    for (int i = 0; i < MAX_MODEL_NUM; i++) {
        if (g_model_status[i] == MODEL_STATE_UNINIT && g_model_handles[i] == NULL) {
            g_model_handles[i] = handle;
            g_model_status[i] = MODEL_STATE_CREATED;
            return i;
        }
    }
    return INVALID_INDEX;
}

bool ModelState_Check(int index, ModelState expect)
{
    return IS_INDEX_VALID(index) && g_model_status[index] == expect;
}

void ModelState_Transition(int index, ModelState target)
{
    if (!IS_INDEX_VALID(index) || !IsValidStateTransition(g_model_status[index], target)) {
        return;
    }

    if (target == MODEL_STATE_UNINIT) {
        g_model_handles[index] = NULL;
        g_model_status[index] = MODEL_STATE_UNINIT;
    } else {
        g_model_status[index] = target;
    }
}

bool ModelState_HasUnreleasedModel(void)
{
    for (int i = 0; i < MAX_MODEL_NUM; i++) {
        if (g_model_status[i] != MODEL_STATE_UNINIT) {
            return true;
        }
    }
    return false;
}