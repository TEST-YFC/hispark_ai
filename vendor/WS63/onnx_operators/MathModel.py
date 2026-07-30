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


def _make_gemm_reshape_matmul_nodes(initializer_list):
    reshape_to_2d_shape = helper.make_tensor(
        'reshape_to_2d_shape', TensorProto.INT64, [2], [4, 4]
    )
    initializer_list.append(reshape_to_2d_shape)
    reshape_to_2d_node = helper.make_node(
        'Reshape', inputs=['X', 'reshape_to_2d_shape'],
        outputs=['reshape_to_2d_out']
    )
    gemm_weight = helper.make_tensor(
        'gemm_weight', TensorProto.FLOAT, [4, 4],
        np.random.randn(4, 4).astype(np.float32).flatten().tolist()
    )
    gemm_bias = helper.make_tensor(
        'gemm_bias', TensorProto.FLOAT, [4],
        np.random.randn(4).astype(np.float32).tolist()
    )
    initializer_list.extend([gemm_weight, gemm_bias])
    gemm_node = helper.make_node(
        'Gemm', inputs=['reshape_to_2d_out', 'gemm_weight', 'gemm_bias'],
        outputs=['gemm_out'], alpha=1.0, beta=1.0, transA=0, transB=0
    )
    reshape_to_3d_shape = helper.make_tensor(
        'reshape_to_3d_shape', TensorProto.INT64, [3], [1, 4, 4]
    )
    initializer_list.append(reshape_to_3d_shape)
    reshape_to_3d_node = helper.make_node(
        'Reshape', inputs=['gemm_out', 'reshape_to_3d_shape'],
        outputs=['gemm_3d_out']
    )
    matmul_weight = helper.make_tensor(
        'matmul_weight', TensorProto.FLOAT, [4, 4],
        np.random.randn(4, 4).astype(np.float32).flatten().tolist()
    )
    initializer_list.append(matmul_weight)
    matmul_node = helper.make_node(
        'MatMul', inputs=['gemm_3d_out', 'matmul_weight'],
        outputs=['matmul_out']
    )
    nodes = [
        reshape_to_2d_node, gemm_node, reshape_to_3d_node, matmul_node,
    ]
    return nodes


def _make_activation_arith_nodes():
    relu_node = helper.make_node(
        'Relu', inputs=['matmul_out'], outputs=['relu_out'])
    tanh_node = helper.make_node(
        'Tanh', inputs=['relu_out'], outputs=['tanh_out'])
    sigmoid_node = helper.make_node(
        'Sigmoid', inputs=['tanh_out'], outputs=['sigmoid_out'])
    softmax_node = helper.make_node(
        'Softmax', inputs=['sigmoid_out'], outputs=['softmax_out'], axis=2
    )
    add_node = helper.make_node(
        'Add', inputs=['softmax_out', 'Y'], outputs=['add_out'])
    sub_node = helper.make_node(
        'Sub', inputs=['add_out', 'Y'], outputs=['sub_out'])
    mul_node = helper.make_node(
        'Mul', inputs=['sub_out', 'Y'], outputs=['mul_out'])
    nodes = [
        relu_node, tanh_node, sigmoid_node,
        softmax_node, add_node, sub_node, mul_node,
    ]
    return nodes


