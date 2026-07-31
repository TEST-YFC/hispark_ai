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
#include <stddef.h>
#include <stdint.h>

#include "ai.h"
#include "app_init.h"
#include "cmsis_os2.h"
#include "common_def.h"
#include "osal_debug.h"
#include "securec.h"
#include "tcxo.h"
#include "mnist_training_data.h"

#define MNIST_TRAIN_STACK_SIZE 0x2000
#define MNIST_TRAIN_TASK_PRIO (osPriority_t)(17)
#define MNIST_TRAIN_DELAY_MS 1000
#define MNIST_TRAIN_TICKS_PER_SECOND 24000
#define MNIST_TRAIN_PRINT_FLOAT_MULTIPLIER 100000
#define MNIST_TRAIN_LOGITS_ELEMENTS 10

struct ai_mcu_param {
    OH_AI_ModelHandle model;
    OH_AI_ContextHandle context;
    OH_AI_TensorHandleArray inputs;
    OH_AI_TensorHandleArray labels;
    OH_AI_TensorHandleArray outputs;
};

static void ai_mcu_sample_print_float(float value)
{
    int sign = value < 0.0f ? -1 : 1;
    float abs_value = value < 0.0f ? -value : value;
    int integer = (int)abs_value;
    int fraction = (int)(abs_value * MNIST_TRAIN_PRINT_FLOAT_MULTIPLIER) % MNIST_TRAIN_PRINT_FLOAT_MULTIPLIER;
    if (sign < 0) {
        osal_printk("-%d.%05d", integer, fraction);
    } else {
        osal_printk("%d.%05d", integer, fraction);
    }
}

static OH_AI_Status ai_mcu_sample_copy_tensor(OH_AI_TensorHandle tensor, const void *data, size_t data_size)
{
    if (tensor == NULL || data == NULL) {
        return OH_AI_STATUS_FAILED;
    }
    size_t tensor_size = OH_AI_TensorGetDataSize(tensor);
    if (tensor_size != data_size) {
        osal_printk("[MNIST_TRAIN] tensor size mismatch, expect %zu, got %zu\n", data_size, tensor_size);
        return OH_AI_STATUS_FAILED;
    }
    void *tensor_data = OH_AI_TensorGetMutableData(tensor);
    if (tensor_data == NULL) {
        osal_printk("[MNIST_TRAIN] OH_AI_TensorGetMutableData failed\n");
        return OH_AI_STATUS_FAILED;
    }
    if (memcpy_s(tensor_data, tensor_size, data, data_size) != EOK) {
        osal_printk("[MNIST_TRAIN] memcpy_s failed\n");
        return OH_AI_STATUS_FAILED;
    }
    return OH_AI_STATUS_SUCCESS;
}

static OH_AI_Status ai_mcu_sample_load_batch(struct ai_mcu_param *param, const float *input, const int32_t *label)
{
    if (param->inputs.handle_num != 1 || param->labels.handle_num != 1) {
        osal_printk("[MNIST_TRAIN] sample expects one input tensor and one label tensor\n");
        return OH_AI_STATUS_FAILED;
    }
    OH_AI_Status ret = ai_mcu_sample_copy_tensor(
        param->inputs.handle_list[0], input, MNIST_TRAIN_INPUT_ELEMENTS * sizeof(float));
    if (ret != OH_AI_STATUS_SUCCESS) {
        return ret;
    }
    return ai_mcu_sample_copy_tensor(param->labels.handle_list[0], label, MNIST_TRAIN_LABEL_ELEMENTS * sizeof(int32_t));
}

static OH_AI_Status ai_mcu_sample_print_logits(OH_AI_TensorHandleArray outputs)
{
    if (outputs.handle_num < 1 || outputs.handle_list[0] == NULL) {
        osal_printk("[MNIST_TRAIN] logits output is unavailable\n");
        return OH_AI_STATUS_FAILED;
    }
    OH_AI_TensorHandle logits = outputs.handle_list[0];
    if (OH_AI_TensorGetElementNum(logits) != MNIST_TRAIN_LOGITS_ELEMENTS ||
        OH_AI_TensorGetDataType(logits) != OH_AI_DATATYPE_NUMBERTYPE_FLOAT32) {
        osal_printk("[MNIST_TRAIN] logits output expects 10 float32 elements\n");
        return OH_AI_STATUS_FAILED;
    }
    void *data = OH_AI_TensorGetMutableData(logits);
    if (data == NULL) {
        return OH_AI_STATUS_FAILED;
    }

    osal_printk("logits=[");
    for (int64_t i = 0; i < MNIST_TRAIN_LOGITS_ELEMENTS; ++i) {
        if (i != 0) {
            osal_printk(", ");
        }
        ai_mcu_sample_print_float(((float *)data)[i]);
    }
    osal_printk("]");
    return OH_AI_STATUS_SUCCESS;
}

