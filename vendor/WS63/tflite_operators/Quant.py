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
import numpy as np
import tensorflow as tf
 
logging.basicConfig(level=logging.NOTSET)
 
 
def create_quant_tflite_model(output_path):
    """创建 Quant 算子的 TFLite 模型"""
    # 使用 tf.quantization.fake_quant_with_min_max_args
    @tf.function(input_signature=[tf.TensorSpec(shape=[2, 3, 4], dtype=tf.float32)])
    def fake_quant(x):
        # 这会被转换为 TFLite 的 Quantize 节点
        return tf.quantization.fake_quant_with_min_max_args(
            x, 
            min=-6.0, 
            max=6.0, 
            num_bits=8, 
            narrow_range=False
        )
    
    # 转换为具体函数
    concrete_func = fake_quant.get_concrete_function()
    
    # 转换为 TFLite
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_func])
    
    # 启用量化
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.inference_input_type = tf.float32
    converter.inference_output_type = tf.int8
    
    def representative_dataset():
        for _ in range(5):
            yield [np.random.randn(2, 3, 4).astype(np.float32)]
    
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    
    tflite_model = converter.convert()
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    logging.info(f"✓ Quant TFLite 模型已保存: {output_path}")