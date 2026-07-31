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
#include <stdbool.h>
#include "math.h"
#include "securec.h"

static const int32_t g_deviceNodeId = 0;
static const uint32_t g_inputSize[INPUT_NUM] = {1568};
static const uint32_t g_outputSize[OUTPUT_NUM] = {20};
enum { LENET5_MODEL_INPUT };
enum { LENET5_MODEL_OUTPUT };
static void *g_modelInput = NULL;
static void *g_modelOutput = NULL;

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

// 开辟输入输出内存
static Result ModelMemAlloc(void)
{
    aclError ret;
    ret = aclrtMalloc(&g_modelInput, g_inputSize[LENET5_MODEL_INPUT], ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        osal_printk("aclrtMalloc failed, input_size[%u]\n", g_inputSize[LENET5_MODEL_INPUT]);
        return FAILED;
    }
    ret = aclrtMalloc(&g_modelOutput, g_outputSize[LENET5_MODEL_OUTPUT], ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        osal_printk("aclrtMalloc failed, output_size[%u]\n", g_outputSize[LENET5_MODEL_OUTPUT]);
        return FAILED;
    }
    return SUCCESS;
}

// 释放输入输出内存
static void ModelMemFree(void)
{
    if (g_modelInput != NULL) {
        aclrtFree(g_modelInput);
        g_modelInput = NULL;
    }
    if (g_modelOutput != NULL) {
        aclrtFree(g_modelOutput);
        g_modelOutput = NULL;
    }
}

// 加载模型
Result LoadModel(ModelInfo *modelInfo, const char *modelPath, const char *modelInputFile)
{
    aclError ret;
    MemInfo *memInfo = &modelInfo->memInfo;
    if (strlen(modelPath) >= MAX_FILE_NAME_LEN || strlen(modelInputFile) >= MAX_FILE_NAME_LEN) {
        osal_printk("File path is too long\n");
        return FAILED;
    }
    // 复制模型文件路径
    (void)memcpy_s(modelInfo->modelFile, MAX_FILE_NAME_LEN, modelPath, MAX_FILE_NAME_LEN);
    (void)memcpy_s(modelInfo->inputFile, MAX_FILE_NAME_LEN, modelInputFile, MAX_FILE_NAME_LEN);
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
    // 开辟输入输出内存
    if (ModelMemAlloc() != SUCCESS) {
        osal_printk("In/Out Memory alloc failed\n");
        return FAILED;
    }
    osal_printk("Load model <%s> succeed\n", modelPath);
    return SUCCESS;
}

// 销毁Dataset
static void MemInfoReset(MemInfo *memInfo)
{
    if (memInfo->input != NULL) {
        size_t inputDatasetNumBuffers = aclmdlGetDatasetNumBuffers(memInfo->input);
        for (size_t i = 0; i < inputDatasetNumBuffers; ++i) {
            aclDataBuffer *dataBuffer = aclmdlGetDatasetBuffer(memInfo->input, i);
            aclDestroyDataBuffer(dataBuffer);
        }
        aclmdlDestroyDataset(memInfo->input);
        memInfo->input = NULL;
    }

    if (memInfo->output != NULL) {
        size_t outputDatasetNumBuffers = aclmdlGetDatasetNumBuffers(memInfo->output);
        for (size_t i = 0; i < outputDatasetNumBuffers; ++i) {
            aclDataBuffer *dataBuffer = aclmdlGetDatasetBuffer(memInfo->output, i);
            aclDestroyDataBuffer(dataBuffer);
        }
        aclmdlDestroyDataset(memInfo->output);
        memInfo->output = NULL;
    }
}

// 创建输入Dataset
static Result CreateInputDataset(MemInfo *memInfo, void **inputAddr)
{
    aclError ret;
    memInfo->input = aclmdlCreateDataset();
    if (memInfo->input == NULL) {
        osal_printk("Interface of aclmdlCreateDataset return failed\n");
        return FAILED;
    }

    for (int32_t i = 0; i < INPUT_NUM; ++i) {
        aclDataBuffer *inputData = aclCreateDataBuffer(inputAddr[i], g_inputSize[i]);
        if (inputData == NULL) {
            osal_printk("Interface of aclCreateDataBuffer return failed\n");
            return FAILED;
        }
        ret = aclmdlAddDatasetBuffer(memInfo->input, inputData);
        if (ret != ACL_SUCCESS) {
            osal_printk("Interface of aclmdlAddDatasetBuffer return failed, error code is:%d\n", ret);
            return FAILED;
        }
    }
    return SUCCESS;
}

