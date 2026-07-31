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
#include "osal_debug.h"
#include "cmsis_os2.h"
#include "securec.h"

#include <string.h>
#include <stdio.h>

#include "ai.h"
#include "tcxo.h"
#include "ai_infer.h"
#include "ai_dump.h"
#include "ai_common.h"

#define TASKS_MCU_AI_PRINT_FLOAT_MULTIPILER 100000 /* Float Print Bits. For example: 0.99998 */

typedef struct {
    OH_AI_ModelHandle model;
    OH_AI_ContextHandle context;
    OH_AI_TensorHandleArray inputs;
    OH_AI_TensorHandleArray outputs;
} ai_infer_param;

static ai_infer_param g_ai_infer_param = { 0 };
static void *g_input_ptr[AI_LOAD_MAX_INPUT_NUM] = { 0 };

static MS_AI_INFER_Status MS_AI_INFER_DumpOutput(OH_AI_TensorHandle tensor)
{
    void *out_data = OH_AI_TensorGetMutableData(tensor);
    if (out_data == NULL) {
        osal_printk("[ERROR] OH_AI_TensorGetMutableData failed\n");
        return MS_AI_INFER_STATUS_FAILED;
    }
    MS_AI_DUMP_Status res = MS_AI_DUMP_Data(out_data, (size_t)(OH_AI_TensorGetElementNum(tensor)) * sizeof(float));
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        osal_printk("[ERROR] OH_AI_TensorGetMutableData failed\n");
        return MS_AI_INFER_STATUS_FAILED;
    }
    return MS_AI_INFER_STATUS_SUCCESS;
}


static MS_AI_INFER_Status MS_AI_INFER_CopyInputData(DumpInfo_t *dump_info_pool)
{
    for (size_t i = 0; i < g_ai_infer_param.inputs.handle_num; i++) {
        if (g_input_ptr[i] == NULL) {
            void *input_data = OH_AI_TensorGetMutableData(g_ai_infer_param.inputs.handle_list[i]);
            if (input_data == NULL) {
                osal_printk("[ERROR] OH_AI_TensorGetMutableData failed\n");
                return OH_AI_STATUS_FAILED;
            }
            g_input_ptr[i] = input_data;
        }
        errcode_t res = uapi_sfc_reg_read(dump_info_pool[i].base, g_input_ptr[i], OH_AI_TensorGetElementNum(g_ai_infer_param.inputs.handle_list[i]) *
            sizeof(float));
        if (res != ERRCODE_SUCC) {
            return MS_AI_INFER_STATUS_FAILED;
        }
    }
    return MS_AI_INFER_STATUS_SUCCESS;
}


MS_AI_INFER_Status MS_AI_Init(void)
{
    /* OH_AI_Init */
    OH_AI_Status res = OH_AI_Init(NULL, 0);
    if (res != OH_AI_STATUS_SUCCESS) {
        osal_printk("[ERROR] OH_AI_Init failed\n");
        return MS_AI_INFER_STATUS_FAILED;
    }
    /* 1. Init */
    OH_AI_ModelHandle model = OH_AI_ModelCreate();
    g_ai_infer_param.model = model;
    if (model == NULL) {
        osal_printk("[ERROR] OH_AI_ModelCreate failed\n");
        return MS_AI_INFER_STATUS_FAILED;
    }
    OH_AI_ContextHandle context = OH_AI_ContextCreate();
    g_ai_infer_param.context = context;
    if (context == NULL) {
        osal_printk("[ERROR] OH_AI_ContextCreate failed\n");
        return MS_AI_INFER_STATUS_FAILED;
    }
    OH_AI_Status ret = OH_AI_ModelBuild(g_ai_infer_param.model, NULL, 0, g_ai_infer_param.context);
    if (ret != OH_AI_STATUS_SUCCESS) {
        osal_printk("[ERROR] OH_AI_ModelBuild failed (%d)\n", ret);
        return MS_AI_INFER_STATUS_FAILED;
    }
    OH_AI_TensorHandleArray inputs = OH_AI_ModelGetInputs(g_ai_infer_param.model);
    g_ai_infer_param.inputs = inputs;
    if (inputs.handle_list == NULL) {
        osal_printk("[ERROR] OH_AI_ModelGetInputs failed\n");
        return MS_AI_INFER_STATUS_FAILED;
    }
    OH_AI_TensorHandleArray outputs = OH_AI_ModelGetOutputs(g_ai_infer_param.model);
    g_ai_infer_param.outputs = outputs;
    if (outputs.handle_list == NULL) {
        osal_printk("[AI_MCU] OH_AI_ModelGetOutputs failed\n");
        return MS_AI_INFER_STATUS_FAILED;
    }
    return MS_AI_INFER_STATUS_SUCCESS;
}