def _make_unary_math_nodes(initializer_list):
    abs_node = helper.make_node(
        'Abs', inputs=['mul_out'], outputs=['abs_out'])
    cos_node = helper.make_node(
        'Cos', inputs=['abs_out'], outputs=['cos_out'])
    sin_node = helper.make_node(
        'Sin', inputs=['cos_out'], outputs=['sin_out'])
    exp_node = helper.make_node(
        'Exp', inputs=['sin_out'], outputs=['exp_out'])
    log_node = helper.make_node(
        'Log', inputs=['exp_out'], outputs=['log_out'])
    abs_before_sqrt_node = helper.make_node(
        'Abs', inputs=['log_out'], outputs=['abs_before_sqrt'])
    sqrt_node = helper.make_node(
        'Sqrt', inputs=['abs_before_sqrt'], outputs=['sqrt_out'])
    prescale_value = helper.make_tensor(
        'prescale_value', TensorProto.FLOAT, [], [100.0]
    )
    postscale_value = helper.make_tensor(
        'postscale_value', TensorProto.FLOAT, [], [0.01]
    )
    initializer_list.extend([prescale_value, postscale_value])
    prescale_node = helper.make_node(
        'Mul', inputs=['sqrt_out', 'prescale_value'], outputs=['prescaled'])
    floor_node = helper.make_node(
        'Floor', inputs=['prescaled'], outputs=['floor_out'])
    ceil_node = helper.make_node(
        'Ceil', inputs=['floor_out'], outputs=['ceil_out'])
    round_node = helper.make_node(
        'Round', inputs=['ceil_out'], outputs=['round_out'])
    postscale_node = helper.make_node(
        'Mul', inputs=['round_out', 'postscale_value'],
        outputs=['postscaled'])
    nodes = [
        abs_node, cos_node, sin_node, exp_node, log_node,
        abs_before_sqrt_node, sqrt_node,
        prescale_node, floor_node, ceil_node, round_node, postscale_node,
    ]
    return nodes


def _make_div_to_prelu_nodes(initializer_list):
    y_reshape_16_shape = helper.make_tensor(
        'y_reshape_16_shape', TensorProto.INT64, [2], [1, 16]
    )
    initializer_list.append(y_reshape_16_shape)
    y_reshape_16_node = helper.make_node(
        'Reshape', inputs=['Y', 'y_reshape_16_shape'],
        outputs=['y_reshaped']
    )
    reshape_to_16_shape = helper.make_tensor(
        'reshape_to_16_shape', TensorProto.INT64, [2], [1, 16]
    )
    initializer_list.append(reshape_to_16_shape)
    reshape_to_16_node = helper.make_node(
        'Reshape', inputs=['postscaled', 'reshape_to_16_shape'],
        outputs=['main_flat']
    )
    div_node = helper.make_node(
        'Div', inputs=['main_flat', 'y_reshaped'], outputs=['div_out'])
    leakyrelu_node = helper.make_node(
        'LeakyRelu', inputs=['div_out'], outputs=['leakyrelu_out'],
        alpha=0.01)
    clip_min = helper.make_tensor(
        'clip_min', TensorProto.FLOAT, [], [0.0])
    clip_max = helper.make_tensor(
        'clip_max', TensorProto.FLOAT, [], [6.0])
    initializer_list.extend([clip_min, clip_max])
    clip_node = helper.make_node(
        'Clip', inputs=['leakyrelu_out', 'clip_min', 'clip_max'],
        outputs=['clip_out'])
    hardswish_node = helper.make_node(
        'HardSwish', inputs=['clip_out'], outputs=['hardswish_out'])
    elu_node = helper.make_node(
        'Elu', inputs=['hardswish_out'], outputs=['elu_out'], alpha=1.0)
    prelu_slope = helper.make_tensor(
        'prelu_slope', TensorProto.FLOAT, [16],
        np.full(16, 0.25).astype(np.float32).tolist()
    )
    initializer_list.append(prelu_slope)
    prelu_node = helper.make_node(
        'PRelu', inputs=['elu_out', 'prelu_slope'], outputs=['prelu_out'])
    nodes = [
        y_reshape_16_node, reshape_to_16_node,
        div_node, leakyrelu_node, clip_node, hardswish_node,
        elu_node, prelu_node,
    ]
    return nodes


def _make_cumsum_node(initializer_list):
    cumsum_axis = helper.make_tensor(
        'cumsum_axis', TensorProto.INT64, [], [1])
    initializer_list.append(cumsum_axis)
    cumsum_node = helper.make_node(
        'CumSum', inputs=['prelu_out', 'cumsum_axis'],
        outputs=['cumsum_out'])
    return [cumsum_node]


