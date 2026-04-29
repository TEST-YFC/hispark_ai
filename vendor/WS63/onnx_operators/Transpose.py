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
    """Create ONNX model with Conv2D + Transpose + Add operators"""
    # Define shapes and constants
    input_shape = [1, 1, 5, 5]
    conv_output_shape = [1, 1, 3, 3]
    perm = [0, 2, 3, 1]
    transpose_output_shape = [conv_output_shape[p] for p in perm]
    
    # Create tensors
    w_tensor = helper.make_tensor('W', TensorProto.FLOAT, [1, 1, 3, 3], np.ones(9).tolist())
    add_const_tensor = helper.make_tensor('Add_Constant', TensorProto.FLOAT, transpose_output_shape, 
                                         np.full(9, 0.5).tolist())

    # Create nodes
    nodes = [
        helper.make_node('Conv', ['X', 'W'], ['Conv_Out'], name='Conv_Node',
                        kernel_shape=[3, 3], strides=[1, 1], pads=[0, 0, 0, 0]),
        helper.make_node('Transpose', ['Conv_Out'], ['Transpose_Out'], name='Transpose_Node', perm=perm),
        helper.make_node('Add', ['Transpose_Out', 'Add_Constant'], ['Y'], name='Add_Node')
    ]

    # Create and save model
    graph = helper.make_graph(
        nodes, 'Conv_Transpose_Add_Graph',
        [helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)],
        [helper.make_tensor_value_info('Y', TensorProto.FLOAT, transpose_output_shape)],
        initializer=[w_tensor, add_const_tensor]
    )
    
    model = create_low_ir_version_model(graph, producer_name='conv-transpose-add-generator',
        output_path=output_path)
    logging.info(f"✓ Model created at: {output_path}")
    return model