# Copyright (c) 2025-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from onnx import helper, TensorProto
import numpy as np
from . import create_low_ir_version_model

logging.basicConfig(level=logging.NOTSET)


def create_transpose_onnx_model(output_path):
    """Create ONNX model with Conv2D + Transpose + Add operators.
    
    Flow: X -> Conv2D -> Transpose -> Add -> Y
    
    Args:
        output_path: Path to save the generated ONNX model
    """
    # 定义维度参数
    input_shape = [1, 1, 5, 5]  # [N, C, H, W]
    conv_output_shape = [1, 1, 3, 3]  # Conv输出形状
    perm = [0, 2, 3, 1]  # Transpose permutation: [N, H, W, C]
    transpose_output_shape = [conv_output_shape[p] for p in perm]  # [1, 3, 3, 1]
    add_constant_shape = transpose_output_shape  # Add的第二个输入形状相同
    
    logging.info(f"Creating Conv2D + Transpose + Add model")
    logging.info(f"  Input shape: {input_shape}")
    logging.info(f"  Conv output shape: {conv_output_shape}")
    logging.info(f"  Permutation: {perm}")
    logging.info(f"  Transpose output shape: {transpose_output_shape}")
    logging.info(f"  Saving to: {output_path}")
    
    try:
        # 定义输入和输出
        input_X = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
        output_Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, transpose_output_shape)
        
        # 1. 创建Conv的权重张量W（全1的3x3卷积核）
        W_data = np.ones((1, 1, 3, 3), dtype=np.float32)  # [out_channels, in_channels, height, width]
        W_tensor = helper.make_tensor(
            name='W',
            data_type=TensorProto.FLOAT,
            dims=[1, 1, 3, 3],
            vals=W_data.flatten().tolist()
        )
        
        # 2. 创建Add的常量张量（全0.5的偏置）
        add_const_data = np.full(transpose_output_shape, 0.5, dtype=np.float32)
        add_const_tensor = helper.make_tensor(
            name='Add_Constant',
            data_type=TensorProto.FLOAT,
            dims=transpose_output_shape,
            vals=add_const_data.flatten().tolist()
        )
        
        # 创建节点
        # 节点1: Constant初始化卷积权重
        w_initializer = helper.make_node(
            'Constant',
            inputs=[],
            outputs=['W'],
            value=W_tensor,
            name='W_Initializer'
        )
        
        # 节点2: Conv2D算子
        conv_node = helper.make_node(
            'Conv',
            inputs=['X', 'W'],
            outputs=['Conv_Out'],
            name='Conv_Node',
            kernel_shape=[3, 3],
            strides=[1, 1],
            pads=[0, 0, 0, 0],  # 无padding，输出3x3
            dilations=[1, 1],
            group=1
        )
        
        # 节点3: Transpose算子
        transpose_node = helper.make_node(
            'Transpose',
            inputs=['Conv_Out'],
            outputs=['Transpose_Out'],
            name='Transpose_Node',
            perm=perm
        )
        
        # 节点4: Constant初始化Add的常量
        add_initializer = helper.make_node(
            'Constant',
            inputs=[],
            outputs=['Add_Const'],
            value=add_const_tensor,
            name='Add_Constant_Initializer'
        )
        
        # 节点5: Add算子
        add_node = helper.make_node(
            'Add',
            inputs=['Transpose_Out', 'Add_Const'],
            outputs=['Y'],
            name='Add_Node'
        )
        
        # 创建图（注意节点顺序）
        graph = helper.make_graph(
            nodes=[w_initializer, conv_node, transpose_node, add_initializer, add_node],
            name='Conv_Transpose_Add_Graph',
            inputs=[input_X],
            outputs=[output_Y],
            # 可以添加initializer列表作为额外信息
            initializer=[W_tensor, add_const_tensor]
        )
        
        # 创建模型
        model = create_low_ir_version_model(
            graph,
            producer_name='conv-transpose-add-generator',
            output_path=output_path
        )
        
        logging.info(f"✓ Successfully created Conv2D+Transpose+Add ONNX model at: {output_path}")
        
        # 打印模型计算流程
        print("\n" + "="*50)
        print("Model computation flow:")
        print("="*50)
        print(f"Input X: {input_shape}")
        print(f"  ↓ Conv2D (3x3 kernel, stride=1, no padding)")
        print(f"Conv_Out: {conv_output_shape}")
        print(f"  ↓ Transpose (perm={perm})")
        print(f"Transpose_Out: {transpose_output_shape}")
        print(f"  ↓ Add (+ constant 0.5)")
        print(f"Output Y: {transpose_output_shape}")
        print("="*50 + "\n")
        
        return model
        
    except Exception as e:
        logging.error(f"Failed to create Conv2D+Transpose+Add model: {str(e)}")
        raise