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


def create_pad_tflite_model(output_path, mode='CONSTANT'):
    """创建 Pad 算子的 TFLite 模型
    
    Args:
        output_path: 模型保存路径
        mode: 填充模式 ('CONSTANT', 'REFLECT', 'SYMMETRIC')
              CONSTANT - 常数填充(默认)
              REFLECT - 镜像填充(不包含边界值)
              SYMMETRIC - 对称填充(包含边界值)
    """
    class PadModel(tf.Module):
        def __init__(self):
            super(PadModel, self).__init__()
        
        @tf.function(input_signature=[
            tf.TensorSpec(shape=[1, 2, 3, 1], dtype=tf.float32, name="input")
        ])
        def __call__(self, x):
            # 定义填充尺寸 [[0,0], [1,1], [1,1], [0,0]]
            # 表示在高度和宽度维度各填充1
            paddings = tf.constant([[0, 0], [1, 1], [1, 1], [0, 0]])
            
            # 使用 tf.pad 进行填充
            return tf.pad(
                x,
                paddings=paddings,
                mode=mode,
                constant_values=0,  # 仅CONSTANT模式有效
                name="output"
            )
    
    # 创建模型实例
    model = PadModel()
    
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
    logging.info(f"✓ Pad TFLite 模型已保存: {output_path}")