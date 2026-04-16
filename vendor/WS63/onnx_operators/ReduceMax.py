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


def create_reducemax_onnx_model(output_path):
    """
    创建 ReduceMax ONNX 模型

    Args:
        output_path: 模型保存路径
        input_shape: 输入 shape
        axes: reduce 轴
        keepdims: 是否保持维度
    """
    logging.info(f"创建 ReduceMax 模型: {output_path}")
    
    # 定义输入输出
    input_shape = [1, 3, 4, 4]
    output_shape = [1, 1, 4, 4]  # 对axes=1进行ReduceMax计算
    
    # 输入、输出描述
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, output_shape)

    # 创建常量axes节点
    axes_tensor = helper.make_tensor(
        name='axes',
        data_type=TensorProto.INT64,
        dims=[1],
        vals=[1]
    )
    
    # 创建ReduceMax节点
    reducemax_node = helper.make_node(
        "ReduceMax",
        inputs=["X", "axes"],
        outputs=["Y"],
        name="reducemax_node",
        keepdims=1,
        noop_with_empty_axes=0
    )
    
    # 创建计算图
    graph = helper.make_graph(
        [reducemax_node],
        "reducemax_graph",
        [input_x],
        [output_y],
        initializer=[axes_tensor]
    )

    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='reducemax-generator', output_path=output_path)
    logging.info(f"✓ ReduceMax 模型已保存: {output_path}")