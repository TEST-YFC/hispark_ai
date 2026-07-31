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

#include "utils.h"
#include <stdio.h>
#include <stdint.h>
#include "math.h"
#include "securec.h"

static const int32_t g_deviceNodeId = 0;

// 初始化模型
Result NpuEnvInit(ModelInfo *modelInfo)
{
    aclError ret;
    // 初始化ACL环境
    ret = aclInit(NULL);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclInit return failed, error code is:%d\n", ret);
        return FAILED;
    }
    // 初始化设备
    ret = aclrtSetDevice(g_deviceNodeId);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclrtSetDevice return failed, error code is:%d\n", ret);
        return FAILED;
    }
    osal_printk("Set device %d success\n", g_deviceNodeId);
    // 初始化上下文
    ret = aclrtCreateContext(&modelInfo->context, g_deviceNodeId);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclrtCreateContext return failed, error code is:%d\n", ret);
        return FAILED;
    }
    // 初始化流配置句柄
    aclrtStreamConfigHandle *handle = aclrtCreateStreamConfigHandle();
    // 初始化流
    ret = aclrtCreateStreamV2(&modelInfo->modelStream, handle);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclrtCreateStream return failed, error code is:%d\n", ret);
        aclrtDestroyStreamConfigHandle(handle);
        return FAILED;
    }
    // 销毁句柄
    aclrtDestroyStreamConfigHandle(handle);
    return SUCCESS;
}

// 加载模型
Result LoadModel(ModelInfo *modelInfo, const char *modelPath, const char *modelInputFile, const char *modelOutputFile)
{
    aclError ret;
    MemInfo *memInfo = &modelInfo->memInfo;
    if (strlen(modelPath) >= MAX_FILE_NAME_LEN || strlen(modelInputFile) >= MAX_FILE_NAME_LEN || strlen(modelOutputFile) >= MAX_FILE_NAME_LEN) {
        osal_printk("File path is too long\n");
        return FAILED;
    }
    // 复制模型文件路径
    (void)memcpy_s(modelInfo->modelFile, MAX_FILE_NAME_LEN, modelPath, MAX_FILE_NAME_LEN);
    (void)memcpy_s(modelInfo->inputPath, MAX_FILE_NAME_LEN, modelInputFile, MAX_FILE_NAME_LEN);
    (void)memcpy_s(modelInfo->outputPath, MAX_FILE_NAME_LEN, modelOutputFile, MAX_FILE_NAME_LEN);
    // 获取workSize和weightSize
    ret = aclmdlQuerySize(modelPath, &memInfo->workSize, &memInfo->weightSize);
    if (ret != ACL_SUCCESS) {
        osal_printk("Interface of aclmdlQuerySize return failed, error code is:%d\n", ret);
        return FAILED;
    }
    osal_printk("Get model work_space_size[%u], weight_size[%u]\n", memInfo->workSize, memInfo->weightSize);
    // 开辟weightSize大小的内存
    ret = aclrtMalloc(&memInfo->weight, memInfo->weightSize, ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        osal_printk("aclrtMalloc failed, weight_size[%u]\n", memInfo->weightSize);
        return FAILED;
    }
    // 开辟workSize大小的内存
    ret = aclrtMalloc(&memInfo->workspace, memInfo->workSize, ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        osal_printk("aclrtMalloc failed, work_size[%u]\n", memInfo->workSize);
        return FAILED;
    }
    // 初始化加载配置句柄
    aclmdlConfigHandle *mdlConfigHandle = aclmdlCreateConfigHandle();
    // 设置加载配置句柄
    aclmdlSetConfigOpt(mdlConfigHandle, ACL_MDL_WEIGHT_ADDR_PTR, &memInfo->weight, sizeof(memInfo->weight));
    aclmdlSetConfigOpt(mdlConfigHandle, ACL_MDL_WEIGHT_SIZET, &memInfo->weightSize, sizeof(memInfo->weightSize));
    aclmdlSetConfigOpt(mdlConfigHandle, ACL_MDL_PATH_PTR, &modelPath, sizeof(modelPath));
    size_t loadType = ACL_MDL_LOAD_FROM_FILE_WITH_MEM;
    aclmdlSetConfigOpt(mdlConfigHandle, ACL_MDL_LOAD_TYPE_SIZET, &loadType, sizeof(loadType));
    // 加载模型
    ret = aclmdlLoadWithConfig(mdlConfigHandle, &modelInfo->modelId);
    if (ret != ACL_SUCCESS) {
        osal_printk("Interface of aclmdlLoadFromFileWithMem return failed, error code is:%d\n", ret);
        aclmdlDestroyConfigHandle(mdlConfigHandle);
        return FAILED;
    }
    // 销毁句柄
    aclmdlDestroyConfigHandle(mdlConfigHandle);
    osal_printk("Load model <%s> succeed\n", modelPath);
    return SUCCESS;
}

