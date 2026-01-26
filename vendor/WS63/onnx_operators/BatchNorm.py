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


def create_batchnorm_onnx_model(output_path):
    """创建 BatchNorm 算子 ONNX 模型
    
    Args:
        output_path: 模型保存路径
    """
    logging.info(f"创建 BatchNorm 模型: {output_path}")
    
    # 定义输入输出 (BatchNorm 需要输入、scale、bias、mean、var 5个输入)
    input_shape = [1, 3, 4, 4]
    output_shape = input_shape
    param_shape = [3]  # C维度
    
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    input_scale = helper.make_tensor_value_info('scale', TensorProto.FLOAT, param_shape)
    input_bias = helper.make_tensor_value_info('bias', TensorProto.FLOAT, param_shape)
    input_mean = helper.make_tensor_value_info('mean', TensorProto.FLOAT, param_shape)
    input_var = helper.make_tensor_value_info('var', TensorProto.FLOAT, param_shape)
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, output_shape)
    
    # 创建 BatchNorm 节点
    batchnorm_node = helper.make_node(
        'BatchNormalization',
        inputs=['X', 'scale', 'bias', 'mean', 'var'],
        outputs=['Y'],
        name='batchnorm_node',
        epsilon=1e-5  # 防止除零的小常数
    )
    
    # 创建计算图
    graph = helper.make_graph(
        [batchnorm_node],
        'batchnorm_graph',
        [input_x, input_scale, input_bias, input_mean, input_var],
        [output_y]
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='batchnorm-generator', output_path=output_path)
    logging.info(f"✓ BatchNorm 模型已保存: {output_path}")