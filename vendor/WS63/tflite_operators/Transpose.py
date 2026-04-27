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
import numpy as np
logging.basicConfig(level=logging.NOTSET)


def create_transpose_tflite_model(output_path):
    """创建 Conv2D + Transpose + Add 算子的 TFLite 模型
    
    流程: input -> Conv2D -> Transpose -> Add -> output
    
    Args:
        output_path: 模型保存路径
    """
    class ConvTransposeAddModel(tf.Module):
        def __init__(self):
            super(ConvTransposeAddModel, self).__init__()
        
        @tf.function(input_signature=[
            tf.TensorSpec(shape=[1, 5, 5, 1], dtype=tf.float32, name="input")  # [batch, height, width, channels]
        ])
        def __call__(self, x):
            # 1. Conv2D 层
            # 创建 3x3 卷积核，输入通道1，输出通道1，使用全1初始化
            conv_kernel = tf.constant(
                [
                    [[[1.0]], [[1.0]], [[1.0]]],
                    [[[1.0]], [[1.0]], [[1.0]]],
                    [[[1.0]], [[1.0]], [[1.0]]]
                ],
                dtype=tf.float32,
                name="conv_kernel"
            )
            
            # 执行卷积: padding='VALID' 使得输出尺寸从 5x5 变为 3x3
            conv_output = tf.nn.conv2d(
                x,
                conv_kernel,
                strides=[1, 1, 1, 1],
                padding='VALID',
                name="conv2d"
            )
            # conv_output shape: [1, 3, 3, 1]
            
            # 2. Transpose 层
            # 定义转置轴排列: [batch, height, width, channels] -> [batch, width, height, channels]
            # 相当于交换 H 和 W 维度
            perm = tf.constant([0, 2, 1, 3], dtype=tf.int32, name="perm")
            transpose_output = tf.transpose(
                conv_output,
                perm=perm,
                name="transpose"
            )
            # transpose_output shape: [1, 3, 3, 1] (经过转置后 H和W交换，但尺寸相同所以形状不变)
            # 如果想看到明显的形状变化，可以使用 perm=[0, 3, 1, 2] 得到 [1, 1, 3, 3]
            
            # 3. Add 层
            # 创建一个常量张量用于加法
            add_constant = tf.constant(
                0.5,
                dtype=tf.float32,
                shape=[1, 3, 3, 1],
                name="add_constant"
            )
            output = tf.add(
                transpose_output,
                add_constant,
                name="output"
            )
            # output shape: [1, 3, 3, 1]
            
            return output
    
    # 创建模型实例
    model = ConvTransposeAddModel()
    
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
    
    logging.info(f"✓ Conv2D+Transpose+Add TFLite 模型已保存: {output_path}")
    
    # 打印模型信息
    print("\n" + "="*50)
    print("TFLite Model computation flow:")
    print("="*50)
    print(f"Input shape: [1, 5, 5, 1] (NHWC format)")
    print(f"  ↓ Conv2D (3x3 kernel, stride=1, padding='VALID')")
    print(f"Conv2D output shape: [1, 3, 3, 1]")
    print(f"  ↓ Transpose (perm=[0, 2, 1, 3]) - 交换 H 和 W 维度")
    print(f"Transpose output shape: [1, 3, 3, 1]")
    print(f"  ↓ Add (+ constant 0.5)")
    print(f"Output shape: [1, 3, 3, 1]")
    print("="*50 + "\n")
