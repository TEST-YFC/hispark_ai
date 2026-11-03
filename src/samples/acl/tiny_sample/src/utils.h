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

#ifndef TINY_SAMPLE_UTILS_H
#define TINY_SAMPLE_UTILS_H

#include "acl.h"
#include "acl_base.h"
#include "acl_mdl.h"
#include "acl_rt.h"
#include <stdio.h>
#define osal_printk printf

#define MAX_FILE_NUM 12
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
    char *modelFile;
    uint32_t modelId;
    aclrtContext context;
    aclrtStream modelStream;
    MemInfo memInfo;
    aclmdlDesc *modelDesc;
    char **inputFileList;
    size_t inputNum;
    char *outputPath;
    int32_t envInited;   // aclInit是否成功
    int32_t deviceSet;   // aclrtSetDevice是否成功
} ModelInfo;

Result NpuEnvInit(ModelInfo *modelInfo);
Result LoadModel(ModelInfo *modelInfo);
Result CreateModelDesc(ModelInfo *modelInfo);
Result CreateModelInput(ModelInfo *modelInfo);
Result CreateModelOutput(ModelInfo *modelInfo);
Result ExecuteModel(ModelInfo *modelInfo);
void NpuEnvFinalize(ModelInfo *modelInfo);

#endif // TINY_SAMPLE_UTILS_H