def _make_reduction_nodes(initializer_list):
    reduce_axes = helper.make_tensor(
        'reduce_axes', TensorProto.INT64, [1], [1]
    )
    initializer_list.append(reduce_axes)
    reducemax_node = helper.make_node(
        'ReduceMax', inputs=['prelu_out', 'reduce_axes'],
        outputs=['reducemax_out'], keepdims=1
    )
    reducemin_node = helper.make_node(
        'ReduceMin', inputs=['prelu_out', 'reduce_axes'],
        outputs=['reducemin_out'], keepdims=1
    )
    reducemean_node = helper.make_node(
        'ReduceMean', inputs=['prelu_out', 'reduce_axes'],
        outputs=['reducemean_out'], keepdims=1
    )
    reducesum_node = helper.make_node(
        'ReduceSum', inputs=['prelu_out', 'reduce_axes'],
        outputs=['reducesum_out'], keepdims=1
    )
    abs_for_logsum_node = helper.make_node(
        'Abs', inputs=['prelu_out'], outputs=['abs_for_logsum']
    )
    logsum_epsilon = helper.make_tensor(
        'logsum_epsilon', TensorProto.FLOAT, [], [1e-10]
    )
    initializer_list.append(logsum_epsilon)
    logsum_safe_node = helper.make_node(
        'Max', inputs=['abs_for_logsum', 'logsum_epsilon'],
        outputs=['logsum_safe']
    )
    reducelogsum_node = helper.make_node(
        'ReduceLogSum', inputs=['logsum_safe', 'reduce_axes'],
        outputs=['reducelogsum_out'], keepdims=1
    )
    reducelogsumexp_node = helper.make_node(
        'ReduceLogSumExp', inputs=['prelu_out', 'reduce_axes'],
        outputs=['reducelogsumexp_out'], keepdims=1
    )
    nodes = [
        reducemax_node, reducemin_node, reducemean_node, reducesum_node,
        abs_for_logsum_node, logsum_safe_node,
        reducelogsum_node, reducelogsumexp_node,
    ]
    return nodes


def _make_arg_nodes():
    argmax_node = helper.make_node(
        'ArgMax', inputs=['prelu_out'], outputs=['argmax_out'],
        axis=1, keepdims=1
    )
    argmin_node = helper.make_node(
        'ArgMin', inputs=['prelu_out'], outputs=['argmin_out'],
        axis=1, keepdims=1
    )
    cast_argmax_node = helper.make_node(
        'Cast', inputs=['argmax_out'], outputs=['cast_argmax_out'],
        to=TensorProto.FLOAT
    )
    cast_argmin_node = helper.make_node(
        'Cast', inputs=['argmin_out'], outputs=['cast_argmin_out'],
        to=TensorProto.FLOAT
    )
    nodes = [argmax_node, argmin_node, cast_argmax_node, cast_argmin_node]
    return nodes


def _make_comparison_logical_nodes():
    equal_node = helper.make_node(
        'Equal', inputs=['prelu_out', 'y_reshaped'], outputs=['equal_out'])
    greater_node = helper.make_node(
        'Greater', inputs=['prelu_out', 'y_reshaped'],
        outputs=['greater_out'])
    greater_or_equal_node = helper.make_node(
        'GreaterOrEqual', inputs=['prelu_out', 'y_reshaped'],
        outputs=['greater_or_equal_out'])
    less_node = helper.make_node(
        'Less', inputs=['prelu_out', 'y_reshaped'], outputs=['less_out'])
    logical_not_node = helper.make_node(
        'Not', inputs=['equal_out'], outputs=['logical_not_out'])
    logical_and_node = helper.make_node(
        'And', inputs=['greater_out', 'greater_or_equal_out'],
        outputs=['logical_and_out'])
    logical_or_node = helper.make_node(
        'Or', inputs=['greater_out', 'less_out'],
        outputs=['logical_or_out'])
    logical_xor_node = helper.make_node(
        'Xor', inputs=['greater_or_equal_out', 'less_out'],
        outputs=['logical_xor_out'])
    nodes = [
        equal_node, greater_node, greater_or_equal_node, less_node,
        logical_not_node, logical_and_node, logical_or_node,
        logical_xor_node,
    ]
    return nodes


