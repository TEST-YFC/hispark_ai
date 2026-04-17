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
 
 
def create_dequant_tflite_model(output_path):
    """创建 Dequant 算子的 TFLite 模型"""
    # 1. 先创建一个包含 QUANTIZE 和 DEQUANTIZE 的模型
    class QuantDequantModel(tf.Module):
        def __init__(self):
            super().__init__()
            
        @tf.function(input_signature=[tf.TensorSpec(shape=[2, 3, 4], dtype=tf.float32)])
        def quantize_dequantize(self, x):
            # 使用 tf.quantization.fake_quant_with_min_max_vars
            # 这会生成 QUANTIZE 和 DEQUANTIZE 节点
            quantized = tf.quantization.fake_quant_with_min_max_vars(
                x,
                min=tf.constant(-6.0, dtype=tf.float32),
                max=tf.constant(6.0, dtype=tf.float32),
                num_bits=8,
                narrow_range=False
            )
            return quantized
    
    # 2. 创建模型实例
    model = QuantDequantModel()
    
    # 3. 转换为具体函数
    concrete_func = model.quantize_dequantize.get_concrete_function()
    
    # 4. 转换为 TensorFlow Lite
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_func])
    
    # 重要：设置输入为 int8，这会强制模型使用 QUANTIZE/DEQUANTIZE
    converter.inference_input_type = tf.uint8
    converter.inference_output_type = tf.float32
    
    # 启用量化
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    
    # 设置代表性数据集
    def representative_dataset():
        for _ in range(5):
            data = np.random.randint(0, 255, (2, 3, 4), dtype=np.uint8)
            yield [data.astype(np.float32)]  # 转换为 float32 输入
    
    converter.representative_dataset = representative_dataset
    
    # 设置支持的算子
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS_INT8,
        tf.lite.OpsSet.TFLITE_BUILTINS
    ]
    
    # 5. 转换模型
    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    logging.info(f"✓ Dequant TFLite 模型已保存: {output_path}")