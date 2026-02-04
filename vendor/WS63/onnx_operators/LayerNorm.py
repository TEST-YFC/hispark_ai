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


def create_layernorm_onnx_model(output_path, axis=-1, epsilon=1e-5, m=3, k=4):
    """创建LayerNormalization算子ONNX模型"""
    logging.info(f"创建LayerNormalization模型: {output_path}")
    
    # 输入定义 (假设输入形状为[M, K])
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, [m, k])
    # 可选的scale和bias输入（通常也使用）
    input_scale = helper.make_tensor_value_info('scale', TensorProto.FLOAT, [k])
    input_bias = helper.make_tensor_value_info('bias', TensorProto.FLOAT, [k])
    # 输出定义
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [m, k])
    
    # LayerNormalization节点
    layer_norm_node = helper.make_node(
        'LayerNormalization',
        inputs=['X', 'scale', 'bias'],
        outputs=['Y'],  # 只保留Y输出
        axis=axis,
        epsilon=epsilon,
        name='layer_norm_node'
    )
    
    # 创建计算图
    graph = helper.make_graph(
        [layer_norm_node],
        'layer_norm_graph',
        [input_x, input_scale, input_bias],  # 输入
        [output_y]  # 只输出Y
    )
    # 创建并保存模型
    model = create_low_ir_version_model(graph, producer_name='layer_norm-generator', output_path=output_path)
    logging.info(f"✓ LayerNormalization模型已保存: {output_path}")