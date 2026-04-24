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
 *
 * Description: At plt cmd table \n
 */

#if !defined(AT_AI_CMD_TALBE_H)
#define AT_AI_CMD_TALBE_H

#include "at.h"

typedef struct {
    uint32_t                para_map;
    int32_t                 para1; /* Range: 0x00000000..0x7fffffff */
    int32_t                 para2; /* Range: 0x00000000..0x7fffffff */
    int32_t                 para3; /* Range: 0x00000000..0x7fffffff */
} ai_infer_param_t;

const at_para_parse_syntax_t ai_infer_syntax[] = {
    {
        .type = AT_SYNTAX_TYPE_INT,
        .last = false,
        .attribute = AT_SYNTAX_ATTR_AT_MIN_VALUE | AT_SYNTAX_ATTR_AT_MAX_VALUE,
        .entry.int_range.min_val = 0x00000000,
        .entry.int_range.max_val = 0x7fffffff,
        .offset = offsetof(ai_infer_param_t, para1)
    },
    {
        .type = AT_SYNTAX_TYPE_INT,
        .last = false,
        .attribute = AT_SYNTAX_ATTR_AT_MIN_VALUE | AT_SYNTAX_ATTR_AT_MAX_VALUE,
        .entry.int_range.min_val = 0x00000000,
        .entry.int_range.max_val = 0x7fffffff,
        .offset = offsetof(ai_infer_param_t, para2)
    },
    {
        .type = AT_SYNTAX_TYPE_INT,
        .last = true,
        .attribute = AT_SYNTAX_ATTR_AT_MIN_VALUE | AT_SYNTAX_ATTR_AT_MAX_VALUE,
        .entry.int_range.min_val = 0x00000000,
        .entry.int_range.max_val = 0x7fffffff,
        .offset = offsetof(ai_infer_param_t, para3)
    },
};

/* AT+AIINIT */
at_ret_t at_ai_init_process(void);

/* AT+AIINFER */
at_ret_t at_ai_infer_process(const ai_infer_param_t *args);

/* AT+AIDESTROY */
at_ret_t at_ai_destroy_process(void);
 
const at_cmd_entry_t at_ai_cmd_parse_table[] = {
    {
        "AIINFER",
        40001,
        0,
        ai_infer_syntax,
        NULL,
        (at_set_func_t)at_ai_infer_process,
        NULL,
        NULL,
    },
    {
        "AIINIT",
        40002,
        0,
        NULL,
        at_ai_init_process,
        NULL,
        NULL,
        NULL,
    },
    {
        "AIDESTROY",
        40003,
        0,
        NULL,
        at_ai_destroy_process,
        NULL,
        NULL,
        NULL,
    },
};

#endif  /* AT_AI_CMD_TALBE_H */

