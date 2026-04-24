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
#ifndef MS_INCLUDE_AI_INFER_H
#define MS_INCLUDE_AI_INFER_H

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
 * @brief  AI Infer return status
 * @else
 * @brief  AI Infer功能返回状态码
 * @endif
 */
typedef enum MS_AI_INFER_Status {
    MS_AI_INFER_STATUS_SUCCESS = 0,
    MS_AI_INFER_STATUS_FULL = 1,
    MS_AI_INFER_STATUS_FAILED = 500,
} MS_AI_INFER_Status;

/**
 * @if Eng
 * @brief  MSLite Infer.
 * @retval MS_AI_INFER_STATUS_SUCCESS      Success.
 * @retval other                          Failed.
 * @else
 * @brief  完成AI推理流程。
 * @retval MS_AI_INFER_STATUS_SUCCESS      成功返回#MS_AI_INFER_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
MS_AI_INFER_Status MS_AI_Infer(AI_File_Handle handle);

/**
 * @if Eng
 * @brief  MSLite AI Resource Init.
 * @retval MS_AI_INFER_STATUS_SUCCESS     Success.
 * @retval other                          Failed.
 * @else
 * @brief  完成AI资源初始化。
 * @retval MS_AI_INFER_STATUS_SUCCESS     成功返回#MS_AI_INFER_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
MS_AI_INFER_Status MS_AI_Init(void);

/**
 * @if Eng
 * @brief  MSLite AI Resource Destroy.
 * @retval MS_AI_INFER_STATUS_SUCCESS     Success.
 * @retval other                          Failed.
 * @else
 * @brief  完成AI资源销毁。
 * @retval MS_AI_INFER_STATUS_SUCCESS     成功返回#MS_AI_INFER_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
MS_AI_INFER_Status MS_AI_Destroy(void);

/**
 * @}
 */

#ifdef __cplusplus
#if __cplusplus
}
#endif /* __cplusplus */
#endif /* __cplusplus */

#endif /* MS_INCLUDE_AI_INFER_H */