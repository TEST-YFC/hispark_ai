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


def create_sqrt_onnx_model(output_path):
    """创建 Sqrt 算子 ONNX 模型
    
    Args:
        output_path: 模型保存路径
    """
    logging.info(f"创建 Sqrt 模型: {output_path}")
    
    # 定义输入输出（保持和之前相同的形状）
    input_shape = [1, 3, 4, 4]
    output_shape = input_shape
    
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, output_shape)
    
    # 创建 Sqrt 节点
    sqrt_node = helper.make_node(
        'Sqrt',  # 平方根算子
        inputs=['X'],
        outputs=['Y'],
        name='sqrt_node'
    )
    
    # 创建计算图
    graph = helper.make_graph(
        [sqrt_node],
        'sqrt_graph',
        [input_x],
        [output_y]
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='sqrt-generator', output_path=output_path)

    logging.info(f"✓ Sqrt 模型已保存: {output_path}")
