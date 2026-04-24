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
#ifndef MS_INCLUDE_AI_LOAD_H
#define MS_INCLUDE_AI_LOAD_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "sfc.h"
#include "ai_common.h"

#ifdef __cplusplus
#if __cplusplus
extern "C" {
#endif /* __cplusplus */
#endif /* __cplusplus */

/**
 * @if Eng
 * @brief  AI Load return status
 * @else
 * @brief  AI Load功能返回状态码
 * @endif
 */
typedef enum MS_AI_LOAD_Status {
    MS_AI_LOAD_STATUS_SUCCESS = 0,
    MS_AI_LOAD_STATUS_FULL = 1,
    MS_AI_LOAD_STATUS_FAILED = 500,
} MS_AI_LOAD_Status;

/**
 * @if Eng
 * @brief  MSLite Load Init.
 * @retval MS_AI_INFER_STATUS_SUCCESS     Success.
 * @retval other                          Failed.
 * @else
 * @brief  完成Load初始化。
 * @retval MS_AI_INFER_STATUS_SUCCESS      成功返回#MS_AI_DUMP_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
MS_AI_LOAD_Status MS_AI_LoadInit(int32_t base, int32_t offset);

/**
 * @if Eng
 * @brief  MSLite Load Data.
 * @retval MS_AI_LOAD_STATUS_SUCCESS     Success.
 * @retval other                          Failed.
 * @else
 * @brief  完成Load数据。
 * @retval MS_AI_LOAD_STATUS_SUCCESS     成功返回#MS_AI_DUMP_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
MS_AI_LOAD_Status MS_AI_Load(AI_File_Handle *handle);

/**
 * @}
 */

#ifdef __cplusplus
#if __cplusplus
}
#endif /* __cplusplus */
#endif /* __cplusplus */

#endif /* MS_INCLUDE_AI_LOAD_H */