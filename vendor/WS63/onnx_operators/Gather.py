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

def create_gather_onnx_model(output_path):
    """创建Gather算子ONNX模型（indices 改为常量）"""
    print(f"创建Gather模型: {output_path}")
    
    input_data = helper.make_tensor_value_info('data', TensorProto.FLOAT, [3, 4])
    output_output = helper.make_tensor_value_info('output', TensorProto.FLOAT, [2, 4])
    indices_data = np.array([0, 2], dtype=np.int64)  # 必须是 INT64 类型
    indices_tensor = helper.make_tensor(
        name='const_indices',
        data_type=TensorProto.INT64,
        dims=indices_data.shape,
        vals=indices_data.flatten().tolist()
    )
    const_indices_node = helper.make_node(
        'Constant',
        inputs=[],
        outputs=['const_indices'],
        value=indices_tensor,
        name='const_indices_node'
    )
    gather_node = helper.make_node(
        'Gather',
        inputs=['data', 'const_indices'],  # 使用 const_indices 而不是 input_indices
        outputs=['output'],
        axis=0,
        name='gather_node'
    )
    graph = helper.make_graph(
        [const_indices_node, gather_node],  # 包含常量节点
        'gather_graph',
        [input_data],  # 只有 data 是输入
        [output_output]
    )
    model = create_low_ir_version_model(graph, producer_name='gather-generator', output_path=output_path)
    print(f"✓ Gather模型已保存: {output_path}")