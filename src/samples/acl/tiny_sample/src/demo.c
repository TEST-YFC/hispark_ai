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

#include <stdio.h>
#include <stdint.h>
#include "ai.h"
#include "securec.h"
#include "utils.h"

static char *g_modelFileName = "/asic_test/mul/mul.om";
static char *g_modelInputFileList[] = {"/asic_test/mul/x.bin","/asic_test/mul/y.bin"};
static char *g_modelOutputFile = "/asic_test/mul/output/";

int32_t TinySampleRun()
{
    ModelInfo modelInfo = {0};
    modelInfo.modelFile = g_modelFileName;
    modelInfo.inputFileList = g_modelInputFileList;
    modelInfo.inputNum = sizeof(g_modelInputFileList) / sizeof(g_modelInputFileList[0]);
    modelInfo.outputPath = g_modelOutputFile;
    
    // 初始化环境
    if (NpuEnvInit(&modelInfo)) {
        goto DESTROY;
    }
    // 加载模型文件
    if (LoadModel(&modelInfo)) {
        goto DESTROY;
    }
    // 创建模型描述
    if (CreateModelDesc(&modelInfo)) {
        goto DESTROY;
    }
    // 创建模型输入
    if (CreateModelInput(&modelInfo)) {
        goto DESTROY;
    }
    // 创建模型输出
    if (CreateModelOutput(&modelInfo)) {
        goto DESTROY;
    }
    // 模型执行
    if (ExecuteModel(&modelInfo)) {
        goto DESTROY;
    }
    osal_printk("Execute finish!\n");

    // 销毁环境
    NpuEnvFinalize(&modelInfo);
    osal_printk("Finish!\n");
    return SUCCESS;

DESTROY:
    NpuEnvFinalize(&modelInfo);
    osal_printk("Execute failed!\n");
    return FAILED;
}

int main(void)
{
    osal_printk("[AI_NPU] execute npu sample\n");
    if (TinySampleRun() == SUCCESS) {
        return 0;
    }
    return 1;
}
