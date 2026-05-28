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


def create_hardswish_onnx_model(output_path):
    """Create ONNX model with HardSwish operator.

    HardSwish(x) = x * clamp(x + 3, 0, 6) / 6  (ONNX opset 14+)

    Args:
        output_path: Path to save the generated ONNX model
    """
    input_shape = [1, 3, 4, 4]

    logging.info(f"Creating HardSwish model with shape {input_shape}, saving to: {output_path}")

    try:
        input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
        output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, input_shape)

        node = helper.make_node(
            'HardSwish',
            inputs=['X'],
            outputs=['Y'],
            name='HardSwish_Node',
        )

        graph = helper.make_graph(
            nodes=[node],
            name='HardSwish_Graph',
            inputs=[input_x],
            outputs=[output_y],
        )

        model = create_low_ir_version_model(
            graph,
            producer_name='hardswish-model-generator',
            output_path=output_path
        )

        logging.info(f"✓ Successfully created HardSwish ONNX model at: {output_path}")
        return model

    except Exception as e:
        logging.error(f"Failed to create HardSwish model: {str(e)}")
        raise
