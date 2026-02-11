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
from . import create_low_ir_version_model

logging.basicConfig(level=logging.NOTSET)


def create_transpose_onnx_model(output_path):
    """Create ONNX model with Transpose operator.
    
    Args:
        output_path: Path to save the generated ONNX model
    """
    input_shape = [1, 3, 4, 4]
    perm = [0, 2, 3, 1]
    logging.info(f"Creating Transpose model with shape {input_shape} and permutation {perm}, saving to: {output_path}")
    
    try:
        # Calculate output shape based on input shape and permutation
        output_shape = [input_shape[p] for p in perm]
        
        # Input/Output tensor info
        input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
        output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, output_shape)
        
        # Create Transpose node with permutation attribute
        transpose_node = helper.make_node(
            'Transpose',
            inputs=['X'],
            outputs=['Y'],
            name='Transpose_Node',
            perm=perm
        )
        
        # Create the graph
        graph = helper.make_graph(
            nodes=[transpose_node],
            name='Transpose_Graph',
            inputs=[input_x],
            outputs=[output_y],
        )
        
        # Create the model
        model = create_low_ir_version_model(
            graph,
            producer_name='transpose-model-generator',
            output_path=output_path
        )
        
        logging.info(f"✓ Successfully created Transpose ONNX model at: {output_path}")
        return model
        
    except Exception as e:
        logging.error(f"Failed to create Transpose model: {str(e)}")
        raise