static OH_AI_Status ai_mcu_sample_get_loss(OH_AI_TensorHandleArray outputs, float *loss)
{
    if (loss == NULL || outputs.handle_num < 2 || outputs.handle_list[1] == NULL) {
        osal_printk("[MNIST_TRAIN] loss output is unavailable\n");
        return OH_AI_STATUS_FAILED;
    }
    if (OH_AI_TensorGetElementNum(outputs.handle_list[1]) != 1 ||
        OH_AI_TensorGetDataType(outputs.handle_list[1]) != OH_AI_DATATYPE_NUMBERTYPE_FLOAT32) {
        osal_printk("[MNIST_TRAIN] loss output expects one float32 element\n");
        return OH_AI_STATUS_FAILED;
    }
    void *data = OH_AI_TensorGetMutableData(outputs.handle_list[1]);
    if (data == NULL) {
        return OH_AI_STATUS_FAILED;
    }
    *loss = ((float *)data)[0];
    return OH_AI_STATUS_SUCCESS;
}

static OH_AI_Status ai_mcu_sample_init(struct ai_mcu_param *param)
{
    OH_AI_Status ret = OH_AI_Init(NULL, 0);
    if (ret != OH_AI_STATUS_SUCCESS) {
        osal_printk("[MNIST_TRAIN] OH_AI_Init failed (%d)\n", ret);
        return ret;
    }
    param->model = OH_AI_ModelCreate();
    param->context = OH_AI_ContextCreate();
    if (param->model == NULL || param->context == NULL) {
        osal_printk("[MNIST_TRAIN] create model/context failed\n");
        return OH_AI_STATUS_FAILED;
    }
    ret = OH_AI_ModelBuild(param->model, NULL, 0, param->context);
    if (ret != OH_AI_STATUS_SUCCESS) {
        osal_printk("[MNIST_TRAIN] OH_AI_ModelBuild failed (%d)\n", ret);
        return ret;
    }
    /*
     * Build allocates the internal RAM weight area. LoadWeight(0) copies the
     * generated initial weights into that RAM area before predict/train/eval.
     */
    ret = OH_AI_ModelLoadWeight(param->model, 0);
    if (ret != OH_AI_STATUS_SUCCESS) {
        osal_printk("[MNIST_TRAIN] OH_AI_ModelLoadWeight failed (%d)\n", ret);
        return ret;
    }
    param->inputs = OH_AI_ModelGetInputs(param->model);
    param->labels = OH_AI_ModelGetLabels(param->model);
    param->outputs = OH_AI_ModelGetOutputs(param->model);
    if (param->inputs.handle_list == NULL || param->labels.handle_list == NULL || param->outputs.handle_list == NULL) {
        osal_printk("[MNIST_TRAIN] get model tensors failed\n");
        return OH_AI_STATUS_FAILED;
    }
    return OH_AI_STATUS_SUCCESS;
}

static OH_AI_Status ai_mcu_sample_predict(struct ai_mcu_param *param)
{
    OH_AI_Status ret = ai_mcu_sample_copy_tensor(
        param->inputs.handle_list[0], g_mnist_eval_inputs[0], MNIST_TRAIN_INPUT_ELEMENTS * sizeof(float));
    if (ret != OH_AI_STATUS_SUCCESS) {
        return ret;
    }

    OH_AI_TensorHandleArray predict_outputs = param->outputs;
    if (predict_outputs.handle_num > 1) {
        predict_outputs.handle_num -= 1;
    }
    uint64_t start = uapi_tcxo_get_count();
    ret = OH_AI_ModelPredict(param->model, param->inputs, &predict_outputs);
    uint64_t end = uapi_tcxo_get_count();
    if (ret != OH_AI_STATUS_SUCCESS) {
        osal_printk("[MNIST_TRAIN] OH_AI_ModelPredict failed (%d)\n", ret);
        return ret;
    }
    osal_printk("[MNIST_TRAIN] predict label=%d time=%dms ", g_mnist_eval_labels[0],
        ((int)end - (int)start) / MNIST_TRAIN_TICKS_PER_SECOND);
    ret = ai_mcu_sample_print_logits(predict_outputs);
    osal_printk("\n");
    return ret;
}

