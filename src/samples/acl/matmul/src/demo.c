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
#include "ai_main.h"
#include "cmsis_os2.h"
#include "utils.h"

#define TASKS_NPU_AI_STACK_SIZE 0x1000       /* Max Stack Size in this task */
#define TASKS_NPU_AI_PRIO (osPriority_t)(17) /* Task Priority in LiteOS */

static const char *modelFileName = "/user/ai/matmul/matmul.exeom";
static const char *modelInputFile = "/user/ai/matmul/input.bin";
static const char *modelOutputFile = "/user/ai/matmul/output.bin";

int32_t MatmulRun()
{
    ModelInfo modelInfo = {0};

    // 初始化环境
    if (NpuEnvInit(&modelInfo)) {
        goto DESTROY;
    }

    // 加载模型文件
    if (LoadModel(&modelInfo, modelFileName, modelInputFile, modelOutputFile)) {
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

static void *ai_npu_task(const char *arg)
{
    (void)arg;
    osal_printk("[AI_NPU] execute npu sample\n");
    uapi_npu_dlog_setlevel(0, 0x3, 1);
    MatmulRun();
    uapi_npu_dlog_setlevel(0, 0, 1);
    return NULL;
}

/* Sample entry function */
void tasks_test_entry(void)
{
    osThreadAttr_t attr;
    attr.name = "AI_NPU_Task";
    attr.attr_bits = 0U;
    attr.cb_mem = NULL;
    attr.cb_size = 0U;
    attr.stack_mem = NULL;
    attr.stack_size = TASKS_NPU_AI_STACK_SIZE;
    attr.priority = TASKS_NPU_AI_PRIO;

    if (osThreadNew((osThreadFunc_t)ai_npu_task, NULL, &attr) == NULL) {
        /* Create task fail. */
        osal_printk("[AI_NPU] Task Create Failed\n");
    }
}