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


def _make_conv_relu_pool_nodes(initializer_list):
    conv_weight = helper.make_tensor(
        'conv_weight', TensorProto.FLOAT, [8, 3, 3, 3],
        np.random.randn(8, 3, 3, 3).astype(np.float32).flatten().tolist()
    )
    conv_bias = helper.make_tensor(
        'conv_bias', TensorProto.FLOAT, [8],
        np.random.randn(8).astype(np.float32).tolist()
    )
    initializer_list.extend([conv_weight, conv_bias])
    conv_node = helper.make_node(
        'Conv', inputs=['X', 'conv_weight', 'conv_bias'],
        outputs=['conv_out'], kernel_shape=[3, 3],
        pads=[1, 1, 1, 1], strides=[1, 1], dilations=[1, 1]
    )
    relu_node = helper.make_node(
        'Relu', inputs=['conv_out'], outputs=['relu_out']
    )
    maxpool_node = helper.make_node(
        'MaxPool', inputs=['relu_out'], outputs=['maxpool_out'],
        kernel_shape=[2, 2], strides=[2, 2], pads=[0, 0, 0, 0]
    )
    avgpool_node = helper.make_node(
        'AveragePool', inputs=['maxpool_out'], outputs=['avgpool_out'],
        kernel_shape=[2, 2], strides=[2, 2], pads=[0, 0, 0, 0]
    )
    nodes = [conv_node, relu_node, maxpool_node, avgpool_node]
    return nodes, 'avgpool_out'


def _make_resize_pad_nodes(initializer_list, avgpool_out_name):
    sizes = helper.make_tensor(
        'resize_sizes', TensorProto.INT64, [4], [1, 8, 16, 16])
    roi = helper.make_tensor('resize_roi', TensorProto.FLOAT, [0], [])
    scales = helper.make_tensor('resize_scales', TensorProto.FLOAT, [0], [])
    initializer_list.extend([roi, scales])
    resize_node = helper.make_node(
        'Resize',
        inputs=[avgpool_out_name, 'resize_roi', 'resize_scales',
                'resize_sizes'],
        outputs=['resize_out'],
        mode='linear', coordinate_transformation_mode='half_pixel'
    )
    pads = helper.make_tensor(
        'pad_pads', TensorProto.INT64, [8],
        [0, 0, 1, 1, 0, 0, 1, 1]
    )
    pad_value = helper.make_tensor('pad_value', TensorProto.FLOAT, [], [0.0])
    initializer_list.extend([pads, pad_value])
    pad_node = helper.make_node(
        'Pad', inputs=['resize_out', 'pad_pads', 'pad_value'],
        outputs=['pad_out'], mode='constant'
    )
    return [resize_node, pad_node], 'pad_out', sizes


def _make_flatten_reshape_slice_tile_nodes(initializer_list, pad_out_name):
    flatten_node = helper.make_node(
        'Flatten', inputs=[pad_out_name], outputs=['flatten_out'], axis=1
    )
    reshape_shape = helper.make_tensor(
        'reshape_shape', TensorProto.INT64, [2], [1, 2592]
    )
    initializer_list.append(reshape_shape)
    reshape_node = helper.make_node(
        'Reshape', inputs=['flatten_out', 'reshape_shape'],
        outputs=['reshape_out']
    )
    slice_starts = helper.make_tensor(
        'slice_starts', TensorProto.INT64, [2], [0, 0]
    )
    slice_ends = helper.make_tensor(
        'slice_ends', TensorProto.INT64, [2], [1, 40]
    )
    slice_axes = helper.make_tensor(
        'slice_axes', TensorProto.INT64, [2], [0, 1]
    )
    initializer_list.extend([slice_starts, slice_ends, slice_axes])
    slice_node = helper.make_node(
        'Slice',
        inputs=['reshape_out', 'slice_starts', 'slice_ends', 'slice_axes'],
        outputs=['slice_out']
    )
    tile_repeats = helper.make_tensor(
        'tile_repeats', TensorProto.INT64, [2], [1, 1]
    )
    initializer_list.append(tile_repeats)
    tile_node = helper.make_node(
        'Tile', inputs=['slice_out', 'tile_repeats'], outputs=['tile_out']
    )
    nodes = [flatten_node, reshape_node, slice_node, tile_node]
    return nodes, 'tile_out'


