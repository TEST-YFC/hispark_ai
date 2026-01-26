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
from onnx import helper, TensorProto
from . import create_low_ir_version_model

logging.basicConfig(level=logging.NOTSET)


def create_flatten_onnx_model(output_path, axis=1):
    """创建 Flatten 算子 ONNX 模型
    
    Args:
        output_path: 模型保存路径
        axis: 指定从哪个维度开始展平 (默认=1)
    """
    logging.info(f"创建 Flatten 模型: {output_path}")
    
    # 定义输入输出
    input_shape = [1, 3, 4, 4]
    
    # Flatten后的输出形状计算
    # 展平后的维度数为：axis前维度保持不变，axis及之后维度相乘
    dim_before = 1
    for i in range(axis):
        dim_before *= input_shape[i]
    dim_after = 1
    for i in range(axis, len(input_shape)):
        dim_after *= input_shape[i]
    output_shape = [dim_before, dim_after]
    
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, output_shape)
    
    # 创建 Flatten 节点
    flatten_node = helper.make_node(
        'Flatten',  # 展平算子
        inputs=['X'],
        outputs=['Y'],
        name='flatten_node',
        axis=axis  # 指定从哪个维度开始展平
    )
    
    # 创建计算图
    graph = helper.make_graph(
        [flatten_node],
        'flatten_graph',
        [input_x],
        [output_y]
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='flatten-generator', output_path=output_path)

    logging.info(f"✓ Flatten 模型已保存: {output_path}")