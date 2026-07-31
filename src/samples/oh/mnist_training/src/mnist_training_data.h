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
#ifndef MNIST_TRAINING_DATA_H_
#define MNIST_TRAINING_DATA_H_

#include <stdint.h>

#define AI_MCU_SAMPLE_TRAIN_DATASET_SIZE 500
#define AI_MCU_SAMPLE_EVAL_DATASET_SIZE 500
#define AI_MCU_SAMPLE_INPUT_1_SIZE 784
#define AI_MCU_SAMPLE_LABEL_SIZE 1

extern const uint8_t g_mnist_train_inputs[AI_MCU_SAMPLE_TRAIN_DATASET_SIZE][AI_MCU_SAMPLE_INPUT_1_SIZE];
extern const int32_t g_mnist_train_labels[AI_MCU_SAMPLE_TRAIN_DATASET_SIZE];
extern const uint8_t g_mnist_eval_inputs[AI_MCU_SAMPLE_EVAL_DATASET_SIZE][AI_MCU_SAMPLE_INPUT_1_SIZE];
extern const int32_t g_mnist_eval_labels[AI_MCU_SAMPLE_EVAL_DATASET_SIZE];

#endif
