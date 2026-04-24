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
#include <stdio.h>

#include "osal_debug.h"
#include "cmsis_os2.h"
#include "securec.h"

#include "ai_common.h"
#include "ai_dump.h"

#ifdef CHIP_WS63
#define MIN_DUMP_ADDR 0x00390000
#define MAX_DUMP_ADDR 0x00460000
#else
#define MIN_DUMP_ADDR 0x00000000
#define MAX_DUMP_ADDR 0x7fffffff
#endif

static uint32_t g_ai_dump_start = AI_DUMP_START_ADDR; /* Default: 0x00390000 */
static uint32_t g_ai_dump_max_size = AI_DUMP_MAX_SIZE; /* Default: 0x00030000 */
static DumpHeaderMeta g_header_section = {AI_FILESYS_HEADSECTION_MAGIC_VALUE, AI_FILESYS_HEADSECTION_VERSION_VALUE,
    0, 0, 0};
static DumpInfoHeader g_dump_infotable[AI_DUMP_MAX_BLOCK_NUM];
static DumpInfo_t g_dump_infosection[AI_DUMP_MAX_BLOCK_NUM];

static MS_AI_DUMP_Status MS_AI_Dump_Check_Dump_Info(void *data, size_t size)
{
    if (data == NULL) {
        osal_printk("[ERROR] MS_AI_DUMP_Data_Without_Info Nullptr\n");
        return MS_AI_DUMP_STATUS_FAILED;
    }
    if (g_header_section.info_len == AI_DUMP_MAX_BLOCK_NUM) {
        return MS_AI_DUMP_STATUS_FULL;
    }
    if (g_header_section.info_len && CEIL(g_dump_infosection[g_header_section.info_len - 1].offset + size,
        AI_DUMP_ALIGN_BASE) > AI_DUMP_DATA_MAX_SIZE) {
        return MS_AI_DUMP_STATUS_FULL;
    }
    return MS_AI_DUMP_STATUS_SUCCESS;
}

static MS_AI_DUMP_Status MS_AI_DUMP_Write_Header_Info_Table(void)
{
    uint32_t write_base = g_ai_dump_start + AI_FILESYS_HEADSECTION_SIZE + (g_header_section.info_len *
        AI_FILESYS_INFOTABLE_ITEM_SIZE);
    MS_AI_DUMP_Status res = uapi_sfc_reg_write(write_base, (void *)(&(g_dump_infotable[g_header_section.info_len].base)),
        sizeof(g_dump_infotable[g_header_section.info_len].base));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(g_dump_infotable[g_header_section.info_len].base);
    res = uapi_sfc_reg_write(write_base, (void *)(&(g_dump_infotable[g_header_section.info_len].offset)),
        sizeof(g_dump_infotable[g_header_section.info_len].offset));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(g_dump_infotable[g_header_section.info_len].offset);
    g_header_section.info_len++;
    return res;
}

static MS_AI_DUMP_Status MS_AI_DUMP_Write_Info(DumpInfo_t *info)
{
    uint32_t write_base = g_dump_infotable[g_header_section.info_len].base;
    if (write_base < MIN_DUMP_ADDR || write_base > MAX_DUMP_ADDR) {
        osal_printk("[ERROR] AI Dump Invalid info_item base (0x%04x), base in [0x%04x, 0x%04x]\n", write_base, MIN_DUMP_ADDR, MAX_DUMP_ADDR, MAX_DUMP_ADDR);
        return MS_AI_DUMP_STATUS_FAILED;
    }
    errcode_t res = uapi_sfc_reg_write(write_base, (void *)(&(info->base)), sizeof(info->base));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(info->base);
    res = uapi_sfc_reg_write(write_base, (void *)(&(info->offset)), sizeof(info->offset));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(info->offset);
    res = uapi_sfc_reg_write(write_base, (void *)(&(info->dtype)), sizeof(info->dtype));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(info->dtype);
    write_base += (AI_FILESYS_INFOSECTION_NDIMS - AI_FILESYS_INFOSECTION_DTYPE - sizeof(uint8_t));
    res = uapi_sfc_reg_write(write_base, (void *)(&(info->ndims)), sizeof(info->ndims));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(info->ndims);
    res = uapi_sfc_reg_write(write_base, (void *)(&(info->nameLens)), sizeof(info->nameLens));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(info->nameLens);
    write_base += (AI_FILESYS_INFOSECTION_SHAPE - AI_FILESYS_INFOSECTION_NAMELENS - sizeof(uint16_t));
    for (size_t idx = 0; idx < info->ndims; idx++) {
        res = uapi_sfc_reg_write(write_base, (void *)(&(info->shape[idx])), sizeof(info->shape[idx]));
        if (res != ERRCODE_SUCC) {
            return MS_AI_DUMP_STATUS_FAILED;
        }
        write_base += sizeof(info->shape[idx]);
    }
    write_base = CEIL(write_base, AI_DUMP_ALIGN_BASE);
    res = uapi_sfc_reg_write(write_base, (void *)(info->name), info->nameLens + 1);
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += ((uint32_t)info->nameLens + 1);
    write_base = CEIL(write_base, AI_DUMP_ALIGN_BASE);
    g_dump_infotable[g_header_section.info_len].offset = write_base - g_dump_infotable[g_header_section.info_len].base;
    return res;
}

