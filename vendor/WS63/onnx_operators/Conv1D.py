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
import numpy as np
from onnx import helper, TensorProto, numpy_helper
from . import create_low_ir_version_model

def create_conv1d_onnx_model(output_path):
    """创建兼容 MindSpore Lite 的 Conv1D 模型（权重扩展为 4D）"""
    print(f"创建兼容 MindSpore Lite 的 Conv1D 模型: {output_path}")
    # 输入形状 [N, C, 1, L]（兼容 Conv2D）
    input_X = helper.make_tensor_value_info('X', TensorProto.FLOAT, [1, 1, 1, 5])
    
    # 权重形状 [C_out, C_in, 1, kernel_size]（兼容 Conv2D）
    weights_data = np.random.randn(1, 1, 1, 3).astype(np.float32)  # 随机初始化权重
    tensor_W = numpy_helper.from_array(weights_data, name='W')  # 创建 initializer
    output_Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [1, 1, 1, 3])
    # 关键修改：kernel_shape 改为 [1, 3]（兼容 Conv2D）
    conv_node = helper.make_node(
        'Conv',
        inputs=['X', 'W'],  # W 是 initializer，不是输入
        outputs=['Y'],
        kernel_shape=[1, 3],  # 1D Conv 模拟为 2D Conv
        strides=[1, 1],
        dilations=[1, 1],
        name='conv1d_node'
    )
    graph = helper.make_graph(
        [conv_node],
        'conv1d_graph',
        [input_X],  # 输入只有 X，W 是 initializer，不在 inputs 里
        [output_Y],
        initializer=[tensor_W]  # 将 W 添加为 initializer
    )
    model = create_low_ir_version_model(graph, producer_name='conv1d-generator', output_path=output_path)
    print(f"✓ 兼容 MindSpore Lite 的 Conv1D 模型已保存: {output_path}")