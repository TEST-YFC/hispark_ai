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
from onnx import helper, TensorProto, numpy_helper
import numpy as np
from . import create_low_ir_version_model

logging.basicConfig(level=logging.NOTSET)


def create_mathmodel_onnx_model(output_path):
    """
    修复 Reshape 错误版本
    """
    logging.info(f"创建数学运算类模型: {output_path}")
    
    # 定义输入
    input_shape = [1, 4, 4]
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    input_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, input_shape)
    
    # 1. 处理 X
    reshape_to_2d_shape = helper.make_tensor(
        'reshape_to_2d_shape',
        TensorProto.INT64,
        [2],
        [4, 4]
    )
    
    reshape_to_2d_node = helper.make_node(
        'Reshape',
        inputs=['X', 'reshape_to_2d_shape'],
        outputs=['reshape_to_2d_out']
    )
    
    # 2. Gemm
    gemm_weight = helper.make_tensor(
        'gemm_weight',
        TensorProto.FLOAT,
        [4, 4],
        np.random.randn(4, 4).astype(np.float32).flatten().tolist()
    )
    
    gemm_bias = helper.make_tensor(
        'gemm_bias',
        TensorProto.FLOAT,
        [4],
        np.random.randn(4).astype(np.float32).tolist()
    )
    
    gemm_node = helper.make_node(
        'Gemm',
        inputs=['reshape_to_2d_out', 'gemm_weight', 'gemm_bias'],
        outputs=['gemm_out'],
        alpha=1.0,
        beta=1.0,
        transA=0,
        transB=0
    )
    
    # 3. 恢复为 3D
    reshape_to_3d_shape = helper.make_tensor(
        'reshape_to_3d_shape',
        TensorProto.INT64,
        [3],
        [1, 4, 4]
    )
    
    reshape_to_3d_node = helper.make_node(
        'Reshape',
        inputs=['gemm_out', 'reshape_to_3d_shape'],
        outputs=['gemm_3d_out']
    )
    
    # 4. MatMul
    matmul_weight = helper.make_tensor(
        'matmul_weight',
        TensorProto.FLOAT,
        [4, 4],
        np.random.randn(4, 4).astype(np.float32).flatten().tolist()
    )
    
    matmul_node = helper.make_node(
        'MatMul',
        inputs=['gemm_3d_out', 'matmul_weight'],
        outputs=['matmul_out']  # 形状保持为 [1, 4, 4]
    )
    
    # 5. 一系列激活函数
    relu_node = helper.make_node('Relu', inputs=['matmul_out'], outputs=['relu_out'])
    tanh_node = helper.make_node('Tanh', inputs=['relu_out'], outputs=['tanh_out'])
    sigmoid_node = helper.make_node('Sigmoid', inputs=['tanh_out'], outputs=['sigmoid_out'])
    
    # 6. Softmax
    softmax_node = helper.make_node(
        'Softmax',
        inputs=['sigmoid_out'],
        outputs=['softmax_out'],
        axis=2
    )
    
    # 7. Add
    add_node = helper.make_node(
        'Add',
        inputs=['softmax_out', 'Y'],
        outputs=['add_out']
    )
    
    # 8. Sub
    sub_node = helper.make_node(
        'Sub',
        inputs=['add_out', 'Y'],
        outputs=['sub_out']
    )
    
    # 9. Mul
    mul_node = helper.make_node(
        'Mul',
        inputs=['sub_out', 'Y'],
        outputs=['mul_out']
    )
    
    # 10. 一系列数学运算
    abs_node = helper.make_node('Abs', inputs=['mul_out'], outputs=['abs_out'])
    cos_node = helper.make_node('Cos', inputs=['abs_out'], outputs=['cos_out'])
    sin_node = helper.make_node('Sin', inputs=['cos_out'], outputs=['sin_out'])
    exp_node = helper.make_node('Exp', inputs=['sin_out'], outputs=['exp_out'])
    log_node = helper.make_node('Log', inputs=['exp_out'], outputs=['log_out'])
    sqrt_node = helper.make_node('Sqrt', inputs=['log_out'], outputs=['sqrt_out'])
    floor_node = helper.make_node('Floor', inputs=['sqrt_out'], outputs=['floor_out'])
    ceil_node = helper.make_node('Ceil', inputs=['floor_out'], outputs=['ceil_out'])
    round_node = helper.make_node('Round', inputs=['ceil_out'], outputs=['round_out'])
    
    # 11. Reshape 到 [1, 16]
    final_reshape_shape = helper.make_tensor(
        'final_reshape_shape',
        TensorProto.INT64,
        [2],
        [1, 16]
    )
    
    final_reshape_node = helper.make_node(
        'Reshape',
        inputs=['round_out', 'final_reshape_shape'],
        outputs=['final_reshape_out']
    )
    
    # 12. Flatten
    flatten_node = helper.make_node(
        'Flatten',
        inputs=['final_reshape_out'],
        outputs=['Z'],
        axis=1
    )
    
    graph = helper.make_graph(
        [
            reshape_to_2d_node, gemm_node, reshape_to_3d_node,
            matmul_node, relu_node, tanh_node, sigmoid_node,
            softmax_node, add_node, sub_node, mul_node,
            abs_node, cos_node, sin_node, exp_node, log_node,
            sqrt_node, floor_node, ceil_node, round_node,
            final_reshape_node, flatten_node
        ],
        'math_ops_graph',
        [input_x, input_y],
        [helper.make_tensor_value_info('Z', TensorProto.FLOAT, [1, 16])],
        initializer=[
            reshape_to_2d_shape, gemm_weight, gemm_bias, 
            reshape_to_3d_shape, matmul_weight,
            final_reshape_shape
        ]
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='math-ops-generator', output_path=output_path)
    logging.info(f"✓ 数学运算类模型已保存: {output_path}")