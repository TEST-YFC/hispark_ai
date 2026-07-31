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
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include "ai.h"

#define AI_MCU_SAMPLE_NOT_QUANT 0             /* Route No.1: Not Quant */
#define AI_MCU_SAMPLE_MICRO_QUANT 0           /* Route No.2: Micro Quant */
#define AI_MCU_SAMPLE_TFLITE_QUANT 1          /* Route No.3: TFLite Quant */

#define TIME_SECOND_PER_SECOND (1000000)
#define TASKS_MCU_AI_DELAY_MS 10              /* Default */
#define AI_MCU_SAMPLE_INPUT_1_SIZE (1 * 28 * 28 * 1) /* Example: 1 * 28 * 28 * 1 */

/* third party param (TFLite) */
#define AI_MCU_SAMPLE_TFLITE_INPUT_DATATYPE uint8_t /* support change to int8_t */
#define AI_MCU_SAMPLE_TFLITE_OUTPUT_DATATYPE uint8_t /* support change to int8_t */
#define AI_MCU_SAMPLE_TFLITE_INPUT_1_QUANT_MULTIPILER 1.0 /* Example: 0.031646765768527985 */
#define AI_MCU_SAMPLE_TFLITE_INPUT_1_QUANT_ZP 0 /* Example: 53 */
#define AI_MCU_SAMPLE_TFLITE_OUTPUT_1_QUANT_MULTIPILER 1.0 /* Example: 0.00390625 */
#define AI_MCU_SAMPLE_TFLITE_OUTPUT_1_QUANT_ZP 0 /* Example: 0 */
/* To Add More input/output quant params
 * #define AI_MCU_SAMPLE_TFLITE_INPUT_2_QUANT_MULTIPILER <Input 2 Scale From Model >
 * #define AI_MCU_SAMPLE_TFLITE_INPUT_2_QUANT_ZP <Input 2 Zero Point From Model >
 * #define AI_MCU_SAMPLE_TFLITE_INPUT_3_QUANT_MULTIPILER <Input 3 Scale From Model >
 * #define AI_MCU_SAMPLE_TFLITE_INPUT_3_QUANT_ZP <Input 3 Zero Point From Model >
 * #define AI_MCU_SAMPLE_TFLITE_OUTPUT_2_QUANT_MULTIPILER <Input 2 Scale From Model >
 * #define AI_MCU_SAMPLE_TFLITE_OUTPUT_2_QUANT_ZP <Input 2 Zero Point From Model >
*/

