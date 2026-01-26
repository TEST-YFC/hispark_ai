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
import onnx
from onnx import helper, TensorProto
from . import create_low_ir_version_model

def create_sub_onnx_model(output_path):
    """创建Sub算子ONNX模型"""
    print(f"创建Sub模型: {output_path}")
    
    input_A = helper.make_tensor_value_info('A', TensorProto.FLOAT, [2, 3])
    input_B = helper.make_tensor_value_info('B', TensorProto.FLOAT, [2, 3])
    output_C = helper.make_tensor_value_info('C', TensorProto.FLOAT, [2, 3])
    
    sub_node = helper.make_node(
        'Sub',
        inputs=['A', 'B'],
        outputs=['C'],
        name='sub_node'
    )
    
    graph = helper.make_graph(
        [sub_node],
        'sub_graph',
        [input_A, input_B],
        [output_C]
    )
    
    model = create_low_ir_version_model(graph, producer_name='sub-generator', output_path=output_path)
    onnx.save(model, output_path)
    print(f"✓ Sub模型已保存: {output_path}")