// 创建输入
Result CreateModelInput(ModelInfo *modelInfo)
{
    aclError ret;
    void *inputBuffer = NULL;
    MemInfo *memInfo = &modelInfo->memInfo;
    // 创建输入Dataset
    memInfo->input = aclmdlCreateDataset();
    if (memInfo->input == NULL) {
        osal_printk("Interface of aclmdlCreateDataset return failed\n");
        return FAILED;
    }
    // 开辟输入文件大小的内存
    ret = aclrtMalloc(&inputBuffer, INPUT_SIZE, ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("aclrtMalloc failed, size[%u]\n", INPUT_SIZE);
        return FAILED;
    }
    // 创建模型输入DataBuffer
    aclDataBuffer *inputData = aclCreateDataBuffer(inputBuffer, INPUT_SIZE);
    if (inputData == NULL) {
        osal_printk("Interface of aclCreateDataBuffer return failed\n");
        return FAILED;
    }
    // 将DataBuffer添加到Dataset中
    ret = aclmdlAddDatasetBuffer(memInfo->input, inputData);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclmdlAddDatasetBuffer return failed, error code is:%d\n", ret);
        return FAILED;
    }
    // 获取输入DataBuffer地址
    void *batchDst = aclGetDataBufferAddr(inputData);
    // 将输入文件读入内存
    FILE *fp = fopen(modelInfo->inputPath, "rb");
    if (fp == NULL) {
        osal_printk("%s open fail\n", modelInfo->inputPath);
        return FAILED;
    }
    (void)fread(batchDst, sizeof(char), INPUT_SIZE, fp);
    (void)fclose(fp);
    return SUCCESS;
}

// 创建输出
Result CreateModelOutput(ModelInfo *modelInfo)
{
    aclError ret;
    void *outputBuffer = NULL;
    MemInfo *memInfo = &modelInfo->memInfo;
    // 创建输出Dataset
    memInfo->output = aclmdlCreateDataset();
    if (memInfo->output == NULL) {
        osal_printk("Interface of aclmdlCreateDataset return failed\n");
        return FAILED;
    }
    // 开辟输出文件大小的内存
    ret = aclrtMalloc(&outputBuffer, OUTPUT_SIZE, ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("aclrtMalloc failed, work_size[%u]\n", OUTPUT_SIZE);
        return FAILED;
    }
    // 创建模型输出DataBuffer
    aclDataBuffer *outputData = aclCreateDataBuffer(outputBuffer, OUTPUT_SIZE);
    if (outputData == NULL) {
        osal_printk("Interface of aclCreateDataBuffer return failed\n");
        return FAILED;
    }
    // 将DataBuffer添加到Dataset中
    ret = aclmdlAddDatasetBuffer(memInfo->output, outputData);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclmdlAddDatasetBuffer return failed, error code is:%d\n", ret);
        return FAILED;
    }
    return SUCCESS;
}

// 销毁Dataset
static void DestroyDataset(aclmdlDataset *dataset)
{
    // 遍历Dataset中的DataBuffer
    for (size_t i = 0; i < aclmdlGetDatasetNumBuffers(dataset); ++i) {
        // 获取DataBuffer
        aclDataBuffer *dataBuffer = aclmdlGetDatasetBuffer(dataset, i);
        // 获取DataBuffer地址
        void *data = aclGetDataBufferAddr(dataBuffer);
        // 释放DataBuffer内存
        aclrtFree(data);
        // 销毁DataBuffer
        aclDestroyDataBuffer(dataBuffer);
    }
    // 销毁Dataset
    aclmdlDestroyDataset(dataset);
}

