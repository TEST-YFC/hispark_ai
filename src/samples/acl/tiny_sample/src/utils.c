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
    modelInfo->envInited = 1;
    // 初始化设备
    ret = aclrtSetDevice(g_deviceNodeId);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclrtSetDevice return failed, error code is:%d\n", ret);
        return FAILED;
    }
    modelInfo->deviceSet = 1;
    osal_printk("Set device %d success\n", g_deviceNodeId);
    // 初始化上下文
    ret = aclrtCreateContext(&modelInfo->context, g_deviceNodeId);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclrtCreateContext return failed, error code is:%d\n", ret);
        return FAILED;
    }
    // 初始化流
    ret = aclrtCreateStream(&modelInfo->modelStream);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclrtCreateStream return failed, error code is:%d\n", ret);
        return FAILED;
    }
    return SUCCESS;
}

// 加载模型
Result LoadModel(ModelInfo *modelInfo)
{
    aclError ret;
    aclmdlConfigHandle *mdlConfigHandle = NULL;
    MemInfo *memInfo = &modelInfo->memInfo;
    // 获取workSize和weightSize
    ret = aclmdlQuerySize(modelInfo->modelFile, &memInfo->workSize, &memInfo->weightSize);
    if (ret != ACL_SUCCESS) {
        osal_printk("Interface of aclmdlQuerySize return failed, error code is:%d\n", ret);
        return FAILED;
    }
    osal_printk("Get model work_space_size[%zu], weight_size[%zu]\n", memInfo->workSize, memInfo->weightSize);
    // 开辟weightSize大小的内存
    ret = aclrtMalloc(&memInfo->weight, memInfo->weightSize, ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        osal_printk("aclrtMalloc failed, weight_size[%zu]\n", memInfo->weightSize);
        return FAILED;
    }
    // 开辟workSize大小的内存
    ret = aclrtMalloc(&memInfo->workspace, memInfo->workSize, ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        osal_printk("aclrtMalloc failed, work_size[%zu]\n", memInfo->workSize);
        return FAILED;
    }
    // 初始化加载配置句柄
    mdlConfigHandle = aclmdlCreateConfigHandle();
    if (mdlConfigHandle == NULL) {
        osal_printk("Interface of aclmdlCreateConfigHandle return failed\n");
        return FAILED;
    }
    // 设置加载配置句柄
    ret = aclmdlSetConfigOpt(mdlConfigHandle, ACL_MDL_WEIGHT_ADDR_PTR, &memInfo->weight, sizeof(memInfo->weight));
    if (ret != ACL_SUCCESS) {
        osal_printk("Interface of aclmdlSetConfigOpt(ACL_MDL_WEIGHT_ADDR_PTR) return failed, error code is:%d\n", ret);
        aclmdlDestroyConfigHandle(mdlConfigHandle);
        return FAILED;
    }
    ret = aclmdlSetConfigOpt(mdlConfigHandle, ACL_MDL_WEIGHT_SIZET, &memInfo->weightSize, sizeof(memInfo->weightSize));
    if (ret != ACL_SUCCESS) {
        osal_printk("Interface of aclmdlSetConfigOpt(ACL_MDL_WEIGHT_SIZET) return failed, error code is:%d\n", ret);
        aclmdlDestroyConfigHandle(mdlConfigHandle);
        return FAILED;
    }
    ret = aclmdlSetConfigOpt(mdlConfigHandle, ACL_MDL_PATH_PTR, &modelInfo->modelFile, sizeof(modelInfo->modelFile));
    if (ret != ACL_SUCCESS) {
        osal_printk("Interface of aclmdlSetConfigOpt(ACL_MDL_PATH_PTR) return failed, error code is:%d\n", ret);
        aclmdlDestroyConfigHandle(mdlConfigHandle);
        return FAILED;
    }
    size_t loadType = ACL_MDL_LOAD_FROM_FILE_WITH_MEM;
    ret = aclmdlSetConfigOpt(mdlConfigHandle, ACL_MDL_LOAD_TYPE_SIZET, &loadType, sizeof(loadType));
    if (ret != ACL_SUCCESS) {
        osal_printk("Interface of aclmdlSetConfigOpt(ACL_MDL_LOAD_TYPE_SIZET) return failed, error code is:%d\n", ret);
        aclmdlDestroyConfigHandle(mdlConfigHandle);
        return FAILED;
    }
    // 加载模型
    ret = aclmdlLoadWithConfig(mdlConfigHandle, &modelInfo->modelId);
    if (ret != ACL_SUCCESS) {
        osal_printk("Interface of aclmdlLoadFromFileWithMem return failed, error code is:%d\n", ret);
        aclmdlDestroyConfigHandle(mdlConfigHandle);
        return FAILED;
    }
    // 销毁句柄
    aclmdlDestroyConfigHandle(mdlConfigHandle);
    osal_printk("Load model <%s> succeed\n", modelInfo->modelFile);
    return SUCCESS;
}

