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

#include "ai_load.h"
#include "ai_dump.h"
#include "sfc.h"

#ifdef CHIP_WS63
#define MIN_LOAD_ADDR 0x00390000
#define MAX_LOAD_ADDR 0x00460000
#else
#define MIN_LOAD_ADDR 0x00000000
#define MAX_LOAD_ADDR 0x7fffffff
#endif

#define LOAD_STANDARD_MAGIC 0x7e01
#define LOAD_STANDARD_VERSION 0x0001

static uint32_t g_ai_load_start = AI_LOAD_DEFAULT_START_ADDR; /* Default: 0x00420000 */
static uint32_t g_ai_load_max_size = AI_LOAD_DEFAULT_MAX_SIZE; /* Default: 0x00030000 */

static DumpHeaderMeta g_meta = { 0 };
static DumpInfoHeader g_header[AI_LOAD_MAX_BLOCK_NUM] = { 0 };
static AI_Input_Store_Table g_ai_input = { 0 };

static uint8_t g_header_section_table[AI_FILESYS_HEADSECTION_SIZE];
static uint8_t g_info_item_table[AI_FILESYS_INFOTABLE_ITEM_SIZE];
static uint8_t g_info_section_table[AI_FILESYS_INFOSECTION_SIZE];

static MS_AI_LOAD_Status ms_ai_load_header_section(uint32_t *read_ptr)
{
    errcode_t res = uapi_sfc_reg_read(*read_ptr, (void *)g_header_section_table, AI_FILESYS_HEADSECTION_SIZE);
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    g_meta.magic = *((uint16_t *)(g_header_section_table + AI_FILESYS_HEADSECTION_MAGIC));
    if (g_meta.magic != LOAD_STANDARD_MAGIC) {
        osal_printk("[ERROR] AI Load Invalid Magic (%02x), Expected (%02x)\n", g_meta.magic, LOAD_STANDARD_MAGIC);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    g_meta.version = *((uint16_t *)(g_header_section_table + AI_FILESYS_HEADSECTION_VERSION));
    if (g_meta.version != LOAD_STANDARD_VERSION) {
        osal_printk("[ERROR] AI Load Invalid Magic (%02x), Expected (%02x)\n", g_meta.version, LOAD_STANDARD_VERSION);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    g_meta.header_len = *((uint16_t *)(g_header_section_table + AI_FILESYS_HEADSECTION_HEADER_LEN));
    if (g_meta.header_len < AI_FILESYS_HEADSECTION_SIZE || g_meta.header_len > AI_FILESYS_HEADSECTION_SIZE + AI_DUMP_MAX_BLOCK_NUM *
        AI_FILESYS_INFOTABLE_ITEM_SIZE) {
        osal_printk("[ERROR] AI Load Invalid header_len (%u), header_len should be in [%u, %u]\n", g_meta.header_len, AI_FILESYS_HEADSECTION_SIZE,
            AI_FILESYS_HEADSECTION_SIZE + AI_DUMP_MAX_BLOCK_NUM * AI_FILESYS_INFOTABLE_ITEM_SIZE);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    g_meta.info_len = *((uint16_t *)(g_header_section_table + AI_FILESYS_HEADSECTION_INFO_LEN));
    if (g_meta.info_len < 1 || g_meta.info_len > AI_LOAD_MAX_INPUT_NUM) {
        osal_printk("[ERROR] AI Load Invalid info_len (%u), Info Len should be in [1, %u]\n", g_meta.info_len, AI_LOAD_MAX_INPUT_NUM);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    g_meta.data_ptr = *((uint32_t *)(g_header_section_table + AI_FILESYS_HEADSECTION_DATA_PTR));
    if (g_meta.data_ptr + AI_DUMP_SFC_OFFSET < MIN_LOAD_ADDR || g_meta.data_ptr + AI_DUMP_SFC_OFFSET > MAX_LOAD_ADDR) {
        osal_printk("[ERROR] AI Load Invalid data_ptr (0x%04x), data_ptr should be in [0x%04x, 0x%04x]\n", g_meta.data_ptr, MIN_LOAD_ADDR - AI_DUMP_SFC_OFFSET,
            MAX_LOAD_ADDR - AI_DUMP_SFC_OFFSET);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    (*read_ptr) += AI_FILESYS_HEADSECTION_SIZE;
    return MS_AI_LOAD_STATUS_SUCCESS;
}

static MS_AI_LOAD_Status ms_ai_load_info_item(uint32_t *read_ptr, DumpInfoHeader *info_item)
{
    errcode_t res = uapi_sfc_reg_read(*read_ptr, (void *)g_info_item_table, AI_FILESYS_INFOTABLE_ITEM_SIZE);
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    info_item->base = *((uint32_t *)(g_info_item_table + AI_FILESYS_INFOTABLE_ITEM_BASE));
    if (info_item->base + AI_DUMP_SFC_OFFSET < MIN_LOAD_ADDR || info_item->base + AI_DUMP_SFC_OFFSET > MAX_LOAD_ADDR) {
        osal_printk("[ERROR] AI Load Invalid info_item base (0x%04x), base should be in [0x%04x, 0x%04x]\n", info_item->base, MIN_LOAD_ADDR -
            AI_DUMP_SFC_OFFSET, MAX_LOAD_ADDR - AI_DUMP_SFC_OFFSET);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    info_item->offset = *((uint32_t *)(g_info_item_table + AI_FILESYS_INFOTABLE_ITEM_OFFSET));
    if (info_item->offset <= 0 || info_item->offset != AI_FILESYS_INFOSECTION_SIZE) {
        osal_printk("[ERROR] AI Load Invalid info_item offset (%u), offset should be %u\n", info_item->offset, AI_FILESYS_INFOSECTION_SIZE);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    (*read_ptr) += AI_FILESYS_INFOTABLE_ITEM_SIZE;
    return MS_AI_LOAD_STATUS_SUCCESS;
}


static MS_AI_LOAD_Status ms_ai_load_info(DumpInfoHeader *info_item, size_t index)
{
    uint32_t info_ptr = info_item->base;
    errcode_t res = uapi_sfc_reg_read(info_ptr, (void *)g_info_section_table, AI_FILESYS_INFOSECTION_SIZE);
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    DumpInfo_t dump = { 0 };
    dump.base = *((uint32_t *)(g_info_section_table + AI_FILESYS_INFOSECTION_BASE));
    if (dump.base + AI_DUMP_SFC_OFFSET < MIN_LOAD_ADDR || dump.base + AI_DUMP_SFC_OFFSET > MAX_LOAD_ADDR) {
        osal_printk("[ERROR] AI Load Invalid info base (0x%04x), base should be in [0x%04x, 0x%04x]\n", dump.base, MIN_LOAD_ADDR - AI_DUMP_SFC_OFFSET,
            MAX_LOAD_ADDR - AI_DUMP_SFC_OFFSET);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    dump.offset = *((uint32_t *)(g_info_section_table + AI_FILESYS_INFOSECTION_OFFSET));
    if (dump.offset <= 0 || dump.offset > AI_LOAD_DATA_MAX_SIZE) {
        osal_printk("[ERROR] AI Load Invalid info offset (%u), offset should be in (0, %u]\n", dump.offset, AI_LOAD_DATA_MAX_SIZE);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    dump.dtype = *((uint8_t *)(g_info_section_table + AI_FILESYS_INFOSECTION_DTYPE));
    if (dump.dtype != MS_AI_DUMP_FLOAT) {
        osal_printk("[ERROR] AI Load Invalid info dtype should be MS_AI_DUMP_FLOAT");
        return MS_AI_DUMP_STATUS_FAILED;
    }
    dump.ndims = *((uint16_t *)(g_info_section_table + AI_FILESYS_INFOSECTION_NDIMS));
    if (dump.ndims <= 0 || dump.ndims > AI_FILESYS_MAX_NDIMS) {
        osal_printk("[ERROR] AI Load Invalid info ndims (%u), ndims should be in (0, %u]\n", dump.ndims, AI_FILESYS_MAX_NDIMS);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    dump.nameLens = *((uint16_t *)(g_info_section_table + AI_FILESYS_INFOSECTION_NAMELENS));
    if (dump.nameLens <= 0 || dump.nameLens > AI_FILESYS_NAME_MAX) {
        osal_printk("[ERROR] AI Load Invalid info nameLens (%u), ndims should be in (0, %u]\n", dump.nameLens, AI_FILESYS_NAME_MAX);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    for (size_t i = 0; i < dump.ndims; i++) {
        dump.shape[i] = *((uint16_t *)(g_info_section_table + AI_FILESYS_INFOSECTION_SHAPE + i * sizeof(uint16_t)));
        if (dump.shape[i] <= 0) {
            return MS_AI_DUMP_STATUS_FAILED;
        }
    }
    uint32_t name_start_offset = CEIL(AI_FILESYS_INFOSECTION_SHAPE + dump.ndims * sizeof(uint16_t), AI_LOAD_ALIGN_BASE);
    errno_t ret = memcpy_s(dump.name, dump.nameLens, (void *)(g_info_section_table + name_start_offset), dump.nameLens);
    if (ret != EOK) {
        return MS_AI_LOAD_STATUS_FAILED;
    }
    ret = memcpy_s(&(g_ai_input.dump_item[index]), sizeof(DumpInfo_t), &dump, sizeof(DumpInfo_t));
    if (ret != EOK) {
        return MS_AI_LOAD_STATUS_FAILED;
    }
    return MS_AI_LOAD_STATUS_SUCCESS;
}


MS_AI_LOAD_Status MS_AI_LoadInit(int32_t base, int32_t offset)
{
    if (base < MIN_LOAD_ADDR || offset <= 0 || base > MAX_LOAD_ADDR - offset) {
        osal_printk("[ERROR] MS_AI_LoadInit Failed\n");
        return MS_AI_LOAD_STATUS_FAILED;
    }
    g_ai_load_start = base;
    g_ai_load_max_size = offset;
    return MS_AI_LOAD_STATUS_SUCCESS;
}

MS_AI_LOAD_Status MS_AI_Load(AI_File_Handle *handle)
{
    *handle = (void *)(&g_ai_input); /* Init Handle */
    g_ai_input.input_num = 0;
    uint32_t read_ptr = g_ai_load_start - AI_LOAD_SFC_OFFSET;
    errno_t res = memset_s(&g_meta, sizeof(g_meta), 0, 1);
    if (res != EOK) {
        return MS_AI_LOAD_STATUS_FAILED;
    }
    res = memset_s(&g_header, sizeof(g_header), 0, 1);
    if (res != EOK) {
        return MS_AI_LOAD_STATUS_FAILED;
    }
    res = memset_s(&g_ai_input, sizeof(g_ai_input), 0, 1);
    if (res != EOK) {
        return MS_AI_LOAD_STATUS_FAILED;
    }
    res = memset_s(&g_header_section_table, sizeof(g_header_section_table), 0, 1);
    if (res != EOK) {
        return MS_AI_LOAD_STATUS_FAILED;
    }
    res = memset_s(&g_info_item_table, sizeof(g_info_item_table), 0, 1);
    if (res != EOK) {
        return MS_AI_LOAD_STATUS_FAILED;
    }
    res = memset_s(&g_info_section_table, sizeof(g_info_section_table), 0, 1);
    if (res != EOK) {
        return MS_AI_LOAD_STATUS_FAILED;
    }
    /* 1. Analyze Header Section Resource */
    MS_AI_LOAD_Status ret = ms_ai_load_header_section(&read_ptr);
    if (ret != MS_AI_LOAD_STATUS_SUCCESS) {
        osal_printk("[ERROR] ms_ai_load_header_section failed (%d)\n", ret);
        return MS_AI_LOAD_STATUS_FAILED;
    }
    for (size_t idx = 0; idx < g_meta.info_len; idx++) {
        /* 2. Analyze Info Section Table */
        ret = ms_ai_load_info_item(&read_ptr, &g_header[idx]);
        if (ret != MS_AI_LOAD_STATUS_SUCCESS) {
            osal_printk("[ERROR] ms_ai_load_info_item failed (%d)\n", ret);
            return MS_AI_LOAD_STATUS_FAILED;
        }
        /* 3. Analyze Info */
        ret = ms_ai_load_info(&g_header[idx], idx);
        if (ret != MS_AI_LOAD_STATUS_SUCCESS) {
            osal_printk("[ERROR] ms_ai_load_info failed (%d)\n", ret);
            return MS_AI_LOAD_STATUS_FAILED;
        }
        g_ai_input.input_num++;
    }
    return MS_AI_LOAD_STATUS_SUCCESS;
}