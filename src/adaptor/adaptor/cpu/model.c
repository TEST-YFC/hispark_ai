/**
 * Copyright (c) 2025-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
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
#include "ai_mcu.h"
#include "ai.h"
#include "model_state.h"

#ifdef __cplusplus
#if __cplusplus
extern "C" {
#endif
#endif

OH_AI_ModelHandle OH_AI_ModelCreate(void)
{
    MSModelHandle model_handle = MSModelCreate();
    if (model_handle == NULL) {
        return NULL;
    }
    int index = ModelState_BindHandle(model_handle);
    if (index == INVALID_INDEX) {
        MSModelDestroy(&model_handle);
        return NULL;
    }
    return (OH_AI_ModelHandle)model_handle;
}

OH_AI_Status OH_AI_ModelBuildFromFile(
    OH_AI_ModelHandle model, const char *model_path, const OH_AI_ContextHandle model_context)
{
    (void)(model_path);
    if (model_context == NULL) {
        return OH_AI_STATUS_FAILED;
    }
    int index = ModelState_FindIndex(model);
    if (!ModelState_Check(index, MODEL_STATE_CREATED)) {
        return OH_AI_STATUS_FAILED;
    }

    ModelState_Transition(index, MODEL_STATE_BUILT);
    return OH_AI_STATUS_SUCCESS;
}

OH_AI_Status OH_AI_ModelBuild(
    OH_AI_ModelHandle model, const void *model_data, size_t data_size, const OH_AI_ContextHandle model_context)
{
    if (model_context == NULL) {
        return OH_AI_STATUS_FAILED;
    }
    int index = ModelState_FindIndex(model);
    if (!ModelState_Check(index, MODEL_STATE_CREATED)) {
        return OH_AI_STATUS_FAILED;
    }
    
    MSStatus status = MSModelBuild(
        (MSModelHandle)model,
        model_data,
        data_size,
        kMSModelTypeMindIR,
        (MSContextHandle)model_context
    );
    if (status == kMSStatusSuccess) {
        ModelState_Transition(index, MODEL_STATE_BUILT);
        return OH_AI_STATUS_SUCCESS;
    } else {
        return OH_AI_STATUS_FAILED;
    }
}

OH_AI_Status OH_AI_ModelBuildFromName(
    OH_AI_ModelHandle model, const char *model_name, const OH_AI_ContextHandle model_context)
{
    (void)(model_name);
    if (model_context == NULL) {
        return OH_AI_STATUS_FAILED;
    }
    int index = ModelState_FindIndex(model);
    if (!ModelState_Check(index, MODEL_STATE_CREATED)) {
        return OH_AI_STATUS_FAILED;
    }
    
    ModelState_Transition(index, MODEL_STATE_BUILT);
    return OH_AI_STATUS_SUCCESS;
}

void OH_AI_ModelDestroy(OH_AI_ModelHandle *model)
{
    if (model == NULL || *model == NULL) {
        return;
    }

    int index = ModelState_FindIndex(*model);
    MSModelDestroy((MSModelHandle *)model);
    ModelState_Transition(index, MODEL_STATE_UNINIT);

    *model = NULL;
}

OH_AI_TensorHandleArray OH_AI_ModelGetInputs(const OH_AI_ModelHandle model)
{
    OH_AI_TensorHandleArray stub_array;
    stub_array.handle_num = 0;
    stub_array.handle_list = NULL;

    if (!ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return stub_array;
    }

    MSTensorHandleArray inputs = MSModelGetInputs((MSModelHandle)model);

    stub_array.handle_num = inputs.handle_num;
    stub_array.handle_list = (OH_AI_TensorHandle *)inputs.handle_list;

    return stub_array;
}

OH_AI_TensorHandleArray OH_AI_ModelGetLabels(const OH_AI_ModelHandle model)
{
    OH_AI_TensorHandleArray stub_array;
    stub_array.handle_num = 0;
    stub_array.handle_list = NULL;

    if (!ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return stub_array;
    }

    MSTensorHandleArray labels = MSModelGetLabels((MSModelHandle)model);

    stub_array.handle_num = labels.handle_num;
    stub_array.handle_list = (OH_AI_TensorHandle *)labels.handle_list;

    return stub_array;
}

OH_AI_TensorHandleArray OH_AI_ModelGetOutputs(const OH_AI_ModelHandle model)
{
    OH_AI_TensorHandleArray stub_array;
    stub_array.handle_num = 0;
    stub_array.handle_list = NULL;

    if (!ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return stub_array;
    }

    MSTensorHandleArray outputs = MSModelGetOutputs((MSModelHandle)model);
    
    stub_array.handle_num = outputs.handle_num;
    stub_array.handle_list = (OH_AI_TensorHandle *)outputs.handle_list;
    
    return stub_array;
}

OH_AI_TensorHandle OH_AI_ModelGetInputByTensorName(const OH_AI_ModelHandle model, const char *tensor_name)
{
    OH_AI_TensorHandle stub_tensor = NULL;

    if (!ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return stub_tensor;
    }

    if (tensor_name == NULL) {
        return stub_tensor;
    }

    MSTensorHandle ms_tensor = MSModelGetInputByTensorName((MSModelHandle)model, tensor_name);

    stub_tensor = (OH_AI_TensorHandle)ms_tensor;

    return stub_tensor;
}

OH_AI_TensorHandle OH_AI_ModelGetOutputByTensorName(const OH_AI_ModelHandle model, const char *tensor_name)
{
    OH_AI_TensorHandle stub_tensor = NULL;

    if (!ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return stub_tensor;
    }

    if (tensor_name == NULL) {
        return stub_tensor;
    }

    MSTensorHandle ms_tensor = MSModelGetOutputByTensorName((MSModelHandle)model, tensor_name);

    stub_tensor = (OH_AI_TensorHandle)ms_tensor;

    return stub_tensor;
}

OH_AI_Status OH_AI_ModelPredict(
    OH_AI_ModelHandle model, const OH_AI_TensorHandleArray inputs, OH_AI_TensorHandleArray *outputs)
{
    if (outputs == NULL || inputs.handle_list == NULL || inputs.handle_num == 0 ||
        !ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return OH_AI_STATUS_FAILED;
    }
    MSModelHandle ms_model = (MSModelHandle)model;
    
    MSTensorHandleArray ms_inputs;
    ms_inputs.handle_num = inputs.handle_num;
    ms_inputs.handle_list = (MSTensorHandle *)inputs.handle_list;

    MSStatus status = MSModelPredict(ms_model, ms_inputs, (MSTensorHandleArray*)outputs, NULL, NULL);
    if (status == kMSStatusSuccess) {
        return OH_AI_STATUS_SUCCESS;
    } else {
        return OH_AI_STATUS_FAILED;
    }
}

OH_AI_Status OH_AI_ModelRunStep(OH_AI_ModelHandle model)
{
    if (!ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return OH_AI_STATUS_FAILED;
    }

    MSStatus status = MSModelRunStep((MSModelHandle)model, NULL, NULL);
    return status == kMSStatusSuccess ? OH_AI_STATUS_SUCCESS : OH_AI_STATUS_FAILED;
}

OH_AI_Status OH_AI_ModelSetTrainMode(OH_AI_ModelHandle model, bool train)
{
    if (!ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return OH_AI_STATUS_FAILED;
    }

    MSStatus status = MSModelSetTrainMode((MSModelHandle)model, train);
    return status == kMSStatusSuccess ? OH_AI_STATUS_SUCCESS : OH_AI_STATUS_FAILED;
}

OH_AI_Status OH_AI_ModelGetTrainMode(OH_AI_ModelHandle model, bool *train)
{
    if (train == NULL || !ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return OH_AI_STATUS_FAILED;
    }

    *train = MSModelGetTrainMode((MSModelHandle)model);
    return OH_AI_STATUS_SUCCESS;
}

OH_AI_Status OH_AI_ModelLoadWeight(OH_AI_ModelHandle model, uintptr_t flash_addr)
{
    if (!ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return OH_AI_STATUS_FAILED;
    }

    const void *weight_addr = (flash_addr == 0U) ? NULL : (const void *)flash_addr;
    MSStatus status = MSModelLoadWeight((MSModelHandle)model, weight_addr);
    return status == kMSStatusSuccess ? OH_AI_STATUS_SUCCESS : OH_AI_STATUS_FAILED;
}

OH_AI_Status OH_AI_ModelSaveWeight(OH_AI_ModelHandle model, uintptr_t flash_addr)
{
    if (flash_addr == 0U || !ModelState_Check(ModelState_FindIndex(model), MODEL_STATE_BUILT)) {
        return OH_AI_STATUS_FAILED;
    }

    /*
    * Saving RAM weights to Flash needs board-specific erase/write/verify logic.
    * Keep this API as a visible placeholder until that storage path is implemented.
    */
    return OH_AI_STATUS_FAILED;
}

#ifdef __cplusplus
#if __cplusplus
}
#endif
#endif