def _make_concat_gather_unsqueeze_squeeze_nodes(initializer_list, tile_out_name):
    concat_node = helper.make_node(
        'Concat', inputs=[tile_out_name, tile_out_name],
        outputs=['concat_out'], axis=1
    )
    gather_indices = helper.make_tensor(
        'gather_indices', TensorProto.INT64, [32], list(range(32))
    )
    initializer_list.append(gather_indices)
    gather_node = helper.make_node(
        'Gather', inputs=['concat_out', 'gather_indices'],
        outputs=['gather_out'], axis=1
    )
    unsqueeze_axes = helper.make_tensor(
        'unsqueeze_axes', TensorProto.INT64, [1], [0]
    )
    initializer_list.append(unsqueeze_axes)
    unsqueeze_node = helper.make_node(
        'Unsqueeze', inputs=['gather_out', 'unsqueeze_axes'],
        outputs=['unsqueeze_out']
    )
    squeeze_axes = helper.make_tensor(
        'squeeze_axes', TensorProto.INT64, [1], [0]
    )
    initializer_list.append(squeeze_axes)
    squeeze_node = helper.make_node(
        'Squeeze', inputs=['unsqueeze_out', 'squeeze_axes'],
        outputs=['squeeze_out']
    )
    nodes = [concat_node, gather_node, unsqueeze_node, squeeze_node]
    return nodes, 'squeeze_out'


def _make_lstm_slice_to_unsqueeze_nodes(initializer_list, squeeze_out_name):
    lstm_slice_starts = helper.make_tensor(
        'lstm_slice_starts', TensorProto.INT64, [2], [0, 0]
    )
    lstm_slice_ends = helper.make_tensor(
        'lstm_slice_ends', TensorProto.INT64, [2], [1, 16]
    )
    lstm_slice_axes = helper.make_tensor(
        'lstm_slice_axes', TensorProto.INT64, [2], [0, 1]
    )
    initializer_list.extend(
        [lstm_slice_starts, lstm_slice_ends, lstm_slice_axes])
    lstm_slice_node = helper.make_node(
        'Slice',
        inputs=[squeeze_out_name, 'lstm_slice_starts', 'lstm_slice_ends',
                'lstm_slice_axes'],
        outputs=['lstm_sliced']
    )
    lstm_to_1d_shape = helper.make_tensor(
        'lstm_to_1d_shape', TensorProto.INT64, [1], [16]
    )
    initializer_list.append(lstm_to_1d_shape)
    lstm_reshape_node = helper.make_node(
        'Reshape', inputs=['lstm_sliced', 'lstm_to_1d_shape'],
        outputs=['lstm_squeeze_out']
    )
    gemm_unsqueeze_axes = helper.make_tensor(
        'gemm_unsqueeze_axes', TensorProto.INT64, [1], [0]
    )
    initializer_list.append(gemm_unsqueeze_axes)
    gemm_unsqueeze_node = helper.make_node(
        'Unsqueeze',
        inputs=['lstm_squeeze_out', 'gemm_unsqueeze_axes'],
        outputs=['gemm_unsqueeze_out']
    )
    nodes = [lstm_slice_node, lstm_reshape_node, gemm_unsqueeze_node]
    return nodes, 'gemm_unsqueeze_out'


def _make_gemm_final_reshape_nodes(initializer_list):
    hidden_size = 16
    gemm_weight = helper.make_tensor(
        'gemm_weight', TensorProto.FLOAT, [hidden_size, 10],
        np.random.randn(hidden_size, 10).astype(np.float32).flatten().tolist()
    )
    gemm_bias = helper.make_tensor(
        'gemm_bias', TensorProto.FLOAT, [10],
        np.random.randn(10).astype(np.float32).tolist()
    )
    initializer_list.extend([gemm_weight, gemm_bias])
    gemm_node = helper.make_node(
        'Gemm', inputs=['gemm_unsqueeze_out', 'gemm_weight', 'gemm_bias'],
        outputs=['gemm_out'], alpha=1.0, beta=1.0, transA=0, transB=0
    )
    final_reshape_shape = helper.make_tensor(
        'final_reshape_shape', TensorProto.INT64, [2], [1, 10]
    )
    initializer_list.append(final_reshape_shape)
    final_reshape_node = helper.make_node(
        'Reshape', inputs=['gemm_out', 'final_reshape_shape'],
        outputs=['final_output']
    )
    nodes = [gemm_node, final_reshape_node]
    return nodes, 'final_output'


