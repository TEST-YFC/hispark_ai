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
import logging
from onnx import helper, TensorProto
from . import create_low_ir_version_model

logging.basicConfig(level=logging.NOTSET)


def create_pad_onnx_model(output_path, mode='constant'):
    """创建 Pad 算子 ONNX 模型
    
    Args:
        output_path: 模型保存路径
        mode: 填充模式 ('constant', 'reflect', 'edge')
    """
    logging.info(f"创建 Pad 模型: {output_path}")
    
    # 定义输入输出
    input_shape = [1, 3, 4, 4]
    output_shape = [1, 3, 6, 6]  # 假设每边填充1
    
    # 输入、输出和填充值描述
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, output_shape)
    
    # 填充参数 (ONNX格式: [dim1_begin, dim2_begin,..., dim1_end, dim2_end,...])
    pads = [0, 0, 1, 1, 0, 0, 1, 1]  # 对H和W维度各填充1
    
    # 创建常量节点
    pads_const = helper.make_tensor(
        name='pads',
        data_type=TensorProto.INT64,
        dims=[len(pads)],
        vals=pads
    )
    
    # 如果是constant模式，可以添加value参数
    value_const = helper.make_tensor(
        name='value',
        data_type=TensorProto.FLOAT,
        dims=[],
        vals=[0.0]  # 默认填充0
    )
    
    # 创建Pad节点
    pad_node = helper.make_node(
        'Pad',
        inputs=['X', 'pads', 'value'] if mode == 'constant' else ['X', 'pads'],
        outputs=['Y'],
        name='pad_node',
        mode=mode
    )
    
    # 创建计算图
    graph = helper.make_graph(
        [pad_node],
        'pad_graph',
        [input_x],
        [output_y],
        initializer=[pads_const, value_const] if mode == 'constant' else [pads_const]
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='pad-generator', output_path=output_path)
    logging.info(f"✓ Pad 模型已保存: {output_path}")