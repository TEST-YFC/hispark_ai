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


def create_prelu_onnx_model(output_path):
    """Create PRelu ONNX model.

    Args:
        output_path: Model save path.
    """
    logging.info(f"Create PRelu model: {output_path}")

    input_shape = [1, 3, 4, 4]
    slope_shape = [3, 1, 1]

    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, input_shape)

    slope_const = helper.make_tensor(
        name='slope',
        data_type=TensorProto.FLOAT,
        dims=slope_shape,
        vals=[0.25, 0.5, 0.75]
    )

    prelu_node = helper.make_node(
        'PRelu',
        inputs=['X', 'slope'],
        outputs=['Y'],
        name='prelu_node'
    )

    graph = helper.make_graph(
        [prelu_node],
        'prelu_graph',
        [input_x],
        [output_y],
        initializer=[slope_const]
    )

    model = create_low_ir_version_model(graph, producer_name='prelu-generator', output_path=output_path)
    logging.info(f"PRelu ONNX model saved: {output_path}")
