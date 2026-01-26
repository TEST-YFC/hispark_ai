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

def create_avgpool1d_onnx_model(output_path):
    """创建AvgPool1D算子ONNX模型"""
    print(f"创建AvgPool1D模型: {output_path}")
    
    # 定义输入输出 (1D池化，输入形状为 [N, C, L])
    input_X = helper.make_tensor_value_info('X', TensorProto.FLOAT, [1, 1, 5])
    output_Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [1, 1, 3])
    
    # 创建AvgPool节点
    avgpool_node = helper.make_node(
        'AveragePool',
        inputs=['X'],
        outputs=['Y'],
        kernel_shape=[3],
        strides=[1],
        name='avgpool1d_node'
    )
    
    graph = helper.make_graph(
        [avgpool_node],
        'avgpool1d_graph',
        [input_X],
        [output_Y]
    )
    
    model = create_low_ir_version_model(graph, producer_name='avgpool1d-generator', output_path=output_path)
    print(f"✓ AvgPool1D模型已保存: {output_path}")