def _make_1d_conv_nodes(initializer_list, avgpool_out_name):
    reshape_1d_in_shape = helper.make_tensor(
        'reshape_1d_in_shape', TensorProto.INT64, [3], [1, 8, 64]
    )
    initializer_list.append(reshape_1d_in_shape)
    reshape_1d_in_node = helper.make_node(
        'Reshape', inputs=[avgpool_out_name, 'reshape_1d_in_shape'],
        outputs=['branch_1d_in']
    )
    conv1d_weight = helper.make_tensor(
        'conv1d_weight', TensorProto.FLOAT, [4, 8, 3],
        np.random.randn(4, 8, 3).astype(np.float32).flatten().tolist()
    )
    conv1d_bias = helper.make_tensor(
        'conv1d_bias', TensorProto.FLOAT, [4],
        np.random.randn(4).astype(np.float32).tolist()
    )
    initializer_list.extend([conv1d_weight, conv1d_bias])
    conv1d_node = helper.make_node(
        'Conv', inputs=['branch_1d_in', 'conv1d_weight', 'conv1d_bias'],
        outputs=['conv1d_out'], kernel_shape=[3],
        pads=[1, 1], strides=[1], dilations=[1]
    )
    nodes = [reshape_1d_in_node, conv1d_node]
    return nodes, 'conv1d_out'


def _make_1d_bn_pool_flat_nodes(initializer_list, conv1d_out_name):
    bn_scale = helper.make_tensor(
        'bn_scale', TensorProto.FLOAT, [4],
        np.ones(4).astype(np.float32).tolist()
    )
    bn_bias = helper.make_tensor(
        'bn_bias', TensorProto.FLOAT, [4],
        np.zeros(4).astype(np.float32).tolist()
    )
    bn_mean = helper.make_tensor(
        'bn_mean', TensorProto.FLOAT, [4],
        np.zeros(4).astype(np.float32).tolist()
    )
    bn_var = helper.make_tensor(
        'bn_var', TensorProto.FLOAT, [4],
        np.ones(4).astype(np.float32).tolist()
    )
    initializer_list.extend([bn_scale, bn_bias, bn_mean, bn_var])
    bn_node = helper.make_node(
        'BatchNormalization',
        inputs=[conv1d_out_name, 'bn_scale', 'bn_bias', 'bn_mean', 'bn_var'],
        outputs=['bn_out'], epsilon=1e-5, momentum=0.9
    )
    avgpool1d_node = helper.make_node(
        'AveragePool', inputs=['bn_out'], outputs=['avgpool1d_out'],
        kernel_shape=[2], strides=[2], pads=[0, 0]
    )
    maxpool1d_node = helper.make_node(
        'MaxPool', inputs=['avgpool1d_out'], outputs=['maxpool1d_out'],
        kernel_shape=[2], strides=[2], pads=[0, 0]
    )
    reshape_1d_flat_shape = helper.make_tensor(
        'reshape_1d_flat_shape', TensorProto.INT64, [2], [1, 64]
    )
    initializer_list.append(reshape_1d_flat_shape)
    reshape_1d_flat_node = helper.make_node(
        'Reshape', inputs=['maxpool1d_out', 'reshape_1d_flat_shape'],
        outputs=['branch_1d_flat']
    )
    nodes = [bn_node, avgpool1d_node, maxpool1d_node, reshape_1d_flat_node]
    return nodes, 'branch_1d_flat'