static MS_AI_DUMP_Status MS_AI_DUMP_Fill_InfoSection_Default(DumpInfo_t *info, size_t offset)
{
    if (!g_header_section.info_len) {
        g_dump_infotable[g_header_section.info_len].base = g_ai_dump_start + g_header_section.header_len;
        info->base = g_header_section.data_ptr;
    } else {
        g_dump_infotable[g_header_section.info_len].base = g_dump_infotable[g_header_section.info_len - 1].base +
            CEIL(g_dump_infotable[g_header_section.info_len - 1].offset, AI_DUMP_ALIGN_BASE);
        info->base = CEIL(g_dump_infosection[g_header_section.info_len - 1].base +
            g_dump_infosection[g_header_section.info_len - 1].offset, AI_DUMP_ALIGN_BASE);
    }
    int res = sprintf_s(info->name, sizeof(info->name), "UNKnown_%hu", g_header_section.info_len);
    if (res <= 0) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    info->offset = offset;
    info->nameLens = strlen(info->name);
    return MS_AI_DUMP_STATUS_SUCCESS;
}

static MS_AI_DUMP_Status MS_AI_DUMP_Fill_InfoSection(DumpInfo_t *info, MS_AI_DUMPInfo *data_info, size_t offset)
{
    if (!g_header_section.info_len) {
        g_dump_infotable[g_header_section.info_len].base = g_ai_dump_start + g_header_section.header_len;
        info->base = g_header_section.data_ptr;
    } else {
        g_dump_infotable[g_header_section.info_len].base = g_dump_infotable[g_header_section.info_len - 1].base +
            CEIL(g_dump_infotable[g_header_section.info_len - 1].offset, AI_DUMP_ALIGN_BASE);
        info->base = CEIL(g_dump_infosection[g_header_section.info_len - 1].base +
            g_dump_infosection[g_header_section.info_len - 1].offset, AI_DUMP_ALIGN_BASE);
    }
    int res = memset_s(info->name, sizeof(info->name), '\0', 1);
    if (res != 0) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    uint32_t target_len = strlen(data_info->name);
    if (target_len + AI_FILESYS_INFOSECTION_SHAPE + sizeof(uint16_t) * data_info->ndims + 1 > AI_FILESYS_INFOSECTION_SIZE) {
        target_len = AI_FILESYS_INFOSECTION_SIZE - 1 - sizeof(uint16_t) * data_info->ndims - AI_FILESYS_INFOSECTION_SHAPE;
    }
    info->nameLens = target_len;
    memcpy_s(info->name, sizeof(info->name), data_info->name, target_len);
    memcpy_s(info->shape, sizeof(info->shape), data_info->shape, info->ndims * sizeof(uint16_t));
    info->offset = offset;
    info->ndims = data_info->ndims;
    info->dtype = data_info->dtype;
    return MS_AI_DUMP_STATUS_SUCCESS;
}

static void MS_AI_DUMP_Clear_Info(DumpInfo_t *info)
{
    memset_s(info->name, sizeof(info->name), '\0', 1);
    memset_s(info->shape, sizeof(info->shape), '\0', 1);
    info->nameLens = 0;
    info->base = 0x00000000;
    info->offset = 0;
    info->dtype = MS_AI_DUMP_UNKNOWN;
    info->ndims = 0;
}

MS_AI_DUMP_Status MS_AI_DUMPInit(uint32_t base, uint32_t offset)
{
    if (base < MIN_DUMP_ADDR || base + offset > MAX_DUMP_ADDR || offset <= 0) {
        osal_printk("[ERROR] MS_AI_DUMPInit Failed\n");
        return MS_AI_DUMP_STATUS_FAILED;
    }
    g_ai_dump_start = base;
    g_ai_dump_max_size = offset;

    /* 0. Erase All Section */
    errcode_t res = uapi_sfc_reg_erase(g_ai_dump_start, CEIL(g_ai_dump_max_size, AI_DUMP_ALIGN_BASE));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }

    /* 1. Init header section */
    g_header_section.header_len = CEIL(AI_FILESYS_HEADSECTION_SIZE + AI_DUMP_MAX_BLOCK_NUM * AI_FILESYS_INFOTABLE_ITEM_SIZE,
        AI_DUMP_ALIGN_BASE);
    g_header_section.data_ptr = CEIL(g_ai_dump_start + g_header_section.header_len + AI_DUMP_MAX_BLOCK_NUM *
        AI_FILESYS_INFOSECTION_SIZE, AI_DUMP_ALIGN_BASE);

    uint32_t write_base = g_ai_dump_start;
    res = uapi_sfc_reg_write(write_base, (void *)(&(g_header_section.magic)), sizeof(g_header_section.magic));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(g_header_section.magic);
    res = uapi_sfc_reg_write(write_base, (void *)(&(g_header_section.version)), sizeof(g_header_section.version));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(g_header_section.version);
    return res;
}

