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
#include "ai.h"
#include "securec.h"

#if defined(CHIP_VERSION) && (CHIP_VERSION == 3322)

#include "ai_main.h"
#include "osal_debug.h"
#include "common_def.h"
#include "cmsis_os2.h"
#include "tcxo.h"

/* Task Param */
#define TASKS_NPU_AI_STACK_SIZE 0x1000       /* Max Stack Size in this task */
#define TASKS_NPU_AI_PRIO (osPriority_t)(17) /* Task Priority in LiteOS */
#define TASKS_NPU_AI_DELAY_MS 10              /* Default */

/* Src Path */
#define TASKS_NPU_AI_INPUT_PATH "/user/sample_mnist.bin"
#define TASKS_NPU_AI_MODEL_PATH "/user/mnist.exeom"

#define ai_printf(...) osal_printk(__VA_ARGS__)

static long long get_time_ms(void)
{
    return uapi_tcxo_get_ms();
}

#elif CHIP_VERSION == 1156

#include <stdio.h>
#include <time.h>

#define ai_printf(...) printf(__VA_ARGS__)

/* Src Path */
#define TASKS_NPU_AI_INPUT_PATH "/etc/workspace/sample.bin"
#define TASKS_NPU_AI_MODEL_PATH "/etc/workspace/mnist.om"

static long long get_time_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    long long time_ms = ts.tv_sec * 1000LL + ts.tv_nsec / 1000000LL;
    return time_ms;
}

#else
#endif

/* Model Param */
enum {
    LENET5_MODEL_INPUT_IAMGE = 0,
    AI_NPU_INPUT_NUM
};
enum {
    LENET5_MODEL_OUTPUT_LOGITS = 0,
    AI_NPU_OUTPUT_NUM
};

struct ai_npu_param {
    OH_AI_ModelHandle model;
    OH_AI_ContextHandle context;
    OH_AI_TensorHandleArray inputs;
    OH_AI_TensorHandleArray outputs;
};

void float32_fuzz(float *__restrict out, const short in)
{
    unsigned int t1;
    unsigned int t2;
    unsigned int t3;

    t1 = (unsigned int)in & 0x7fffu;                       // Non-sign bits
    t2 = (unsigned int)in & 0x8000u;                       // Sign bit
    t3 = (unsigned int)in & 0x7c00u;                       // Exponent

    t1 <<= 13u;                                            // Align mantissa on MSB
    t2 <<= 16u;                                            // Shift sign bit into position

    t1 += 0x38000000;                                      // Adjust bias

    t1 = (t3 == 0 ? 0 : t1);                               // Denormals-as-zero

    t1 |= t2;                                              // Re-insert sign bit

    *((unsigned int *)out) = t1;
};

static OH_AI_Status ai_npu_sample_read_bin_to_buffer(const char* file_path, void *input_buffer, size_t input_size)
{
    ai_printf("[AI_NPU] ai_npu_sample_read_bin_to_buffer\n");

    FILE* fp = fopen(file_path, "rb");
    if (fp == NULL) {
        ai_printf("[AI_NPU] File load failed");
        return OH_AI_STATUS_FAILED;
    }

    size_t read_elements = fread(input_buffer, sizeof(char), input_size, fp);
    if (read_elements != input_size) {
        ai_printf("[AI_NPU] expected element number: %zu, got: %zu\n", input_size, read_elements);
        fclose(fp);
        return OH_AI_STATUS_FAILED;
    }

    if (fclose(fp) != 0) {
        ai_printf("[AI_NPU] fclose fail\n");
    }
    return OH_AI_STATUS_SUCCESS;
}

static OH_AI_Status ai_npu_sample_load_data(struct ai_npu_param *sample_param)
{
    if (sample_param->inputs.handle_num != 1) {
        ai_printf("[AI_NPU] the model inputs num mismatch\n");
        return OH_AI_STATUS_FAILED;
    }
    void *input_image_data = OH_AI_TensorGetMutableData(sample_param->inputs.handle_list[LENET5_MODEL_INPUT_IAMGE]);
    if (input_image_data == NULL) {
        ai_printf("[AI_NPU] OH_AI_TensorGetMutableData failed\n");
        return OH_AI_STATUS_FAILED;
    }

    size_t data_size = OH_AI_TensorGetDataSize(sample_param->inputs.handle_list[LENET5_MODEL_INPUT_IAMGE]);

    OH_AI_Status ret = ai_npu_sample_read_bin_to_buffer(TASKS_NPU_AI_INPUT_PATH, input_image_data, data_size);
    if (ret != OH_AI_STATUS_SUCCESS) {
        ai_printf("[AI_NPU] ai_npu_sample_read_bin_to_buffer failed (%d)\n", ret);
        return ret;
    }

    return OH_AI_STATUS_SUCCESS;
}