def _make_transpose_split_l2norm_nodes(initializer_list, branch_1d_flat_name):
    transpose_node = helper.make_node(
        'Transpose', inputs=[branch_1d_flat_name], outputs=['transpose_out'],
        perm=[1, 0]
    )
    reshape_t_back_shape = helper.make_tensor(
        'reshape_t_back_shape', TensorProto.INT64, [2], [1, 64]
    )
    initializer_list.append(reshape_t_back_shape)
    reshape_t_back_node = helper.make_node(
        'Reshape', inputs=['transpose_out', 'reshape_t_back_shape'],
        outputs=['t_back_out']
    )
    split_node = helper.make_node(
        'Split', inputs=['t_back_out'],
        outputs=['split_out_0', 'split_out_1'],
        axis=1
    )
    l2norm_node = helper.make_node(
        'LpNormalization', inputs=['split_out_0'], outputs=['l2norm_out'],
        axis=1, p=2
    )
    ln_flat_node = helper.make_node(
        'Identity', inputs=['l2norm_out'], outputs=['ln_flat_out']
    )
    nodes = [transpose_node, reshape_t_back_node, split_node,
             l2norm_node, ln_flat_node]
    return nodes, 'ln_flat_out', 'split_out_1'


def _make_gru_weight_tensors(initializer_list):
    gru_hidden_size = 8
    gru_num_directions = 1
    gru_w = helper.make_tensor(
        'gru_w', TensorProto.FLOAT,
        [gru_num_directions, 3 * gru_hidden_size, 16],
        np.random.randn(
            gru_num_directions, 3 * gru_hidden_size, 16
        ).astype(np.float32).flatten().tolist()
    )
    gru_r = helper.make_tensor(
        'gru_r', TensorProto.FLOAT,
        [gru_num_directions, 3 * gru_hidden_size, gru_hidden_size],
        np.random.randn(
            gru_num_directions, 3 * gru_hidden_size, gru_hidden_size
        ).astype(np.float32).flatten().tolist()
    )
    gru_b = helper.make_tensor(
        'gru_b', TensorProto.FLOAT,
        [gru_num_directions, 6 * gru_hidden_size],
        np.random.randn(
            gru_num_directions, 6 * gru_hidden_size
        ).astype(np.float32).flatten().tolist()
    )
    gru_initial_h = helper.make_tensor(
        'gru_initial_h', TensorProto.FLOAT,
        [gru_num_directions, 1, gru_hidden_size],
        np.zeros([gru_num_directions, 1, gru_hidden_size]
                 ).astype(np.float32).flatten().tolist()
    )
    gru_seq_lens = helper.make_tensor(
        'gru_seq_lens', TensorProto.INT32, [1], [2]
    )
    initializer_list.extend(
        [gru_w, gru_r, gru_b, gru_seq_lens, gru_initial_h])
    return gru_hidden_size


def _make_gru_nodes(initializer_list, split_out_1_name):
    gru_reshape_shape = helper.make_tensor(
        'gru_reshape_shape', TensorProto.INT64, [3], [2, 1, 16]
    )
    initializer_list.append(gru_reshape_shape)
    gru_reshape_node = helper.make_node(
        'Reshape', inputs=[split_out_1_name, 'gru_reshape_shape'],
        outputs=['gru_in']
    )
    gru_hidden_size = _make_gru_weight_tensors(initializer_list)
    gru_node = helper.make_node(
        'GRU',
        inputs=['gru_in', 'gru_w', 'gru_r', 'gru_b',
                'gru_seq_lens', 'gru_initial_h'],
        outputs=['gru_y', 'gru_y_h'],
        hidden_size=gru_hidden_size, direction='forward'
    )
    gru_flat_shape = helper.make_tensor(
        'gru_flat_shape', TensorProto.INT64, [2], [1, 8]
    )
    initializer_list.append(gru_flat_shape)
    gru_flat_node = helper.make_node(
        'Reshape', inputs=['gru_y_h', 'gru_flat_shape'],
        outputs=['gru_flat_out']
    )
    nodes = [gru_reshape_node, gru_node, gru_flat_node]
    return nodes, 'gru_flat_out'


