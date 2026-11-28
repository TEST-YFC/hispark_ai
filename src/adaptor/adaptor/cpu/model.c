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

 static OH_AI_Status BuildLinkedModel(OH_AI_ModelHandle model, const char *name, const void *data,
    size_t size, OH_AI_ContextHandle context)
{
    MSModelHandle native = ModelState_Select(model, name);
    if (native == NULL || context == NULL) {
        return OH_AI_STATUS_FAILED;
    }
    if (MSModelBuild(native, data, size, kMSModelTypeMindIR, (MSContextHandle)context) != kMSStatusSuccess) {
        return OH_AI_STATUS_FAILED;
    }
    ModelState_SetBuilt(model, native);
    return OH_AI_STATUS_SUCCESS;
}

OH_AI_ModelHandle OH_AI_ModelCreate(void)
{
    return ModelState_Reserve();
}

OH_AI_Status OH_AI_ModelBuildFromFile(
    OH_AI_ModelHandle model, const char *model_path, const OH_AI_ContextHandle model_context)
{
    (void)model_path;
    return BuildLinkedModel(model, NULL, NULL, 0, model_context);
}

OH_AI_Status OH_AI_ModelBuild(
    OH_AI_ModelHandle model, const void *model_data, size_t data_size, const OH_AI_ContextHandle model_context)
{
    return BuildLinkedModel(model, NULL, model_data, data_size, model_context);
}

OH_AI_Status OH_AI_ModelBuildFromName(
    OH_AI_ModelHandle model, const char *model_name, const OH_AI_ContextHandle model_context)
{
    if (model_name == NULL || *model_name == '\0') {
        return OH_AI_STATUS_FAILED;
    }
    return BuildLinkedModel(model, model_name, NULL, 0, model_context);
}

void OH_AI_ModelDestroy(OH_AI_ModelHandle *model)
{
    if (model != NULL) {
        ModelState_Release(*model);
        *model = NULL;
    }
}

OH_AI_TensorHandleArray OH_AI_ModelGetInputs(const OH_AI_ModelHandle model)
{
    OH_AI_TensorHandleArray stub_array;
    stub_array.handle_num = 0;
    stub_array.handle_list = NULL;

    MSModelHandle native = ModelState_BuiltHandle(model);
    if (native == NULL) {
        return stub_array;
    }

    MSTensorHandleArray inputs = MSModelGetInputs(native);

    stub_array.handle_num = inputs.handle_num;
    stub_array.handle_list = (OH_AI_TensorHandle *)inputs.handle_list;

    return stub_array;
}

OH_AI_TensorHandleArray OH_AI_ModelGetLabels(const OH_AI_ModelHandle model)
{
    OH_AI_TensorHandleArray stub_array;
    stub_array.handle_num = 0;
    stub_array.handle_list = NULL;

    MSModelHandle native = ModelState_BuiltHandle(model);
    if (native == NULL) {
        return stub_array;
    }

    MSTensorHandleArray labels = MSModelGetLabels(native);

    stub_array.handle_num = labels.handle_num;
    stub_array.handle_list = (OH_AI_TensorHandle *)labels.handle_list;

    return stub_array;
}

OH_AI_TensorHandleArray OH_AI_ModelGetOutputs(const OH_AI_ModelHandle model)
{
    OH_AI_TensorHandleArray stub_array;
    stub_array.handle_num = 0;
    stub_array.handle_list = NULL;

    MSModelHandle native = ModelState_BuiltHandle(model);
    if (native == NULL) {
        return stub_array;
    }

    MSTensorHandleArray outputs = MSModelGetOutputs(native);

    stub_array.handle_num = outputs.handle_num;
    stub_array.handle_list = (OH_AI_TensorHandle *)outputs.handle_list;

    return stub_array;
}

OH_AI_TensorHandle OH_AI_ModelGetInputByTensorName(const OH_AI_ModelHandle model, const char *tensor_name)
{
    OH_AI_TensorHandle stub_tensor = NULL;

    MSModelHandle native = ModelState_BuiltHandle(model);
    if (native == NULL) {
        return stub_tensor;
    }

    if (tensor_name == NULL) {
        return stub_tensor;
    }

    MSTensorHandle ms_tensor = MSModelGetInputByTensorName(native, tensor_name);

    stub_tensor = (OH_AI_TensorHandle)ms_tensor;

    return stub_tensor;
}

OH_AI_TensorHandle OH_AI_ModelGetOutputByTensorName(const OH_AI_ModelHandle model, const char *tensor_name)
{
    OH_AI_TensorHandle stub_tensor = NULL;

    MSModelHandle native = ModelState_BuiltHandle(model);
    if (native == NULL) {
        return stub_tensor;
    }

    if (tensor_name == NULL) {
        return stub_tensor;
    }

    MSTensorHandle ms_tensor = MSModelGetOutputByTensorName(native, tensor_name);

    stub_tensor = (OH_AI_TensorHandle)ms_tensor;

    return stub_tensor;
}

OH_AI_Status OH_AI_ModelPredict(
    OH_AI_ModelHandle model, const OH_AI_TensorHandleArray inputs, OH_AI_TensorHandleArray *outputs)
{
    MSModelHandle native = ModelState_BuiltHandle(model);
    if (outputs == NULL || inputs.handle_list == NULL || inputs.handle_num == 0 || native == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    MSTensorHandleArray ms_inputs;
    ms_inputs.handle_num = inputs.handle_num;
    ms_inputs.handle_list = (MSTensorHandle *)inputs.handle_list;

    MSStatus status = MSModelPredict(native, ms_inputs, (MSTensorHandleArray*)outputs, NULL, NULL);
    if (status == kMSStatusSuccess) {
        return OH_AI_STATUS_SUCCESS;
    } else {
        return OH_AI_STATUS_FAILED;
    }
}

OH_AI_Status OH_AI_ModelRunStep(OH_AI_ModelHandle model)
{
    MSModelHandle native = ModelState_BuiltHandle(model);
    if (native == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    MSStatus status = MSModelRunStep(native, NULL, NULL);
    return status == kMSStatusSuccess ? OH_AI_STATUS_SUCCESS : OH_AI_STATUS_FAILED;
}

OH_AI_Status OH_AI_ModelSetTrainMode(OH_AI_ModelHandle model, bool train)
{
    MSModelHandle native = ModelState_BuiltHandle(model);
    if (native == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    MSStatus status = MSModelSetTrainMode(native, train);
    return status == kMSStatusSuccess ? OH_AI_STATUS_SUCCESS : OH_AI_STATUS_FAILED;
}

OH_AI_Status OH_AI_ModelGetTrainMode(OH_AI_ModelHandle model, bool *train)
{
    MSModelHandle native = ModelState_BuiltHandle(model);
    if (train == NULL || native == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    *train = MSModelGetTrainMode(native);
    return OH_AI_STATUS_SUCCESS;
}

OH_AI_Status OH_AI_ModelLoadWeight(OH_AI_ModelHandle model, uintptr_t flash_addr)
{
    MSModelHandle native = ModelState_BuiltHandle(model);
    if (native == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    const void *weight_addr = (flash_addr == 0U) ? NULL : (const void *)flash_addr;
    MSStatus status = MSModelLoadWeight(native, weight_addr);
    return status == kMSStatusSuccess ? OH_AI_STATUS_SUCCESS : OH_AI_STATUS_FAILED;
}

OH_AI_Status OH_AI_ModelSaveWeight(OH_AI_ModelHandle model, uintptr_t flash_addr)
{
    MSModelHandle native = ModelState_BuiltHandle(model);
    if (flash_addr == 0U || native == NULL) {
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
