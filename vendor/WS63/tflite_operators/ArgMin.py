# Copyright (c) 2025-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
import logging
import tensorflow as tf

logging.basicConfig(level=logging.NOTSET)


def create_argmin_tflite_model(output_path):
    """创建 ArgMin 算子的 TFLite 模型"""
    # 1. 定义 TensorFlow 模型（仅包含 ArgMin 操作）
    class ArgMinModel(tf.Module):
        def __init__(self):
            super(ArgMinModel, self).__init__()
        
        @tf.function(input_signature=[
            tf.TensorSpec(shape=[2, 3, 4, 5], dtype=tf.float32, name="input")  # 4D输入示例
        ])
        def __call__(self, x):
            return tf.argmin(x, axis=3, output_type=tf.int32, name="argmin_output")
    
    # 2. 创建模型实例
    model = ArgMinModel()
    
    # 3. 转换为 TFLite 模型
    converter = tf.lite.TFLiteConverter.from_concrete_functions(
        [model.__call__.get_concrete_function()],
        model
    )
    
    # 禁用实验性转换器以获得更稳定的输出
    converter.experimental_new_converter = False
    
    # 4. 保存 TFLite 模型
    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    logging.info(f"✓ ArgMin TFLite 模型已保存: {output_path}")