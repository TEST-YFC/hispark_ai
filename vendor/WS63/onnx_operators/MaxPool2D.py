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
from onnx import helper, TensorProto
from . import create_low_ir_version_model

def create_maxpool2d_onnx_model(output_path):
    """创建MaxPool2D算子ONNX模型"""
    print(f"创建MaxPool2D模型: {output_path}")
    
    input_X = helper.make_tensor_value_info('X', TensorProto.FLOAT, [1, 1, 5, 5])
    output_Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [1, 1, 3, 3])
    
    maxpool_node = helper.make_node(
        'MaxPool',
        inputs=['X'],
        outputs=['Y'],
        kernel_shape=[3, 3],
        strides=[1, 1],
        name='maxpool2d_node'
    )
    
    graph = helper.make_graph(
        [maxpool_node],
        'maxpool2d_graph',
        [input_X],
        [output_Y]
    )
    
    model = create_low_ir_version_model(graph, producer_name='maxpool2d-generator', output_path=output_path)
    print(f"✓ MaxPool2D模型已保存: {output_path}")