def _make_cast_slice_cmp_nodes(initializer_list):
    cmp_slice_starts = helper.make_tensor(
        'cmp_slice_starts', TensorProto.INT64, [2], [0, 0]
    )
    cmp_slice_ends = helper.make_tensor(
        'cmp_slice_ends', TensorProto.INT64, [2], [1, 1]
    )
    cmp_slice_axes = helper.make_tensor(
        'cmp_slice_axes', TensorProto.INT64, [2], [0, 1]
    )
    initializer_list.extend([cmp_slice_starts, cmp_slice_ends, cmp_slice_axes])
    cmp_logical_outputs = [
        ('equal_out', 'cast_equal_out'),
        ('greater_out', 'cast_greater_out'),
        ('greater_or_equal_out', 'cast_ge_out'),
        ('less_out', 'cast_less_out'),
        ('logical_not_out', 'cast_not_out'),
        ('logical_and_out', 'cast_and_out'),
        ('logical_or_out', 'cast_or_out'),
        ('logical_xor_out', 'cast_xor_out'),
    ]
    cast_nodes = []
    slice_nodes = []
    cast_slice_names = []
    for i, (bool_in, cast_out) in enumerate(cmp_logical_outputs):
        cast_nodes.append(helper.make_node(
            'Cast', inputs=[bool_in], outputs=[cast_out],
            to=TensorProto.FLOAT
        ))
        slice_name = 'cmp_slice_{}'.format(i)
        cast_slice_names.append(slice_name)
        slice_nodes.append(helper.make_node(
            'Slice',
            inputs=[cast_out, 'cmp_slice_starts',
                    'cmp_slice_ends', 'cmp_slice_axes'],
            outputs=[slice_name]
        ))
    return cast_nodes, slice_nodes, cast_slice_names


def _make_einsum_nodes(initializer_list):
    einsum_a_shape = helper.make_tensor(
        'einsum_a_shape', TensorProto.INT64, [2], [4, 4]
    )
    initializer_list.append(einsum_a_shape)
    einsum_a_reshape_node = helper.make_node(
        'Reshape', inputs=['cumsum_out', 'einsum_a_shape'],
        outputs=['einsum_a']
    )
    einsum_node = helper.make_node(
        'Einsum', inputs=['einsum_a', 'matmul_weight'],
        outputs=['einsum_out'], equation='ij,jk->ik'
    )
    einsum_flat_shape = helper.make_tensor(
        'einsum_flat_shape', TensorProto.INT64, [2], [1, 16]
    )
    initializer_list.append(einsum_flat_shape)
    einsum_flat_node = helper.make_node(
        'Reshape', inputs=['einsum_out', 'einsum_flat_shape'],
        outputs=['einsum_flat']
    )
    einsum_slice_starts = helper.make_tensor(
        'einsum_slice_starts', TensorProto.INT64, [2], [0, 0]
    )
    einsum_slice_ends = helper.make_tensor(
        'einsum_slice_ends', TensorProto.INT64, [2], [1, 8]
    )
    einsum_slice_axes = helper.make_tensor(
        'einsum_slice_axes', TensorProto.INT64, [2], [0, 1]
    )
    initializer_list.extend(
        [einsum_slice_starts, einsum_slice_ends, einsum_slice_axes])
    einsum_slice_node = helper.make_node(
        'Slice',
        inputs=['einsum_flat', 'einsum_slice_starts',
                'einsum_slice_ends', 'einsum_slice_axes'],
        outputs=['einsum_sliced']
    )
    nodes = [
        einsum_a_reshape_node, einsum_node,
        einsum_flat_node, einsum_slice_node,
    ]
    return nodes, 'einsum_sliced'