static OH_AI_Status ai_mcu_sample_train_step(struct ai_mcu_param *param, size_t index)
{
    OH_AI_Status ret = OH_AI_ModelSetTrainMode(param->model, true);
    if (ret != OH_AI_STATUS_SUCCESS) {
        return ret;
    }
    param->outputs = OH_AI_ModelGetOutputs(param->model);

    ret = ai_mcu_sample_load_batch(param, g_mnist_train_inputs[index], &g_mnist_train_labels[index]);
    if (ret != OH_AI_STATUS_SUCCESS) {
        return ret;
    }
    uint64_t start = uapi_tcxo_get_count();
    ret = OH_AI_ModelRunStep(param->model);
    uint64_t end = uapi_tcxo_get_count();
    if (ret != OH_AI_STATUS_SUCCESS) {
        osal_printk("[MNIST_TRAIN] train OH_AI_ModelRunStep failed (%d)\n", ret);
        return ret;
    }
    float loss = 0.0f;
    ret = ai_mcu_sample_get_loss(param->outputs, &loss);
    if (ret != OH_AI_STATUS_SUCCESS) {
        return ret;
    }
    osal_printk("[MNIST_TRAIN] train step=%u label=%d time=%dms loss=", (unsigned int)index,
        g_mnist_train_labels[index], ((int)end - (int)start) / MNIST_TRAIN_TICKS_PER_SECOND);
    ai_mcu_sample_print_float(loss);
    osal_printk(" ");
    ret = ai_mcu_sample_print_logits(param->outputs);
    osal_printk("\n");
    return ret;
}

static OH_AI_Status ai_mcu_sample_eval(struct ai_mcu_param *param, const char *tag)
{
    OH_AI_Status ret = OH_AI_ModelSetTrainMode(param->model, false);
    if (ret != OH_AI_STATUS_SUCCESS) {
        return ret;
    }
    param->outputs = OH_AI_ModelGetOutputs(param->model);
    float loss_sum = 0.0f;
    uint64_t start = uapi_tcxo_get_count();
    for (size_t i = 0; i < MNIST_TRAIN_DATASET_SIZE; ++i) {
        ret = ai_mcu_sample_load_batch(param, g_mnist_eval_inputs[i], &g_mnist_eval_labels[i]);
        if (ret != OH_AI_STATUS_SUCCESS) {
            return ret;
        }
        ret = OH_AI_ModelRunStep(param->model);
        if (ret != OH_AI_STATUS_SUCCESS) {
            osal_printk("[MNIST_TRAIN] eval OH_AI_ModelRunStep failed (%d)\n", ret);
            return ret;
        }
        float loss = 0.0f;
        ret = ai_mcu_sample_get_loss(param->outputs, &loss);
        if (ret != OH_AI_STATUS_SUCCESS) {
            return ret;
        }
        loss_sum += loss;
    }
    uint64_t end = uapi_tcxo_get_count();
    osal_printk("[MNIST_TRAIN] eval %s avg_loss=", tag);
    ai_mcu_sample_print_float(loss_sum / (float)MNIST_TRAIN_DATASET_SIZE);
    osal_printk(" time=%dms\n", ((int)end - (int)start) / MNIST_TRAIN_TICKS_PER_SECOND);
    return OH_AI_STATUS_SUCCESS;
}

static void ai_mcu_sample_destroy(struct ai_mcu_param *param)
{
    if (param->model != NULL) {
        OH_AI_ModelDestroy(&(param->model));
    }
    if (param->context != NULL) {
        OH_AI_ContextDestroy(&(param->context));
    }
    (void)OH_AI_Deinit();
}

static void *ai_mcu_task(const char *arg)
{
    unused(arg);
    struct ai_mcu_param param = { 0 };
    OH_AI_Status ret = ai_mcu_sample_init(&param);
    if (ret != OH_AI_STATUS_SUCCESS) {
        osal_printk("[MNIST_TRAIN] init failed (%d)\n", ret);
        ai_mcu_sample_destroy(&param);
        return NULL;
    }

    ret = ai_mcu_sample_predict(&param);
    if (ret == OH_AI_STATUS_SUCCESS) {
        ret = ai_mcu_sample_eval(&param, "before");
    }
    for (size_t i = 0; ret == OH_AI_STATUS_SUCCESS && i < MNIST_TRAIN_DATASET_SIZE; ++i) {
        ret = ai_mcu_sample_train_step(&param, i);
    }
    if (ret == OH_AI_STATUS_SUCCESS) {
        ret = ai_mcu_sample_eval(&param, "after");
    }
    if (ret != OH_AI_STATUS_SUCCESS) {
        osal_printk("[MNIST_TRAIN] run failed (%d)\n", ret);
    }
    ai_mcu_sample_destroy(&param);
    while (true) {
        osDelay(MNIST_TRAIN_DELAY_MS);
    }
    return NULL;
}

static void tasks_test_entry(void)
{
    osal_printk("[MNIST_TRAIN] task entry\n");
    osThreadAttr_t attr;
    attr.name = "MNIST_Train_Task";
    attr.attr_bits = 0U;
    attr.cb_mem = NULL;
    attr.cb_size = 0U;
    attr.stack_mem = NULL;
    attr.stack_size = MNIST_TRAIN_STACK_SIZE;
    attr.priority = MNIST_TRAIN_TASK_PRIO;

    if (osThreadNew((osThreadFunc_t)ai_mcu_task, NULL, &attr) == NULL) {
        osal_printk("[MNIST_TRAIN] task create failed\n");
    }
}

app_run(tasks_test_entry);
