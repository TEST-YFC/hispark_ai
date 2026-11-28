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
#include <string.h>

#ifdef __cplusplus
#if __cplusplus
extern "C" {
#endif
#endif

extern MSModelHandle MSGetModelByIndex(size_t index, const char **file) __attribute__((weak));

typedef struct {
    const char *filename;
    size_t stem_len;
    MSModelHandle native;
} ModelSource;

typedef struct {
    ModelState state;
    MSModelHandle native;
} ModelSlot;

static ModelSource g_sources[MAX_MODEL_NUM];
static ModelSlot g_slots[MAX_MODEL_NUM];
static size_t g_count;

bool ModelState_Init(void)
{
    ModelSource sources[MAX_MODEL_NUM] = {0};

    memset(g_sources, 0, sizeof(g_sources));
    memset(g_slots, 0, sizeof(g_slots));
    g_count = 0;
    if (MSGetModelByIndex == NULL) {
        g_count = 1;
        return true;
    }
    for (size_t i = 0; i <= MAX_MODEL_NUM; ++i) {
        const char *file = NULL;
        MSModelHandle native = MSGetModelByIndex(i, &file);
        if (native == NULL) {
            if (i == 0) {
                return false;
            }
            memcpy(g_sources, sources, i * sizeof(sources[0]));
            g_count = i;
            return true;
        }
        if (i == MAX_MODEL_NUM || file == NULL || *file == '\0') {
            return false;
        }
        const char *dot = strrchr(file, '.');
        size_t len = (dot != NULL && dot != file) ? (size_t)(dot - file) : strlen(file);
        for (size_t j = 0; j < i; ++j) {
            if (native == sources[j].native ||
                (len == sources[j].stem_len && memcmp(file, sources[j].filename, len) == 0)) {
                return false;
            }
        }
        sources[i] = (ModelSource){file, len, native};
    }
    return false;
}

void ModelState_Clear(void)
{
    memset(g_sources, 0, sizeof(g_sources));
    memset(g_slots, 0, sizeof(g_slots));
    g_count = 0;
}

OH_AI_ModelHandle ModelState_Reserve(void)
{
    for (size_t i = 0; i < g_count; ++i) {
        if (g_slots[i].state == MODEL_STATE_UNINIT) {
            if (MSGetModelByIndex == NULL) {
                g_slots[i].native = MSModelCreate();
                if (g_slots[i].native == NULL) {
                    return NULL;
                }
            }
            g_slots[i].state = MODEL_STATE_CREATED;
            return &g_slots[i];
        }
    }
    return NULL;
}

static ModelSlot *FindSlot(OH_AI_ModelHandle model)
{
    for (size_t i = 0; i < g_count; ++i) {
        if (model == &g_slots[i] && g_slots[i].state != MODEL_STATE_UNINIT) {
            return &g_slots[i];
        }
    }
    return NULL;
}

MSModelHandle ModelState_Select(OH_AI_ModelHandle model, const char *name)
{
    ModelSlot *slot = FindSlot(model);
    if (slot == NULL || slot->state != MODEL_STATE_CREATED) {
        return NULL;
    }
    if (MSGetModelByIndex == NULL) {
        return name == NULL ? slot->native : NULL;
    }
    size_t len = name == NULL ? 0 : strlen(name);
    for (size_t i = 0; i < g_count; ++i) {
        const ModelSource *src = &g_sources[i];
        if (name != NULL && (src->stem_len != len || memcmp(src->filename, name, len) != 0)) {
            continue;
        }
        for (size_t j = 0; j < g_count; ++j) {
            if (g_slots[j].native == src->native) {
                return NULL;
            }
        }
        return src->native;
    }
    return NULL;
}

void ModelState_SetBuilt(OH_AI_ModelHandle model, MSModelHandle native)
{
    ModelSlot *slot = FindSlot(model);
    if (slot == NULL || native == NULL) {
        return;
    }
    slot->native = native;
    slot->state = MODEL_STATE_BUILT;
}

MSModelHandle ModelState_BuiltHandle(OH_AI_ModelHandle model)
{
    ModelSlot *slot = FindSlot(model);
    return slot != NULL && slot->state == MODEL_STATE_BUILT ? slot->native : NULL;
}

void ModelState_Release(OH_AI_ModelHandle model)
{
    ModelSlot *slot = FindSlot(model);
    if (slot != NULL) {
        if (slot->native != NULL) {
            MSModelDestroy(&slot->native);
        }
        slot->native = NULL;
        slot->state = MODEL_STATE_UNINIT;
    }
}

bool ModelState_HasUnreleasedModel(void)
{
    for (size_t i = 0; i < g_count; ++i) {
        if (g_slots[i].state != MODEL_STATE_UNINIT) {
            return true;
        }
    }
    return false;
}

#ifdef __cplusplus
#if __cplusplus
}
#endif
#endif
