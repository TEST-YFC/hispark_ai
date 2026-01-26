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


def create_transpose_tflite_model(output_path):
    """创建 Transpose 算子的 TFLite 模型
    
    Args:
        output_path: 模型保存路径
    """
    class TransposeModel(tf.Module):
        def __init__(self):
            super(TransposeModel, self).__init__()
        
        @tf.function(input_signature=[
            tf.TensorSpec(shape=[1, 2, 3, 1], dtype=tf.float32, name="input")
        ])
        def __call__(self, x):
            # 定义转置的轴排列顺序 [0, 2, 1, 3]
            perm = tf.constant([0, 2, 1, 3], dtype=tf.int32)
            
            # 使用 tf.transpose 进行张量转置
            return tf.transpose(
                x,
                perm=perm,
                name="output"
            )
    
    # 创建模型实例
    model = TransposeModel()
    
    # 转换为 TFLite 模型
    converter = tf.lite.TFLiteConverter.from_concrete_functions(
        [model.__call__.get_concrete_function()],
        model
    )
    
    # 禁用实验性转换器以获得更稳定的输出
    converter.experimental_new_converter = False
    
    # 保存 TFLite 模型
    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    logging.info(f"✓ Transpose TFLite 模型已保存: {output_path}")