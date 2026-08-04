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

#ifndef LENET5_UTILS_H
#define LENET5_UTILS_H

#include "acl/acl.h"
#include "osal_debug.h"

#define INPUT_NUM 1
#define OUTPUT_NUM 1
#define OUTPUT_DATA_NUM 10
#define MAX_FILE_NAME_LEN 256

typedef enum Result {
    SUCCESS = 0,
    FAILED = 1
} Result;

typedef struct {
    aclmdlDataset *input;
    aclmdlDataset *output;
    void *weight;
    size_t weightSize;
    void *workspace;
    size_t workSize;
} MemInfo;

typedef struct {
    char modelFile[MAX_FILE_NAME_LEN];
    uint32_t modelId;
    aclrtContext context;
    aclrtStream modelStream;
    MemInfo memInfo;
    char inputFile[MAX_FILE_NAME_LEN];
} ModelInfo;

Result NpuEnvInit(ModelInfo *modelInfo);
Result LoadModel(ModelInfo *modelInfo, const char *modelPath, const char *modelInputFile);
Result CreateDesc(ModelInfo *modelInfo);
Result ModelExecute(ModelInfo *modelInfo);
void NpuEnvFinalize(ModelInfo *modelInfo);
void PrintModelResult(void);

#endif // LENET5_UTILS_H
