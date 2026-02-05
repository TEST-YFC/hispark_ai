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


def create_neuralnetwork_onnx_model(output_path):
    """
    Conv, InstanceNormalization, MaxPool, AveragePool, Resize, Pad
    LSTM
    Reshape、Flatten、Squeeze、Unsqueeze、Tile、Concat、Split、Gather
    """
    logging.info(f"创建卷积池化类模型: {output_path}")
    
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
    
    # 5. Resize
    roi = helper.make_tensor(
        'resize_roi',
        TensorProto.FLOAT,
        [8],
        [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    )
    
    scales = helper.make_tensor(
        'resize_scales',
        TensorProto.FLOAT,
        [4],
        [1.0, 1.0, 2.0, 2.0]  # 放大2倍
    )
    
    resize_node = helper.make_node(
        'Resize',
        inputs=['avgpool_out', 'resize_roi', 'resize_scales'],
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
    # 7. Flatten - 将卷积输出展平
    flatten_node = helper.make_node(
        'Flatten',
        inputs=['pad_out'],
        outputs=['flatten_out'],
        axis=1
    )
    
    # 8. Reshape
    reshape_shape = helper.make_tensor(
        'reshape_shape',
        TensorProto.INT64,
        [2],
        [1, -1]
    )
    
    reshape_node = helper.make_node(
        'Reshape',
        inputs=['flatten_out', 'reshape_shape'],
        outputs=['reshape_out']
    )
    
    # 9. Tile
    tile_repeats = helper.make_tensor(
        'tile_repeats',
        TensorProto.INT64,
        [2],
        [1, 2]
    )
    
    tile_node = helper.make_node(
        'Tile',
        inputs=['reshape_out', 'tile_repeats'],
        outputs=['tile_out']
    )
    
    # 10. Concat
    concat_node = helper.make_node(
        'Concat',
        inputs=['tile_out', 'tile_out'],
        outputs=['concat_out'],
        axis=1
    )
    
    # 11. Split
    split_node = helper.make_node(
        'Split',
        inputs=['concat_out'],
        outputs=['split_out1', 'split_out2'],
        axis=1,
        num_outputs=2
    )
    
    # 12. Gather
    gather_indices = helper.make_tensor(
        'gather_indices',
        TensorProto.INT64,
        [4],
        [0, 10, 20, 30]
    )
    
    gather_node = helper.make_node(
        'Gather',
        inputs=['split_out1', 'gather_indices'],
        outputs=['gather_out'],
        axis=1
    )
    
    # 13. 修改Squeeze操作，确保输出是2D用于可能的Gemm操作
    squeeze_axes = helper.make_tensor(
        'squeeze_axes',
        TensorProto.INT64,
        [1],
        [0]
    )
    
    squeeze_node = helper.make_node(
        'Squeeze',
        inputs=['unsqueeze_out', 'squeeze_axes'],
        outputs=['squeeze_out']  # 形状变为[4, 1]
    )
    
    # 14. 添加一个Reshape确保是2D矩阵 [4, 1] -> [1, 4]
    gemm_reshape_shape = helper.make_tensor(
        'gemm_reshape_shape',
        TensorProto.INT64,
        [2],
        [1, 4]
    )
    
    gemm_reshape_node = helper.make_node(
        'Reshape',
        inputs=['squeeze_out', 'gemm_reshape_shape'],
        outputs=['gemm_ready_out']
    )
    unsqueeze_axes = helper.make_tensor(
        'unsqueeze_axes',
        TensorProto.INT64,
        [1],
        [2]
    )
    
    unsqueeze_node = helper.make_node(
        'Unsqueeze',
        inputs=['gather_out', 'unsqueeze_axes'],
        outputs=['unsqueeze_out']
    )
    
    # 移除大小为1的维度（从[1,4,1]变为[4]）
    squeeze_axes = helper.make_tensor(
        'squeeze_axes',
        TensorProto.INT64,
        [2],
        [0, 2]  # 移除第0维（大小为1）和第2维（大小为1）
    )
    
    squeeze_node = helper.make_node(
        'Squeeze',
        inputs=['unsqueeze_out', 'squeeze_axes'],
        outputs=['squeeze_out']
    )
    
    # 15. Gemm
    gemm_weight = helper.make_tensor(
        'gemm_weight',
        TensorProto.FLOAT,
        [4, 10],
        np.random.randn(4, 10).astype(np.float32).flatten().tolist()
    )
    
    gemm_bias = helper.make_tensor(
        'gemm_bias',
        TensorProto.FLOAT,
        [10],
        np.random.randn(10).astype(np.float32).tolist()
    )
    
    gemm_node = helper.make_node(
        'Gemm',
        inputs=['gemm_ready_out', 'gemm_weight', 'gemm_bias'],
        outputs=['gemm_out'],
        alpha=1.0,
        beta=1.0,
        transA=0,
        transB=0
    )
    
    # 最终输出
    output1 = helper.make_tensor_value_info('gemm_out', TensorProto.FLOAT, [1, 10])
    output2 = helper.make_tensor_value_info('lstm_Y', TensorProto.FLOAT, [5, num_directions, 1, hidden_size])
    output3 = helper.make_tensor_value_info('lstm_Y_h', TensorProto.FLOAT, [num_directions, 1, hidden_size])
    output4 = helper.make_tensor_value_info('lstm_Y_c', TensorProto.FLOAT, [num_directions, 1, hidden_size])
    
    # 创建计算图（添加gemm_reshape_node和gemm_node）
    graph = helper.make_graph(
        [
            conv_node, instance_norm_node, maxpool_node, avgpool_node,
            resize_node, pad_node, flatten_node, reshape_node,
            tile_node, concat_node, split_node, gather_node,
            unsqueeze_node, squeeze_node, gemm_reshape_node, gemm_node,
            lstm_node
        ],
        'conv_pool_graph',
        [input_x, lstm_input],
        [output1, output2, output3, output4],
        initializer=[
            conv_weight, conv_bias, in_scale, in_bias,
            roi, scales, pads, pad_value, reshape_shape,
            tile_repeats, gather_indices, 
            unsqueeze_axes, squeeze_axes, gemm_reshape_shape,
            gemm_weight, gemm_bias,
            lstm_W, lstm_R, lstm_B, lstm_initial_h, lstm_initial_c
        ]
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='conv-pool-generator', output_path=output_path)
    logging.info(f"✓ 卷积池化类模型已保存: {output_path}")