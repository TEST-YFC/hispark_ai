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


def create_tile_onnx_model(output_path):
    """创建 Tile 算子 ONNX 模型
    
    Args:
        output_path: 模型保存路径
    """
    logging.info(f"创建 Tile 模型: {output_path}")
    
    # 定义输入输出
    input_shape = [1, 3, 4, 4]  # 输入张量形状
    repeats = [1, 2, 3, 1]      # 各维度重复次数
    output_shape = [input_shape[i] * repeats[i] for i in range(len(input_shape))]
    
    # 输入输出描述
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, output_shape)
    
    # 创建重复次数的常量节点
    repeats_const = helper.make_tensor(
        name='repeats',
        data_type=TensorProto.INT64,
        dims=[len(repeats)],
        vals=repeats
    )
    
    # 创建Tile节点
    tile_node = helper.make_node(
        'Tile',
        inputs=['X', 'repeats'],
        outputs=['Y'],
        name='tile_node'
    )
    
    # 创建计算图
    graph = helper.make_graph(
        [tile_node],
        'tile_graph',
        [input_x],
        [output_y],
        initializer=[repeats_const]
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='tile-generator', output_path=output_path)
    logging.info(f"✓ Tile ONNX 模型已保存: {output_path}")