def _make_layernorm_nodes(initializer_list):
    ln_reshape_in_shape = helper.make_tensor(
        'ln_reshape_in_shape', TensorProto.INT64, [3], [1, 4, 10]
    )
    initializer_list.append(ln_reshape_in_shape)
    ln_reshape_in_node = helper.make_node(
        'Reshape', inputs=['concat_z', 'ln_reshape_in_shape'],
        outputs=['ln_ready']
    )
    ln_scale = helper.make_tensor(
        'ln_scale', TensorProto.FLOAT, [10],
        np.ones(10).astype(np.float32).tolist()
    )
    ln_bias_val = helper.make_tensor(
        'ln_bias_val', TensorProto.FLOAT, [10],
        np.zeros(10).astype(np.float32).tolist()
    )
    initializer_list.extend([ln_scale, ln_bias_val])
    layernorm_node = helper.make_node(
        'LayerNormalization',
        inputs=['ln_ready', 'ln_scale', 'ln_bias_val'],
        outputs=['layernorm_out'], axis=-1, epsilon=1e-5
    )
    ln_reshape_out_shape = helper.make_tensor(
        'ln_reshape_out_shape', TensorProto.INT64, [2], [1, 40]
    )
    initializer_list.append(ln_reshape_out_shape)
    ln_reshape_out_node = helper.make_node(
        'Reshape', inputs=['layernorm_out', 'ln_reshape_out_shape'],
        outputs=['Z']
    )
    nodes = [ln_reshape_in_node, layernorm_node, ln_reshape_out_node]
    return nodes


def create_mathmodel_onnx_model(output_path):
    logging.info(f"creating math ops model: {output_path}")
    input_shape = [1, 4, 4]
    input_x = helper.make_tensor_value_info(
        'X', TensorProto.FLOAT, input_shape)
    input_y = helper.make_tensor_value_info(
        'Y', TensorProto.FLOAT, input_shape)
    initializer_list = []
    nodes_gemm = _make_gemm_reshape_matmul_nodes(initializer_list)
    nodes_activations = _make_activation_arith_nodes()
    nodes_unary = _make_unary_math_nodes(initializer_list)
    nodes_div_prelu = _make_div_to_prelu_nodes(initializer_list)
    nodes_cumsum = _make_cumsum_node(initializer_list)
    nodes_reduce = _make_reduction_nodes(initializer_list)
    nodes_arg = _make_arg_nodes()
    nodes_cmp_logical = _make_comparison_logical_nodes()
    cast_nodes, slice_nodes, cast_slice_names = \
        _make_cast_slice_cmp_nodes(initializer_list)
    nodes_einsum, einsum_sliced_name = _make_einsum_nodes(initializer_list)
    concat_inputs = [
        'cumsum_out', 'reducemax_out', 'reducemin_out',
        'reducemean_out', 'reducesum_out', 'reducelogsum_out',
        'reducelogsumexp_out', 'cast_argmax_out', 'cast_argmin_out',
    ] + cast_slice_names + [einsum_sliced_name]
    concat_final_node = helper.make_node(
        'Concat', inputs=concat_inputs, outputs=['concat_z'], axis=1
    )
    nodes_ln = _make_layernorm_nodes(initializer_list)
    all_nodes = (
        nodes_gemm + nodes_activations + nodes_unary +
        nodes_div_prelu + nodes_cumsum +
        nodes_reduce + nodes_arg + nodes_cmp_logical +
        cast_nodes + slice_nodes + nodes_einsum +
        [concat_final_node] + nodes_ln
    )
    graph = helper.make_graph(
        all_nodes,
        'math_ops_graph',
        [input_x, input_y],
        [helper.make_tensor_value_info('Z', TensorProto.FLOAT, [1, 40])],
        initializer=initializer_list
    )
    model = create_low_ir_version_model(
        graph, producer_name='math-ops-generator',
        output_path=output_path)
    logging.info(f"math ops model saved: {output_path}")
