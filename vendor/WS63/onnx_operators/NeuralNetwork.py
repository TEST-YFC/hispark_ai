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
from onnx import helper, TensorProto, numpy_helper
import numpy as np
from . import create_low_ir_version_model

logging.basicConfig(level=logging.NOTSET)


def create_neuralnetwork_model(output_path):
    """
    Conv, InstanceNormalization, MaxPool, AveragePool, Resize, Pad
    LSTM
    Reshape、Flatten、Squeeze、Unsqueeze、Tile、Concat、Split、Gather
    """
    logging.info(f"创建卷积池化类模型: {output_path}")
    
    # 第一个分支：2D卷积处理路径
    # 定义输入
    input_shape = [1, 3, 32, 32]
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    
    # 1. Conv 2D
    conv_weight = helper.make_tensor(
        'conv_weight',
        TensorProto.FLOAT,
        [16, 3, 3, 3],  # [output_channels, input_channels, height, width]
        np.random.randn(16, 3, 3, 3).astype(np.float32).flatten().tolist()
    )
    
    conv_bias = helper.make_tensor(
        'conv_bias',
        TensorProto.FLOAT,
        [16],
        np.random.randn(16).astype(np.float32).tolist()
    )
    
    conv_node = helper.make_node(
        'Conv',
        inputs=['X', 'conv_weight', 'conv_bias'],
        outputs=['conv_out'],
        kernel_shape=[3, 3],
        pads=[1, 1, 1, 1],
        strides=[1, 1],
        dilations=[1, 1]
    )
    
    # 2. InstanceNormalization
    in_scale = helper.make_tensor(
        'in_scale',
        TensorProto.FLOAT,
        [16],
        np.ones(16).astype(np.float32).tolist()
    )
    
    in_bias = helper.make_tensor(
        'in_bias',
        TensorProto.FLOAT,
        [16],
        np.zeros(16).astype(np.float32).tolist()
    )
    
    instance_norm_node = helper.make_node(
        'InstanceNormalization',
        inputs=['conv_out', 'in_scale', 'in_bias'],
        outputs=['instance_norm_out']
    )
    
    # 3. MaxPool
    maxpool_node = helper.make_node(
        'MaxPool',
        inputs=['instance_norm_out'],
        outputs=['maxpool_out'],
        kernel_shape=[2, 2],
        strides=[2, 2],
        pads=[0, 0, 0, 0]
    )
    
    # 4. AveragePool
    avgpool_node = helper.make_node(
        'AveragePool',
        inputs=['maxpool_out'],
        outputs=['avgpool_out'],
        kernel_shape=[2, 2],
        strides=[2, 2],
        pads=[0, 0, 0, 0]
    )
    
    # 5. Resize (用于上采样)
    scales = helper.make_tensor(
        'resize_scales',
        TensorProto.FLOAT,
        [4],
        [1.0, 1.0, 2.0, 2.0]  # 放大2倍
    )
    
    resize_node = helper.make_node(
        'Resize',
        inputs=['avgpool_out', '', 'resize_scales'],
        outputs=['resize_out'],
        mode='linear',
        coordinate_transformation_mode='half_pixel'
    )
    
    # 6. Pad
    pads = helper.make_tensor(
        'pad_pads',
        TensorProto.INT64,
        [8],
        [0, 0, 1, 1, 0, 0, 1, 1]
    )
    
    pad_value = helper.make_tensor(
        'pad_value',
        TensorProto.FLOAT,
        [],
        [0.0]
    )
    
    pad_node = helper.make_node(
        'Pad',
        inputs=['resize_out', 'pad_pads', 'pad_value'],
        outputs=['pad_out'],
        mode='constant'
    )
    
    # 第二个分支：1D序列处理路径 (用于LSTM)
    # LSTM输入 (序列数据)
    lstm_input_shape = [5, 1, 8]  # [seq_length, batch_size, input_size]
    lstm_input = helper.make_tensor_value_info('LSTM_X', TensorProto.FLOAT, lstm_input_shape)
    
    # LSTM参数
    hidden_size = 16
    num_directions = 1
    
    lstm_W = helper.make_tensor(
        'lstm_W',
        TensorProto.FLOAT,
        [num_directions, 4*hidden_size, 8],
        np.random.randn(num_directions, 4*hidden_size, 8).astype(np.float32).flatten().tolist()
    )
    
    lstm_R = helper.make_tensor(
        'lstm_R',
        TensorProto.FLOAT,
        [num_directions, 4*hidden_size, hidden_size],
        np.random.randn(num_directions, 4*hidden_size, hidden_size).astype(np.float32).flatten().tolist()
    )
    
    lstm_B = helper.make_tensor(
        'lstm_B',
        TensorProto.FLOAT,
        [num_directions, 8*hidden_size],
        np.random.randn(num_directions, 8*hidden_size).astype(np.float32).flatten().tolist()
    )
    
    lstm_initial_h = helper.make_tensor(
        'lstm_initial_h',
        TensorProto.FLOAT,
        [num_directions, 1, hidden_size],
        np.zeros([num_directions, 1, hidden_size]).astype(np.float32).flatten().tolist()
    )
    
    lstm_initial_c = helper.make_tensor(
        'lstm_initial_c',
        TensorProto.FLOAT,
        [num_directions, 1, hidden_size],
        np.zeros([num_directions, 1, hidden_size]).astype(np.float32).flatten().tolist()
    )
    
    # LSTM节点
    lstm_node = helper.make_node(
        'LSTM',
        inputs=['LSTM_X', 'lstm_W', 'lstm_R', 'lstm_B', '', 'lstm_initial_h', 'lstm_initial_c'],
        outputs=['lstm_Y', 'lstm_Y_h', 'lstm_Y_c'],
        hidden_size=hidden_size,
        direction='forward'
    )
    
    # 第三个分支：形状变换操作
    # 7. Reshape
    reshape_shape = helper.make_tensor(
        'reshape_shape',
        TensorProto.INT64,
        [3],
        [1, 8, 8]
    )
    
    reshape_node = helper.make_node(
        'Reshape',
        inputs=['pad_out', 'reshape_shape'],
        outputs=['reshape_out']
    )
    
    # 8. Flatten
    flatten_node = helper.make_node(
        'Flatten',
        inputs=['reshape_out'],
        outputs=['flatten_out'],
        axis=1
    )
    
    # 9. Squeeze (移除batch维度)
    squeeze_node = helper.make_node(
        'Squeeze',
        inputs=['flatten_out'],
        outputs=['squeeze_out'],
        axes=[0]
    )
    
    # 10. Unsqueeze (添加维度)
    unsqueeze_node = helper.make_node(
        'Unsqueeze',
        inputs=['squeeze_out'],
        outputs=['unsqueeze_out'],
        axes=[0, 2]
    )
    
    # 11. Tile (复制)
    tile_repeats = helper.make_tensor(
        'tile_repeats',
        TensorProto.INT64,
        [4],
        [1, 2, 1, 1]
    )
    
    tile_node = helper.make_node(
        'Tile',
        inputs=['unsqueeze_out', 'tile_repeats'],
        outputs=['tile_out']
    )
    
    # 12. Concat (连接两个分支)
    concat_node = helper.make_node(
        'Concat',
        inputs=['tile_out', 'tile_out'],  # 与自身连接
        outputs=['concat_out'],
        axis=1
    )
    
    # 13. Split (分割)
    split_node = helper.make_node(
        'Split',
        inputs=['concat_out'],
        outputs=['split_out1', 'split_out2'],
        axis=1
    )
    
    # 14. Gather (收集)
    gather_indices = helper.make_tensor(
        'gather_indices',
        TensorProto.INT64,
        [4],
        [0, 2, 4, 6]
    )
    
    gather_node = helper.make_node(
        'Gather',
        inputs=['split_out1', 'gather_indices'],
        outputs=['gather_out'],
        axis=1
    )
    
    # 最终输出
    output1 = helper.make_tensor_value_info('gather_out', TensorProto.FLOAT, [1, 4, 1, 8])
    output2 = helper.make_tensor_value_info('lstm_Y', TensorProto.FLOAT, [5, num_directions, 1, hidden_size])
    output3 = helper.make_tensor_value_info('lstm_Y_h', TensorProto.FLOAT, [num_directions, 1, hidden_size])
    output4 = helper.make_tensor_value_info('lstm_Y_c', TensorProto.FLOAT, [num_directions, 1, hidden_size])
    
    # 创建计算图
    graph = helper.make_graph(
        [
            conv_node, instance_norm_node, maxpool_node, avgpool_node,
            resize_node, pad_node, reshape_node, flatten_node,
            squeeze_node, unsqueeze_node, tile_node, concat_node,
            split_node, gather_node, lstm_node
        ],
        'conv_pool_graph',
        [input_x, lstm_input],
        [output1, output2, output3, output4],
        initializer=[
            conv_weight, conv_bias, in_scale, in_bias,
            scales, pads, pad_value, reshape_shape,
            tile_repeats, gather_indices,
            lstm_W, lstm_R, lstm_B, lstm_initial_h, lstm_initial_c
        ]
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='conv-pool-generator', output_path=output_path)
    logging.info(f"✓ 卷积池化类模型已保存: {output_path}")
    """创建简化的测试模型（用于快速验证）"""
    logging.info("创建简化测试模型...")
    
    # 简化卷积模型
    input_shape = [1, 3, 8, 8]
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    
    # Conv
    conv_weight = helper.make_tensor(
        'conv_weight',
        TensorProto.FLOAT,
        [4, 3, 3, 3],
        np.random.randn(4, 3, 3, 3).astype(np.float32).flatten().tolist()
    )
    
    conv_node = helper.make_node(
        'Conv',
        inputs=['X', 'conv_weight'],
        outputs=['conv_out'],
        kernel_shape=[3, 3],
        pads=[1, 1, 1, 1]
    )
    
    # MaxPool
    maxpool_node = helper.make_node(
        'MaxPool',
        inputs=['conv_out'],
        outputs=['maxpool_out'],
        kernel_shape=[2, 2],
        strides=[2, 2]
    )
    
    # AveragePool
    avgpool_node = helper.make_node(
        'AveragePool',
        inputs=['maxpool_out'],
        outputs=['avgpool_out'],
        kernel_shape=[2, 2],
        strides=[2, 2]
    )
    
    # Relu
    relu_node = helper.make_node(
        'Relu',
        inputs=['avgpool_out'],
        outputs=['relu_out']
    )
    
    graph = helper.make_graph(
        [conv_node, maxpool_node, avgpool_node, relu_node],
        'simple_conv_graph',
        [input_x],
        [helper.make_tensor_value_info('relu_out', TensorProto.FLOAT, [1, 4, 2, 2])],
        initializer=[conv_weight]
    )
    
    return graph