// 创建输出Dataset
static Result CreateOutputDataset(MemInfo *memInfo, void **outputAddr)
{
    aclError ret;
    memInfo->output = aclmdlCreateDataset();
    if (memInfo->output == NULL) {
        osal_printk("Interface of aclmdlCreateDataset return failed\n");
        return FAILED;
    }

    for (int32_t i = 0; i < OUTPUT_NUM; ++i) {
        aclDataBuffer *outputData = aclCreateDataBuffer(outputAddr[i], g_outputSize[i]);
        if (outputData == NULL) {
            osal_printk("Interface of aclCreateDataBuffer return failed\n");
            return FAILED;
        }
        ret = aclmdlAddDatasetBuffer(memInfo->output, outputData);
        if (ret != ACL_SUCCESS) {
            osal_printk("Interface of aclmdlAddDatasetBuffer return failed, error code is:%d\n", ret);
            return FAILED;
        }
    }
    return SUCCESS;
}

// 获取输入数据地址
static void GetInputAddr(void **inputAddr)
{
    inputAddr[LENET5_MODEL_INPUT] = g_modelInput;
}

// 获取输出数据地址
static void GetOutputAddr(void **outputAddr)
{
    outputAddr[LENET5_MODEL_OUTPUT] = g_modelOutput;
}

// 从文件中读取输入数据
static Result GetInputData(const char *filePath)
{
    uint32_t fileSize = g_inputSize[LENET5_MODEL_INPUT];
    FILE *fp = NULL;
    fp = fopen(filePath, "rb");
    if (fp == NULL) {
        osal_printk("Open %s failed\n", filePath);
        return FAILED;
    }
    (void)fread(g_modelInput, sizeof(char), fileSize, fp);
    (void)fclose(fp);
    return SUCCESS;
}

// 模型开始执行
static Result ModelExecuteStart(ModelInfo *modelInfo)
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
    return SUCCESS;
}

// 模型执行前准备，填写输入输出Dataset
Result ModelExecute(ModelInfo *modelInfo)
{
    MemInfo *memInfo = &modelInfo->memInfo;
    void *inputAddr[INPUT_NUM];
    void *outputAddr[OUTPUT_NUM];
    // 从文件中读取输入数据
    if (GetInputData(modelInfo->inputFile) != SUCCESS) {
        osal_printk("Get input data failed\n");
        return FAILED;
    }
    // 获取输入输出数据地址
    GetInputAddr(inputAddr);
    GetOutputAddr(outputAddr);
    // 创建输入输出Dataset
    if (CreateInputDataset(memInfo, inputAddr) != SUCCESS) {
        osal_printk("Create input dataset failed\n");
        return FAILED;
    }
    if (CreateOutputDataset(memInfo, outputAddr) != SUCCESS) {
        osal_printk("Create output dataset failed\n");
        return FAILED;
    }
    // 模型执行
    if (ModelExecuteStart(modelInfo) != SUCCESS) {
        osal_printk("Run acl model failed\n");
        return FAILED;
    }
    // 销毁输入输出Dataset
    MemInfoReset(memInfo);
    return SUCCESS;
}

// 销毁模型
static void FreeModelInfo(ModelInfo *modelInfo)
{
    MemInfo *memInfo = &modelInfo->memInfo;
    // 销毁输入输出
    MemInfoReset(memInfo);
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
    // 释放输入输出内存
    ModelMemFree();
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

static void fp162fp32(float *__restrict out, const short in)
{
    unsigned int t1;
    unsigned int t2;
    unsigned int t3;

    t1 = (unsigned int)in & 0x7fffu;                       // Non-sign bits
    t2 = (unsigned int)in & 0x8000u;                       // Sign bit
    t3 = (unsigned int)in & 0x7c00u;                       // Exponent

    t1 <<= 13u;                              // Align mantissa on MSB
    t2 <<= 16u;                              // Shift sign bit into position

    t1 += 0x38000000;                       // Adjust bias

    t1 = (t3 == 0 ? 0 : t1);                // Denormals-as-zero

    t1 |= t2;                               // Re-insert sign bit

    *((unsigned int *)out) = t1;
};

void PrintModelResult(void)
{
    osal_printk("[AI_NPU] Data:");
    for (int i = 0; i < OUTPUT_DATA_NUM; i++) {
        float f;
        fp162fp32(&f, ((short *)g_modelOutput)[i]);
        osal_printk("[%.5f]", f);
    }
    osal_printk("\n");
}