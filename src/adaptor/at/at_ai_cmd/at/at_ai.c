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

#include <string.h>

#include "at_cmd.h"
#include "at_ai_cmd_register.h"
#include "at_ai_cmd_table.h"
#include "debug_print.h"
#include "time64.h"
#include "version_porting.h"
#include "ai.h"
#include "tcxo.h"
#include "sfc.h"
#include "ai_dump.h"
#include "ai_load.h"
#include "ai_infer.h"

#include "at_ai.h"

static bool g_ai_resource_init_flag = false;

at_ret_t at_ai_init_process(void)
{
    if (!g_ai_resource_init_flag) {
        MS_AI_INFER_Status res = MS_AI_Init();
        if (res != MS_AI_INFER_STATUS_SUCCESS) {
            osal_printk("MS_AI_Init Failed\n");
            return AT_RET_PROGRESS_BLOCK;
        }
    }
    g_ai_resource_init_flag = true;
    return AT_RET_OK;
}

at_ret_t at_ai_infer_process(const ai_infer_param_t *args)
{
    if (!g_ai_resource_init_flag) {
        osal_printk("AI Resource Not Init\n");
        return AT_RET_PROGRESS_BLOCK;
    }
    AI_File_Handle ai_file_handle;
    MS_AI_LOAD_Status load_res = MS_AI_LoadInit(args->para1 + args->para2, args->para3);
    if (load_res != MS_AI_LOAD_STATUS_SUCCESS) {
        osal_printk("AI Load Init Failed");
        return AT_RET_PROGRESS_BLOCK;
    }
    MS_AI_DUMP_Status dump_res = MS_AI_DUMPInit(args->para1, args->para2);
    if (dump_res != MS_AI_DUMP_STATUS_SUCCESS) {
        osal_printk("AI Dump Init Failed");
        return AT_RET_PROGRESS_BLOCK;
    }
    load_res = MS_AI_Load(&ai_file_handle);
    if (load_res != MS_AI_LOAD_STATUS_SUCCESS) {
        osal_printk("AI Load Failed");
        return AT_RET_PROGRESS_BLOCK;
    }
    MS_AI_INFER_Status infer_res = MS_AI_Infer(ai_file_handle);
    if (infer_res != MS_AI_INFER_STATUS_SUCCESS) {
        osal_printk("AI Infer Failed");
        return AT_RET_PROGRESS_BLOCK;
    }
    return AT_RET_OK;
}

at_ret_t at_ai_destroy_process(void)
{
    if (g_ai_resource_init_flag) {
        MS_AI_INFER_Status res = MS_AI_Destroy();
        if (res != MS_AI_INFER_STATUS_SUCCESS) {
            osal_printk("MS_AI_Init Failed\n");
            return AT_RET_PROGRESS_BLOCK;
        }
        g_ai_resource_init_flag = false;
    }
    return AT_RET_OK;
}


#define AT_AI_FUNC_NUM (sizeof(at_ai_cmd_parse_table) / sizeof(at_ai_cmd_parse_table[0]))

void los_at_ai_cmd_register(void)
{
    print_str("los_at_ai_cmd_register EXCUTE\r\n");
    uapi_at_ai_register_cmd(at_ai_cmd_parse_table, AT_AI_FUNC_NUM);
}