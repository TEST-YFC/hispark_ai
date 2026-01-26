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


def create_squeeze_onnx_model(output_path, axes=None):
    """创建 Squze 算子 ONNX 模型
    
    Args:
        output_path: 模型保存路径
        axes: 要压缩的维度列表(可选)，如果不指定则压缩所有长度为1的维度
    """
    logging.info(f"创建 Squeeze 模型: {output_path}")
    
    # 输入形状为 [1, 3, 1, 5] (第0和第2维度为1)
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, [1, 3, 1, 5])
    # 输出形状变为 [1, 3, 5]（仅压缩第2个维度）
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [1, 3, 5])  
    # 创建axes参数，仅压缩第2个维度（索引=2）
    axes = helper.make_tensor(
        name='axes',
        data_type=TensorProto.INT64,
        dims=[1],  # 仅压缩1个维度
        vals=[2]   # 指定要压缩的维度索引（第2个维度）
    )
    
    squeeze_node = helper.make_node(
        'Squeeze',
        inputs=['X', 'axes'],
        outputs=['Y'],
        name='squeeze_node'
    )
    
    # 创建包含初始值的图（axes作为初始值）
    graph = helper.make_graph(
        [squeeze_node],
        'squeeze_graph',
        [input_x],
        [output_y],
        initializer=[axes]  # 将axes作为初始值添加到图中
    )
    
    model = create_low_ir_version_model(graph, producer_name='squeeze-generator', output_path=output_path)
    logging.info(f"✓ Squeeze 模型已保存: {output_path}")
