# Copyright (c) HiSilicon (Shanghai) Technologies Co., Ltd. 2025-2025. All rights reserved.
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


def create_l2norm_tflite_model(output_path):
    """创建 L2Norm 算子的 TFLite 模型"""
    # 1. 定义 TensorFlow 模型（仅包含 L2Norm 操作）
    class L2NormModel(tf.Module):
        def __init__(self):
            super(L2NormModel, self).__init__()
        
        @tf.function(input_signature=[
            tf.TensorSpec(shape=[1, 3, 4, 1], dtype=tf.float32, name="input")  # 4D输入示例
        ])
        def __call__(self, x):
            # 计算L2范数（沿最后一个维度归一化）
            l2_norm = tf.math.l2_normalize(
                x, 
                axis=-1,  # 指定归一化轴（最后一个维度）
                epsilon=1e-12,  # 防止除以零的小值
                name="output"  # 明确指定输出名称
            )
            return l2_norm
    
    # 2. 创建模型实例
    model = L2NormModel()
    
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
    logging.info(f"✓ L2Norm TFLite 模型已保存: {output_path}")