static void ai_npu_sample_print_data(OH_AI_DataType data_type, void *out_data, size_t element_num)
{
    ai_printf("[AI_NPU] Data: ");
    for (size_t i = 0; i < element_num; i++) {
        float f;
        switch (data_type) {
            case OH_AI_DATATYPE_NUMBERTYPE_FLOAT16:
                float32_fuzz(&f, ((short *)out_data)[i]);
                break;
            case OH_AI_DATATYPE_NUMBERTYPE_FLOAT32:
                f = ((float *)out_data)[i];
                break;
            case OH_AI_DATATYPE_NUMBERTYPE_INT8:
                f = ((int8_t *)out_data)[i];
                break;
            case OH_AI_DATATYPE_NUMBERTYPE_UINT8:
                f = ((uint8_t *)out_data)[i];
                break;
            default:
                f = 0.0f;
                break;
        }
        ai_printf("[%.5f]", f);
    }
    ai_printf("\n");
}

static OH_AI_Status ai_npu_sample_print_output_tensor(OH_AI_TensorHandle tensor)
{
    size_t data_size = OH_AI_TensorGetDataSize(tensor);
    ai_printf("[AI_NPU] Data size: [%zu]\n", data_size);
    ai_printf("[AI_NPU] Shape: [");
    size_t shape_num = 0;
    const int64_t *dims = OH_AI_TensorGetShape(tensor, &shape_num);
    if (dims == NULL) {
        ai_printf("[AI_NPU] OH_AI_TensorGetShape failed\n");
        return OH_AI_STATUS_FAILED;
    }
    for (size_t i = 0; i < shape_num; i++) {
        if (i == shape_num - 1) {
            ai_printf("%d", (int)dims[i]);
        } else {
            ai_printf("%d ", (int)dims[i]);
        }
    }
    ai_printf("]\n");

    OH_AI_DataType data_type = OH_AI_TensorGetDataType(tensor);
    if (data_type == OH_AI_DATATYPE_UNKNOWN) {
        ai_printf("[AI_NPU] OH_AI_TensorGetDataType failed\n");
        return OH_AI_STATUS_FAILED;
    }
    ai_printf("[AI_NPU] DataType: %d\n", data_type);

    void *out_data = OH_AI_TensorGetMutableData(tensor);
    if (out_data == NULL) {
        ai_printf("[AI_NPU] OH_AI_TensorGetMutableData failed\n");
        return OH_AI_STATUS_FAILED;
    }
    size_t element_num = (size_t)OH_AI_TensorGetElementNum(tensor);
    ai_npu_sample_print_data(data_type, out_data, element_num);

    return OH_AI_STATUS_SUCCESS;
}

static OH_AI_Status ai_npu_deploy_sample_process(struct ai_npu_param *sample_param)
{
    ai_printf("[AI_NPU] ai_npu_deploy_sample_process\n");

    /* Prepare Input Data */
    OH_AI_Status ret = ai_npu_sample_load_data(sample_param);
    if (ret != OH_AI_STATUS_SUCCESS) {
        ai_printf("[AI_NPU] ai_npu_sample_load_data failed (%d)\n", ret);
        return ret;
    }

    /* Model Predict */
    long long t1 = get_time_ms();
    ret = OH_AI_ModelPredict(sample_param->model, sample_param->inputs, &(sample_param->outputs));
    long long t2 = get_time_ms();
    ai_printf("[AI_NPU] the predict cost time %d ms\n", (int)(t2 - t1));
    if (ret != OH_AI_STATUS_SUCCESS) {
        ai_printf("[AI_NPU] OH_AI_ModelPredict failed (%d)\n", ret);
        return ret;
    }

    /* PostProcess */
    if (sample_param->outputs.handle_num != 1) {
        ai_printf("[AI_NPU] the model outputs num mismatch\n");
        return OH_AI_STATUS_FAILED;
    }
    OH_AI_TensorHandle output_logits = sample_param->outputs.handle_list[LENET5_MODEL_OUTPUT_LOGITS];
    if (output_logits == NULL) {
        ai_printf("[AI_NPU] OH_AI_ModelGetOutputs failed\n");
        return OH_AI_STATUS_FAILED;
    }
    ret = ai_npu_sample_print_output_tensor(output_logits);
    if (ret != OH_AI_STATUS_SUCCESS) {
        ai_printf("[AI_NPU] ai_npu_sample_print_output_tensor failed (%d)\n", ret);
        return ret;
    }

    return OH_AI_STATUS_SUCCESS;
}

