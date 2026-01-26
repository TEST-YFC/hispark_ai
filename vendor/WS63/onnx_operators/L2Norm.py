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


def create_l2norm_onnx_model(output_path, axis=-1, p=2, m=3, n=4):
    """创建L2Norm算子ONNX模型"""
    logging.info(f"创建L2Norm模型: {output_path}")
    
    # 输入张量 (可以是任意形状，这里使用M×N作为示例)
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, [m, n])
    # 输出张量 (与输入形状相同)
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [m, n])
    
    # 创建LpNormalization节点 (p=2即为L2Norm)
    l2norm_node = helper.make_node(
        'LpNormalization',
        inputs=['X'],
        outputs=['Y'],
        axis=axis,  # 沿哪个轴进行归一化，默认-1表示最后一个轴
        p=p,        # p=2表示L2范数
        name='l2norm_node'
    )
    
    graph = helper.make_graph(
        [l2norm_node],
        'l2norm_graph',
        [input_x],
        [output_y]
    )

    model = create_low_ir_version_model(graph, producer_name='l2norm-generator', output_path=output_path, opset_version=13)
    logging.info(f"✓ L2Norm模型已保存: {output_path}")