def _make_dropout_gatherelements_expand_nodes(
        initializer_list, ln_flat_out_name):
    dropout_node = helper.make_node(
        'Dropout', inputs=[ln_flat_out_name], outputs=['dropout_out']
    )
    ge_indices = helper.make_tensor(
        'ge_indices', TensorProto.INT64, [1, 32],
        (np.arange(32).astype(np.int64) % 16).tolist()
    )
    initializer_list.append(ge_indices)
    gatherelements_node = helper.make_node(
        'GatherElements', inputs=['dropout_out', 'ge_indices'],
        outputs=['gatherelements_out'], axis=1
    )
    expand_slice_starts = helper.make_tensor(
        'expand_slice_starts', TensorProto.INT64, [2], [0, 0]
    )
    expand_slice_ends = helper.make_tensor(
        'expand_slice_ends', TensorProto.INT64, [2], [1, 1]
    )
    expand_slice_axes = helper.make_tensor(
        'expand_slice_axes', TensorProto.INT64, [2], [0, 1]
    )
    initializer_list.extend(
        [expand_slice_starts, expand_slice_ends, expand_slice_axes])
    expand_slice_node = helper.make_node(
        'Slice',
        inputs=[ln_flat_out_name, 'expand_slice_starts',
                'expand_slice_ends', 'expand_slice_axes'],
        outputs=['expand_slice_out']
    )
    expand_shape = helper.make_tensor(
        'expand_shape', TensorProto.INT64, [2], [1, 16]
    )
    initializer_list.append(expand_shape)
    expand_node = helper.make_node(
        'Expand', inputs=['expand_slice_out', 'expand_shape'],
        outputs=['expand_out']
    )
    nodes = [dropout_node, gatherelements_node,
             expand_slice_node, expand_node]
    return nodes, 'gatherelements_out', 'expand_out'


def _make_depthtospace_spacetodepth_nodes(
        initializer_list, gatherelements_out_name):
    dts_4d_shape = helper.make_tensor(
        'dts_4d_shape', TensorProto.INT64, [4], [1, 8, 2, 2]
    )
    initializer_list.append(dts_4d_shape)
    dts_reshape_4d_node = helper.make_node(
        'Reshape', inputs=[gatherelements_out_name, 'dts_4d_shape'],
        outputs=['dts_4d_out']
    )
    depthtospace_node = helper.make_node(
        'DepthToSpace', inputs=['dts_4d_out'],
        outputs=['depthtospace_out'],
        blocksize=2, mode='DCR'
    )
    spacetodepth_node = helper.make_node(
        'SpaceToDepth', inputs=['depthtospace_out'],
        outputs=['spacetodepth_out'],
        blocksize=2
    )
    dts_flat_shape = helper.make_tensor(
        'dts_flat_shape', TensorProto.INT64, [2], [1, 32]
    )
    initializer_list.append(dts_flat_shape)
    dts_flat_node = helper.make_node(
        'Reshape', inputs=['spacetodepth_out', 'dts_flat_shape'],
        outputs=['dts_flat_out']
    )
    nodes = [dts_reshape_4d_node, depthtospace_node,
             spacetodepth_node, dts_flat_node]
    return nodes, 'dts_flat_out'


