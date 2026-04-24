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
#ifndef MS_INCLUDE_AI_COMMON_H
#define MS_INCLUDE_AI_COMMON_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "sfc.h"

#ifdef __cplusplus
#if __cplusplus
extern "C" {
#endif /* __cplusplus */
#endif /* __cplusplus */


#define CEIL(num, base) ((((num) + (base) - 1) / (base)) * (base))

#define AI_LOAD_DEFAULT_START_ADDR 0x00420000 /* WS63 */
#define AI_LOAD_DEFAULT_MAX_SIZE 0x00030000 /* WS63 */
#define AI_LOAD_SFC_OFFSET 0x00200000 /* WS63 */
#define AI_LOAD_MAX_BLOCK_NUM 64
#define AI_LOAD_ALIGN_BASE 16
#define AI_LOAD_MAX_INPUT_NUM 4
#define AI_LOAD_DATA_MAX_SIZE (16 * 1024)

#define AI_DUMP_START_ADDR 0x00390000 /* WS63 */
#define AI_DUMP_MAX_SIZE 0x00030000 /* WS63 */
#define AI_DUMP_DATA_MAX_SIZE (16 * 1024) /* WS63 */
#define AI_DUMP_SFC_OFFSET 0x00200000 /* WS63 */
#define AI_DUMP_MAX_BLOCK_NUM 64
#define AI_DUMP_ALIGN_BASE 16
#define AI_DUMP_MAX_INPUT_NUM 4

#define AI_FILESYS_NAME_MAX 112
#define AI_FILESYS_MAX_NDIMS 48

/* Header Section (32B)
    |-- Magic 0x7e01  --|-- Version 0x0001 --|-- Header Lens (u16) --|-- Info Lens (u16) --|-- Data Ptr Offser (u32) --|-- Reserve (20 B) --|
*/
#define AI_FILESYS_HEADSECTION_SIZE 32
#define AI_FILESYS_HEADSECTION_MAGIC 0
#define AI_FILESYS_HEADSECTION_VERSION 2
#define AI_FILESYS_HEADSECTION_HEADER_LEN 4
#define AI_FILESYS_HEADSECTION_INFO_LEN 6
#define AI_FILESYS_HEADSECTION_DATA_PTR 8
#define AI_FILESYS_HEADSECTION_MAGIC_VALUE 0x7e01
#define AI_FILESYS_HEADSECTION_VERSION_VALUE 0x0001

/* Info Table
    |-- base (u32)  --|-- Size (u32) --| |-- base (u32)  --|-- Size (u32) --| |-- base (u32)  --|-- Size (u32) --|... <Align 16>
*/
#define AI_FILESYS_INFOTABLE_ITEM_SIZE 8
#define AI_FILESYS_INFOTABLE_ITEM_BASE 0
#define AI_FILESYS_INFOTABLE_ITEM_OFFSET 4

/* Info Section (128B)
    |-- base (u32) --|-- offset (u32) --|-- dtype (u8) + reseve 1B --|-- ndims (u16) --|-- namelens (u32) --|
    |-- shape_item (u16) --| Align For 16
    |-- name (string) --|
*/
#define AI_FILESYS_INFOSECTION_SIZE 128
#define AI_FILESYS_INFOSECTION_BASE 0
#define AI_FILESYS_INFOSECTION_OFFSET 4
#define AI_FILESYS_INFOSECTION_DTYPE 8
#define AI_FILESYS_INFOSECTION_NDIMS 10
#define AI_FILESYS_INFOSECTION_NAMELENS 12
#define AI_FILESYS_INFOSECTION_SHAPE 16

/**
 * @if Eng
 * @brief  AI Dump return status
 * @else
 * @brief  AI Dump Dtype
 * @endif
 */
typedef enum MS_AI_DUMP_DType {
    MS_AI_DUMP_UNKNOWN = 0,
    MS_AI_DUMP_UINT8 = 1,
    MS_AI_DUMP_INT8 = 2,
    MS_AI_DUMP_UINT16 = 3,
    MS_AI_DUMP_INT16 = 4,
    MS_AI_DUMP_UINT32 = 5,
    MS_AI_DUMP_INT32 = 6,
    MS_AI_DUMP_FLOAT = 7,
    MS_AI_DUMP_DOUBLE = 8,
} MS_AI_DUMP_DType;


typedef struct DumpHeaderMeta {
    uint16_t magic;
    uint16_t version;
    uint16_t header_len;
    uint16_t info_len;
    uint32_t data_ptr;
} DumpHeaderMeta;


typedef struct DumpInfoHeader {
    uint32_t base;
    uint32_t offset;
} DumpInfoHeader;


typedef struct DumpInfo {
    uint32_t base;
    uint32_t offset;
    MS_AI_DUMP_DType dtype;
    uint16_t ndims;
    uint16_t nameLens;
    uint16_t shape[AI_FILESYS_MAX_NDIMS];
    char name[AI_FILESYS_NAME_MAX];
} DumpInfo_t;

typedef struct AI_Input_Store_Table {
    uint16_t input_num;
    DumpInfo_t dump_item[AI_LOAD_MAX_INPUT_NUM];
} AI_Input_Store_Table;

typedef void *AI_File_Handle;

/**
 * @}
 */

#ifdef __cplusplus
#if __cplusplus
}
#endif /* __cplusplus */
#endif /* __cplusplus */

#endif /* MS_INCLUDE_AI_COMMON_H */