// 创建模型描述
Result CreateModelDesc(ModelInfo *modelInfo)
{
    aclError ret;
    // 创建模型描述指针
    modelInfo->modelDesc = aclmdlCreateDesc();
    if (modelInfo->modelDesc == NULL) {
        osal_printk("Interface of aclmdlCreateDesc return failed\n");
        return FAILED;
    }
    // 获取模型描述
    ret = aclmdlGetDesc(modelInfo->modelDesc, modelInfo->modelId);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclmdlGetDesc return failed, error code is:%d\n", ret);
        return FAILED;
    }
    return SUCCESS;
}

// 创建输入
Result CreateModelInput(ModelInfo *modelInfo)
{
    aclError ret;
    void *inputBuffer = NULL;
    MemInfo *memInfo = &modelInfo->memInfo;
    // 获取输入个数
    size_t inputNum = aclmdlGetNumInputs(modelInfo->modelDesc);
    if (inputNum != modelInfo->inputNum) {
        osal_printk("input items count error! need count: %zu, real count: %zu\n", modelInfo->inputNum, inputNum);
        return FAILED;
    }

    // 创建输入Dataset
    memInfo->input = aclmdlCreateDataset();
    if (memInfo->input == NULL) {
        osal_printk("Interface of aclmdlCreateDataset return failed\n");
        return FAILED;
    }
    for (size_t index = 0; index < inputNum; index++) {
        size_t inputSize = aclmdlGetInputSizeByIndex(modelInfo->modelDesc, index);
        // 开辟输入文件大小的内存
        ret = aclrtMalloc(&inputBuffer, inputSize, ACL_MEM_MALLOC_NORMAL_ONLY);
        if (ret != ACL_ERROR_NONE) {
            osal_printk("aclrtMalloc failed, size[%zu]\n", inputSize);
            return FAILED;
        }
        // 创建模型输入DataBuffer
        aclDataBuffer *inputData = aclCreateDataBuffer(inputBuffer, inputSize);
        if (inputData == NULL) {
            osal_printk("Interface of aclCreateDataBuffer return failed\n");
            aclrtFree(inputBuffer);
            return FAILED;
        }
        // 将DataBuffer添加到Dataset中
        ret = aclmdlAddDatasetBuffer(memInfo->input, inputData);
        if (ret != ACL_ERROR_NONE) {
            osal_printk("Interface of aclmdlAddDatasetBuffer return failed, error code is:%d\n", ret);
            aclDestroyDataBuffer(inputData);
            aclrtFree(inputBuffer);
            return FAILED;
        }
        // 获取输入DataBuffer地址
        void *batchDst = aclGetDataBufferAddr(inputData);
        // 将输入文件读入内存
        FILE *fp = fopen(modelInfo->inputFileList[index], "rb");
        if (fp == NULL) {
            osal_printk("%s open fail\n", modelInfo->inputFileList[index]);
            return FAILED;
        }
        size_t readSize = fread(batchDst, sizeof(char), inputSize, fp);
        if (readSize != inputSize) {
            osal_printk("read %s fail, expected[%zu], actual[%zu]\n", modelInfo->inputFileList[index], inputSize, readSize);
            (void)fclose(fp);
            return FAILED;
        }
        (void)fclose(fp);
    }
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
    // 获取输出个数
    size_t outputNum = aclmdlGetNumOutputs(modelInfo->modelDesc);
    for (size_t index = 0; index < outputNum; index++) {
        // 获取输出Size
        size_t bufferSize = aclmdlGetOutputSizeByIndex(modelInfo->modelDesc, index);
        // 开辟输出文件大小的内存
        ret = aclrtMalloc(&outputBuffer, bufferSize, ACL_MEM_MALLOC_NORMAL_ONLY);
        if (ret != ACL_ERROR_NONE) {
            osal_printk("aclrtMalloc failed, work_size[%zu]\n", bufferSize);
            return FAILED;
        }
        // 创建模型输出DataBuffer
        aclDataBuffer *outputData = aclCreateDataBuffer(outputBuffer, bufferSize);
        if (outputData == NULL) {
            osal_printk("Interface of aclCreateDataBuffer return failed\n");
            aclrtFree(outputBuffer);
            return FAILED;
        }
        // 将DataBuffer添加到Dataset中
        ret = aclmdlAddDatasetBuffer(memInfo->output, outputData);
        if (ret != ACL_ERROR_NONE) {
            osal_printk("Interface of aclmdlAddDatasetBuffer return failed, error code is:%d\n", ret);
            aclDestroyDataBuffer(outputData);
            aclrtFree(outputBuffer);
            return FAILED;
        }
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
static Result DumpOutput(ModelInfo *modelInfo, size_t index)
{
    // 获取Dataset中的DataBuffer
    aclDataBuffer *dataBuffer = aclmdlGetDatasetBuffer(modelInfo->memInfo.output, index);
    // 获取DataBuffer地址
    void *data = aclGetDataBufferAddr(dataBuffer);
    // 计算DataBuffer大小
    size_t totalLen = aclGetDataBufferSizeV2(dataBuffer);
    // 将输出写入到文件中
    char outputFileName[MAX_FILE_NAME_LEN];
    int ret = snprintf_s(outputFileName, sizeof(outputFileName), sizeof(outputFileName) - 1, "%s/output_%zu.bin", modelInfo->outputPath, index);
    if (ret < 0 || ret >= sizeof(outputFileName)) {
        osal_printk("output file name %s is invalid\n", outputFileName);
        return FAILED;
    }
    FILE *fop = fopen(outputFileName, "wb+");
    if (fop == NULL) {
        osal_printk("%s open failed\n", outputFileName);
        return FAILED;
    }
    size_t writeSize = fwrite((uint8_t *) data, sizeof(char), totalLen, fop);
    if (writeSize != totalLen) {
        osal_printk("write %s fail, expected[%u], actual[%zu]\n", outputFileName, totalLen, writeSize);
        (void)fclose(fop);
        return FAILED;
    }
    (void)fclose(fop);
    return SUCCESS;
}

// 模型执行
Result ExecuteModel(ModelInfo *modelInfo)
{
    aclError ret;
    aclError SynchronizeStreamRet;
    MemInfo *memInfo = &modelInfo->memInfo;
    // 模型执行
    ret = aclmdlExecuteAsync(modelInfo->modelId, memInfo->input, memInfo->output, modelInfo->modelStream);
    if (ret != ACL_ERROR_NONE) {
        osal_printk("Interface of aclmdlExecute return failed, error code is:%d\n", ret);
        return FAILED;
    }
    // 执行成功后再同步等待流
    SynchronizeStreamRet = aclrtSynchronizeStream(modelInfo->modelStream);
    if (SynchronizeStreamRet != ACL_ERROR_NONE) {
        osal_printk("Interface of aclrtSynchronizeStream return failed, error code is:%d\n", SynchronizeStreamRet);
        return FAILED;
    }
    // 根据输出数据集来获取输出个数
    size_t outputNum = aclmdlGetDatasetNumBuffers(memInfo->output);
    for (size_t index = 0; index < outputNum; index++) {
        // 将推理结果写到输出
        if (DumpOutput(modelInfo, index) != SUCCESS) {
            ResetDataset(memInfo);
            return FAILED;
        }
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
    // 销毁模型描述
    if (modelInfo->modelDesc != NULL) {
        aclmdlDestroyDesc(modelInfo->modelDesc);
    }
    // 销毁工作流
    if (modelInfo->modelStream != NULL) {
        aclrtDestroyStream(modelInfo->modelStream);
    }
    // 销毁上下文
    if (modelInfo->context != NULL) {
        aclrtDestroyContext(modelInfo->context);
    }
}

// 销毁资源
void NpuEnvFinalize(ModelInfo *modelInfo)
{
    // 销毁模型
    if (modelInfo != NULL) {
        FreeModelInfo(modelInfo);
        // 仅当Device初始化成功时才复位Device
        if (modelInfo->deviceSet) {
            aclrtResetDevice(g_deviceNodeId);
        }
        // 仅当ACL环境初始化成功时才销毁ACL环境
        if (modelInfo->envInited) {
            aclFinalize();
        }
    }
}
