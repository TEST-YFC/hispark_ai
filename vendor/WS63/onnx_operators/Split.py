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

def create_split_onnx_model(output_path):
    """创建Split算子ONNX模型"""
    print(f"创建Split模型: {output_path}")
    
    input_X = helper.make_tensor_value_info('X', TensorProto.FLOAT, [6, 4])
    output_Y1 = helper.make_tensor_value_info('Y1', TensorProto.FLOAT, [2, 4])
    output_Y2 = helper.make_tensor_value_info('Y2', TensorProto.FLOAT, [2, 4])
    output_Y3 = helper.make_tensor_value_info('Y3', TensorProto.FLOAT, [2, 4])
    
    split_node = helper.make_node(
        'Split',
        inputs=['X'],
        outputs=['Y1', 'Y2', 'Y3'],
        axis=0,
        num_outputs=3,
        name='split_node'
    )
    
    graph = helper.make_graph(
        [split_node],
        'split_graph',
        [input_X],
        [output_Y1, output_Y2, output_Y3]
    )
    
    model = create_low_ir_version_model(graph, producer_name='split-generator', output_path=output_path)
    print(f"✓ Split模型已保存: {output_path}")