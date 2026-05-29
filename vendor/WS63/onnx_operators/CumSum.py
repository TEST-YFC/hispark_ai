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


def create_cumsum_onnx_model(output_path):
    """Create CumSum ONNX model.

    Args:
        output_path: Model save path.
    """
    logging.info(f"Create CumSum model: {output_path}")

    input_shape = [2, 3, 4]

    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, input_shape)

    axis_const = helper.make_tensor(
        name='axis',
        data_type=TensorProto.INT32,
        dims=[],
        vals=[2]
    )

    cumsum_node = helper.make_node(
        'CumSum',
        inputs=['X', 'axis'],
        outputs=['Y'],
        name='cumsum_node'
    )

    graph = helper.make_graph(
        [cumsum_node],
        'cumsum_graph',
        [input_x],
        [output_y],
        initializer=[axis_const]
    )

    model = create_low_ir_version_model(graph, producer_name='cumsum-generator', output_path=output_path)
    logging.info(f"CumSum ONNX model saved: {output_path}")
