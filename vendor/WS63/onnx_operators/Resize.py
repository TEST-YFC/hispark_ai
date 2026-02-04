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
import numpy
from onnx import helper, TensorProto
from onnx import numpy_helper
from . import create_low_ir_version_model

logging.basicConfig(level=logging.NOTSET)


def create_resize_onnx_model(output_path, mode='nearest'):
    """创建 Resize 算子 ONNX 模型
    
    Args:
        output_path: 模型保存路径
        mode: 插值模式 ('nearest' 或 'linear')
    """
    logging.info(f"创建 Resize 模型: {output_path}")
    
    # 定义输入输出（使用固定尺寸）
    input_shape = [1, 3, 4, 4]  # 固定输入尺寸 4x4
    output_shape = [1, 3, 8, 8]  # 固定输出尺寸 8x8
    
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    output_y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, output_shape)
    
    sizes = numpy.array(output_shape, dtype=numpy.int64)  # 必须是 int64 类型
    sizes_tensor = helper.make_tensor(
        name='sizes',
        data_type=TensorProto.INT64,
        dims=sizes.shape,
        vals=sizes.flatten().tolist()
    )
    
    # 创建 Resize 节点
    resize_node = helper.make_node(
        'Resize',
        inputs=['X', '', '', 'sizes'],  # roi 和 scales 留空，使用 sizes
        outputs=['Y'],
        name='resize_node',
        mode=mode,
        coordinate_transformation_mode='asymmetric',
        nearest_mode='floor'  # 仅 nearest 模式需要
    )
    
    # 创建初始值（仅 sizes）
    initializer = [sizes_tensor]
    
    # 创建计算图
    graph = helper.make_graph(
        [resize_node],
        'resize_graph',
        [input_x],
        [output_y],
        initializer=initializer
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='resize-generator', output_path=output_path)

    logging.info(f"✓ Resize 模型已保存: {output_path}")
