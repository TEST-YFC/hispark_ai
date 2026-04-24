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
#ifndef MCU_MODEL_H
#define MCU_MODEL_H

#include "acl_mdl.h"
#include "acl_base.h"
#include "tensor.h"
#include "context.h"

#define DESTORYALL (-1)

typedef struct {
    uint32_t model_id;
    ContextInfo *context;
    aclmdlDesc *model_desc;
    aclrtStream model_stream;
    aclmdlDataset *input_dataset;
    aclmdlDataset *output_dataset;
    void *weight;
    size_t weight_size;
    void *workspace;
    size_t work_size;
    NPUTensor **inputs;
    size_t input_count;
    NPUTensor **outputs;
    size_t output_count;
    bool is_model_loaded;
} ModelInfo;

#endif /* MCU_MODEL_H */