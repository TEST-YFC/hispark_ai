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
import numpy as np
from onnx import helper, TensorProto
from . import create_low_ir_version_model

def create_conv2d_onnx_model(output_path):
    """创建Conv2D算子ONNX模型"""
    print(f"创建Conv2D模型: {output_path}")
    
    # 定义输入和输出
    input_X = helper.make_tensor_value_info('X', TensorProto.FLOAT, [1, 1, 5, 5])
    output_Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [1, 1, 3, 3])
    
    # 创建权重张量W并初始化（这里使用全1作为示例）
    W_data = np.ones((1, 1, 3, 3), dtype=np.float32)
    W_tensor = helper.make_tensor(
        name='W',
        data_type=TensorProto.FLOAT,
        dims=[1, 1, 3, 3],
        vals=W_data.flatten().tolist()
    )
    
    # 创建Conv节点
    conv_node = helper.make_node(
        'Conv',
        inputs=['X', 'W'],
        outputs=['Y'],
        kernel_shape=[3, 3],
        strides=[1, 1],
        name='conv2d_node'
    )
    
    # 创建初始值节点
    W_initializer = helper.make_node(
        'Constant',
        inputs=[],
        outputs=['W'],
        value=W_tensor,
        name='W_initializer'
    )
    
    graph = helper.make_graph(
        [W_initializer, conv_node],  # 注意顺序：初始值节点在前
        'conv2d_graph',
        [input_X],  # 现在只有X是输入，W是常量
        [output_Y]
    )
    
    model = create_low_ir_version_model(graph, producer_name='conv2d-generator', output_path=output_path)
    print(f"✓ Conv2D模型已保存: {output_path}")