def _make_reverse_sequence_nodes(initializer_list):
    revseq_reshape_in_shape = helper.make_tensor(
        'revseq_reshape_in_shape', TensorProto.INT64, [3], [1, 32, 96]
    )
    initializer_list.append(revseq_reshape_in_shape)
    revseq_reshape_in_node = helper.make_node(
        'Reshape', inputs=['X', 'revseq_reshape_in_shape'],
        outputs=['revseq_in']
    )
    revseq_lengths = helper.make_tensor(
        'revseq_lengths', TensorProto.INT64, [1], [16]
    )
    initializer_list.append(revseq_lengths)
    reversesequence_node = helper.make_node(
        'ReverseSequence',
        inputs=['revseq_in', 'revseq_lengths'],
        outputs=['revseq_out'],
        batch_axis=0, time_axis=1
    )
    revseq_flat_shape = helper.make_tensor(
        'revseq_flat_shape', TensorProto.INT64, [2], [1, 3072]
    )
    initializer_list.append(revseq_flat_shape)
    revseq_flat_node = helper.make_node(
        'Reshape', inputs=['revseq_out', 'revseq_flat_shape'],
        outputs=['revseq_flat_out']
    )
    revseq_slice_starts = helper.make_tensor(
        'revseq_slice_starts', TensorProto.INT64, [2], [0, 0]
    )
    revseq_slice_ends = helper.make_tensor(
        'revseq_slice_ends', TensorProto.INT64, [2], [1, 32]
    )
    revseq_slice_axes = helper.make_tensor(
        'revseq_slice_axes', TensorProto.INT64, [2], [0, 1]
    )
    initializer_list.extend(
        [revseq_slice_starts, revseq_slice_ends, revseq_slice_axes])
    revseq_slice_node = helper.make_node(
        'Slice',
        inputs=['revseq_flat_out', 'revseq_slice_starts',
                'revseq_slice_ends', 'revseq_slice_axes'],
        outputs=['revseq_sliced']
    )
    nodes = [revseq_reshape_in_node, reversesequence_node,
             revseq_flat_node, revseq_slice_node]
    return nodes, 'revseq_sliced'


def _make_merge_node():
    merged_node = helper.make_node(
        'Concat',
        inputs=['final_output', 'gru_flat_out', 'dts_flat_out',
                'revseq_sliced', 'expand_out'],
        outputs=['merged_output'],
        axis=1
    )
    return merged_node


def create_neuralnetwork_onnx_model(output_path):
    logging.info(f"creating conv pool model: {output_path}")
    initializer_list = []
    input_shape = [1, 3, 32, 32]
    input_x = helper.make_tensor_value_info(
        'X', TensorProto.FLOAT, input_shape)
    nodes1, avgpool_out_name = _make_conv_relu_pool_nodes(initializer_list)
    nodes2, pad_out_name, sizes = _make_resize_pad_nodes(
        initializer_list, avgpool_out_name)
    nodes3, tile_out_name = _make_flatten_reshape_slice_tile_nodes(
        initializer_list, pad_out_name)
    nodes4, squeeze_out_name = \
        _make_concat_gather_unsqueeze_squeeze_nodes(
            initializer_list, tile_out_name)
    nodes5a, _ = _make_lstm_slice_to_unsqueeze_nodes(
        initializer_list, squeeze_out_name)
    nodes5b, _ = _make_gemm_final_reshape_nodes(initializer_list)
    nodes6a, conv1d_out_name = _make_1d_conv_nodes(
        initializer_list, avgpool_out_name)
    nodes6b, branch_1d_flat_name = _make_1d_bn_pool_flat_nodes(
        initializer_list, conv1d_out_name)
    nodes7, ln_flat_out_name, split_out_1_name = \
        _make_transpose_split_l2norm_nodes(
            initializer_list, branch_1d_flat_name)
    nodes8, _ = _make_gru_nodes(initializer_list, split_out_1_name)
    nodes9, gatherelements_out_name, _ = \
        _make_dropout_gatherelements_expand_nodes(
            initializer_list, ln_flat_out_name)
    nodes10, _ = _make_depthtospace_spacetodepth_nodes(
        initializer_list, gatherelements_out_name)
    nodes11, _ = _make_reverse_sequence_nodes(initializer_list)
    merge_node = _make_merge_node()
    initializer_list.insert(4, sizes)
    all_nodes = (
        nodes1 + nodes2 + nodes3 + nodes4 + nodes5a + nodes5b +
        nodes6a + nodes6b + nodes7 + nodes8 + nodes9 + nodes10 +
        nodes11 + [merge_node]
    )
    merged_output = helper.make_tensor_value_info(
        'merged_output', TensorProto.FLOAT, [1, 98])
    graph = helper.make_graph(
        all_nodes, 'single_branch_conv_pool_graph',
        [input_x], [merged_output], initializer=initializer_list)
    model = create_low_ir_version_model(
        graph, producer_name='conv-pool-generator',
        output_path=output_path, opset_version=13)
    logging.info(f"conv pool model saved: {output_path}")
