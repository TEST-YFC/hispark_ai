#!/bin/bash
# Copyright (c) 2026-2026 HiSilicon (Shanghai) Technologies Co., Ltd

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
set -e
# step1: 下载mnist数据集；并处理成bin格式
python3 ../../../oh/lenet5/scripts/preproc_mnist_data.py \
    --orig_path ./data \
    --train_path ./train_data \
    --test_path ./test_data \
    --train_file_format bin \
    --test_file_format bin

# step2：进行模型量化操作
amct_onnx calibration --model "../../../oh/lenet5/model/mnist-12.onnx" \
    --save_path "./output/mnist" \
    --input_shape "Input3:1,1,28,28" \
    --data_dir "./train_data/bin" \
    --data_types "float32" \
    --batch_num 9999