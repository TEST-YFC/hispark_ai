/**
 * Copyright (c) 2025-2025 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
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
 #if defined(PROCESSOR_TYPE_NANO)
#include "std_def.h"
#endif
#include "acl_mdl.h"
#include "acl_base.h"
#include "acl_rt.h"
#include "acl.h"
#include "tensor.h"
#include "ai.h"
#include "env.h"
#include "model.h"

uint32_t g_model_id = 0;

static OH_AI_DataType ConvertAclTypeToOhAi(aclDataType acl_data_type)
{
    switch (acl_data_type) {
        case ACL_FLOAT16:
            return OH_AI_DATATYPE_NUMBERTYPE_FLOAT16;
        case ACL_FLOAT:
            return OH_AI_DATATYPE_NUMBERTYPE_FLOAT32;
        case ACL_INT8:
            return OH_AI_DATATYPE_NUMBERTYPE_INT8;
        case ACL_INT16:
            return OH_AI_DATATYPE_NUMBERTYPE_INT16;
        case ACL_INT32:
            return OH_AI_DATATYPE_NUMBERTYPE_INT32;
        case ACL_INT64:
            return OH_AI_DATATYPE_NUMBERTYPE_INT64;
        case ACL_UINT8:
            return OH_AI_DATATYPE_NUMBERTYPE_UINT8;
        case ACL_UINT16:
            return OH_AI_DATATYPE_NUMBERTYPE_UINT16;
        case ACL_UINT32:
            return OH_AI_DATATYPE_NUMBERTYPE_UINT32;
        case ACL_UINT64:
            return OH_AI_DATATYPE_NUMBERTYPE_UINT64;
        case ACL_DOUBLE:
            return OH_AI_DATATYPE_NUMBERTYPE_FLOAT64;
        case ACL_BOOL:
            return OH_AI_DATATYPE_NUMBERTYPE_BOOL;
        case ACL_STRING:
            return OH_AI_DATATYPE_OBJECTTYPE_STRING;
        // The following types have no corresponding entries in OH_AI_DataType; unknown is returned.
        case ACL_DT_UNDEFINED:
        case ACL_COMPLEX64:
        case ACL_COMPLEX128:
        case ACL_BF16:
        case ACL_INT4:
        case ACL_UINT1:
        case ACL_COMPLEX32:
        case ACL_HIFLOAT8:
        case ACL_FLOAT8_E5M2:
        case ACL_FLOAT8_E4M3FN:
        case ACL_FLOAT8_E8M0:
        case ACL_FLOAT6_E3M2:
        case ACL_FLOAT6_E2M3:
        case ACL_FLOAT4_E2M1:
        case ACL_FLOAT4_E1M2:
        default:
            return OH_AI_DATATYPE_UNKNOWN;
    }
}

#if defined(PROCESSOR_TYPE_NANO)
static OH_AI_Status createModelDescFromFile(ModelInfo *model_info, const char *model_path)
{
    if (model_info == NULL || model_path == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    aclError ret;

    model_info->model_desc = aclmdlCreateDesc();
    if (model_info->model_desc == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    ret = aclmdlGetDescFromFile(model_info->model_desc, model_path);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        aclmdlDestroyDesc(model_info->model_desc);
        model_info->model_desc = NULL;
        return OH_AI_STATUS_FAILED;
    }

    return OH_AI_STATUS_SUCCESS;
}
#elif defined(PROCESSOR_TYPE_TINY)
static OH_AI_Status createModelDescFromFile(ModelInfo *model_info)
{
    if (model_info == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    aclError ret;

    model_info->model_desc = aclmdlCreateDesc();
    if (model_info->model_desc == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    ret = aclmdlGetDesc(model_info->model_desc, model_info->model_id);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        aclmdlDestroyDesc(model_info->model_desc);
        model_info->model_desc = NULL;
        return OH_AI_STATUS_FAILED;
    }

    return OH_AI_STATUS_SUCCESS;
}
#else
#endif

static void destroyTensorArray(NPUTensor **tensors, size_t *count, int max_index)
{
    if (tensors == NULL || count == NULL) {
        return;
    }

    size_t release_count = (max_index == -1) ? *count : (size_t)max_index;
    for (size_t i = 0; i < release_count; i++) {
        if (tensors[i] != NULL) {
            if (tensors[i]->shape != NULL) {
                aclrtFree(tensors[i]->shape);
            }
            aclrtFree(tensors[i]);
            tensors[i] = NULL;
        }
    }
    aclrtFree(tensors);
    tensors = NULL;
    *count = 0;
}

static void destoryDataset(aclmdlDataset *dataset)
{
    size_t buf_count = aclmdlGetDatasetNumBuffers(dataset);
    for (size_t i = 0; i < buf_count; ++i) {
        aclDataBuffer *data_buffer = aclmdlGetDatasetBuffer(dataset, i);
        if (data_buffer != NULL) {
            void *buffer_addr = aclGetDataBufferAddr(data_buffer);
            aclrtFree(buffer_addr);
            buffer_addr = NULL;
            aclDestroyDataBuffer(data_buffer);
        }
    }
    aclmdlDestroyDataset(dataset);
}

static void destroyModelInputAndOutput(ModelInfo *model_info)
{
    if (model_info == NULL) {
        return;
    }
    if (model_info->input_dataset != NULL) {
        destoryDataset(model_info->input_dataset);
        model_info->input_dataset = NULL;
    }
    if (model_info->output_dataset != NULL) {
        destoryDataset(model_info->output_dataset);
        model_info->output_dataset = NULL;
    }
    if (model_info->inputs != NULL) {
        destroyTensorArray(model_info->inputs, &model_info->input_count, DESTORYALL);
    }
    if (model_info->outputs != NULL) {
        destroyTensorArray(model_info->outputs, &model_info->output_count, DESTORYALL);
    }
}

static void destroyModelWeightAndWorkspace(ModelInfo *model_info)
{
    if (model_info->weight != NULL) {
        aclrtFree(model_info->weight);
        model_info->weight = NULL;
    }

    if (model_info->workspace != NULL) {
        aclrtFree(model_info->workspace);
        model_info->workspace = NULL;
    }

    model_info->weight_size = 0;
    model_info->work_size = 0;

    if (model_info->is_model_loaded) {
        aclmdlUnload(model_info->model_id);
        model_info->is_model_loaded = false;
    }
}

static void destroyModelStreamAndDesc(ModelInfo *model_info)
{
    if (model_info == NULL) {
        return;
    }

    if (model_info->model_stream != NULL) {
        aclError ret = aclrtDestroyStream(model_info->model_stream);
        if (ret != ACL_SUCCESS) {
            error_code = ret;
            return;
        }
        model_info->model_stream = NULL;

    }
    if (model_info->model_desc != NULL) {
        aclError ret = aclmdlDestroyDesc(model_info->model_desc);
        if (ret != ACL_SUCCESS) {
            error_code = ret;
            return;
        }
        model_info->model_desc = NULL;
    }
}

#if defined(PROCESSOR_TYPE_NANO)
static OH_AI_Status loadModelFromFile(ModelInfo *model_info, const char *model_path)
{
    if (model_info == NULL || model_path == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    aclError ret;

    ret = aclmdlQuerySize(model_path, &model_info->work_size, &model_info->weight_size);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return OH_AI_STATUS_FAILED;
    }

    ret = aclrtMalloc(&model_info->weight, model_info->weight_size, ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return OH_AI_STATUS_FAILED;
    }

    ret = aclrtMalloc(&model_info->workspace, model_info->work_size, ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        destroyModelWeightAndWorkspace(model_info);
        return OH_AI_STATUS_FAILED;
    }

    aclmdlConfigHandle *config_handle = aclmdlCreateConfigHandle();
    if (config_handle == NULL) {
        destroyModelWeightAndWorkspace(model_info);
        return OH_AI_STATUS_FAILED;
    }

    aclmdlSetConfigOpt(config_handle, ACL_MDL_WEIGHT_ADDR_PTR, &model_info->weight, sizeof(model_info->weight));
    aclmdlSetConfigOpt(config_handle, ACL_MDL_WEIGHT_SIZET, &model_info->weight_size, sizeof(model_info->weight_size));
    aclmdlSetConfigOpt(config_handle, ACL_MDL_PATH_PTR, &model_path, sizeof(model_path));
    size_t load_type = ACL_MDL_LOAD_FROM_FILE_WITH_MEM;
    aclmdlSetConfigOpt(config_handle, ACL_MDL_LOAD_TYPE_SIZET, &load_type, sizeof(load_type));

    ret = aclmdlLoadWithConfig(config_handle, &model_info->model_id);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        aclmdlDestroyConfigHandle(config_handle);
        destroyModelWeightAndWorkspace(model_info);
        return OH_AI_STATUS_FAILED;
    }

    aclmdlDestroyConfigHandle(config_handle);
    return OH_AI_STATUS_SUCCESS;
}

static OH_AI_Status setModelStream(ModelInfo *model_info)
{
    aclError ret;
    aclrtStreamConfigHandle *stream_config_handle = aclrtCreateStreamConfigHandle();
    if (stream_config_handle == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    ret = aclrtCreateStreamV2(&model_info->model_stream, stream_config_handle);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        aclrtDestroyStreamConfigHandle(stream_config_handle);
        return OH_AI_STATUS_FAILED;
    }

    aclrtDestroyStreamConfigHandle(stream_config_handle);
    return OH_AI_STATUS_SUCCESS;
}
#elif defined(PROCESSOR_TYPE_TINY)
static OH_AI_Status loadModelFromFile(ModelInfo *model_info, const char *model_path)
{
    if (model_info == NULL || model_path == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    aclError ret;

    ret = aclmdlLoadFromFile(model_path, &model_info->model_id);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return OH_AI_STATUS_FAILED;
    }

    return OH_AI_STATUS_SUCCESS;
}

static OH_AI_Status setModelStream(ModelInfo *model_info)
{
    aclError ret;

    ret = aclrtCreateStream(&model_info->model_stream);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return OH_AI_STATUS_FAILED;
    }

    return OH_AI_STATUS_SUCCESS;
}
#else
#endif

static aclError GetInputDims(aclmdlDesc *model_desc, size_t idx, aclmdlIODims *dims)
{
#if defined(PROCESSOR_TYPE_NANO)
    return aclmdlGetInputDims(model_desc, idx, dims);
#elif defined(PROCESSOR_TYPE_TINY)
    return aclmdlGetInputDimsV2(model_desc, idx, dims);
#else
#endif
}

static OH_AI_Status InitializeInputTensors(ModelInfo *model_info, size_t input_count)
{
    for (size_t i = 0; i < input_count; i++) {
        NPUTensor *tensor = NULL;
        aclError ret = aclrtMalloc((void **)&tensor, sizeof(NPUTensor), ACL_MEM_MALLOC_NORMAL_ONLY);
        if (ret != ACL_SUCCESS) {
            return OH_AI_STATUS_FAILED;
        }
        model_info->inputs[i] = tensor;

        aclmdlIODims input_dims;
        ret = GetInputDims(model_info->model_desc, i, &input_dims);
        if (ret != ACL_SUCCESS) {
            error_code = ret;
            destroyTensorArray(model_info->inputs, &model_info->input_count, DESTORYALL);
            destoryDataset(model_info->input_dataset);
            return OH_AI_STATUS_FAILED;
        }

        tensor->shape_len = input_dims.dimCount;
        if (input_dims.dimCount > 0) {
            if (aclrtMalloc((void **)&tensor->shape, input_dims.dimCount * sizeof(int64_t),
                            ACL_MEM_MALLOC_NORMAL_ONLY) != ACL_SUCCESS) {
                destroyTensorArray(model_info->inputs, &model_info->input_count, DESTORYALL);
                destoryDataset(model_info->input_dataset);
                return OH_AI_STATUS_FAILED;
            }

            aclrtMemcpy(tensor->shape, input_dims.dimCount * sizeof(int64_t),
                        input_dims.dims, input_dims.dimCount * sizeof(int64_t), ACL_MEMCPY_DEVICE_TO_HOST);
        } else {
            tensor->shape = NULL;
        }

        aclDataType acl_type = aclmdlGetInputDataType(model_info->model_desc, i);
        tensor->data_type = ConvertAclTypeToOhAi(acl_type);

        uint32_t input_size = aclmdlGetInputSizeByIndex(model_info->model_desc, i);
        void *input_buffer = NULL;
        if (aclrtMalloc(&input_buffer, input_size, ACL_MEM_MALLOC_NORMAL_ONLY) != ACL_SUCCESS) {
            destroyTensorArray(model_info->inputs, &model_info->input_count, DESTORYALL);
            destoryDataset(model_info->input_dataset);
            return OH_AI_STATUS_FAILED;
        }

        aclrtMemset(input_buffer, input_size, 0, input_size);

        aclDataBuffer *input_data = aclCreateDataBuffer(input_buffer, input_size);
        if (input_data == NULL || aclmdlAddDatasetBuffer(model_info->input_dataset, input_data) != ACL_SUCCESS) {
            aclDestroyDataBuffer(input_data);
            aclrtFree(input_buffer);
            destroyTensorArray(model_info->inputs, &model_info->input_count, DESTORYALL);
            destoryDataset(model_info->input_dataset);
            return OH_AI_STATUS_FAILED;
        }

        tensor->data = input_buffer;
        tensor->size = input_size;
        model_info->inputs[i] = tensor;
    }

    return OH_AI_STATUS_SUCCESS;
}

static OH_AI_Status InitializeOutputTensors(ModelInfo *model_info, size_t output_count)
{
    for (size_t i = 0; i < output_count; i++) {
        NPUTensor *tensor = NULL;
        aclError ret = aclrtMalloc((void **)&tensor, sizeof(NPUTensor), ACL_MEM_MALLOC_NORMAL_ONLY);
        if (ret != ACL_SUCCESS) {
            destroyTensorArray(model_info->outputs, &model_info->output_count, DESTORYALL);
            destoryDataset(model_info->output_dataset);
            return OH_AI_STATUS_FAILED;
        }
        model_info->outputs[i] = tensor;

        aclmdlIODims output_dims;
        ret = aclmdlGetOutputDims(model_info->model_desc, i, &output_dims);
        if (ret != ACL_SUCCESS) {
            error_code = ret;
            destroyTensorArray(model_info->outputs, &model_info->output_count, DESTORYALL);
            destoryDataset(model_info->output_dataset);
            return OH_AI_STATUS_FAILED;
        }

        tensor->shape_len = output_dims.dimCount;
        if (output_dims.dimCount > 0) {
            if (aclrtMalloc((void **)&tensor->shape, output_dims.dimCount * sizeof(int64_t),
                            ACL_MEM_MALLOC_NORMAL_ONLY) != ACL_SUCCESS) {
                destroyTensorArray(model_info->outputs, &model_info->output_count, DESTORYALL);
                destoryDataset(model_info->output_dataset);
                return OH_AI_STATUS_FAILED;
            }

            aclrtMemcpy(tensor->shape, output_dims.dimCount * sizeof(int64_t),
                        output_dims.dims, output_dims.dimCount * sizeof(int64_t), ACL_MEMCPY_DEVICE_TO_HOST);
        } else {
            tensor->shape = NULL;
        }

        aclDataType acl_type = aclmdlGetOutputDataType(model_info->model_desc, i);
        tensor->data_type = ConvertAclTypeToOhAi(acl_type);

        uint32_t output_size = aclmdlGetOutputSizeByIndex(model_info->model_desc, i);
        void *output_buffer = NULL;
        if (aclrtMalloc(&output_buffer, output_size, ACL_MEM_MALLOC_NORMAL_ONLY) != ACL_SUCCESS) {
            destroyTensorArray(model_info->outputs, &model_info->output_count, DESTORYALL);
            destoryDataset(model_info->output_dataset);
            return OH_AI_STATUS_FAILED;
        }

        aclrtMemset(output_buffer, output_size, 0, output_size);

        aclDataBuffer *output_data = aclCreateDataBuffer(output_buffer, output_size);
        if (output_data == NULL || aclmdlAddDatasetBuffer(model_info->output_dataset, output_data) != ACL_SUCCESS) {
            aclDestroyDataBuffer(output_data);
            aclrtFree(output_buffer);
            destroyTensorArray(model_info->outputs, &model_info->output_count, DESTORYALL);
            destoryDataset(model_info->output_dataset);
            return OH_AI_STATUS_FAILED;
        }

        tensor->data = output_buffer;
        tensor->size = output_size;
        model_info->outputs[i] = tensor;
    }

    return OH_AI_STATUS_SUCCESS;
}

OH_AI_ModelHandle OH_AI_ModelCreate(void)
{
    ModelInfo *model_info = NULL;

    aclError ret = aclrtMalloc(&model_info, sizeof(ModelInfo), ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return NULL;
    }

    model_info->model_id = g_model_id;
    model_info->context = NULL;
    model_info->model_desc = NULL;
    model_info->model_stream = NULL;
    model_info->input_dataset = NULL;
    model_info->output_dataset = NULL;
    model_info->weight = NULL;
    model_info->weight_size = 0;
    model_info->workspace = NULL;
    model_info->work_size = 0;
    model_info->inputs = NULL;
    model_info->input_count = 0;
    model_info->outputs = NULL;
    model_info->output_count = 0;
    model_info->is_model_loaded = false;

    g_model_id++;
    return (OH_AI_ModelHandle)model_info;
}

OH_AI_Status OH_AI_ModelBuildFromFile(
    OH_AI_ModelHandle model, const char *model_path, const OH_AI_ContextHandle model_context)
{
    if (model == NULL || model_path == NULL || model_context == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    ModelInfo *model_info = (ModelInfo *)model;

    model_info->context = (ContextInfo *)model_context;
    model_info->context->model_count++;

    OH_AI_Status ret = setModelStream(model_info);
    if (ret != OH_AI_STATUS_SUCCESS) {
        return ret;
    }

    ret = loadModelFromFile(model_info, model_path);
    if (ret != OH_AI_STATUS_SUCCESS) {
        destroyModelStreamAndDesc(model_info);
        return ret;
    }

#if defined(PROCESSOR_TYPE_NANO)
    ret = createModelDescFromFile(model_info, model_path);
#elif defined(PROCESSOR_TYPE_TINY)
    ret = createModelDescFromFile(model_info);
#else
#endif
    if (ret != OH_AI_STATUS_SUCCESS) {
        destroyModelStreamAndDesc(model_info);
        destroyModelWeightAndWorkspace(model_info);
        return ret;
    }
    model_info->is_model_loaded = true;

    OH_AI_TensorHandleArray input_tensors = OH_AI_ModelGetInputs(model);
    if (input_tensors.handle_num == 0 || input_tensors.handle_list == NULL) {
        destroyModelStreamAndDesc(model_info);
        destroyModelWeightAndWorkspace(model_info);
        return OH_AI_STATUS_FAILED;
    }

    OH_AI_TensorHandleArray output_tensors = OH_AI_ModelGetOutputs(model);
    if (output_tensors.handle_num == 0 || output_tensors.handle_list == NULL) {
        destroyModelStreamAndDesc(model_info);
        destroyModelWeightAndWorkspace(model_info);
        return OH_AI_STATUS_FAILED;
    }

    return OH_AI_STATUS_SUCCESS;
}

void OH_AI_ModelDestroy(OH_AI_ModelHandle *model)
{
    if (model == NULL || *model == NULL) {
        return;
    }

    ModelInfo *model_info = (ModelInfo *)*model;
    if (model_info->context != NULL) {
        model_info->context->model_count--;
    }

    destroyModelInputAndOutput(model_info);
    destroyModelWeightAndWorkspace(model_info);
    destroyModelStreamAndDesc(model_info);

    aclrtFree(model_info);
    *model = NULL;
}

OH_AI_TensorHandleArray OH_AI_ModelGetInputs(const OH_AI_ModelHandle model)
{
    OH_AI_TensorHandleArray result = {0, NULL};

    if (model == NULL) {
        return result;
    }

    aclError ret;
    ModelInfo *model_info = (ModelInfo *)model;
    if (!model_info->is_model_loaded) {
        return result;
    }

    if (model_info->inputs != NULL && model_info->input_count > 0) {
        result.handle_num = model_info->input_count;
        result.handle_list = (OH_AI_TensorHandle *)model_info->inputs;
        return result;
    }

    size_t input_count = aclmdlGetNumInputs(model_info->model_desc);
    if (input_count == 0) {
        return result;
    }
    model_info->input_count = input_count;

    ret = aclrtMalloc((void **)&model_info->inputs, input_count * sizeof(NPUTensor *), ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return result;
    }

    model_info->input_dataset = aclmdlCreateDataset();
    if (model_info->input_dataset == NULL) {
        aclrtFree(model_info->inputs);
        model_info->inputs = NULL;
        return result;
    }

    if (InitializeInputTensors(model_info, input_count) != OH_AI_STATUS_SUCCESS) {
        if (model_info->inputs != NULL) {
            aclrtFree(model_info->inputs);
            model_info->inputs = NULL;
        }
        if (model_info->input_dataset != NULL) {
            aclmdlDestroyDataset(model_info->input_dataset);
            model_info->input_dataset = NULL;
        }
        return result;
    }

    result.handle_num = input_count;
    result.handle_list = (OH_AI_TensorHandle *)model_info->inputs;

    return result;
}

OH_AI_TensorHandleArray OH_AI_ModelGetOutputs(const OH_AI_ModelHandle model)
{
    OH_AI_TensorHandleArray result = {0, NULL};

    if (model == NULL) {
        return result;
    }

    ModelInfo *model_info = (ModelInfo *)model;
    if (!model_info->is_model_loaded) {
        return result;
    }

    if (model_info->outputs != NULL && model_info->output_count > 0) {
        result.handle_num = model_info->output_count;
        result.handle_list = (OH_AI_TensorHandle *)model_info->outputs;
        return result;
    }

    size_t output_count = aclmdlGetNumOutputs(model_info->model_desc);
    if (output_count == 0) {
        return result;
    }
    model_info->output_count = output_count;

    if (aclrtMalloc((void **)&model_info->outputs,
                    output_count * sizeof(NPUTensor *),
                    ACL_MEM_MALLOC_NORMAL_ONLY) != ACL_SUCCESS) {
        return result;
    }

    model_info->output_dataset = aclmdlCreateDataset();
    if (model_info->output_dataset == NULL) {
        aclrtFree(model_info->outputs);
        model_info->outputs = NULL;
        return result;
    }

    if (InitializeOutputTensors(model_info, output_count) != OH_AI_STATUS_SUCCESS) {
        if (model_info->outputs != NULL) {
            aclrtFree(model_info->outputs);
            model_info->outputs = NULL;
        }
        if (model_info->output_dataset != NULL) {
            aclmdlDestroyDataset(model_info->output_dataset);
            model_info->output_dataset = NULL;
        }
        return result;
    }

    result.handle_num = output_count;
    result.handle_list = (OH_AI_TensorHandle *)model_info->outputs;

    return result;
}

OH_AI_Status OH_AI_ModelPredict(
    OH_AI_ModelHandle model, const OH_AI_TensorHandleArray inputs, OH_AI_TensorHandleArray *outputs)
{
    if (model == NULL || outputs == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    ModelInfo *model_info = (ModelInfo *)model;
    if (!model_info->is_model_loaded) {
        return OH_AI_STATUS_FAILED;
    }

    OH_AI_TensorHandleArray model_inputs = OH_AI_ModelGetInputs(model_info);
    OH_AI_TensorHandleArray model_outputs = OH_AI_ModelGetOutputs(model_info);
    if (model_inputs.handle_list != inputs.handle_list || model_outputs.handle_list != outputs->handle_list) {
        return OH_AI_STATUS_FAILED;
    }

#if defined(PROCESSOR_TYPE_NANO)
    aclmdlExecConfigHandle *exec_config_handle = aclmdlCreateExecConfigHandle();
    if (exec_config_handle == NULL) {
        return OH_AI_STATUS_FAILED;
    }
    aclError ret = aclmdlSetExecConfigOpt(exec_config_handle, ACL_MDL_WORK_ADDR_PTR,
                                          &model_info->workspace, sizeof(model_info->workspace));
    ret |= aclmdlSetExecConfigOpt(exec_config_handle, ACL_MDL_WORK_SIZET,
                                  &model_info->work_size, sizeof(model_info->work_size));
    if (ret != ACL_SUCCESS) {
        aclmdlDestroyExecConfigHandle(exec_config_handle);
        return OH_AI_STATUS_FAILED;
    }
    ret = aclmdlExecuteV2(model_info->model_id, model_info->input_dataset, model_info->output_dataset,
                          model_info->model_stream, exec_config_handle);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        aclmdlDestroyExecConfigHandle(exec_config_handle);
        return OH_AI_STATUS_FAILED;
    }
    aclmdlDestroyExecConfigHandle(exec_config_handle);
#elif defined(PROCESSOR_TYPE_TINY)
    aclError ret = aclmdlExecute(model_info->model_id, model_info->input_dataset, model_info->output_dataset);
    if (ret != ACL_SUCCESS) {
        error_code = ret;
        return OH_AI_STATUS_FAILED;
    }
#else
#endif
    return OH_AI_STATUS_SUCCESS;
}
