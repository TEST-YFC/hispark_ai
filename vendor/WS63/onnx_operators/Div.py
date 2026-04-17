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
from onnx import helper, TensorProto
from . import create_low_ir_version_model


def create_div_onnx_model(output_path, input_n=3, input_d=6):
    """创建DIV算子ONNX模型"""    
    input1_tensor = helper.make_tensor_value_info("input1", TensorProto.FLOAT, [input_n, input_d])
    input2_tensor = helper.make_tensor_value_info("input2", TensorProto.FLOAT, [input_n, input_d])
    output_tensor = helper.make_tensor_value_info("output", TensorProto.FLOAT, [input_n, input_d])
    
    div_node = helper.make_node(
        "Div",
        inputs=["input1", "input2"],
        outputs=["output"]
    )

    graph = helper.make_graph(
        nodes=[div_node],
        name="div_graph",
        inputs=[input1_tensor, input2_tensor],
        outputs=[output_tensor]
    )

    model = create_low_ir_version_model(graph, producer_name='div-generator', output_path=output_path)