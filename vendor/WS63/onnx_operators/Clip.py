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


def create_clip_onnx_model(output_path):
    """创建 Clip 算子 ONNX 模型
    
    Args:
        output_path: 模型保存路径
    """
    # 定义输入输出
    input_shape = [9, 10]
    input_tensor_info = helper.make_tensor_value_info(
        name='input',
        elem_type=TensorProto.FLOAT,
        shape=input_shape
    )

    output_tensor_info = helper.make_tensor_value_info(
        name='output',
        elem_type=TensorProto.FLOAT,
        shape=input_shape
    )

    min_val_data = [-5.0]
    min_tensor = helper.make_tensor(
        name='min_const',
        data_type=TensorProto.FLOAT,
        dims=[1], 
        vals=min_val_data
    )

    max_val_data = [5.0]
    max_tensor = helper.make_tensor(
        name='max_const',
        data_type=TensorProto.FLOAT,
        dims=[1], 
        vals=max_val_data
    )

    # 创建 Clip 节点
    clip_node = helper.make_node(
        op_type='Clip',
        inputs=['input', 'max_const', 'min_const'],
        outputs=['output'],
        name='clip_node_0'
    )

    # 创建计算图
    graph = helper.make_graph(
        nodes=[clip_node],
        name='Clip_Graph',
        inputs=[input_tensor_info],
        outputs=[output_tensor_info],
        initializer=[min_tensor, max_tensor]
    )

    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='ceil-generator', output_path=output_path)

    logging.info(f"✓ Ceil 模型已保存: {output_path}")