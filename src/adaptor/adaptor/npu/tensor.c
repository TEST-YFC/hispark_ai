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
#include "tensor.h"
#include "ai.h"

size_t OH_AI_TensorGetDataSize(const OH_AI_TensorHandle tensor)
{
    if (tensor == NULL) {
        return 0;
    }

    NPUTensor *np_tensor = (NPUTensor *)tensor;
    return np_tensor->size;
}

const int64_t *OH_AI_TensorGetShape(const OH_AI_TensorHandle tensor, size_t *shape_num)
{
    if (tensor == NULL || shape_num == NULL) {
        return NULL;
    }

    NPUTensor *np_tensor = (NPUTensor *)tensor;
    *shape_num = np_tensor->shape_len;
    return np_tensor->shape;
}

int64_t OH_AI_TensorGetElementNum(const OH_AI_TensorHandle tensor)
{
    if (tensor == NULL) {
        return -1;
    }
    NPUTensor *np_tensor = (NPUTensor *)tensor;
    if (np_tensor->shape_len == 0 || np_tensor->shape == NULL) {
        return 0;
    }
    int64_t element_num = 1;
    for (size_t i = 0; i < np_tensor->shape_len; i++) {
        element_num *= np_tensor->shape[i];
    }
    return element_num;
}

OH_AI_DataType OH_AI_TensorGetDataType(const OH_AI_TensorHandle tensor)
{
    if (tensor == NULL) {
        return OH_AI_DATATYPE_UNKNOWN;
    }
    NPUTensor *np_tensor = (NPUTensor *)tensor;
    return np_tensor->data_type;
}

void *OH_AI_TensorGetMutableData(const OH_AI_TensorHandle tensor)
{
    if (tensor == NULL) {
        return NULL;
    }

    NPUTensor *np_tensor = (NPUTensor *)tensor;
    return np_tensor->data;
}
