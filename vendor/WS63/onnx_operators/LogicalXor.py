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
from onnx import helper, TensorProto
from . import create_low_ir_version_model

logging.basicConfig(level=logging.NOTSET)


def create_logicalxor_onnx_model(output_path):
    """创建 LogicalXor 算子 ONNX 模型
    
    Args:
        output_path: 模型保存路径
    """
    logging.info(f"创建 LogicalXor 模型: {output_path}")
    
    # 定义输入输出
    input_A = helper.make_tensor_value_info('A', TensorProto.BOOL, [2, 3])
    input_B = helper.make_tensor_value_info('B', TensorProto.BOOL, [2, 3])
    output_C = helper.make_tensor_value_info('C', TensorProto.BOOL, [2, 3])
    
    # 创建 LogicalXor 节点
    logicalxor_node = helper.make_node(
        'Xor',
        inputs=['A', 'B'],
        outputs=['C'],
        name='logicalxor_node'
    )
    
    # 创建计算图
    graph = helper.make_graph(
        [logicalxor_node],
        'logicalxor_graph',
        [input_A, input_B],
        [output_C]
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='logicalxor-generator', output_path=output_path)
    logging.info(f"✓ LogicalXor 模型已保存: {output_path}")