static OH_AI_Status ai_npu_sample_init(struct ai_npu_param *sample_param)
{
    ai_printf("[AI_NPU] ai_npu_sample_init\n");

    OH_AI_Status ret = OH_AI_InitFromFile(NULL);
    if (ret != OH_AI_STATUS_SUCCESS) {
        ai_printf("[AI_NPU] OH_AI_InitFromFile failed (%d)\n", ret);
        return ret;
    }

    OH_AI_ModelHandle model = OH_AI_ModelCreate();
    if (model == NULL) {
        int32_t error_code = OH_AI_GetErrorCode();
        ai_printf("[AI_NPU] OH_AI_ModelCreate failed (%d)\n", error_code);
        return OH_AI_STATUS_FAILED;
    }
    OH_AI_ContextHandle context = OH_AI_ContextCreate();
    if (context == NULL) {
        int32_t error_code = OH_AI_GetErrorCode();
        ai_printf("[AI_NPU] OH_AI_ContextCreate failed (%d)\n", error_code);
        return OH_AI_STATUS_FAILED;
    }
    sample_param->model = model;
    sample_param->context = context;

    ret = OH_AI_ModelBuildFromFile(sample_param->model, TASKS_NPU_AI_MODEL_PATH, sample_param->context);
    if (ret != OH_AI_STATUS_SUCCESS) {
        ai_printf("[AI_NPU] OH_AI_ModelBuildFromFile failed (%d)\n", ret);
        return ret;
    }

    OH_AI_TensorHandleArray inputs = OH_AI_ModelGetInputs(sample_param->model);
    sample_param->inputs = inputs;
    if (inputs.handle_list == NULL) {
        ai_printf("[AI_NPU] OH_AI_ModelGetInputs failed\n");
        return OH_AI_STATUS_FAILED;
    }
    if (inputs.handle_num != AI_NPU_INPUT_NUM) {
        ai_printf("[AI_NPU] The number of model inputs does not match.\n");
        return OH_AI_STATUS_FAILED;
    }
    OH_AI_TensorHandleArray outputs = OH_AI_ModelGetOutputs(sample_param->model);
    sample_param->outputs = outputs;
    if (outputs.handle_list == NULL) {
        ai_printf("[AI_NPU] OH_AI_ModelGetOutputs failed\n");
        return OH_AI_STATUS_FAILED;
    }
    if (outputs.handle_num != AI_NPU_OUTPUT_NUM) {
        ai_printf("[AI_NPU] The number of model outputs does not match.\n");
        return OH_AI_STATUS_FAILED;
    }

    return OH_AI_STATUS_SUCCESS;
}

static void ai_npu_sample_destroy(struct ai_npu_param *sample_param)
{
    ai_printf("[AI_NPU] ai_npu_sample_destroy\n");
    /* Model Destroy (Only once) */
    OH_AI_ModelDestroy(&(sample_param->model));
    OH_AI_ContextDestroy(&(sample_param->context));

    /* Deinitialize the AI module */
    OH_AI_Status ret = OH_AI_Deinit();
    if (ret != OH_AI_STATUS_SUCCESS) {
        ai_printf("[AI_NPU] OH_AI_Deinit failed (%d)\n", ret);
    }
}

static void ai_npu_task_deploy_sample(void)
{
    /* Model Init (Only once) */
    struct ai_npu_param sample_param = {0};
    OH_AI_Status ret = ai_npu_sample_init(&sample_param);
    if (ret != OH_AI_STATUS_SUCCESS) {
        ai_printf("[AI_NPU] ai_npu_sample_init failed (%d)\n", ret);
        ai_npu_sample_destroy(&sample_param);
        return;
    }

    ret = ai_npu_deploy_sample_process(&sample_param);
    if (ret != OH_AI_STATUS_SUCCESS) {
        ai_printf("[AI_NPU] ai_npu_sample_process failed (%d)\n", ret);
        ai_npu_sample_destroy(&sample_param);
        return;
    }

    ai_npu_sample_destroy(&sample_param);
}

#if defined(CHIP_VERSION) && (CHIP_VERSION == 3322)

static void *ai_npu_task(const char *arg)
{
    unused(arg);
    ai_printf("[AI_NPU] excute deploy sample\n");
    ai_npu_task_deploy_sample();
    return NULL;
}

/* Sample entry function */
void tasks_test_entry(void)
{
    osThreadAttr_t attr;
    attr.name = "AI_NPU_Task";
    attr.attr_bits = 0U;
    attr.cb_mem = NULL;
    attr.cb_size = 0U;
    attr.stack_mem = NULL;
    attr.stack_size = TASKS_NPU_AI_STACK_SIZE;
    attr.priority = TASKS_NPU_AI_PRIO;

    if (osThreadNew((osThreadFunc_t)ai_npu_task, NULL, &attr) == NULL) {
        /* Create task fail. */
        ai_printf("[AI_NPU] Task Create Failed\n");
    }
}

#elif CHIP_VERSION == 1156

int main()
{
    ai_npu_task_deploy_sample();
    return 0;
}

#else
#endif