MS_AI_INFER_Status MS_AI_Destroy(void)
{
    if (g_ai_infer_param.context != NULL) {
        (void)OH_AI_ContextDestroy(&(g_ai_infer_param.context));
    }
    if (g_ai_infer_param.model != NULL) {
        (void)OH_AI_ModelDestroy(&(g_ai_infer_param.model));
    }
    return MS_AI_INFER_STATUS_SUCCESS;
}


MS_AI_INFER_Status MS_AI_Infer(AI_File_Handle handle)
{
    AI_Input_Store_Table *input_sys = (AI_Input_Store_Table *)handle;
    if (input_sys == NULL) {
        osal_printk("[ERROR] AI_File_Handle nullptr\n");
        return MS_AI_INFER_STATUS_FAILED;
    }
    DumpInfo_t *dump_info_pool = input_sys->dump_item;
    if (dump_info_pool == NULL) {
        osal_printk("[ERROR] dump_info_pool nullptr\n");
        return MS_AI_INFER_STATUS_FAILED;
    }
    uint16_t input_size = input_sys->input_num;
    if (input_size < 1 || input_size > AI_DUMP_MAX_INPUT_NUM || input_size != g_ai_infer_param.inputs.handle_num) {
        osal_printk("[ERROR] input_size (%u) invalid. Expect (0, %u], equal with (%u)\n", input_size, AI_DUMP_MAX_INPUT_NUM,
            g_ai_infer_param.inputs.handle_num);
        return MS_AI_INFER_STATUS_FAILED;
    }

    /* 1. Malloc Buffer & Copy Data */
    MS_AI_INFER_Status infer_res = MS_AI_INFER_CopyInputData(dump_info_pool);
    if (infer_res != MS_AI_INFER_STATUS_SUCCESS) {
        osal_printk("[ERROR] infer_res failed\n");
        return MS_AI_INFER_STATUS_FAILED;
    }

    /* 2. AI Infer */
    uint64_t start = uapi_tcxo_get_count();
    OH_AI_Status ret = OH_AI_ModelPredict(g_ai_infer_param.model, g_ai_infer_param.inputs, &(g_ai_infer_param.outputs));
    uint64_t end = uapi_tcxo_get_count();
    if (ret != OH_AI_STATUS_SUCCESS) {
        osal_printk("[ERROR] OH_AI_ModelPredict failed (%d)\n", ret);
        return MS_AI_INFER_STATUS_FAILED;
    }
    osal_printk("[TCXO] %llu ticks\n", end - start);

    /* 3. Output */
    for (size_t i = 0; i < g_ai_infer_param.outputs.handle_num; i++) {
        OH_AI_TensorHandle output = g_ai_infer_param.outputs.handle_list[i];
        if (output == NULL) {
            osal_printk("[ERROR] OH_AI_ModelGetOutputs failed\n");
            return MS_AI_INFER_STATUS_FAILED;
        }
        MS_AI_INFER_Status ret_dump = MS_AI_INFER_DumpOutput(output);
        if (ret_dump != MS_AI_INFER_STATUS_SUCCESS) {
            osal_printk("[ERROR] ai_mcu_sample_print_output_tensor failed (%d)\n", ret);
            return MS_AI_INFER_STATUS_FAILED;
        }
    }
    MS_AI_INFER_Status ret_dump = MS_AI_DUMP_Store();
    if (ret_dump != MS_AI_INFER_STATUS_SUCCESS) {
        osal_printk("[ERROR] MS_AI_DUMP_Store failed\n");
        return MS_AI_INFER_STATUS_FAILED;
    }
    return MS_AI_INFER_STATUS_SUCCESS;
}