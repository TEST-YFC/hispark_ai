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

def create_softmax_onnx_model(output_path):
    """创建Softmax算子ONNX模型"""
    print(f"创建Softmax模型: {output_path}")
    
    input_X = helper.make_tensor_value_info('X', TensorProto.FLOAT, [2, 3])
    output_Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [2, 3])
    
    softmax_node = helper.make_node(
        'Softmax',
        inputs=['X'],
        outputs=['Y'],
        axis=1,
        name='softmax_node'
    )
    
    graph = helper.make_graph(
        [softmax_node],
        'softmax_graph',
        [input_X],
        [output_Y]
    )
    
    model = create_low_ir_version_model(graph, producer_name='softmax-generator', output_path=output_path)
    print(f"✓ Softmax模型已保存: {output_path}")