MS_AI_DUMP_Status MS_AI_DUMP_Data_Without_Info(void *data, size_t size)
{
    /* 0. Error Check */
    MS_AI_DUMP_Status res = MS_AI_Dump_Check_Dump_Info(data, size);
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        return res;
    }
    /* 1. Generate Info */
    res = MS_AI_DUMP_Fill_InfoSection_Default(&(g_dump_infosection[g_header_section.info_len]), size);
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        osal_printk("[ERROR] MS_AI_DUMP_Fill_InfoSection_Default Failed\n");
        MS_AI_DUMP_Clear_Info(&(g_dump_infosection[g_header_section.info_len]));
        return res;
    }
    /* 2. Allocate and Register Info */
    res = MS_AI_DUMP_Write_Info(&(g_dump_infosection[g_header_section.info_len]));
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        osal_printk("[ERROR] MS_AI_DUMP_Write_Info Failed\n");
        return res;
    }
    /* 3. Write Info */
    res = MS_AI_DUMP_Write_Header_Info_Table();
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        osal_printk("[ERROR] MS_AI_DUMP_Write_Header_Info_Table Failed\n");
        return res;
    }
    /* 4. Write Data */
    res = uapi_sfc_reg_write(g_dump_infosection[g_header_section.info_len - 1].base, data, size);
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        return res;
    }
    return MS_AI_DUMP_STATUS_SUCCESS;
}

MS_AI_DUMP_Status MS_AI_DUMP_Data_With_Info(void *data, size_t size, MS_AI_DUMPInfo *data_info)
{
    /* 0. Error Check */
    MS_AI_DUMP_Status res = MS_AI_Dump_Check_Dump_Info(data, size);
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        return res;
    }
    if (data_info->ndims > AI_FILESYS_MAX_NDIMS) {
        osal_printk("[ERROR] MS_AI_DUMP_Data_Without_Info nDims is too large\n");
        return MS_AI_DUMP_STATUS_FAILED;
    }
    /* 1. Generate Info */
    res = MS_AI_DUMP_Fill_InfoSection(&(g_dump_infosection[g_header_section.info_len]), data_info, size);
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        osal_printk("[ERROR] MS_AI_DUMP_Fill_Info Failed\n");
        MS_AI_DUMP_Clear_Info(&(g_dump_infosection[g_header_section.info_len]));
        return res;
    }
    /* 2. Allocate and Register Info */
    res = MS_AI_DUMP_Write_Info(&(g_dump_infosection[g_header_section.info_len]));
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        osal_printk("[ERROR] MS_AI_DUMP_Write_Info Failed\n");
        return res;
    }
    /* 3. Write Info */
    res = MS_AI_DUMP_Write_Header_Info_Table();
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        osal_printk("[ERROR] MS_AI_DUMP_Write_Header_Info_Table Failed\n");
        return res;
    }
    /* 4. Write Data */
    res = uapi_sfc_reg_write(g_dump_infosection[g_header_section.info_len].base, data, size);
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        return res;
    }
    return res;
}

MS_AI_DUMP_Status MS_AI_DUMP_Store(void)
{
    uint32_t write_base = g_ai_dump_start;
    write_base += AI_FILESYS_HEADSECTION_HEADER_LEN;
    errcode_t res = uapi_sfc_reg_write(write_base, (void *)(&(g_header_section.header_len)), sizeof(g_header_section.header_len));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(g_header_section.header_len);
    res = uapi_sfc_reg_write(write_base, (void *)(&(g_header_section.info_len)), sizeof(g_header_section.info_len));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(g_header_section.info_len);
    res = uapi_sfc_reg_write(write_base, (void *)(&(g_header_section.data_ptr)), sizeof(g_header_section.data_ptr));
    if (res != ERRCODE_SUCC) {
        return MS_AI_DUMP_STATUS_FAILED;
    }
    write_base += sizeof(g_header_section.data_ptr);
    return MS_AI_DUMP_STATUS_SUCCESS;
}

MS_AI_DUMP_Status MS_AI_DUMP_DeInit(void)
{
    MS_AI_DUMP_Status res = uapi_sfc_reg_erase(g_ai_dump_start, CEIL(AI_DUMP_MAX_SIZE,
        AI_DUMP_ALIGN_BASE));
    if (res != MS_AI_DUMP_STATUS_SUCCESS) {
        return res;
    }
    return MS_AI_DUMP_STATUS_SUCCESS;
}