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
    LSTM, Reshape, Flatten, Squeeze, Unsqueeze, Tile, Concat, Split, Gather, Gemm
    """
    logging.info(f"创建卷积池化类模型: {output_path}")
    
    input_shape = [1, 3, 32, 32]
    input_x = helper.make_tensor_value_info('X', TensorProto.FLOAT, input_shape)
    
    # 1. Conv 2D
    conv_weight = helper.make_tensor(
        'conv_weight',
        TensorProto.FLOAT,
        [8, 3, 3, 3],
        np.random.randn(8, 3, 3, 3).astype(np.float32).flatten().tolist()
    )
    
    conv_bias = helper.make_tensor(
        'conv_bias',
        TensorProto.FLOAT,
        [8],
        np.random.randn(8).astype(np.float32).tolist()
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
        [8],
        np.ones(8).astype(np.float32).tolist()
    )
    
    in_bias = helper.make_tensor(
        'in_bias',
        TensorProto.FLOAT,
        [8],
        np.zeros(8).astype(np.float32).tolist()
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
    sizes = helper.make_tensor(
        'resize_sizes',
        TensorProto.INT64,
        [4],
        [1, 8, 16, 16]
    )
    roi = helper.make_tensor(
        'resize_roi',
        TensorProto.FLOAT,
        [0],
        []
    )

    scales = helper.make_tensor(
        'resize_scales',
        TensorProto.FLOAT,
        [0],
        []
    )

    resize_node = helper.make_node(
        'Resize',
        inputs=['avgpool_out', 'resize_roi', 'resize_scales', 'resize_sizes'],
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
    
    # 7. Flatten
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
        [1, 2592]
    )
    
    reshape_node = helper.make_node(
        'Reshape',
        inputs=['flatten_out', 'reshape_shape'],
        outputs=['reshape_out']
    )
    
    # 9.Slice
    slice_starts = helper.make_tensor(
        'slice_starts',
        TensorProto.INT64,
        [2],
        [0, 0]
    )
    
    slice_ends = helper.make_tensor(
        'slice_ends',
        TensorProto.INT64,
        [2],
        [1, 40]
    )
    
    slice_axes = helper.make_tensor(
        'slice_axes',
        TensorProto.INT64,
        [2],
        [0, 1]
    )
    
    slice_node = helper.make_node(
        'Slice',
        inputs=['reshape_out', 'slice_starts', 'slice_ends', 'slice_axes'],
        outputs=['slice_out']
    )
    
    # 10. Tile
    tile_repeats = helper.make_tensor(
        'tile_repeats',
        TensorProto.INT64,
        [2],
        [1, 1]
    )
    
    tile_node = helper.make_node(
        'Tile',
        inputs=['slice_out', 'tile_repeats'],
        outputs=['tile_out']
    )
    
    # 11. Concat
    concat_node = helper.make_node(
        'Concat',
        inputs=['tile_out', 'tile_out'],
        outputs=['concat_out'],
        axis=1
    )
    
    # 12. Split
    split_node = helper.make_node(
        'Split',
        inputs=['concat_out'],
        outputs=['split_out1', 'split_out2'],
        axis=1,
        num_outputs=2
    )
    
    # 13. Gather
    gather_indices = helper.make_tensor(
        'gather_indices',
        TensorProto.INT64,
        [32],
        list(range(32))
    )
    
    gather_node = helper.make_node(
        'Gather',
        inputs=['split_out1', 'gather_indices'],
        outputs=['gather_out'],
        axis=1
    )
    
    # 14. Unsqueeze
    unsqueeze_axes = helper.make_tensor(
        'unsqueeze_axes',
        TensorProto.INT64,
        [1],
        [0]
    )
    
    unsqueeze_node = helper.make_node(
        'Unsqueeze',
        inputs=['gather_out', 'unsqueeze_axes'],
        outputs=['unsqueeze_out']
    )
    
    # 15.Squeeze
    lstm_reshape_shape = helper.make_tensor(
        'lstm_reshape_shape',
        TensorProto.INT64,
        [3],
        [4, 1, 8]
    )
    
    lstm_reshape_node = helper.make_node(
        'Reshape',
        inputs=['unsqueeze_out', 'lstm_reshape_shape'],
        outputs=['lstm_ready_out']
    )
    
    # 16. LSTM
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
    
    lstm_node = helper.make_node(
        'LSTM',
        inputs=['lstm_ready_out', 'lstm_W', 'lstm_R', 'lstm_B', '', 'lstm_initial_h', 'lstm_initial_c'],
        outputs=['lstm_Y', 'lstm_Y_h', 'lstm_Y_c'],
        hidden_size=hidden_size,
        direction='forward'
    )
    
    # 17. 使用LSTM的最终隐藏状态
    final_lstm_node = helper.make_node(
        'Identity',
        inputs=['lstm_Y_h'],
        outputs=['final_lstm_out']
    )
    
    # 18. Squeeze LSTM输出
    lstm_squeeze_axes = helper.make_tensor(
        'lstm_squeeze_axes',
        TensorProto.INT64,
        [2],
        [0, 1]
    )
    
    lstm_squeeze_node = helper.make_node(
        'Squeeze',
        inputs=['final_lstm_out', 'lstm_squeeze_axes'],
        outputs=['lstm_squeeze_out']
    )
    
    # 19. Unsqueeze
    gemm_unsqueeze_axes = helper.make_tensor(
        'gemm_unsqueeze_axes',
        TensorProto.INT64,
        [1],
        [0]
    )
    
    gemm_unsqueeze_node = helper.make_node(
        'Unsqueeze',
        inputs=['lstm_squeeze_out', 'gemm_unsqueeze_axes'],
        outputs=['gemm_unsqueeze_out']
    )
    
    # 20. Gemm
    gemm_weight = helper.make_tensor(
        'gemm_weight',
        TensorProto.FLOAT,
        [hidden_size, 10],
        np.random.randn(hidden_size, 10).astype(np.float32).flatten().tolist()
    )
    
    gemm_bias = helper.make_tensor(
        'gemm_bias',
        TensorProto.FLOAT,
        [10],
        np.random.randn(10).astype(np.float32).tolist()
    )
    
    gemm_node = helper.make_node(
        'Gemm',
        inputs=['gemm_unsqueeze_out', 'gemm_weight', 'gemm_bias'],
        outputs=['gemm_out'],
        alpha=1.0,
        beta=1.0,
        transA=0,
        transB=0
    )
    
    final_reshape_shape = helper.make_tensor(
        'final_reshape_shape',
        TensorProto.INT64,
        [2],
        [1, 10]
    )
    
    final_reshape_node = helper.make_node(
        'Reshape',
        inputs=['gemm_out', 'final_reshape_shape'],
        outputs=['final_output']
    )
    
    output = helper.make_tensor_value_info('final_output', TensorProto.FLOAT, [1, 10])
    
    initializer_list = [roi, scales,
        conv_weight, conv_bias, in_scale, in_bias,
        pads, pad_value, reshape_shape,
        slice_starts, slice_ends, slice_axes,
        tile_repeats, gather_indices, 
        unsqueeze_axes, lstm_reshape_shape,
        lstm_squeeze_axes, gemm_unsqueeze_axes,
        gemm_weight, gemm_bias, final_reshape_shape,
        lstm_W, lstm_R, lstm_B, lstm_initial_h, lstm_initial_c
    ]
    
    initializer_list.insert(4, sizes)
    
    graph = helper.make_graph(
        [
            conv_node, instance_norm_node, maxpool_node, avgpool_node,
            resize_node, pad_node, flatten_node, reshape_node,
            slice_node, tile_node, concat_node, split_node,
            gather_node, unsqueeze_node, lstm_reshape_node,
            lstm_node, final_lstm_node, lstm_squeeze_node,
            gemm_unsqueeze_node, gemm_node, final_reshape_node
        ],
        'single_branch_conv_pool_graph',
        [input_x],
        [output],
        initializer=initializer_list
    )
    
    # 创建模型
    model = create_low_ir_version_model(graph, producer_name='conv-pool-generator', output_path=output_path)
    logging.info(f"✓ 卷积池化模型已保存: {output_path}")