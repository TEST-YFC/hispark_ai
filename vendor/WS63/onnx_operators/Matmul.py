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
from onnx import helper, TensorProto
from . import create_low_ir_version_model

def create_matmul_onnx_model(output_path):
    """创建Matmul算子ONNX模型"""
    print(f"创建Matmul模型: {output_path}")
    
    input_A = helper.make_tensor_value_info('A', TensorProto.FLOAT, [2, 3])
    input_B = helper.make_tensor_value_info('B', TensorProto.FLOAT, [3, 4])
    output_Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [2, 4])
    
    matmul_node = helper.make_node(
        'MatMul',
        inputs=['A', 'B'],
        outputs=['Y'],
        name='matmul_node'
    )
    
    graph = helper.make_graph(
        [matmul_node],
        'matmul_graph',
        [input_A, input_B],
        [output_Y]
    )
    
    model = create_low_ir_version_model(graph, producer_name='matmul-generator', output_path=output_path)
    print(f"✓ Matmul模型已保存: {output_path}")