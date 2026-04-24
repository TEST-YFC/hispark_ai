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
#ifndef MS_INCLUDE_AI_DUMP_H
#define MS_INCLUDE_AI_DUMP_H

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
 * @brief  AI Dump return status
 * @else
 * @brief  AI Dump功能返回状态码
 * @endif
 */
typedef enum MS_AI_DUMP_Status {
    MS_AI_DUMP_STATUS_SUCCESS = 0,
    MS_AI_DUMP_STATUS_FULL = 1,
    MS_AI_DUMP_STATUS_FAILED = 500,
} MS_AI_DUMP_Status;

typedef struct {
    const char *name;
    int16_t ndims;
    int16_t shape[AI_FILESYS_MAX_NDIMS];
    MS_AI_DUMP_DType dtype;
} MS_AI_DUMPInfo;

/**
 * @if Eng
 * @brief  MSLite Dump Init.
 * @retval MS_AI_DUMP_STATUS_SUCCESS      Success.
 * @retval other                          Failed.
 * @else
 * @brief  完成Dump初始化。
 * @retval MS_AI_DUMP_STATUS_SUCCESS      成功返回#MS_AI_DUMP_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
MS_AI_DUMP_Status MS_AI_DUMPInit(uint32_t base, uint32_t offset);

/**
 * @if Eng
 * @brief  MSLite Dump Data without DumpInfo
 * @param  [in]  data                     Dumped data Addr in Memory.
 * @param  [in]  size                     Dumped data size.
 * @retval MS_AI_DUMP_STATUS_SUCCESS      Success.
 * @retval other                          Failed.
 * @else
 * @brief  完成数据Dump并不传入DumpInfo信息。
 * @param  [in]  data                     被Dump数据的地址
 * @param  [in]  size                     被Dump数据的大小
 * @retval MS_AI_DUMP_STATUS_SUCCESS      成功返回#MS_AI_DUMP_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
MS_AI_DUMP_Status MS_AI_DUMP_Data_Without_Info(void *data, size_t size);

/**
 * @if Eng
 * @brief  MSLite Dump Data with DumpInfo
 * @param  [in]  data                     Dumped data Addr in Memory.
 * @param  [in]  size                     Dumped data size.
 * @param  [in]  data_info                Dumped data info.
 * @retval MS_AI_DUMP_STATUS_SUCCESS      Success.
 * @retval other                          Failed.
 * @else
 * @brief  完成数据Dump并传入DumpInfo信息。
 * @param  [in]  data                     被Dump数据的地址
 * @param  [in]  size                     被Dump数据的大小
 * @param  [in]  data_info                被Dump数据的信息.
 * @retval MS_AI_DUMP_STATUS_SUCCESS      成功返回#MS_AI_DUMP_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
MS_AI_DUMP_Status MS_AI_DUMP_Data_With_Info(void *data, size_t size, MS_AI_DUMPInfo *data_info);

/**
 * @if Eng
 * @brief  MSLite Dump Data (overload)
 * @param  [in]  data                     Dumped data Addr in Memory.
 * @param  [in]  size                     Dumped data size.
 * @param  [in]  data_info (selected)     Dumped data info.
 * @retval MS_AI_DUMP_STATUS_SUCCESS      Success.
 * @retval other                          Failed.
 * @else
 * @brief  完成数据Dump并传入DumpInfo信息。
 * @param  [in]  data                     被Dump数据的地址
 * @param  [in]  size                     被Dump数据的大小
 * @param  [in]  data_info (selected)     被Dump数据的信息.
 * @retval MS_AI_DUMP_STATUS_SUCCESS      成功返回#MS_AI_DUMP_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
#define MS_AI_DUMP_OVERLOAD(dara_param, size_param, info_param, FUNC, ...) FUNC
#define MS_AI_DUMP_FUNC(...) MS_AI_DUMP_OVERLOAD(__VA_ARGS__, MS_AI_DUMP_Data_With_Info, \
    MS_AI_DUMP_Data_Without_Info)(__VA_ARGS__)
#define MS_AI_DUMP_Data(...) MS_AI_DUMP_FUNC(__VA_ARGS__)

/**
 * @if Eng
 * @brief  MSLite Dump Store.
 * @retval MS_AI_DUMP_STATUS_SUCCESS      Success.
 * @retval other                          Failed.
 * @else
 * @brief  结束Dump，存储元信息。
 * @retval MS_AI_DUMP_STATUS_SUCCESS      成功返回#MS_AI_DUMP_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
MS_AI_DUMP_Status MS_AI_DUMP_Store(void);

/**
 * @if Eng
 * @brief  MSLite Dump Deinit.
 * @retval MS_AI_DUMP_STATUS_SUCCESS      Success.
 * @retval other                          Failed.
 * @else
 * @brief  完成Dump信息去初始化。
 * @retval MS_AI_DUMP_STATUS_SUCCESS      成功返回#MS_AI_DUMP_STATUS_SUCCESS状态。
 * @retval 其他                           失败返回#其他状态码。
 * @endif
 */
MS_AI_DUMP_Status MS_AI_DUMP_DeInit(void);

/**
 * @}
 */

#ifdef __cplusplus
#if __cplusplus
}
#endif /* __cplusplus */
#endif /* __cplusplus */

#endif /* MS_INCLUDE_AI_DUMP_H */