#ifdef __cplusplus
#if __cplusplus
extern "C" {
#endif
#endif

typedef struct {
    OH_AI_ModelHandle model;
    OH_AI_ContextHandle context;
    OH_AI_TensorHandleArray inputs;
    OH_AI_TensorHandleArray outputs;
} ai_mcu_param;

const float input_buffer_fp32[AI_MCU_SAMPLE_INPUT_1_SIZE] = { 0 };
static struct timeval g_time_start, g_time_end;

static OH_AI_Status ai_mcu_sample_print_output_tensor(OH_AI_TensorHandle tensor, float scale, float zp)
{
    size_t data_size = OH_AI_TensorGetDataSize(tensor);
    printf("[AI_MCU] Data size: [%zu]\n", data_size);
    printf("Shape: [");
    size_t shape_num = 0;
    const int64_t *dims = OH_AI_TensorGetShape(tensor, &shape_num);
    if (dims == NULL) {
        printf("[AI_MCU] OH_AI_TensorGetShape failed\n");
        return OH_AI_STATUS_FAILED;
    }
    for (size_t i = 0; i < shape_num; i++) {
        printf("%d ", (int)dims[i]);
    }
    printf("]\n");

    OH_AI_DataType data_type = OH_AI_TensorGetDataType(tensor);
    if (data_type == OH_AI_DATATYPE_UNKNOWN) {
        printf("[AI_MCU] OH_AI_TensorGetDataType failed\n");
        return OH_AI_STATUS_FAILED;
    }
    printf("DataType: %d\n", data_type);

    void *out_data = OH_AI_TensorGetMutableData(tensor);
    if (out_data == NULL) {
        printf("[AI_MCU] OH_AI_TensorGetMutableData failed\n");
        return OH_AI_STATUS_FAILED;
    }
    printf("[AI_MCU] Data: ");
    for (size_t i = 0; i < (size_t)(OH_AI_TensorGetElementNum(tensor)); i++) {
#if AI_MCU_SAMPLE_NOT_QUANT
        unused(scale);
        unused(zp);
        float f = ((float *)out_data)[i];
        printf("[%f]", f);
#elif AI_MCU_SAMPLE_MICRO_QUANT
        unused(scale);
        unused(zp);
        float f = ((float *)out_data)[i];
        printf("[%f]", f);
#elif AI_MCU_SAMPLE_TFLITE_QUANT
        AI_MCU_SAMPLE_TFLITE_OUTPUT_DATATYPE d = ((AI_MCU_SAMPLE_TFLITE_OUTPUT_DATATYPE *)out_data)[i];
        float f = ((float)d - zp) * scale;
        printf("[%f]", f);
#endif
    }
    printf("\n");
    return OH_AI_STATUS_SUCCESS;
}
/* To Add Output Datatype for index (used the function below)
 1. change {float f = ((float *)out_data)[i];} --> {int32_t f = ((int32_t *)out_data)[i];}
 2. change {ai_mcu_sample_printf_float(f);} --> {printf("%d", f);}
*/

static void ai_mcu_sample_load_data(void *input_buffer, void *data_buf, size_t size, float scale, float zp)
{
#if AI_MCU_SAMPLE_NOT_QUANT
    unused(scale);
    unused(zp);
    size_t mem_size = size * sizeof(float);
    memcpy_s(input_buffer, mem_size, data_buf, mem_size);
#elif AI_MCU_SAMPLE_MICRO_QUANT
    unused(scale);
    unused(zp);
    size_t mem_size = size * sizeof(float);
    memcpy_s(input_buffer, mem_size, data_buf, mem_size);
#elif AI_MCU_SAMPLE_TFLITE_QUANT
    for (size_t b = 0; b < size; b++) {
        ((AI_MCU_SAMPLE_TFLITE_INPUT_DATATYPE *)input_buffer)[b] = (((float *)data_buf)[b] / scale + zp);
    }
#endif
}
/* To Add Input Datatype for index (used the function below)
    static void ai_mcu_sample_index_load_data(void *input_buffer, void *data_buf, size_t size, float scale, float zp)
    {
    #if AI_MCU_SAMPLE_NOT_QUANT
        unused(scale);
        unused(zp);
        size_t mem_size = size * sizeof(int32_t);
        memcpy_s(input_buffer, mem_size, data_buf, mem_size);
    #elif AI_MCU_SAMPLE_MICRO_QUANT
        unused(scale);
        unused(zp);
        size_t mem_size = size * sizeof(int32_t);
        memcpy_s(input_buffer, mem_size, data_buf, mem_size);
    #else
        for (size_t b = 0; b < size; b++) {
          ((AI_MCU_SAMPLE_TFLITE_INPUT_DATATYPE *)input_buffer)[b] = (((int32_t *)data_buf)[b] / scale + zp);
        }
    #endif
    }
*/

OH_AI_Status ai_mcu_sample_init(ai_mcu_param *sample_param)
{
    /* MS Model Init (Only once) */
    printf("[AI_MCU] ai_mcu_sample_init\n");
    OH_AI_Status ret = OH_AI_Init(NULL, 0);
    if (ret != OH_AI_STATUS_SUCCESS) {
        printf("[AI_MCU] OH_AI_Init failed (%d)\n", ret);
        return ret;
    }
    OH_AI_ModelHandle model = OH_AI_ModelCreate();
    OH_AI_ContextHandle context = OH_AI_ContextCreate();
    sample_param->model = model;
    sample_param->context = context;
    ret = OH_AI_ModelBuild(sample_param->model, NULL, 0, sample_param->context);
    if (ret != OH_AI_STATUS_SUCCESS) {
        printf("[AI_MCU] OH_AI_ModelBuild failed (%d)\n", ret);
        return ret;
    }
    OH_AI_TensorHandleArray inputs = OH_AI_ModelGetInputs(sample_param->model);
    sample_param->inputs = inputs;
    if (inputs.handle_list == NULL) {
        printf("[AI_MCU] OH_AI_ModelGetInputs failed\n");
        return OH_AI_STATUS_FAILED;
    }
    OH_AI_TensorHandleArray outputs = OH_AI_ModelGetOutputs(sample_param->model);
    sample_param->outputs = outputs;
    if (outputs.handle_list == NULL) {
        printf("[AI_MCU] OH_AI_ModelGetOutputs failed\n");
        return OH_AI_STATUS_FAILED;
    }
    return OH_AI_STATUS_SUCCESS;
}

static void ai_mcu_sample_destroy(ai_mcu_param *sample_param)
{
    printf("[AI_MCU] ai_mcu_sample_destroy\n");
    /* MS Model Destroy (Only once) */
    OH_AI_ModelDestroy(&(sample_param->model));
    OH_AI_ContextDestroy(&(sample_param->context));
    OH_AI_Deinit();
}

OH_AI_Status ai_mcu_sample_process(ai_mcu_param sample_param)
{
    printf("[AI_MCU] ai_mcu_sample_process\n");

    /* MS Prepare Input Data */
    void *input_data = OH_AI_TensorGetMutableData(sample_param.inputs.handle_list[0]);
    if (input_data == NULL) {
        printf("[AI_MCU] OH_AI_TensorGetMutableData failed\n");
        return OH_AI_STATUS_FAILED;
    }
    /* Add More Input
     * void *input_data_2 = OH_AI_TensorGetMutableData(sample_param.inputs.handle_list[1]);
     * if (input_data_2 == NULL) {
     *     printf("[AI_MCU] OH_AI_TensorGetMutableData 2 failed\n");
     *     return OH_AI_STATUS_FAILED;
     * }
     * void *input_data_3 = OH_AI_TensorGetMutableData(sample_param.inputs.handle_list[2]);
     * if (input_data_3 == NULL) {
     *     printf("[AI_MCU] OH_AI_TensorGetMutableData 2 failed\n");
     *     return OH_AI_STATUS_FAILED;
     * }
    */

    ai_mcu_sample_load_data(input_data, (void *)input_buffer_fp32, AI_MCU_SAMPLE_INPUT_1_SIZE,
        AI_MCU_SAMPLE_TFLITE_INPUT_1_QUANT_MULTIPILER, AI_MCU_SAMPLE_TFLITE_INPUT_1_QUANT_ZP);
    /*
     * Add More Input
     * ai_mcu_sample_load_data(input_data_2, (void *)input_buffer_fp32_2, AI_MCU_SAMPLE_INPUT_2_SIZE,
     *     AI_MCU_SAMPLE_TFLITE_INPUT_2_QUANT_MULTIPILER, AI_MCU_SAMPLE_TFLITE_INPUT_2_QUANT_ZP);
     * ai_mcu_sample_load_data(input_data_3, (void *)input_buffer_fp32_3, AI_MCU_SAMPLE_INPUT_3_SIZE,
     *     AI_MCU_SAMPLE_TFLITE_INPUT_3_QUANT_MULTIPILER, AI_MCU_SAMPLE_TFLITE_INPUT_3_QUANT_ZP);
    */

    /* MS Model Predict */
    gettimeofday(&g_time_start, NULL);
    OH_AI_Status ret = OH_AI_ModelPredict(sample_param.model, sample_param.inputs, &(sample_param.outputs));
    gettimeofday(&g_time_end, NULL);
    printf("[AI_MCU] Get Time %lld ms\n\n",
                    TIME_SECOND_PER_SECOND * (g_time_end.tv_sec - g_time_start.tv_sec) +
                    ((int)(g_time_end.tv_usec) - g_time_start.tv_usec));
    
    if (ret != OH_AI_STATUS_SUCCESS) {
        printf("[AI_MCU] OH_AI_ModelPredict failed (%d)\n", ret);
        return ret;
    }

    /* PostProcess */
    OH_AI_TensorHandle output = sample_param.outputs.handle_list[0];
    if (output == NULL) {
        printf("[AI_MCU] OH_AI_ModelGetOutputs failed\n");
        return OH_AI_STATUS_FAILED;
    }
    /* Add more output
     * OH_AI_TensorHandle output_2 = sample_param.outputs.handle_list[1];
     * if (output_2 == NULL) {
     *     printf("[AI_MCU] OH_AI_ModelGetOutputs 2 failed\n");
     *     return OH_AI_STATUS_FAILED;
     * }
    */

    ret = ai_mcu_sample_print_output_tensor(output, AI_MCU_SAMPLE_TFLITE_OUTPUT_1_QUANT_MULTIPILER,
        AI_MCU_SAMPLE_TFLITE_OUTPUT_1_QUANT_ZP);
    if (ret != OH_AI_STATUS_SUCCESS) {
        printf("[AI_MCU] ai_mcu_sample_print_output_tensor failed (%d)\n", ret);
        return ret;
    }
    /* Add more output
     * ret = ai_mcu_sample_print_output_tensor(output_2, AI_MCU_SAMPLE_TFLITE_OUTPUT_2_QUANT_MULTIPILER
     *     AI_MCU_SAMPLE_TFLITE_OUTPUT_2_QUANT_ZP);
     * if (ret != OH_AI_STATUS_SUCCESS) {
     *     printf("[AI_MCU] ai_mcu_sample_print_output_tensor 2 failed (%d)\n", ret);
     *     return ret;
     * }
    */
    return OH_AI_STATUS_SUCCESS;
}

int main()
{
    ai_mcu_param sample_param = {0};
    OH_AI_Status ret = ai_mcu_sample_init(&sample_param);
    if (ret != OH_AI_STATUS_SUCCESS) {
        printf("[AI_MCU] ai_mcu_sample_init failed (%d)\n", ret);
        ai_mcu_sample_destroy(&sample_param);
        return -1;
    }
    while (1) {
        ret = ai_mcu_sample_process(sample_param);
        if (ret != OH_AI_STATUS_SUCCESS) {
            printf("[AI_MCU] ai_mcu_sample_process failed (%d)\n", ret);
            ai_mcu_sample_destroy(&sample_param);
            return -1;
        }
        sleep(TASKS_MCU_AI_DELAY_MS);
    }
    ai_mcu_sample_destroy(&sample_param);
    return 0;
}

#ifdef __cplusplus
#if __cplusplus
}
#endif
#endif