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
#ifndef MODEL_STATE_H
#define MODEL_STATE_H

#include "ai_mcu.h"

#ifdef __cplusplus
#if __cplusplus
extern "C" {
#endif
#endif

typedef enum {
    MODEL_STATE_UNINIT = 0,
    MODEL_STATE_CREATED,
    MODEL_STATE_BUILT
} ModelState;

#define MAX_MODEL_NUM 4
#define INVALID_INDEX  (-1)

#define IS_INDEX_VALID(index)  ((index) >= 0 && (index) < MAX_MODEL_NUM && g_model_handles[(index)] != NULL)

int ModelState_FindIndex(MSModelHandle handle);

int ModelState_BindHandle(MSModelHandle handle);

bool ModelState_Check(int index, ModelState expect);

void ModelState_Transition(int index, ModelState target);

bool ModelState_HasUnreleasedModel(void);

#ifdef __cplusplus
#if __cplusplus
}
#endif
#endif

#endif // MODEL_STATE_H