// 销毁输入输出
static void ResetDataset(MemInfo *memInfo)
{
    if (memInfo->input != NULL) {
        // 销毁输入Dataset
        DestroyDataset(memInfo->input);
        memInfo->input = NULL;
    }
    if (memInfo->output != NULL) {
        // 销毁输出Dataset
        DestroyDataset(memInfo->output);
        memInfo->output = NULL;
    }
}

// Dump输出
static Result DumpOutput(ModelInfo *modelInfo)
{
    // 获取Dataset中的DataBuffer
    aclDataBuffer *dataBuffer = aclmdlGetDatasetBuffer(modelInfo->memInfo.output, 0);
    // 获取DataBuffer地址
    void *data = aclGetDataBufferAddr(dataBuffer);
    // 计算DataBuffer大小
    uint32_t totalLen = aclGetDataBufferSizeV2(dataBuffer);
    // 将输出写入到文件中
    FILE *fop = fopen(modelInfo->outputPath, "wb+");
    if (fop == NULL) {
        osal_printk("%s open failed\n", modelInfo->outputPath);
        return FAILED;
    }
    (void)fwrite((uint8_t *) data, totalLen, sizeof(char), fop);
    (void)fclose(fop);
    return SUCCESS;
}

// 模型执行
Result ExecuteModel(ModelInfo *modelInfo)
{
    aclError ret;
    // 初始化模型执行句柄
    aclmdlExecConfigHandle *mdlExecHandle = aclmdlCreateExecConfigHandle();
    MemInfo *memInfo = &modelInfo->memInfo;
    // 设置模型执行句柄
    aclmdlSetExecConfigOpt(mdlExecHandle, ACL_MDL_WORK_ADDR_PTR, &memInfo->workspace, sizeof(memInfo->workspace));
    aclmdlSetExecConfigOpt(mdlExecHandle, ACL_MDL_WORK_SIZET, &memInfo->workSize, sizeof(memInfo->workSize));
    // 模型执行
    ret = aclmdlExecuteV2(modelInfo->modelId, memInfo->input, memInfo->output, modelInfo->modelStream, mdlExecHandle);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclmdlExecute return failed, error code is:%d\n", ret);
        aclmdlDestroyExecConfigHandle(mdlExecHandle);
        return FAILED;
    }
    // 销毁模型执行句柄
    aclmdlDestroyExecConfigHandle(mdlExecHandle);
    // 将推理结果写到输出
    if (DumpOutput(modelInfo) != SUCCESS) {
        ResetDataset(memInfo);
        return FAILED;
    }
    // 销毁输入输出
    ResetDataset(memInfo);
    return SUCCESS;
}

// 销毁模型
static void FreeModelInfo(ModelInfo *modelInfo)
{
    MemInfo *memInfo = &modelInfo->memInfo;
    // 销毁输入输出
    ResetDataset(memInfo);
    // 销毁模型信息
    if (memInfo->weight != NULL) {
        aclrtFree(memInfo->weight);
    }
    if (memInfo->workspace != NULL) {
        aclrtFree(memInfo->workspace);
    }
    // 销毁模型
    aclmdlUnload(modelInfo->modelId);
    // 销毁工作流
    if (modelInfo->modelStream != NULL) {
        aclrtDestroyStream(modelInfo->modelStream);
    }
}

// 销毁资源
void NpuEnvFinalize(ModelInfo *modelInfo)
{
    // 销毁模型
    if (modelInfo != NULL) {
        FreeModelInfo(modelInfo);
    }
    // 销毁上下文
    aclrtDestroyContext(modelInfo->context);
    // 复位Device
    aclrtResetDevice(g_deviceNodeId);
    // 销毁ACL环境
    aclFinalize();
}
