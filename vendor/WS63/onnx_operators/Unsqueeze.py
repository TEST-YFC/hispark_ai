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
import logging
from onnx import helper, TensorProto
from . import create_low_ir_version_model

logging.basicConfig(level=logging.NOTSET)


def create_unsqueeze_onnx_model(output_path, axes=None):
    """创建 Unsqueeze 算子 ONNX 模型
    
    Args:
        output_path: 模型保存路径
        axes: 要扩展的维度列表(可选)，如果不指定则必须作为输入提供
    """
    logging.info(f"创建 Unsqueeze 模型: {output_path}")
    
    # 输入形状为 [1, 3, 5] 
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, [1, 3, 5])
    # 输出形状变为 [1, 3, 1, 5]（在第2维度上扩展）
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [1, 3, 1, 5])  
    # 创建axes参数，指定在第2个维度（索引=2）上扩展
    axes = helper.make_tensor(
        name='axes',
        data_type=TensorProto.INT64,
        dims=[1],  # 扩展1个维度
        vals=[2]   # 指定要扩展的维度位置（在第2个位置插入新维度）
    )
    
    unsqueeze_node = helper.make_node(
        'Unsqueeze',
        inputs=['X', 'axes'],
        outputs=['Y'],
        name='unsqueeze_node'
    )
    
    # 创建包含初始值的图（axes作为初始值）
    graph = helper.make_graph(
        [unsqueeze_node],
        'unsqueeze_graph',
        [input_x],
        [output_y],
        initializer=[axes]  # 将axes作为初始值添加到图中
    )
    
    model = create_low_ir_version_model(graph, producer_name='unsqueeze-generator', output_path=output_path)
    logging.info(f"✓ Unsqueeze 模型已保存: {output_path}")
